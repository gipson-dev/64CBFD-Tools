"""Recover movement return layout with complete source and unchanged compiler gates."""
import hashlib
import json
from pathlib import Path
from collections import Counter
import struct
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_allocation as previous
from tools.experiments import game_actor_command_finalizer_backend_trace as backend

source = previous.source
BUILD = 'conker/build/game-actor-input-movement-return'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_return_predecessor', 'tools/experiments/game_actor_input_movement_allocation.py',
     '7bf5055197bbf49e2f0687ee25976df112c8089c0a14928e1058eafd42b70c01'),
    ('movement_return_predecessor_tests', 'tools/tests/test_game_actor_input_movement_allocation.py',
     'ed7e643ab1bfbc218897200d35d29269ac66f4f33150fbee7f5b3ee7bd82b762'),
    ('movement_return_backend', 'tools/experiments/game_actor_command_finalizer_backend_trace.py',
     'd86989f315d22eff8b3e428f9a9054e294ed323c33034cf0ad122ed1813cb2a0'),
    ('movement_return_backend_nodes', 'tools/experiments/game_text_measurer_ugen_nodes.py',
     'afb7dae1d47e87f7a2b86c1a6eabf852aa47444bf103d3adfbc17911ca2cdd6b'),
    ('movement_return_compiler_as1', 'ido/ido5.3_recomp/as1',
     'dc18ffdd8cb629eaf71489507d4186674d44b9aa86bf26d8821d4e138e9ab2b6'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement return predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement return predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement return frozen input: ' + key)


def conditional_heading(body):
    before = ('        actor->desiredHeading = (u16)actor->yaw;\n'
              '        angle = (u16)((u32)angle + (u32)D_800CC280);\n'
              '        if (initialMagnitude > 1.0f) {\n'
              '            actor->desiredHeading = angle;\n'
              '        }')
    after = ('        actor->desiredHeading = actor->yaw;\n'
             '        if (initialMagnitude > 1.0f) {\n'
             '            actor->desiredHeading = (u16)((u32)angle + (u32)D_800CC280);\n'
             '        }')
    return previous.replace(body, before, after)


def held_guard(body, common_exit=False):
    header = '        if (actor->held != 0) {\n'
    end = '    } else if (actor->mode == 0) {'
    lo, hi = body.index(header), body.index(end)
    inner = body[lo + len(header):hi]
    if not inner.endswith('        }\n') or lo >= hi:
        raise ValueError('Changed disabled release block')
    lines = inner[:-10].splitlines(keepends=True)
    if any(line.strip() and not line.startswith('            ') for line in lines):
        raise ValueError('Unexpected nested disabled release')
    release = ''.join(line[4:] if line.strip() else line for line in lines)
    command = 'goto movement_done;' if common_exit else 'return;'
    guard = '        if (actor->held == 0) {\n            ' + command + '\n        }\n'
    result = body[:lo] + guard + release + body[hi:]
    if common_exit:
        if not result.endswith('\n}'):
            raise ValueError('Changed movement function end')
        result = result[:-1] + 'movement_done:\n    return;\n}'
    return result


def forms():
    body = previous.selected_body()
    yield 'selected', body
    yield 'held-zero-return', held_guard(body)
    yield 'held-zero-return-conditional-heading', held_guard(conditional_heading(body))
    yield 'held-zero-exit', held_guard(body, common_exit=True)
    yield 'held-zero-exit-conditional-heading', held_guard(conditional_heading(body), common_exit=True)
    cached = previous.replace(body, '    s32 heldIndex;', '    s32 heldIndex;\n    u32 heldValue;')
    before = ('        if (actor->held != 0) {\n'
              '            heldIndex = actor->held - 100;')
    after = ('        heldValue = actor->held;\n'
             '        if (heldValue != 0) {\n'
             '            heldIndex = (s32)heldValue - 100;')
    yield 'cached-held-value', previous.replace(cached, before, after)


def exit_forms():
    for name, body in (('local-disabled-exit', previous.selected_body()),
                       ('local-disabled-exit-conditional-heading', conditional_heading(previous.selected_body()))):
        body = held_guard(body)
        body = previous.replace(body, '        if (actor->held == 0) {\n            return;\n        }',
                                '        if (actor->held == 0) {\n            goto disabled_done;\n        }')
        body = previous.replace(body, '    } else if (actor->mode == 0) {',
                                'disabled_done:\n        return;\n    } else if (actor->mode == 0) {')
        yield name, body
    yield 'nonvoid-ABI-control', previous.replace(previous.selected_body(),
        'void func_150F34F4(MovementActor34F4 *actor)', 's32 func_150F34F4(MovementActor34F4 *actor)')


def separate_buttons(body, kind='u32', name='buttons'):
    if name == 'buttons':
        body = previous.replace(body, '    s32 heldIndex;', '    s32 heldIndex;\n    ' + kind + ' buttons;')
    start = body.index('        angle = D_800CC284->buttons;')
    end = body.index('        func_1505A3A8(', start)
    block = body[start:end]
    if block.count('angle') != 5:
        raise ValueError('Changed movement button-snapshot block')
    return body[:start] + block.replace('angle', name) + body[end:]


def button_forms():
    body = dict(exit_forms())['local-disabled-exit']
    for kind in ('u32', 's32', 'u16'):
        yield 'separate-' + kind + '-buttons', separate_buttons(body, kind)
    for name in ('animation', 'count'):
        yield 'reuse-' + name + '-buttons', separate_buttons(body, name=name)


def heading_forms():
    body = dict(button_forms())['separate-u32-buttons']
    before = ('        actor->desiredHeading = (u16)actor->yaw;\n'
              '        angle = (u16)((u32)angle + (u32)D_800CC280);')
    after = ('        angle = (u16)((u32)angle + (u32)D_800CC280);\n'
             '        actor->desiredHeading = (u16)actor->yaw;')
    heading = previous.replace(body, before, after)
    yield 'heading-before-yaw', heading
    for name, candidate in (('unsigned-yaw', body), ('heading-before-unsigned-yaw', heading)):
        yield name, previous.replace(candidate, 'actor->desiredHeading = (u16)actor->yaw;',
                                      'actor->desiredHeading = *(u16 *)&actor->yaw;')


SELECTED_NAME = 'heading-before-unsigned-yaw'
SELECTED_SHA = 'ba72844ce4ee23c39a00a669951e6ab8891c58104360f4fceaf605879acee082'


def selected_body():
    return dict(heading_forms())[SELECTED_NAME]


def all_forms():
    yield from forms()
    yield from exit_forms()
    yield from button_forms()
    yield from heading_forms()


def measure(root, out, name, body):
    freeze(root, out)
    return previous.measure(root, out, name, body)


FRAME_SCRIPT = previous.frame.shared.debugger_script


def debugger_script(root, work):
    reference = backend.debugger_script(root, work)
    start = 'from pathlib import Path\nimport hashlib\nas1 = '
    end = 'end\ncatch exec'
    if reference.count(start) != 1 or reference.count(end) != 1:
        raise ValueError('Changed qualified AS1 collector anchors')
    declaration = reference[reference.index(start):reference.index(end)]
    declaration = previous.replace(declaration,
        '    if gdb.current_progspace().filename != as1:\n        return\n    inferior =',
        '    if gdb.current_progspace().filename != as1:\n        return\n'
        '    if any(probe.is_valid() for probe in movement_emit_probes):\n'
        "        raise gdb.GdbError('UGEN emitter probes survived into AS1')\n"
        '    inferior =')
    declaration += "program = str(compiler_dir / 'ugen')\n"
    declaration += '''movement_emit_probes = []
def movement_emit_removed(event):
    if event.inferior.progspace.filename == program:
        for probe in movement_emit_probes:
            if probe.is_valid():
                name = probe.name
                probe.delete()
                gdb.write('FINALIZER_EMIT_REMOVED ' + name + '\\n')
gdb.events.exited.connect(movement_emit_removed)
'''
    script = FRAME_SCRIPT(root, work)
    script = previous.replace(script, end, declaration + end)
    script = previous.replace(script, 'python\ncapture()\n', 'python\ncapture_as1()\ncapture()\n')
    install = "    Begin('f_readuinstr.constprop.0')"
    observers = ''.join("\n    movement_emit_probes.append(EmitObserver(%r, 0x%x))\n    gdb.write('FINALIZER_EMIT_INSTALLED %s\\n')" %
                        (name, address, name) for name, address in backend.PROBES.items())
    script = previous.replace(script, install, install + observers)
    marker = "    if breakpoint.location in ('f_spill_to_temp','f_temp_offset','f_free_temp'):"
    locations = tuple('*0x%x' % address for address in backend.PROBES.values())
    cleanup = ("    if breakpoint.location in %r:\n"
               "        name = breakpoint.name\n"
               "        breakpoint.delete()\n"
               "        gdb.write('FINALIZER_EMIT_REMOVED ' + name + '\\n')\n"
               "    elif breakpoint.location in ('f_spill_to_temp','f_temp_offset','f_free_temp'):") % (locations,)
    return previous.replace(script, marker, cleanup)


def trace(root, out, name=SELECTED_NAME, body=None):
    if Path(name).name != name or name in ('.', '..'):
        raise ValueError('Movement trace name must be one owned path component')
    freeze(root, out)
    body = dict(all_forms())[name] if body is None else body
    with patch.object(previous.frame.shared, 'debugger_script', debugger_script):
        record, words = previous.capture(root, out, name, body)
    return finish_trace(root, out, name, body)


def finish_trace(root, out, name, body):
    work = out / 'traces' / name
    record = json.loads((work / 'allocation-summary.json').read_text())
    content = (work / 'baseline.c').read_text()
    if (content != previous.frame.isolated(body)
            or hashlib.sha256(content.encode()).hexdigest() != record['source_sha']
            or record.get('exit_code') != 0 or record.get('code_unchanged') is not True
            or record.get('whole_owner_target_identical') is not True
            or record.get('compiler_sha256') != previous.frame.shared.fingerprints(root)
            or source.parse_object(work / 'baseline.o') != source.parse_object(work / 'trace.o')
            or source.parts(work / 'baseline.o') != source.parts(out / (name + '.o'))
            or source.normalized_pools(work / 'baseline.o') != source.normalized_pools(work / 'trace.o')):
        raise ValueError('Changed completed movement backend capture')
    raw, _ = source.parts(work / 'baseline.o')
    count = len(raw) // 4
    words = source.linked(root, work, work / 'baseline.o', 'verified-linked')
    saved = list(struct.unpack_from('>%dI' % count, source.projection.sections(work / 'baseline-linked.elf')['.text'][1]))
    if (words != saved or record['baseline'] != dict(words=count, frame=(-words[0]) & 65535,
            raw_sha=hashlib.sha256(raw).hexdigest(), whole_owner_target_identical=True)):
        raise ValueError('Changed backend target metadata or real link bindings')
    log = (work / 'debugger.txt').read_text()
    observations = previous.frame.shared.validate_observations(work, log)
    if any(record[k] != observations[k] for k in ('events', 'inputs', 'records')):
        raise ValueError('Changed movement frame/wire capture')
    with patch.object(backend.nodes, 'CHILD_EXIT', 'TRACE_EXIT inferior=4 code=0'):
        events = backend.emitter_events(log)
        assembler = backend.validate_as1(work, log)
    binary = backend.instruction_records((work / 'as1-input-11.bin').read_bytes())
    emitted = Counter((e['raw']['rdx'], e['raw']['rcx'],
                       72 if e['probe'] == 'immediate' else e['raw']['r9'], e['raw']['r8']) for e in events)
    captured = Counter((r['opcode'], r['register0'], r['register1'], r['word3']) for r in binary)
    if emitted - captured:
        raise ValueError('Movement UGEN emitter disagrees with real AS1 input')
    record.update(assembler=assembler, emitter_events=events, correlated_events=sum(emitted.values()),
                  compiler_as1_sha256=BASELINE['movement_return_compiler_as1'])
    (work / 'return-summary.json').write_text(json.dumps(record, indent=2) + '\n')
    freeze(root, out)
    return record, words, binary


def check_layout(record, words, content):
    if record.get('code_unchanged') is not True or record.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement return layout')
    frame = previous.frame
    markers = dict(frame.MARKERS)
    markers['distanceCall'] = 'nearestDistance = func_1505A6F8(D_800D154C, record);'
    markers['turn'] = 'func_150599C8(actor, 8, (u16)heading);'
    summary = frame.summary(record, content, markers)
    phases = summary['phases']
    local_bytes = [[r['length'] for r in phases[p]['definitions'] if r['storage'] == 'M']
                   for p in ('frontend', 'optimizer')]
    homes = dict(contact=-40, speed=-24, input=-20, angle=-2, distance=-56,
                 index=-48, record=-76, distanceCall=-52)
    for name, offset in homes.items():
        stores = [r for r in phases['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M']
        dtype, size = ('L', 2) if name == 'angle' else ('J', 4) if name == 'index' else ('A', 4) if name == 'record' else ('R', 4)
        if len(stores) != 1 or (stores[0]['offset'], stores[0]['dtype'], stores[0]['length']) != (offset, dtype, size):
            raise ValueError('Changed movement return live home: ' + name)
    lines = [i + 1 for i, line in enumerate(content.splitlines()) if line.strip() == 'buttons = D_800CC284->buttons;']
    if len(lines) != 2:
        raise ValueError('Changed movement buttons source markers')
    current = None
    stores = []
    for row in frame.procedure_records(record['records']['frontend'], summary['procedure']):
        if row['name'] == 'loc':
            current = row['words'][1]
        if current == lines[0] and row['name'] == 'str' and row['storage'] == 'M':
            stores.append(row)
    events = record['events']
    if (local_bytes != [[88], [76]] or len(stores) != 1
            or (stores[0]['offset'], stores[0]['dtype'], stores[0]['length']) != (-88, 'L', 4)
            or [e['event'] for e in events] != ['frame-watch-installed', 'frame-write', 'frame-write', 'frame-write']
            or [e['frame'] for e in events] != [0, 16, 48, 128]
            or [e['host_pc'] for e in events] != [4268224, 4566873, 4523375, 4523375]
            or [(e['saved'], e['outgoing'], e['locals']) for e in events] != [(0, 0, 0), (16, 0, 0), (16, 32, 0), (16, 32, 80)]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)
            or (words[0], words[1], words[4], words[5]) != (0x27BDFF80, 0xAFB00028, 0xAFBF002C, 0xE7B00058)):
        raise ValueError('Changed movement frame or real buttons home')
    angle_call = words.index(0x0D41698C)
    magnitude_call = words.index(0x0D416973)
    if sum(w >> 26 == 41 and w >> 21 & 31 == 29 and w & 65535 == 0x7E
           for w in words[angle_call + 1:magnitude_call + 2]) != 1:
        raise ValueError('Changed emitted movement angle store')
    distance_call = words.index(0x0D4169BE)
    for op, offset in ((43, 0x50), (43, 0x34), (57, 0x48)):
        if sum(w >> 26 == op and w >> 21 & 31 == 29 and w & 65535 == offset
               for w in words[distance_call - 5:distance_call + 2]) != 1:
            raise ValueError('Changed emitted movement call-save store')
    return dict(frontend_local_bytes=88, optimizer_local_bytes=76, rounded_locals=80, frame=128,
                caller_relative=homes, actual_buttons_home=-88, saved_budget=16, outgoing_budget=32,
                emitted_five_storage_sites_checked=True, late_growth=False)


def screens(root, out, group='basic'):
    rows = []
    for name, body in {'basic': forms, 'exits': exit_forms, 'buttons': button_forms, 'heading': heading_forms}[group]():
        try:
            _, _, row = measure(root, out, name, body)
        except ValueError as exc:
            if name != 'nonvoid-ABI-control' or not str(exc).startswith('Movement compiler diagnostics:'):
                raise
            row = dict(name=name, rejected_compiler_diagnostics=str(exc), installed=False, matching_credit=0)
        row = {k: v for k, v in row.items() if k != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / (group + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--reuse-trace', action='store_true')
    parser.add_argument('--group', choices=('basic', 'exits', 'buttons', 'heading'), default='basic')
    parser.add_argument('--form', choices=tuple(name for name, _ in all_forms()), default=SELECTED_NAME)
    parser.add_argument('--label')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.trace or args.reuse_trace:
        run = finish_trace if args.reuse_trace else trace
        record, words, binary = run(root, root / BUILD, args.label or args.form, dict(all_forms())[args.form])
        print(json.dumps(dict(form=args.form, normal_object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], binary_instructions=len(binary),
                              as1=record['assembler']), indent=2), flush=True)
    else:
        screens(root, root / BUILD, args.group)
