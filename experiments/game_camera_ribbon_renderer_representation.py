"""Measure complete ribbon pointer and local representations; no installation."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_controlflow as flow
from tools.experiments import game_camera_ribbon_renderer_lifetimes as lifetime
from tools.experiments import game_camera_ribbon_renderer_stackfit as stackfit


def byte_callback(body, capture=False):
    body = body.replace('Gfx *func_1514803C(u8 *actor, Gfx *output,',
        'u8 *func_1514803C(u8 *actor, u8 *output,')
    assert 'u8 *func_1514803C(u8 *actor, u8 *output,' in body
    if capture:
        body = body.replace('    Vtx *cursor;', '    Gfx *packet;\n    Vtx *cursor;', 1)
    for helper in ('func_150950D4', 'func_15142B7C', 'func_15142C10', 'func_15142CF0',
            'func_1513F4E4', 'func_15142FBC'):
        body = body.replace('output = ' + helper + '(output,',
            'output = (u8 *)' + helper + '((Gfx *)output,')
    for command in ('gSPVertex', 'gSP1Triangle'):
        token = '            ' + command + '(output++,'
        assert token in body
        replacement = ('            packet = (Gfx *)output;\n'
            '            output += sizeof(Gfx);\n            ' + command + '(packet,') if capture else \
            '            ' + command + '((Gfx *)output,'
        lines = body.splitlines(True)
        for index in reversed([i for i, line in enumerate(lines) if token in line]):
            lines[index] = lines[index].replace(token, replacement)
            if not capture:
                lines.insert(index + 1, '            output += sizeof(Gfx);\n')
        body = ''.join(lines)
    return body


def indexed_records(body):
    body = body.replace('    CameraRibbonRecord *prior;\n', '')
    body = body.replace('        prior = records + previousIndex;\n', '')
    return body.replace('prior->', 'records[previousIndex].')


def byte_records(body):
    body = body.replace('CameraRibbonRecord *records;', 'u8 *records;')
    body = body.replace('records = *(CameraRibbonRecord **)', 'records = *(u8 **)')
    body = body.replace('records + previousIndex',
        '(CameraRibbonRecord *)(records + previousIndex * sizeof(CameraRibbonRecord))')
    body = body.replace('records + index',
        '(CameraRibbonRecord *)(records + index * sizeof(CameraRibbonRecord))')
    body = body.replace('records[previousIndex].position',
        '((CameraRibbonRecord *)(records + previousIndex * sizeof(CameraRibbonRecord)))->position')
    body = body.replace('records[previousIndex].phase',
        '((CameraRibbonRecord *)(records + previousIndex * sizeof(CameraRibbonRecord)))->phase')
    return body


def candidates():
    selected = dict(flow.candidates())['selected-outer']
    for name, convert in (('typed-gfx', lambda body: body), ('byte-callback', byte_callback),
            ('byte-callback-capture', lambda body: byte_callback(body, capture=True))):
        yield name, convert(selected)
        yield name + '-indexed-records', convert(indexed_records(selected))
        yield name + '-byte-records', convert(byte_records(selected))
        yield name + '-indexed-byte-records', convert(byte_records(indexed_records(selected)))
        yield name + '-typed-payload', convert(lifetime.typed_fields(selected, actor=False))
        yield name + '-color-array', convert(stackfit.grouped_colors(selected, arrays=True))
        yield name + '-color-struct', convert(stackfit.grouped_colors(selected))
        yield name + '-scoped-colors', convert(stackfit.scoped_colors(selected))
        declarations = [line for line in selected.splitlines(True) if line.startswith('    s16 primitive') or
            line.startswith('    s16 environment')]
        early = selected
        for line in declarations:
            early = early.replace(line, '')
        early = early.replace('    Vtx *cursor;', ''.join(declarations) + '    Vtx *cursor;', 1)
        yield name + '-early-colors', convert(early)
        for groups in (('colors',), ('colors', 'floats'), ('colors', 'pointers'),
                ('colors', 'indices'), ('colors', 'floats', 'pointers', 'indices'),
                ('colors', 'normals', 'length'), ('colors', 'rays', 'length'),
                ('colors', 'deltas', 'length')):
            lines = [line for line in selected.splitlines(True) if
                ('colors' in groups and line in declarations) or
                ('floats' in groups and line.startswith('    f32 ') and '*' not in line) or
                ('normals' in groups and line.startswith('    f32 normal')) or
                ('rays' in groups and line.startswith('    f32 ray')) or
                ('deltas' in groups and line.startswith('    f32 delta')) or
                ('length' in groups and line.startswith('    f32 length;')) or
                ('pointers' in groups and line.startswith(('    CameraRibbonRecord *', '    f32 *origin;'))) or
                ('indices' in groups and line.startswith(('    s32 index;', '    s32 previousIndex;')))]
            scoped = selected
            for line in lines:
                scoped = scoped.replace(line, '')
            scoped = scoped.replace('    if (cursor != NULL) {\n',
                '    if (cursor != NULL) {\n' + ''.join('    ' + line for line in lines), 1)
            yield name + '-cursor-local-' + '-'.join(groups), convert(scoped)


def compile_form(root, output, name, body):
    return flow.compile_form(root, output, name, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--scope-quartets', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-representation'
    forms = dict(candidates())
    if args.scope_quartets:
        forms = {name: body for name, body in forms.items()
            if name.endswith(('-normals-length', '-rays-length', '-deltas-length'))}
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    results = []
    for name, body in forms.items():
        meta, words = compile_form(root, output, name, body)
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        meta['saved_gpr'] = [(w >> 16 & 31, w & 65535) for w in words[:30]
            if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
            and (w & 65535) < meta['frame']]
        color = words.index(0x0D451069)
        meta['primitive_addresses'] = [w & 65535 for w in words[color - 20:color]
            if w >> 26 == 9 and w >> 21 & 31 == 29 and 4 <= w >> 16 & 31 <= 7]
        results.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_gpr'], meta['saved_FP'], list(map(hex, meta['primitive_addresses'])), flush=True)
    (output / ((args.form or ('scope-quartets' if args.scope_quartets else 'all')) + '.json')).write_text(
        json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
