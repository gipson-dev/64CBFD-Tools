"""Recover position-based node refinement and its five-neighbor projection scan."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from unittest.mock import patch

from tools.experiments import game_balanced_target_assignment_candidates as previous
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-spatial-neighbor-refinement'
SOURCE,OWNER=previous.SOURCE,previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_15086098',0x15086098,0xB3548,179
ORIGINAL='s32 func_15086098() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'b03873bc9c984f3ce9eac8649d91170673bb8607b238b11f4686389edff11359',
    'conker/retail_word_patches.us.csv':'6a9e810059f31fc023e7fec0e58165fa71b8e5a32bfecb103aa1388c11e2f6b5',
    'conker/build/conker.us.elf':'6dae1b0cfba38f03c17601e1b9afdecefcfbd03f8302c4db89501b04801ac0bc'})
DECLARATIONS='''extern u8 *D_800D2350;
extern f32 D_8009D9D0;
s32 func_15085DA8(f32 y);
s32 func_15085DF8(f32 x, f32 y, f32 z, s8 mode, s8 band);
s32 func_15086C70(s32 index);
s32 func_150A32B4(s32 object, s32 x, s32 y, s32 z);
s32 func_150A3194();
s32 func_15086364();
'''
HELPER_OLD='''void func_15086C70(arg0)
s32 arg0;
{
    u8 *temp_v0 = (u8 *) ((s32) D_800D2350 + arg0 * 16);
    s32 temp_v1 = *(s16 *) (temp_v0 + 4);

    func_150A3194(3, 0xB, *(s16 *) temp_v0, *(s16 *) (temp_v0 + 2), temp_v1);
}'''
HELPER_NEW=HELPER_OLD.replace('void func_15086C70','s32 func_15086C70').replace(
    '    func_150A3194(','    return func_150A3194(')
SELECTED='''/* Refine a spatial node using record containment or the nearest forward edge. */
s32 func_15086098(f32 x, f32 y, f32 z, s8 count, s8 option, u8 *list, u8 *state) {
    s32 refined = 0xFF;
    s32 band;
    s32 index;
    s32 object;
    s32 selected;
    s32 candidate;
    s32 i;
    s32 originX;
    s32 originZ;
    u8 *nodes;
    u8 *node;
    u8 *cursor;
    u8 *neighbor;
    f32 radius;
    f32 diameter;
    f32 minimum;
    f32 dx;
    f32 dz;
    f32 inverseLength;
    f32 nx;
    f32 nz;
    f32 baseX;
    f32 baseZ;
    f32 projection;
    f32 distance;

    band = func_15085DA8(y);
    index = func_15085DF8(x, y, z, 0, band);
    if ((count > 0) && (index != 0xFF)) {
        object = func_15086C70(index);
        if ((object != 0) && (func_150A32B4(object, (s32)x, (s32)y, (s32)z) != 0)) {
            refined = func_15086364(index, count, option, list, state);
        } else {
            nodes = D_800D2350;
            node = nodes + index * 16;
            radius = (f32)(u32)node[8];
            minimum = D_8009D9D0;
            diameter = radius + radius;
            if (minimum < diameter * diameter) {
                refined = func_15086364(index, count, option, list, state);
            } else {
                selected = 0xFF;
                cursor = node;
                i = 0;
                do {
                    candidate = cursor[9];
                    i++;
                    if (candidate != 0xFF) {
                        neighbor = nodes + candidate * 16;
                        originX = *(s16 *)(node + 0);
                        originZ = *(s16 *)(node + 4);
                        dx = (f32)(*(s16 *)(neighbor + 0) - originX);
                        dz = (f32)(*(s16 *)(neighbor + 4) - originZ);
                        inverseLength = 1.0f / sqrtf(dx * dx + dz * dz);
                        nx = dx * inverseLength;
                        nz = dz * inverseLength;
                        baseX = (f32)originX;
                        baseZ = (f32)originZ;
                        projection = (x * nx + z * nz) + -(baseX * nx + baseZ * nz);
                        if (projection > 0.0f) {
                            dx = x - (baseX + nx * projection);
                            dz = z - (baseZ + nz * projection);
                            distance = dx * dx + dz * dz;
                            if (distance < minimum) {
                                selected = candidate;
                                minimum = distance;
                            }
                        }
                    }
                    cursor++;
                } while (i < 5);
                if (selected != 0xFF) {
                    object = func_15086364(index, count, option, list, state);
                    if (object == selected) {
                        refined = object;
                    }
                }
            }
        }
    }
    if (refined != 0xFF) {
        index = refined;
    }
    return index;
}
'''
compile_profile,link_owner=previous.compile_profile,previous.link_owner
INITIAL=SELECTED


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1 or before.count(HELPER_OLD)!=1:
        raise ValueError('Unknown spatial-refinement or record-wrapper predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip()).replace(HELPER_OLD,HELPER_NEW)


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']];words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero refinement alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in bindings.items() if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>179I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    register=INITIAL.replace('f32 x, f32 y, f32 z,','register f32 x, register f32 y, register f32 z,',1)
    yield 'register-args',register
    start=INITIAL.index('    band =')
    cached=INITIAL[:start]+'''    f32 px = x;
    f32 pz = z;

'''+re.sub(r'\b[xyz]\b',lambda m:{'x':'px','y':'y','z':'pz'}[m[0]],INITIAL[start:])
    yield 'cached-xz',cached
    scoped=INITIAL
    groups=(
        ('        } else {\n            nodes =',
         ('u8 *nodes;','u8 *node;','f32 radius;','f32 diameter;','f32 minimum;'),12),
        ('            } else {\n                selected =',
         ('s32 selected;','s32 candidate;','s32 i;','u8 *cursor;'),16),
        ('                    if (candidate != 0xFF) {\n                        neighbor =',
         ('s32 originX;','s32 originZ;','u8 *neighbor;','f32 dx;','f32 dz;','f32 inverseLength;',
          'f32 nx;','f32 nz;','f32 baseX;','f32 baseZ;','f32 projection;','f32 distance;'),24))
    for marker,names,indent in groups:
        for name in names:
            if scoped.count('    '+name+'\n')!=1:raise ValueError('Unknown refinement declaration')
            scoped=scoped.replace('    '+name+'\n','',1)
        split=marker.index('\n')+1
        scoped=scoped.replace(marker,marker[:split]+''.join(' '*indent+n+'\n' for n in names)+'\n'+marker[split:],1)
    yield 'scoped',scoped
    yield 'scoped-register-args',scoped.replace('f32 x, f32 y, f32 z,','register f32 x, register f32 y, register f32 z,',1)
    reused=scoped.replace('                        f32 nx;\n','').replace('                        f32 nz;\n','')
    reused=re.sub(r'\b(nx|nz)\b',lambda m:{'nx':'dx','nz':'dz'}[m[0]],reused)
    yield 'in-place-normal',reused
    yield 'negative-first',reused.replace(
        'projection = (x * dx + z * dz) + -(baseX * dx + baseZ * dz);',
        'projection = -(baseX * dx + baseZ * dz) + (x * dx + z * dz);')
    compact=reused.replace('    s32 band;\n','').replace('    s32 object;\n','').replace(
        '    band = func_15085DA8(y);\n    index = func_15085DF8(x, y, z, 0, band);',
        '    index = func_15085DF8(x, y, z, 0, func_15085DA8(y));').replace(
        '    if ((count > 0) && (index != 0xFF)) {',
        '    if ((count > 0) && (index != 0xFF)) {\n        s32 object;').replace(
        '            f32 diameter;\n','').replace('            diameter = radius + radius;',
        '            radius += radius;').replace('diameter * diameter','radius * radius')
    yield 'compact',compact
    yield 'compact-register-index',compact.replace('    s32 index;','    register s32 index;')
    yield 'compact-outer-object',compact.replace('    s32 index;', '    s32 index;\n    s32 object;').replace(
        '        s32 object;\n', '')
    yield 'compact-return-selection',compact.replace('''    if (refined != 0xFF) {
        index = refined;
    }
    return index;''','''    return refined != 0xFF ? refined : index;''')
    yield 'compact-original-radius',compact.replace('            f32 radius;','            f32 radius;\n            f32 diameter;').replace(
        '            radius += radius;', '            diameter = radius + radius;').replace('radius * radius','diameter * diameter')
    yield 'compact-band-local',compact.replace('    s32 index;', '    s32 band;\n    s32 index;').replace(
        '    index = func_15085DF8(x, y, z, 0, func_15085DA8(y));',
        '    band = func_15085DA8(y);\n    index = func_15085DF8(x, y, z, 0, band);')
    inline=compact.replace('        s32 object;\n','').replace('    s32 index;','    s32 index;\n    s32 object;')
    for axis in ('X','Z'):
        offset=0 if axis=='X' else 4
        inline=inline.replace('                        s32 origin%s;\n'%axis,'').replace(
            '                        origin%s = *(s16 *)(node + %d);\n'%(axis,offset),'')
        inline=inline.replace('origin'+axis,'*(s16 *)(node + %d)'%offset)
    yield 'inline-coordinates',inline
    split=inline.replace('            f32 minimum;','            f32 threshold;').replace(
        '            minimum = D_8009D9D0;','            threshold = D_8009D9D0;').replace(
        'if (minimum < radius * radius)','if (threshold < radius * radius)').replace(
        '            } else {\n                s32 selected;',
        '            } else {\n                f32 minimum = threshold;\n                s32 selected;')
    yield 'split-threshold',split
    yield 'split-compact',split.replace('    s32 object;\n','').replace(
        '    if ((count > 0) && (index != 0xFF)) {',
        '    if ((count > 0) && (index != 0xFF)) {\n        s32 object;')
    yield 'split-negative-first',split.replace(
        'projection = (x * dx + z * dz) + -(baseX * dx + baseZ * dz);',
        'projection = -(baseX * dx + baseZ * dz) + (x * dx + z * dz);')
    yield 'compact-distance',compact.replace('                        f32 distance;\n','').replace(
        '                            distance = dx * dx + dz * dz;',
        '                            projection = dx * dx + dz * dz;').replace(
        'distance < minimum','projection < minimum').replace('minimum = distance;','minimum = projection;')
    yield 'plane-offset',INITIAL.replace('    f32 projection;','    f32 projection;\n    f32 planeOffset;').replace(
        '                        projection = (x * nx + z * nz) + -(baseX * nx + baseZ * nz);',
        '                        planeOffset = -(baseX * nx + baseZ * nz);\n                        projection = (x * nx + z * nz) + planeOffset;')


SELECTED=dict(candidates())['compact']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--normal',action='store_true')
    p.add_argument('--whole',action='store_true');p.add_argument('--screens',action='store_true')
    args=p.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        _,_,row=compile_candidate(root,root/BUILD,name+('-whole' if args.whole else '')+
            ('-normal' if args.normal else ''),body,normal=args.normal,whole=args.whole)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
