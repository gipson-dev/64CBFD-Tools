"""Complete alternate loader with retail ignored status and inverted NULL-free gates."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1503F62C,0x6CADC,99
FUNCTION,SOURCE='func_1503F62C','conker/src/game/generated_6C960.c'
ORIGINAL='s32 func_1503F62C() {\n    return 0;\n}'
RECORD=''
DECLARATIONS='''void *allocate_memory(s32, s32, s32, s32);
s32 func_1502FE10(s32, u8 **, u8 *, u8 **, u8 **, u8 **, u32 *);
void func_10004074(void *);
s32 func_1503F5B8(u8 *, s32, s32, f32, f32, s32);
'''
SYMBOLS=dict(allocate_memory=0x10003C40,bzero=0x100226F0,func_1502FE10=0x1502FE10,
    func_10004074=0x10004074,func_1503F5B8=0x1503F5B8)
BASE='''s32 func_1503F62C(s32 kind, s32 selector, u8 **records, u8 *count,
        u8 **source, u8 **transform, u8 **attached) {
    u32 recordCount;
    u8 *node;

    *attached = allocate_memory(0x3F8, 1, 2, 2);
    if (*attached == 0) {
        return 1;
    }
    bzero(*attached, 0x40);
    (*attached)[0x215] = 1;
    (*attached)[0x45] = 1;
    /* Retail ignores this status, including an unwritten recordCount on failure. */
    func_1502FE10(kind, records, count, source, transform,
        (u8 **)(*attached + 0x3F0), &recordCount);
    (*attached)[0x3F4] = recordCount;
    (*attached)[0x3F5] = selector;
    (*attached)[0x3F6] = 0;
    *(u8 **)(*attached + 0x3E8) = allocate_memory(recordCount << 6, 1, 2, 2);
    *(u8 **)(*attached + 0x3EC) = allocate_memory(recordCount << 6, 1, 2, 2);
    node = *attached;
    /* These inverted NULL-free gates are part of the original routine. */
    if (*(u8 **)(node + 0x3E8) == 0 || *(u8 **)(node + 0x3EC) == 0) {
        if (*(u8 **)(node + 0x3E8) == 0) {
            func_10004074(*(u8 **)(node + 0x3E8));
            node = *attached;
        }
        if (*(u8 **)(node + 0x3EC) == 0) {
            func_10004074(*(u8 **)(node + 0x3EC));
            node = *attached;
        }
        func_10004074(node);
        return 1;
    }
    func_1503F5B8(node, 1, 0, 1.0f, 0.0f, 0);
    return 0;
}'''
SELECTED=BASE.replace('    node = *attached;',
    '    kind = (s32)*attached;\n    node = (u8 *)kind;',1).replace(
    '            node = *attached;',
    '            kind = (s32)*attached;\n            node = (u8 *)kind;')


def candidates():
    yield 'selected',SELECTED
    yield 'separate-node',BASE
    yield 'node-first',SELECTED.replace('    u32 recordCount;\n    u8 *node;', '    u8 *node;\n    u32 recordCount;')
    yield 'signed-count',SELECTED.replace('u32 recordCount','s32 recordCount').replace('&recordCount','(u32 *)&recordCount')
    yield 'register-node',SELECTED.replace('    u8 *node;','    register u8 *node;')
    yield 'selector-byte',SELECTED.replace('s32 selector','u8 selector')
    yield 'success-first',SELECTED.replace('''    if (*(u8 **)(node + 0x3E8) == 0 || *(u8 **)(node + 0x3EC) == 0) {''',
        '''    if (*(u8 **)(node + 0x3E8) != 0 && *(u8 **)(node + 0x3EC) != 0) {
        func_1503F5B8(node, 1, 0, 1.0f, 0.0f, 0);
        return 0;
    } else {''').replace('''    func_1503F5B8(node, 1, 0, 1.0f, 0.0f, 0);
    return 0;''','')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale alternate loader owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-node-alternate-loader';records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
