"""Recover the complete reciprocal/range alpha caller of the four-output matrix entry."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502D630, 0x5AAE0, 125
FUNCTION, SOURCE = 'func_1502D630', 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502D630() {\n    return 0;\n}'
DECLARATIONS = '''extern f32 D_800D9B1C, D_800D9B20;
extern u16 D_800DD2E8, D_800DD2EC;
extern f32 D_800D2CA8[][16];
extern f32 D_80096DE8, D_80096DEC, D_80096DF0, D_80096DF4;
void func_150A7A00(f32 *, f32, f32, f32, f32 *, f32 *, f32 *, f32 *);
'''
SYMBOLS = dict(D_800D9B1C=0x800D9B1C, D_800D9B20=0x800D9B20,
    D_800DD2E8=0x800DD2E8, D_800DD2EC=0x800DD2EC, D_800D2CA8=0x800D2CA8,
    D_80096DE8=0x80096DE8, D_80096DEC=0x80096DEC,
    D_80096DF0=0x80096DF0, D_80096DF4=0x80096DF4, func_150A7A00=0x150A7A00)
SELECTED = '''void func_1502D630(u8 *actor, s32 *parameters, s32 view) {
    f32 start, end, step;
    f32 x, y, z, w;
    f32 factor;

    start = D_800D9B1C != 0.0f ? 1.0f / D_800D9B1C : D_80096DE8;
    end = D_800D9B20 != 0.0f ? 1.0f / D_800D9B20 : D_80096DEC;
    step = (start - end) * D_80096DF0;
    start = (f32)(u32)D_800DD2E8 * step + end;
    end = (f32)(u32)D_800DD2EC * step + end;
    func_150A7A00(D_800D2CA8[view], *(f32 *)(actor + 0x14),
        *(f32 *)(actor + 0x18), *(f32 *)(actor + 0x1C), &x, &y, &z, &w);
    if (w != 0.0f) {
        w = 1.0f / w;
    } else {
        w = D_80096DF4;
    }
    if (w < 0.0f || end <= w) {
        factor = 0.0f;
    } else if (w <= start) {
        factor = 1.0f;
    } else {
        factor = (w - end) / (start - end);
    }
    parameters[3] = (s32)((1.0f - factor) * 255.0f);
}'''


def candidates():
    yield 'selected', SELECTED
    explicit = SELECTED.replace(
        '    start = D_800D9B1C != 0.0f ? 1.0f / D_800D9B1C : D_80096DE8;',
        '    if (D_800D9B1C != 0.0f) { start = 1.0f / D_800D9B1C; } else { start = D_80096DE8; }').replace(
        '    end = D_800D9B20 != 0.0f ? 1.0f / D_800D9B20 : D_80096DEC;',
        '    if (D_800D9B20 != 0.0f) { end = 1.0f / D_800D9B20; } else { end = D_80096DEC; }')
    nested = explicit.replace('if (w < 0.0f || end <= w)', 'if (w < 0.0f)').replace(
        '} else if (w <= start)', '} else if (end <= w) {\n        factor = 0.0f;\n    } else if (w <= start)')
    yield 'explicit-reciprocals', explicit
    yield 'explicit-nested', nested
    split = nested.replace('f32 start, end, step;', 'f32 start, end, first, second, step;').replace(
        '{ start = 1.0f / D_800D9B1C; } else { start = D_80096DE8; }',
        '{ first = 1.0f / D_800D9B1C; } else { first = D_80096DE8; }').replace(
        '{ end = 1.0f / D_800D9B20; } else { end = D_80096DEC; }',
        '{ second = 1.0f / D_800D9B20; } else { second = D_80096DEC; }').replace(
        'step = (start - end)', 'step = (first - second)').replace(
        '* step + end;', '* step + second;')
    yield 'split-reciprocals', split
    ordered = split.replace('f32 start, end, first, second, step;',
        'f32 end, start, first, second, step;')
    yield 'ordered-private-homes', ordered
    yield 'literal-final-fallback', ordered.replace('w = D_80096DF4;', 'w = 0.001f;')
    yield 'literal-first-fallback', ordered.replace('first = D_80096DE8;', 'first = 0.001f;')
    yield 'literal-all-split', ordered.replace('D_80096DE8', '0.001f').replace(
        'D_80096DEC', '0.001f').replace('D_80096DF0', '0.001f').replace('D_80096DF4', '0.001f')
    yield 'ternary-w', ordered.replace('''    if (w != 0.0f) {
        w = 1.0f / w;
    } else {
        w = D_80096DF4;
    }''', '    w = w != 0.0f ? 1.0f / w : D_80096DF4;')
    yield 'compound-alpha', ordered.replace('    parameters[3] = (s32)((1.0f - factor) * 255.0f);',
        '    factor = 1.0f - factor;\n    parameters[3] = (s32)(factor * 255.0f);')
    yield 'factor-zero-before-reciprocal', ordered.replace(
        '    if (w != 0.0f)', '    factor = 0.0f;\n    if (w != 0.0f)')
    yield 'factor-zero-before-matrix', ordered.replace('    func_150A7A00(',
        '    factor = 0.0f;\n    func_150A7A00(')
    yield 'factor-zero-after-reciprocal', ordered.replace(
        '    if (w < 0.0f)', '    factor = 0.0f;\n    if (w < 0.0f)')
    yield 'explicit-zero-variable', ordered.replace('    f32 factor;',
        '    f32 factor, zero;').replace('    if (w != 0.0f)',
        '    zero = 0.0f;\n    if (w != 0.0f)').replace('factor = 0.0f;', 'factor = zero;')
    yield 'literal-constants', SELECTED.replace('D_80096DE8', '0.001f').replace(
        'D_80096DEC', '0.001f').replace('D_80096DF0', '0.001f').replace('D_80096DF4', '0.001f')
    yield 'nested-clamps', SELECTED.replace('if (w < 0.0f || end <= w)',
        'if (w < 0.0f)').replace('} else if (w <= start)',
        '} else if (end <= w) {\n        factor = 0.0f;\n    } else if (w <= start)')
    yield 'output-first', SELECTED.replace('    f32 start, end, step;\n    f32 x, y, z, w;',
        '    f32 x, y, z, w;\n    f32 start, end, step;')
    yield 'signed-halfword-cast', SELECTED.replace('(f32)(u32)', '(f32)(s32)')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-alpha-shading'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
