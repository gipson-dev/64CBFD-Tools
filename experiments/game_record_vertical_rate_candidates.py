"""Recover timer-120 initialization and unsigned random vertical rates."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503EFC4, 0x6C474, 45
FUNCTION, SOURCE = 'func_1503EFC4', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503EFC4() {\n    return 0;\n}'
DECLARATIONS = '''#include "variables.h"
extern u8 D_80098914[];
s32 func_150ADA20(void);
'''
SYMBOLS = dict(D_800C6660=0x800C6660, D_80098914=0x80098914, func_150ADA20=0x150ADA20)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3'), compact=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''void func_1503EFC4(s32 slot) {
    struct106 *control = &D_800C6660[slot];
    s32 count;
    s32 index;

    *(s16 *)((u8 *)control + 0xC) = 120;
    count = D_80098914[((u8 *)control)[0xE]];
    for (index = 0; index < count; index++) {
        u32 random = func_150ADA20();
        ((f32 *)((struct04 *)control->unk0 + index))[19] = (s32)(random % 20) - 5;
    }
}'''
SELECTED = BASE.replace('        u32 random = func_150ADA20();\n', '').replace(
    'random % 20', '(u32)func_150ADA20() % 20')


def candidates():
    yield 'selected', SELECTED
    yield 'unsigned-literal', BASE.replace('random % 20', 'random % 20U')
    yield 'direct-expression', BASE.replace('        u32 random = func_150ADA20();\n', '').replace(
        'random % 20', '(u32)func_150ADA20() % 20')
    yield 'cached-group', BASE.replace('    s32 count;', '    u8 group;\n    s32 count;').replace(
        '    *(s16 *)', '    group = ((u8 *)control)[0xE];\n    *(s16 *)').replace(
        'D_80098914[((u8 *)control)[0xE]]', 'D_80098914[group]')
    yield 'count-first', BASE.replace('    s32 count;\n', '').replace(
        '    struct106 *control', '    s32 count;\n    struct106 *control')
    yield 'divisor-local', BASE.replace('    s32 index;', '    s32 index;\n    u32 divisor = 20;').replace(
        'random % 20', 'random % divisor')
    yield 'do-loop', BASE.replace('    for (index = 0; index < count; index++) {',
        '    index = 0;\n    if (count > 0) {\n    do {').replace(
        '    }\n}', '        index++;\n    } while (index != count);\n    }\n}')
    yield 'offset-cursor', BASE.replace('    s32 index;', '    s32 index;\n    s32 offset = 0;').replace(
        '(struct04 *)control->unk0 + index', '(struct04 *)(control->unk0 + offset)').replace(
        'index++)', 'index++, offset += 104)')
    yield 'count-home-slot', BASE.replace('    s32 count;\n', '').replace('count = D_', 'slot = D_').replace(
        'index < count', 'index < slot')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    return source.replace(ORIGINAL, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='selected')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root=Path(__file__).resolve().parents[2]; out=root/'conker/build/game-record-vertical-rate'
    records=[]
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner','compact','o1g3','o1') if args.profiles else ('owner',)):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta); print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
