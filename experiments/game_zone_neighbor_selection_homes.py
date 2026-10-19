"""Screen real query/scalar homes without adding storage or changing the ABI."""

import argparse
import json
import re
from pathlib import Path

from tools.experiments import game_zone_neighbor_selection_candidates as source
from tools.experiments import game_zone_neighbor_selection_lifetimes as lifetime


BUILD = 'conker/build/game-zone-neighbor-homes'


def declarations(body, names):
    head, tail = body.split('\n\n', 1)
    lines = head.splitlines()
    if not lines[0] == 'void func_1508B3F8(void) {':
        raise ValueError('Missing complete parent declaration block')
    old = lines[1:]
    if any(not re.fullmatch(r'    [\w *]+ \*?\w+;', line) for line in old):
        raise ValueError('Unexpected declaration form')
    by_name = {re.search(r'(\w+);$', line)[1]: line for line in old}
    if len(by_name) != len(old) or len(names) != len(old) or set(names) != set(by_name):
        raise ValueError('Declaration permutation is not closed')
    return '\n'.join(lines[:1] + [by_name[name] for name in names]) + '\n\n' + tail


def names(body):
    head = body.split('\n\n', 1)[0]
    return [re.search(r'(\w+);$', line)[1] for line in head.splitlines()[1:]]


def narrow_best(body):
    body = source.replace(body, '    s32 best;', '    u8 best;')
    return re.sub(r'best = ([^;]+);', lambda m:
                  m[0] if m[1] == '0xFF' else 'best = (u8)(%s);' % m[1], body)


def homes(body):
    # IDO reserves these actual declarations in reverse order within the frame.
    others = [name for name in names(body)
              if name not in ('i', 'selections', 'query', 'zone')]
    if len(others) != 19:
        raise ValueError('Original scalar/query inventory changed')
    order = ['i'] + others[:5] + ['selections'] + others[5:13]
    order += ['query'] + others[13:18] + ['zone'] + others[18:]
    return declarations(body, order)


SELECTED = homes(source.SELECTED)


def candidates():
    yield 'installed', source.SELECTED
    old = names(source.SELECTED)
    for position in (1, 5, 10, 15, 20, 22):
        order = [name for name in old if name != 'query']
        order.insert(position, 'query')
        yield 'query-position-%d' % position, declarations(source.SELECTED, order)
    selected = SELECTED
    yield 'retail-named-homes', selected
    yield 'retail-named-homes-byte-best', narrow_best(selected)
    flags = lifetime.context_pointer(source.CHECKPOINT, flags=True)
    yield 'retained-flags', flags
    yield 'retained-flags-byte-best', narrow_best(flags)
    for label, body in (('homes', selected), ('flags', flags)):
        yield label + '-guarded-actor', lifetime.guarded_actor(body)
        yield label + '-cached-coordinates', lifetime.cached_coordinates(body)
        yield label + '-deferred-zone', lifetime.deferred_zone(body)
    controls = dict(lifetime.cursor_candidates())
    for suffix in ('word', 'byte'):
        body = controls['cursor-direct-distances-context-' + suffix]
        yield 'typed-distance-' + suffix, body
        yield 'typed-distance-homes-' + suffix, homes(body)
    for field in ('threshold', 'count', 'x', 'z'):
        yield 'direct-' + field, selected.replace('context->' + field, 'query.' + field)
    direct = selected
    for field in ('threshold', 'count', 'x', 'z', 'ids', 'distances', 'visited'):
        direct = direct.replace('context->' + field, 'query.' + field)
    yield 'direct-all-fields', direct
    for name, body in (('byte-cursors', selected),
                       ('typed-byte', homes(controls['cursor-direct-distances-context-byte']))):
        candidate = body.replace('    s32 remainder;\n', '').replace(
            '                        remainder = context->count & 3;\n', '')
        candidate = re.sub(r'\bremainder\b', '(context->count & 3)', candidate)
        yield name + '-inline-remainder', candidate
        yield name + '-ready-byte', body.replace('    s32 ready;', '    u8 ready;')
        yield name + '-explicit-byte-winners', re.sub(
            r'best = ([^;]+);', lambda m: m[0] if m[1] == '0xFF'
            else 'best = (u8)(%s);' % m[1], body)


def locations(words):
    def stack_offsets(op, register=None):
        return [w & 65535 for w in words if w >> 26 == op and w >> 21 & 31 == 29
                and (register is None or w >> 16 & 31 == register)]
    return dict(query_x_stores=stack_offsets(57, 22),
                query_count_stores=stack_offsets(41, 0),
                zero_word_homes=stack_offsets(43, 0),
                opening_pointer_homes=[w & 65535 for w in words[:50]
                    if w >> 26 == 43 and w >> 21 & 31 == 29
                    and w >> 16 & 31 in range(8, 16)],
                retained_stack_pointers=[(w >> 16 & 31, w & 65535) for w in words
                    if w >> 26 == 9 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    forms = dict(candidates())
    if args.names:
        if not set(args.names) <= forms.keys():
            parser.error('Unknown source form')
        forms = {name: forms[name] for name in args.names}
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    records = []
    for name, body in forms.items():
        record, words = source.compile_candidate(root, out, name, body)
        record['locations'] = locations(words)
        records.append(record)
        print(name, record['body_words'], record['frame'], record['real_differences'],
              json.dumps(record['locations']), flush=True)
    (out / 'home-screen.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
