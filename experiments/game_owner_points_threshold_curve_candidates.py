"""Complete threshold-selected owner curve; bounded source/profile measurements."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B3FDC, 0x1E148C, 178
FUNCTION = 'func_151B3FDC'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B3FDC() {\n    return 0;\n}'
TYPES = 'typedef struct { f32 x, y, z; } OwnerRibbonPosition32C8;\n'
DECLARATIONS = '''extern f32 D_800AA3B0, D_800AA3B4;
s32 func_151B3A7C(u8 *);
f32 sinf(f32), cosf(f32), sqrtf(f32), fabsf(f32);
#pragma intrinsic (fabsf)
'''
OWNER_INSERT = 'extern f32 D_800AA3B0, D_800AA3B4;\n'
SYMBOLS = dict(D_800AA3B0=0x800AA3B0, D_800AA3B4=0x800AA3B4,
    func_151B3A7C=0x151B3A7C, sinf=0x15047D60, cosf=0x15047C00)
SELECTED = '''s32 func_151B3FDC(u8 *actor) {
    OwnerRibbonPosition32C8 midpoint, first, last;
    f32 x0, y0, z0, x1, y1, z1;
    f32 epsilon, dx, dy, dz, inverse, nx, nz;
    f32 projection, vertical, squared, length, radius, threshold, quarter;
    f32 horizontal, upright, minorRadius, angle, sine, along, across, h, v;
    s32 offset;
    OwnerRibbonPosition32C8 *cursor;

    epsilon = D_800AA3B0;
    x1 = *(f32 *)(actor + 0x20);
    x0 = *(f32 *)(actor + 0x14);
    y1 = *(f32 *)(actor + 0x24);
    y0 = *(f32 *)(actor + 0x18);
    dx = x1 - x0;
    dy = y1 - y0;
    z1 = *(f32 *)(actor + 0x28);
    z0 = *(f32 *)(actor + 0x1C);
    dz = z1 - z0;
    if (epsilon < fabsf(dx) || epsilon < fabsf(dz)) {
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
        squared = projection * projection + vertical * vertical;
        length = sqrtf(squared);
        inverse = 1.0f / length;
        radius = length * 0.5f;
        threshold = *(f32 *)(actor + 0x138);
        horizontal = projection * inverse;
        upright = vertical * inverse;
        quarter = squared * 0.25f;
        if (threshold < quarter) {
            return func_151B3A7C(actor);
        }
        minorRadius = sqrtf(threshold - quarter);
        angle = 0.0f;
        cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);
        for (offset = 0; offset != 0xF0; offset += 0x18) {
            sine = sinf(angle);
            along = radius * cosf(angle);
            across = minorRadius * sine;
            h = along * horizontal - across * upright;
            v = along * upright - across * horizontal;
            cursor->x = h * nx + midpoint.x;
            cursor->y = v + midpoint.y;
            cursor->z = h * nz + midpoint.z;
            angle += D_800AA3B4;
            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);
        }
    }
    return 1;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'private-vectors', SELECTED.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
        '    volatile OwnerRibbonPosition32C8 midpoint, first, last;')
    yield 'private-threshold', SELECTED.replace('radius, threshold, quarter;', 'radius, quarter;\n    volatile f32 threshold;')
    yield 'private-squared', SELECTED.replace('vertical, squared, length', 'vertical, length').replace(
        '    s32 offset;', '    volatile f32 squared;\n    s32 offset;')
    yield 'private-first-last', SELECTED.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
        '    OwnerRibbonPosition32C8 midpoint;\n    volatile OwnerRibbonPosition32C8 first, last;')
    private_y = SELECTED.replace('epsilon, dx, dy, dz, inverse', 'epsilon, dx, dz, inverse').replace(
        '    s32 offset;', '    volatile f32 dy;\n    s32 offset;')
    yield 'private-delta-y', private_y
    yield 'private-delta-y-threshold', private_y.replace('radius, threshold, quarter;',
        'radius, quarter;\n    volatile f32 threshold;')
    yield 'negative-plus-upright', SELECTED.replace('v = along * upright - across * horizontal;',
        'v = along * upright + across * horizontal;')
    yield 'negative-stale-step', SELECTED.replace('    s32 offset;', '    f32 angleStep;\n    s32 offset;').replace(
        '        angle = 0.0f;', '        angleStep = D_800AA3B4;\n        angle = 0.0f;').replace(
        'angle += D_800AA3B4;', 'angle += angleStep;')
    yield 'negative-quarter-from-radius', SELECTED.replace('quarter = squared * 0.25f;', 'quarter = radius * radius;')
    yield 'negative-discard-fallback-result', SELECTED.replace('return func_151B3A7C(actor);',
        'func_151B3A7C(actor);\n            return 1;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None, entry=ENTRY):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=entry, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [w & 65535 for w in words[:16] if w >> 26 == 9 and w >> 21 & 31 == 29
        and w >> 16 & 31 == 29 and w & 32768]
    if len(adjustments) != 1:
        raise ValueError('expected one complete frame allocation')
    meta['frame'] = (-adjustments[0]) & 65535
    return meta, words


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-curve'
    rows = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        rows.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
