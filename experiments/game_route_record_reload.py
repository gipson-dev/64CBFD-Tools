"""Recover seed reload order and later route setup saved roles, without installation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_route_record_capture as source
from tools.experiments import game_text_measurer_frontend_trace as frontend
from tools.experiments.game_actor_record_gate_compiler_trace import lifecycle
from tools.experiments.game_remaining_donor_candidates import sections

BUILD = 'conker/build/game-route-record-reload'
OWNER, FUNCTION, ENTRY, ROM, WORDS = source.OWNER, source.FUNCTION, source.ENTRY, source.ROM, source.WORDS
INPUTS, BINDINGS = source.INPUTS, source.BINDINGS
installed, freeze, parse_object, function_span = source.installed, source.freeze, source.parse_object, source.function_span
recovered_owner, measure = source.source.recovered_owner, source.source.measure
RAW_SHA = 'bdfe29694f9756fa66c4a4be439376e2b1a81129d69ed74954f8cfbef31b5442'
GATE = ('        if (selected != 0xFF &&\n'
        '            (neighbor1 = scratch.seed[1], neighbor0 = scratch.seed[0], neighbor0 != 0xFF) && neighbor1 != 0xFF) {')


def forms():
    base = source.selected()
    if base.count(GATE) != 1 or base.count('            i = neighbor1;') != 1:
        raise ValueError('Unknown complete delayed-capture source')
    explicit = base.replace('            i = neighbor1;\n', '')
    yield 'comma-next-before-last-gate', explicit.replace(GATE,
        '        if (selected != 0xFF &&\n'
        '            (neighbor1 = scratch.seed[1], neighbor0 = scratch.seed[0], neighbor0 != 0xFF) &&\n'
        '            (i = (u8)neighbor1, neighbor1 != 0xFF)) {')
    yield 'late-after-reload', explicit.replace(GATE,
        '        if (selected != 0xFF && (neighbor0 = scratch.seed[0]) != 0xFF &&\n'
        '            (i = (u8)(neighbor1 = scratch.seed[1]), neighbor1 != 0xFF)) {')
    nested = explicit.replace(GATE,
        '        if (selected != 0xFF && (neighbor0 = scratch.seed[0]) != 0xFF) {\n'
        '            i = (u8)(neighbor1 = scratch.seed[1]);\n'
        '            if (neighbor1 != 0xFF) {').replace(
        '            D_800D239A = 1;\n        }', '            D_800D239A = 1;\n            }\n        }')
    yield 'nested-next-before-last-gate', nested
    yield 'explicit-failure-returns', explicit.replace(GATE,
        '        if (selected == 0xFF) return;\n'
        '        neighbor1 = scratch.seed[1];\n'
        '        neighbor0 = scratch.seed[0];\n'
        '        if (neighbor0 == 0xFF) return;\n'
        '        i = (u8)neighbor1;\n'
        '        if (neighbor1 == 0xFF) return;\n        {')


def field_forms():
    marker = '        if (selected != 0xFF &&\n'
    base = selected()
    if base.count(marker) != 1:
        raise ValueError('Unknown route setup validity scope')
    head, tail = base.split(marker)
    for mask in (1, 2, 3):
        body = marker + tail
        for bit, name, field in ((1, 'neighbor1', 1), (2, 'neighbor0', 0)):
            if mask & bit:
                body = body.replace('%s = scratch.seed[%d], ' % (name, field), '')
                body = re.sub(r'\b%s\b' % name, 'scratch.seed[%d]' % field, body)
        yield 'direct-seed-fields-%d' % mask, head + body


def screen(root, out, candidates):
    values = source.freeze(root, out)
    baseline, diagnostics = source.installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected baseline diagnostics')
    for name, body in candidates:
        row = source.source.measure(root, out, name, body, baseline)[2]
        print(json.dumps({key: row[key] for key in
            ('name', 'words', 'frame', 'differences', 'raw_sha256', 'saved', 'diagnostics', 'neighbors')}), flush=True)


def selected():
    return dict(forms())['comma-next-before-last-gate']


def checked(obj):
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    raw = text[function['value']:function['value'] + function['size']]
    bindings = {at - function['value']: entries for at, entries in relocations.items()
                if function['value'] <= at < function['value'] + function['size']}
    if len(raw) != 640 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown complete next-index gate model or bindings')
    return raw, bindings


def qualify(root, out):
    values = freeze(root, out)
    baseline, diagnostics = installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    obj, words, row = measure(root, out, 'qualified', selected(), baseline)
    checked(obj)
    if diagnostics or row['diagnostics'] or (row['words'], row['frame'], row['differences']) != (160, 96, 37):
        raise ValueError('Changed next-index gate qualification')
    row.update(installation_permitted=False, initial_nine_word_capture_preserved=True,
               raw_private_order_and_later_saved_roles_equal=False)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def isolated_content(root, out):
    owner = source.freeze(root, out)['conker/src/game/generated_B3020.c'].decode()
    first = source.function_span(owner, 'func_15085B70')[0]
    return owner[:first] + 's32 func_15086D48(s32);\n' + selected()


def wire(root):
    out = root / BUILD
    content = isolated_content(root, out)

    def compile_baseline(root, work, label, actual):
        if actual != content:
            raise ValueError('Changed isolated route reload source')
        obj, diagnostics = source.installed.prior.compile_profile(root, work, actual, label)
        checked(obj)
        if diagnostics or set(source.parse_object(obj)[1]) != {source.FUNCTION}:
            raise ValueError('Unexpected isolated reload diagnostics or function scope')
        return dict(function=source.FUNCTION, raw_sha256=RAW_SHA, words=160, diagnostics=diagnostics), None

    adapter = SimpleNamespace(compile_candidate=compile_baseline,
        PROFILES={'owner': ('-O2', '-g3', '-Wo,-loopunroll,0')},
        compiler=SimpleNamespace(parse_object=source.parse_object, sections=sections))
    with patch.object(frontend.trace, 'screen', adapter):
        complete = frontend.capture_frontend(root, out, 'selected-wire', content)
    work = out / 'selected-wire'
    ended = lifecycle(root.resolve(), (work / 'debugger.txt').read_text())
    if not complete['code_unchanged']:
        raise ValueError('Route reload wire capture changed normal code')
    raw, _ = checked(work / 'trace.o')
    rows = {label: [r for r in complete[key] if r['storage'] == 'M' and r['offset'] in (-23, -24)]
            for label, key in (('frontend', 'records'), ('optimizer', 'optimizer_records'))}
    result = dict(complete=complete, lifecycle=ended, raw_sha256=RAW_SHA,
                  facts=wire_facts(complete, raw),
                  stack_seed_records=rows, production_unchanged=True, installable=False)
    source.freeze(root, out)
    (work / 'route-wire.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def wire_facts(complete, raw):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA or complete.get('code_unchanged') is not True:
        raise ValueError('Unknown normal route-reload wire model')
    records = complete['optimizer_records']
    entries = [r for r in records if r['name'] == 'ent']
    if len(entries) != 1 or entries[0]['block'] != 768:
        raise ValueError('Unknown isolated reload procedure')
    reads = [(i, r) for i, r in enumerate(records)
             if r['name'] == 'lod' and r['storage'] == 'M' and r['offset'] in (-23, -24)]
    if len(reads) != 2 or [r['offset'] for _, r in reads] != [-23, -24]:
        raise ValueError('Changed optimized seed read identities/order')
    a, b = [i for i, _ in reads]
    signature = lambda r: (r['name'], r['dtype'], r['storage'], r['block'], r['length'], r['offset'])
    expected = [('lod', 'L', 'M', 768, 1, -23), ('str', 'J', 'R', 0, 4, 2),
                ('lod', 'J', 'R', 0, 4, 2), ('str', 'J', 'R', 0, 4, 30),
                ('lod', 'L', 'M', 768, 1, -24), ('str', 'J', 'R', 0, 4, 23)]
    if b != a + 5 or [signature(records[i]) for i in (a, a + 2, a + 3, a + 4, b, b + 2)] != expected:
        raise ValueError('Changed optimized after-copy/before allocation')
    if any(records[i]['name'] != 'cvt' or records[i]['dtype'] != 'J'
           or records[i]['words'][2] != 0x08000001 for i in (a + 1, b + 1)):
        raise ValueError('Changed byte-to-word seed conversions')
    words = struct.unpack('>160I', raw)
    if (words[71], words[72], words[74]) != (0x93B70048, 0x93A20049, 0x0040F025):
        raise ValueError('Changed emitted seed reads or after-value copy')
    return dict(procedure=768, optimized_seed_offsets=[-23, -24],
        optimized_after_temporary_GPR=2, optimized_after_saved_GPR=30, optimized_before_saved_GPR=23,
        emitted_seed_offsets=[0x48, 0x49], emitted_after_copy_to_FP=True,
        load_reorder_after_optimized_wire=True, frontend_indirect_field_order_not_inferred=True,
        original_retail_allocator_or_source_types_not_observed=True)


def audit_wire(root):
    out = root / BUILD
    work = out / 'selected-wire'
    old = json.loads((work / 'route-wire.json').read_text())
    child = old['complete']['complete']
    content = isolated_content(root, out)
    if (work / 'baseline.c').read_text() != content or hashlib.sha256(content.encode()).hexdigest() != child['source_sha256']:
        raise ValueError('Changed completed wire source')
    with patch.object(frontend.trace, 'screen', SimpleNamespace(
            compiler=SimpleNamespace(parse_object=parse_object, sections=sections))):
        complete = frontend.validate_capture(root, work, (work / 'debugger.txt').read_text(), child)
    raw, _ = checked(work / 'trace.o')
    ended = lifecycle(root.resolve(), (work / 'debugger.txt').read_text())
    facts = wire_facts(complete, raw)
    result = dict(facts=facts, lifecycle=ended, reused_completed_capture=True,
                  code_unchanged=True, production_unchanged=True, installable=False)
    (work / 'wire-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wire', action='store_true')
    parser.add_argument('--fields', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--audit-wire', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.audit_wire:
        print(json.dumps(audit_wire(root), indent=2))
        raise SystemExit(0)
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
        raise SystemExit(0)
    if args.wire:
        result = wire(root)
        print(json.dumps({k: v for k, v in result.items() if k != 'complete'}, indent=2))
        raise SystemExit(0)
    screen(root, root / BUILD, field_forms() if args.fields else forms())
