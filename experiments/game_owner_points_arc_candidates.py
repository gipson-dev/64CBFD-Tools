"""Complete owner ten-point arc preparation and bounded IDO source fitting."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_owner_points_initializer_fitting import TYPES

ENTRY, ROM, WORDS = 0x151B3CF0, 0x1E11A0, 142
FUNCTION = 'func_151B3CF0'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B3CF0() {\n    return 0;\n}'
DECLARATIONS = '''extern f32 D_800AA3A0, D_800AA3A4, D_800AA3A8;
f32 func_150484A0(f32, f32);
f32 sinf(f32), cosf(f32), sqrtf(f32), fabsf(f32);
#pragma intrinsic (fabsf)
'''
SYMBOLS = dict(D_800AA3A0=0x800AA3A0, D_800AA3A4=0x800AA3A4,
    D_800AA3A8=0x800AA3A8, func_150484A0=0x150484A0, sinf=0x15047D60, cosf=0x15047C00)
SELECTED = '''s32 func_151B3CF0(u8 *actor) {
    OwnerRibbonPosition32C8 midpoint, first, last;
    f32 x0, y0, z0, x1, y1, z1;
    f32 dx, dy, dz;
    f32 inverse, nx, nz;
    f32 projection, vertical, angle, radius, angleStep;
    f32 sine, cosine, along;
    s32 offset;
    OwnerRibbonPosition32C8 *point;

    x0 = *(f32 *)(actor + 0x14);
    y0 = *(f32 *)(actor + 0x18);
    z0 = *(f32 *)(actor + 0x1C);
    x1 = *(f32 *)(actor + 0x20);
    y1 = *(f32 *)(actor + 0x24);
    z1 = *(f32 *)(actor + 0x28);
    dx = x1 - x0;
    dy = y1 - y0;
    dz = z1 - z0;
    if (D_800AA3A0 < fabsf(dx) || D_800AA3A0 < fabsf(dz)) {
        midpoint.x = x0 + dx * 0.5f;
        midpoint.y = y0 + dy * 0.5f;
        midpoint.z = z0 + dz * 0.5f;
        first.x = x0 - midpoint.x;
        first.y = y0 - midpoint.y;
        first.z = z0 - midpoint.z;
        last.x = x1 - midpoint.x;
        last.y = y1 - midpoint.y;
        last.z = z1 - midpoint.z;
        inverse = 1.0f / sqrtf(dx * dx + dz * dz);
        nz = dz * inverse;
        nx = dx * inverse;
        projection = (last.z * nz + last.x * nx) - (first.z * nz + first.x * nx);
        vertical = last.y - first.y;
        angle = func_150484A0(vertical, projection);
        radius = sqrtf(projection * projection + vertical * vertical) * 0.5f;
        angle -= D_800AA3A4;
        angleStep = D_800AA3A8;
        for (offset = 0; offset != 0xF0; offset += 0x18) {
            point = (OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);
            sine = sinf(angle);
            cosine = cosf(angle);
            along = radius * cosine;
            point->x = along * nx + midpoint.x;
            point->y = radius * sine + midpoint.y;
            point->z = along * nz + midpoint.z;
            angle += angleStep;
        }
    }
    return 1;
}'''

COMPACT = '''s32 func_151B3CF0(u8 *actor) {
    OwnerRibbonPosition32C8 midpoint, first, last;
    f32 dx, dy, dz;
    f32 inverse, nx, nz;
    f32 projection, vertical, angle, radius, angleStep;
    f32 sine, along;
    s32 offset;
    OwnerRibbonPosition32C8 *point;

    dx = *(f32 *)(actor + 0x20) - *(f32 *)(actor + 0x14);
    dy = *(f32 *)(actor + 0x24) - *(f32 *)(actor + 0x18);
    dz = *(f32 *)(actor + 0x28) - *(f32 *)(actor + 0x1C);
    if (D_800AA3A0 < fabsf(dx) || D_800AA3A0 < fabsf(dz)) {
        midpoint.x = *(f32 *)(actor + 0x14) + dx * 0.5f;
        midpoint.y = *(f32 *)(actor + 0x18) + dy * 0.5f;
        midpoint.z = *(f32 *)(actor + 0x1C) + dz * 0.5f;
        first.x = *(f32 *)(actor + 0x14) - midpoint.x;
        first.y = *(f32 *)(actor + 0x18) - midpoint.y;
        first.z = *(f32 *)(actor + 0x1C) - midpoint.z;
        last.x = *(f32 *)(actor + 0x20) - midpoint.x;
        last.y = *(f32 *)(actor + 0x24) - midpoint.y;
        last.z = *(f32 *)(actor + 0x28) - midpoint.z;
        inverse = 1.0f / sqrtf(dx * dx + dz * dz);
        nz = dz * inverse;
        nx = dx * inverse;
        projection = (last.z * nz + last.x * nx) - (first.z * nz + first.x * nx);
        vertical = last.y - first.y;
        angle = func_150484A0(vertical, projection);
        radius = sqrtf(projection * projection + vertical * vertical) * 0.5f;
        angle -= D_800AA3A4;
        angleStep = D_800AA3A8;
        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);
        for (offset = 0; offset != 0xF0; offset += 0x18) {
            sine = sinf(angle);
            along = radius * cosf(angle);
            point->x = along * nx + midpoint.x;
            point->y = radius * sine + midpoint.y;
            point->z = along * nz + midpoint.z;
            angle += angleStep;
            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);
        }
    }
    return 1;
}'''


def candidates():
    typed = COMPACT.replace('s32 func_151B3CF0(u8 *actor) {',
        's32 func_151B3CF0(u8 *actor) {\n    OwnerPoints3A7C *owner = (OwnerPoints3A7C *)actor;')
    for field, offset in (('x', 0x14), ('y', 0x18), ('z', 0x1C)):
        typed = typed.replace('*(f32 *)(actor + 0x%X)' % offset, 'owner->start.' + field).replace(
            '*(f32 *)(actor + 0x%X)' % (offset + 12), 'owner->end.' + field)
    yield 'typed-owner', typed
    reduced = typed.replace('    f32 inverse, nx, nz;', '    f32 inverse;').replace('nz = dz * inverse;',
        'dz *= inverse;').replace('nx = dx * inverse;', 'dx *= inverse;').replace(' * nx', ' * dx').replace(' * nz', ' * dz')
    yield 'typed-reused-normal', reduced
    yield 'typed-vector-delta', typed.replace('midpoint, first, last;', 'midpoint, first, last, delta;').replace(
        '    f32 dx, dy, dz;\n', '').replace('dx', 'delta.x').replace('dy', 'delta.y').replace('dz', 'delta.z')
    interleaved = typed.replace('        first.y = owner->start.y - midpoint.y;\n', '').replace(
        '        first.z = owner->start.z - midpoint.z;\n', '').replace(
        '        last.y = owner->end.y - midpoint.y;', '        first.z = owner->start.z - midpoint.z;\n'
        '        last.y = owner->end.y - midpoint.y;\n        first.y = owner->start.y - midpoint.y;')
    yield 'typed-interleaved-deltas', interleaved
    yield 'compact', COMPACT
    yield 'compact-early-norm', COMPACT.replace('        inverse = 1.0f / sqrtf(dx * dx + dz * dz);\n', '').replace(
        '        midpoint.x =', '        inverse = 1.0f / sqrtf(dx * dx + dz * dz);\n        midpoint.x =', 1)
    yield 'compact-vector-delta', COMPACT.replace('midpoint, first, last;', 'midpoint, first, last, delta;').replace(
        '    f32 dx, dy, dz;\n', '').replace('dx', 'delta.x').replace('dy', 'delta.y').replace('dz', 'delta.z')
    yield 'selected', SELECTED
    yield 'point-pointer', SELECTED.replace(
        '        for (offset = 0;', '        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);\n        for (offset = 0;').replace(
        '            point = (OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);\n', '').replace(
        '            angle += angleStep;', '            angle += angleStep;\n            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);')
    yield 'threshold-snapshot', SELECTED.replace('    f32 sine, cosine, along;', '    f32 sine, cosine, along, threshold;').replace(
        '    x0 =', '    threshold = D_800AA3A0;\n    x0 =', 1).replace(
        'D_800AA3A0 < fabsf', 'threshold < fabsf')
    yield 'last-first-locals', SELECTED.replace('midpoint, first, last', 'midpoint, last, first')
    yield 'delta-private', SELECTED.replace('midpoint, first, last;', 'midpoint, first, last, delta;').replace(
        '    f32 dx, dy, dz;\n', '').replace('dx', 'delta.x').replace('dy', 'delta.y').replace('dz', 'delta.z')
    yield 'count-index', SELECTED.replace('offset != 0xF0; offset += 0x18', 'offset != 10; offset++').replace(
        'actor + 0x48 + offset', 'actor + 0x48 + offset * 0x18')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [word & 65535 for word in words[:12]
        if word >> 26 == 9 and word >> 21 & 31 == 29 and word >> 16 & 31 == 29 and word & 0x8000]
    if len(adjustments) != 1:
        raise ValueError('expected one complete negative SP adjustment')
    return dict(meta, frame=(-adjustments[0]) & 65535), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc'
    rows = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles and name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
