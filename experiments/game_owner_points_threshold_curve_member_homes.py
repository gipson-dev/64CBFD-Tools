"""Fit typed private vector members without address-cast pointer capture."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_vectors as previous
from tools.experiments.game_owner_points_arc_lifetimes import stage_reuse

base = previous.base
MEMBER_TYPE = 'typedef struct { volatile f32 x, y, z; } OwnerCurveMemberHome;\n'
TYPES = previous.TYPES + MEMBER_TYPE


def candidates():
    seeds = dict(previous.cached_candidates())
    for schema, records, private, projected in itertools.product(('whole', 'member'), (False, True),
            ((), ('threshold', 'quarter'), ('radius', 'minorRadius'),
             ('threshold', 'quarter', 'radius', 'minorRadius')), (False, True)):
        label = 'cached-' + ('-'.join(private) or 'register') + ('-projected' if projected else '')
        body = seeds[label]
        if schema == 'member':
            body = body.replace('volatile OwnerRibbonPosition32C8 midpoint;', 'OwnerCurveMemberHome midpoint;').replace(
                'volatile OwnerRibbonPosition32C8 first, last;', 'OwnerCurveMemberHome first, last;')
        if records:
            body = stage_reuse(body, dict(along='sample.x', across='sample.y', h='point.x', v='point.y'))
            body = body.replace('    s32 offset;',
                '    OwnerRibbonPosition32C8 sample, point;\n    s32 offset;')
        yield schema + ('-loop-records-' if records else '-scalars-') + ('-'.join(private) or 'register') + (
            '-projected' if projected else ''), body


def control_candidates():
    seeds = dict(previous.home_candidates())
    for private, member_projection, root_copy, counter in itertools.product(((), ('threshold', 'quarter')),
            (False, True), (False, True), ('up', 'down', 'negative')):
        name = 'read-homes-' + ('-'.join(private) or 'register') + '-inverse-y'
        body = seeds[name + '-private-projection']
        if member_projection:
            body = body.replace('    OwnerRibbonPosition32C8 normal, projected, direction;',
                '    OwnerRibbonPosition32C8 normal, direction;\n    OwnerCurveProjected projected;').replace(
                '*(volatile f32 *)&projected.x =', 'projected.x =')
        if root_copy:
            body = body.replace('    s32 offset;', '    volatile f32 rootSquared;\n    s32 offset;').replace(
                '        length = sqrtf(squared);', '        rootSquared = squared;\n        length = sqrtf(rootSquared);')
        if counter == 'down':
            body = body.replace('for (offset = 0; offset != 0xF0; offset += 0x18)',
                'for (offset = 0xF0; offset != 0; offset -= 0x18)')
        elif counter == 'negative':
            body = body.replace('for (offset = 0; offset != 0xF0; offset += 0x18)',
                'for (offset = -0xF0; offset != 0; offset += 0x18)')
        yield 'control-' + ('-'.join(private) or 'register') + ('-member' if member_projection else '-cast') + (
            '-root-copy' if root_copy else '') + '-' + counter, body


def direct_root_candidates():
    for name, body in control_candidates():
        if name not in ('control-register-cast-root-copy-down', 'control-register-cast-root-copy-negative'):
            continue
        yield name + '-direct-root', body.replace('length = sqrtf(rootSquared);',
            '(void)&rootSquared;\n        length = sqrtf(squared);')


SELECTED_NAME = 'control-register-cast-root-copy-down-direct-root'
SELECTED = dict(direct_root_candidates())[SELECTED_NAME]


def negative_candidates():
    with patch.object(previous, 'SELECTED', SELECTED):
        yield from previous.negative_candidates()
    yield 'negative-private-relative-home-swap', SELECTED.replace('midpoint, first, last;', 'midpoint, last, first;')


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None, entry=base.ENTRY):
    with patch.object(previous, 'TYPES', TYPES):
        return previous.compile_candidate(root, out, name, body, profile, symbols, entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-member-homes'
    rows = []
    for name, body in itertools.chain(candidates(), control_candidates(), direct_root_candidates()):
        if args.only not in name:
            continue
        meta, _ = compile_candidate(root, out, name, body)
        rows.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    if not rows:
        parser.error('no selected candidates')
    (out / ('measurements-' + (args.only or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
