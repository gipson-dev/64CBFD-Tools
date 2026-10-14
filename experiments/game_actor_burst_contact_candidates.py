"""Recover the complete threshold/contact callback and its mixed O32 effect ABI."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151A743C, 0x1D48EC, 117
FUNCTION = 'func_151A743C'
SOURCE = 'conker/src/game/generated_1D43B0.c'
ORIGINAL = 's32 func_151A743C() {\n    return 0;\n}'
MARKER = 'extern s32 D_800BE9E4;'
RECORD = '''typedef struct {
    f32 field00;
    u8 *animation;
    u8 field08, field09;
    s16 field0A, field0C;
    u8 reserved0E[2];
} BurstExtra1D43B0;
'''
DECLARATIONS = '''void func_1516972C(u32);
void func_1514AB5C(f32, f32, s32, f32, s32, f32, f32, f32, f32, s16, s16, u8);
'''
SYMBOLS = dict(func_1516972C=0x1516972C, func_150ADA20=0x150ADA20, func_1514AB5C=0x1514AB5C)
BASE = '''s32 func_151A743C(u8 *actor, f32 arg1, s32 unused, s32 context, f32 arg4) {
    BurstExtra1D43B0 *extra = (BurstExtra1D43B0 *)(actor + 0x170);
    f32 threshold, velocity, value, half;
    u8 variant;
    u32 count;

    *(f32 *)(actor + 0x3C) = *(f32 *)(actor + 0x10) + arg4;
    if (*(u32 *)(actor + 0x174) != 0) {
        func_1516972C((u32)extra->animation);
        extra->animation = NULL;
    }
    extra = (BurstExtra1D43B0 *)(actor + 0x170);
    threshold = extra->field00;
    velocity = *(f32 *)(actor + 0x48);
    if (threshold < velocity) {
        *(u32 *)(actor + 0x60) &= ~7;
        *(u32 *)(actor + 0x60) &= ~8;
        *(u32 *)(actor + 0x60) &= ~0x40;
        *(u32 *)(actor + 0x60) &= ~0x20;
        *(f32 *)(actor + 0x44) = 0.0f;
        *(f32 *)(actor + 0x48) = 0.0f;
        *(f32 *)(actor + 0x4C) = 0.0f;
        if (*(s16 *)(actor + 0x64) > 32) {
            *(s16 *)(actor + 0x64) = 32;
        }
        if (extra->field08 != 0) {
            variant = extra->field09 != 0;
            count = (u32)func_150ADA20() % 3 + 2;
            value = *(f32 *)(actor + 0x18);
            half = value * 0.5f;
            func_1514AB5C(arg1, arg4, context, value * 35.0f, count,
                value, half, value, half, extra->field0A, extra->field0C, variant);
        }
    } else {
        value = *(f32 *)(actor + 0x14);
        *(f32 *)(actor + 0x44) *= value;
        *(f32 *)(actor + 0x48) = -velocity * value;
        *(f32 *)(actor + 0x4C) *= value;
        *(f32 *)(actor + 0x50) *= value;
        *(f32 *)(actor + 0x54) *= value;
        *(f32 *)(actor + 0x58) *= value;
    }
    return 1;
}'''
SELECTED = BASE


def compact_forms():
    for inline_compare, inline_half, flag_style in itertools.product((False, True), (False, True), range(3)):
        body = BASE
        if inline_compare:
            body = body.replace('f32 threshold, velocity, value, half;', 'f32 velocity, value, half;').replace(
                '    threshold = extra->field00;\n    velocity = *(f32 *)(actor + 0x48);\n'
                '    if (threshold < velocity)', '    if (extra->field00 < (velocity = *(f32 *)(actor + 0x48)))')
        if inline_half:
            body = body.replace('value, half;', 'value;').replace('            half = value * 0.5f;\n', '').replace(
                'value, half, value, half,', 'value, value * 0.5f, value, value * 0.5f,')
        if flag_style == 1:
            body = body.replace('            variant = extra->field09 != 0;',
                '            variant = 0;\n            if (extra->field09 != 0) {\n'
                '                variant = 1;\n            }')
        elif flag_style == 2:
            body = body.replace('            variant = extra->field09 != 0;',
                '            if (extra->field09 != 0) {\n                variant = 1;\n'
                '            } else {\n                variant = 0;\n            }')
        yield 'compact-compare%d-half%d-flag%d' % (inline_compare, inline_half, flag_style), body


COMPACT = dict(compact_forms())['compact-compare1-half1-flag1']


def workspace_forms():
    yield 'workspace-parameter-count', COMPACT.replace('    u32 count;\n', '').replace(
        '            count = ', '            unused = ').replace('value * 35.0f, count,', 'value * 35.0f, unused,')
    for width in ('u8', 'u16', 's32'):
        yield 'workspace-count-' + width, COMPACT.replace('    u32 count;', '    %s count;' % width)
    for ordering in (False, True):
        body = COMPACT.replace('    f32 velocity, value;', '    f32 velocity;').replace(
            '    u32 count;', '    u32 count;\n    f32 value;')
        if ordering:
            body = body.replace('    u8 variant;\n', '').replace(
                '    BurstExtra1D43B0 *extra', '    u8 variant;\n    BurstExtra1D43B0 *extra')
        yield 'workspace-declaration-order%d' % ordering, body


def field_load_forms():
    for unnamed_velocity, unnamed_value, recompute in itertools.product((False, True), repeat=3):
        if not (unnamed_velocity or unnamed_value):
            continue
        body = COMPACT
        if unnamed_velocity:
            body = body.replace('    f32 velocity, value;', '    f32 value;').replace(
                '(velocity = *(f32 *)(actor + 0x48))', '*(f32 *)(actor + 0x48)').replace(
                '-velocity * value', '-*(f32 *)(actor + 0x48) * value')
        if unnamed_value:
            body = body.replace('    f32 velocity, value;', '    f32 velocity;').replace('    f32 value;\n', '')
            body = body.replace('            value = *(f32 *)(actor + 0x18);\n', '').replace(
                '        value = *(f32 *)(actor + 0x14);\n', '')
            start, tail = body.split('    } else {\n', 1)
            start = start.replace('value', '*(f32 *)(actor + 0x18)')
            tail = tail.replace('value', '*(f32 *)(actor + 0x14)')
            body = start + '    } else {\n' + tail
        if not recompute:
            body = body.replace('    extra = (BurstExtra1D43B0 *)(actor + 0x170);\n', '')
        yield 'fields-velocity%d-value%d-recompute%d' % (unnamed_velocity, unnamed_value, recompute), body


NEAR_MATCH = dict(field_load_forms())['fields-velocity1-value1-recompute0']
SELECTED = NEAR_MATCH.replace('-*(f32 *)(actor + 0x48) * *(f32 *)(actor + 0x14)',
    '*(f32 *)(actor + 0x14) * -*(f32 *)(actor + 0x48)')


def candidates():
    yield 'base', BASE
    yield 'selected', SELECTED
    yield 'damping-uncommuted', NEAR_MATCH
    yield 'sixth-unused-argument', SELECTED.replace('s32 context, f32 arg4)',
        's32 context, f32 arg4, u8 *unusedOutput)')
    yield from compact_forms()
    yield from workspace_forms()
    yield from field_load_forms()
    for inline_compare, explicit_flag, recompute in itertools.product((False, True), repeat=3):
        if not (inline_compare or explicit_flag or not recompute):
            continue
        body = BASE
        if inline_compare:
            body = body.replace('f32 threshold, velocity, value, half;', 'f32 velocity, value, half;').replace(
                '    threshold = extra->field00;\n    velocity = *(f32 *)(actor + 0x48);\n'
                '    if (threshold < velocity)', '    if (extra->field00 < (velocity = *(f32 *)(actor + 0x48)))')
        if explicit_flag:
            body = body.replace('            variant = extra->field09 != 0;',
                '            if (extra->field09 != 0) {\n                variant = 1;\n'
                '            } else {\n                variant = 0;\n            }')
        if not recompute:
            body = body.replace('    extra = (BurstExtra1D43B0 *)(actor + 0x170);\n', '')
        yield 'shape-compare%d-flag%d-recompute%d' % (inline_compare, explicit_flag, recompute), body
    for zero in ('0', '0.0', '(f32)0'):
        yield 'typed-zero-' + zero.replace('(', '').replace(')', ''), BASE.replace('= 0.0f;', '= %s;' % zero)
    for unsigned in (False, True):
        yield 'count-%s' % ('unsigned-inline' if unsigned else 'signed-negative-control'), BASE.replace(
            'count = (u32)func_150ADA20() % 3 + 2;',
            'count = %sfunc_150ADA20() %% 3 + 2;' % ('(u32)' if unsigned else ''))


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS='s32 func_150ADA20(void);\n' + DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def recovered_owner(before):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1:
        raise ValueError('Expected one contact placeholder and declaration marker')
    return before.replace(MARKER, DECLARATIONS + '\n' + MARKER).replace(ORIGINAL, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-burst-contact'
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
