"""Recovered endpoint-quad frame and certified closed GPR allocation fitting."""
import argparse
import csv
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_endpoint_quad_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, ORIGINAL = recovery.FUNCTION, recovery.SOURCE, recovery.ORIGINAL
TYPES, DECLARATIONS, SYMBOLS = recovery.TYPES, recovery.DECLARATIONS, recovery.SYMBOLS
GEOMETRY = recovery.GEOMETRY.replace('nx = ny = nz = 0.0f;',
    'nx = 0.0f; ny = 0.0f; nz = 0.0f;')
LOCALS = '''    u8 *pair;
    u8 invalid;
    u8 sync;
    Vtx *cursor;
    OwnerQuadPosition2974 *origin;
    f32 dx, dy, dz, rx, ry, rz;
    f32 length;
    OwnerQuadPosition2974 first, second;
    f32 nx, ny, nz;
    u8 *matrix;
    f32 scale;
'''
_locals = recovery.SELECTED[recovery.SELECTED.index('    Vtx *cursor;'):
    recovery.SELECTED.index('\n    invalid =')]
SELECTED = recovery.SELECTED.replace(_locals, LOCALS).replace(
    recovery.GEOMETRY, GEOMETRY).replace(
    '*(u8 **)(*(u8 **)pair + 0x1D4) + (pair[5] << 6)',
    '(pair[5] << 6) + *(u8 **)(*(u8 **)pair + 0x1D4)').replace(
    'D_800A4AC8[11] | D_800A4AC8[10]', 'D_800A4AC8[10] | D_800A4AC8[11]').replace(
    '        origin =', '        sync = 1;\n        origin =').replace(
    '\n        sync = 1;\n        output =', '\n        output =')

VOLATILE = {1, 2, 3, *range(4, 16), 24, 25, 31}
MAPS = (
    (0x80, 0x84, {11: 12}),
    (0x1D8, 0x1FC, {12: 25, 24: 8, 13: 24}),
    (0x324, 0x53C, {8: 11, 25: 10, 11: 12, 10: 15, 12: 25,
        15: 14, 24: 8, 14: 9, 13: 24, 9: 13}),
)


def fields(word):
    """Only architectural GPR operand fields; FP fields are never renamed."""
    op, fn, fmt = word >> 26, word & 63, word >> 21 & 31
    if word == 0:
        return (), ()
    if op == 0:
        if fn in (0, 2, 3):
            return (16,), (11,)
        if fn in (33, 35, 37):
            return (21, 16), (11,)
        if fn == 8:
            return (21,), ()
    if op in (8, 9, 12, 13, 14):
        return (21,), (16,)
    if op == 15:
        return (), (16,)
    if op in (32, 33, 35, 36, 37):
        return (21,), (16,)
    if op in (40, 41, 43):
        return (21, 16), ()
    if op in (49, 57):
        return (21,), ()
    if op == 17:
        if fmt == 0:
            return (), (16,)
        if fmt == 4:
            return (16,), ()
        if fmt in (8, 16):
            return (), ()
    if op in (4, 5, 20, 21):
        return (21, 16), ()
    if op in (2, 3):
        return (), ()
    raise ValueError('unsupported proof word 0x%08X' % word)


def normalize(words):
    if len(words) != WORDS or words[0] != 0x27BDFF48:
        raise ValueError('complete 340-word/frame0xB8 body required')
    result = list(words)
    for begin, end, mapping in MAPS:
        for i in range(begin // 4, end // 4):
            reads, writes = fields(words[i])
            word = words[i]
            for shift in set(reads + writes):
                register = words[i] >> shift & 31
                word = (word & ~(31 << shift)) | (mapping.get(register, register) << shift)
            result[i] = word
    return result


def certify(words):
    """Compare symbolic operand provenance on every acyclic branch path.

    Each instruction result has the same token in both bodies only after all
    input tokens agree. Calls observe their ABI arguments after their delay
    slot, then independently clobber caller-saved registers. This proves the
    renamed temporaries do not escape into memory, branch decisions or calls.
    """
    fitted = normalize(words)
    offsets = [i * 4 for i, (a, b) in enumerate(zip(words, fitted)) if a != b]
    if len(offsets) != 84:
        raise ValueError('expected exactly84 allocation words')
    for i, (raw, new) in enumerate(zip(words, fitted)):
        reads, writes = fields(raw)
        mask = sum(31 << shift for shift in set(reads + writes))
        if raw & ~mask != new & ~mask or fields(raw) != fields(new):
            raise ValueError('non-register instruction bits changed at 0x%X' % (i * 4))

    initial = tuple(('incoming', i) for i in range(32))
    initial = (('zero',),) + initial[1:]
    pending = [(0, initial, initial, frozenset())]
    reached, paths, calls = set(), 0, 0

    def step(pc, a, b):
        raw, new = words[pc], fitted[pc]
        reads, destinations = fields(raw)
        for shift in reads:
            if a[raw >> shift & 31] != b[new >> shift & 31]:
                raise ValueError('live operand provenance mismatch at 0x%X' % (pc * 4))
        a, b = list(a), list(b)
        for shift in destinations:
            ra, rb = raw >> shift & 31, new >> shift & 31
            token = ('result', pc, shift)
            if ra:
                a[ra] = token
            if rb:
                b[rb] = token
        reached.add(pc)
        return tuple(a), tuple(b)

    while pending:
        pc, a, b, history = pending.pop()
        while True:
            if pc >= WORDS or pc in history:
                raise ValueError('out-of-body or cyclic proof path')
            history = history | {pc}
            word = words[pc]
            op = word >> 26
            a, b = step(pc, a, b)
            is_return = op == 0 and word & 63 == 8
            fp_branch = op == 17 and word >> 21 & 31 == 8
            if op in (2, 3, 4, 5, 20, 21) or is_return or fp_branch:
                if pc + 1 >= WORDS:
                    raise ValueError('missing delay word')
                if op in (4, 5, 20, 21) or fp_branch:
                    displacement = word & 65535
                    displacement = displacement if displacement < 32768 else displacement - 65536
                    target = pc + 1 + displacement
                    delayed_a, delayed_b = step(pc + 1, a, b)
                    if op == 4 and word >> 21 & 31 == 0 and word >> 16 & 31 == 0:
                        pc, a, b = target, delayed_a, delayed_b
                        continue
                    pending.append((target, delayed_a, delayed_b, history | {pc + 1}))
                    if op not in (20, 21):
                        a, b = delayed_a, delayed_b
                    pc += 2
                    continue
                a, b = step(pc + 1, a, b)
                if is_return:
                    if (word >> 21 & 31) != 31:
                        raise ValueError('non-RA return')
                    for reg in (2, 16, 17, 29, 31):
                        if a[reg] != b[reg]:
                            raise ValueError('escaped live return register')
                    paths += 1
                    break
                if op == 2:
                    raise ValueError('unexpected absolute jump')
                for reg in (4, 5, 6, 7, 29):
                    if a[reg] != b[reg]:
                        raise ValueError('escaped live helper argument')
                calls += 1
                a, b = list(a), list(b)
                for reg in VOLATILE:
                    a[reg] = b[reg] = ('helper-clobber', pc, reg)
                a, b = tuple(a), tuple(b)
                pc += 2
                continue
            pc += 1
    if reached != set(range(WORDS)) - {0xA0 // 4}:
        raise ValueError('unexpected proof coverage')
    return dict(offsets=offsets, paths=paths, helper_boundaries=calls,
        instruction_words_reached=len(reached), unreachable_duplicate=0xA0,
        all_operand_provenance_equal=True, memory_access_order_equal=True,
        ABI_arguments_and_preserved_returns_equal=True, FP_arithmetic_and_FP_operand_fields_unchanged=True,
        branch_targets_and_immediates_unchanged=True, retail_lookup=False)


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    return recovery.compile_candidate(root, out, name, body, profile)


def guard_rows(obj):
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    words = list(struct.unpack_from('>340I', text, function['value']))
    proof, fitted = certify(words), normalize(words)
    rows = []
    for offset in proof['offsets']:
        uses = relocations.get(function['value'] + offset, [])
        spec = ';'.join(kind + ':' + name for kind, name in uses) or '-'
        rows.append(dict(filename='generated_1DF510', function=FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % words[offset // 4], replacement='0x%08X' % fitted[offset // 4],
            expected_relocations=spec, replacement_relocations=spec,
            note='Normalize certified endpoint quad closed GPR allocation lifetimes',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-endpoint-quad-matching'
    records = []
    for profile in recovery.compiler.PROFILES if args.profiles else ('o2g3',):
        meta, words = compile_candidate(root, out, 'selected-' + profile, profile=profile)
        if profile == 'o2g3':
            meta['certificate'] = certify(words)
            guards = guard_rows(out / ('selected-' + profile + '.o'))
            stream = io.StringIO()
            csv.DictWriter(stream, fieldnames=list(guards[0]), lineterminator='\n').writerows(guards)
            (out / 'guards.csv').write_text(stream.getvalue())
        records.append(meta)
        print(profile, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
