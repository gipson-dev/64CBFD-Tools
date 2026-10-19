"""Recover the complete route event dispatcher in private compiler fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_actor_event_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-route-event-dispatch'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_B3020', 'func_150880F8', 0x150880F8, 0xB55A8, 53
SOURCE = previous.SOURCE
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_B3020/func_150880F8.s")'
INPUTS = dict(previous.INPUTS)
INPUTS[SOURCE] = '7404fc38e06fd103a24b15df10d4b3b2ee014dbb586f36d0d0cfcd60191d3d75'
INPUTS['conker/asm/nonmatchings/generated_B3020/func_150880F8.s'] = '458a28abcd34caa2d5b2a2d81eef68e3f5b3dbe04b504552ee2507053e10185a'
DECLARATIONS = '''extern u8 *D_800872A0;
extern u8 D_800CC2D0[];
extern s8 D_800D239A;
s32 func_1508802C(u8 *, u8 *, s32);
'''
INITIAL = '''/* Dispatch a route actor's event state and stamp its sequence counter. */
s32 func_150880F8(s32 recordIndex, s32 reason) {
    u8 *table;
    u8 *record;
    u8 *actor;
    s32 result;
    s8 state;

    result = 0;
    table = D_800872A0;
    if (table == 0) {
        return 0;
    }
    record = (u8 *)((u32)table + (u32)recordIndex * 0x84);
    actor = (u8 *)((u32)D_800CC2D0 + (s32)*(s8 *)(record + 0x31) * 0x32C);
    state = *(s8 *)(record + 0x30);
    if (state == 0) {
        result = func_1508802C(record, actor, reason);
    } else if (state == 1) {
        record[0x30] = 2;
        actor[0x125] = 0xFF;
    }
    record[0x2A] = D_800D239A;
    D_800D239A++;
    return result;
}
'''
SELECTED = INITIAL.replace('    u8 *table;\n','').replace('    s8 state;\n','').replace(
    '    table = D_800872A0;\n','').replace('if (table == 0)','if (D_800872A0 == 0)').replace(
    '(u32)table + (u32)recordIndex * 0x84','(u32)recordIndex * 0x84 + (u32)D_800872A0').replace(
    '    state = *(s8 *)(record + 0x30);\n','').replace('state ==','*(s8 *)(record + 0x30) ==')


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):
        return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:
        raise ValueError('Unknown route-dispatch assembly predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body.rstrip())


def payload(obj):
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):
        raise ValueError('Nonzero dispatch alignment tail')
    return raw[:end*4],{at-f['value']:entries for at,entries in relocations.items()
        if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=SELECTED,whole=False,normal=False):
    values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+'\n'+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal)
    image,functions=link_owner(root,out,obj,OWNER)
    raw,bindings=payload(obj)
    at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>53I',values['conker/conker.us.bin'],ROM)
    row=dict(name=name,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        diagnostics=diagnostics,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def candidates():
    no_table=INITIAL.replace('    u8 *table;\n','').replace('    table = D_800872A0;',
        '    record = D_800872A0;').replace('if (table == 0)','if (record == 0)').replace(
        '(u32)table + (u32)recordIndex * 0x84','(u32)recordIndex * 0x84 + (u32)record')
    for name,body in (('initial',INITIAL),('record-table-lifetime',no_table)):
        yield name,body
        yield name+'-direct-state',body.replace('    s8 state;\n','').replace(
            '    state = *(s8 *)(record + 0x30);\n','').replace(
            'state ==','*(s8 *)(record + 0x30) ==')
    direct=no_table.replace('    u8 *actor;\n','').replace('    s8 state;\n','').replace(
        '    state = *(s8 *)(record + 0x30);\n','').replace('state ==','*(s8 *)(record + 0x30) ==')
    reuse=direct.replace('    actor = (u8 *)','    recordIndex = (s32)').replace(
        'func_1508802C(record, actor, reason)','func_1508802C(record, (u8 *)recordIndex, reason)').replace(
        'actor[0x125]','((u8 *)recordIndex)[0x125]')
    yield 'consumed-index-actor-address',reuse
    address='(u8 *)((u32)D_800CC2D0 + (s32)*(s8 *)(record + 0x31) * 0x32C)'
    inline=direct.replace('    actor = '+address+';\n','').replace(
        'func_1508802C(record, actor, reason)','func_1508802C(record, '+address+', reason)').replace(
        'actor[0x125]','('+address+')[0x125]')
    yield 'branch-local-actor-address',inline
    direct_global=SELECTED
    yield 'direct-global-table',direct_global
    yield 'direct-global-base-first',direct_global.replace(
        '(u32)recordIndex * 0x84 + (u32)D_800872A0','(u32)D_800872A0 + (u32)recordIndex * 0x84')
    yield 'actor-table-lifetime',direct_global.replace('    if (D_800872A0 == 0)',
        '    actor = D_800872A0;\n    if (actor == 0)').replace(
        '(u32)recordIndex * 0x84 + (u32)D_800872A0','(u32)recordIndex * 0x84 + (u32)actor')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--whole',action='store_true')
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        if args.filter and args.filter not in name:
            continue
        row=compile_candidate(root,root/BUILD,name,body,whole=args.whole)[2]
        print(json.dumps(row,indent=2) if not args.screens else
            json.dumps({key:row[key] for key in ('name','words','frame','differences','raw_SHA256')}),flush=True)
