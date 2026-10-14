"""Recover the signed actor-mask snapshot and six-slot vector dispatch."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1506AAE0, 0x97F90, 39
FUNCTION = 'func_1506AAE0'
SOURCE = 'conker/src/game/generated_97AA0.c'
ORIGINAL = 's32 func_1506AAE0() {\n    return 0;\n}'
MARKER = 'extern u8 D_800D1560[];'
DECLARATIONS = '''extern s32 D_800CC260;
extern u8 D_800CC2D0[];
s32 func_15137610(u8 *, u8 *, u8 *, s32, u8, s32);
'''
SYMBOLS = dict(D_800CC260=0x800CC260, D_800CC2D0=0x800CC2D0,
    D_800D1560=0x800D1560, D_800D1570=0x800D1570, func_15137610=0x15137610)
VECTORS = 'extern u8 D_800D1560[];\nextern u8 D_800D1570[];\n'
SELECTED = '''void func_1506AAE0(s32 arg0, s32 arg1) {
    s32 mask = D_800CC260;
    u8 *actor = D_800CC2D0;

    while (mask != 0) {
        if (mask & 1) {
            func_15137610(actor, D_800D1560, D_800D1570, 0, 0xFF, 1);
        }
        mask >>= 1;
        actor += 0x32C;
    }
}'''


def candidates():
    for order, loop, qualifiers in itertools.product((0, 1), ('while', 'for', 'do'), range(4)):
        body = SELECTED
        if order:
            body = body.replace('    s32 mask = D_800CC260;\n    u8 *actor = D_800CC2D0;',
                '    u8 *actor = D_800CC2D0;\n    s32 mask = D_800CC260;')
        if qualifiers & 1:
            body = body.replace('s32 arg0', 's32 volatile arg0')
        if qualifiers & 2:
            body = body.replace('s32 arg1', 's32 volatile arg1')
        if loop == 'for':
            body = body.replace('while (mask != 0)', 'for (; mask != 0; mask >>= 1, actor += 0x32C)')
            body = body.replace('        mask >>= 1;\n        actor += 0x32C;\n', '')
        elif loop == 'do':
            body = body.replace('    while (mask != 0) {', '    if (mask != 0) {\n        do {')
            body = body.replace('    }\n}', '        } while (mask != 0);\n    }\n}')
        yield 'order%d-%s-qualifier%d' % (order, loop, qualifiers), body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=VECTORS, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def recovered_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1:
        raise ValueError('Expected the original mask-scan placeholder and vector declarations')
    return before.replace(MARKER, DECLARATIONS + '\n' + MARKER, 1).replace(ORIGINAL, body, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-mask-scan'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
