"""Recover ordered target publication, distance timer and callback-aware flag update."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_category_boundaries_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-actor-target-timer'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508D850',0x1508D850,0xBAD00,115
ORIGINAL='s32 func_1508D850() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'f6aa1bdcd664ae77bb54512d09baac1a6277f6bafc959743ea10a05ff37c5f57',
    'conker/retail_word_patches.us.csv':'d59c93d7b205eb3f77acd7715b29e87fc447b5f2094bc5ffef81b0f07081f2df',
    'conker/build/conker.us.elf':'06b437552ed0b3d57ac5522b1d821f063f150fa77c053b993dd4534d30914505',
    'conker/src/game_DAE50.c':'ca6779c0fd3e2cd16b2f8ce758865df59310da359987cce07781cc5005733729',
    'conker/asm/nonmatchings/game_DAE50/func_150ADA68.s':'5a6e99909e32a7a447765007d4194689565251d4f5d8723adb62a7e141c71bad',
    'conker/asm/data/2441D0.rodata.s':'0407289916ea092d71053024b8fc3e092e35f5b0521c738ccfa3888861f1e782'})
DECLARATIONS='''extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern s8 D_800E0BD0;
extern s16 D_80087320[];
extern s8 D_800872E8[];
extern f32 D_8009DA8C;
s32 func_1508EB90(s32, s32, s32);
f32 func_150ADA68(void);
'''
INITIAL='''/* Publish the target and update its distance timer and probability flag. */
void func_1508D850(s32 slot) {
    u8 *state = (u8 *)D_800D23B0;
    s32 *targetSlot = (s32 *)(state + 0x11C + slot * 4);
    s32 *timer = (s32 *)(state + 0x29C + slot * 4);
    u8 *actor = D_800CC2D0 + slot * 0x32C;
    u8 *targetActor;
    s32 target;
    s32 distanceClass;
    f32 dx;
    f32 dz;
    f32 distance;
    f32 sample;

    (*(u8 **)(actor + 0x31C))[0x129] = *targetSlot;
    target = *targetSlot;
    if (target < 0) {
        return;
    }
    targetActor = D_800CC2D0 + target * 0x32C;
    dx = *(f32 *)(actor + 0x14);
    dz = *(f32 *)(actor + 0x1C);
    dx = *(f32 *)(targetActor + 0x14) - dx;
    dz = *(f32 *)(targetActor + 0x1C) - dz;
    distance = sqrtf(dx * dx + dz * dz);
    if (D_8009DA8C < distance) {
        distanceClass = 0;
    } else {
        distanceClass = 2;
        if (distance > 2000.0f) {
            distanceClass = 1;
        }
    }
    if (D_80087320[D_800E0BD0 * 3 + distanceClass] < *timer) {
        *timer = 0;
        if ((0x10000U << (*targetSlot & 31)) & *(u32 *)((u8 *)D_800D23B0 + slot * 4 + 0x16C0)) {
            func_1508EB90(slot, 0x61, 0x2000);
        }
    }
    if (*timer == 0) {
        (*(u8 **)(actor + 0x31C))[0x12A] = 0;
        sample = func_150ADA68();
        if (D_800872E8[D_800E0BD0] < (s32)(sample * 100.0f)) {
            (*(u8 **)(actor + 0x31C))[0x12A] = 1;
        }
    }
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown actor-target-timer predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>115I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'void-operation',INITIAL
    yield 'partial-int-return',INITIAL.replace('void func_1508D850','s32 func_1508D850').replace('        return;','        return 0;')
    yield 'implicit-int-return',INITIAL.replace('void func_1508D850','s32 func_1508D850')
    yield 'uncached-source-coordinates',INITIAL.replace('    dx = *(f32 *)(actor + 0x14);\n    dz = *(f32 *)(actor + 0x1C);\n','').replace(
        ' - dx;',' - *(f32 *)(actor + 0x14);').replace(' - dz;',' - *(f32 *)(actor + 0x1C);')


def fitting_candidates():
    for returns in ('void','partial-int'):
        base=INITIAL if returns=='void' else INITIAL.replace('void func_1508D850','s32 func_1508D850').replace('        return;','        return 0;')
        for cache in ('direct','array-bases'):
            body=base.replace('    u8 *state = (u8 *)D_800D23B0;\n','').replace('(state +','((u8 *)D_800D23B0 +')
            body=body.replace('    f32 sample;\n','').replace('sample','distance').replace('(*targetSlot & 31)','*targetSlot')
            if cache=='array-bases':
                body=body.replace('s32 *targetSlot = (s32 *)((u8 *)D_800D23B0 + 0x11C + slot * 4);',
                    's32 *targets = (s32 *)((u8 *)D_800D23B0 + 0x11C);').replace(
                    's32 *timer = (s32 *)((u8 *)D_800D23B0 + 0x29C + slot * 4);',
                    's32 *timers = (s32 *)((u8 *)D_800D23B0 + 0x29C);\n    s32 *timer;').replace(
                    '*targetSlot','targets[slot]').replace('    if (D_80087320[','    timer = timers + slot;\n    if (D_80087320[')
            yield returns+'-'+cache,body


def lifetime_candidates():
    base=dict(fitting_candidates())['partial-int-array-bases']
    ternary=base.replace('        distanceClass = 2;\n        if (distance > 2000.0f) {\n            distanceClass = 1;\n        }',
        '        distanceClass = distance > 2000.0f ? 1 : 2;')
    yield 'ternary-class',ternary
    direct=ternary.replace('    dx = *(f32 *)(actor + 0x14);\n    dz = *(f32 *)(actor + 0x1C);\n','').replace(
        ' - dx;',' - *(f32 *)(actor + 0x14);').replace(' - dz;',' - *(f32 *)(actor + 0x1C);')
    yield 'ternary-direct-coordinates',direct
    for label,unit in (('cached',ternary),('direct',direct)):
        offset=unit.replace('    s32 *targets =','    s32 slotOffset = slot * 4;\n    s32 *targets =').replace(
            '    s32 *timers = (s32 *)((u8 *)D_800D23B0 + 0x29C);\n    s32 *timer;',
            '    s32 *timer = (s32 *)((u8 *)D_800D23B0 + 0x29C);').replace(
            'targets[slot]','*(s32 *)((u8 *)targets + slotOffset)').replace(
            '    timer = timers + slot;','    timer = (s32 *)((u8 *)timer + slotOffset);').replace(
            '+ slot * 4 + 0x16C0','+ slotOffset + 0x16C0')
        yield 'shared-offset-'+label,offset


RESEARCH_PARTIAL=dict(lifetime_candidates())['ternary-direct-coordinates']
# Retail only establishes a numeric return on the negative-target path.
# Keep the fallthrough-int form as compiler research, not a production ABI.
SELECTED=RESEARCH_PARTIAL.replace('s32 func_1508D850','void func_1508D850').replace('        return 0;','        return;')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--fitting',action='store_true');parser.add_argument('--lifetimes',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (lifetime_candidates() if args.lifetimes else fitting_candidates() if args.fitting else candidates() if args.screens else [('selected',SELECTED)]):
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
