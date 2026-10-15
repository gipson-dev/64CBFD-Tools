"""Observe and fit the quad emitter's named locals without changing its compiler."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_quad_edge_emitter as source
from tools.experiments import game_table_fade_frame as frame

BUILD = 'conker/build/game-quad-edge-frame'
HOME_ORDER = ('edge', 'presetByte', 'xHigh', 'xLow', 'zHigh', 'zLow',
    'startY', 'startZ', 'x', 'y', 'z', 'extent', 'xFixed', 'zFixed', 'delay',
    'limit', 'base', 'nextIndex', 'index', 'next', 'color', 'count',
    'initial', 'ranges', 'colors', 'inverse', 'current', 'nextEdge')


def inline_invariants(body=source.SELECTED):
    # Diagnostic only: recomputing the reciprocal loses the per-edge snapshot.
    for declaration in ('    s32 width;\n', '    s32 lifetime;\n', '    f32 inverse;\n'):
        body = body.replace(declaration, '')
    return body.replace('            width = (s32)(836.0f * scale);\n', '').replace(
        '            lifetime = (s32)(143.0f * scale);\n', '').replace(
        '            inverse = 1.0f / (f32)((&count)[0] - 1);\n', '').replace(
        'index * inverse', 'index * (1.0f / (f32)((&count)[0] - 1))').replace(
        '(u32)width', '(u32)(s32)(836.0f * scale)').replace('+ lifetime', '+ (s32)(143.0f * scale)')


def candidates():
    inline = inline_invariants()
    fraction = inline.replace('    f32 fraction;\n', '').replace(
        '                fraction = (f32)index * (1.0f / (f32)((&count)[0] - 1));\n', '').replace(
        '* fraction', '* ((f32)index * (1.0f / (f32)((&count)[0] - 1)))')
    start = inline.replace('    f32 startX;\n', '').replace('                startX = current[0];\n', '').replace('startX', 'current[0]')
    snapshot = fraction.replace('    s32 count;\n', '    s32 count;\n    f32 inverse;\n').replace(
        '            do {\n', '            inverse = 1.0f / (f32)((&count)[0] - 1);\n            do {\n').replace(
        '((f32)index * (1.0f / (f32)((&count)[0] - 1)))', '((f32)index * inverse)').replace(
        '    f32 startX;\n', '').replace('                startX = current[0];\n', '').replace('startX', 'current[0]')
    named = reorder(snapshot, HOME_ORDER)
    addressed = named
    for old in ('if (edge != 3)', 'if (edge == 0 || edge == 2)', 'edge + 1', 'while (edge != 4)'):
        addressed = addressed.replace(old, old.replace('edge', '(&edge)[0]'))
    advancing = snapshot.replace('    s32 nextEdge;\n', '').replace('    f32 startZ;\n', '    f32 startZ;\n    f32 startX;\n').replace(
        '            nextEdge = nextIndex;\n', '').replace('            nextEdge = edge + 1;\n', '').replace(
        '        edge = nextEdge;', '        edge++;').replace(
        '                startY = current[1];', '                startX = current[0];\n                startY = current[1];').replace(
        'x = (next[0] - current[0]) * ((f32)index * inverse) + current[0];',
        'x = (next[0] - startX) * ((f32)index * inverse) + startX;')
    advancing = reorder(advancing, tuple('startX' if name == 'nextEdge' else name for name in HOME_ORDER))
    integer = named.replace('    f32 startY;\n    f32 startZ;\n', '    s32 width;\n    s32 lifetime;\n').replace(
        '                startY = current[1];\n', '').replace('                startZ = current[2];\n', '').replace(
        'startY', 'current[1]').replace('startZ', 'current[2]').replace(
        '            base = (s32)(D_800A6E84 * scale);',
        '            base = (s32)(D_800A6E84 * scale);\n            width = (s32)(836.0f * scale);\n            lifetime = (s32)(143.0f * scale);').replace(
        '% (u32)(s32)(836.0f * scale)', '% (u32)width').replace('+ (s32)(143.0f * scale)', '+ lifetime')
    return {'selected': source.SELECTED, 'inline-invariants': inline,
        'inline-fraction': fraction, 'inline-start-x': start, 'snapshot-reciprocal': snapshot,
        'named-homes': named, 'named-addressed-edge': addressed, 'advancing-edge': advancing,
        'integer-snapshots': integer}


def reorder(body, order):
    head, sep, tail = body.partition('                  s32 context) {\n')
    declarations, marker, code = tail.partition('    current = vertices;')
    if not sep or not marker:
        raise ValueError('Unknown edge-emitter declaration boundary')
    lines = [line for line in declarations.splitlines() if line]
    named = {line.split()[1].lstrip('*').rstrip(';'): line for line in lines}
    if len(named) != len(lines) or len(order) != len(named) or set(order) != set(named):
        raise ValueError('Declaration order must retain each actual local exactly once')
    return head + sep + '\n'.join(named[name] for name in order) + '\n\n' + marker + code


def trace(root, out, label='selected', body=source.SELECTED):
    root, out = Path(root).resolve(), Path(out).resolve()
    if (not out.is_relative_to(root / 'conker/build') or Path(label).name != label
            or label in ('', '.', '..')):
        raise ValueError('Owned frame output and simple label required')
    source.freeze(root, out)
    before = (out / 'before-preset_owner').read_text()
    prototype = source.build.body(before, 'func_1516D4E8').split('{', 1)[0].strip() + ';\n'
    declarations = source.DECLARATIONS + 's32 func_150ADA20(void);\n' + prototype
    with patch.object(frame, 'source', source), patch.object(source, 'DECLARATIONS', declarations):
        return frame.trace(root, out, label, body)


def summary(receipt):
    return dict(baseline={key: value for key, value in receipt['baseline'].items() if key != 'different_words'},
        events=receipt['events'], code_unchanged=receipt['code_unchanged'],
        standalone_equals_complete_owner=receipt['standalone_equals_complete_owner'],
        completed_exits=receipt['completed_exits'],
        reservations={stage: [row for row in rows if row['name'] == 'def'] for stage, rows in receipt['records'].items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', choices=candidates(), default='selected')
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    bodies = candidates()
    if args.screen:
        for label, body in bodies.items():
            if args.filter not in label:
                continue
            _, _, row = source.measure(root, root / BUILD, label, body)
            print(json.dumps({key: value for key, value in row.items() if key != 'different_words'}), flush=True)
    else:
        print(json.dumps(summary(trace(root, root / BUILD, args.label, bodies[args.label])), indent=2))
