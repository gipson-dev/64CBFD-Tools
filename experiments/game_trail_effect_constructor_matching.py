"""Complete source discriminators for the banked constructor's 61 differences."""

import itertools
import json
import re
from pathlib import Path

from tools.experiments import game_trail_effect_constructor_candidates as recovery


def field_candidates():
    body, types = recovery.SELECTED, recovery.SELECTED_TYPES
    kind = '    descriptor.kind = D_800AB3F4[selector];\n'
    alpha = '    descriptor.alpha = 255;\n'
    anchors = ('    descriptor.time = time;', '    descriptor.velocity =',
        '    descriptor.scale = scale;', '    descriptor.limit = D_800AB498;',
        '    firstContribution =', '    secondContribution =', '    flags =',
        '    flags |= 0x40;', '    descriptor.flags = flags;')
    for index, anchor in enumerate(anchors):
        for together in (False, True):
            edited = body.replace(kind, '')
            if together:
                edited = edited.replace(alpha, '')
            edited = edited.replace(anchor, kind + (alpha if together else '') + anchor, 1)
            yield 'kind-%d-both%d' % (index, together), edited, types
    payload = '    payload.first = first;\n    payload.second = second;\n    payload.selector = selector;\n'
    for order in itertools.permutations(payload.splitlines(keepends=True)):
        yield 'payload-' + ''.join(str(payload.splitlines(keepends=True).index(line)) for line in order), body.replace(payload, ''.join(order)), types


def control_candidates():
    body, types = recovery.SELECTED, recovery.SELECTED_TYPES
    controls = '    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;\n'
    for leading, element_type in itertools.product((False, True), ('s32', 'u8')):
        fields = '    %s firstFlag, secondFlag, fadeFlag, fadeAlpha;\n' % element_type
        render = '    TrailRender151DA6F8 render;\n'
        setup = 'typedef struct {\n' + (fields + render if leading else render + fields) + '} TrailSetup151DA6F8;\n'
        edited = body.replace(controls, '').replace(render, '    TrailSetup151DA6F8 setup;\n')
        for name in ('firstFlag', 'secondFlag', 'fadeFlag', 'fadeAlpha', 'render'):
            edited = re.sub(r'\b%s\b' % name, 'setup.' + name, edited)
        yield 'setup-first%d-%s' % (leading, element_type), edited, types + setup
    for flag_type, contribution_type in itertools.product(('u8', 's32'), ('u8', 's32')):
        fields = ('typedef struct {\n    %s firstFlag, secondFlag, fadeFlag, fadeAlpha;\n'
            '    %s firstContribution, secondContribution;\n} TrailControls151DA6F8;\n') % (flag_type, contribution_type)
        edited = body.replace(controls, '').replace('    s32 firstContribution, secondContribution;\n',
            '    TrailControls151DA6F8 controls;\n')
        for name in ('firstFlag', 'secondFlag', 'fadeFlag', 'fadeAlpha', 'firstContribution', 'secondContribution'):
            edited = re.sub(r'\b%s\b' % name, 'controls.' + name, edited)
        yield 'controls-%s-%s' % (flag_type, contribution_type), edited, types + fields


def array_candidates():
    for arrays in itertools.product((False, True), repeat=4):
        body = recovery.SELECTED
        for name, type_name, array in zip(('request', 'descriptor', 'payload', 'render'),
                ('TrailRequest151DA6F8', 'TrailDescriptor151DA6F8', 'TrailPayload151DA6F8', 'TrailRender151DA6F8'), arrays):
            if array:
                body = body.replace('%s %s;' % (type_name, name), '%s %s[1];' % (type_name, name))
                body = body.replace(name + '.', name + '[0].').replace('&' + name, '&' + name + '[0]').replace(
                    'sizeof(%s)' % name, 'sizeof(%s[0])' % name)
        yield 'arrays-' + ''.join(str(int(a)) for a in arrays), body, recovery.SELECTED_TYPES


def pointer_candidates():
    body, types = recovery.SELECTED, recovery.SELECTED_TYPES
    for type_name in ('void *', 'TrailPayload151DA6F8 *', 'u8 *'):
        edited = body.replace('    u8 *created;', '    u8 *created;\n    %s payloadPointer;' % type_name)
        edited = edited.replace('    if (created != NULL)',
            '    payloadPointer = (%s)&payload;\n    if (created != NULL)' % type_name).replace(
            '+ 0x48, &payload, sizeof(payload)', '+ 0x48, payloadPointer, sizeof(payload)')
        yield 'copy-pointer-' + type_name.split()[0], edited, types
    for before in (True, False):
        edited = body.replace('    u8 *created;', '    u8 *created;\n    u8 *copyDestination;')
        old = '        memcpy(*(u8 **)(created + 0x98) + 0x48, &payload, sizeof(payload));'
        new = '        copyDestination = *(u8 **)(created + 0x98) + 0x48;\n        memcpy(copyDestination, &payload, sizeof(payload));'
        edited = edited.replace(old, new)
        if before:
            edited = edited.replace('    u8 *created;\n    u8 *copyDestination;', '    u8 *copyDestination;\n    u8 *created;')
        yield 'copy-destination-first%d' % before, edited, types
    for record in ('payload', 'render', 'descriptor'):
        type_name = {'payload': 'TrailPayload151DA6F8', 'render': 'TrailRender151DA6F8',
            'descriptor': 'TrailDescriptor151DA6F8'}[record]
        edited = body.replace('    %s %s;' % (type_name, record), '    volatile %s %s;' % (type_name, record))
        if record == 'payload':
            edited = edited.replace('+ 0x48, &payload,', '+ 0x48, (const void *)&payload,')
        else:
            edited = edited.replace('&' + record, '(void *)&' + record)
        yield 'volatile-' + record, edited, types


def lifetime_candidates():
    body, types = recovery.SELECTED, recovery.SELECTED_TYPES
    kind = '    descriptor.kind = D_800AB3F4[selector];\n'
    for kind_early, payload_volatile, alias, scalar_register in itertools.product(
            (False, True), (False, True), ('position', 'velocity'), (False, True)):
        edited = body
        if kind_early:
            edited = edited.replace(kind, '').replace('    flags =', kind + '    flags =', 1)
        if payload_volatile:
            edited = edited.replace('    TrailPayload151DA6F8 payload;', '    volatile TrailPayload151DA6F8 payload;')
        edited = edited.replace('    if (created != NULL)',
            '    %s = (void *)&payload;\n    if (created != NULL)' % alias).replace(
            '+ 0x48, &payload, sizeof(payload)', '+ 0x48, ' + alias + ', sizeof(payload)')
        if scalar_register:
            edited = edited.replace('    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;',
                '    register s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;')
        yield 'lifetime-k%d-v%d-%s-r%d' % (kind_early, payload_volatile, alias, scalar_register), edited, types


def candidates():
    yield 'banked', recovery.SELECTED, recovery.SELECTED_TYPES
    yield from field_candidates()
    yield from control_candidates()
    yield from array_candidates()
    yield from pointer_candidates()
    yield from lifetime_candidates()


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-trail-effect-constructor-matching'
    records = []
    for name, body, types in candidates():
        meta, _ = recovery.compile_candidate(root, output, name, body, types)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
