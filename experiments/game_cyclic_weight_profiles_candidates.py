"""Recover randomized cyclic byte-weight profiles with a cached signed count."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_spatial_neighbor_refinement_candidates as previous
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-cyclic-weight-profiles'
SOURCE,OWNER=previous.SOURCE,previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_1508BC20',0x1508BC20,0xB90D0,189
ORIGINAL='s32 func_1508BC20() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'1ea8523c2148a3603e5fb04c2699952822166a403a4568c2228d74153e3fcbf1',
    'conker/retail_word_patches.us.csv':'754763e55d3731701d31c0b53fc3f672b366bde617412ebf38872c77625c79d1',
    'conker/build/conker.us.elf':'e8d1f53395dcf4b35dc4eb38b49b019a00bb11443694e3e6b0604deb67026e24'})
DECLARATIONS='''extern s8 D_8008FD8C;
extern s32 D_800D23B0;
f32 func_150ADA68(void);
'''
SELECTED='''/* Fill each weight row from a random cyclic origin with an upper-threshold bounce. */
void func_1508BC20(void) {
    s32 count = D_8008FD8C;
    u8 *weights = (u8 *)D_800D23B0 + 0x15B4;
    s32 divisor = count >> 1;
    s32 step;
    s8 used[16];
    s32 row;
    s32 i;
    s32 position;
    s32 direction;
    s32 value;
    s32 delta;

    if (divisor < 2) {
        divisor = 2;
    }
    step = 170 / divisor;
    for (row = 0; row < count; row++, weights += 16) {
        direction = -1;
        value = 85;
        delta = step;
        for (i = 0; i < 16; i++) {
            used[i] = 0;
        }
        /* The inclusive RNG endpoint is used without an initial index clamp. */
        position = (s32)(func_150ADA68() * (f32)count);
        if (func_150ADA68() > 0.5f) {
            direction = 1;
        }
        while (used[position] != 0) {
            position += direction;
            if (position < 0) {
                position = count - 1;
            }
            if (position >= count) {
                position = 0;
            }
        }
        used[position] = 1;
        for (i = 0; i < count; i++) {
            weights[position] = value < 256 ? value : 255;
            position++;
            if (position >= count) {
                position = 0;
            }
            value += delta;
            if (value >= 256) {
                delta = -delta;
            }
        }
    }
}
'''
compile_profile,link_owner=previous.compile_profile,previous.link_owner


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown cyclic-weight predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip())


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']];words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero weight-profile alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in bindings.items() if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=None,normal=True,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at));truth=struct.unpack_from('>189I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'selected',SELECTED
    marker='''        for (i = 0; i < 16; i++) {
            used[i] = 0;
        }'''
    clear=SELECTED.replace('    s8 used[16];','    s8 used[16];\n    s8 *clear;\n    s8 *end;').replace(marker,'''        clear = used;
        end = used + 16;
        do {
            clear += 4;
            clear[-4] = 0;
            clear[-3] = 0;
            clear[-2] = 0;
            clear[-1] = 0;
        } while (clear != end);''')
    yield 'unrolled-clear',clear
    yield 'if-store',SELECTED.replace('            weights[position] = value < 256 ? value : 255;',
        '''            if (value < 256) {
                weights[position] = value;
            } else {
                weights[position] = 255;
            }''')
    yield 'cached-float',SELECTED.replace('    s32 step;','    s32 step;\n    f32 floatCount = (f32)count;').replace(
        'func_150ADA68() * (f32)count','func_150ADA68() * floatCount')
    array_last=SELECTED.replace('    s8 used[16];\n','').replace('    s32 delta;','    s32 delta;\n    s8 used[16];')
    yield 'array-last',array_last
    row_first=array_last.replace('    s32 row;\n','').replace('    s32 count =','    s32 row;\n    s32 count =',1)
    yield 'row-first',row_first
    for name,body in (('do-rows',SELECTED),('do-row-first',row_first)):
        marker='    for (row = 0; row < count; row++, weights += 16) {\n'
        a=body.index(marker);b=body.rfind('    }\n}\n')
        middle=body[a+len(marker):b]
        yield name,body[:a]+'''    row = 0;
    if (count > 0) {
        do {
'''+''.join('    '+line+'\n' for line in middle.splitlines())+'''            row++;
            weights += 16;
        } while (row != count);
    }
}
'''


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--normal',action='store_true',dest='normal',default=True)
    p.add_argument('--primary',action='store_false',dest='normal')
    p.add_argument('--whole',action='store_true');p.add_argument('--screens',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        _,_,row=compile_candidate(root,root/BUILD,name+('-normal' if args.normal else '')+('-whole' if args.whole else ''),
            body,args.normal,args.whole)
        print(json.dumps(dict(name=name,**row)),flush=True)
