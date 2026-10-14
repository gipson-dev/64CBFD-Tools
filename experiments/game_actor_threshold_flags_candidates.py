"""Recover the complete leaf threshold/rotation/flag/color updater."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151A77C0, 0x1D4C70, 47
FUNCTION = 'func_151A77C0'
SOURCE = 'conker/src/game/generated_1D43B0.c'
ORIGINAL = 's32 func_151A77C0() {\n    return 0;\n}'
SYMBOLS = dict(D_800BE9E4=0x800BE9E4)
BASE = '''void func_151A77C0(u8 *arg0) {
    u8 *params = arg0 + 0x50;
    s32 value = *(s16 *)(arg0 + 0x38);
    s32 delta;
    s32 intensity;

    if (value < *(s16 *)(params + 4)) {
        arg0[0x3F] = value * (u32)*(s16 *)(params + 6);
    }
    if (value < *(s16 *)(params + 8)) {
        delta = *(s16 *)(params + 0xA) * (u32)D_800BE9E4;
        *(s16 *)(arg0 + 0x34) += delta;
        *(s16 *)(arg0 + 0x36) += delta;
        value = *(s16 *)(arg0 + 0x38);
    }
    if (value < *(s16 *)params) {
        arg0[0x2F] = 0x15;
        *(u16 *)(arg0 + 0x44) |= 0x201;
        intensity = value * (u32)*(s16 *)(params + 2);
        *(u32 *)(arg0 + 0x14) = 0xC000F;
        arg0[0x42] = intensity;
        arg0[0x41] = intensity;
        arg0[0x40] = intensity;
    }
}'''
SELECTED = BASE.replace('s32 delta;', 'u32 delta;').replace('s32 intensity;', 'u32 intensity;')


def candidates():
    yield 'selected', SELECTED
    for flags_first, explicit_unsigned, multiplier_before in itertools.product((False, True), repeat=3):
        body = BASE
        if flags_first:
            body = body.replace('        arg0[0x2F] = 0x15;\n        *(u16 *)(arg0 + 0x44) |= 0x201;',
                '        *(u16 *)(arg0 + 0x44) |= 0x201;\n        arg0[0x2F] = 0x15;')
        if explicit_unsigned:
            body = body.replace('s32 delta;', 'u32 delta;').replace('s32 intensity;', 'u32 intensity;')
        if multiplier_before:
            body = body.replace('        intensity = value * (u32)*(s16 *)(params + 2);\n', '').replace(
                '        arg0[0x2F] =', '        intensity = value * (u32)*(s16 *)(params + 2);\n        arg0[0x2F] =')
        yield 'shape-flags%d-unsigned%d-multiplier%d' % (flags_first, explicit_unsigned, multiplier_before), body
    yield from lifetime_forms()


def lifetime_forms():
    for registered, separate_store, commute in itertools.product((False, True), repeat=3):
        body = BASE
        if registered:
            body = body.replace('    s32 delta;', '    register s32 delta;').replace(
                '    s32 intensity;', '    register s32 intensity;')
        if separate_store:
            body = body.replace('*(s16 *)(arg0 + 0x34) += delta;',
                '*(s16 *)(arg0 + 0x34) = (u32)*(s16 *)(arg0 + 0x34) + (u32)delta;').replace(
                '*(s16 *)(arg0 + 0x36) += delta;',
                '*(s16 *)(arg0 + 0x36) = (u32)*(s16 *)(arg0 + 0x36) + (u32)delta;')
        if commute:
            body = body.replace('value * (u32)*(s16 *)(params + 6)', '(u32)value * *(s16 *)(params + 6)').replace(
                'value * (u32)*(s16 *)(params + 2)', '(u32)value * *(s16 *)(params + 2)')
        yield 'lifetime-register%d-store%d-commute%d' % (registered, separate_store, commute), body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS='extern s32 D_800BE9E4;\n', SYMBOLS=SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    meta['frame'] = (-words[0]) & 65535 if words[0] >> 16 == 0x27BD else 0
    return meta, words


def recovered_owner(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('Expected one threshold updater placeholder')
    return before.replace(ORIGINAL, SELECTED)


GUARDS = (
    (0x20, 0x01E30019, 0x006F0019),
    (0x3C, 0x844E0000, 0x84580000),
    (0x48, 0x848A0034, 0x848C0034),
    (0x4C, 0x848C0036, 0x848E0036),
    (0x54, 0x84830038, 0x00005812),
    (0x58, 0x00002812, 0x018B6821),
    (0x5C, 0x01455821, 0x01CB7821),
    (0x60, 0x01856821, 0xA48D0034),
    (0x64, 0xA48B0034, 0xA48F0036),
    (0x68, 0xA48D0036, 0x84830038),
    (0x6C, 0x844E0000, 0x84580000),
    (0x70, 0x006E082A, 0x0078082A),
    (0x7C, 0x94980044, 0x94880044),
    (0x80, 0x240F0015, 0x24190015),
    (0x84, 0xA08F002F, 0xA099002F),
    (0x88, 0x37190201, 0x35090201),
    (0x8C, 0xA4990044, 0xA4890044),
    (0x90, 0x84480002, 0x844A0002),
    (0x94, 0x3C09000C, 0x3C0C000C),
    (0x98, 0x3529000F, 0x358C000F),
    (0x9C, 0x01030019, 0x006A0019),
    (0xA0, 0xAC890014, 0xAC8C0014),
    (0xA4, 0x00002812, 0x00005812),
    (0xA8, 0xA0850042, 0xA08B0042),
    (0xAC, 0xA0850041, 0xA08B0041),
    (0xB0, 0xA0850040, 0xA08B0040),
)


def guard_rows(words, relocations):
    if len(words) != 47 or words[0] != 0x84830038:
        raise ValueError('Unexpected complete threshold updater shape')
    rows = []
    for offset, expected, replacement in GUARDS:
        if words[offset // 4] != expected or relocations.get(offset):
            raise ValueError('Unexpected threshold allocation, schedule or relocation')
        rows.append(dict(filename='generated_1D43B0', function=FUNCTION, offset='0x%03X' % offset,
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations='-', replacement_relocations='-',
            note='Normalize threshold flags updater register allocation and value reload schedule',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-threshold-flags'
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
