"""Fit meaningful value lifetimes without padding or changing the transfer algorithm."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_slot_state_transfer_candidates as source

BUILD=source.BUILD+'/value-homes'


def replace_once(body,old,new):
    if body.count(old)!=1:raise ValueError('Unknown source fragment: '+old)
    return body.replace(old,new,1)


def candidates():
    base=source.FITTED
    yield 'baseline',base
    active=replace_once(base,'    s32 actorIndex;','    u32 activeBits;\n    s32 actorIndex;')
    active=replace_once(active,'        D_800D18A0 &= inverseDestination;',
        '        activeBits = D_800D18A0 & inverseDestination;\n        D_800D18A0 = activeBits;')
    active=replace_once(active,'        D_800D18A0 |= sourceBit;',
        '        D_800D18A0 = activeBits | sourceBit;')
    loaded=replace_once(active,'        activeBits = D_800D18A0 & inverseDestination;',
        '        activeBits = D_800D18A0;\n        activeBits &= inverseDestination;')
    flags=replace_once(base,'    s32 actorIndex;','    s32 tableFlags;\n    s32 actorIndex;')
    flags=replace_once(flags,'        if (*(s32 *)((u8 *)D_800D23B0 + 0x18) != 0) {',
        '        tableFlags = *(s32 *)((u8 *)D_800D23B0 + 0x18);\n        if (tableFlags != 0) {')
    flags=replace_once(flags,'            *(s32 *)((u8 *)D_800D23B0 + 0x18) &= inverseDestination;',
        '            *(s32 *)((u8 *)D_800D23B0 + 0x18) = tableFlags & inverseDestination;')
    for label,body in (('active',active),('loaded-active',loaded),('table-flags',flags)):
        yield label,body
        yield label+'-last',replace_once(replace_once(body,
            '    '+('s32 tableFlags;' if label=='table-flags' else 'u32 activeBits;')+'\n',''),
            '    u32 inverseDestination;',
            '    u32 inverseDestination;\n    '+('s32 tableFlags;' if label=='table-flags' else 'u32 activeBits;'))
    both=replace_once(active,'    s32 actorIndex;','    s32 tableFlags;\n    s32 actorIndex;')
    both=replace_once(both,'        if (*(s32 *)((u8 *)D_800D23B0 + 0x18) != 0) {',
        '        tableFlags = *(s32 *)((u8 *)D_800D23B0 + 0x18);\n        if (tableFlags != 0) {')
    both=replace_once(both,'            *(s32 *)((u8 *)D_800D23B0 + 0x18) &= inverseDestination;',
        '            *(s32 *)((u8 *)D_800D23B0 + 0x18) = tableFlags & inverseDestination;')
    yield 'both',both
    for label,body in (('baseline',base),('active',active),('table-flags',flags),('both',both)):
        score=replace_once(body,'    s32 actorIndex;','    s32 score;\n    s32 actorIndex;')
        score=replace_once(score,'        func_15085710((s16)destinationSlot, 2, func_150859AC((s16)sourceSlot, 3));',
            '        score = func_150859AC((s16)sourceSlot, 3);\n        func_15085710((s16)destinationSlot, 2, score);')
        yield label+'-score',score


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--filter',default='')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD
    for name,body in candidates():
        if args.filter not in name:continue
        _,_,row=source.compile_candidate(root,out,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)


if __name__=='__main__':main()
