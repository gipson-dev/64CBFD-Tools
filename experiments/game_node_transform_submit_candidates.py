"""Recover the full attachment transform/submission routine and live selector."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1503F4B0,0x6C960,66
FUNCTION,SOURCE='func_1503F4B0','conker/src/game/generated_6C960.c'
ORIGINAL='s32 func_1503F4B0() {\n    return 0;\n}'
RECORD='#include "structs.h"\n'
DECLARATIONS='''extern u8 D_800BE9C0;
extern f32 D_800BE9A4;
void *allocate_memory(s32, s32, s32, s32);
void func_10004074(void *);
s32 func_1502D824();
void func_150A81D0(u8 **, void *, u8 *, u8 *, s32, s16 *, s32, s32);
void func_150A9984(u8 *, s32);
void func_1507BDB0(struct197 *, f32, struct127 *, s32);
'''
SYMBOLS=dict(D_800BE9C0=0x800BE9C0,D_800BE9A4=0x800BE9A4,
    allocate_memory=0x10003C40,func_1502D824=0x1502D824,
    func_150A81D0=0x150A81D0,func_150A9984=0x150A9984,
    func_1507BDB0=0x1507BDB0,func_10004074=0x10004074)
BASE='''void func_1503F4B0(u8 *node) {
    void *temporary = NULL;
    u8 *buffer;
    s16 scale;

    if (((void **)(node + 0x3E0))[D_800BE9C0] != NULL) {
        temporary = allocate_memory(0x320, 1, 2, 2);
        func_1502D824(node, 0, temporary);
        scale = 0x1000;
        buffer = ((u8 **)(node + 0x3E8))[D_800BE9C0];
        func_150A81D0(&buffer, ((void **)(node + 0x3E0))[D_800BE9C0],
            node, *(u8 **)(node + 0x3F0), node[0x3F4], &scale, 0, 0);
        func_150A9984(((u8 **)(node + 0x3E8))[D_800BE9C0], node[0x3F4]);
        node[0x3F6] = 1;
    }
    func_1507BDB0((struct197 *)node, D_800BE9A4, NULL, 0);
    if (temporary != NULL) {
        func_10004074(temporary);
    }
}'''
SELECTED=BASE.replace('    u8 *buffer;\n    s16 scale;',
    '    void *matrix;\n    s16 scale;\n    u8 *buffer;').replace(
    '        buffer = ((u8 **)(node + 0x3E8))[D_800BE9C0];',
    '        matrix = ((void **)(node + 0x3E0))[D_800BE9C0];\n        buffer = ((u8 **)(node + 0x3E8))[D_800BE9C0];').replace(
    'func_150A81D0(&buffer, ((void **)(node + 0x3E0))[D_800BE9C0],','func_150A81D0(&buffer, matrix,')


def candidates():
    yield 'selected',SELECTED
    yield 'uncaptured-matrix',BASE
    yield 'buffer-first',SELECTED.replace('    void *temporary = NULL;\n    void *matrix;\n    s16 scale;\n    u8 *buffer;',
        '    u8 *buffer;\n    void *temporary = NULL;\n    void *matrix;\n    s16 scale;')
    yield 'scale-first',SELECTED.replace('    void *temporary = NULL;\n    void *matrix;\n    s16 scale;\n    u8 *buffer;',
        '    s16 scale;\n    void *temporary = NULL;\n    void *matrix;\n    u8 *buffer;')
    yield 'separate-zero',SELECTED.replace('    void *temporary = NULL;','    void *temporary;').replace(
        '    if (((void **)', '    temporary = NULL;\n    if (((void **)',1)
    yield 'word-step',SELECTED.replace('node, D_800BE9A4, NULL, 0','node, *(f32 *)&D_800BE9A4, NULL, 0')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale transform submit owner')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+RECORD).replace(
        ORIGINAL,DECLARATIONS+'\n'+body).replace(
        '/* Non-matching placeholders for the text-only asm slice asm/6C960.s. */',
        '/* Recovered routines for the text-only asm slice asm/6C960.s. */')


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-node-transform-submit';records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
