"""Complete actor-type0x33 timer/callback update recovery and IDO fitting."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B3184, 0x1E0634, 81
FUNCTION = 'func_151B3184'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B3184() {\n    return 0;\n}'
TYPES = ''
DECLARATIONS = '''extern s32 D_800BE9E4;
extern s32 (*D_8008FAF0[])(u8 *, void *, s32);
extern s32 (*D_8008FAF8[])(u8 *);
void func_1516972C(u8 *);
'''
SYMBOLS = dict(D_800BE9E4=0x800BE9E4, D_8008FAF0=0x8008FAF0,
    D_8008FAF8=0x8008FAF8, func_1516972C=0x1516972C)
UNFITTED = '''void func_151B3184(u8 *actor) {
    u8 remove;

    remove = 0;
    if (actor[0x10] & 1) {
        *(s16 *)(actor + 0x12) -= D_800BE9E4;
        if (*(s16 *)(actor + 0x12) < 0) {
            remove = 1;
        }
    }
    if (!remove) {
        if ((s8)actor[0x2C] != -1) {
            if (!D_8008FAF0[(s8)actor[0x2C]](actor, actor + 0x14, 1)) {
                remove = 1;
            }
        }
        if ((s8)actor[0x2D] != -1) {
            if (!D_8008FAF0[(s8)actor[0x2D]](actor, actor + 0x20, 0)) {
                remove = 1;
            }
        }
        if ((actor[0x10] & 4) || (actor[0x10] & 8)) {
            actor[0x10] |= 2;
        } else if ((s8)actor[0x34] != -1) {
            if (!D_8008FAF8[(s8)actor[0x34]](actor)) {
                remove = 1;
            }
        }
    }
    if (remove) {
        func_1516972C(actor);
    }
}'''

SELECTED = UNFITTED.replace('    u8 remove;', '    s32 selector;\n    u8 remove;')
for _offset in ('2C', '2D'):
    SELECTED = SELECTED.replace('        if ((s8)actor[0x' + _offset + '] != -1)',
        '        selector = (s8)actor[0x' + _offset + '];\n        if (selector != -1)').replace(
        'D_8008FAF0[(s8)actor[0x' + _offset + ']]', 'D_8008FAF0[selector]')


def candidates():
    yield 'selected', SELECTED
    yield 'unfitted', UNFITTED
    yield 'volatile-actor', SELECTED.replace('u8 *actor)', 'u8 *volatile actor)')
    yield 'int-remove', SELECTED.replace('u8 remove;', 's32 remove;')
    yield 'explicit-zero', SELECTED.replace('if (!remove)', 'if (remove == 0)')
    yield 'nested-third', SELECTED.replace('} else if ((s8)actor[0x34] != -1) {',
        '} else { if ((s8)actor[0x34] != -1) {').replace('    if (remove) {',
        '    }\n    if (remove) {')
    yield 'byte-and', SELECTED.replace('if ((actor[0x10] & 4) || (actor[0x10] & 8))',
        'if (actor[0x10] & 12)')
    yield 'byte-selector', SELECTED.replace('s32 selector;', 's8 selector;')


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
    out = root / 'conker/build/game-owner-actor-update'
    rows = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles and name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
