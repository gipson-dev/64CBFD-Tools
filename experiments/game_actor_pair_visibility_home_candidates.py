"""Recover concrete pair-mask scalar homes using only real local declarations."""
import argparse
import json
import math
from pathlib import Path
import re

from tools.experiments import game_actor_pair_visibility_candidates as source
from tools.tests import game_actor_pair_visibility_oracle as guest

BUILD = source.BUILD + '/homes'


def declarations(body, order):
    head, tail = body.split('\n\n    queryClear = 0;', 1)
    lines = head.splitlines()
    entries = {}
    for line in lines[2:]:
        match = re.fullmatch(r'    (?:s32|f32|u8|u32|void) \*?(\w+);', line)
        if not match or match[1] in entries:
            raise ValueError('Unknown pair-mask declaration block: ' + line)
        entries[match[1]] = line
    if len(order) != len(entries) or set(order) != entries.keys():
        raise ValueError('Pair-mask declaration order changes real locals')
    return '\n'.join([*lines[:2], *(entries[name] for name in order)]) + '\n\n    queryClear = 0;' + tail


def candidates():
    yield 'baseline', source.SELECTED
    prefix = ('clear', 'queryClear', 'actor')
    outputs = ('distance', 'hitA', 'hitB', 'hitC', 'hitDistance')
    suffix = ('active', 'otherActive', 'other', 'row')
    orders = {
        'interleaved-points': prefix + ('dx', 'dz', 'dy', 'nested') + outputs +
            ('x', 'otherX', 'y', 'otherY', 'startZ', 'otherZ') + suffix,
        'point-registers': prefix + ('dy', 'x', 'y', 'otherY') + outputs +
            ('otherX', 'nested', 'startZ', 'otherZ', 'dx', 'dz') + suffix,
        'delta-registers': prefix + ('dx', 'dz', 'dy', 'otherY') + outputs +
            ('x', 'otherX', 'y', 'nested', 'startZ', 'otherZ') + suffix,
        'pointer-registers': prefix + ('nested', 'other', 'row', 'active', 'otherActive') + outputs +
            ('x', 'otherX', 'y', 'otherY', 'startZ', 'otherZ', 'dx', 'dz', 'dy'),
        'named-delta-homes': prefix + ('nested', 'other', 'row', 'dy') + outputs +
            ('x', 'otherX', 'y', 'otherY', 'startZ', 'otherZ', 'dx', 'dz', 'active', 'otherActive'),
    }
    for label, order in orders.items():
        yield label, declarations(source.SELECTED, order)
    named = declarations(source.SELECTED, orders['named-delta-homes'])
    interleaved = declarations(source.SELECTED, orders['interleaved-points'])
    for label, body in (('named', named), ('interleaved', interleaved)):
        compound = body.replace('        dz = otherZ - startZ;', '        dz = otherZ;\n        dz -= startZ;').replace(
            '        dx = otherX - x;', '        dx = otherX;\n        dx -= x;')
        yield label + '-compound-deltas', compound
        norm = body.replace('sqrtf((dx * dx) + (dy * dy) + (dz * dz))',
            'sqrtf((dz * dz) + ((dx * dx) + (dy * dy)))')
        yield label + '-z-product-first', norm
        yield label + '-compound-z-first', compound.replace('sqrtf((dx * dx) + (dy * dy) + (dz * dz))',
            'sqrtf((dz * dz) + ((dx * dx) + (dy * dy)))')
    for names in (('dx', 'dz'), ('nested', 'other'), ('nested', 'row')):
        body = named
        for name in names:
            line = next(line for line in body.splitlines() if line.endswith(' ' + name + ';') or line.endswith('*' + name + ';'))
            body = body.replace(line, line.replace('    ', '    register ', 1))
        label = 'register-' + '-'.join(names)
        yield label, body
        body = body.replace('    f32 dx;\n', '    f32 cachedDX;\n    f32 dx;\n') if names != ('dx', 'dz') else body.replace(
            '    register f32 dx;\n', '    f32 cachedDX;\n    register f32 dx;\n')
        body = body.replace('    f32 dz;\n', '    f32 cachedDZ;\n    f32 dz;\n') if names != ('dx', 'dz') else body.replace(
            '    register f32 dz;\n', '    f32 cachedDZ;\n    register f32 dz;\n')
        body = body.replace('        dx = otherX - x;', '        dx = otherX - x;\n        cachedDX = dx;\n        cachedDZ = dz;').replace(
            'func_15086D94(x, y, startZ, dx, dz)', 'func_15086D94(x, y, startZ, cachedDX, cachedDZ)')
        yield label + '-delta-copies', body
    body = named
    body = body.replace('    u8 *nested;\n', '').replace('    u32 *row;\n', '')
    body = body.replace('        nested = *(u8 **)(actor + 0x31C);\n', '').replace(
        '            nested = *(u8 **)(other + 0x31C);\n', '')
    body = body.replace('active = nested[0x84];', 'active = (*(u8 **)(actor + 0x31C))[0x84];').replace(
        'otherActive = nested[0x84];', 'otherActive = (*(u8 **)(other + 0x31C))[0x84];')
    before, after = body.split('        otherX =', 1)
    for old, new in (('nested + 0x114', '(*(u8 **)(actor + 0x31C)) + 0x114'),
            ('nested[0x75]', '(*(u8 **)(actor + 0x31C))[0x75]')):
        before = before.replace(old, new)
        after = after.replace(old, new.replace('actor +', 'other +'))
    body = before + '        otherX =' + after
    for index, opposite in (('first', 'second'), ('second', 'first')):
        for mask in ('1u', '0x10000u'):
            old = '        row = (u32 *)((u8 *)D_800D23B0 + (u32)%s * 4);\n        row[0x16C0 / 4] |= %s << ((u32)%s & 31);' % (index, mask, opposite)
            new = '        *(u32 *)((u8 *)D_800D23B0 + (u32)%s * 4 + 0x16C0) |= %s << ((u32)%s & 31);' % (index, mask, opposite)
            if body.count(old) != 1:
                raise ValueError('Unknown pair-mask row expression')
            body = body.replace(old, new)
    if re.search(r'\b(?:nested|row)\b', body):
        raise ValueError('Remaining inlined pair-mask local')
    body = body.replace('    f32 dx;\n', '    f32 dx;\n    f32 cachedDX;\n    f32 cachedDZ;\n')
    body = body.replace('        dx = otherX - x;', '        dx = otherX - x;\n        cachedDX = dx;\n        cachedDZ = dz;').replace(
        'func_15086D94(x, y, startZ, dx, dz)', 'func_15086D94(x, y, startZ, cachedDX, cachedDZ)')
    order = prefix + ('dx', 'dz', 'dy', 'other') + outputs + (
        'x', 'otherX', 'y', 'otherY', 'startZ', 'otherZ', 'cachedDX', 'cachedDZ', 'active', 'otherActive')
    body = declarations(body, order)
    yield 'inline-delta-copies', body
    yield 'inline-delta-copies-z-first', body.replace('sqrtf((dx * dx) + (dy * dy) + (dz * dz))',
        'sqrtf((dz * dz) + ((dx * dx) + (dy * dy)))')


def homes(words):
    case = guest.Case()
    model = guest.PairModel(words, guest.fixture(case), case).run()
    query = next(row for row in model.raw_calls if row[0] == guest.QUERY)
    frame = (-words[0]) & 65535
    sp = guest.STACK - frame
    values = dict(zip(('x', 'y', 'startZ', 'dx', 'dy', 'dz'), query[1:7]))
    squares = [guest.f32(guest.floating(value) ** 2) for value in query[4:7]]
    values.update(otherX=guest.bits(case.points[1][0]), otherZ=guest.bits(case.points[1][2]),
        distance=guest.bits(guest.f32(math.sqrt(guest.f32(guest.f32(squares[0] + squares[1]) + squares[2])))))
    slots = {name: sorted({a - sp for a, size, value in model.stores
        if size == 4 and sp + 0x40 <= a < guest.STACK and value == bits}) for name, bits in values.items()}
    slots['outputs'] = [address - sp for address in query[9:13]]
    return slots


def screen(root, out, label, body, normal=False, whole=False):
    obj, words, row = source.compile_candidate(root, out, label, body, normal, whole)
    row = {key: value for key, value in row.items() if key != 'bindings'}
    row.update(name=label, homes=homes(words))
    (out / (label + '-homes.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--filter')
    p.add_argument('--normal', action='store_true')
    p.add_argument('--whole', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    values = source.freeze(root, out)
    import struct
    retail = list(struct.unpack_from('>261I', values['conker/conker.us.bin'], source.ROM))
    print(json.dumps(dict(name='retail', homes=homes(retail))), flush=True)
    for label, body in candidates():
        if args.filter and args.filter not in label:
            continue
        _, _, row = screen(root, out, label + ('-normal' if args.normal else '') +
            ('-whole' if args.whole else ''), body, args.normal, args.whole)
        print(json.dumps(row), flush=True)
