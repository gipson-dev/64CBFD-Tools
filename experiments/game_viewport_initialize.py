"""Recover the complete view/viewport initializer before any production change."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_view_point_projection as previous
from tools.tests import view_point_projection_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections

BUILD = 'conker/build/game-viewport-initialize'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_476D0', 'func_1501A8C0', 0x1501A8C0, 0x47D70, 373
PATHS = dict(previous.PATHS, viewport_original='conker/asm/nonmatchings/game_476D0/func_1501A8C0.s',
    viewport_data='conker/asm/data/2275E0.data.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    viewport_original='b41161a616b4b892962927c6668218ad76dbd65e1b032ecb45d7aeecc22ecda4',
    viewport_data='9c912a5b5595b37b590fb8da13727bf91e1c495b0ff0f297231347417e7d700e')
build = previous.build
DECLARATIONS = '''extern const f32 D_800968E4, D_800968E8, D_800968EC, D_800968F0;
extern f32 D_80082FA8[];
extern s16 D_800BE668[][2];
extern u8 D_800BE630[];
'''
INITIAL = '''/* Initialize view geometry, both viewport pages and the projection state. */
void func_1501A8C0(s32 index, s32 layout, s32 depth, s16 transferFov) {
    f32 angle;
    f32 sine;

    VIEW_PROJECTIONS_476D0[index].width = (f32)((s32 *)&D_800BE638)[layout];
    VIEW_PROJECTIONS_476D0[index].height = (f32)((s32 *)&D_800BE650)[layout];
    if (layout != 0) {
        VIEW_PROJECTIONS_476D0[index].width -= 2.0f;
        VIEW_PROJECTIONS_476D0[index].height -= 2.0f;
    }
    VIEW_PROJECTIONS_476D0[index].layoutAspect = D_80082FA8[layout];
    VIEW_PROJECTIONS_476D0[index].layoutScale = 2.0f;
    if (layout == 1) {
        VIEW_PROJECTIONS_476D0[index].width *= D_800BE6B8;
        VIEW_PROJECTIONS_476D0[index].baseFovX = D_800968E4 * D_800BE6B8;
        VIEW_PROJECTIONS_476D0[index].baseFovY = 50.0f;
    } else {
        VIEW_PROJECTIONS_476D0[index].baseFovX = D_800968E8;
        VIEW_PROJECTIONS_476D0[index].baseFovY = 50.0f;
    }
    VIEW_PROJECTIONS_476D0[index].fovX = VIEW_PROJECTIONS_476D0[index].baseFovX;
    VIEW_PROJECTIONS_476D0[index].fovY = VIEW_PROJECTIONS_476D0[index].baseFovY;
    VIEW_PROJECTIONS_476D0[index].aspect = VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height;
    VIEW_PROJECTIONS_476D0[index].extentX = VIEW_PROJECTIONS_476D0[index].width * 0.5f;
    VIEW_PROJECTIONS_476D0[index].extentY = VIEW_PROJECTIONS_476D0[index].height * 0.5f;
    VIEW_PROJECTIONS_476D0[index].originX = (f32)D_800BE668[layout * 5 + index][0];
    VIEW_PROJECTIONS_476D0[index].originY = (f32)D_800BE668[layout * 5 + index][1];
    VIEW_PROJECTIONS_476D0[index].left = VIEW_PROJECTIONS_476D0[index].originX - VIEW_PROJECTIONS_476D0[index].extentX;
    VIEW_PROJECTIONS_476D0[index].top = VIEW_PROJECTIONS_476D0[index].originY - VIEW_PROJECTIONS_476D0[index].extentY;
    VIEW_PROJECTIONS_476D0[index].right = VIEW_PROJECTIONS_476D0[index].extentX + VIEW_PROJECTIONS_476D0[index].originX;
    VIEW_PROJECTIONS_476D0[index].bottom = VIEW_PROJECTIONS_476D0[index].extentY + VIEW_PROJECTIONS_476D0[index].originY;
    if (transferFov != 0) {
        func_1501B0A0(index, layout);
    } else {
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / (f32)D_800BE638) *
            (((f32)D_800BE638 / (f32)D_800BE650) / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));
        VIEW_PROJECTIONS_476D0[index].axisScaleY = VIEW_PROJECTIONS_476D0[index].height / (f32)D_800BE650;
    }
    angle = VIEW_PROJECTIONS_476D0[index].baseFovX * 0.5f * D_800968EC;
    sine = sinf(angle);
    VIEW_PROJECTIONS_476D0[index].projectionScaleX = sine / (VIEW_PROJECTIONS_476D0[index].extentX * cosf(angle));
    angle = VIEW_PROJECTIONS_476D0[index].baseFovY * 0.5f * D_800968F0;
    sine = sinf(angle);
    VIEW_PROJECTIONS_476D0[index].projectionScaleY = sine / (VIEW_PROJECTIONS_476D0[index].extentY * cosf(angle));
    ((Vp *)D_800BE62C)[index].vp.vscale[0] = (s16)(s32)((VIEW_PROJECTIONS_476D0[index].width + 10.0f) * 2.0f);
    ((Vp *)D_800BE62C)[index].vp.vscale[1] = (s16)(s32)((VIEW_PROJECTIONS_476D0[index].height + 10.0f) * 2.0f);
    depth >>= 1;
    ((Vp *)D_800BE62C)[index].vp.vscale[2] = depth;
    ((Vp *)D_800BE62C)[index].vp.vscale[3] = 0;
    ((Vp *)D_800BE62C)[index].vp.vtrans[0] = (s16)(s32)(VIEW_PROJECTIONS_476D0[index].originX * 4.0f);
    ((Vp *)D_800BE62C)[index].vp.vtrans[1] = (s16)(s32)(VIEW_PROJECTIONS_476D0[index].originY * 4.0f);
    ((Vp *)D_800BE62C)[index].vp.vtrans[2] = depth;
    ((Vp *)D_800BE62C)[index].vp.vtrans[3] = 0;
    VIEW_PROJECTIONS_476D0[index].viewport[D_800BE9C0] = ((Vp *)D_800BE62C)[index];
    VIEW_PROJECTIONS_476D0[index].viewport[!D_800BE9C0] = VIEW_PROJECTIONS_476D0[index].viewport[D_800BE9C0];
    VIEW_PROJECTIONS_476D0[index].projectionScale = 1.0f;
    VIEW_PROJECTIONS_476D0[index].insideBounds = func_1501AE94(index);
    func_1501AF44(&VIEW_PROJECTIONS_476D0[index].left, &VIEW_PROJECTIONS_476D0[index].top,
        &VIEW_PROJECTIONS_476D0[index].right, &VIEW_PROJECTIONS_476D0[index].bottom);
    func_1510B32C(index, 0.0f, 0.0f, VIEW_PROJECTIONS_476D0[index].projectionScale);
    D_800BE630[index] = index;
}'''
SELECTED = INITIAL


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, body=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501A8C0(s32 arg0, s32 arg1, s32 arg2, s32 arg3) {\n    return 0;\n}':
        raise ValueError('Unknown viewport-initializer predecessor')
    result = before[:lo] + body.split('\n', 1)[1] + before[hi:]
    for old, new in (
        ('s32 func_1501A8C0(s32 arg0, s32 arg1, s32 arg2, s32 arg3);', body.splitlines()[1][:-2] + ';'),
        ('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A8C0.s. */', body.splitlines()[0]),
        ('    u8 padding0[0xC];', '    u8 padding0;\n    u8 insideBounds;\n    u8 padding2[2];\n    f32 width, height;'),
        ('    u8 padding14[0x10];', '    f32 axisScaleX, axisScaleY;\n    u8 padding1C[8];'),
        ('    u8 padding60[0xC];', '    f32 aspect, layoutAspect, layoutScale;'),
        ('    u8 padding74[0x10C];', '    f32 fovX, fovY, projectionScaleX, projectionScaleY, projectionScale;\n    u8 padding88[0xF8];'),
        ('/* Generated placeholder declarations. */', DECLARATIONS + '\n/* Generated placeholder declarations. */')):
        if result.count(old) != 1: raise ValueError('Unknown viewport-initializer declaration/layout anchor')
        result = result.replace(old, new, 1)
    return result


def forms():
    yield 'initial', INITIAL
    yield 'sine-first-declaration', INITIAL.replace('    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;')
    yield 'depth-copy', INITIAL.replace('    f32 angle;', '    s32 halfDepth;\n    f32 angle;').replace(
        '    depth >>= 1;', '    halfDepth = depth >> 1;').replace(' = depth;', ' = halfDepth;')
    yield 'fov-chain-assignment', INITIAL.replace(
        '    VIEW_PROJECTIONS_476D0[index].fovX = VIEW_PROJECTIONS_476D0[index].baseFovX;\n', '').replace(
        '    VIEW_PROJECTIONS_476D0[index].fovY = VIEW_PROJECTIONS_476D0[index].baseFovY;\n', '').replace(
        '.baseFovX = D_800968', '.fovX = VIEW_PROJECTIONS_476D0[index].baseFovX = D_800968').replace(
        '.baseFovY = 50.0f;', '.fovY = VIEW_PROJECTIONS_476D0[index].baseFovY = 50.0f;')


def carrier_forms():
    body = INITIAL.replace('    f32 angle;', '    s16 *origin;\n    f32 angle;').replace(
        '(f32)D_800BE668[layout * 5 + index][0]', '(f32)origin[0]').replace(
        '(f32)D_800BE668[layout * 5 + index][1]', '(f32)origin[1]')
    for label, address in (('pair', 'D_800BE668[layout * 5 + index]'),
            ('bytes', '(s16 *)((u8 *)D_800BE668 + layout * 20 + index * 4)'),
            ('word-bytes', '(s16 *)((u32)D_800BE668 + (u32)layout * 20 + (u32)index * 4)')):
        for at in ('aspect', 'originX'):
            needle = '    VIEW_PROJECTIONS_476D0[index].' + at + ' = '
            yield label + '-before-' + at, body.replace(needle, '    origin = ' + address + ';\n' + needle, 1)


def temporary_forms():
    for label, body in (('initial', INITIAL), ('origin', dict(carrier_forms())['bytes-before-aspect'])):
        named = body.replace('    f32 angle;', '    f32 widthWithBorder, heightWithBorder;\n    f32 angle;')
        for field, name in (('width', 'widthWithBorder'), ('height', 'heightWithBorder')):
            expression = '(VIEW_PROJECTIONS_476D0[index].' + field + ' + 10.0f) * 2.0f'
            needle = '    ((Vp *)D_800BE62C)[index].vp.vscale[' + ('0' if field == 'width' else '1') + '] = '
            named = named.replace(needle, '    ' + name + ' = VIEW_PROJECTIONS_476D0[index].' + field + ' + 10.0f;\n' + needle, 1).replace(expression, '(' + name + ' + ' + name + ')')
        yield label + '-named-borders', named
        yield label + '-named-borders-depth', named.replace('    f32 angle;', '    s32 halfDepth;\n    f32 angle;').replace(
            '    depth >>= 1;', '    halfDepth = depth >> 1;').replace(' = depth;', ' = halfDepth;')
        yield label + '-named-borders-repeated-depth', named.replace('    depth >>= 1;\n', '').replace(' = depth;', ' = depth >> 1;')


def ratio_forms():
    body = dict(carrier_forms())['bytes-before-aspect'].replace(
        '.right = VIEW_PROJECTIONS_476D0[index].extentX + VIEW_PROJECTIONS_476D0[index].originX;',
        '.right = VIEW_PROJECTIONS_476D0[index].originX + VIEW_PROJECTIONS_476D0[index].extentX;').replace(
        '.bottom = VIEW_PROJECTIONS_476D0[index].extentY + VIEW_PROJECTIONS_476D0[index].originY;',
        '.bottom = VIEW_PROJECTIONS_476D0[index].originY + VIEW_PROJECTIONS_476D0[index].extentY;')
    old = '''        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / (f32)D_800BE638) *
            (((f32)D_800BE638 / (f32)D_800BE650) / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));'''
    values = {'selectedAspect':'VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height',
        'referenceAspect':'(f32)D_800BE638 / (f32)D_800BE650',
        'widthFraction':'VIEW_PROJECTIONS_476D0[index].width / (f32)D_800BE638'}
    import itertools
    for order in itertools.permutations(values):
        new = '\n'.join('        ' + n + ' = ' + values[n] + ';' for n in order)
        new += '\n        VIEW_PROJECTIONS_476D0[index].axisScaleX = widthFraction * (referenceAspect / selectedAspect);'
        candidate = body.replace('    f32 angle;', '    f32 selectedAspect, referenceAspect, widthFraction;\n    f32 angle;').replace(old, new)
        label = '-'.join(n[0] for n in order)
        yield 'ratios-' + label, candidate
        if order == tuple(values):
            yield 'ratios-sine-first', candidate.replace('    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;')
            yield 'ratios-repeated-depth', candidate.replace('    depth >>= 1;\n', '').replace(' = depth;', ' = depth >> 1;')


def trig_forms():
    base = dict(temporary_forms())['origin-named-borders-repeated-depth']
    for named in (False, True):
        body = base
        if named:
            body = body.replace('    f32 angle;', '    f32 cosine;\n    f32 angle;')
            for axis in ('X', 'Y'):
                needle = '    VIEW_PROJECTIONS_476D0[index].projectionScale' + axis + ' = '
                body = body.replace(needle, '    cosine = cosf(angle);\n' + needle).replace(
                    '.extent' + axis + ' * cosf(angle)', '.extent' + axis + ' * cosine')
        for reverse in (False, True):
            candidate = body
            if reverse:
                value = 'cosine' if named else 'cosf(angle)'
                for axis in ('X', 'Y'):
                    candidate = candidate.replace('VIEW_PROJECTIONS_476D0[index].extent' + axis + ' * ' + value,
                        value + ' * VIEW_PROJECTIONS_476D0[index].extent' + axis)
            for swap in (False, True):
                selected = candidate.replace('    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;') if swap else candidate
                yield 'trig-%d-%d-%d' % (named, reverse, swap), selected


def dimension_forms():
    body = dict(carrier_forms())['bytes-before-aspect']
    for reverse in (False, True):
        selected = body
        if reverse:
            for edge, origin, extent in (('right', 'originX', 'extentX'), ('bottom', 'originY', 'extentY')):
                selected = selected.replace('.' + edge + ' = VIEW_PROJECTIONS_476D0[index].' + extent + ' + VIEW_PROJECTIONS_476D0[index].' + origin,
                    '.' + edge + ' = VIEW_PROJECTIONS_476D0[index].' + origin + ' + VIEW_PROJECTIONS_476D0[index].' + extent)
        for order in (0, 1):
            setup = '        referenceWidth = (f32)D_800BE638;\n        referenceHeight = (f32)D_800BE650;\n'
            if order: setup = '\n'.join(reversed(setup.rstrip().splitlines())) + '\n'
            needle = '    } else {\n        VIEW_PROJECTIONS_476D0[index].axisScaleX'
            candidate = selected.replace('    f32 angle;', '    f32 referenceWidth, referenceHeight;\n    f32 angle;').replace(
                needle, '    } else {\n' + setup + '        VIEW_PROJECTIONS_476D0[index].axisScaleX')
            start = candidate.index('        VIEW_PROJECTIONS_476D0[index].axisScaleX')
            end = candidate.index('        VIEW_PROJECTIONS_476D0[index].axisScaleY', start)
            candidate = candidate[:start] + candidate[start:end].replace('(f32)D_800BE638', 'referenceWidth').replace(
                '(f32)D_800BE650', 'referenceHeight') + candidate[end:]
            for repeat in (False, True):
                value = candidate.replace('    depth >>= 1;\n', '').replace(' = depth;', ' = depth >> 1;') if repeat else candidate
                yield 'dimensions-%d-%d-%d' % (reverse, order, repeat), value


def width_forms():
    body = dict(dimension_forms())['dimensions-1-0-1'].replace('    f32 referenceWidth, referenceHeight;',
        '    f32 referenceWidth;').replace('        referenceHeight = (f32)D_800BE650;\n', '').replace(
        'referenceWidth / referenceHeight', 'referenceWidth / (f32)D_800BE650')
    for named in (False, True):
        candidate = body
        if named:
            candidate = candidate.replace('    f32 angle;', '    f32 cosine;\n    f32 angle;')
            for axis in ('X', 'Y'):
                needle = '    VIEW_PROJECTIONS_476D0[index].projectionScale' + axis + ' = '
                candidate = candidate.replace(needle, '    cosine = cosf(angle);\n' + needle).replace(
                    '.extent' + axis + ' * cosf(angle)', '.extent' + axis + ' * cosine')
        yield 'width-%d' % named, candidate
        yield 'width-%d-sine-first' % named, candidate.replace('    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;')
        if named:
            yield 'width-cosine-after-sine', candidate.replace('    f32 cosine;\n', '').replace(
                '    f32 sine;', '    f32 sine;\n    f32 cosine;')
            yield 'width-coefficient-first', candidate.replace('    f32 referenceWidth;\n', '').replace(
                '    s16 *origin;', '    f32 referenceWidth;\n    s16 *origin;')


def declaration_forms():
    import itertools
    body = dict(dimension_forms())['dimensions-1-0-1']
    old = '    s16 *origin;\n    f32 referenceWidth, referenceHeight;\n    f32 angle;\n    f32 sine;'
    declarations = ('s16 *origin;', 'f32 referenceWidth;', 'f32 referenceHeight;', 'f32 angle;', 'f32 sine;')
    if body.count(old) != 1: raise ValueError('Unknown viewport declaration block')
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'declarations-%03d' % index, body.replace(old, '\n'.join('    ' + s for s in order), 1)


def height_word_forms():
    body = dict(dimension_forms())['dimensions-1-0-1'].replace('    f32 referenceWidth, referenceHeight;',
        '    f32 referenceWidth;\n    s32 referenceHeight;').replace(
        '        referenceHeight = (f32)D_800BE650;', '        referenceHeight = D_800BE650;').replace(
        'referenceWidth / referenceHeight', 'referenceWidth / (f32)referenceHeight')
    yield 'height-word', body
    yield 'height-word-sine-first', body.replace('    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;')
    yield 'height-word-first', body.replace('    f32 referenceWidth;\n    s32 referenceHeight;',
        '    s32 referenceHeight;\n    f32 referenceWidth;')
    yield 'height-word-early-load', body.replace('        referenceWidth = (f32)D_800BE638;\n        referenceHeight = D_800BE650;',
        '        referenceHeight = D_800BE650;\n        referenceWidth = (f32)D_800BE638;')


SELECTED = dict(dimension_forms())['dimensions-1-0-1']
RAW_SHA256 = '6cc0dd6c52665773dbb2a5ef7e185af99be4b3aad7ef9a1d14cde4d3ae1e6e3e'
RELOCATIONS = {
    0x8: [('R_MIPS_HI16', 'D_800BE628')],
    0x18: [('R_MIPS_HI16', 'D_800BE650')],
    0x1C: [('R_MIPS_HI16', 'D_800BE638')],
    0x20: [('R_MIPS_LO16', 'D_800BE638')],
    0x24: [('R_MIPS_LO16', 'D_800BE650')],
    0x30: [('R_MIPS_LO16', 'D_800BE628')],
    0xC8: [('R_MIPS_HI16', 'D_80082FA8')],
    0xD4: [('R_MIPS_LO16', 'D_80082FA8')],
    0xE8: [('R_MIPS_HI16', 'D_800BE6B8')],
    0xFC: [('R_MIPS_LO16', 'D_800BE6B8')],
    0x10C: [('R_MIPS_HI16', 'D_800968E4')],
    0x11C: [('R_MIPS_LO16', 'D_800968E4')],
    0x14C: [('R_MIPS_HI16', 'D_800968E8')],
    0x150: [('R_MIPS_LO16', 'D_800968E8')],
    0x198: [('R_MIPS_HI16', 'D_800BE668')],
    0x1B4: [('R_MIPS_LO16', 'D_800BE668')],
    0x28C: [('R_MIPS_26', 'func_1501B0A0')],
    0x308: [('R_MIPS_HI16', 'D_800968EC')],
    0x30C: [('R_MIPS_LO16', 'D_800968EC')],
    0x324: [('R_MIPS_26', 'sinf')],
    0x330: [('R_MIPS_26', 'cosf')],
    0x354: [('R_MIPS_HI16', 'D_800968F0')],
    0x364: [('R_MIPS_LO16', 'D_800968F0')],
    0x37C: [('R_MIPS_26', 'sinf')],
    0x388: [('R_MIPS_26', 'cosf')],
    0x3A8: [('R_MIPS_HI16', 'D_800BE62C')],
    0x3B0: [('R_MIPS_LO16', 'D_800BE62C')],
    0x3C0: [('R_MIPS_HI16', 'D_800BE9C0')],
    0x3C4: [('R_MIPS_LO16', 'D_800BE9C0')],
    0x55C: [('R_MIPS_26', 'func_1501AE94')],
    0x584: [('R_MIPS_26', 'func_1501AF44')],
    0x5A4: [('R_MIPS_26', 'func_1510B32C')],
    0x5AC: [('R_MIPS_HI16', 'D_800BE630')],
    0x5B4: [('R_MIPS_LO16', 'D_800BE630')],
}


def checked_candidate(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 1492 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown viewport candidate words/bindings/pools')
    return raw


def measure(root, out, label='selected', body=None, flags=('-O2', '-g3')):
    freeze(root, out)
    content = recovered_owner((out / 'before-frustum_owner').read_text(), body)
    obj, diagnostics = build.compile_owner(root, out, content, label, flags)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>373I', (out / 'before-retail_rom').read_bytes(), ROM))
    padded = words + [0] * max(0, WORDS - len(words))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(padded, truth)) + max(0, len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={a - f['value']:r for a, r in relocations.items() if f['value'] <= a < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(padded, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--carriers', action='store_true')
    parser.add_argument('--temporaries', action='store_true')
    parser.add_argument('--ratios', action='store_true')
    parser.add_argument('--trig', action='store_true')
    parser.add_argument('--dimensions', action='store_true')
    parser.add_argument('--width', action='store_true')
    parser.add_argument('--declarations', action='store_true')
    parser.add_argument('--height-word', action='store_true')
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    best = 10000
    for label, body in (height_word_forms() if args.height_word else declaration_forms() if args.declarations else width_forms() if args.width else dimension_forms() if args.dimensions else trig_forms() if args.trig else ratio_forms() if args.ratios else temporary_forms() if args.temporaries else carrier_forms() if args.carriers else forms() if args.screens else [('selected', SELECTED)]):
        row = measure(root, root / BUILD, label, body)[2]
        if not args.declarations or row['differences'] < best:
            best = min(best, row['differences'])
            print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
        if args.declarations and row['differences'] == 0: break
    if args.declarations: print(json.dumps(dict(last=label, best=best)), flush=True)
