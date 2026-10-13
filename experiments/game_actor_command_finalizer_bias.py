"""Fit bias conversion and incoming-home lifetimes without changing widths."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_noise as previous

BASE = previous.BASE
replace_once = previous.replace_once


def signed_selection(body):
    body = replace_once(body, '(u32)value == 0x7CU', 'value == 0x7C')
    return previous.selection(body, 'delta', '0', False)


def shared_constant(body, local, early=True):
    body = signed_selection(body)
    marker = '    if (value == 0x70)' if early else '    if (value == 0x7C)'
    body = replace_once(body, marker, '    ' + local + ' = 0x7C;\n' + marker)
    body = replace_once(body, 'value == 0x7C', 'value == ' + local)
    return replace_once(body, 'delta != 0x7C', 'delta != ' + local)


def candidates():
    yield 'baseline', BASE
    for signed in (False, True):
        body = signed_selection(BASE) if signed else BASE
        for first, second in ((True, False), (False, True), (True, True)):
            source = body
            if first:
                source = replace_once(source, 's32 first,', 'volatile s32 first,')
            if second:
                source = replace_once(source, 's32 second)', 'volatile s32 second)')
            yield 'homes-s%d-f%d-t%d' % (signed, first, second), source
    for local in ('lower', 'limit', 'current', 'primaryIndex'):
        for early in (False, True):
            yield 'constant-' + local + '-e' + str(int(early)), shared_constant(BASE, local, early)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--faults', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-command-finalizer-bias'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>405I', (root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
    fitting = previous.previous.previous.fitting
    _, baseline = fitting.compile_candidate(root, out, 'control', BASE)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = previous.previous.previous.measure(root, out, name, body, retail, baseline)
        if args.faults and meta['body_words'] == 405 and meta['first14_exact']:
            meta['fault_sweep'] = previous.previous.previous.previous.previous.fault_sweep(words, retail)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'prefix', meta['first14_exact'], meta.get('fault_sweep', {}).get('equal_states'), flush=True)
    (out / ('measurements-' + (args.filter or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
