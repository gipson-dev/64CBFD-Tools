"""Recover slot-query/release paths and ordered actor-coordinate capture."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_parallel_array_reset_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-record-release'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508DAEC',0x1508DAEC,0xBAF9C,78
ORIGINAL='s32 func_1508DAEC() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'3bd649eeedd4e6bf5fe3fed8de0f2e6446cacfe5155bce52f3e54b5e97c31791',
    'conker/retail_word_patches.us.csv':'0cca1083e8dc92310a3b170d9774cb7a2f7c5d07bbbe6528f4e0550067813333',
    'conker/build/conker.us.elf':'6777c5ec8ffd50a7e30a4e1c80fe44ef40de9ce4e177c5208c7d0886907cb995',
    'conker/asm/11A680.s':'54a63a8903fd59c8b04b3fcb671926dfac0ba82a81b953280d5311092ee4a94c'})
DECLARATIONS='extern s32 D_800D23B0;\nextern u8 D_800CC2D0[];\n'
INITIAL='''/* Query or release a selected record, optionally capturing actor position. */
s32 func_1508DAEC(s32 slot, s32 mode) {
    s32 record;
    s32 nextState;
    u8 *actor;

    if (D_800D23B0 == 0) {
        return 0;
    }
    record = *(s32 *)((u8 *)D_800D23B0 + slot * 4 + 0xEB0);
    if (record < 0) {
        return 0;
    }
    if (mode < 0) {
        return 1;
    }
    *(s32 *)((u8 *)D_800D23B0 + slot * 4 + 0xEB0) = -1;
    if (*(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4) & 2) {
        return 0;
    }
    *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0xF70) = -1;
    *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x10F0) = -1;
    nextState = *(s32 *)((u8 *)D_800D23B0 + 0xEAC);
    if (mode == 1) {
        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x12F4) = 300;
        actor = D_800CC2D0 + slot * 0x32C;
        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1374) = (s32)*(f32 *)(actor + 0x14);
        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x13F4) = (s32)(*(f32 *)(actor + 0x18) + 50.0f);
        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1474) = (s32)*(f32 *)(actor + 0x1C);
        nextState = 4;
    }
    *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1070) = nextState;
    return 0;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown record-release predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(FITTED if body is None else body).rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>78I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    yield 'unsigned-slot',INITIAL.replace('(s32 slot,','(u32 slot,')
    yield 'actor-before-timer',INITIAL.replace(
        '        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x12F4) = 300;\n        actor = D_800CC2D0 + slot * 0x32C;',
        '        actor = D_800CC2D0 + slot * 0x32C;\n        *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x12F4) = 300;')
    yield 'mode-reuse',INITIAL.replace('    s32 nextState;','    s32 inputMode = mode;').replace(
        'if (mode < 0)','if (inputMode < 0)').replace('if (mode == 1)','if (inputMode == 1)').replace('nextState','mode')
    yield 'unsigned-offsets',INITIAL.replace('    s32 nextState;','    s32 nextState;\n    u32 slotOffset = slot * 4;\n    u32 recordOffset;').replace(
        'slot * 4 +','slotOffset +').replace('    if (record < 0)',
        '    recordOffset = record * 4;\n    if (record < 0)').replace('record * 4 +','recordOffset +')
    yield 'record-first',INITIAL.replace('    s32 record;\n    s32 nextState;','    s32 nextState;\n    s32 record;')


def fitting_candidates():
    for label,record,flag in (('goto-record',True,False),('goto-flag',False,True),('goto-both',True,True)):
        body=INITIAL
        if record:body=body.replace('    if (record < 0) {\n        return 0;','    if (record < 0) {\n        goto return_zero;')
        if flag:body=body.replace('0x11F4) & 2) {\n        return 0;','0x11F4) & 2) {\n        goto return_zero;')
        body=body.removesuffix('    return 0;\n}\n')+'return_zero:\n    return 0;\n}\n'
        yield label,body
    nested=INITIAL.replace('    if (record < 0) {\n        return 0;\n    }','    if (record >= 0) {')
    nested=nested.removesuffix('    return 0;\n}\n')+'    }\n    return 0;\n}\n'
    yield 'nested-record',nested
    nested=nested.replace('    if (*(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4) & 2) {\n        return 0;\n    }',
        '    if (!(*(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4) & 2)) {')
    nested=nested.removesuffix('    }\n    return 0;\n}\n')+'    }\n    }\n    return 0;\n}\n'
    yield 'nested-both',nested


def allocation_candidates():
    base=dict(fitting_candidates())['goto-both']
    declarations=('    s32 record;\n','    s32 nextState;\n','    u8 *actor;\n')
    for n,order in enumerate(itertools.permutations(declarations)):
        yield 'declarations-%d'%n,base.replace(''.join(declarations),''.join(order))
    reuse=base.replace('    s32 nextState;','    s32 inputMode = mode;').replace(
        'if (mode < 0)','if (inputMode < 0)').replace('if (mode == 1)','if (inputMode == 1)').replace('nextState','mode')
    yield 'formal-reuse',reuse
    yield 'formal-reuse-record-last',reuse.replace('    s32 record;\n','').replace('    u8 *actor;','    u8 *actor;\n    s32 record;')
    yield 'actor-register',base.replace('    u8 *actor;','    register u8 *actor;')
    yield 'state-register',base.replace('    s32 nextState;','    register s32 nextState;')


FITTED='''/* Query or release a selected record, optionally capturing actor position. */
s32 func_1508DAEC(s32 slot, s32 mode) {
    s32 record;
    s32 nextState;
    u8 *actor;

    if (D_800D23B0 == 0) {
        return 0;
    }
    record = *(s32 *)((u8 *)D_800D23B0 + slot * 4 + 0xEB0);
    if (record >= 0) {
        if (mode < 0) {
            return 1;
        }
        *(s32 *)((u8 *)D_800D23B0 + slot * 4 + 0xEB0) = -1;
        if (!(*(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4) & 2)) {
            *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0xF70) = -1;
            *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x10F0) = -1;
            nextState = *(s32 *)((u8 *)D_800D23B0 + 0xEAC);
            if (mode == 1) {
                *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x12F4) = 300;
                actor = D_800CC2D0 + slot * 0x32C;
                *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1374) = (s32)*(f32 *)(actor + 0x14);
                *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x13F4) = (s32)(*(f32 *)(actor + 0x18) + 50.0f);
                *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1474) = (s32)*(f32 *)(actor + 0x1C);
                nextState = 4;
            }
            *(s32 *)((u8 *)D_800D23B0 + record * 4 + 0x1070) = nextState;
        }
    }
    return 0;
}
'''


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='');parser.add_argument('--fitting',action='store_true')
    parser.add_argument('--allocation',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (allocation_candidates() if args.allocation else fitting_candidates() if args.fitting else candidates() if args.screens else [('selected',FITTED)]):
        if args.filter not in name:continue
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
