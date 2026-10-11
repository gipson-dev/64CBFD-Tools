"""Recover complete live descriptor loading and exact failure-sentinel handling."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503DC3C, 0x6B0EC, 56
FUNCTION, SOURCE = 'func_1503DC3C', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503DC3C() {\n    return 0;\n}'
DECLARATIONS = '''extern u16 D_800C5628[];
extern u32 *D_800C5338[];
u32 func_1510D0EC(u32, s32, s32, s32);
'''
SYMBOLS = dict(D_800C5628=0x800C5628, D_800C5338=0x800C5338,
    func_1510D0EC=0x1510D0EC)
SELECTED = '''s32 func_1503DC3C(s32 identity) {
    u16 *count;
    s32 failed;
    s32 index;
    u32 **slot;
    u32 *cursor;
    s32 offset;
    u32 loaded;

    count = &D_800C5628[identity];
    failed = 0;
    index = 0;
    if (*count > 0) {
        slot = &D_800C5338[identity];
        cursor = *slot;
        offset = 0;
        do {
            loaded = func_1510D0EC(cursor[1], 0, 0x3E, 1);
            *(u32 *)((u8 *)*slot + offset) = loaded;
            cursor = (u32 *)((u8 *)*slot + offset);
            if (*cursor == 0x80000000U) {
                failed |= 0x10;
            }
            index++;
            offset += 12;
            cursor += 3;
        } while (index < *count);
    }
    return failed;
}'''


def candidates():
    yield 'selected', SELECTED
    inline = SELECTED.replace('    u32 loaded;\n', '').replace(
        '            loaded = func_1510D0EC(cursor[1], 0, 0x3E, 1);\n'
        '            *(u32 *)((u8 *)*slot + offset) = loaded;',
        '            *(u32 *)((u8 *)*slot + offset) = func_1510D0EC(cursor[1], 0, 0x3E, 1);')
    yield 'inline-result', inline
    yield 'count-last', inline.replace('    u16 *count;\n', '').replace(
        '    s32 offset;', '    s32 offset;\n    u16 *count;')
    yield 'inline-slot', inline.replace('    u32 **slot;\n', '').replace(
        '        slot = &D_800C5338[identity];\n', '').replace('*slot', 'D_800C5338[identity]')
    yield 'inline-count', inline.replace('    u16 *count;\n', '').replace(
        '    count = &D_800C5628[identity];\n', '').replace('*count', 'D_800C5628[identity]')


QUALIFIED = SELECTED


def compile_candidate(root, out, name, body=None, profile='retail'):
    body = QUALIFIED if body is None else body
    profiles = dict(compiler.PROFILES,retail=('-O2','-g3','-Wo,-loopunroll,0'))
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=profiles):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before, body=None):
    body = QUALIFIED if body is None else body
    if before.count(ORIGINAL)!=1 or before.count('s32 func_1503DC3C();')!=1:
        raise ValueError('stale extras loader owner/interface')
    return before.replace('s32 func_1503DC3C();','s32 func_1503DC3C(s32);').replace(
        ORIGINAL,'u32 func_1510D0EC(u32, s32, s32, s32);\n\n'+body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-resource-extras'
    records = []
    for name,body in candidates() if args.variants else [('qualified',QUALIFIED)]:
        meta,_ = compile_candidate(root,out,name,body)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
