"""Screen complete movement source carriers against the retail instruction order."""
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_frame as frame

source = frame.source
BUILD = 'conker/build/game-actor-input-movement-allocation'
PATHS, BASELINE = dict(frame.PATHS), dict(frame.BASELINE)
for key, path, sha in (
    ('movement_allocation_frame', 'tools/experiments/game_actor_input_movement_frame.py',
     '13e8cd793752ef8df55c076d43971379ed74865671c44f189dc47e9f82c5c30d'),
    ('movement_allocation_fitting_tests', 'tools/tests/test_game_actor_input_movement_fitting.py',
     'f32d58f3ee210b26b59a08f1359f46501722c064726cbc23e3345d71293088fa'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement allocation predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement allocation predecessor: ' + key)
        frozen = out / ('before-' + key)
        if not frozen.exists():
            frozen.write_bytes(data)
        if frozen.read_bytes() != data:
            raise ValueError('Changed movement allocation frozen input: ' + key)


def replace(body, before, after, count=1):
    if body.count(before) != count:
        raise ValueError('Changed movement source boundary: ' + before)
    return body.replace(before, after)


def explicit_link_index(body, name='index', first_only=False):
    first = '            record = (MovementActor34F4 *)(D_800CC2D0 + (actor->held - 100) * 0x32C);'
    second = ('                    record = (MovementActor34F4 *)(D_800CC2D0 +\n'
              '                              (actor->held - 100) * 0x32C);')
    sites = ((first, '            '),) if first_only else ((first, '            '), (second, '                    '))
    for before, indent in sites:
        body = replace(body, before,
                       indent + name + ' = actor->held - 100;\n' + indent +
                       'record = (MovementActor34F4 *)D_800CC2D0 + ' + name + ';')
    return body


def early_heading(body):
    before = ('        actor->desiredHeading = actor->yaw;\n'
              '        if (initialMagnitude > 1.0f) {\n'
              '            actor->desiredHeading = angle + D_800CC280;\n'
              '        }')
    after = ('        actor->desiredHeading = (u16)actor->yaw;\n'
             '        angle += D_800CC280;\n'
             '        if (initialMagnitude > 1.0f) {\n'
             '            actor->desiredHeading = angle;\n'
             '        }')
    return replace(body, before, after)


def nearby_indexed_fields(body, direct=False):
    before = ('                record = (MovementActor34F4 *)(D_800CC2D0 +\n'
              '                         D_800CC26D * 0x32C - 100 * 0x32C);\n'
              '                if (record->depth == 0.0f) {\n'
              '                    actor->verticalVelocity = 20.0f;\n'
              '                    actor->positionY = record->positionY + 70.0f;')
    after = ('                record = (MovementActor34F4 *)D_800CC2D0 + D_800CC26D;\n'
             '                if (record[-100].depth == 0.0f) {\n'
             '                    actor->verticalVelocity = 20.0f;\n'
             '                    actor->positionY = record[-100].positionY + 70.0f;')
    if direct:
        element = '((MovementActor34F4 *)D_800CC2D0)[D_800CC26D - 100]'
        after = ('                if (' + element + '.depth == 0.0f) {\n'
                 '                    actor->verticalVelocity = 20.0f;\n'
                 '                    actor->positionY = ' + element + '.positionY + 70.0f;')
    return replace(body, before, after)


def structural_forms():
    body = frame.fitted_body()
    named = replace(body, '    u32 heading;', '    u32 heading;\n    s32 heldIndex;')
    named = explicit_link_index(named, 'heldIndex')
    yield 'named-link-index', named
    yield 'nearby-indexed-fields', nearby_indexed_fields(body)
    yield 'named-link-nearby-fields', nearby_indexed_fields(named)
    for name, candidate in (('nearby-fields', nearby_indexed_fields(frame.global_controller_body())),
                            ('named-link-nearby', nearby_indexed_fields(named))):
        if name == 'named-link-nearby':
            candidate = replace(candidate, '    MovementInput34F4 *controller;\n', '')
            candidate = replace(candidate, '    controller = *D_800BE728;\n    D_800CC284 = controller;',
                                '    D_800CC284 = *D_800BE728;')
            candidate = replace(candidate, '        controller->x = 0;', '        D_800CC284->x = 0;')
        yield 'global-' + name, candidate
    yield 'named-link-nearby-heading', early_heading(nearby_indexed_fields(named))


def direct_forms():
    body = frame.fitted_body()
    named = replace(body, '    u32 heading;', '    u32 heading;\n    s32 heldIndex;')
    named = explicit_link_index(named, 'heldIndex')
    yield 'nearby-direct', nearby_indexed_fields(body, direct=True)
    yield 'named-link-nearby-direct', nearby_indexed_fields(named, direct=True)
    direct = nearby_indexed_fields(frame.global_controller_body(), direct=True)
    yield 'global-nearby-direct', direct
    yield 'global-named-link-nearby-direct', explicit_link_index(
        replace(direct, '    u32 heading;', '    u32 heading;\n    s32 heldIndex;'), 'heldIndex')


def pickup_forms():
    body = frame.global_controller_body()
    named = replace(body, '    u32 heading;', '    u32 heading;\n    s32 heldIndex;')
    named = explicit_link_index(named, 'heldIndex')
    for name, candidate in (('global-pickup-order', body), ('global-link-pickup-order', named)):
        candidate = nearby_indexed_fields(candidate, direct=True)
        before = ('                    actor->verticalVelocity = 20.0f;\n'
                  '                    actor->positionY = ((MovementActor34F4 *)D_800CC2D0)[D_800CC26D - 100].positionY + 70.0f;')
        after = ('                    actor->positionY = ((MovementActor34F4 *)D_800CC2D0)[D_800CC26D - 100].positionY + 70.0f;\n'
                 '                    actor->verticalVelocity = 20.0f;')
        yield name, replace(candidate, before, after)
    cached = nearby_indexed_fields(named, direct=True)
    cached = replace(cached, '    s32 heldIndex;', '    s32 heldIndex;\n    s32 nearbyIndex;')
    cached = replace(cached, '            if (D_800CC26D != 0 && actor->held == 0) {',
                     '            nearbyIndex = D_800CC26D;\n'
                     '            if (nearbyIndex != 0 && actor->held == 0) {')
    cached = replace(cached, '[D_800CC26D - 100]', '[nearbyIndex - 100]', 2)
    yield 'global-link-cached-nearby', cached


def first_link_forms():
    body = dict(pickup_forms())['global-pickup-order']
    for name in ('index', 'count', 'animation', 'heldIndex'):
        candidate = body
        if name == 'heldIndex':
            candidate = replace(candidate, '    u32 heading;', '    u32 heading;\n    s32 heldIndex;')
        yield 'first-link-' + name, explicit_link_index(candidate, name, first_only=True)


def release_speed_first(body):
    before = ('            record->heldBy = 0;\n'
              '            record->animation = 0x21;\n'
              '            record->state = 0;\n'
              '            record->disabled = 0;\n'
              '            record->flags &= ~0x400;\n'
              '            record->speed = actor->speed;')
    after = ('            record->heldBy = 0;\n'
             '            record->speed = actor->speed;\n'
             '            record->animation = 0x21;\n'
             '            record->state = 0;\n'
             '            record->disabled = 0;\n'
             '            record->flags &= ~0x400;')
    return replace(body, before, after)


def combined_forms():
    bodies = dict(first_link_forms())
    for name in ('heldIndex', 'animation'):
        body = bodies['first-link-' + name]
        yield 'first-' + name + '-heading', early_heading(body)
    body = bodies['first-link-heldIndex']
    yield 'first-heldIndex-release-speed', release_speed_first(body)
    yield 'first-heldIndex-heading-release-speed', release_speed_first(early_heading(body))
    yield 'global-pickup-release-speed', release_speed_first(dict(pickup_forms())['global-pickup-order'])


def early_return(body):
    return replace(body, '    } else if (actor->mode == 0) {',
                   '        return;\n    }\n    if (actor->mode == 0) {')


def return_forms():
    bodies = dict(combined_forms())
    for name in ('first-heldIndex-release-speed', 'first-heldIndex-heading-release-speed',
                 'global-pickup-release-speed'):
        yield name + '-return', early_return(bodies[name])


SELECTED_NAME = 'first-heldIndex-heading-release-speed'
SELECTED_SHA = 'b87c2558ec5faccd9da9c0214da280fcc06cfbc5e16a152a067ea4732f95e181'


def selected_body():
    body = dict(combined_forms())[SELECTED_NAME]
    return replace(body, '        angle += D_800CC280;',
                   '        angle = (u16)((u32)angle + (u32)D_800CC280);')


def capture(root, out, name=SELECTED_NAME, body=None):
    body = selected_body() if body is None else body
    expected, words, row = measure(root, out, name, body)

    def compile_candidate(root, work, label, body):
        obj, diagnostics = source.compile_owner(root, work, frame.isolated(body), label)
        if diagnostics or source.parts(obj) != source.parts(expected):
            raise ValueError('Movement isolated trace changed diagnostics/words/relocations')
        _, functions, _ = source.parse_object(obj)
        if set(functions) != {source.FUNCTION}:
            raise ValueError('Extra isolated movement procedure')
        isolated = source.linked(root, work, obj, label + '-linked')
        if isolated != words:
            raise ValueError('Movement isolated linking changed words')
        return dict(words=row['words'], frame=row['frame'], raw_sha=row['raw_sha'],
                    whole_owner_target_identical=True), isolated

    with patch.object(frame.shared, 'screen', SimpleNamespace(compile_candidate=compile_candidate)):
        record = frame.shared.trace(root, out / 'traces', name, body)
    work = out / 'traces' / name
    content = (work / 'baseline.c').read_text()
    if content != frame.isolated(body):
        raise ValueError('Movement captured source differs')
    record.update(source_sha=hashlib.sha256(content.encode()).hexdigest(),
                  whole_owner_target_identical=True)
    (work / 'allocation-summary.json').write_text(json.dumps(record, indent=2) + '\n')
    freeze(root, out)
    return record, words


def allocation_facts(record, words):
    if record.get('code_unchanged') is not True or record.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement allocation capture')
    if record.get('compiler_sha256') != frame.shared.COMPILERS:
        raise ValueError('Changed movement allocation compiler fingerprints')
    rows = record['records']['optimizer']
    ranges = [r['words'][1:] for r in rows if r['name'] == 'regs']
    indirect = next(i for i, r in enumerate(rows) if r['name'] == 'ilod')
    if rows[indirect]['dtype'] != 'A' or rows[indirect]['length'] != 4:
        raise ValueError('Changed initial controller wire operand')
    assigned = rows[indirect + 1]
    controller = {k: assigned[k] for k in ('name', 'dtype', 'storage', 'offset', 'block', 'length')}
    constants = [dict(register=r['words'][1], dtype=r['dtype'], bits=r['constants'][0])
                 for r in rows if r['name'] == 'rldc' and r['dtype'] in ('A', 'J')]
    return dict(register_ranges=ranges, initial_controller_assignment=controller,
                initial_machine_controller_register=words[17] >> 16 & 31,
                constant_carriers=constants, no_original_source_or_allocator_claim=True)


def check_allocation(record, words, kind):
    if kind not in ('selected', 'global-controller'):
        raise ValueError('Unknown qualified movement allocation form')
    facts = allocation_facts(record, words)
    selected = kind == 'selected'
    count, controller = (8, 10) if selected else (9, 11)
    constants = [dict(register=8, dtype='J', bits=812)]
    if not selected:
        constants.append(dict(register=9, dtype='A', bits=0xFFFEC2D0))
    constants = constants * 2 + [dict(register=3, dtype='J', bits=37)]
    if (facts['register_ranges'] != [[1, count, 2], [2, 1, 16], [3, 6, 44]]
            or facts['initial_controller_assignment'] != dict(name='str', dtype='A', storage='S',
                                                               offset=0, block=755, length=4)
            or facts['initial_machine_controller_register'] != controller
            or facts['constant_carriers'] != constants
            or len(words) != 959 or words[0] != 0x27BDFF80
            or (words[17], words[23], words[47]) !=
               (0x8F200000 | controller << 16, 0xAC20C284 | controller << 16,
                0xA0000002 | controller << 21)):
        raise ValueError('Changed movement reservation/controller/constant evidence')
    return facts


def revalidate_capture(root, out, name, body, kind):
    work = out / 'traces' / name
    record = json.loads((work / 'allocation-summary.json').read_text())
    if record.get('exit_code') != 0 or record.get('compiler_sha256') != frame.shared.fingerprints(root):
        raise ValueError('Changed movement capture completion or live compiler')
    content = (work / 'baseline.c').read_text()
    if content != frame.isolated(body) or hashlib.sha256(content.encode()).hexdigest() != record['source_sha']:
        raise ValueError('Changed movement capture source')
    observed = frame.shared.validate_observations(work, (work / 'debugger.txt').read_text())
    if any(record[key] != observed[key] for key in ('events', 'inputs', 'records')):
        raise ValueError('Changed movement capture wire observations')
    if source.parse_object(work / 'baseline.o') != source.parse_object(work / 'trace.o'):
        raise ValueError('Changed movement traced object')
    if source.normalized_pools(work / 'baseline.o') != source.normalized_pools(work / 'trace.o'):
        raise ValueError('Changed movement traced pools')
    raw, _ = source.parts(work / 'baseline.o')
    if source.parts(work / 'baseline.o') != source.parts(out / (name + '.o')):
        raise ValueError('Changed complete owner versus isolated capture')
    expected = SELECTED_SHA if kind == 'selected' else 'dbaf70063f8d6ce82a2b33781acd1722592f219030eb4cbb491ba451612fb053'
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Changed complete captured target')
    words = list(struct.unpack_from('>959I', source.projection.sections(work / 'baseline-linked.elf')['.text'][1]))
    return record, words, check_allocation(record, words, kind)


def forms():
    body = frame.fitted_body()
    yield 'fitted', body
    yield 'register-controller', replace(body, '    MovementInput34F4 *controller;',
                                        '    register MovementInput34F4 *controller;')
    integer = replace(body, '    MovementInput34F4 *controller;', '    u32 controllerAddress;')
    integer = replace(integer, '    controller = *D_800BE728;\n    D_800CC284 = controller;',
                      '    controllerAddress = (u32)*D_800BE728;\n'
                      '    D_800CC284 = (MovementInput34F4 *)controllerAddress;')
    integer = replace(integer, '        controller->x = 0;',
                      '        ((MovementInput34F4 *)controllerAddress)->x = 0;')
    yield 'integer-controller', integer
    yield 'expression-controller', replace(body,
        '    controller = *D_800BE728;\n    D_800CC284 = controller;',
        '    controller = (D_800CC284 = *D_800BE728);')
    yield 'global-local-controller', replace(body,
        '    controller = *D_800BE728;\n    D_800CC284 = controller;',
        '    D_800CC284 = *D_800BE728;\n    controller = D_800CC284;')
    record = replace(body, '    MovementInput34F4 *controller;\n', '')
    record = replace(record, '    controller = *D_800BE728;\n    D_800CC284 = controller;',
                     '    record = (MovementActor34F4 *)*D_800BE728;\n'
                     '    D_800CC284 = (MovementInput34F4 *)record;')
    record = replace(record, '        controller->x = 0;',
                     '        ((MovementInput34F4 *)record)->x = 0;')
    yield 'record-controller', record
    yield 'global-controller', frame.global_controller_body()
    yield 'explicit-link-index', explicit_link_index(body)
    yield 'explicit-link-count', explicit_link_index(body, 'count')
    yield 'early-heading', early_heading(body)
    yield 'unsigned-yaw-load', replace(body, 'actor->desiredHeading = actor->yaw;',
                                      'actor->desiredHeading = *(u16 *)&actor->yaw;')
    yield 'link-index-early-heading', early_heading(explicit_link_index(body))


def measure(root, out, name, body):
    freeze(root, out)
    obj, words, row = source.measure(root, out, name, body)
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first = next((i for i, (a, b) in enumerate(zip(words, truth)) if a != b), None)
    row.update(name=name, first_unequal_word=first,
               first_unequal_PC=None if first is None else source.ENTRY + first * 4,
               initial_controller_register=words[17] >> 16 & 31)
    return obj, words, row


def screens(root, out, group='basic', selected=None):
    rows = []
    for name, body in {'basic': forms, 'structural': structural_forms,
                       'direct': direct_forms, 'pickup': pickup_forms,
                       'first-link': first_link_forms, 'combined': combined_forms,
                       'returns': return_forms}[group]():
        if selected is not None and name != selected:
            continue
        _, _, row = measure(root, out, name, body)
        row = {key: value for key, value in row.items() if key != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    if not rows:
        raise ValueError('No complete movement forms selected')
    (out / (group + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('basic', 'structural', 'direct', 'pickup', 'first-link', 'combined', 'returns'), default='basic')
    parser.add_argument('--form')
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.capture:
        name = args.form or SELECTED_NAME
        bodies = {SELECTED_NAME: selected_body(), 'global-controller': frame.global_controller_body()}
        if name not in bodies:
            parser.error('Capture is qualified only for the selected form and global-controller control')
        record, words = capture(root, root / BUILD, name, bodies[name])
        _, _, facts = revalidate_capture(root, root / BUILD, name, bodies[name],
                                         'selected' if name == SELECTED_NAME else 'global-controller')
        print(json.dumps(facts, indent=2), flush=True)
    else:
        screens(root, root / BUILD, args.group, args.form)
