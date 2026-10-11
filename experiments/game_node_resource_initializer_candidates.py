"""Complete loader selection, copy ownership, allocation failure and rollback."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502FFD8, 0x5D488, 96
FUNCTION, SOURCE = 'func_1502FFD8', 'conker/src/game/generated_5D2C0.c'
ORIGINAL = 's32 func_1502FFD8() {\n    return 0;\n}'
RECORD = ''
DECLARATIONS = '''s32 func_1502FE10();
s32 func_1503F62C();
void *allocate_memory(s32, s32, s32, s32);
void func_10004074(void *);
'''
SYMBOLS = dict(func_1502FE10=0x1502FE10, func_1503F62C=0x1503F62C,
    allocate_memory=0x10003C40, func_10004074=0x10004074, bcopy=0x10023A10)
EARLY = '''s32 func_1502FFD8(u8 *node, u8 *actor) {
    u8 *source;
    s32 size;
    u32 actorFlags;

    if (*(u8 **)(node + 0x24) != 0) {
        return 0;
    }
    if (*(s8 *)(node + 0x17) == -1) {
        if (func_1502FE10(node[1], (u8 **)(node + 0x24), node + 0x14,
                &source, (u8 **)(node + 0x30), 0, 0) != 0) {
            return 1;
        }
    } else {
        if (func_1503F62C(node[1], *(s8 *)(node + 0x17), (u8 **)(node + 0x24),
                node + 0x14, &source, (u8 **)(node + 0x30), (u8 **)(node + 0x48)) != 0) {
            return 1;
        }
    }
    size = (u32)*(u8 **)(node + 0x24) - (u32)source;
    actorFlags = actor[0x66];
    if (!(node[4] & 0x10) && (actorFlags & 0xC) == 8 && *(u8 **)(node + 0x30) != 0) {
        *(u8 **)(node + 0x28) = allocate_memory(size, 1, 2, 2);
        if (*(u8 **)(node + 0x28) == 0) {
            return 1;
        }
        *(u8 **)(node + 0x2C) = allocate_memory(size, 1, 2, 2);
        if (*(u8 **)(node + 0x2C) == 0) {
            func_10004074(*(u8 **)(node + 0x28));
            *(u8 **)(node + 0x28) = 0;
            return 1;
        }
        bcopy(source, *(u8 **)(node + 0x28), size);
        bcopy(source, *(u8 **)(node + 0x2C), size);
        node[8] = 1;
    } else {
        *(u8 **)(node + 0x28) = source;
        *(u8 **)(node + 0x2C) = source;
    }
    node[9] = 1;
    return 0;
}'''
OUTER = EARLY.replace('''    if (*(u8 **)(node + 0x24) != 0) {
        return 0;
    }''', '''    if (*(u8 **)(node + 0x24) == 0) {''').replace(
    '    node[9] = 1;\n    return 0;', '    node[9] = 1;\n    }\n    return 0;')
SELECTED = '''s32 func_1502FFD8(u8 *node, u8 *actor) {
    u8 *source;
    u32 actorFlags;
    s32 size;

    if (*(u8 **)(node + 0x24) == 0) {
        if (*(s8 *)(node + 0x17) == -1) {
            if (func_1502FE10(node[1], (u8 **)(node + 0x24), node + 0x14,
                    &source, (u8 **)(node + 0x30), 0, 0) != 0) {
                return 1;
            }
        } else {
            if (func_1503F62C(node[1], *(s8 *)(node + 0x17), (u8 **)(node + 0x24),
                    node + 0x14, &source, (u8 **)(node + 0x30), (u8 **)(node + 0x48)) != 0) {
                return 1;
            }
        }
        size = (u32)*(u8 **)(node + 0x24) - (u32)source;
        actorFlags = actor[0x66];
        if (!(node[4] & 0x10) && (actorFlags & 0xC) == 8 && *(u8 **)(node + 0x30) != 0) {
            *(u8 **)(node + 0x28) = allocate_memory(size, 1, 2, 2);
            if (*(u8 **)(node + 0x28) == 0) {
                return 1;
            }
            *(u8 **)(node + 0x2C) = allocate_memory(size, 1, 2, 2);
            if (*(u8 **)(node + 0x2C) == 0) {
                func_10004074(*(u8 **)(node + 0x28));
                *(u8 **)(node + 0x28) = 0;
                return 1;
            }
            bcopy(source, *(u8 **)(node + 0x28), size);
            bcopy(source, *(u8 **)(node + 0x2C), size);
            node[8] = 1;
        } else {
            *(u8 **)(node + 0x28) = source;
            *(u8 **)(node + 0x2C) = source;
        }
        node[9] = 1;
    }
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'early-return', EARLY
    yield 'register-node', SELECTED.replace('u8 *node,','register u8 *node,')
    yield 'volatile-size', SELECTED.replace('    s32 size;', '    volatile s32 size;')
    yield 'pointer-span', SELECTED.replace('(u32)*(u8 **)(node + 0x24) - (u32)source',
        '*(u8 **)(node + 0x24) - source')
    yield 'flags-first', SELECTED.replace('    size = (u32)*(u8 **)(node + 0x24) - (u32)source;\n    actorFlags = actor[0x66];',
        '    actorFlags = actor[0x66];\n    size = (u32)*(u8 **)(node + 0x24) - (u32)source;')
    yield 'byte-flags', SELECTED.replace('u32 actorFlags;', 'u8 actorFlags;')
    yield 'outer', OUTER
    yield 'outer-flags-first-local', OUTER.replace('    u8 *source;\n    s32 size;\n    u32 actorFlags;',
        '    u32 actorFlags;\n    u8 *source;\n    s32 size;')
    yield 'outer-source-last', OUTER.replace('    u8 *source;\n    s32 size;\n    u32 actorFlags;',
        '    u32 actorFlags;\n    s32 size;\n    u8 *source;')
    yield 'outer-no-flag-local', OUTER.replace('    u32 actorFlags;\n','').replace(
        '    actorFlags = actor[0x66];\n','').replace('(actorFlags & 0xC)', '(actor[0x66] & 0xC)')
    yield 'outer-register-flags', OUTER.replace('    u32 actorFlags;', '    register u32 actorFlags;')
    yield 'outer-register-size', OUTER.replace('    s32 size;', '    register s32 size;')
    yield 'outer-flags-before-size', OUTER.replace('    s32 size;\n    u32 actorFlags;',
        '    u32 actorFlags;\n    s32 size;')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1: raise ValueError('stale node resource initializer owner')
    return before.replace(ORIGINAL,'s32 func_1503F62C();\nvoid func_10004074(void *);\n\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-node-resource-initializer'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
