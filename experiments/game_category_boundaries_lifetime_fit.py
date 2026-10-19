"""Fit initializer order and actual scratch lifetimes without changing production."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_category_boundaries_candidates as source

BUILD=source.BUILD+'/lifetime-fit'
SOURCE,OWNER,FUNCTION,ENTRY,ROM,WORDS=source.SOURCE,source.OWNER,source.FUNCTION,source.ENTRY,source.ROM,source.WORDS
INPUTS,freeze,payload,compile_profile,link_owner=source.INPUTS,source.freeze,source.payload,source.compile_profile,source.link_owner
BASE_RECOVERY=source.recovered_owner


def recovered_owner(before,body=None):
    old='s32 func_15085BE8();'
    if before.count(old)!=1:raise ValueError('Unknown category-boundary forward declaration')
    return BASE_RECOVERY(before,SELECTED if body is None else body).replace(old,'s32 func_15085BE8(void);')


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    with patch.object(source,'recovered_owner',recovered_owner):
        return source.compile_candidate(root,out,name,SELECTED if body is None else body,normal,whole)


def candidates():
    body=source.FITTED.replace('    f32 minimum[6];\n    f32 maximum[6];\n','').replace(
        '    s32 count;\n    f32 height;',
        '    f32 initialMaximum = D_8009D9C0;\n    f32 initialMinimum = D_8009D9C4;')
    body=body.replace('    f32 upper;', '    f32 minimum[6];\n    f32 maximum[6];\n    f32 upper;')
    body=body.replace('minimum[i] = D_8009D9C4','minimum[i] = initialMinimum').replace(
        'maximum[i] = D_8009D9C0','maximum[i] = initialMaximum').replace('height','upper')
    body=body.replace('    count = D_80087290 * 16;\n','').replace('i < count; i += 16','i < D_80087290 * 16; i += 16')
    yield 'cached-indexed',body
    row_do=body.replace('    if (D_80087290 > 0) {','    i = 0;\n    if (D_80087290 > 0) {').replace(
        '        for (i = 0; i < D_80087290 * 16; i += 16, row += 16) {','        do {').replace(
        '            category = row[6];\n            upper = (f32)*(s16 *)(row + 2);',
        '            upper = (f32)*(s16 *)(row + 2);\n            category = row[6];\n            i += 16;').replace(
        '        }\n    }\n    D_800D2358 = 0;',
        '            row += 16;\n        } while (i < D_80087290 * 16);\n    }\n    D_800D2358 = 0;')
    yield 'cached-row-do',row_do
    yield 'cached-row-do-inner-zero',row_do.replace('        row = D_800D2350;','        i = 0;\n        row = D_800D2350;')
    one_cache=body.replace('    f32 initialMinimum = D_8009D9C4;\n','').replace('minimum[i] = initialMinimum','minimum[i] = D_8009D9C4')
    yield 'cached-maximum-only',one_cache
    logical=body.replace('        row = D_800D2350;\n        for (i = 0; i < D_80087290 * 16; i += 16, row += 16) {',
        '        for (i = 0; i < D_80087290; i++) {\n            row = D_800D2350 + i * 16;')
    yield 'logical-row-index',logical
    yield 'logical-height-first',logical.replace('            category = row[6];\n            upper = (f32)*(s16 *)(row + 2);',
        '            upper = (f32)*(s16 *)(row + 2);\n            category = row[6];')
    for label,unit in (('logical',logical),('offset',body)):
        single=unit.replace('    f32 initialMinimum = D_8009D9C4;\n','').replace('minimum[i] = initialMinimum','minimum[i] = D_8009D9C4')
        yield label+'-one-cache',single
        yield label+'-one-gate',single.replace('    if (D_80087290 > 0) {\n','').replace(
            '        }\n    }\n    D_800D2358 = 0;','        }\n    D_800D2358 = 0;')


def reuse_candidates():
    base=dict(candidates())['logical-one-gate']
    reused=base.replace('    f32 initialMaximum = D_8009D9C0;\n','').replace(
        '    for (i = 0; i < 6; i++) {','    upper = D_8009D9C0;\n    for (i = 0; i < 6; i++) {',1).replace(
        'maximum[i] = initialMaximum','maximum[i] = upper')
    yield 'reuse-upper-initializer',reused
    yield 'reuse-upper-byte-category',reused.replace('    s32 category;','    u8 category;')
    both=reused.replace('    upper = D_8009D9C0;','    upper = D_8009D9C0;\n    lower = D_8009D9C4;').replace(
        'minimum[i] = D_8009D9C4','minimum[i] = lower')
    yield 'reuse-both-initializers',both
    yield 'reuse-both-byte-category',both.replace('    s32 category;','    u8 category;')


def scratch_candidates():
    base=dict(reuse_candidates())['reuse-both-byte-category']
    arrays='    f32 minimum[6];\n    f32 maximum[6];\n'
    last=base.replace(arrays,'').replace('    u8 *row;','    u8 *row;\n'+arrays.rstrip())
    yield 'arrays-last',last
    inline=last.replace('    f32 lower;\n','').replace('    f32 upper;','    f32 height;').replace(
        '    upper = D_8009D9C0;\n    lower = D_8009D9C4;',
        '    height = D_8009D9C0;').replace('minimum[i] = lower','minimum[i] = D_8009D9C4').replace(
        'maximum[i] = upper','maximum[i] = height')
    start=inline.index('    D_800D2358 = 0;')
    inline=inline[:start].replace('upper','height')+inline[start:]
    inline=inline.replace('        upper = maximum[D_800D237C[i]];\n        lower = minimum[D_800D237C[i + 1]];\n        D_800D2360[i] = (lower + upper) * 0.5f;\n        if (lower < upper)',
        '        D_800D2360[i] = (minimum[D_800D237C[i + 1]] + maximum[D_800D237C[i]]) * 0.5f;\n        if (minimum[D_800D237C[i + 1]] < maximum[D_800D237C[i]])')
    yield 'inline-midpoints',inline
    yield 'inline-word-category',inline.replace('    u8 category;','    s32 category;')


SELECTED='''/* Build category height boundaries and report overlapping adjacent ranges. */
s32 func_15085BE8(void) {
    s32 overlap = 0;
    s32 i;
    u8 category;
    f32 lower;
    f32 upper;
    u8 *row;
    f32 minimum[6];
    f32 maximum[6];

    upper = D_8009D9C0;
    lower = D_8009D9C4;
    for (i = 0; i < 6; i++) {
        minimum[i] = lower;
        maximum[i] = upper;
    }
    for (i = 0; i < D_80087290; i++) {
        row = D_800D2350 + i * 16;
        category = row[6];
        upper = (f32)*(s16 *)(row + 2);
        if (upper < minimum[category]) {
            minimum[category] = upper;
        }
        if (maximum[category] < upper) {
            maximum[category] = upper;
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
    parser.add_argument('--filter',default='');parser.add_argument('--reuse',action='store_true')
    parser.add_argument('--scratch',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in (scratch_candidates() if args.scratch else reuse_candidates() if args.reuse else candidates() if args.screens else [('selected',SELECTED)]):
        if args.filter not in name:continue
        _,_,row=source.compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
