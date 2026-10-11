"""Recover complete record matrix setup, decomposition and actor-relative direction."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503E3C4, 0x6B874, 141
FUNCTION, SOURCE = 'func_1503E3C4', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503E3C4() {\n    return 0;\n}'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800C6660=0x800C6660,
    D_80084454=0x80084454, bcopy=0x10023A10, func_150499A0=0x150499A0,
    func_150A7A48=0x150A7A48, func_1503E5F8=0x1503E5F8)
DECLARATIONS = '''#include "variables.h"
extern s8 *D_80084454[];
void func_150499A0(f32 [4][4], f32 [4][4]);
void func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);
void func_1503E5F8(f32 [4][4], f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *);
'''
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503E3C4(s32 slot, s32 index, s32 offset, f32 *record, s32 absolute) {
    f32 matrix[4][4];
    f32 inverse[4][4];
    struct127 *actor;
    s32 type;
    f32 x;
    f32 y;
    f32 z;
    f32 length;

    actor = &D_800CC2D0[slot];
    bcopy((f32 (*)[4][4])actor->unk1D4 + index + offset, matrix, sizeof(matrix));
    if (absolute != 0) {
        type = -1;
    } else {
        type = D_80084454[((u8 *)&D_800C6660[slot])[0xE]][index];
    }
    if (type != -1) {
        func_150499A0(((f32 (*)[4][4])actor->unk1D4)[type], inverse);
        matrix[1][3] = 0.0f;
        matrix[0][3] = 0.0f;
        matrix[2][3] = 0.0f;
        matrix[3][3] = 1.0f;
        func_150A7A48(matrix, inverse, matrix);
    }
    func_1503E5F8(matrix, &record[0], &record[1], &record[2],
        &record[3], &record[4], &record[5], &record[6], &record[7], &record[8]);
    record[9] = record[0];
    record[10] = record[1];
    record[11] = record[2];
    record[12] = record[3];
    record[13] = record[4];
    record[14] = record[5];
    record[15] = record[6];
    record[16] = record[7];
    record[17] = record[8];
    x = record[9] - actor->x_position;
    y = record[10] - actor->y_position - 30.0f;
    z = record[11] - actor->z_position;
    length = sqrtf(x*x + y*y + z*z);
    if (length == 0.0f) {
        length = 1.0f;
    }
    length = 1.0f / length;
    record[18] = x * length;
    record[19] = y * length;
    record[20] = z * length;
}'''
COMBINED = BASE.replace('actor->unk1D4 + index + offset', 'actor->unk1D4 + (index + offset)')
DIRECT = COMBINED.replace('    s32 type;\n', '').replace('    f32 matrix[4][4];',
    '    s32 type;\n    f32 matrix[4][4];')
SELECTED = DIRECT.replace('f32 *record,', 'struct04 *record,').replace('record[', '((f32 *)record)[')
PROTOTYPE = 's32 func_1503E3C4();'
RECOVERED_PROTOTYPE = 'void func_1503E3C4(s32, s32, s32, struct04 *, s32);'
LOCAL_DECLARATIONS = DECLARATIONS.split('void func_150499A0', 1)[1]
LOCAL_DECLARATIONS = 'void func_150499A0'+LOCAL_DECLARATIONS


def candidates():
    yield 'selected', SELECTED
    yield 'direct-float-interface', DIRECT
    yield 'register-record', BASE.replace('f32 *record,', 'register f32 *record,')
    yield 'register-actor', BASE.replace('    struct127 *actor;', '    register struct127 *actor;')
    combined = BASE.replace('actor->unk1D4 + index + offset', 'actor->unk1D4 + (index + offset)')
    yield 'combined-index', combined
    yield 'combined-register-type', combined.replace('    s32 type;', '    register s32 type;')
    yield 'combined-type-argument', combined.replace('    s32 type;\n', '').replace(
        'type =', 'absolute =').replace('type !=', 'absolute !=').replace('[type]', '[absolute]')
    yield 'combined-actor-initialized', combined.replace('    struct127 *actor;',
        '    struct127 *actor = &D_800CC2D0[slot];').replace('    actor = &D_800CC2D0[slot];\n', '')
    for local in ('s32 type;', 'struct127 *actor;', 'f32 x;', 'f32 y;', 'f32 z;', 'f32 length;'):
        yield 'home-first-'+local.split()[-1].replace(';', '').replace('*', ''), combined.replace(
            '    '+local+'\n', '').replace('    f32 matrix[4][4];', '    '+local+'\n    f32 matrix[4][4];')
    yield 'original-coordinates', BASE.replace('x = record[9]', 'x = record[0]').replace(
        'y = record[10]', 'y = record[1]').replace('z = record[11]', 'z = record[2]')
    yield 'matrix-order', BASE.replace('    f32 matrix[4][4];\n    f32 inverse[4][4];',
        '    f32 inverse[4][4];\n    f32 matrix[4][4];')
    yield 'scalar-order', BASE.replace('    s32 type;\n    f32 x;\n    f32 y;\n    f32 z;\n    f32 length;',
        '    f32 x;\n    f32 y;\n    f32 z;\n    f32 length;\n    s32 type;')
    yield 'split-length', BASE.replace('    f32 length;', '    f32 length;\n    f32 squared;\n    f32 reciprocal;').replace(
        'length = sqrtf(x*x + y*y + z*z);', 'squared = x*x + y*y + z*z;\n    length = sqrtf(squared);').replace(
        'length = 1.0f / length;', 'reciprocal = 1.0f / length;').replace('* length;', '* reciprocal;')
    yield 'vector-array', BASE.replace('    f32 x;\n    f32 y;\n    f32 z;', '    f32 delta[3];').replace(
        'x = record', 'delta[0] = record').replace('y = record', 'delta[1] = record').replace('z = record', 'delta[2] = record').replace(
        'x*x + y*y + z*z', 'delta[0]*delta[0] + delta[1]*delta[1] + delta[2]*delta[2]').replace(
        'x * length', 'delta[0] * length').replace('y * length', 'delta[1] * length').replace('z * length', 'delta[2] * length')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == source.count(PROTOTYPE) == 1
    assert SELECTED not in source and LOCAL_DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL, SELECTED).replace(PROTOTYPE,
        RECOVERED_PROTOTYPE+'\n'+LOCAL_DECLARATIONS.rstrip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-transform-setup'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta); print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
