"""Recover first-free route slot reservation and its actor association."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_record_copy_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-route-slot-reservation'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508868C',0x1508868C,0xB5B3C,61
SOURCE=previous.SOURCE
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_B3020/func_1508868C.s")'
INPUTS=dict(previous.INPUTS)
INPUTS[SOURCE]='30e5e821869754c8aa1e6d734cd85c842cadb9e22576de1ed79db559820a20dd'
INPUTS['conker/asm/nonmatchings/generated_B3020/func_1508868C.s']='4dd68e203f15f82856252b42d1ed7fafbf970848ead3a177b07987aed75a0329'
DECLARATIONS='''extern u8 *D_800872A0;
extern s8 D_800D2399;
extern s8 D_800D2398;
extern s32 D_800D2394;
extern u8 D_800CC2D0[];
void func_15088824(u8 *);
'''
INITIAL='''/* Reserve the first free route slot and associate it with the actor. */
s32 func_1508868C(u8 *actor) {
    s32 recordIndex;
    u32 bit;
    u8 *table;

    table = D_800872A0;
    if (table == 0) {
        return -1;
    }
    bit = 1;
    for (recordIndex = 0; recordIndex < D_800D2399; recordIndex++, bit <<= 1) {
        if (((u32)D_800D2394 & bit) == 0) {
            recordIndex += D_800D2398;
            D_800D2394 |= bit;
            func_15088824((u8 *)((u32)recordIndex * 0x84 + (u32)table));
            D_800872A0[(u32)recordIndex * 0x84 + 0x30] = 1;
            D_800872A0[(u32)recordIndex * 0x84 + 0x31] =
                (s32)((u32)actor - (u32)D_800CC2D0) / 0x32C;
            return recordIndex;
        }
    }
    return -1;
}
'''
SELECTED=INITIAL.replace('            recordIndex += D_800D2398;\n            D_800D2394 |= bit;',
    '            D_800D2394 |= bit;\n            recordIndex += D_800D2398;').replace(
    'D_800872A0[(u32)recordIndex * 0x84 + 0x30]',
    '((u8 *)((u32)D_800872A0 + (u32)recordIndex * 0x84))[0x30]').replace(
    'D_800872A0[(u32)recordIndex * 0x84 + 0x31]',
    '((u8 *)((u32)D_800872A0 + (u32)recordIndex * 0x84))[0x31]')


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown slot-reservation assembly predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='selected',body=SELECTED,whole=False,normal=False):
    values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+'\n'+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal)
    image,functions=link_owner(root,out,obj,OWNER);raw,bindings=payload(obj);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>61I',values['conker/conker.us.bin'],ROM)
    row=dict(name=name,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        diagnostics=diagnostics,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--whole',action='store_true')
    parser.add_argument('--normal',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(compile_candidate(root,root/BUILD,whole=args.whole,normal=args.normal)[2],indent=2))
