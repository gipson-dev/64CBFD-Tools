"""Fit route-vector invariant roles without changing the ordered memory contract."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_vector_builder as model
from tools.experiments import game_route_spline_payload_integration as installed
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-route-vector-saved-role-fit'
INPUTS = dict(installed.INPUTS, **installed.AFTER)
RAW_SHA = '8824f4396809c366367e8bd116bd8426e5615a55ae3449643c83a7d0cdbe3710'
BINDINGS = {12: [('R_MIPS_HI16', 'D_800D2350')], 40: [('R_MIPS_LO16', 'D_800D2350')]}


def freeze(root, out):
    with patch.object(checkpoint, 'INPUTS', INPUTS):
        return checkpoint.freeze(root, out)


def forms():
    sources = dict(model.forms())
    selected = 'other = table + candidate * 0x10;'
    expressions = {
        'half-left': '(u8 *)((s16 *)table + candidate * 8)',
        'half-right': '(u8 *)(candidate * 8 + (s16 *)table)',
        'float-left': '(u8 *)((f32 *)table + candidate * 4)',
        'word-right': '(u8 *)(candidate * 0x10 + (u32)table)',
        'signed-right': '(u8 *)((s32)candidate * 0x10 + (s32)table)',
        'byte-offset': '(u8 *)table + (candidate << 4)',
    }
    for family in ('local-outputs-assigned', 'local-outputs-assigned-byte-ids'):
        base = sources[family]
        for label, expression in expressions.items():
            body = base.replace(selected, 'other = ' + expression + ';')
            if body == base:
                raise ValueError('Selected-pointer substitution did not fire')
            yield family + '-' + label, body
    base = sources['local-outputs-assigned-byte-ids']
    for label, expression in expressions.items():
        body = base.replace(selected, 'other = ' + expression + ';')
        body = body.replace('    s16 currentX;', '    f32 baseX;\n    s16 currentX;').replace(
            '            deltaX = (f32)(nextX - currentX);',
            '            baseX = (f32)currentX;\n            deltaX = (f32)(nextX - currentX);').replace(
            '*x = (f32)currentX + deltaX * speed;', '*x = baseX + deltaX * speed;')
        yield 'early-conversion-' + label, body


def conversion_forms():
    base = dict(model.forms())['local-outputs-assigned'].replace(
        'other = table + candidate * 0x10;', 'other = (u8 *)((s16 *)table + candidate * 8);')
    for narrow in range(4):
        body = base
        for bit, name in ((1, 'currentX'), (2, 'nextX')):
            if narrow & bit:
                body = body.replace('    s32 ' + name + ';', '    s16 ' + name + ';')
        for order in ('after-speed', 'before-speed', 'before-next'):
            result = body.replace('    f32 speed;', '    f32 baseX;\n    f32 speed;')
            where = {'after-speed': '            deltaX =',
                     'before-speed': '            speed =',
                     'before-next': '            nextX ='}[order]
            result = result.replace(where, '            baseX = (f32)currentX;\n' + where, 1).replace(
                '*x = (f32)currentX + deltaX * speed;', '*x = baseX + deltaX * speed;')
            yield 'conversion-%d-%s' % (narrow, order), result


def arithmetic_forms():
    base = dict(forms())['local-outputs-assigned-half-left']
    for early_delta in (False, True):
        body = base
        if early_delta:
            body = body.replace('            speed = *(f32 *)record;\n            deltaX = (f32)(nextX - currentX);',
                                '            deltaX = (f32)(nextX - currentX);\n            speed = *(f32 *)record;')
        for order in ('plain', 'base-first', 'product-speed', 'product-delta'):
            result = body
            if order == 'base-first':
                result = result.replace('    f32 speed;', '    f32 baseX;\n    f32 speed;').replace(
                    '            nextX =', '            baseX = (f32)currentX;\n            nextX =', 1).replace(
                    '*x = (f32)currentX + deltaX * speed;', '*x = baseX + deltaX * speed;')
            elif order == 'product-speed':
                result = result.replace('            *x = (f32)currentX + deltaX * speed;',
                    '            speed = deltaX * speed;\n            *x = (f32)currentX + speed;')
            elif order == 'product-delta':
                result = result.replace('            *x = (f32)currentX + deltaX * speed;',
                    '            deltaX *= speed;\n            *x = (f32)currentX + deltaX;')
            yield 'arithmetic-%d-%s' % (early_delta, order), result


def measure(root, out, name, body, baseline=None):
    values = freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    obj, diagnostics = model.compile_owner(root, out, model.recovered_owner(before, body), name)
    data, functions = model.link_owner(root, out, obj, model.OWNER)
    function = functions[model.FUNCTION]
    words = list(struct.unpack_from('>%dI' % (function['size'] // 4), data, function['value']))
    text, definitions, relocations = model.parse_object(obj)
    definition = definitions[model.FUNCTION]
    raw = text[definition['value']:definition['value'] + definition['size']]
    bindings = {at - definition['value']: value for at, value in relocations.items()
                if definition['value'] <= at < definition['value'] + definition['size']}
    truth = struct.unpack_from('>83I', values['conker/conker.us.bin'], model.ROM)
    row = dict(name=name, words=len(words), frame=(-words[0]) & 65535,
               differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - 83),
               raw_sha256=hashlib.sha256(raw).hexdigest(), bindings=bindings,
               saved=[(w >> 16 & 31, w & 65535) for w in words if w >> 26 == 43 and w >> 21 & 31 == 29],
               diagnostics=diagnostics, production_installed=False)
    if baseline is not None:
        row['neighbors'] = model.same_functions(baseline, obj, (model.FUNCTION,))
        if row['neighbors'] != 72 or normalized_pools(baseline) != normalized_pools(obj):
            raise ValueError('Candidate changed another owner function or literal pool')
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def selected():
    return dict(arithmetic_forms())['arithmetic-0-product-speed']


def checked(obj):
    text, functions, relocations = model.parse_object(obj)
    function = functions[model.FUNCTION]
    raw = text[function['value']:function['value'] + function['size']]
    bindings = {at - function['value']: value for at, value in relocations.items()
                if function['value'] <= at < function['value'] + function['size']}
    if len(raw) != 332 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown complete saved-role vector body or bindings')
    return raw, bindings


def qualify(root, out):
    values = freeze(root, out)
    baseline, diagnostics = model.compile_owner(root, out, values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    obj, words, row = measure(root, out, 'qualified', selected(), baseline)
    checked(obj)
    model.require_retail_stack_contract(words)
    if diagnostics or row['diagnostics'] or row['differences'] != 56:
        raise ValueError('Changed saved-role candidate evidence')
    row.update(necessary_stack_gate_passed=True, matching_credit=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screen(root, out, group='pointers'):
    if group not in ('pointers', 'conversions', 'arithmetic'):
        raise ValueError('Unknown saved-role screen')
    values = freeze(root, out)
    baseline, diagnostics = model.compile_owner(root, out, values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected baseline diagnostics: ' + diagnostics)
    rows = []
    candidates = {'pointers': forms, 'conversions': conversion_forms, 'arithmetic': arithmetic_forms}
    for name, body in candidates[group]():
        _, _, row = measure(root, out, name, body, baseline)
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'saved', 'diagnostics')}), flush=True)
    freeze(root, out)
    result = dict(candidates=rows, frozen_inputs_unchanged=True, matching_credit=0)
    (out / ('screen-' + group + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', choices=('pointers', 'conversions', 'arithmetic'), default='pointers')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
    else:
        screen(root, root / BUILD, args.screen)
