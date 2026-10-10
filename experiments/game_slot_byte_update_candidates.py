"""Measure the complete two-byte updater, retaining callback-sensitive reloads."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502EEF4, 0x5C3A4, 74
FUNCTION = 'func_1502EEF4'
SOURCE = 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502EEF4() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 D_800CC2D0[];
s32 func_1502EE8C(s32, s32);
void func_1507E3C0(u8 *);
'''
SYMBOLS = dict(D_800CC2D0=0x800CC2D0,func_1502EE8C=0x1502EE8C,func_1507E3C0=0x1507E3C0)
BASE = '''void func_1502EEF4(s32 slot) {
    u8 *actor;
    s32 index;
    u8 state;

    actor = (u8 *)D_800CC2D0 + slot * 0x32C;
    for (index = 0; index != 2; index++, actor++) {
        if (actor[0x6C] < 10) {
            state = func_1502EE8C(slot, index);
            if (state == 0) {
                if (actor[0x6C] > 0) {
                    actor[0x6C]--;
                }
            } else if (state == 1) {
                if (actor[0x6C] < 2) {
                    actor[0x6C]++;
                }
            } else {
                actor[0x6C] = 1;
            }
        }
    }
    func_1507E3C0((u8 *)D_800CC2D0 + slot * 0x32C);
}'''
SELECTED = BASE.replace('slot * 0x32C', '(u32)slot * 0x32C').replace(
    '    func_1507E3C0((u8 *)D_800CC2D0 + (u32)slot * 0x32C);',
    '    /* Keep the final slot lookup separate from the advanced byte cursor. */\n'
    '    func_1507E3C0((u8 *)D_800CC2D0 + ((u32)slot * 0xCB << 2));')


def candidates():
    yield 'selected',SELECTED
    yield 'pointer-spill-baseline',BASE
    yield 'selected-unsigned-slot',SELECTED.replace('s32 slot)','u32 slot)')
    yield 'selected-register-slot',SELECTED.replace('s32 slot)','register s32 slot)')
    yield 'selected-index-first',SELECTED.replace('    u8 *actor;\n    s32 index;', '    s32 index;\n    u8 *actor;')
    yield 'selected-unsigned-literal',SELECTED.replace('(u32)slot * 0xCB', 'slot * 0xCBu')
    yield 's32-state',BASE.replace('u8 state;', 's32 state;').replace('state = func_1502EE8C(slot, index);',
        'state = (u8)func_1502EE8C(slot, index);')
    yield 'register-slot',BASE.replace('s32 slot)', 'register s32 slot)')
    yield 'register-index',BASE.replace('s32 index;', 'register s32 index;')
    yield 'register-actor',BASE.replace('u8 *actor;', 'register u8 *actor;')
    yield 'less-count',BASE.replace('index != 2', 'index < 2')
    yield 'while-loop',BASE.replace('    for (index = 0; index != 2; index++, actor++) {',
        '    index = 0;\n    do {').replace('    }\n    func_1507E3C0',
        '        index++;\n        actor++;\n    } while (index != 2);\n    func_1507E3C0')
    yield 'switch-state',BASE.replace('            if (state == 0) {', '            switch (state) {\n            case 0:').replace(
        '            } else if (state == 1) {', '                break;\n            case 1:').replace(
        '            } else {\n                actor[0x6C] = 1;', '                break;\n            default:\n                actor[0x6C] = 1;')
    yield 'integer-compare',BASE.replace('state == 1', 'state == (s32)1')
    yield 'byte-store',BASE.replace('actor[0x6C] = 1;', 'actor[0x6C] = (u8)1;')
    for name,address in (
        ('unsigned-final','(u8 *)((u32)D_800CC2D0 + (u32)slot * 0x32C)'),
        ('signed-final','(u8 *)((s32)D_800CC2D0 + slot * 0x32C)'),
        ('distributed-final','(u8 *)D_800CC2D0 + slot * 0x300 + slot * 0x2C'),
        ('shift-final','(u8 *)D_800CC2D0 + ((u32)slot << 10) - (u32)slot * 0xD4'),
        ('offset-final','(u8 *)D_800CC2D0 + ((u32)slot * 0xCB << 2)'),
        ('offset-signed-final','(u8 *)D_800CC2D0 + (slot * 0xCB << 2)'),
        ('offset-multiply-final','(u8 *)D_800CC2D0 + (slot * 0xCB) * 4'),
        ('index-final','(u8 *)&D_800CC2D0[slot]')):
        yield name,BASE.replace('(u8 *)D_800CC2D0 + slot * 0x32C);',address+');')
    yield 'unsigned-offset',BASE.replace('slot * 0x32C', '(u32)slot * 0x32C').replace(
        '(u8 *)D_800CC2D0 + (u32)slot * 0x32C);', '(u8 *)D_800CC2D0 + ((u32)slot * 0xCB << 2));')
    yield 'negative-cache-byte',BASE.replace('    u8 state;', '    u8 state, byte;').replace(
        '        if (actor[0x6C] < 10)', '        byte = actor[0x6C];\n        if (byte < 10)').replace(
        'if (actor[0x6C] > 0)', 'if (byte > 0)').replace('actor[0x6C]--;', 'actor[0x6C] = byte - 1;').replace(
        'if (actor[0x6C] < 2)', 'if (byte < 2)').replace('actor[0x6C]++;', 'actor[0x6C] = byte + 1;')
    yield 'negative-no-byte-mask',BASE.replace('u8 state;', 's32 state;')
    yield 'negative-gate',BASE.replace('actor[0x6C] < 10', 'actor[0x6C] <= 10')
    yield 'negative-one-iteration',BASE.replace('index != 2', 'index != 1')
    yield 'negative-final-pointer',BASE.replace('func_1507E3C0((u8 *)D_800CC2D0 + slot * 0x32C);', 'func_1507E3C0(actor);')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    declarations = DECLARATIONS
    if '&D_800CC2D0[slot]' in body:
        declarations = declarations.replace('extern u8 D_800CC2D0[];',
            'typedef struct { u8 bytes[0x32C]; } ActorSlot58F80;\nextern ActorSlot58F80 D_800CC2D0[];')
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
        RECORD='',DECLARATIONS=declarations,SYMBOLS=SYMBOLS):
        meta,words = compiler.compile_candidate(root,out,name,body,profile)
    frames = [(-word)&65535 for word in words if word>>16==0x27BD and word&0x8000]
    meta['frame'] = frames[0] if frames else 0
    return meta,words


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-slot-byte-update'
    records = []
    for name,body in candidates():
        for profile in compiler.PROFILES if name=='selected' else ('o2g3',):
            meta,_ = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
