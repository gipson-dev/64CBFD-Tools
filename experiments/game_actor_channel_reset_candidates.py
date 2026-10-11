"""Complete actor channel refresh/reset with unsigned fields and five-arg O32 ABI."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1507EABC,0xABF6C,28
FUNCTION,SOURCE='func_1507EABC','conker/src/game/generated_AB760.c'
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_AB760/func_1507EABC.s")'
DECLARATIONS='void func_1507E7E4(u8 *, u8, u8, u16, s32);\n'
SYMBOLS=dict(func_1507E7E4=0x1507E7E4)
SELECTED='''void func_1507EABC(u8 *actor) {
    func_1507E7E4(actor, actor[0x70], 3, 0xFFFF, 10);
    actor[0x71] = 0;
    *(u16 *)(actor + 0x72) = 0;
    if (actor[0x6C] >= 10) {
        actor[0x6C] = 0;
        actor[0x6A] = 0;
    }
    if (actor[0x6D] >= 10) {
        actor[0x6D] = 0;
        actor[0x6B] = 0;
    }
}'''


def candidates():
    yield 'selected',SELECTED
    for width in ('u8','s32','u32'):
        yield 'captured-'+width,SELECTED.replace('    func_1507E7E4',
            '    '+width+' first;\n\n    func_1507E7E4').replace(
            '    actor[0x71] = 0;', '    first = actor[0x6C];\n    actor[0x71] = 0;').replace(
            'actor[0x6C] >= 10', 'first >= 10')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale actor channel reset owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-channel-reset'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
