"""Fit meaningful quad-emitter loop-state lifetimes against the original code."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_quad_edge_emitter as source
from tools.experiments import game_quad_edge_frame as fitting

BUILD = 'conker/build/game-quad-edge-lifetime'


def candidates():
    body = fitting.candidates()['named-homes']
    yield 'named-homes', body
    yield 'addressed-next-edge', body.replace('edge = nextEdge;', 'edge = (&nextEdge)[0];')
    yield 'addressed-next-store', body.replace('nextEdge = nextIndex;', '(&nextEdge)[0] = nextIndex;').replace(
        'nextEdge = edge + 1;', '(&nextEdge)[0] = edge + 1;')
    yield 'separate-next-edge', body.replace('nextEdge = nextIndex;', 'nextEdge = edge + 1;')
    yield 'unsigned-edge', body.replace('    s32 edge;', '    u32 edge;')
    yield 'word-preset', body.replace('f32 originZ, u8 preset', 'f32 originZ, s32 preset').replace(
        'presetByte = preset;', 'presetByte = (u8)preset;')
    yield 'short-extent', body.replace('    s32 extent;', '    s16 extent;')
    advancing = body.replace('    s32 nextEdge;\n', '').replace('            nextEdge = nextIndex;\n', '').replace(
        '            nextEdge = edge + 1;\n', '').replace('        edge = nextEdge;', '        edge++;')
    yield 'advance-edge', advancing
    for name, indexed in (('advance-indexed-current', advancing), ('indexed-current', body)):
        for axis in range(3):
            indexed = indexed.replace('current[%d]' % axis, 'current[edge * 3 + %d]' % axis)
        yield name, indexed.replace('        current += 3;\n', '')
    yield 'advance-home-read', advancing.replace('        edge++;', '        edge = (&edge)[0] + 1;')
    yield 'advance-home-update', advancing.replace('        edge++;', '        (&edge)[0]++;')
    yield 'advance-all-home-reads', advancing.replace('        edge++;', '        edge = (&edge)[0] + 1;').replace(
        'if (edge != 3)', 'if ((&edge)[0] != 3)').replace('if (edge == 0 || edge == 2)',
        'if ((&edge)[0] == 0 || (&edge)[0] == 2)').replace('nextIndex = edge + 1;',
        'nextIndex = (&edge)[0] + 1;').replace('while (edge != 4)', 'while ((&edge)[0] != 4)')
    yield 'advance-unsigned-edge', advancing.replace('    s32 edge;', '    u32 edge;')
    yield 'advance-inline-y', advancing.replace('    f32 startY;\n', '').replace(
        '                startY = current[1];\n', '').replace('startY', 'current[1]')
    yield 'next-edge-before-branch', body.replace('        if (edge != 3) {',
        '        nextEdge = edge + 1;\n        if (edge != 3) {').replace(
        '            nextIndex = edge + 1;\n            nextEdge = nextIndex;', '            nextIndex = nextEdge;').replace(
        '            nextEdge = edge + 1;\n', '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label, body in candidates():
        if args.filter not in label:
            continue
        _, _, row = source.measure(root, root / BUILD, label, body)
        print(json.dumps({key: value for key, value in row.items() if key != 'different_words'}), flush=True)


if __name__ == '__main__':
    main()
