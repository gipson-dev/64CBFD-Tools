"""Closed arc instruction scheduling and register roles over the complete C body."""
import csv
import io
import json
import struct
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_points_arc_branch_fold as control
from tools.experiments.game_owner_ribbon_renderer_scheduling import add, private_offset
from tools.pad_generated_object import parse_object

SELECTED, TYPES, DELTA_TYPE, base = control.SELECTED, control.TYPES, control.DELTA_TYPE, control.base
source = control.source
PERMUTATIONS = (
    (0, (0, 4, 0x3C, 0x40, 8, 0xC, 0x10, 0x14, 0x18, 0x1C,
        0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38, 0x48, 0x4C, 0x44,
        0x60, 0x58, 0x54, 0x68, 0x64, 0x5C, 0x50, 0x6C, 0x70, 0x74,
        0x78, 0x7C, 0x80, 0x84, 0x88)),
    (0x8C, (0xAC, 0x94, 0x8C, 0x90, 0xB0, 0xB8, 0xBC, 0x9C, 0xD0,
        0x98, 0xB4, 0xA4, 0xDC, 0xC4, 0xA0, 0xE4, 0xE8, 0xA8, 0xC8,
        0xF0, 0xD8, 0xC0, 0xD4, 0xE0, 0xF4, 0xCC, 0xF8, 0xEC, 0x100,
        0x104, 0x108, 0xFC, 0x10C, 0x110, 0x114, 0x118, 0x11C, 0x120,
        0x124, 0x128, 0x12C, 0x130, 0x134, 0x138, 0x13C, 0x140, 0x148,
        0x144, 0x14C, 0x150, 0x154, 0x158, 0x15C)),
    (0x160, (0x160, 0x164, 0x168, 0x16C, 0x170, 0x174, 0x178, 0x17C,
        0x180, 0x18C, 0x188, 0x184, 0x190, 0x194, 0x198, 0x19C, 0x1A0)),
    (0x1CC, (0x1D0, 0x1D4, 0x1D8, 0x1DC, 0x1E0, 0x1E4, 0x1E8,
        0x1EC, 0x1F0, 0x1F4, 0x1FC, 0x1F8, 0x1CC)),
)
# Destination offset: expected raw FP fields -> retail-role fields. Arithmetic
# tuples are (fd, fs, ft); unary tuples omit ft; transfers use their FP field.
FP_ROLES = {
    0x0C: (12, 16), 0x3C: (28, 26), 0x40: (22, 2), 0x44: (30, 28),
    0x48: (20, 12), 0x4C: ((18, 28, 22), (18, 26, 2)),
    0x54: ((4, 30, 20), (4, 28, 12)), 0x60: ((12, 0), (16, 0)),
    0x64: (24, 14), 0x68: (26, 30), 0x70: ((2, 26, 24), (20, 30, 14)),
    0x74: ((0, 2), (0, 20)), 0x78: ((12, 0), (16, 0)),
    0x8C: (6, 10), 0x90: (8, 4),
    0x98: ((12, 8, 22), (16, 2, 8)), 0x9C: ((10, 6, 8), (6, 10, 4)),
    0xA0: (10, 8), 0xA8: (12, 16), 0xAC: ((6, 2, 10), (10, 20, 8)),
    0xB0: ((10, 22, 12), (4, 2, 16)), 0xB4: ((4, 10, 20), (22, 12, 6)),
    0xB8: (10, 4), 0xBC: ((14, 6, 24), (24, 14, 10)), 0xC0: (4, 22),
    0xC4: ((4, 28, 12), (10, 26, 16)), 0xC8: (14, 24),
    0xCC: ((4, 24, 14), (8, 14, 24)), 0xD0: (4, 10),
    0xD4: ((8, 30, 4), (4, 28, 22)), 0xD8: (4, 8),
    0xDC: ((10, 18, 18), (8, 18, 18)), 0xE0: ((6, 20, 4), (6, 12, 22)),
    0xE4: (8, 4), 0xE8: ((6, 2, 2), (10, 20, 20)),
    0xF4: ((8, 26, 14), (6, 30, 24)), 0xF8: ((0, 10, 6), (0, 8, 10)),
    0xFC: (8, 6), 0x100: (8, 6), 0x104: (6, 10),
    0x10C: ((16, 4, 0), (22, 4, 0)), 0x110: ((28, 2, 16), (26, 20, 22)),
    0x118: ((30, 18, 16), (28, 18, 22)),
    0x120: ((10, 8, 28), (8, 6, 26)), 0x128: ((4, 6, 30), (4, 10, 28)),
    0x12C: (6, 10), 0x130: ((8, 10, 4), (6, 8, 4)),
    0x134: ((10, 6, 28), (8, 10, 26)), 0x13C: ((6, 4, 30), (10, 4, 28)),
    0x140: ((4, 10, 6), (4, 8, 10)), 0x144: (6, 10), 0x148: (10, 8),
    0x14C: ((26, 8, 4), (14, 6, 4)), 0x150: ((24, 10, 6), (24, 8, 10)),
    0x154: ((14, 26), (30, 14)), 0x160: ((8, 26, 26), (6, 30, 30)),
    0x164: ((20, 0), (2, 0)), 0x170: (10, 8), 0x178: (6, 10), 0x180: (26, 30),
    0x188: ((0, 8, 4), (0, 6, 4)), 0x194: ((20, 20, 6), (20, 2, 10)),
    0x19C: ((22, 0, 10), (22, 0, 8)),
    0x1BC: ((2, 0, 22), (2, 22, 0)), 0x1CC: ((8, 2, 30), (6, 2, 28)),
    0x1D0: ((10, 8, 4), (8, 6, 4)), 0x1D4: ((6, 22, 24), (10, 22, 24)),
    0x1D8: (10, 8), 0x1DC: (8, 6), 0x1E0: ((10, 2, 28), (8, 2, 26)),
    0x1E4: ((4, 6, 8), (4, 10, 6)), 0x1EC: (6, 10),
    0x1F0: ((8, 10, 6), (6, 8, 10)), 0x1F4: (8, 6),
    0x1FC: ((20, 20, 26), (20, 20, 30)),
}
GPR_ROLES = {0x184: ((11, 18, 17),), 0x18C: ((16, 17, 18),),
    0x1A4: ((21, 17, 18),), 0x1C4: ((21, 18, 17), (16, 18, 17)),
    0x1C8: ((21, 17, 18), (16, 17, 18)), 0x1F8: ((21, 18, 17),)}


def fp_fields(word):
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op in (49, 57):
        return (16,)
    if op == 17 and rs == 4:
        return (11,)
    if op == 17 and rs == 16:
        if fn == 60:
            return (11, 16)
        return (6, 11) if fn in (4, 5, 6) else (6, 11, 16)
    raise ValueError('unexpected FP-role instruction')


def recipe(words):
    result, origins = control.recipe(words)
    before, sources = result.copy(), origins.copy()
    for begin, offsets in PERMUTATIONS:
        if sorted(offsets) != list(range(begin, begin + len(offsets) * 4, 4)):
            raise ValueError('arc scheduling window is not a complete permutation')
        for index, offset in enumerate(offsets):
            result[begin // 4 + index] = before[offset // 4]
            origins[begin // 4 + index] = sources[offset // 4]
    for offset, (expected, replacement) in FP_ROLES.items():
        shifts = fp_fields(result[offset // 4])
        expected = (expected,) if isinstance(expected, int) else expected
        replacement = (replacement,) if isinstance(replacement, int) else replacement
        if len(shifts) != len(expected) or tuple(result[offset // 4] >> s & 31 for s in shifts) != expected:
            raise ValueError('stale arc FP roles at0x%X' % offset)
        for shift, register in zip(shifts, replacement):
            result[offset // 4] = (result[offset // 4] & ~(31 << shift)) | (register << shift)
    for offset, edits in GPR_ROLES.items():
        for shift, expected, replacement in edits:
            if result[offset // 4] >> shift & 31 != expected:
                raise ValueError('stale arc GP role at0x%X' % offset)
            result[offset // 4] = (result[offset // 4] & ~(31 << shift)) | (replacement << shift)
    return result, origins


def execute(words, first_true, second_true):
    """Full symbolic memory/ABI/helper contract, with commutative FP add/multiply.

    This proves the value-expression contract, not NaN payload, FCSR/trap or
    memory access ordering. Numeric guest qualification and exact linked bytes
    are separate gates. The actor and private frame are disjoint.
    """
    gp = [0] + [('incoming-GP', i) for i in range(1, 32)]
    fp = [('incoming-FP', i) for i in range(32)]
    gp[4], gp[29] = ('actor',), ('private-SP',)
    memory, reads, writes, calls, branches, visited = {}, [], [], [], [], set()
    flag, condition = first_true, None
    comparisons = 0

    def load(address, size):
        reads.append((address, size))
        chunks = [memory.get(add(address, i), ('initial-byte', add(address, i))) for i in range(size)]
        if all(isinstance(c, tuple) and len(c) == 4 and c[0] == 'stored-byte' for c in chunks):
            value = chunks[0][1]
            if chunks == [('stored-byte', value, size, i) for i in range(size)]:
                return value
        return ('bytes', tuple(chunks))

    def store(address, value, size):
        writes.append((address, size, value))
        for i in range(size):
            memory[add(address, i)] = ('stored-byte', value, size, i)

    def instruction(pc):
        nonlocal flag, condition, comparisons
        visited.add(pc)
        w = words[pc // 4]
        op, rs, rt, fs, fd, fn = w >> 26, w >> 21 & 31, w >> 16 & 31, w >> 11 & 31, w >> 6 & 31, w & 63
        signed = (w & 65535) - (65536 if w & 32768 else 0)
        if w == 0:
            return
        if op == 9:
            gp[rt] = add(gp[rs], signed & 0xFFFFFFFF)
        elif op == 15:
            gp[rt] = (w & 65535) << 16
        elif op == 0 and fn == 37:
            if gp[rt] != 0 and gp[rs] != 0:
                raise ValueError('unexpected non-move OR')
            gp[fs] = gp[rs] if gp[rt] == 0 else gp[rt]
        elif op in (35, 49, 53):
            value = load(add(gp[rs], signed & 0xFFFFFFFF), 8 if op == 53 else 4)
            if op == 53:
                if value[0] != 'saved-FP-pair':
                    raise ValueError('invalid saved-FP reload')
                fp[rt:rt + 2] = value[1:]
            elif op == 49:
                fp[rt] = value
            else:
                gp[rt] = value
        elif op in (43, 57, 61):
            value = ('saved-FP-pair', *fp[rt:rt + 2]) if op == 61 else fp[rt] if op == 57 else gp[rt]
            store(add(gp[rs], signed & 0xFFFFFFFF), value, 8 if op == 61 else 4)
        elif op == 17 and rs == 4:
            fp[fs] = ('f32-bits', gp[rt])
        elif op == 17 and rs == 16 and fn in (0, 1, 2, 3, 4, 5, 6):
            args = (fp[fs],) if fn in (4, 5, 6) else (fp[fs], fp[rt])
            if fn in (0, 2):
                args = tuple(sorted(args, key=repr))
            fp[fd] = fp[fs] if fn == 6 else ('FP-expression', fn, *args)
        elif op == 17 and rs == 16 and fn == 60:
            condition = (fp[fs], fp[rt])
            comparisons += 1
            flag = first_true if comparisons == 1 else second_true
        else:
            raise ValueError('unsupported arc proof word0x%08X' % w)
        gp[0] = 0

    pc = 0
    for _ in range(1000):
        w = words[pc // 4]
        op, rs, rt = w >> 26, w >> 21 & 31, w >> 16 & 31
        if op == 17 and rs == 8:
            visited.add(pc)
            take = flag == bool(rt & 1)
            branches.append(('FP', condition, take))
            if take or not rt & 2:
                instruction(pc + 4)
            pc = control.branch_target(pc, w) if take else pc + 8
        elif op == 5:
            visited.add(pc)
            if not isinstance(gp[rs], int) or not isinstance(gp[rt], int):
                raise ValueError('unproved arc counter')
            take = gp[rs] != gp[rt]
            branches.append(('GP', gp[rs], gp[rt], take))
            instruction(pc + 4)
            pc = control.branch_target(pc, w) if take else pc + 8
        elif op == 3:
            visited.add(pc)
            instruction(pc + 4)
            args = (fp[12], fp[14]) if pc == 0x158 else (fp[12],)
            kind = {0x158: 'angle', 0x1A8: 'sin', 0x1B4: 'cos'}[pc]
            call = (kind, w & 0x3FFFFFF, args)
            calls.append(call)
            for register in (*range(1, 16), 24, 25, 31):
                gp[register] = ('call-GP', len(calls), register)
            for register in range(20):
                fp[register] = ('call-FP', len(calls), register)
            fp[0] = ('helper-f32-response', len(calls), call)
            pc += 8
        elif w == 0x03E00008:
            visited.add(pc)
            instruction(pc + 4)
            return dict(memory=memory, reads=Counter(reads), writes=Counter(writes),
                public_writes=[event for event in writes if private_offset(event[0]) is None],
                calls=calls, branches=branches, return_value=gp[2],
                saved_GP=tuple(gp[r] for r in (*range(16, 24), 28, 29, 30, 31)),
                saved_FP=tuple(fp[20:]), reached=visited)
        else:
            instruction(pc)
            pc += 4
    raise ValueError('arc symbolic budget exhausted')


def certify(words):
    branch_certificate = control.certify(words)
    before, after = control.normalize(words), recipe(words)[0]
    reached = [set(), set()]
    paths = []
    for first, second in ((True, False), (False, True), (False, False)):
        old, new = execute(before, first, second), execute(after, first, second)
        for key in ('memory', 'reads', 'writes', 'public_writes', 'calls', 'branches',
                'return_value', 'saved_GP', 'saved_FP'):
            if old[key] != new[key]:
                raise ValueError('arc symbolic ' + key + ' changed')
        for coverage, model in zip(reached, (old, new)):
            coverage.update(model['reached'])
        paths.append(dict(first_true=first, second_true=second, helper_calls=len(old['calls']),
            public_writes=len(old['public_writes']), full_memory_and_ABI_equal=True))
    if any(coverage != set(range(0, 142 * 4, 4)) for coverage in reached):
        raise ValueError('arc symbolic coverage incomplete')
    return dict(branch_certificate=branch_certificate, symbolic_paths=paths, all_142_words_reached=True,
        exact_ordered_helper_arguments_and_public_writes=True,
        FP_add_multiply_commutation_only=True, NaN_payload_FCSR_and_access_order_not_claimed=True)


def normalize(words):
    certify(words)
    return recipe(words)[0]


def guard_rows(object_path):
    text, functions, relocations = parse_object(object_path)
    target = functions[base.FUNCTION]
    if target['size'] != 144 * 4:
        raise ValueError('expected complete 144-word arc extent')
    words = list(struct.unpack_from('>144I', text, target['value']))
    fitted = normalize(words)
    _, origins = recipe(words)
    rows, destination = [], 0
    for offset in range(0, 144 * 4, 4):
        omitted = offset in control.OMIT
        original_uses = relocations.get(target['value'] + offset, [])
        uses = [] if omitted else relocations.get(target['value'] + origins[destination], [])
        spec = lambda group: ';'.join(kind + ':' + symbol for kind, symbol in group) or '-'
        rows.append(dict(filename='generated_1E0560', function=base.FUNCTION, offset='0x%03X' % offset,
            expected='0x%08X' % words[offset // 4],
            replacement='0x%08X' % (words[offset // 4] if omitted else fitted[destination]),
            expected_relocations=spec(original_uses), replacement_relocations=spec(uses),
            note='Normalize certified complete arc register roles and scheduling',
            insert_after='', insert_after_relocations='', omit=str(omitted).lower()))
        if not omitted:
            destination += 1
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None):
    meta, raw = control.source.compile_candidate(root, out, name, body, profile, symbols)
    fitted, origins = recipe(raw)
    certify(raw)
    original = struct.unpack_from('>142I', (root / 'conker/conker.us.bin').read_bytes(), base.ROM)
    rels = meta['relocations']
    return dict(meta, raw_body_words=144, raw_differences=meta['differences'], raw_relocations=rels,
        relocations={i * 4: rels[o] for i, o in enumerate(origins) if o in rels},
        body_words=142, differences=sum(a != b for a, b in zip(fitted, original))), fitted


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-matching'
    meta, _ = compile_candidate(root, out, 'raw-selected')
    raw = list(struct.unpack_from('>144I', parse_object(out / 'raw-selected.o')[0]))
    meta['certificate'] = certify(raw)
    rows = guard_rows(out / 'raw-selected.o')
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    (out / 'guards.csv').write_text(stream.getvalue())
    (out / 'measurement.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
