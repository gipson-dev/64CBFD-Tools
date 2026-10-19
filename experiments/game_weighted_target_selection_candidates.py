"""Recover the cached neighbor-table scan and weighted strict-minimum target."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_sine_selector_candidates as previous
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-weighted-target-selection'
SOURCE,OWNER=previous.SOURCE,previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_1508B9BC',0x1508B9BC,0xB8E6C,153
ORIGINAL='s32 func_1508B9BC() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'5d8b6cbccee79b0db84aaaac92d5533d213bebe62bf683686ad1f2379eee0f37',
    'conker/retail_word_patches.us.csv':'b200d8dc1c2d3a753e1865f20524c8fcc69ee922e8d12c27bf544f8dd9d27fcc',
    'conker/build/conker.us.elf':'a0cce96c2ae430f94f8f717f94a10b9d46d37c90faa725929c5ff7bdc962ea78'})
DECLARATIONS='''extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern f32 D_8009DA60;
extern f32 D_8009DA64;
s32 func_1508C5B8();
s32 func_1508A1BC(void);
'''
SELECTED='''/* Publish the first minimum weighted neighbor and its current X/Z distance. */
s32 func_1508B9BC(void) {
    u8 *context = (u8 *)D_800D23B0;
    s32 count = *(s32 *)(context + 0x10);
    s32 current = *(s32 *)(context + 4);
    s32 *active = (s32 *)(context + 0x39C);
    s32 *neighbors = (s32 *)(context + 0x5DC);
    s32 *distances = (s32 *)(context + 0x9DC);
    s32 *targets = (s32 *)(context + 0x11C);
    s32 pairBudget = 1;
    s32 selected;
    s32 best;
    s32 i;
    s32 scan;
    s32 limit;
    s32 score;
    u8 *weights;
    u8 *actor;
    u8 *target;
    f32 weight;
    f32 dx;
    f32 dz;

    if (count >= 9) {
        pairBudget = 4;
    }
    func_1508C5B8(0, pairBudget);
    func_1508A1BC();
    context = (u8 *)D_800D23B0;
    weights = context + current * 16 + 0x15B4;
    selected = -1;
    best = 10000000;
    for (i = 0; i < count; i++) {
        if ((active[i] > 0) && (i != current)) {
            score = -1;
            scan = i * 16;
            limit = scan + 16;
            while ((scan < limit) && (neighbors[scan] != -1)) {
                if (neighbors[scan] == current) {
                    score = distances[scan];
                    scan = limit;
                } else {
                    scan++;
                }
            }
            if (score != -1) {
                weight = (f32)(u32)weights[i] * D_8009DA64;
                if (targets[current] == i) {
                    weight *= D_8009DA60;
                }
                score = (s32)((f32)score * weight);
                if (score < best) {
                    best = score;
                    selected = i;
                }
            }
        }
    }
    *(s32 *)(context + current * 4 + 0x49C) = selected;
    if (selected != -1) {
        actor = D_800CC2D0 + current * 0x32C;
        target = D_800CC2D0 + selected * 0x32C;
        dx = *(f32 *)(actor + 0x14) - *(f32 *)(target + 0x14);
        dz = *(f32 *)(actor + 0x1C) - *(f32 *)(target + 0x1C);
        *(s32 *)((u8 *)D_800D23B0 + current * 4 + 0x45C) =
            (s32)sqrtf(dx * dx + dz * dz);
    } else {
        *(s32 *)((u8 *)D_800D23B0 + current * 4 + 0x45C) = best;
    }
    return 0;
}
'''
compile_profile,link_owner=previous.compile_profile,previous.link_owner

INITIAL=SELECTED
SELECTED=INITIAL.replace('    u8 *context = (u8 *)D_800D23B0;\n','').replace(
    '    context = (u8 *)D_800D23B0;\n','').replace('(context +','((u8 *)D_800D23B0 +').replace(
    'weights = context +','weights = (u8 *)D_800D23B0 +').replace(
    '    f32 weight;','    f32 weight;\n    f32 targetScale;\n    f32 weightScale;').replace(
    '    for (i = 0; i < count; i++) {',
    '    if (count > 0) {\n        targetScale = D_8009DA60;\n        weightScale = D_8009DA64;\n    i = 0;\n    do {').replace(
    '    *(s32 *)((u8 *)D_800D23B0 + current * 4 + 0x49C) = selected;',
    '    }\n    *(s32 *)((u8 *)D_800D23B0 + current * 4 + 0x49C) = selected;').replace(
    '    }\n    }\n    *(s32 *)','    } while (++i < count);\n    }\n    *(s32 *)').replace(
    ' * D_8009DA64',' * weightScale').replace('weight *= D_8009DA60','weight *= targetScale')
_begin=SELECTED.index('    i = 0;\n    do {');_end=SELECTED.index('    }\n    *(s32 *)',_begin)
SELECTED=SELECTED[:_begin]+''.join('    '+line if line.strip() else line for line in
    SELECTED[_begin:_end].splitlines(True))+SELECTED[_end:]


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown weighted-selector predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip())


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']];words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero weighted-selector alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in bindings.items() if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>153I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'selected',SELECTED
    yield 'initial',INITIAL
    start=SELECTED.index('            while ((scan < limit)')
    finish=SELECTED.index('            if (score != -1)',start)
    yield 'for-break',SELECTED[:start]+'''            for (; (scan < limit) && (neighbors[scan] != -1); scan++) {
                if (neighbors[scan] == current) {
                    score = distances[scan];
                    break;
                }
            }
'''+SELECTED[finish:]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--screens',action='store_true')
    p.add_argument('--normal',action='store_true');args=p.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        _,_,row=compile_candidate(root,root/BUILD,name+('-normal' if args.normal else ''),body,normal=args.normal)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
