"""Recover movement preload and smoothing lifetimes with complete source forms."""
# Preload the stdlib leaf before the historical recursive experiment imports.
import ctypes
import hashlib
import itertools
import json
from pathlib import Path

from tools.experiments import game_actor_input_movement_return as previous

source = previous.source
BUILD = 'conker/build/game-actor-input-movement-preload'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
for key, path, sha in (
    ('movement_preload_predecessor', 'tools/experiments/game_actor_input_movement_return.py',
     'ae370a878b76747ab7d6dd24ce2000f3b1aa7148d63fac9f7cffe1e2dee6b300'),
    ('movement_preload_predecessor_tests', 'tools/tests/test_game_actor_input_movement_return.py',
     '565ae6e757efb79daf29a287718f12f1f813d560c5cc04873f236e66a5906aab'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement preload predecessor')
    PATHS[key], BASELINE[key] = path, sha


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Changed movement preload predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement preload frozen input: ' + key)


replace = previous.previous.replace
DEFAULT_ANIMATION = '        actor->animation = 7;'
DEFAULT_STATE = '        actor->state = 0;'
TARGET_SPEED = '        actor->targetSpeed = initialMagnitude * D_800A1988;'
INITIALIZERS = (DEFAULT_ANIMATION, DEFAULT_STATE, TARGET_SPEED)


def animation_forms():
    body = previous.selected_body()
    before = '\n'.join(INITIALIZERS)
    for order in itertools.permutations(range(3)):
        yield 'initialize-' + ''.join(str(i) for i in order), replace(body, before, '\n'.join(INITIALIZERS[i] for i in order))


def initializer_body():
    return dict(animation_forms())['initialize-201']


def smoothing_forms(body=None):
    body = initializer_body() if body is None else body
    prefix = '        previousInput = actor->valueC4;\n'
    expression = ('        actor->valueC4 = previousInput + (((f32)D_800CC284->x - previousInput) *\n'
                  '                                  (D_800A1990 * D_800D1550));')
    yield 'selected', body
    compound = replace(body, expression,
        '        actor->valueC4 += (((f32)D_800CC284->x - previousInput) *\n'
        '                                  (D_800A1990 * D_800D1550));')
    yield 'compound-smoothing', compound
    for order in ('before', 'after'):
        stick = replace(body, '    u32 buttons;', '    u32 buttons;\n    f32 stickX;')
        assignment = '        stickX = (f32)D_800CC284->x;\n'
        stick = replace(stick, prefix, assignment + prefix if order == 'before' else prefix + assignment)
        stick = replace(stick, expression, expression.replace('(f32)D_800CC284->x', 'stickX'))
        yield 'stick-X-' + order, stick
    for name in ('smoothing', 'rate', 'value'):
        factor = body
        if name == 'smoothing':
            factor = replace(factor, '    u32 buttons;', '    u32 buttons;\n    f32 smoothing;')
        factor = replace(factor, prefix, '        ' + name + ' = D_800A1990 * D_800D1550;\n' + prefix)
        factor = replace(factor, expression, expression.replace('(D_800A1990 * D_800D1550)', name))
        yield 'factor-' + name, factor
    inline = replace(body, '    f32 previousInput;\n', '')
    inline = replace(inline, prefix + expression,
        '        actor->valueC4 += (((f32)D_800CC284->x - actor->valueC4) *\n'
        '                                  (D_800A1990 * D_800D1550));')
    yield 'inline-smoothing', inline


def flow_forms():
    body = dict(smoothing_forms())['stick-X-before']
    before = '                actor->mode = 1;\n                actor->held = D_800CC26D;'
    sampled = replace(body, before,
        '                heldIndex = D_800CC26D;\n'
        '                actor->mode = 1;\n'
        '                actor->held = heldIndex;')
    swapped = replace(body, before,
        '                actor->held = D_800CC26D;\n                actor->mode = 1;')
    yield 'held-before-mode', swapped
    yield 'sample-held', sampled
    for name, candidate in (('late-turn-step', body), ('sample-held-late-step', sampled),
                             ('held-before-mode-late-step', swapped)):
        candidate = replace(candidate, '        actor->turnStep = 25;\n', '')
        candidate = replace(candidate, '        actor->heading = heading;\n',
                            '        actor->heading = heading;\n        actor->turnStep = 25;\n')
        yield name, candidate
        reused = replace(candidate, '    f32 stickX;\n', '')
        if reused.count('stickX') != 2:
            raise ValueError('Changed movement stick sample lifetime')
        yield name + '-reuse-amount', reused.replace('stickX', 'amount')


def measure(root, out, name, body):
    freeze(root, out)
    return previous.measure(root, out, name, body)


def all_forms():
    yield from animation_forms()
    yield from smoothing_forms()
    yield from flow_forms()


SELECTED_NAME = 'held-before-mode-late-step-reuse-amount'
SELECTED_SHA = '5a5d99ac87599139e2c06f4adc5f415d2f8397c8760dddd747e4e06e5382e3a2'


def selected_body():
    return dict(flow_forms())[SELECTED_NAME]


def trace(root, out, name=SELECTED_NAME, body=None):
    freeze(root, out)
    return previous.trace(root, out, name, selected_body() if body is None else body)


def finish_trace(root, out, name=SELECTED_NAME, body=None):
    freeze(root, out)
    return previous.finish_trace(root, out, name, selected_body() if body is None else body)


def check_layout(record, words, content):
    layout = previous.check_layout(record, words, content)
    frame = previous.previous.frame
    summary = frame.summary(record, content, {'stickSample': 'amount = (f32)D_800CC284->x;'})
    stores = [r for r in summary['phases']['frontend']['markers']['stickSample']
              if r['name'] == 'str' and r['storage'] == 'M']
    if [(r['offset'], r['dtype'], r['length']) for r in stores] != [(-8, 'R', 4)]:
        raise ValueError('Changed movement stick sample existing amount home')
    return dict(layout, stick_sample_existing_amount_home=-8)


def screens(root, out, group, selected=None):
    rows = []
    factory = {'animation': animation_forms, 'smoothing': smoothing_forms, 'flow': flow_forms}[group]
    for name, body in factory():
        if selected is not None and selected != name:
            continue
        _, _, row = measure(root, out, name, body)
        row = {k: v for k, v in row.items() if k != 'bindings'}
        rows.append(row)
        print(json.dumps(row), flush=True)
    if not rows:
        raise ValueError('Movement source form does not belong to selected group')
    (out / ((selected or group) + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('animation', 'smoothing', 'flow'), default='animation')
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
