"""Inventory and compile balanced commented C without editing the archive."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments.alternative_source_c_inventory import DEFINITIONS, LEXEMES, masked_source, definitions
from tools.experiments.alternative_source_function_isolation import compile_one, PROTOTYPES, blanks
from tools.experiments.alternative_source_byte_match_audit import code_name
from tools import match_progress as matcher


def comment_groups(source):
    """Decode only real comments, preserving line numbers and pointer operators."""
    line_comments = []
    for token in LEXEMES.finditer(source):
        text = token[0]
        if text.startswith('/*'):
            text = text[2:-2]
            nonempty = [line for line in text.splitlines() if line.strip()]
            if nonempty and all(line.lstrip().startswith('*') for line in nonempty):
                text = re.sub(r'(?m)^[ \t]*\* ?', '', text)
            yield token.start(), text, 'block'
        elif text.startswith('//'):
            line_start = source.rfind('\n', 0, token.start()) + 1
            if not source[line_start:token.start()].strip():
                line_comments.append((line_start, token.end()))
    groups = []
    for lo, hi in line_comments:
        if groups and not source[groups[-1][1]:lo].strip():
            groups[-1] = (groups[-1][0], hi)
        else:
            groups.append((lo, hi))
    for lo, hi in groups:
        text = re.sub(r'(?m)^([ \t]*)// ?', r'\1', source[lo:hi])
        yield lo, text, 'line'


def commented_definitions(source, known_names=()):
    results = []
    for start, decoded, kind in comment_groups(source):
        masked = masked_source(decoded)
        # A prose parenthesis can greedily span a later real declaration.
        # Probe each line independently so a rejected prose match cannot hide it.
        for line in re.finditer(r'(?m)^(?=[^\r\n]*\S)', masked):
            match = DEFINITIONS.match(masked, line.start())
            if match is None:
                continue
            name = match[1]
            if not code_name(name):
                continue
            prefix = masked[match.start():match.start(1)].split()
            head = prefix[0] if prefix else ''
            builtin = head in ('void', 'char', 'short', 'int', 'long', 'float', 'double',
                'signed', 'unsigned', 'static', 'extern', 'const', 'volatile', 'register', 'struct', 'union')
            if not (re.fullmatch(r'func_[0-9A-Fa-f]{8}', name) or name in known_names or builtin or
                    re.fullmatch(r'(?:[su](?:8|16|32|64)|f(?:32|64))', head)):
                continue
            opening = masked.index('{', match.start())
            depth, end = 0, None
            for position in range(opening, len(masked)):
                depth += (masked[position] == '{') - (masked[position] == '}')
                if depth == 0:
                    end = position + 1
                    break
            results.append(dict(function=name, source_line=source.count('\n', 0, start) +
                decoded.count('\n', 0, match.start()) + 1, comment_kind=kind,
                complete_body=end is not None, body=decoded[match.start():end].strip() if end else None))
    return results


def expand(source, row):
    """Replace only the selected stub/prototype; omit ASM from a C-only screen."""
    name, body = row['function'], row['body']
    records = definitions(source)
    selected = [item for item in records if item['function'] == name]
    if len(selected) > 1:
        raise ValueError('Ambiguous active definition: ' + name)
    result = source
    if selected:
        lo, hi = selected[0]['source_start'], selected[0]['source_end']
        result = result[:lo] + result[hi:]
    masked = masked_source(result)
    regions = definitions(result)
    for item in reversed(regions):
        lo, hi = item['source_start'], item['source_end']
        masked = masked[:lo] + blanks(masked[lo:hi]) + masked[hi:]
    for match in reversed(list(PROTOTYPES.finditer(masked))):
        if match[1] == name:
            lo, hi = match.span()
            result = result[:lo] + blanks(result[lo:hi]) + result[hi:]
    result = re.sub(r'(?m)^[ \t]*#pragma GLOBAL_ASM\("[^"\n]+"\)[ \t]*$', '', result)
    return result + '\n' + body + '\n'


def adjacent_asm_function(source, line):
    for text in reversed(source.splitlines()[:line - 1]):
        stripped = text.strip()
        if not stripped or stripped.startswith('//'):
            continue
        match = re.fullmatch(r'#pragma GLOBAL_ASM\("[^"\n]*/([^/"\n]+)\.s"\)', stripped)
        return match[1] if match else None
    return None


def audit(root, reference, snapshot, output, compile_drafts=False, limit=None, workers=4, profiles=False):
    catalogue = [row for row in csv.DictReader((reference / 'progress.csv').open())
        if row['version'] == 'us' and code_name(row['function'])]
    anchors = matcher.load_symbol_addrs(str(reference / 'symbol_addrs.us.txt'))
    segments = matcher.load_segments('us', str(reference / 'progress.csv'))
    matcher.add_retail_lengths(catalogue, 'us', segments, anchors)
    by_name = {row['function']: row for row in catalogue}
    by_address = {matcher.function_vram(row, anchors): row for row in catalogue}
    current, _, addresses = matcher.load_elf_functions(
        str(reference / 'build/conker.us.elf'), 'mips-linux-gnu-objdump')
    rom = (reference / 'conker.us.bin').read_bytes()
    discovered, files = [], []
    for path in sorted((snapshot / 'src').rglob('*.c')):
        original = path.read_bytes()
        text = original.decode()
        relative = path.relative_to(snapshot).as_posix()
        candidates = commented_definitions(text, set(by_name) | set(anchors))
        if candidates:
            files.append(dict(path=relative, source_sha256=hashlib.sha256(original).hexdigest()))
        for index, candidate in enumerate(candidates):
            name = candidate['function']
            address = int(name[5:], 16) if re.fullmatch(r'func_[0-9A-F]{8}', name) else anchors.get(name)
            canonical = by_name.get(name) or by_address.get(address)
            claimed = adjacent_asm_function(text, candidate['source_line'])
            if canonical is None and claimed in by_name:
                canonical = by_name[claimed]
            record = dict(candidate, path=relative, variant=index,
                source_sha256=hashlib.sha256(original).hexdigest(), canonical_function=canonical['function'] if canonical else None,
                adjacent_asm_function=claimed)
            if canonical is None:
                record['status'] = 'unanchored'
            elif not candidate['complete_body']:
                record['status'] = 'incomplete_comment_body'
            else:
                entry = matcher.function_vram(canonical, anchors)
                base, rom_base = segments[canonical['section']]
                count = canonical['_retail_nwords']
                truth = list(struct.unpack_from('>%dI' % count, rom, rom_base + entry - base))
                words = current.get(canonical['function'], [])
                exact = canonical['language'] == 'c' and addresses.get(canonical['function']) == entry and words == truth
                record.update(status='already_exact_active_C' if exact else 'needs_compilation',
                    section=canonical['section'], retail_words=count, current_language=canonical['language'])
            discovered.append(record)
    results = []
    if compile_drafts:
        selected = [row for row in discovered if row['status'] == 'needs_compilation']
        if limit is not None:
            selected = selected[:limit]
        inputs = snapshot / 'build' / output.stem
        inputs.mkdir(exist_ok=True)
        objects = output.parent / (output.stem + '-objects')
        objects.mkdir(exist_ok=True)
        def compile_candidate(row, flags=None):
            path = snapshot / row['path']
            original = path.read_bytes()
            if hashlib.sha256(original).hexdigest() != row['source_sha256']:
                raise ValueError('Changed commented source input')
            text = expand(original.decode(), row)
            if row['canonical_function'] != row['function']:
                text = re.sub(r'\b' + re.escape(row['function']) + r'\b', row['canonical_function'], text)
            flags = flags or (['-g'] if path.name in ('game_221290.c', 'game_21FC90.c') else ['-O2', '-g3'])
            suffix = '-'.join(flag.lstrip('-') for flag in flags)
            generated = inputs / (row['path'].replace('/', '_').removesuffix('.c') + '-%d-%s.c' % (row['variant'], suffix))
            generated.write_text(text)
            item = dict(path=generated.relative_to(snapshot).as_posix(), function=row['canonical_function'],
                source_sha256=hashlib.sha256(generated.read_bytes()).hexdigest(), compiler_flags=flags,
                drop_unused_interfaces=True, c_only=True)
            result = compile_one(root, snapshot, objects, item)
            result.update(generated_input_path=result['path'], generated_input_sha256=result['source_sha256'],
                path=row['path'], source_sha256=row['source_sha256'], source_line=row['source_line'], variant=row['variant'],
                commented_body_sha256=hashlib.sha256(row['body'].encode()).hexdigest(),
                original_comment_function=row['function'], original_file_compile_failed=False)
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['source_sha256']:
                raise ValueError('Commented archive changed during compilation')
            return result
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(compile_candidate, selected):
                results.append(result)
                if len(results) % 16 == 0 or len(results) == len(selected):
                    print('Commented compile: %d/%d %s' % (len(results), len(selected),
                        dict(Counter(row['status'] for row in results))), flush=True)
        if profiles:
            compiled = {(row['path'], row['variant']) for row in results if row['status'] == 'object_compiled'}
            baseline = {(row['path'], row['variant']): tuple(row['compiler_flags']) for row in results}
            trials = [(row, list(flags)) for row in selected if (row['path'], row['variant']) in compiled
                for flags in (('-O2', '-g3'), ('-O2',), ('-O1', '-g3'), ('-O1',), ('-g',))
                if flags != baseline[(row['path'], row['variant'])]]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for index, result in enumerate(pool.map(lambda pair: compile_candidate(*pair), trials), 1):
                    results.append(result)
                    if index % 32 == 0 or index == len(trials):
                        print('Commented profiles: %d/%d' % (index, len(trials)), flush=True)
    return dict(source_files_with_comment_definitions=len(files), commented_definitions=len(discovered),
        statuses=dict(Counter(row['status'] for row in discovered)), definitions=discovered, files=files,
        draft_compile_gate=results, compilation_statuses=dict(Counter(row['status'] for row in results)),
        reference_ELF_sha256=hashlib.sha256((reference / 'build/conker.us.elf').read_bytes()).hexdigest(),
        no_original_source_or_header_changes=True, no_matching_credit_or_source_adoption=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error('workers and limit must be positive')
    result = audit(Path(__file__).resolve().parents[2], args.reference.resolve(), args.snapshot.resolve(),
        args.output.resolve(), args.compile, args.limit, args.workers, args.profiles)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('definitions', 'files', 'draft_compile_gate')}, indent=2))


if __name__ == '__main__':
    main()
