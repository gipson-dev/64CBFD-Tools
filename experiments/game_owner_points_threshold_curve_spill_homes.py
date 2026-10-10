"""Recover real squared-length and endpoint/radius spill homes with complete C."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_scalar_homes as previous
from tools.experiments.game_owner_points_threshold_curve_workspace import private_scalars
from tools.experiments.game_owner_points_arc_lifetimes import stage_reuse

base = previous.base
MEASURES_TYPE = 'typedef struct { volatile f32 squared, threshold, quarter; } OwnerCurveMeasures;\n'
SCRATCH_TYPE = 'typedef struct { volatile f32 endpointZ, squared, threshold, quarter; } OwnerCurveScratch;\n'
RADII_TYPE = 'typedef struct { volatile f32 squared, threshold, quarter, radius; } OwnerCurveRadiusMeasures;\n'
LATE_ENDPOINT_TYPE = 'typedef struct { volatile f32 squared, threshold, quarter, endpointZ; } OwnerCurveLateEndpointMeasures;\n'
TYPES = previous.TYPES + MEASURES_TYPE + SCRATCH_TYPE + RADII_TYPE + LATE_ENDPOINT_TYPE
PAIR_TYPE = LATE_ENDPOINT_TYPE


def candidates():
    for measures, endpoint, radii, copy in itertools.product((False, True), (False, True),
            ((), ('radius', 'minorRadius')), (False, True)):
        body = previous.SELECTED
        if measures:
            body = body.replace('    volatile f32 rootSquared;\n', '').replace(
                '    OwnerCurveLimits limits;', '    OwnerCurveMeasures limits;').replace(
                '        rootSquared = squared;\n        (void)&rootSquared;', '        limits.squared = squared;')
        names = radii + (('z1',) if endpoint else ())
        body = private_scalars(body, names)
        if copy:
            body = body.replace('        length = sqrtf(squared);',
                '        *(volatile f32 *)&squared = squared;\n        length = sqrtf(squared);')
        yield ('measures' if measures else 'separate') + ('-endpoint' if endpoint else '') + (
            '-radii' if radii else '') + ('-squared-home' if copy else ''), body


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None, entry=base.ENTRY):
    with patch.object(previous, 'TYPES', TYPES):
        return previous.compile_candidate(root, out, name, body, profile, symbols, entry)


def record_candidates():
    for schema, copy in itertools.product(('array', 'endpoint-record', 'late-endpoint-record', 'radius-record'), (False, True)):
        body = previous.SELECTED.replace('    volatile f32 rootSquared;\n', '').replace(
            '        rootSquared = squared;\n        (void)&rootSquared;', '        limits.squared = squared;')
        if schema == 'array':
            body = body.replace('    OwnerCurveLimits limits;', '    volatile f32 limits[3];')
            for index, field in enumerate(('squared', 'threshold', 'quarter')):
                body = body.replace('limits.' + field, 'limits[%d]' % index)
        elif schema in ('endpoint-record', 'late-endpoint-record'):
            record = 'OwnerCurveScratch' if schema == 'endpoint-record' else 'OwnerCurveLateEndpointMeasures'
            body = body.replace('    OwnerCurveLimits limits;', '    ' + record + ' limits;').replace(
                'z1 = *(f32 *)(actor + 0x28);', 'z1 = limits.endpointZ = *(f32 *)(actor + 0x28);').replace(
                'last.z = z1 - midpoint.z;', 'last.z = limits.endpointZ - midpoint.z;')
        else:
            body = body.replace('    OwnerCurveLimits limits;', '    OwnerCurveRadiusMeasures limits;')
            body = stage_reuse(body, dict(radius='limits.radius'))
        if copy:
            body = body.replace('        length = sqrtf(squared);',
                '        *(volatile f32 *)&squared = squared;\n        length = sqrtf(squared);')
        yield schema + ('-squared-home' if copy else ''), body


def lifetime_candidates():
    seed = dict(record_candidates())['late-endpoint-record']
    for endpoints, delta, snapshot in itertools.product((False, True), (False, True), ('inverse', 'squared')):
        body = seed
        if endpoints:
            body = stage_reuse(body, dict(x1='normal.z', y1='normal.x'))
        if delta:
            body = body.replace('delta.x', 'angle').replace('delta.z', 'sine')
        if snapshot == 'squared':
            body = body.replace('    inverse = delta.y;', '    squared = delta.y;').replace(
                'midpoint.y = y0 + inverse * 0.5f;', 'midpoint.y = y0 + squared * 0.5f;')
        yield 'late-' + ('endpoints-' if endpoints else '') + ('delta-' if delta else '') + snapshot, body


def midpoint_candidates():
    for seed, counter, cursor in itertools.product(('limits', 'endpoint'), ('up', 'down'), (False, True)):
        body = previous.SELECTED if seed == 'limits' else dict(record_candidates())['late-endpoint-record']
        body = body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
            '    OwnerCurveMemberHome midpoint;\n    OwnerRibbonPosition32C8 first, last;').replace(
            '((volatile OwnerRibbonPosition32C8 *)&midpoint)->', 'midpoint.')
        for axis, scalar in zip('xyz', ('h', 'v', 'across')):
            assignment = '        midpoint.' + axis + ' = '
            start = body.index(assignment)
            end = body.index(';', start) + 1
            line = body[start:end]
            body = body[:start] + line.replace('midpoint.' + axis, scalar) + '\n' + (
                '        midpoint.' + axis + ' = ' + scalar + ';') + body[end:]
            body = body.replace('- midpoint.' + axis, '- ' + scalar)
        if counter == 'up':
            body = body.replace('for (offset = 0xF0; offset != 0; offset -= 0x18)',
                'for (offset = 0; offset != 0xF0; offset += 0x18)')
        if cursor:
            body = body.replace('            sine = sinf(angle);', '            actor = (u8 *)cursor;\n            sine = sinf(angle);').replace(
                'cursor->', '((OwnerRibbonPosition32C8 *)actor)->')
        yield 'midpoint-' + seed + '-' + counter + ('-cursor' if cursor else ''), body


SELECTED_NAME = 'late-endpoint-record'
SELECTED = dict(record_candidates())[SELECTED_NAME]


def negative_candidates():
    with patch.object(previous, 'SELECTED', SELECTED):
        yield from previous.negative_candidates()
    yield 'negative-private-missing-square-copy', SELECTED.replace('        limits.squared = squared;\n', '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-spill-homes'
    rows = []
    for name, body in itertools.chain(candidates(), record_candidates(), lifetime_candidates(), midpoint_candidates()):
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
