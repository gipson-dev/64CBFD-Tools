"""Recover the complete owner descriptor validation and state transition."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B2100, 0x1DF5B0, 67
FUNCTION = 'func_151B2100'
SOURCE = 'conker/src/game/generated_1DF510.c'
ORIGINAL = 's32 func_151B2100() {\n    return 0;\n}'
DECLARATIONS = '''s32 func_151B22F4(u8 *);
void func_151B222C(u8 *);
void func_151B2348(u8 *);
void func_151B2690(u8 *);
'''
SYMBOLS = dict(func_151B22F4=0x151B22F4, func_151B222C=0x151B222C,
    func_151B2348=0x151B2348, func_151B2690=0x151B2690)
SELECTED = '''void func_151B2100(u8 *actor) {
    u8 *first = *(u8 **)(actor + 0x28);
    u8 *second = *(u8 **)(actor + 0x30);
    u8 *pair = actor + 0x28;
    u8 previous;

    if (*(s32 *)first == 0 || first[4] == 255 || pair[4] != first[0x3B] ||
        *(s32 *)second == 0 || second[4] == 255 || pair[12] != second[0x3B]) {
        *(s16 *)(actor + 0xE) = -1;
    } else {
        previous = pair[13];
        pair[13] = func_151B22F4(actor);
        if (previous != pair[13]) {
            func_151B222C(actor);
            if (pair[13] == 1) {
                func_151B2348(actor);
            }
            if (pair[13] == 2 || pair[13] == 0) {
                func_151B2690(actor);
            }
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    declarations = SELECTED.split(' {\n', 1)[1].split('    u8 previous;', 1)[0]
    for order in itertools.permutations(declarations.splitlines()):
        yield 'locals-' + '-'.join(line.split('*')[1].split()[0] for line in order), SELECTED.replace(
            declarations, '\n'.join(order) + '\n')
    yield 'wide-previous', SELECTED.replace('u8 previous;', 's32 previous;')
    yield 'positive-gate', SELECTED.replace('if (*(s32 *)first == 0 || first[4] == 255 || pair[4] != first[0x3B] ||\n        *(s32 *)second == 0 || second[4] == 255 || pair[12] != second[0x3B]) {\n        *(s16 *)(actor + 0xE) = -1;\n    } else {',
        'if (*(s32 *)first != 0 && first[4] != 255 && pair[4] == first[0x3B] &&\n        *(s32 *)second != 0 && second[4] != 255 && pair[12] == second[0x3B]) {').replace(
        '        }\n    }\n}', '        }\n    } else {\n        *(s16 *)(actor + 0xE) = -1;\n    }\n}')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-state'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
