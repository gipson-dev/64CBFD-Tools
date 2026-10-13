"""Fit the primary clamp without discarding recovered secondary roles."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_secondary as previous

BASE = previous.SELECTED
replace_once = previous.replace_once
CLAMP = '''            current = value < 256 ? value : limit;
            value = current;'''
BOUNDS = '''        upper = 60;
        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        }'''


def bounds_forms(body):
    for name, bounds in (
        ('explicit', '''        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        } else {
            upper = 60;
        }'''),
        ('inverted', '''        if (actor[4] != 0x42) {
            upper = 60;
        } else {
            lower = 80;
            upper = 120;
        }'''),
        ('upper-first', '''        upper = 60;
        if (actor[4] == 0x42) {
            upper = 120;
            lower = 80;
        }'''),
        ('upper-default-120', '''        upper = 120;
        if (actor[4] != 0x42) {
            upper = 60;
        } else {
            lower = 80;
        }''')):
        yield name, replace_once(body, BOUNDS, bounds)


def tail_velocity(body, local):
    marker = '\n        delta = *(s8 *)(actor + 0x209);\n        *(s16 *)(actor + 0x204) += delta;'
    assert body.count(marker) == 1
    head, tail = body.split(marker, 1)
    return head + marker.replace('delta', local) + tail.replace('delta', local)


def tail_forms(body):
    marker = '\n        delta = *(s8 *)(actor + 0x209);\n        *(s16 *)(actor + 0x204) += delta;'
    assert body.count(marker) == 1
    head, tail = body.split(marker, 1)
    field = '*(s8 *)(actor + 0x209)'
    yield 'field', head + '\n        *(s16 *)(actor + 0x204) += ' + field + ';' + tail.replace('delta', field)
    for local in ('current', 'primaryIndex'):
        update = '\n        delta = ' + field + ';\n        ' + local + ' = *(s16 *)(actor + 0x204);'
        yield 'sum-' + local, head + update + '\n        *(s16 *)(actor + 0x204) = ' + local + ' + delta;' + tail
    yield 'swap-predicates', head + marker + tail.replace('value < 0 && delta < 0',
        'delta < 0 && value < 0').replace('value > 0 && delta > 0', 'delta > 0 && value > 0')


def aligned_body():
    base = dict(bounds_forms(replace_once(BASE, 'value < 256 ? value : limit',
        'value >= 256 ? limit : value')))['explicit']
    return dict(tail_forms(base))['field']


def candidates():
    yield 'baseline', BASE
    for name, choice in (
        ('ge-ternary', '            current = value >= 256 ? limit : value;'),
        ('default-value', '''            current = value;
            if (value >= 256) {
                current = limit;
            }'''),
        ('default-limit', '''            current = limit;
            if (value < 256) {
                current = value;
            }'''),
        ('lt-arms', '''            if (value < 256) {
                current = value;
            } else {
                current = limit;
            }'''),
        ('ge-arms', '''            if (value >= 256) {
                current = limit;
            } else {
                current = value;
            }''')):
        yield name, replace_once(BASE, CLAMP, choice + '\n            value = current;')
    for ge in (False, True):
        body = replace_once(BASE, 'value < 256 ? value : limit', 'value >= 256 ? limit : value') if ge else BASE
        for name, bound in bounds_forms(body):
            yield 'bounds-' + name + '-ge' + str(int(ge)), bound
    base = dict(bounds_forms(replace_once(BASE, 'value < 256 ? value : limit',
        'value >= 256 ? limit : value')))['explicit']
    for local in ('current', 'primaryIndex', 'suppressed', 'secondaryBias'):
        yield 'tail-' + local, tail_velocity(base, local)
    for name, tail in tail_forms(base):
        yield 'tail-shape-' + name, tail
    body = aligned_body()
    noise = '(u32)(delta = value) != 0x69U && (u32)delta != 0x7CU && (u32)delta != 0x87U'
    for name, predicate in (
        ('second', '(u32)value != 0x69U && (u32)(delta = value) != 0x7CU && (u32)delta != 0x87U'),
        ('third', '(u32)value != 0x69U && (u32)value != 0x7CU && (u32)(delta = value) != 0x87U')):
        yield 'noise-' + name, replace_once(body, noise, predicate)
    yield 'aligned-early-lower', previous.previous.early_lower(body)


SELECTED_NAME = 'tail-shape-field'
SELECTED = aligned_body()


def recovered_owner(source):
    if source.count(BASE) == 1:
        return source.replace(BASE, SELECTED, 1)
    if source.count(SELECTED) == 1:
        return source
    raise ValueError('Expected the banked or qualified aligned finalizer body')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--faults', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-command-finalizer-clamp'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>405I', (root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
    _, baseline = previous.fitting.compile_candidate(root, out, 'control', BASE)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = previous.measure(root, out, name, body, retail, baseline, args.faults)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'opening', meta['first14_exact'], 'changed', len(meta['changed_words']),
            meta.get('fault_sweep', {}).get('equal_states'), flush=True)
    (out / ('measurements-' + (args.filter or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
