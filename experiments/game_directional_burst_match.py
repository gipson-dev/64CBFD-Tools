"""Retain the burst's compiled operations and omit one duplicate zero transfer."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_directional_burst as previous
from tools.experiments.game_directional_burst_proof import prove
from tools.experiments import game_quad_edge_match as fields
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-directional-burst-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = (previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS)
PATHS, BASELINE, freeze, build = previous.PATHS, previous.BASELINE, previous.freeze, previous.build
SELECTED = previous.SELECTED.replace(
    '/* Emit a directional burst using the compact or extended record factory. */',
    '/* Emit a directional burst using the compact or extended record factory.\n'
    ' * Guards retain the checked value graph and omit a duplicate zero transfer. */')
RAW_SHA256 = '90aaf609d75863cdfe97818d966344a8fb7854f8e3cd762b997533ce9afa0f3d'
RELOCATIONS = {
    32: [('R_MIPS_HI16', 'D_800CC34A')], 36: [('R_MIPS_LO16', 'D_800CC34A')],
    40: [('R_MIPS_26', 'func_151EF610')], 72: [('R_MIPS_26', 'func_150489B0')],
    84: [('R_MIPS_26', 'func_15048A40')], 100: [('R_MIPS_26', 'func_150489B0')],
    380: [('R_MIPS_26', 'func_1516D4E8')], 716: [('R_MIPS_26', 'func_1516D99C')],
}
BINDINGS = dict(D_800CC34A=previous.DEFAULT_ANGLE, func_151EF610=previous.RANDOM,
    func_150489B0=previous.COSINE, func_15048A40=previous.SINE,
    func_1516D4E8=previous.SMALL, func_1516D99C=previous.LARGE)
ORDER = (*range(32), 34, 33, 78, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
    46, 47, 48, 53, 49, 50, 51, 54, 55, 52, 57, 58, 59, 56, 74, 62, 63, 60,
    61, 66, 67, 68, 70, 69, 65, 64, 71, 72, 73, 75, 76, 77, 151, 79, 80,
    81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97,
    98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 112, 108, 109, 110, 113,
    114, 111, 116, 117, 118, 115, 126, 121, 122, 119, 120, 125, 123, 124,
    127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140,
    141, 142, 143, 144, 145, 146, 147, 148, 149, 150, *range(152, 185))
REGISTERS = {
    23: (0, 0, 12), 26: (29, 12), 27: (29, 2), 28: (29, 12),
    30: (0, 2, 2), 31: (0, 16), 33: (0, 12, 12), 35: (16, 16, 14),
    36: (2, 2, 2), 38: (12, 12, 12), 43: (0, 2, 4), 46: (0, 12, 8),
    49: (0, 14, 18), 55: (0, 4, 6), 58: (0, 8, 10), 59: (2, 6),
    61: (0, 18, 4), 62: (3, 10), 65: (12, 4), 68: (2, 13),
    71: (3, 24), 102: (0, 2, 6), 105: (0, 12, 10), 108: (0, 14, 4),
    114: (0, 6, 8), 117: (0, 10, 18), 118: (2, 8), 120: (0, 4, 6),
    121: (3, 18), 124: (12, 6),
}


def register_fields(word):
    if word >> 26 in (33, 37) or word >> 26 == 0 and word & 63 == 26:
        return (21, 16)
    return fields.register_fields(word)


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown burst compiler words or bindings')
    words = struct.unpack('>185I', raw)
    if len(ORDER) != 184 or sorted(ORDER) != [i for i in range(185) if i != 32]:
        raise ValueError('Burst plan must retain every operation except the duplicate MTC1 zero')
    positions = {old: new for new, old in enumerate(ORDER)}
    output, moved = [], {}
    for at, old in enumerate(ORDER):
        word = words[old]
        if word >> 21 & 31 == 29 and word >> 26 in (35, 43) and word & 65535 == 0xD0:
            word = word & ~65535 | 0xD4
        if word >> 26 in (4, 5):
            target = old + 1 + ((word & 65535) + 32768) % 65536 - 32768
            delta = positions[target] - at - 1
            if not -32768 <= delta <= 32767:
                raise ValueError('Burst branch exceeds signed reach')
            word = word & ~65535 | delta & 65535
        if at in REGISTERS:
            shifts, values = register_fields(word), REGISTERS[at]
            if len(shifts) != len(values) or any(not 0 <= value < 32 for value in values):
                raise ValueError('Invalid burst register plan')
            for shift, value in zip(shifts, values):
                word = word & ~(31 << shift) | value << shift
        output.append(word)
        if old * 4 in relocations:
            moved[at * 4] = list(relocations[old * 4])
    return struct.pack('>184I', *output), moved


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def link_target(out, name, raw, rel, entry=ENTRY, bindings=None):
    bindings = BINDINGS if bindings is None else bindings
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), rel, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound burst symbols: ' + repr(missing))
    path = out / (name + '.s')
    path.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(path.with_suffix('.ld')), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(path.with_suffix('.elf')),
        str(path.with_suffix('.o'))], check=True, capture_output=True)
    return list(struct.unpack_from('>%dI' % (len(raw) // 4), sections(path.with_suffix('.elf'))['.text'][1]))


def guard_manifest(before, raw, rel):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown burst guard predecessor')
    normalized, moved = normalize(raw, rel)
    old, new = struct.unpack('>185I', raw), struct.unpack('>184I', normalized)
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    spec = lambda rows: ';'.join(kind + ':' + name for kind, name in rows) or '-'
    emitted = 0
    for i, expected in enumerate(old):
        omit = i == 32
        replacement = expected if omit else new[emitted]
        a, b = rel.get(i * 4, []), [] if omit else moved.get(emitted * 4, [])
        identity = not omit and expected == replacement and a == b
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec(a), replacement_relocations=spec(b),
            note='Omit duplicate burst zero transfer' if omit else 'Retain burst compiler fingerprint' if identity else
                'Normalize checked burst ordered value graph, home and instruction schedule',
            insert_after='', insert_after_relocations='', omit='true' if omit else 'false'))
        emitted += not omit
    return before + output.getvalue().encode()


def recovered_owner(before):
    return previous.recovered_owner(before, SELECTED)


def qualify(root, out):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text()), 'qualified')
    if diagnostics:
        raise ValueError('Burst compiler diagnostics: ' + diagnostics)
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    raw_words = link_target(out, 'proof-raw', raw, rel)
    words = link_target(out, 'proof-normalized', normalized, moved)
    result = prove(raw_words, words)
    truth = list(struct.unpack_from('>184I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Derived burst stream is not retail exact')
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 736 or list(struct.unpack_from('>184I', data, f['value'])) != words:
        raise ValueError('Burst full-owner padding differs')
    row = dict(raw_words=185, raw_differences=sum(a != b for a, b in zip(raw_words, truth)) + 1,
        normalized_words=184, normalized_differences=0, frame=256, guards_added=185,
        identity_guards=guards[len((out / 'before-guards').read_bytes()):].count(b'Retain burst compiler fingerprint'),
        omitted_duplicate_zero_index=32, moved_relocations=moved, ordered_value_proof=result,
        not_a_raw_C_match=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown burst predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown burst predecessor extent')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 736)
    result[offset:offset + 736] = rom[ROM:ROM + 736]
    struct.pack_into('>I', result, row[0] + 8, 736)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
