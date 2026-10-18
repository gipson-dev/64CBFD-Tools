"""Recover movement pitch and surface read/store order in the complete C body."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_release_addressing as previous

source = previous.source
BUILD = 'conker/build/game-actor-input-movement-pitch-inputs'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_pitch_predecessor', 'tools/experiments/game_actor_input_movement_release_addressing.py',
     'b79a765a3ae182922ef330552548f53443a1100e15e57ca3edfbc9507c068a45'),
    ('movement_pitch_predecessor_tests', 'tools/tests/test_game_actor_input_movement_release_addressing.py',
     'df31bd75668885a4cdbb3893f33878a51906647ef9744744cc90c30838db3ac5'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement pitch predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement pitch predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement pitch frozen input: ' + key)


replace = previous.replace
PITCH = ('            index = D_800CC284->y;\n'
         '            value = actor->valueB8;\n'
         '            actor->verticalVelocity = 0.0f;\n'
         '            actor->acceleration = 0.0f;\n'
         '            actor->valueB8 += (((f32)index - value) * D_800A19C4);')


def equality_forms():
    body = previous.selected_body()
    yield 'previous', body
    yield 'zero-left', replace(body, 'if (acceleration == 0.0f)', 'if (0.0f == acceleration)')


def coefficient_forms():
    body = dict(equality_forms())['zero-left']
    yield 'coefficient-base', body
    lines = PITCH.splitlines()
    for name in ('pitchRate', 'rate', 'amount', 'magnitude'):
        local = name == 'pitchRate'
        declaration = '            f32 pitchRate;\n' if local else ''
        assignment = '            ' + name + ' = D_800A19C4;'
        for slot in (0, 1, 2):
            block = list(lines)
            block.insert(slot, assignment)
            block[-1] = block[-1].replace('D_800A19C4', name)
            yield 'coefficient-' + name + '-' + str(slot), replace(body, PITCH, declaration + '\n'.join(block))


def all_forms():
    yield from equality_forms()
    yield from coefficient_forms()
    yield from surface_forms()
    yield from surface_store_forms()
    yield from surface_mode_forms()


def surface_forms():
    body = previous.selected_body()
    yield 'surface-base', body
    expression = 'actor->verticalVelocity = speed * -1.0f;'
    for name, replacement in (('integer', 'speed * -1'), ('double', 'speed * -1.0'),
                              ('reversed', '-1.0f * speed'), ('negation', '-speed')):
        yield 'surface-' + name, replace(body, expression, 'actor->verticalVelocity = ' + replacement + ';')
    anchor = '            actor->speed *= D_800A19C8;'
    for name in ('value', 'velocity'):
        candidate = replace(body, anchor, anchor + '\n            ' + name + ' = speed * -1.0f;')
        yield 'surface-snapshot-' + name, replace(candidate, expression, 'actor->verticalVelocity = ' + name + ';')


SURFACE = ('                actor->mode = 0;',
           '                actor->verticalVelocity = speed * -1.0f;',
           '                actor->valueB8 = 0.0f;',
           '                actor->depth = D_800A19CC;')


def surface_store_forms():
    body = previous.selected_body()
    for order in itertools.permutations((1, 2, 3)):
        indices = (0, *order)
        yield 'surface-store-' + ''.join(str(i) for i in indices), replace(
            body, '\n'.join(SURFACE), '\n'.join(SURFACE[i] for i in indices))


def surface_mode_forms():
    body = previous.selected_body()
    for order in ((1, 0, 3, 2), (1, 3, 0, 2), (1, 3, 2, 0)):
        yield 'surface-mode-' + ''.join(str(i) for i in order), replace(
            body, '\n'.join(SURFACE), '\n'.join(SURFACE[i] for i in order))


SELECTED_NAME = 'surface-mode-1032'
SELECTED_SHA = '1a31a90ee6291e47eeead06e6359174d46ea6a4ddc597fb9069e243b6fea6da4'


def selected_body():
    return dict(surface_mode_forms())[SELECTED_NAME]


def normalize(words, truth, bindings):
    result, prior = previous.previous.normalize(words, truth, bindings)
    result, heading = previous.prove_heading(result, truth, bindings)
    return result, dict(prior=prior, heading=heading)


def measure(root, out, name, body):
    freeze(root, out)
    obj, words, row = source.measure(root, out, name, body)
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first = next(i for i, (a, b) in enumerate(zip(words, truth)) if a != b)
    row.update(name=name, first_unequal_word=first, first_unequal_PC=source.ENTRY + first * 4)
    try:
        normalized, _ = normalize(words, truth, source.parts(obj)[1])
    except ValueError as exc:
        row.update(previous_maps_compatible=False, previous_map_error=str(exc))
    else:
        first = next(i for i, (a, b) in enumerate(zip(normalized, truth)) if a != b)
        row.update(previous_maps_compatible=True, normalized_differences=sum(a != b for a, b in zip(normalized, truth)),
                   normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4)
    (out / (name + '-audit.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    zero_proof = previous.previous.check_zero_lifetime(selected_body())
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, 152, SELECTED_SHA):
        raise ValueError('Changed movement surface selected C')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first28, _ = previous.previous.normalize(words, truth, bindings)
    expected, proof = normalize(words, truth, bindings)
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, first28))
               if previous.flags.START <= i < previous.flags.END and a != b]
    table = out / 'expected-surface-guards.csv'
    table.write_bytes(previous.guard_text((out / 'before-guards').read_bytes().decode(), raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'surface-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if normalized_bindings != bindings or sum(a != b for a, b in zip(raw, normalized_raw)) != 39 or linked != expected:
        raise ValueError('Changed movement surface guarded bytes or bindings')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement surface padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(), normalized_target_changed_bytes=39,
        target_relocations_unchanged=True, proof=proof, zero_proof=zero_proof,
        research_guards=31, new_research_guards=0, production_guards_added=0, matching_credit=0, installed=False)
    if (row['normalized_differences'], first) != (121, 478):
        raise ValueError('Changed movement surface normalized result')
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, linked, row


def screens(root, out, group, selected=None):
    rows = []
    for name, body in {'equality': equality_forms, 'coefficient': coefficient_forms,
                       'surface': surface_forms, 'store': surface_store_forms,
                       'mode': surface_mode_forms}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        rows.append({k: v for k, v in row.items() if k != 'bindings'})
        print(json.dumps(rows[-1]), flush=True)
    if not rows:
        raise ValueError('Unknown movement pitch source form')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('equality', 'coefficient', 'surface', 'store', 'mode'), default='equality')
    parser.add_argument('--form')
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
        run = previous.backend.trace if args.trace else previous.backend.finish_trace
        record, words, binary = run(root, root / BUILD, SELECTED_NAME, selected_body())
        print(json.dumps(dict(words=len(words), object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], AS1_instructions=len(binary))))
    else:
        screens(root, root / BUILD, args.group, args.form)
