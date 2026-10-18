"""Measure the remaining movement coefficient and counter setup schedules."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_scalar_lifetimes as previous

source = previous.source
BUILD = 'conker/build/game-actor-input-movement-pitch-coefficient'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_coefficient_predecessor', 'tools/experiments/game_actor_input_movement_scalar_lifetimes.py',
     '2db9d8046e3715338303fb2cd696af9844a2ddbf98a2fd58b0a06450d64b7a25'),
    ('movement_coefficient_predecessor_tests', 'tools/tests/test_game_actor_input_movement_scalar_lifetimes.py',
     '93dbb38b1c786f72fcc38f78309cad330cc107f73932758f831693b2d253eb98'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement coefficient predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement coefficient predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement coefficient frozen input: ' + key)


replace = previous.replace
PITCH = ('            index = D_800CC284->y;\n'
         '            value = actor->valueB8;\n'
         '            actor->verticalVelocity = 0.0f;\n'
         '            actor->acceleration = 0.0f;\n'
         '            actor->valueB8 += (((f32)index - value) * D_800A19C4);')


def coefficient_block(snapshot, coefficient, early=False, compound=True):
    lines = ['            index = D_800CC284->y;',
             '            ' + snapshot + ' = actor->valueB8;']
    lines.insert(0 if early else 2, '            ' + coefficient + ' = D_800A19C4;')
    lines.extend(('            actor->verticalVelocity = 0.0f;',
                  '            actor->acceleration = 0.0f;'))
    expression = '(((f32)index - ' + snapshot + ') * ' + coefficient + ')'
    lines.append('            actor->valueB8 += ' + expression + ';' if compound else
                 '            actor->valueB8 = ' + snapshot + ' + ' + expression + ';')
    return '\n'.join(lines)


def role_forms():
    body = previous.selected_body()
    yield 'previous', body
    for snapshot in ('pitchValue', 'previousInput', 'magnitude', 'amount'):
        for early in (False, True):
            yield 'roles-' + snapshot + ('-early' if early else '-after-B8'), replace(
                body, PITCH, coefficient_block(snapshot, 'value', early))
    yield 'roles-inverse', replace(body, PITCH, coefficient_block('value', 'pitchValue'))
    yield 'roles-explicit-add', replace(body, PITCH, coefficient_block('pitchValue', 'value', compound=False))


def all_forms():
    yield from role_forms()
    yield from loop_forms()
    yield from qualifier_forms()
    yield from dataflow_forms()
    yield from inline_forms()


def inline_forms():
    body = dict(dataflow_forms())['dataflow-423']
    block = '\n'.join((PITCH.splitlines()[0], PITCH.splitlines()[1],
                       PITCH.splitlines()[4], PITCH.splitlines()[2], PITCH.splitlines()[3]))
    yield 'inline-base', body
    for name, y, snapshot in (('Y', True, False), ('B8', False, True), ('both', True, True)):
        candidate = block
        if y:
            candidate = replace(candidate, '            index = D_800CC284->y;\n', '')
            candidate = replace(candidate, '(f32)index', '(f32)D_800CC284->y')
        if snapshot:
            candidate = replace(candidate, '            value = actor->valueB8;\n', '')
            candidate = replace(candidate, '- value)', '- actor->valueB8)')
        yield 'inline-' + name, replace(body, block, candidate)


def dataflow_forms():
    body = previous.selected_body()
    lines = PITCH.splitlines()
    for order in itertools.permutations((2, 3, 4)):
        yield 'dataflow-' + ''.join(str(i) for i in order), replace(
            body, PITCH, '\n'.join((lines[0], lines[1], *(lines[i] for i in order))))
    for name in ('amount', 'rate', 'pitchValue'):
        block = lines[:2] + ['            ' + name + ' = (f32)index;'] + lines[2:]
        block[-1] = block[-1].replace('(f32)index', name)
        yield 'dataflow-cast-' + name, replace(body, PITCH, '\n'.join(block))
    advisory = ('            index = D_800CC284->y;\n'
                '            actor->verticalVelocity = 0.0f;\n'
                '            pitchValue = actor->valueB8;\n'
                '            actor->acceleration = 0.0f;\n'
                '            value = (f32)index;\n'
                '            actor->valueB8 += (value - pitchValue) * D_800A19C4;')
    yield 'dataflow-advisory-A', replace(body, PITCH, advisory)


def qualifier_forms():
    yield 'const-coefficient', previous.selected_body()


def owner_types(name):
    types = source.TYPE
    if name == 'const-coefficient':
        types = replace(types, 'extern f32 D_800A19C4, D_800A19C8, D_800A19CC, D_800A19D0, D_800A19D4;',
            'extern const f32 D_800A19C4;\nextern f32 D_800A19C8, D_800A19CC, D_800A19D0, D_800A19D4;')
    return types


SELECTED_NAME = 'dataflow-423'
SELECTED_SHA = '4a4c3574716a6ab788981a28d6af57e8bd46c6c01d6a92aed2c100edfc38b5a7'
backend = previous.backend


def selected_body():
    return dict(dataflow_forms())[SELECTED_NAME]


PITCH_SITES = ((0x150F3E1C, 0x3C01800A), (0x150F3E24, 0xC42819C4),
               (0x150F3E28, 0xE6100020), (0x150F3E30, 0xC6020020), (0x150F3E34, 0xE6100024))


def check_layout(record, words, content):
    layout = previous.check_layout(record, words, content)
    if any(words[(pc - source.ENTRY) // 4] != word for pc, word in PITCH_SITES):
        raise ValueError('Changed movement pitch emitted read/store order')
    return dict(layout, pitch_sites=[(pc - source.ENTRY) // 4 for pc, _ in PITCH_SITES],
                coefficient_is_inline_F8_expression_not_F12_local=True)


LOOP_END = ('                        countRecord++;\n'
            '                    } while ((u8 *)countRecord != D_800D121C);')


def loop_forms():
    body = previous.selected_body()
    yield 'loop-base', body
    for label, comparison in (('typed', 'countRecord != (MovementActor34F4 *)D_800D121C'),
                               ('reversed', 'D_800D121C != (u8 *)countRecord'),
                               ('typed-reversed', '(MovementActor34F4 *)D_800D121C != countRecord')):
        yield 'loop-' + label, replace(body, '(u8 *)countRecord != D_800D121C', comparison)
    for label, comparison in (('increment', '(u8 *)++countRecord != D_800D121C'),
                               ('increment-reversed', 'D_800D121C != (u8 *)++countRecord')):
        yield 'loop-' + label, replace(body, LOOP_END, '                    } while (' + comparison + ');')


def measure(root, out, name, body):
    freeze(root, out)
    with patch.object(source, 'TYPE', owner_types(name)):
        obj, words, row = source.measure(root, out, name, body)
    row['const_coefficient'] = name == 'const-coefficient'
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first = next(i for i, (a, b) in enumerate(zip(words, truth)) if a != b)
    row.update(name=name, first_unequal_word=first, first_unequal_PC=source.ENTRY + first * 4)
    try:
        normalized, _ = previous.previous.normalize(words, truth, source.parts(obj)[1])
    except ValueError as exc:
        row.update(previous_maps_compatible=False, previous_map_error=str(exc))
    else:
        first = next(i for i, (a, b) in enumerate(zip(normalized, truth)) if a != b)
        row.update(previous_maps_compatible=True, normalized_differences=sum(a != b for a, b in zip(normalized, truth)),
                   normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4)
    (out / (name + '-audit.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    zero_proof = previous.check_zero_lifetime(selected_body())
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, 134, SELECTED_SHA):
        raise ValueError('Changed movement schedule selected C')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    release = previous.previous.previous
    first28, _ = release.previous.normalize(words, truth, bindings)
    expected, proof = previous.previous.normalize(words, truth, bindings)
    flags = release.flags
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, first28))
               if flags.START <= i < flags.END and a != b]
    table = out / 'expected-schedule-guards.csv'
    table.write_bytes(release.guard_text((out / 'before-guards').read_bytes().decode(), raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'schedule-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if normalized_bindings != bindings or sum(a != b for a, b in zip(raw, normalized_raw)) != 39 or linked != expected:
        raise ValueError('Changed movement schedule guarded bytes or bindings')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement schedule padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(), normalized_target_changed_bytes=39,
        target_relocations_unchanged=True, proof=proof, zero_proof=zero_proof,
        research_guards=31, new_research_guards=0, production_guards_added=0, matching_credit=0, installed=False)
    if (row['normalized_differences'], first) != (103, 478):
        raise ValueError('Changed movement schedule normalized result')
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, linked, row


def screens(root, out, group, selected=None):
    rows = []
    for name, body in {'coefficient': role_forms, 'loop': loop_forms, 'qualifier': qualifier_forms,
                       'dataflow': dataflow_forms, 'inline': inline_forms}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        rows.append({k: v for k, v in row.items() if k != 'bindings'})
        print(json.dumps(rows[-1]), flush=True)
    if not rows:
        raise ValueError('Unknown movement coefficient source form')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--group', choices=('coefficient', 'loop', 'qualifier', 'dataflow', 'inline'), default='coefficient')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--normalize', action='store_true')
    mode.add_argument('--trace', action='store_true')
    mode.add_argument('--reuse-trace', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.normalize:
        print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items() if k not in ('bindings', 'proof')}, indent=2))
    elif args.trace or args.reuse_trace:
        freeze(root, root / BUILD)
        run = backend.trace if args.trace else backend.finish_trace
        record, words, binary = run(root, root / BUILD, SELECTED_NAME, selected_body())
        print(json.dumps(dict(words=len(words), object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], AS1_instructions=len(binary))))
    else:
        screens(root, root / BUILD, args.group, args.form)
