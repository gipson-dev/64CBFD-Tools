"""Recover the complete signed-byte, eight-byte command-stream relocator."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x1503D368, 0x6A818, 52
FUNCTION, SOURCE = 'func_1503D368', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503D368() {\n    return 0;\n}'
DECLARATIONS = 'void func_1503D438(u32 *, u32);\n'
SYMBOLS = dict(func_1503D438=0x1503D438)
SELECTED = '''void func_1503D368(s8 *commands, u32 base) {
    s32 index;
    s8 *cursor;

    if (commands != NULL) {
        index = 0;
        cursor = commands;
        while (cursor[0] != -0x21) {
            if (cursor[0] == -0x24) {
                if (((u8 *)cursor)[3] == 0x0E) {
                    func_1503D438((u32 *)(cursor + 4), base);
                }
            } else if (cursor[0] == 1) {
                func_1503D438((u32 *)(cursor + 4), base);
            }
            index++;
            cursor = commands + index * 8;
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'index-before-null', SELECTED.replace('        index = 0;', '').replace(
        '    if (commands != NULL)', '    index = 0;\n    if (commands != NULL)')
    yield 'index-initializer', SELECTED.replace('    s32 index;', '    s32 index = 0;').replace(
        '        index = 0;\n', '')
    yield 'cursor-first', SELECTED.replace('    s32 index;\n    s8 *cursor;', '    s8 *cursor;\n    s32 index;')
    yield 'subtype-signed', SELECTED.replace('((u8 *)cursor)[3]', 'cursor[3]')
    yield 'unsigned-cursor', SELECTED.replace('s8 *commands', 'u8 *commands').replace(
        's8 *cursor', 'u8 *cursor').replace('cursor[0]', '(s8)cursor[0]')
    yield 'indexed-test', SELECTED.replace('while (cursor[0] != -0x21)',
        'while (commands[index * 8] != -0x21)')
    yield 'increment-in-address', SELECTED.replace('            index++;\n            cursor = commands + index * 8;',
        '            cursor = commands + ++index * 8;')
    yield 'word-opcodes', SELECTED.replace('cursor[0]', '(s32)*(u32 *)cursor >> 24')
    for declaration in ('s32', 's8'):
        body = SELECTED.replace('    s8 *cursor;', '    s8 *cursor;\n    '+declaration+' opcode;')
        body = body.replace('            if (cursor[0] ==', '            opcode = cursor[0];\n            if (opcode ==')
        body = body.replace('else if (cursor[0] ==', 'else if (opcode ==')
        yield 'cached-opcode-'+declaration, body
    ordered = SELECTED.replace('''            if (cursor[0] == -0x24) {
                if (((u8 *)cursor)[3] == 0x0E) {
                    func_1503D438((u32 *)(cursor + 4), base);
                }
            } else if (cursor[0] == 1) {
                func_1503D438((u32 *)(cursor + 4), base);
            }''', '''            if (cursor[0] == 1) {
                func_1503D438((u32 *)(cursor + 4), base);
            } else if (cursor[0] == -0x24) {
                if (((u8 *)cursor)[3] == 0x0E) {
                    func_1503D438((u32 *)(cursor + 4), base);
                }
            }''')
    for name, body in (('dc-first', SELECTED), ('vertex-first', ordered)):
        yield name+'-unsigned-index', body.replace('s32 index;', 'u32 index;')
        indexed = body.replace('    s8 *cursor;\n', '').replace('        cursor = commands;\n', '').replace(
            '            cursor = commands + index * 8;\n', '')
        indexed = indexed.replace('cursor[0]', 'commands[index * 8]').replace(
            '((u8 *)cursor)[3]', '((u8 *)commands)[index * 8 + 3]').replace(
            '(u32 *)(cursor + 4)', '(u32 *)(commands + index * 8 + 4)')
        yield name+'-all-indexed', indexed
        yield name+'-all-indexed-unsigned', indexed.replace('s32 index;', 'u32 index;')
        gfx = indexed.replace('s8 *commands', 'Gfx *commands').replace(
            'commands[index * 8]', '((s8 *)&commands[index])[0]').replace(
            '((u8 *)commands)[index * 8 + 3]', '((u8 *)&commands[index])[3]').replace(
            '(u32 *)(commands + index * 8 + 4)', '(u32 *)&commands[index].words.w1')
        yield name+'-gfx-indexed', gfx
        yield name+'-gfx-indexed-unsigned', gfx.replace('s32 index;', 'u32 index;')
        for cases in (('vertex', 'memory'), ('memory', 'vertex')):
            blocks = dict(vertex='''            case 1:
                func_1503D438((u32 *)&commands[index].words.w1, base);
                break;''', memory='''            case -0x24:
                if (((u8 *)&commands[index])[3] == 0x0E) {
                    func_1503D438((u32 *)&commands[index].words.w1, base);
                }
                break;''')
            start = gfx.index('            if (')
            end = gfx.index('            index++;', start)
            switched = gfx[:start]+'            switch (((s8 *)&commands[index])[0]) {\n'+\
                '\n'.join(blocks[key] for key in cases)+'\n            }\n'+gfx[end:]
            yield name+'-switch-'+cases[0], switched
            yield name+'-switch-'+cases[0]+'-register', switched.replace('s32 index;', 'register s32 index;').replace(
                'Gfx *commands', 'register Gfx *commands')
        for variable in ('index', 'commands'):
            yield name+'-gfx-register-'+variable, gfx.replace('s32 index;', 'register s32 index;') if variable == 'index' else gfx.replace(
                'Gfx *commands', 'register Gfx *commands')
        if name == 'vertex-first':
            yield name, body


QUALIFIED = dict(candidates())['vertex-first-switch-vertex']
PARENT_SOURCE_SHA = 'f43fa661893aadea680107f8ebe446bdad763489b5558996c8a906802beca058'


def parent_source(root):
    """Project only the exact qualified child back onto historical parent audits."""
    source = (root/SOURCE).read_text()
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED) == 1
    assert source.count('void func_1503D368(Gfx *, u32);') == 1
    assert source.count('func_1503D368((Gfx *)*(u32 *)') == 2
    before = source.replace(QUALIFIED, ORIGINAL).replace(
        'void func_1503D368(Gfx *, u32);', 's32 func_1503D368();').replace(
        'func_1503D368((Gfx *)*(u32 *)', 'func_1503D368(*(u32 *)')
    assert hashlib.sha256(before.encode('ascii')).hexdigest() == PARENT_SOURCE_SHA
    assert install(before) == source
    return before


def parent_elf(root, before):
    """Validate the direct child, then reverse only its slot and symbol extent."""
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset

    source = parent_source(root)
    actual = (root/'conker/build/conker.us.elf').read_bytes()
    if (root/SOURCE).read_text() == source:
        return actual
    assert hashlib.sha256(source.encode('ascii')).hexdigest() == PARENT_SOURCE_SHA
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


def compile_candidate(root, out, name, body=None, profile='retail'):
    profiles = dict(compiler.PROFILES, retail=('-O2', '-g3', '-Wo,-loopunroll,0'))
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=profiles):
        return compiler.compile_candidate(root, out, name, QUALIFIED if body is None else body, profile)


def install(before, body=None):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1503D368();') != 1:
        raise ValueError('stale command-stream owner or interface')
    result = before.replace('s32 func_1503D368();', 'void func_1503D368(Gfx *, u32);')
    result = result.replace('func_1503D368(*(u32 *)', 'func_1503D368((Gfx *)*(u32 *)')
    assert result.count('func_1503D368((Gfx *)*(u32 *)') == 2
    return result.replace(ORIGINAL, QUALIFIED if body is None else body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-command-stream-relocator'
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
