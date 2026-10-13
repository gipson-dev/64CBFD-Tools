"""Screen secondary sign setup against the banked full finalizer body."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_fitting as fitting
from tools.experiments import game_actor_command_finalizer_schedule as previous

BASE = previous.SELECTED
replace_once = previous.replace_once
SIGN = '''        if (scale < 0.0f) {
            sign = -1;
        } else {
            sign = 1;
        }'''
NEGATIVE = '''        if (scale < 0.0f) {
            sign = -1;
        }'''


def sign_default(body, early):
    body = replace_once(body, SIGN, NEGATIVE)
    anchor = '    if (second != limit) {' if early else NEGATIVE
    replacement = anchor + '\n        sign = 1;' if early else '        sign = 1;\n' + anchor
    return replace_once(body, anchor, replacement)


def scale_capture(body, local):
    anchor = '        if (*(s8 *)(actor + 0x208) == 0) {'
    body = replace_once(body, anchor,
        '        ' + local + ' = *(s8 *)(actor + 0x208);\n' +
        '        if (' + local + ' == 0) {')
    return replace_once(body, '(f32)*(s8 *)(actor + 0x208)', '(f32)' + local)


def secondary_value(body, local):
    head, tail = body.split('    if (second != limit) {', 1)
    assert tail.count('current = *(s16 *)(actor + 0x204);') == 1
    return head + '    if (second != limit) {' + tail.replace('current', local)


def candidates():
    yield 'baseline', BASE
    for early in (False, True):
        body = sign_default(BASE, early)
        label = 'before-scale' if early else 'after-scale'
        yield label, body
        for local in ('delta', 'current', 'value'):
            yield label + '-' + local, scale_capture(body, local)
    yield 'ternary', replace_once(BASE, SIGN, '        sign = scale < 0.0f ? -1 : 1;')
    yield 'inverted', replace_once(BASE, SIGN, '''        if (!(scale < 0.0f)) {
            sign = 1;
        } else {
            sign = -1;
        }''')
    for local in ('value', 'primaryIndex', 'suppressed', 'secondaryBias'):
        body = secondary_value(BASE, local)
        yield 'value-' + local, body
        yield 'value-' + local + '-default', sign_default(body, True)


SELECTED_NAME = 'value-value'
SELECTED = secondary_value(BASE, 'value')


def recovered_owner(source):
    if source.count(BASE) == 1:
        return source.replace(BASE, SELECTED, 1)
    if source.count(SELECTED) == 1:
        return source
    raise ValueError('Expected the banked or qualified secondary-value body')


def measure(root, out, name, body, retail, baseline_words, sweep=False):
    meta, words = fitting.compile_candidate(root, out, name, body)
    meta['body_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
    meta['first14_exact'] = words[:14] == retail[:14]
    meta['last4_exact'] = words[-4:] == retail[-4:]
    meta['changed_words'] = [i for i, (old, new) in enumerate(zip(baseline_words, words)) if old != new]
    meta['probes'] = previous.fault_probes(words, retail)
    if sweep:
        meta['fault_sweep'] = previous.previous.fault_sweep(words, retail)
    return meta, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--faults', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-command-finalizer-secondary'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>405I', (root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
    _, baseline = fitting.compile_candidate(root, out, 'control', BASE)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = measure(root, out, name, body, retail, baseline, args.faults)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'opening', meta['first14_exact'], 'tail', meta['last4_exact'],
            [(r['first'], r['cut'], r['GPRs'], r['FPRs']) for r in meta['probes'][:3] + meta['probes'][5:6]],
            meta.get('fault_sweep', {}).get('equal_states'), flush=True)
    (out / ('measurements-' + (args.filter or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
