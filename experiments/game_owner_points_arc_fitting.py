"""Full arc workspace, midpoint lifetime and IDO frame fitting."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_owner_points_arc_candidates as base


def workspace_body(body, volatile_names):
    names = ('midpoint', 'first', 'last')
    ordinary = [name for name in names if name not in volatile_names]
    explicit = [name for name in names if name in volatile_names]
    declaration = ''
    if ordinary:
        declaration += '    OwnerRibbonPosition32C8 ' + ', '.join(ordinary) + ';\n'
    if explicit:
        declaration += '    volatile OwnerRibbonPosition32C8 ' + ', '.join(explicit) + ';\n'
    return body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;\n', declaration)


def cached_midpoint(body):
    result = body.replace('    f32 dx, dy, dz;', '    f32 dx, dy, dz;\n    f32 mx, my, mz;')
    for field, scalar in zip(('x', 'y', 'z'), ('mx', 'my', 'mz')):
        assignment = '        midpoint.' + field + ' = '
        begin = result.index(assignment)
        end = result.index(';', begin) + 1
        statement = result[begin:end]
        result = result[:begin] + statement.replace('midpoint.' + field, scalar) + '\n' + (
            '        midpoint.' + field + ' = ' + scalar + ';') + result[end:]
        setup, loop = result.split('        point =', 1)
        setup = setup.replace('- midpoint.' + field, '- ' + scalar)
        result = setup + '        point =' + loop
    return result


def candidates():
    for names in (('midpoint',), ('first', 'last'), ('midpoint', 'first', 'last')):
        body = workspace_body(base.COMPACT, names)
        yield 'workspace-' + '-'.join(names), body
        yield 'cache-' + '-'.join(names), cached_midpoint(body)
    pointer = base.COMPACT.replace('    OwnerRibbonPosition32C8 *point;',
        '    OwnerRibbonPosition32C8 *point, *center;').replace(
        '        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);',
        '        center = &midpoint;\n        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);')
    setup, loop = pointer.split('        for (offset', 1)
    pointer = setup + '        for (offset' + loop.replace('midpoint.', 'center->')
    yield 'midpoint-pointer', pointer
    for name, body in (('pointer', pointer), ('workspace', workspace_body(base.COMPACT, ('first', 'last'))),
            ('cached', cached_midpoint(workspace_body(base.COMPACT, ('midpoint', 'first', 'last'))))):
        indexed = body.replace('        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);\n', '').replace(
            '        for (offset = 0; offset != 0xF0; offset += 0x18) {',
            '        for (offset = 0; offset != 0xF0; offset += 0x18) {\n'
            '            point = (OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);').replace(
            '            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);\n', '')
        yield name + '-indexed', indexed
        cursor = body.replace('OwnerRibbonPosition32C8 *point', 'OwnerRibbonPosition32C8 *cursor, *point').replace(
            '        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);',
            '        cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);').replace(
            '        for (offset = 0; offset != 0xF0; offset += 0x18) {',
            '        for (offset = 0; offset != 0xF0; offset += 0x18) {\n            point = cursor;').replace(
            '            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);',
            '            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);')
        yield name + '-cursor', cursor
        for suffix, statement in (('projection', '        projection ='), ('vertical', '        vertical =')):
            scoped = indexed.replace('    f32 projection, vertical, angle, radius, angleStep;',
                '    f32 projection, vertical;').replace('    f32 sine, along;\n', '')
            scoped = scoped.replace(statement, '        {\n        f32 angle, radius, angleStep, sine, along;\n' + statement, 1)
            scoped = scoped.replace('    }\n    return 1;', '        }\n    }\n    return 1;')
            yield name + '-scope-' + suffix, scoped
        points = indexed.replace('    OwnerRibbonPosition32C8 *point, *center;',
            '    OwnerRibbonPosition32C8 *point, *center, *relative;')
        if points != indexed:
            points = points.replace('        projection = (last.z * nz + last.x * nx) - (first.z * nz + first.x * nx);',
                '        relative = &last;\n        projection = relative->z * nz + relative->x * nx;\n'
                '        relative = &first;\n        projection -= relative->z * nz + relative->x * nx;')
            yield name + '-relative-pointer', points
    for name, body in list(base.candidates())[:4]:
        yield 'prior-' + name, body
    snapshot = base.SELECTED.replace('    f32 sine, cosine, along;', '    f32 sine, along;').replace(
        '            cosine = cosf(angle);\n            along = radius * cosine;',
        '            along = radius * cosf(angle);')
    for names in ((), ('midpoint',), ('first', 'last'), ('midpoint', 'first', 'last')):
        body = workspace_body(snapshot, names)
        label = 'snapshot-' + ('-'.join(names) or 'ordinary')
        yield label, body
        for order in (('last', 'first', 'midpoint'), ('last', 'midpoint', 'first')):
            if names:
                continue
            reordered = body.replace('midpoint, first, last;', ', '.join(order) + ';')
            yield label + '-' + '-'.join(order), reordered
    relative = pointer.replace('    OwnerRibbonPosition32C8 *point, *center;',
        '    OwnerRibbonPosition32C8 *point, *center, *relative;')
    relative = relative.replace('        projection = (last.z * nz + last.x * nx) - (first.z * nz + first.x * nx);',
        '        relative = &last;\n        projection = relative->z * nz + relative->x * nx;\n'
        '        relative = &first;\n        projection -= relative->z * nz + relative->x * nx;')
    yield 'relative-pointer-walk', relative
    for name, body in (('compact', base.COMPACT), ('midpoint-pointer', pointer), ('snapshot', snapshot)):
        for qualifier in ('', 'volatile '):
            grouped = body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
                '    ' + qualifier + 'OwnerRibbonPosition32C8 workspace[3];')
            for index, vector in enumerate(('last', 'first', 'midpoint')):
                grouped = grouped.replace(vector + '.', 'workspace[%d].' % index).replace(
                    '&' + vector + ';', '&workspace[%d];' % index)
            if qualifier and 'center' in grouped:
                continue
            yield 'grouped-' + name + ('-volatile' if qualifier else ''), grouped
    for name, body in (('snapshot-all', workspace_body(snapshot, ('midpoint', 'first', 'last'))),
            ('relative', relative), ('workspace', workspace_body(base.COMPACT, ('first', 'last')))):
        reused = body.replace('    f32 projection, vertical, angle, radius, angleStep;',
            '    f32 projection, vertical, angle, angleStep;').replace('    f32 sine, along;', '    f32 along;')
        reused = reused.replace('        radius =', '        inverse =').replace('            sine =', '            vertical =')
        reused = reused.replace('radius *', 'inverse *').replace(' * sine', ' * vertical')
        yield name + '-reused-radius-sine', reused


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None):
    return base.compile_candidate(root, out, name, body, profile, symbols)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--only', help='Compile candidate names containing this substring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-fitting'
    rows = []
    for name, body in candidates():
        if args.only and args.only not in name:
            continue
        for profile in base.compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            rows.append(meta)
            print(meta['name'], meta['body_words'], meta['frame'], meta['differences'], flush=True)
    suffix = (args.only or 'all') + ('-profiles' if args.profiles else '-o2g3')
    (out / ('measurements-' + suffix + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
