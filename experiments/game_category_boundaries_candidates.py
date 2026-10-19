"""Recover category boundaries; screens are compile-only, FITTED is tested separately."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_release_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-category-boundaries'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15085BE8',0x15085BE8,0xB3098,112
ORIGINAL='s32 func_15085BE8() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'af0fd776d65e309e9dcc8e4d68bd3e3155dc0eff3c46faf6fa8f28da66ad96b8',
    'conker/retail_word_patches.us.csv':'5ddd1615d90ce59ff70ff6e95de91a52151b442b86156c2aea53a738393c34c3',
    'conker/build/conker.us.elf':'14bd44cfcbbb6ea376ada9c64ab529cd029dd38984f35e023ef166a594ccfcfe',
    'conker/asm/data/242480.rodata.s':'4add61fb582bd9368ec71f1a974de8545c88624aa7ee27c41d9addd675013618'})
DECLARATIONS='''extern s16 D_80087290;
extern u8 *D_800D2350;
extern u8 D_800D2358;
extern u8 D_800D237C[];
extern f32 D_800D2360[];
extern f32 D_8009D9C0;
extern f32 D_8009D9C4;
extern f32 D_8009D9C8;
'''
INITIAL='''/* Build category height boundaries and report overlapping adjacent ranges. */
s32 func_15085BE8(void) {
    f32 minimum[6];
    f32 maximum[6];
    s32 overlap = 0;
    s32 i;
    s32 category;
    s32 count;
    f32 height;
    f32 lower;
    f32 upper;
    u8 *row;

    for (i = 0; i < 6; i++) {
        minimum[i] = D_8009D9C4;
        maximum[i] = D_8009D9C0;
    }
    count = D_80087290 * 16;
    row = D_800D2350;
    for (i = 0; i < count; i += 16, row += 16) {
        category = row[6];
        height = (f32)*(s16 *)(row + 2);
        if (height < minimum[category]) {
            minimum[category] = height;
        }
        if (maximum[category] < height) {
            maximum[category] = height;
        }
    }
    D_800D2358 = 0;
    for (i = 0; i < 6; i++) {
        if (minimum[i] <= maximum[i]) {
            D_800D237C[D_800D2358] = i;
            D_800D2358++;
        }
    }
    count = D_800D2358 - 1;
    for (i = 0; i < count; i++) {
        upper = maximum[D_800D237C[i]];
        lower = minimum[D_800D237C[i + 1]];
        D_800D2360[i] = (lower + upper) * 0.5f;
        if (lower < upper) {
            overlap = 1;
        }
    }
    D_800D2360[i] = D_8009D9C8;
    return overlap;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown category-boundaries predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(FITTED if body is None else body).rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>112I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'indexed',INITIAL
    for size in (6,8):
        for indexed in (True,False):
            body=INITIAL.replace('[6];','[%d];'%size)
            if not indexed:
                body=body.replace('    u8 *row;','    u8 *row;\n    f32 *minCursor;\n    f32 *maxCursor;').replace(
                    '    for (i = 0; i < 6; i++) {\n        minimum[i] = D_8009D9C4;\n        maximum[i] = D_8009D9C0;\n    }',
                    '    minCursor = minimum;\n    maxCursor = maximum;\n    do {\n        *minCursor++ = D_8009D9C4;\n        *maxCursor++ = D_8009D9C0;\n    } while (maxCursor < maximum + 6);')
            body=body.replace('    row = D_800D2350;\n    for (i = 0; i < count; i += 16, row += 16) {',
                '    if (D_80087290 > 0) {\n    row = D_800D2350;\n    for (i = 0; i < count; i += 16, row += 16) {').replace(
                '    D_800D2358 = 0;','    }\n    D_800D2358 = 0;')
            yield ('index' if indexed else 'pointer')+'-size%d'%size,body


def fitting_candidates():
    indexed=INITIAL.replace('    f32 minimum[6];\n    f32 maximum[6];\n','').replace(
        '    u8 *row;','    u8 *row;\n    f32 minimum[6];\n    f32 maximum[6];')
    for label,base in (('initial',INITIAL),('arrays-last',indexed)):
        for reversed_fill in (False,True):
            body=base
            if reversed_fill:body=body.replace('        minimum[i] = D_8009D9C4;\n        maximum[i] = D_8009D9C0;',
                '        maximum[i] = D_8009D9C0;\n        minimum[i] = D_8009D9C4;')
            body=body.replace('    count = D_80087290 * 16;\n    row = D_800D2350;\n    for (i = 0; i < count; i += 16, row += 16) {',
                '    i = 0;\n    if (D_80087290 > 0) {\n        count = D_80087290 * 16;\n        row = D_800D2350;\n        do {').replace(
                '        category = row[6];\n        height = (f32)*(s16 *)(row + 2);',
                '        height = (f32)*(s16 *)(row + 2);\n        category = row[6];\n        i += 16;').replace(
                '    D_800D2358 = 0;',
                '        row += 16;\n        } while (i < count);\n    }\n    D_800D2358 = 0;')
            # The old closing brace is replaced with the actual row-loop back edge.
            body=body.replace('    }\n        row += 16;','        row += 16;')
            yield label+('-max-first' if reversed_fill else '-min-first'),body
            for pointer in (False,True):
                final=body.replace('    for (i = 0; i < count; i++) {',
                    '    for (i = 0; i < count;) {').replace('        D_800D2360[i] = (lower + upper) * 0.5f;',
                    '        i++;\n        D_800D2360[i - 1] = (lower + upper) * 0.5f;')
                if pointer:final=final.replace('    u8 *row;','    u8 *row;\n    u8 *ids;\n    f32 *output;').replace(
                    '    count = D_800D2358 - 1;','    count = D_800D2358 - 1;\n    ids = D_800D237C;\n    output = D_800D2360;').replace(
                    'maximum[D_800D237C[i]]','maximum[ids[0]]').replace('minimum[D_800D237C[i + 1]]','minimum[ids[1]]').replace(
                    '        i++;','        i++;\n        ids++;').replace('D_800D2360[i - 1] =','*output++ =')
                yield label+('-max-first' if reversed_fill else '-min-first')+('-cursor' if pointer else '-increment'),final


def loop_candidates():
    for fill in ('min-first','max-first'):
        base=INITIAL
        if fill=='max-first':base=base.replace('        minimum[i] = D_8009D9C4;\n        maximum[i] = D_8009D9C0;',
            '        maximum[i] = D_8009D9C0;\n        minimum[i] = D_8009D9C4;')
        base=base.replace('    count = D_80087290 * 16;\n    row = D_800D2350;\n    for (i = 0; i < count; i += 16, row += 16) {',
            '    i = 0;\n    if (D_80087290 > 0) {\n    row = D_800D2350;\n    for (i = 0; i < D_80087290 * 16; i += 16, row += 16) {').replace(
            '    D_800D2358 = 0;','    }\n    D_800D2358 = 0;')
        for final in ('for','do','pointer-do'):
            body=base
            if final!='for':
                body=body.replace('    for (i = 0; i < count; i++) {',
                    '    i = 0;\n    if (count > 0) {\n    do {').replace(
                    '    D_800D2360[i] = D_8009D9C8;',
                    '    D_800D2360[i] = D_8009D9C8;')
                body=body.replace('    }\n    D_800D2360[i] = D_8009D9C8;',
                    '        i++;\n    } while (i < count);\n    }\n    D_800D2360[i] = D_8009D9C8;')
            if final=='pointer-do':
                body=body.replace('    u8 *row;','    u8 *row;\n    f32 *output;').replace(
                    '    count = D_800D2358 - 1;','    count = D_800D2358 - 1;\n    row = D_800D237C;\n    output = D_800D2360;').replace(
                    'maximum[D_800D237C[i]]','maximum[row[0]]').replace('minimum[D_800D237C[i + 1]]','minimum[row[1]]').replace(
                    'D_800D2360[i] = (lower + upper) * 0.5f;','*output = (lower + upper) * 0.5f;').replace(
                    '        i++;\n    } while (i < count);','        i++;\n        row++;\n        output++;\n    } while (i < count);')
            yield 'direct-'+fill+'-'+final,body


def counter_candidates():
    base=INITIAL.replace('    s32 category;','    s32 category;\n    s32 rowOffset;\n    s8 categoryIndex = 0;\n    s32 boundaryIndex;')
    base=base.replace('    count = D_80087290 * 16;\n    row = D_800D2350;\n    for (i = 0; i < count; i += 16, row += 16) {',
        '    if (D_80087290 > 0) {\n    row = D_800D2350;\n    for (rowOffset = 0; rowOffset < D_80087290 * 16; rowOffset += 16, row += 16) {').replace(
        '    D_800D2358 = 0;','    }\n    D_800D2358 = 0;')
    start=base.index('    D_800D2358 = 0;');end=base.index('    count = D_800D2358 - 1;')
    compact=base[start:end].replace('for (i = 0; i < 6; i++)','for (; categoryIndex < 6; categoryIndex++)').replace('[i]','[categoryIndex]').replace(' = i;',' = categoryIndex;')
    base=base[:start]+compact+base[end:]
    start=base.index('    count = D_800D2358 - 1;')
    base=base[:start]+base[start:].replace('i = 0; i < count; i++','boundaryIndex = 0; boundaryIndex < count; boundaryIndex++').replace('[i + 1]','[boundaryIndex + 1]').replace('[i]','[boundaryIndex]')
    for signed in (True,False):
        body=base if signed else base.replace('s8 categoryIndex','s32 categoryIndex')
        for reverse in (False,True):
            selected=body
            if reverse:selected=selected.replace('        minimum[i] = D_8009D9C4;\n        maximum[i] = D_8009D9C0;',
                '        maximum[i] = D_8009D9C0;\n        minimum[i] = D_8009D9C4;')
            yield 'counters-'+('s8' if signed else 's32')+('-max' if reverse else '-min'),selected


def shape_candidates():
    base=dict(loop_candidates())['direct-max-first-for']
    base=base.replace('    for (i = 0; i < count; i++) {',
        '    for (i = 0; i < D_800D2358 - 1; i++) {')
    yield 'global-bound',base
    for index_type in ('s32','u32'):
        body=base.replace('    s32 i;','    '+index_type+' i;')
        yield 'global-bound-'+index_type,body
    pointer=POINTER_BODY
    yield 'literal-pointers',pointer
    yield 'literal-registers',pointer.replace('    s32 ','    register s32 ').replace(
        '    f32 *','    register f32 *').replace('    f32 maxInitial','    register f32 maxInitial').replace(
        '    f32 minInitial','    register f32 minInitial').replace('    f32 lower','    register f32 lower').replace(
        '    f32 upper','    register f32 upper').replace('    u8 *','    register u8 *')


def placement_candidates():
    base=dict(shape_candidates())['global-bound']
    for min_first in (False,True):
        body=base
        if min_first:body=body.replace('        maximum[i] = D_8009D9C0;\n        minimum[i] = D_8009D9C4;',
            '        minimum[i] = D_8009D9C4;\n        maximum[i] = D_8009D9C0;')
        arrays='    f32 minimum[6];\n    f32 maximum[6];\n'
        for marker in ('s32 overlap','s32 i','s32 category','s32 count','f32 height','f32 lower','f32 upper','u8 *row'):
            moved=body.replace(arrays,'').replace('    '+marker,arrays+'    '+marker,1)
            yield ('min' if min_first else 'max')+'-arrays-before-'+marker.split()[-1].lstrip('*'),moved


def lifetime_candidates():
    for fill in ('min','max'):
        body=dict(placement_candidates())[fill+'-arrays-before-upper']
        body=body.replace('    f32 height;\n','').replace('height','lower').replace('    s32 category;',
            '    s32 category;\n    s32 rowOffset;')
        body=body.replace('for (i = 0; i < D_80087290 * 16; i += 16, row += 16)',
            'for (rowOffset = 0; rowOffset < D_80087290 * 16; rowOffset += 16, row += 16)')
        start=body.index('    D_800D2358 = 0;');end=body.index('    count = D_800D2358 - 1;')
        compact=body[start:end].replace('for (i = 0; i < 6; i++)','for (; i < 6; i++)')
        body=body[:start]+compact+body[end:]
        yield 'shared-'+fill,body
        inner=body.replace('for (rowOffset = 0; rowOffset < D_80087290 * 16; rowOffset += 16, row += 16) {',
            'rowOffset = 0;\n    do {').replace('    }\n    }\n    D_800D2358 = 0;',
            '        rowOffset += 16;\n        row += 16;\n    } while (rowOffset < D_80087290 * 16);\n    }\n    D_800D2358 = 0;')
        yield 'shared-do-'+fill,inner


POINTER_BODY='''/* Build category height boundaries and report overlapping adjacent ranges. */
s32 func_15085BE8(void) {
    f32 minimum[6];
    f32 maximum[6];
    s32 overlap = 0;
    s32 i;
    s32 category;
    s32 count;
    f32 maxInitial = D_8009D9C0;
    f32 minInitial = D_8009D9C4;
    f32 lower;
    f32 upper;
    f32 *minCursor = minimum;
    f32 *maxCursor = maximum;
    f32 *output;
    u8 *row;

    do {
        *minCursor++ = minInitial;
        *maxCursor++ = maxInitial;
    } while (maxCursor < maximum + 6);
    i = 0;
    if (D_80087290 > 0) {
        count = D_80087290 * 16;
        row = D_800D2350;
        do {
            lower = (f32)*(s16 *)(row + 2);
            category = row[6];
            i += 16;
            if (lower < minimum[category]) {
                minimum[category] = lower;
            }
            if (maximum[category] < lower) {
                maximum[category] = lower;
            }
            row += 16;
        } while (i < count);
    }
    D_800D2358 = 0;
    minCursor = minimum;
    maxCursor = maximum;
    i = 0;
    do {
        if (*minCursor++ <= *maxCursor++) {
            D_800D237C[D_800D2358] = i;
            D_800D2358++;
        }
        i++;
    } while (i < 6);
    row = D_800D237C;
    count = D_800D2358 - 1;
    i = 0;
    if (count > 0) {
        output = D_800D2360;
        do {
            upper = maximum[row[0]];
            lower = minimum[row[1]];
            i++;
            row++;
            *output = (lower + upper) * 0.5f;
            if (lower < upper) {
                overlap = 1;
            }
            output++;
        } while (i < count);
    }
    D_800D2360[i] = D_8009D9C8;
    return overlap;
}
'''


SEMANTIC=dict(candidates())['index-size6']
FITTED='''/* Build category height boundaries and report overlapping adjacent ranges. */
s32 func_15085BE8(void) {
    f32 minimum[6];
    f32 maximum[6];
    s32 overlap = 0;
    s32 i;
    s32 category;
    s32 count;
    f32 height;
    f32 lower;
    f32 upper;
    u8 *row;

    for (i = 0; i < 6; i++) {
        minimum[i] = D_8009D9C4;
        maximum[i] = D_8009D9C0;
    }
    count = D_80087290 * 16;
    if (D_80087290 > 0) {
        row = D_800D2350;
        for (i = 0; i < count; i += 16, row += 16) {
            category = row[6];
            height = (f32)*(s16 *)(row + 2);
            if (height < minimum[category]) {
                minimum[category] = height;
            }
            if (maximum[category] < height) {
                maximum[category] = height;
            }
        }
    }
    D_800D2358 = 0;
    for (i = 0; i < 6; i++) {
        if (minimum[i] <= maximum[i]) {
            D_800D237C[D_800D2358] = i;
            D_800D2358++;
        }
    }
    for (i = 0; i < D_800D2358 - 1; i++) {
        upper = maximum[D_800D237C[i]];
        lower = minimum[D_800D237C[i + 1]];
        D_800D2360[i] = (lower + upper) * 0.5f;
        if (lower < upper) {
            overlap = 1;
        }
    }
    D_800D2360[i] = D_8009D9C8;
    return overlap;
}
'''


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--fitting',action='store_true');parser.add_argument('--loops',action='store_true')
    parser.add_argument('--counters',action='store_true');parser.add_argument('--shape',action='store_true')
    parser.add_argument('--placement',action='store_true');parser.add_argument('--lifetimes',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (lifetime_candidates() if args.lifetimes else placement_candidates() if args.placement else shape_candidates() if args.shape else counter_candidates() if args.counters else loop_candidates() if args.loops else fitting_candidates() if args.fitting else candidates() if args.screens else [('selected',FITTED)]):
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
