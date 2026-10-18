"""Source-level scalar lifetime screens following the observed route-update frame."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_actor_update as source

BUILD = 'conker/build/game-route-actor-update-fit'
SELECTED_NAME = 'start-gain-offset-bound-10'
RAW_SHA = '2cf5b5c91a70d570c609fb89d9d6da3516bb690cdf46cdfc6eeb519694ef4902'
BINDING_SHA = 'd58b6498d00706402c7b74606be29f8fe973b12a6caf1c5b13bfbb4338b98297'


def replace_once(body, old, new):
    if body.count(old) != 1:
        raise ValueError('Unknown route-update scope marker: ' + old)
    return body.replace(old, new)


def registered(body, names):
    for name in names:
        pattern = r'(?m)^    ((?:f32|s32|u32|s8|u8 \*) ?' + name + r';)$'
        body, n = re.subn(pattern, r'    register \1', body)
        if n != 1:
            raise ValueError('Unknown address-free route scalar: ' + name)
    return body


def scoped(body, split_step=True):
    for name in ('valueX', 'valueZ', 'inverse', 'angle', 'temporaryScore'):
        body = replace_once(body, '    f32 ' + name + ';\n', '')
    body = replace_once(body, '    do {\n        again = 0;',
        '    do {\n        f32 valueX;\n        f32 valueZ;\n        f32 inverse;\n        again = 0;')
    body = replace_once(body, '    } else {\n        *(f32 *)record = 0.0f;',
        '    } else {\n        f32 valueX;\n        f32 valueZ;\n        f32 inverse;\n        *(f32 *)record = 0.0f;')
    body = replace_once(body, '            if (active == 0) {\n',
        '            if (active == 0) {\n                f32 angle;\n')
    body = replace_once(body, '                if (scores[i] < scores[i + 1]) {\n',
        '                if (scores[i] < scores[i + 1]) {\n                    f32 temporaryScore;\n')
    if split_step:
        body = replace_once(body, '    f32 step;\n', '')
        body = replace_once(body, '    } else {\n        step =', '    } else {\n        f32 step;\n        step =')
        body = replace_once(body, '        if (error < -50.0f || 50.0f < error) {\n',
            '        if (error < -50.0f || 50.0f < error) {\n            f32 step;\n')
    return body


def forms():
    temps = ('step', 'valueX', 'valueZ', 'inverse', 'gain', 'angle', 'temporaryScore')
    late = ('recordOffset', 'iterations', 'again', 'i', 'last', 'sorted', 'temporary', 'record', 'cursor', *temps)
    for label, body in list(source.forms())[:3]:
        names = tuple(n for n in temps if re.search(r'(?m)^    f32 ' + n + r';$', body))
        yield label + '-register-float-temps', registered(body, names)
        names = tuple(n for n in late if re.search(r'(?m)^    (?:f32|s32|u32|s8|u8 \*) ?' + n + r';$', body))
        yield label + '-register-late-scalars', registered(body, names)
    yield 'block-values', scoped(source.SELECTED, False)
    yield 'block-values-step', scoped(source.SELECTED, True)
    yield 'block-values-registered-gain', registered(scoped(source.SELECTED, True), ('gain',))


def merge_names(body, pairs):
    for old, new in pairs:
        body, n = re.subn(r'(?m)^    (?:f32|s32|u8 \*|s8) ?' + old + r';\n', '', body)
        if n != 1:
            raise ValueError('Unknown disjoint route carrier: ' + old)
        body = re.sub(r'\b' + old + r'\b', new, body)
    return body


def role_forms(body=source.SELECTED):
    first = merge_names(body, (('step', 'valueX'), ('angle', 'valueX'),
        ('temporaryScore', 'valueX'), ('inverse', 'absoluteError')))
    second = merge_names(first, (('valueZ', 'error'),))
    third = merge_names(body, (('step', 'absoluteError'), ('inverse', 'absoluteError'),
        ('angle', 'absoluteError'), ('temporaryScore', 'absoluteError'),
        ('valueX', 'intercept'), ('valueZ', 'error')))
    for label, body in (('loop-value-and-absolute', first), ('loop-value-error-reuse', second),
                         ('three-phase-float-roles', third)):
        yield label, body
        for old, new in (('sorted', 'again'), ('temporary', 'refresh'), ('cursor', 'actor')):
            body = merge_names(body, ((old, new),))
        marker = '    if (recordOffset == 0) {\n'
        head, tail = body.split(marker)
        head = replace_once(head, '    s32 i;\n', '')
        tail = re.sub(r'\bi\b', 'recordIndex', tail)
        yield label + '-late-role-reuse', head + marker + tail


def local_forms():
    base = dict(role_forms())['loop-value-error-reuse']
    for label, body in (('loop-value', base), ('loop-value-start-gain', merge_names(base, (('startZ', 'gain'),)))):
        for flag, byte, bound in ((1, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)):
            value = body
            if flag:
                value = merge_names(value, (('sorted', 'again'),))
            if byte:
                value = merge_names(value, (('temporary', 'refresh'),))
            if bound:
                value = merge_names(value, (('last', 'active'),))
            yield '%s-late-%d%d%d' % (label, flag, byte, bound), value


def selected():
    return dict(bound_forms())[SELECTED_NAME]


def bound_forms():
    a = dict(local_forms())['loop-value-start-gain-late-100']
    b = merge_names(dict(role_forms())['loop-value-error-reuse'],
        (('startZ', 'previousError'), ('sorted', 'again')))
    for label, base in (('start-gain', a), ('start-prior', b)):
        for bound, counter in ((1, 0), (0, 1), (1, 1)):
            body = base
            if bound:
                body = replace_once(body, '    s32 last;\n', '')
                body = replace_once(body, '        last = D_800D2398 - 1;',
                    '        recordOffset = (u32)(D_800D2398 - 1);')
                body = replace_once(body, 'i < last;', 'i < (s32)recordOffset;')
            if counter:
                body = replace_once(body, '    s32 i;\n', '')
                marker = '    if (recordOffset == 0) {\n'
                head, tail = body.split(marker)
                tail = re.sub(r'\bi\b', 'iterations', tail)
                body = head + marker + tail
            yield '%s-offset-bound-%d%d' % (label, bound, counter), body


def checked(obj):
    text, functions, relocations = source.parse_object(obj)
    f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']: value for at, value in relocations.items()
                if f['value'] <= at < f['value'] + f['size']}
    check_payload(raw, bindings)
    return raw, bindings


def check_payload(raw, bindings):
    binding_sha = hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if len(raw) != 2356 or hashlib.sha256(raw).hexdigest() != RAW_SHA or binding_sha != BINDING_SHA:
        raise ValueError('Changed complete frame456 route-update point or bindings')


def qualify(root, out):
    values = source.freeze(root, out)
    baseline, diagnostics = source.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected frame-fit baseline diagnostics')
    obj, words, row = source.measure(root, out, 'qualified-bound', selected(), baseline)
    checked(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (589, 456, 481, ''):
        raise ValueError('Changed frame456 qualification shape')
    row.update(frame_restored=True, matching_credit=0, installed=False,
        extent_restored=False, saved_register_layout_restored=True)
    (out / 'qualified-bound.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screen(root, out, roles=False, locals_only=False, bounds=False):
    values = source.freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    baseline, diagnostics = source.prior.compile_profile(root, out, before, 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected route fit baseline diagnostics')
    rows = []
    for label, body in bound_forms() if bounds else local_forms() if locals_only else role_forms() if roles else forms():
        row = source.measure(root, out, label, body, baseline)[2]
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'raw_sha256', 'diagnostics', 'neighbors')}), flush=True)
    receipt = 'bound-screens.json' if bounds else 'local-screens.json' if locals_only else 'role-screens.json' if roles else 'screens.json'
    (out / receipt).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roles', action='store_true')
    parser.add_argument('--locals', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--bounds', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
    else:
        screen(root, root / BUILD, args.roles, args.locals, args.bounds)
