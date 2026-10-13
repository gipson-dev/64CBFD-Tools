"""Fit category promotion and noise selection on the aligned finalizer body."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_clamp as previous

BASE = previous.SELECTED
replace_once = previous.replace_once
NOISE = '''    if ((u32)(delta = value) != 0x69U && (u32)delta != 0x7CU && (u32)delta != 0x87U) {
        noise = 10;
    } else {
        noise = 0;
    }'''


def optimizer_prefix(record):
    records = record['records']['optimizer']
    limits = [r for r in records if r['name'] == 'rldc' and r['constants'] == [255, 0]]
    assert limits
    boundary = min(r['byte_offset'] for r in limits)
    before = [r for r in records if r['byte_offset'] < boundary]
    kinds = ('rldc', 'rlod', 'rstr', 'ldc', 'lod', 'str', 'cvt', 'cvtl', 'equ', 'neq', 'fjp', 'tjp', 'ujp')
    return [r for r in before if r['name'] in kinds]


def prefix_summary(record):
    prefix = optimizer_prefix(record)
    biases = [r for r in prefix if r['name'] == 'rldc' and r['constants'] == [124, 0]]
    branches = [r for r in prefix if r['name'] == 'equ' and r['dtype'] == 'L']
    cache = [r for r in prefix if r['name'] == 'str' and r['storage'] == 'R' and r['offset'] == 3]
    typed = [r for r in cache if r['dtype'] == 'L']
    return dict(bias_constants=biases, bias_comparisons=branches, storage_R3=cache,
        typed_L_cache_before_bias=bool(typed and branches and typed[0]['byte_offset'] < branches[0]['byte_offset']),
        descriptor_defined_fields_only=True, physical_ready_list_not_observed=True)


def selection(body, local, placement, unsigned=True, inverted=False):
    values = ['value'] * 3
    prefix = ''
    if local:
        if placement == 'before':
            prefix = '    ' + local + ' = value;\n'
            values = [local] * 3
        else:
            index = int(placement)
            values[index] = '(' + local + ' = value)'
            values[index + 1:] = [local] * (2 - index)
    literals = ('0x69', '0x7C', '0x87')
    operator = ' == ' if inverted else ' != '
    predicate = (' || ' if inverted else ' && ').join(
        ('(u32)' if unsigned else '') + value + operator + literal + ('U' if unsigned else '')
        for value, literal in zip(values, literals))
    yes, no = (0, 10) if inverted else (10, 0)
    return replace_once(body, NOISE, prefix + '''    if (%s) {
        noise = %d;
    } else {
        noise = %d;
    }''' % (predicate, yes, no))


def operand_forms(body):
    sum_old = 'value = actor[0x1FE] + *(s8 *)(actor + 0x203);'
    sum_new = 'value = *(s8 *)(actor + 0x203) + actor[0x1FE];'
    yield 'primary-sum', replace_once(body, sum_old, sum_new)
    yield 'limit-left', replace_once(body, 'value == limit', 'limit == value')
    yield 'sum-and-limit', replace_once(replace_once(body, sum_old, sum_new), 'value == limit', 'limit == value')
    update = '*(s16 *)(actor + 0x204) += *(s8 *)(actor + 0x209);'
    yield 'explicit-tail-sum', replace_once(body, update,
        '*(s16 *)(actor + 0x204) = *(s16 *)(actor + 0x204) + *(s8 *)(actor + 0x209);')
    yield 'reversed-tail-sum', replace_once(body, update,
        '*(s16 *)(actor + 0x204) = *(s8 *)(actor + 0x209) + *(s16 *)(actor + 0x204);')
    yield 'sign-left', replace_once(body, '*(s8 *)(actor + 0x209) * sign', 'sign * *(s8 *)(actor + 0x209)')
    row = 'delta = (s32)((f32)*(s16 *)(actor + 0x204) * magnitude * D_80097D5C);'
    for local in ('scale', 'magnitude'):
        floating = replace_once(body, row, local + ' = (f32)*(s16 *)(actor + 0x204) * magnitude * D_80097D5C;')
        yield 'floating-row-' + local, replace_once(floating, '*(s16 *)(output + 2) = -delta;',
            '*(s16 *)(output + 2) = -(s32)' + local + ';')


def category_local(body, local):
    body = selection(body, None, None)
    body = replace_once(body, '    s16 value = actor[4];', '    s16 value;')
    body = replace_once(body, '    s32 ' + local + ';', '    s32 ' + local + ' = actor[4];')
    declarations, body = body.split('    if (value == 0x70)', 1)
    conditions, tail = ('    if (value == 0x70)' + body).split('    limit = 0xFF;', 1)
    return declarations + conditions.replace('value', local) + '    limit = 0xFF;' + tail


def candidates():
    yield 'baseline', BASE
    for unsigned in (False, True):
        suffix = '-u' + str(int(unsigned))
        yield 'value' + suffix, selection(BASE, None, None, unsigned)
        yield 'value-or' + suffix, selection(BASE, None, None, unsigned, True)
        for local in ('delta', 'current', 'primaryIndex'):
            for placement in ('before', '0', '1', '2'):
                if local == 'delta' and placement == '0' and unsigned:
                    continue
                yield local + '-' + placement + suffix, selection(BASE, local, placement, unsigned)
    for mask in range(1, 7):
        predicate = ' && '.join(('(u32)value != ' + literal + 'U' if mask & (1 << i)
            else 'value != ' + literal) for i, literal in enumerate(('0x69', '0x7C', '0x87')))
        yield 'mixed-' + str(mask), replace_once(BASE, NOISE, '''    if (%s) {
        noise = 10;
    } else {
        noise = 0;
    }''' % predicate)
    unsigned = replace_once(BASE, '    s16 value = actor[4];', '    u16 value = actor[4];')
    for token in ('value < 0', 'value >= 256', 'value > 0', 'value < -255'):
        unsigned = unsigned.replace(token, '(s16)' + token)
    unsigned = replace_once(unsigned, 'current = (s16)value >= 256 ? limit : value;',
        'current = (s16)value >= 256 ? limit : (s16)value;')
    yield 'unsigned-short', unsigned
    wide = replace_once(BASE, '    s16 value = actor[4];', '    s32 value = actor[4];')
    for expression in (
        '(s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48)',
        '(s32)((f32)(actor[0x1FE] * *(s8 *)(actor + 0x202) / limit)\n            * D_80097D4C * D_80097D50)',
        'actor[0x1FE] + *(s8 *)(actor + 0x203)',
        'current'):
        wide = replace_once(wide, 'value = ' + expression + ';', 'value = (s16)(' + expression + ');')
    yield 'wide-with-short-writes', wide
    for name, body in operand_forms(BASE):
        yield 'operands-' + name, body
    for local in ('delta', 'current', 'primaryIndex'):
        yield 'category-' + local, category_local(BASE, local)
    direct_bias = replace_once(BASE, '(u32)value == 0x7CU', '(u32)actor[4] == 0x7CU')
    yield 'direct-bias', direct_bias
    for unsigned in (False, True):
        body = selection(direct_bias, None, None, unsigned)
        yield 'direct-bias-value-u' + str(int(unsigned)), body
        predicate_body = body.split('    limit = 0xFF;', 1)[0]
        start = predicate_body.rfind('    if (')
        field = predicate_body[:start] + predicate_body[start:].replace('value', 'actor[4]')
        yield 'direct-bias-field-u' + str(int(unsigned)), field + '    limit = 0xFF;' + body.split('    limit = 0xFF;', 1)[1]
    for name, expression in (('byte', '(u8)value'), ('halfword', '(u16)value'),
            ('byte-mask', '((u32)value & 0xFFU)')):
        yield 'bias-width-' + name, replace_once(BASE, '(u32)value == 0x7CU', expression + ' == 0x7CU')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--faults', action='store_true')
    parser.add_argument('--trace', choices=('baseline', 'mixed-2', 'value-u0'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-command-finalizer-noise'
    out.mkdir(exist_ok=True)
    if args.trace:
        body = dict(candidates())[args.trace]
        record = previous.previous.fitting.trace(root, out / 'owned-types', args.trace, body)
        prefix = optimizer_prefix(record)
        (out / ('optimizer-' + args.trace + '.json')).write_text(json.dumps(prefix, indent=2) + '\n')
        print(json.dumps(dict(candidate=args.trace, code_unchanged=record['code_unchanged'],
            shape={k: record['baseline'][k] for k in ('body_words', 'frame', 'differences')},
            inputs=record['inputs'], summary=prefix_summary(record)), indent=2))
        return
    retail = list(struct.unpack_from('>405I', (root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
    compiler = previous.previous.fitting.compile_candidate
    _, baseline = compiler(root, out, 'control', BASE)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = previous.previous.measure(root, out, name, body, retail, baseline)
        if args.faults:
            if meta['body_words'] == 405 and meta['first14_exact']:
                meta['fault_sweep'] = previous.previous.previous.previous.fault_sweep(words, retail)
            else:
                meta['fault_sweep_skipped'] = 'Original extent/opening gate failed; candidate is rejected'
        meta['opening_differences'] = [i for i in range(32) if words[i] != retail[i]]
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'prefix', meta['first14_exact'], 'opening', meta['opening_differences'],
            meta.get('fault_sweep', {}).get('equal_states'), flush=True)
    (out / ('measurements-' + (args.filter or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
