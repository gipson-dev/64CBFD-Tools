"""Fit the route setup's first-result lifetime without changing production."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.experiments import game_route_record_setup as source

BUILD = 'conker/build/game-route-record-capture'
OWNER, FUNCTION, ENTRY, ROM, WORDS = source.OWNER, source.FUNCTION, source.ENTRY, source.ROM, source.WORDS
INPUTS, BINDINGS = source.INPUTS, source.BINDINGS
installed, freeze, parse_object, function_span = source.installed, source.freeze, source.parse_object, source.function_span
RAW_SHA = '823565227dec4d2fc1f6875ea3c50c42cb476ff1fa8bc7e7766455c34f6decc0'


def forms():
    base = source.selected()
    old = ('            scratch.seed[1] = func_150888A8(scratch.seed[3], selected, 0);\n'
           '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);')
    captured = ('            after = (u8)func_150888A8(scratch.seed[3], selected, 0);\n'
                '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);\n'
                '            scratch.seed[1] = after;')
    gate = ('        if (selected != 0xFF && scratch.seed[0] != 0xFF && scratch.seed[1] != 0xFF) {\n'
            '            previous = scratch.seed[0];\n            after = scratch.seed[1];')
    if base.count(old) != 1 or base.count(gate) != 1:
        raise ValueError('Unknown route setup source sites')
    base = base.replace(old, captured)
    for label, body in (
        ('delayed', base),
        ('after-first-gate', base.replace(gate,
            '        if (selected != 0xFF &&\n'
            '            (after = scratch.seed[1], previous = scratch.seed[0], previous != 0xFF) && after != 0xFF) {')),
        ('previous-first-gate', base.replace(gate,
            '        if (selected != 0xFF &&\n'
            '            (previous = scratch.seed[0], after = scratch.seed[1], previous != 0xFF) && after != 0xFF) {')),
    ):
        yield label, body
        yield label + '-byte-after', body.replace('    s32 after;', '    u8 after;')
        yield label + '-early-after', body.replace('    u8 selected;', '    s32 after;\n    u8 selected;').replace(
            '    s32 previous;\n    s32 after;', '    s32 previous;')
        yield label + '-captured-both', body.replace(
            '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);\n'
            '            scratch.seed[1] = after;',
            '            previous = func_150888A8(selected, scratch.seed[3], 0);\n'
            '            scratch.seed[1] = after;\n            scratch.seed[0] = previous;')


def nested_forms():
    base = dict(forms())['after-first-gate-captured-both']
    yield 'after-first-condition', base.replace('previous != 0xFF) && after != 0xFF',
                                              'after != 0xFF) && previous != 0xFF')
    yield 'explicit-next-byte', base.replace('            i = after;', '            i = (u8)after;')
    for label, declaration, temporary in (
            ('separate-result', '    s32 firstResult;\n', 'firstResult'),
            ('reuse-candidate', '', 'candidate'),
            ('reuse-start', '', 'start'),
            ('reuse-index', '', 'i')):
        body = base.replace('    s32 limit;', declaration + '    s32 limit;').replace(
            '            after = (u8)func_150888A8(scratch.seed[3], selected, 0);',
            '            %s = (u8)func_150888A8(scratch.seed[3], selected, 0);' % temporary).replace(
            '            scratch.seed[1] = after;', '            scratch.seed[1] = %s;' % temporary)
        yield label, body
    original_gate = ('        if (selected != 0xFF && scratch.seed[0] != 0xFF && scratch.seed[1] != 0xFF) {\n'
                     '            previous = scratch.seed[0];\n            after = scratch.seed[1];')
    body = dict(forms())['delayed-captured-both'].replace(original_gate,
        '        if (selected != 0xFF && (previous = scratch.seed[0]) != 0xFF) {\n'
        '            after = scratch.seed[1];\n            if (after != 0xFF) {').replace(
        '            D_800D239A = 1;\n        }', '            D_800D239A = 1;\n            }\n        }')
    yield 'nested-after-gate', body
    yield 'nested-after-gate-byte-next', body.replace('            i = after;', '            i = (u8)after;')


def width_forms():
    base = dict(forms())['after-first-gate-captured-both']
    for label, old, new in (
        ('byte-previous', '    s32 previous;', '    u8 previous;'),
        ('unsigned-previous', '    s32 previous;', '    u32 previous;'),
        ('unsigned-after', '    s32 after;', '    u32 after;'),
        ('register-after', '    s32 after;', '    register s32 after;')):
        yield label, base.replace(old, new)
    yield 'cross-captured', base.replace(
        '            after = (u8)func_150888A8(scratch.seed[3], selected, 0);\n'
        '            previous = func_150888A8(selected, scratch.seed[3], 0);\n'
        '            scratch.seed[1] = after;\n            scratch.seed[0] = previous;',
        '            previous = (u8)func_150888A8(scratch.seed[3], selected, 0);\n'
        '            after = func_150888A8(selected, scratch.seed[3], 0);\n'
        '            scratch.seed[1] = previous;\n            scratch.seed[0] = after;')
    body = dict(forms())['delayed-captured-both'].replace(
        '            scratch.seed[0] = previous;\n        }',
        '            scratch.seed[0] = previous;\n'
        '            after = scratch.seed[1];\n            previous = scratch.seed[0];\n        }').replace(
        '        if (selected != 0xFF && scratch.seed[0] != 0xFF && scratch.seed[1] != 0xFF) {\n'
        '            previous = scratch.seed[0];\n            after = scratch.seed[1];',
        '        if (selected != 0xFF && previous != 0xFF && after != 0xFF) {')
    yield 'selected-only-reloads', body
    yield 'selected-only-byte-previous', body.replace('    s32 previous;', '    u8 previous;')


def reload_forms():
    base = dict(width_forms())['cross-captured']
    yield 'cross-explicit-limit', base.replace('limit = other[0xF];', 'limit = other[0xF] & 0xFF;')
    old = ('        if (selected != 0xFF &&\n'
           '            (after = scratch.seed[1], previous = scratch.seed[0], previous != 0xFF) && after != 0xFF) {')
    # A diagnostic retail-load view, not proof of portable indeterminate-byte reads.
    view = base.replace(old, '        after = scratch.seed[1];\n'
        '        previous = scratch.seed[0];\n'
        '        if (selected != 0xFF && previous != 0xFF && after != 0xFF) {')
    if view == base:
        raise ValueError('Unknown delayed-capture gate')
    yield 'unconditional-byte-view', view
    yield 'unconditional-byte-view-limit', view.replace('limit = other[0xF];', 'limit = other[0xF] & 0xFF;')
    yield 'unconditional-byte-view-limit-next', view.replace('limit = other[0xF];',
        'limit = other[0xF] & 0xFF;').replace('            i = after;', '            i = (u8)after;')


def byte_view_forms():
    base = dict(reload_forms())['unconditional-byte-view-limit']
    for mask in (1, 2, 3):
        body = base
        for bit, name in ((1, 'previous'), (2, 'after')):
            if mask & bit:
                body = body.replace('    s32 %s;' % name, '    u8 %s;' % name)
        yield 'byte-view-width-%d' % mask, body


def selected():
    body = dict(reload_forms())['cross-explicit-limit']
    body = body.replace('previous', 'neighbor0').replace('after', 'neighbor1')
    return body.replace('        if (selected != 0xFF) {',
        '        /* Reuse the call-result temporaries for the stored seed pair at the gate. */\n'
        '        if (selected != 0xFF) {', 1)


def checked(obj):
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    raw = text[function['value']:function['value'] + function['size']]
    bindings = {at - function['value']: entries for at, entries in relocations.items()
                if function['value'] <= at < function['value'] + function['size']}
    if len(raw) != 640 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown complete delayed-capture model or bindings')
    return raw, bindings


def qualify(root, out):
    values = freeze(root, out)
    baseline, diagnostics = installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    obj, words, row = source.measure(root, out, 'qualified', selected(), baseline)
    checked(obj)
    if diagnostics or row['diagnostics'] or (row['words'], row['frame'], row['differences']) != (160, 96, 39):
        raise ValueError('Changed delayed-capture qualification')
    row.update(installation_permitted=False, initial_S7_capture_and_two_delayed_stores=True,
               original_C_scratch_type_and_complete_private_order_not_claimed=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screen(root, out, candidates):
    values = source.freeze(root, out)
    baseline, diagnostics = source.installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected baseline diagnostics')
    for name, body in candidates:
        row = source.measure(root, out, name, body, baseline)[2]
        print(json.dumps({key: row[key] for key in
            ('name', 'words', 'frame', 'differences', 'raw_sha256', 'saved', 'diagnostics', 'neighbors')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nested', action='store_true')
    parser.add_argument('--widths', action='store_true')
    parser.add_argument('--reloads', action='store_true')
    parser.add_argument('--byte-views', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
        raise SystemExit(0)
    screen(root, root / BUILD, byte_view_forms() if args.byte_views else reload_forms() if args.reloads else width_forms() if args.widths else nested_forms() if args.nested else forms())
