"""Recover movement pitch snapshots and held-record addressing in full C."""
import ctypes
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_heading_continuation as previous

BUILD = 'conker/build/game-actor-input-movement-release-addressing'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_release_predecessor', 'tools/experiments/game_actor_input_movement_heading_continuation.py',
     '77b8e9f2410084853fc455b183a1810e3d0c15094a3af98d5a51a1fa938f8862'),
    ('movement_release_predecessor_tests', 'tools/tests/test_game_actor_input_movement_heading_continuation.py',
     '0c0aecc6b7f6c0b7d6e531e45e7c1728ee46ba3b3ce25932e6a392a47c60c15e'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement release predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement release predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement release frozen input: ' + key)


replace = previous.replace
PITCH = ('            index = D_800CC284->y;\n'
         '            value = actor->valueB8;\n'
         '            actor->verticalVelocity = 0.0f;\n'
         '            actor->acceleration = 0.0f;\n'
         '            actor->valueB8 = value + (((f32)index - value) * D_800A19C4);')


def pitch_forms():
    body = previous.selected_body()
    yield 'previous', body
    yield 'pitch-compound', replace(body, PITCH,
        PITCH.replace('actor->valueB8 = value + ', 'actor->valueB8 += '))
    for name in ('rate', 'amount', 'previousInput'):
        block = replace(PITCH, '            value = actor->valueB8;',
                        '            value = actor->valueB8;\n            ' + name + ' = D_800A19C4;')
        block = replace(block, '* D_800A19C4', '* ' + name)
        yield 'coefficient-' + name, replace(body, PITCH, block)
        yield 'coefficient-' + name + '-compound', replace(body, PITCH,
            block.replace('actor->valueB8 = value + ', 'actor->valueB8 += '))


RELEASE = ('                    record = (MovementActor34F4 *)(D_800CC2D0 +\n'
           '                              (actor->held - 100) * 0x32C);')
FLAGS = '                    actor->controlFlags &= ~2;'


def release_forms():
    body = previous.selected_body()
    yield 'release-base', body
    yield 'release-pointer', replace(body, RELEASE,
        '                    record = (MovementActor34F4 *)D_800CC2D0 + (actor->held - 100);')
    yield 'release-indexed', replace(body, RELEASE,
        '                    record = &((MovementActor34F4 *)D_800CC2D0)[actor->held - 100];')
    for name in ('index', 'heldIndex'):
        assignment = '                    ' + name + ' = actor->held - 100;'
        for form, expression in (
            ('bytes', '(MovementActor34F4 *)(D_800CC2D0 + ' + name + ' * 0x32C)'),
            ('array', '&((MovementActor34F4 *)D_800CC2D0)[' + name + ']'),
        ):
            block = assignment + '\n                    record = ' + expression + ';'
            yield 'release-' + name + '-' + form, replace(body, RELEASE, block)
        block = assignment + '\n' + FLAGS + '\n' + '                    record = &((MovementActor34F4 *)D_800CC2D0)[' + name + '];'
        yield 'release-' + name + '-before-flags', replace(body, FLAGS + '\n' + RELEASE, block)


def all_forms():
    yield from pitch_forms()
    yield from release_forms()
    yield from flow_forms()
    yield from tail_forms()
    yield from literal_forms()
    yield from copy_forms()


def compound_pitch(body):
    return replace(body, '            actor->valueB8 = value + (((f32)index - value) * D_800A19C4);',
                   '            actor->valueB8 += (((f32)index - value) * D_800A19C4);')


def flow_forms():
    base = compound_pitch(previous.selected_body())
    yield 'flow-base', base
    local = {}
    for style, expression in (('bytes', '(MovementActor34F4 *)(D_800CC2D0 + releaseIndex * 0x32C)'),
                               ('array', '&((MovementActor34F4 *)D_800CC2D0)[releaseIndex]')):
        block = ('                    s32 releaseIndex = actor->held - 100;\n' + FLAGS + '\n'
                 '                    record = ' + expression + ';')
        local[style] = replace(base, FLAGS + '\n' + RELEASE, block)
        yield 'local-release-' + style, local[style]
    held = compound_pitch(dict(release_forms())['release-heldIndex-bytes'])
    end = ('                    func_1506E8D8();\n'
           '                }\n'
           '            } else if ((D_800CC288 & 0x2000) && actor->cooldown == 0) {')
    for name, body in (('current', base), ('heldIndex', held), ('local', local['array'])):
        body = replace(body, end, end.replace('func_1506E8D8();', 'func_1506E8D8();\n                    goto movement_contact;'))
        yield 'contact-jump-' + name, replace(body, '        if (actor->depth <= contactHeight) {',
                                            'movement_contact:\n        if (actor->depth <= contactHeight) {')


def tail_forms():
    bodies = {'current': compound_pitch(previous.selected_body()),
              'release': compound_pitch(dict(release_forms())['release-heldIndex-bytes']),
              'local': dict(flow_forms())['local-release-bytes']}
    for group, original in bodies.items():
        for name in ('rate', 'initialMagnitude', 'animationZero'):
            body = original
            if name == 'animationZero':
                body = replace(body, '    f32 value;', '    f32 value;\n    f32 animationZero;')
            tail = body[body.index('        animation = 0xF;'):]
            modified = tail
            for before, after in (('actor->valueC0 <= 0.0f', 'actor->valueC0 <= ' + name),
                                  ('input == 0.0f', 'input == ' + name),
                                  ('value < 0.0f', 'value < ' + name),
                                  ('9.0f, 0.0f, 0.0f, 0)', '9.0f, ' + name + ', ' + name + ', 0)')):
                modified = replace(modified, before, after)
            yield 'tail-zero-' + group + '-' + name, replace(body, tail,
                '        ' + name + ' = 0.0f;\n' + modified)


def literal_forms():
    bodies = {'current': compound_pitch(previous.selected_body()),
              'local': dict(flow_forms())['local-release-bytes']}
    for group, body in bodies.items():
        tail = body[body.index('        animation = 0xF;'):]
        for name, condition in (('integer-zero', 'value < 0'), ('double-zero', 'value < 0.0'),
                                ('float-cast-zero', 'value < (f32)0'), ('constant-first-zero', '0.0f > value')):
            yield 'negative-' + group + '-' + name, replace(body, tail,
                replace(tail, 'value < 0.0f', condition))


def copy_forms():
    body = dict(literal_forms())['negative-local-integer-zero']
    yield 'copy-base', body
    copy = '                    record->speed = actor->speed;'
    flags = '                    record->flags &= ~0x400;'
    yield 'copy-before-flags', replace(body, flags + '\n' + copy, copy + '\n' + flags)
    moved = replace(body, copy + '\n', '')
    first = '                    record->heldBy = 0;'
    yield 'copy-after-heldBy', replace(moved, first, first + '\n' + copy)
    for name in ('rate', 'magnitude', 'amount'):
        snapshot = first + '\n                    ' + name + ' = actor->speed;'
        candidate = replace(body, first, snapshot)
        yield 'copy-snapshot-' + name, replace(candidate, copy, '                    record->speed = ' + name + ';')


SELECTED_NAME = 'copy-after-heldBy'
SELECTED_SHA = 'baf3b1d68ff8fea1d6b9d8b572f45244c76d74a90c40017184840b9ebf49dcb1'
NORMALIZED_SHA = '435560ad975b9affbb0f4875d838f956a6c49ebdec2c32d2f55013332c22870a'
START, END = 469, 478
ROLE_MAP = {11: 13, 12: 14}
GUARDS = ((0x754, 0x860B007A, 0x860D007A), (0x760, 0x256C4000, 0x25AE4000),
          (0x764, 0x448C5000, 0x448E5000))
flags = previous.previous
backend = previous.backend


def selected_body():
    return dict(all_forms())[SELECTED_NAME]


def prove_heading(words, truth, bindings, mapping=None):
    mapping = dict(ROLE_MAP if mapping is None else mapping)
    if mapping != ROLE_MAP:
        raise ValueError('Invalid movement heading temporary roles')
    if len(words) != 959 or len(truth) != 959 or words[0] != 0x27BDFF80:
        raise ValueError('Changed movement heading extent/frame')
    for offset, expected, _ in GUARDS:
        if words[offset // 4] != expected or bindings.get(offset):
            raise ValueError('Changed movement heading expected word or relocation')
    for i, word in enumerate(words):
        control = flags.control(word, i)
        if control and control[0] in ('branch', 'jump', 'call') and START < control[1] < END:
            raise ValueError('Incoming control enters movement heading interior')
        if START <= i < END and control:
            raise ValueError('Unexpected control inside movement heading window')
    result, defined, identity, uses = list(words), set(), set(), {r: 0 for r in mapping}
    writes = {r: 0 for r in mapping}
    for i in range(START, END):
        reads, destinations = flags.operands(words[i])
        for shift in reads:
            r = words[i] >> shift & 31
            if r in mapping:
                if r not in defined:
                    raise ValueError('Movement heading role read before definition')
                uses[r] += 1
            else:
                identity.add(r)
        for shift in destinations:
            r = words[i] >> shift & 31
            if r in mapping:
                writes[r] += 1
                defined.add(r)
            else:
                identity.add(r)
        result[i] = flags.rename(words[i], mapping)
    if (set(mapping.values()) & identity or any(writes[r] != 1 or uses[r] != 1 for r in mapping)
            or result[START:END] != truth[START:END]):
        raise ValueError('Movement heading literal correspondence or identity collision')
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, result)) if a != b]
    if changes != list(GUARDS):
        raise ValueError('Changed movement heading rewrite set')
    affected = set(mapping) | set(mapping.values())
    liveout = flags.path_definitions(words, END, len(words), {r: r for r in affected})
    return result, dict(window_words=END - START, changes=3, source_to_retail=mapping,
        local_uses=uses, local_definitions=writes, identity_registers=sorted(identity),
        non_call_boundary=True, continuation_first_definitions=liveout,
        all_four_affected_physical_registers_dead_before_read=True,
        no_ABI_clobber_used_to_excuse_liveout_reads=True,
        FP_fields_memory_addresses_and_control_order_unchanged=True,
        arbitrary_private_registers_and_unpassed_provider_observation_not_claimed=True)


def guard_text(before, raw_words, bindings, changes):
    prefix = flags.guard_text(before, raw_words, bindings, changes)
    fields = next(csv.reader(io.StringIO(before)))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\r\n' if before.endswith('\r\n') else '\n')
    for offset, expected, replacement in GUARDS:
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations='-', replacement_relocations='-',
            note='Normalize dead local movement heading temporary roles', omit='false'))
    return prefix + output.getvalue()


def check_layout(record, words, content):
    frame = backend.frame
    if record.get('code_unchanged') is not True or record.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement release layout')
    summary = frame.summary(record, content, backend.MARKERS)
    phases = summary['phases']
    sizes = [[r['length'] for r in phases[p]['definitions'] if r['storage'] == 'M']
             for p in ('frontend', 'optimizer')]
    for name, offset in backend.HOMES.items():
        stores = [r for r in phases['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M']
        dtype, size = ('L', 2) if name == 'angle' else ('J', 4) if name == 'index' else ('A', 4) if name == 'record' else ('R', 4)
        if [(r['offset'], r['dtype'], r['length']) for r in stores] != [(offset, dtype, size)]:
            raise ValueError('Changed movement release predecessor home: ' + name)
    marker = 's32 releaseIndex = actor->held - 100;'
    lines = [i + 1 for i, line in enumerate(content.splitlines()) if line.strip() == marker]
    if len(lines) != 1:
        raise ValueError('Changed movement release index marker')
    stores = {}
    for phase, expected in (('frontend', ('M', -88, 'J', 4)), ('optimizer', ('R', 4, 'J', 4))):
        current, found = None, []
        for row in frame.procedure_records(record['records'][phase], summary['procedure']):
            if row['name'] == 'loc':
                current = row['words'][1]
            if current == lines[0] and row['name'] == 'str':
                found.append(row)
        if [(r['storage'], r['offset'], r['dtype'], r['length']) for r in found] != [expected]:
            raise ValueError('Changed movement release index home: ' + phase)
        stores[phase] = found[0]
    events = record['events']
    if (sizes != [[88], [76]] or [e['event'] for e in events] != ['frame-watch-installed', 'frame-write', 'frame-write', 'frame-write']
            or [e['host_pc'] for e in events] != [4268224, 4566873, 4523375, 4523375]
            or [e['frame'] for e in events] != [0, 16, 48, 128]
            or [(e['saved'], e['outgoing'], e['locals']) for e in events] != [(0, 0, 0), (16, 0, 0), (16, 32, 0), (16, 32, 80)]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)):
        raise ValueError('Changed movement release frame budgets')
    sites = ((0, 0x27BDFF80), (1, 0xAFB00028), (4, 0xAFBF002C), (5, 0xE7B00058))
    emitted = ((0x150F3FE0, 0x2464FF9C), (0x150F3FF0, 0x00880019),
               (0x150F4014, 0xA040013D), (0x150F4018, 0xC60A003C),
               (0x150F4034, 0xE44A003C), (0x150F4050, 0),
               (0x150F4354, 0x44802000))
    sites += tuple(((pc - source.ENTRY) // 4, word) for pc, word in emitted)
    if any(words[i] != word for i, word in sites):
        raise ValueError('Changed movement release emitted lifetime')
    return dict(frontend=88, optimizer=76, rounded=80, frame=128, saved=16, outgoing=32,
                old_homes=backend.HOMES, release_index=stores, sites=[i for i, _ in sites],
                new_index_is_real_signed_address_input_not_padding=True)


def qualify(root, out):
    zero_proof = previous.check_zero_lifetime(selected_body())
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, 200, SELECTED_SHA):
        raise ValueError('Changed movement release selected C')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    prior_words, prior_proof = previous.normalize(words, truth, bindings)
    normalized, heading_proof = prove_heading(prior_words, truth, bindings)
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, prior_words))
               if flags.START <= i < flags.END and a != b]
    table = out / 'expected-release-guards.csv'
    table.write_bytes(guard_text((out / 'before-guards').read_bytes().decode(), raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'release-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    if (normalized_bindings != bindings or sum(a != b for a, b in zip(raw, normalized_raw)) != 39
            or hashlib.sha256(normalized_raw).hexdigest() != NORMALIZED_SHA):
        raise ValueError('Changed movement release guarded bytes or bindings')
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if linked != normalized:
        raise ValueError('Movement release actual padder disagrees with role proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement release padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(previous_28_differences=row['normalized_differences'], normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(), normalized_target_changed_bytes=39,
        target_relocations_unchanged=True, prior_proof=prior_proof, heading_proof=heading_proof, zero_proof=zero_proof,
        research_guards=31, new_research_guards=3, production_guards_added=0, matching_credit=0, installed=False)
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, normalized, row


def measure(root, out, name, body):
    freeze(root, out)
    obj, words, row = source.measure(root, out, name, body)
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first = next(i for i, (a, b) in enumerate(zip(words, truth)) if a != b)
    row.update(name=name, first_unequal_word=first, first_unequal_PC=source.ENTRY + first * 4)
    try:
        normalized, _ = previous.normalize(words, truth, source.parts(obj)[1])
    except ValueError as exc:
        row.update(previous_maps_compatible=False, previous_map_error=str(exc))
    else:
        first = next(i for i, (a, b) in enumerate(zip(normalized, truth)) if a != b)
        row.update(previous_maps_compatible=True, normalized_differences=sum(a != b for a, b in zip(normalized, truth)),
                   normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4)
    (out / (name + '-audit.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screens(root, out, group, selected=None):
    rows = []
    for name, body in {'pitch': pitch_forms, 'release': release_forms,
                       'flow': flow_forms, 'tail': tail_forms, 'literal': literal_forms, 'copy': copy_forms}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        rows.append({k: v for k, v in row.items() if k != 'bindings'})
        print(json.dumps(rows[-1]), flush=True)
    if not rows:
        raise ValueError('Unknown movement release source form')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('pitch', 'release', 'flow', 'tail', 'literal', 'copy'), default='release')
    parser.add_argument('--form')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--normalize', action='store_true')
    mode.add_argument('--trace', action='store_true')
    mode.add_argument('--reuse-trace', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.normalize:
        print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items()
                          if k not in ('bindings', 'prior_proof', 'heading_proof')}, indent=2))
    elif args.trace or args.reuse_trace:
        freeze(root, root / BUILD)
        run = backend.trace if args.trace else backend.finish_trace
        record, words, binary = run(root, root / BUILD, SELECTED_NAME, selected_body())
        print(json.dumps(dict(words=len(words), object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], AS1_instructions=len(binary))))
    else:
        screens(root, root / BUILD, args.group, args.form)
