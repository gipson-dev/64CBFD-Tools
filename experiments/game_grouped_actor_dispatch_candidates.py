"""Recover the two-index descriptor gate and retained actor dispatch lifetime."""
import argparse
from pathlib import Path
import subprocess
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_context_classifier_candidates import compile_owner as generic_owner

ENTRY, ROM, WORDS = 0x150226BC, 0x4FB6C, 38
FUNCTION, SOURCE = 'func_150226BC', 'conker/src/game/generated_49D30.c'
TABLE_DECLARATIONS = '''extern u16 *D_800C35C8[];
extern u8 *D_800C35F0[];
'''
DECLARATIONS = TABLE_DECLARATIONS + 'u8 *func_151149AC(u8);\nvoid func_15022640(s32, s32);\n'
SYMBOLS = dict(D_800C35C8=0x800C35C8, D_800C35F0=0x800C35F0,
               func_151149AC=0x151149AC, func_15022640=0x15022640)
ORIGINAL = 's32 func_150226BC() {\n    return 0;\n}'
SELECTED = '''void func_150226BC(s32 index, s32 group) {
    u8 *actor;
    u8 *record;

    if (D_800C35C8[group][index] == 0) {
        return;
    }
    record = D_800C35F0[group] + (u32)index * 8;
    if (*(u16 *)record != 3) {
        return;
    }
    actor = func_151149AC(record[2]);
    if (actor != NULL) {
        if (actor[0x6E] == 1) {
            func_15022640(actor[0x72], group);
            actor[0x6E] = 0;
        }
    }
}'''


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known dispatcher placeholder or complete body')
    if TABLE_DECLARATIONS not in source:
        source = source.replace('#include "structs.h"\n', '#include "structs.h"\n' + TABLE_DECLARATIONS, 1)
    return source


def compile_candidate(root, out, name, body=SELECTED):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS,
                        PROFILES=dict(compiler.PROFILES, owner=('-O2', '-g3', '-Wo,-loopunroll,0'))):
        return compiler.compile_candidate(root, out, name, body, 'owner')


def compile_owner(root, out, source, name):
    run = subprocess.run
    invocations = []

    def with_profile(argv, **kwargs):
        if argv[0] == str(root / 'ido/ido5.3_recomp/cc'):
            argv = list(argv)
            argv.insert(argv.index('-mips2'), '-Wo,-loopunroll,0')
            invocations.append(argv)
        return run(argv, **kwargs)

    # Retain the existing owner preprocessing, adding its real per-slice flag.
    with patch.object(subprocess, 'run', side_effect=with_profile):
        result = generic_owner(root, out, source, name)
    if len(invocations) != 1:
        raise ValueError('Expected exactly one production owner compiler invocation')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-grouped-actor-dispatch'
    out.mkdir(exist_ok=True)
    bodies = [('direct', SELECTED)]
    if args.controls:
        bodies += [('combined-actor-gate', SELECTED.replace('if (actor != NULL) {\n        if (actor[0x6E] == 1) {',
            'if (actor != NULL && actor[0x6E] == 1) {').replace('        }\n    }\n}', '    }\n}')),
            ('signed-record-offset', SELECTED.replace('(u32)index * 8', 'index * 8')),
            ('record-declaration-first', SELECTED.replace('    u8 *actor;\n    u8 *record;', '    u8 *record;\n    u8 *actor;'))]
    for name, body in bodies:
        meta, _ = compile_candidate(root, out, name, body)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'], flush=True)


if __name__ == '__main__':
    main()
