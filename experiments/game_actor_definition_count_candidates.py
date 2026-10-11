"""Complete actor definition count, special identity and unsigned header size."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1507E968,0xABE18,32
FUNCTION,SOURCE='func_1507E968','conker/src/game/generated_AB760.c'
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_AB760/func_1507E968.s")'
DECLARATIONS='extern u8 *D_800D1C90[];\ns32 func_150849A0(u8 *);\n'
SYMBOLS=dict(func_150849A0=0x150849A0,D_800D1C90=0x800D1C90)
INITIAL='''s32 func_1507E968(u8 *actor) {
    s32 identity;
    u8 *archive;

    identity = actor[4];
    if (identity != 150) {
        identity = func_150849A0(actor);
    }
    if (identity != 255) {
        archive = D_800D1C90[identity];
        if (archive != 0) {
            archive -= 8;
            return *(u32 *)(archive + 4) / 10;
        }
    }
    return 0;
}'''
SELECTED='''s32 func_1507E968(u8 *actor) {
    s32 identity;
    u8 *archive;

    identity = actor[4] != 150 ? func_150849A0(actor) : actor[4];
    if (identity == 255) {
        return 0;
    }
    archive = D_800D1C90[identity];
    if (archive != 0) {
        archive -= 8;
        return *(u32 *)(archive + 4) / 10;
    }
    return 0;
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'if-nested',INITIAL
    yield 'header-direct',INITIAL.replace('            archive -= 8;\n            return *(u32 *)(archive + 4) / 10;',
        '            return *(u32 *)(archive - 4) / 10;')
    yield 'byte-identity',INITIAL.replace('s32 identity','u8 identity')
    yield 'word-identity',INITIAL.replace('s32 identity','u32 identity')
    yield 'signed-size',INITIAL.replace('*(u32 *)','*(s32 *)')
    opening='''    identity = actor[4];
    if (identity != 150) {
        identity = func_150849A0(actor);
    }'''
    early='''    if (identity == 255) {
        return 0;
    }
    archive = D_800D1C90[identity];
    if (archive != 0) {
        archive -= 8;
        return *(u32 *)(archive + 4) / 10;
    }
    return 0;'''
    for name,form in (
            ('ternary-repeat','    identity = actor[4] == 150 ? actor[4] : func_150849A0(actor);'),
            ('ternary-call-first','    identity = actor[4] != 150 ? func_150849A0(actor) : actor[4];'),
            ('ternary-local','    identity = actor[4];\n    identity = identity == 150 ? identity : func_150849A0(actor);'),
            ('ternary-literal','    identity = actor[4] == 150 ? 150 : func_150849A0(actor);'),
            ('if-else-local','    identity = actor[4];\n    if (identity == 150) {\n        identity = identity;\n    } else {\n        identity = func_150849A0(actor);\n    }')):
        source=INITIAL.replace(opening,form)
        yield name,source
        yield name+'-early',source[:source.index('    if (identity != 255)')]+early+'\n}'


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale actor definition count owner')
    return before.replace(ORIGINAL,body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-definition-count'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
