"""Fit the complete renderer's view/texture/stride staging, without installation."""

import argparse
import hashlib
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_candidates as base
from tools.experiments import game_camera_ribbon_renderer_fitting as fitting
from tools.experiments import game_camera_ribbon_renderer_lifetimes as lifetime
from tools.experiments import game_camera_ribbon_renderer_stackfit as stackfit


def record_stride(body, variable):
    body = body.replace('        index = previousIndex - 1;',
        '        %s = sizeof(CameraRibbonRecord);\n        index = previousIndex - 1;' % variable)
    body = body.replace('records + previousIndex',
        '(CameraRibbonRecord *)((u8 *)records + previousIndex * %s)' % variable)
    body = body.replace('records + index',
        '(CameraRibbonRecord *)((u8 *)records + index * %s)' % variable)
    body = body.replace('records[previousIndex].position',
        '((CameraRibbonRecord *)((u8 *)records + previousIndex * %s))->position' % variable)
    body = body.replace('            point--;',
        '            point = (CameraRibbonRecord *)((u8 *)point - %s);' % variable)
    return body


def stride_context(body, parameter=False):
    return record_stride(lifetime.context_lifetime(body, parameter), 'view' if parameter else 'context')


def union_context(body, wide_view=False):
    body = body.replace('    s32 texture;', '    CameraRibbonPhase phase;')
    body = body.replace('    payload =', '    phase.view = view;\n    payload =', 1)
    body = body.replace('actor + 0x84, view,', 'actor + 0x84, (s16)phase.view,')
    body = body.replace('func_15144B34(view)', 'func_15144B34(phase.view)')
    body = body.replace('texture =', 'phase.texture =').replace('texture !=', 'phase.texture !=').replace(
        '= texture;', '= phase.texture;')
    body = record_stride(body, 'phase.stride')
    return 'typedef union { %s view; s32 texture, stride; } CameraRibbonPhase;\n' % (
        's32' if wide_view else 's16') + body


def compact_geometry(body, retain_rays=False):
    for declaration in ('    f32 rayX, rayY, rayZ;\n', '    f32 normalX, normalY, normalZ;\n',
            '    f32 length, scale;\n', '    f32 offsetX, offsetY, offsetZ;\n'):
        assert declaration in body
        body = body.replace(declaration, '')
    body = body.replace('    f32 deltaX, deltaY, deltaZ;\n',
        '    f32 deltaX, deltaY, deltaZ;\n    f32 normalX;\n')
    if retain_rays:
        body = body.replace('    f32 normalX;\n', '    f32 normalX;\n    f32 rayX, rayY, rayZ;\n')
    for point, indent in (('previous', 8), ('current', 12)):
        offset = '''deltaY = previous.y - current.y;
deltaZ = previous.z - current.z;
deltaX = previous.x - current.x;
normalX = deltaY * ({p}.z - origin[2]) - ({p}.y - origin[1]) * deltaZ;
deltaZ = deltaZ * ({p}.x - origin[0]) - ({p}.z - origin[2]) * deltaX;
deltaY = deltaX * ({p}.y - origin[1]) - ({p}.x - origin[0]) * deltaY;
deltaX = sqrtf(normalX * normalX + deltaZ * deltaZ + deltaY * deltaY);
if (deltaX == 0.0f) {{
    normalX = deltaZ = deltaY = 0.0f;
}} else {{
    deltaX = *(f32 *)payload / deltaX;
    normalX = normalX * deltaX;
    deltaZ = deltaZ * deltaX;
    deltaY = deltaY * deltaX;
}}
'''.format(p=point)
        if retain_rays:
            for axis, index in zip('XYZ', range(3)):
                offset = offset.replace('(%s.%s - origin[%d])' % (point, axis.lower(), index), 'ray' + axis)
            rays = ''.join('ray%s = %s.%s - origin[%d];\n' % (axis, point, axis.lower(), index)
                for axis, index in zip('XYZ', range(3)))
            offset = rays + offset
        before = ''.join(' ' * (indent - 4) + line for line in base.OFFSET.format(point=point).splitlines(True))
        after = ''.join(' ' * indent + line for line in offset.splitlines(True))
        assert body.count(before) == 1
        body = body.replace(before, after)
    for axis, value in zip('XYZ', ('normalX', 'deltaZ', 'deltaY')):
        body = body.replace('offset' + axis, value)
    return body


def candidates():
    forms = dict(stackfit.candidates())
    originals = dict(fitting.candidates())
    for name, body in (('selected', forms['selected-last-output-scale-deltaX-deltaY-deltaZ']),
            ('outer', forms['outer-active-last-output-scale-deltaX-deltaY-deltaZ']),
            ('retail-fp', originals['selected-mixed-deltaY-deltaZ-rayX-deltaX'])):
        for parameter in (False, True):
            yield name + ('-parameter-stride' if parameter else '-local-stride'), stride_context(body, parameter)
        for wide_view in (False, True):
            yield name + ('-union-wide' if wide_view else '-union-short'), union_context(body, wide_view)
        argument = body.replace('s16 view)', 's32 inputView)').replace('    Vtx *cursor;',
            '    s16 view;\n    Vtx *cursor;').replace('    payload =',
            '    view = (s16)inputView;\n    payload =', 1)
        yield name + '-wide-input-local-view', argument
        if name == 'selected':
            short_input = argument.replace('s32 inputView)', 's16 inputView)')
            yield 'selected-short-input-local-view', short_input
            callback = short_input.replace('Gfx *func_1514803C(u8 *actor, Gfx *output,',
                'u8 *func_1514803C(u8 *actor, u8 *commands,').replace('    s16 view;',
                '    Gfx *output;\n    s16 view;').replace('    view = (s16)inputView;',
                '    output = (Gfx *)commands;\n    view = (s16)inputView;').replace(
                'return output;', 'return (u8 *)output;')
            yield 'selected-callback-compatible', callback
            word_records = argument.replace('CameraRibbonRecord *records;', 'u32 records;').replace(
                'records = *(CameraRibbonRecord **)', 'records = *(u32 *)')
            word_records = word_records.replace('records + previousIndex',
                '(CameraRibbonRecord *)(records + previousIndex * 20)').replace('records + index',
                '(CameraRibbonRecord *)(records + index * 20)').replace('records[previousIndex].position',
                '*(CameraRibbonPosition *)(records + previousIndex * 20)')
            yield name + '-wide-input-word-records', word_records
    yield 'compact-geometry', compact_geometry(base.SELECTED)
    yield 'compact-retained-rays', compact_geometry(base.SELECTED, retain_rays=True)


def compile_form(root, output, name, body, profile='o2g3'):
    profiles = dict(base.PROFILES)
    profiles['o2g3-no-unroll'] = profiles['o2g3'] + ('-Wo,-loopunroll,0',)
    with patch.dict(base.PROFILES, profiles):
        return base.compile_candidate(root, output, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--profile', choices=('o2g3', 'o2', 'o2g3-no-unroll'), default='o2g3')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-staging'
    forms = dict(candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    records = []
    for name, body in forms.items():
        meta, words = compile_form(root, output, name + '-' + args.profile, body, args.profile)
        meta['saved_gpr'] = [(w >> 16 & 31, w & 65535) for w in words[:30]
            if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
            and (w & 65535) < meta['frame']]
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_gpr'], meta['saved_FP'], flush=True)
    (output / ((args.form or 'all') + '-' + args.profile + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
