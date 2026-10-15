"""Focused live-temporary and clip-literal fitting; production stays frozen."""
import argparse
import itertools
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_remaining_donor_candidates as build

BUILD = source.BUILD + '/lifetime-fit'


def variants():
    old = dict(source.variants())
    for base, lifetime, zero in itertools.product(('homes-1-0-2', 'nested-if', 'selected'),
            ('same', 'shared-cosine', 'focal-cosine', 'cosine-product', 'focal-product', 'named-sine'),
            ('0.0f', '0', '0.0')):
        body = old[base]
        cosines = ('cosineX', 'cosineY') if base == 'homes-1-0-2' else ('cosine', 'cosine')
        if lifetime == 'shared-cosine' and base == 'homes-1-0-2':
            body = body.replace('cosineX, cosineY,', 'cosine,')
            body = re.sub(r'\bcosine[XY]\b', 'cosine', body)
        elif lifetime == 'focal-cosine':
            for cosine in set(cosines):
                body = body.replace(cosine + ', ', '')
                body = re.sub(r'\b' + cosine + r'\b', 'focalExtent', body)
        elif lifetime in ('cosine-product', 'focal-product'):
            for axis, cosine in zip(('X', 'Y'), cosines):
                left = 'PROJECTION_VIEWS_138520[index].projection' + axis
                temporary = cosine if lifetime == 'cosine-product' else 'focalExtent'
                start = body.index('    ' + left + ' =')
                end = body.index(';', start) + 1
                statement = body[start:end].replace(left + ' =', temporary + ' =', 1)
                body = body[:start] + statement + '\n    ' + left + ' = ' + temporary + ';' + body[end:]
        elif lifetime == 'named-sine':
            body = body.replace('    f32 halfAngle,', '    f32 sine;\n    f32 halfAngle,', 1)
            body = body.replace('    focalExtent =', '    sine = sinf(halfAngle);\n    focalExtent =')
            body = body.replace(' / sinf(halfAngle);', ' / sine;')
        body = body.replace('0.0f', zero)
        yield '%s-%s-zero%s' % (base, lifetime, ('f' if zero == '0.0f' else 'i' if zero == '0' else 'd')), body
    for base, inner, outer, scale_first in itertools.product(('homes-1-0-2', 'nested-if'), range(2), range(2), range(2)):
        body = old[base]
        for axis in ('X', 'Y'):
            target = 'PROJECTION_VIEWS_138520[index].projection' + axis
            factor = 'PROJECTION_VIEWS_138520[index].projectionScale' + axis
            unit = 'PROJECTION_VIEWS_138520[index].axisScale' + axis
            product = '(' + (('focalExtent * ' + unit) if inner else (unit + ' * focalExtent')) + ')'
            product = (product + ' * ' + factor) if outer else (factor + ' * ' + product)
            product = ('scale * (' + product + ')') if scale_first else ('(' + product + ') * scale')
            start = body.index('    ' + target + ' =')
            end = body.index(';', start) + 1
            body = body[:start] + '    ' + target + ' = ' + product + ';' + body[end:]
        yield 'product-%s-%d-%d-%d' % (base, inner, outer, scale_first), body
    yield from clip_variants(old['homes-1-0-2'])
    for base, form in itertools.product(('nested-if', 'homes-1-0-2'), range(7)):
        body = product_view(old[base])
        cosines = ('cosineX', 'cosineY') if base == 'homes-1-0-2' else ('cosine', 'cosine')
        if form in (0, 1):
            body = body.replace('    f32 halfAngle,', '    f32 cosineCopy;\n    f32 halfAngle,', 1)
            for cosine in set(cosines):
                body = body.replace('    focalExtent = ' + cosine + ' *',
                    '    cosineCopy = ' + cosine + ';\n    focalExtent = cosineCopy *')
            if form == 1:
                body = body.replace('    f32 cosineCopy;\n', '')
                body = body.replace('f32 halfAngle,', 'f32 cosineCopy, halfAngle,', 1)
        elif form == 2:
            for cosine in set(cosines):
                body = body.replace('    focalExtent = ' + cosine + ' *',
                    '    focalExtent = ' + cosine + ';\n    focalExtent = focalExtent *')
        elif form == 3:
            body = body.replace('    f32 halfAngle,', '    f32 halfArgument;\n    f32 halfAngle,', 1)
            body = body.replace(' = cosf(halfAngle);', ' = cosf(halfArgument);').replace('/ sinf(halfAngle);', '/ sinf(halfArgument);')
            for cosine in set(cosines):
                body = body.replace('    ' + cosine + ' =', '    halfArgument = halfAngle;\n    ' + cosine + ' =')
        elif form == 4:
            body = body.replace('    f32 halfAngle,', '    f32 sine, numerator;\n    f32 halfAngle,', 1)
            for axis, cosine in zip(('X', 'Y'), cosines):
                old_line = '    focalExtent = ' + cosine + ' * PROJECTION_VIEWS_138520[index].extent' + axis + ' / sinf(halfAngle);'
                new_line = ('    sine = sinf(halfAngle);\n'
                    '    numerator = ' + cosine + ' * PROJECTION_VIEWS_138520[index].extent' + axis + ';\n'
                    '    focalExtent = numerator / sine;')
                assert body.count(old_line) == 1
                body = body.replace(old_line, new_line)
        elif form == 5:
            body = body.replace('    f32 halfAngle,', '    f32 horizontalOffset = offsetX;\n    f32 verticalOffset = offsetY;\n    f32 halfAngle,', 1)
            body = body.replace('baseFovX + offsetX', 'baseFovX + horizontalOffset').replace('baseFovY + offsetY', 'baseFovY + verticalOffset')
        elif form == 6 and base == 'homes-1-0-2':
            body = body.replace('    focalExtent = cosineX *', '    cosineY = cosineX;\n    focalExtent = cosineY *', 1)
        yield 'copy-%s-%d' % (base, form), body
    base = product_view(old['homes-1-0-2'])
    for mode in range(4):
        body = base
        if mode & 1:
            body = body.replace('if (nearOverride != 0.0f)', 'if (D_800C364C != 0.0f)')
        if mode & 2:
            body = body.replace('farPlane = farOverride != 0.0f', 'farPlane = D_800C3650 != 0.0f')
        yield 'global-condition-%d' % mode, body
    alias = base.replace('    focalExtent = cosineX *', '    cosineY = cosineX;\n    focalExtent = cosineY *', 1)
    for zero_form, clip_form in itertools.product(range(4), range(4)):
        body = alias
        if zero_form:
            if zero_form == 1:
                body = body.replace('    f32 farOverride;', '    f32 zero;\n    f32 farOverride;', 1)
                body = body.replace('    nearOverride =', '    zero = 0.0f;\n    nearOverride =', 1)
            elif zero_form == 2:
                body = body.replace('    f32 farOverride;', '    f32 zero = 0.0f;\n    f32 farOverride;', 1)
            else:
                body = body.replace('    f32 farOverride;', '    const f32 zero = 0.0f;\n    f32 farOverride;', 1)
            body = body.replace('nearOverride != 0.0f', 'zero != nearOverride')
            body = body.replace('nearFallback != 0.0f', 'nearFallback != zero')
            body = body.replace('farOverride != 0.0f', 'zero != farOverride')
        zero = 'zero' if zero_form else '0.0f'
        old_clip = ('if (' + (zero + ' != nearOverride' if zero_form else 'nearOverride != 0.0f') + ') { nearPlane = nearOverride; }\n'
            '    else if (nearFallback != ' + zero + ') { nearPlane = nearFallback; }\n'
            '    else { nearPlane = D_800D9B20; }')
        assert body.count(old_clip) == 1
        if clip_form == 1:
            body = body.replace(old_clip, 'if (' + zero + ' != nearOverride) { nearPlane = nearOverride; }\n'
                '    else { nearPlane = nearFallback != ' + zero + ' ? nearFallback : D_800D9B20; }')
        elif clip_form == 2:
            body = body.replace(old_clip, 'nearPlane = nearOverride;\n'
                '    if (' + zero + ' == nearOverride) {\n'
                '        nearPlane = nearFallback != ' + zero + ' ? nearFallback : D_800D9B20;\n    }')
        elif clip_form == 3:
            body = body.replace(old_clip, 'nearPlane = nearFallback;\n'
                '    if (' + zero + ' != nearOverride) { nearPlane = nearOverride; }\n'
                '    else if (nearFallback == ' + zero + ') { nearPlane = D_800D9B20; }')
        yield 'zero-%d-%d' % (zero_form, clip_form), body
    old_clip = ('if (nearOverride != 0.0f) { nearPlane = nearOverride; }\n'
        '    else if (nearFallback != 0.0f) { nearPlane = nearFallback; }\n'
        '    else { nearPlane = D_800D9B20; }')
    shapes = (
        'if (nearOverride == 0.0f) {\n'
        '        if (nearFallback != 0.0f) { nearPlane = nearFallback; }\n'
        '        else { nearPlane = D_800D9B20; }\n'
        '    } else { nearPlane = nearOverride; }',
        'nearPlane = nearOverride != 0.0f ? nearOverride : nearFallback;\n'
        '    if (nearPlane == 0.0f) { nearPlane = D_800D9B20; }',
        'if ((nearPlane = nearOverride) == 0.0f) {\n'
        '        if ((nearPlane = nearFallback) == 0.0f) { nearPlane = D_800D9B20; }\n    }',
        'if (nearOverride != 0.0f || nearFallback != 0.0f) {\n'
        '        nearPlane = nearOverride != 0.0f ? nearOverride : nearFallback;\n'
        '    } else { nearPlane = D_800D9B20; }',
        'nearPlane = nearFallback;\n'
        '    if (nearOverride != 0.0f) { nearPlane = nearOverride; }\n'
        '    if (nearOverride == 0.0f && nearFallback == 0.0f) { nearPlane = D_800D9B20; }',
        'if (nearOverride == 0.0f && nearFallback == 0.0f) { nearPlane = D_800D9B20; }\n'
        '    else { nearPlane = nearOverride != 0.0f ? nearOverride : nearFallback; }',
        'if (nearOverride != 0.0f) { nearPlane = nearOverride; }\n'
        '    else if (nearFallback == 0.0f) { nearPlane = D_800D9B20; }\n'
        '    else { nearPlane = nearFallback; }',
    )
    for mode, shape in enumerate(shapes):
        assert alias.count(old_clip) == 1
        yield 'branch-%d' % mode, alias.replace(old_clip, shape)
    yield from layout_variants(alias)
    for index, declarations in enumerate((
            'f32 D_800C364C, D_800C3650;',
            'f32 D_800C3648, D_800C364C, D_800C3650;',
            'f32 D_800C364C;',
            'f32 D_800C3650;')):
        yield 'ownership-%d' % index, declarations + '\n\n' + alias


def layout_variants(alias):
    for mode in range(10):
        body = alias
        if mode == 0:
            body = body.replace('{ nearPlane =', '{\n        nearPlane =').replace('; }', ';\n    }')
        elif mode == 1:
            body = body.replace(';\n', '; ')
        elif mode == 2:
            start = body.index('    PROJECTION_VIEWS_138520[index].fovX =')
            end = body.index('    cosineX =')
            body = body[:start] + ' '.join(body[start:end].split()) + '\n' + body[end:]
        elif mode == 3:
            start = body.index('    nearOverride =')
            end = body.index('    func_1510B5F8(')
            body = body[:start] + ' '.join(body[start:end].split()) + '\n' + body[end:]
        elif mode == 4:
            body = ' '.join(body.split()) + '\n'
        elif mode == 5:
            body = body.replace(';', ';\n').replace('{', '{\n').replace('}', '\n}\n')
        elif mode == 6:
            body = body.replace('    nearOverride =', '    {\n    nearOverride =', 1)
            body = body.replace('    func_1510B5F8(', '    }\n    func_1510B5F8(', 1)
        elif mode == 7:
            body = body.replace('    PROJECTION_VIEWS_138520[index].fovX =', '    {\n    PROJECTION_VIEWS_138520[index].fovX =', 1)
            body = body.replace('    halfAngle = PROJECTION_VIEWS_138520[index].fovX', '    }\n    halfAngle = PROJECTION_VIEWS_138520[index].fovX', 1)
        elif mode == 8:
            body = body.replace('    farOverride =', '    if (1) {}\n    farOverride =', 1)
        elif mode == 9:
            body = body.replace('    halfAngle = PROJECTION_VIEWS_138520[index].fovX', '    if (1) {}\n    halfAngle = PROJECTION_VIEWS_138520[index].fovX', 1)
        yield 'layout-%d' % mode, body


def product_view(body):
    for axis in ('X', 'Y'):
        target = 'PROJECTION_VIEWS_138520[index].projection' + axis
        start = body.index('    ' + target + ' =')
        end = body.index(';', start) + 1
        expression = ('(PROJECTION_VIEWS_138520[index].axisScale' + axis + ' * focalExtent) * '
            'PROJECTION_VIEWS_138520[index].projectionScale' + axis + ' * scale')
        body = body[:start] + '    ' + target + ' = ' + expression + ';' + body[end:]
    return body


def clip_variants(before):
    base = product_view(before)
    old = ('if (nearOverride != 0.0f) { nearPlane = nearOverride; }\n'
        '    else if (nearFallback != 0.0f) { nearPlane = nearFallback; }\n'
        '    else { nearPlane = D_800D9B20; }')
    assert base.count(old) == 1
    for shape, reverse_near, reverse_far in itertools.product(range(4), range(2), range(2)):
        shapes = (
            old,
            'nearPlane = nearOverride != 0.0f ? nearOverride :\n'
            '        nearFallback != 0.0f ? nearFallback : D_800D9B20;',
            'if (nearOverride != 0.0f) { nearPlane = nearOverride; }\n'
            '    else { nearPlane = nearFallback != 0.0f ? nearFallback : D_800D9B20; }',
            'nearPlane = nearOverride != 0.0f ? nearOverride :\n'
            '        nearFallback == 0.0f ? D_800D9B20 : nearFallback;',
        )
        body = base.replace(old, shapes[shape])
        if reverse_near:
            body = body.replace('nearOverride != 0.0f', '0.0f != nearOverride')
        if reverse_far:
            body = body.replace('farOverride != 0.0f', '0.0f != farOverride')
        yield 'clip-%d-%d-%d' % (shape, reverse_near, reverse_far), body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]*', args.filter):
        parser.error('filter must contain only label characters')
    root = Path(__file__).resolve().parents[2]
    source.freeze(root, root / source.BUILD)
    out = root / BUILD
    out.mkdir(exist_ok=True)
    before = (root / source.BUILD / 'before-owner').read_text()
    retail = list(struct.unpack_from('>129I', (root / 'conker/conker.us.bin').read_bytes(), source.ROM))
    rows = []
    for label, body in variants():
        if args.filter not in label:
            continue
        obj, diagnostics = build.compile_owner(root, out, source.recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, source.OWNER)
        info = functions[source.FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, bytes=info['size'], frame=(-words[0] & 65535), diagnostics=diagnostics,
            differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b],
            uncovered=max(0, 129 - len(words)))
        rows.append(row)
        print(label, row['bytes'], row['frame'], len(row['differences']), diagnostics, flush=True)
    suffix = '-' + args.filter if args.filter else ''
    (out / ('screens' + suffix + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
