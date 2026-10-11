"""Recover the complete callback-aware record initialization/update dispatcher."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL

ENTRY, ROM, WORDS = 0x1503DF48, 0x6B3F8, 171
FUNCTION, SOURCE = 'func_1503DF48', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503DF48() {\n    return 0;\n}'
ANCHOR = 'extern u8 D_800C6668[];'
LOCAL_DECLARATIONS = '''extern u8 D_80098914[];
extern s8 *D_80084454[];
extern void (*D_80084430[])(struct04 *, s32);
extern void (*D_8008443C[])(s32);
extern void (*D_80084448[])(s32);
s32 allocate_memory(s32, s32, s32, s32);
s32 func_1503E1F4(s32, s32);
s32 func_1503E3C4();
s32 func_1503EA54();
s32 func_1503E82C();
'''
DECLARATIONS = '#include "variables.h"\n' + LOCAL_DECLARATIONS
SYMBOLS = dict(D_800C6660=0x800C6660, D_800CC2D0=0x800CC2D0,
    D_80098914=0x80098914, D_80084454=0x80084454, D_80084430=0x80084430,
    D_8008443C=0x8008443C, D_80084448=0x80084448, allocate_memory=0x10003C40,
    func_1503E1F4=0x1503E1F4, func_1503E3C4=0x1503E3C4,
    func_1503EA54=0x1503EA54, func_1503E82C=0x1503E82C)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
FLAT = '''void func_1503DF48(s32 slot) {
    struct106 *record = &D_800C6660[slot];
    struct04 *element;
    struct04 *buffer;
    s8 *types;
    s32 state = record->unkF;
    s32 count;
    s32 index;

    if (state == 2) {
        D_800CC2D0[slot].unk74 |= 0x80;
        state = 3;
        if (D_800CC2D0[slot].unk1D4 == NULL) {
            return;
        }
    }
    if (state == 3) {
        count = D_80098914[((u8 *)record)[0xE]];
        if (record->unk0 == 0) {
            buffer = (struct04 *)allocate_memory(count * sizeof(struct04), 1, 0, 0);
            if (buffer == NULL) {
                return;
            }
            record->unk0 = (s32)buffer;
            for (index = 0; index < count; index++) {
                buffer[index].unk64 = 0;
            }
        }
        types = D_80084454[((u8 *)record)[0xE]];
        for (index = 0; index < count; index++, types++) {
            if (*types != -2) {
                element = (struct04 *)record->unk0 + index;
                if (func_1503E1F4(index, slot) != 0 && element->unk64 == 0) {
                    func_1503E3C4(slot, index, 0, element, 0);
                    D_80084430[((u8 *)record)[0xE]](element, slot);
                    element->unk64 = 1;
                }
            }
        }
        D_8008443C[((u8 *)record)[0xE]](slot);
        record->unkF = 1;
        state = 1;
    }
    if (state == 1) {
        D_80084448[((u8 *)record)[0xE]](slot);
        if (record->unkF != 0) {
            func_1503EA54(slot);
            func_1503E82C(slot);
        }
    }
}'''


SELECTED = FLAT.replace('index++, types++', 'index++').replace(
    '            if (*types != -2) {',
    '            switch (types[index]) {\n            case -2:\n                break;\n            default:').replace(
    '                    element->unk64 = 1;\n                }',
    '                    element->unk64 = 1;\n                }\n                break;').replace(
    'record->unkF = 1;\n        state = 1;', 'state = 1;\n        record->unkF = 1;')


def candidates():
    yield 'selected', SELECTED
    yield 'flat', FLAT
    switch = FLAT.replace('            if (*types != -2) {',
        '            switch (*types) {\n            case -2:\n                break;\n            default:').replace(
        '                    element->unk64 = 1;\n                }',
        '                    element->unk64 = 1;\n                }\n                break;')
    indexed = switch.replace('index++, types++', 'index++').replace('switch (*types)', 'switch (types[index])')
    for name, tail in (
            ('indexed-combined', 'state = record->unkF = 1;'),
            ('indexed-state-first', 'state = 1;\n        record->unkF = 1;'),
            ('indexed-record-from-state', 'state = 1;\n        record->unkF = state;'),
            ('indexed-state-in-record', 'record->unkF = state = 1;'),
            ('indexed-cast-state-in-record', 'record->unkF = (u8)(state = 1);'),
            ('indexed-comma', 'state = 1, record->unkF = 1;')):
        yield name, indexed.replace('record->unkF = 1;\n        state = 1;', tail)
    for name, body in (
            ('switch-base', switch),
            ('switch-indexed', switch.replace('index++, types++', 'index++').replace('switch (*types)', 'switch (types[index])')),
            ('switch-postincrement', switch.replace('index++, types++', 'index++').replace('switch (*types)', 'switch (*types++)')),
            ('switch-combined-state', switch.replace('record->unkF = 1;\n        state = 1;', 'state = record->unkF = 1;')),
            ('switch-state-first', switch.replace('record->unkF = 1;\n        state = 1;', 'state = 1;\n        record->unkF = 1;')),
            ('switch-inner-cursor', switch.replace('        for (index = 0; index < count; index++, types++) {',
                '        index = 0;\n        if (count > 0) {\n        s8 *cursor = types;\n        do {').replace('switch (*types)', 'switch (*cursor)').replace(
                '        }\n        D_8008443C', '            index++;\n            cursor++;\n        } while (index != count);\n        }\n        D_8008443C'))):
        yield name, body
    yield 'u8-count', FLAT.replace('    s32 count;', '    u8 count;')
    yield 'u8-state', FLAT.replace('    s32 state =', '    u8 state =')
    yield 'reverse-locals', FLAT.replace('    struct04 *element;\n    struct04 *buffer;\n    s8 *types;',
        '    s32 index;\n    s8 *types;\n    struct04 *buffer;\n    struct04 *element;').replace('    s32 index;\n\n', '\n')
    yield 'body-increment', FLAT.replace('index++, types++', 'index++').replace(
        '        }\n        D_8008443C', '            types++;\n        }\n        D_8008443C')
    yield 'cached-buffer-before', FLAT.replace('            buffer = (struct04 *)allocate_memory',
        '            element = (struct04 *)allocate_memory').replace('buffer == NULL', 'element == NULL').replace(
        'record->unk0 = (s32)buffer', 'record->unk0 = (s32)element').replace('buffer[index].unk64', 'element[index].unk64')
    yield 'split-conditions', FLAT.replace('if (func_1503E1F4(index, slot) != 0 && element->unk64 == 0) {',
        'if (func_1503E1F4(index, slot) != 0) {\n                    if (element->unk64 == 0) {').replace(
        '                    element->unk64 = 1;\n                }',
        '                    element->unk64 = 1;\n                    }\n                }')
    yield 'post-test-loop', FLAT.replace('        for (index = 0; index < count; index++, types++) {',
        '        index = 0;\n        if (count > 0) {\n        do {').replace(
        '        }\n        D_8008443C', '            index++;\n            types++;\n        } while (index != count);\n        }\n        D_8008443C')
    yield 'switch-sentinel', FLAT.replace('            if (*types != -2) {',
        '            switch (*types) {\n            case -2:\n                break;\n            default:').replace(
        '                    element->unk64 = 1;\n                }',
        '                    element->unk64 = 1;\n                }\n                break;')
    yield 'inline-buffer', FLAT.replace('    struct04 *buffer;\n', '').replace(
        '            buffer = (struct04 *)allocate_memory', '            record->unk0 = allocate_memory').replace(
        '            if (buffer == NULL)', '            if (record->unk0 == 0)').replace(
        '            record->unk0 = (s32)buffer;\n', '').replace('buffer[index].unk64', '((struct04 *)record->unk0)[index].unk64')
    yield 'indexed-types', FLAT.replace('index++, types++', 'index++').replace('*types != -2', 'types[index] != -2')
    yield 'increment-state', FLAT.replace('state = 3;', 'state++;').replace('state = 1;', 'state = record->unkF;')


def install(source):
    assert source.count(ORIGINAL) == source.count(ANCHOR) == 1
    assert LOCAL_DECLARATIONS not in source and SELECTED not in source
    return source.replace(ORIGINAL, SELECTED).replace(ANCHOR, ANCHOR+'\n'+LOCAL_DECLARATIONS.rstrip())


def install_caller(source):
    before, after = 's32 func_1503DF48();', 'void func_1503DF48(s32);'
    assert source.count(before) == 1 and after not in source
    return source.replace(before, after)


def metadata_pair(data):
    """Locate the measured adjacent absolute-symbol permutation, not arbitrary metadata."""
    header = ELF_HEADER.unpack_from(data)
    sections = [SECTION_HEADER.unpack_from(data, header[6]+i*header[11]) for i in range(header[12])]
    tables = [section for section in sections if section[1] == 2]
    assert len(tables) == 1
    table = tables[0]; strings = sections[table[6]]
    names = bytes(data[strings[4]:strings[4]+strings[5]])
    expected = {b'D_80088730': 0x80088730, b'D_80084430': 0x80084430}
    found = []
    for offset in range(table[4], table[4]+table[5], table[9]):
        symbol = SYMBOL.unpack_from(data, offset); name = names[symbol[0]:].split(b'\0', 1)[0]
        if name in expected:
            assert symbol[1:] == (expected[name], 0, 16, 0, 65521)
            found.append((offset, strings[4]+symbol[0], name))
    assert len(found) == 2 and {item[2] for item in found} == set(expected)
    assert found[1][0]-found[0][0] == 16 and found[1][1]-found[0][1] == 11
    return found


def swap_metadata_pair(data):
    pair = metadata_pair(data); result = bytearray(data)
    for index, (offset, string, _) in enumerate(pair):
        other_offset, other_string, _ = pair[1-index]
        result[offset+4:offset+8] = data[other_offset+4:other_offset+8]
        result[string:string+11] = data[other_string:other_string+11]
    metadata_pair(result)
    return bytes(result)


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--profile', action='append', choices=tuple(PROFILES))
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-state-dispatch'
    measurements = []
    for name, body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (args.profile or (('owner', 'compact') if args.profiles else ('owner',))):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            measurements.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
