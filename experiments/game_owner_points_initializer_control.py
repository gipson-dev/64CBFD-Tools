"""Certify the initializer's closed two-pass induction and guarded direct exit."""
import argparse
import csv
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_points_initializer_induction as source
from tools.experiments.game_owner_ribbon_renderer_registers import fields as prior_fields
from tools.pad_generated_object import parse_object

SELECTED = source.SELECTED
TYPES = source.TYPES
LOOP, OMIT, BRANCH, DELAY = 0x11C, 0x238, 0x254, 0x258
EXPECTED_SLT, EXPECTED_BRANCH, DIRECT_BRANCH = 0x00A3082A, 0x1420FFB1, 0x14A3FFB2


def branch_target(offset, word):
    immediate = word & 65535
    return offset + 4 + (immediate if immediate < 32768 else immediate - 65536) * 4


def fields(word):
    if word >> 26 == 0 and word & 63 == 42:
        return (21, 16), (11,)
    return prior_fields(word)


def certify(words):
    if len(words) != 158 or words[0] != 0x27BDFFA0:
        raise ValueError('complete 158-word/frame0x60 initializer required')
    if words[OMIT // 4] != EXPECTED_SLT or words[BRANCH // 4] != EXPECTED_BRANCH:
        raise ValueError('stale SLT/branch control words')
    if words[DELAY // 4] != 0xE7A4004C or words[-2:] != [0x03E00008, 0x27BD0060]:
        raise ValueError('stale delay-store or complete return tail')
    reads, writes, transfers = {r: [] for r in (1, 3, 5)}, {r: [] for r in (1, 3, 5)}, []
    for index, word in enumerate(words):
        offset = index * 4
        inputs, outputs = fields(word)
        for register in reads:
            if any(word >> shift & 31 == register for shift in inputs):
                reads[register].append(offset)
            if any(word >> shift & 31 == register for shift in outputs):
                writes[register].append(offset)
        op, fn = word >> 26, word & 63
        if op in (1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 23) or (
                op == 0 and fn in (8, 9)) or (op == 17 and word >> 21 & 31 == 8):
            transfers.append(offset)
    if transfers != [BRANCH, 0x270] or branch_target(BRANCH, words[BRANCH // 4]) != LOOP:
        raise ValueError('unexpected CFG or loop-back target')
    if writes[5] != [0x6C, 0x120] or words[0x6C // 4] != 0x24050002 or words[0x120 // 4] != 0x24A50004:
        raise ValueError('counter must initialize2 and advance4 exactly once per pass')
    if writes[3] != [0x4C] or words[0x4C // 4] != 0x2403000A:
        raise ValueError('end count must initialize10 and remain invariant')
    if reads[5] != [0x120, OMIT] or reads[3] != [OMIT]:
        raise ValueError('unexpected counter/end use')
    if [offset for offset in reads[1] if offset > OMIT] != [BRANCH] or (
            [offset for offset in writes[1] if offset >= OMIT] != [OMIT]):
        raise ValueError('SLT result must be consumed only by the branch and dead afterward')
    if words[LOOP // 4] != 0x8D610000:
        raise ValueError('loop must redefine AT before its next use')
    states = []
    counter = 2
    while True:
        entry = counter
        counter += 4
        less = counter < 10
        different = counter != 10
        if less != different:
            raise ValueError('induction predicates disagree')
        states.append(dict(entry=entry, tested=counter, end=10, take=less))
        if not less:
            break
        if len(states) > 2:
            raise ValueError('unexpected reachable induction state')
    if states != [dict(entry=2, tested=6, end=10, take=True),
                  dict(entry=6, tested=10, end=10, take=False)]:
        raise ValueError('two-pass induction proof failed')
    if branch_target(BRANCH - 4, DIRECT_BRANCH) != LOOP:
        raise ValueError('relocated direct branch does not retain the loop target')
    return dict(raw_words=158, emitted_words=157, frame_bytes=96, counter_register=5,
        invariant_end_register=3, reachable_states=states, only_dead_AT_result_omitted=True,
        memory_FP_and_delay_store_unchanged=True, omitted_offset=OMIT,
        raw_branch_offset=BRANCH, emitted_branch_offset=BRANCH - 4, loop_offset=LOOP,
        return_and_saved_registers_unchanged=True, no_hardware_or_full_match_claim=True)


def normalize(words):
    certify(words)
    result = list(words)
    result[BRANCH // 4] = DIRECT_BRANCH
    del result[OMIT // 4]
    return result


def guard_rows(object_path):
    text, functions, relocations = parse_object(object_path)
    target = functions[source.fitting.base.FUNCTION]
    words = list(struct.unpack_from('>%dI' % (target['size'] // 4), text, target['value']))
    certify(words)
    rows = []
    for offset, replacement, omit in ((OMIT, EXPECTED_SLT, True), (BRANCH, DIRECT_BRANCH, False)):
        if relocations.get(target['value'] + offset, []):
            raise ValueError('control normalization cannot move or omit a relocation')
        rows.append(dict(filename='generated_1E0560', function='func_151B3A7C',
            offset='0x%03X' % offset, expected='0x%08X' % words[offset // 4],
            replacement='0x%08X' % replacement, expected_relocations='-', replacement_relocations='-',
            note='Normalize certified two-pass point initializer counter exit',
            insert_after='', insert_after_relocations='', omit=str(omit).lower()))
    return rows


def compile_candidate(root, out, name, body=None, profile='o2g3', symbols=None):
    meta, words = source.compile_candidate(root, out, name, SELECTED if body is None else body, profile, symbols)
    fitted = normalize(words)
    retail = struct.unpack_from('>157I', (root / 'conker/conker.us.bin').read_bytes(), source.fitting.base.ROM)
    return dict(meta, raw_body_words=meta['body_words'], raw_differences=meta['differences'],
        body_words=len(fitted), differences=sum(a != b for a, b in zip(fitted, retail)), guards=2), fitted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--certificate', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-initializer-control'
    meta, fitted = compile_candidate(root, out, 'selected')
    if args.certificate:
        _, raw = source.compile_candidate(root, out, 'raw-selected')
        meta['certificate'] = certify(raw)
        rows = guard_rows(out / 'selected.o')
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        (out / 'guards.csv').write_text(stream.getvalue())
    (out / 'measurement.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
