"""Fit the cross-call matrix index using real, non-overlapping temporary lifetimes."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_matrix_reflection_roles as previous

BASE = dict(previous.candidates())[previous.SELECTED_NAME]
SELECTED_NAME = 'shared-float-index-s32-arms'
TAIL_SELECTED_NAME = 'tail-outputFixed-return0'
HOME_SELECTED_NAME = 'home-primary-guard1'


def shared_float(body):
    assert body.count('    f32 value;\n') == 1
    return body.replace('    f32 value;\n', '').replace('value', 'distance')


def direct_cursor(body):
    assert body.count('    f32 (*destination)[4];\n') == 1
    assert body.count('            destination = (f32 (*)[4])cursor;\n') == 2
    body = body.replace('    f32 (*destination)[4];\n', '')
    body = body.replace('            destination = (f32 (*)[4])cursor;\n', '')
    body = body.replace('    u8 *cursor;', '    f32 (*cursor)[4];')
    body = body.replace('cursor = output;', 'cursor = (f32 (*)[4])output;')
    body = body.replace('cursor += 64;', 'cursor += 4;')
    return body.replace('destination', 'cursor')


def shared_index(body, placement, kind='s32'):
    body = previous.capture_offset(body, kind, kind == 'u32', placement)
    if placement == 'arms':
        body = body.replace('matrix = (f32 (*)[4])(input + matrixOffset);',
            'matrix = (f32 (*)[4])(input + offset);')
    return body


def positive_setup(body, secondary=False):
    cast = 'cursor = (f32 (*)[4])output;'
    typed = body.count(cast) == 2
    if typed:
        body = body.replace(cast, 'cursor = output;')
    body = previous.positive_loop_setup(body, True, True, secondary)
    return body.replace('cursor = output;', cast) if typed else body


def candidates():
    yield 'banked333', BASE
    for name, transform in (('shared-float', shared_float), ('direct-cursor', direct_cursor)):
        body = transform(BASE)
        yield name, body
        for kind in ('s32', 'u32'):
            for placement in ('top', 'arms'):
                current = shared_index(body, placement, kind)
                yield name + '-index-' + kind + '-' + placement, current
                for setup in ('primary', 'both'):
                    adjusted = positive_setup(current)
                    if setup == 'both':
                        adjusted = positive_setup(adjusted, True)
                    yield name + '-index-' + kind + '-' + placement + '-setup-' + setup, adjusted
    for lifetime in ('shared-float', 'direct-cursor'):
        transform = shared_float if lifetime == 'shared-float' else direct_cursor
        for placement in ('top', 'arms'):
            body = shared_index(transform(BASE), placement)
            for qualifier in ('register ', 'volatile ', 'register volatile '):
                yield lifetime + '-' + placement + '-index-' + qualifier.strip().replace(' ', '-'), body.replace(
                    '    s32 matrixOffset;', '    ' + qualifier + 's32 matrixOffset;')
            for target in ('reflection', 'inputFixed', 'outputFixed'):
                if target == 'reflection':
                    adjusted = body.replace('    f32 reflection[4][4];', '    volatile f32 reflection[4][4];')
                    adjusted = adjusted.replace('matrix, reflection, destination', 'matrix, (f32 (*)[4])reflection, destination')
                    adjusted = adjusted.replace('destination, reflection, destination',
                        'destination, (f32 (*)[4])reflection, destination')
                    adjusted = adjusted.replace('matrix, reflection, cursor', 'matrix, (f32 (*)[4])reflection, cursor')
                    adjusted = adjusted.replace('cursor, reflection, cursor', 'cursor, (f32 (*)[4])reflection, cursor')
                else:
                    adjusted = body.replace('s32 ' + target, 'volatile s32 ' + target)
                yield lifetime + '-' + placement + '-volatile-' + target, adjusted


def qualified_body():
    return dict(home_candidates())[HOME_SELECTED_NAME]


def tail_body():
    return dict(tail_candidates())[TAIL_SELECTED_NAME]


def tail_candidates():
    body = dict(candidates())[SELECTED_NAME]
    yield 'tail-baseline332', body
    old = '''    if (actor != 0 && *(u32 *)(actor + 0x9C) != 0) {
        saved = *(u8 **)(actor + 0x1D4);
        *(u8 **)(actor + 0x1D4) = output;
        func_15034728(actor);
        *(u8 **)(actor + 0x1D4) = saved;
    }'''
    assert body.count(old) == 1
    for carrier in ('i', 'offset', 'matrixOffset', 'mode', 'inputFixed', 'outputFixed'):
        for early_return in (False, True):
            core = '''        saved = *(u8 **)(actor + 0x1D4);
        *(u8 **)(actor + 0x1D4) = cursor;
        func_15034728(actor);
        *(u8 **)(actor + 0x1D4) = saved;'''
            load = carrier + ' = *(u32 *)(actor + 0x9C);\n'
            if early_return:
                tail = '    if (actor == 0) return;\n    ' + load + '    cursor = output;\n'
                tail += '    if (' + carrier + ' == 0) return;\n' + '\n'.join(
                    line[4:] for line in core.splitlines())
            else:
                tail = '    if (actor != 0) {\n        ' + load + '        cursor = output;\n'
                tail += '        if (' + carrier + ' != 0) {\n' + '\n'.join(
                    '    ' + line for line in core.splitlines()) + '\n        }\n    }'
            yield 'tail-' + carrier + '-return%d' % early_return, body.replace(old, tail)


def cold_loop_candidates():
    body = tail_body()
    yield 'cold-baseline329', body
    for cursor, offset in ((False, False), (True, False), (False, True), (True, True)):
        moved = previous.positive_loop_setup(body, cursor, offset) if cursor or offset else body
        name = 'cold-c%d-o%d' % (cursor, offset)
        if cursor or offset:
            yield name, moved
        marker = '        i = 0;\n        if (count > 0) {\n'
        assert moved.count(marker) == 2
        yield name + '-index-inside', moved.replace(marker,
            '        if (count > 0) {\n            i = 0;\n', 1)


def home_candidates():
    body = tail_body()
    view = '(*(u8 *volatile *)&output)'
    for guarded in (False, True):
        current = previous.positive_loop_setup(body, True, True) if guarded else body
        for uses in ('primary', 'cursors', 'all'):
            candidate = current.replace('cursor = output;', 'cursor = ' + view + ';',
                1 if uses == 'primary' else 3)
            if uses == 'all':
                candidate = candidate.replace('output + matrixOffset', view + ' + matrixOffset')
            yield 'home-' + uses + '-guard%d' % guarded, candidate


def typedef_candidates():
    body = tail_body()
    declaration = 'u8 *volatile output,'
    assert body.count(declaration) == 1
    for guarded in (False, True):
        current = previous.positive_loop_setup(body, True, True) if guarded else body
        for qualifier in ('volatile ReflectionOutput', 'ReflectionOutput volatile'):
            candidate = 'typedef u8 *ReflectionOutput;\n' + current.replace(declaration, qualifier + ' output,')
            yield 'typedef-guard%d-' % guarded + qualifier.replace(' ', '-'), candidate


def direct_home_candidates():
    body = previous.positive_loop_setup(tail_body(), True, True)
    for name, view in (('dereference-address', '*&output'), ('parenthesized-address', '*(&output)'),
                       ('zero-subscript', '(&output)[0]')):
        yield 'direct-home-' + name, body.replace('cursor = output;', 'cursor = ' + view + ';', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    stages = dict(measurements=candidates, tails=tail_candidates, cold=cold_loop_candidates,
        homes=home_candidates, typedefs=typedef_candidates)
    stages['direct-homes'] = direct_home_candidates
    modes = parser.add_mutually_exclusive_group()
    for stage in stages:
        if stage != 'measurements':
            modes.add_argument('--' + stage, dest='stage', action='store_const', const=stage)
    parser.set_defaults(stage='measurements')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-index-lifetime'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>486I',
        (root / 'conker/conker.us.bin').read_bytes(), previous.previous.ROM))
    records = []
    for name, body in stages[args.stage]():
        if args.filter not in name:
            continue
        meta, words = previous.previous.compile_candidate(root, out, name, body)
        first = next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b),
            min(len(words), len(retail)))
        meta.update(prefix_words=first, first23_exact=words[:23] == retail[:23])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], 'prefix', first, flush=True)
    (out / (args.stage + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
