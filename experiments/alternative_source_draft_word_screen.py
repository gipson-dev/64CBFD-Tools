"""Relocation-aware per-function screen of compiled, previously unlinked C.

Unknown local text/constant-pool bindings are rejected, never assigned fake
addresses. A positive result is a candidate for active-ABI/owner qualification,
not permission to install the draft or claim a matching conversion.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from tools import match_progress as matcher
from tools.experiments.alternative_source_byte_match_audit import code_name, compare
from tools.pad_generated_object import parse_object


def nm_anchors(elf):
    result = subprocess.run(['mips-linux-gnu-nm', '-n', str(elf)], capture_output=True, text=True, check=True)
    return {match[2]: int(match[1], 16) for line in result.stdout.splitlines()
        if (match := re.fullmatch(r'([0-9a-fA-F]+) \S (\S+)', line))}


def emit_function(text, info, relocations, name, anchors):
    lines = ['.section .text', '.balign 4', '.globl ' + name, '.type ' + name + ', @function', name + ':']
    unresolved = set()
    for offset in range(info['value'], info['value'] + info['size'], 4):
        word = struct.unpack_from('>I', text, offset)[0]
        for kind, symbol in relocations.get(offset, []):
            if symbol.startswith('.') or symbol not in anchors:
                unresolved.add(symbol)
            lines.append('.reloc ., %s, %s' % (kind, symbol))
        lines.append('.word 0x%08X' % word)
    lines.append('.size %s, . - %s' % (name, name))
    return '\n'.join(lines) + '\n', sorted(unresolved)


def screen(reference, snapshot, receipt, output):
    output.mkdir(exist_ok=True)
    rows = list(csv.DictReader((reference / 'progress.csv').open()))
    rows = [row for row in rows if row['version'] == 'us' and code_name(row['function'])]
    anchors = matcher.load_symbol_addrs(str(reference / 'symbol_addrs.us.txt'))
    segments = matcher.load_segments('us', str(reference / 'progress.csv'))
    matcher.add_retail_lengths(rows, 'us', segments, anchors)
    canonical = {row['function']: row for row in rows}
    symbols = nm_anchors(snapshot / 'build/conker.us.elf')
    symbols.update(matcher.load_symbol_addrs(str(snapshot / 'symbol_addrs.us.txt')))
    current_words, current_symbols, current_addresses = matcher.load_elf_functions(
        str(reference / 'build/conker.us.elf'), 'mips-linux-gnu-objdump')
    rom = (reference / 'conker.us.bin').read_bytes()
    catalogue = json.loads(receipt.read_text())
    results = []
    positive = []
    for artifact in catalogue['draft_compile_gate']:
        if artifact['status'] != 'object_compiled':
            continue
        obj = Path(artifact['object'])
        if hashlib.sha256(obj.read_bytes()).hexdigest() != artifact['object_sha256']:
            raise ValueError('Modified draft object: ' + str(obj))
        text, functions, relocations = parse_object(obj)
        for name, info in sorted(functions.items()):
            row = canonical.get(name)
            if row is None:
                results.append(dict(function=name, path=artifact['path'], status='unanchored'))
                continue
            entry = matcher.function_vram(row, anchors)
            count = row['_retail_nwords']
            base, rom_base = segments[row['section']]
            truth = list(struct.unpack_from('>%dI' % count, rom, rom_base + entry - base))
            current = current_words.get(name, [])
            already = row['language'] == 'c' and current == truth and current_addresses.get(name) == entry
            if already:
                results.append(dict(function=name, path=artifact['path'], status='already_exact_active_C'))
                continue
            assembly, unresolved = emit_function(text, info, relocations, name, symbols)
            record = dict(function=name, path=artifact['path'], current_language=row['language'],
                section=row['section'], raw_words=info['size'] // 4, retail_words=count,
                source_sha256=artifact['source_sha256'], object_sha256=artifact['object_sha256'])
            if unresolved:
                record.update(status='needs_symbol_or_pool_binding', unresolved=unresolved)
                results.append(record)
                continue
            stem = output / (Path(artifact['path']).stem + '-' + name)
            asm, compiled, script, elf = (stem.with_suffix(suffix) for suffix in ('.s', '.o', '.ld', '.elf'))
            asm.write_text(assembly)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(compiled), str(asm)],
                capture_output=True, text=True, check=True)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            referenced = {symbol for offset, values in relocations.items()
                if info['value'] <= offset < info['value'] + info['size'] for _, symbol in values}
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', name,
                *['--defsym=%s=0x%X' % (symbol, symbols[symbol]) for symbol in sorted(referenced)],
                '-o', str(elf), str(compiled)], capture_output=True, text=True, check=True)
            from tools.experiments.game_actor_classifier_candidates import sections
            raw = sections(elf)['.text'][1][:info['size']]
            emitted = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
            # Only compiler terminal object alignment may lie beyond the full
            # canonical slot. No executable instruction is discarded.
            excess = len(emitted) - count
            if excess > 0 and not any(emitted[count:]):
                emitted = emitted[:count]
            detail = compare(emitted, truth, current_symbols, anchors)
            record.update(status='word_candidate' if detail['content_exact'] else 'word_different',
                **detail, terminal_object_alignment_nops=max(0, excess) if len(emitted) == count else 0)
            results.append(record)
            if detail['content_exact']:
                positive.append(record)
                print('Provisional word candidate: ' + name + ' in ' + artifact['path'], flush=True)
    return dict(reference_elf_sha256=hashlib.sha256((reference / 'build/conker.us.elf').read_bytes()).hexdigest(),
        screened_compiled_draft_files=sum(row['status'] == 'object_compiled' for row in catalogue['draft_compile_gate']),
        statuses=dict(Counter(row['status'] for row in results)), function_results=results,
        provisional_candidates=positive, no_source_adoption_or_matching_credit=True,
        missing_pool_bindings_and_failed_files_remain_unqualified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('compile_receipt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = screen(args.reference.resolve(), args.snapshot.resolve(), args.compile_receipt.resolve(),
        args.output.resolve().parent / 'unlinked-word-screen')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('function_results', 'provisional_candidates')}, indent=2))


if __name__ == '__main__':
    main()
