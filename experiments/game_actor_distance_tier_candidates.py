"""Recover signed view lookup, callback-sensitive distance tiers and final tier store."""
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502C6E8,0x59B98,163
FUNCTION,SOURCE='func_1502C6E8','conker/src/game/generated_58F80.c'
ORIGINAL='s32 func_1502C6E8() {\n    return 0;\n}'
DECLARATIONS='''extern u8 D_800CC2D0[],*D_800DBFF0;
extern u8 D_800BE616,D_800C35EA;
extern f32 D_80096DE0,D_80096DE4;
s32 func_150849A0(u8 *);
void func_150837D4(s32,s32,s32);
'''
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,D_800DBFF0=0x800DBFF0,D_800BE616=0x800BE616,
    D_800C35EA=0x800C35EA,D_80096DE0=0x80096DE0,D_80096DE4=0x80096DE4,
    func_150849A0=0x150849A0,func_150837D4=0x150837D4)
SELECTED='''void func_1502C6E8(s32 slot, s16 view, s32 unused) {
    u8 *actor;
    u8 *player;
    f32 thresholds[4];
    f32 delta, distance;
    s32 selector, identity, tier;

    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
    player = D_800DBFF0 + view * 0x9A0;
    if (actor[0x1C9] == 0 && actor[5] != 7) {
        thresholds[0] = 500.0f;
        thresholds[1] = D_80096DE0;
        thresholds[2] = D_80096DE4;
        thresholds[3] = 2000.0f;
        selector = actor[0x2C8] - 1;
        if (selector != -1) {
            identity = func_150849A0(actor);
            delta = *(f32 *)(player + 0x2F8) - *(f32 *)(actor + 0x14);
            distance = delta * delta;
            delta = *(f32 *)(player + 0x2FC) - *(f32 *)(actor + 0x18);
            distance = distance + delta * delta;
            delta = *(f32 *)(player + 0x300) - *(f32 *)(actor + 0x1C);
            distance = distance + delta * delta;
            if (distance < thresholds[0] * thresholds[0]) {
                tier = 0;
            } else if (distance < thresholds[1] * thresholds[1]) {
                tier = 1;
            } else if (distance < thresholds[2] * thresholds[2]) {
                tier = 2;
            } else if (distance < thresholds[3] * thresholds[3]) {
                tier = 3;
            } else {
                tier = 4;
            }
            if (tier >= 2 && *(f32 *)(actor + 0x3C) < 3.0f) {
                tier--;
            }
            if (identity != 0) {
                if (identity == 0x5A && tier == 0) {
                    tier = 1;
                }
            } else if (D_800BE616 != 0) {
                tier = 1;
            }
            if (D_800C35EA == 1) {
                tier = 0;
            }
            if (selector < tier) {
                tier = selector;
                if (selector < 0) {
                    tier = 0;
                }
            }
            if (tier != -1 && tier != actor[0x1C8]) {
                func_150837D4(slot, (*(u8 **)(actor + 0x2C4))[tier], 0);
                actor[0x1C8] = tier;
            }
        }
    }
}'''


def candidates():
    yield 'selected',SELECTED
    for types in itertools.product(('s32','volatile s32'),('s16','s32','volatile s16'),('s32','volatile s32')):
        body=SELECTED.replace('s32 slot, s16 view, s32 unused',
            '%s slot, %s view, %s unused'%types)
        yield 'arguments-'+'-'.join(t.replace(' ','_') for t in types),body
    yield 'captured-prepare',SELECTED.replace('    s32 selector, identity, tier;',
        '    s32 selector, identity, tier;\n    u32 prepare;').replace(
        '    player = D_800DBFF0 + view * 0x9A0;',
        '    prepare = actor[0x1C9];\n    player = D_800DBFF0 + view * 0x9A0;').replace(
        'actor[0x1C9] == 0','prepare == 0')
    yield 'volatile-player-pointer',SELECTED.replace('player = D_800DBFF0',
        'player = *(u8 *volatile *)&D_800DBFF0')
    named=SELECTED.replace('f32 delta, distance;','f32 x, y, z, distance;').replace(
        'delta = *(f32 *)(player + 0x2F8)','x = *(f32 *)(player + 0x2F8)').replace(
        'delta = *(f32 *)(player + 0x2FC)','y = *(f32 *)(player + 0x2FC)').replace(
        'delta = *(f32 *)(player + 0x300)','z = *(f32 *)(player + 0x300)').replace(
        'distance = delta * delta;','distance = x * x;').replace(
        'distance = distance + delta * delta;', 'distance = distance + y * y;',1).replace(
        'distance = distance + delta * delta;','distance = distance + z * z;')
    yield 'named-deltas',named
    yield 'signed-slot',SELECTED.replace('(u32)slot','slot')
    squared=SELECTED.replace('distance = distance + delta * delta;',
        'delta = delta * delta;\n            distance = distance + delta;')
    yield 'squared-delta',squared
    early=SELECTED.replace('    if (actor[0x1C9] == 0 && actor[5] != 7) {',
        '    if (actor[0x1C9] != 0 || actor[5] == 7) { return; }\n    {').replace(
        '        if (selector != -1) {','        if (selector == -1) { return; }\n        {')
    yield 'early-returns',early
    square=early.replace('f32 delta, distance;','f32 delta, distance, square;').replace(
        'distance = distance + delta * delta;',
        'square = delta * delta;\n            distance = distance + square;')
    yield 'early-square-local',square
    yield 'early-square-compound',square.replace('square = delta * delta;',
        'square = delta;\n            square *= square;')
    yield 'named-early-returns',named.replace('    if (actor[0x1C9] == 0 && actor[5] != 7) {',
        '    if (actor[0x1C9] != 0 || actor[5] == 7) { return; }\n    {').replace(
        '        if (selector != -1) {','        if (selector == -1) { return; }\n        {')
    declarations=('    u8 *actor;\n','    u8 *player;\n','    f32 thresholds[4];\n',
        '    f32 delta, distance;\n','    s32 selector, identity, tier;\n')
    block=''.join(declarations)
    for index,order in enumerate(itertools.permutations((0,1,2,4))):
        yield 'declarations-%02d'%index,SELECTED.replace(block,
            ''.join(declarations[i] for i in (*order,3)))
    for name,body in (
            ('volatile-thresholds',SELECTED.replace('f32 thresholds[4];','volatile f32 thresholds[4];')),
            ('volatile-selector-load',SELECTED.replace('actor[0x2C8] - 1','*(volatile u8 *)(actor + 0x2C8) - 1')),
            ('squared-volatile-selector',squared.replace('actor[0x2C8] - 1',
                '*(volatile u8 *)(actor + 0x2C8) - 1')),
            ('squared-volatile-thresholds',squared.replace('f32 thresholds[4];','volatile f32 thresholds[4];')),
            ('squared-compound',squared.replace('distance = distance + delta;','distance += delta;')),
            ('selector-reused-view',squared.replace('s32 selector, identity, tier;','s32 identity, tier;').replace(
                'selector = actor[0x2C8] - 1;','view = actor[0x2C8] - 1;').replace('selector','view'))):
        yield name,body
    for name,old,new in (
            ('negative-state-gate','actor[5] != 7','actor[5] == 7'),
            ('negative-zero-based-selector','actor[0x2C8] - 1','actor[0x2C8]'),
            ('negative-inclusive-distance','distance < thresholds','distance <= thresholds'),
            ('negative-no-speed-adjust','tier--;','tier = tier;'),
            ('negative-no-clamp','if (selector < tier)','if (0)'),
            ('negative-wrong-tier-store','actor[0x1C8] = tier;','actor[0x1C9] = tier;')):
        yield name,SELECTED.replace(old,new)


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word>>16==0x27BD and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def install(before,body=SELECTED):
    assert before.count(ORIGINAL)==1
    declarations='''extern u8 *D_800DBFF0;
extern u8 D_800BE616, D_800C35EA;
extern f32 D_80096DE0, D_80096DE4;
s32 func_150849A0(u8 *);
void func_150837D4(s32, s32, s32);
'''
    return before.replace(ORIGINAL,declarations+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-distance-tier'
    records=[]
    for name,body in candidates():
        for profile in compiler.PROFILES if name=='selected' else ('o2g3',):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
