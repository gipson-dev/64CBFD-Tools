"""Recover the counted seven-input spray and its complete 31-word factory packet."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_random_drag as previous
from tools.tests import record_random_drag_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments import game_quad_edge_match as allocation
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

SCREEN_BUILD = 'conker/build/game-scaled-random-spray'
BUILD = 'conker/build/game-scaled-random-spray-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_151709B4', 0x151709B4, 0x19DE64, 119
DIRECTION, FACTORY = 0x15170034, 0x1516D4E8
PATHS = dict(previous.PATHS, spray_caller_original='conker/asm/197120.s',
    spray_float_caller_original='conker/asm/nonmatchings/game_EF410/func_150C3D5C.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    spray_caller_original='e40af17e5b36f34acbe50cbaeb36a09c68ac8fe7a523d38861e86a473b070a16',
    spray_float_caller_original='09bf5b6eafd3b93efbafdcaf88df2ff3592c8c54aa6bc32334a752ab54cd3938')
build = previous.build
SELECTED = '''/* Emit count records using a scaled direction and doubled vertical spread. */
void func_151709B4(s16 x, s16 y, s16 z, s32 count, f32 scale,
                  u8 flags, s32 context) {
    f32 directionX;
    f32 directionY;
    f32 directionZ;
    f32 velocityX;
    f32 velocityZ;
    f32 velocityY;
    s32 fixedX;
    s32 fixedZ;
    s32 index;

    index = 0;
    if (count > 0) {
        do {
            func_15170034(0x40, &directionX, &directionY, &directionZ);
            velocityX = directionX * scale;
            velocityY = directionY * (2.0f * scale);
            velocityZ = directionZ * scale;
            fixedX = (s32)velocityX;
            fixedZ = (s32)velocityZ;
            directionZ = velocityZ;
            directionY = velocityY;
            directionX = velocityX;
            func_1516D4E8(x, y, z, 0x2F, 0, 255, 255, 255, 0, 255, 0, 0, 7,
                fixedX >> 8, fixedX & 255, fixedZ >> 8, fixedZ & 255,
                0, 0, 0, 0, 0, 0, 0x200, 0x200, 40, (s32)velocityY, 0, 0,
                flags, context);
            index += 1;
        } while (index != count);
    }
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed scaled-spray predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed scaled-spray manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed scaled-spray fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151709B4() {\n    return 0;\n}':
        raise ValueError('Unknown scaled-spray placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='selected', body=None):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>119I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools = sections(obj)
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        frame=(0x10000 - (words[0] & 65535)) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        pool_bytes=sum(len(pools.get(name, (0, b''))[1]) for name in ('.rodata', '.data')),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screens(root, out):
    for name, body in (
            ('add-scale', INITIAL.replace('2.0f * scale', 'scale + scale')),
            ('typed-addressed-coordinates', INITIAL.replace('func_1516D4E8(x, y, z,',
                'func_1516D4E8((&x)[0], (&y)[0], (&z)[0],')),
            ('early-vertical-conversion', INITIAL.replace('    s32 fixedZ;', '    s32 fixedZ;\n    s32 fixedY;').replace(
                '            directionZ =', '            fixedY = (s32)velocityY;\n            directionZ =').replace(
                '40, (s32)velocityY,', '40, fixedY,')),
            ('in-place-outputs', INITIAL.replace('    f32 velocityX;\n    f32 velocityZ;\n    f32 velocityY;\n', '').replace(
                'velocityX', 'directionX').replace('velocityY', 'directionY').replace('velocityZ', 'directionZ').replace(
                '            directionZ = directionZ;\n            directionY = directionY;\n            directionX = directionX;\n', ''))):
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


def argument_screens(root, out):
    word = INITIAL.replace('s16 x, s16 y, s16 z', 's32 x, s32 y, s32 z')
    local = word.replace('    s32 index;', '    s32 index;\n    s16 positionX;\n    s16 positionY;\n    s16 positionZ;').replace(
        '    if (count > 0) {', '    if (count > 0) {\n        positionX = x;\n        positionY = y;\n        positionZ = z;').replace(
        'func_1516D4E8(x, y, z,', 'func_1516D4E8(positionX, positionY, positionZ,')
    for name, body in (
            ('word-coordinates', word),
            ('word-coordinates-explicit-casts', word.replace('func_1516D4E8(x, y, z,',
                'func_1516D4E8((s16)x, (s16)y, (s16)z,')),
            ('word-coordinates-narrow-locals', local),
            ('word-coordinates-word-locals', local.replace('s16 position', 's32 position').replace(
                'positionX = x;', 'positionX = (s16)x;').replace('positionY = y;', 'positionY = (s16)y;').replace(
                'positionZ = z;', 'positionZ = (s16)z;')),
            ('unsigned-halfword-coordinates', INITIAL.replace('s16 x, s16 y, s16 z', 'u16 x, u16 y, u16 z'))):
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


def layout_screens(root, out):
    word = INITIAL.replace('s16 x, s16 y, s16 z', 's32 x, s32 y, s32 z')
    lo, hi = word.index('    f32 directionX;'), word.index('\n\n    index = 0;')
    declarations = {line.split()[-1].rstrip(';'): line for line in word[lo:hi].splitlines()}
    orders = (
        ('index', 'directionX', 'directionY', 'directionZ', 'velocityX', 'velocityZ', 'velocityY', 'fixedX', 'fixedZ'),
        ('fixedX', 'fixedZ', 'index', 'directionX', 'directionY', 'directionZ', 'velocityX', 'velocityZ', 'velocityY'),
        ('directionX', 'directionY', 'directionZ', 'fixedX', 'fixedZ', 'index', 'velocityX', 'velocityZ', 'velocityY'),
        ('velocityX', 'velocityZ', 'velocityY', 'fixedX', 'fixedZ', 'index', 'directionX', 'directionY', 'directionZ'),
        ('fixedX', 'fixedZ', 'directionX', 'directionY', 'directionZ', 'velocityX', 'velocityZ', 'velocityY', 'index'))
    for number, order in enumerate(orders):
        body = word[:lo] + '\n'.join(declarations[name] for name in order) + word[hi:]
        for reverse in (False, True):
            candidate = body.replace('directionY * (2.0f * scale)', '(2.0f * scale) * directionY') if reverse else body
            _, _, row = measure(root, out, 'layout-%d-%d' % (number, reverse), candidate)
            print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


INITIAL = SELECTED
SELECTED = INITIAL.replace('s16 x, s16 y, s16 z', 's32 x, s32 y, s32 z').replace(
    '    f32 directionX;', '    s32 index;\n    f32 directionX;').replace('    s32 index;\n\n', '\n').replace(
    '/* Emit count records using a scaled direction and doubled vertical spread. */',
    '/* Emit count records using a scaled direction and doubled vertical spread.\n'
    ' * Guards normalize temporary scheduling and one finite multiply operand order. */')
RAW_SHA256 = '4b4cb351904ac7241612626c230982855308fa4b49f8d0e1d04b1c373e561b7a'
RELOCATIONS = {136: [('R_MIPS_26', 'func_15170034')], 396: [('R_MIPS_26', 'func_1516D4E8')]}
ORDER = (*range(36), 37, 36, 38, 42, 40, 43, 39, 47, 49, 45, 50, 52, 66, 44,
    46, 51, 80, 53, 54, 55, 56, 57, 58, 59, 62, 61, 41, 48, 63, 64, 65, 67,
    69, 68, 71, 70, 76, 75, 78, 77, 79, 81, 82, 83, 60, 72, 73, 74, *range(84, 118))
REGISTERS = {36: (29, 0), 37: (29, 2), 38: (29, 12), 39: (20, 0, 0),
    42: (22, 2, 2), 43: (6, 9), 44: (4, 25), 45: (20, 12, 12), 46: (0, 10),
    47: (0, 11), 48: (0, 12), 49: (0, 13), 50: (29, 13), 51: (0, 0, 4),
    52: (29, 12), 53: (29, 11), 54: (0, 12, 6), 55: (2, 4), 56: (29, 10),
    57: (0, 2, 8), 58: (3, 6), 59: (25, 0, 4), 60: (9, 0, 6), 61: (15, 8),
    63: (5, 8), 67: (0, 14), 68: (2, 25), 69: (2, 24), 74: (29, 24),
    75: (29, 25), 76: (29, 14), 80: (8, 0, 5)}


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def normalize(raw, rel):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or rel != RELOCATIONS:
        raise ValueError('Unknown scaled-spray compiler words or bindings')
    words = struct.unpack('>118I', raw)
    if sorted(ORDER) != list(range(118)):
        raise ValueError('Scaled-spray plan must retain every operation exactly once')
    output = [allocation.allocate(words[old], REGISTERS[at]) if at in REGISTERS else words[old]
        for at, old in enumerate(ORDER)]
    if {ORDER.index(at // 4) * 4: rows for at, rows in rel.items()} != rel:
        raise ValueError('Scaled-spray calls unexpectedly moved')
    return struct.pack('>118I', *output)


def link_target(out, name, raw, rel, entry=ENTRY, bindings=None):
    bindings = bindings or dict(func_15170034=DIRECTION, func_1516D4E8=FACTORY)
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), rel, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound spray symbols: ' + repr(missing))
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
        raise ValueError('Unknown spray guard predecessor')
    normalized = struct.unpack('>118I', normalize(raw, rel))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    for i, word in enumerate(struct.unpack('>118I', raw)):
        binding = ';'.join(kind + ':' + name for kind, name in rel.get(i * 4, [])) or '-'
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % word, replacement='0x%08X' % normalized[i],
            expected_relocations=binding, replacement_relocations=binding,
            note='Retain scaled-spray compiler fingerprint' if word == normalized[i] else
                'Normalize checked scaled-spray schedule, temporaries and finite multiply operands',
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    from tools.experiments.game_scaled_random_spray_proof import prove
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (118, 248, 48, '', 0):
        raise ValueError('Unknown scaled-spray compiler shape')
    raw, rel = raw_target(obj)
    normalized = normalize(raw, rel)
    words = link_target(out, 'normalized', normalized, rel)
    proof = prove(raw_words, words)
    truth = list(struct.unpack_from('>119I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words + [0] != truth:
        raise ValueError('Derived spray does not match the full retail body and padding')
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 472 or list(struct.unpack_from('>119I', data, f['value'])) != truth:
        raise ValueError('Scaled-spray production padding differs')
    row.update(guarded_body_words=118, retail_slot_words=119, padding_words=1,
        real_raw_differences=47, identity_guards=71, transforming_guards=47, proof=proof)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown spray predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown spray predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 476)
    result[at:at + 476] = rom[ROM:ROM + 476]
    struct.pack_into('>I', result, row[0] + 8, 472)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--argument-screen', action='store_true')
    parser.add_argument('--layout-screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
    elif args.layout_screen:
        layout_screens(root, root / BUILD)
    elif args.argument_screen:
        argument_screens(root, root / BUILD)
    elif args.screen:
        screens(root, root / BUILD)
    else:
        print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
