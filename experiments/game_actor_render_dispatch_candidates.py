"""Recover the complete five-argument actor renderer dispatch and cursor limit."""
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502C974,0x59E24,176
FUNCTION,SOURCE='func_1502C974','conker/src/game/generated_58F80.c'
ORIGINAL='Gfx *func_1502C974() {\n    return 0;\n}'
RECORD=''
DECLARATIONS='''extern u8 D_800CC2D0[],D_800C3638,D_800C3656,D_800DF7C4,D_800BE9C0;
extern u8 *D_800B0DF0,*D_800DF7C0;
extern Gfx *D_800BE9C8[];
extern s32 D_800BEBA4;
s32 func_150229E4(u8 *);
s32 func_1506196C(u8 *,s32);
void func_1502C6E8(s32,s16,s32);
s32 func_150849CC(u8 *,s32 *);
void func_1502D54C(s32,s32 *);
void func_1502D630(u8 *,s32 *,s32);
Gfx *func_1502CCFC(Gfx *,s32,s32,u8 *,s32,s32 *,s32,s32);
'''
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,D_800C3638=0x800C3638,D_800C3656=0x800C3656,
    D_800DF7C4=0x800DF7C4,D_800BE9C0=0x800BE9C0,D_800B0DF0=0x800B0DF0,
    D_800DF7C0=0x800DF7C0,D_800BE9C8=0x800BE9C8,D_800BEBA4=0x800BEBA4,
    func_150229E4=0x150229E4,func_1506196C=0x1506196C,func_1502C6E8=0x1502C6E8,
    func_150849CC=0x150849CC,func_1502D54C=0x1502D54C,func_1502D630=0x1502D630,
    func_1502CCFC=0x1502CCFC)
SELECTED='''Gfx *func_1502C974(Gfx *commands, s32 slot, s32 view, s32 mode, s32 extra) {
    Gfx *original;
    u8 *actor;
    u8 *matrix;
    s32 parameters[4];
    s32 tier;
    s32 alpha;

    original = commands;
    if (D_800C3638 != 0 && D_800C3656 == 0) {
        if (func_150229E4((u8 *)D_800CC2D0 + (u32)slot * 0x32C) == 0) {
            return commands;
        }
    }
    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
    if ((actor[0x74] & (1U << (view & 31))) == (1U << (view & 31))) {
        return commands;
    }
    if (func_1506196C(actor, view) == 0) {
        return commands;
    }
    if (*(u8 **)(actor + 0x1D4) == NULL) {
        return commands;
    }
    if (mode != 4 && mode != 5 && mode != 3) {
        func_1502C6E8(slot, (s16)view, mode);
        tier = actor[0x1C8];
    } else {
        func_150849CC(actor, &tier);
    }
    func_1502D54C(slot, parameters);
    if (*(s16 *)(D_800B0DF0 + 0x3E) != 0) {
        func_1502D630(actor, parameters, view);
    } else {
        parameters[3] = 255;
    }
    alpha = func_1506196C(actor, view);
    if (alpha < 255) {
        u8 *owner = *(u8 **)(actor + 0x318);
        if (owner != NULL && *(s32 *)(owner + 0x2C) == 0x100 && view != actor[0x127]) {
            alpha = 255;
        }
    }
    if (mode == 4) {
        matrix = D_800DF7C0;
        alpha = (s32)((u32)D_800DF7C4 * (u32)alpha) >> 8;
    } else {
        matrix = *(u8 **)(actor + 0x1D4);
    }
    commands = func_1502CCFC(commands, slot, view, matrix, alpha, parameters, mode, extra);
    if (D_800BEBA4 < ((s32)((u32)commands - (u32)D_800BE9C8[D_800BE9C0]) >> 3)) {
        return original;
    }
    return commands;
}'''


def candidates():
    yield 'selected',SELECTED
    for index,order in enumerate(itertools.permutations(('u8 *actor;','u8 *matrix;',
            's32 parameters[4];','s32 tier;'))):
        block='    Gfx *original;\n'+'\n'.join('    '+line for line in order)+'\n    s32 alpha;'
        before='\n'.join('    '+line for line in (
            'Gfx *original;','u8 *actor;','u8 *matrix;','s32 parameters[4];','s32 tier;','s32 alpha;'))
        yield 'order-%02d'%index,SELECTED.replace(before,block)
    for name,old,new in (
            ('register-actor','u8 *actor;','register u8 *actor;'),
            ('volatile-actor','u8 *actor;','u8 *volatile actor;'),
            ('register-alpha','s32 alpha;','register s32 alpha;'),
            ('volatile-original','Gfx *original;','Gfx *volatile original;'),
            ('signed-slot','(u32)slot * 0x32C','slot * 0x32C'),
            ('unmasked-shift','(view & 31)','view'),
            ('volatile-mode','s32 mode, s32 extra','volatile s32 mode, s32 extra'),
            ('volatile-view','s32 view, s32 mode','volatile s32 view, s32 mode'),
            ('volatile-slot','s32 slot, s32 view','volatile s32 slot, s32 view'),
            ('cursor-assignment','return original;','commands = original;')):
        yield name,SELECTED.replace(old,new)
    for name,old,new in (
            ('negative-zero-alpha','func_1506196C(actor, view) == 0','func_1506196C(actor, view) != 0'),
            ('negative-inverted-mask','== (1U << (view & 31))','!= (1U << (view & 31))'),
            ('negative-one-alpha','alpha = func_1506196C(actor, view);','alpha = 255;'),
            ('negative-unsigned-alpha','if (alpha < 255)','if ((u32)alpha < 255)'),
            ('negative-divide-product','(s32)((u32)D_800DF7C4 * (u32)alpha) >> 8',
                '(s32)((u32)D_800DF7C4 * (u32)alpha) / 256'),
            ('negative-inclusive-limit','D_800BEBA4 <','D_800BEBA4 <='),
            ('negative-wrong-rollback','return original;','return commands;')):
        yield name,SELECTED.replace(old,new)


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word>>16==0x27BD and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-render-dispatch'
    records=[]
    for profile in compiler.PROFILES:
        meta,_=compile_candidate(root,out,'selected-'+profile,profile=profile)
        records.append(meta)
        print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    for name,body in candidates():
        if name=='selected' or name.startswith('negative-'): continue
        meta,_=compile_candidate(root,out,name,body)
        records.append(meta)
        print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
