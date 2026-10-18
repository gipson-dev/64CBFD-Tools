"""Recover movement velocity and stick-sample lifetimes in complete C bodies."""
# Preload this stdlib leaf before the historical recursive experiment imports.
import ctypes
import hashlib
import json
from pathlib import Path

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_preload as previous

BUILD = 'conker/build/game-actor-input-movement-float-lifetimes'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_float_predecessor', 'tools/experiments/game_actor_input_movement_preload.py',
     '74370b23ab50ba306096ac38f5216314ce0a8784da72b1371229d2657bdf1a94'),
    ('movement_float_predecessor_tests', 'tools/tests/test_game_actor_input_movement_preload.py',
     '593191e7fa722b5e1b8e1813bfc9beac2fad0baff7d41e8076aea484ba2e7333'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement float predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement float predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement float frozen input: ' + key)


replace = previous.replace
CAP = ('        if (D_800A198C < actor->positionY) {\n'
       '            value = actor->verticalVelocity;\n'
       '            if (value > -30.0f) {\n'
       '                actor->verticalVelocity = value - 1.5f;\n'
       '            }\n'
       '            input = 40.0f;\n'
       '        }')


def velocity_forms():
    body = previous.selected_body()
    yield 'previous', body
    for name in ('velocity', 'magnitude', 'previousInput', 'pitchValue', 'amount'):
        yield 'cap-' + name, replace(body, CAP, CAP.replace('value', name))
    inline = ('        if (D_800A198C < actor->positionY) {\n'
              '            if (actor->verticalVelocity > -30.0f) {\n'
              '                actor->verticalVelocity -= 1.5f;\n'
              '            }\n'
              '            input = 40.0f;\n'
              '        }')
    yield 'cap-inline', replace(body, CAP, inline)
    yield 'cap-constant-first', replace(body, CAP, CAP.replace('value > -30.0f', '-30.0f < value'))


def expression_forms():
    for name in ('velocity', 'pitchValue'):
        body = dict(velocity_forms())['cap-' + name]
        before = '            ' + name + ' = actor->verticalVelocity;\n            if (' + name + ' > -30.0f) {'
        for order in ('left', 'right'):
            condition = ('-30.0f < (' + name + ' = actor->verticalVelocity)' if order == 'left' else
                         '(' + name + ' = actor->verticalVelocity) > -30.0f')
            yield 'cap-expression-' + name + '-' + order, replace(body, before, '            if (' + condition + ') {')
    body = dict(velocity_forms())['cap-velocity']
    sample = '        amount = (f32)D_800CC284->x;\n'
    inline = replace(body, sample, '')
    inline = replace(inline, '((amount - previousInput) *', '(((f32)D_800CC284->x - previousInput) *')
    yield 'velocity-inline-X', inline
    for name in ('rate', 'magnitude', 'pitchValue'):
        candidate = replace(body, sample, sample.replace('amount', name))
        yield 'velocity-X-' + name, replace(candidate, '((amount - previousInput) *', '((' + name + ' - previousInput) *')
    difference = replace(body, sample, '')
    before = ('        previousInput = actor->valueC4;\n'
              '        actor->valueC4 = previousInput + ((amount - previousInput) *\n')
    after = ('        previousInput = actor->valueC4;\n'
             '        amount = (f32)D_800CC284->x - previousInput;\n'
             '        actor->valueC4 = previousInput + (amount *\n')
    yield 'velocity-X-difference', replace(difference, before, after)


def cap_body():
    return dict(expression_forms())['cap-expression-velocity-left']


def smoothed_body():
    body = replace(cap_body(), '        amount = (f32)D_800CC284->x;',
                   '        magnitude = (f32)D_800CC284->x;')
    return replace(body, '((amount - previousInput) *', '((magnitude - previousInput) *')


def heading_forms():
    body = smoothed_body()
    yield 'cap-and-X-magnitude', body
    assignment = ('        heading = (u32)actor->heading - (u32)(s32)(actor->valueC4 * D_800D1550 *\n'
                  '                  D_800A1994 * ((100.0f - speed) * D_800A1998) * 220.0f);\n'
                  '        actor->heading = heading;')
    callback = '        func_150599C8(actor, 8, (u16)heading);'
    for name, expression in (
        ('field-heading', assignment.replace('heading = (u32)actor->heading -', 'actor->heading = (u32)actor->heading -')
         .replace('\n        actor->heading = heading;', '')),
        ('field-compound-heading', assignment.replace('heading = (u32)actor->heading -', 'actor->heading -=')
         .replace('\n        actor->heading = heading;', '')),
    ):
        field = replace(body, '    u32 heading;\n', '')
        field = replace(field, assignment, expression)
        yield name, replace(field, callback, '        func_150599C8(actor, 8, actor->heading);')
    for name, marker in (('early-heading', '        magnitude = (f32)D_800CC284->x;\n'),
                         ('snapshot-heading', '        previousInput = actor->valueC4;\n')):
        cached = replace(body, marker, '        heading = actor->heading;\n' + marker)
        yield name, replace(cached, assignment, assignment.replace('heading = (u32)actor->heading -', 'heading -='))
    compound = replace(body, 'actor->valueC4 = previousInput + ((magnitude - previousInput) *',
                       'actor->valueC4 += ((magnitude - previousInput) *')
    yield 'compound-smoothed-X', compound


def compound_smoothing(body):
    return replace(body, 'actor->valueC4 = previousInput + ((magnitude - previousInput) *',
                   'actor->valueC4 += ((magnitude - previousInput) *')


def delta_forms():
    body = dict(heading_forms())['field-heading']
    yield 'field-heading-compound-X', compound_smoothing(body)
    before = ('        actor->heading = (u32)actor->heading - (u32)(s32)(actor->valueC4 * D_800D1550 *\n'
              '                  D_800A1994 * ((100.0f - speed) * D_800A1998) * 220.0f);')
    for name in ('turnDelta', 'index'):
        candidate = body
        if name == 'turnDelta':
            candidate = replace(candidate, '    s32 heldIndex;', '    s32 turnDelta;\n    s32 heldIndex;')
        after = ('        ' + name + ' = (s32)(actor->valueC4 * D_800D1550 *\n'
                 '                  D_800A1994 * ((100.0f - speed) * D_800A1998) * 220.0f);\n'
                 '        actor->heading = (u32)actor->heading - (u32)' + name + ';')
        candidate = replace(candidate, before, after)
        yield 'delta-' + name, candidate
        yield 'delta-' + name + '-compound-X', compound_smoothing(candidate)


def all_forms():
    yield from velocity_forms()
    yield from expression_forms()
    yield from heading_forms()
    yield from delta_forms()


def measure(root, out, name, body):
    freeze(root, out)
    return previous.measure(root, out, name, body)


SELECTED_NAME = 'field-heading-compound-X'
SELECTED_SHA = '5fab097557f1f8a7b65ea3be5ac6fb7f0adb0d5547e8ef0392d7dd538a3710dd'


def selected_body():
    return dict(all_forms())[SELECTED_NAME]


def trace(root, out, name=SELECTED_NAME, body=None):
    freeze(root, out)
    return previous.trace(root, out, name, selected_body() if body is None else body)


def finish_trace(root, out, name=SELECTED_NAME, body=None):
    freeze(root, out)
    return previous.finish_trace(root, out, name, selected_body() if body is None else body)


frame = previous.previous.previous.frame
MARKERS = dict(frame.MARKERS,
    distanceCall='nearestDistance = func_1505A6F8(D_800D154C, record);',
    turn='func_150599C8(actor, 8, actor->heading);',
    cap='if (-30.0f < (velocity = actor->verticalVelocity)) {',
    stickSample='magnitude = (f32)D_800CC284->x;',
    previousInput='previousInput = actor->valueC4;')
HOMES = dict(contact=-40, speed=-24, input=-20, angle=-2, distance=-56,
             index=-48, record=-76, distanceCall=-52, cap=-32, stickSample=-16, previousInput=-60)


def check_layout(record, words, content):
    if record.get('code_unchanged') is not True or record.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement float layout')
    summary = frame.summary(record, content, MARKERS)
    phases = summary['phases']
    sizes = [[r['length'] for r in phases[p]['definitions'] if r['storage'] == 'M']
             for p in ('frontend', 'optimizer')]
    for name, offset in HOMES.items():
        stores = [r for r in phases['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M']
        kind, size = ('L', 2) if name == 'angle' else ('J', 4) if name == 'index' else ('A', 4) if name == 'record' else ('R', 4)
        if len(stores) != 1 or (stores[0]['offset'], stores[0]['dtype'], stores[0]['length']) != (offset, kind, size):
            raise ValueError('Changed movement float live home: ' + name)
    lines = [i + 1 for i, line in enumerate(content.splitlines()) if line.strip() == 'buttons = D_800CC284->buttons;']
    if len(lines) != 2:
        raise ValueError('Changed movement float buttons source markers')
    current, buttons = None, []
    for row in frame.procedure_records(record['records']['frontend'], summary['procedure']):
        if row['name'] == 'loc':
            current = row['words'][1]
        if current == lines[0] and row['name'] == 'str' and row['storage'] == 'M':
            buttons.append(row)
    events = record['events']
    if (sizes != [[84], [76]] or len(buttons) != 1
            or (buttons[0]['offset'], buttons[0]['dtype'], buttons[0]['length']) != (-84, 'L', 4)
            or [e['event'] for e in events] != ['frame-watch-installed', 'frame-write', 'frame-write', 'frame-write']
            or [e['frame'] for e in events] != [0, 16, 48, 128]
            or [e['host_pc'] for e in events] != [4268224, 4566873, 4523375, 4523375]
            or [(e['saved'], e['outgoing'], e['locals']) for e in events] != [(0, 0, 0), (16, 0, 0), (16, 32, 0), (16, 32, 80)]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)
            or (words[0], words[1], words[4], words[5]) != (0x27BDFF80, 0xAFB00028, 0xAFBF002C, 0xE7B00058)):
        raise ValueError('Changed movement float frame or buttons home')
    angle = words.index(0x0D41698C)
    magnitude = words.index(0x0D416973)
    if sum(w >> 26 == 41 and w >> 21 & 31 == 29 and w & 65535 == 0x7E
           for w in words[angle + 1:magnitude + 2]) != 1:
        raise ValueError('Changed movement float angle store')
    call = words.index(0x0D4169BE)
    for op, offset in ((43, 0x50), (43, 0x34), (57, 0x48)):
        if sum(w >> 26 == op and w >> 21 & 31 == 29 and w & 65535 == offset
               for w in words[call - 5:call + 2]) != 1:
            raise ValueError('Changed movement float call-save store')
    return dict(frontend_local_bytes=84, optimizer_local_bytes=76, rounded_locals=80, frame=128,
                caller_relative=HOMES, actual_buttons_home=-84, saved_budget=16, outgoing_budget=32,
                emitted_five_storage_sites_checked=True, late_growth=False)


def screens(root, out, group='velocity', selected=None):
    rows = []
    factory = {'velocity': velocity_forms, 'expression': expression_forms, 'heading': heading_forms,
               'delta': delta_forms}[group]
    for name, body in factory():
        if selected is not None and name != selected:
            continue
        _, _, row = measure(root, out, name, body)
        row = {k: v for k, v in row.items() if k != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    if not rows:
        raise ValueError('Unknown movement float form in group')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('velocity', 'expression', 'heading', 'delta'), default='velocity')
    parser.add_argument('--form', choices=tuple(name for name, _ in all_forms()))
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--reuse-trace', action='store_true')
    parser.add_argument('--label')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.trace or args.reuse_trace:
        run = finish_trace if args.reuse_trace else trace
        form = args.form or SELECTED_NAME
        record, words, binary = run(root, root / BUILD, args.label or form, dict(all_forms())[form])
        print(json.dumps(dict(form=form, words=len(words), normal_object_identical=record['code_unchanged'],
                              emitter_events=record['correlated_events'], binary_instructions=len(binary)), indent=2))
    else:
        screens(root, root / BUILD, args.group, args.form)
