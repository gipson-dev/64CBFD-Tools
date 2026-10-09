"""Complete endpoint-link quad renderer recovery; installation requires byte matching."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B2974, 0x1DFE24, 340
FUNCTION = 'func_151B2974'
SOURCE = 'conker/src/game/generated_1DF510.c'
ORIGINAL = 's32 func_151B2974() {\n    return 0;\n}'
TYPES = 'typedef struct { f32 x, y, z; } OwnerQuadPosition2974;\n'
DECLARATIONS = '''extern u8 *D_800DBFF0;
extern u8 D_80090DE8[];
extern u32 D_800D2C9C, D_800A4AC8[];
void func_151D5D60(void *, s16, s32, Vtx **, u8 *);
void func_15143134(void *, void *, u8 *);
Gfx *func_15142B7C(Gfx *, u32, u32);
Gfx *func_15142E24(Gfx *, void *, s32, s32, s32, s32, s32, u8, u8 *, u8 *, s32);
Gfx *func_15142C10(Gfx *, s32, s32, s32, s32, u8 *);
Gfx *func_15142CF0(Gfx *, s32, s32, s32, s32, s32, s32, u8 *);
Gfx *func_1513F4E4(Gfx *, u8, u8 *);
Gfx *func_15142FBC(Gfx *, u32, u32, u8 *);
'''
SYMBOLS = dict(D_800DBFF0=0x800DBFF0, D_80090DE8=0x80090DE8,
    D_800D2C9C=0x800D2C9C, D_800A4AC8=0x800A4AC8,
    func_151D5D60=0x151D5D60, func_15143134=0x15143134,
    func_15142B7C=0x15142B7C, func_15142E24=0x15142E24,
    func_15142C10=0x15142C10, func_15142CF0=0x15142CF0,
    func_1513F4E4=0x1513F4E4, func_15142FBC=0x15142FBC)
GEOMETRY = '''        dx = second.x - first.x;
        dy = second.y - first.y;
        dz = second.z - first.z;
        rx = dx * 0.5f + first.x - origin->x;
        ry = dy * 0.5f + first.y - origin->y;
        rz = dz * 0.5f + first.z - origin->z;
        nx = dy * rz - ry * dz;
        ny = dz * rx - rz * dx;
        nz = dx * ry - rx * dy;
        squared = nx * nx + ny * ny + nz * nz;
        length = squared;
        if (squared == 0.0f) {
            ox = oy = oz = 0.0f;
        } else {
            length = sqrtf(length);
            scale = *(f32 *)(pair + 0x20) / length;
            ox = nx * scale;
            oy = ny * scale;
            oz = nz * scale;
        }
'''
VERTEX = '''        cursor->v.ob[0] = (s32)({point}.x {sign} ox);
        cursor->v.ob[1] = (s32)({point}.y {sign} oy);
        cursor->v.ob[2] = (s32)({point}.z {sign} oz);
        cursor->v.tc[0] = {s};
        cursor->v.tc[1] = {t};
        cursor++;
'''
BASE = '''Gfx *func_151B2974(Gfx *output, u8 *actor, s16 view) {
    Vtx *cursor;
    u8 sync;
    u8 invalid;
    OwnerQuadPosition2974 first, second;
    u8 *pair;
    u8 *matrix;
    OwnerQuadPosition2974 *origin;
    f32 dx, dy, dz, rx, ry, rz;
    f32 nx, ny, nz, squared, length, scale;
    f32 ox, oy, oz;

    invalid = 0;
    pair = actor + 0x28;
    if (**(s32 **)pair == 0 || pair[4] != (*(u8 **)pair)[0x3B]) {
        invalid = 1;
    }
    pair = actor + 0x28;
    if (!invalid && *(u8 **)(*(u8 **)pair + 0x1D4) != NULL) {
        func_151D5D60(actor + 0x14, view, 64, &cursor, NULL);
        if (cursor == NULL) {
            return output;
        }
        matrix = *(u8 **)(*(u8 **)pair + 0x1D4) + (pair[5] << 6);
        func_15143134(pair + 8, &first, matrix);
        func_15143134(pair + 0x14, &second, matrix);
        origin = (OwnerQuadPosition2974 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);
        sync = 1;
        output = func_15142B7C(output, 0x200005, 0x60600);
        output = func_15142E24(output, D_80090DE8, 0, 0, 0, 0, 54, 0, NULL, &sync, 3);
        output = func_15142C10(output, 255, 255, 255, 255, &sync);
        output = func_15142CF0(output, 0, 0, 255, 255, 255, 255, &sync);
        output = func_1513F4E4(output, 0x2B, &sync);
        output = func_15142FBC(output, D_800D2C9C | 0x80000 | 0x2CA0,
            D_800A4AC8[11] | D_800A4AC8[10], &sync);
''' + GEOMETRY + ''.join(VERTEX.format(point=p, sign=sign, s=s, t=t)
    for p, sign, s, t in (('second', '+', '0', '0'),
        ('second', '-', '0x3C0', '0'), ('first', '-', '0x3C0', '0x3C0'),
        ('first', '+', '0', '0x3C0'))) + '''        gSPVertex(output++, cursor - 4, 4, 0);
        gSP1Triangle(output++, 0, 1, 2, 0);
        gSP1Triangle(output++, 0, 2, 3, 0);
    }
    if (invalid) {
        *(s16 *)(actor + 0xE) = -1;
    }
    return output;
}'''


def frame_body(body):
    value=body.replace('nz, squared, length','nz, length').replace(
        'squared = nx * nx + ny * ny + nz * nz;\n        length = squared;',
        'length = nx * nx + ny * ny + nz * nz;').replace('if (squared ==','if (length ==')
    value=value.replace('    f32 ox, oy, oz;\n','')
    for before,after in (('ox','nx'),('oy','ny'),('oz','nz')):value=value.replace(before,after)
    return value


SELECTED=frame_body(BASE)
GEOMETRY=frame_body(GEOMETRY)


def candidates():
    yield 'selected', SELECTED
    yield 'initial-complete', BASE
    yield 'separate-zero', SELECTED.replace('nx = ny = nz = 0.0f;',
        'nx = 0.0f; ny = 0.0f; nz = 0.0f;')
    yield 'volatile-actor', SELECTED.replace('u8 *actor,', 'u8 *volatile actor,')
    yield 'volatile-view', SELECTED.replace('s16 view)', 'volatile s16 view)')
    yield 'separate-positions', SELECTED.replace('OwnerQuadPosition2974 first, second;',
        'OwnerQuadPosition2974 first;\n    OwnerQuadPosition2974 second;')
    yield 'reversed-positions', SELECTED.replace('OwnerQuadPosition2974 first, second;',
        'OwnerQuadPosition2974 second, first;')
    yield 'volatile-length', SELECTED.replace('f32 nx, ny, nz, length, scale;',
        'f32 nx, ny, nz, scale;\n    volatile f32 length;')
    yield 'reuse-scale', SELECTED.replace('length, scale','length').replace('scale =','dx =').replace('* scale','* dx')


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
    out = root/'conker/build/game-owner-endpoint-quad'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles and name == 'selected' else ('o2g3',):
            meta, words = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
