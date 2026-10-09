"""Recover the complete backward ring ribbon renderer and phase-wrap joins."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D80C4, 0x205574, 405
FUNCTION = 'func_151D80C4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D80C4.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } RibbonPosition151D80C4;
typedef struct {
    RibbonPosition151D80C4 position;
    f32 velocity, length;
    u8 alpha, padding[3];
    f32 phase;
} RibbonRecord151D80C4;
extern u8 D_80090CD4[];
extern u32 D_800D2C9C, D_800A4AC8[];
extern f32 D_800DD1E8[], D_800DD1D8[];
void func_151D5D60(void *slots, s16 view, s32 size, Vtx **cursor, u8 *fresh);
Gfx *func_15142E24(Gfx *, void *, s32, s32, s32, s32, s32, u8, u8 *, u8 *, s32);
Gfx *func_15142B7C(Gfx *, u32, u32);
Gfx *func_1513F4E4(Gfx *, u8, u8 *);
Gfx *func_15142FBC(Gfx *, u32, u32, u8 *);
'''
SYMBOLS = dict(D_80090CD4=0x80090CD4, D_800D2C9C=0x800D2C9C,
    D_800A4AC8=0x800A4AC8, D_800DD1E8=0x800DD1E8, D_800DD1D8=0x800DD1D8,
    func_151D5D60=0x151D5D60, func_15142E24=0x15142E24,
    func_15142B7C=0x15142B7C, func_1513F4E4=0x1513F4E4,
    func_15142FBC=0x15142FBC, memcpy=0x10022EC0)
SELECTED = '''Gfx *func_151D80C4(u8 *owner, Gfx *output, s16 view) {
    RibbonPosition151D80C4 currentPosition;
    RibbonPosition151D80C4 previousPosition;
    RibbonRecord151D80C4 *records;
    RibbonRecord151D80C4 *payload;
    RibbonRecord151D80C4 *point;
    Vtx *cursor;
    u8 sync;
    f32 previousPhase;
    f32 currentPhase;
    f32 xOffset;
    f32 zOffset;
    s32 index;
    s32 previousIndex;
    s32 previousAlpha;
    s32 currentAlpha;
    s32 factor;
    s32 phase;
    s32 alpha;

    if (*(s8 *)(owner + 0x2C) < 2) {
        return output;
    }
    records = *(RibbonRecord151D80C4 **)(owner + 0x94);
    payload = *(RibbonRecord151D80C4 **)(owner + 0x98);
    func_151D5D60(owner + 0x84, view, owner[0x25] * 32 + 160, &cursor, NULL);
    if (cursor == NULL) {
        return output;
    }
    sync = 1;
    output = func_15142E24(output, D_80090CD4, 0, 0, 0, 0, 31, 0, NULL, &sync, 62);
    output = func_15142B7C(output, 0x200005, 0x1F0600);
    output = func_1513F4E4(output, 0x4C, &sync);
    output = func_15142FBC(output, D_800D2C9C | 0x80000 | 0x2CA0,
        D_800A4AC8[3] | D_800A4AC8[2], &sync);
    if (*(u16 *)(owner + 0x1E) & 2) {
        index = *(s8 *)(owner + 0x2E) - 1;
        if (index < 0) {
            index = owner[0x25] - 1;
        }
        previousPosition = *(RibbonPosition151D80C4 *)(owner + 0x10);
        previousAlpha = 0;
        previousPhase = payload->phase;
    } else {
        previousIndex = *(s8 *)(owner + 0x2E) - 1;
        if (previousIndex < 0) {
            previousIndex = owner[0x25] - 1;
        }
        index = previousIndex - 1;
        if (index < 0) {
            index = owner[0x25] - 1;
        }
        previousPosition = records[previousIndex].position;
        previousAlpha = records[previousIndex].alpha;
        previousPhase = records[previousIndex].phase;
    }
    point = records + index;
    currentPosition = point->position;
    xOffset = D_800DD1E8[view] * 5.5f;
    zOffset = D_800DD1D8[view] * 5.5f;
    currentAlpha = point->alpha;
    currentPhase = point->phase;
    if (*(u16 *)(owner + 0x1E) & 8) {
        factor = (*(s16 *)(owner + 0x1C) * 12) & 255;
    } else {
        factor = 255;
    }
    alpha = (previousAlpha * factor) >> 8;
    phase = (s32)previousPhase;
    cursor->v.ob[0] = (s32)(previousPosition.x + xOffset);
    cursor->v.ob[1] = (s32)previousPosition.y;
    cursor->v.ob[2] = (s32)(previousPosition.z - zOffset);
    cursor->v.tc[0] = phase;
    cursor->v.tc[1] = 0x800;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = alpha;
    cursor->v.flag = 0;
    cursor++;
    cursor->v.ob[0] = (s32)(previousPosition.x - xOffset);
    cursor->v.ob[1] = (s32)previousPosition.y;
    cursor->v.ob[2] = (s32)(previousPosition.z + zOffset);
    cursor->v.tc[0] = phase;
    cursor->v.tc[1] = 0;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = alpha;
    cursor->v.flag = 0;
    cursor++;
    do {
        alpha = (currentAlpha * factor) >> 8;
        phase = (s32)currentPhase;
        cursor->v.ob[0] = (s32)(currentPosition.x + xOffset);
        cursor->v.ob[1] = (s32)currentPosition.y;
        cursor->v.ob[2] = (s32)(currentPosition.z - zOffset);
        cursor->v.tc[0] = phase;
        cursor->v.tc[1] = 0x800;
        cursor->v.cn[0] = 255;
        cursor->v.cn[1] = 255;
        cursor->v.cn[2] = 255;
        cursor->v.cn[3] = alpha;
        cursor->v.flag = 0;
        cursor++;
        cursor->v.ob[0] = (s32)(currentPosition.x - xOffset);
        cursor->v.ob[1] = (s32)currentPosition.y;
        cursor->v.ob[2] = (s32)(currentPosition.z + zOffset);
        cursor->v.tc[0] = phase;
        cursor->v.tc[1] = 0;
        cursor->v.cn[0] = 255;
        cursor->v.cn[1] = 255;
        cursor->v.cn[2] = 255;
        cursor->v.cn[3] = alpha;
        cursor->v.flag = 0;
        cursor++;
        gSPVertex(output++, cursor - 4, 4, 0);
        gSP1Triangle(output++, 0, 1, 2, 0);
        gSP1Triangle(output++, 1, 3, 2, 0);
        if (currentPhase < previousPhase) {
            memcpy(cursor, cursor - 2, 32);
            cursor[-2].v.tc[0] -= 0x8000;
            cursor++;
            cursor[-2].v.tc[0] -= 0x8000;
            cursor++;
        }
        previousIndex = index;
        index--;
        point--;
        if (index < 0) {
            index = owner[0x25] - 1;
            point = records + index;
        }
        currentPosition = point->position;
        currentAlpha = point->alpha;
        previousPhase = records[previousIndex].phase;
        currentPhase = point->phase;
    } while (previousIndex != *(s8 *)(owner + 0x2D));
    return output;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'array-records', SELECTED.replace('RibbonRecord151D80C4 *records;', 'u8 *records;').replace(
        'records = *(RibbonRecord151D80C4 **)', 'records = *(u8 **)').replace(
        'records[previousIndex].', '((RibbonRecord151D80C4 *)(records + previousIndex * 28))->').replace(
        'point = records + index;', 'point = (RibbonRecord151D80C4 *)(records + index * 28);')
    yield 'reversed-positions', SELECTED.replace('    RibbonPosition151D80C4 currentPosition;\n    RibbonPosition151D80C4 previousPosition;',
        '    RibbonPosition151D80C4 previousPosition;\n    RibbonPosition151D80C4 currentPosition;')
    yield 'unsigned-products', SELECTED.replace('(previousAlpha * factor)', '((u32)previousAlpha * factor)').replace(
        '(currentAlpha * factor)', '((u32)currentAlpha * factor)')
    yield 'outer-success', SELECTED.replace('    if (cursor == NULL) {\n        return output;\n    }',
        '    if (cursor != NULL) {').replace('    return output;\n}', '    }\n    return output;\n}')
    byte = SELECTED.replace('RibbonRecord151D80C4 *records;', 'u8 *records;').replace(
        'RibbonRecord151D80C4 *point;', 'u8 *point;').replace(
        'records = *(RibbonRecord151D80C4 **)', 'records = *(u8 **)').replace(
        'records[previousIndex].position', '*(RibbonPosition151D80C4 *)(records + previousIndex * 28)').replace(
        'records[previousIndex].alpha', 'records[previousIndex * 28 + 0x14]').replace(
        'records[previousIndex].phase', '*(f32 *)(records + previousIndex * 28 + 0x18)').replace(
        'point = records + index;', 'point = records + index * 28;').replace(
        'point->position', '*(RibbonPosition151D80C4 *)point').replace('point->alpha', 'point[0x14]').replace(
        'point->phase', '*(f32 *)(point + 0x18)').replace('        point--;', '        point -= 28;')
    yield 'byte-stride', byte
    reused = byte.replace('    s32 alpha;\n', '').replace('    alpha = (previousAlpha',
        '    previousAlpha = (previousAlpha').replace('        alpha = (currentAlpha',
        '        currentAlpha = (currentAlpha')
    seed, loop = reused.split('    do {', 1)
    reused = seed.replace(' = alpha;', ' = previousAlpha;') + '    do {' + loop.replace(' = alpha;', ' = currentAlpha;')
    yield 'byte-reused-alpha', reused
    reused = reused.replace('    s32 phase;\n', '').replace('    phase = (s32)previousPhase;',
        '    previousIndex = (s32)previousPhase;').replace('        phase = (s32)currentPhase;',
        '        previousIndex = (s32)currentPhase;').replace(' = phase;', ' = previousIndex;')
    yield 'byte-reused-phase', reused
    factored = reused.replace('previousIndex * 28', '(previousIndex * 8 - previousIndex) * 4').replace(
        'index * 28', '(index * 8 - index) * 4')
    yield 'factored-stride', factored
    yield 'factored-byte-alpha', factored.replace('s32 previousAlpha;', 'u8 previousAlpha;').replace(
        's32 currentAlpha;', 'u8 currentAlpha;')
    yield 'byte-factor-else', reused.replace('    if (*(u16 *)(owner + 0x1E) & 8) {',
        '    if (!(*(u16 *)(owner + 0x1E) & 8)) {\n        factor = 255;\n    } else {').replace(
        '    } else {\n        factor = 255;\n    }', '    }')
    floating = reused.replace('u8 *records;', 'f32 *records;').replace('u8 *point;', 'f32 *point;').replace(
        'records = *(u8 **)', 'records = *(f32 **)').replace('previousIndex * 28', 'previousIndex * 7').replace(
        'records[previousIndex * 7 + 0x14]', '((u8 *)(records + previousIndex * 7))[0x14]').replace(
        '*(f32 *)(records + previousIndex * 7 + 0x18)', 'records[previousIndex * 7 + 6]').replace(
        'records + index * 28', 'records + index * 7').replace('point[0x14]', '((u8 *)point)[0x14]').replace(
        '*(f32 *)(point + 0x18)', 'point[6]').replace('point -= 28;', 'point -= 7;')
    yield 'float-stride', floating
    for name, body in (('float-stride', floating), ('byte-reused-phase', reused)):
        yield name + '-phase-at-store', body.replace('    previousIndex = (s32)previousPhase;\n', '').replace(
            '        previousIndex = (s32)currentPhase;\n', '').replace(
            'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)previousPhase;', 2).replace(
            'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)currentPhase;')


def fitting_candidates():
    base = dict(candidates())['factored-byte-alpha']
    yield 'factored-byte-alpha', base
    for name, old, new in (
        ('previous-int-alpha', 'u8 previousAlpha;', 's32 previousAlpha;'),
        ('current-int-alpha', 'u8 currentAlpha;', 's32 currentAlpha;'),
        ('unsigned-factor', 's32 factor;', 'u32 factor;'),
        ('byte-factor', 's32 factor;', 'u8 factor;'),
        ('half-factor', 's32 factor;', 'u16 factor;'),
        ('cursor-first', '    Vtx *cursor;\n', ''),
        ('sync-first', '    u8 sync;\n', ''),
        ('register-output', 'Gfx *output,', 'register Gfx *output,'),
        ('register-index', 's32 index;', 'register s32 index;'),
    ):
        body = base.replace(old, new)
        if name == 'cursor-first':
            body = body.replace('    RibbonPosition151D80C4 currentPosition;',
                '    Vtx *cursor;\n    RibbonPosition151D80C4 currentPosition;')
        if name == 'sync-first':
            body = body.replace('    RibbonPosition151D80C4 currentPosition;',
                '    u8 sync;\n    RibbonPosition151D80C4 currentPosition;')
        yield name, body
    yield 'reverse-factor', base.replace('    if (*(u16 *)(owner + 0x1E) & 8) {',
        '    if (!(*(u16 *)(owner + 0x1E) & 8)) {\n        factor = 255;\n    } else {').replace(
        '    } else {\n        factor = 255;\n    }', '    }')
    yield 'conditional-factor', base.replace('''    if (*(u16 *)(owner + 0x1E) & 8) {
        factor = (*(s16 *)(owner + 0x1C) * 12) & 255;
    } else {
        factor = 255;
    }''', '''    factor = (*(u16 *)(owner + 0x1E) & 8) ?
        (*(s16 *)(owner + 0x1C) * 12) & 255 : 255;''')
    yield 'seed-factor', base.replace('    s32 factor;', '    s32 factor;\n    s32 seedFactor;').replace(
        '        factor =', '        seedFactor =').replace(
        '    previousAlpha = (previousAlpha * factor)', '    factor = seedFactor;\n    previousAlpha = (previousAlpha * seedFactor)')
    yield 'phase-at-store', base.replace('    previousIndex = (s32)previousPhase;\n', '').replace(
        '        previousIndex = (s32)currentPhase;\n', '').replace(
        'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)previousPhase;', 2).replace(
        'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)currentPhase;')
    yield 'separate-phase', base.replace('    s32 previousIndex;', '    s32 previousIndex;\n    s32 phase;').replace(
        'previousIndex = (s32)', 'phase = (s32)').replace('cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = phase;')
    fitted = base.replace('s32 factor;', 'u8 factor;')
    for name, body in fitting_candidates_base(base):
        yield 'byte-factor-' + name, body.replace('s32 factor;', 'u8 factor;')
    yield 'byte-factor-stride-seven', fitted.replace('(previousIndex * 8 - previousIndex) * 4',
        'previousIndex * 7 * 4').replace('(index * 8 - index) * 4', 'index * 7 * 4')
    yield 'byte-factor-stride-four', fitted.replace('(previousIndex * 8 - previousIndex) * 4',
        '(previousIndex * 32 - previousIndex * 4)').replace('(index * 8 - index) * 4',
        '(index * 32 - index * 4)')
    yield 'byte-factor-separate-phases', fitted.replace('    s32 previousIndex;',
        '    s32 previousIndex;\n    s32 previousS;\n    s32 currentS;').replace(
        '    previousIndex = (s32)previousPhase;', '    previousS = (s32)previousPhase;').replace(
        '        previousIndex = (s32)currentPhase;', '        currentS = (s32)currentPhase;').replace(
        'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = previousS;', 2).replace(
        'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = currentS;')
    locals_begin = fitted.index('    RibbonPosition151D80C4 currentPosition;')
    locals_end = fitted.index('\n\n    if (*(s8 *)')
    locals_text = fitted[locals_begin:locals_end]
    declarations = locals_text.splitlines(keepends=True)
    for name, first in (
        ('cursor-first', ('Vtx *cursor;',)),
        ('cursor-last', tuple(line.strip() for line in declarations if 'Vtx *cursor;' not in line)),
        ('positions-last', tuple(line.strip() for line in declarations if 'RibbonPosition151D80C4' not in line)),
        ('positions-reverse', ('RibbonPosition151D80C4 previousPosition;', 'RibbonPosition151D80C4 currentPosition;')),
        ('index-first', ('s32 index;', 's32 previousIndex;')),
        ('alpha-first', ('u8 previousAlpha;', 'u8 currentAlpha;', 'u8 factor;')),
        ('retail-local-order', ('s32 index;', 'RibbonPosition151D80C4 currentPosition;',
            'RibbonPosition151D80C4 previousPosition;', 'RibbonRecord151D80C4 *payload;',
            'u8 *point;', 'u8 *records;', 'u8 sync;', 'f32 previousPhase;', 'f32 currentPhase;',
            'f32 xOffset;', 'f32 zOffset;', 's32 previousIndex;', 'Vtx *cursor;')),
    ):
        reordered = [next(line for line in declarations if line.strip() == item) for item in first]
        reordered += [line for line in declarations if line.strip() not in first]
        yield 'byte-factor-' + name, fitted[:locals_begin] + ''.join(reordered).rstrip('\n') + fitted[locals_end:]
        if name == 'retail-local-order':
            ordered = fitted[:locals_begin] + ''.join(reordered).rstrip('\n') + fitted[locals_end:]
            for variant, body in fitting_candidates_base(ordered):
                yield 'retail-local-order-' + variant, body
            yield 'retail-local-order-request-lifetime', ordered.replace(
                '    records = *(u8 **)(owner + 0x94);',
                '    previousIndex = owner[0x25] * 32 + 160;\n    records = *(u8 **)(owner + 0x94);').replace(
                'owner[0x25] * 32 + 160, &cursor', 'previousIndex, &cursor')
            yield 'retail-local-order-scaled-factor', ordered.replace(
                '        factor = (*(s16 *)(owner + 0x1C) * 12) & 255;',
                '        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;')
            wide = ordered.replace('u8 previousAlpha;', 's32 previousAlpha;')
            yield 'retail-local-order-wide-scaled-factor', wide.replace(
                '        factor = (*(s16 *)(owner + 0x1C) * 12) & 255;',
                '        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;')
            yield 'retail-local-order-wide-reverse-factor', dict(fitting_candidates_base(wide))['reverse-factor']


def fitting_candidates_base(base):
    for name, old, new in (
        ('previous-int-alpha', 'u8 previousAlpha;', 's32 previousAlpha;'),
        ('current-int-alpha', 'u8 currentAlpha;', 's32 currentAlpha;'),
    ):
        yield name, base.replace(old, new)
    yield 'reverse-factor', base.replace('    if (*(u16 *)(owner + 0x1E) & 8) {',
        '    if (!(*(u16 *)(owner + 0x1E) & 8)) {\n        factor = 255;\n    } else {').replace(
        '    } else {\n        factor = 255;\n    }', '    }')
    yield 'separate-phase', base.replace('    s32 previousIndex;', '    s32 previousIndex;\n    s32 phase;').replace(
        'previousIndex = (s32)', 'phase = (s32)').replace('cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = phase;')


FITTED_NAME = 'retail-local-order-wide-scaled-factor'
FITTED = dict(fitting_candidates())[FITTED_NAME]


def scheduling_candidates():
    yield 'fitted-baseline', FITTED
    for name, body in (
        ('seed-product-order', FITTED.replace('(previousAlpha * factor)', '(factor * previousAlpha)')),
        ('both-product-order', FITTED.replace('(previousAlpha * factor)', '(factor * previousAlpha)').replace(
            '(currentAlpha * factor)', '(factor * currentAlpha)')),
        ('explicit-byte-factor', FITTED.replace('factor = (*(s16 *)(owner + 0x1C) * 3) * 4;',
            'factor = (u8)((*(s16 *)(owner + 0x1C) * 3) * 4);')),
        ('masked-byte-factor', FITTED.replace('factor = (*(s16 *)(owner + 0x1C) * 3) * 4;',
            'factor = ((*(s16 *)(owner + 0x1C) * 3) * 4) & 255;')),
        ('masked-half-factor', FITTED.replace('u8 factor;', 'u16 factor;').replace(
            'factor = (*(s16 *)(owner + 0x1C) * 3) * 4;', 'factor = ((*(s16 *)(owner + 0x1C) * 3) * 4) & 255;')),
    ):
        yield name, body
    vertex = 'gSPVertex(output++, cursor - 4, 4, 0);'
    triangles = ('gSP1Triangle(output++, 0, 1, 2, 0);', 'gSP1Triangle(output++, 1, 3, 2, 0);')
    for name, commands in (('vertex-cursor-lifetime', (vertex,)),
            ('triangle-cursor-lifetime', triangles), ('all-command-cursor-lifetimes', (vertex, *triangles))):
        body = FITTED
        for command in commands:
            body = body.replace(command, command.replace('output++', 'output') + '\n        output++;')
        yield name, body
    for type_ in ('u32', 'f32'):
        words = FITTED.replace('u8 *records;', type_ + ' *records;').replace('u8 *point;', type_ + ' *point;').replace(
            'records = *(u8 **)', 'records = *(' + type_ + ' **)').replace(
            'records[(previousIndex * 8 - previousIndex) * 4 + 0x14]',
            '((u8 *)(records + (previousIndex * 8 - previousIndex)))[0x14]').replace(
            '(previousIndex * 8 - previousIndex) * 4 + 0x18', '(previousIndex * 8 - previousIndex) + 6').replace(
            '(previousIndex * 8 - previousIndex) * 4', '(previousIndex * 8 - previousIndex)').replace(
            '(index * 8 - index) * 4', '(index * 8 - index)').replace('point[0x14]', '((u8 *)point)[0x14]').replace(
            '*(f32 *)(point + 0x18)', '*(f32 *)(point + 6)').replace('point -= 28;', 'point -= 7;')
        yield type_ + '-word-records', words
        yield type_ + '-seven-word-records', words.replace('(previousIndex * 8 - previousIndex)',
            '(previousIndex * 7)').replace('(index * 8 - index)', '(index * 7)')
    seed, loop = FITTED.split('    do {', 1)
    yield 'view-seed-phase-lifetime', seed.replace('previousIndex = (s32)previousPhase;',
        'view = (s32)previousPhase;').replace('cursor->v.tc[0] = previousIndex;',
        'cursor->v.tc[0] = view;') + '    do {' + loop
    yield 'view-both-phase-lifetimes', FITTED.replace('previousIndex = (s32)previousPhase;',
        'view = (s32)previousPhase;').replace('previousIndex = (s32)currentPhase;',
        'view = (s32)currentPhase;').replace('cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = view;')
    for name, declaration in (
        ('seed-alpha-first', '    s32 previousAlpha;\n'),
        ('factor-before-seed-alpha', '    u8 factor;\n'),
    ):
        body = FITTED.replace(declaration, '').replace('    s32 index;\n', '    s32 index;\n' + declaration)
        yield name, body
    yield 'stride-seven-compound', FITTED.replace(
        '        previousPosition = *(RibbonPosition151D80C4 *)(records + (previousIndex * 8 - previousIndex) * 4);',
        '        previousIndex *= 7;\n        previousIndex *= 4;\n' +
        '        previousPosition = *(RibbonPosition151D80C4 *)(records + previousIndex);').replace(
        'previousAlpha = records[(previousIndex * 8 - previousIndex) * 4 + 0x14];',
        'previousAlpha = records[previousIndex + 0x14];').replace(
        'previousPhase = *(f32 *)(records + (previousIndex * 8 - previousIndex) * 4 + 0x18);',
        'previousPhase = *(f32 *)(records + previousIndex + 0x18);', 1)
    for type_ in ('u8', 's32'):
        yield type_ + '-request-count-lifetime', FITTED.replace('    u8 factor;',
            '    u8 factor;\n    ' + type_ + ' count;').replace('    records = *(u8 **)(owner + 0x94);',
            '    count = owner[0x25];\n    records = *(u8 **)(owner + 0x94);').replace(
            'owner[0x25] * 32 + 160, &cursor', 'count * 32 + 160, &cursor')
    yield 'initial-ring-offset-lifetime', FITTED.replace('    point = records + (index * 8 - index) * 4;',
        '    previousIndex = index * 7;\n    point = records + previousIndex * 4;', 1)
    yield 'tail-Gfx-lifetime', FITTED.replace('    u8 factor;', '    u8 factor;\n    Gfx *tail;').replace(
        '    output = func_15142FBC(', '    tail = func_15142FBC(', 1).replace(
        'gSPVertex(output++', 'gSPVertex(tail++').replace('gSP1Triangle(output++', 'gSP1Triangle(tail++').replace(
        '    return output;\n}', '    return tail;\n}')
    yield 'integer-record-addresses', FITTED.replace('records + (index * 8 - index) * 4',
        '(u8 *)((u32)records + (u32)((index * 8 - index) * 4))').replace(
        'records + (previousIndex * 8 - previousIndex) * 4',
        '(u8 *)((u32)records + (u32)((previousIndex * 8 - previousIndex) * 4))')
    factor_start = '    if (*(u16 *)(owner + 0x1E) & 8) {'
    first_x = '    cursor->v.ob[0] = (s32)(previousPosition.x + xOffset);'
    yield 'view-seed-X-lifetime', FITTED.replace(factor_start,
        '    view = (s32)(previousPosition.x + xOffset);\n' + factor_start).replace(first_x, '    cursor->v.ob[0] = view;')
    yield 'separate-seed-X-lifetime', FITTED.replace('    u8 factor;', '    u8 factor;\n    s32 firstX;').replace(
        factor_start, '    firstX = (s32)(previousPosition.x + xOffset);\n' + factor_start).replace(
        first_x, '    cursor->v.ob[0] = firstX;')
    yield 'byte-alpha-separate-seed-X', FITTED.replace('s32 previousAlpha;', 'u8 previousAlpha;').replace(
        '    u8 factor;', '    u8 factor;\n    s32 firstX;').replace(factor_start,
        '    firstX = (s32)(previousPosition.x + xOffset);\n' + factor_start).replace(
        first_x, '    cursor->v.ob[0] = firstX;')


def setup_candidates():
    block = '''    if (*(u16 *)(owner + 0x1E) & 8) {
        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;
    } else {
        factor = 255;
    }'''
    reverse = '''    if (!(*(u16 *)(owner + 0x1E) & 8)) {
        factor = 255;
    } else {
        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;
    }'''
    mode = FITTED.replace('D_800A4AC8[3] | D_800A4AC8[2]', 'D_800A4AC8[2] | D_800A4AC8[3]')
    yield 'fitted-baseline', FITTED
    yield 'mode-operands', mode
    yield 'reverse-factor', FITTED.replace(block, reverse)
    yield 'retail-mode-order-reverse-factor', mode.replace(block, reverse)
    yield 'conditional-factor', mode.replace(block, '''    factor = (*(u16 *)(owner + 0x1E) & 8) ?
        (*(s16 *)(owner + 0x1C) * 3) * 4 : 255;''')
    yield 'default-before-factor', mode.replace(block, '''    factor = 255;
    if (*(u16 *)(owner + 0x1E) & 8) {
        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;
    }''')
    for type_ in ('s32', 'u32'):
        yield type_ + '-common-narrow', mode.replace('u8 factor;', type_ + ' factor;').replace(
            block, block + '\n    factor = (u8)factor;')
    yield 'signed-byte-factor', mode.replace('u8 factor;', 's8 factor;').replace(
        '(previousAlpha * factor)', '(previousAlpha * (u8)factor)').replace(
        '(currentAlpha * factor)', '(currentAlpha * (u8)factor)')
    for name, expression in (
        ('scaled-stages', 'factor = *(s16 *)(owner + 0x1C) * 3;\n        factor *= 4;'),
        ('narrow-opacity', 'factor = *(s16 *)(owner + 0x1C);\n        factor *= 12;'),
        ('index-scale-lifetime', 'previousIndex = *(s16 *)(owner + 0x1C) * 3;\n        factor = previousIndex * 4;'),
        ('view-opacity-lifetime', 'view = *(s16 *)(owner + 0x1C);\n        factor = (view * 3) * 4;'),
    ):
        yield name, mode.replace('factor = (*(s16 *)(owner + 0x1C) * 3) * 4;', expression)
    yield 'switch-default-factor', mode.replace(block, '''    switch (*(u16 *)(owner + 0x1E) & 8) {
    case 0:
        factor = 255;
        break;
    default:
        factor = (*(s16 *)(owner + 0x1C) * 3) * 4;
        break;
    }''')


SETUP_FITTED_NAME = 'retail-mode-order-reverse-factor'
SETUP_FITTED = dict(setup_candidates())[SETUP_FITTED_NAME]


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n#include <string.h>\n' + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'record-ring-renderer.ld'
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
    return dict(name=name, profile=profile, body_words=end, frame=(-words[0]) & 65535,
        saved_FP=[w >> 16 & 31 for w in words if w >> 26 == 61 and w >> 21 & 31 == 29],
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocations,
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--fit', action='store_true', help='screen complete stride/alpha/lifetime fitting forms')
    mode.add_argument('--schedule', action='store_true', help='screen complete register-role and scheduling forms')
    mode.add_argument('--setup', action='store_true', help='screen complete factor and mode-load fitting forms')
    parser.add_argument('--form', help='compile one named complete source form')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-ring-renderer'
    records = []
    forms = dict(setup_candidates() if args.setup else scheduling_candidates() if args.schedule
        else fitting_candidates() if args.fit else candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    for name, body in forms.items():
        for profile in PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    receipt = ('setup-' if args.setup else 'scheduling-' if args.schedule else 'fitting-' if args.fit else '') + ('profiles.json' if args.profiles else 'measurements.json')
    if args.form:
        receipt = args.form + '-' + receipt
    (out / receipt).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
