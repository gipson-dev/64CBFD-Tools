"""Recover first packed-row typed dispatch, helper reloads and final clear."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_packed_peer_lookup_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-packed-row-dispatch'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508EE0C',0x1508EE0C,0xBC2BC,91
SLOT_WORDS=93
ORIGINAL='s32 func_1508EE0C() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'9847b3641891ec5035d87f0bf0c96568bc649abb6ed9911fb3786a584ae959d7',
    'conker/retail_word_patches.us.csv':'5c1e9119eed376d6ed986bfbe8c332cec79b259a6cbdbe23db3b1bb4d4517c4c',
    'conker/build/conker.us.elf':'5261c62f0c48dda8fb5a94ab56b8d275bf27ade0a8e1e87bae72010597aa4050',
    'conker/asm/142560.s':'ca734f7ffd435f954360ac879e7762e8adbb56cc72ce60eadebcac3030d1121f',
    'conker/asm/EC420.s':'aef6386a693d547bbe86b49a5801307ba533103ccced9effa7c4953c50eb44f3',
    'conker/asm/13D350.s':'aae655875cae186bc7377f14463dc61e80cb55f511b1931a0ed03d1308333a2c',
    'conker/asm/6B280.s':'0e2de440ccb069c1bb74ffccce9b1dd1ac8030e03549d70783e3f0c727c374d5',
    'conker/src/game/generated_6B280.c':'6e8d6eeb31c3da74f40a3a6c59506fdc6e7e9452cb7a0a0f7ff02c5382227022'})
DECLARATIONS='''extern u8 *D_800D23C0;
extern u32 D_80087380;
void func_15114B94(s32);
void func_1503DDD0(s32);
void func_1508EDBC(u32);
'''
ROW_TYPE='typedef struct { u16 unk0; u16 count; u32 unk4; u16 entries[8]; } PackedPeerRow;\n'
INITIAL='''/* Dispatch typed entries in the first matching packed row, then clear it. */
void func_1508EE0C(u16 group, u16 value) {
    u32 rowIndex;
    u32 entryIndex;
    u32 dispatchIndex;
    u16 key;
    u16 packed;

    for (rowIndex = 0; rowIndex < D_80087380; rowIndex++) {
        for (entryIndex = 0; entryIndex < ((PackedPeerRow *)D_800D23C0)[rowIndex].count; entryIndex++) {
            key = (group << 12) + value;
            if (((PackedPeerRow *)D_800D23C0)[rowIndex].entries[entryIndex] == key) {
                for (dispatchIndex = 0; dispatchIndex < ((PackedPeerRow *)D_800D23C0)[rowIndex].count; dispatchIndex++) {
                    packed = ((PackedPeerRow *)D_800D23C0)[rowIndex].entries[dispatchIndex];
                    if ((packed >> 12) == 2) {
                        func_15114B94(packed & 0xFFF);
                    } else if ((packed >> 12) == 3) {
                        func_1503DDD0(packed & 0xFFF);
                    }
                }
                func_1508EDBC(rowIndex);
                return;
            }
        }
    }
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    body=FITTED if body is None else body
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown packed-row dispatcher predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+ROW_TYPE+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>91I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    reused=INITIAL.replace('    u32 dispatchIndex;\n','').replace('dispatchIndex','entryIndex')
    yield 'reused-index',reused
    for label,body in (('initial',INITIAL),('reused',reused)):
        switched=body.replace('                    if ((packed >> 12) == 2) {',
            '                    switch (packed >> 12) {\n                        case 2:').replace(
            '                    } else if ((packed >> 12) == 3) {','                            break;\n                        case 3:').replace(
            '                        func_1503DDD0(packed & 0xFFF);\n                    }',
            '                        func_1503DDD0(packed & 0xFFF);\n                            break;\n                    }')
        yield label+'-switch',switched
        yield label+'-signed-packed',body.replace('    u16 packed;','    s32 packed;')
        raw=body.replace('((PackedPeerRow *)D_800D23C0)[rowIndex].count',
            '*(u16 *)(D_800D23C0 + rowIndex * 24 + 2)').replace(
            '((PackedPeerRow *)D_800D23C0)[rowIndex].entries',
            '((u16 *)(D_800D23C0 + rowIndex * 24 + 8))')
        yield label+'-byte-views',raw
        if label=='reused':switched_base=switched
    for kind_type in ('u16','s32'):
        code=switched_base.replace('    u16 packed;','    u16 packed;\n    '+kind_type+' code;').replace(
            '                    switch (packed >> 12)',
            '                    code = packed & 0xFFF;\n                    switch (packed >> 12)').replace(
            'func_15114B94(packed & 0xFFF);','func_15114B94(code);').replace(
            'func_1503DDD0(packed & 0xFFF);','func_1503DDD0(code);')
        yield 'shared-code-'+kind_type,code
        yield 'shared-code-'+kind_type+'-key-first',code.replace(
            'if (((PackedPeerRow *)D_800D23C0)[rowIndex].entries[entryIndex] == key)',
            'if (key == ((PackedPeerRow *)D_800D23C0)[rowIndex].entries[entryIndex])')
    yield 'reused-switch-key-first',switched_base.replace(
        'if (((PackedPeerRow *)D_800D23C0)[rowIndex].entries[entryIndex] == key)',
        'if (key == ((PackedPeerRow *)D_800D23C0)[rowIndex].entries[entryIndex])')
    yield 'switch-signed-packed',switched_base.replace('    u16 packed;','    s32 packed;')
    for label,definition in (('value','value'),('new-code','code')):
        body=switched_base.replace('    u16 packed;','    s32 packed;'+('\n    s32 code;' if label=='new-code' else ''))
        body=body.replace('                    switch (packed >> 12)',
            '                    '+definition+' = packed & 0xFFF;\n                    switch (packed >> 12)').replace(
            'func_15114B94(packed & 0xFFF);','func_15114B94('+definition+');').replace(
            'func_1503DDD0(packed & 0xFFF);','func_1503DDD0('+definition+');')
        yield 'switch-signed-packed-'+label,body


FITTED=next(body for name,body in candidates() if name=='reused-switch').replace(
    '                        func_', '                            func_')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='');args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in (candidates() if args.screens else [('selected',FITTED)]):
        if args.filter not in name:continue
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
