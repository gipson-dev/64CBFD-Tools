"""Complete special actor tile helper; measure original single-precision and state order."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150C3160, 0xF0610, 52
FUNCTION, SOURCE = 'func_150C3160', 'conker/src/game_EF410.c'
ORIGINAL = 's32 func_150C3160() {\n    return 0;\n}'
SELECTED = '''Gfx *func_150C3160(Gfx *commands, u8 *actor) {
    f32 ratio;
    s32 coordinate, previous;

    if (*(s32 *)(actor + 0x2E8) != 0) {
        ratio = (f32)*(s32 *)(actor + 0x2E4) / (f32)*(s32 *)(actor + 0x2E8);
    } else {
        ratio = 1.0f;
    }
    ratio = 1.0f - ratio;
    coordinate = (s32)(500.0f * ratio + 2.0f);
    previous = (s32)(2U - *(u32 *)(actor + 0x2EC));
    *(s32 *)(actor + 0x2EC) = coordinate / 3;
    while (previous < 0) {
        previous += 64;
    }
    gDPSetTileSize(commands++, 4, coordinate, previous, 0x1FE, 0x3E);
    return commands;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'signed-previous', SELECTED.replace('(s32)(2U - *(u32 *)', '(2 - *(s32 *)')
    yield 'ratio-first', SELECTED.replace('    if (*(s32 *)', '    ratio = 1.0f;\n    if (*(s32 *)', 1).replace(
        '    } else {\n        ratio = 1.0f;\n', '')
    yield 'do-wrap', SELECTED.replace('    while (previous < 0) {\n        previous += 64;\n    }',
        '    if (previous < 0) {\n        do {\n            previous += 64;\n        } while (previous < 0);\n    }')
    yield 'coordinate-before-wrap', SELECTED.replace('s32 coordinate, previous;', 's32 previous, coordinate;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS='', SYMBOLS={}):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    meta['frame'] = next(((-word)&65535 for word in words
        if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000), 0)
    return meta, words


def copied_owner(before, body=SELECTED):
    if before.count(ORIGINAL)!=1 or before.count('s32 func_150C3160();')!=1:
        raise ValueError('stale special tile owner')
    return before.replace('s32 func_150C3160();', 'Gfx *func_150C3160(Gfx *, u8 *);').replace(
        '/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C3160.s. */',
        '/* Emit the special actor texture phase and retain the previous phase for wrapping. */').replace(ORIGINAL, body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-actor-special-tile'
    records = []
    for name, body in candidates():
        for profile in ('o2g3', 'o1g3'):
            meta, words = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta, flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
