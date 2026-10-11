"""Recover the complete first-command-stream weighted opcode counter."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x1503D984, 0x6AE34, 46
FUNCTION, SOURCE = 'func_1503D984', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503D984() {\n    return 0;\n}'
DECLARATIONS = 'extern u32 *D_800C4488[];\nextern s16 D_800C5918[];\n'
SYMBOLS = dict(D_800C4488=0x800C4488, D_800C5918=0x800C5918)
SELECTED = '''void func_1503D984(s32 identity) {
    s32 count;
    s32 index;
    u32 *cursor;
    s8 opcode;

    count = 0;
    for (index = 0; index < 1; index++) {
        cursor = (u32 *)D_800C4488[identity][index];
        opcode = *cursor >> 24;
        while (opcode != -0x21) {
            if (opcode == 5) {
                count++;
            } else if (opcode == 6) {
                count += 2;
            } else if ((opcode >> 4) == 1) {
                count += 4;
            }
            cursor += 2;
            opcode = *cursor >> 24;
        }
    }
    D_800C5918[identity] = count;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'unsigned-count', SELECTED.replace('s32 count;', 'u32 count;')
    yield 'signed-word-cursor', SELECTED.replace('u32 *cursor;', 's32 *cursor;').replace(
        '(u32 *)D_800C4488', '(s32 *)D_800C4488')
    yield 'full-width-opcode', SELECTED.replace('s8 opcode;', 's32 opcode;').replace(
        'opcode = *cursor >> 24;', 'opcode = (s8)(*cursor >> 24);')
    yield 'opcode-before-cursor', SELECTED.replace('    u32 *cursor;\n    s8 opcode;', '    s8 opcode;\n    u32 *cursor;')
    yield 'index-before-count', SELECTED.replace('    s32 count;\n    s32 index;', '    s32 index;\n    s32 count;')
    yield 'count-initializer', SELECTED.replace('s32 count;', 's32 count = 0;').replace('    count = 0;\n', '')
    yield 'do-outer', SELECTED.replace('    for (index = 0; index < 1; index++) {',
        '    index = 0;\n    do {').replace('    }\n    D_800C5918', '        index++;\n    } while (index < 1);\n    D_800C5918')
    yield 'byte-offset-outer', SELECTED.replace('index < 1; index++', 'index < 4; index += 4').replace(
        'D_800C4488[identity][index]', '*(u32 *)((u8 *)D_800C4488[identity] + index)')
    yield 'single-stream', SELECTED.replace('    for (index = 0; index < 1; index++) {', '    {').replace(
        '    s32 index;\n', '').replace('D_800C4488[identity][index]', 'D_800C4488[identity][0]')
    yield 'unsigned-opcode', SELECTED.replace('s8 opcode;', 'u32 opcode;').replace('!= -0x21', '!= 0xDF')
    yield 'byte-opcode', SELECTED.replace('opcode = *cursor >> 24;', 'opcode = *(s8 *)cursor;')
    for result in ('s32', 'u32'):
        returning = SELECTED.replace('void func_1503D984', result+' func_1503D984').replace(
            '    D_800C5918[identity] = count;', '    D_800C5918[identity] = count;\n    return count;')
        yield result+'-return-count', returning
        yield result+'-return-count-full-opcode', returning.replace('s8 opcode;', 's32 opcode;').replace(
            'opcode = *cursor >> 24;', 'opcode = (s8)(*cursor >> 24);')
    byte_cursor = SELECTED.replace('u32 *cursor;', 'u8 *cursor;').replace(
        '(u32 *)D_800C4488', '(u8 *)D_800C4488').replace(
        'opcode = *cursor >> 24;', 'opcode = *(u32 *)cursor >> 24;').replace('cursor += 2;', 'cursor += 8;')
    gfx = SELECTED.replace('u32 *cursor;', 'Gfx *cursor;').replace(
        '(u32 *)D_800C4488', '(Gfx *)D_800C4488').replace(
        'opcode = *cursor >> 24;', 'opcode = cursor->words.w0 >> 24;').replace('cursor += 2;', 'cursor++;')
    yield 'byte-cursor-word-opcode', byte_cursor
    yield 'Gfx-cursor', gfx
    for name, body in (('word', SELECTED), ('byte', byte_cursor), ('Gfx', gfx)):
        pointer = {'word':'u32', 'byte':'u8', 'Gfx':'Gfx'}[name]
        body = body.replace('    s8 opcode;', '    s8 opcode;\n    '+pointer+' *commands;')
        body = body.replace('        cursor = ', '        commands = ', 1)
        start = body.index('        opcode = ')
        end = body.index('\n', start)
        opening = body[start:end].replace('cursor', 'commands')
        separate = body[:start]+opening+'\n        cursor = commands;'+body[end:]
        yield name+'-separate-opening', separate
        yield name+'-separate-opening-declaration', separate.replace(
            '    s8 opcode;\n    '+pointer+' *commands;', '    '+pointer+' *commands;\n    s8 opcode;')
        word = '*commands' if name == 'word' else '*(u32 *)commands' if name == 'byte' else 'commands->words.w0'
        explicit_word = separate.replace('    s8 opcode;', '    s8 opcode;\n    u32 command;').replace(
            opening, '        command = '+word+';').replace(
            '        cursor = commands;', '        cursor = commands;\n        opcode = command >> 24;')
        yield name+'-explicit-opening-word', explicit_word
        full_word = separate.replace('s8 opcode;', 's32 opcode;').replace(
            opening, '        opcode = '+word+';').replace(
            '        cursor = commands;', '        cursor = commands;\n        opcode = (s8)((u32)opcode >> 24);').replace(
            'opcode = *cursor >> 24;', 'opcode = (s8)(*cursor >> 24);').replace(
            'opcode = *(u32 *)cursor >> 24;', 'opcode = (s8)(*(u32 *)cursor >> 24);').replace(
            'opcode = cursor->words.w0 >> 24;', 'opcode = (s8)(cursor->words.w0 >> 24);')
        yield name+'-full-opening-word', full_word
        condition = full_word.replace('        opcode = (s8)((u32)opcode >> 24);\n', '').replace(
            'while (opcode != -0x21)', 'while ((opcode = (s8)((u32)opcode >> 24)) != -0x21)').replace(
            'opcode = (s8)(*cursor >> 24);', 'opcode = *cursor;').replace(
            'opcode = (s8)(*(u32 *)cursor >> 24);', 'opcode = *(u32 *)cursor;').replace(
            'opcode = (s8)(cursor->words.w0 >> 24);', 'opcode = cursor->words.w0;')
        yield name+'-full-word-condition', condition
    for name, body, word in (('word', SELECTED, '*(u32 *)D_800C4488[identity][index]'),
            ('byte', byte_cursor, '*(u32 *)D_800C4488[identity][index]'),
            ('Gfx', gfx, '((Gfx *)D_800C4488[identity][index])->words.w0')):
        first = body.index('        cursor = ')
        end = body.index('        while ', first)
        assignment = body[first:body.index('\n', first)]
        separate = body[:first]+'        opcode = '+word+' >> 24;\n'+assignment+'\n'+body[end:]
        yield name+'-opening-table-reread', separate
        yield name+'-opening-table-reread-full', separate.replace('s8 opcode;', 's32 opcode;').replace(
            'opcode = '+word+' >> 24;', 'opcode = (s8)('+word+' >> 24);').replace(
            'opcode = *cursor >> 24;', 'opcode = (s8)(*cursor >> 24);').replace(
            'opcode = *(u32 *)cursor >> 24;', 'opcode = (s8)(*(u32 *)cursor >> 24);').replace(
            'opcode = cursor->words.w0 >> 24;', 'opcode = (s8)(cursor->words.w0 >> 24);')
    for name, body, word in (('word', SELECTED, '*cursor'), ('byte', byte_cursor, '*(u32 *)cursor'),
            ('Gfx', gfx, 'cursor->words.w0')):
        first = body.index('        cursor = ')
        line_end = body.index('\n', first)
        assignment = body[first:line_end].strip().removesuffix(';')
        initial = body.index('        while ', first)
        step = {'word':'cursor += 2', 'byte':'cursor += 8', 'Gfx':'cursor++'}[name]
        inner = (body[:first]+'        for ('+assignment+'; (opcode = (s8)('+word+
            ' >> 24)) != -0x21; '+step+') {\n'+body[body.index('\n', initial)+1:])
        inner = inner.replace('            '+step+';\n', '').replace(
            '            opcode = '+word+' >> 24;\n', '')
        yield name+'-inner-for', inner
        yield name+'-inner-for-full-opcode', inner.replace('s8 opcode;', 's32 opcode;')
        combined = body[:first]+'        opcode = '+word.replace('cursor', '('+assignment+')')+' >> 24;\n'+body[initial:]
        yield name+'-assignment-expression', combined
        declarations = dict(cursor={'word':'u32', 'byte':'u8', 'Gfx':'Gfx'}[name]+' *cursor;',
            opcode='s8 opcode;', count='s32 count;', index='s32 index;')
        for variable in ('cursor', 'opcode', 'count', 'index'):
            yield name+'-register-'+variable, body.replace(declarations[variable], 'register '+declarations[variable])
    for name, body, pointer in (('word', SELECTED, 'u32'), ('byte', byte_cursor, 'u8'), ('Gfx', gfx, 'Gfx')):
        table = body.replace('    s32 count;', '    '+pointer+' **streams;\n    s32 count;').replace(
            '    count = 0;', '    streams = ('+pointer+' **)D_800C4488[identity];\n    count = 0;').replace(
            '('+pointer+' *)D_800C4488[identity][index]', 'streams[index]')
        yield name+'-typed-stream-table', table
        yield name+'-typed-stream-table-last', table.replace('    '+pointer+' **streams;\n', '').replace(
            '    s8 opcode;', '    s8 opcode;\n    '+pointer+' **streams;')
        yield name+'-typed-stream-table-opcode-first', table.replace(
            '        cursor = streams[index];\n        opcode = ', '        opcode = ').replace(
            '*cursor >> 24;\n        while', '*streams[index] >> 24;\n        cursor = streams[index];\n        while').replace(
            '*(u32 *)cursor >> 24;\n        while', '*(u32 *)streams[index] >> 24;\n        cursor = streams[index];\n        while').replace(
            'cursor->words.w0 >> 24;\n        while', 'streams[index]->words.w0 >> 24;\n        cursor = streams[index];\n        while')
    for address_type in ('s32', 'u32'):
        address = SELECTED.replace('    s8 opcode;', '    s8 opcode;\n    '+address_type+' commandAddress;').replace(
            '        cursor = (u32 *)D_800C4488[identity][index];\n        opcode = *cursor >> 24;',
            '        commandAddress = D_800C4488[identity][index];\n        opcode = *(u32 *)commandAddress >> 24;\n        cursor = (u32 *)commandAddress;')
        yield address_type+'-opening-address', address
        yield address_type+'-opening-address-full', address.replace('s8 opcode;', 's32 opcode;').replace(
            'opcode = *(u32 *)commandAddress >> 24;', 'opcode = (s8)(*(u32 *)commandAddress >> 24);').replace(
            'opcode = *cursor >> 24;', 'opcode = (s8)(*cursor >> 24);')
    indexed = SELECTED.replace('    s8 opcode;', '    s8 opcode;\n    s32 commandIndex;').replace(
        '        opcode = *cursor >> 24;', '        commandIndex = 0;\n        opcode = cursor[commandIndex * 2] >> 24;', 1).replace(
        '            cursor += 2;\n            opcode = *cursor >> 24;',
        '            commandIndex++;\n            opcode = cursor[commandIndex * 2] >> 24;')
    yield 'indexed-word-cursor', indexed
    yield 'indexed-word-cursor-full-opcode', indexed.replace('s8 opcode;', 's32 opcode;').replace(
        'opcode = cursor[commandIndex * 2] >> 24;', 'opcode = (s8)(cursor[commandIndex * 2] >> 24);')
    yield 'indexed-Gfx-cursor', indexed.replace('u32 *cursor;', 'Gfx *cursor;').replace(
        '(u32 *)D_800C4488', '(Gfx *)D_800C4488').replace('cursor[commandIndex * 2]', 'cursor[commandIndex].words.w0')
    yield 'indexed-byte-cursor', indexed.replace('u32 *cursor;', 'u8 *cursor;').replace(
        '(u32 *)D_800C4488', '(u8 *)D_800C4488').replace('cursor[commandIndex * 2]', '*(u32 *)(cursor + commandIndex * 8)')


def compile_candidate(root, out, name, body=None, profile='retail'):
    profiles = dict(compiler.PROFILES, retail=('-O2', '-g3', '-Wo,-loopunroll,0'))
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=profiles):
        meta, words = compiler.compile_candidate(root, out, name, QUALIFIED if body is None else body, profile)
    meta['frame'] = -words[0]&65535 if words[0] >> 26 == 9 and words[0] >> 16 & 31 == 29 else 0
    return meta, words


def install(before, body=None):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1503D984();') != 1:
        raise ValueError('stale command counter or interface')
    marker = 'extern s16 D_800C5A90[];'
    assert before.count(marker) == 1 and 'extern s16 D_800C5918[];' not in before
    return before.replace(marker, marker+'\nextern s16 D_800C5918[];').replace(
        's32 func_1503D984();', 'void func_1503D984(s32);').replace(ORIGINAL, QUALIFIED if body is None else body)


QUALIFIED = dict(candidates())['indexed-word-cursor']
COMMAND_SOURCE_SHA = '0f8594be47c2082c073901586c8a3a7ee74b6a4b70588de92729e61d3ba0c52d'


def command_source(root):
    """Reverse only the exact counter successor for earlier command/parent audits."""
    from tools.experiments import game_record_pair_copy_candidates as pairs
    source = pairs.counter_source(root)
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED) == 1
    assert source.count('void func_1503D984(s32);') == 1
    assert source.count('extern s16 D_800C5918[];') == 1
    before = source.replace(QUALIFIED, ORIGINAL).replace(
        'void func_1503D984(s32);', 's32 func_1503D984();').replace(
        '\nextern s16 D_800C5918[];', '')
    assert hashlib.sha256(before.encode('ascii')).hexdigest() == COMMAND_SOURCE_SHA
    assert install(before) == source
    return before


def command_elf(root, before):
    """Validate the counter's full linked words/extent before historical projection."""
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset
    from tools.experiments import game_record_pair_copy_candidates as pairs

    source = command_source(root)
    actual = pairs.counter_elf(root, before)
    if pairs.counter_source(root) == source:
        return actual
    start = elf_slot_offset(actual, ENTRY, WORDS*4)
    original_start = elf_slot_offset(before, ENTRY, WORDS*4)
    extent = symbol_size_offset(actual, FUNCTION, ENTRY)
    original_extent = symbol_size_offset(before, FUNCTION, ENTRY)
    retail = (root/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    assert actual[start:start+WORDS*4] == retail
    assert struct.unpack_from('>I', actual, extent)[0] == WORDS*4
    assert struct.unpack_from('>I', before, original_extent)[0] == 12
    result = bytearray(actual)
    result[start:start+WORDS*4] = before[original_start:original_start+WORDS*4]
    struct.pack_into('>I', result, extent, 12)
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-command-weight-counter'
    records = []
    for name, body in candidates() if args.variants else [('qualified', QUALIFIED)]:
        if args.filter not in name:
            continue
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
