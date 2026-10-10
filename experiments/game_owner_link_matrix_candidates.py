"""Complete linked-node endpoint updater, byte selector and palette reload."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B47D8, 0x1E1C88, 65
FUNCTION = 'func_151B47D8'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B47D8() {\n    return 0;\n}'
TYPES = '''typedef struct {
    u8 *first;
    u8 firstEpoch, firstMatrix, padding06[2];
    f32 firstPosition[3];
    u8 *second;
    u8 secondEpoch, secondMatrix, padding1A[2];
    f32 secondPosition[3];
} OwnerMatrixLink47D8;
'''
DECLARATIONS = 'void func_15143134(f32 *, f32 *, u8 *);\n'
SYMBOLS = dict(func_15143134=0x15143134)
BASE = '''s32 func_151B47D8(u8 *actor, OwnerMatrixLink47D8 *link,
    f32 *destination, u8 firstEndpoint) {
    u8 *first;
    u8 *second;
    s32 mask;
    f32 *point;
    u8 *matrix;

    first = link->first;
    second = link->second;
    if (*(u8 **)(first + 0x1D4) == NULL || *(u8 **)(second + 0x1D4) == NULL) {
        actor[0x10] |= 0xC;
        return 1;
    }
    if (*(s32 *)first == 0 || link->firstEpoch != first[0x3B] ||
        *(s32 *)second == 0 || link->secondEpoch != second[0x3B]) {
        return 0;
    }
    mask = firstEndpoint ? 4 : 8;
    actor[0x10] &= ~mask;
    point = firstEndpoint ? link->firstPosition : link->secondPosition;
    if (firstEndpoint) {
        matrix = *(u8 **)(first + 0x1D4) + (link->firstMatrix << 6);
    } else {
        matrix = *(u8 **)(second + 0x1D4) + (link->secondMatrix << 6);
    }
    func_15143134(point, destination, matrix);
    return 1;
}'''
SELECTED = BASE.replace('    s32 mask;\n', '').replace('    u8 *matrix;',
    '    union { s32 mask; u8 *matrix; } selected;').replace(
    'mask = firstEndpoint', 'selected.mask = firstEndpoint').replace(
    'actor[0x10] &= ~mask;', 'actor[0x10] &= ~selected.mask;').replace(
    '        matrix =', '        selected.matrix =').replace(
    'func_15143134(point, destination, matrix)', 'func_15143134(point, destination, selected.matrix)')


def candidates():
    yield 'selected', SELECTED
    yield 'split-mask', BASE
    yield 'word-selector', SELECTED.replace('u8 firstEndpoint', 'u32 firstEndpoint').replace(
        '    first = link->first;', '    firstEndpoint = (u8)firstEndpoint;\n    first = link->first;')
    yield 'shared-word', BASE.replace('    s32 mask;', '').replace('    u8 *matrix;',
        '    u32 selected;').replace('mask = firstEndpoint', 'selected = firstEndpoint').replace(
        'actor[0x10] &= ~mask;', 'actor[0x10] &= ~selected;').replace(
        'matrix = *(u8 **)', 'selected = (u32)*(u8 **)').replace(
        'func_15143134(point, destination, matrix)', 'func_15143134(point, destination, (u8 *)selected)')
    yield 'negative-full-word-selector', SELECTED.replace('u8 firstEndpoint', 'u32 firstEndpoint')
    yield 'negative-wrong-flag', SELECTED.replace('firstEndpoint ? 4 : 8', 'firstEndpoint ? 8 : 4')
    yield 'negative-wrong-output', SELECTED.replace(
        'firstEndpoint ? link->firstPosition : link->secondPosition',
        'firstEndpoint ? link->secondPosition : link->firstPosition')
    yield 'negative-short-index', SELECTED.replace('Matrix << 6', 'Matrix << 5')
    yield 'negative-missing-epoch', SELECTED.replace('link->firstEpoch != first[0x3B]', '0')
    yield 'negative-cached-palette', SELECTED.replace('    f32 *point;', '    f32 *point;\n    u8 *palette;').replace(
        '    selected.mask = firstEndpoint ? 4 : 8;',
        '    palette = *(u8 **)((firstEndpoint ? first : second) + 0x1D4);\n    selected.mask = firstEndpoint ? 4 : 8;').replace(
        '*(u8 **)(first + 0x1D4) +', 'palette +').replace('*(u8 **)(second + 0x1D4) +', 'palette +')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None, entry=ENTRY):
    with patch.multiple(compiler, ENTRY=entry, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('expected one original endpoint placeholder')
    return before.replace('/* Non-matching placeholders', TYPES + DECLARATIONS +
        '\n/* Non-matching placeholders', 1).replace(ORIGINAL, SELECTED)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-link-matrix'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
