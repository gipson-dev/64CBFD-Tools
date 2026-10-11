"""Recover complete record-to-actor mask transfer and callback-aware teardown."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503E260, 0x6B710, 89
FUNCTION, SOURCE = 'func_1503E260', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503E260() {\n    return 0;\n}'
ANCHOR = 's32 func_1503E82C();'
LOCAL_DECLARATIONS = 'extern u8 *D_80084460[];\nvoid func_10004074(void *);\n'
DECLARATIONS = '#include "variables.h"\nextern u8 D_80098914[];\ns32 func_1503E1F4(s32, s32);\n'+LOCAL_DECLARATIONS
SYMBOLS = dict(D_800C6660=0x800C6660, D_800CC2D0=0x800CC2D0,
    D_80084460=0x80084460, D_80098914=0x80098914,
    func_1503E1F4=0x1503E1F4, func_10004074=0x10004074)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
FLAT = '''void func_1503E260(s32 slot) {
    struct106 *record = &D_800C6660[slot];
    u8 *bits;
    s32 count;
    s32 index;
    struct127 *actor;

    if (record->unkF != 0) {
        bits = D_80084460[((u8 *)record)[0xE]];
        if (bits != NULL) {
            count = D_80098914[((u8 *)record)[0xE]];
            for (index = 0; index < count; index++, bits++) {
                if (*bits != 255 && func_1503E1F4(index, slot) != 0) {
                    D_800CC2D0[slot].unk94 |= 1U << *bits;
                }
            }
        }
        actor = &D_800CC2D0[slot];
        record->unkF = 0;
        if (record->unk0 != 0) {
            func_10004074((void *)record->unk0);
        }
        record->unk0 = 0;
        actor->unk74 &= ~0x80;
    }
}'''

SELECTED = FLAT.replace('index++, bits++', 'index++').replace('*bits !=', 'bits[index] !=').replace(
    '<< *bits', '<< bits[index]').replace('    struct127 *actor;\n', '').replace(
    '        actor = &D_800CC2D0[slot];\n', '').replace('actor->unk74', 'D_800CC2D0[slot].unk74')
GUARD_ROWS = (('generated_6B320', FUNCTION, '0x120', '0xAFA20038', '0xAFA2003C', '-', '-',
    'Normalize closed record teardown actor-address spill pair', '', '', 'false'),
    ('generated_6B320', FUNCTION, '0x124', '0x8FA20038', '0x8FA2003C', '-', '-',
    'Normalize closed record teardown actor-address spill pair', '', '', 'false'))


def candidates():
    yield 'selected', SELECTED
    yield 'flat', FLAT
    indexed = FLAT.replace('index++, bits++', 'index++').replace('*bits !=', 'bits[index] !=').replace('<< *bits', '<< bits[index]')
    inline = indexed.replace('    struct127 *actor;\n', '').replace(
        '        actor = &D_800CC2D0[slot];\n', '').replace('actor->unk74', 'D_800CC2D0[slot].unk74')
    yield 'initial-s32-state', inline.replace('    s32 index;', '    s32 index;\n    s32 state = record->unkF;').replace(
        'if (record->unkF != 0)', 'if (state != 0)')
    yield 'initial-u8-state', inline.replace('    s32 index;', '    s32 index;\n    u8 state = record->unkF;').replace(
        'if (record->unkF != 0)', 'if (state != 0)')
    yield 'initial-index-state', inline.replace('    if (record->unkF != 0)',
        '    index = record->unkF;\n    if (index != 0)')
    yield 'initial-mask-temp', inline.replace('    s32 index;', '    s32 index;\n    u32 mask;').replace(
        '                    D_800CC2D0[slot].unk94 |= 1U << bits[index];',
        '                    mask = 1U << bits[index];\n                    D_800CC2D0[slot].unk94 |= mask;')
    yield 'initial-bit-temp', inline.replace('    s32 index;', '    s32 index;\n    u8 bit;').replace(
        '                    D_800CC2D0[slot].unk94 |= 1U << bits[index];',
        '                    bit = bits[index];\n                    D_800CC2D0[slot].unk94 |= 1U << bit;')
    yield 'inline-u8-count', inline.replace('s32 count;', 'u8 count;')
    yield 'inline-u32-count', inline.replace('s32 count;', 'u32 count;')
    yield 'inline-u32-index', inline.replace('s32 index;', 'u32 index;')
    yield 'inline-locals-reversed', inline.replace('    u8 *bits;\n    s32 count;\n    s32 index;',
        '    s32 index;\n    s32 count;\n    u8 *bits;')
    yield 'inline-record-late', inline.replace('    struct106 *record = &D_800C6660[slot];',
        '    struct106 *record;').replace('    if (record->unkF != 0)',
        '    record = &D_800C6660[slot];\n    if (record->unkF != 0)')
    yield 'inline-buffer-temp', inline.replace('    s32 index;', '    s32 index;\n    s32 buffer;').replace(
        '        record->unkF = 0;', '        buffer = record->unk0;\n        record->unkF = 0;').replace(
        'if (record->unk0 != 0)', 'if (buffer != 0)').replace('(void *)record->unk0', '(void *)buffer')
    yield 'inline-group-temp', inline.replace('    s32 index;', '    s32 index;\n    s32 group;').replace(
        '        bits = D_80084460[((u8 *)record)[0xE]];',
        '        group = ((u8 *)record)[0xE];\n        bits = D_80084460[group];')
    yield 'inline-flag-temp', inline.replace('    s32 index;', '    s32 index;\n    u8 flags;').replace(
        '        record->unk0 = 0;\n        D_800CC2D0[slot].unk74 &= ~0x80;',
        '        flags = D_800CC2D0[slot].unk74;\n        record->unk0 = 0;\n        D_800CC2D0[slot].unk74 = flags & ~0x80;')
    yield 'inline-cached-flag-pointer', inline.replace('    s32 index;', '    s32 index;\n    u8 *flag;').replace(
        '        record->unkF = 0;', '        flag = &D_800CC2D0[slot].unk74;\n        record->unkF = 0;').replace(
        'D_800CC2D0[slot].unk74 &= ~0x80', '*flag &= ~0x80')
    yield 'inline-reused-table-pointer', inline.replace('        record->unkF = 0;',
        '        bits = &D_800CC2D0[slot].unk74;\n        record->unkF = 0;').replace(
        'D_800CC2D0[slot].unk74 &= ~0x80', '*bits &= ~0x80')
    yield 'indexed-inline-actor', indexed.replace('    struct127 *actor;\n', '').replace(
        '        actor = &D_800CC2D0[slot];\n', '').replace('actor->unk74', 'D_800CC2D0[slot].unk74')
    yield 'indexed-local-flag', indexed.replace('    struct127 *actor;', '    struct127 *actor;\n    u8 flags;').replace(
        '        record->unk0 = 0;\n        actor->unk74 &= ~0x80;',
        '        flags = actor->unk74;\n        record->unk0 = 0;\n        actor->unk74 = flags & ~0x80;')
    yield 'indexed-inner-actor', indexed.replace('    struct127 *actor;\n', '').replace(
        '        actor = &D_800CC2D0[slot];', '        {\n        struct127 *actor = &D_800CC2D0[slot];').replace(
        '        actor->unk74 &= ~0x80;', '        actor->unk74 &= ~0x80;\n        }')
    yield 'indexed-byte-actor', indexed.replace('struct127 *actor;', 'u8 *actor;').replace(
        'actor = &D_800CC2D0[slot]', 'actor = (u8 *)&D_800CC2D0[slot]').replace('actor->unk74', 'actor[0x74]')
    yield 'indexed-u32-actor', indexed.replace('struct127 *actor;', 'u32 actor;').replace(
        'actor = &D_800CC2D0[slot]', 'actor = (u32)&D_800CC2D0[slot]').replace('actor->unk74', '((u8 *)actor)[0x74]')
    yield 'indexed-actor-first', indexed.replace('    struct106 *record', '    struct127 *actor;\n    struct106 *record').replace(
        '    s32 index;\n    struct127 *actor;', '    s32 index;')
    yield 'indexed-byte-mask-first', indexed.replace('        record->unk0 = 0;\n        actor->unk74 &= ~0x80;',
        '        actor->unk74 &= ~0x80;\n        record->unk0 = 0;')
    yield 'signed-mask', FLAT.replace('1U <<', '1 <<')
    yield 'mask-bit-range', FLAT.replace('1U << *bits', '1U << (*bits & 31)')
    yield 'indexed-bits', indexed
    yield 'nested-test', FLAT.replace('if (*bits != 255 && func_1503E1F4(index, slot) != 0) {',
        'if (*bits != 255) {\n                    if (func_1503E1F4(index, slot) != 0) {').replace(
        '                    D_800CC2D0[slot].unk94 |= 1U << *bits;\n',
        '                    D_800CC2D0[slot].unk94 |= 1U << *bits;\n                    }\n')
    yield 'inline-final-actor', FLAT.replace('    struct127 *actor;\n', '').replace(
        '        actor = &D_800CC2D0[slot];\n', '').replace('actor->unk74', 'D_800CC2D0[slot].unk74')
    yield 'buffer-local', FLAT.replace('    struct127 *actor;', '    struct127 *actor;\n    s32 buffer;').replace(
        '        record->unkF = 0;', '        buffer = record->unk0;\n        record->unkF = 0;').replace(
        'if (record->unk0 != 0)', 'if (buffer != 0)').replace('(void *)record->unk0', '(void *)buffer')
    yield 'clear-before-actor', FLAT.replace('        actor = &D_800CC2D0[slot];\n        record->unkF = 0;',
        '        record->unkF = 0;\n        actor = &D_800CC2D0[slot];')


def install(source):
    assert source.count(ORIGINAL) == source.count(ANCHOR) == 1
    assert LOCAL_DECLARATIONS not in source and SELECTED not in source
    return source.replace(ORIGINAL, SELECTED).replace(ANCHOR, ANCHOR+'\n'+LOCAL_DECLARATIONS.rstrip())


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+out.getvalue().encode('ascii')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-mask-teardown'
    measurements = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            measurements.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
