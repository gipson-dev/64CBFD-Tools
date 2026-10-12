"""Recover timer-300 finish and three actor-flag mask-query updates."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503F16C, 0x6C61C, 81
FUNCTION, SOURCE = 'func_1503F16C', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503F16C() {\n    return 0;\n}'
LOCAL_DECLARATION = 'extern u8 D_800C666C[];\n'
DECLARATIONS = '#include "variables.h"\n'+LOCAL_DECLARATION+'s32 func_1503EF4C(s32, s32, s32);\n'
SYMBOLS = dict(D_800C666C=0x800C666C, D_800CC2D0=0x800CC2D0, func_1503EF4C=0x1503EF4C)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3'), compact=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''void func_1503F16C(s32 slot) {
    *(s16 *)(D_800C666C + slot * 0x10) = 300;
    if (func_1503EF4C(2, 0, slot) != 0) {
        D_800CC2D0[slot].unk94 |= 0x40;
        D_800CC2D0[slot].unk94 &= ~0x200;
    }
    if (func_1503EF4C(2, 1, slot) != 0) {
        D_800CC2D0[slot].unk94 |= 0x80;
        D_800CC2D0[slot].unk94 &= ~0x100;
    }
    if (func_1503EF4C(2, 2, slot) != 0) {
        D_800CC2D0[slot].unk94 &= ~0x400;
    }
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'truthy', BASE.replace(' != 0','')
    yield 'unsigned-flags', BASE.replace('D_800CC2D0[slot].unk94','((u32 *)&D_800CC2D0[slot])[37]')
    yield 'local-actor', BASE.replace('    *(s16 *)','    struct127 *actor;\n\n    *(s16 *)',1).replace(
        ' != 0) {',' != 0) {\n        actor = &D_800CC2D0[slot];').replace('D_800CC2D0[slot].unk94','actor->unk94')
    yield 'control-timer', BASE.replace('*(s16 *)(D_800C666C + slot * 0x10)','*(s16 *)((u8 *)&D_800C6660[slot] + 12)')
    yield 'halfword-array', BASE.replace('*(s16 *)(D_800C666C + slot * 0x10)','((s16 *)D_800C666C)[slot * 8]')
    yield 'shifted-timer', BASE.replace('slot * 0x10','slot << 4')


def compile_candidate(root,out,name,body=SELECTED,profile='owner'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(source):
    assert source.count(ORIGINAL)==1 and SELECTED not in source
    assert LOCAL_DECLARATION.rstrip() not in source
    return source.replace(ORIGINAL,SELECTED).replace('#include "variables.h"\n',
        '#include "variables.h"\n'+LOCAL_DECLARATION,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]; out=root/'conker/build/game-record-mask-finish'
    records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner','compact','o1g3','o1') if args.profiles else ('owner',)):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta); print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
