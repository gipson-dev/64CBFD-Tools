"""Recover the complete first-matching-group pointer/count propagation leaf."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503D510, 0x6A9C0, 56
FUNCTION, SOURCE = 'func_1503D510', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503D510() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 D_80098888[];
extern u8 *D_80084410[];
extern u8 *D_800D1588[];
extern s16 D_800C5A90[];
'''
SYMBOLS = dict(D_80098888=0x80098888, D_80084410=0x80084410,
    D_800D1588=0x800D1588, D_800C5A90=0x800C5A90)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3','-Wo,-loopunroll,0'), retail=('-O2','-g3'),
    o1compact=('-O1','-g3','-Wo,-loopunroll,0'))
SELECTED = '''void func_1503D510(s32 identity) {
    s32 group;
    s32 member;
    s32 count;
    u8 *members;

    for (group = 0; group < 5; group++) {
        count = D_80098888[group];
        members = D_80084410[group];
        for (member = 0; member < count; member++) {
            if (identity == members[member]) {
                for (group = 0; group < count; group++) {
                    D_800D1588[members[group]] = D_800D1588[identity];
                    D_800C5A90[members[group]] = D_800C5A90[identity];
                }
                return;
            }
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    tables = '''void func_1503D510(s32 identity) {
    s32 group;
    s32 member;
    s32 copy;

    for (group = 0; group < 5; group++) {
        for (member = 0; member < D_80098888[group]; member++) {
            if (identity == D_80084410[group][member]) {
                for (copy = 0; copy < D_80098888[group]; copy++) {
                    D_800D1588[D_80084410[group][copy]] = D_800D1588[identity];
                    D_800C5A90[D_80084410[group][copy]] = D_800C5A90[identity];
                }
                return;
            }
        }
    }
}'''
    yield 'table-counts', tables
    yield 'table-counts-unsigned', tables.replace(
        'D_800C5A90[D_80084410[group][copy]]','((u16 *)D_800C5A90)[D_80084410[group][copy]]').replace(
        'D_800C5A90[identity]', '((u16 *)D_800C5A90)[identity]')
    yield 'table-counts-outer-do', tables.replace('    for (group = 0; group < 5; group++) {',
        '    group = 0;\n    do {').replace('        }\n    }\n}', '        }\n        group++;\n    } while (group != 5);\n}')
    explicit = '''void func_1503D510(s32 identity) {
    s32 group = 0;
    s32 member;
    s32 count;
    u8 *members;

    do {
        count = D_80098888[group];
        member = 0;
        if (count > 0) {
            members = D_80084410[group];
            do {
                if (identity == members[member]) {
                    group = 0;
                    if (count > 0) {
                        do {
                            D_800D1588[members[group]] = D_800D1588[identity];
                            D_800C5A90[members[group]] = (u16)D_800C5A90[identity];
                            group++;
                        } while (group < count);
                    }
                    return;
                }
                member++;
            } while (member < count);
        }
        group++;
    } while (group != 5);
}'''
    yield 'explicit-do', explicit
    yield 'explicit-do-member-first', explicit.replace(
        '                if (identity == members[member])', '                member++;\n                if (identity == members[member - 1])').replace(
        '                member++;\n            }', '            }')
    yield 'explicit-do-outer-less', explicit.replace('group != 5', 'group < 5')
    yield 'explicit-do-inner-for', explicit.replace(
        '                    group = 0;\n                    if (count > 0) {\n                        do {',
        '                    if (count > 0) {\n                        for (group = 0; group < count; group++) {').replace(
        '                            group++;\n                        } while (group < count);', '                        }')
    declarations = ('    s32 group;', '    s32 member;', '    s32 count;', '    u8 *members;')
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'declarations-'+str(index), SELECTED.replace('\n'.join(declarations),'\n'.join(order))
    gated = SELECTED.replace('        members = D_80084410[group];', '        if (count > 0) {\n        members = D_80084410[group];').replace(
        '        }\n    }\n}', '        }\n        }\n    }\n}')
    yield 'positive-count', gated
    inside = SELECTED.replace('        members = D_80084410[group];\n', '').replace(
        '            if (identity == members[member])', '            members = D_80084410[group];\n            if (identity == members[member])')
    yield 'inner-members', inside
    for base_name,base in (('plain',inside),('do',explicit)):
        for types in itertools.product(('s16','u16','u32'),('s16','u16','s32'),('s32','u8')):
            group,member,count=types
            yield base_name+'-types-'+'-'.join(types), base.replace('s32 group','%s group'%group).replace(
                's32 member','%s member'%member).replace('s32 count','%s count'%count).replace(
                'D_800C5A90[members[group]]','((u16 *)D_800C5A90)[members[group]]').replace(
                '(u16)D_800C5A90[identity]','((u16 *)D_800C5A90)[identity]')
    post = inside.replace('member < count; member++', 'member < count;').replace(
        'identity == members[member]', 'identity == members[member++]').replace(
        'group < count; group++', 'group < count;').replace(
        'D_800C5A90[members[group]]', '((u16 *)D_800C5A90)[members[group++]]').replace(
        'D_800C5A90[identity];', '((u16 *)D_800C5A90)[identity];')
    yield 'post-increment', post
    for name,body in (('plain',inside),('do',explicit),('post',post)):
        yield name+'-volatile-count-read', body.replace('D_80098888[group]','((volatile u8 *)D_80098888)[group]')
        yield name+'-opaque-count', body.replace('D_80098888[group]','*(u8 *)((u32)D_80098888 + group)')
        yield name+'-unsigned-half-view', body.replace(
            'D_800C5A90[members[group]]', '((u16 *)D_800C5A90)[members[group]]').replace(
            '(u16)D_800C5A90[identity]', '((u16 *)D_800C5A90)[identity]').replace(
            '= D_800C5A90[identity];', '= ((u16 *)D_800C5A90)[identity];')
    yield 'post-increment-key-local', post.replace('    s32 group;', '    s32 key = identity;\n    s32 group;').replace(
        'identity == members', 'key == members').replace('[identity]', '[key]')
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'post-declarations-'+str(index), post.replace('\n'.join(declarations),'\n'.join(order))
    reuse = inside.replace('s32 identity)', 's32 count)').replace('    s32 count;', '    s32 identity = count;')
    yield 'reuse-incoming-count', reuse
    yield 'reuse-incoming-count-gated', gated.replace('s32 identity)', 's32 count)').replace(
        '    s32 count;', '    s32 identity = count;')
    yield 'reuse-incoming-count-separate-key', reuse.replace('    s32 identity = count;', '    s32 identity;').replace(
        '    for (group = 0;', '    identity = count;\n    for (group = 0;', 1)
    yield 'unsigned-count', SELECTED.replace('s32 count;', 'u32 count;')
    yield 'halfword-unsigned', SELECTED.replace('D_800C5A90[identity];','(u16)D_800C5A90[identity];')
    yield 'member-index-inner', SELECTED.replace('for (group = 0; group < count; group++)','for (member = 0; member < count; member++)').replace(
        'D_800D1588[members[group]]','D_800D1588[members[member]]').replace('D_800C5A90[members[group]]','D_800C5A90[members[member]]')
    yield 'separate-copy-index', SELECTED.replace('    s32 group;','    s32 group;\n    s32 copy;').replace(
        'for (group = 0; group < count; group++)','for (copy = 0; copy < count; copy++)').replace(
        'D_800D1588[members[group]]','D_800D1588[members[copy]]').replace('D_800C5A90[members[group]]','D_800C5A90[members[copy]]')


QUALIFIED = dict(candidates())['table-counts-unsigned']
DESCRIPTOR_SOURCE_SHA = '491ba6e43604e7d8ce7dd9b0f60fd860eefa60bb8274e7b9c259448a2b50a526'


def install(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale group propagation body')
    return before.replace(ORIGINAL,QUALIFIED)


def descriptor_source(root):
    """Reverse only this complete exact successor for older frozen audits."""
    import hashlib
    from tools.experiments import game_record_resource_cleanup_candidates as cleanup
    source = cleanup.propagation_source(root)
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED) == 1
    before = source.replace(QUALIFIED,ORIGINAL)
    assert hashlib.sha256(before.encode('ascii')).hexdigest() == DESCRIPTOR_SOURCE_SHA
    assert install(before) == source
    return before


def descriptor_elf(root, before):
    import struct
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset

    source = descriptor_source(root)
    from tools.experiments import game_record_resource_cleanup_candidates as cleanup
    actual = cleanup.propagation_elf(root,before)
    if source == cleanup.propagation_source(root):
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


def compile_candidate(root, out, name, body=QUALIFIED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        meta, words = compiler.compile_candidate(root,out,name,body,profile)
    frames = [(-word)&65535 for word in words if word&0xFFFF0000 == 0x27BD0000 and word&0x8000]
    meta['frame'] = frames[0] if frames else 0
    return meta, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--filter',default='table-counts-unsigned')
    parser.add_argument('--all-profiles',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-group-publication-propagation'
    records = []
    for name,body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in PROFILES if args.all_profiles else (('owner','retail') if args.profiles else ('owner',)):
            meta,words = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
