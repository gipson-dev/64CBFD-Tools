"""Screen real array/address lifetimes; no production or ABI decision."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_target_timer_candidates as source

BUILD=source.BUILD+'/pointer-fit'


def forms():
    base=source.RESEARCH_PARTIAL
    shared=base.replace('    s32 *targets =','    s32 slotOffset = slot * 4;\n    s32 *targets =').replace(
        'targets[slot]','*(s32 *)((u8 *)targets + slotOffset)').replace(
        '    timer = timers + slot;','    timer = (s32 *)((u8 *)timers + slotOffset);').replace(
        '+ slot * 4 + 0x16C0','+ slotOffset + 0x16C0')
    target=shared.replace('    s32 *targets = (s32 *)((u8 *)D_800D23B0 + 0x11C);',
        '    s32 *targetSlot = (s32 *)((u8 *)D_800D23B0 + 0x11C + slotOffset);').replace(
        '*(s32 *)((u8 *)targets + slotOffset)','*targetSlot')
    for label,body in (('base',base),('shared',shared),('target',target)):
        yield label,body,source.DECLARATIONS
        two=body.replace('D_80087320[D_800E0BD0 * 3 + distanceClass]',
            'D_80087320[D_800E0BD0][distanceClass]')
        yield label+'-2D',two,source.DECLARATIONS.replace('D_80087320[]','D_80087320[][3]')
    for label,body in (('shared',shared),('target',target)):
        table=body.replace('    s32 *targets =','    s16 *thresholds = D_80087320;\n    s32 *targets =') if label=='shared' else body.replace(
            '    s32 *targetSlot =','    s16 *thresholds = D_80087320;\n    s32 *targetSlot =')
        table=table.replace('D_80087320[D_800E0BD0 * 3 + distanceClass]','thresholds[D_800E0BD0 * 3 + distanceClass]')
        yield label+'-threshold-base',table,source.DECLARATIONS
        actor=body.replace('    s32 slotOffset =','    u8 *actors = D_800CC2D0;\n    s32 slotOffset =').replace(
            'D_800CC2D0 + slot','actors + slot').replace('D_800CC2D0 + target','actors + target')
        yield label+'-actor-base',actor,source.DECLARATIONS
    for label,body in (('base',base),('target',target)):
        expression='D_80087320[D_800E0BD0 * 3 + distanceClass]'
        for form,replacement in (
            ('byte-threshold','*(s16 *)((u8 *)D_80087320 + D_800E0BD0 * 6 + distanceClass * 2)'),
            ('pointer-threshold','*(D_80087320 + D_800E0BD0 * 3 + distanceClass)')):
            yield label+'-'+form,body.replace(expression,replacement),source.DECLARATIONS
    mask='(0x10000U << targets[slot]) & *(u32 *)((u8 *)D_800D23B0 + slot * 4 + 0x16C0)'
    swapped='*(u32 *)((u8 *)D_800D23B0 + slot * 4 + 0x16C0) & (0x10000U << targets[slot])'
    yield 'base-mask-first',base.replace(mask,swapped),source.DECLARATIONS
    cached=base.replace('    s32 distanceClass;','    s32 distanceClass;\n    u32 targetBit;').replace(
        '        if ('+mask+') {','        targetBit = 0x10000U << targets[slot];\n        if (targetBit & *(u32 *)((u8 *)D_800D23B0 + slot * 4 + 0x16C0)) {')
    yield 'base-bit-lifetime',cached,source.DECLARATIONS


def compile_form(root,out,name,body,declarations,normal=False,whole=False):
    with patch.object(source,'DECLARATIONS',declarations):
        return source.compile_candidate(root,out,name,body,normal,whole)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--filter',default='');args=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body,declarations in forms():
        if args.filter and args.filter not in name:continue
        _,_,row=compile_form(root,root/BUILD,name,body,declarations)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
