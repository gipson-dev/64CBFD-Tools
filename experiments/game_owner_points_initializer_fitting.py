"""Full owner point-initializer layout, workspace and induction fitting."""
import argparse
import itertools
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_initializer_candidates as base

RECOVERY_BODY = base.RECOVERED
OWNER_TYPE = '''typedef struct {
    u8 header[0x10];
    u8 flags;
    u8 gap11[3];
    OwnerRibbonPosition32C8 start, end;
    u8 metadata[0x1C];
    OwnerPointRecord3A7C points[10];
} OwnerPoints3A7C;
'''
TYPES = base.TYPES + OWNER_TYPE


def owner_body(body):
    result = body.replace('    OwnerPointRecord3A7C *points;\n', '').replace(
        '    points = (OwnerPointRecord3A7C *)(actor + 0x48);\n', '')
    result = result.replace('points[', 'owner->points[').replace('actor[0x10]', 'owner->flags').replace(
        '*(OwnerRibbonPosition32C8 *)(actor + 0x14)', 'owner->start')
    for field, offset in (('x', 0x14), ('y', 0x18), ('z', 0x1C)):
        result = result.replace('*(f32 *)(actor + 0x%X)' % offset, 'owner->start.' + field).replace(
            '*(f32 *)(actor + 0x%X)' % (offset + 12), 'owner->end.' + field)
    return result.replace('s32 func_151B3A7C(u8 *actor) {',
        's32 func_151B3A7C(u8 *actor) {\n    OwnerPoints3A7C *owner = (OwnerPoints3A7C *)actor;')


def candidates():
    forms = dict(base.candidates())
    for name in ('typed-records', 'typed-vector-steps', 'typed-vector-four-count-late',
                 'typed-vector-four-late-separate'):
        yield 'owner-' + name, owner_body(forms[name])
    seed = owner_body(RECOVERY_BODY)
    declarations = '    OwnerRibbonPosition32C8 delta, step;\n    OwnerRibbonPosition32C8 position;'
    for order in itertools.permutations(('delta', 'step', 'position')):
        yield 'owner-order-' + '-'.join(order), seed.replace(declarations,
            ''.join('    OwnerRibbonPosition32C8 %s;\n' % name for name in order).rstrip())
    ordered = seed.replace(declarations, '    OwnerRibbonPosition32C8 delta, position, step;')
    for label, fields in (('raw-position', ('position',)),
                         ('raw-second-vector', ('velocity.x', 'velocity.y', 'velocity.z'))):
        body = ordered
        offsets = dict(position=0x48, **{'velocity.x': 0x54, 'velocity.y': 0x58, 'velocity.z': 0x5C})
        for field in fields:
            kind = 'OwnerRibbonPosition32C8' if field == 'position' else 'f32'
            body = re.sub(r'owner->points\[([^]]+)\]\.' + re.escape(field),
                lambda m: '*(%s *)(actor + 0x%X + (%s) * 0x18)' % (kind, offsets[field], m[1]), body)
        yield 'owner-hybrid-' + label, body
    local = ordered.replace('    s32 i, count;',
        '    s32 i, count;\n    OwnerPointRecord3A7C *points;').replace(
        '    delta.x =', '    points = owner->points;\n    delta.x =', 1).replace('owner->points[', 'points[')
    yield 'owner-local-record-pointer', local
    yield 'owner-local-register-counter', local.replace('s32 i, count;', 'register s32 i, count;')
    yield 'owner-local-counter-first', local.replace('    s32 i, count;\n', '').replace(
        '    OwnerPoints3A7C *owner', '    s32 i, count;\n    OwnerPoints3A7C *owner')
    yield 'owner-local-count-difference', local.replace('i < count', 'count - i > 0')
    yield 'owner-local-count-difference-nonzero', local.replace('i < count', '(count - i) != 0')
    for kind in ('u32', 'u16', 'u8', 's16', 's8'):
        yield 'owner-counter-' + kind, seed.replace('s32 i, count;', kind + ' i, count;')
    for operator in ('!=', '<=', '=='):
        if operator == '==':
            body = seed.replace('    for (i = 2; i < count; i += 4) {', '    i = 2;\n    for (;;) {').replace(
                '    }\n    owner->flags', '        i += 4;\n        if (i == count) { break; }\n'
                '    }\n    owner->flags')
        else:
            body = seed.replace('i < count', 'i ' + operator + ' ' + ('count - 1' if operator == '<=' else 'count'))
        yield 'owner-counter-' + operator.replace('=', 'eq').replace('!', 'not').replace('<', 'le'), body
    for name in ('typed-records', 'typed-vector-steps'):
        body = owner_body(forms[name])
        setup, loop = body.split('    for (i = 0; i < 10; i++) {\n', 1)
        work, tail = loop.split('    }\n', 1)
        for field in ('x', 'y', 'z'):
            scalar = dict(x='dx', y='dy', z='dz')[field]
            setup = setup.replace('    %s *= D_800AA39%s;\n' %
                (scalar, dict(x='4', y='8', z='C')[field]), '')
            setup = setup.replace('    step.%s = delta.%s * D_800AA39%s;\n' %
                (field, field, dict(x='4', y='8', z='C')[field]), '')
        copied, advances = work.split('        position.x +=', 1)
        scales = (''.join('        %s *= D_800AA39%s;\n' % (scalar, suffix)
            for scalar, suffix in (('dx', '4'), ('dy', '8'), ('dz', 'C'))) if name == 'typed-records'
            else ''.join('        step.%s = delta.%s * D_800AA39%s;\n' % (field, field, suffix)
                for field, suffix in (('x', '4'), ('y', '8'), ('z', 'C'))))
        first = copied.replace('owner->points[i]', 'owner->points[0]') + scales + '        position.x +=' + advances
        result = setup + first + '    for (i = 1; i < 10; i++) {\n' + work + '    }\n' + tail
        yield 'owner-' + name + '-peeled-first', result
        yield 'owner-' + name + '-peeled-count', result.replace('    s32 i;', '    s32 i, count;').replace(
            '    for (i = 1; i < 10;', '    count = 10;\n    for (i = 1; i < count;')


SELECTED_NAME = 'owner-local-record-pointer'
SELECTED = dict(candidates())[SELECTED_NAME]


def compile_candidate(root, out, name, body=None, profile='o2g3', symbols=None):
    with patch.object(base, 'TYPES', TYPES):
        return base.compile_candidate(root, out, name, SELECTED if body is None else body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-initializer-fitting'
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    rows = []
    if args.profiles:
        profiles = {'o3g3': ('-O3', '-g3'), 'o2g2': ('-O2', '-g2'),
            'o2g3-unroll2': ('-O2', '-g3', '-Wo,-loopunroll,2'),
            'o2g3-unroll4': ('-O2', '-g3', '-Wo,-loopunroll,4'),
            'o2g3-unroll0': ('-O2', '-g3', '-Wo,-loopunroll,0')}
        with patch.dict(base.compiler.PROFILES, profiles):
            for name in (SELECTED_NAME, 'owner-typed-vector-steps',
                         'owner-typed-vector-steps-peeled-first'):
                for profile in profiles:
                    try:
                        meta, _ = compile_candidate(root, out, name + '-' + profile, dict(candidates())[name], profile)
                    except ValueError as error:
                        rows.append(dict(name=name, profile=profile, rejected_diagnostics=str(error)))
                        print(name, profile, 'rejected diagnostics', str(error).strip(), flush=True)
                        continue
                    rows.append(meta)
                    print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    for name, body in forms.items():
        meta, _ = compile_candidate(root, out, name, body)
        rows.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / ((args.form or 'measurements') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
