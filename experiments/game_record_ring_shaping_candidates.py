"""Recover live backward ring trimming, wrapped phase and unsigned fade bytes."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D7CD0, 0x205180, 253
FUNCTION = 'func_151D7CD0'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D7CD0.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } ShapingVector151D7CD0;
typedef struct {
    ShapingVector151D7CD0 position;
    f32 velocity, length;
    u8 alpha, padding[3];
    f32 phase;
} ShapingRecord151D7CD0;
extern f32 D_800BE9A4;
extern f32 D_800AB2DC, D_800AB2E0, D_800AB2E4, D_800AB2E8;
f32 func_15143E64(f32 *vector);
f32 func_15144528(f32 value, f32 upper, f32 lower);
'''
SYMBOLS = {'D_800BE9A4': 0x800BE9A4, 'D_800AB2DC': 0x800AB2DC,
    'D_800AB2E0': 0x800AB2E0, 'D_800AB2E4': 0x800AB2E4,
    'D_800AB2E8': 0x800AB2E8, 'func_15143E64': 0x15143E64,
    'func_15144528': 0x15144528}
BASE = '''s32 func_151D7CD0(u8 *owner) {
    f32 *payload;
    f32 *records;
    f32 *previous;
    f32 *record;
    f32 vector[3];
    f32 total;
    f32 fraction;
    f32 distance;
    f32 start;
    f32 width;
    f32 inverse;
    s32 index;

    payload = *(f32 **)(owner + 0x98);
    records = *(f32 **)(owner + 0x94);
    if (*(s8 *)(owner + 0x2C) >= 2) {
        total = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        if (*(u16 *)(owner + 0x1E) & 2) {
            previous = (f32 *)(owner + 0x10);
        } else {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            previous = records + index * 7;
        }
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            vector[0] = record[0] - previous[0];
            vector[1] = record[1] - previous[1];
            vector[2] = record[2] - previous[2];
            fraction = func_15143E64(vector);
            total += fraction;
            record[4] = fraction;
            if (total > 80.0f) {
                if (record[4] != 0.0f) {
                    fraction = (total - 80.0f) * (1.0f / record[4]);
                    record[0] -= vector[0] * fraction;
                    record[1] -= vector[1] * fraction;
                    record[2] -= vector[2] * fraction;
                    record[4] *= 1.0f - fraction;
                }
                total = 80.0f;
                while (index != *(s8 *)(owner + 0x2D)) {
                    owner[0x2D] = *(s8 *)(owner + 0x2D) + 1;
                    if (*(s8 *)(owner + 0x2D) == owner[0x25]) {
                        owner[0x2D] = 0;
                    }
                    owner[0x2C] = *(s8 *)(owner + 0x2C) - 1;
                }
            }
            previous = record;
        } while (index != *(s8 *)(owner + 0x2D));
    }
    if (*(s8 *)(owner + 0x2C) >= 2) {
        payload[6] += -41.0f * D_800BE9A4;
        payload[6] = func_15144528(payload[6], D_800AB2DC, -16384.0f);
        distance = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            distance += record[4];
            record[6] = func_15144528(payload[6] + distance * D_800AB2E0,
                D_800AB2E4, -16384.0f);
        } while (index != *(s8 *)(owner + 0x2D));
    }
    if (*(s8 *)(owner + 0x2C) >= 2) {
        start = total * D_800AB2E8;
        width = total - start;
        inverse = 1.0f / width;
        distance = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            if (start < distance) {
                fraction = distance - start;
                if (width < fraction) {
                    fraction = width;
                }
                ((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);
            } else {
                ((u8 *)record)[0x14] = 60;
            }
            distance += record[4];
        } while (index != *(s8 *)(owner + 0x2D));
    }
    return 1;
}'''


def byte_stride(body):
    return body.replace('f32 *records;', 'u8 *records;').replace(
        'records = *(f32 **)', 'records = *(u8 **)').replace('records + index * 7', '(f32 *)(records + index * 0x1C)')


def phase_locals(body, record=False):
    body = body.replace('    f32 distance;\n', '').replace('    s32 index;\n', '')
    declaration = '        s32 index;\n'
    if record:
        pointer = 'ShapingRecord151D7CD0 *record;' if 'ShapingRecord151D7CD0 *record;' in body else 'f32 *record;'
        body = body.replace('    ' + pointer + '\n', '')
        declaration += '        ' + pointer + '\n'
    body = body.replace('        total = 0.0f;', declaration + '\n        total = 0.0f;')
    body = body.replace('        payload[6] +=', declaration + '        f32 distance;\n\n        payload[6] +=')
    return body.replace('        start = total', declaration + '        f32 distance;\n\n        start = total')


def staged_trim(body, stages=1):
    field = 'record->length' if 'record->length' in body else 'record[4]'
    body = body.replace('    f32 fraction;', '    f32 length;\n    f32 fraction;')
    body = body.replace('            if (total > 80.0f) {\n                if (' + field + ' != 0.0f) {',
        '            if (total > 80.0f) {\n                length = ' + field + ';\n                if (length != 0.0f) {')
    body = body.replace('(total - 80.0f) * (1.0f / ' + field + ')', '(total - 80.0f) * (1.0f / length)')
    body = body.replace(field + ' *= 1.0f - fraction;', field + ' = length * (1.0f - fraction);')
    if stages >= 2:
        body = body.replace('    f32 length;', '    f32 excess;\n    f32 reciprocal;\n    f32 length;')
        body = body.replace('                    fraction = (total - 80.0f) * (1.0f / length);',
            '                    reciprocal = 1.0f / length;\n                    excess = total - 80.0f;\n                    fraction = excess * reciprocal;')
    if stages >= 3:
        body = body.replace('    f32 excess;', '    f32 xTrim, yTrim, zTrim;\n    f32 excess;')
        for index, axis in enumerate('xyz'):
            output = 'record->position.' + axis if 'record->position.' in body else 'record[%d]' % index
            vector = 'vector.' + axis if 'vector.' in body else 'vector[%d]' % index
            body = body.replace('                    ' + output + ' -= ' + vector + ' * fraction;',
                '                    ' + axis + 'Trim = ' + vector + ' * fraction;\n                    ' + output + ' -= ' + axis + 'Trim;')
    return body


def typed_records(body):
    body = body.replace('f32 *records;', 'ShapingRecord151D7CD0 *records;').replace(
        'f32 *record;', 'ShapingRecord151D7CD0 *record;').replace('f32 *previous;', 'ShapingVector151D7CD0 *previous;')
    body = body.replace('records = *(f32 **)', 'records = *(ShapingRecord151D7CD0 **)').replace(
        'previous = (f32 *)(owner + 0x10);', 'previous = (ShapingVector151D7CD0 *)(owner + 0x10);')
    body = body.replace('previous = records + index * 7;', 'previous = &records[index].position;').replace(
        'record = records + index * 7;', 'record = records + index;').replace('previous = record;', 'previous = &record->position;')
    for index, axis in enumerate('xyz'):
        body = body.replace('record[%d]' % index, 'record->position.' + axis).replace('previous[%d]' % index, 'previous->' + axis)
    return body.replace('record[4]', 'record->length').replace('record[6]', 'record->phase').replace('((u8 *)record)[0x14]', 'record->alpha')


def fitting_candidates():
    for name, body in (('byte', byte_stride(BASE)), ('typed', typed_records(BASE))):
        for local in (False, True):
            current = phase_locals(body, record=True) if local else body
            yield 'fit-%s-local%d' % (name, local), current
            for stages in (1, 2, 3):
                yield 'fit-%s-local%d-trim%d' % (name, local, stages), staged_trim(current, stages)
            yield 'fit-%s-local%d-short-condition' % (name, local), current.replace('record[4] != 0.0f', 'record[4]').replace(
                'record->length != 0.0f', 'record->length')
            yield 'fit-%s-local%d-reverse-zero' % (name, local), current.replace('record[4] != 0.0f', '0.0f != record[4]').replace(
                'record->length != 0.0f', '0.0f != record->length')
    short = phase_locals(byte_stride(BASE), record=True).replace('record[4] != 0.0f', 'record[4]')
    for stages in (0, 1, 2, 3):
        current = phase_locals(byte_stride(BASE), record=True)
        if stages:
            current = staged_trim(current, stages)
        current = current.replace('record[4] != 0.0f', 'record[4]').replace('length != 0.0f', 'length')
        yield 'fit-short-trim%d' % stages, current
        yield 'fit-short-trim%d-scoped-fraction' % stages, scoped_fade(current, fraction=True)
        yield 'fit-short-trim%d-scoped-fade' % stages, scoped_fade(current, fraction=True, fields=True)
    for name, current in (('short', short), ('short-scoped', scoped_fade(short, fraction=True, fields=True))):
        for mode in ('break', 'leading', 'length-local', 'alpha-local'):
            yield 'fit-' + name + '-' + mode, fade_loop(current, mode)
    fitted = staged_trim(phase_locals(byte_stride(BASE), record=True), 3).replace('length != 0.0f', 'length')
    for mode in ('leading', 'break', 'length-local', 'alpha-local'):
        yield 'fit-trim3-' + mode, fade_loop(fitted, mode)
    for field in ('total', 'xTrim', 'excess', 'reciprocal', 'length', 'fraction', 'start', 'width', 'inverse', 'payload'):
        marker = '    f32 ' + field + ';' if field != 'xTrim' else '    f32 xTrim, yTrim, zTrim;'
        if field == 'payload':
            marker = '    f32 *payload;'
        placed = fitted.replace('    f32 vector[3];\n', '').replace(marker, '    f32 vector[3];\n' + marker)
        yield 'fit-trim3-vector-before-' + field, placed
    yield 'fit-trim3-separate-axes', fitted.replace('    f32 xTrim, yTrim, zTrim;', '    f32 xTrim;\n    f32 yTrim;\n    f32 zTrim;')
    separate = fitted.replace('    f32 xTrim, yTrim, zTrim;', '    f32 xTrim;\n    f32 yTrim;\n    f32 zTrim;')
    for axis in 'yz':
        placed = separate.replace('    f32 vector[3];\n', '').replace('    f32 ' + axis + 'Trim;',
            '    f32 vector[3];\n    f32 ' + axis + 'Trim;')
        yield 'fit-trim3-vector-before-' + axis + 'Trim', placed
    for mode in ('post', 'conditional-post', 'length-local'):
        yield 'fit-trim3-loop-' + mode, fade_loop(fitted, mode)
    for mode in ('split-length', 'split-distance', 'ceiling'):
        yield 'fit-trim3-' + mode, fade_loop(fitted, mode)
        yield 'fit-trim3-leading-' + mode, fade_loop(fade_loop(fitted, mode), 'leading')
    separate = fitted.replace('    f32 xTrim, yTrim, zTrim;', '    f32 xTrim;\n    f32 yTrim;\n    f32 zTrim;')
    placed = separate.replace('    f32 vector[3];\n', '').replace('    f32 yTrim;', '    f32 vector[3];\n    f32 yTrim;')
    yield 'fit-retail-extent', fade_loop(placed, 'split-distance')
    delta = fitted
    for index, axis in enumerate('xyz'):
        delta = delta.replace('            vector[%d] = record[%d] - previous[%d];' % (index, index, index),
            '            %sTrim = record[%d] - previous[%d];\n            vector[%d] = %sTrim;' % (axis, index, index, index, axis))
        delta = delta.replace('                    %sTrim = vector[%d] * fraction;\n                    record[%d] -= %sTrim;' % (axis, index, index, axis),
            '                    record[%d] -= vector[%d] * fraction;' % (index, index))
    yield 'fit-trim3-vector-deltas', fade_loop(delta, 'split-distance')
    yield 'fit-trim3-scoped-split-distance', fade_loop(scoped_fade(fitted, fraction=True, fields=True), 'split-distance')
    for replacement in ('length', 'record[4]'):
        if replacement == 'length':
            current = fitted.replace('            fraction = func_15143E64(vector);\n            total += fraction;\n            record[4] = fraction;',
                '            length = func_15143E64(vector);\n            total += length;\n            record[4] = length;')
        else:
            current = fitted.replace('            fraction = func_15143E64(vector);\n            total += fraction;\n            record[4] = fraction;',
                '            record[4] = func_15143E64(vector);\n            total += record[4];')
        yield 'fit-trim3-return-' + ('length' if replacement == 'length' else 'store'), current
    phase = fitted.replace('    f32 *payload;', '    f32 *payload;\n    f32 *phase;').replace('        payload[6] +=',
        '        phase = payload + 6;\n        *phase +=').replace('payload[6]', '*phase')
    yield 'fit-trim3-phase-pointer', phase
    for stages in (1, 2, 3):
        current = staged_trim(phase_locals(byte_stride(BASE), record=True), stages).replace('length != 0.0f', 'length')
        current = current.replace('    f32 total;', '    f32 total;\n    f32 savedTotal;').replace(
            '        } while (index != *(s8 *)(owner + 0x2D));',
            '        } while (index != *(s8 *)(owner + 0x2D));\n        savedTotal = total;', 1)
        current = current.replace('start = total *', 'start = savedTotal *').replace('width = total - start;', 'width = savedTotal - start;')
        yield 'fit-trim%d-saved-total' % stages, current
        yield 'fit-trim%d-saved-total-local' % stages, current.replace('    f32 total;\n', '').replace(
            '        total = 0.0f;', '        f32 total;\n\n        total = 0.0f;')


def scoped_fade(body, fraction=False, fields=False):
    gate = '    if (*(s8 *)(owner + 0x2C) >= 2) {\n'
    parts = body.split(gate)
    assert len(parts) == 4
    if fraction:
        parts[0] = parts[0].replace('    f32 fraction;\n', '')
        parts[1] = '        f32 fraction;\n' + parts[1]
        parts[3] = '        f32 fraction;\n' + parts[3]
    if fields:
        for field in ('start', 'width', 'inverse'):
            parts[0] = parts[0].replace('    f32 ' + field + ';\n', '')
            parts[3] = '        f32 ' + field + ';\n' + parts[3]
    return gate.join(parts)


def fade_loop(body, mode):
    gate = '    if (*(s8 *)(owner + 0x2C) >= 2) {\n'
    before, tail = body.rsplit(gate, 1)
    if mode == 'break':
        tail = tail.replace('        do {', '        for (;;) {').replace('        } while (index != *(s8 *)(owner + 0x2D));',
            '            if (index == *(s8 *)(owner + 0x2D)) {\n                break;\n            }\n        }')
    elif mode in ('leading', 'post', 'conditional-post'):
        tail = tail.replace('        index = *(s8 *)(owner + 0x2E);', '        index = *(s8 *)(owner + 0x2E) - 1;').replace(
            '        do {\n            index--;', '        do {')
        if mode == 'leading':
            tail = tail.replace('        do {', '        for (;;) {').replace('        } while (index != *(s8 *)(owner + 0x2D));',
                '            if (index == *(s8 *)(owner + 0x2D)) {\n                break;\n            }\n            index--;\n        }')
        elif mode == 'post':
            tail = tail.replace('        } while (index != *(s8 *)(owner + 0x2D));', '        } while (index-- != *(s8 *)(owner + 0x2D));')
        else:
            tail = tail.replace('        } while (index != *(s8 *)(owner + 0x2D));',
                '        } while (index != *(s8 *)(owner + 0x2D) && (index--, 1));')
    elif mode == 'length-local':
        tail = '        f32 pointLength;\n' + tail
        tail = tail.replace('            distance += record[4];', '            pointLength = record[4];\n            distance += pointLength;')
    elif mode == 'alpha-local':
        tail = '        u32 alpha;\n' + tail
        tail = tail.replace('            if (start < distance)', '            alpha = 60;\n            if (start < distance)').replace(
            '((u8 *)record)[0x14] = (u32)', 'alpha = (u32)').replace('            } else {\n                ((u8 *)record)[0x14] = 60;\n            }',
            '            }\n            ((u8 *)record)[0x14] = alpha;')
    elif mode == 'split-length':
        tail = tail.replace('((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);',
            '((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);\n                length = record[4];').replace(
            '((u8 *)record)[0x14] = 60;', '((u8 *)record)[0x14] = 60;\n                length = record[4];').replace(
            'distance += record[4];', 'distance += length;')
    elif mode == 'split-distance':
        tail = tail.replace('            distance += record[4];\n', '').replace(
            '((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);',
            '((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);\n                distance += record[4];').replace(
            '((u8 *)record)[0x14] = 60;', '((u8 *)record)[0x14] = 60;\n                distance += record[4];')
    elif mode == 'ceiling':
        tail = '        f32 ceiling;\n' + tail
        tail = tail.replace('        start = total', '        ceiling = 60.0f;\n        start = total').replace(
            '* inverse * 60.0f', '* inverse * ceiling').replace('((u8 *)record)[0x14] = 60;', '((u8 *)record)[0x14] = ceiling;')
    else:
        raise ValueError(mode)
    return before + gate + tail


def fitted_base():
    body = staged_trim(phase_locals(byte_stride(BASE), record=True), 3).replace('length != 0.0f', 'length')
    body = body.replace('    f32 xTrim, yTrim, zTrim;', '    f32 xTrim;\n    f32 yTrim;\n    f32 zTrim;')
    body = body.replace('    f32 vector[3];\n', '').replace('    f32 yTrim;', '    f32 vector[3];\n    f32 yTrim;')
    return fade_loop(body, 'split-distance')


SELECTED = fitted_base()


def owner_guards():
    pairs = (
        (0x10C, 0x820C002D, 0x02201025), (0x110, 0xC6220010, 0xC62C0010),
        (0x11C, 0x46061032, 0x460C3032), (0x12C, 0x4602C283, 0x460CC083),
        (0x134, 0xC6260000, 0xC62A0000), (0x13C, 0x460A4002, 0x46024002),
        (0x144, 0x46002302, 0x46002182), (0x14C, 0x460C3201, 0x46065201),
        (0x158, 0x46005382, 0x46005182), (0x160, 0x460E2181, 0x46062201),
        (0x164, 0xE6260004, 0xE6280004), (0x168, 0xC7A800A0, 0xC7A400A0),
        (0x16C, 0x4600C181, 0x46002182), (0x170, 0x46004402, 0x4600C101),
        (0x174, 0x46105101, 0x46065201), (0x178, 0x46023202, 0x46046282),
        (0x17C, 0xE6240008, 0xE6280008), (0x180, 0xE6280010, 0xE62A0010),
        (0x1A0, 0x54490004, 0x55220004), (0x1C0, 0x820C002D, 0x02201025),
        (0x1C4, 0x02201025, 0x820C002D), (0x1D4, 0xE7B600A8, 0xE7B600AC),
        (0x1EC, 0xC7B600A8, 0xC7B600AC), (0x1F4, 0x44815000, 0x44813000),
        (0x1FC, 0xC424E9A4, 0xC428E9A4), (0x200, 0xC6A80018, 0xC6AA0018),
        (0x208, 0x46045182, 0x46083102), (0x210, 0x46064280, 0x46045180),
        (0x214, 0xE6AA0018, 0xE6A60018), (0x24C, 0xC426B2E0, 0xC424B2E0),
        (0x250, 0xC6A80018, 0xC6AA0018), (0x268, 0xC6440010, 0xC6480010),
        (0x26C, 0x4604A500, 0x4608A500), (0x270, 0x4606A282, 0x4604A182),
        (0x278, 0x460A4300, 0x46065300), (0x29C, 0xC424B2E8, 0xC428B2E8),
        (0x2A4, 0x44801000, 0x44806000), (0x2A8, 0x4604B402, 0x4608B402),
        (0x2B0, 0x8203002E, 0x8202002E), (0x2C0, 0x2463FFFF, 0x2442FFFF),
        (0x2C4, 0x04630004, 0x04430004), (0x2C8, 0x4602803C, 0x460C803C),
        (0x2CC, 0x92030025, 0x92020025), (0x2D0, 0x2463FFFF, 0x2442FFFF),
        (0x2D4, 0x4602803C, 0x460C803C), (0x2D8, 0x000378C0, 0x000278C0),
        (0x2DC, 0x01E37823, 0x01E27823), (0x2E8, 0x01F31021, 0x01F31821),
        (0x2EC, 0x46101301, 0x46106081), (0x2F4, 0x460C703C, 0x4602703C),
        (0x300, 0x460C7181, 0x46027101), (0x304, 0x46007306, 0x46007086),
        (0x308, 0x460C7181, 0x46027101), (0x310, 0x46123202, 0x46122282),
        (0x318, 0x46144282, 0x46145182), (0x328, 0x46005124, 0x46003224),
        (0x340, 0x44812000, 0x44814000), (0x348, 0x46045101, 0x46083201),
        (0x354, 0x46002124, 0x46004224), (0x36C, 0x44192000, 0x44194000),
        (0x384, 0x44192000, 0x44194000), (0x398, 0xC4460010, 0xA0790014),
        (0x39C, 0xA0590014, 0x00000000), (0x3A0, 0x10000004, 0x10000003),
        (0x3A4, 0x46061080, 0xC4640010), (0x3A8, 0xC4480010, 0xA0640014),
        (0x3AC, 0xA0440014, 0xC4640010), (0x3B0, 0x46081080, 0x46046300),
        (0x3B8, 0x5468FFC2, 0x5448FFC2), (0x3BC, 0x2463FFFF, 0x2442FFFF),
    )
    symbols = {0x1FC: 'D_800BE9A4', 0x24C: 'D_800AB2E0', 0x29C: 'D_800AB2E8'}
    rows = []
    for offset, before, after in pairs:
        relocation = 'R_MIPS_LO16:' + symbols[offset] if offset in symbols else '-'
        if offset in symbols:
            before &= 0xFFFF0000
            after &= 0xFFFF0000
        if offset in (0x10C, 0x1A0, 0x1C0, 0x1C4):
            note = 'Normalize closed previous point goal read schedule and branch operand order'
        elif offset in (0x1D4, 0x1EC):
            note = 'Normalize paired private total spill slot from SP+A8 to SP+AC'
        elif offset < 0x1EC:
            note = 'Normalize closed trim FP allocation and independent retained length schedule'
        elif offset < 0x29C:
            note = 'Normalize closed phase FP allocation preserving live loads and callee ABI'
        else:
            note = 'Normalize closed fade GP FP allocation and output length branch delay schedule'
        rows.append(dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % before, replacement='0x%08X' % after,
            expected_relocations=relocation, replacement_relocations=relocation, note=note,
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[0] == 0x27BDFF48
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        before, after = int(row['expected'], 0), int(row['replacement'], 0)
        if row['expected_relocations'] != '-':
            addend = SYMBOLS[row['expected_relocations'].split(':')[1]] & 0xFFFF
            before |= addend
            after |= addend
        assert result[index] == before, ('stale shaping schedule', index)
        result[index] = after
    return result


def candidates():
    yield 'selected', SELECTED
    yield 'natural', BASE
    yield 'negative-reassociated-divide', BASE.replace('(total - 80.0f) * (1.0f / record[4])', '(total - 80.0f) / record[4]')
    byte = byte_stride(BASE)
    yield 'byte-stride', byte
    for name, body in (('natural', BASE), ('byte', byte)):
        yield name + '-integer-zeros', body.replace('0.0f', '0')
        vector = body.replace('f32 vector[3];', 'ShapingVector151D7CD0 vector;').replace(
            'func_15143E64(vector)', 'func_15143E64((f32 *)&vector)')
        for index, axis in enumerate('xyz'):
            vector = vector.replace('vector[%d]' % index, 'vector.' + axis)
        yield name + '-struct-vector', vector
        yield name + '-struct-integer-zeros', vector.replace('0.0f', '0')
        phased = body.replace('    f32 distance;\n', '').replace('    s32 index;\n', '')
        phased = phased.replace('        total = 0.0f;', '        s32 index;\n\n        total = 0.0f;')
        phased = phased.replace('        payload[6] +=', '        s32 index;\n        f32 distance;\n\n        payload[6] +=')
        phased = phased.replace('        start = total', '        s32 index;\n        f32 distance;\n\n        start = total')
        yield name + '-phase-locals', phased
        yield name + '-phase-integer-zeros', phased.replace('0.0f', '0')
    for field in ('vector', 'total', 'index', 'record'):
        line = {'vector': '    f32 vector[3];', 'total': '    f32 total;', 'index': '    s32 index;', 'record': '    f32 *record;'}[field]
        yield 'first-' + field, BASE.replace(line + '\n', '').replace('    f32 *payload;', line + '\n    f32 *payload;')
    yield 'reverse-count-compare', BASE.replace('*(s8 *)(owner + 0x2D) == owner[0x25]', 'owner[0x25] == *(s8 *)(owner + 0x2D)')
    yield from fitting_candidates()
    yield 'negative-unsigned-state', BASE.replace('*(s8 *)(owner + 0x2C)', 'owner[0x2C]')
    yield 'negative-unsigned-current', BASE.replace('*(s8 *)(owner + 0x2E)', 'owner[0x2E]')
    yield 'negative-unsigned-goal', BASE.replace('*(s8 *)(owner + 0x2D)', 'owner[0x2D]')
    yield 'negative-signed-count', BASE.replace('owner[0x25]', '*(s8 *)(owner + 0x25)')
    yield 'negative-live-buffer', BASE.replace('record = records + index * 7;', 'record = *(f32 **)(owner + 0x94) + index * 7;')
    yield 'negative-limit', BASE.replace('80.0f', '81.0f')
    yield 'negative-phase-sign', BASE.replace('-41.0f', '41.0f')
    yield 'negative-no-state-reload', BASE.replace('    f32 *payload;', '    s32 state;\n    f32 *payload;').replace(
        '    payload =', '    state = *(s8 *)(owner + 0x2C);\n    payload =', 1).replace('if (*(s8 *)(owner + 0x2C) >= 2)', 'if (state >= 2)')
    yield 'negative-signed-fade', BASE.replace('(u32)((width - fraction)', '(s32)((width - fraction)')
    yield 'negative-return', BASE.replace('    return 1;', '    return 0;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'record-ring-shaping.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()], '-o', str(elf), str(obj)],
        check=True, capture_output=True)
    _, functions, relocations = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(struct.unpack_from('>%dI' % (meta['size'] // 4), pools['.text'][1], meta['value']))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:])
    words = words[:end]
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    frames = [(-word) & 65535 for word in words if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000]
    return dict(name=name, profile=profile, body_words=end, frame=frames[0] if frames else 0,
        vector_offsets=[word & 65535 for word in words if word & 0xFFFF0000 == 0x27A40000],
        total_spills=[word & 65535 for word in words if word & 0xFFFF0000 == 0xE7B60000],
        saved_FP=[word >> 16 & 31 for word in words if word >> 26 == 61 and word >> 21 & 31 == 29],
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocations,
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--profiles', action='store_true')
    mode.add_argument('--candidate', choices=[name for name, _ in candidates()])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-ring-shaping'
    forms = [('profile-' + p, SELECTED, p) for p in PROFILES] if args.profiles else [
        (name, body, 'o2g3') for name, body in candidates() if args.candidate is None or name == args.candidate]
    records = []
    for name, body, profile in forms:
        record, _ = compile_candidate(root, out, name, body, profile)
        records.append(record)
        print(name, record['body_words'], hex(record['frame']), record['differences'], flush=True)
    filename = 'profiles.json' if args.profiles else args.candidate + '-measurement.json' if args.candidate else 'measurements.json'
    (out / filename).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
