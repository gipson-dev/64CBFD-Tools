"""Fit complete camera ribbon private lifetimes without installing production C."""

import argparse
import json
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_candidates as base


def reuse(body, offset=True, scale=True):
    if offset:
        body = body.replace('    f32 offsetX, offsetY, offsetZ;\n', '')
        for axis in 'XYZ':
            body = body.replace('offset' + axis, 'ray' + axis)
    if scale:
        body = body.replace('f32 length, scale;', 'f32 length;').replace('scale =', 'length =').replace('* scale;', '* length;')
    return body


def candidates():
    forms = dict(base.candidates())
    for name in ('selected', 'indexed-seed', 'single-gate', 'outer-active', 'outer-indexed'):
        for offset, scale in ((True, True), (True, False), (False, True)):
            body = reuse(forms[name], offset, scale)
            yield '%s-reuse-%d-%d' % (name, offset, scale), body
            if offset and scale:
                yield name + '-reuse-separate-zero', body.replace('rayX = rayY = rayZ = 0.0f;',
                    'rayX = 0.0f; rayY = 0.0f; rayZ = 0.0f;')
                for variable in ('records', 'payload', 'origin', 'texture', 'previousIndex', 'view'):
                    old = next(line for line in body.splitlines() if ';' in line and
                        ((' ' + variable + ';' in line) or ('*' + variable + ';' in line))) if variable != 'view' else None
                    altered = body.replace(old, old.replace('    ', '    register ', 1), 1) if old else body.replace(
                        's16 view)', 'register s16 view)')
                    yield name + '-reuse-register-' + variable, altered
                shared = body.replace('    s32 texture;\n', '').replace('texture =', 'previousIndex =').replace(
                    'texture !=', 'previousIndex !=').replace('= texture;', '= previousIndex;')
                yield name + '-reuse-texture-index', shared
                shared_view = shared.replace('    s32 previousIndex;', '    s32 previousIndex;\n    s32 context;').replace(
                    '        origin = func_15144B34(view);', '        context = view;\n        origin = func_15144B34(context);').replace(
                    'previousIndex = func_1514306C', 'context = func_1514306C').replace('previousIndex != D_800DD1B0',
                    'context != D_800DD1B0').replace('D_800DD1B0 = previousIndex;', 'D_800DD1B0 = context;')
                yield name + '-reuse-context', shared_view
    for name in ('selected', 'indexed-seed', 'outer-active', 'outer-indexed'):
        for targets in (('deltaY', 'deltaZ', 'rayX'), ('deltaX', 'deltaY', 'deltaZ'),
                ('normalX', 'normalY', 'normalZ')):
            for factor in ('length', 'deltaX', 'rayY'):
                if factor in targets:
                    continue
                body = forms[name].replace('    f32 offsetX, offsetY, offsetZ;\n', '')
                for axis, target in zip('XYZ', targets):
                    body = body.replace('offset' + axis, target)
                body = body.replace('f32 length, scale;', 'f32 length;').replace('scale =', factor + ' =').replace('* scale;', '* ' + factor + ';')
                yield name + '-mixed-' + '-'.join(targets) + '-' + factor, body
    for name in ('selected', 'indexed-seed', 'outer-active', 'outer-indexed'):
        for factor in ('length', 'deltaX', 'rayY'):
            body = forms[name].replace('    f32 normalX, normalY, normalZ;\n', '').replace('f32 length, scale;', 'f32 length;')
            for axis in 'XYZ':
                body = body.replace('normal' + axis, 'offset' + axis)
            body = body.replace('scale =', factor + ' =').replace('* scale;', '* ' + factor + ';')
            yield name + '-late-offsets-' + factor, body
        inlined = forms[name].replace('    f32 rayX, rayY, rayZ;\n', '')
        for axis, index in zip('XYZ', range(3)):
            for position in ('previous', 'current'):
                inlined = inlined.replace('            ray%s = %s.%s - origin[%d];\n' % (axis, position, axis.lower(), index), '')
                inlined = inlined.replace('        ray%s = %s.%s - origin[%d];\n' % (axis, position, axis.lower(), index), '')
        first, loop = inlined.split('        do {\n', 1)
        for axis, index in zip('XYZ', range(3)):
            first = first.replace('ray' + axis, '(previous.%s - origin[%d])' % (axis.lower(), index))
            loop = loop.replace('ray' + axis, '(current.%s - origin[%d])' % (axis.lower(), index))
        inlined = first + '        do {\n' + loop
        yield name + '-inline-rays', inlined
        yield name + '-inline-rays-length', reuse(inlined, offset=False, scale=True)
        for kind in ('u8', 'u32', 's32'):
            byte = inlined.replace('CameraRibbonRecord *records;', kind + ' ' + ('*' if kind == 'u8' else '') + 'records;').replace(
                'records = *(CameraRibbonRecord **)', 'records = *(' + kind + (' **)' if kind == 'u8' else ' *)'))
            byte = byte.replace('records + previousIndex', '(CameraRibbonRecord *)(records + previousIndex * 20)').replace(
                'records + index', '(CameraRibbonRecord *)(records + index * 20)').replace(
                'records[previousIndex].position', '*(CameraRibbonPosition *)(records + previousIndex * 20)').replace(
                'records[previousIndex].phase', '*(u16 *)(records + previousIndex * 20 + 16)')
            yield name + '-inline-rays-records-' + kind, byte


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--mixed', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-fitting'
    output.mkdir(parents=True, exist_ok=True)
    forms = dict(candidates())
    if args.mixed:
        forms = {name: body for name, body in forms.items() if '-mixed-' in name}
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    results = []
    for name, body in forms.items():
        meta, _ = base.compile_candidate(root, output, name, body)
        results.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / ((args.form or ('mixed' if args.mixed else 'all')) + '.json')).write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__': main()
