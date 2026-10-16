"""Match the rectangle caller using a proven framed-value schedule normalization."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_quad_edge_wrapper as previous
from tools.experiments.game_quad_wrapper_proof import prove
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-quad-edge-wrapper-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS, CALLEE = (previous.OWNER, previous.FUNCTION,
    previous.ENTRY, previous.ROM, previous.WORDS, previous.CALLEE)
PATHS, BASELINE, build, freeze = previous.PATHS, previous.BASELINE, previous.build, previous.freeze
DECLARATIONS = 'void func_151700D8(f32 *, f32, f32, s32, f32, s32, s32, s32, u8, s32);\n\n'
SELECTED = previous.SELECTED.replace('/* Build a rectangle around signed actor coordinates and emit its perimeter. */',
    '/* Build a rectangle around signed actor coordinates and emit its perimeter.\n'
    ' * Guards normalize the compiler\'s private homes and FP/register schedule. */')
RAW_SHA256 = '48a0510230d4e54c5b616a777466e450a35ce08fcff6c8a953830239a8225d7e'
RELOCATIONS = {228: [('R_MIPS_26', 'func_151700D8')]}

# Every retained operation comes from this C object. Only register fields and
# placement change; the omitted incoming-actor spill/reload never escape in C.
PLAN = (
    (0, (29, 29)), (1, (29, 31)), (3, (29, 5)), (4, (29, 6)), (5, (29, 7)),
    (9, (4, 14)), (11, (4, 15)), (7, (29, 8)), (12, (14, 4)), (14, (15, 10)),
    (10, (4, 24)), (15, (0, 4, 6)), (19, (29, 25)), (21, (29, 8)), (22, (29, 9)),
    (24, (29, 10)), (25, (0, 10, 4)), (26, (29, 11)), (28, (29, 4)), (29, (29, 7)),
    (31, (29, 25)), (30, (8, 6, 14)), (13, (24, 8)), (16, (29, 6)), (32, (29, 8)),
    (20, (0, 8, 10)), (17, (29, 8)), (34, (5, 14)), (35, (29, 9)), (38, (29, 10)),
    (36, (6, 4, 12)), (8, (29, 4)), (18, (29, 6)), (58, (29, 11)), (33, (4, 10, 16)),
    (40, (29, 12)), (41, (29, 12)), (45, (14, 6, 18)), (37, (6, 16)), (46, (29, 12)),
    (39, (8, 16, 10)), (49, (29, 18)), (50, (29, 18)), (48, (6, 14, 2)), (43, (29, 10)),
    (44, (29, 4)), (42, (16, 8, 0)), (23, (29, 6)), (52, (29, 2)), (53, (29, 2)),
    (51, (29, 0)), (54, (29, 0)), (47, (29, 12)), (55, (29, 4)), (56, (29, 4)),
    (57, ()), (27, (29, 6)), (59, (29, 31)), (60, (29, 29)), (61, (31,)), (62, ()))


def register_fields(word):
    op = word >> 26
    if word == 0 or op == 3:
        return ()
    if op in (9, 33, 35, 36, 43, 49, 57):
        return (21, 16)
    if op == 17:
        return (16, 11) if word >> 21 & 31 in (0, 4) else (16, 11, 6)
    if op == 0 and word & 63 == 8:
        return (21,)
    raise ValueError('Unknown wrapper register layout')


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown wrapper compiler words or relocations')
    words, output, moved = struct.unpack('>63I', raw), [], {}
    if sorted(old for old, _ in PLAN) != [i for i in range(63) if i not in (2, 6)]:
        raise ValueError('Wrapper plan lost or duplicated an operation')
    for new, (old, fields) in enumerate(PLAN):
        word = words[old]
        shifts = register_fields(word)
        if len(shifts) != len(fields) or any(not 0 <= value < 32 for value in fields):
            raise ValueError('Malformed wrapper register allocation')
        for shift, value in zip(shifts, fields):
            word = word & ~(31 << shift) | value << shift
        output.append(word)
        if old * 4 in relocations:
            moved[new * 4] = list(relocations[old * 4])
    result = struct.pack('>61I', *output)
    prove(raw, relocations, result, moved)
    return result, moved


def guard_manifest(before, raw, relocations):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown wrapper guard predecessor')
    normalized, moved = normalize(raw, relocations)
    words, replacements = struct.unpack('>63I', raw), struct.unpack('>61I', normalized)
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    emitted = 0
    for index, expected in enumerate(words):
        omit = index in (2, 6)
        replacement = expected if omit else replacements[emitted]
        old, new = relocations.get(index * 4, []), [] if omit else moved.get(emitted * 4, [])
        if not omit:
            emitted += 1
        identity = not omit and expected == replacement and not old and not new
        spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec(old), replacement_relocations=spec(new),
            note='Retain rectangle compiler fingerprint' if identity else
                'Omit nonescaping incoming actor spill/reload' if omit else
                'Normalize proven rectangle value graph and call/register schedule',
            insert_after='', insert_after_relocations='', omit='true' if omit else 'false'))
    return before + output.getvalue().encode()


def recovered_owner(before):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151717FC() {\n    return 0;\n}':
        raise ValueError('Unknown rectangle-wrapper placeholder')
    marker = '/* Non-matching placeholders for the text-only asm slice asm/19E040.s. */'
    return (before[:lo] + SELECTED.rstrip() + before[hi:]).replace(marker, DECLARATIONS + marker, 1)


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: entries for at, entries in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def qualify(root, out):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-edge_wrapper_owner').read_text()), 'qualified')
    raw, rel = raw_target(obj)
    if diagnostics:
        raise ValueError('Wrapper compiler diagnostic: ' + diagnostics)
    normalized, moved = normalize(raw, rel)
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'], filename=OWNER, word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>61I', data, f['value']))
    truth = list(struct.unpack_from('>61I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != 244 or words != truth:
        raise ValueError('Normalized wrapper is not retail exact')
    raw_data, raw_functions = build.link_owner(root, out, obj, OWNER)
    raw_function = raw_functions[FUNCTION]
    raw_words = list(struct.unpack_from('>63I', raw_data, raw_function['value']))
    row = dict(raw_words=63, guarded_words=61, guarded_differences=0, raw_C_exact=False,
        guards_added=len(guards[len((out / 'before-guards').read_bytes()):].splitlines()),
        identity_guards=guards[len((out / 'before-guards').read_bytes()):].count(b'Retain rectangle compiler fingerprint'),
        moved_relocations=moved, proof=prove(raw, rel, normalized, moved))
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown wrapper predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown wrapper predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 244)
    result[offset:offset + 244] = rom[ROM:ROM + 244]
    struct.pack_into('>I', result, row[0] + 8, 244)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
