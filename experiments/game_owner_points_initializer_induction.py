"""Fit complete point initializer loop termination and zero-store emission."""
import argparse
import itertools
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_initializer_fitting as fitting

TYPES = fitting.TYPES
SEED = fitting.SELECTED
LOOP = '    for (i = 2; i < count; i += 4) {'


def separate_zeros(body, indices=None, reverse=False):
    pattern = (r'        points\[([^]]+)\]\.velocity\.x =\n'
        r'            points\[\1\]\.velocity\.y =\n'
        r'            points\[\1\]\.velocity\.z = 0\.0f;')

    def replace(match):
        index = match[1]
        if indices is not None and index not in indices:
            return match[0]
        return '\n'.join('        points[%s].velocity.%s = 0.0f;' % (index, field)
            for field in ('zyx' if reverse else 'xyz'))

    return re.sub(pattern, replace, body)


def controls():
    yield 'less-than', SEED
    yield 'not-equal', SEED.replace('i < count', 'i != count')
    yield 'less-equal', SEED.replace('i < count', 'i <= count - 1')
    for predicate in ('i != count', 'i < count'):
        body = SEED.replace(LOOP, '    i = 2;\n    do {').replace(
            '    }\n    owner->flags', '        i += 4;\n    } while (' + predicate + ');\n    owner->flags')
        yield 'do-' + ('not-equal' if '!=' in predicate else 'less-than'), body
    for comparison in ('!=', '<'):
        body = SEED.replace('    s32 i, count;', '    s32 i, count;\n    OwnerPointRecord3A7C *cursor;')
        body = body.replace(LOOP, '    cursor = points + 2;\n'
            '    for (i = 2; i ' + comparison + ' count; i += 4, cursor += 4) {')
        body = re.sub(r'points\[i \+ ([0-3])\]', r'cursor[\1]', body)
        yield 'cursor-' + ('not-equal' if comparison == '!=' else 'less-than'), body
    byte_index = SEED.replace('i < count', 'i != count').replace('count = 10;', 'count = 0xF0;').replace(
        'i = 2;', 'i = 0x30;').replace('i += 4', 'i += 0x60')
    for offset in range(4):
        for field, extra in (('position', 0), ('velocity.x', 12), ('velocity.y', 16), ('velocity.z', 20)):
            kind = 'OwnerRibbonPosition32C8' if field == 'position' else 'f32'
            byte_index = byte_index.replace('points[i + %d].%s' % (offset, field),
                '*(%s *)((u8 *)points + i + 0x%X)' % (kind, offset * 24 + extra))
    yield 'byte-counter', byte_index


def origin_forms():
    for origin in (0x18, 0x30, 0x48, 0x60):
        shift = (0x48 - origin) // 24
        body = SEED.replace('points = owner->points;',
            'points = (OwnerPointRecord3A7C *)(actor + 0x%X);' % origin)
        body = re.sub(r'points\[([^]]+)\]',
            lambda m: 'points[%s + %d]' % (m[1], shift), body)
        yield 'origin-%X-chain' % origin, body
        for reverse in (False, True):
            yield 'origin-%X-separate-%s' % (origin, 'reverse' if reverse else 'forward'), separate_zeros(body, reverse=reverse)
    for offset in (0, 1, 4, 6):
        body = SEED.replace('i = 2;', 'i = %d;' % offset).replace('count = 10;', 'count = %d;' % (offset + 8))
        body = re.sub(r'points\[i \+ ([0-3])\]',
            lambda m: 'points[i + %d]' % (int(m[1]) + 2 - offset), body)
        yield 'counter-origin-%d' % offset, body
        yield 'counter-origin-%d-not-equal' % offset, body.replace('i < count', 'i != count')
    goto = SEED.replace(LOOP, '    i = 2;\npoint_loop:\n    {').replace(
        '    }\n    owner->flags', '        i += 4;\n    }\n    if (i != count) goto point_loop;\n    owner->flags')
    yield 'goto-counter', goto
    for zero_decl in ('    f32 zero = 0.0f;\n', '    const f32 zero = 0.0f;\n'):
        for reverse in (False, True):
            body = separate_zeros(SEED, reverse=reverse).replace('    s32 i, count;',
                zero_decl + '    s32 i, count;').replace('= 0.0f;', '= zero;')
            body = body.replace('f32 zero = zero;', 'f32 zero = 0.0f;')
            yield ('const-zero' if 'const' in zero_decl else 'named-zero') + ('-reverse' if reverse else '-forward'), body
    for destination in ('x', 'y', 'z'):
        body = SEED
        pattern = (r'        points\[([^]]+)\]\.velocity\.x =\n'
            r'            points\[\1\]\.velocity\.y =\n'
            r'            points\[\1\]\.velocity\.z = 0\.0f;')
        def replace(match):
            fields = (destination,) + tuple(f for f in 'xyz' if f != destination)
            return '\n'.join('        points[%s].velocity.%s = %s;' % (match[1], field,
                '0.0f' if index == 0 else 'points[%s].velocity.%s' % (match[1], destination))
                for index, field in enumerate(fields))
        yield 'stored-zero-' + destination, re.sub(pattern, replace, body)


def staging_forms():
    scales = {field: '        step.%s = delta.%s * D_800AA39%s;\n' % (field, field, suffix)
        for field, suffix in (('x', '4'), ('y', '8'), ('z', 'C'))}
    advances = {field: '        position.%s += step.%s;\n' % (field, field) for field in 'xyz'}
    old = ''.join(scales.values()) + ''.join(advances.values())
    orders = ('sxsyszaxayaz', 'sxsyaxayszaz', 'sxaxsyayszaz',
        'sxaxsyszayaz', 'sxsyaxszayaz', 'sxsyszazaxay')
    for zero_kind in ('chain', 'loop-separated', 'raw-separated'):
        body = SEED if zero_kind == 'chain' else separate_zeros(SEED,
            None if zero_kind == 'raw-separated' else ('i + 0', 'i + 1', 'i + 2', 'i + 3'), True)
        if zero_kind == 'raw-separated':
            for field, offset in (('x', 0x54), ('y', 0x58), ('z', 0x5C)):
                body = re.sub(r'points\[([^]]+)\]\.velocity\.' + field,
                    lambda m: '*(f32 *)(actor + 0x%X + (%s) * 24)' % (offset, m[1]), body)
        assert body.count(old) == 1
        for order in orders:
            pieces = [order[i:i+2] for i in range(0, len(order), 2)]
            replacement = ''.join((scales if p[0] == 's' else advances)[p[1]] for p in pieces)
            assert len(pieces) == 6 and set(pieces) == set(('sx', 'sy', 'sz', 'ax', 'ay', 'az'))
            yield 'staging-' + zero_kind + '-' + order, body.replace(old, replacement)


def candidates():
    yield from staging_forms()
    for kind, indices in (('all', None), ('loop', ('i + 0', 'i + 1', 'i + 2', 'i + 3')),
            ('second-loop', ('i + 1',))):
        for zeros in ('chain', 'loop-separated'):
            body = SEED if zeros == 'chain' else separate_zeros(SEED, ('i + 0', 'i + 1', 'i + 2', 'i + 3'), True)
            def replace(match):
                if indices is not None and match[1] not in indices:
                    return match[0]
                return '*(OwnerRibbonPosition32C8 *)(actor + 0x48 + (%s) * 24)' % match[1]
            yield 'raw-position-' + kind + '-' + zeros, re.sub(r'points\[([^]]+)\]\.position', replace, body)
    yield from origin_forms()
    for split_index in (0, 1, 2):
        marker = '        points[i + %d].position = position;\n' % split_index
        head, tail = SEED.split(marker, 1)
        tail = re.sub(r'points\[i \+ ([0-3])\]',
            lambda m: 'points[i - %d]' % (4 - int(m[1])), tail)
        body = (head + marker + '        i += 4;\n' + tail).replace('i += 4) {', ') {')
        for predicate in ('i < count', 'i != count'):
            body2 = body.replace('i < count', predicate)
            yield 'mid-counter-%d-' % split_index + ('lt' if '<' in predicate else 'ne'), body2
            separated = separate_zeros(body2, reverse=True)
            for field, offset in (('x', 0x54), ('y', 0x58), ('z', 0x5C)):
                separated = re.sub(r'points\[([^]]+)\]\.velocity\.' + field,
                    lambda m: '*(f32 *)(actor + 0x%X + (%s) * 24)' % (offset, m[1]), separated)
            yield 'mid-counter-raw-%d-' % split_index + ('lt' if '<' in predicate else 'ne'), separated
    for label, declaration, start, address in (
            ('actor', '', '', 'actor + 0x%X + (%s) * 24'),
            ('bytes', '    u8 *pointBytes;\n', '    pointBytes = actor + 0x48;\n', 'pointBytes + 0x%X + (%s) * 24'),
            ('record-bytes', '', '', '(u8 *)points + 0x%X + (%s) * 24')):
        body = SEED.replace('    s32 i, count;', declaration + '    s32 i, count;').replace(
            '    points = owner->points;', start + '    points = owner->points;')
        for field, offset in (('x', 12), ('y', 16), ('z', 20)):
            body = re.sub(r'points\[([^]]+)\]\.velocity\.' + field,
                lambda m: '*(f32 *)(' + address % (offset + (0x48 if label == 'actor' else 0), m[1]) + ')', body)
        yield 'raw-zero-' + label, body
        # Split one or all original chains before replacing typed addresses.
        for suffix, indices in (('all', None), ('second-loop', ('i + 1',))):
            separated = separate_zeros(SEED, indices, True)
            for field, offset in (('x', 12), ('y', 16), ('z', 20)):
                separated = re.sub(r'points\[([^]]+)\]\.velocity\.' + field,
                    lambda m: '*(f32 *)(actor + 0x%X + (%s) * 24)' % (offset + 0x48, m[1]), separated)
            if label == 'actor':
                yield 'raw-zero-actor-' + suffix, separated
    for label, condition in (('xor', '(i ^ count) != 0'), ('masked', '(i & 15) != count'),
            ('unsigned-difference', '(u32)(i - count) != 0'),
            ('complement-difference', 'i + ~count != -1')):
        body = SEED.replace('i < count', condition)
        yield 'counter-' + label, body
    pattern = (r'        points\[([^]]+)\]\.velocity\.x =\n'
        r'            points\[\1\]\.velocity\.y =\n'
        r'            points\[\1\]\.velocity\.z = 0\.0f;')
    for fields in itertools.permutations('xyz'):
        for label, indices in (('all', None), ('loop', ('i + 0', 'i + 1', 'i + 2', 'i + 3')),
                ('second-loop', ('i + 1',))):
            def replace(match):
                if indices is not None and match[1] not in indices:
                    return match[0]
                return ''.join(('        ' if index == 0 else '            ') +
                    'points[%s].velocity.%s =' % (match[1], field) + (' 0.0f;' if index == 2 else '\n')
                    for index, field in enumerate(fields))
            yield 'zero-chain-' + label + '-' + ''.join(fields), re.sub(pattern, replace, SEED)
    for name, body in controls():
        yield name + '-chain', body
        for label, indices in (('all', None), ('loop', ('i + 0', 'i + 1', 'i + 2', 'i + 3')),
                ('second-loop', ('i + 1',))):
            for reverse in (False, True):
                if indices is not None and not all('points[%s]' % i in body for i in indices):
                    continue
                yield name + '-' + label + ('-reverse' if reverse else '-forward'), separate_zeros(body, indices, reverse)


SELECTED_NAME = 'staging-raw-separated-sxaxsyayszaz'
SELECTED = dict(staging_forms())[SELECTED_NAME]


def compile_candidate(root, out, name, body=None, profile='o2g3', symbols=None):
    return fitting.compile_candidate(root, out, name, SELECTED if body is None else body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--no-unroll', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-initializer-induction'
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    profiles = {'o2g3-no-unroll': ('-O2', '-g3', '-Wo,-loopunroll,0')}
    rows = []
    with patch.dict(fitting.base.compiler.PROFILES, profiles):
        for name, body in forms.items():
            profile = 'o2g3-no-unroll' if args.no_unroll else 'o2g3'
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / ((args.form or 'measurements') + ('-no-unroll' if args.no_unroll else '') + '.json')).write_text(
        json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
