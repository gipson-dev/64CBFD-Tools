"""Measure complete ribbon ray outputs and shared view/texture/stride lifetimes."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_representation as representation


def ray_outputs(body, factor='deltaX'):
    zero = 'deltaX = deltaY = deltaZ = 0.0f;'
    before = 'deltaZ = *(f32 *)payload / length;\n{pad}deltaX = normalX * deltaZ;\n' \
        '{pad}deltaY = normalY * deltaZ;\n{pad}deltaZ = normalZ * deltaZ;'
    after = factor + ' = *(f32 *)payload / length;\n{pad}rayX = normalX * ' + factor + ';\n' \
        '{pad}rayY = normalY * ' + factor + ';\n{pad}rayZ = normalZ * ' + factor + ';'
    assert body.count(zero) == 2
    body = body.replace(zero, 'rayX = rayY = rayZ = 0.0f;')
    for indent in (12, 16):
        old = before.format(pad=' ' * indent)
        assert body.count(old) == 1
        body = body.replace(old, after.format(pad=' ' * indent))
    for axis in 'XYZ':
        for sign in ('+', '-'):
            body = body.replace(sign + ' delta' + axis + ')', sign + ' ray' + axis + ')')
    return body


def cursor_color_scope(body, group='normal'):
    lines = [line for line in body.splitlines(True) if line.startswith(('    s16 primitive',
        '    s16 environment', '    f32 ' + group, '    f32 length;'))]
    assert len(lines) == 4
    for line in lines:
        body = body.replace(line, '')
    return body.replace('    if (cursor != NULL) {\n',
        '    if (cursor != NULL) {\n' + ''.join('    ' + line for line in lines), 1)


def candidates():
    original = dict(representation.candidates())['typed-gfx-cursor-local-colors-normals-length']
    seeds = [('color-homes', original)]
    seeds += [('ray-output-' + factor, ray_outputs(original, factor)) for factor in ('deltaX', 'length')]
    mixed = dict(representation.flow.candidates())['mixed-outer']
    seeds += [('mixed-color-homes-' + group, cursor_color_scope(mixed, group))
        for group in ('normal', 'ray', 'delta')]
    for name, body in seeds:
        yield name, body
        yield name + '-phase', representation.flow.phase_lifetime(body)
        yield name + '-phase-stride', representation.flow.phase_lifetime(body, stride=True)


def compile_form(root, output, name, body):
    return representation.compile_form(root, output, name, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-registers'
    forms = dict(candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    records = []
    for name, body in forms.items():
        meta, words = compile_form(root, output, name, body)
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        meta['saved_gpr'] = [(w >> 16 & 31, w & 65535) for w in words[:30]
            if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
            and (w & 65535) < meta['frame']]
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_gpr'], meta['saved_FP'], flush=True)
    (output / ((args.form or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
