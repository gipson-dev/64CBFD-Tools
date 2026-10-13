"""Recover the live-mask backwards 3x3 bone-matrix clear."""
import argparse
import csv
import io
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_type_dispatch_candidates import compile_owner

ENTRY, ROM, WORDS = 0x15034728, 0x61BD8, 48
FUNCTION, SOURCE = 'func_15034728', 'conker/src/game/generated_61490.c'
DECLARATIONS = 's32 func_1502DB20(s32 type);\n'
SYMBOLS = {'func_1502DB20': 0x1502DB20}
ORIGINAL = 's32 func_15034728() {\n    return 0;\n}'
GUARD_INPUTS = ((0x38, 0x8E0901D4), (0x40, 0x2408001F), (0x44, 0x00604025),
    (0x48, 0x05000018), (0x4C, 0x24070003), (0x60, 0x01195004),
    (0x64, 0x030A5824), (0x68, 0x1160000D), (0x70, 0x00086180),
    (0x74, 0x01893021), (0x78, 0x00056900), (0x7C, 0x01A61821),
    (0x84, 0x00627021), (0x90, 0xE5C00000), (0x98, 0x54A7FFF8),
    (0x9C, 0x00056900), (0xA0, 0x2508FFFF), (0xA4, 0x0503FFED))
MATRIX_INDEX = '''void func_15034728(u8 *actor) {
    s32 bone;
    s32 row;
    s32 column;
    f32 (*matrices)[4][4];

    if (*(u32 *)(actor + 0x1D4) == 0 || *(u32 *)(actor + 0x9C) == 0) {
        return;
    }
    bone = (s32)((u32)func_1502DB20(actor[4]) - 1);
    matrices = *(f32 (**)[4][4])(actor + 0x1D4);
    bone = bone < 31 ? bone : 31;
    for (; bone >= 0; bone--) {
        if (*(u32 *)(actor + 0x9C) & (1U << bone)) {
            for (row = 0; row < 3; row++) {
                for (column = 0; column < 3; column++) {
                    matrices[bone][row][column] = 0.0f;
                }
            }
        }
    }
}'''
def renamed_word(word, offset):
    if offset < 0x30:
        return word
    # The post-helper A2..T7 cycle leaves immediates and COP1 fields untouched.
    op, fn = word >> 26, word & 63
    if op == 0:
        assert fn in (0, 4, 8, 33, 36, 37)
        fields = (21, 16, 11)
    elif op in (4, 5, 9, 10, 20, 21, 35):
        fields = (21, 16)
    elif op in (1, 57):
        fields = (21,)
    elif op == 17:
        assert word == 0x44800000
        fields = ()
    else:
        raise ValueError('Unexpected post-helper instruction 0x%08X' % word)
    for shift in fields:
        register = word >> shift & 31
        if 6 <= register <= 15:
            replacement = register + 1 if register < 15 else 6
            word = (word & ~(31 << shift)) | (replacement << shift)
    if offset == 0x7C:
        assert op == 0 and fn == 33
        first, second = word >> 21 & 31, word >> 16 & 31
        word = (word & ~0x03FF0000) | (second << 21) | (first << 16)
    return word


def normalize(words):
    assert len(words) == WORDS
    for offset, expected in GUARD_INPUTS:
        assert words[offset // 4] == expected, ('stale matrix-clear allocation', offset)
    result = [renamed_word(word, i * 4) for i, word in enumerate(words)]
    assert {i*4 for i,(a,b) in enumerate(zip(words,result)) if a!=b} == {o for o,_ in GUARD_INPUTS}
    return result


def owner_guards():
    return [dict(filename='generated_61490', function=FUNCTION, offset='0x%X' % offset,
        expected='0x%08X' % word, replacement='0x%08X' % renamed_word(word, offset),
        expected_relocations='-', replacement_relocations='-',
        note='Normalize matrix clear closed post-helper GPR cycle and commutative row-base addition',
        insert_after='', insert_after_relocations='', omit='false') for offset, word in GUARD_INPUTS]


def guard_bytes(before):
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('matrix-clear guards already installed')
    tail = io.StringIO()
    writer = csv.DictWriter(tail, fieldnames=reader.fieldnames, lineterminator='\n')
    writer.writerows(owner_guards())
    return before + tail.getvalue().encode()


BYTE_OFFSETS = '''void func_15034728(u8 *actor) {
    s32 last;
    s32 bone;
    s32 row;
    s32 offset;
    u8 *buffer;

    if (*(u32 *)(actor + 0x1D4) == 0 || *(u32 *)(actor + 0x9C) == 0) {
        return;
    }
    last = (s32)((u32)func_1502DB20(actor[4]) - 1);
    buffer = *(u8 **)(actor + 0x1D4);
    for (bone = last < 31 ? last : 31; bone >= 0; bone--) {
        if (*(u32 *)(actor + 0x9C) & (1U << bone)) {
            u8 *matrix = buffer + bone * 64;
            for (row = 0; row < 3; row++) {
                u8 *vector = matrix + row * 16;
                for (offset = 0; offset < 12; offset += 4) {
                    *(f32 *)(vector + offset) = 0.0f;
                }
            }
        }
    }
}'''


SELECTED = BYTE_OFFSETS.replace('u8 *buffer;', 'u32 buffer;').replace('*(u8 **)', '*(u32 *)').replace(
    'u8 *matrix =', 'u32 matrix =').replace('u8 *vector =', 'u32 vector =').replace(
    '    for (bone = last < 31 ? last : 31; bone >= 0; bone--) {',
    '    bone = 31;\n    if (last < 31) {\n        bone = last;\n    }\n    for (; bone >= 0; bone--) {').replace('row * 16', '(row << 4)')


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known matrix-clear placeholder or complete body')
    if DECLARATIONS not in source:
        source = source.replace('extern u8 D_800CC2D4[];', DECLARATIONS + '\nextern u8 D_800CC2D4[];', 1)
    return source


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    profiles = dict(compiler.PROFILES, no_unroll=('-O2', '-g3', '-Wo,-loopunroll,0'))
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=profiles):
        return compiler.compile_candidate(root, out, name, body, profile)


def candidates():
    yield 'selected', SELECTED
    yield 'matrix-index', MATRIX_INDEX
    yield 'byte-offsets', BYTE_OFFSETS
    yield 'byte-equality', BYTE_OFFSETS.replace('row < 3', 'row != 3').replace('offset < 12', 'offset != 12')
    yield 'byte-clamp-if', BYTE_OFFSETS.replace('    for (bone = last < 31 ? last : 31; bone >= 0; bone--) {',
        '    bone = 31;\n    if (last < 31) {\n        bone = last;\n    }\n    for (; bone >= 0; bone--) {')
    yield 'matrix-byte-column', MATRIX_INDEX.replace('column < 3; column++', 'column < 12; column += 4').replace(
        'matrices[bone][row][column] = 0.0f;', '*(f32 *)((u8 *)matrices[bone][row] + column) = 0.0f;')
    yield 'matrix-equality-byte-column', MATRIX_INDEX.replace('row < 3', 'row != 3').replace(
        'column < 3; column++', 'column != 12; column += 4').replace(
        'matrices[bone][row][column] = 0.0f;', '*(f32 *)((u8 *)matrices[bone][row] + column) = 0.0f;')
    yield 'byte-unsigned-offset', BYTE_OFFSETS.replace('    s32 offset;', '    u32 offset;')
    yield 'byte-unsigned-row', BYTE_OFFSETS.replace('    s32 row;', '    u32 row;')
    flat = MATRIX_INDEX.replace('(*matrices)[4][4]', '(*matrices)[16]').replace('(**)[4][4]', '(**)[16]').replace(
        'matrices[bone][row][column]', 'matrices[bone][row * 4 + column]')
    yield 'flat-floats', flat
    yield 'flat-equality', flat.replace('row < 3', 'row != 3').replace('column < 3', 'column != 3')
    yield 'flat-split-clamp', flat.replace('    s32 bone;', '    s32 last;\n    s32 bone;').replace(
        '    bone = (s32)', '    last = (s32)').replace('bone = bone < 31 ? bone : 31;', 'bone = last < 31 ? last : 31;')
    yield 'direct-byte-address', BYTE_OFFSETS.replace('            u8 *matrix = buffer + bone * 64;\n', '').replace(
        '                u8 *vector = matrix + row * 16;\n', '').replace(
        '*(f32 *)(vector + offset)', '*(f32 *)(buffer + bone * 64 + row * 16 + offset)')
    yield 'flat-vector-base', flat.replace('            for (row =', '            f32 *matrix = matrices[bone];\n            for (row =').replace(
        'matrices[bone][row * 4 + column]', 'matrix[row * 4 + column]')
    yield 'byte-do-loops', BYTE_OFFSETS.replace('            for (row = 0; row < 3; row++) {',
        '            row = 0;\n            do {').replace('                for (offset = 0; offset < 12; offset += 4) {',
        '                offset = 0;\n                do {').replace(
        '                    *(f32 *)(vector + offset) = 0.0f;\n                }\n            }',
        '                    *(f32 *)(vector + offset) = 0.0f;\n                    offset += 4;\n                } while (offset != 12);\n                row++;\n            } while (row != 3);')
    yield 'matrix-do-loops', MATRIX_INDEX.replace('            for (row = 0; row < 3; row++) {',
        '            row = 0;\n            do {').replace('                for (column = 0; column < 3; column++) {',
        '                column = 0;\n                do {').replace(
        '                    matrices[bone][row][column] = 0.0f;\n                }\n            }',
        '                    matrices[bone][row][column] = 0.0f;\n                    column++;\n                } while (column != 3);\n                row++;\n            } while (row != 3);')
    integer = BYTE_OFFSETS.replace('u8 *buffer;', 'u32 buffer;').replace('*(u8 **)', '*(u32 *)').replace(
        'u8 *matrix =', 'u32 matrix =').replace('u8 *vector =', 'u32 vector =')
    yield 'integer-addresses', integer
    yield 'integer-if-clamp', integer.replace('    for (bone = last < 31 ? last : 31; bone >= 0; bone--) {',
        '    bone = 31;\n    if (last < 31) {\n        bone = last;\n    }\n    for (; bone >= 0; bone--) {')
    yield 'integer-direct-address', integer.replace('            u32 matrix = buffer + bone * 64;\n', '').replace(
        '                u32 vector = matrix + row * 16;\n', '').replace(
        '*(f32 *)(vector + offset)', '*(f32 *)(buffer + bone * 64 + row * 16 + offset)')
    shaped = integer.replace('    for (bone = last < 31 ? last : 31; bone >= 0; bone--) {',
        '    bone = 31;\n    if (last < 31) {\n        bone = last;\n    }\n    for (; bone >= 0; bone--) {').replace('row * 16', '(row << 4)')
    yield 'shifts', shaped
    yield 'shifts-u32-loops', shaped.replace('    s32 row;', '    u32 row;').replace('    s32 offset;', '    u32 offset;')
    declarations = '    s32 last;\n    s32 bone;\n    s32 row;\n    s32 offset;\n    u32 buffer;'
    yield 'shifts-buffer-first', shaped.replace(declarations,
        '    u32 buffer;\n    s32 bone;\n    s32 row;\n    s32 offset;\n    s32 last;')
    yield 'shifts-loops-first', shaped.replace(declarations,
        '    s32 row;\n    s32 offset;\n    s32 bone;\n    u32 buffer;\n    s32 last;')
    yield 'shifts-pointer-buffer', shaped.replace('u32 buffer;', 'u8 *buffer;').replace('*(u32 *)(actor + 0x1D4);',
        '*(u8 **)(actor + 0x1D4);').replace('u32 matrix = buffer', 'u32 matrix = (u32)buffer')
    yield 'shifts-pointer-matrix', shaped.replace('u32 matrix = buffer + bone * 64;',
        'u8 *matrix = (u8 *)(buffer + bone * 64);').replace('u32 vector = matrix', 'u32 vector = (u32)matrix')
    yield 'shifts-explicit-limits', shaped.replace('    u32 buffer;', '    u32 buffer;\n    s32 rows;\n    s32 columns;').replace(
        '    for (; bone >= 0;', '    rows = 3;\n    columns = 12;\n    for (; bone >= 0;').replace('row < 3', 'row < rows').replace('offset < 12', 'offset < columns')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-matrix-clear'
    for name, body in candidates() if args.controls else [('selected', SELECTED)]:
        for profile in ('o2g3', 'no_unroll') if args.profiles else ('o2g3',):
            meta, words = compile_candidate(root, out, name + '-' + profile, body, profile)
            print(name, profile, meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'], flush=True)
            if name == 'selected' and profile == 'o2g3':
                fitted = normalize(words)
                retail = struct.unpack_from('>48I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
                assert fitted == list(retail)
                print(json.dumps([(i*4, '0x%08X' % a, '0x%08X' % b) for i,(a,b) in enumerate(zip(words,fitted)) if a!=b]))


if __name__ == '__main__':
    main()
