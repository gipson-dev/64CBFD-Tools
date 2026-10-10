"""Fit complete threshold-curve workspace and non-overlapping value lifetimes."""
import argparse
import itertools
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_candidates as base
from tools.experiments.game_owner_points_arc_delta_y import DELTA_TYPE
from tools.experiments.game_owner_points_arc_lifetimes import stage_reuse

TYPES = base.TYPES + DELTA_TYPE
SEED = base.SELECTED


def workspace(body, representation):
    body = body.replace('    f32 epsilon, dx, dy, dz, inverse, nx, nz;',
        '    OwnerArcDeltaY delta;\n    f32 epsilon, inverse, nx, nz;')
    for scalar, field in (('dx', 'x'), ('dy', 'y'), ('dz', 'z')):
        body = re.sub(r'\b' + scalar + r'\b', 'delta.' + field, body)
    if representation == 'relative':
        body = body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
            '    OwnerRibbonPosition32C8 midpoint;\n    volatile OwnerRibbonPosition32C8 first, last;')
    elif representation == 'all':
        body = body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
            '    volatile OwnerRibbonPosition32C8 midpoint, first, last;')
    elif representation != 'ordinary':
        raise ValueError(representation)
    return body


def private_scalars(body, names):
    for name in names:
        def declaration(match):
            fields = match[1].split(', ')
            if name not in fields:
                return match[0]
            fields.remove(name)
            return ('    f32 ' + ', '.join(fields) + ';\n' if fields else '') + '    volatile f32 ' + name + ';'
        body = re.sub(r'^    f32 ([a-zA-Z0-9_, ]+);', declaration, body, flags=re.MULTILINE)
    return body


def coordinate_order(body, order):
    prefix, rest = body.split('        midpoint.x =', 1)
    work, suffix = ('        midpoint.x =' + rest).split('        inverse =', 1)
    statements = {line.strip().split(' =')[0]: line for line in work.splitlines() if line.strip()}
    keys = tuple(vector + '.' + axis for axis in 'xyz' for vector in ('midpoint', 'first', 'last'))
    if order == 'grouped':
        keys = tuple(vector + '.' + axis for vector in ('midpoint', 'first', 'last') for axis in 'xyz')
    return prefix + '\n'.join(statements[key] for key in keys) + '\n        inverse =' + suffix


def candidates():
    storage = ((), ('threshold', 'quarter'), ('radius', 'minorRadius'),
        ('threshold', 'quarter', 'radius', 'minorRadius'))
    for representation, reuse, private in itertools.product(('ordinary', 'relative', 'all'), (False, True), storage):
        body = workspace(SEED, representation)
        if reuse:
            body = stage_reuse(body, dict(x1='nz', y1='nx', z1='sine', x0='along', y0='angle', z0='across'))
        body = private_scalars(body, private)
        name = representation + ('-reuse' if reuse else '-snapshot') + '-' + ('-'.join(private) or 'register')
        yield name, body
        yield name + '-axis-cursor', coordinate_order(body, 'axis').replace(
            '            sine = sinf(angle);', '            actor = (u8 *)cursor;\n            sine = sinf(angle);').replace(
            'cursor->', '((OwnerRibbonPosition32C8 *)actor)->')


def endpoint_candidates():
    compact = SEED.replace('    f32 x0, y0, z0, x1, y1, z1;\n', '')
    for name, offset in (('x0', 0x14), ('y0', 0x18), ('z0', 0x1C), ('x1', 0x20), ('y1', 0x24), ('z1', 0x28)):
        compact = compact.replace('    %s = *(f32 *)(actor + 0x%X);\n' % (name, offset), '')
        compact = re.sub(r'\b' + name + r'\b', '*(f32 *)(actor + 0x%X)' % offset, compact)
    for representation, private, cursor in itertools.product(('ordinary', 'relative'),
            (('threshold', 'quarter'), ('threshold', 'quarter', 'radius', 'minorRadius'),
             ('projection', 'threshold', 'quarter', 'radius', 'minorRadius'),
             ('squared', 'projection', 'threshold', 'quarter', 'radius', 'minorRadius')), (False, True)):
        body = private_scalars(workspace(compact, representation), private)
        if cursor:
            body = body.replace('            sine = sinf(angle);',
                '            actor = (u8 *)cursor;\n            sine = sinf(angle);').replace(
                'cursor->', '((OwnerRibbonPosition32C8 *)actor)->')
        yield 'compact-' + representation + '-' + '-'.join(private) + ('-cursor' if cursor else ''), body


def delta_first_candidates():
    for representation, private in itertools.product(('ordinary', 'relative'),
            ((), ('threshold', 'quarter'), ('radius', 'minorRadius'),
             ('threshold', 'quarter', 'radius', 'minorRadius'),
             ('projection', 'threshold', 'quarter', 'radius', 'minorRadius'),
             ('squared', 'projection', 'threshold', 'quarter', 'radius', 'minorRadius'))):
        body = private_scalars(workspace(SEED, representation), private)
        body = body.replace('    OwnerArcDeltaY delta;\n', '').replace(
            's32 func_151B3FDC(u8 *actor) {\n', 's32 func_151B3FDC(u8 *actor) {\n    OwnerArcDeltaY delta;\n')
        yield 'delta-first-' + representation + '-' + ('-'.join(private) or 'register'), body


SELECTED_NAME = 'delta-first-ordinary-radius-minorRadius'
SELECTED = dict(delta_first_candidates())[SELECTED_NAME]


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None, entry=base.ENTRY):
    with patch.object(base, 'TYPES', TYPES):
        return base.compile_candidate(root, out, name, body, profile, symbols, entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-threshold-workspace'
    rows = []
    for name, body in itertools.chain(candidates(), endpoint_candidates(), delta_first_candidates()):
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
