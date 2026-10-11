"""Complete default node resource loader, retained cache and seven output arguments."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502FE10,0x5D2C0,114
FUNCTION,SOURCE='func_1502FE10','conker/src/game/generated_5D2C0.c'
ORIGINAL='s32 func_1502FE10() {\n    return 0;\n}'
RECORD=''
DECLARATIONS='''extern u8 D_800DF7D0[];
extern s32 *D_800DF9B8[];
extern u8 *D_800E0148[];
void *func_1502B6BC(s32 *, s32, s32 *, s32, ...);
s32 func_1510CE60(void *, s32, s32, s32, s32 *);
void func_15168E54(void *, void *);
'''
SYMBOLS=dict(D_800DF7D0=0x800DF7D0,D_800DF9B8=0x800DF9B8,D_800E0148=0x800E0148,
    func_1502B6BC=0x1502B6BC,func_1510CE60=0x1510CE60,func_15168E54=0x15168E54)
BASE='''s32 func_1502FE10(s32 kind, u8 **records, u8 *count, u8 **source,
        u8 **transform, u8 **extra, u32 *extraCount) {
    u8 *header;
    u8 *references;
    s32 index;
    s32 offset;
    s32 *dependencies;

    references = &D_800DF7D0[kind];
    if (*references == 0) {
        header = func_1502B6BC(0, 0, 0, 2, 9, kind);
        if (header == 0) {
            return 1;
        }
        *records = *(u8 **)header;
        *count = *(u32 *)(header + 4) >> 2;
        index = 0;
        offset = 0;
        if (*count != 0) {
            dependencies = (s32 *)&D_800DF9B8[kind];
            do {
                *(u8 **)(*records + offset) += (u32)header;
                func_1510CE60(*(u8 **)(*records + offset), 0, 1, 0x3E, dependencies);
                func_15168E54(*(u8 **)(*records + offset), header);
                index++;
                offset += 4;
            } while (index < *count);
        }
        D_800E0148[kind] = header;
    } else {
        header = D_800E0148[kind];
        *records = *(u8 **)header;
        *count = *(u32 *)(header + 4) >> 2;
    }
    (*references)++;
    *source = header + 0x18;
    if (transform != 0) {
        *transform = *(u8 **)(header + 0x10);
    }
    if (extra != 0) {
        *extra = *(u8 **)(header + 8);
        if (extraCount != 0) {
            *extraCount = *(u32 *)(header + 0xC) >> 4;
        }
    }
    return 0;
}'''
SELECTED='''s32 func_1502FE10(s32 kind, u8 **records, u8 *count, u8 **source,
        u8 **transform, u8 **extra, u32 *extraCount) {
    u8 *header;
    s32 index;

    if (D_800DF7D0[kind] == 0) {
        header = func_1502B6BC(0, 0, 0, 2, 9, kind);
        if (header == 0) {
            return 1;
        }
        *records = *(u8 **)header;
        *count = *(u32 *)(header + 4) >> 2;
        index = 0;
        if (*count > 0) {
            do {
                *(u32 *)(*records + index * 4) += (u32)header;
                func_1510CE60(*(u8 **)(*records + index * 4), 0, 1, 0x3E,
                    (s32 *)&D_800DF9B8[kind]);
                func_15168E54(*(u8 **)(*records + index * 4), header);
                index++;
            } while (index < *count);
        }
        D_800E0148[kind] = header;
    } else {
        header = D_800E0148[kind];
        *records = *(u8 **)header;
        *count = *(u32 *)(header + 4) >> 2;
    }
    D_800DF7D0[kind]++;
    *source = header + 0x18;
    if (transform != 0) {
        *transform = *(u8 **)(header + 0x10);
    }
    if (extra != 0) {
        *extra = *(u8 **)(header + 8);
        if (extraCount != 0) {
            *extraCount = *(u32 *)(header + 0xC) >> 4;
        }
    }
    return 0;
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'explicit-locals',BASE
    yield 'index-first',BASE.replace('    u8 *header;\n    u8 *references;\n    s32 index;\n    s32 offset;',
        '    s32 offset;\n    s32 index;\n    u8 *header;\n    u8 *references;')
    yield 'integer-offset',BASE.replace('*(u8 **)(*records + offset) += (u32)header;',
        '*(u32 *)(*records + offset) += (u32)header;')
    yield 'for-loop',BASE.replace('''        index = 0;
        offset = 0;
        if (*count != 0) {''','''        offset = 0;
        if (*count != 0) {''').replace('''            do {''','''            for (index = 0; index < *count; index++) {''').replace(
        '                index++;\n','').replace('''            } while (index < *count);''','''            }''')
    yield 'register-header',SELECTED.replace('    u8 *header;','    register u8 *header;')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale default resource loader owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-node-resource-loader';records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
