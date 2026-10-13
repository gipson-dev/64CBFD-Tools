"""Measure argument lowering and conversion-buffer cache allocation."""
import argparse
import itertools
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_candidates as compiler
from tools.experiments import game_matrix_reflection_saved_index as previous

BASE = previous.qualified_body()
SELECTED_NAME = 'identity-direct-plain'


def candidates():
    yield 'baseline259', BASE
    for kind in ('s32', 'u32'):
        body = BASE.replace('Mtx *input,', kind + ' input,')
        body = body.replace('input = (Mtx *)reflection;', 'input = (%s)reflection;' % kind)
        body = body.replace('input = (Mtx *)saved;', 'input = (%s)saved;' % kind)
        body = body.replace('&input[i]', '&((Mtx *)input)[i]')
        yield 'input-address-' + kind, body
    for owner in ('cursor', 'matrix'):
        body = BASE.replace('    u8 *saved;\n', '')
        if owner == 'cursor':
            body = body.replace('saved = (u8 *)input;', 'cursor = (u8 *)input;')
            body = body.replace('input = (Mtx *)saved;', 'input = (Mtx *)cursor;')
        else:
            body = body.replace('saved = (u8 *)input;', 'matrix = (f32 (*)[4])input;')
            body = body.replace('input = (Mtx *)saved;', 'input = (Mtx *)matrix;')
        yield 'opening-owner-' + owner, body
    marker = '''    saved = (u8 *)input;
    input = (Mtx *)reflection;
    guMtxIdentF((f32 (*)[4])input);
    input = (Mtx *)saved;'''
    assert BASE.count(marker) == 1
    for name, expression in (('plain', 'reflection'), ('cast', '(f32 (*)[4])reflection'),
            ('address', '(f32 (*)[4])&reflection')):
        body = BASE.replace(marker, '    guMtxIdentF(%s);' % expression)
        body = body.replace('    u8 *saved;\n', '')
        yield 'identity-direct-' + name, body
    body = BASE.replace('    f32 converted[4][4];', '    f32 converted[16];')
    body = body.replace('guMtxL2F(converted,', 'guMtxL2F((f32 (*)[4])converted,')
    body = body.replace('matrix = converted;', 'matrix = (f32 (*)[4])converted;')
    body = body.replace('guMtxF2L2(converted,', 'guMtxF2L2((f32 (*)[4])converted,')
    yield 'converted-flat', body
    for pointer, output_typed in itertools.product(('f32', 'Mtx'), (False, True)):
        body = BASE
        if pointer == 'f32':
            body = body.replace('Mtx *input,', 'f32 (*input)[4][4],')
            body = body.replace('input = (Mtx *)reflection;', 'input = (f32 (*)[4][4])reflection;')
            body = body.replace('input = (Mtx *)saved;', 'input = (f32 (*)[4][4])saved;')
        if output_typed:
            body = body.replace('u8 *volatile output,', 'Mtx *volatile output,')
            body = body.replace('cursor = output;', 'cursor = (u8 *)output;')
            body = body.replace('(u8 *)&((Mtx *)output)[i]', '&output[i]')
        yield 'pointer-view-%s-o%d' % (pointer, output_typed), body
    direct = BASE.replace(marker, '    guMtxIdentF(reflection);').replace('    u8 *saved;\n', '')
    value_block = '''            distance = matrix[3][1];
            ((f32 (*)[4])cursor)[3][1] = distance - ((distance - pivotY) + (distance - pivotY));'''
    assert direct.count(value_block) == 1
    for placement in ('before-converted', 'after-converted', 'after-distance'):
        body = direct
        declaration = '    f32 value;\n'
        if placement == 'before-converted':
            body = body.replace('    f32 converted[4][4];\n', declaration + '    f32 converted[4][4];\n')
        elif placement == 'after-converted':
            body = body.replace('    f32 converted[4][4];\n', '    f32 converted[4][4];\n' + declaration)
        else:
            body = body.replace('    f32 distance;\n', '    f32 distance;\n' + declaration)
        yield 'value-' + placement, body.replace(value_block, value_block.replace('distance', 'value'))
    yield 'value-direct-expression', direct.replace(value_block,
        '            ((f32 (*)[4])cursor)[3][1] = matrix[3][1] - ((matrix[3][1] - pivotY) + (matrix[3][1] - pivotY));')
    for mode_unsigned, offset_unsigned in itertools.product((False, True), repeat=2):
        body = direct
        if mode_unsigned:
            body = body.replace('    s32 firstMode;', '    u32 firstMode;')
        if offset_unsigned:
            body = body.replace('    s32 offset;', '    u32 offset;')
        yield 'direct-types-m%d-o%d' % (mode_unsigned, offset_unsigned), body
    old = '''                guMtxL2F(converted, (Mtx *)(&input[i]));
                matrix = converted;'''
    assert direct.count(old) == 2
    yield 'conversion-pointer-before-call', direct.replace(old,
        '''                matrix = converted;
                guMtxL2F(matrix, &input[i]);''')
    body = direct.replace('    f32 (*matrix)[4];', '    f32 (*matrix)[4];\n    f32 (*conversion)[4];')
    body = body.replace('        do {\n', '        conversion = converted;\n        do {\n')
    body = body.replace('guMtxL2F(converted,', 'guMtxL2F(conversion,')
    body = body.replace('matrix = converted;', 'matrix = conversion;')
    body = body.replace('bcopy(matrix, converted, 64);', 'bcopy(matrix, conversion, 64);')
    body = body.replace('guMtxF2L2(converted,', 'guMtxF2L2(conversion,')
    yield 'conversion-explicit-pointer', body


def qualified_body():
    return dict(candidates())[SELECTED_NAME]


def compile_candidate(root, out, name, body, profile='o2g3'):
    with patch.multiple(compiler.compiler, ENTRY=compiler.ENTRY, ROM=compiler.ROM,
            WORDS=compiler.WORDS, FUNCTION=compiler.FUNCTION, RECORD='',
            DECLARATIONS=compiler.DECLARATIONS, SYMBOLS=compiler.SYMBOLS):
        return compiler.compiler.compile_candidate(root, out, name, body, profile)


def probe(root, out):
    from tools.tests import test_game_matrix_reflection_recovery as oracle
    from tools.tests.test_game_matrix_reflection_roles import state

    body = qualified_body()
    meta, words = compile_candidate(root, out, 'selected-probe', body)
    _, banked = compile_candidate(root, out, 'banked259-probe', BASE)
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), compiler.ROM))
    memory, args = oracle.fixture(0, 1, 1)
    models = [oracle.ReflectionOracle(w, memory, args).run() for w in (retail, banked, words)]
    adapter = SimpleNamespace(SELECTED=body, compile_candidate=compiler.compile_candidate)
    with patch.object(oracle.observer, 'screen', adapter):
        observed = oracle.observer.trace(root, out, 'frame-selected', body)
    opening = {}
    for stage in ('frontend', 'optimizer'):
        records = observed['records'][stage]
        first_call = next(i for i, r in enumerate(records) if r['name'] == 'cup')
        opening[stage] = [dict(name=r['name'], dtype=r['dtype'], words=r['words'])
            for r in records[:first_call] if r['storage'] == 'P' and r['offset'] == 12]
    memory, args = oracle.fixture(0, 1, 0)
    boundaries = []
    for phase in (0, 8):
        completed = [oracle.FaultOracle(w, memory, args, phase=phase).run() for w in (retail, words)]
        for cut in range(min(m.accesses for m in completed)):
            snapshots = []
            for w in (retail, words):
                model = oracle.FaultOracle(w, memory, args, phase=phase, fault=cut)
                try:
                    model.run()
                except oracle.AccessFault:
                    assert model.accesses == cut
                else:
                    raise AssertionError('Fault gate did not fire')
                snapshots.append(state(model))
            if snapshots[0] != snapshots[1]:
                boundaries.append(dict(phase=phase, first_difference=cut))
                break
    result = dict(meta=meta, changed_words=sum(a != b for a, b in zip(banked, words)),
        RAM=[models[0].memory == m.memory for m in models], FPR=[models[0].f == m.f for m in models],
        GPR=[[i for i in range(32) if models[0].r[i] != m.r[i]] for m in models],
        code_unchanged=observed['code_unchanged'],
        frames=[e for e in observed['events'] if e['event'] == 'frame-write'],
        definitions={stage: [dict(storage=r['storage'], length=r['length'])
            for r in observed['records'][stage] if r['name'] == 'def'] for stage in ('frontend', 'optimizer')},
        caches=[(r['offset'], r['words'][2]) for r in observed['records']['optimizer']
            if r['name'] == 'rlda' and r['storage'] == 'M'], opening_input_records=opening,
        boundaries=boundaries)
    (out / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-register-schedule'
    out.mkdir(exist_ok=True)
    if args.probe:
        probe(root, out)
        return
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), compiler.ROM))
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in ('o2g3', 'o2', 'o1g3', 'o1') if args.profiles else ('o2g3',):
            meta, words = compile_candidate(root, out, name + '-' + profile, body, profile)
            meta.update(prefix_words=next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b),
                min(len(words), len(retail))), opening_words=['%08X' % w for w in words[:23]])
            records.append(meta)
            print(name, profile, meta['body_words'], hex(meta['frame']), meta['differences'],
                'prefix', meta['prefix_words'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
