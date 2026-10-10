"""Fit actual arc delta-Y storage and complete coordinate-loop forms."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_candidates as base
from tools.experiments import game_owner_points_arc_lifetimes as previous

DELTA_TYPE = '''typedef struct {
    f32 x;
    volatile f32 y;
    f32 z;
} OwnerArcDeltaY;
'''
TYPES = base.TYPES + DELTA_TYPE
ORIGINAL_BODY = previous.SELECTED


def candidates():
    member = ORIGINAL_BODY.replace('    OwnerRibbonPosition32C8 delta, midpoint;',
        '    OwnerArcDeltaY delta;\n    OwnerRibbonPosition32C8 midpoint;')
    yield 'member-private-y', member
    snapshots = ((0x20, 'nx'), (0x14, 'along'), (0x24, 'nz'), (0x18, 'sine'),
        (0x28, 'inverse'), (0x1C, 'vertical'))
    end = tuple(item for item in snapshots if item[0] >= 0x20)
    groups = (('start-xy', ((0x14, 'along'), (0x18, 'sine'))),
            ('end', tuple(item for item in snapshots if item[0] >= 0x20)),
            ('end-start-x', end + ((0x14, 'along'),)),
            ('end-start-y', end + ((0x18, 'sine'),)),
            ('end-start-z', end + ((0x1C, 'vertical'),)),
            ('end-start-xy', end + ((0x14, 'along'), (0x18, 'sine'))),
            ('end-start-yz', end + ((0x18, 'sine'), (0x1C, 'vertical'))),
            ('all', snapshots),
            ('all-angle-y', end + ((0x14, 'along'), (0x18, 'angle'), (0x1C, 'sine'))),
            ('all-radius-x', end + ((0x14, 'radius'), (0x18, 'angle'), (0x1C, 'sine'))))
    for label, selected in groups:
        body = member
        loads = []
        for offset, scalar in selected:
            access = '*(f32 *)(actor + 0x%X)' % offset
            body = body.replace(access, scalar)
            loads.append('    ' + scalar + ' = ' + access + ';')
        body = body.replace('    delta.x =', '\n'.join(loads) + '\n    delta.x =', 1)
        yield 'member-snapshot-' + label, body
        # When angle holds an endpoint, this variant is an effective collision control.
        threshold = body.replace('    delta.x =', '    angle = D_800AA3A0;\n    delta.x =', 1).replace(
            'D_800AA3A0 < fabsf', 'angle < fabsf')
        yield 'member-snapshot-' + label + '-threshold', threshold
        if label in ('end', 'all-angle-y'):
            for suffix, expression in (('divide-half', lambda field: 'delta.' + field + ' / 2.0f'),
                    ('cast-half', lambda field: '(f32)(delta.' + field + ' * 0.5)')):
                changed = body
                for field in ('x', 'y', 'z'):
                    changed = changed.replace('delta.' + field + ' * 0.5f', expression(field))
                yield 'member-snapshot-' + label + '-' + suffix, changed
    yield 'cast-private-y', ORIGINAL_BODY.replace('delta.y', '*(volatile f32 *)&delta.y')
    assignment = '    delta.y = *(f32 *)(actor + 0x24) - *(f32 *)(actor + 0x18);'
    yield 'cast-read-y', ORIGINAL_BODY.replace('delta.y * 0.5f', '*(volatile f32 *)&delta.y * 0.5f')
    yield 'cast-write-y', ORIGINAL_BODY.replace(assignment, assignment.replace('delta.y', '*(volatile f32 *)&delta.y'))
    array = ORIGINAL_BODY.replace('    OwnerRibbonPosition32C8 delta, midpoint;',
        '    f32 delta[3], midpoint[3];').replace('    volatile OwnerRibbonPosition32C8 first, last;',
        '    f32 first[3], last[3];')
    for vector in ('delta', 'midpoint', 'first', 'last'):
        for index, field in enumerate(('x', 'y', 'z')):
            array = array.replace(vector + '.' + field, vector + '[%d]' % index)
    yield 'array-coordinates', array
    prefix, calculation = array.split('    delta[0] =', 1)
    _, remaining = calculation.split('    if (', 1)
    initial = '''    for (axis = 0; axis < 3; axis++) {
        delta[axis] = *(f32 *)(actor + 0x20 + axis * 4) - *(f32 *)(actor + 0x14 + axis * 4);
    }
'''
    looped = (prefix + initial + '    if (' + remaining).replace('    s32 offset;', '    s32 offset, axis;')
    yield 'array-delta-loop', looped
    for name, body in (('array', array), ('array-delta', looped)):
        begin, rest = body.split('        midpoint[0] =', 1)
        _, tail = rest.split('        inverse =', 1)
        coordinates = '''        for (axis = 0; axis < 3; axis++) {
            midpoint[axis] = *(f32 *)(actor + 0x14 + axis * 4) + delta[axis] * 0.5f;
            first[axis] = *(f32 *)(actor + 0x14 + axis * 4) - midpoint[axis];
            last[axis] = *(f32 *)(actor + 0x20 + axis * 4) - midpoint[axis];
        }
'''
        result = begin + coordinates + '        inverse =' + tail
        if name == 'array':
            result = result.replace('    s32 offset;', '    s32 offset, axis;')
        yield name + '-coordinate-loop', result


SELECTED_NAME = 'member-snapshot-end'
SELECTED = dict(candidates())[SELECTED_NAME]


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None):
    with patch.object(base, 'TYPES', TYPES):
        return base.compile_candidate(root, out, name, body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Compile names containing this substring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-delta-y'
    rows = []
    for name, body in candidates():
        if args.only and args.only not in name:
            continue
        meta, _ = compile_candidate(root, out, name, body)
        rows.append(meta)
        print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    if not rows:
        parser.error('no matching candidate names')
    (out / ('measurements-' + (args.only or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
