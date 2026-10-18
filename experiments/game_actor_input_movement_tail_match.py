"""Qualify the complete movement tail permutation and independent address pair."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_physics_call_roles as previous

flags = previous.flags
BUILD = 'conker/build/game-actor-input-movement-tail-match'
START, END = 627, 954
ROLE_MAP = {11: 14, 12: 10, 13: 24, 8: 9, 9: 8, 10: 15, 14: 25, 15: 11, 24: 12, 25: 13}
CALLS = {682: 'func_1505959C', 690: 'func_1506E8D8', 724: 'func_1506E8D8',
         764: 'func_15073FA0', 805: 'func_1506E5FC', 810: 'func_1506E8D8',
         822: 'func_1506E8D8', 895: 'func_150F34A0', 952: 'func_1505E650'}
PAIR = (745, 746)
BINDING_SHA = 'b5f5a0d6a39993007249d2fd038b5d971225c50395f03bda5d9c7f15e72c4551'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_tail_predecessor', 'tools/experiments/game_actor_input_movement_physics_call_roles.py',
     '2bcc6360338d5a0b049acb77639cb327c335a5d2bdcddfd8baf18b03751f8e0f'),
    ('movement_tail_predecessor_tests', 'tools/tests/test_game_actor_input_movement_physics_call_roles.py',
     'e19652188a34867265a7ddc50b18e0b1e21a725d518ce57c8034d212a107c2d4'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement tail predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement tail predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement tail frozen input: ' + key)


def paths(words, mapping):
    pending, seen, visited, calls, branches = [(START, frozenset())], set(), set(), set(), set()
    exits = 0

    def consume(i, defined):
        if not START <= i < END:
            raise ValueError('Unexpected movement tail CFG exit')
        reads, writes = flags.operands(words[i])
        if any(words[i] >> s & 31 in mapping and words[i] >> s & 31 not in defined for s in reads):
            raise ValueError('Movement tail role read before definition at %d' % i)
        visited.add(i)
        return defined | {words[i] >> s & 31 for s in writes if words[i] >> s & 31 in mapping}

    while pending:
        i, defined = pending.pop()
        state = i, frozenset(defined)
        if state in seen:
            continue
        seen.add(state)
        defined = consume(i, defined)
        flow = flags.control(words[i], i)
        if flow is None:
            pending.append((i + 1, frozenset(defined)))
            continue
        kind, target, likely, always, never = flow
        if flags.control(words[i + 1], i + 1) is not None:
            raise ValueError('Control in movement tail delay slot')
        if kind == 'call' and i in CALLS:
            calls.add(i)
            consume(i + 1, defined)
            if i == END - 2:
                exits += 1
            else:
                # Caller-saved physical registers need not return permuted.
                # Every role must be redefined after each actual call.
                pending.append((i + 2, frozenset()))
        elif kind in ('branch', 'jump'):
            if target <= i and (i, target) != (756, 749):
                raise ValueError('Unqualified movement tail backedge')
            if not never:
                branches.add((i, True))
                pending.append((target, frozenset(consume(i + 1, defined))))
            if not always:
                branches.add((i, False))
                pending.append((i + 2, frozenset(defined if likely else consume(i + 1, defined))))
        else:
            raise ValueError('Unqualified movement tail control')
    if calls != set(CALLS) or not exits:
        raise ValueError('Missing movement tail call path')
    return dict(states=len(seen), exit_states=exits, visited_indices=sorted(visited),
                call_indices=sorted(calls), branch_outcomes=sorted(branches),
                all_roles_invalidated_after_every_call=True)


def prove_tail(words, truth, bindings, mapping=None):
    mapping = dict(ROLE_MAP if mapping is None else mapping)
    if mapping != ROLE_MAP or set(mapping) != set(mapping.values()):
        raise ValueError('Invalid movement tail closed permutation')
    if (START, END, PAIR) != (627, 954, (745, 746)):
        raise ValueError('Changed movement tail proof boundaries')
    if len(words) != 959 or len(truth) != 959 or words[0] != 0x27BDFF80:
        raise ValueError('Changed movement tail extent/frame')
    region_bindings = {k: v for k, v in bindings.items() if START * 4 <= k < END * 4}
    if hashlib.sha256(json.dumps(region_bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != BINDING_SHA:
        raise ValueError('Changed movement tail relocation binding')
    delays = {i + 1 for i in range(START, END) if flags.control(words[i], i) is not None}
    calls = set()
    for i, word in enumerate(words):
        flow = flags.control(word, i)
        if flow is None:
            continue
        kind, target, *_ = flow
        if kind in ('branch', 'jump', 'call'):
            if not START <= i < END and START < target < END:
                raise ValueError('Incoming control enters movement tail interior')
            if START <= i < END and kind != 'call' and (not START <= target < END or target in delays):
                raise ValueError('Movement tail target exits region or enters delay slot')
        if START <= i < END:
            if flags.control(words[i + 1], i + 1) is not None:
                raise ValueError('Control in movement tail delay slot')
            if kind == 'call':
                if i not in CALLS or bindings.get(i * 4) != [('R_MIPS_26', CALLS[i])] or word != truth[i]:
                    raise ValueError('Changed movement tail call target')
                calls.add(i)
            if kind in ('branch', 'jump') and target <= i and (i, target) != (756, 749):
                raise ValueError('Unqualified movement tail backedge')
    if calls != set(CALLS):
        raise ValueError('Changed movement tail call set')
    if tuple(words[i] for i in PAIR) != (0x2442C5FC, 0x24A5121C):
        raise ValueError('Changed movement tail independent address words')
    if any(i in delays for i in PAIR):
        raise ValueError('Movement tail address word is a delay slot')
    for i, word in enumerate(words):
        flow = flags.control(word, i)
        if flow and flow[0] in ('branch', 'jump', 'call') and flow[1] in (746, 747):
            raise ValueError('Movement tail entry splits independent address pair')
    reads0, writes0 = flags.operands(words[PAIR[0]])
    reads1, writes1 = flags.operands(words[PAIR[1]])
    r0 = {words[PAIR[0]] >> s & 31 for s in reads0}
    w0 = {words[PAIR[0]] >> s & 31 for s in writes0}
    r1 = {words[PAIR[1]] >> s & 31 for s in reads1}
    w1 = {words[PAIR[1]] >> s & 31 for s in writes1}
    if w0 & (r1 | w1) or w1 & (r0 | w0):
        raise ValueError('Dependent movement tail address pair')
    result, identity = list(words), set()
    for i in range(START, END):
        reads, writes = flags.operands(words[i])
        identity.update(words[i] >> s & 31 for s in set(reads) | set(writes) if words[i] >> s & 31 not in mapping)
        result[i] = flags.rename(words[i], mapping)
    role_changes = [i for i in range(START, END) if words[i] != result[i]]
    if len(role_changes) != 86 or set(mapping.values()) & identity:
        raise ValueError('Changed movement tail role sites or identity collision')
    result[745], result[746] = result[746], result[745]
    if result != list(truth):
        raise ValueError('Movement tail complete literal correspondence failed')
    local = paths(words, mapping)
    unreachable = sorted(set(range(START, END)) - set(local['visited_indices']))
    if unreachable != [815, 842, 864, 892]:
        raise ValueError('Changed movement tail unreachable duplicates')
    liveout = flags.path_definitions(words, END, len(words), mapping)
    return result, dict(kernel_words=END - START, changed_role_words=len(role_changes),
        source_to_retail=mapping, paths=local, post_call_liveness=liveout,
        identity_registers=sorted(identity), unreachable_literal_duplicates=unreachable,
        independent_nontrapping_ADDIU_pair=list(PAIR),
        call_arguments_identity_O32_registers_4_to_7_and_stack_and_FP=True,
        C_ABI_only_not_arbitrary_unpassed_callee_private_registers=True)


def guard_text(before, raw_words, bindings):
    fields = next(csv.reader(io.StringIO(before)))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\r\n' if before.endswith('\r\n') else '\n')
    swapped = {PAIR[0]: PAIR[1], PAIR[1]: PAIR[0]}
    for i in range(START, END):
        replacement = raw_words[swapped[i]] if i in PAIR else flags.rename(raw_words[i], ROLE_MAP)
        if replacement == raw_words[i]:
            continue
        relocation_index = swapped.get(i, i)
        before_spec = ';'.join(k + ':' + s for k, s in bindings.get(i * 4, [])) or '-'
        after_spec = ';'.join(k + ':' + s for k, s in bindings.get(relocation_index * 4, [])) or '-'
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % raw_words[i], replacement='0x%08X' % replacement,
            expected_relocations=before_spec, replacement_relocations=after_spec,
            note=('Schedule independent movement record-bound addresses' if i in PAIR else
                  'Normalize call-invalidated movement tail temporary permutation'), omit='false'))
    return before + output.getvalue()


def qualify(root, out):
    freeze(root, out)
    obj, _, words, first46, row = previous.qualify(root, out)
    raw, bindings = source.parts(obj)
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    expected, proof = prove_tail(first46, truth, bindings)
    table = out / 'expected-tail-guards.csv'
    table.write_bytes(guard_text((out / 'expected-physics-call-guards.csv').read_bytes().decode(),
                                 list(struct.unpack('>959I', raw)), bindings).encode())
    padded = source.literal.padded_object(root, out, obj, 'tail-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    wanted_bindings = dict(bindings)
    wanted_bindings[745 * 4], wanted_bindings[746 * 4] = bindings[746 * 4], bindings[745 * 4]
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if normalized_bindings != wanted_bindings or linked != expected:
        raise ValueError('Movement tail padder/link differs from proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-tail-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement tail padded neighbors')
    row.update(normalized_differences=0, normalized_exact_opening_words=959, normalized_first_PC=None,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(),
        normalized_target_changed_bytes=sum(a != b for a, b in zip(raw, normalized_raw)),
        target_relocations_unchanged=False, target_relocations_only_address_pair_moved=True,
        tail_proof=proof, research_guards=134, new_research_guards=88,
        production_guards_added=0, matching_credit=0, installed=False)
    (out / 'tail-normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, linked, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items()
                      if k not in ('bindings', 'proof', 'physics_call_proof', 'tail_proof')}, indent=2))
