"""Measure shared matrix indices and ordinary incoming-register hints."""
import argparse
import itertools
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_candidates as compiler
from tools.experiments import game_matrix_reflection_dispatch_homes as previous

BASE = previous.qualified_body()
SELECTED_NAME = 'actor-flags-u32-owner-cursor'


def index_body(placement, primary=True, secondary=True, unsigned=False):
    parts = list(BASE.split('secondary_check:\n', 1))
    for index, enabled in enumerate((primary, secondary)):
        if not enabled:
            continue
        body = parts[index]
        opening = '            if (inputFixed != 0) {\n'
        cold = '            } else {\n                matrix = (f32 (*)[4])(input + offset);\n'
        normalized = '                matrix[3][3] = 1.0f;\n'
        assert body.count(opening) == body.count(cold) == body.count(normalized) == 1
        assignment = '                firstMode = i * 64;\n'
        if placement == 'before':
            body = body.replace(opening, '            firstMode = i * 64;\n' + opening)
        else:
            body = body.replace(opening, opening + assignment)
            if placement == 'arms-before':
                body = body.replace(cold, cold + assignment)
            elif placement == 'arms-after':
                body = body.replace(normalized, normalized + assignment)
            elif placement != 'expression':
                raise ValueError(placement)
        body = body.replace('input + i * 64', 'input + firstMode')
        if placement == 'expression':
            marker = normalized + '                matrix = (f32 (*)[4])(input + firstMode);'
            assert body.count(marker) == 1
            body = body.replace(marker, normalized +
                '                matrix = (f32 (*)[4])(input + (firstMode = i * 64));')
        body = body.replace('output + offset', 'output + firstMode')
        parts[index] = body
    result = 'secondary_check:\n'.join(parts)
    if unsigned:
        assert result.count('    s32 i;\n') == 1
        result = result.replace('    s32 i;\n', '    u32 i;\n')
    return result


def typed_body():
    body = BASE.replace('input + i * 64', '(u8 *)&((f32 (*)[4][4])input)[i]')
    return body.replace('output + offset', '(u8 *)&((Mtx *)output)[i]')


def candidates():
    yield 'baseline331', BASE
    for placement, modes, unsigned in itertools.product(
            ('before', 'arms-before', 'arms-after', 'expression'),
            ((True, False), (False, True), (True, True)), (False, True)):
        primary, secondary = modes
        yield '%s-p%d-s%d-u%d' % (placement, primary, secondary, unsigned), index_body(
            placement, primary, secondary, unsigned)
    for body_name, body in (('baseline', BASE), ('shared', index_body('arms-before'))):
        yield 'incoming-register-' + body_name, body.replace('u8 *input,', 'register u8 *input,', 1)
    for first_unsigned, counter_unsigned, offset_unsigned in itertools.product((False, True), repeat=3):
        body = index_body('arms-before', unsigned=counter_unsigned)
        if first_unsigned:
            body = body.replace('    s32 firstMode;', '    u32 firstMode;')
        if offset_unsigned:
            body = body.replace('    s32 offset;', '    u32 offset;')
        yield 'index-types-f%d-i%d-o%d' % (first_unsigned, counter_unsigned, offset_unsigned), body
    for view, body in (('base', BASE), ('shared', index_body('arms-before'))):
        for kind in ('array', 'sizeof', 'shift'):
            typed = body
            if kind == 'array':
                typed = typed.replace('input + i * 64', '(u8 *)&((f32 (*)[4][4])input)[i]')
                typed = typed.replace('input + firstMode', '(u8 *)&((f32 (*)[4][4])input)[i]')
                typed = typed.replace('output + offset', '(u8 *)&((Mtx *)output)[i]')
                typed = typed.replace('output + firstMode', '(u8 *)&((Mtx *)output)[i]')
            elif kind == 'sizeof':
                typed = typed.replace('i * 64', 'i * sizeof(Mtx)')
            else:
                typed = typed.replace('i * 64', '(i << 6)')
            yield 'typed-%s-%s' % (view, kind), typed
    for shared, remove_destination, reuse_matrix in itertools.product((False, True), repeat=3):
        if not (remove_destination or reuse_matrix):
            continue
        body = index_body('arms-before') if shared else BASE
        if remove_destination:
            body = body.replace('    f32 (*destination)[4];\n', '')
            body = body.replace('            destination = (f32 (*)[4])cursor;\n', '')
            body = body.replace('destination', '((f32 (*)[4])cursor)')
        if reuse_matrix:
            body = body.replace('    u8 *saved;\n', '')
            body = body.replace('    saved = input;', '    matrix = (f32 (*)[4])input;')
            body = body.replace('    input = saved;', '    input = (u8 *)matrix;')
            body = body.replace('            saved = *(u8 **)(actor + 0x1D4);',
                '            matrix = *(f32 (**)[4])(actor + 0x1D4);')
            body = body.replace('            *(u8 **)(actor + 0x1D4) = saved;',
                '            *(f32 (**)[4])(actor + 0x1D4) = matrix;')
        yield 'local-reuse-s%d-d%d-m%d' % (shared, remove_destination, reuse_matrix), body
    typed = typed_body()
    for carrier in ('firstMode', 'i', 'destination'):
        body = typed
        if carrier == 'destination':
            body = body.replace('    f32 (*destination)[4];', '    s32 secondMode;')
            body = body.replace('            destination = (f32 (*)[4])cursor;\n', '')
            body = body.replace('destination', '((f32 (*)[4])cursor)')
            carrier = 'secondMode'
        body = body.replace('    offset = mode;\n', '    %s = mode;\n' % carrier)
        body = body.replace('if (offset != 2)', 'if (%s != 2)' % carrier)
        if carrier == 'firstMode':
            body = body.replace('    firstMode = mode;\n    if (firstMode == 1)',
                '    i = mode;\n    if (i == 1)', 1)
            body = body.replace('    if (firstMode != 0) goto secondary_check;',
                '    if (i != 0) goto secondary_check;', 1)
        yield 'mode-carrier-' + carrier, body
    marker = '''            distance = matrix[3][1];
            destination[3][1] = distance - ((distance - pivotY) + (distance - pivotY));'''
    assert typed.count(marker) == 1
    direct = '            destination[3][1] = matrix[3][1] - ((matrix[3][1] - pivotY) + (matrix[3][1] - pivotY));'
    yield 'translation-direct', typed.replace(marker, direct)
    yield 'translation-separate', typed.replace('    f32 distance;', '    f32 distance;\n    f32 value;').replace(
        marker, marker.replace('distance', 'value'))
    for input_typed, output_typed in itertools.product((False, True), repeat=2):
        if not (input_typed or output_typed):
            continue
        body = typed
        if input_typed:
            body = body.replace('u8 *input,', 'Mtx *input,')
            body = body.replace('saved = input;', 'saved = (u8 *)input;')
            body = body.replace('input = (u8 *)reflection;', 'input = (Mtx *)reflection;')
            body = body.replace('input = saved;', 'input = (Mtx *)saved;')
            body = body.replace('input + offset', '(u8 *)input + offset')
            body = body.replace('(u8 *)&((f32 (*)[4][4])input)[i]', '&input[i]')
        if output_typed:
            body = body.replace('u8 *volatile output,', 'Mtx *volatile output,')
            body = body.replace('cursor = output;', 'cursor = (u8 *)output;')
            body = body.replace('(u8 *)&((Mtx *)output)[i]', '&output[i]')
        yield 'matrix-parameters-i%d-o%d' % (input_typed, output_typed), body
    typed = typed.replace('u8 *input,', 'Mtx *input,').replace('saved = input;', 'saved = (u8 *)input;')
    typed = typed.replace('input = (u8 *)reflection;', 'input = (Mtx *)reflection;')
    typed = typed.replace('input = saved;', 'input = (Mtx *)saved;')
    typed = typed.replace('input + offset', '(u8 *)input + offset')
    typed = typed.replace('(u8 *)&((f32 (*)[4][4])input)[i]', '&input[i]')
    for gate, owner in itertools.product(('inputFixed', 'i', 'offset', 'firstMode'), ('saved', 'matrix', 'cursor')):
        prefix, tail = typed.rsplit('finish:\n', 1)
        tail = tail.replace('inputFixed', gate)
        if owner == 'matrix':
            tail = tail.replace('saved = *(u8 **)(actor + 0x1D4);',
                'matrix = *(f32 (**)[4])(actor + 0x1D4);')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = saved;',
                '*(f32 (**)[4])(actor + 0x1D4) = matrix;')
        elif owner == 'cursor':
            tail = tail.replace('cursor = output;', 'destination = (f32 (*)[4])output;')
            tail = tail.replace('saved = *(u8 **)(actor + 0x1D4);', 'cursor = *(u8 **)(actor + 0x1D4);')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = cursor;',
                '*(f32 (**)[4])(actor + 0x1D4) = destination;')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = saved;', '*(u8 **)(actor + 0x1D4) = cursor;')
        yield 'tail-gate-%s-owner-%s' % (gate, owner), prefix + 'finish:\n' + tail
    for gate_type, owner in itertools.product(('s32', 'u32'), ('saved', 'matrix', 'cursor')):
        body = typed.replace('    f32 (*destination)[4];', '    %s actorFlags;' % gate_type)
        body = body.replace('            destination = (f32 (*)[4])cursor;\n', '')
        body = body.replace('destination', '((f32 (*)[4])cursor)')
        prefix, tail = body.rsplit('finish:\n', 1)
        tail = tail.replace('inputFixed', 'actorFlags')
        if owner == 'matrix':
            tail = tail.replace('saved = *(u8 **)(actor + 0x1D4);',
                'matrix = *(f32 (**)[4])(actor + 0x1D4);')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = saved;',
                '*(f32 (**)[4])(actor + 0x1D4) = matrix;')
        elif owner == 'cursor':
            tail = tail.replace('cursor = output;', 'matrix = (f32 (*)[4])output;')
            tail = tail.replace('saved = *(u8 **)(actor + 0x1D4);', 'cursor = *(u8 **)(actor + 0x1D4);')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = cursor;',
                '*(f32 (**)[4])(actor + 0x1D4) = matrix;')
            tail = tail.replace('*(u8 **)(actor + 0x1D4) = saved;', '*(u8 **)(actor + 0x1D4) = cursor;')
        current = prefix + 'finish:\n' + tail
        yield 'actor-flags-%s-owner-%s' % (gate_type, owner), current
        if gate_type == 'u32' and owner == 'cursor':
            for snapshot in ('actorFlags', 'i'):
                body = current.replace('    offset = mode;\n', '    %s = mode;\n' % snapshot)
                body = body.replace('if (offset != 2)', 'if (%s != 2)' % snapshot)
                yield 'secondary-snapshot-' + snapshot, body


def qualified_body():
    return dict(candidates())[SELECTED_NAME]


def probe(root, out):
    from tools.tests import test_game_matrix_reflection_recovery as oracle

    body = qualified_body()
    meta, words = compiler.compile_candidate(root, out, 'selected-probe', body)
    _, old = compiler.compile_candidate(root, out, 'banked331-probe', BASE)
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), compiler.ROM))
    memory, args = oracle.fixture(0, 1, 1)
    models = [oracle.ReflectionOracle(w, memory, args).run() for w in (retail, old, words)]
    adapter = SimpleNamespace(SELECTED=body, compile_candidate=compiler.compile_candidate)
    with patch.object(oracle.observer, 'screen', adapter):
        observed = oracle.observer.trace(root, out, 'frame-selected', body)
    result = dict(meta=meta, changed_words=sum(a != b for a, b in zip(old, words)),
        RAM=[models[0].memory == m.memory for m in models],
        FPR=[models[0].f == m.f for m in models],
        GPR=[[i for i in range(32) if models[0].r[i] != m.r[i]] for m in models],
        code_unchanged=observed['code_unchanged'],
        frames=[e for e in observed['events'] if e['event'] == 'frame-write'],
        definitions={stage: [dict(storage=r['storage'], length=r['length'])
            for r in observed['records'][stage] if r['name'] == 'def']
            for stage in ('frontend', 'optimizer')},
        caches=[(r['offset'], r['words'][2]) for r in observed['records']['optimizer']
            if r['name'] == 'rlda' and r['storage'] == 'M'])
    (out / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-saved-index'
    out.mkdir(exist_ok=True)
    if args.probe:
        probe(root, out)
        return
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), compiler.ROM))
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = compiler.compile_candidate(root, out, name, body)
        meta.update(prefix_words=next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b),
            min(len(words), len(retail))),
            shifted_index_words=[dict(index=i, word='%08X' % w) for i, w in enumerate(words)
                if w >> 26 == 0 and w & 63 == 0 and w >> 6 & 31 == 6])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'prefix', meta['prefix_words'], 'shifts', len(meta['shifted_index_words']), flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
