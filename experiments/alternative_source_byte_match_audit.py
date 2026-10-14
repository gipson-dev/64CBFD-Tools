"""Read-only function-content comparison against a banked retail catalogue.

Diagnostic ELF contents are evidence, not a successful or runnable build.
Only reports are written, outside the candidate or in reference build output. No guards or relocations
are modified, and assembly/bookkeeping/data rows do not receive C credit.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import struct

from tools import match_progress as matcher
from tools.experiments.game_actor_classifier_candidates import sections


def rows(path):
    with path.open(newline='') as stream:
        return [row for row in csv.DictReader(stream) if row['version'] == 'us']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_name(name):
    return not name.startswith(('D_', '.', 'L8')) and '.NON_MATCHING' not in name


def compare(body, truth, symbols, anchors):
    kind, differences = matcher.classify(body, truth, symbols, anchors)
    strict = body == truth
    padding_only = len(body) < len(truth) and body == truth[:len(body)] and not any(truth[len(body):])
    return dict(classification=kind, real_word_differences=differences,
        strict_full_slot=strict, content_exact=kind == 'exact',
        omitted_alignment_nops=len(truth) - len(body) if padding_only else 0,
        retail_words=len(truth), emitted_words=len(body))


def audit(reference, candidate):
    canonical = rows(reference / 'progress.csv')
    anchors = matcher.load_symbol_addrs(str(reference / 'symbol_addrs.us.txt'))
    segments = matcher.load_segments('us', str(reference / 'progress.csv'))
    matcher.add_retail_lengths(canonical, 'us', segments, anchors)
    by_name = {row['function']: row for row in canonical}
    by_address = {}
    for row in canonical:
        address = matcher.function_vram(row, anchors)
        if address in by_address:
            raise ValueError('Ambiguous reference address: 0x%X' % address)
        by_address[address] = row
    rom = (reference / 'conker.us.bin').read_bytes()
    if hashlib.sha1(rom).hexdigest() != '842e3d348e3c8ae0039e2ab367ad492f9b5266d8':
        raise ValueError('Unexpected decompressed US reference')
    if (candidate / 'conker.us.bin').read_bytes() != rom:
        raise ValueError('Candidate reference differs')
    old_words, old_symbols, old_addresses = matcher.load_elf_functions(
        str(reference / 'build/conker.us.elf'), 'mips-linux-gnu-objdump')
    new_words, new_symbols, new_addresses = matcher.load_elf_functions(
        str(candidate / 'build/conker.us.elf'), 'mips-linux-gnu-objdump')
    image_sections = sections(candidate / 'build/conker.us.elf')
    text_sections = {}
    for section, (vram, start) in segments.items():
        body = image_sections['.' + section][1]
        truth = rom[start:start + len(body)]
        if len(truth) != len(body):
            raise ValueError('Section exceeds reference: ' + section)
        text_sections[section] = dict(bytes=len(body), different_bytes=sum(a != b for a, b in zip(body, truth)),
            sha256=hashlib.sha256(body).hexdigest())
    new_anchors = matcher.load_symbol_addrs(str(candidate / 'symbol_addrs.us.txt'))
    candidate_rows = rows(candidate / 'progress.csv')
    excluded, unanchored, matched, occupied = Counter(), [], [], set()
    all_reference, current = [], []

    def truth_for(row):
        address = matcher.function_vram(row, anchors)
        vram, start = segments[row['section']]
        size = row['_retail_nwords'] * 4
        offset = address - vram + start
        if size <= 0 or offset < 0 or offset + size > len(rom):
            raise ValueError('Invalid retail slot: ' + row['function'])
        return address, list(struct.unpack_from('>%dI' % (size // 4), rom, offset))

    for row in canonical:
        if not code_name(row['function']):
            continue
        address, truth = truth_for(row)
        record = dict(function=row['function'], section=row['section'], retail_address=address,
            current_converted=row['language'] == 'c',
            **compare(old_words.get(row['function'], []), truth, old_symbols, anchors))
        all_reference.append(record)
        if row['language'] == 'c':
            current.append(record)

    for row in candidate_rows:
        name = row['function']
        if '.NON_MATCHING' in name:
            excluded['bookkeeping'] += 1
            continue
        if row['language'] != 'c':
            excluded['assembly_or_other'] += 1
            continue
        if not code_name(name):
            excluded['C_data_or_local_labels'] += 1
            continue
        if name in by_name:
            reference_row = by_name[name]
        else:
            address = matcher.name_implied_vram(name) or new_anchors.get(name)
            reference_row = by_address.get(address)
        if reference_row is None or reference_row['section'] != row['section']:
            unanchored.append(dict(row))
            continue
        address, truth = truth_for(reference_row)
        if address in occupied:
            raise ValueError('Duplicate candidate function address: 0x%X' % address)
        occupied.add(address)
        if name not in new_words:
            raise ValueError('Converted candidate missing from ELF: ' + name)
        matched.append(dict(function=reference_row['function'], candidate_function=name,
            section=row['section'], filename=row['filename'], retail_address=address,
            linked_address=new_addresses[name], current_converted=reference_row['language'] == 'c',
            **compare(new_words[name], truth, new_symbols, new_anchors)))

    def totals(records):
        result = defaultdict(Counter)
        for record in records:
            for section in (record['section'], 'total'):
                counts = result[section]
                counts['functions'] += 1
                counts[record['classification']] += 1
                counts['strict_full_slot'] += record['strict_full_slot']
                counts['omitted_alignment_nops'] += record['omitted_alignment_nops']
                counts['retail_bytes'] += record['retail_words'] * 4
                counts['content_exact_retail_bytes'] += record['retail_words'] * 4 if record['content_exact'] else 0
                if 'linked_address' in record:
                    counts['at_retail_address'] += record['linked_address'] == record['retail_address']
        return {section: dict(counts) for section, counts in result.items()}

    current_by_name = {record['function']: record for record in all_reference}
    potential = [record for record in matched if record['content_exact'] and
        (not current_by_name[record['function']]['content_exact'] or not record['current_converted'])]
    return dict(reference_elf_sha256=sha(reference / 'build/conker.us.elf'),
        candidate_elf_sha256=sha(candidate / 'build/conker.us.elf'),
        original_decompressed_sha1=hashlib.sha1(rom).hexdigest(),
        definition='Executable C rows anchored to reference catalogue; D_ data and .NON_MATCHING excluded; content independent of placement',
        canonical_executable_functions=len(all_reference), candidate=totals(matched),
        main_guarded=totals(current), excluded_rows=dict(excluded), unanchored_C_rows=unanchored,
        text_sections_including_unconverted_assembly=text_sections,
        canonical_catalogue_by_section=dict(Counter(record['section'] for record in all_reference)),
        potential_function_donors=potential, candidate_functions=matched,
        not_a_runnable_or_normally_linked_build=True, no_source_adoption=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    reference, candidate, output = (path.resolve() for path in (args.reference, args.candidate, args.output))
    if output.is_relative_to(candidate) or (output.is_relative_to(reference) and
            not output.is_relative_to(reference / 'build')):
        raise ValueError('Reports must be outside candidate and reference source inputs')
    result = audit(reference, candidate)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    for group in ('candidate', 'main_guarded'):
        print(group, json.dumps(result[group], sort_keys=True))
    print('Unanchored C rows:', len(result['unanchored_C_rows']))
    print('Potential individual function donors:', len(result['potential_function_donors']))
    print('Diagnostic comparison only; no source adopted')


if __name__ == '__main__':
    main()
