"""Compile individual C definitions hidden by failed additional-source owners.

Keep original headers, globals, types, conditionals and function declarations.
Only unrelated bodies become declarations in ignored copies. Results are
screening evidence, not qualified source transfers or matching credit.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from tools.experiments.alternative_source_c_inventory import DEFINITIONS, definitions, masked_source
from tools.pad_generated_object import parse_object


PROTOTYPES = re.compile(DEFINITIONS.pattern.removesuffix(r'\{') + r';')
EXTERNS = re.compile(r'(?m)^[ \t]*extern\s+(?:[A-Za-z_]\w*\s+)+(?:\*\s*)*'
    r'([A-Za-z_]\w*)\s*(?:\[[^\];{}]*\]\s*)*;')


def blanks(text):
    return ''.join('\n' if character == '\n' else ' ' for character in text)


def isolate(source, name, drop_unused_interfaces=False):
    records = definitions(source)
    selected = [row for row in records if row['function'] == name]
    if len(selected) != 1:
        raise ValueError('Expected exactly one definition: ' + name)
    masked = masked_source(source)
    needed, unused = None, []
    if drop_unused_interfaces:
        # Examine true top-level declarations, never call/return statements in
        # a body. Global initializer/macro references keep their interfaces.
        global_text = masked
        for row in reversed(records):
            lo, hi = row['source_start'], row['source_end']
            global_text = global_text[:lo] + blanks(global_text[lo:hi]) + global_text[hi:]
        prototypes = list(PROTOTYPES.finditer(global_text)) + list(EXTERNS.finditer(global_text))
        prototypes.sort(key=lambda match: match.start())
        context = global_text
        for declaration in reversed(prototypes):
            lo, hi = declaration.span()
            context = context[:lo] + blanks(context[lo:hi]) + context[hi:]
        row = selected[0]
        needed = set(re.findall(r'\b[A-Za-z_]\w*\b', context + masked[row['source_start']:row['source_end']]))
        unused = [(match.start(), match.end()) for match in prototypes if match[1] not in needed]
    result = source
    edits = [(lo, hi, blanks(source[lo:hi])) for lo, hi in unused]
    for row in records:
        if row['function'] == name:
            continue
        if needed is not None and row['function'] not in needed:
            lo, hi = row['source_start'], row['source_end']
            edits.append((lo, hi, blanks(source[lo:hi])))
        else:
            opening = masked.index('{', row['source_start'], row['source_end'])
            edits.append((opening, row['source_end'], ';'))
    for lo, hi, replacement in sorted(edits, reverse=True):
        result = result[:lo] + replacement + result[hi:]
    return result


def compile_one(root, snapshot, output, item):
    path = snapshot / item['path']
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != item['source_sha256']:
        raise ValueError('Changed source input: ' + item['path'])
    source = data.decode()
    selected = isolate(source, item['function'], item.get('drop_unused_interfaces', False))
    stem = item['path'].replace('/', '_').removesuffix('.c') + '-' + item['function']
    raw, processed, obj, log = (output / (stem + suffix) for suffix in
        ('.c', '-processed.c', '.o', '-diagnostics.txt'))
    raw.write_text(selected)
    obj.unlink(missing_ok=True)
    flags = item['compiler_flags']
    extra_definitions = []
    processor = root / 'tools/asm-processor/asm_processor.py'
    pre = subprocess.run([sys.executable, str(processor), *flags, str(raw)],
        cwd=snapshot, capture_output=True, text=True)
    diagnostics = pre.stdout + pre.stderr if pre.returncode else pre.stderr
    if pre.returncode:
        status, returncode = 'preprocess_error', pre.returncode
    else:
        processed.write_text(pre.stdout)
        includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
            'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
        command = [str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0',
            '-Xfullwarn', '-Xcpluscomm', '-signed', '-nostdinc', '-non_shared',
            '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
            '-D_MIPS_SZLONG=32', '-woff', '649,838',
            *[flag for directory in includes for flag in ('-I', directory)],
            *flags, '-mips2', '-o32', '-o', os.path.relpath(obj, snapshot),
            os.path.relpath(processed, snapshot)]
        result = subprocess.run(command, cwd=snapshot, capture_output=True, text=True)
        diagnostics += result.stdout + result.stderr
        returncode = result.returncode
        if returncode:
            status = 'compile_error'
        elif not obj.exists():
            status = 'missing_object'
        else:
            _, functions, _ = parse_object(obj)
            status = 'object_compiled' if item['function'] in functions else 'selected_definition_not_emitted'
            if set(functions) - {item['function']}:
                extra_definitions = sorted(set(functions) - {item['function']})
                status = 'extra_definition_emitted'
    log.write_text(diagnostics)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Source changed during isolated compilation: ' + item['path'])
    record = dict(path=item['path'], function=item['function'], source_sha256=digest,
        isolated_source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        original_file_compile_failed=True, other_bodies_replaced_with_declarations=True,
        unused_interfaces_omitted=item.get('drop_unused_interfaces', False),
        extra_definitions=extra_definitions,
        status=status, returncode=returncode, compiler_flags=flags,
        object=str(obj), diagnostics_file=str(log),
        object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest() if status == 'object_compiled' else None,
        not_linked_or_active_ABI_owner_qualified=True)
    pending = log.with_suffix('.json.tmp')
    pending.write_text(json.dumps(record, indent=2) + '\n')
    pending.replace(log.with_suffix('.json'))
    return record


def compile_failed(root, snapshot, receipt, output, workers=4, limit=None,
        previous_isolation=None, drop_unused_interfaces=False):
    catalogue = json.loads(receipt.read_text())
    failed = {row['path']: row for row in catalogue['draft_compile_gate']
        if row['status'] in ('compile_error', 'preprocess_error')}
    selected = []
    parser_additions = []
    for path, artifact in sorted(failed.items()):
        actual = hashlib.sha256((snapshot / path).read_bytes()).hexdigest()
        if actual != artifact['source_sha256']:
            raise ValueError('Changed failed-file input: ' + path)
        recorded = [row['function'] for row in catalogue['function_definitions'] if row['path'] == path]
        discovered = definitions((snapshot / path).read_text())
        names = [row['function'] for row in discovered]
        if not set(recorded).issubset(names):
            raise ValueError('Changed definition inventory: ' + path)
        parser_additions.extend(dict(path=path, function=name) for name in names if name not in recorded)
        selected.extend(dict(path=path, function=row['function'], source_sha256=actual,
            compiler_flags=artifact['compiler_flags'], drop_unused_interfaces=drop_unused_interfaces) for row in discovered)
    if previous_isolation:
        previous = json.loads(previous_isolation.read_text())
        if not previous['complete_definition_sweep']:
            raise ValueError('Retry needs a complete prior isolation receipt')
        if previous.get('receipt_sha256') != hashlib.sha256(receipt.read_bytes()).hexdigest():
            raise ValueError('Retry receipt belongs to different source inputs')
        expected = {(row['path'], row['function']): row for row in selected}
        rows = previous['draft_compile_gate']
        if len(rows) != len(expected) or {(row['path'], row['function']) for row in rows} != set(expected):
            raise ValueError('Retry receipt does not cover all failed-file definitions')
        for row in rows:
            original = expected[(row['path'], row['function'])]
            if any(row[key] != original[key] for key in ('source_sha256', 'compiler_flags')):
                raise ValueError('Changed prior isolation input: ' + row['function'])
        pending = {(row['path'], row['function']) for row in previous['draft_compile_gate']
            if row['status'] in ('compile_error', 'preprocess_error', 'extra_definition_emitted')}
        selected = [row for row in selected if (row['path'], row['function']) in pending]
    if limit is not None:
        selected = selected[:limit]
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(lambda item: compile_one(root, snapshot, output, item), selected):
            results.append(row)
            if len(results) % 32 == 0 or len(results) == len(selected):
                print('Isolated compile: %d/%d %s' % (len(results), len(selected),
                    dict(Counter(item['status'] for item in results))), flush=True)
    return dict(failed_source_files=len(failed), attempted_definitions=len(selected),
        complete_definition_sweep=limit is None,
        newly_recognized_definitions=parser_additions,
        statuses=dict(Counter(row['status'] for row in results)), draft_compile_gate=results,
        receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
        previous_isolation_sha256=hashlib.sha256(previous_isolation.read_bytes()).hexdigest() if previous_isolation else None,
        unused_interfaces_omitted=drop_unused_interfaces,
        no_original_source_or_header_changes=True, no_matching_credit_or_source_adoption=True)


def collect_records(snapshot, receipt, directory):
    """Validate completed, immutable records without touching the live workers."""
    original = json.loads(receipt.read_text())
    failed = {row['path']: row for row in original['draft_compile_gate'] if row['status'] == 'compile_error'}
    records = []
    for path in sorted(directory.glob('*-diagnostics.json')):
        row = json.loads(path.read_text())
        artifact = failed[row['path']]
        data = (snapshot / row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['source_sha256'] or row['source_sha256'] != artifact['source_sha256']:
            raise ValueError('Changed collected source: ' + row['path'])
        if row['compiler_flags'] != artifact['compiler_flags']:
            raise ValueError('Changed collected profile: ' + row['function'])
        raw = isolate(data.decode(), row['function'], row.get('unused_interfaces_omitted', False)).encode()
        if hashlib.sha256(raw).hexdigest() != row['isolated_source_sha256']:
            raise ValueError('Changed collected isolation: ' + row['function'])
        if row['status'] == 'object_compiled':
            obj = Path(row['object'])
            if hashlib.sha256(obj.read_bytes()).hexdigest() != row['object_sha256']:
                raise ValueError('Changed collected object: ' + str(obj))
            if set(parse_object(obj)[1]) != {row['function']}:
                raise ValueError('Collected object contains another definition')
        records.append(row)
    return dict(failed_source_files=len(failed), attempted_definitions=len(records),
        complete_definition_sweep=False, verified_completed_records_only=True,
        statuses=dict(Counter(row['status'] for row in records)), draft_compile_gate=records,
        no_matching_credit_or_source_adoption=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('compile_receipt', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--previous-isolation', type=Path)
    parser.add_argument('--drop-unused-interfaces', action='store_true')
    parser.add_argument('--collect-records', type=Path)
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error('workers and limit must be positive')
    root = Path(__file__).resolve().parents[2]
    if args.collect_records:
        result = collect_records(args.snapshot.resolve(), args.compile_receipt.resolve(), args.collect_records.resolve())
    else:
        result = compile_failed(root, args.snapshot.resolve(), args.compile_receipt.resolve(),
            args.output.resolve().parent / (args.output.stem + '-objects'), args.workers, args.limit,
            args.previous_isolation.resolve() if args.previous_isolation else None, args.drop_unused_interfaces)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key:value for key,value in result.items() if key != 'draft_compile_gate'}, indent=2))


if __name__ == '__main__':
    main()
