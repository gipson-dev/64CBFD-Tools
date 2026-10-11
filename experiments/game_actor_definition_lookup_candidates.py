"""Complete nullable actor definition lookup with full-word record indexing."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1507E908,0xABDB8,24
FUNCTION,SOURCE='func_1507E908','conker/src/game/generated_AB760.c'
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_AB760/func_1507E908.s")'
DECLARATIONS='extern u8 *D_800D1C90[];\ns32 func_150849A0(u8 *);\n'
SYMBOLS=dict(func_150849A0=0x150849A0,D_800D1C90=0x800D1C90)
SELECTED='''u8 *func_1507E908(u8 *actor, s32 index) {
    u8 *archive;
    u8 *records;

    archive = D_800D1C90[func_150849A0(actor)];
    if (archive != 0) {
        archive -= 8;
        records = *(u8 **)archive;
        if (records != 0) {
            return records + (u32)index * 10;
        }
    }
    return 0;
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'word-address',SELECTED.replace('records + (u32)index * 10',
        '(u8 *)((u32)records + (u32)index * 10)')
    yield 'no-header-cursor',SELECTED.replace('        archive -= 8;\n        records = *(u8 **)archive;',
        '        records = *(u8 **)(archive - 8);')
    yield 'signed-index',SELECTED.replace('(u32)index * 10','index * 10')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale actor definition lookup owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-definition-lookup'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
