"""Recover group-2 active timer expiry and live paired-mask flag updates."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503F2B0, 0x6C760, 85
FUNCTION, SOURCE = 'func_1503F2B0', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503F2B0() {\n    return 0;\n}'
DECLARATIONS = '''#include "variables.h"
void func_1503ECA0(s32);
void func_1503E260(s32);
s32 func_1503EF4C(s32, s32, s32);
'''
SYMBOLS = dict(D_800C6660=0x800C6660, D_800BE9E4=0x800BE9E4,
    D_800CC2D0=0x800CC2D0, func_1503ECA0=0x1503ECA0,
    func_1503E260=0x1503E260, func_1503EF4C=0x1503EF4C)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'),
    compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503F2B0(s32 slot) {
    struct106 *control;

    func_1503ECA0(slot);
    control = &D_800C6660[slot];
    *(s16 *)((u8 *)control + 0xC) -= D_800BE9E4;
    if (*(s16 *)((u8 *)control + 0xC) <= 0) {
        func_1503E260(slot);
        if (func_1503EF4C(2, 0, slot) != 0) {
            D_800CC2D0[slot].unk94 |= 8;
        }
        if (func_1503EF4C(2, 1, slot) != 0) {
            D_800CC2D0[slot].unk94 |= 4;
        }
        if (func_1503EF4C(2, 2, slot) != 0) {
            D_800CC2D0[slot].unk94 |= 2;
        }
    }
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'early-return', BASE.replace('    if (*(s16 *)((u8 *)control + 0xC) <= 0) {',
        '    if (*(s16 *)((u8 *)control + 0xC) > 0) {\n        return;\n    }\n    {')
    yield 'explicit-subtract', BASE.replace(' -= D_800BE9E4;',
        ' = *(s16 *)((u8 *)control + 0xC) - D_800BE9E4;')
    yield 'truthy', BASE.replace(' != 0', '')
    yield 'halfword-result', BASE.replace('    struct106 *control;', '    struct106 *control;\n    s16 timer;').replace(
        '    if (*(s16 *)((u8 *)control + 0xC) <= 0) {',
        '    timer = *(s16 *)((u8 *)control + 0xC);\n    if (timer <= 0) {')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS,
            SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    return source.replace(ORIGINAL, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='selected')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-record-mask-active'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
