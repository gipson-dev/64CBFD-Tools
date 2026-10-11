"""Recover the complete callback-aware active-record matrix rebuild."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503E82C, 0x6BCDC, 138
FUNCTION, SOURCE = 'func_1503E82C', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503E82C() {\n    return 0;\n}'
PROTOTYPE, RECOVERED_PROTOTYPE = 's32 func_1503E82C();', 'void func_1503E82C(s32);'
LOCAL_DECLARATIONS = '''void func_150A7DA0(f32 [4][4], u32, u32, u32);
void func_150A8050(f32 [4][4], f32, f32, f32);
void func_150A7CB0(u32 *, u32, u32, u32);
void func_15043EC8(f32 [4][4], f32, f32, f32, f32, f32, f32);
'''
DECLARATIONS = '''#include "variables.h"
extern u8 D_80098914[];
extern s8 *D_80084454[];
void func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);
'''+LOCAL_DECLARATIONS
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800C6660=0x800C6660,
    D_80098914=0x80098914, D_80084454=0x80084454, func_150A7DA0=0x150A7DA0,
    func_150A8050=0x150A8050, func_150A7CB0=0x150A7CB0,
    func_150A7A48=0x150A7A48, func_15043EC8=0x15043EC8)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503E82C(s32 slot) {
    struct127 *actor;
    struct106 *record;
    struct04 *element;
    f32 (*destination)[4];
    s8 *types;
    s32 count;
    s32 index;
    s32 type;
    f32 matrix[4][4];

    actor = &D_800CC2D0[slot];
    if (actor->unk1D4 != NULL) {
        record = &D_800C6660[slot];
        count = D_80098914[((u8 *)record)[0xE]];
        types = D_80084454[((u8 *)record)[0xE]];
        for (index = 0; index < count; index++) {
            if (types[index] != -2) {
                element = (struct04 *)record->unk0 + index;
                if (element->unk64 != 0) {
                    type = D_80084454[((u8 *)record)[0xE]][index];
                    destination = ((f32 (*)[4][4])actor->unk1D4)[index];
                    if (type != -1) {
                        func_150A7DA0(matrix, ((u32 *)element)[9], ((u32 *)element)[10], ((u32 *)element)[11]);
                        func_150A7A48(matrix, ((f32 (*)[4][4])actor->unk1D4)[type], matrix);
                        element = (struct04 *)record->unk0 + index;
                        func_150A8050(destination, ((f32 *)element)[12], ((f32 *)element)[13], ((f32 *)element)[14]);
                        func_150A7A48(destination, matrix, destination);
                        element = (struct04 *)record->unk0 + index;
                        func_150A7CB0((u32 *)matrix, element->unk3C, element->unk40, element->unk44);
                        func_150A7A48(matrix, destination, destination);
                    } else {
                        func_150A8050(destination, ((f32 *)element)[12], ((f32 *)element)[13], ((f32 *)element)[14]);
                        element = (struct04 *)record->unk0 + index;
                        func_15043EC8(destination, ((f32 *)element)[15], ((f32 *)element)[16], ((f32 *)element)[17],
                            ((f32 *)element)[9], ((f32 *)element)[10], ((f32 *)element)[11]);
                    }
                }
            }
        }
    }
}'''
SWITCH = BASE.replace('            if (types[index] != -2) {',
    '            switch (types[index]) {\n            case -2:\n                break;\n            default:').replace(
    '                }\n            }\n        }', '                }\n                break;\n            }\n        }')
ORDERED = SWITCH.replace(
    '                    type = D_80084454[((u8 *)record)[0xE]][index];\n                    destination = ((f32 (*)[4][4])actor->unk1D4)[index];',
    '                    destination = ((f32 (*)[4][4])actor->unk1D4)[index];\n                    type = D_80084454[((u8 *)record)[0xE]][index];')
INLINE_BOTH = ORDERED.replace('    struct106 *record;\n', '').replace('        record = &D_800C6660[slot];\n', '').replace(
    '((u8 *)record)[0xE]', '((u8 *)&D_800C6660[slot])[0xE]').replace('record->unk0', 'D_800C6660[slot].unk0').replace(
    '    struct127 *actor;\n', '').replace('    actor = &D_800CC2D0[slot];\n', '').replace('actor->unk1D4', 'D_800CC2D0[slot].unk1D4')
COUNT_FIRST = INLINE_BOTH.replace('    s32 count;\n', '').replace('    struct04 *element;', '    s32 count;\n    struct04 *element;')
SELECTED = COUNT_FIRST.replace('    struct04 *element;\n', '').replace('    if (D_800CC2D0[slot].unk1D4 != NULL) {',
    '    if (D_800CC2D0[slot].unk1D4 != NULL) {\n        struct04 *element;')


def candidates():
    yield 'selected', SELECTED
    yield 'flat', BASE
    yield 'cursor', BASE.replace('index++)', 'index++, types++)').replace('types[index] != -2', '*types != -2')
    yield 'matrix-first', BASE.replace('    f32 matrix[4][4];\n', '').replace('    struct127 *actor;',
        '    f32 matrix[4][4];\n    struct127 *actor;')
    yield 'count-first', BASE.replace('    s32 count;\n', '').replace('    struct127 *actor;',
        '    s32 count;\n    struct127 *actor;')
    yield 'actor-initialized', BASE.replace('    struct127 *actor;',
        '    struct127 *actor = &D_800CC2D0[slot];').replace('    actor = &D_800CC2D0[slot];\n', '')
    for local in ('s32 count;', 's32 type;', 'struct127 *actor;', 'struct106 *record;', 'f32 matrix[4][4];'):
        yield 'switch-first-'+local.split()[-1].replace(';', '').replace('*', '').replace('[4][4]', ''), SWITCH.replace(
            '    '+local+'\n', '').replace('    struct127 *actor;' if local != 'struct127 *actor;' else '    struct106 *record;',
                '    '+local+'\n'+('    struct127 *actor;' if local != 'struct127 *actor;' else '    struct106 *record;'))
    yield 'switch-record-initialized', SWITCH.replace('    struct106 *record;',
        '    struct106 *record = &D_800C6660[slot];').replace('        record = &D_800C6660[slot];\n', '')
    yield 'type-first', SWITCH
    for name, old, new in (('byte-count', 's32 count;', 'u8 count;'),
            ('byte-type', 's32 type;', 's8 type;'), ('unsigned-index', 's32 index;', 'u32 index;'),
            ('register-count', 's32 count;', 'register s32 count;')):
        yield name, SWITCH.replace(old, new)
    yield 'slot-count', SWITCH.replace('    s32 count;\n', '').replace('count = D_', 'slot = D_').replace('index < count', 'index < slot')
    yield 'count-last', SWITCH.replace('        count = D_80098914[((u8 *)record)[0xE]];\n        types = D_80084454[((u8 *)record)[0xE]];',
        '        types = D_80084454[((u8 *)record)[0xE]];\n        count = D_80098914[((u8 *)record)[0xE]];')
    yield 'explicit-do', SWITCH.replace('        for (index = 0; index < count; index++) {',
        '        index = 0;\n        if (count > 0) {\n        do {').replace(
        '        }\n    }\n}', '            index++;\n        } while (index != count);\n        }\n    }\n}')
    yield 'float-element', SWITCH.replace('struct04 *element;', 'f32 *element;').replace(
        'element = (struct04 *)record->unk0 + index;', 'element = (f32 *)record->unk0 + index * 26;').replace(
        'element->unk64', '((u8 *)element)[100]').replace('element->unk3C', '((u32 *)element)[15]').replace(
        'element->unk40', '((u32 *)element)[16]').replace('element->unk44', '((u32 *)element)[17]')
    for local in ('struct127 *actor;', 'struct106 *record;', 'struct04 *element;', 'f32 (*destination)[4];',
            's8 *types;', 's32 index;', 's32 type;'):
        yield 'ordered-register-'+local.split()[-1].replace(';', '').replace('*', '').replace('(', '').replace(')', '').replace('[4]', ''), ORDERED.replace(
            '    '+local, '    register '+local)
    yield 'ordered-register-all', ORDERED.replace('    struct', '    register struct').replace(
        '    s32 ', '    register s32 ').replace('    s8 ', '    register s8 ').replace('    f32 (*', '    register f32 (*')
    yield 'ordered-byte-offset', ORDERED.replace('    s32 type;', '    s32 type;\n    s32 byteOffset;').replace(
        '                element = (struct04 *)record->unk0 + index;',
        '                byteOffset = index * sizeof(struct04);\n                element = (struct04 *)(record->unk0 + byteOffset);').replace(
        'element = (struct04 *)record->unk0 + index;', 'element = (struct04 *)(record->unk0 + byteOffset);')
    yield 'ordered-position-locals', ORDERED.replace('    s32 type;', '    s32 type;\n    f32 x;\n    f32 y;\n    f32 z;').replace(
        '                        func_15043EC8(destination,',
        '                        x = ((f32 *)element)[9];\n                        y = ((f32 *)element)[10];\n                        z = ((f32 *)element)[11];\n                        func_15043EC8(destination,').replace(
        '((f32 *)element)[9], ((f32 *)element)[10], ((f32 *)element)[11]);', 'x, y, z);')
    inline_actor = ORDERED.replace('    struct127 *actor;\n', '').replace('    actor = &D_800CC2D0[slot];\n', '').replace(
        'actor->unk1D4', 'D_800CC2D0[slot].unk1D4')
    inline_record = ORDERED.replace('    struct106 *record;\n', '').replace('        record = &D_800C6660[slot];\n', '').replace(
        '((u8 *)record)[0xE]', '((u8 *)&D_800C6660[slot])[0xE]').replace('record->unk0', 'D_800C6660[slot].unk0')
    yield 'ordered-inline-actor', inline_actor
    yield 'ordered-inline-record', inline_record
    yield 'ordered-inline-both', inline_record.replace('    struct127 *actor;\n', '').replace('    actor = &D_800CC2D0[slot];\n', '').replace(
        'actor->unk1D4', 'D_800CC2D0[slot].unk1D4')
    for name, body in (('actor', inline_actor), ('record', inline_record)):
        yield 'ordered-offset-inline-'+name, body.replace('    s32 type;', '    s32 type;\n    s32 byteOffset;').replace(
            '                element = (struct04 *)record->unk0 + index;' if name == 'actor' else '                element = (struct04 *)D_800C6660[slot].unk0 + index;',
            '                byteOffset = index * sizeof(struct04);\n                element = (struct04 *)('+('record->unk0' if name == 'actor' else 'D_800C6660[slot].unk0')+' + byteOffset);').replace(
            'element = (struct04 *)'+('record->unk0' if name == 'actor' else 'D_800C6660[slot].unk0')+' + index;',
            'element = (struct04 *)('+('record->unk0' if name == 'actor' else 'D_800C6660[slot].unk0')+' + byteOffset);')
    for local in ('struct04 *element;', 'f32 (*destination)[4];', 's8 *types;', 's32 count;', 's32 index;', 's32 type;', 'f32 matrix[4][4];'):
        short = local.split()[-1].replace(';', '').replace('*', '').replace('(', '').replace(')', '').replace('[4]', '')
        removed = INLINE_BOTH.replace('    '+local+'\n', '')
        first_line = removed.splitlines()[1]
        yield 'both-first-'+short, removed.replace(first_line, '    '+local+'\n'+first_line, 1)
        yield 'both-scoped-'+short, removed.replace('    if (D_800CC2D0[slot].unk1D4 != NULL) {',
            '    if (D_800CC2D0[slot].unk1D4 != NULL) {\n        '+local)
    yield 'both-count-initialized', INLINE_BOTH.replace('    s32 count;\n', '').replace('        count = D_', '        s32 count = D_')
    yield 'both-count-last', INLINE_BOTH.replace('    s32 count;\n', '').replace('    f32 matrix[4][4];', '    f32 matrix[4][4];\n    s32 count;')
    for local in ('struct04 *element;', 'f32 (*destination)[4];', 's8 *types;', 's32 index;', 's32 type;'):
        yield 'final-scoped-'+local.split()[-1].replace(';', '').replace('*', '').replace('(', '').replace(')', '').replace('[4]', ''), COUNT_FIRST.replace(
            '    '+local+'\n', '').replace('    if (D_800CC2D0[slot].unk1D4 != NULL) {',
            '    if (D_800CC2D0[slot].unk1D4 != NULL) {\n        '+local)


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == source.count(PROTOTYPE) == 1
    assert SELECTED not in source and LOCAL_DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL, SELECTED).replace(PROTOTYPE,
        RECOVERED_PROTOTYPE+'\n'+LOCAL_DECLARATIONS.rstrip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-matrix-update'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta); print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
