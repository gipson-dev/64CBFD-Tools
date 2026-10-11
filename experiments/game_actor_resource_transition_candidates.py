"""Complete actor identity/resource transition, signed height and live table reload."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x150837D4,0xB0C84,70
FUNCTION,SOURCE='func_150837D4','conker/src/game/generated_AEB40.c'
ORIGINAL='s32 func_150837D4() {\n    return 0;\n}'
DECLARATIONS='''extern u8 D_800CC2D0[];
extern u8 *D_800D1C90[];
extern u16 D_800C5A90[];
void func_15062BDC(u8 *, f32, f32);
s32 func_15084D00(u8 *);
u32 func_1502B020(u32 *, u32, ...);
'''
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,D_800D1C90=0x800D1C90,D_800C5A90=0x800C5A90,
    func_15062BDC=0x15062BDC,func_15084D00=0x15084D00,func_1502B020=0x1502B020)
SELECTED='''void func_150837D4(s32 slot, s32 identity, s32 unused) {
    u8 *actor;
    u8 **resource;
    u8 animation;

    actor = D_800CC2D0 + (u32)slot * 0x32C;
    actor[4] = identity;
    if (identity == 255) {
        *(s16 *)(actor + 0xE4) = 0;
        *(s16 *)(actor + 0xE6) = 0;
        *(s16 *)(actor + 0xE8) = 0;
        *(s16 *)(actor + 0xD2) = 70;
        *(s16 *)(actor + 0xD4) = 70;
        *(s16 *)(actor + 0xD6) = 0;
        *(s16 *)(actor + 0x160) = 0;
        *(f32 *)(actor + 0xC8) = 0.0f;
    } else {
        resource = &D_800D1C90[identity];
        *(f32 *)(actor + 0xC8) = (f32)*(s16 *)(*resource + 6);
        func_15062BDC(actor, *(f32 *)(actor + 0x14C), *(f32 *)(actor + 0x150));
        actor[5] = (*resource)[0x12];
    }
    animation = func_15084D00(actor);
    actor[6] = animation;
    if (D_800C5A90[animation] != 0) {
        *(u32 *)(actor + 0x58) = func_1502B020(NULL, 2, 2, animation);
    }
}'''


def candidates():
    yield 'selected',SELECTED
    for width in ('u8','s32','u32'):
        body=SELECTED.replace('u8 animation;',width+' animation;')
        if width!='u8':body=body.replace('animation = func_15084D00(actor);','animation = func_15084D00(actor) & 255;')
        yield 'animation-'+width,body
    yield 'argument-address',SELECTED.replace('    u8 *actor;', '    u8 *actor;\n    f32 xz, y;').replace(
        '        *(f32 *)(actor + 0xC8) = (f32)*(s16 *)(*resource + 6);',
        '        xz = *(f32 *)(actor + 0x14C);\n        *(f32 *)(actor + 0xC8) = (f32)*(s16 *)(*resource + 6);\n        y = *(f32 *)(actor + 0x150);').replace(
        'func_15062BDC(actor, *(f32 *)(actor + 0x14C), *(f32 *)(actor + 0x150));','func_15062BDC(actor, xz, y);')
    yield 'resource-local',SELECTED.replace('    u8 **resource;', '    u8 **resource;\n    u8 *definition;').replace(
        '        *(f32 *)(actor + 0xC8) = (f32)*(s16 *)(*resource + 6);',
        '        definition = *resource;\n        *(f32 *)(actor + 0xC8) = (f32)*(s16 *)(definition + 6);')
    yield 'pointer-width',SELECTED.replace('u8 animation;', 's32 animation;').replace(
        'animation = func_15084D00(actor);','animation = (u8)func_15084D00(actor);')
    for cast in ('(u8)', '(u32)', ''):
        body=SELECTED.replace('    u8 animation;\n','').replace('animation','identity').replace(
            'identity = func_15084D00(actor);','identity = '+cast+'func_15084D00(actor)'+
            (' & 255' if cast!='(u8)' else '')+';')
        yield 'reused-identity-'+str(len(cast)),body
    for order in ('    u8 **resource;\n    u8 animation;\n    u8 *actor;',
            '    u8 animation;\n    u8 *actor;\n    u8 **resource;'):
        yield 'order-'+str(order.index('actor')),SELECTED.replace(
            '    u8 *actor;\n    u8 **resource;\n    u8 animation;',order)
    reused=SELECTED.replace('    u8 animation;\n','').replace('animation','identity').replace(
        '    identity = func_15084D00(actor);\n    actor[6] = identity;',
        '    identity = actor[6] = func_15084D00(actor);')
    yield 'chain-identity',reused
    for width in ('u8','s32'):
        body=SELECTED.replace('    u8 **resource;\n','').replace('    } else {',
            '    } else {\n        u8 **resource;').replace('u8 animation;',width+' animation;')
        yield 'scoped-'+width,body
        yield 'scoped-chain-'+width,body.replace('    animation = func_15084D00(actor);\n    actor[6] = animation;',
            '    animation = actor[6] = func_15084D00(actor);')
    for variable in ('slot','unused'):
        for chain in (False,True):
            body=SELECTED.replace('    u8 animation;\n','').replace('animation',variable).replace(
                variable+' = func_15084D00(actor);',variable+' = (u8)func_15084D00(actor);')
            if chain:body=body.replace(variable+' = (u8)func_15084D00(actor);\n    actor[6] = '+variable+';',
                variable+' = actor[6] = func_15084D00(actor);')
            yield 'reuse-'+variable+'-'+str(chain),body
    for width in ('u8','s32'):
        yield 'register-'+width,SELECTED.replace('u8 animation;', 'register '+width+' animation;').replace(
            'animation = func_15084D00(actor);','animation = (u8)func_15084D00(actor);')
    base=SELECTED.replace('    u8 animation;\n','').replace('animation','identity')
    yield 'mask-at-uses',base.replace('D_800C5A90[identity]', 'D_800C5A90[(u8)identity]').replace(
        'NULL, 2, 2, identity)', 'NULL, 2, 2, (u8)identity)')
    yield 'mask-after-store',base.replace('    actor[6] = identity;',
        '    actor[6] = identity;\n    identity &= 255;')
    yield 'cast-after-store',base.replace('    actor[6] = identity;',
        '    actor[6] = identity;\n    identity = (u8)identity;')
    base=base.replace('    actor[6] = identity;',
        '    actor[6] = identity;\n    identity &= 255;')
    for width in ('s32', 'u32', 'u8'):
        yield 'separate-result-'+width,base.replace('    u8 **resource;',
            '    u8 **resource;\n    '+width+' result;').replace(
            '    identity = func_15084D00(actor);\n    actor[6] = identity;\n    identity &= 255;',
            '    result = func_15084D00(actor);\n    actor[6] = result;\n    identity = (u8)result;')
    yield 'early-return',base.replace('    if (D_800C5A90[identity] != 0) {',
        '    if (D_800C5A90[identity] == 0) return;\n    {')
    yield 'word-identity',base.replace('s32 identity', 'u32 identity')
    yield 'saved-count',base.replace('    u8 **resource;',
        '    u8 **resource;\n    u16 count;').replace(
        '    if (D_800C5A90[identity] != 0) {',
        '    count = D_800C5A90[identity];\n    if (count != 0) {')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def copied_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale actor resource transition owner')
    declarations=DECLARATIONS.replace('extern u8 D_800CC2D0[];\n','')
    return before.replace(ORIGINAL,declarations+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-resource-transition'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
