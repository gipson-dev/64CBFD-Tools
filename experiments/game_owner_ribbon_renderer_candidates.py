"""Complete actor-type0x33 nine-quad ribbon renderer recovery and IDO screens."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments import game_owner_endpoint_quad_candidates as quad

ENTRY, ROM, WORDS = 0x151B32C8, 0x1E0778, 475
FUNCTION = 'func_151B32C8'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B32C8() {\n    return 0;\n}'
TYPES = 'typedef struct { f32 x, y, z; } OwnerRibbonPosition32C8;\n'
DECLARATIONS = quad.DECLARATIONS.replace('void func_15143134(void *, void *, u8 *);\n', '') + '''extern s32 (*D_8008FB10[])(u8 *, s32 *, s32 *, s32 *, s32 *, s32 *,
    s32 *, s32 *, s32 *, s32 *, s32 *, s32 *, u8 *, u8 *);
'''
SYMBOLS = {n: a for n, a in quad.SYMBOLS.items() if n != 'func_15143134'}
SYMBOLS['D_8008FB10'] = 0x8008FB10
GEOMETRY = '''    rx = {point}.x - origin->x;
    ry = {point}.y - origin->y;
    rz = {point}.z - origin->z;
    dx = second.x - first.x;
    dy = second.y - first.y;
    dz = second.z - first.z;
    nx = dy * rz - ry * dz;
    ny = dz * rx - rz * dx;
    nz = dx * ry - rx * dy;
    length = nx * nx + ny * ny + nz * nz;
    if (length == 0.0f) {{
        nx = ny = nz = 0.0f;
    }} else {{
        length = sqrtf(length);
        scale = *(f32 *)(actor + 0x30) / length;
        nx *= scale;
        ny *= scale;
        nz *= scale;
    }}
'''
VERTEX = '''    cursor->v.ob[0] = (s32)({point}.x {sign} nx);
    cursor->v.ob[1] = (s32)({point}.y {sign} ny);
    cursor->v.ob[2] = (s32)({point}.z {sign} nz);
    cursor->v.tc[0] = {s};
    cursor->v.tc[1] = {t};
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 100;
    cursor->v.cn[2] = 100;
    cursor->v.cn[3] = 255;
    cursor++;
'''
PREFIX = '''Gfx *func_151B32C8(Gfx *output, u8 *actor, s16 view) {
    Vtx *cursor;
    OwnerRibbonPosition32C8 first, second;
    OwnerRibbonPosition32C8 *origin;
    f32 dx, dy, dz, rx, ry, rz, nx, ny, nz, length, scale;
    s32 mode1, mode2, envR, envG, envB, alpha, primR, primG, primB, primA, renderMode;
    u8 bank, combine, sync;
    s32 offset;
    u32 textureT;

    if (actor[0x10] & 4) {
        return output;
    }
    if (actor[0x10] & 8) {
        return output;
    }
    if (actor[0x10] & 2) {
        return output;
    }
    func_151D5D60(actor + 0x140, view, 0x190, &cursor, NULL);
    if (cursor == NULL) {
        return output;
    }
    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);
    sync = 1;
    if (!D_8008FB10[actor[0x2E]](actor, &mode1, &mode2, &envR, &envG, &envB,
            &alpha, &primR, &primG, &primB, &primA, &renderMode, &bank, &combine)) {
        return output;
    }
    output = func_15142B7C(output, mode1, mode2);
    output = func_15142C10(output, primR, primG, primB, primA, &sync);
    output = func_15142CF0(output, 0, 0, envR, envG, envB, alpha, &sync);
    output = func_1513F4E4(output, combine, &sync);
    output = func_15142E24(output, D_80090DE8, 0, 0, 0, 0, 54, 0, NULL, &sync, 3);
    output = func_15142FBC(output, renderMode | 0x80000 | D_800D2C9C | 0x2CA0,
        D_800A4AC8[bank * 2 + 1] | D_800A4AC8[bank * 2], &sync);
    first = *(OwnerRibbonPosition32C8 *)(actor + 0x48);
    second = *(OwnerRibbonPosition32C8 *)(actor + 0x60);
'''
SELECTED = PREFIX + GEOMETRY.format(point='first') + ''.join(VERTEX.format(
    point='first', sign=sign, s=s, t='0') for sign, s in (('+', '0'), ('-', '0x3C0'))) + '''    textureT = *(s32 *)(actor + 0x13C);
    for (offset = 0x18; offset != 0xF0; offset += 0x18) {
        first = *(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset - 0x18);
        second = *(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);
''' + '\n'.join('    ' + line if line else '' for line in GEOMETRY.format(point='second').split('\n')) + ''.join(
    '\n'.join('    ' + line if line else '' for line in VERTEX.format(
        point='second', sign=sign, s=s, t='textureT').split('\n'))
    for sign, s in (('+', '0'), ('-', '0x3C0'))) + '''
        textureT += *(s32 *)(actor + 0x13C);
        gSPVertex(output++, cursor - 4, 4, 0);
        gSP1Triangle(output++, 0, 1, 2, 0);
        gSP1Triangle(output++, 1, 3, 2, 0);
    }
    return output;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'separate-zero', SELECTED.replace('nx = ny = nz = 0.0f;',
        'nx = 0.0f; ny = 0.0f; nz = 0.0f;')
    yield 'separate-points', SELECTED.replace('first, second;', 'first;\n    OwnerRibbonPosition32C8 second;')
    yield 'volatile-cursor', SELECTED.replace('Vtx *cursor;', 'Vtx *volatile cursor;').replace(
        '&cursor, NULL', '(Vtx **)&cursor, NULL')
    yield 'signed-texture', SELECTED.replace('u32 textureT;', 's32 textureT;')
    yield 'loop-less', SELECTED.replace('offset != 0xF0', 'offset < 0xF0')
    yield 'pointer-loop', SELECTED.replace('s32 offset;', 'u8 *point;').replace(
        'for (offset = 0x18; offset != 0xF0; offset += 0x18)',
        'for (point = actor + 0x60; point != actor + 0x138; point += 0x18)').replace(
        'actor + 0x48 + offset - 0x18', 'point - 0x18').replace('actor + 0x48 + offset', 'point')
    expanded = SELECTED.replace('nz, length, scale;', 'nz, squared, length, scale;\n    f32 ox, oy, oz;').replace(
        'length = nx * nx + ny * ny + nz * nz;', 'squared = nx * nx + ny * ny + nz * nz;\n    length = squared;').replace(
        'if (length == 0.0f)', 'if (squared == 0.0f)').replace('nx = ny = nz = 0.0f;',
        'ox = oy = oz = 0.0f;').replace('nx *= scale;', 'ox = nx * scale;').replace(
        'ny *= scale;', 'oy = ny * scale;').replace('nz *= scale;', 'oz = nz * scale;')
    for normal, scaled in (('nx', 'ox'), ('ny', 'oy'), ('nz', 'oz')):
        for sign in ('+', '-'):
            expanded = expanded.replace(' ' + sign + ' ' + normal + ')', ' ' + sign + ' ' + scaled + ')')
    yield 'separate-normal-and-offset', expanded


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-ribbon-renderer'
    rows = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles and name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
