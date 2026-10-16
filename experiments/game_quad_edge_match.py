"""Derive the emitter's retail layout from a closed, checked C operation stream."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_quad_edge_loop as previous
from tools.experiments.game_quad_edge_loop_values import prove
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-quad-edge-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = (previous.OWNER, previous.FUNCTION,
    previous.ENTRY, previous.ROM, previous.WORDS)
PATHS, BASELINE, freeze = previous.PATHS, previous.BASELINE, previous.freeze
build = previous.previous.build
SELECTED = previous.SELECTED.replace(
    '/* Emit packed particles along each edge of a four-vertex perimeter. */',
    '/* Emit packed particles along each edge of a four-vertex perimeter.\n'
    ' * Guards normalize the checked loop schedule and unescaped private homes. */')
RAW_SHA256 = 'd4596869f8e006f6a5ae9865601afd8586e315eb100909624290ce11817fb9df'
RELOCATIONS = {
    92: [('R_MIPS_HI16', 'D_8008CBF4')], 96: [('R_MIPS_LO16', 'D_8008CBF4')],
    120: [('R_MIPS_HI16', 'D_8008CC00')], 124: [('R_MIPS_LO16', 'D_8008CC00')],
    140: [('R_MIPS_HI16', 'D_8008CC0C')], 144: [('R_MIPS_LO16', 'D_8008CC0C')],
    368: [('R_MIPS_HI16', 'D_800A6E84')], 432: [('R_MIPS_LO16', 'D_800A6E84')],
    652: [('R_MIPS_26', 'func_150ADA20')], 664: [('R_MIPS_26', 'func_150ADA20')],
    696: [('R_MIPS_26', 'func_150ADA20')], 948: [('R_MIPS_26', 'func_1516D4E8')],
}
BINDINGS = dict(func_150ADA20=0x150ADA20, func_1516D4E8=0x1516D4E8,
    D_8008CBF4=0x8008CBF4, D_8008CC00=0x8008CC00,
    D_8008CC0C=0x8008CC0C, D_800A6E84=0x800A6E84)

# Retain every compiled operation except the redundant next-index move, the
# edge+1 comparison's constant one, and its now-unused pre-loop scheduling NOP.
# Materialize only retail's unescaped edge home; do not invent a helper input.
OMITTED = (66, 72, 145)
ORDER = (*range(63),
    63, 64, 65, 67, 68, 69, 70, 71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
    83, 84, 85, 86, 87, 88, 119, 90, 91, 89, 124, 93, 94, 120, 125, 127, 92,
    109, 101, 97, 103, 98, 104, 100, 95, 105, 96, 99, 102, 106, 107, 108,
    114, 113, 111, 116, 118, 123, 121, 112, 115, 128, 130, 122, 133, 142, 131,
    126, 132, 135, 134, 146, 136, 143, 138, 139, 149, 144, 141, 140, 137,
    'store-edge', 129, 110, 147, 148, 117, 150, 151, 152, 'load-edge', 153, 154,
    155, 156, 'store-edge', 157, 158, 159, 160, 161, 162, 163, 164, *range(165, 266))
REGISTERS = {
    40: (0, 0, 5), 63: (5, 1), 65: (5, 4), 67: (29, 4),
    68: (5, 24), 69: (29, 24), 71: (5, 0), 72: (4, 8),
    74: (5, 1), 75: (29, 25), 76: (29, 13), 78: (29, 13),
    79: (29, 25), 80: (29, 15), 81: (8, 4, 8), 82: (8, 8),
    83: (15, 8, 16), 84: (16, 10), 85: (21, 16), 87: (29, 25),
    89: (16, 16), 90: (29, 9), 91: (25, 15), 93: (21, 18),
    94: (29, 8), 95: (15, 25, 15), 96: (15, 8, 17), 98: (9, 13),
    99: (6, 4, 0), 100: (18, 16, 4), 101: (0, 0, 8), 103: (0, 8, 10),
    105: (8, 6, 2), 106: (2, 10), 107: (2, 2, 10), 108: (0, 10, 16),
    109: (3, 16), 110: (9, 0), 111: (29, 5), 117: (1, 18),
    118: (28, 8, 10), 119: (29, 11), 121: (1, 8), 122: (2, 12),
    123: (3, 25), 125: (28, 18, 4), 126: (29, 11), 127: (3, 11),
    129: (25, 15), 130: (12, 14), 131: (0, 10, 16), 132: (13, 10),
    133: (2, 9), 134: (0, 4, 6), 135: (23, 16), 137: (0, 10, 16),
    138: (30, 6), 139: (29, 14), 140: (29, 15), 141: (29, 11),
    144: (20, 18), 147: (0, 18, 4), 160: (2, 8, 20), 169: (10,),
    170: (10, 22, 19), 177: (17, 10), 179: (29, 9), 180: (29, 10),
    181: (29, 10), 183: (17, 12), 184: (2, 10), 185: (4, 14),
    186: (14, 4), 187: (29, 12), 188: (17, 14), 190: (0, 24),
    191: (29, 24), 195: (29, 9), 197: (5, 13), 198: (13, 5),
    199: (6, 8), 200: (8, 6), 201: (29, 8), 202: (29, 13),
    203: (29, 9), 204: (29, 24), 205: (29, 25), 206: (29, 15),
    207: (3, 11), 208: (12,), 209: (29, 14), 210: (12, 30, 14),
    211: (29, 14), 212: (11, 0, 3), 213: (29, 11), 214: (29, 11),
    228: (29, 8), 229: (29, 13), 230: (29, 9), 231: (29, 24),
    232: (29, 25), 233: (29, 15), 234: (10, 0), 239: (29, 13),
    241: (20, 13), 243: (29, 5), 246: (5, 1),
}


def register_fields(word):
    op = word >> 26
    if word == 0 or op == 3:
        return ()
    if op in (9, 12, 15, 35, 36, 40, 43, 49, 53, 57, 61, 4, 5, 21, 22):
        return (21, 16)
    if op == 17:
        return (16, 11) if word >> 21 & 31 in (0, 4) else (16, 11, 6)
    if op == 0:
        shifts = {8: (21,), 0: (16, 11), 3: (16, 11), 16: (11,),
            27: (21, 16), 13: (), 33: (21, 16, 11), 35: (21, 16, 11), 37: (21, 16, 11)}
        if word & 63 in shifts:
            return shifts[word & 63]
    raise ValueError('Unknown emitter register encoding')


def allocate(word, registers):
    shifts = register_fields(word)
    if len(shifts) != len(registers) or any(not 0 <= r < 32 for r in registers):
        raise ValueError('Invalid emitter register plan')
    for shift, value in zip(shifts, registers):
        word = word & ~(31 << shift) | value << shift
    return word


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown emitter compiler words or bindings')
    words = list(struct.unpack('>266I', raw))
    retained = [i for i in ORDER if isinstance(i, int)]
    if sorted(retained) != [i for i in range(266) if i not in OMITTED] or len(ORDER) != WORDS:
        raise ValueError('Emitter plan lost or duplicated an operation')
    if [(i, op) for i, op in enumerate(ORDER) if isinstance(op, str)] != [
            (142, 'store-edge'), (151, 'load-edge'), (156, 'store-edge')]:
        raise ValueError('Unknown emitter private operation plan')
    positions = {old: new for new, old in enumerate(ORDER) if isinstance(old, int)}
    output, moved = [], {}
    for at, old in enumerate(ORDER):
        if isinstance(old, str):
            # Clone the compiled frame's SW/LW forms, not literal retail words.
            word = words[18 if old == 'store-edge' else 56]
            word = allocate(word & ~65535 | 0x18C, (29, 5))
        else:
            word = words[old]
            if old == 75:
                word = word & ~65535 | ((word & 65535) - 1)
            if word >> 21 & 31 == 29 and word >> 26 in (35, 43) and word & 65535 in (0x108, 0xE0):
                word = word & ~65535 | {0x108: 0x104, 0xE0: 0xF4}[word & 65535]
            if word >> 26 in (4, 5, 21, 22):
                target = old + 1 + ((words[old] & 65535) + 32768) % 65536 - 32768
                if target in OMITTED:
                    target = next(i for i in sorted(positions) if i > target)
                delta = positions[target] - at - 1
                if not -32768 <= delta <= 32767:
                    raise ValueError('Emitter branch exceeds signed reach')
                word = word & ~65535 | delta & 65535
            if at in REGISTERS:
                word = allocate(word, REGISTERS[at])
            if old * 4 in relocations:
                moved[at * 4] = list(relocations[old * 4])
        output.append(word)
    return struct.pack('>266I', *output), moved


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def link_target(root, out, label, raw, relocations, entry=ENTRY, bindings=None):
    bindings = BINDINGS if bindings is None else bindings
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), relocations, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound emitter symbols: ' + repr(missing))
    path = out / (label + '.s')
    path.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(path.with_suffix('.ld')), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(path.with_suffix('.elf')),
        str(path.with_suffix('.o'))], check=True, capture_output=True)
    return list(struct.unpack_from('>266I', sections(path.with_suffix('.elf'))['.text'][1]))


def guard_manifest(before, raw, relocations):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown emitter guard predecessor')
    normalized, moved = normalize(raw, relocations)
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    spec = lambda rows: ';'.join(kind + ':' + name for kind, name in rows) or '-'
    for i, (old, new) in enumerate(zip(struct.unpack('>266I', raw), struct.unpack('>266I', normalized))):
        a, b = relocations.get(i * 4, []), moved.get(i * 4, [])
        identity = old == new and a == b
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % old, replacement='0x%08X' % new,
            expected_relocations=spec(a), replacement_relocations=spec(b),
            note='Retain quad compiler fingerprint' if identity else
                'Normalize checked quad loop value graph, private homes and instruction schedule',
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def recovered_owner(before):
    return previous.previous.recovered_owner(before, SELECTED)


def qualify(root, out):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text()), 'qualified')
    if diagnostics:
        raise ValueError('Emitter compiler diagnostics: ' + diagnostics)
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    raw_words = link_target(root, out, 'proof-raw', raw, rel)
    words = link_target(root, out, 'proof-normalized', normalized, moved)
    result = prove(raw_words, words)
    truth = list(struct.unpack_from('>266I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Derived emitter stream is not retail exact')
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 1064 or list(struct.unpack_from('>266I', data, f['value'])) != words:
        raise ValueError('Emitter full-owner padding differs')
    row = dict(raw_words=266, raw_differences=sum(a != b for a, b in zip(raw_words, truth)),
        guarded_words=266, guarded_differences=0, frame=400, guards_added=266,
        identity_guards=guards[len((out / 'before-guards').read_bytes()):].count(b'Retain quad compiler fingerprint'),
        retained_operations=263, omitted_operations=list(OMITTED), materialized_private_operations=3,
        moved_relocations=moved, conditional_loop_proof=result, not_a_raw_C_match=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown emitter predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown emitter predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 1064)
    result[offset:offset + 1064] = rom[ROM:ROM + 1064]
    struct.pack_into('>I', result, row[0] + 8, 1064)
    return serialize_symbols(bytes(result))


def serialize_symbols(initial):
    """Account for two exact GNU-ld record/name cycles, not section exclusions.

    The original slot/extent-only prediction is archived and rejected. Two
    full relinks independently reproduce these cycles with every named
    definition and all code/data identical. Keep the initial fingerprint gate.
    """
    if hashlib.sha256(initial).hexdigest() != 'c76743afb954c3fcbf9b1537f84e2ec0c8f04be594c3cf22534194b26af250e4':
        raise ValueError('Unknown initial emitter image for symbol serialization')
    groups = [
        (('.L150A2614_game_data', 'D_80089B5C'), ('D_80089B5C', '.L150A2614_game_data')),
        (('D_800A6E84', 'D_800A2454', 'D_80090184'), ('D_800A2454', 'D_80090184', 'D_800A6E84')),
    ]
    definitions = {'.L150A2614_game_data': (0x150A2614, 0, 16, 0, 5),
        'D_80089B5C': (0x80089B5C, 0, 16, 0, 65521),
        'D_800A6E84': (0x800A6E84, 0, 16, 0, 65521),
        'D_800A2454': (0x800A2454, 0, 16, 0, 65521),
        'D_80090184': (0x80090184, 0, 16, 0, 6)}
    rows = {name: (at, fields, name_at) for at, name, fields, name_at in symbol_rows(initial) if name in definitions}
    if set(rows) != set(definitions):
        raise ValueError('Missing emitter serialization symbols')
    result = bytearray(initial)
    for original, ordered in groups:
        slots = [rows[name][0] for name in original]
        first_string = rows[original[0]][2]
        string_base = first_string - rows[original[0]][1][0]
        cursor = first_string
        for index, name in enumerate(original):
            at, fields, name_at = rows[name]
            encoded = name.encode() + b'\0'
            if at != slots[0] + index * SYMBOL.size or name_at != cursor or fields[1:] != definitions[name] or initial[cursor:cursor + len(encoded)] != encoded:
                raise ValueError('Changed emitter symbol record/name span')
            cursor += len(encoded)
        names = b''.join(name.encode() + b'\0' for name in ordered)
        if len(names) != cursor - first_string:
            raise ValueError('Emitter symbol names changed extent')
        result[first_string:cursor] = names
        cursor = first_string
        for at, name in zip(slots, ordered):
            SYMBOL.pack_into(result, at, cursor - string_base, *definitions[name])
            cursor += len(name) + 1
    if canonical_symbols(result) != canonical_symbols(initial) or sum(a != b for a, b in zip(result, initial)) != 64:
        raise ValueError('Emitter symbol cycles changed definitions or byte accounting')
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
