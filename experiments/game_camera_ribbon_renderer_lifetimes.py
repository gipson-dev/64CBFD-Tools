"""Fit the complete renderer's view/texture/stride and scalar lifetimes."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_candidates as base
from tools.experiments import game_camera_ribbon_renderer_fitting as fitting


TYPES = '''typedef struct {
    f32 width;
    u8 reserved04[0x14];
    u8 flags, textureIndex, intensity, channel;
    u8 reserved1C[0xC];
    u32 renderMode, geometrySet, geometryClear;
    s32 combineIndex;
    u8 reserved38[3], combineKind;
    u32 render0, render1;
    s8 primitiveMode, environmentMode;
} CameraRibbonPayload;
typedef struct {
    u8 reserved00[0x25];
    u8 count;
    u8 reserved26[6];
    s8 active, start, head;
    u8 reserved2F[0x55];
    u8 vertexSlots[0x10];
    CameraRibbonRecord *records;
    CameraRibbonPayload *payload;
} CameraRibbonActor;
'''


def typed_fields(body, actor=True, payload=True):
    if actor:
        body = body.replace('u8 *actor,', 'CameraRibbonActor *actor,').replace(
            '*(s8 *)(actor + 0x2C)', 'actor->active').replace('actor + 0x84', 'actor->vertexSlots').replace(
            'actor[0x25]', 'actor->count').replace('*(s8 *)(actor + 0x2E)', 'actor->head').replace(
            '*(s8 *)(actor + 0x2D)', 'actor->start').replace(
            '*(CameraRibbonRecord **)(actor + 0x94)', 'actor->records').replace(
            '*(u8 **)(actor + 0x98)', '(u8 *)actor->payload')
    if payload:
        body = body.replace('    u8 *payload;', '    CameraRibbonPayload *payload;')
        body = body.replace('(u8 *)actor->payload', 'actor->payload').replace(
            '*(u8 **)(actor + 0x98)', '*(CameraRibbonPayload **)(actor + 0x98)')
        for offset, name in ((0x18, 'flags'), (0x19, 'textureIndex'), (0x1A, 'intensity'),
                (0x1B, 'channel'), (0x3B, 'combineKind')):
            body = body.replace('payload[0x%X]' % offset, 'payload->' + name)
        for kind, offset, name in (('f32', '', 'width'), ('u32', '0x28', 'renderMode'),
                ('u32', '0x2C', 'geometrySet'), ('u32', '0x30', 'geometryClear'),
                ('s32', '0x34', 'combineIndex'), ('u32', '0x3C', 'render0'),
                ('u32', '0x40', 'render1'), ('s8', '0x44', 'primitiveMode'),
                ('s8', '0x45', 'environmentMode')):
            expression = ('*(%s *)(payload + %s)' % (kind, offset)) if offset else '*(f32 *)payload'
            body = body.replace(expression, 'payload->' + name)
    return TYPES + body


def context_lifetime(body, parameter=False):
    body = body.replace('    s32 texture;\n', '')
    if parameter:
        body = body.replace('s16 view)', 's32 view)').replace(
            '    payload =', '    view = (s16)view;\n    payload =', 1)
        name = 'view'
    else:
        body = body.replace('    s32 previousIndex;\n', '    s32 previousIndex;\n    s32 context;\n').replace(
            '    payload =', '    context = view;\n    payload =', 1)
        body = body.replace('actor + 0x84, view,', 'actor + 0x84, (s16)context,').replace(
            'func_15144B34(view)', 'func_15144B34(context)')
        name = 'context'
    body = body.replace('texture =', name + ' =').replace('texture !=', name + ' !=').replace(
        '= texture;', '= ' + name + ';')
    return body


def candidates():
    forms = dict(fitting.candidates())
    for name, body in (('selected', base.SELECTED),
            ('inline', forms['selected-inline-rays']), ('outer-inline', forms['outer-indexed-inline-rays'])):
        yield name + '-register-view', body.replace('s16 view)', 'register s16 view)')
        for parameter in (False, True):
            shared = context_lifetime(body, parameter)
            label = name + ('-parameter-context' if parameter else '-local-context')
            yield label, shared
            if parameter:
                registered = shared.replace('s32 view)', 'register s32 view)')
            else:
                registered = shared.replace('    s32 context;', '    register s32 context;')
            yield label + '-register', registered
        registered = body
        for line in body.splitlines():
            if line.startswith('    f32 ') and '*' not in line:
                registered = registered.replace(line, line.replace('    ', '    register ', 1), 1)
        yield name + '-register-scalars', registered
    for name, body in (('selected', base.SELECTED), ('inline', forms['selected-inline-rays'])):
        split = body.replace('    f32 length, scale;\n', '    f32 length;\n    f32 scale;\n')
        groups = [line for line in split.splitlines(True) if line.startswith('    f32 ') and '*' not in line]
        for group in groups:
            relocated = split.replace(group, '').replace('    s16 primitiveR', group + '    s16 primitiveR', 1)
            yield name + '-early-' + group.strip().replace('f32 ', '').replace(';', '').replace(', ', '-'), relocated
        for label, names in (('ray-delta-length', ('ray', 'delta', 'length')),
                ('delta-normal-length', ('delta', 'normal', 'length')),
                ('normal-offset-length', ('normal', 'offset', 'length')),
                ('all-float', ('ray', 'delta', 'normal', 'length', 'scale', 'offset'))):
            selected = [line for line in groups if any(line.startswith('    f32 ' + variable) for variable in names)]
            relocated = split
            for group in selected:
                relocated = relocated.replace(group, '')
            relocated = relocated.replace('    s16 primitiveR', ''.join(selected) + '    s16 primitiveR', 1)
            yield name + '-early-' + label, relocated
        early_index = body.replace('            previousIndex = index;\n            index--;\n', '').replace(
            '        do {\n', '        do {\n            previousIndex = index;\n            index--;\n', 1)
        yield name + '-early-index-step', early_index
        for parameter in (False, True):
            shared = context_lifetime(body, parameter)
            variable = 'view' if parameter else 'context'
            shared = shared.replace('        index = previousIndex - 1;',
                '        %s = sizeof(CameraRibbonRecord);\n        index = previousIndex - 1;' % variable)
            shared = shared.replace('records + previousIndex',
                '(CameraRibbonRecord *)((u8 *)records + previousIndex * %s)' % variable).replace(
                'records + index', '(CameraRibbonRecord *)((u8 *)records + index * %s)' % variable).replace(
                'records[previousIndex].position',
                '*(CameraRibbonPosition *)((u8 *)records + previousIndex * %s)' % variable)
            yield name + ('-parameter-stride' if parameter else '-local-stride'), shared
        reversed_scale = body.replace('offsetX = normalX * scale;\n', 'OFFSET_X\n').replace(
            'offsetZ = normalZ * scale;', 'offsetX = normalX * scale;').replace(
            'OFFSET_X', 'offsetZ = normalZ * scale;')
        yield name + '-reversed-scale', reversed_scale
        for label, prefix in (('rays', ('ray',)), ('cross', ('ray', 'delta', 'normal', 'length', 'scale'))):
            declarations = [line for line in body.splitlines(True)
                if line.startswith('    f32 ') and '*' not in line
                and any(line.startswith('    f32 ' + p) for p in prefix)]
            first, loop = body.split('        do {\n', 1)
            names = [part.strip() for line in declarations
                for part in line.strip()[4:-1].split(',')]
            for variable in names:
                loop = loop.replace(variable, 'loop_' + variable)
            local = ''.join(line.replace('    ', '            ', 1) for line in declarations)
            for variable in names:
                local = local.replace(variable, 'loop_' + variable)
            yield name + '-separate-loop-' + label, first + '        do {\n' + local + loop
        for actor, payload in ((True, False), (False, True), (True, True)):
            yield '%s-typed-%d-%d' % (name, actor, payload), typed_fields(body, actor, payload)
        captured = body.replace('    Vtx *cursor;', '    Gfx *packet;\n    Vtx *cursor;')
        for command in ('gSPVertex', 'gSP1Triangle'):
            captured = captured.replace('            ' + command + '(output++,',
                '            packet = output++;\n            ' + command + '(packet,')
        yield name + '-captured-packet', captured
    mixed = forms['selected-mixed-deltaY-deltaZ-rayX-deltaX']
    for label, body in (('selected', base.SELECTED), ('mixed', mixed)):
        first, loop = body.split('        do {\n', 1)
        loop = loop.replace('            previousIndex = index;\n            index--;\n', '')
        loop = loop.replace('            rayX = current.x - origin[0];\n',
            '            rayX = current.x - origin[0];\n            previousIndex = index;\n').replace(
            '            rayY = current.y - origin[1];\n',
            '            rayY = current.y - origin[1];\n            index--;\n')
        split = first + '        do {\n' + loop
        yield label + '-split-index-step', split
        if label == 'mixed':
            yield label + '-split-separate-zero', split.replace('deltaY = deltaZ = rayX = 0.0f;',
                'deltaY = 0.0f; deltaZ = 0.0f; rayX = 0.0f;')
        yield label + '-split-typed', typed_fields(split)
        for groups in (('ray',), ('delta',), ('normal',), ('offset',), ('ray', 'delta', 'normal', 'offset')):
            grouped = body
            present = []
            for group in groups:
                declaration = '    f32 %sX, %sY, %sZ;\n' % (group, group, group)
                if declaration not in grouped:
                    continue
                present.append(group)
                grouped = grouped.replace(declaration, '    CameraRibbonPosition %sVector;\n' % group)
                for axis in 'XYZ':
                    grouped = grouped.replace(group + axis, group + 'Vector.' + axis.lower())
            if present:
                yield label + '-vector-' + '-'.join(present), grouped
        first, loop = body.split('        do {\n', 1)
        yield label + '-separate-loop-length', first + '        do {\n            f32 loopLength;\n' + loop.replace('length', 'loopLength')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-lifetimes'
    forms = dict(candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    receipts = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, output, name, body)
        meta['saved_gpr'] = [(word >> 16 & 31, word & 65535) for word in words[:30]
            if word >> 26 == 43 and word >> 21 & 31 == 29 and 16 <= word >> 16 & 31 <= 23
            and (word & 65535) < meta['frame']]
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        receipts.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_gpr'], meta['saved_FP'], flush=True)
    (output / ((args.form or 'all') + '.json')).write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
