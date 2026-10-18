"""Recover movement zero, count-loop and final speed-test scalar lifetimes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_input_movement_pitch_surface_order as previous

source = previous.source
BUILD = 'conker/build/game-actor-input-movement-scalar-lifetimes'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_scalar_predecessor', 'tools/experiments/game_actor_input_movement_pitch_surface_order.py',
     '9092f3a1dc717383a07bbe87bb90e1fbe1c7ab6380f26d53dfb0cceb2bc6c89f'),
    ('movement_scalar_predecessor_tests', 'tools/tests/test_game_actor_input_movement_pitch_surface_order.py',
     'c151396274aa68581956bb4ead937da3293ab6f34a90a8215ba70db65c4f4ddf'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement scalar predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement scalar predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement scalar frozen input: ' + key)


replace = previous.replace


def zero_forms():
    body = previous.selected_body()
    yield 'previous', body
    for label, condition in (('right', 'acceleration == contactHeight'),
                             ('left', 'contactHeight == acceleration')):
        yield 'zero-' + label, replace(body, 'acceleration == 0.0f', condition)


COUNT = ('                count = 0;\n'
         '                if (D_800BE9F0 == 0x3C) {\n'
         '                    record = (MovementActor34F4 *)D_800CC5FC;')
END = '                    } while ((u8 *)record != D_800D121C);'


def count_forms():
    body = previous.selected_body()
    yield 'count-base', body
    for slot in ('before', 'after'):
        lines = ['                if (D_800BE9F0 == 0x3C) {',
                 '                    record = (MovementActor34F4 *)D_800CC5FC;']
        lines.insert(1 if slot == 'before' else 2, '                    count = 0;')
        yield 'count-initialize-' + slot, replace(body, COUNT, '\n'.join(lines))
    for slot in ('before', 'after'):
        declaration = '                    MovementActor34F4 *recordEnd;'
        assignment = '                    recordEnd = (MovementActor34F4 *)D_800D121C;'
        lines = COUNT.splitlines()
        lines.insert(2, declaration)
        lines.insert(3 if slot == 'before' else 4, assignment)
        candidate = replace(body, COUNT, '\n'.join(lines))
        yield 'count-end-' + slot, replace(candidate, END, '                    } while (record != recordEnd);')
    start = body.index(COUNT)
    stop = body.index('\n            }\n        }\n        if (actor->depth', start)
    block = body[start:stop]
    for name in ('index', 'heldIndex'):
        yield 'count-reuse-' + name, body[:start] + block.replace('count', name) + body[stop:]
    for name in ('cursor', 'countRecord'):
        current = block.replace('record', name)
        current = current.replace('                count = 0;',
                                  '                MovementActor34F4 *' + name + ';\n                count = 0;', 1)
        yield 'count-pointer-' + name, body[:start] + current + body[stop:]


def final_forms():
    body = previous.selected_body()
    yield 'final-base', body
    for label, condition in (('integer', 'value < 20'), ('double', 'value < 20.0'),
                             ('reversed', '20.0f > value')):
        yield 'final-' + label, replace(body, 'value < 20.0f', condition)
    for name in ('velocity', 'rate', 'pitchValue', 'lowSpeedLimit'):
        candidate = body
        if name == 'lowSpeedLimit':
            candidate = replace(candidate, '    u32 buttons;', '    u32 buttons;\n    f32 lowSpeedLimit;')
        candidate = replace(candidate, '        value = actor->speed;',
            '        ' + name + ' = 20.0f;\n        value = actor->speed;')
        yield 'final-limit-' + name, replace(candidate, 'value < 20.0f', 'value < ' + name)
    sampled = replace(body, '        value = actor->speed;\n', '')
    for label, condition in (('left', '(value = actor->speed) < 20.0f'),
                             ('right', '20.0f > (value = actor->speed)')):
        yield 'final-sample-' + label, replace(sampled, 'value < 20.0f', condition)


def all_forms():
    yield from zero_forms()
    yield from count_forms()
    yield from final_forms()
    yield from coupled_forms()


def coupled_forms():
    body = dict(count_forms())['count-pointer-countRecord']
    body = replace(body, 'acceleration == 0.0f', 'contactHeight == acceleration')
    yield 'count-pointer-zero', body
    sampled = replace(body, '        value = actor->speed;\n', '')
    for label, condition in (('left', '(value = actor->speed) < 20.0f'),
                             ('right', '20.0f > (value = actor->speed)')):
        yield 'count-pointer-zero-speed-' + label, replace(sampled, 'value < 20.0f', condition)
    assignment = '                    countRecord = (MovementActor34F4 *)D_800CC5FC;'
    for slot in ('before', 'after'):
        lines = ['                    MovementActor34F4 *countEnd;']
        bound = '                    countEnd = (MovementActor34F4 *)D_800D121C;'
        lines.extend((bound, assignment) if slot == 'before' else (assignment, bound))
        candidate = replace(body, assignment, '\n'.join(lines))
        yield 'count-pointer-zero-end-' + slot, replace(candidate,
            '                    } while ((u8 *)countRecord != D_800D121C);',
            '                    } while (countRecord != countEnd);')


def check_zero_lifetime(body):
    """Extend the earlier AST proof with one dominated zero comparison."""
    from pycparser import c_ast, c_parser
    marker = 'if (contactHeight == acceleration) {'
    stripped = replace(body, marker, 'if (acceleration == 0.0f) {')
    proof = previous.previous.previous.check_zero_lifetime(stripped)
    preamble = ('typedef float f32; typedef double f64; typedef int s32; typedef unsigned int u32;'
                'typedef short s16; typedef unsigned short u16; typedef unsigned char u8; typedef signed char s8;'
                'typedef struct A MovementActor34F4; typedef struct I MovementInput34F4;\n')
    cpp = subprocess.run(['gcc', '-E', '-P', '-xc', '-'], input=preamble + body,
                         text=True, capture_output=True, check=True)
    tree = c_parser.CParser().parse(cpp.stdout)
    nodes, parents = [], {}

    def walk(node, ancestors=()):
        nodes.append(node)
        parents[id(node)] = ancestors
        for _, child in node.children():
            walk(child, (*ancestors, node))

    walk(tree)
    comparisons = [n for n in nodes if isinstance(n, c_ast.BinaryOp) and n.op == '=='
                   and isinstance(n.left, c_ast.ID) and n.left.name == 'contactHeight']
    if len(comparisons) != 1:
        raise ValueError('Changed movement scalar zero comparison')
    comparison = comparisons[0]
    ancestors = parents[id(comparison)]
    branch = ancestors[-1]
    if (not isinstance(comparison.right, c_ast.ID) or comparison.right.name != 'acceleration'
            or not isinstance(branch, c_ast.If) or branch.cond is not comparison
            or any(isinstance(n, (c_ast.For, c_ast.While, c_ast.DoWhile)) for n in ancestors)
            or not proof['zero_initial_line'] < comparison.coord.line < proof['pitch_line'] < proof['later_50_line']):
        raise ValueError('Unqualified movement scalar zero comparison lifetime')
    compound = parents[id(branch)][-1]
    if not isinstance(compound, c_ast.Compound):
        raise ValueError('Changed movement scalar comparison scope')
    items = compound.block_items
    index = items.index(branch)
    if index < 2:
        raise ValueError('Missing movement scalar comparison inputs')
    for assignment, name, field in ((items[index - 2], 'acceleration', 'acceleration'),
                                    (items[index - 1], 'velocity', 'verticalVelocity')):
        if (not isinstance(assignment, c_ast.Assignment) or assignment.op != '='
                or not isinstance(assignment.lvalue, c_ast.ID) or assignment.lvalue.name != name
                or not isinstance(assignment.rvalue, c_ast.StructRef) or assignment.rvalue.type != '->'
                or not isinstance(assignment.rvalue.name, c_ast.ID) or assignment.rvalue.name.name != 'actor'
                or assignment.rvalue.field.name != field):
            raise ValueError('Changed movement scalar comparison input dominance')
    return dict(proof, identifier_uses=5, comparison_line=comparison.coord.line,
                extra_comparison_zero_dominated_and_unescaped=True,
                acceleration_and_velocity_assignments_precede_comparison=True)


SELECTED_NAME = 'count-pointer-zero-speed-left'
SELECTED_SHA = 'bb6adfabfc1313eacf798fce43423b75eea912051212638b373e18e1808235eb'
backend = previous.previous.backend


def selected_body():
    return dict(coupled_forms())[SELECTED_NAME]


def check_layout(record, words, content):
    if record.get('code_unchanged') is not True or record.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement scalar layout')
    markers = dict(backend.MARKERS,
        countPointer='countRecord = (MovementActor34F4 *)D_800CC5FC;',
        releaseIndex='s32 releaseIndex = actor->held - 100;')
    summary = backend.frame.summary(record, content, markers)
    phases = summary['phases']
    sizes = [[r['length'] for r in phases[p]['definitions'] if r['storage'] == 'M']
             for p in ('frontend', 'optimizer')]
    for name, offset in backend.HOMES.items():
        stores = [r for r in phases['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M']
        kind, size = ('L', 2) if name == 'angle' else ('J', 4) if name == 'index' else ('A', 4) if name == 'record' else ('R', 4)
        if [(r['offset'], r['dtype'], r['length']) for r in stores] != [(offset, kind, size)]:
            raise ValueError('Changed movement scalar predecessor home: ' + name)
    expected = {'countPointer': {'frontend': ('M', -92, 'A', 4), 'optimizer': ('R', 2, 'A', 4)},
                'releaseIndex': {'frontend': ('M', -88, 'J', 4), 'optimizer': ('R', 4, 'J', 4)}}
    stores = {}
    for name, profiles in expected.items():
        stores[name] = {}
        for phase, profile in profiles.items():
            found = [r for r in phases[phase]['markers'][name] if r['name'] == 'str']
            if [(r['storage'], r['offset'], r['dtype'], r['length']) for r in found] != [profile]:
                raise ValueError('Changed movement scalar home: ' + phase + '/' + name)
            stores[name][phase] = found[0]
    events = record['events']
    if (sizes != [[92], [76]] or [e['event'] for e in events] != ['frame-watch-installed', 'frame-write', 'frame-write', 'frame-write']
            or [e['host_pc'] for e in events] != [4268224, 4566873, 4523375, 4523375]
            or [e['frame'] for e in events] != [0, 16, 48, 128]
            or [(e['saved'], e['outgoing'], e['locals']) for e in events] != [(0, 0, 0), (16, 0, 0), (16, 32, 0), (16, 32, 80)]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)):
        raise ValueError('Changed movement scalar frame budgets')
    sites = ((0x150F34F4, 0x27BDFF80), (0x150F34F8, 0xAFB00028),
             (0x150F3504, 0xAFBF002C), (0x150F3508, 0xE7B00058),
             (0x150F3D44, 0x46008032), (0x150F4088, 0x00001825),
             (0x150F4090, 0x3C02800D), (0x150F4094, 0x3C05800D),
             (0x150F40BC, 0x24630001), (0x150F434C, 0x44813000), (0x150F4350, 0xC600003C))
    if any(words[(pc - source.ENTRY) // 4] != word for pc, word in sites):
        raise ValueError('Changed movement scalar emitted lifetime')
    return dict(frontend=92, optimizer=76, rounded=80, frame=128, saved=16, outgoing=32,
                old_homes=backend.HOMES, homes=stores, sites=[(pc - source.ENTRY) // 4 for pc, _ in sites],
                count_pointer_is_used_A4_R2_not_padding=True)


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


def qualify(root, out):
    zero_proof = check_zero_lifetime(selected_body())
    obj, words, row = measure(root, out, SELECTED_NAME, selected_body())
    if tuple(row[k] for k in ('words', 'frame', 'differences', 'raw_sha')) != (959, 128, 139, SELECTED_SHA):
        raise ValueError('Changed movement scalar selected C')
    raw, bindings = source.parts(obj)
    raw_words = list(struct.unpack('>959I', raw))
    truth = list(struct.unpack_from('>959I', (out / 'before-retail_rom').read_bytes(), source.ROM))
    first28, _ = previous.previous.previous.normalize(words, truth, bindings)
    expected, proof = previous.normalize(words, truth, bindings)
    flags = previous.previous.flags
    changes = [(i * 4, a, b) for i, (a, b) in enumerate(zip(words, first28))
               if flags.START <= i < flags.END and a != b]
    table = out / 'expected-scalar-guards.csv'
    table.write_bytes(previous.previous.guard_text((out / 'before-guards').read_bytes().decode(), raw_words, bindings, changes).encode())
    padded = source.literal.padded_object(root, out, obj, 'scalar-normalized', table)
    normalized_raw, normalized_bindings = source.parts(padded)
    image, functions = source.build.link_owner(root, out, padded, source.OWNER)
    linked = list(struct.unpack_from('>959I', image, functions[source.FUNCTION]['value']))
    if normalized_bindings != bindings or sum(a != b for a, b in zip(raw, normalized_raw)) != 39 or linked != expected:
        raise ValueError('Changed movement scalar guarded bytes or bindings')
    before = source.literal.padded_object(root, out, out / 'owner-before.o', 'protected-owner-before')
    if source.same_functions(before, padded, (source.FUNCTION,)) != 11:
        raise ValueError('Changed movement scalar padded neighbors')
    first = next(i for i, (a, b) in enumerate(zip(linked, truth)) if a != b)
    row.update(normalized_differences=sum(a != b for a, b in zip(linked, truth)),
        normalized_exact_opening_words=first, normalized_first_PC=source.ENTRY + first * 4,
        normalized_raw_sha=hashlib.sha256(normalized_raw).hexdigest(), normalized_target_changed_bytes=39,
        target_relocations_unchanged=True, proof=proof, zero_proof=zero_proof,
        research_guards=31, new_research_guards=0, production_guards_added=0, matching_credit=0, installed=False)
    if (row['normalized_differences'], first) != (108, 478):
        raise ValueError('Changed movement scalar normalized result')
    (out / 'normalization-audit.json').write_text(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2) + '\n')
    freeze(root, out)
    return obj, padded, words, linked, row


def screens(root, out, group, selected=None):
    rows = []
    for name, body in {'zero': zero_forms, 'count': count_forms, 'final': final_forms,
                       'coupled': coupled_forms}[group]():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        rows.append({k: v for k, v in row.items() if k != 'bindings'})
        print(json.dumps(rows[-1]), flush=True)
    if not rows:
        raise ValueError('Unknown movement scalar source form')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('zero', 'count', 'final', 'coupled'), default='zero')
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
        print(json.dumps(dict(words=len(words), object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], AS1_instructions=len(binary))))
    else:
        screens(root, root / BUILD, args.group, args.form)
