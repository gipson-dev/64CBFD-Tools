"""Fit real geometry temporaries and private lifetimes for the full renderer."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_ribbon_renderer_candidates as base

RECOVERED = base.SELECTED


def separate_offsets(body):
    body = body.replace('nz, length, scale;', 'nz, length, scale;\n    f32 ox, oy, oz;')
    body = body.replace('nx = ny = nz = 0.0f;', 'ox = oy = oz = 0.0f;')
    for normal, offset in zip(('nx', 'ny', 'nz'), ('ox', 'oy', 'oz')):
        body = body.replace(normal + ' *= scale;', offset + ' = ' + normal + ' * scale;')
        for sign in ('+', '-'):
            body = body.replace(' ' + sign + ' ' + normal + ')', ' ' + sign + ' ' + offset + ')')
    return body


def squared_components(body):
    body = body.replace('f32 ox, oy, oz;', 'f32 ox, oy, oz;\n    f32 squaredX, squaredY, squaredZ;')
    return body.replace('length = nx * nx + ny * ny + nz * nz;',
        'squaredX = nx * nx;\n    squaredY = ny * ny;\n    squaredZ = nz * nz;\n'
        '    length = squaredX + squaredY + squaredZ;')


def allocated_scope(body):
    start = '    if (cursor == NULL) {\n        return output;\n    }\n'
    assert body.count(start) == 1
    body = body.replace(start, '    if (cursor != NULL) {\n')
    return body.replace('    return output;\n}', '    }\n    return output;\n}')


def sync_before_modes(body):
    return body.replace('    s32 mode1,', '    u8 sync;\n    s32 mode1,').replace(
        'u8 bank, combine, sync;', 'u8 bank, combine;')


def offset_loop(body, form):
    opening = 'for (offset = 0x18; offset != 0xF0; offset += 0x18)'
    if form == 'index':
        return body.replace(opening, 'for (offset = 1; offset != 10; offset++)').replace(
            'actor + 0x48 + offset - 0x18', 'actor + 0x48 + (offset - 1) * 0x18').replace(
            'actor + 0x48 + offset)', 'actor + 0x48 + offset * 0x18)')
    if form == 'upfront':
        return body.replace(opening, 'for (offset = 0; offset != 0xD8;)').replace(
            '        first = *(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset - 0x18);',
            '        first = *(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset);\n'
            '        offset += 0x18;')
    if form == 'explicit-pointers':
        return body.replace('    s32 offset;', '    s32 offset;\n    u8 *previous, *point;').replace(
            opening, 'previous = actor + 0x48;\n    point = actor + 0x60;\n'
            '    for (offset = 0x18; offset != 0xF0; offset += 0x18, previous += 0x18, point += 0x18)').replace(
            'actor + 0x48 + offset - 0x18', 'previous').replace('actor + 0x48 + offset)', 'point)')
    raise ValueError(form)


def locals_form(body, top, floats, low_length=False):
    begin, end = body.index('    Vtx *cursor;'), body.index('\n    if (actor[0x10]')
    prefix = {
        'texture-first': '    u32 textureT;\n    Vtx *cursor;\n'
            '    OwnerRibbonPosition32C8 first, second;\n    s32 offset;\n'
            '    OwnerRibbonPosition32C8 *origin;\n',
        'offset-first': '    s32 offset;\n    Vtx *cursor;\n'
            '    OwnerRibbonPosition32C8 first, second;\n    u32 textureT;\n'
            '    OwnerRibbonPosition32C8 *origin;\n',
        'cursor-first': '    Vtx *cursor;\n    OwnerRibbonPosition32C8 first, second;\n'
            '    s32 offset;\n    OwnerRibbonPosition32C8 *origin;\n    u32 textureT;\n',
    }[top]
    groups = {
        'rays': '    f32 rx, ry, rz;\n', 'deltas': '    f32 dx, dy, dz;\n',
        'normals': '    f32 nx, ny, nz;\n', 'offsets': '    f32 ox, oy, oz;\n',
        'length': '    f32 length, scale;\n',
    }
    geometry = ''.join(groups[name] for name in floats if not (low_length and name == 'length'))
    material = ('    u8 sync;\n'
        '    s32 mode1, mode2, envR, envG, envB, alpha, primR, primG, primB, primA, renderMode;\n'
        '    u8 bank, combine;\n    f32 squaredX, squaredY, squaredZ;\n')
    if low_length:
        material += groups['length']
    return body[:begin] + prefix + geometry + material + body[end:]


def reused_offsets(body, targets):
    for current, target in zip(('ox', 'oy', 'oz'), targets):
        for sign in ('+', '-'):
            body = body.replace(' ' + sign + ' ' + current + ')', ' ' + sign + ' ' + target + ')')
        body = body.replace(current + ' = ', target + ' = ')
    body = body.replace('ox = oy = oz = 0.0f;', ' = '.join(targets) + ' = 0.0f;')
    body = body.replace('f32 ox, oy, oz;', 'f32 productX, productY, productZ;')
    body = body.replace('nx = dy * rz - ry * dz;',
        'productX = dy * rz; productY = ry * dz; nx = productX - productY;').replace(
        'ny = dz * rx - rz * dx;',
        'productZ = dz * rx; productY = rz * dx; ny = productZ - productY;').replace(
        'nz = dx * ry - rx * dy;',
        'productX = dx * ry; productY = rx * dy; nz = productX - productY;')
    return body


def geometry_input_order(body, order):
    for point, indent in (('first', '    '), ('second', '        ')):
        original = base.GEOMETRY.format(point=point).splitlines()[:6]
        assignments = {line.strip().split(' = ', 1)[0]: line.strip() for line in original}
        before = '\n'.join(indent + line.strip() for line in original)
        after = '\n'.join(indent + assignments[name] for name in order)
        assert body.count(before) == 1
        body = body.replace(before, after)
    return body


def candidates():
    separated = separate_offsets(RECOVERED)
    components = squared_components(separated)
    for name, body in (('offsets', separated), ('components', components)):
        for scope in (False, True):
            scoped = allocated_scope(body) if scope else body
            for sync in (False, True):
                selected = sync_before_modes(scoped) if sync else scoped
                label = name + ('-allocated' if scope else '') + ('-sync' if sync else '')
                yield label, selected
                if scope and sync:
                    for form in ('index', 'upfront', 'explicit-pointers'):
                        yield label + '-' + form, offset_loop(selected, form)
    scoped = sync_before_modes(allocated_scope(components))
    for top in ('texture-first', 'offset-first', 'cursor-first'):
        for label, order in (
                ('rays', ('rays', 'deltas', 'normals', 'length', 'offsets')),
                ('length-rays', ('length', 'rays', 'deltas', 'normals', 'offsets')),
                ('ray-offsets', ('rays', 'offsets', 'deltas', 'normals', 'length')),
                ('normals-rays', ('normals', 'rays', 'deltas', 'length', 'offsets'))):
            yield top + '-' + label, locals_form(scoped, top, order)
    best = locals_form(scoped, 'texture-first', ('rays', 'deltas', 'normals', 'length', 'offsets'), True)
    yield 'retail-homes', best
    yield 'retail-homes-zero', best.replace('ox = oy = oz = 0.0f;',
        'ox = 0.0f; oy = 0.0f; oz = 0.0f;')
    yield 'retail-homes-reverse-zero', best.replace('ox = oy = oz = 0.0f;',
        'oz = oy = ox = 0.0f;')
    yield 'retail-homes-register-rays', best.replace('f32 rx, ry, rz;', 'register f32 rx, ry, rz;')
    yield 'retail-homes-register-all', best.replace('    f32 ', '    register f32 ')
    scalar = best.replace('ox = oy = oz = 0.0f;', 'ox = 0.0f; oy = 0.0f; oz = 0.0f;')
    for order in (('rx', 'ry', 'rz', 'dy', 'dz', 'dx'), ('dy', 'dz', 'rx', 'ry', 'rz', 'dx'),
            ('dy', 'dz', 'rx', 'dx', 'ry', 'rz'), ('dx', 'dy', 'dz', 'rx', 'ry', 'rz'),
            ('dy', 'dz', 'dx', 'rx', 'ry', 'rz'), ('rz', 'ry', 'rx', 'dz', 'dy', 'dx'),
            ('rx', 'dy', 'ry', 'dz', 'rz', 'dx')):
        yield 'retail-inputs-' + '-'.join(order), geometry_input_order(scalar, order)
    for targets in (('dx', 'dy', 'dz'), ('rx', 'ry', 'rz'), ('dz', 'rx', 'ry'),
            ('nx', 'ny', 'nz')):
        yield 'retail-homes-reuse-' + '-'.join(targets), reused_offsets(best, targets)


SELECTED_NAME = 'retail-inputs-dx-dy-dz-rx-ry-rz'
SELECTED = dict(candidates())[SELECTED_NAME]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-ribbon-renderer-fitting'
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    rows = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, out, name, body)
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        rows.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / ((args.form or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
