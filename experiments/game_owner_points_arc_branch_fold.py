"""Certify shared arc branch definitions; do not drop live FP values to fit a slot."""
import csv
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_points_arc_endpoint_reads as source
from tools.experiments.game_owner_points_initializer_control import branch_target
from tools.pad_generated_object import parse_object

SELECTED, TYPES, DELTA_TYPE, base = source.SELECTED, source.TYPES, source.DELTA_TYPE, source.base
OMIT = (0x74, 0x90)
WINDOW = {
    0x6C: 0x45030008, 0x70: 0x44813000, 0x74: 0x4618D001,
    0x78: 0x46000005, 0x7C: 0x4600603C, 0x80: 0,
    0x84: 0x45020061, 0x88: 0x24020001, 0x8C: 0x44813000,
    0x90: 0x4618D081,
}


def branch(word):
    return word >> 26 in (4, 5) or (word >> 26 == 17 and word >> 21 & 31 == 8)


def recipe(words):
    if len(words) != 144 or words[0] != 0x27BDFF78:
        raise ValueError('expected complete 144-word arc with original frame')
    for offset, expected in WINDOW.items():
        if words[offset // 4] != expected:
            raise ValueError('stale arc branch definition at0x%X' % offset)
    origins = [offset for offset in range(0, len(words) * 4, 4) if offset not in OMIT]
    positions = {offset: index * 4 for index, offset in enumerate(origins)}
    result = []
    for old_pc in origins:
        word = words[old_pc // 4]
        if old_pc == 0x70:
            word = words[0x90 // 4]
        elif old_pc == 0x78:
            word = (word & ~(31 << 11)) | (2 << 11)
        if branch(word):
            target = 0x8C if old_pc == 0x6C else branch_target(old_pc, word)
            if target not in positions:
                raise ValueError('branch enters removed definition')
            if old_pc == 0x6C:
                word &= ~(2 << 16)
            displacement = (positions[target] - positions[old_pc] - 4) // 4
            if not -32768 <= displacement < 32768:
                raise ValueError('folded branch out of range')
            word = (word & 0xFFFF0000) | (displacement & 65535)
        result.append(word)
    origins[positions[0x70] // 4] = 0x90
    return result, origins


def execute_window(words, first_true, second_true, folded=False):
    """Compare exact ordered FP expressions on all three short-circuit paths."""
    fp = [('incoming-FP', i) for i in range(32)]
    gp = [('incoming-GPR', i) for i in range(32)]
    gp[0], gp[1] = 0, ('unchanged-AT-half-bits',)
    flag, flag_expression = first_true, ('initial-X-condition', first_true)
    visited, branches = [], []
    end, exit_pc = (0x8C, 0x204) if folded else (0x94, 0x20C)

    def instruction(pc):
        nonlocal flag, flag_expression
        visited.append(pc)
        word = words[pc // 4]
        op, rs, rt, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if word == 0:
            return
        if op == 17 and rs == 4:
            fp[fs] = ('mtc1-bits', gp[rt])
        elif op == 17 and rs == 16 and fn == 1:
            fp[fd] = ('ordered-sub.s-bits', fp[fs], fp[rt])
        elif op == 17 and rs == 16 and fn == 5:
            fp[fd] = ('abs.s-bits', fp[fs])
        elif op == 17 and rs == 16 and fn == 60:
            flag_expression = ('ordered-c.lt.s', fp[fs], fp[rt])
            flag = second_true
        elif word == 0x24020001:
            gp[2] = 1
        else:
            raise ValueError('unsupported branch-fold proof word')

    pc = 0x6C
    for _ in range(32):
        if pc in (end, exit_pc):
            return dict(join='active' if pc == end else 'return', gp=gp, fp=fp,
                flag=flag, flag_expression=flag_expression, branches=branches, visited=visited)
        word = words[pc // 4]
        if word >> 26 == 17 and word >> 21 & 31 == 8:
            visited.append(pc)
            rt = word >> 16 & 31
            take = flag == bool(rt & 1)
            branches.append(take)
            if take or not rt & 2:
                instruction(pc + 4)
            pc = branch_target(pc, word) if take else pc + 8
        else:
            instruction(pc)
            pc += 4
    raise ValueError('branch-fold proof instruction budget exhausted')


def certify(words):
    folded, _ = recipe(words)
    paths = []
    for first, second in ((True, False), (False, True), (False, False)):
        old = execute_window(words, first, second)
        new = execute_window(folded, first, second, folded=True)
        for key in ('join', 'gp', 'flag', 'flag_expression', 'branches'):
            if old[key] != new[key]:
                raise ValueError('branch-fold symbolic ' + key + ' changed')
        live = list(range(32)) if old['join'] == 'active' else [i for i in range(32) if i != 2]
        if any(old['fp'][i] != new['fp'][i] for i in live):
            raise ValueError('branch-fold live FP bits changed')
        paths.append(dict(first_true=first, second_true=second, join=old['join'],
            all_GP_and_branch_predicates_equal=True, live_FP_registers=len(live)))
    if folded[0x70 // 4] != words[0x90 // 4] or folded[0x88 // 4] != words[0x8C // 4]:
        raise ValueError('required Z delta or half definition lost')
    return dict(symbolic_paths=paths, exact_ordered_FP_value_expressions=True,
        required_Z_delta_hoisted_not_deleted=True, shared_half_definition_retained=True,
        early_exit_only_dead_caller_FP2_may_differ=True, frame_or_extent_not_blindly_patched=True,
        raw_words=144, folded_words=142, memory_access_and_FP_exception_order_not_claimed=True)


def normalize(words):
    certify(words)
    return recipe(words)[0]


def guard_rows(object_path):
    text, functions, relocations = parse_object(object_path)
    target = functions[base.FUNCTION]
    if target['size'] != 144 * 4:
        raise ValueError('expected complete 144-word arc object extent')
    words = list(struct.unpack_from('>144I', text, target['value']))
    fitted = normalize(words)
    rows, destination = [], 0
    for offset in range(0, len(words) * 4, 4):
        uses = relocations.get(target['value'] + offset, [])
        if offset in WINDOW and uses:
            raise ValueError('relocated branch-fold window unsupported')
        omitted = offset in OMIT
        replacement = words[offset // 4] if omitted else fitted[destination]
        if offset in WINDOW or omitted or replacement != words[offset // 4]:
            if uses:
                raise ValueError('cannot rewrite relocated word')
            rows.append(dict(filename='generated_1E0560', function=base.FUNCTION, offset='0x%03X' % offset,
                expected='0x%08X' % words[offset // 4], replacement='0x%08X' % replacement,
                expected_relocations='-', replacement_relocations='-',
                note='Normalize certified shared arc Z delta and half definitions',
                insert_after='', insert_after_relocations='', omit=str(omitted).lower()))
        if not omitted:
            destination += 1
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None):
    meta, raw = source.compile_candidate(root, out, name, body, profile, symbols)
    fitted = normalize(raw)
    _, origins = recipe(raw)
    raw_relocations = meta['relocations']
    relocations = {index * 4: raw_relocations[origin] for index, origin in enumerate(origins)
        if origin in raw_relocations}
    original = struct.unpack_from('>142I', (root / 'conker/conker.us.bin').read_bytes(), base.ROM)
    return dict(meta, raw_body_words=meta['body_words'], raw_differences=meta['differences'],
        raw_relocations=raw_relocations, relocations=relocations,
        body_words=len(fitted), differences=sum(a != b for a, b in zip(fitted, original))), fitted


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-arc-branch-fold'
    meta, words = compile_candidate(root, out, 'folded')
    _, raw = source.compile_candidate(root, out, 'raw', SELECTED)
    meta['certificate'] = certify(raw)
    rows = guard_rows(out / 'folded.o')
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    (out / 'guards.csv').write_text(stream.getvalue())
    (out / 'measurement.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
