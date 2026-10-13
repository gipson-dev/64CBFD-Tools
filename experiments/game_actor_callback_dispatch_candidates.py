"""Recover the indexed actor's live state and type-specific callbacks."""
import argparse
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_type_dispatch_candidates import compile_owner

ENTRY, ROM, WORDS = 0x150345E4, 0x61A94, 81
FUNCTION, SOURCE = 'func_150345E4', 'conker/src/game/generated_61490.c'
CALLER_SOURCE = 'conker/src/game/generated_58F80.c'
CALLER_OLD, CALLER_NEW = 's32 func_150345E4();', 'void func_150345E4(s32 slot);'
OWNER_DECLARATIONS = '''extern u8 D_800BE616;
s32 func_15036310(s32, s32, s32, s32);
void func_15034EB4(u8 *, s32, s32);
s32 func_150F1A00(u8 *);
void func_150DFDA4(u8 *);
'''
DECLARATIONS = OWNER_DECLARATIONS + 'extern u8 D_800CC2D0[];\nvoid func_1503453C(s32);\n'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800BE616=0x800BE616,
    func_1503453C=0x1503453C, func_15036310=0x15036310, func_15034EB4=0x15034EB4,
    func_150F1A00=0x150F1A00, func_150DFDA4=0x150DFDA4)
ORIGINAL = 's32 func_150345E4() {\n    return 0;\n}'
BASE = '''void func_150345E4(s32 index) {
    u8 *actor = D_800CC2D0 + (u32)index * 0x32C;

    if (*(u32 *)(actor + 0x1D4) == 0) {
        return;
    }
    if (*(s32 *)actor == 1 || actor[5] == 7) {
        func_1503453C(index);
    }
    if (*(s32 *)actor == 0x22) {
        func_1503453C(index);
    }
    switch (actor[4]) {
        case 4:
            if (D_800BE616 == 0) {
                func_15036310(0, index, 9, 0);
                func_15036310(0, index, 4, 0);
            }
            break;
        case 0x60:
            func_150DFDA4(actor);
            break;
        case 0x70:
            func_15034EB4(actor, 10, 11);
            break;
        case 0x7B:
            func_150F1A00(actor);
            break;
    }
}'''
RETAIL_CASES = BASE.replace('        case 0x60:\n            func_150DFDA4(actor);\n            break;\n', '').replace(
    '            func_150F1A00(actor);\n            break;',
    '            func_150F1A00(actor);\n            break;\n        case 0x60:\n            func_150DFDA4(actor);\n            break;')
SELECTED = RETAIL_CASES.replace('    u8 *actor =', '    s32 type;\n    u8 *actor =').replace(
    '    switch (actor[4]) {', '    type = actor[4];\n    switch (type) {')
FRAME_WORDS = {0x0:(0x27BDFFD8,0x27BDFFE0),0x8:(0xAFA40028,0xAFA40020),
    0xC:(0x8FAE0028,0x8FAE0020),0x54:(0x8FA40028,0x8FA40020),
    0x88:(0x8FA40028,0x8FA40020),0xD8:(0x8FA50028,0x8FA50020),
    0xF0:(0x8FA50028,0x8FA50020),0x138:(0x27BD0028,0x27BD0020)}


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known callback dispatcher placeholder or complete body')
    if OWNER_DECLARATIONS not in source:
        source = source.replace('extern u8 D_800CC2D4[];', OWNER_DECLARATIONS + '\nextern u8 D_800CC2D4[];', 1)
    return source


def recovered_caller(source):
    if source.count(CALLER_OLD) == 1:
        return source.replace(CALLER_OLD, CALLER_NEW)
    if source.count(CALLER_NEW) == 1:
        return source
    raise ValueError('Expected the known caller prototype')


def compile_candidate(root, out, name, body=SELECTED):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body)


def candidates():
    yield 'selected', SELECTED
    yield 'volatile-index', BASE.replace('s32 index)', 'volatile s32 index)')
    yield 'ordinary-index', BASE
    yield 'signed-index-arithmetic', SELECTED.replace('(u32)index *', 'index *')
    yield 'separate-actor-local', SELECTED.replace('    u8 *actor =', '    u8 *actor;\n\n    actor =')
    last_case = BASE.replace('        case 0x60:\n            func_150DFDA4(actor);\n            break;\n', '').replace(
        '            func_150F1A00(actor);\n            break;', '            func_150F1A00(actor);\n            break;\n        case 0x60:\n            func_150DFDA4(actor);\n            break;')
    yield 'retail-case-order', last_case
    yield 'register-actor', BASE.replace('    u8 *actor', '    register u8 *actor')
    yield 'register-actor-retail-cases', last_case.replace('    u8 *actor', '    register u8 *actor')
    yield 'ordinary-separate-actor', last_case.replace('    u8 *actor =', '    u8 *actor;\n\n    actor =')
    yield 'explicit-default', SELECTED.replace('            func_150DFDA4(actor);\n            break;',
        '            func_150DFDA4(actor);\n            break;\n        default:\n            break;')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-callback-dispatch'
    for name, body in candidates() if args.controls else [('selected', SELECTED)]:
        meta, _ = compile_candidate(root, out, name, body)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'], flush=True)


if __name__ == '__main__':
    main()
