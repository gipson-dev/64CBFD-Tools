"""Qualify private movement temporary roles through the physics call slot."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_remaining_schedules as previous
from tools.experiments import game_actor_input_movement_flag_paths as flags

BUILD = 'conker/build/game-actor-input-movement-physics-call-roles'
START, END = 478, 627
ROLE_MAP = {13: 10, 14: 15, 25: 13, 10: 24, 15: 25, 24: 11, 3: 12}
CHANGED = (478, 480, 483, 494, 516, 519, 572, 576, 578, 580, 581, 582, 584, 587, 626)
REGION_BINDINGS = {
    i * 4: [(kind, symbol)] for i, kind, symbol in (
        (481, 'R_MIPS_HI16', 'D_800CC284'), (486, 'R_MIPS_LO16', 'D_800A19AC'),
        (521, 'R_MIPS_HI16', 'D_800A19B0'), (522, 'R_MIPS_LO16', 'D_800A19B0'),
        (523, 'R_MIPS_HI16', 'D_800A19B4'), (524, 'R_MIPS_LO16', 'D_800A19B4'),
        (544, 'R_MIPS_HI16', 'D_800A19BC'), (547, 'R_MIPS_HI16', 'D_800A19B8'),
        (548, 'R_MIPS_LO16', 'D_800A19B8'), (551, 'R_MIPS_LO16', 'D_800A19BC'),
        (554, 'R_MIPS_HI16', 'D_800A19C0'), (555, 'R_MIPS_LO16', 'D_800A19C0'),
        (579, 'R_MIPS_LO16', 'D_800CC284'), (586, 'R_MIPS_HI16', 'D_800A19C4'),
        (588, 'R_MIPS_LO16', 'D_800A19C4'), (623, 'R_MIPS_HI16', 'D_800CBDD3'),
        (625, 'R_MIPS_26', 'func_15059140'), (626, 'R_MIPS_LO16', 'D_800CBDD3'),
    )
}
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('physics_call_predecessor', 'tools/experiments/game_actor_input_movement_remaining_schedules.py',
     'd6adc897882c0d0f6f8a4f25ff0894c1d007ad1544f98448575b8fb932b17c2c'),
    ('physics_call_predecessor_tests', 'tools/tests/test_game_actor_input_movement_remaining_schedules.py',
     '53d89438f4346ca8c69cba3fc4c396686c70c3a87f695f21e3d69bf2b510ae6a'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement physics-call predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement physics-call predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement physics-call frozen input: ' + key)


def prove_roles(words, truth, bindings, mapping=None):
    mapping = dict(ROLE_MAP if mapping is None else mapping)
    if mapping != ROLE_MAP or len(set(mapping.values())) != len(mapping):
        raise ValueError('Invalid movement physics-call injective role map')
    if len(words) != 959 or len(truth) != 959 or words[0] != 0x27BDFF80:
        raise ValueError('Changed movement physics-call extent/frame')
    if words[END - 2] != 0x0D416450 or truth[END - 2] != words[END - 2]:
        raise ValueError('Changed movement physics-call target')
    if {k: v for k, v in bindings.items() if START * 4 <= k < END * 4} != REGION_BINDINGS:
        raise ValueError('Changed movement physics-call relocation binding')
    delays = {i + 1 for i in range(START, END) if flags.control(words[i], i) is not None}
    for i, word in enumerate(words):
        flow = flags.control(word, i)
        if flow is None:
            continue
        kind, target, *_ = flow
        if kind in ('branch', 'jump', 'call'):
            if not START <= i < END and START < target < END:
                raise ValueError('Incoming control enters movement physics-call interior')
            if START <= i < END and kind != 'call' and (not START <= target < END or target in delays):
                raise ValueError('Movement physics-call target exits region or enters delay slot')
        if START <= i < END and flags.control(words[i + 1], i + 1) is not None:
            raise ValueError('Control in movement physics-call delay slot')
    result, identity = list(words), set()
    for i in range(START, END):
        reads, writes = flags.operands(words[i])
        identity.update(words[i] >> s & 31 for s in set(reads) | set(writes) if words[i] >> s & 31 not in mapping)
        result[i] = flags.rename(words[i], mapping)
    if set(mapping.values()) & identity or result[START:END] != truth[START:END]:
        raise ValueError('Movement physics-call literal correspondence or identity collision')
    changed = tuple(i for i in range(START, END) if words[i] != result[i])
    if changed != CHANGED:
        raise ValueError('Changed movement physics-call rewrite sites')
    paths = flags.path_definitions(words, START, END, mapping, terminal_call=True)
    affected = set(mapping) | set(mapping.values())
    # The map is injective, not closed. Neither side may escape as a live role;
    # later calls are not counted as definitions by the continuation scanner.
    liveout = flags.path_definitions(words, END, len(words), {r: r for r in affected})
    unreachable = sorted(set(range(START, END)) - set(paths['visited_indices']))
    if unreachable != [543, 567, 598, 615]:
        raise ValueError('Changed movement physics-call unreachable duplicates')
    return result, dict(kernel_words=END - START, changed_words=len(changed), source_to_retail=mapping,
        affected_physical_registers=sorted(affected), paths=paths, post_call_liveness=liveout,
        unchanged_identity_registers=sorted(identity), injective_not_closed=True,
        unreachable_duplicates_checked_literally_not_by_path_execution=unreachable,
        no_source_live_in_or_either_side_live_out_before_definition=True,
        relocation_metadata_and_low16_addends_unchanged=True,
        C_ABI_only_not_arbitrary_private_or_opaque_provider_equivalence=True)


def guard_text(before, raw_words, bindings):
    fields = next(csv.reader(io.StringIO(before)))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\r\n' if before.endswith('\r\n') else '\n')
    for i in CHANGED:
        word = raw_words[i]
        spec = ';'.join(kind + ':' + symbol for kind, symbol in bindings.get(i * 4, [])) or '-'
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % word, replacement='0x%08X' % flags.rename(word, ROLE_MAP),
            expected_relocations=spec, replacement_relocations=spec,
            note='Normalize branch-qualified movement temporaries through physics call delay slot', omit='false'))
    return before + output.getvalue()


def qualify(root, out):
    freeze(root, out)
    obj, _, words, first31, row = previous.qualify(root, out)
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    expected, proof = prove_roles(first31, truth, bindings)
    table = out / 'expected-physics-call-guards.csv'
    table.write_bytes(guard_text((out / 'expected-schedule-guards.csv').read_bytes().decode(), raw_words, bindings).encode())
    padded = source.literal.padded_object(root, out, obj, 'physics-call-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if normalized_bindings != bindings or linked != expected:
        raise ValueError('Movement physics-call padder/link differs from proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-physics-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement physics-call padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(),
        normalized_target_changed_bytes=sum(a != b for a, b in zip(raw, normalized_raw)),
        physics_call_proof=proof, research_guards=46, new_research_guards=15,
        production_guards_added=0, matching_credit=0, installed=False)
    if (row['normalized_differences'], first) != (88, 633):
        raise ValueError('Changed movement physics-call normalized result')
    (out / 'physics-call-normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, linked, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items()
                      if k not in ('bindings', 'proof', 'physics_call_proof')}, indent=2))
