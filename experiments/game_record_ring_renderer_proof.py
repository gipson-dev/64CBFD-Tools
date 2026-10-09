"""Target-only ribbon live-value congruence, not a numeric or hardware proof."""

import json
import struct
from collections import deque
from pathlib import Path

from tools.experiments import game_record_ring_renderer_candidates as screen

# Paired GP/FP files, HI/LO/condition, then immutable entry S2/S3 anchors.
N = 136
ANCHORS = {18: 134, 19: 135}
CALL_ARITIES = (
    ('func_151D5D60', 5), ('func_15142E24', 11), ('func_15142B7C', 3),
    ('func_1513F4E4', 3), ('func_15142FBC', 4), ('memcpy', 3))


def canonical(labels):
    ids = {}
    return tuple(ids.setdefault(value, len(ids)) for value in labels)


def initial():
    labels = list(range(N))
    for reg in range(32):
        labels[32 + reg] = labels[reg]
        labels[96 + reg] = labels[64 + reg]
    for left, right in ((128, 129), (130, 131), (132, 133)):
        labels[right] = labels[left]
    for reg, anchor in ANCHORS.items():
        labels[anchor] = labels[reg]
    return canonical(labels)


def meet(left, right):
    return canonical(zip(left, right))


def factor_order(words):
    expected = (0x15E00003, 0x4600540D, 0x10000006, 0x240300FF,
        0x8683001C, 0x0003C880, 0x0323C823, 0x0019C880, 0x332300FF)
    start = 0x278 // 4
    if tuple(words[start:start + 9]) != expected:
        raise ValueError('stale complete factor block')
    result = list(words)
    source = words[start:start + 9]
    # Predicate, both arms and the unconditional branch delay form one block.
    result[start:start + 9] = [(source[0] & ~((63 << 26) | 65535)) | (4 << 26) | 7, source[1],
        source[4], source[5], source[6], source[7], (source[2] & ~65535) | 2,
        source[8], source[3]]
    return result


def gp_mask(word):
    """Mask only the target's actually decoded GP operands, never reserved bits."""
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0:
        return {0: 0x001FF800, 3: 0x001FF800, 8: 0x03E00000,
            18: 0x0000F800, 25: 0x03FF0000, 33: 0x03FFF800,
            35: 0x03FFF800, 37: 0x03FFF800}.get(fn, 0)
    if op in (1, 6, 7, 22, 23, 49, 53, 57, 61):
        return 0x03E00000
    if op == 17 and rs in (0, 4):
        return 0x001F0000
    if op == 15:
        return 0x001F0000
    if op in (4, 5, 9, 10, 12, 13, 20, 21, 32, 33, 35, 36, 37, 40, 41, 43):
        return 0x03FF0000
    return 0


def check_save_window(raw, target):
    """The two private entry saves commute only across this closed store window."""
    for words in (raw, target):
        for pc in range(0x14, 0x38, 4):
            word = words[pc // 4]
            op, rs = word >> 26, word >> 21 & 31
            if pc in (0x14, 0x34):
                continue
            if op == 43 and rs == 29:
                offset = word & 65535
                if any(offset <= byte < offset + 4 for byte in range(0x50, 0x58)):
                    raise ValueError('overlapping private save window +0x%X' % pc)
            elif op == 0 and word & 63 == 37 and word >> 11 & 31 != 29:
                continue
            else:
                raise ValueError('non-commuting private save window +0x%X' % pc)


class Proof:
    def __init__(self, words, retail, entry=screen.ENTRY, symbols=None):
        self.raw, self.target = factor_order(words), list(retail)
        if len(words) != 405 or len(retail) != 405:
            raise ValueError('wrong complete extent')
        self.entry = entry
        symbols = screen.SYMBOLS if symbols is None else symbols
        self.arities = {symbols[name]: count for name, count in CALL_ARITIES}
        check_save_window(self.raw, self.target)
        for index, (a, b) in enumerate(zip(self.raw, self.target)):
            if index * 4 in (0x14, 0x34):
                continue
            mask = gp_mask(a)
            if mask != gp_mask(b) or a & ~mask != b & ~mask:
                raise ValueError('non-GP structural mismatch +0x%X' % (index * 4))
        self.obligations, self.visited, self.calls = [], set(), set()

    def require(self, state, left, right, pc, reason, checking):
        if checking:
            self.obligations.append((pc, reason, left, right))
            if state[left] != state[right]:
                raise ValueError('live input mismatch +0x%X %s: %d != %d' %
                    (pc, reason, left, right))
        return state[left] == state[right]

    @staticmethod
    def write(state, left, right, equal=True, copy=None):
        state = list(state)
        if copy is None:
            fresh = max(state) + 1
            if left not in (0, 32):
                state[left] = fresh
            if right not in (0, 32):
                state[right] = fresh if equal else fresh + 1
        else:
            old = tuple(state)
            if left not in (0, 32):
                state[left] = old[copy[0]]
            if right not in (0, 32):
                state[right] = old[copy[1]]
        return canonical(state)

    def step(self, pc, state, checking):
        a, b = self.raw[pc // 4], self.target[pc // 4]
        self.visited.add(pc)
        op, rs, rt, rd = a >> 26, a >> 21 & 31, a >> 16 & 31, a >> 11 & 31
        brs, brt, brd = b >> 21 & 31, b >> 16 & 31, b >> 11 & 31
        if pc in (0x14, 0x34):
            expected = {0x14: (0xAFB30054, 0xAFB20050),
                0x34: (0xAFB20050, 0xAFB30054)}[pc]
            if (a, b) != expected:
                raise ValueError('stale saved-register schedule')
            self.require(state, 29, 61, pc, 'saved frame base', checking)
            for word, base in ((a, 0), (b, 32)):
                source, slot = word >> 16 & 31, word & 65535
                reg = {0x50: 18, 0x54: 19}[slot]
                self.require(state, base + source, ANCHORS[reg], pc,
                    'save entry GP%d at SP+%X' % (reg, slot), checking)
            return state

        def inputs(pairs, reason='operand'):
            results = [self.require(state, left, right, pc, reason, checking)
                for left, right in pairs]
            return all(results)

        def gp_inputs(commute=False):
            pairs = [(rs, 32 + brs), (rt, 32 + brt)]
            if commute and (state[rs] != state[32 + brs] or state[rt] != state[32 + brt]):
                pairs = [(rs, 32 + brt), (rt, 32 + brs)]
            return inputs(pairs)

        def fresh_gp(equal):
            return self.write(state, rd, 32 + brd, equal)

        if a == b == 0:
            return state
        if op == 0:
            fn = a & 63
            if fn in (0, 3):
                return fresh_gp(inputs([(rt, 32 + brt)]))
            if fn in (33, 35, 37):
                equal = gp_inputs(fn in (33, 37))
                if fn in (33, 37) and (rs == 0 or rt == 0) and (brs == 0 or brt == 0):
                    return self.write(state, rd, 32 + brd,
                        copy=(rt if rs == 0 else rs, 32 + (brt if brs == 0 else brs)))
                return fresh_gp(equal)
            if fn == 25:
                equal = gp_inputs(True)
                state = self.write(state, 128, 129, equal)
                return self.write(state, 130, 131, equal)
            if fn == 18:
                return self.write(state, rd, 32 + brd, copy=(130, 131))
            if fn == 8:
                inputs([(rs, 32 + brs)], 'return target')
                inputs([(2, 34)], 'return V0')
                return state
            raise ValueError('unsupported SPECIAL +0x%X fn%d' % (pc, fn))
        if op == 3:
            return self.write(state, 31, 63)
        if op in (4, 5, 20, 21):
            gp_inputs(op in (4, 5, 20, 21))
            return state
        if op in (1, 6, 7, 22, 23):
            if op == 1 and rt not in (1, 3):
                raise ValueError('unsupported REGIMM subtype +0x%X' % pc)
            inputs([(rs, 32 + brs)], 'branch predicate')
            return state
        if op in (9, 10, 12, 13, 15):
            equal = True if op == 15 else inputs([(rs, 32 + brs)])
            if op in (9, 13) and a & 65535 == 0:
                return self.write(state, rt, 32 + brt, copy=(rs, 32 + brs))
            return self.write(state, rt, 32 + brt, equal)
        if op in (32, 33, 35, 36, 37):
            equal = inputs([(rs, 32 + brs)], 'load address')
            return self.write(state, rt, 32 + brt, equal)
        if op in (40, 41, 43):
            inputs([(rs, 32 + brs), (rt, 32 + brt)], 'store address/value')
            return state
        if op in (49, 53, 57, 61):
            equal = inputs([(rs, 32 + brs)], 'FP memory address')
            for reg in range(rt, rt + (2 if op in (53, 61) else 1)):
                if op in (57, 61):
                    inputs([(64 + reg, 96 + reg)], 'FP store value')
                else:
                    state = self.write(state, 64 + reg, 96 + reg, equal)
            return state
        if op == 17:
            if rs == 0:
                return self.write(state, rt, 32 + brt, copy=(64 + rd, 96 + rd))
            if rs == 4:
                return self.write(state, 64 + rd, 96 + rd, copy=(rt, 32 + brt))
            if rs == 8:
                if rt != 0:
                    raise ValueError('unsupported COP1 branch subtype +0x%X' % pc)
                inputs([(132, 133)], 'FP branch predicate')
                return state
            if rs == 16 and a & 63 in (0, 1, 2, 13, 60):
                pairs = [(64 + rd, 96 + rd)]
                if a & 63 != 13:
                    pairs.append((64 + rt, 96 + rt))
                equal = inputs(pairs, 'FP operands')
                if a & 63 == 60:
                    return self.write(state, 132, 133, equal)
                fd = a >> 6 & 31
                return self.write(state, 64 + fd, 96 + fd, equal)
        raise ValueError('unsupported opcode +0x%X %08X' % (pc, a))

    def edges(self, pc):
        word = self.raw[pc // 4]
        op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
        if op == 3:
            return [(pc + 8, True, True)]
        if op == 0 and word & 63 == 8:
            return [(None, True, False)]
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (op == 17 and rs == 8):
            imm = word & 65535
            target = pc + 4 + 4 * (imm - 65536 if imm & 32768 else imm)
            likely = op in (20, 21, 22, 23) or op == 1 and rt in (2, 3)
            if op in (4, 20) and rs == rt:
                return [(target, True, False)]
            if op in (5, 21) and rs == rt:
                return [(pc + 8, not likely, False)]
            return [(target, True, False), (pc + 8, not likely, False)]
        return [(pc + 4, False, False)]

    def edge_step(self, pc, state, delay, call, checking):
        state = self.step(pc, state, checking)
        if delay:
            state = self.step(pc + 4, state, checking)
        if call:
            target = ((self.entry + pc + 4) & 0xF0000000) | (self.raw[pc // 4] & 0x3FFFFFF) << 2
            if target not in self.arities:
                raise ValueError('unmodelled call +0x%X' % pc)
            self.calls.add((pc, target))
            for reg in range(4, 4 + min(4, self.arities[target])):
                self.require(state, reg, 32 + reg, pc, 'call argument', checking)
            for reg in (*range(1, 16), 24, 25):
                state = self.write(state, reg, 32 + reg, False)
            for reg in range(20):
                state = self.write(state, 64 + reg, 96 + reg, False)
            for left, right in ((128, 129), (130, 131), (132, 133)):
                state = self.write(state, left, right, False)
            state = self.write(state, 2, 34)
        return state

    def run(self):
        # Join by intersecting equalities, then check operands only at convergence.
        states, pending, queued = {0: initial()}, deque([0]), {0}
        iterations = 0
        while pending:
            pc = pending.popleft()
            queued.remove(pc)
            iterations += 1
            if iterations > 20000:
                raise ValueError('fixed-point bound exceeded')
            for target, delay, call in self.edges(pc):
                result = self.edge_step(pc, states[pc], delay, call, False)
                if target is None:
                    continue
                if not 0 <= target < len(self.raw) * 4:
                    raise ValueError('outside function edge +0x%X' % target)
                incoming = result if target not in states else meet(states[target], result)
                if states.get(target) != incoming:
                    states[target] = incoming
                    if target not in queued:
                        pending.append(target)
                        queued.add(target)
        self.visited.clear()
        for pc, state in sorted(states.items()):
            for _, delay, call in self.edges(pc):
                self.edge_step(pc, state, delay, call, True)
        missing = [i * 4 for i in range(405) if i * 4 not in self.visited]
        if any(self.raw[pc // 4] != self.target[pc // 4] for pc in missing):
            raise ValueError('unqualified changed unreachable word')
        return dict(fixed_point_iterations=iterations, reachable_nodes=len(states),
            checked_words=len(self.visited), obligations=len(self.obligations),
            call_sites=len(self.calls), missing_words=missing,
            save_schedule='owned mapped frame; closure at +0x34, not private fault-prefix equality',
            factor_schedule='closed non-annulled predicate inversion and arm/delay reorder',
            call_contract='equal arguments/memory effects/return; independent volatile-register kills',
            assumptions=['equal initial memory and entry registers', 'nontrapping matching operations',
                'ABI-conforming equal-effect bounded callees', 'owned mapped stack save window'],
            installed=False, numeric_oracle=False)


if __name__ == '__main__':
    root = Path.cwd()
    pool = screen.sections(root / 'conker/build/game-record-ring-renderer-test/setup-fitted/selected.elf')['.text'][1]
    words = struct.unpack_from('>405I', pool)
    retail = struct.unpack_from('>405I', (root / 'conker/conker.us.bin').read_bytes(), screen.ROM)
    result = Proof(words, retail).run()
    result['raw_differences'] = sum(a != b for a, b in zip(words, retail))
    receipt = root / 'conker/build/game-record-ring-renderer-test/live-value-proof.json'
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
