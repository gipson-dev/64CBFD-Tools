"""Recover the full thirteen-argument node constructor, not just allocation."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15030AF4, 0x5DFA4, 152
FUNCTION, SOURCE = 'func_15030AF4', 'conker/src/game/generated_5D2C0.c'
ORIGINAL = 's32 func_15030AF4() {\n    return 0;\n}'
RECORD = ''
NODE = '''typedef struct AnimationNode15030AF4 {
    u8 group, kind, index, priority, flags, unused5, key, extra;
    u8 byte8, byte9;
    u16 x, y, z;
    u8 gap10[3], unused13, gap14, slot, mode, selector;
    s16 a18, a1A, duration, parent, joint, a22;
    s32 p24, p28, p2C, p30;
    u8 *matrix;
    s32 p38, p3C;
    f32 scale;
    u8 *values44, *attached48, *p4C, *p50;
    struct AnimationNode15030AF4 *next, *previous;
} AnimationNode15030AF4;
'''
DECLARATIONS = '''extern u8 *D_800C3EE0;
void *allocate_memory(s32, s32, s32, s32);
s32 func_1502FFD8();
s32 func_15030158();
void func_15031A50(u8 *, u8 *);
'''
SYMBOLS = dict(D_800C3EE0=0x800C3EE0, allocate_memory=0x10003C40,
    func_1502FFD8=0x1502FFD8, func_15030158=0x15030158, func_15031A50=0x15031A50)
SELECTED = '''u8 *func_15030AF4(u8 *actor, s32 kind, s32 index, s32 flags,
    s32 slot, s32 mode, s32 duration, s32 key, s32 extra, u16 *values,
    s32 selector, s32 parent, s32 joint) {
    u8 *node;
    u8 *next;
    s32 failed;

    if (actor[0x3B] == 0) {
        return 0;
    }
    if (!(flags & 8)) {
        node = D_800C3EE0;
        if (node != 0) {
            do {
                next = *(u8 **)(node + 0x54);
                if (actor[0x3B] == node[0] && key == node[6] && kind == node[1]) {
                    return 0;
                }
                node = next;
            } while (next != 0);
        }
    }
    node = allocate_memory(0x5C, 1, 0, 2);
    if (node == 0) {
        return 0;
    }
    failed = 0;
    if (D_800C3EE0 != 0) {
        *(u8 **)(D_800C3EE0 + 0x58) = node;
    }
    *(u8 **)(node + 0x54) = D_800C3EE0;
    *(u8 **)(node + 0x58) = 0;
    D_800C3EE0 = node;
    node[0] = actor[0x3B];
    node[1] = kind;
    *(s32 *)(node + 0x24) = 0;
    *(s32 *)(node + 0x28) = 0;
    *(s32 *)(node + 0x2C) = 0;
    *(s32 *)(node + 0x30) = 0;
    node[3] = 0xFF;
    *(u8 **)(node + 0x44) = 0;
    node[4] = flags;
    node[6] = key;
    *(f32 *)(node + 0x40) = 1.0f;
    node[2] = index;
    *(s32 *)(node + 0x38) = 0;
    *(s32 *)(node + 0x3C) = 0;
    node[8] = 0;
    node[9] = 0;
    *(s16 *)(node + 0x18) = 0;
    *(s16 *)(node + 0x1A) = 0;
    node[7] = extra;
    *(u16 *)(node + 0xA) = values[0];
    *(u16 *)(node + 0xC) = values[1];
    *(u16 *)(node + 0xE) = values[2];
    *(u8 **)(node + 0x48) = 0;
    node[0x17] = selector;
    node[0x16] = mode;
    node[0x15] = slot;
    *(s16 *)(node + 0x1E) = parent;
    node[0x13] = 0;
    *(u8 **)(node + 0x4C) = 0;
    *(u8 **)(node + 0x50) = 0;
    node[5] = 0;
    *(s16 *)(node + 0x22) = 0;
    *(s16 *)(node + 0x20) = joint;
    if (mode == 4 || (flags & 4)) {
        *(u8 **)(node + 0x34) = allocate_memory(0x80, 1, 2, 2);
        if (*(u8 **)(node + 0x34) == 0) {
            failed = 1;
        }
    } else {
        *(u8 **)(node + 0x34) = 0;
    }
    if (duration == 0) {
        *(s16 *)(node + 0x1C) = -1;
    } else {
        *(s16 *)(node + 0x1C) = duration;
    }
    if (failed == 0) {
        failed |= func_1502FFD8(node, actor);
    }
    if (failed != 0) {
        func_15030158(node, 1);
        return 0;
    }
    func_15031A50(node, actor);
    return node;
}'''
BASE = SELECTED
SELECTED = BASE.replace('*(s16 *)(node + 0x1C)', '*(u16 *)(node + 0x1C)').replace('= -1;', '= 0xFFFF;')
SELECTED = SELECTED.replace('u16 *values,','u8 *values,')
for _index in range(3):
    SELECTED = SELECTED.replace('values[%d]'%_index,'*(u16 *)(values + %d)'%(_index*2))


def candidates():
    yield 'selected', SELECTED
    yield 'pointer-first', SELECTED.replace('    u8 *node;\n    u8 *next;\n    s32 failed;',
        '    s32 failed;\n    u8 *node;\n    u8 *next;')
    yield 'cached-group', SELECTED.replace('    s32 failed;', '    s32 failed;\n    u32 group;').replace(
        '    if (actor[0x3B] == 0)', '    group = actor[0x3B];\n    if (group == 0)').replace(
        'if (actor[0x3B] == node[0]', 'if (group == node[0]')
    yield 'conditional-duration', SELECTED.replace('''    if (duration == 0) {
        *(s16 *)(node + 0x1C) = -1;
    } else {
        *(s16 *)(node + 0x1C) = duration;
    }''', '    *(s16 *)(node + 0x1C) = duration != 0 ? duration : -1;')
    yield 'typed-fields', typed(SELECTED)
    yield 'unsigned-duration', SELECTED.replace('= -1;', '= 0xFFFF;')
    yield 'duration-halfword', SELECTED.replace('*(s16 *)(node + 0x1C)', '*(u16 *)(node + 0x1C)').replace(
        '= -1;', '= 0xFFFF;')
    ordered = SELECTED.replace('    node[0] = actor[0x3B];\n    node[1] = kind;',
        '    node[1] = kind;\n    node[0] = actor[0x3B];')
    yield 'kind-before-group', ordered
    early = ordered.replace('    node[2] = index;\n', '').replace(
        '    node[0] = actor[0x3B];', '    node[0] = actor[0x3B];\n    node[2] = index;')
    yield 'index-early', early
    yield 'typed-ordered', typed(ordered)
    yield 'typed-index-early', typed(early)
    yield 'volatile-node', ordered.replace('    u8 *node;', '    volatile u8 *node;').replace(
        'func_15031A50(node, actor)', 'func_15031A50((u8 *)node, actor)').replace(
        'return node;', 'return (u8 *)node;').replace('D_800C3EE0 = node;', 'D_800C3EE0 = (u8 *)node;').replace(
        '*(u8 **)(D_800C3EE0 + 0x58) = node;', '*(u8 **)(D_800C3EE0 + 0x58) = (u8 *)node;')
    yield 'volatile-fields', typed(ordered).replace('    AnimationNode15030AF4 *node;',
        '    volatile AnimationNode15030AF4 *node;').replace('->previous = node;',
        '->previous = (AnimationNode15030AF4 *)node;')


def typed(body):
    names = {0:'group',1:'kind',2:'index',3:'priority',4:'flags',5:'unused5',6:'key',7:'extra',
        8:'byte8',9:'byte9',0xA:'x',0xC:'y',0xE:'z',0x13:'unused13',0x15:'slot',0x16:'mode',
        0x17:'selector',0x18:'a18',0x1A:'a1A',0x1C:'duration',0x1E:'parent',0x20:'joint',0x22:'a22',
        0x24:'p24',0x28:'p28',0x2C:'p2C',0x30:'p30',0x34:'matrix',0x38:'p38',0x3C:'p3C',
        0x40:'scale',0x44:'values44',0x48:'attached48',0x4C:'p4C',0x50:'p50',0x54:'next',0x58:'previous'}
    for offset,name in names.items():
        for value in (str(offset),'0x%X'%offset):
            body=body.replace('node['+value+']','node->'+name)
            for kind in ('u8 **','s32 *','f32 *','s16 *','u16 *'):
                body=body.replace('*('+kind+')(node + '+value+')','node->'+name)
    body=body.replace('    u8 *node;','    AnimationNode15030AF4 *node;').replace(
        '    u8 *next;','    AnimationNode15030AF4 *next;').replace('node = D_800C3EE0;',
        'node = (AnimationNode15030AF4 *)D_800C3EE0;').replace('node->next = D_800C3EE0;',
        'node->next = (AnimationNode15030AF4 *)D_800C3EE0;').replace(
        '*(u8 **)(D_800C3EE0 + 0x58) = node;', '((AnimationNode15030AF4 *)D_800C3EE0)->previous = node;').replace(
        'D_800C3EE0 = node;', 'D_800C3EE0 = (u8 *)node;').replace('func_15031A50(node, actor);',
        'func_15031A50((u8 *)node, actor);').replace('return node;', 'return (u8 *)node;')
    return NODE+body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale animation node constructor owner')
    return before.replace(ORIGINAL, 'void func_15031A50(u8 *, u8 *);\n\n' + body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-animation-node-constructor'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
