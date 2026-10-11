"""Recover the complete descriptor loader and its live publication contract."""
import argparse
import hashlib
import itertools
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503D660, 0x6AB10, 69
FUNCTION, SOURCE = 'func_1503D660', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503D660() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 *D_800D1588[];
extern s16 D_800C5A90[];
s32 func_1503D5F0(s32);
void *func_1502B5C8(s32 *, u32, ...);
void func_1503D45C(s32 *, s32);
void func_1503D484(u8 *, s32);
s32 func_1503D510();
'''
SYMBOLS = dict(D_800D1588=0x800D1588, D_800C5A90=0x800C5A90,
    func_1503D5F0=0x1503D5F0, func_1502B5C8=0x1502B5C8,
    func_1503D45C=0x1503D45C, func_1503D484=0x1503D484, func_1503D510=0x1503D510)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3','-Wo,-loopunroll,0'), retail=('-O2','-g3'))
SELECTED = '''s32 func_1503D660(s32 identity, s32 unused) {
    s32 size;
    u8 **slot = &D_800D1588[identity];
    u8 *loaded;

    if (*slot != NULL) {
        return 0;
    }
    loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity));
    if (loaded == NULL) {
        *slot = NULL;
        D_800C5A90[identity] = 0;
        func_1503D510(identity);
        return 4;
    }
    *slot = loaded;
    if (*(u32 *)loaded != 0) {
        *(u32 *)loaded += (u32)loaded;
        func_1503D45C((s32 *)*(u32 *)*slot, (s32)(*slot + 0x10));
    }
    loaded = *slot;
    if (*(u32 *)(loaded + 4) != 0) {
        *(u32 *)(loaded + 4) += (u32)loaded;
        loaded = *slot;
    }
    if (*(u32 *)(loaded + 8) != 0) {
        *(u32 *)(loaded + 8) += (u32)loaded;
        loaded = *slot;
    }
    *slot = loaded + 0x10;
    func_1503D484(*slot, identity);
    func_1503D510(identity);
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    declarations = ('    s32 size;', '    u8 **slot = &D_800D1588[identity];', '    u8 *loaded;')
    original = '\n'.join(declarations)
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'declarations-'+str(index), SELECTED.replace(original, '\n'.join(order))
    yield 'separate-slot-init', SELECTED.replace('u8 **slot = &D_800D1588[identity];', 'u8 **slot;').replace(
        '    if (*slot != NULL)', '    slot = &D_800D1588[identity];\n    if (*slot != NULL)')
    yield 'allocation-expression', SELECTED.replace(
        '    loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity));\n    if (loaded == NULL)',
        '    if ((loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity))) == NULL)')
    yield 'word-loaded-view', SELECTED.replace('u8 *loaded;', 'u32 *loaded;').replace(
        '*slot = loaded;', '*slot = (u8 *)loaded;').replace('loaded = *slot;', 'loaded = (u32 *)*slot;').replace(
        '*(u32 *)(loaded + 4)', 'loaded[1]').replace('*(u32 *)(loaded + 8)', 'loaded[2]').replace(
        '*slot = loaded + 0x10;', '*slot = (u8 *)loaded + 0x10;')
    live = SELECTED.replace('    loaded = *slot;\n', '').replace(
        '*(u32 *)loaded', '*(u32 *)*slot').replace('(u32)loaded', '(u32)*slot').replace(
        '*(u32 *)(loaded + 4)', '*(u32 *)(*slot + 4)').replace(
        '*(u32 *)(loaded + 8)', '*(u32 *)(*slot + 8)').replace('*slot = loaded + 0x10;', '*slot += 0x10;')
    yield 'live-slot', live
    yield 'live-slot-inverted-failure', live.replace('if (loaded == NULL)', 'if (!loaded)')
    yield 'live-slot-expression', live.replace(
        '    loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity));\n    if (loaded == NULL)',
        '    if ((loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity))) == NULL)')
    yield 'live-slot-published-expression', live.replace('    u8 *loaded;\n', '').replace(
        '    loaded = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity));\n    if (loaded == NULL)',
        '    if ((*slot = func_1502B5C8(&size, 2, 15, func_1503D5F0(identity))) == NULL)').replace(
        '    *slot = loaded;\n', '')
    yield 'live-slot-explicit-final', live.replace('*slot += 0x10;', '*slot = *slot + 0x10;')
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'live-declarations-'+str(index), live.replace(original, '\n'.join(order))
    reused = live.replace('s32 unused)', 's32 loaded)').replace('    u8 *loaded;\n', '').replace(
        'loaded = func_1502B5C8(', 'loaded = (s32)func_1502B5C8(').replace('loaded == NULL', 'loaded == 0').replace(
        '*slot = loaded;', '*slot = (u8 *)loaded;')
    yield 'reuse-incoming-word', reused
    yield 'reuse-incoming-word-slot-first', reused.replace(
        '    s32 size;\n    u8 **slot = &D_800D1588[identity];',
        '    u8 **slot = &D_800D1588[identity];\n    s32 size;')
    yield 'reuse-incoming-word-expression', reused.replace(
        '    loaded = (s32)func_1502B5C8(&size, 2, 15, func_1503D5F0(identity));\n    if (loaded == 0)',
        '    if ((loaded = (s32)func_1502B5C8(&size, 2, 15, func_1503D5F0(identity))) == 0)')
    reused_pointer = live.replace('s32 unused)', 'u8 *loaded)').replace('    u8 *loaded;\n', '')
    yield 'reuse-incoming-pointer', reused_pointer
    yield 'reuse-incoming-pointer-slot-first', reused_pointer.replace(
        '    s32 size;\n    u8 **slot = &D_800D1588[identity];',
        '    u8 **slot = &D_800D1588[identity];\n    s32 size;')
    for scope in ('size', 'loaded', 'slot', 'all'):
        body = SELECTED
        for variable, declaration in zip(('size','slot','loaded'), declarations):
            if scope in (variable,'all'):
                body = body.replace(declaration, declaration.replace('    ', '    register ',1)) if variable != 'size' else body
        yield 'register-'+scope, body


QUALIFIED = dict(candidates())['reuse-incoming-word'].replace('        }', '    }').replace(
    '    s32 size;', '    /* Ignore the incoming second word; reuse it for the returned address. */\n    s32 size;')
PAIR_SOURCE_SHA = 'c5e63d79936dc66521f8cd1bc284c0f09c854e8a33889994d1876c076fb0450b'


def compile_candidate(root, out, name, body=QUALIFIED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before, body=QUALIFIED):
    anchor = 'extern u8 *D_800C6360[];'
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1503D660();') != 1:
        raise ValueError('stale descriptor loader body or forward declaration')
    if before.count(anchor) != 1 or 'extern u8 *D_800D1588[];' in before or 'void *func_1502B5C8(s32 *, u32, ...);' in before:
        raise ValueError('stale descriptor loader declarations')
    return before.replace(ORIGINAL,body).replace('s32 func_1503D660();','s32 func_1503D660(s32, s32);').replace(
        anchor, anchor+'\nextern u8 *D_800D1588[];\nvoid *func_1502B5C8(s32 *, u32, ...);')


def pair_source(root):
    """Reverse only this exact complete successor for the frozen pair-stage audit."""
    source = (root/SOURCE).read_text()
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED) == 1
    assert source.count('s32 func_1503D660(s32, s32);') == 1
    assert source.count('extern u8 *D_800D1588[];') == 1
    assert source.count('void *func_1502B5C8(s32 *, u32, ...);') == 1
    before = source.replace(QUALIFIED,ORIGINAL).replace('s32 func_1503D660(s32, s32);','s32 func_1503D660();').replace(
        '\nextern u8 *D_800D1588[];\nvoid *func_1502B5C8(s32 *, u32, ...);','')
    assert hashlib.sha256(before.encode('ascii')).hexdigest() == PAIR_SOURCE_SHA
    assert install(before) == source
    return before


def pair_elf(root, before):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset

    source = pair_source(root)
    actual = (root/'conker/build/conker.us.elf').read_bytes()
    if source == (root/SOURCE).read_text():
        return actual
    start = elf_slot_offset(actual,ENTRY,WORDS*4)
    extent = symbol_size_offset(actual,FUNCTION,ENTRY)
    retail = (root/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    assert actual[start:start+WORDS*4] == retail
    assert struct.unpack_from('>I',actual,extent)[0] == WORDS*4
    old_start = elf_slot_offset(before,ENTRY,WORDS*4)
    old_extent = symbol_size_offset(before,FUNCTION,ENTRY)
    assert struct.unpack_from('>I',before,old_extent)[0] == 12
    result = bytearray(actual)
    result[start:start+WORDS*4] = before[old_start:old_start+WORDS*4]
    struct.pack_into('>I',result,extent,12)
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--filter',default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-descriptor-resource-loader'
    records = []
    for name,body in [('qualified',QUALIFIED), *candidates()]:
        if args.filter and args.filter not in name:
            continue
        for profile in ('owner','retail') if args.profiles else ('owner',):
            meta,words = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
