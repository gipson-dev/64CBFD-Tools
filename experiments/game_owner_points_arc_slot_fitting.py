"""Fit complete arc Z-delta lifetimes without changing private homes or extent gates."""
import argparse
import json
import re
from pathlib import Path

from tools.experiments import game_owner_points_arc_endpoint_reads as previous

base = previous.base
TYPES = previous.TYPES
DELTA_TYPE = previous.DELTA_TYPE


def delta_z_alias(body, scalar, copy=False):
    prefix, suffix = body.split('        angle = func_150484A0', 1)
    initial, rest = prefix.split('    if (', 1)
    if re.search(r'^\s*' + scalar + r'\s*=', initial, re.MULTILINE):
        raise ValueError('live endpoint snapshot would be overwritten: ' + scalar)
    if copy:
        initial = initial.rstrip() + '\n    ' + scalar + ' = delta.z;\n'
        prefix = initial + '    if (' + rest.replace('delta.z', scalar)
    else:
        prefix = prefix.replace('delta.z', scalar)
    return prefix + '        angle = func_150484A0' + suffix


def candidates():
    seeds = dict(previous.candidates())
    yield 'retained-six-reads', previous.SELECTED
    combinations = (
        ('stage-retail-reuse-axis', 'radius'),
        ('stage-retail-reuse-grouped', 'radius'),
        ('stage-short-along-retail-reuse-axis', 'angle'),
        ('stage-short-along-retail-reuse-axis', 'radius'),
        ('stage-short-along-retail-reuse-grouped', 'angle'),
        ('stage-short-along-retail-reuse-grouped', 'radius'),
    )
    for name, scalar in combinations:
        for copy in (False, True):
            yield name + '-z-' + scalar + ('-copy' if copy else '-reuse'), delta_z_alias(seeds[name], scalar, copy)
    condition = 'D_800AA3A0 < fabsf(delta.x) || D_800AA3A0 < fabsf(delta.z)'
    prefix, block = previous.SELECTED.split('    if (' + condition + ') {', 1)
    work, ending = block.rsplit('    }\n    return 1;', 1)
    flat = '\n'.join(line[4:] if line.startswith('        ') else line for line in work.splitlines())
    yield 'condition-early-return', prefix + '    if (!(' + condition + ')) return 1;' + flat + '\n    return 1;' + ending
    gotos = '''    if (D_800AA3A0 < fabsf(delta.x)) goto active;
    if (D_800AA3A0 < fabsf(delta.z)) goto active;
    return 1;
active:
'''
    yield 'condition-goto-active', prefix + gotos + flat.lstrip('\n') + '\n    return 1;' + ending
    yield 'condition-z-first', previous.SELECTED.replace(condition,
        'D_800AA3A0 < fabsf(delta.z) || D_800AA3A0 < fabsf(delta.x)')
    yield 'condition-boolean', previous.SELECTED.replace('    s32 offset;', '    s32 offset, active;').replace(
        '    if (' + condition + ') {', '    active = ' + condition + ';\n    if (active) {')
    yield 'condition-precomputed-abs-z', previous.SELECTED.replace('    if (' + condition + ') {',
        '    radius = fabsf(delta.z);\n    if (D_800AA3A0 < fabsf(delta.x) || D_800AA3A0 < radius) {')
    counter = previous.SELECTED.replace('        cursor =',
        '        offset = 0;\n        cursor =', 1).replace('for (offset = 0;', 'for (;')
    yield 'counter-first', counter
    yield 'counter-for-angle', counter.replace('            angle += angleStep;\n', '').replace(
        'offset += 0x18) {', 'offset += 0x18, angle += angleStep) {')
    do = counter.replace('        for (; offset != 0xF0; offset += 0x18) {', '        do {').replace(
        '        }\n    }\n    return 1;', '        } while ((offset += 0x18) != 0xF0);\n    }\n    return 1;')
    yield 'counter-do', do
    yield 'counter-do-angle', do.replace('            angle += angleStep;\n', '').replace(
        'while ((offset += 0x18) != 0xF0)', 'while (offset += 0x18, angle += angleStep, offset != 0xF0)')
    advance = '            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);\n'
    indexed = previous.SELECTED.replace('            actor = (u8 *)cursor;',
        '            actor = (u8 *)cursor + offset;').replace(advance, '')
    yield 'cursor-indexed', indexed
    yield 'cursor-indexed-do', indexed.replace('        for (offset = 0; offset != 0xF0; offset += 0x18) {',
        '        offset = 0;\n        do {').replace('        }\n    }\n    return 1;',
        '        } while ((offset += 0x18) != 0xF0);\n    }\n    return 1;')
    records = previous.SELECTED.replace('OwnerRibbonPosition32C8 *cursor;',
        'OwnerPointRecord3A7C *cursor;').replace('cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);',
        'cursor = (OwnerPointRecord3A7C *)(actor + 0x48);').replace(advance, '')
    yield 'cursor-record-postincrement', records.replace('actor = (u8 *)cursor;', 'actor = (u8 *)cursor++;')
    yield 'cursor-record-late-increment', records.replace('            angle += angleStep;',
        '            angle += angleStep;\n            cursor++;')
    half = previous.SELECTED
    for field in 'xyz':
        half = half.replace('delta.' + field + ' * 0.5f', '0.5f * delta.' + field)
    yield 'half-commuted-multiply', half
    sums = previous.SELECTED
    for field, scalar in zip('xyz', ('along', 'angle', 'sine')):
        sums = sums.replace(scalar + ' + delta.' + field + ' * 0.5f',
            'delta.' + field + ' * 0.5f + ' + scalar)
    yield 'half-commuted-add', sums
    constant = previous.SELECTED.replace('    if (' + condition + ') {',
        '    inverse = 0.5f;\n    if (' + condition + ') {')
    for field in 'xyz':
        constant = constant.replace('delta.' + field + ' * 0.5f', 'delta.' + field + ' * inverse')
    yield 'half-stage-scalar', constant
    vector = previous.SEED.replace('volatile OwnerRibbonPosition32C8 first, last;',
        'OwnerRibbonPosition32C8 first, last;')
    loads = []
    for field, index in zip('xyz', range(3)):
        for name, offset in (('first', 0x14), ('last', 0x20)):
            access = '*(f32 *)(actor + 0x%X)' % (offset + index * 4)
            vector = vector.replace(access, name + '.' + field)
            loads.append('    ' + name + '.' + field + ' = ' + access + ';')
    vector = vector.replace('    delta.x =', '\n'.join(loads) + '\n    delta.x =', 1)
    yield 'vector-ordinary-inputs', vector
    prefix, tail = vector.split('        angleStep = (last.z', 1)
    reads = '        angleStep = (last.z' + tail
    for name in ('first', 'last'):
        reads = reads.replace(name + '.', '((volatile OwnerRibbonPosition32C8 *)&' + name + ')->')
    yield 'vector-read-offsets', prefix + reads
    offsets = prefix
    for name in ('first', 'last'):
        for field in 'xyz':
            offsets = offsets.replace('        ' + name + '.' + field + ' =',
                '        ((volatile OwnerRibbonPosition32C8 *)&' + name + ')->' + field + ' =')
    yield 'vector-write-offsets', offsets + '        angleStep = (last.z' + tail
    yield 'vector-volatile-offsets', offsets + reads
    copied = vector.replace('\n'.join(loads),
        '    first = ((OwnerPoints3A7C *)actor)->start;\n    last = ((OwnerPoints3A7C *)actor)->end;')
    yield 'vector-record-copy', copied
    yield 'vector-record-copy-read-offsets', (prefix + reads).replace('\n'.join(loads),
        '    first = ((OwnerPoints3A7C *)actor)->start;\n    last = ((OwnerPoints3A7C *)actor)->end;')


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None):
    return previous.compile_candidate(root, out, name, body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Compile names containing this substring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-slot-fitting'
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
