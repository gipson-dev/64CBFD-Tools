"""Fit complete endpoint snapshots against retail arc input reads and FP lifetimes."""
import argparse
import itertools
import json
from pathlib import Path

from tools.experiments import game_owner_points_arc_delta_y as previous

base = previous.base
TYPES = previous.TYPES
DELTA_TYPE = previous.DELTA_TYPE
SEED = dict(previous.candidates())['member-private-y']


def snapshots(body, start, end, order='paired'):
    selected = dict(zip(range(0x14, 0x20, 4), start))
    selected.update(zip(range(0x20, 0x2C, 4), end))
    for offset, scalar in selected.items():
        body = body.replace('*(f32 *)(actor + 0x%X)' % offset, scalar)
    orderings = {
        'paired': (0x20, 0x14, 0x24, 0x18, 0x28, 0x1C),
        'end-first': (0x20, 0x24, 0x28, 0x14, 0x18, 0x1C),
        'start-first': (0x14, 0x18, 0x1C, 0x20, 0x24, 0x28),
    }
    loads = ['    %s = *(f32 *)(actor + 0x%X);' % (selected[offset], offset)
        for offset in orderings[order]]
    return body.replace('    delta.x =', '\n'.join(loads) + '\n    delta.x =', 1)


def ordered_work(body, order):
    prefix, work = body.split('        midpoint.x =', 1)
    calculations, suffix = ('        midpoint.x =' + work).split('        inverse =', 1)
    statements = {line.strip().split(' =')[0]: line for line in calculations.splitlines() if line.strip()}
    return prefix + '\n'.join(statements[key] for key in order) + '\n        inverse =' + suffix


def candidates():
    orders = {
        'grouped': tuple(vector + '.' + axis for vector in ('midpoint', 'first', 'last') for axis in 'xyz'),
        'axis': tuple(vector + '.' + axis for axis in 'xyz' for vector in ('midpoint', 'first', 'last')),
        'retail': ('midpoint.x', 'midpoint.y', 'midpoint.z', 'first.x', 'last.x', 'first.z',
            'last.y', 'first.y', 'last.z'),
    }
    starts = (
        ('dedicated', ('startX', 'startY', 'startZ')),
        ('stage', ('along', 'angle', 'sine')),
        ('stage-radius', ('radius', 'angle', 'sine')),
        ('stage-short', ('inverse', 'vertical', 'sine')),
        ('stage-short-angle', ('inverse', 'vertical', 'angle')),
        ('stage-short-step', ('inverse', 'sine', 'vertical')),
        ('stage-short-along', ('inverse', 'along', 'sine')),
    )
    ends = (
        ('retail-reuse', ('nz', 'nx', 'angleStep')),
        ('previous-reuse', ('nx', 'nz', 'inverse')),
        ('dedicated', ('endX', 'endY', 'endZ')),
    )
    for (start_name, start), (end_name, end), (order_name, order) in itertools.product(
            starts, ends, orders.items()):
        if set(start) & set(end) or (start_name.startswith('stage-short') and end_name != 'retail-reuse'):
            continue
        seed = SEED
        added = [name for name in (*start, *end) if name.startswith(('start', 'end'))]
        if added:
            seed = seed.replace('    f32 inverse, nx, nz;',
                '    f32 ' + ', '.join(added) + ';\n    f32 inverse, nx, nz;')
        body = ordered_work(snapshots(seed, start, end), order)
        label = start_name + '-' + end_name + '-' + order_name
        yield label, body
        if start_name == 'dedicated' and end_name == 'retail-reuse':
            for load_order in ('end-first', 'start-first'):
                yield label + '-' + load_order, ordered_work(snapshots(seed, start, end, load_order), order)
        if start_name == 'dedicated':
            registered = body.replace('    f32 startX, startY, startZ;',
                '    register f32 startX, startY, startZ;')
            if end_name == 'dedicated':
                registered = body.replace('    f32 startX, startY, startZ, endX, endY, endZ;',
                    '    register f32 startX, startY, startZ, endX, endY, endZ;')
            yield label + '-register', registered
    for label, seed in (('previous-end-snapshots', previous.SELECTED),
            ('stage-grouped', ordered_work(snapshots(SEED, ('along', 'angle', 'sine'),
                ('nz', 'nx', 'angleStep')), orders['grouped'])),
            ('stage-axis', ordered_work(snapshots(SEED, ('along', 'angle', 'sine'),
                ('nz', 'nx', 'angleStep')), orders['axis'])),
            ('stage-retail', ordered_work(snapshots(SEED, ('along', 'angle', 'sine'),
                ('nz', 'nx', 'angleStep')), orders['retail']))):
        ordinary = seed.replace('volatile OwnerRibbonPosition32C8 first, last;',
            'OwnerRibbonPosition32C8 first, last;')
        prefix, tail = ordinary.split('        angleStep = (last.z', 1)
        reads = '        angleStep = (last.z' + tail
        for vector in ('last', 'first'):
            reads = reads.replace(vector + '.', '((volatile OwnerRibbonPosition32C8 *)&' + vector + ')->')
        yield 'read-workspace-' + label, prefix + reads
        yield 'ordinary-workspace-' + label, ordinary


SELECTED_NAME = 'stage-retail-reuse-axis'
SELECTED = dict(candidates())[SELECTED_NAME]


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None):
    return previous.compile_candidate(root, out, name, body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Compile names containing this substring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-endpoint-reads'
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
