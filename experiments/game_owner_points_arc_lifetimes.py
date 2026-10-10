"""Complete arc vector representation and real scalar/cursor lifetime fitting."""
import argparse
import itertools
import json
import re
from pathlib import Path

from tools.experiments import game_owner_points_arc_candidates as base
from tools.experiments import game_owner_points_arc_fitting as previous

RECOVERY_COMPACT = base.COMPACT


def arrays(body):
    result = body.replace('    OwnerRibbonPosition32C8 midpoint, first, last;',
        '    f32 midpoint[3], first[3], last[3];')
    for vector in ('midpoint', 'first', 'last'):
        for index, field in enumerate(('x', 'y', 'z')):
            result = result.replace(vector + '.' + field, vector + '[%d]' % index)
    return result


def register_locals(body):
    return re.sub(r'^(    )f32 ([^;]+);',
        lambda match: match[0] if '[' in match[2] else match[1] + 'register f32 ' + match[2] + ';',
        body, flags=re.MULTILINE)


def reused_scalars(body, selected=('projection', 'vertical', 'radius', 'sine')):
    mapping = dict(projection='dx', vertical='dz', radius='inverse', sine='dy')
    result = body
    for declaration in ('projection, vertical, angle, radius, angleStep', 'sine, along'):
        result = result.replace('    f32 ' + declaration + ';',
            '    f32 ' + ', '.join(name for name in declaration.split(', ') if name not in selected) + ';')
    for name in selected:
        result = re.sub(r'\b' + name + r'\b', mapping[name], result)
    return result


def stage_reuse(body, mapping):
    def declarations(match):
        names = [name for name in match[1].split(', ') if name not in mapping]
        return '    f32 ' + ', '.join(names) + ';' if names else ''
    result = re.sub(r'^    f32 ([a-zA-Z0-9_, ]+);', declarations, body, flags=re.MULTILINE)
    names = r'\b(' + '|'.join(mapping) + r')\b'
    return re.sub(names, lambda match: mapping[match[0]], result)


def separate_cursor(body, early_advance=False):
    result = body.replace('    OwnerRibbonPosition32C8 *point;',
        '    OwnerRibbonPosition32C8 *point, *cursor;')
    result = result.replace('        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);',
        '        cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);')
    result = result.replace('        for (offset = 0; offset != 0xF0; offset += 0x18) {',
        '        for (offset = 0; offset != 0xF0; offset += 0x18) {\n'
        '            actor = (u8 *)cursor;\n            point = (OwnerRibbonPosition32C8 *)actor;')
    result = result.replace('            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);',
        '            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);')
    if early_advance:
        advance = '            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);\n'
        result = result.replace(advance, '').replace('            sine =', advance + '            sine =')
    return result


def candidates():
    snapshot = base.SELECTED.replace('    f32 sine, cosine, along;', '    f32 sine, along;').replace(
        '            cosine = cosf(angle);\n            along = radius * cosine;',
        '            along = radius * cosf(angle);').replace(
        '        for (offset = 0;', '        point = (OwnerRibbonPosition32C8 *)(actor + 0x48);\n        for (offset = 0;').replace(
        '            point = (OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);\n', '').replace(
        '            angle += angleStep;', '            angle += angleStep;\n'
        '            point = (OwnerRibbonPosition32C8 *)((u8 *)point + 0x18);')
    for name, body in (('compact', RECOVERY_COMPACT), ('snapshot', snapshot)):
        yield name + '-register', register_locals(body)
        yield name + '-arrays', arrays(body)
        yield name + '-arrays-register', register_locals(arrays(body))
        yield name + '-reuse', reused_scalars(body)
        for representation, workspace in (('vectors', body), ('arrays', arrays(body))):
            for advance in (False, True):
                cursor = separate_cursor(workspace, advance)
                label = name + '-' + representation + '-cursor' + ('-early' if advance else '')
                yield label, cursor
                yield label + '-register', register_locals(cursor)
    for name, body in (('first-last', previous.workspace_body(RECOVERY_COMPACT, ('first', 'last'))),
            ('midpoint', previous.workspace_body(RECOVERY_COMPACT, ('midpoint',)))):
        yield name + '-register', register_locals(body)
        yield name + '-reuse', reused_scalars(body)
    workspace = previous.workspace_body(RECOVERY_COMPACT, ('first', 'last'))
    for flags in itertools.product((False, True), repeat=4):
        selected = tuple(name for name, enabled in zip(('projection', 'vertical', 'radius', 'sine'), flags) if enabled)
        label = 'workspace-subset-' + ( '-'.join(selected) or 'none')
        yield label, reused_scalars(workspace, selected)
        for early in (False, True):
            cursor = separate_cursor(workspace, early)
            yield label + ('-early-cursor' if early else '-cursor'), reused_scalars(cursor, selected)
    stage_mappings = (
        ('vertical-sine', dict(vertical='sine')),
        ('vertical-delta-y', dict(vertical='dy', sine='dy')),
        ('projection-step', dict(projection='angleStep')),
        ('projection-step-vertical-sine', dict(projection='angleStep', vertical='sine')),
        ('projection-step-vertical-sine-radius', dict(projection='angleStep', vertical='sine', radius='inverse')),
        ('projection-step-vertical-y-radius', dict(projection='angleStep', vertical='dy', sine='dy', radius='inverse')),
        ('projection-radius', dict(projection='radius')),
        ('projection-radius-vertical-sine', dict(projection='radius', vertical='sine')),
    )
    for name, mapping in stage_mappings:
        for cursor in (False, True):
            body = separate_cursor(workspace) if cursor else workspace
            yield 'stage-' + name + ('-cursor' if cursor else ''), stage_reuse(body, mapping)
    direct = stage_reuse(separate_cursor(workspace), dict(projection='angleStep'))
    direct = direct.replace('    OwnerRibbonPosition32C8 *point, *cursor;',
        '    OwnerRibbonPosition32C8 *cursor;').replace(
        '            point = (OwnerRibbonPosition32C8 *)actor;\n', '').replace(
        'point->', '((OwnerRibbonPosition32C8 *)actor)->')
    yield 'direct-cursor', direct
    delta = direct.replace('    OwnerRibbonPosition32C8 midpoint;',
        '    OwnerRibbonPosition32C8 delta, midpoint;').replace('    f32 dx, dy, dz;\n', '')
    for scalar, field in (('dx', 'x'), ('dy', 'y'), ('dz', 'z')):
        delta = re.sub(r'\b' + scalar + r'\b', 'delta.' + field, delta)
    yield 'direct-delta-vector', delta
    counter_first = delta.replace('        cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);',
        '        offset = 0;\n        cursor = (OwnerRibbonPosition32C8 *)(actor + 0x48);').replace(
        'for (offset = 0;', 'for (;')
    yield 'control-counter-first', counter_first
    increment = counter_first.replace('            angle += angleStep;\n', '').replace(
        'offset += 0x18) {', 'offset += 0x18, angle += angleStep) {')
    yield 'control-for-angle-increment', increment
    loop_end = '        }\n    }\n    return 1;'
    do_loop = counter_first.replace('        for (; offset != 0xF0; offset += 0x18) {', '        do {').replace(
        loop_end, '        } while ((offset += 0x18) != 0xF0);\n    }\n    return 1;')
    yield 'control-do-counter', do_loop
    condition = do_loop.replace('            angle += angleStep;\n', '').replace(
        'while ((offset += 0x18) != 0xF0)', 'while (offset += 0x18, angle += angleStep, offset != 0xF0)')
    yield 'control-do-angle-condition', condition
    advance = '            cursor = (OwnerRibbonPosition32C8 *)((u8 *)cursor + 0x18);\n'
    early = do_loop.replace(advance, '').replace('while ((offset += 0x18) != 0xF0)', 'while (offset != 0xF0)')
    early = early.replace('            ((OwnerRibbonPosition32C8 *)actor)->x =',
        '            offset += 0x18;\n' + advance + '            ((OwnerRibbonPosition32C8 *)actor)->x =', 1)
    yield 'control-do-early-counter-cursor', early
    yield 'control-do-early-angle-condition', early.replace('            angle += angleStep;\n', '').replace(
        'while (offset != 0xF0)', 'while (angle += angleStep, offset != 0xF0)')
    yield 'direct-delta-vector-ordinary', delta.replace('volatile OwnerRibbonPosition32C8 first, last;',
        'OwnerRibbonPosition32C8 first, last;')
    ordinary = delta.replace('volatile OwnerRibbonPosition32C8 first, last;',
        'OwnerRibbonPosition32C8 first, last;')
    setup, reads = ordinary.split('        angleStep = (last.z', 1)
    for vector in ('last', 'first'):
        reads = reads.replace(vector + '.', '((volatile OwnerRibbonPosition32C8 *)&' + vector + ')->')
    yield 'direct-read-workspace', setup + '        angleStep = (((volatile OwnerRibbonPosition32C8 *)&last)->z' + reads
    vectors = ordinary
    loads = []
    for index, field in enumerate(('x', 'y', 'z')):
        for vector, offset in (('last', 0x20), ('first', 0x14)):
            access = '*(f32 *)(actor + 0x%X)' % (offset + index * 4)
            vectors = vectors.replace(access, vector + '.' + field)
            loads.append('    ' + vector + '.' + field + ' = ' + access + ';')
    vectors = vectors.replace('    delta.x =', '\n'.join(loads) + '\n    delta.x =', 1)
    yield 'endpoint-vectors', vectors
    array_vectors = vectors.replace('    OwnerRibbonPosition32C8 first, last;',
        '    f32 first[3], last[3];')
    for vector in ('first', 'last'):
        for index, field in enumerate(('x', 'y', 'z')):
            array_vectors = array_vectors.replace(vector + '.' + field, vector + '[%d]' % index)
    yield 'endpoint-vectors-arrays', array_vectors
    pointed = vectors.replace('    OwnerRibbonPosition32C8 *cursor;',
        '    OwnerRibbonPosition32C8 *cursor, *center;').replace(
        '        cursor =', '        center = &midpoint;\n        cursor =', 1)
    setup, loop = pointed.split('        for (offset', 1)
    yield 'endpoint-vectors-midpoint-pointer', setup + '        for (offset' + loop.replace('midpoint.', 'center->')
    setup, reads = vectors.split('        angleStep = (last.z', 1)
    for vector in ('last', 'first'):
        reads = reads.replace(vector + '.', '((volatile OwnerRibbonPosition32C8 *)&' + vector + ')->')
    yield 'endpoint-vectors-read-workspace', setup + '        angleStep = (((volatile OwnerRibbonPosition32C8 *)&last)->z' + reads
    scalar_y = direct.replace('    f32 dx, dy, dz;', '    f32 dx, dz;').replace(
        '    OwnerRibbonPosition32C8 midpoint;', '    volatile f32 dy;\n    OwnerRibbonPosition32C8 midpoint;')
    yield 'direct-private-delta-y', scalar_y
    yield 'direct-delta-vector-private-y', delta.replace('    OwnerRibbonPosition32C8 delta, midpoint;',
        '    volatile OwnerRibbonPosition32C8 delta;\n    OwnerRibbonPosition32C8 midpoint;')
    setup, remainder = delta.split('        midpoint.x =', 1)
    work, tail = ('        midpoint.x =' + remainder).split('        inverse =', 1)
    statements = [statement for statement in work.splitlines() if statement.strip()]
    by_field = {statement.strip().split(' =')[0]: statement for statement in statements}
    orders = (
        ('axis', tuple(vector + '.' + field for field in ('x', 'y', 'z') for vector in ('midpoint', 'first', 'last'))),
        ('first-x', ('midpoint.x', 'first.x', 'midpoint.y', 'midpoint.z', 'last.x', 'first.z', 'last.y', 'first.y', 'last.z')),
        ('original-offset', ('midpoint.x', 'midpoint.y', 'midpoint.z', 'first.x', 'last.x', 'first.z', 'last.y', 'first.y', 'last.z')),
    )
    for label, order in orders:
        ordered = setup + '\n'.join(by_field[field] for field in order) + '\n        inverse =' + tail
        for snapshots in (False, True):
            body = ordered
            if snapshots:
                values, loads = [], []
                for endpoint, offset in (('start', 0x14), ('end', 0x20)):
                    for index, field in enumerate(('x', 'y', 'z')):
                        scalar = endpoint + field.upper()
                        values.append(scalar)
                        access = '*(f32 *)(actor + 0x%X)' % (offset + index * 4)
                        body = body.replace(access, scalar)
                        loads.append('    ' + scalar + ' = ' + access + ';')
                body = body.replace('    OwnerRibbonPosition32C8 delta, midpoint;',
                    '    f32 ' + ', '.join(values) + ';\n    OwnerRibbonPosition32C8 delta, midpoint;')
                body = body.replace('    delta.x =', '\n'.join(loads) + '\n    delta.x =', 1)
            yield 'ordered-' + label + ('-snapshots' if snapshots else ''), body


def compile_candidate(root, out, name, body, profile='o2g3', symbols=None):
    return base.compile_candidate(root, out, name, body, profile, symbols)


SELECTED_NAME = 'direct-delta-vector'
SELECTED = dict(candidates())[SELECTED_NAME]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Compile names containing this substring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-lifetimes'
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
