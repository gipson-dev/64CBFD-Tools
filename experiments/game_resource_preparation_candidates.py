"""Recover the complete actor resource-preparation caller and live extras loop."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503DA9C, 0x6AF4C, 104
FUNCTION, SOURCE = 'func_1503DA9C', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503DA9C() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 *D_800D19A0[];
extern u8 *D_800C5C08[];
extern u16 D_800C5628[];
extern u32 *D_800C5338[];
extern u16 D_800C4778[];
extern u32 *D_800C4488[];
s32 func_1503CF20();
s32 func_1503DC3C();
void func_150028BC(s32);
void func_1510CE60(u32, s32, s32, s32, s32);
s32 func_15084044(u8 *, s32);
'''
SYMBOLS = dict(D_800D19A0=0x800D19A0, D_800C5C08=0x800C5C08,
    D_800C5628=0x800C5628, D_800C5338=0x800C5338,
    D_800C4778=0x800C4778, D_800C4488=0x800C4488,
    func_1503CF20=0x1503CF20, func_1503DC3C=0x1503DC3C,
    func_150028BC=0x150028BC, func_1510CE60=0x1510CE60,
    func_15084044=0x15084044)
SELECTED = '''s32 func_1503DA9C(u8 *actor, s32 identity, s32 channel, s32 extras) {
    s32 result;
    u8 *config;
    u8 *resource;
    s32 index;
    s32 offset;
    u16 *count;
    u32 **list;

    resource = D_800D19A0[identity];
    config = *(u8 **)(actor + 0x144);
    if (resource == NULL) {
        result = func_1503CF20(identity, 0, config, extras, actor[0xAC]);
    } else {
        result = 0;
        if (((config != NULL) && (*(u32 *)(config + 0x18) & 0x4000)) ||
            (actor[0xAC] & 1)) {
            if (D_800C5C08[identity] == NULL) {
                func_150028BC(identity);
            }
        }
        if ((extras != 0) && (D_800C5628[identity] != 0)) {
            if (*D_800C5338[identity] < 0x10000000U) {
                result = func_1503DC3C(identity);
                count = &D_800C4778[identity];
                index = 0;
                if (*count > 0) {
                    list = &D_800C4488[identity];
                    offset = 0;
                    do {
                        func_1510CE60(*(u32 *)((u8 *)*list + offset), 0, 0, 0x3E, 0);
                        index++;
                        offset += 4;
                    } while (index < *count);
                }
            }
        }
    }
    if (result == 0) {
        result = func_15084044(actor, channel);
    }
    return result;
}'''


def compile_candidate(root, out, name, body=None, profile='retail'):
    body = QUALIFIED if body is None else body
    profiles = dict(compiler.PROFILES, retail=('-O2', '-g3', '-Wo,-loopunroll,0'))
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS,
            PROFILES=profiles):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=None):
    body = QUALIFIED if body is None else body
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale resource preparation owner')
    declarations = DECLARATIONS.replace('extern u8 *D_800D19A0[];\n', '')
    return before.replace(ORIGINAL, declarations + '\n' + body)


def candidates():
    yield 'selected', SELECTED
    inline = SELECTED.replace('    u8 *resource;\n', '').replace(
        '    resource = D_800D19A0[identity];\n', '').replace('resource == NULL', 'D_800D19A0[identity] == NULL')
    yield 'inline-resource', inline
    yield 'result-last', SELECTED.replace('    s32 result;\n', '').replace(
        '    u32 **list;', '    u32 **list;\n    s32 result;')
    yield 'inline-result-last', inline.replace('    s32 result;\n', '').replace(
        '    u32 **list;', '    u32 **list;\n    s32 result;')
    yield 'result-before-count', SELECTED.replace('    s32 result;\n', '').replace(
        '    u16 *count;', '    s32 result;\n    u16 *count;')
    yield 'result-before-offset', SELECTED.replace('    s32 result;\n', '').replace(
        '    s32 offset;', '    s32 result;\n    s32 offset;')
    yield 'for-loop', inline.replace('                index = 0;\n                if (*count > 0)',
        '                if (*count > 0)').replace('                    do {',
        '                    for (index = 0; index < *count; index++) {').replace(
        '                        index++;\n', '').replace('                    } while (index < *count);', '                    }')
    yield 'inline-list', SELECTED.replace('    u32 **list;\n', '').replace(
        '                    list = &D_800C4488[identity];\n', '').replace(
        '(u8 *)*list', '(u8 *)D_800C4488[identity]')
    yield 'indexed-list', SELECTED.replace('    s32 offset;\n', '').replace(
        '                    offset = 0;\n', '').replace(
        '*(u32 *)((u8 *)*list + offset)', '(*list)[index]').replace('                        offset += 4;\n', '')
    yield 'inline-count', SELECTED.replace('    u16 *count;\n', '').replace(
        '                count = &D_800C4778[identity];\n', '').replace('*count', 'D_800C4778[identity]')
    start = SELECTED.index('                count = &D_800C4778[identity];')
    end = SELECTED.index('\n            }\n        }\n    }', start)
    loop = '''                for (index = 0; index < D_800C4778[identity]; index++) {
                    func_1510CE60(D_800C4488[identity][index], 0, 0, 0x3E, 0);
                }'''
    natural = (SELECTED[:start] + loop + SELECTED[end:]).replace(
        '    s32 offset;\n    u16 *count;\n    u32 **list;\n', '')
    yield 'natural-loop', natural
    yield 'natural-inline', natural.replace('    u8 *resource;\n', '').replace(
        '    resource = D_800D19A0[identity];\n', '').replace('resource == NULL', 'D_800D19A0[identity] == NULL')
    compact = natural.replace('    u8 *resource;\n', '').replace(
        '    resource = D_800D19A0[identity];\n', '').replace('resource == NULL', 'D_800D19A0[identity] == NULL')
    yield 'natural-descriptor', compact.replace('    s32 index;', '    s32 index;\n    u32 *descriptor;').replace(
        '            if (*D_800C5338[identity] < 0x10000000U)',
        '            descriptor = D_800C5338[identity];\n            if (*descriptor < 0x10000000U)')
    yield 'natural-descriptor-word', compact.replace('    s32 index;', '    s32 index;\n    u32 descriptor;').replace(
        '            if (*D_800C5338[identity] < 0x10000000U)',
        '            descriptor = *D_800C5338[identity];\n            if (descriptor < 0x10000000U)')
    yield 'natural-config-flags', compact.replace('    s32 index;', '    s32 index;\n    u32 flags;').replace(
        '        if (((config != NULL) && (*(u32 *)(config + 0x18) & 0x4000)) ||',
        '        flags = config != NULL ? *(u32 *)(config + 0x18) & 0x4000 : 0;\n        if ((flags != 0) ||')
    table_offset = compact.replace('    s32 index;', '    s32 index;\n    s32 tableOffset;').replace(
        '    config = *(u8 **)(actor + 0x144);', '    tableOffset = identity * 4;\n    config = *(u8 **)(actor + 0x144);')
    for table, kind in (('D_800D19A0', 'u8 *'), ('D_800C5C08', 'u8 *'),
            ('D_800C5338', 'u32 *'), ('D_800C4488', 'u32 *')):
        table_offset = table_offset.replace(table + '[identity]',
            '(*(' + kind.replace(' *', '') + ' **)((u8 *)' + table + ' + tableOffset))')
    yield 'natural-table-offset', table_offset
    count_pointer = compact.replace('    s32 index;', '    s32 index;\n    u16 *count;').replace(
        '                for (index = 0;', '                count = &D_800C4778[identity];\n                for (index = 0;').replace(
        'index < D_800C4778[identity]', 'index < *count')
    yield 'natural-count-pointer', count_pointer
    yield 'natural-result-last', natural.replace('    s32 result;\n', '').replace(
        '    s32 index;', '    s32 index;\n    s32 result;')


QUALIFIED = dict(candidates())['natural-table-offset'].replace(
    '    s32 result;\n    u8 *config;\n    s32 index;',
    '    u8 *config;\n    s32 index;\n    s32 result;')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', action='store_true')
    parser.add_argument('--declarations', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-resource-preparation'
    records = []
    forms = list(candidates()) if args.variants else [('qualified', QUALIFIED)]
    if args.declarations:
        body = dict(candidates())['natural-table-offset']
        declarations = ('s32 result;', 'u8 *config;', 's32 index;', 's32 tableOffset;')
        original = '\n'.join('    ' + line for line in declarations)
        assert body.count(original) == 1
        forms = [('declarations-%02d' % i, body.replace(original,
            '\n'.join('    ' + line for line in order)))
            for i, order in enumerate(itertools.permutations(declarations))]
    for name, body in forms:
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
