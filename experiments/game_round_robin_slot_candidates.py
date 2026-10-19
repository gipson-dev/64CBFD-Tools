"""Recover signed-byte round-robin slot selection without a helper call."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_packed_row_dispatch_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-round-robin-slot'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508C9CC',0x1508C9CC,0xB9E7C,47
ORIGINAL='s32 func_1508C9CC() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'683e47b76b3db771b532b1959ad0e9f642b29b013d87777026020d62b38065c7',
    'conker/retail_word_patches.us.csv':'3126566e693decebd75d4ad1c088626c63ec19de18d3f3572882f4c830e70fd1',
    'conker/build/conker.us.elf':'da178d6b0ea5c11261fce0de32475e3b13287696034b80e2d10d592ee721dcc9'})
DECLARATIONS='''extern s32 D_800D23B0;
extern s8 D_8008FD8C;
extern u16 D_800D18A0;
extern u8 D_800CC2D0[];
'''
INITIAL='''/* Advance the signed slot cursor to the next eligible, unmasked actor. */
s32 func_1508C9CC(void) {
    u8 *state = (u8 *)D_800D23B0;
    s32 attempts = 0;
    s32 selected = -1;
    s32 count = D_8008FD8C;
    s32 slot;
    u8 *actor;
    u8 *nested;

    for (slot = *(s8 *)(state + 0x1702) + 1; ; slot++) {
        slot = (s8)slot;
        if (slot >= count) {
            slot = 0;
        }
        actor = D_800CC2D0 + slot * 0x32C;
        if (*(s32 *)actor != 0) {
            nested = *(u8 **)(actor + 0x31C);
            if (nested != 0 && nested[0x84] != 0 && !(D_800D18A0 & (1U << (slot & 31)))) {
                attempts = count;
                selected = slot;
            }
        }
        attempts++;
        if (attempts >= count) {
            break;
        }
    }
    *(s8 *)(state + 0x1702) = slot;
    return selected;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown round-robin predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(FITTED if body is None else body).rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>47I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    yield 'signed-shift',INITIAL.replace('1U << (slot & 31)','1 << slot')
    yield 'unsigned-shift',INITIAL.replace('1U << (slot & 31)','1U << slot')
    yield 'count-before-result',INITIAL.replace('    s32 selected = -1;\n    s32 count = D_8008FD8C;',
        '    s32 count = D_8008FD8C;\n    s32 selected = -1;')
    for label,body in (('masked',INITIAL),('shift',INITIAL.replace('1U << (slot & 31)','1U << slot'))):
        yield label+'-byte-slot',body.replace('    s32 slot;','    s8 slot;').replace('        slot = (s8)slot;\n','')
        yield label+'-do',body.replace('    for (slot = *(s8 *)(state + 0x1702) + 1; ; slot++) {\n        slot = (s8)slot;',
            '    slot = *(s8 *)(state + 0x1702);\n    do {\n        slot = (s8)(slot + 1);').replace(
            '        if (attempts >= count) {\n            break;\n        }\n    }','    } while (attempts < count);')


def declaration_candidates():
    body=dict(candidates())['shift-do']
    declarations=('    u8 *state = (u8 *)D_800D23B0;\n','    s32 attempts = 0;\n',
        '    s32 selected = -1;\n','    s32 count = D_8008FD8C;\n')
    old=''.join(declarations)
    for n,order in enumerate(itertools.permutations(declarations)):
        yield 'declarations-%02d'%n,body.replace(old,''.join(order))


def role_candidates():
    base=dict(declaration_candidates())['declarations-09']
    declarations=('    s32 attempts = 0;\n','    s32 selected = -1;\n',
        '    s32 count = D_8008FD8C;\n','    u8 *state = (u8 *)D_800D23B0;\n')
    old=''.join(declarations)+'    s32 slot;\n'
    for position in range(5):
        order=list(declarations);order.insert(position,'    s32 slot;\n')
        body=base.replace(old,''.join(order))
        yield 'slot-order-%d'%position,body
        yield 'slot-register-%d'%position,body.replace('    s32 slot;','    register s32 slot;')
        yield 'byte-count-%d'%position,body.replace('    s32 count =','    s8 count =')
    merged=base.replace('    s32 count = D_8008FD8C;\n','').replace(
        '    s32 slot;','    s32 slot = *(s8 *)(state + 0x1702);\n    s32 count = D_8008FD8C;').replace(
        '    slot = *(s8 *)(state + 0x1702);\n','')
    yield 'merged-cursor',merged
    yield 'merged-cursor-byte-count',merged.replace('    s32 count =','    s8 count =')
    yield 'merged-cursor-selected-last',merged.replace('    s32 selected = -1;\n','').replace(
        '    s32 count = D_8008FD8C;','    s32 count = D_8008FD8C;\n    s32 selected = -1;')


FITTED=dict(role_candidates())['merged-cursor-selected-last']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--declarations',action='store_true');parser.add_argument('--roles',action='store_true')
    parser.add_argument('--filter',default='');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (role_candidates() if args.roles else declaration_candidates() if args.declarations else candidates() if args.screens else [('selected',FITTED)]):
        if args.filter not in name:continue
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
