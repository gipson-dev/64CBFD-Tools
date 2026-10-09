"""Fit complete renderer private aggregates; retain typed decompiler evidence."""

import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_candidates as base
from tools.experiments import game_camera_ribbon_renderer_fitting as fitting
from tools.experiments import game_camera_ribbon_renderer_lifetimes as lifetime


COLORS = '''typedef struct {
    s16 alpha, blue, green, red;
} CameraRibbonColors;
'''
STACK = '''typedef struct {
    CameraRibbonPosition position;
} CameraRibbonOrigin;
struct _m2c_stack_func_1514803C {
    u8 reserved00[0xB4];
    s16 environmentA, environmentB, environmentG, environmentR;
    s16 primitiveA, primitiveB, primitiveG, primitiveR;
    u8 reservedC4[0x28];
    CameraRibbonRecord *records;
    CameraRibbonOrigin *origin;
    u8 reservedF4[8];
    CameraRibbonPosition previous;
    CameraRibbonPosition current;
    u8 reserved114[3];
    u8 sync;
    Vtx *cursor;
    u8 reserved11C[4];
};
'''


def grouped_colors(body, arrays=False):
    for name in ('primitive', 'environment'):
        declaration = '    s16 %sR, %sG, %sB, %sA;\n' % ((name,) * 4)
        replacement = ('    s16 %s[4];\n' if arrays else '    CameraRibbonColors %s;\n') % name
        assert declaration in body
        body = body.replace(declaration, replacement)
        for channel, index, field in (('R', 3, 'red'), ('G', 2, 'green'), ('B', 1, 'blue'), ('A', 0, 'alpha')):
            body = body.replace(name + channel, '%s[%d]' % (name, index) if arrays else name + '.' + field)
    return body if arrays else COLORS + body


def grouped_positions(body):
    declaration = '    CameraRibbonPosition current;\n    CameraRibbonPosition previous;\n'
    assert declaration in body
    body = body.replace(declaration, '    CameraRibbonPosition positions[2];\n')
    body = body.replace('previous.', 'positions[0].').replace('current.', 'positions[1].')
    body = body.replace('previous =', 'positions[0] =').replace('current =', 'positions[1] =')
    return body


def field_positions(body):
    for destination, source in (('previous', 'prior->position'), ('current', 'point->position'),
            ('previous', 'records[previousIndex].position')):
        assignment = destination + ' = ' + source + ';'
        if assignment not in body:
            continue
        body = body.replace(assignment, '\n'.join('%s.%s = %s.%s;' % (destination, axis, source, axis)
            for axis in 'xyz'))
    return body


def scoped_colors(body):
    declarations = []
    for name in ('primitive', 'environment'):
        line = '    s16 %sR, %sG, %sB, %sA;\n' % ((name,) * 4)
        assert line in body
        declarations.append(line.replace('    ', '            ', 1))
        body = body.replace(line, '')
    body = body.replace('        func_151441A4(', '        {\n' + ''.join(declarations) + '        func_151441A4(', 1)
    body = body.replace('        output = func_1513F4E4(', '        }\n        output = func_1513F4E4(', 1)
    return body


def nested_private_colors(body):
    first = 'output = func_15142B7C(output, *(u32 *)(payload + 0x2C), *(u32 *)(payload + 0x30));'
    second = 'output = func_15142C10(output, environmentR, environmentG, environmentB, environmentA, &sync);'
    third = 'output = func_15142CF0(output, 0, 0, primitiveR, primitiveG, primitiveB, primitiveA, &sync);'
    assert all(line in body for line in (first, second, third))
    inner = first[len('output = '):-1]
    middle = second[len('output = '):-1].replace('(output,', '(' + inner + ',', 1)
    outer = third.replace('(output,', '(' + middle + ',', 1)
    return body.replace(first + '\n        ' + second + '\n        ' + third, outer)


def candidates():
    forms = dict(fitting.candidates())
    stride = dict(lifetime.candidates())['inline-local-stride']
    for name, body in (('selected', base.SELECTED), ('stride', stride),
            ('mixed', forms['selected-mixed-deltaY-deltaZ-rayX-deltaX'])):
        for arrays in (False, True):
            colors = grouped_colors(body, arrays)
            label = name + ('-color-array' if arrays else '-color-struct')
            yield label, colors
            yield label + '-positions', grouped_positions(colors)
        yield name + '-scoped-colors', scoped_colors(body)
        yield name + '-nested-private-colors', nested_private_colors(body)
        yield name + '-field-positions', field_positions(body)
        yield name + '-field-positions-colors', grouped_colors(field_positions(body))
    for name in ('outer-active', 'outer-indexed'):
        body = forms[name + '-mixed-deltaY-deltaZ-rayX-deltaX']
        yield name + '-mixed-color-struct', grouped_colors(body)
        yield name + '-mixed-nested-private-colors', nested_private_colors(body)
    for name, body in (('selected', base.SELECTED),
            ('outer-active', dict(base.candidates())['outer-active']),
            ('outer-indexed', dict(base.candidates())['outer-indexed'])):
        for targets in (('deltaY', 'deltaZ', 'rayX'), ('deltaX', 'deltaY', 'deltaZ'), ('rayX', 'rayY', 'rayZ')):
            shared = body.replace('    f32 offsetX, offsetY, offsetZ;\n', '').replace('f32 length, scale;', 'f32 length;')
            for axis, target in zip('XYZ', targets):
                shared = shared.replace('offset' + axis, target)
            factor = targets[-1]
            shared = shared.replace('scale =', factor + ' =').replace('* scale;', '* ' + factor + ';')
            label = name + '-last-output-scale-' + '-'.join(targets)
            yield label, shared
            yield label + '-positions', grouped_positions(shared)
            yield label + '-fields', field_positions(shared)
            if targets == ('deltaX', 'deltaY', 'deltaZ'):
                for parameter in (False, True):
                    context = lifetime.context_lifetime(shared, parameter)
                    yield label + ('-parameter-context' if parameter else '-local-context'), context


def decompiler_context():
    primitive = '''typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
typedef struct { struct { s16 ob[3]; u16 flag; s16 tc[2]; u8 cn[4]; } v; } Vtx;
typedef struct { struct { u32 w0, w1; } words; } Gfx;
'''
    declarations = base.DECLARATIONS.replace('f32 *func_15144B34(s32);',
        'CameraRibbonOrigin *func_15144B34(s32);')
    record, helpers = declarations.split('extern u8 D_800BE9C0;', 1)
    return primitive + record + lifetime.TYPES + STACK + 'extern u8 D_800BE9C0;' + helpers + \
        'Gfx *func_1514803C(CameraRibbonActor *, Gfx *, s16);\nf32 sqrtf(f32);\n'


def decompile(root, output):
    output.mkdir(parents=True, exist_ok=True)
    context = output / 'typed-stack-context.c'
    context.write_text(decompiler_context())
    result = subprocess.run([sys.executable, str(root / 'conker/tools/mips_to_c/m2c.py'),
        '--context', str(context), '--no-cache', '--globals', 'none',
        '--reg-vars', 's3,f2,f12,f14,f16,f18,f20,f22,f24,f26', '-f', base.FUNCTION,
        str(root / 'conker/asm/nonmatchings/generated_175250/func_1514803C.s')],
        cwd=root, capture_output=True, text=True, check=True)
    (output / 'typed-decompiler.txt').write_text(result.stdout)
    (output / 'typed-decompiler.stderr').write_text(result.stderr)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--decompiler', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-stackfit'
    if args.decompiler:
        text = decompile(root, output)
        print('Typed decompiler evidence retained; output is not installed or compiled.', len(text))
        return
    forms = dict(candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    results = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, output, name, body)
        meta['saved_gpr'] = [(w >> 16 & 31, w & 65535) for w in words[:30]
            if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
            and (w & 65535) < meta['frame']]
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        results.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], meta['saved_gpr'], meta['saved_FP'], flush=True)
    (output / ((args.form or 'all') + '.json')).write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
