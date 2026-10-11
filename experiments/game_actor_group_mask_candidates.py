"""Recover the complete actor/group mask command wrapper without word guards."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503DE70, 0x6B320, 39
FUNCTION, SOURCE = 'func_1503DE70', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503DE70() {\n    return 0;\n}'
PROTOTYPE = 'void func_1503DF0C(s32, s32, s32, s32);'
ANCHOR = 'extern s32 *D_8008446C[];'
DECLARATIONS = '#include "variables.h"\n' + ANCHOR + '\n' + PROTOTYPE + '\n'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_8008446C=0x8008446C, func_1503DF0C=0x1503DF0C)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
FLAT = '''void func_1503DE70(struct127 *actor, s32 group, s32 entry) {
    if (entry != -1) {
        func_1503DF0C(((s32)actor - (s32)D_800CC2D0) / (s32)sizeof(struct127),
            group, D_8008446C[group][entry * 2], D_8008446C[group][entry * 2 + 1]);
    } else {
        func_1503DF0C(((s32)actor - (s32)D_800CC2D0) / (s32)sizeof(struct127),
            group, -1, -1);
    }
}'''
SELECTED = FLAT.replace('D_8008446C[group][entry * 2], D_8008446C[group][entry * 2 + 1]',
    '((s32 (*)[2])D_8008446C[group])[entry][0], ((s32 (*)[2])D_8008446C[group])[entry][1]')


def candidates():
    yield 'selected', SELECTED
    yield 'flat', FLAT
    for name, first, second in (
            ('shift-index', 'D_8008446C[group][entry << 1]', 'D_8008446C[group][(entry << 1) + 1]'),
            ('pair-array', '((s32 (*)[2])D_8008446C[group])[entry][0]', '((s32 (*)[2])D_8008446C[group])[entry][1]'),
            ('byte-pair', '((s32 *)((u8 *)D_8008446C[group] + entry * 8))[0]',
                '((s32 *)((u8 *)D_8008446C[group] + entry * 8))[1]'),
            ('byte-words', '*(s32 *)((u8 *)D_8008446C[group] + entry * 8)',
                '*(s32 *)((u8 *)D_8008446C[group] + entry * 8 + 4)')):
        yield name, FLAT.replace('D_8008446C[group][entry * 2], D_8008446C[group][entry * 2 + 1]',
            first + ', ' + second)
    yield 'pointer-difference', FLAT.replace(
        '((s32)actor - (s32)D_800CC2D0) / (s32)sizeof(struct127)', 'actor - D_800CC2D0')
    yield 'local-pair', FLAT.replace('    if (entry != -1)', '    s32 *pair;\n\n    if (entry != -1)').replace(
        '        func_1503DF0C(', '        pair = D_8008446C[group] + entry * 2;\n        func_1503DF0C(', 1).replace(
        'D_8008446C[group][entry * 2], D_8008446C[group][entry * 2 + 1]', 'pair[0], pair[1]')


def install(source):
    assert source.count(ORIGINAL) == source.count(ANCHOR) == 1
    assert PROTOTYPE not in source and SELECTED not in source
    return source.replace(ORIGINAL, SELECTED).replace(ANCHOR, ANCHOR + '\n' + PROTOTYPE)


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-group-mask'
    measurements = []
    for name, body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in ('owner', 'compact') if args.profiles else ('owner',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            measurements.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')


if __name__ == '__main__':
    main()
