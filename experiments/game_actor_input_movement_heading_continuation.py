"""Recover movement heading, velocity clamp and continuation lifetimes."""
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_flag_paths as previous

BUILD = 'conker/build/game-actor-input-movement-heading-continuation'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_heading_predecessor', 'tools/experiments/game_actor_input_movement_flag_paths.py',
     '323179346c8db886062251ddd3813596d9ba9056c44a5b73cf612fa3255e3a67'),
    ('movement_heading_predecessor_tests', 'tools/tests/test_game_actor_input_movement_flag_paths.py',
     '1a4682596e9e613232dc87b685111b528995c66e7d78b8ead43b24e55772c172'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement heading predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement heading predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement heading frozen input: ' + key)


replace = previous.replace
UPPER = '            if (actor->verticalVelocity > 26.0f) {'
LOWER = '            if (actor->verticalVelocity < -34.0f) {'


def clamp_forms():
    body = previous.selected_body()
    yield 'previous', body
    for name in ('velocity', 'magnitude', 'pitchValue', 'value'):
        upper = replace(body, UPPER, '            if ((' + name + ' = actor->verticalVelocity) > 26.0f) {')
        lower = replace(body, LOWER, '            if ((' + name + ' = actor->verticalVelocity) < -34.0f) {')
        yield 'upper-' + name, upper
        yield 'lower-' + name, lower
        yield 'clamp-' + name, replace(upper, LOWER, '            if ((' + name + ' = actor->verticalVelocity) < -34.0f) {')
    for name in ('velocity', 'pitchValue'):
        body = previous.selected_body()
        for before, sign, limit in ((UPPER, '>', '26.0f'), (LOWER, '<', '-34.0f')):
            after = ('            ' + name + ' = actor->verticalVelocity;\n'
                     '            if (' + name + ' ' + sign + ' ' + limit + ') {')
            body = replace(body, before, after)
        yield 'snapshot-' + name, body


def normalize(words, truth, bindings):
    result, turn = previous.previous.prove_roles(words, truth, bindings)
    result, flags = previous.prove_roles(result, truth, bindings)
    return result, dict(turn=turn, flags=flags)


def measure(root, out, name, body):
    freeze(root, out)
    # The stronger manifest already includes every inherited predecessor.
    # Call the complete owner measurer without repeating each historical freeze.
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
        row.update(previous_maps_compatible=True,
                   normalized_differences=sum(a != b for a, b in zip(normalized, truth)),
                   normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4)
    (out / (name + '-audit.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


FACING_CALL = '        func_1505A3A8(actor->valueC0, actor, speed, rate, 1);\n'
FACING = FACING_CALL + '        actor->facingAngle = (f32)(actor->yaw + 0x4000) * 0.005493164f;'
ACCELERATION = ('            if (magnitude * D_800A19C0 < velocity && acceleration < 0.0f) {\n'
                '                goto stop_acceleration;\n'
                '            }\n'
                '            if (velocity < -magnitude * 1.5f && acceleration > 0.0f) {\n'
                'stop_acceleration:\n'
                '                actor->acceleration = 0.0f;\n'
                '            }')
PITCH = ('            pitchValue = actor->valueB8;\n'
         '            actor->verticalVelocity = 0.0f;\n'
         '            actor->acceleration = 0.0f;\n'
         '            actor->valueB8 = pitchValue + (((f32)D_800CC284->y - pitchValue) * D_800A19C4);')


def continuation_forms():
    body = dict(clamp_forms())['clamp-velocity']
    yield 'continuation-base', body
    for name in ('index', 'heldIndex'):
        yield 'heading-' + name, replace(body, FACING,
            FACING_CALL + '        ' + name + ' = actor->yaw + 0x4000;\n'
            '        actor->facingAngle = (f32)' + name + ' * 0.005493164f;')
    yield 'zero-first-acceleration', replace(body, '        if (acceleration == 0.0f) {',
                                          '        if (0.0f == acceleration) {')
    yield 'exclusive-acceleration', replace(body, ACCELERATION,
        '            if (magnitude * D_800A19C0 < velocity && acceleration < 0.0f) {\n'
        '                actor->acceleration = 0.0f;\n'
        '            } else if (velocity < -magnitude * 1.5f && acceleration > 0.0f) {\n'
        '                actor->acceleration = 0.0f;\n'
        '            }')
    for name in ('pitchValue', 'value'):
        yield 'early-Y-' + name, replace(body, PITCH,
            '            amount = (f32)D_800CC284->y;\n'
            '            ' + name + ' = actor->valueB8;\n'
            '            actor->verticalVelocity = 0.0f;\n'
            '            actor->acceleration = 0.0f;\n'
            '            actor->valueB8 = ' + name + ' + ((amount - ' + name + ') * D_800A19C4);')


def all_forms():
    yield from clamp_forms()
    yield from continuation_forms()
    yield from combined_forms()


def combined_forms():
    forms = dict(continuation_forms())
    selected = None
    for mode in ('continuation-base', 'exclusive-acceleration'):
        for name in ('index', 'heldIndex'):
            body = replace(forms[mode], PITCH,
                '            ' + name + ' = D_800CC284->y;\n'
                '            value = actor->valueB8;\n'
                '            actor->verticalVelocity = 0.0f;\n'
                '            actor->acceleration = 0.0f;\n'
                '            actor->valueB8 = value + (((f32)' + name + ' - value) * D_800A19C4);')
            yield mode + '-Y-' + name, body
            if mode == 'exclusive-acceleration' and name == 'index':
                selected = body
    # contactHeight is still its initial zero here; its first conditional
    # 50.0f update occurs after the later physics callback.
    pitch = '            pitchValue = (actor->verticalVelocity - 0.0f) * -2.0f;'
    zeroed = replace(selected, pitch,
        '            pitchValue = (actor->verticalVelocity - contactHeight) * -2.0f;')
    yield 'exclusive-Y-index-height-zero', zeroed
    staged = ('            pitchValue = actor->verticalVelocity - contactHeight;\n'
              '            pitchValue *= -2.0f;')
    yield 'exclusive-Y-index-staged-height-zero', replace(selected, pitch, staged)
    named = replace(zeroed, '            index = D_800CC284->y;',
                    '            s32 stickY = D_800CC284->y;')
    yield 'exclusive-Y-named-height-zero', replace(named, '((f32)index - value)', '((f32)stickY - value)')


SELECTED_NAME = 'exclusive-Y-index-height-zero'
SELECTED_SHA = 'febe5b0f8847416cc6e090fb028ffaf84533df97e551d98a7eceead8975eddb6'
SELECTED_DIFFERENCES = 270
NORMALIZED_SHA = '91aea57be0905e303383818b3e09a1fed3c58dcfcaab30961178dba4ac27f6f1'
backend = previous.previous.previous


def selected_body():
    return dict(all_forms())[SELECTED_NAME]


def check_zero_lifetime(body):
    """Prove the reused zero local has no write or address escape at the pitch."""
    from pycparser import c_ast, c_parser
    preamble = ('typedef float f32; typedef double f64; typedef int s32; typedef unsigned int u32;'
                'typedef short s16; typedef unsigned short u16; typedef unsigned char u8; typedef signed char s8;'
                'typedef struct A MovementActor34F4; typedef struct I MovementInput34F4;\n')
    cpp = subprocess.run(['gcc', '-E', '-P', '-xc', '-'], input=preamble + body,
                         text=True, capture_output=True, check=True)
    tree = c_parser.CParser().parse(cpp.stdout)
    functions = [n for n in tree.ext if isinstance(n, c_ast.FuncDef)]
    if len(functions) != 1 or functions[0].decl.name != source.FUNCTION:
        raise ValueError('Changed movement zero-lifetime function')
    function, parents, nodes = functions[0], {}, []

    def walk(node, ancestors=()):
        nodes.append(node)
        parents[id(node)] = ancestors
        for _, child in node.children():
            walk(child, (*ancestors, node))

    walk(function)
    ids = [n for n in nodes if isinstance(n, c_ast.ID) and n.name == 'contactHeight']
    assignments = [n for n in nodes if isinstance(n, c_ast.Assignment)
                   and isinstance(n.lvalue, c_ast.ID) and n.lvalue.name == 'contactHeight']
    if len(ids) != 4 or len(assignments) != 2:
        raise ValueError('Unqualified movement zero write, use or address escape')
    initial, later = sorted(assignments, key=lambda n: n.coord.line)
    first = next(n for n in function.body.block_items if not isinstance(n, c_ast.Decl))
    for assignment, expected in ((initial, '0.0f'), (later, '50.0f')):
        if (assignment.op != '=' or not isinstance(assignment.rvalue, c_ast.Constant)
                or assignment.rvalue.value != expected):
            raise ValueError('Changed movement zero initialization/update')
    if first is not initial:
        raise ValueError('Movement initial zero does not dominate function body')
    uses = [n for n in ids if n is not initial.lvalue and n is not later.lvalue]
    pitch = [n for n in uses if isinstance(parents[id(n)][-1], c_ast.BinaryOp)
             and parents[id(n)][-1].op == '-']
    if len(pitch) != 1:
        raise ValueError('Changed movement zero pitch use')
    pitch = pitch[0]
    gotos = [n for n in nodes if isinstance(n, c_ast.Goto)]
    labels = [n for n in nodes if isinstance(n, c_ast.Label) and n.name == 'disabled_done']
    if (len(gotos) != 1 or len(labels) != 1 or gotos[0].name != 'disabled_done'
            or not initial.coord.line < gotos[0].coord.line < labels[0].coord.line < pitch.coord.line):
        raise ValueError('Unqualified movement zero-lifetime jump')
    ancestors, subtraction = parents[id(pitch)], parents[id(pitch)][-1]
    if (subtraction.right is not pitch or not isinstance(subtraction.left, c_ast.StructRef)
            or not isinstance(subtraction.left.name, c_ast.ID) or subtraction.left.name.name != 'actor'
            or subtraction.left.field.name != 'verticalVelocity'
            or any(isinstance(n, (c_ast.For, c_ast.While, c_ast.DoWhile)) for n in ancestors)
            or not initial.coord.line < pitch.coord.line < later.coord.line):
        raise ValueError('Unqualified movement zero pitch lifetime')
    calls = [n for n in nodes if isinstance(n, c_ast.FuncCall) and isinstance(n.name, c_ast.ID)
             and n.name.name == 'func_15059140' and pitch.coord.line < n.coord.line < later.coord.line]
    remaining = next(n for n in uses if n is not pitch)
    parent = parents[id(remaining)][-1]
    if (not calls or not isinstance(parent, c_ast.BinaryOp) or parent.op != '<='
            or parent.right is not remaining or remaining.coord.line <= later.coord.line):
        raise ValueError('Changed movement height update/continuation boundary')
    return dict(unescaped_local=True, initial_zero_dominates=True, pitch_precedes_only_update=True,
                zero_initial_line=initial.coord.line, pitch_line=pitch.coord.line, later_50_line=later.coord.line,
                identifier_uses=4, writes=2, only_forward_disabled_jump_before_pitch=True,
                no_pitch_enclosing_loop=True,
                C_ABI_only_not_arbitrary_caller_stack_alias_or_hardware_equivalence=True)


def check_layout(record, words, content):
    result = previous.check_layout(record, words, content)
    frame = backend.frame
    summary = frame.summary(record, content, backend.MARKERS)
    markers = {
        'upper': 'if ((velocity = actor->verticalVelocity) > 26.0f) {',
        'lower': 'if ((velocity = actor->verticalVelocity) < -34.0f) {',
        'Y': 'index = D_800CC284->y;',
        'pitch': 'pitchValue = (actor->verticalVelocity - contactHeight) * -2.0f;',
    }
    expected = {
        'frontend': {'upper': [('M', -32, 'R', 4)], 'lower': [('M', -32, 'R', 4)],
                     'Y': [('M', -48, 'J', 4)], 'pitch': [('M', -64, 'R', 4)]},
        'optimizer': {'upper': [('R', 34, 'R', 4)], 'lower': [],
                      'Y': [('R', 3, 'J', 4)], 'pitch': [('R', 34, 'R', 4), ('R', 32, 'R', 4)]},
    }
    lines = {}
    for name, marker in markers.items():
        found = [i + 1 for i, line in enumerate(content.splitlines()) if line.strip() == marker]
        if len(found) != 1:
            raise ValueError('Changed movement continuation layout marker: ' + name)
        lines[name] = found[0]
    stores = {}
    for phase in ('frontend', 'optimizer'):
        current = None
        stores[phase] = {name: [] for name in markers}
        for row in frame.procedure_records(record['records'][phase], summary['procedure']):
            if row['name'] == 'loc':
                current = row['words'][1]
            for name, line in lines.items():
                if current == line and row['name'] == 'str':
                    stores[phase][name].append(row)
        for name, rows in stores[phase].items():
            if [(r['storage'], r['offset'], r['dtype'], r['length']) for r in rows] != expected[phase][name]:
                raise ValueError('Changed movement continuation home: ' + phase + '/' + name)
    for pc, expected_word in ((0x150F3CBC, 0xC6020020), (0x150F3CD8, 0xC6020020),
                              (0x150F3E14, 0x80430003), (0x150F3E58, 0x46101181), (0x150F3EB4, 0xE7A20068)):
        if words[(pc - source.ENTRY) // 4] != expected_word:
            raise ValueError('Changed movement continuation emitted lifetime')
    return dict(previous=result, stores=stores, no_optimizer_store_at_lower_marker_is_not_a_missing_load=True)


def qualify(root, out):
    zero_proof = check_zero_lifetime(selected_body())
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, SELECTED_DIFFERENCES, SELECTED_SHA):
        raise ValueError('Changed movement continuation selected C')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    normalized, proof = normalize(words, truth, bindings)
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, normalized))
               if previous.START <= i < previous.END and a != b]
    table = out / 'expected-continuation-guards.csv'
    table.write_bytes(previous.guard_text((out / 'before-guards').read_bytes().decode(),
                                         raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'continuation-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    if (normalized_bindings != bindings or sum(a != b for a, b in zip(raw, normalized_raw)) != 36
            or hashlib.sha256(normalized_raw).hexdigest() != NORMALIZED_SHA):
        raise ValueError('Changed movement continuation guarded bytes or bindings')
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if linked != normalized:
        raise ValueError('Movement continuation actual padder disagrees with proof')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement continuation padded neighbors')
    row.update(normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(),
        normalized_target_changed_bytes=36, target_relocations_unchanged=True, proof=proof,
        zero_proof=zero_proof, research_guards=28, new_research_guards=0, production_guards_added=0, matching_credit=0, installed=False)
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, normalized, row


def screens(root, out, group='clamp', selected=None):
    rows = []
    for name, body in {'clamp': clamp_forms, 'continuation': continuation_forms, 'combined': combined_forms}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        rows.append({k: v for k, v in row.items() if k != 'bindings'})
        print(json.dumps(rows[-1]), flush=True)
    if not rows:
        raise ValueError('Unknown movement continuation source form')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('clamp', 'continuation', 'combined'), default='clamp')
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
        run = backend.trace if args.trace else backend.finish_trace
        record, words, binary = run(root, root / BUILD, SELECTED_NAME, selected_body())
        print(json.dumps(dict(words=len(words), normal_object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], AS1_instructions=len(binary))))
    else:
        screens(root, root / BUILD, args.group, args.form)
