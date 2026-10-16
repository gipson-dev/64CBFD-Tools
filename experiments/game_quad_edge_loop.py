"""Current-checkpoint quad-emitter measurements; no production normalization."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_quad_edge_emitter as previous
from tools.experiments import game_quad_edge_lifetime as lifetime
from tools.experiments import game_quad_edge_wrapper_match as wrapper
from tools.tests import quad_edge_wrapper_checkpoint as checkpoint

BUILD = 'conker/build/game-quad-edge-loop-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = (previous.OWNER, previous.FUNCTION,
    previous.ENTRY, previous.ROM, previous.WORDS)
PATHS = wrapper.PATHS
BASELINE = dict(wrapper.BASELINE, **checkpoint.AFTER)
SELECTED = dict(lifetime.candidates())['word-preset']


def freeze(root, out):
    with patch.object(previous, 'PATHS', PATHS), patch.object(previous, 'BASELINE', BASELINE):
        previous.freeze(root, out)


def measure(root, out, label='word-preset', body=SELECTED):
    with patch.object(previous, 'PATHS', PATHS), patch.object(previous, 'BASELINE', BASELINE):
        return previous.measure(root, out, label, body)


def candidates():
    body = SELECTED
    inner = '                startY = current[1];'
    yield 'word-preset', body
    yield 'inner-home-read', body.replace(inner, '                edge = (&edge)[0];\n' + inner)
    yield 'inner-home-read-after', body.replace('                index++;',
        '                edge = (&edge)[0];\n                index++;')
    yield 'inner-home-write', body.replace(inner, '                (&edge)[0] = edge;\n' + inner)
    yield 'outer-home-next', body.replace('nextEdge = nextIndex;', 'nextEdge = (&edge)[0] + 1;').replace(
        'nextEdge = edge + 1;', 'nextEdge = (&edge)[0] + 1;')
    advance = body.replace('    s32 nextEdge;\n', '').replace('            nextEdge = nextIndex;\n', '').replace(
        '            nextEdge = edge + 1;\n', '')
    yield 'edge-next-home', advance.replace('        edge = nextEdge;', '        edge = (&edge)[0] + 1;')
    yield 'no-next-edge-one-home-read', advance.replace('        edge = nextEdge;', '        edge++;').replace(
        inner, '                edge = (&edge)[0];\n' + inner)
    yield 'next-computed-before', body.replace('        if (edge != 3) {',
        '        nextEdge = edge + 1;\n        if (edge != 3) {').replace(
        '            nextEdge = nextIndex;\n', '').replace('            nextEdge = edge + 1;\n', '')
    yield 'signed-next-before', body.replace('        if (edge != 3) {',
        '        nextIndex = edge + 1;\n        nextEdge = nextIndex;\n        if (edge != 3) {').replace(
        '            nextIndex = edge + 1;\n            nextEdge = nextIndex;\n', '').replace(
        '            nextEdge = edge + 1;\n', '')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for name, body in candidates() if args.screen else [('word-preset', SELECTED)]:
        _, _, row = measure(root, root / BUILD, name, body)
        print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)
