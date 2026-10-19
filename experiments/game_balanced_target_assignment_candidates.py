"""Recover two-pass team assignment with signed costs and reuse penalties."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_weighted_target_selection_candidates as previous
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-balanced-target-assignment'
SOURCE,OWNER=previous.SOURCE,previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_1508BF14',0x1508BF14,0xB93C4,160
ORIGINAL='s32 func_1508BF14() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'05899c7b26d31e5c0ff2cc13709a7df9055b65eab28f6abdaeb8a400dce122a2',
    'conker/retail_word_patches.us.csv':'705662100309d5c1aae4b0ad71bbebc411ae6a4b2044314b4f0d576dd3129181',
    'conker/build/conker.us.elf':'f56b8cca096731899df5ddecd2fcd8060cf57f53ac03508ab093929f7e14ee4d'})
DECLARATIONS='extern s32 D_800D23B0;\n'
SELECTED='''/* Assign opposite-team neighbors in two passes, penalizing repeated choices. */
s32 func_1508BF14(void) {
    s32 current = *(s32 *)((u8 *)D_800D23B0 + 4);
    s32 count = *(s32 *)((u8 *)D_800D23B0 + 0x10);
    s32 *flags = (s32 *)((u8 *)D_800D23B0 + 0x15C);
    s32 *active = (s32 *)((u8 *)D_800D23B0 + 0x39C);
    s32 *teams = (s32 *)((u8 *)D_800D23B0 + 0xE64);
    s32 *costs = (s32 *)((u8 *)D_800D23B0 + 0x45C);
    s32 *targets = (s32 *)((u8 *)D_800D23B0 + 0x49C);
    s32 ownTeam = teams[current];
    s32 *neighbors = (s32 *)((u8 *)D_800D23B0 + 0x5DC);
    s32 *distances = (s32 *)((u8 *)D_800D23B0 + 0x9DC);
    s8 usageStorage[41];
    s8 *uses = usageStorage + 1;
    s32 pass;
    s32 i;
    s32 candidate;
    s32 special;
    s32 selected;
    s32 best;
    s32 scan;
    s32 limit;
    s32 score;
    s32 remainder;
    s8 *clear;
    s8 *end;

    /* Back the no-selection byte too; its value never participates in scoring. */
    usageStorage[0] = 0;
    i = 0;
    if (count > 0) {
        remainder = count & 3;
        if (remainder != 0) {
            clear = uses;
            do {
                i++;
                *clear++ = 0;
            } while (i != remainder);
        }
        if (i != count) {
            clear = uses + i;
            end = uses + count;
            do {
                clear += 4;
                clear[-4] = 0;
                clear[-3] = 0;
                clear[-2] = 0;
                clear[-1] = 0;
            } while (clear != end);
        }
    }
    pass = 0;
    do {
        for (i = 0; i < count; i++) {
            special = 0;
            if ((flags[i] == 2) || (flags[i] == 3)) {
                special = 1;
            }
            if ((special && (pass == 0)) || (!special && (pass != 0))) {
                best = 10000000;
                selected = -1;
                if (teams[i] == ownTeam) {
                    for (candidate = 0; candidate < count; candidate++) {
                        if ((active[candidate] > 0) && (teams[candidate] != ownTeam)) {
                            score = -1;
                            scan = candidate * 16;
                            limit = scan + 16;
                            while ((scan < limit) && (neighbors[scan] != -1)) {
                                if (neighbors[scan] == i) {
                                    score = distances[scan];
                                    scan = limit;
                                } else {
                                    scan++;
                                }
                            }
                            if (score != -1) {
                                score = (s32)((u32)score << ((u32)uses[candidate] & 31));
                                if (score < best) {
                                    best = score;
                                    selected = candidate;
                                }
                            }
                        }
                    }
                    uses[selected]++;
                    costs[i] = best;
                    targets[i] = selected;
                }
            }
        }
    } while (++pass != 2);
    return 0;
}
'''
compile_profile,link_owner=previous.compile_profile,previous.link_owner


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown balanced-assignment predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip())


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']];words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero assignment alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in bindings.items() if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>160I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'selected',SELECTED
    start=SELECTED.index('    i = 0;\n    if (count > 0)')
    end=SELECTED.index('    pass = 0;',start)
    counter=SELECTED[:start]+'''    for (i = 0; i < count; i++) {
        uses[i] = 0;
    }
'''+SELECTED[end:]
    yield 'counter-clear',counter
    yield 'pointer-clear',SELECTED[:start]+'''    i = 0;
    if (count > 0) {
        clear = uses;
        do {
            i++;
            *clear++ = 0;
        } while (i != count);
    }
'''+SELECTED[end:]
    yield 'single-context',SELECTED.replace('s32 func_1508BF14(void) {',
        's32 func_1508BF14(void) {\n    u8 *context = (u8 *)D_800D23B0;').replace(
        '((u8 *)D_800D23B0 +','(context +')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--normal',action='store_true')
    p.add_argument('--screens',action='store_true');args=p.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        _,_,row=compile_candidate(root,root/BUILD,name+('-normal' if args.normal else ''),body,normal=args.normal)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
