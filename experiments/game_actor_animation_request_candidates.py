"""Complete one-based animation request with a signed integer millisecond scale."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1507EA44,0xABEF4,30
FUNCTION,SOURCE='func_1507EA44','conker/src/game/generated_AB760.c'
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_AB760/func_1507EA44.s")'
DECLARATIONS='''extern f32 D_8009B8A0;
u8 *func_1507E9F8(u8 *, s32 *);
u8 *func_15083568(u8 *, s32, f32, s32);
'''
INSTALL_DECLARATIONS='''extern f32 D_8009B8A0;
u8 *func_15083568(u8 *, s32, f32, s32);
'''
SYMBOLS=dict(func_1507E9F8=0x1507E9F8,func_15083568=0x15083568,D_8009B8A0=0x8009B8A0)
SELECTED='''void func_1507EA44(u8 *actor, s32 index, s32 amount) {
    u8 *animations;

    if (index != 0) {
        animations = func_1507E9F8(actor, 0);
        if (animations != 0) {
            func_15083568(actor, animations[(u32)index - 1], (f32)amount * D_8009B8A0, 0);
        }
    }
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'signed-index-offset',SELECTED.replace('(u32)index - 1','index - 1')
    yield 'scale-first-local',SELECTED.replace('    u8 *animations;', '    u8 *animations;\n    f32 scale;').replace(
        '            func_15083568(actor, animations[(u32)index - 1], (f32)amount * D_8009B8A0, 0);',
        '            scale = (f32)amount * D_8009B8A0;\n            func_15083568(actor, animations[(u32)index - 1], scale, 0);')
    yield 'null-early',SELECTED.replace('        if (animations != 0) {',
        '        if (animations == 0) {\n            return;\n        }\n        {')
    yield 'zero-early',SELECTED.replace('    if (index != 0) {',
        '    if (index == 0) {\n        return;\n    }\n    {')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale actor animation request owner')
    return before.replace(ORIGINAL,INSTALL_DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-animation-request'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
