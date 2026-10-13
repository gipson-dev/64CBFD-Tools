"""Recover the complete three-mode matrix reflection and opacity routine."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15034F30, 0x623E0, 486
FUNCTION = 'func_15034F30'
QUALIFIED_NAME = 'layout-0-1-2'
SOURCE = 'conker/src/game/generated_61D10.c'
ORIGINAL = 's32 func_15034F30() {\n    return 0;\n}'
SYMBOLS = dict(guMtxIdentF=0x150A7BC0, guMtxL2F=0x151EFEB8,
    guMtxF2L2=0x151EFD00, bcopy=0x10023A10, func_150A7A48=0x150A7A48,
    func_150A8050=0x150A8050, func_150AD960=0x150AD960, func_15034728=0x15034728)
DECLARATIONS = '''void func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);
void func_150A8050(f32 [4][4], f32, f32, f32);
s32 func_150AD960(s32, s32, s32, s32);
void func_15034728(u8 *);
void guMtxF2L2(f32 [4][4], Mtx *);
'''
SELECTED = '''void func_15034F30(u8 *actor, u8 *record, s32 mode, u8 *input,
    u8 *output, s32 count, f32 pivotX, f32 pivotY, f32 pivotZ, f32 unused,
    f32 angle, f32 pointX, f32 pointY, f32 pointZ, f32 nearDistance,
    f32 farDistance, f32 opacity, s32 inputFixed, s32 outputFixed) {
    f32 reflection[4][4];
    f32 rotationMinus[4][4];
    f32 rotationPlus[4][4];
    f32 converted[4][4];
    f32 (*matrix)[4];
    f32 (*destination)[4];
    u8 *cursor;
    u8 *saved;
    s32 i;
    s32 offset;
    f32 distance;
    f32 value;

    guMtxIdentF(reflection);
    if (mode == 1 || mode == 0) {
        reflection[1][1] = -1.0f;
        cursor = output;
        offset = 0;
        for (i = 0; i < count; i++) {
            if (inputFixed != 0) {
                guMtxL2F(converted, (Mtx *)(input + i * 64));
                matrix = converted;
            } else {
                matrix = (f32 (*)[4])(input + offset);
                matrix[0][3] = 0.0f;
                matrix[1][3] = 0.0f;
                matrix[2][3] = 0.0f;
                matrix[3][3] = 1.0f;
            }
            destination = (f32 (*)[4])cursor;
            func_150A7A48(matrix, reflection, destination);
            value = matrix[3][1];
            destination[3][1] = value - ((value - pivotY) + (value - pivotY));
            if (outputFixed != 0) {
                matrix = (f32 (*)[4])(output + i * 64);
                bcopy(matrix, converted, 64);
                guMtxF2L2(converted, (Mtx *)matrix);
            }
            offset += 64;
            cursor += 64;
        }
        distance = pointY - pivotY;
        if (farDistance < distance) {
            record[4] = 0;
        } else if (distance < nearDistance) {
            if (mode == 0) {
                nearDistance = 10.0f;
                if (distance < nearDistance) {
                    record[4] = (u32)((opacity / nearDistance) * distance);
                } else {
                    record[4] = (u32)opacity;
                }
            } else {
                record[4] = (u32)opacity;
            }
        } else {
            record[4] = (u32)(opacity - ((opacity * (distance - nearDistance)) /
                (farDistance - nearDistance)));
        }
    } else if (mode == 2) {
        reflection[0][0] = -1.0f;
        func_150A8050(rotationMinus, 0.0f, -angle, 0.0f);
        func_150A8050(rotationPlus, 0.0f, angle, 0.0f);
        cursor = output;
        offset = 0;
        for (i = 0; i < count; i++) {
            if (inputFixed != 0) {
                guMtxL2F(converted, (Mtx *)(input + i * 64));
                matrix = converted;
            } else {
                matrix = (f32 (*)[4])(input + offset);
                matrix[0][3] = 0.0f;
                matrix[1][3] = 0.0f;
                matrix[2][3] = 0.0f;
                matrix[3][3] = 1.0f;
            }
            destination = (f32 (*)[4])cursor;
            bcopy(matrix, destination, 64);
            destination[3][0] -= pivotX;
            destination[3][1] -= pivotY;
            destination[3][2] -= pivotZ;
            func_150A7A48(destination, rotationMinus, destination);
            func_150A7A48(destination, reflection, destination);
            func_150A7A48(destination, rotationPlus, destination);
            destination[3][0] += pivotX;
            destination[3][1] += pivotY;
            destination[3][2] += pivotZ;
            if (outputFixed != 0) {
                matrix = (f32 (*)[4])(output + i * 64);
                bcopy(matrix, converted, 64);
                guMtxF2L2(converted, (Mtx *)matrix);
            }
            offset += 64;
            cursor += 64;
        }
        distance = (f32)func_150AD960((s32)pivotX, (s32)pivotZ,
            (s32)pointX, (s32)pointZ);
        if (farDistance < distance) {
            record[4] = 0;
        } else if (distance < nearDistance) {
            record[4] = (u32)opacity;
        } else {
            record[4] = (u32)(opacity - ((opacity * (distance - nearDistance)) /
                (farDistance - nearDistance)));
        }
    } else {
        return;
    }
    if (actor != 0 && *(u32 *)(actor + 0x9C) != 0) {
        saved = *(u8 **)(actor + 0x1D4);
        *(u8 **)(actor + 0x1D4) = output;
        func_15034728(actor);
        *(u8 **)(actor + 0x1D4) = saved;
    }
}'''


def recovered_owner(owner, body=None):
    if owner.count(ORIGINAL) != 1:
        raise ValueError('Expected the untouched matrix reflection placeholder')
    return owner.replace(ORIGINAL, qualified_body() if body is None else body).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\n\n' + DECLARATIONS, 1)


def compile_candidate(root, out, name, body=None):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, qualified_body() if body is None else body)


def candidates():
    yield 'selected', SELECTED
    for reverse, loop, inline in itertools.product((False, True), range(2), (False, True)):
        body = SELECTED
        if reverse:
            block = '    f32 reflection[4][4];\n    f32 rotationMinus[4][4];\n    f32 rotationPlus[4][4];\n    f32 converted[4][4];'
            body = body.replace(block, '\n'.join(reversed(block.splitlines())))
        if loop:
            body = body.replace('for (i = 0; i < count; i++) {', 'i = 0;\n        if (count > 0) {\n        do {')
            body = body.replace('            cursor += 64;\n        }',
                '            cursor += 64;\n            i++;\n        } while (i != count);\n        }')
        if inline:
            body = body.replace('            value = matrix[3][1];\n            destination[3][1] = value - ((value - pivotY) + (value - pivotY));',
                '            destination[3][1] = matrix[3][1] - 2.0f * (matrix[3][1] - pivotY);')
        yield 'order%d-loop%d-inline%d' % (reverse, loop, inline), body
    for count_home, output_home, actor_home in itertools.product((False, True), repeat=3):
        if not (count_home or output_home or actor_home):
            continue
        body = SELECTED
        if count_home:
            body = body.replace('s32 count,', 'volatile s32 count,')
        if output_home:
            body = body.replace('u8 *output,', 'u8 *volatile output,')
        if actor_home:
            body = body.replace('u8 *actor,', 'u8 *volatile actor,')
        yield 'homes-c%d-o%d-a%d' % (count_home, output_home, actor_home), body
    for actor_home, output_home in itertools.product((False, True), repeat=2):
        body = SELECTED.replace('s32 count,', 'volatile s32 count,')
        if actor_home:
            body = body.replace('u8 *actor,', 'u8 *volatile actor,')
        if output_home:
            body = body.replace('u8 *output,', 'u8 *volatile output,')
        body = body.replace('for (i = 0; i < count; i++) {', 'i = 0;\n        if (count > 0) {\n        do {')
        body = body.replace('            cursor += 64;\n        }',
            '            cursor += 64;\n            i++;\n        } while (i != count);\n        }')
        yield 'do-count-o%d-a%d' % (output_home, actor_home), body


def layout_candidates():
    base = dict(candidates())['do-count-o1-a0']
    declarations = ('    f32 (*matrix)[4];', '    f32 (*destination)[4];', '    u8 *cursor;',
        '    u8 *saved;', '    s32 i;', '    s32 offset;', '    f32 distance;', '    f32 value;')
    for indices in itertools.combinations(range(len(declarations)), 3):
        body = base
        moved = [declarations[i] for i in indices]
        for line in moved:
            assert body.count(line + '\n') == 1
            body = body.replace(line + '\n', '', 1)
        body = body.replace('    f32 converted[4][4];', '\n'.join(moved) + '\n    f32 converted[4][4];', 1)
        yield 'layout-' + '-'.join(map(str, indices)), body


def qualified_body():
    return dict(layout_candidates())[QUALIFIED_NAME]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--layouts', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-recovery'
    out.mkdir(exist_ok=True)
    records = []
    forms = layout_candidates() if args.layouts else candidates() if args.screens else [(QUALIFIED_NAME, qualified_body())]
    for name, body in forms:
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / ('layouts.json' if args.layouts else 'measurements.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
