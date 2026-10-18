"""Recover complete movement flag paths and their branch-sensitive lifetimes."""
import ctypes
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_turn_argument as previous

BUILD = 'conker/build/game-actor-input-movement-flag-paths'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_flags_predecessor', 'tools/experiments/game_actor_input_movement_turn_argument.py',
     '09de0ac6a88b097f1b489efaa9f1a31702bff6d2bb3bbfb8096c99a1f7456b5f'),
    ('movement_flags_predecessor_tests', 'tools/tests/test_game_actor_input_movement_turn_argument.py',
     '991b989c4a7bd80857443e93a225c0b20b3e3280684a13c561bf56084d073d89'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement flag predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement flag predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement flag frozen input: ' + key)


replace = previous.replace
BUTTON = ('            if (buttons & 0x4000) {\n'
          '                value = actor->verticalVelocity;\n'
          '                actor->valueC0 = 30.0f;\n'
          '                if (value < 0.0f) {\n'
          '                    actor->valueC0 -= value * D_800A19A4;\n'
          '                }\n'
          '                speed = 1.5f;\n'
          '                rate = D_800A19A8;\n'
          '            }')


def button_forms():
    body = previous.previous.selected_body()
    yield 'previous', body
    velocity = BUTTON.replace('value = actor->verticalVelocity', 'velocity = actor->verticalVelocity')
    velocity = velocity.replace('if (value <', 'if (velocity <').replace('-= value *', '-= velocity *')
    yield 'button-velocity', replace(body, BUTTON, velocity)
    inline = BUTTON.replace('                value = actor->verticalVelocity;\n', '')
    inline = inline.replace('if (value <', 'if (actor->verticalVelocity <')
    inline = inline.replace('-= value *', '-= actor->verticalVelocity *')
    yield 'button-inline', replace(body, BUTTON, inline)


INITIALIZERS = ('        actor->valueC0 = 0.0f;', '        speed = 0.0f;', '        rate = D_800A199C;')


def initializer_forms():
    body = dict(button_forms())['button-velocity']
    for order in itertools.permutations(range(3)):
        yield 'initialize-' + ''.join(str(i) for i in order), replace(body, '\n'.join(INITIALIZERS),
            '\n'.join(INITIALIZERS[i] for i in order))


def all_forms():
    yield from button_forms()
    yield from initializer_forms()


def measure(root, out, name, body):
    freeze(root, out)
    return previous.measure(root, out, name, body)


SELECTED_NAME = 'button-velocity'
SELECTED_SHA = '732a850e84d11dea6e8e79d6a3134249fa40d1692345ce33c76f5c47bdf98d20'
NORMALIZED_SHA = 'febdb974cb00937fd7288bef8203c0f65197787b099d4b024d249ad031d7c6ad'
START, END = 406, 469
ROLE_MAP = {13: 10, 12: 14, 25: 12, 11: 13, 10: 24, 14: 15, 15: 25, 24: 11}
RELOCATED_CHANGES = {0x658: 'R_MIPS_HI16', 0x6AC: 'R_MIPS_LO16',
                     0x6D8: 'R_MIPS_HI16', 0x6E0: 'R_MIPS_LO16'}


def selected_body():
    return dict(button_forms())[SELECTED_NAME]


def operands(word):
    """GPR fields for the observed region and its post-call liveness scan."""
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0:
        if fn == 0:
            return (16,), (11,)
        if fn in (33, 35, 36, 37):
            return (21, 16), (11,)
        if fn == 25:
            return (21, 16), ()
        if fn == 18:
            return (), (11,)
        if fn == 8 and rs == 31:
            return (21,), ()
    if op in (4, 5, 20, 21):
        return (21, 16), ()
    if op in (9, 10, 12, 13, 32, 33, 35, 36, 37):
        return (21,), (16,)
    if op == 15:
        return (), (16,)
    if op in (40, 41, 43):
        return (21, 16), ()
    if op in (49, 57):
        return (21,), ()
    if op == 17 and rs == 8:
        return (), ()
    if op == 3:
        return (), ()
    return previous.gpr_operands(word)


def control(word, index, entry=source.ENTRY):
    op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
    pc = entry + index * 4
    if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (op == 17 and rs == 8):
        delta = ((word & 65535) ^ 32768) - 32768
        always = op in (4, 20) and rs == rt
        never = op in (5, 21) and rs == rt
        return 'branch', index + 1 + delta, op in (20, 21, 22, 23) or (op == 17 and bool(rt & 2)), always, never
    if op in (2, 3):
        address = ((pc + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
        return ('call' if op == 3 else 'jump'), (address - entry) // 4, False, True, False
    if op == 0 and word & 63 in (8, 9):
        if word & 63 == 8 and rs == 31:
            return 'return', None, False, True, False
        raise ValueError('Unqualified computed movement entry')
    return None


def rename(word, mapping):
    reads, writes = operands(word)
    result = word
    for shift in set(reads) | set(writes):
        r = word >> shift & 31
        result = (result & ~(31 << shift)) | (mapping.get(r, r) << shift)
    return result


def path_definitions(words, start, stop, mapping, terminal_call=False):
    """Overapproximate branch outcomes, including likely-slot annulment."""
    pending, seen, visited, exits, branches = [(start, frozenset())], set(), set(), 0, set()

    def consume(index, defined):
        if not start <= index < stop:
            raise ValueError('Unexpected movement CFG exit')
        reads, writes = operands(words[index])
        if any(words[index] >> s & 31 in mapping and words[index] >> s & 31 not in defined for s in reads):
            raise ValueError('Movement flag role read before definition at %d' % index)
        visited.add(index)
        return defined | {words[index] >> s & 31 for s in writes if words[index] >> s & 31 in mapping}

    while pending:
        index, defined = pending.pop()
        state = index, frozenset(defined)
        if state in seen:
            continue
        seen.add(state)
        defined = consume(index, defined)
        flow = control(words[index], index)
        if flow is None:
            pending.append((index + 1, frozenset(defined)))
            continue
        kind, target, likely, always, never = flow
        if control(words[index + 1], index + 1) is not None:
            raise ValueError('Control in movement delay slot')
        if kind == 'call' and terminal_call:
            if index != stop - 2:
                raise ValueError('Unexpected movement CFG call')
            consume(index + 1, defined)
            exits += 1
        elif kind == 'return' and not terminal_call:
            consume(index + 1, defined)
            exits += 1
        elif kind == 'call' and not terminal_call:
            # No ABI clobber is used to excuse a live-out read: require a
            # caller-side definition even beyond subsequent calls.
            pending.append((index + 2, frozenset(consume(index + 1, defined))))
        elif kind in ('branch', 'jump'):
            if terminal_call and target <= index:
                raise ValueError('Backward movement flag control')
            if not never:
                branches.add((index, True))
                pending.append((target, frozenset(consume(index + 1, defined))))
            if not always:
                branches.add((index, False))
                pending.append((index + 2, frozenset(defined if likely else consume(index + 1, defined))))
        else:
            raise ValueError('Unexpected movement control')
    if not exits:
        raise ValueError('Movement CFG has no qualified exit')
    return dict(states=len(seen), exit_states=exits, visited_indices=sorted(visited),
                branch_outcomes=sorted(branches))


def prove_roles(words, truth, bindings, mapping=None):
    mapping = dict(ROLE_MAP if mapping is None else mapping)
    if mapping != ROLE_MAP or set(mapping) != set(mapping.values()):
        raise ValueError('Invalid movement flag temporary permutation')
    if len(words) != 959 or len(truth) != 959 or words[0] != 0x27BDFF80:
        raise ValueError('Changed movement flag extent/frame')
    if words[END - 2] != 0x0D4168EA or truth[END - 2] != words[END - 2]:
        raise ValueError('Changed movement flag callback')
    if bindings.get((END - 2) * 4) != [('R_MIPS_26', 'func_1505A3A8')]:
        raise ValueError('Changed movement flag callback binding')
    delays = {i + 1 for i in range(START, END) if control(words[i], i) is not None}
    for i, word in enumerate(words):
        flow = control(word, i)
        if flow is None:
            continue
        kind, target, *_ = flow
        if kind in ('branch', 'jump', 'call'):
            if not START <= i < END and START < target < END:
                raise ValueError('Incoming control enters movement flag interior')
            if START <= i < END and kind != 'call' and (not START <= target < END or target in delays):
                raise ValueError('Movement flag target exits region or enters delay slot')
    result = list(words)
    identity = set()
    for i in range(START, END):
        reads, writes = operands(words[i])
        identity.update(words[i] >> s & 31 for s in set(reads) | set(writes) if words[i] >> s & 31 not in mapping)
        result[i] = rename(words[i], mapping)
    if set(mapping.values()) & identity or result[START:END] != truth[START:END]:
        raise ValueError('Movement flag literal correspondence or identity collision')
    changes = [(i * 4, words[i], result[i]) for i in range(START, END) if words[i] != result[i]]
    if len(changes) != 21:
        raise ValueError('Changed movement flag rewrite count')
    for offset, _, _ in changes:
        expected = [(RELOCATED_CHANGES[offset], 'D_800CC284')] if offset in RELOCATED_CHANGES else []
        if bindings.get(offset, []) != expected:
            raise ValueError('Changed movement flag relocation binding')
    paths = path_definitions(words, START, END, mapping, True)
    liveout = path_definitions(words, END, len(words), mapping)
    if sorted(set(range(START, END)) - set(paths['visited_indices'])) != [420]:
        raise ValueError('Changed movement flag unreachable duplicate')
    return result, dict(kernel_words=END - START, changed_words=len(changes), source_to_retail=mapping,
        paths=paths, post_call_liveness=liveout, unchanged_identity_registers=sorted(identity),
        unreachable_word_420_checked_literally_not_by_path_execution=True,
        relocated_GPR_fields_only_low16_addends_and_metadata_unchanged=True,
        no_mapped_role_live_in_or_read_live_out_before_definition=True,
        C_ABI_only_not_arbitrary_opaque_provider_or_raw_private_equivalence=True)


def guard_text(before, raw_words, bindings, changes):
    # Preserve the complete production prefix and the already certified turn rows.
    prefix = previous.guard_text(before)
    fields = next(csv.reader(io.StringIO(before)))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\r\n' if before.endswith('\r\n') else '\n')
    for offset, _, _ in changes:
        word = raw_words[offset // 4]
        spec = ';'.join(kind + ':' + symbol for kind, symbol in bindings.get(offset, [])) or '-'
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % word, replacement='0x%08X' % rename(word, ROLE_MAP),
            expected_relocations=spec, replacement_relocations=spec,
            note='Normalize branch-qualified movement flag and controller temporary roles', omit='false'))
    return prefix + output.getvalue()


def qualify(root, out):
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, 389, SELECTED_SHA):
        raise ValueError('Changed movement flag C baseline')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    normalized, turn_proof = previous.prove_roles(words, truth, bindings)
    normalized, proof = prove_roles(normalized, truth, bindings)
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, normalized)) if a != b and START <= i < END]
    guards = out / 'expected-flag-guards.csv'
    guards.write_bytes(guard_text((out / 'before-guards').read_bytes().decode(), raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'flag-normalized', guards)
    normalized_raw, normalized_bindings = source.parts(padded)
    if normalized_bindings != bindings or hashlib.sha256(normalized_raw).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed movement flag relocation metadata')
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if linked != normalized:
        raise ValueError('Movement flag padder/link disagrees with role proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement flag padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(),
        normalized_target_changed_bytes=sum(a != b for a, b in zip(raw, normalized_raw)),
        target_relocations_unchanged=True, research_guards=28, production_guards_added=0,
        matching_credit=0, installed=False, proof=proof, turn_proof=turn_proof)
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, normalized, row


def check_layout(record, words, content):
    layout = previous.previous.check_layout(record, words, content)
    frame = previous.previous.frame
    summary = frame.summary(record, content, previous.previous.MARKERS)
    lines = [i + 1 for i, s in enumerate(content.splitlines()) if s.strip() == 'velocity = actor->verticalVelocity;']
    if len(lines) != 2:
        raise ValueError('Changed movement button velocity markers')
    homes = {}
    for phase, expected in (('frontend', ('M', -32, 'R', 4)), ('optimizer', ('R', 34, 'R', 4))):
        current, stores = None, []
        for row in frame.procedure_records(record['records'][phase], summary['procedure']):
            if row['name'] == 'loc':
                current = row['words'][1]
            if current == lines[0] and row['name'] == 'str':
                stores.append(row)
        if [(r['storage'], r['offset'], r['dtype'], r['length']) for r in stores] != [expected]:
            raise ValueError('Changed movement button velocity home: ' + phase)
        homes[phase] = stores[0]
    for pc, expected in ((0x150F3BF4, 0xC6020020), (0x150F3C00, 0x4610103C), (0x150F3C1C, 0x46121102)):
        if words[(pc - source.ENTRY) // 4] != expected:
            raise ValueError('Changed movement button FPR2 instruction')
    return dict(layout=layout, button_stores=homes, actual_button_FPR=2)


def screens(root, out, group):
    rows = []
    for name, body in {'button': button_forms, 'initializers': initializer_forms}[group]():
        _, _, row = measure(root, out, name, body)
        row = {k: v for k, v in row.items() if k != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / (group + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('button', 'initializers'), default='button')
    parser.add_argument('--normalize', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.normalize:
        print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items() if k != 'bindings'}, indent=2))
    else:
        screens(root, root / BUILD, args.group)
