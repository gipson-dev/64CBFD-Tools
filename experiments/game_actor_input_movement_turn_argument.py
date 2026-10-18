"""Screen movement turn-argument evaluation and real integer-width lifetimes."""
import ctypes
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_float_lifetimes as previous

BUILD = 'conker/build/game-actor-input-movement-turn-argument'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_turn_predecessor', 'tools/experiments/game_actor_input_movement_float_lifetimes.py',
     '9ff3aa8b0dc60dbc91086023615e46e3204b59fc7d6278f66477308868f346ff'),
    ('movement_turn_predecessor_tests', 'tools/tests/test_game_actor_input_movement_float_lifetimes.py',
     '2fcfbb584c4a37eb65a34b38ab7475a3758d5224d27951a57f875b02d7262703'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement turn predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement turn predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement turn frozen input: ' + key)


replace = previous.replace
DELTA = ('(u32)(s32)(actor->valueC4 * D_800D1550 *\n'
         '                  D_800A1994 * ((100.0f - speed) * D_800A1998) * 220.0f)')
EXPRESSION = '(u32)actor->heading - ' + DELTA
ASSIGNMENT = '        actor->heading = ' + EXPRESSION + ';'
STEP = '        actor->turnStep = 25;'
CALL = '        func_150599C8(actor, 8, actor->heading);'
TURN = '\n'.join((ASSIGNMENT, STEP, CALL))


def arguments():
    body = previous.selected_body()
    yield 'previous', body
    for name, expression in (
        ('argument-assignment', 'actor->heading = ' + EXPRESSION),
        ('argument-compound', 'actor->heading -= ' + DELTA),
        ('argument-cast', '(u16)(actor->heading = ' + EXPRESSION + ')'),
    ):
        yield name, replace(body, TURN, STEP + '\n        func_150599C8(actor, 8, ' + expression + ');')
    for name, expression in (
        ('argument-late-step', 'actor->heading = ' + EXPRESSION + ', actor->turnStep = 25, actor->heading'),
        ('argument-early-step', 'actor->turnStep = 25, actor->heading = ' + EXPRESSION),
    ):
        yield name, replace(body, TURN, '        func_150599C8(actor, 8, (' + expression + '));')


def widths():
    body = previous.selected_body()
    narrow = DELTA.replace('(u32)(s32)', '(u16)(s32)')
    yield 'narrow-delta', replace(body, ASSIGNMENT, ASSIGNMENT.replace(DELTA, narrow))
    compound = '        actor->heading -= ' + narrow + ';'
    yield 'narrow-compound', replace(body, ASSIGNMENT, compound)
    yield 'narrow-argument-compound', replace(body, TURN,
        STEP + '\n        func_150599C8(actor, 8, actor->heading -= ' + narrow + ');')
    yield 'narrow-argument-assignment', replace(body, TURN,
        STEP + '\n        func_150599C8(actor, 8, actor->heading = (u32)actor->heading - ' + narrow + ');')


def all_forms():
    yield from arguments()
    yield from widths()


def measure(root, out, name, body):
    freeze(root, out)
    return previous.measure(root, out, name, body)


ROLE_MAP = {10: 24, 24: 11, 14: 15, 15: 25}
START, END = 361, 396
NORMALIZED_SHA = '752d65b6308d86281109d9c3237d4ddc52a943597b1d3e6c8b9e231c92d25218'
GUARDS = (
    (0x5A4, 0x960A0076, 0x96180076), (0x5A8, 0x24180019, 0x240B0019),
    (0x5FC, 0xA218007E, 0xA20B007E), (0x618, 0x440E2000, 0x440F2000),
    (0x620, 0x014E7823, 0x030FC823), (0x624, 0xA60F0076, 0xA6190076),
    (0x62C, 0x31E6FFFF, 0x3326FFFF),
)


def gpr_operands(word):
    """Return read/write bit positions only for the observed straight-line kernel."""
    op, rs, function = word >> 26, word >> 21 & 31, word & 63
    if word == 0:
        return (), ()
    if op == 0 and function in (35, 37):
        return (21, 16), (11,)
    if op in (9, 12, 37):
        return (21,), (16,)
    if op == 15:
        return (), (16,)
    if op in (40, 41):
        return (21, 16), ()
    if op in (49, 57):
        return (21,), ()
    if op == 17:
        if rs == 0:
            return (), (16,)
        if rs == 4:
            return (16,), ()
        if rs in (16, 20):
            return (), ()
    if op == 3:
        return (), ()
    raise ValueError('Unsupported movement turn kernel instruction: 0x%08X' % word)


def prove_roles(words, truth, bindings, mapping=None, entry=source.ENTRY):
    mapping = dict(ROLE_MAP if mapping is None else mapping)
    temporary = {*range(8, 16), 24, 25}
    if (set(mapping) != set(ROLE_MAP) or len(set(mapping.values())) != 4
            or not set(mapping.values()) <= temporary):
        raise ValueError('Invalid movement turn temporary mapping')
    if len(words) != 959 or len(truth) != 959 or words[0] != 0x27BDFF80:
        raise ValueError('Changed movement turn extent/frame')
    if any(words[offset // 4] != expected for offset, expected, _ in GUARDS):
        raise ValueError('Changed movement turn expected input word')
    if any(offset in bindings for offset, _, _ in GUARDS):
        raise ValueError('Relocation on movement turn register rewrite')
    if words[END - 2] != 0x0D416672 or truth[END - 2] != words[END - 2]:
        raise ValueError('Changed movement turn callback boundary')
    lo, hi = entry + START * 4, entry + END * 4
    for i, word in enumerate(words):
        op, rs = word >> 26, word >> 21 & 31
        pc, target = entry + i * 4, None
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (op == 17 and rs == 8):
            immediate = ((word & 65535) ^ 32768) - 32768
            target = pc + 4 + immediate * 4
        elif op in (2, 3):
            target = ((pc + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
        elif op == 0 and word & 63 in (8, 9) and not (word & 63 == 8 and rs == 31):
            raise ValueError('Unqualified computed movement entry')
        if target is not None and lo < target < hi:
            raise ValueError('Incoming control enters movement turn kernel')
        if START <= i < END and target is not None and i != END - 2:
            raise ValueError('Unexpected control inside movement turn kernel')
    result, defined, writes, uses = list(words), set(), {r: 0 for r in mapping}, {r: [] for r in mapping}
    identity = set()
    for i in range(START, END):
        reads, destinations = gpr_operands(words[i])
        for shift in reads:
            register = words[i] >> shift & 31
            if register in mapping:
                if register not in defined:
                    raise ValueError('Movement turn role read before definition')
                uses[register].append(i)
            else:
                identity.add(register)
        for shift in destinations:
            register = words[i] >> shift & 31
            if register in mapping:
                writes[register] += 1
                defined.add(register)
            else:
                identity.add(register)
        word = words[i]
        for shift in set(reads) | set(destinations):
            register = words[i] >> shift & 31
            if register in mapping:
                word = (word & ~(31 << shift)) | (mapping[register] << shift)
        result[i] = word
    if (set(mapping.values()) & identity or set(mapping) & identity
            or any(writes[r] != 1 or not uses[r] for r in mapping)):
        raise ValueError('Movement turn role collides with a live identity register')
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, result)) if a != b]
    if changes != list(GUARDS) or result[START:END] != truth[START:END]:
        raise ValueError('Movement turn role correspondence does not match retail')
    return result, dict(kernel_words=END - START, changed_words=len(changes), source_to_retail=mapping,
        local_roles_defined_once=writes, role_use_indices=uses, unchanged_identity_registers=sorted(identity),
        no_internal_direct_interior_entry=True, unchanged_callback_binding_and_delay_position=True,
        unchanged_FP_operands_and_memory_addresses=True,
        C_ABI_temporary_role_proof=True, arbitrary_opaque_provider_or_raw_private_equivalence_not_claimed=True)


def guard_text(before):
    reader = csv.DictReader(io.StringIO(before))
    rows = list(reader)
    fields = ['filename', 'function', 'offset', 'expected', 'replacement', 'expected_relocations',
              'replacement_relocations', 'note', 'insert_after', 'insert_after_relocations', 'omit']
    if (reader.fieldnames != fields or not before.endswith('\n')
            or any(r['filename'] == source.OWNER and r['function'] == source.FUNCTION for r in rows)):
        raise ValueError('Changed movement turn guard predecessor')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames,
                            lineterminator='\r\n' if before.endswith('\r\n') else '\n')
    for offset, expected, replacement in GUARDS:
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations='-', replacement_relocations='-',
            note='Normalize closed movement heading step delta result temporary roles', omit='false'))
    return before + output.getvalue()


def qualify(root, out):
    obj, words, row = measure(root, out, 'previous', previous.selected_body())
    if (row['words'], row['frame'], row['differences'], row['raw_sha']) != (959, 128, 392, previous.SELECTED_SHA):
        raise ValueError('Changed complete movement turn baseline')
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    normalized, proof = prove_roles(words, truth, source.parts(obj)[1])
    guards = out / 'expected-turn-guards.csv'
    guards.write_bytes(guard_text((out / 'before-guards').read_bytes().decode()).encode())
    padded = source.literal.padded_object(root, out, obj, 'turn-normalized', guards)
    normalized_raw, normalized_bindings = source.parts(padded)
    raw, raw_bindings = source.parts(obj)
    if (normalized_bindings != raw_bindings
            or hashlib.sha256(normalized_raw).hexdigest() != NORMALIZED_SHA
            or sum(a != b for a, b in zip(raw, normalized_raw)) != 10):
        raise ValueError('Changed movement turn target bytes or relocation metadata')
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if linked != normalized:
        raise ValueError('Movement turn actual padder/link disagrees with role proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement turn padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=NORMALIZED_SHA, normalized_target_changed_bytes=10, target_relocations_unchanged=True,
        research_guards=7, production_guards_added=0, matching_credit=0, installed=False, proof=proof)
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, normalized, row


def screens(root, out, group, selected=None):
    rows = []
    for name, body in {'arguments': arguments, 'widths': widths}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        row = {k: v for k, v in row.items() if k != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    if not rows:
        raise ValueError('Unknown movement turn form in selected group')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('arguments', 'widths'), default='arguments')
    parser.add_argument('--form', choices=tuple(name for name, _ in all_forms()))
    parser.add_argument('--normalize', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.normalize:
        print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items() if k != 'bindings'}, indent=2))
    else:
        screens(root, root / BUILD, args.group, args.form)
