"""Measure meaningful curve vector records and the unconditional delta-Y read."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_workspace as previous
from tools.experiments.game_owner_points_arc_lifetimes import stage_reuse

base = previous.base
TYPES = previous.TYPES
PROJECTED_TYPE = 'typedef struct { volatile f32 x; f32 y, z; } OwnerCurveProjected;\n'


def vector_body(representation, reuse, private):
    body = previous.workspace(previous.SEED, representation)
    body = body.replace('    OwnerArcDeltaY delta;\n', '').replace(
        's32 func_151B3FDC(u8 *actor) {\n', 's32 func_151B3FDC(u8 *actor) {\n    OwnerArcDeltaY delta;\n')
    body = stage_reuse(body, dict(nx='normal.x', nz='normal.z', projection='projected.x',
        vertical='projected.y', horizontal='direction.x', upright='direction.y'))
    body = body.replace('    f32 x0, y0, z0, x1, y1, z1;',
        '    OwnerRibbonPosition32C8 normal, projected, direction;\n    f32 x0, y0, z0, x1, y1, z1;')
    if reuse:
        body = stage_reuse(body, dict(x1='normal.z', y1='normal.x', z1='length',
            x0='along', y0='angle', z0='sine'))
    body = previous.private_scalars(body, private)
    body = body.replace('    delta.z =', '    inverse = delta.y;\n    delta.z =', 1).replace(
        'midpoint.y = y0 + delta.y * 0.5f;', 'midpoint.y = y0 + inverse * 0.5f;').replace(
        'midpoint.y = angle + delta.y * 0.5f;', 'midpoint.y = angle + inverse * 0.5f;')
    return body


def candidates():
    for representation, reuse, private in itertools.product(('ordinary', 'relative'), (False, True),
            ((), ('threshold', 'quarter'), ('radius', 'minorRadius'),
             ('threshold', 'quarter', 'radius', 'minorRadius'))):
        name = representation + ('-reuse-' if reuse else '-snapshot-') + ('-'.join(private) or 'register')
        body = vector_body(representation, reuse, private)
        yield name, body
        yield name + '-early-epsilon', body.replace('epsilon = D_800AA3B0;',
            'epsilon = *(volatile f32 *)&D_800AA3B0;')


def home_candidates():
    for private, cache in itertools.product(((), ('threshold', 'quarter'),
            ('radius', 'minorRadius'), ('threshold', 'quarter', 'radius', 'minorRadius')), (False, True)):
        seed = vector_body('ordinary', False, private)
        setup, reads = seed.split('        projected.x =', 1)
        for vector in ('first', 'last'):
            reads = reads.replace(vector + '.', '((volatile OwnerRibbonPosition32C8 *)&' + vector + ')->')
        seed = setup + '        projected.x =' + reads
        setup, loop = seed.split('        for (offset', 1)
        for axis in 'xyz':
            loop = loop.replace('midpoint.' + axis, '((volatile OwnerRibbonPosition32C8 *)&midpoint)->' + axis)
        body = setup + '        for (offset' + loop
        if cache:
            body = body.replace('    inverse = delta.y;', '    squared = delta.y;').replace(
                'midpoint.y = y0 + inverse * 0.5f;', 'midpoint.y = y0 + squared * 0.5f;')
        label = 'read-homes-' + ('-'.join(private) or 'register') + ('-squared-y' if cache else '-inverse-y')
        yield label, body
        register = body.replace('    OwnerRibbonPosition32C8 normal, projected, direction;',
            '    register OwnerRibbonPosition32C8 normal, projected, direction;')
        yield label + '-register-vectors', register
        # This member is spilled in retail before its second normalization.
        projected = body.replace('        projected.x =', '        *(volatile f32 *)&projected.x =', 1)
        yield label + '-private-projection', projected


def cached_candidates():
    for private, projected, cursor in itertools.product(((), ('threshold', 'quarter'),
            ('radius', 'minorRadius'), ('threshold', 'quarter', 'radius', 'minorRadius')), (False, True), (False, True)):
        body = vector_body('relative', False, private)
        body = body.replace('    OwnerRibbonPosition32C8 midpoint;', '    volatile OwnerRibbonPosition32C8 midpoint;')
        setup, remaining = body.split('        normal.z =', 1)
        for axis, scalar in zip('xyz', ('h', 'v', 'across')):
            assignment = '        midpoint.' + axis + ' = '
            start = setup.index(assignment)
            end = setup.index(';', start) + 1
            line = setup[start:end]
            setup = setup[:start] + line.replace('midpoint.' + axis, scalar) + '\n' + (
                '        midpoint.' + axis + ' = ' + scalar + ';') + setup[end:]
            setup = setup.replace('- midpoint.' + axis, '- ' + scalar)
        body = setup + '        normal.z =' + remaining
        if projected:
            body = body.replace('    OwnerRibbonPosition32C8 normal, projected, direction;',
                '    OwnerRibbonPosition32C8 normal, direction;\n    OwnerCurveProjected projected;')
        if cursor:
            body = body.replace('            sine = sinf(angle);',
                '            actor = (u8 *)cursor;\n            sine = sinf(angle);').replace(
                'cursor->', '((OwnerRibbonPosition32C8 *)actor)->')
        yield 'cached-' + ('-'.join(private) or 'register') + ('-projected' if projected else '') + ('-cursor' if cursor else ''), body


SELECTED_NAME = 'ordinary-snapshot-register'
SELECTED = dict(candidates())[SELECTED_NAME]


def negative_candidates():
    with patch.object(base, 'SELECTED', SELECTED):
        for name, body in base.candidates():
            if not name.startswith('negative-'):
                continue
            if name == 'negative-plus-upright':
                body = SELECTED.replace('v = along * direction.y - across * direction.x;',
                    'v = along * direction.y + across * direction.x;')
            if body == SELECTED:
                raise ValueError('ineffective negative source: ' + name)
            yield name, body
    yield 'negative-private-no-work-y-read', SELECTED.replace('    inverse = delta.y;\n', '').replace(
        'midpoint.y = y0 + inverse * 0.5f;', 'midpoint.y = y0 + delta.y * 0.5f;')


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None, entry=base.ENTRY):
    with patch.object(previous, 'TYPES', TYPES + PROJECTED_TYPE):
        return previous.compile_candidate(root, out, name, body, profile, symbols, entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-vectors'
    rows = []
    for name, body in itertools.chain(candidates(), home_candidates(), cached_candidates()):
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
