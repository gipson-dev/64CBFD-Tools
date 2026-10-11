"""Recover full node lifetime release, delayed queues and live list unlinking."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15030158, 0x5D608, 102
FUNCTION, SOURCE = 'func_15030158', 'conker/src/game/generated_5D2C0.c'
ORIGINAL = 's32 func_15030158() {\n    return 0;\n}'
RECORD = ''
DECLARATIONS = '''extern u8 *D_800C3EE0;
void func_15031C14(u8 *);
void func_10004074(void *);
void func_100043B4(void *, s32);
void func_1503F7B8(void *);
void func_1518CA04(s32);
'''
SYMBOLS = dict(D_800C3EE0=0x800C3EE0,func_15031C14=0x15031C14,func_10004074=0x10004074,
    func_100043B4=0x100043B4,func_1503F7B8=0x1503F7B8,func_1518CA04=0x1518CA04)
SELECTED = '''void func_15030158(u8 *node, s32 immediate) {
    if (immediate == 0) {
        func_15031C14(node);
    }
    if (node[9] != 0) {
        if (node[8] != 0) {
            if (immediate != 0) {
                func_10004074(*(u8 **)(node + 0x28));
                func_10004074(*(u8 **)(node + 0x2C));
            } else {
                func_100043B4(*(u8 **)(node + 0x28), 4);
                func_100043B4(*(u8 **)(node + 0x2C), 4);
            }
        }
        if (*(u8 **)(node + 0x48) != 0) {
            func_1503F7B8(*(u8 **)(node + 0x48));
        }
        func_1518CA04(node[1]);
    }
    if (*(u8 **)(node + 0x34) != 0) {
        if (immediate != 0) {
            func_10004074(*(u8 **)(node + 0x34));
        } else {
            func_100043B4(*(u8 **)(node + 0x34), 4);
        }
    }
    if (*(u8 **)(node + 0x44) != 0) {
        func_10004074(*(u8 **)(node + 0x44));
    }
    if (*(u8 **)(node + 0x4C) != 0) {
        if (immediate != 0) {
            func_10004074(*(u8 **)(node + 0x4C));
        } else {
            func_100043B4(*(u8 **)(node + 0x4C), 4);
        }
    }
    if (*(u8 **)(node + 0x50) != 0) {
        if (immediate != 0) {
            func_10004074(*(u8 **)(node + 0x50));
        } else {
            func_100043B4(*(u8 **)(node + 0x50), 4);
        }
    }
    if (node == D_800C3EE0) {
        D_800C3EE0 = *(u8 **)(node + 0x54);
    }
    if (*(u8 **)(node + 0x58) != 0) {
        *(u8 **)(*(u8 **)(node + 0x58) + 0x54) = *(u8 **)(node + 0x54);
    }
    if (*(u8 **)(node + 0x54) != 0) {
        *(u8 **)(*(u8 **)(node + 0x54) + 0x58) = *(u8 **)(node + 0x58);
    }
    func_10004074(node);
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'register-node',SELECTED.replace('u8 *node,','register u8 *node,')
    yield 'volatile-immediate',SELECTED.replace('s32 immediate','volatile s32 immediate')
    yield 'signed-byte-immediate',SELECTED.replace('s32 immediate','s8 immediate')
    yield 'unsigned-immediate',SELECTED.replace('s32 immediate','u32 immediate')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale node release owner')
    return before.replace(ORIGINAL,'void func_15031C14(u8 *);\nvoid func_100043B4(void *, s32);\n'
        'void func_1503F7B8(void *);\nvoid func_1518CA04(s32);\n\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-node-release';records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
