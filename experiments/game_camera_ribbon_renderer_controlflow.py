"""Recover complete ribbon exit flow and phase lifetimes without installation."""

import argparse
import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_staging as staging


ACTIVE = '''    if (*(s8 *)(actor + 0x2C) < 2) {
        return output;
    }'''
CURSOR = '''    if (cursor == NULL) {
        return output;
    }
    if (cursor != NULL) {'''


def exit_flow(body, mode):
    assert ACTIVE in body and CURSOR in body
    if mode == 'outer':
        body = body.replace(ACTIVE, '    if (*(s8 *)(actor + 0x2C) >= 2) {')
        body = body.replace('    return output;\n}', '    }\n    return output;\n}')
    elif mode == 'empty-null':
        body = body.replace(ACTIVE, '    if (*(s8 *)(actor + 0x2C) >= 2) {')
        body = body.replace(CURSOR, '    if (cursor == NULL) {\n    } else if (cursor != NULL) {')
        body = body.replace('    return output;\n}', '    }\n    return output;\n}')
    elif mode == 'goto':
        body = body.replace(ACTIVE, '    if (*(s8 *)(actor + 0x2C) < 2) {\n        goto done;\n    }')
        body = body.replace('    return output;\n}', 'done:\n    return output;\n}')
    else:
        assert mode == 'early'
    return body


def phase_lifetime(body, stride=False, registered=False):
    assert '    s16 view;' in body and '    s32 texture;' in body
    body = body.replace('    s16 view;', '    %ss32 phase;' % ('register ' if registered else ''))
    body = body.replace('    s32 texture;\n', '')
    body = body.replace('view = (s16)inputView;', 'phase = (s16)inputView;')
    body = body.replace('actor + 0x84, view,', 'actor + 0x84, (s16)phase,')
    body = body.replace('func_15144B34(view)', 'func_15144B34(phase)')
    body = body.replace('texture =', 'phase =').replace('texture !=', 'phase !=').replace(
        '= texture;', '= phase;')
    return staging.record_stride(body, 'phase') if stride else body


def scalar_order(body, order):
    declarations = [line for line in body.splitlines(True)
        if line.startswith('    f32 ') and '*' not in line]
    names = [name.strip() for line in declarations for name in line.strip()[4:-1].split(',')]
    assert set(names) == set(order) and len(names) == len(order)
    for line in declarations:
        body = body.replace(line, '')
    return body.replace('    Vtx *cursor;', ''.join('    f32 %s;\n' % name for name in order) +
        '    Vtx *cursor;', 1)


def scale_order(body, order):
    assignments = ('deltaY = normalX * deltaX;', 'deltaZ = normalY * deltaX;',
        'rayX = normalZ * deltaX;')
    for indent in (12, 16):
        before = ('\n' + ' ' * indent).join(assignments)
        after = ('\n' + ' ' * indent).join(assignments[index] for index in order)
        assert body.count(before) == 1
        body = body.replace(before, after)
    return body


def candidates():
    originals = dict(staging.candidates())
    seeds = (
        ('selected', originals['selected-short-input-local-view']),
        ('mixed', originals['retail-fp-wide-input-local-view'].replace('s32 inputView)', 's16 inputView)')),
    )
    for name, body in seeds:
        for mode in ('early', 'outer', 'empty-null', 'goto'):
            shaped = exit_flow(body, mode)
            yield name + '-' + mode, shaped
            for stride, registered in ((False, False), (True, False), (True, True)):
                label = name + '-' + mode + ('-phase-stride' if stride else '-phase')
                if registered:
                    label += '-register'
                yield label, phase_lifetime(shaped, stride, registered)
    selected, mixed = (exit_flow(body, 'outer') for _, body in seeds)
    orders = {
        'retail': ('length', 'normalX', 'normalY', 'normalZ', 'deltaY', 'deltaZ',
            'rayX', 'rayY', 'rayZ', 'deltaX'),
        'definitions': ('rayX', 'rayY', 'rayZ', 'deltaY', 'deltaZ', 'deltaX',
            'normalX', 'normalY', 'normalZ', 'length'),
        'cross-first': ('normalX', 'normalY', 'normalZ', 'deltaX', 'deltaY', 'deltaZ',
            'rayX', 'rayY', 'rayZ', 'length'),
    }
    for name, body in (('selected', selected), ('mixed', mixed),
            ('mixed-phase-stride', phase_lifetime(mixed, stride=True))):
        for label, order in orders.items():
            shaped = scalar_order(body, order)
            yield name + '-outer-scalars-' + label, shaped
            zero = 'deltaY = deltaZ = rayX = 0.0f;' if name.startswith('mixed') else \
                'deltaX = deltaY = deltaZ = 0.0f;'
            assert shaped.count(zero) == 2
            targets = zero.split(' = ')[:-1]
            separate = ' '.join(target + ' = 0.0f;' for target in targets)
            yield name + '-outer-scalars-' + label + '-separate-zero', shaped.replace(zero, separate)
    for order in itertools.permutations(range(3)):
        shaped = scale_order(mixed, order)
        label = 'mixed-outer-scale-' + ''.join('XYZ'[index] for index in order)
        yield label, shaped
        split = shaped.replace('            previousIndex = index;\n            index--;\n', '')
        split = split.replace('            rayX = current.x - origin[0];\n',
            '            rayX = current.x - origin[0];\n            previousIndex = index;\n')
        split = split.replace('            rayY = current.y - origin[1];\n',
            '            rayY = current.y - origin[1];\n            index--;\n')
        yield label + '-split-index', split


def compile_form(root, output, name, body):
    return staging.compile_form(root, output, name, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--scale-orders', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-controlflow'
    forms = dict(candidates())
    if args.scale_orders:
        forms = {name: body for name, body in forms.items() if '-scale-' in name}
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    records = []
    for name, body in forms.items():
        meta, words = compile_form(root, output, name, body)
        meta['saved_gpr'] = [(w >> 16 & 31, w & 65535) for w in words[:30]
            if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
            and (w & 65535) < meta['frame']]
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_gpr'], meta['saved_FP'], flush=True)
    (output / ((args.form or ('scale-orders' if args.scale_orders else 'all')) + '.json')).write_text(
        json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
