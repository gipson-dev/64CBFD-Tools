"""Qualify defined color-fade C with a bounded mask/lifetime/schedule normalization."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_color_fade as previous
from tools.experiments.game_table_fade_match import registers as rename_general
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-record-color-fade-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
STEP, TABLE, CALLER, REMOVE = previous.STEP, previous.TABLE, previous.CALLER, previous.REMOVE
PATHS, BASELINE, build, freeze = previous.PATHS, previous.BASELINE, previous.build, previous.freeze
SELECTED = previous.SELECTED.replace(
    '/* Keep fade math full-width and preserve retail\'s repeated width test. */',
    '/* Keep fade math full-width and preserve retail\'s repeated width test.\n'
    ' * Guards remove a redundant MIPS shift mask and normalize temporary scheduling. */')
RAW_SHA256 = '1d6a3ea7c21859ad2e7ed981a0af75c3e78711237ada3f7485d7ff182acfc8ac'
RELOCATIONS = {24: [('R_MIPS_HI16', 'D_800BE9E4')], 28: [('R_MIPS_LO16', 'D_800BE9E4')],
    80: [('R_MIPS_HI16', 'D_800BE9E4')], 88: [('R_MIPS_LO16', 'D_800BE9E4')],
    128: [('R_MIPS_HI16', 'D_800BE9E4')], 136: [('R_MIPS_LO16', 'D_800BE9E4')]}


def recovered_owner(before):
    return previous.recovered_owner(before, SELECTED)


def measure(root, out, label='qualified', selected=None):
    return previous.measure(root, out, label, SELECTED if selected is None else selected)


def raw_target(obj):
    data, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return data[f['value']:f['value'] + f['size']], {
        p - f['value']: list(r) for p, r in rel.items() if f['value'] <= p < f['value'] + f['size']}


def registers(word, mapping):
    # REGIMM.rt encodes the branch kind, not a register operand.
    if word >> 26 == 1:
        old = word >> 21 & 31
        return word & ~(31 << 21) | mapping.get(old, old) << 21
    return rename_general(word, mapping)


def plan():
    order = [i for i in range(98) if i != 24]
    order[21:24] = [22, 23, 21]
    order[69:95] = [70, 71, 76, 73, 74, 72, 77, 78, 79, 80, 81, 82,
        83, 84, 75, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95]
    result = []
    for old in order:
        mapping = {}
        if old <= 36:
            mapping = {2: 3, 3: 2}
        if old == 25:
            mapping.update({8: 25, 9: 8})
        if old == 26:
            mapping[9] = 8
        if 39 <= old <= 55:
            mapping = {2: 3, 3: 2, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14}
        if old in (56, 62):
            mapping = {24: 2}
        if old in (58, 61):
            mapping = {25: 15}
        if 63 <= old <= 65:
            mapping = {24: 2, 8: 24, 3: 2}
        if old in (67, 69):
            mapping = {5: 3}
        if old == 68:
            mapping = {3: 2}
        # Each color consumes its coefficient before the last color reuses T9 for LO.
        if 70 <= old <= 82:
            mapping = {3: 2, 5: 3, 7: 25, 9: 5, 10: 8, 11: 9, 12: 10, 13: 11, 14: 5}
        if 83 <= old <= 89:
            mapping = {5: 3, 7: 25, 14: 5, 15: 12, 25: 13, 24: 14, 8: 15}
        if 90 <= old <= 95:
            mapping = {5: 3, 7: 25, 9: 5, 10: 24, 11: 25, 12: 8, 13: 9}
        result.append((old, mapping))
    return result


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown color-fade words or relocations')
    words = struct.unpack('>98I', raw)
    output, moved = [], {}
    for new, (old, mapping) in enumerate(plan()):
        word = registers(words[old], mapping)
        if old in (17, 19):
            word = word & 0xFFFF0000 | ((word - 1) & 65535)
        output.append(word)
        if old * 4 in relocations:
            moved[new * 4] = list(relocations[old * 4])
    return struct.pack('>97I', *output), moved


def guard_manifest(before, raw, relocations):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown color-fade guard predecessor')
    normalized, moved = normalize(raw, relocations)
    words, replacements = struct.unpack('>98I', raw), struct.unpack('>97I', normalized)
    fields = next(csv.reader(io.StringIO(before.decode())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    for index, expected in enumerate(words):
        omit = index == 24
        emitted = index if index < 24 else index - 1
        replacement = expected if omit else replacements[emitted]
        old, new = relocations.get(index * 4, []), [] if omit else moved.get(emitted * 4, [])
        if not omit and expected == replacement and not old and not new:
            continue
        spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
        note = ('Omit low-five-bit mask consumed only by MIPS SLLV' if omit else
            'Normalize color-fade branch span and closed temporary lifetimes' if index < 70 else
            'Normalize independent color loads and closed multiply/LO lifetimes')
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec(old), replacement_relocations=spec(new), note=note,
            insert_after='', insert_after_relocations='', omit='true' if omit else 'false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    obj, raw_words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (98, 89, 0, ''):
        raise ValueError('Unknown defined color-fade compiler shape')
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>97I', data, f['value']))
    truth = list(struct.unpack_from('>97I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != 388 or len(normalized) != 388 or words != truth:
        raise ValueError('Color-fade production padding is not exact')
    row.update(guarded_words=97, guarded_differences=0, raw_C_exact=False,
        guards_added=len(guards[len((out / 'before-guards').read_bytes()):].splitlines()), moved_relocations=moved)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown color-fade match predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown color-fade match predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 388)
    result[offset:offset + 388] = rom[ROM:ROM + 388]
    struct.pack_into('>I', result, row[0] + 8, 388)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
