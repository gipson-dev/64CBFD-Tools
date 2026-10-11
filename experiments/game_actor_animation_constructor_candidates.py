"""Recover the complete descriptor-driven constructor and both stacked O32 calls."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x15083568,0xB0A18,89
FUNCTION,SOURCE='func_15083568','conker/src/game/generated_AEB40.c'
ORIGINAL='s32 func_15083568() {\n    return 0;\n}'
HELPER_ORIGINAL='s32 func_15083AC8() {\n    return 0;\n}'
HELPER_SELECTED='''u8 *func_15083AC8(u8 *actor, s32 arg1, s32 arg2, s32 arg3,
    s32 arg4, s32 arg5, s32 arg6, s32 arg7, f32 scale) {
    return 0;
}'''
RECORD='''typedef struct {
    u8 *records;
    u8 count;
    u8 padding[3];
} AnimationDescriptor15083568;
'''
DECLARATIONS='''extern AnimationDescriptor15083568 D_80086CC4[];
u8 *func_15083AC8(u8 *, s32, s32, s32, s32, s32, s32, s32, f32);
u8 *func_15030AF4(u8 *, s32, s32, s32, s32, s32, s32, s32, s32, u8 *, s32, s32, s32);
'''
SYMBOLS=dict(D_80086CC4=0x80086CC4,func_15083AC8=0x15083AC8,func_15030AF4=0x15030AF4)
BASE='''u8 *func_15083568(u8 *actor, s32 animation, f32 scale, s32 mode) {
    AnimationDescriptor15083568 *descriptor;
    u8 *record;
    u8 *created = 0;
    s32 i;

    animation--;
    descriptor = &D_80086CC4[(u32)animation];
    record = descriptor->records;
    for (i = 0; i < descriptor->count; i++, record += 16) {
        if (record[3] == 0) {
            created = func_15083AC8(actor, record[1], record[0], 0,
                record[2], record[4], record[5], record[6], scale);
        } else {
            created = func_15030AF4(actor, record[0], record[1], record[7],
                record[4], record[5], mode, animation + 1, record[2],
                record + 8, record[3] == 2 ? record[6] : -1, record[14], record[15]);
        }
    }
    return created;
}'''
SELECTED='''u8 *func_15083568(u8 *actor, s32 animation, f32 scale, s32 mode) {
    AnimationDescriptor15083568 *descriptor;
    u8 *record;
    u8 *records;
    u8 *created = 0;
    s32 i;

    animation--;
    descriptor = &D_80086CC4[(u32)animation];
    records = descriptor->records;
    i = 0;
    if (descriptor->count > 0) {
        record = records;
        do {
            if (record[3] == 0) {
                created = func_15083AC8(actor, record[1], record[0], 0,
                    record[2], record[4], record[5], record[6], scale);
            } else {
                created = func_15030AF4(actor, record[0], record[1], record[7],
                    record[4], record[5], mode, animation + 1, record[2],
                    record + 8, record[3] == 2 ? record[6] : -1, record[14], record[15]);
            }
            i++;
            record += 16;
        } while (i < descriptor->count);
    }
    return created;
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'linear-for',BASE
    yield 'signed-descriptor',SELECTED.replace('(u32)animation','animation')
    yield 'count-before-pointer',SELECTED.replace('    records = descriptor->records;\n    i = 0;',
        '    i = 0;\n    records = descriptor->records;')
    yield 'type-local',SELECTED.replace('    s32 i;','    s32 i;\n    s32 type;').replace(
        '        if (record[3] == 0)', '        type = record[3];\n        if (type == 0)').replace('record[3] == 2','type == 2')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1 or before.count(HELPER_ORIGINAL)!=1:
        raise ValueError('stale actor animation constructor owner')
    return before.replace(ORIGINAL,RECORD+DECLARATIONS+'\n'+body).replace(HELPER_ORIGINAL,HELPER_SELECTED)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-animation-constructor'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
