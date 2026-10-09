"""Complete ten-point owner ribbon initializer recovery and IDO source fitting."""
import argparse
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B3A7C, 0x1E0F2C, 157
FUNCTION = 'func_151B3A7C'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B3A7C() {\n    return 0;\n}'
TYPES = 'typedef struct { f32 x, y, z; } OwnerRibbonPosition32C8;\n'
TYPES += 'typedef struct { OwnerRibbonPosition32C8 position, velocity; } OwnerPointRecord3A7C;\n'
DECLARATIONS = 'extern f32 D_800AA394, D_800AA398, D_800AA39C;\n'
SYMBOLS = dict(D_800AA394=0x800AA394, D_800AA398=0x800AA398, D_800AA39C=0x800AA39C)
BASE = '''s32 func_151B3A7C(u8 *actor) {
    f32 dx, dy, dz;
    OwnerRibbonPosition32C8 position;
    s32 i;

    dx = *(f32 *)(actor + 0x20) - *(f32 *)(actor + 0x14);
    dy = *(f32 *)(actor + 0x24) - *(f32 *)(actor + 0x18);
    dz = *(f32 *)(actor + 0x28) - *(f32 *)(actor + 0x1C);
    position = *(OwnerRibbonPosition32C8 *)(actor + 0x14);
    dx *= D_800AA394;
    dy *= D_800AA398;
    dz *= D_800AA39C;
    for (i = 0; i < 10; i++) {
        *(OwnerRibbonPosition32C8 *)(actor + 0x48 + i * 0x18) = position;
        *(f32 *)(actor + 0x54 + i * 0x18) =
            *(f32 *)(actor + 0x58 + i * 0x18) =
            *(f32 *)(actor + 0x5C + i * 0x18) = 0.0f;
        position.x += dx;
        position.y += dy;
        position.z += dz;
    }
    actor[0x10] &= ~2;
    return 1;
}'''


def candidates():
    yield 'initial', BASE
    typed = BASE.replace('    s32 i;', '    s32 i;\n    OwnerPointRecord3A7C *points;').replace(
        '    for (i = 0;', '    points = (OwnerPointRecord3A7C *)(actor + 0x48);\n    for (i = 0;').replace(
        '*(OwnerRibbonPosition32C8 *)(actor + 0x48 + i * 0x18)', 'points[i].position').replace(
        '*(f32 *)(actor + 0x54 + i * 0x18)', 'points[i].velocity.x').replace(
        '*(f32 *)(actor + 0x58 + i * 0x18)', 'points[i].velocity.y').replace(
        '*(f32 *)(actor + 0x5C + i * 0x18)', 'points[i].velocity.z')
    yield 'typed-records', typed
    vector = typed.replace('    f32 dx, dy, dz;', '    OwnerRibbonPosition32C8 delta, step;')
    for scalar, field in (('dx', 'x'), ('dy', 'y'), ('dz', 'z')):
        vector = vector.replace(scalar + ' =', 'delta.' + field + ' =').replace(
            scalar + ' *= D_', 'step.' + field + ' = delta.' + field + ' * D_').replace(
            '+= ' + scalar + ';', '+= step.' + field + ';')
    yield 'typed-vector-steps', vector
    yield 'typed-vector-position-first', vector.replace(
        '    OwnerRibbonPosition32C8 delta, step;\n    OwnerRibbonPosition32C8 position;',
        '    OwnerRibbonPosition32C8 position;\n    OwnerRibbonPosition32C8 delta, step;')
    setup, loop = vector.split('    for (i = 0; i < 10; i++) {\n', 1)
    work, tail = loop.split('    }\n', 1)
    unrolled = setup
    for index in (0, 1):
        unrolled += work.replace('points[i]', 'points[%d]' % index)
    unrolled += '    for (i = 2; i < 10; i += 4) {\n'
    for index in range(4):
        unrolled += work.replace('points[i]', 'points[i + %d]' % index)
    unrolled += '    }\n' + tail
    yield 'typed-vector-explicit-four', unrolled
    count = unrolled.replace('    s32 i;', '    s32 i, count;').replace(
        '    for (i = 2; i < 10;', '    count = 10;\n    for (i = 2; i < count;')
    yield 'typed-vector-explicit-four-count', count
    late = count.replace('    step.x = delta.x * D_800AA394;\n'
        '    step.y = delta.y * D_800AA398;\n    step.z = delta.z * D_800AA39C;\n', '').replace(
        '        position.x += step.x;',
        '        step.x = delta.x * D_800AA394;\n'
        '        step.y = delta.y * D_800AA398;\n'
        '        step.z = delta.z * D_800AA39C;\n        position.x += step.x;', 1)
    yield 'typed-vector-four-count-late', late
    for label, body in (('count', count), ('late', late)):
        separate = re.sub(r'        (points\[[^]]+\]\.velocity\.x) =\n'
            r'            (points\[[^]]+\]\.velocity\.y) =\n'
            r'            (points\[[^]]+\]\.velocity\.z) = 0\.0f;',
            r'        \1 = 0.0f;\n        \2 = 0.0f;\n        \3 = 0.0f;', body)
        yield 'typed-vector-four-' + label + '-separate', separate
        raw = separate.replace('    OwnerPointRecord3A7C *points;\n', '').replace(
            '    points = (OwnerPointRecord3A7C *)(actor + 0x48);\n', '')
        for field, offset in (('position', 0x48), ('velocity.x', 0x54), ('velocity.y', 0x58), ('velocity.z', 0x5C)):
            kind = 'OwnerRibbonPosition32C8' if field == 'position' else 'f32'
            raw = re.sub(r'points\[([^]]+)\]\.' + re.escape(field),
                lambda m: '*(%s *)(actor + 0x%X + (%s) * 0x18)' % (kind, offset, m[1]), raw)
        yield 'raw-vector-four-' + label + '-separate', raw
    yield 'typed-vector-explicit-four-count-not-equal', count.replace('i < count', 'i != count')
    yield 'typed-vector-explicit-four-late-scales', unrolled.replace(
        '    step.x = delta.x * D_800AA394;\n    step.y = delta.y * D_800AA398;\n'
        '    step.z = delta.z * D_800AA39C;\n', '').replace(
        '        position.x += step.x;',
        '        step.x = delta.x * D_800AA394;\n'
        '        step.y = delta.y * D_800AA398;\n'
        '        step.z = delta.z * D_800AA39C;\n        position.x += step.x;', 1)
    yield 'typed-do-while', typed.replace('    for (i = 0; i < 10; i++) {', '    i = 0;\n    do {').replace(
        '    }\n    actor[0x10]', '    } while (++i != 10);\n    actor[0x10]')
    yield 'typed-count-local', typed.replace('    s32 i;', '    s32 i, count;').replace(
        '    for (i = 0; i < 10;', '    count = 10;\n    for (i = 0; i < count;')
    yield 'typed-one-based', typed.replace('actor + 0x48);', 'actor + 0x30);').replace(
        'points[i]', 'points[i + 1]')
    yield 'typed-pointer-walk', typed.replace('points[i]', 'points->').replace('points->.', 'points->').replace(
        '        position.z += dz;', '        position.z += dz;\n        points++;')
    for label, body in (('raw', BASE), ('typed', typed)):
        distinct = body.replace('    f32 dx, dy, dz;', '    f32 dx, dy, dz;\n    f32 sx, sy, sz;').replace(
            '    dx *= D_800AA394;', '    sx = dx * D_800AA394;').replace(
            '    dy *= D_800AA398;', '    sy = dy * D_800AA398;').replace(
            '    dz *= D_800AA39C;', '    sz = dz * D_800AA39C;').replace(
            'position.x += dx;', 'position.x += sx;').replace(
            'position.y += dy;', 'position.y += sy;').replace('position.z += dz;', 'position.z += sz;')
        yield label + '-not-equal', body.replace('i < 10', 'i != 10')
        yield label + '-distinct-step', distinct
        yield label + '-distinct-not-equal', distinct.replace('i < 10', 'i != 10')
    yield 'typed-separated-zero', typed.replace('        points[i].velocity.x =\n'
        '            points[i].velocity.y =\n            points[i].velocity.z = 0.0f;',
        '        points[i].velocity.x = 0.0f;\n        points[i].velocity.y = 0.0f;\n'
        '        points[i].velocity.z = 0.0f;')
    yield 'typed-late-scales', typed.replace('    dx *= D_800AA394;\n'
        '    dy *= D_800AA398;\n    dz *= D_800AA39C;\n', '').replace(
        '        position.x += dx;\n        position.y += dy;\n        position.z += dz;',
        '        position.x += dx * D_800AA394;\n'
        '        position.y += dy * D_800AA398;\n        position.z += dz * D_800AA39C;')
    yield 'position-first', BASE.replace('    f32 dx, dy, dz;\n    OwnerRibbonPosition32C8 position;',
        '    OwnerRibbonPosition32C8 position;\n    f32 dx, dy, dz;')
    yield 'int-first', BASE.replace('    s32 i;\n', '').replace('    f32 dx', '    s32 i;\n    f32 dx')
    yield 'separate-zero', BASE.replace(
        '        *(f32 *)(actor + 0x54 + i * 0x18) =\n'
        '            *(f32 *)(actor + 0x58 + i * 0x18) =\n'
        '            *(f32 *)(actor + 0x5C + i * 0x18) = 0.0f;',
        '        *(f32 *)(actor + 0x54 + i * 0x18) = 0.0f;\n'
        '        *(f32 *)(actor + 0x58 + i * 0x18) = 0.0f;\n'
        '        *(f32 *)(actor + 0x5C + i * 0x18) = 0.0f;')
    yield 'late-scales', BASE.replace('    dx *= D_800AA394;\n'
        '    dy *= D_800AA398;\n    dz *= D_800AA39C;\n', '').replace(
        '        position.x += dx;\n        position.y += dy;\n        position.z += dz;',
        '        position.x += dx * D_800AA394;\n'
        '        position.y += dy * D_800AA398;\n        position.z += dz * D_800AA39C;')


RECOVERED_NAME = 'typed-vector-four-count-late'
RECOVERED = dict(candidates())[RECOVERED_NAME]


def compile_candidate(root, out, name, body=None, profile='o2g3', symbols=None, declarations=None):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=declarations or DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, RECOVERED if body is None else body, profile)
    prologue_adjustments = [word & 65535 for word in words[:8]
        if word >> 26 == 9 and word >> 21 & 31 == 29 and word >> 16 & 31 == 29
        and word & 0x8000]
    if len(prologue_adjustments) != 1:
        raise ValueError('expected one negative SP adjustment in the complete prologue')
    meta['frame'] = (-prologue_adjustments[0]) & 65535
    return meta, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-initializer'
    rows = []
    for name, body in (('const-scales', BASE), ('const-late-scales', dict(candidates())['late-scales'])):
        meta, _ = compile_candidate(root, out, name, body,
            declarations=DECLARATIONS.replace('extern f32', 'extern const f32'))
        rows.append(meta)
        print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles and name == RECOVERED_NAME else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
