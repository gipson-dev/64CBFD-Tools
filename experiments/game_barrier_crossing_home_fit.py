"""Recover the two live scalar homes without dummy storage or a frame edit."""
import argparse
import json
from pathlib import Path
import re

from tools.experiments import game_barrier_crossing_candidates as source

BUILD = source.BUILD + '/match'
SOURCE, OWNER, FUNCTION, ENTRY, ROM, WORDS = (source.SOURCE, source.OWNER, source.FUNCTION,
    source.ENTRY, source.ROM, source.WORDS)
INPUTS = source.INPUTS
freeze, payload = source.freeze, source.payload
compile_profile, link_owner = source.compile_profile, source.link_owner


def home_candidates(before):
    base = source.selected_body(before)
    pair = '    f32 minimum;\n    f32 fraction;\n'
    if base.count(pair) != 1 or base.count('    s32 band;\n') != 1:
        raise ValueError('Unknown crossing scalar declaration block')
    for name, names in (('hit-first', ('minimum', 'fraction')),
            ('minimum-first', ('minimum',)), ('fraction-first', ('fraction',))):
        body = base
        for variable in names:
            body = body.replace('    f32 ' + variable + ';\n', '', 1)
        body = body.replace('    s32 band;\n', ''.join('    f32 ' + variable + ';\n'
            for variable in names) + '    s32 band;\n', 1)
        yield name, body
    prefix, rest = base.split('    band = func_15085DA8(y);', 1)
    floats = re.findall(r'^    f32 \w+;\n', prefix, re.M)
    for declaration in floats:
        prefix = prefix.replace(declaration, '', 1)
    yield 'floats-first', prefix.replace('    s32 band;\n', ''.join(floats) + '    s32 band;\n', 1) + (
        '    band = func_15085DA8(y);' + rest)
    body = base.replace('    s32 band;\n    s32 count;\n', '', 1)
    yield 'hit-before-count', body.replace(pair, pair + '    s32 band;\n    s32 count;\n', 1)
    for variable in ('ax', 'az', 'nx'):
        body = base.replace(pair, '', 1)
        declaration = '    f32 ' + variable + ';\n'
        for reverse in (False, True):
            hit = '    f32 fraction;\n    f32 minimum;\n' if reverse else pair
            yield 'hit-after-' + variable + ('-reversed' if reverse else ''), body.replace(
                declaration, declaration + hit, 1)


def selected_body(before):
    return dict(home_candidates(before))['hit-after-ax-reversed']


def recovered_owner(before):
    return source.recovered_owner(before,
        '/* Measure horizontal node-edge crossings, retaining the last crossing fraction. */\n' + selected_body(before))


def compile_candidate(root, out, name='selected', body=None, normal=False, whole=False):
    if body is None:
        body = selected_body(freeze(root, out)[SOURCE].decode())
    return source.compile_candidate(root, out, name, body, normal, whole)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / source.BUILD / 'home-fit'
    values = source.freeze(root, out)
    for name, body in home_candidates(values[source.SOURCE].decode()):
        if args.filter and name != args.filter:
            continue
        _, _, row = source.compile_candidate(root, out, name, body)
        print(json.dumps(dict(name=name, **row)), flush=True)


if __name__ == '__main__':
    main()
