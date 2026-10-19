"""Screen the existing barrier-crossing C against its complete retail routine."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_cyclic_weight_profiles_candidates as previous
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-barrier-crossing'
SOURCE, OWNER = previous.SOURCE, previous.OWNER
FUNCTION, ENTRY, ROM, WORDS = 'func_15086D94', 0x15086D94, 0xB4244, 207
INPUTS = dict(previous.INPUTS)
INPUTS.update({
    SOURCE: '55493079cdf8df8d1e59d06e0ccfd9fb983798529ff6c2a91dfb5b788760be74',
    'conker/Makefile': '6e6563d792c110f74f44d615c62f04e87430aa0c0e44b1bd7817ffd6d91a8063',
    'conker/retail_word_patches.us.csv': '1511ad9a4d25fd2dd8835143b187edc5c224ec6e89272eb4c5a8b45a074a8043',
    'conker/build/conker.us.elf': 'ac9821636fcdf152a879c87120645fbc265991065a2b2568e545fc0126dd14ba',
})
DECLARATIONS = '''extern s16 D_80087290;
extern u8 *D_800D2350;
s32 func_15085DA8(f32 y);
'''
compile_profile, link_owner = previous.compile_profile, previous.link_owner


def freeze(root, out):
    with patch.object(previous, 'INPUTS', INPUTS):
        return previous.freeze(root, out)


def original_body(before):
    lo, hi = function_span(before, FUNCTION)
    return before[lo:hi]


def recovered_owner(before, body):
    lo, hi = function_span(before, FUNCTION)
    return before[:lo] + body.rstrip() + before[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero crossing alignment tail')
    return raw[:end * 4], {at - f['value']: v for at, v in bindings.items()
        if f['value'] <= at < f['value'] + end * 4}


def compile_candidate(root, out, name, body, normal=False, whole=False):
    values = freeze(root, out)
    unit = recovered_owner(values[SOURCE].decode(), body) if whole else (
        '#include <ultra64.h>\n' + DECLARATIONS + body)
    obj, diagnostics = compile_profile(root, out, unit, name, normal)
    raw, bindings = payload(obj)
    image, functions = link_owner(root, out, obj, OWNER)
    at = functions[FUNCTION]['value']
    words = list(struct.unpack_from('>%dI' % (len(raw) // 4), image, at))
    truth = struct.unpack_from('>%dI' % WORDS, values['conker/conker.us.bin'], ROM)
    row = dict(words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(), bindings=bindings)
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def candidates(before):
    initial = original_body(before)
    yield 'initial', initial
    cached = initial.replace('while (i < D_80087290)', 'while (i < count)')
    yield 'cached-count', cached
    for label, body in (('initial', initial), ('cached', cached)):
        coords = body.replace('    s32 id;', '    s32 id;\n    s32 bx;\n    s32 bz;\n    s32 ox;\n    s32 oz;')
        old = '''                            nx = (f32)(*(s16 *)(second + 4) - *(s16 *)(first + 4));
                            nz = -(f32)(*(s16 *)(second + 0) - *(s16 *)(first + 0));
                            ax = (f32)*(s16 *)(first + 0);
                            az = (f32)*(s16 *)(first + 4);'''
        new = '''                            bz = *(s16 *)(second + 4);
                            oz = *(s16 *)(first + 4);
                            ox = *(s16 *)(first + 0);
                            bx = *(s16 *)(second + 0);
                            nx = (f32)(bz - oz);
                            nz = -(f32)(bx - ox);
                            ax = (f32)ox;
                            az = (f32)oz;'''
        if coords.count(old) != 1:
            raise ValueError('Unknown original crossing coordinate expressions')
        coords = coords.replace(old, new).replace('(f32)*(s16 *)(second + 0) * nx', '(f32)bx * nx').replace(
            'nz * (f32)*(s16 *)(second + 4)', 'nz * (f32)bz')
        yield label + '-coordinates', coords
        yield label + '-cross-order', coords.replace('cross_x = x + fraction * dx;',
            'cross_x = fraction * dx + x;').replace('cross_z = z + fraction * dz;',
            'cross_z = fraction * dz + z;')


def expressions(before):
    initial = original_body(before)
    rotated = initial.replace('constant = -(ax * nx + swap * az);',
        'constant = -(ax * nx + nz * az);')
    yield 'rotated-role', rotated
    edits = (
        ('delta-z-first', '(x + dx) * nx + (z + dz) * nz', '(z + dz) * nz + (x + dx) * nx'),
        ('delta-normal-first', '(x + dx) * nx + (z + dz) * nz', 'nx * (x + dx) + nz * (z + dz)'),
        ('start-normal-first', 'x * nx + z * nz', 'nx * x + nz * z'),
        ('base-normal-first', 'ax * nx + nz * az', 'nx * ax + az * nz'),
        ('span-normal-first', 'cross_x * nx + cross_z * nz', 'nx * cross_x + nz * cross_z'),
        ('endpoint-z-first', '(f32)*(s16 *)(second + 0) * nx +\n                                      nz * (f32)*(s16 *)(second + 4)',
            'nz * (f32)*(s16 *)(second + 4) +\n                                      (f32)*(s16 *)(second + 0) * nx'),
        ('endpoint-normal-first', '(f32)*(s16 *)(second + 0) * nx', 'nx * (f32)*(s16 *)(second + 0)'),
        ('neighbor-constant-first', 'id != 255', '255 != id'),
    )
    for label, old, new in edits:
        yield label, rotated.replace(old, new)
    floats = ('minimum', 'fraction', 'ax', 'az', 'nx', 'nz', 'constant', 'start', 'end',
        'a', 'b', 'cross_x', 'cross_z', 'swap')
    decls = ''.join('    f32 %s;\n' % name for name in floats)
    if initial.count(decls) != 1:
        raise ValueError('Unknown crossing float declaration block')
    for label, order in (
        ('reverse-floats', floats[::-1]),
        ('minimum-last', floats[2:] + floats[:2]),
        ('normal-first', ('nx', 'nz') + tuple(n for n in floats if n not in ('nx', 'nz'))),
        ('constant-first', ('constant',) + tuple(n for n in floats if n != 'constant')),
        ('start-first', ('start', 'end', 'a', 'b') + tuple(n for n in floats if n not in ('start', 'end', 'a', 'b'))),
    ):
        yield label, rotated.replace(decls, ''.join('    f32 %s;\n' % name for name in order))


def lifetimes(before):
    base = dict(expressions(before))['start-first']
    yield 'delayed-start-copy', base.replace('                            a = start;\n', '').replace(
        '                            b = end;', '                            a = start;\n                            b = end;')
    yield 'absolute-first', base.replace('start = x * nx + z * nz + constant;\n                            a = start;',
        'a = x * nx + z * nz + constant;\n                            start = a;').replace(
        'end = (x + dx) * nx + (z + dz) * nz + constant;\n                            b = end;',
        'b = (x + dx) * nx + (z + dz) * nz + constant;\n                            end = b;')
    old = '                            end = (x + dx) * nx + (z + dz) * nz + constant;'
    for name, new in (
        ('split-deltas', '''                            cross_z = z + dz;
                            cross_x = x + dx;
                            end = cross_x * nx + cross_z * nz + constant;'''),
        ('split-end-term', '''                            b = (z + dz) * nz;
                            end = (x + dx) * nx + b + constant;'''),
        ('early-end-term', '''                            end = z + dz;
                            end *= nz;
                            end = (x + dx) * nx + end + constant;'''),
    ):
        yield name, base.replace(old, new)
    lines = '''                            start = x * nx + z * nz + constant;
                            a = start;
                            end = (x + dx) * nx + (z + dz) * nz + constant;
                            b = end;'''
    yield 'end-before-start', base.replace(lines, '''                            end = (x + dx) * nx + (z + dz) * nz + constant;
                            b = end;
                            start = x * nx + z * nz + constant;
                            a = start;''')
    for name in ('nx', 'nz', 'constant', 'start', 'end', 'a', 'b'):
        yield 'register-' + name, base.replace('    f32 %s;' % name, '    register f32 %s;' % name)


def assignments(before):
    base = dict(expressions(before))['start-first']
    start = 'start = x * nx + z * nz + constant;\n                            a = start;'
    end = 'end = (x + dx) * nx + (z + dz) * nz + constant;\n                            b = end;'
    for label, value in (
        ('start-absolute', 'a = x * nx + z * nz + constant;\n                            start = a;'),
        ('start-chained', 'a = start = x * nx + z * nz + constant;'),
        ('start-chained-reverse', 'start = a = x * nx + z * nz + constant;'),
        ('start-staged', 'start = x * nx;\n                            start += z * nz;\n                            start += constant;\n                            a = start;'),
    ):
        yield label, base.replace(start, value)
    for label, value in (
        ('end-absolute', 'b = (x + dx) * nx + (z + dz) * nz + constant;\n                            end = b;'),
        ('end-chained', 'b = end = (x + dx) * nx + (z + dz) * nz + constant;'),
        ('end-chained-reverse', 'end = b = (x + dx) * nx + (z + dz) * nz + constant;'),
        ('end-staged', 'end = (x + dx) * nx;\n                            end += (z + dz) * nz;\n                            end += constant;\n                            b = end;'),
    ):
        yield label, base.replace(end, value)


def selected_body(before):
    return dict(lifetimes(before))['absolute-first']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', action='store_true')
    parser.add_argument('--whole', action='store_true')
    parser.add_argument('--expressions', action='store_true')
    parser.add_argument('--lifetimes', action='store_true')
    parser.add_argument('--assignments', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    values = freeze(root, out)
    screens = assignments if args.assignments else lifetimes if args.lifetimes else expressions if args.expressions else candidates
    for label, body in screens(values[SOURCE].decode()):
        if args.filter and label != args.filter:
            continue
        name = label + ('-normal' if args.normal else '') + ('-whole' if args.whole else '')
        _, _, row = compile_candidate(root, out, name, body, args.normal, args.whole)
        print(json.dumps(dict(name=name, **row)), flush=True)


if __name__ == '__main__':
    main()
