"""Inventory the complete additional C source, not just its linked functions.

This is discovery evidence, not matching credit. Conditional definitions and
commented reconstructions are recorded explicitly and require compilation.
"""
import argparse
from bisect import bisect_right
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from tools.experiments.alternative_source_byte_match_audit import code_name
from tools.match_progress import function_vram, load_symbol_addrs

LEXEMES = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\(?:\r?\n|[^\r\n])|[^"\\\r\n])*"|'
    r'\'(?:\\(?:\r?\n|[^\r\n])|[^\'\\\r\n])*\'')
FUNCTION_DECLARATOR = (r'(?m)^[ \t]*(?:(?:[A-Za-z_]\w*\s+)|(?:[A-Za-z_]\w*\s*(?:\*\s*)+))+'
    r'([A-Za-z_]\w*)\s*\([^;{}]*\)')
DEFINITIONS = re.compile(FUNCTION_DECLARATOR + r'\s*(?:[A-Za-z_]\w*[\w\s*\[\],()]*;\s*)*\{')


def masked_source(source):
    return LEXEMES.sub(lambda match: ''.join('\n' if char == '\n' else ' ' for char in match[0]), source)


def definitions(source):
    masked = masked_source(source)
    boundaries, depths, nesting = [0], [0], 0
    for directive in re.finditer(r'(?m)^\s*#\s*(if|ifdef|ifndef|endif)\b[^\n]*', masked):
        nesting += -1 if directive[1] == 'endif' else 1
        if nesting < 0:
            raise ValueError('Unbalanced conditional directives')
        boundaries.append(directive.end())
        depths.append(nesting)
    records = []
    for match in DEFINITIONS.finditer(masked):
        name = match[1]
        if name in ('if', 'while', 'for', 'switch'):
            continue
        opening = masked.index('{', match.start())
        argument_start = masked.index('(', match.end(1))
        argument_depth, argument_end = 0, None
        for position in range(argument_start, opening):
            argument_depth += (masked[position] == '(') - (masked[position] == ')')
            if argument_depth == 0:
                argument_end = position
                break
        depth, end = 0, None
        for position in range(opening, len(masked)):
            if masked[position] == '{':
                depth += 1
            elif masked[position] == '}':
                depth -= 1
                if not depth:
                    end = position + 1
                    break
        if end is None:
            raise ValueError('Unclosed C definition: ' + name)
        contents = re.sub(r'\s+', '', masked[opening + 1:end - 1])
        records.append(dict(function=name, line=source.count('\n', 0, match.start()) + 1,
            source_start=match.start(), source_end=end,
            old_style=bool(masked[argument_end + 1:opening].strip()),
            declaration=source[match.start():match.end(1)] + '();',
            trivial_body=contents in ('', 'return;', 'return0;', 'returnNULL;'),
            conditional_region=depths[bisect_right(boundaries, match.start()) - 1] != 0))
    return records


def inventory(reference, snapshot):
    with (reference / 'progress.csv').open(newline='') as stream:
        rows = [row for row in csv.DictReader(stream) if row['version'] == 'us' and code_name(row['function'])]
    canonical = {row['function']: row for row in rows}
    reference_anchors = load_symbol_addrs(str(reference / 'symbol_addrs.us.txt'))
    by_address = {function_vram(row, reference_anchors): row for row in rows}
    anchors = load_symbol_addrs(str(snapshot / 'symbol_addrs.us.txt'))
    files, records = [], []
    for path in sorted((snapshot / 'src').rglob('*.c')):
        relative = str(path.relative_to(snapshot)).replace('\\', '/')
        source = path.read_text()
        discovered = definitions(source)
        wrappers = re.findall(r'(?m)^\s*#pragma\s+GLOBAL_ASM\("([^"\n]+)"\)', source)
        commented = sorted(set(re.findall(r'(?m)^\s*//\s*(?:\w+\s*\*?\s+)+(func_[0-9A-F]{8})\s*\([^;{}]*\)\s*\{', source)))
        object_path = snapshot / 'build' / (relative + '.o')
        files.append(dict(path=relative, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            compiled_object_exists=object_path.exists(), lexical_definitions=len(discovered),
            assembly_wrappers=wrappers, commented_drafts=commented))
        for item in discovered:
            name = item['function']
            anchor = int(name[5:], 16) if re.fullmatch(r'func_[0-9A-F]{8}', name) else anchors.get(name)
            row = canonical.get(name) or by_address.get(anchor)
            item.update(path=relative, compiled_object_exists=object_path.exists(),
                canonical_function=row['function'] if row else None,
                section=row['section'] if row else None,
                current_language=row['language'] if row else None,
                canonical_address=function_vram(row, reference_anchors) if row else None)
            records.append(item)
    return dict(source_files=len(files), definitions=len(records),
        compiled_source_files=sum(item['compiled_object_exists'] for item in files),
        uncompiled_source_files=sum(not item['compiled_object_exists'] for item in files),
        trivial_definitions=sum(item['trivial_body'] for item in records),
        canonical_definitions=sum(item['canonical_function'] is not None for item in records),
        section_counts=dict(Counter(item['section'] or 'unanchored' for item in records)),
        files=files, function_definitions=records,
        lexical_inventory_is_not_a_compile_or_matching_result=True)


def compile_uncompiled(root, snapshot, result, output, workers=4):
    """Compile disposable copies with supplied headers; never alter either source.

    This is a frontend/object gate, not a link or byte-match result. Original
    assembly wrapper labels are not reconstructed into these C draft objects.
    """
    output.mkdir(exist_ok=True)
    cc = root / 'ido/ido5.3_recomp/cc'
    processor = root / 'tools/asm-processor/asm_processor.py'
    includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
        'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
    pending = [item for item in result['files'] if not item['compiled_object_exists']]

    def compile_one(item):
        path = snapshot / item['path']
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        stem = item['path'].replace('/', '_').removesuffix('.c')
        raw, processed, obj, log = (output / (stem + suffix) for suffix in ('.c', '-processed.c', '.o', '-diagnostics.txt'))
        raw.write_bytes(path.read_bytes())
        obj.unlink(missing_ok=True)
        flags = ['-g'] if '/audio/' in item['path'] or path.name == 'game_221290.c' else ['-O2', '-g3']
        pre = subprocess.run([sys.executable, str(processor), *flags, str(raw)],
            cwd=snapshot, capture_output=True, text=True)
        diagnostics = pre.stdout + pre.stderr if pre.returncode else pre.stderr
        if pre.returncode:
            status, returncode = 'preprocess_error', pre.returncode
        else:
            processed.write_text(pre.stdout)
            command = [str(cc), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
                '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C',
                '-D_FINALROM', '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838',
                *[flag for path in includes for flag in ('-I', path)], *flags, '-mips2', '-o32',
                '-o', os.path.relpath(obj, snapshot), os.path.relpath(processed, snapshot)]
            compiled = subprocess.run(command, cwd=snapshot, capture_output=True, text=True)
            diagnostics += compiled.stdout + compiled.stderr
            returncode = compiled.returncode
            status = 'compile_error' if returncode else ('object_compiled' if obj.exists() else 'missing_object')
        log.write_text(diagnostics)
        if hashlib.sha256(path.read_bytes()).hexdigest() != before or before != item['sha256']:
            raise ValueError('Source input changed during compile: ' + item['path'])
        return dict(path=item['path'], source_sha256=before, status=status, returncode=returncode,
            compiler_flags=flags, object=str(obj), diagnostics_file=str(log),
            object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest() if status == 'object_compiled' else None,
            not_linked_or_byte_qualified=True)

    records = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for item in pool.map(compile_one, pending):
            records.append(item)
            if len(records) % 16 == 0 or len(records) == len(pending):
                print('Draft compile gate: %d/%d %s' % (len(records), len(pending), dict(Counter(row['status'] for row in records))), flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--compile-uncompiled', action='store_true')
    args = parser.parse_args()
    result = inventory(args.reference.resolve(), args.snapshot.resolve())
    if args.compile_uncompiled:
        root = Path(__file__).resolve().parents[2]
        result['draft_compile_gate'] = compile_uncompiled(root, args.snapshot.resolve(), result,
            args.output.resolve().parent / 'unlinked-c-objects')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('files', 'function_definitions', 'draft_compile_gate')}, indent=2))


if __name__ == '__main__':
    main()
