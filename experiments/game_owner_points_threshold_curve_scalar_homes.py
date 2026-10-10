"""Fit actual curve scalar lifetimes without discarding qualified vector homes."""
import argparse
import itertools
import json
from pathlib import Path

from tools.experiments import game_owner_points_threshold_curve_member_homes as previous
from tools.experiments.game_owner_points_arc_lifetimes import register_locals, stage_reuse
from unittest.mock import patch

base = previous.base
PAIR_TYPE = 'typedef struct { volatile f32 threshold, quarter; } OwnerCurveLimits;\n'
TYPES = previous.TYPES + PAIR_TYPE


def candidates():
    for projection, delta, private, epsilon in itertools.product(('cast', 'member'),
            ('record', 'scalars'), ((), ('threshold', 'quarter')), (False, True)):
        body = previous.SELECTED
        if projection == 'member':
            body = body.replace('    OwnerRibbonPosition32C8 normal, projected, direction;',
                '    OwnerRibbonPosition32C8 normal;\n    OwnerCurveProjected projected;\n'
                '    OwnerRibbonPosition32C8 direction;').replace(
                '*(volatile f32 *)&projected.x =', 'projected.x =')
        if delta == 'scalars':
            body = body.replace('    f32 epsilon, inverse;', '    f32 epsilon, inverse, dx, dz;').replace(
                'delta.x', 'dx').replace('delta.z', 'dz')
        body = previous.previous.previous.private_scalars(body, private)
        if epsilon:
            body = body.replace('epsilon = D_800AA3B0;', 'epsilon = *(volatile f32 *)&D_800AA3B0;')
        name = projection + '-' + delta + '-' + ('-'.join(private) or 'register') + (
            '-early-epsilon' if epsilon else '')
        yield name, body


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None, entry=base.ENTRY):
    with patch.object(previous, 'TYPES', TYPES):
        return previous.compile_candidate(root, out, name, body, profile, symbols, entry)


def direct_member_candidates():
    for delta, private, counter, root_copy in itertools.product(('record', 'scalars'),
            ((), ('threshold', 'quarter')), ('up', 'down'), (False, True)):
        body = previous.SELECTED.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
            '    OwnerCurveMemberHome midpoint, first, last;').replace(
            '    OwnerRibbonPosition32C8 normal, projected, direction;',
            '    OwnerRibbonPosition32C8 normal;\n    OwnerCurveProjected projected;\n'
            '    OwnerRibbonPosition32C8 direction;').replace(
            '*(volatile f32 *)&projected.x =', 'projected.x =')
        for vector in ('first', 'last', 'midpoint'):
            body = body.replace('((volatile OwnerRibbonPosition32C8 *)&' + vector + ')->', vector + '.')
        for axis, scalar in zip('xyz', ('h', 'v', 'across')):
            assignment = '        midpoint.' + axis + ' = '
            start = body.index(assignment)
            end = body.index(';', start) + 1
            line = body[start:end]
            body = body[:start] + line.replace('midpoint.' + axis, scalar) + '\n' + (
                '        midpoint.' + axis + ' = ' + scalar + ';') + body[end:]
            body = body.replace('- midpoint.' + axis, '- ' + scalar)
        if delta == 'scalars':
            body = body.replace('    f32 epsilon, inverse;', '    f32 epsilon, inverse, dx, dz;').replace(
                'delta.x', 'dx').replace('delta.z', 'dz')
        if counter == 'up':
            body = body.replace('for (offset = 0xF0; offset != 0; offset -= 0x18)',
                'for (offset = 0; offset != 0xF0; offset += 0x18)')
        if not root_copy:
            body = body.replace('    volatile f32 rootSquared;\n', '').replace(
                '        rootSquared = squared;\n        (void)&rootSquared;\n', '')
        body = previous.previous.previous.private_scalars(body, private)
        yield 'direct-' + delta + '-' + ('-'.join(private) or 'register') + '-' + counter + (
            '-root-copy' if root_copy else ''), body


def limit_candidates():
    for position, snapshot, registers, counter in itertools.product(('before-root', 'after-root'),
            (False, True), (False, True), ('up', 'down')):
        body = previous.SELECTED
        declaration = '    OwnerCurveLimits limits;\n'
        anchor = '    volatile f32 rootSquared;\n'
        body = body.replace(anchor, declaration + anchor if position == 'before-root' else anchor + declaration)
        body = body.replace('threshold = *(f32 *)(actor + 0x138);',
            'limits.threshold = *(f32 *)(actor + 0x138);').replace('quarter = squared * 0.25f;',
            'limits.quarter = squared * 0.25f;')
        if snapshot:
            body = body.replace('        if (threshold < quarter)',
                '        length = limits.threshold;\n        squared = limits.quarter;\n'
                '        threshold = limits.threshold;\n        quarter = limits.quarter;\n'
                '        if (length < squared)')
        else:
            body = body.replace('        if (threshold < quarter)',
                '        threshold = limits.threshold;\n        quarter = limits.quarter;\n'
                '        if (threshold < quarter)')
        if registers:
            body = register_locals(body)
        if counter == 'up':
            body = body.replace('for (offset = 0xF0; offset != 0; offset -= 0x18)',
                'for (offset = 0; offset != 0xF0; offset += 0x18)')
        yield 'limits-' + position + ('-snapshot' if snapshot else '-single') + (
            '-registers' if registers else '') + '-' + counter, body


def lifetime_candidates():
    seed = dict(limit_candidates())['limits-after-root-snapshot-down']
    for endpoints, delta, vertical, reads in itertools.product((False, True), repeat=4):
        body = seed
        if endpoints:
            body = stage_reuse(body, dict(x1='normal.z', y1='normal.x'))
        if delta:
            body = body.replace('delta.x', 'angle').replace('delta.z', 'sine')
        if vertical:
            body = body.replace('projected.y', 'v')
        if reads:
            body = body.replace('        length = limits.threshold;\n        squared = limits.quarter;\n'
                '        threshold = limits.threshold;\n        quarter = limits.quarter;\n'
                '        if (length < squared)',
                '        threshold = limits.threshold;\n        quarter = limits.quarter;\n'
                '        length = limits.threshold;\n        squared = limits.quarter;\n'
                '        if (threshold < quarter)').replace('sqrtf(threshold - quarter)', 'sqrtf(length - squared)')
        yield 'lifetime-' + '-'.join(name for name, enabled in zip(
            ('endpoints', 'delta', 'vertical', 'reads'), (endpoints, delta, vertical, reads)) if enabled) + (
                'baseline' if not any((endpoints, delta, vertical, reads)) else ''), body


def gate_candidates():
    seed = dict(lifetime_candidates())['lifetime-vertical']
    for distinct, early in itertools.product((False, True), repeat=2):
        if not distinct and not early:
            continue
        body = seed
        if distinct:
            body = body.replace('    s32 offset;', '    f32 gateThreshold, gateQuarter;\n    s32 offset;').replace(
                '        length = limits.threshold;', '        gateThreshold = limits.threshold;').replace(
                '        squared = limits.quarter;', '        gateQuarter = limits.quarter;').replace(
                'if (length < squared)', 'if (gateThreshold < gateQuarter)')
        if early:
            body = body.replace('        quarter = limits.quarter;\n',
                '        quarter = limits.quarter;\n        minorRadius = threshold - quarter;\n').replace(
                'minorRadius = sqrtf(threshold - quarter);', 'minorRadius = sqrtf(minorRadius);')
        yield 'gate-' + ('distinct' if distinct else 'reused') + ('-early-difference' if early else ''), body


SELECTED_NAME = 'lifetime-vertical'
SELECTED = dict(lifetime_candidates())[SELECTED_NAME]


def negative_candidates():
    with patch.object(previous, 'SELECTED', SELECTED):
        yield from previous.negative_candidates()
    yield 'negative-private-single-limit-reads', SELECTED.replace(
        '        threshold = limits.threshold;\n        quarter = limits.quarter;',
        '        threshold = length;\n        quarter = squared;')
    yield 'negative-private-swapped-limit-homes', SELECTED.replace('limits.threshold', 'limits.swap').replace(
        'limits.quarter', 'limits.threshold').replace('limits.swap', 'limits.quarter')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-scalar-homes'
    rows = []
    if args.profiles:
        for name, body in (('slot-vector', previous.SELECTED), ('scalar-homes', SELECTED)):
            for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
                meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
                rows.append(meta)
                print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
        (out / 'profiles.json').write_text(json.dumps(rows, indent=2) + '\n')
        return
    for name, body in itertools.chain(candidates(), direct_member_candidates(), limit_candidates(), lifetime_candidates(), gate_candidates()):
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
