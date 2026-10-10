"""Closed register/scheduling normalization for the complete point initializer."""
import csv
import io
import json
import struct
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_points_initializer_control as control
from tools.experiments.game_owner_ribbon_renderer_scheduling import add
from tools.pad_generated_object import parse_object

SELECTED, TYPES = control.SELECTED, control.TYPES
GPR_MAP = {5: 2, 3: 9, 6: 3, 7: 5, 10: 6, 9: 7, 11: 10}
# Every source offset occurs exactly once in each closed window.
SETUP = (0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C, 0x30, 0x34,
    0x08, 0x38, 0x40, 0x44, 0x48, 0xB0, 0x50, 0x54, 0x3C, 0x68, 0x60, 0x64,
    0x5C, 0x58, 0x70, 0x74, 0x78, 0x7C, 0x80, 0x88, 0x84, 0x8C, 0x90,
    0x94, 0x98, 0x9C, 0xA0, 0xA4, 0xA8, 0xAC, 0x6C, 0x4C)
LOOP = (0x128, 0x12C, 0x138, 0x13C, 0x148, 0x154, 0x150, 0x14C,
    0x158, 0x15C, 0x160, 0x164, 0x168, 0x16C, 0x170, 0x174, 0x178,
    0x17C, 0x120, 0x124, 0x180, 0x184, 0x130, 0x144, 0x188, 0x18C, 0x140, 0x134)
PERMUTATIONS = ((0x08, SETUP), (0x120, LOOP))
# Pointer folds use the same actor-relative values after moving their definitions.
ADDRESS_EDITS = {
    0x54: (0x24850078, 0x24650048), 0x58: (0x24A60018, 0x24660060),
    0x64: (0x24A70030, 0x24670078), 0x68: (0x24A80048, 0x24680090),
    0x128: (0xACADFFA4, 0xACAD0004), 0x130: (0xACA1FFA8, 0xACA10008),
    0x134: (0xE474FFF4, 0xE4740054), 0x138: (0xE474FFF8, 0xE4740058),
    0x13C: (0xE474FFFC, 0xE474005C), 0x170: (0xACC1FFA0, 0xACC10000),
}
SCRATCH_EDITS = {
    0x60: ((16, 13, 12),), 0x6C: ((16, 13, 12),),
    0xDC: ((16, 24, 14),), 0xE0: ((16, 24, 14),),
    0x124: ((16, 13, 25),), 0x128: ((16, 13, 25),),
    0x174: ((16, 24, 13),), 0x180: ((16, 24, 13),),
    0x1CC: ((16, 13, 24),), 0x1D0: ((16, 13, 24),),
    0x214: ((16, 24, 12),), 0x218: ((16, 24, 12),),
    0x258: ((16, 12, 13),), 0x260: ((21, 12, 13), (16, 25, 11)),
    0x264: ((16, 25, 11),),
}


def recipe(words):
    result = control.normalize(words)
    origins = [i * 4 for i in range(len(words)) if i * 4 != control.OMIT]
    for index, word in enumerate(result[:0x258 // 4]):
        inputs, outputs = control.fields(word)
        for shift in set(inputs + outputs):
            register = word >> shift & 31
            result[index] = (result[index] & ~(31 << shift)) | (GPR_MAP.get(register, register) << shift)
    before, sources = result.copy(), origins.copy()
    for begin, offsets in PERMUTATIONS:
        if sorted(offsets) != list(range(begin, begin + len(offsets) * 4, 4)):
            raise ValueError('window is not a complete instruction permutation')
        for index, offset in enumerate(offsets):
            result[begin // 4 + index] = before[offset // 4]
            origins[begin // 4 + index] = sources[offset // 4]
    for offset, (expected, replacement) in ADDRESS_EDITS.items():
        if result[offset // 4] != expected:
            raise ValueError('stale actor-relative address fold at0x%X' % offset)
        result[offset // 4] = replacement
    for offset, edits in SCRATCH_EDITS.items():
        inputs, outputs = control.fields(result[offset // 4])
        for shift, expected, replacement in edits:
            if shift not in inputs + outputs or result[offset // 4] >> shift & 31 != expected:
                raise ValueError('stale scratch lifetime at0x%X' % offset)
            result[offset // 4] = (result[offset // 4] & ~(31 << shift)) | (replacement << shift)
    return result, origins


def execute(words, actor=('actor',)):
    """Exact bit-expression model for this complete, closed, two-pass routine.

    The private frame is disjoint from live public objects. Memory is byte-addressed;
    ordered FP operand expressions and all final bytes are compared, not host floats.
    Concrete actor views also exercise every aligned scale/output overlap.
    """
    gp = [0] + [('incoming-GPR', i) for i in range(1, 32)]
    fp = [('incoming-FP', i) for i in range(32)]
    gp[4], gp[29] = actor, ('private-SP',)
    initial_gp, initial_fp = gp.copy(), fp.copy()
    memory, reads, writes, reached, branches = {}, [], [], set(), []

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

    def instruction(offset):
        reached.add(offset)
        word = words[offset // 4]
        op, rs, rt, rd, sa, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        immediate = word & 65535
        signed = immediate if immediate < 32768 else immediate - 65536
        if word == 0:
            return
        if op == 9:
            gp[rt] = add(gp[rs], signed & 0xFFFFFFFF)
        elif op == 15:
            gp[rt] = immediate << 16
        elif op == 12:
            gp[rt] = gp[rs] & immediate if isinstance(gp[rs], int) else ('and', gp[rs], immediate)
        elif op == 0 and fn == 42:
            if not all(isinstance(gp[r], int) and gp[r] < 0x80000000 for r in (rs, rt)):
                raise ValueError('unproved signed comparison')
            gp[rd] = int(gp[rs] < gp[rt])
        elif op in (35, 36, 49, 53):
            value = load(add(gp[rs], signed & 0xFFFFFFFF), 8 if op == 53 else 1 if op == 36 else 4)
            if op == 53:
                if not isinstance(value, tuple) or value[0] != 'saved-FP-pair':
                    raise ValueError('unproved saved-FP reload')
                fp[rt:rt + 2] = value[1:]
            elif op == 49:
                fp[rt] = value
            else:
                gp[rt] = value
        elif op in (40, 43, 57, 61):
            value = ('saved-FP-pair', *fp[rt:rt + 2]) if op == 61 else fp[rt] if op == 57 else gp[rt]
            store(add(gp[rs], signed & 0xFFFFFFFF), value, 8 if op == 61 else 1 if op == 40 else 4)
        elif op == 17 and rs == 4:
            fp[rd] = gp[rt]
        elif op == 17 and rs == 16 and fn in (0, 1, 2):
            fp[sa] = ('FP-bits-operation', fn, fp[rd], fp[rt])
        else:
            raise ValueError('unsupported closed-proof instruction0x%08X' % word)
        gp[0] = 0

    pc = 0
    for _ in range(1000):
        word = words[pc // 4]
        if word >> 26 == 5:
            reached.add(pc)
            rs, rt = word >> 21 & 31, word >> 16 & 31
            if not isinstance(gp[rs], int) or not isinstance(gp[rt], int):
                raise ValueError('unproved branch inputs')
            take = gp[rs] != gp[rt]
            branches.append((take, control.branch_target(pc, word)))
            instruction(pc + 4)
            pc = control.branch_target(pc, word) if take else pc + 8
        elif word == 0x03E00008:
            reached.add(pc)
            instruction(pc + 4)
            if gp[29] != initial_gp[29] or fp[20:] != initial_fp[20:]:
                raise ValueError('saved frame/FP state changed')
            return dict(memory=memory, reads=Counter(reads), writes=Counter(writes), reached=reached,
                branches=branches, public_return=gp[2], saved_GP=tuple(gp[r] for r in (*range(16, 24), 28, 29, 30, 31)),
                final_FP=tuple(fp))
        else:
            instruction(pc)
            pc += 4
    raise ValueError('closed proof instruction budget exhausted')


def certify(words):
    induction = control.certify(words)
    fitted, _ = recipe(words)
    actors = [('actor',)] + [0x800AA394 - offset for offset in range(0x48, 0x138, 4)]
    for actor in actors:
        old, new = execute(words, actor), execute(fitted, actor)
        for key in ('memory', 'reads', 'writes', 'branches', 'public_return', 'saved_GP', 'final_FP'):
            if old[key] != new[key]:
                raise ValueError('complete symbolic %s differs for actor%s' % (key, repr(actor)))
        if old['reached'] != set(range(0, 158 * 4, 4)) or new['reached'] != set(range(0, 157 * 4, 4)):
            raise ValueError('complete symbolic word coverage missing')
    return dict(induction=induction, complete_symbolic_actor_views=len(actors),
        exact_byte_memory_and_ordered_FP_expressions=True, read_write_multisets_equal=True,
        complete_word_coverage=True, saved_registers_and_return_equal=True,
        memory_access_and_FP_exception_order_not_claimed=True)


def normalize(words):
    certify(words)
    return recipe(words)[0]


def guard_rows(object_path):
    text, functions, relocations = parse_object(object_path)
    target = functions['func_151B3A7C']
    words = list(struct.unpack_from('>158I', text, target['value']))
    fitted = normalize(words)
    _, origins = recipe(words)
    rows = []
    for raw_offset in range(0, 158 * 4, 4):
        omitted = raw_offset == control.OMIT
        destination = raw_offset if raw_offset < control.OMIT else raw_offset - 4
        replacement = words[raw_offset // 4] if omitted else fitted[destination // 4]
        expected_relocations = relocations.get(target['value'] + raw_offset, [])
        replacement_relocations = [] if omitted else relocations.get(target['value'] + origins[destination // 4], [])
        if omitted and expected_relocations:
            raise ValueError('cannot omit a relocated control word')
        if not omitted and replacement == words[raw_offset // 4] and expected_relocations == replacement_relocations:
            continue
        spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
        rows.append(dict(filename='generated_1E0560', function='func_151B3A7C', offset='0x%03X' % raw_offset,
            expected='0x%08X' % words[raw_offset // 4], replacement='0x%08X' % replacement,
            expected_relocations=spec(expected_relocations), replacement_relocations=spec(replacement_relocations),
            note='Normalize certified point initializer allocation scheduling and direct exit',
            insert_after='', insert_after_relocations='', omit=str(omitted).lower()))
    return rows


def compile_candidate(root, out, name, body=None, profile='o2g3', symbols=None):
    meta, words = control.source.compile_candidate(root, out, name, SELECTED if body is None else body, profile, symbols)
    fitted = normalize(words)
    retail = struct.unpack_from('>157I', (root / 'conker/conker.us.bin').read_bytes(), control.source.fitting.base.ROM)
    return dict(meta, raw_body_words=158, raw_differences=meta['differences'], body_words=157,
        differences=sum(a != b for a, b in zip(fitted, retail))), fitted


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-initializer-matching'
    meta, words = compile_candidate(root, out, 'selected')
    _, raw = control.source.compile_candidate(root, out, 'raw-selected')
    meta['certificate'] = certify(raw)
    rows = guard_rows(out / 'selected.o')
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    (out / 'guards.csv').write_text(stream.getvalue())
    (out / 'measurement.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
