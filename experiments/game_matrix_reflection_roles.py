"""Fit real loop-offset lifetimes and the opening reflection-address cache."""
import argparse
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_matrix_reflection_candidates as previous

BASE = previous.qualified_body()
SELECTED_NAME = 'identity-through-restored-input'


def capture_offset(body, kind='s32', unsigned=False, placement='top'):
    declaration = next(line for line in ('    s32 offset;\n', '    u32 offset;\n') if body.count(line) == 1)
    body = body.replace(declaration, declaration + '    ' + kind + ' matrixOffset;\n', 1)
    expression = '(u32)i * 64U' if unsigned else 'i * 64'
    if placement == 'top':
        marker = '        do {\n'
        assert body.count(marker) == 2
        body = body.replace(marker, marker + '            matrixOffset = ' + expression + ';\n')
    else:
        assert placement == 'arms'
        body = body.replace('            if (inputFixed != 0) {',
            '            if (inputFixed != 0) {\n                matrixOffset = ' + expression + ';')
        body = body.replace('                matrix = (f32 (*)[4])(input + offset);',
            '                matrixOffset = ' + expression + ';\n                matrix = (f32 (*)[4])(input + matrixOffset);')
    body = body.replace('input + i * 64', 'input + matrixOffset').replace('output + i * 64', 'output + matrixOffset')
    return body


def positive_loop_setup(body, cursor=True, offset=True, secondary=False):
    parts = ['        cursor = output;' if cursor else '', '        offset = 0;' if offset else '']
    for part in filter(None, parts):
        marker = part + '\n'
        occurrence = 1 if secondary else 0
        start = body.index('    } else if (mode == 2)') if occurrence else 0
        at = body.index(marker, start)
        body = body[:at] + body[at:].replace(marker, '', 1)
        at = body.index('        if (count > 0) {\n', start)
        body = body[:at] + body[at:].replace('        if (count > 0) {\n',
            '        if (count > 0) {\n' + marker, 1)
    return body


def candidates():
    yield 'baseline', BASE
    for kind, unsigned, placement in itertools.product(('s32', 'u32'), (False, True), ('top', 'arms')):
        body = capture_offset(BASE, kind, unsigned, placement)
        yield 'offset-' + kind + '-u%d-' % unsigned + placement, body
        for cursor, offset in ((True, False), (False, True), (True, True)):
            yield 'offset-' + kind + '-u%d-' % unsigned + placement + '-setup-c%d-o%d' % (cursor, offset), (
                positive_loop_setup(body, cursor, offset))
    for cursor, offset, secondary in itertools.product((False, True), repeat=3):
        if cursor or offset:
            yield 'setup-c%d-o%d-secondary%d' % (cursor, offset, secondary), positive_loop_setup(BASE, cursor, offset, secondary)
    for expression in ('(f32 (*)[4])&reflection', '(f32 (*)[4])&reflection[0][0]', '&reflection[0]'):
        body = BASE.replace('guMtxIdentF(reflection)', 'guMtxIdentF(' + expression + ')')
        body = body.replace('matrix, reflection, destination', 'matrix, ' + expression + ', destination')
        body = body.replace('destination, reflection, destination', 'destination, ' + expression + ', destination')
        yield 'reflection-view-' + str(len(expression)), body
    for storage, qualifier in itertools.product(('register ', ''), ('', 'const ', 'volatile ')):
        if not (storage or qualifier):
            continue
        body = BASE.replace('u8 *input,', storage + 'u8 *' + qualifier + 'input,')
        yield 'input-' + (storage + qualifier).strip().replace(' ', '-'), body
    for name in ('reflection', 'converted', 'rotationMinus', 'rotationPlus'):
        body = BASE.replace('    f32 ' + name + '[4][4];', '    volatile f32 ' + name + '[4][4];')
        expression = '(f32 (*)[4])' + name
        if name == 'reflection':
            body = body.replace('guMtxIdentF(reflection)', 'guMtxIdentF(' + expression + ')')
            body = body.replace('matrix, reflection, destination', 'matrix, ' + expression + ', destination')
            body = body.replace('destination, reflection, destination', 'destination, ' + expression + ', destination')
        elif name == 'converted':
            body = body.replace('guMtxL2F(converted,', 'guMtxL2F(' + expression + ',')
            body = body.replace('matrix = converted;', 'matrix = ' + expression + ';')
            body = body.replace('bcopy(matrix, converted,', 'bcopy(matrix, (void *)converted,')
            body = body.replace('guMtxF2L2(converted,', 'guMtxF2L2(' + expression + ',')
        else:
            body = body.replace('func_150A8050(' + name + ',', 'func_150A8050(' + expression + ',')
            body = body.replace('destination, ' + name + ', destination', 'destination, ' + expression + ', destination')
        yield 'volatile-' + name, body
    for kind in ('u32', 's32', 'void *', 'Mtx *'):
        declaration = kind + ' input,'
        body = BASE.replace('u8 *input,', declaration)
        body = body.replace('input + ', '(u8 *)input + ')
        yield 'input-kind-' + kind.replace(' ', '').replace('*', 'pointer'), body
    for flag in ('inputFixed', 'outputFixed'):
        for capture in (False, True):
            body = BASE.replace('s32 ' + flag + ')', 'register s32 ' + flag + ')') if flag == 'outputFixed' else (
                BASE.replace('s32 ' + flag + ',', 'register s32 ' + flag + ','))
            if capture:
                local = 'decoded' if flag == 'inputFixed' else 'encoded'
                body = body.replace('    guMtxIdentF(reflection);', '    s32 ' + local + ' = ' + flag + ';\n\n    guMtxIdentF(reflection);')
                body = body.replace('if (' + flag + ' != 0)', 'if (' + local + ' != 0)')
            yield 'flag-' + flag + '-capture%d' % capture, body
    for flat, aggregate in ((True, False), (False, True), (True, True)):
        body = BASE
        if aggregate:
            body = body.replace('    f32 reflection[4][4];',
                '    union { f32 matrix[4][4]; f32 values[16]; } reflection;')
            pointer = 'reflection.matrix'
            body = body.replace('reflection[1][1]', 'reflection.values[5]' if flat else 'reflection.matrix[1][1]')
            body = body.replace('reflection[0][0]', 'reflection.values[0]' if flat else 'reflection.matrix[0][0]')
        else:
            body = body.replace('    f32 reflection[4][4];', '    f32 reflection[16];')
            pointer = '(f32 (*)[4])reflection'
            body = body.replace('reflection[1][1]', 'reflection[5]').replace('reflection[0][0]', 'reflection[0]')
        body = body.replace('guMtxIdentF(reflection)', 'guMtxIdentF(' + pointer + ')')
        body = body.replace('matrix, reflection, destination', 'matrix, ' + pointer + ', destination')
        body = body.replace('destination, reflection, destination', 'destination, ' + pointer + ', destination')
        yield 'reflection-flat%d-union%d' % (flat, aggregate), body
    for unsigned_index, unsigned_offset in itertools.product((False, True), repeat=2):
        if not (unsigned_index or unsigned_offset):
            continue
        body = BASE
        if unsigned_index:
            body = body.replace('    s32 i;', '    u32 i;')
        if unsigned_offset:
            body = body.replace('    s32 offset;', '    u32 offset;')
        yield 'loop-width-i%d-o%d' % (unsigned_index, unsigned_offset), body
        for placement in ('top', 'arms'):
            yield 'loop-width-i%d-o%d-' % (unsigned_index, unsigned_offset) + placement, capture_offset(body, 'u32', True, placement)
    for bank_kind in ('u8 *', 'Mtx *'):
        body = BASE.replace('    guMtxIdentF(reflection);', '    ' + bank_kind + 'bank = (' + bank_kind + ')input;\n\n    guMtxIdentF(reflection);')
        body = body.replace('input + ', '(u8 *)bank + ')
        yield 'captured-bank-' + bank_kind.replace(' ', '').replace('*', 'pointer'), body
    for qualifier in ('volatile s32', 'register s32', 'u32'):
        yield 'mode-' + qualifier.replace(' ', '-'), BASE.replace('s32 mode,', qualifier + ' mode,')
    opening = '    if (mode == 1 || mode == 0) {\n'
    split = '    } else if (mode == 2) {\n'
    tail = '    } else {\n        return;\n    }\n'
    assert BASE.count(opening) == BASE.count(split) == BASE.count(tail) == 1
    start, rest = BASE.split(opening, 1)
    horizontal, rest = rest.split(split, 1)
    angled, ending = rest.rsplit(tail, 1)
    for reverse in (False, True):
        condition = 'mode == 0 || mode == 1' if reverse else 'mode == 1 || mode == 0'
        body = start + '    if (' + condition + ') {\n' + horizontal + '        goto finish;\n    }\n'
        body += '    if (mode == 2) {\n' + angled + '        goto finish;\n    }\n    return;\nfinish:\n' + ending
        yield 'flow-goto-reverse%d' % reverse, body
    yield 'flow-switch', start + '    switch (mode) {\n    case 0:\n    case 1:\n' + horizontal + (
        '        break;\n    case 2:\n' + angled + '        break;\n    default:\n        return;\n    }\n' + ending)
    for name, kind in (('i', 's32'), ('offset', 's32'), ('cursor', 'u8 *')):
        declaration = '    ' + kind + ('' if kind.endswith('*') else ' ') + name + ';'
        assert BASE.count(declaration) == 1
        for qualifier in ('register ', 'register volatile ', 'volatile '):
            yield 'local-' + name + '-' + qualifier.strip().replace(' ', '-'), BASE.replace(declaration,
                '    ' + qualifier + declaration.strip(), 1)
    for qualifier in ('register s32', 'register volatile s32', 'volatile s32'):
        yield 'offset-local-' + qualifier.replace(' ', '-'), capture_offset(BASE, qualifier, False, 'top')
    body = capture_offset(BASE, 's32', False, 'arms')
    body = body.replace('matrix = (f32 (*)[4])(input + matrixOffset);',
        'matrix = (f32 (*)[4])(input + offset);')
    yield 'review-shared-index-arms', body
    marker = '                matrix[3][3] = 1.0f;'
    body = body.replace(marker, marker + '\n                matrix = (f32 (*)[4])(input + matrixOffset);')
    yield 'review-shared-index-arms-two-addresses', body
    body = body.replace('        do {\n', '        do {\n            destination = (f32 (*)[4])(input + offset);\n')
    body = body.replace('                matrix = (f32 (*)[4])(input + offset);', '                matrix = destination;')
    yield 'review-shared-index-arms-source-cursor', body
    body = BASE.replace('    s32 offset;', '    u8 *inputCursor;')
    body = body.replace('offset = 0;', 'inputCursor = input;').replace('input + offset', 'inputCursor')
    body = body.replace('offset += 64;', 'inputCursor += 64;')
    yield 'review-independent-input-cursor', body
    for name in ('matrix', 'destination', 'cursor', 'saved'):
        cast = '(u8 *)' if name in ('cursor', 'saved') else ''
        body = BASE.replace('    guMtxIdentF(reflection);',
            '    ' + name + ' = ' + cast + 'reflection;\n    guMtxIdentF((f32 (*)[4])' + name + ');')
        yield 'identity-through-' + name, body
    body = BASE.replace('    guMtxIdentF(reflection);',
        '    saved = input;\n    input = (u8 *)reflection;\n    guMtxIdentF((f32 (*)[4])input);\n    input = saved;')
    yield 'identity-through-restored-input', body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-roles'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), previous.ROM))
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = previous.compile_candidate(root, out, name, body)
        first = next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b), min(len(words), len(retail)))
        meta.update(prefix_words=first, first23_exact=words[:23] == retail[:23])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], 'prefix', first, flush=True)
    (out / ('measurements-' + (args.filter or 'all') + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
