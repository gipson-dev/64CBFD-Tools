"""Instruction-driven gravity/row relation for the derived intermediate.

Ordinary mapped disjoint record, points, private frame and snapshot views;
row index0..18, stable memory between ordered stores, nontrapping FP execution.
Floating values/control are symbolic. No fault-register or timing claim.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib
import json
import struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_strip_update_151ad174_private_oracle as oracle

e = g.e
from tools.experiments import game_strip_update_151ad174_recovery as source
p = source.OUT
FRAME = 776
RECORD, POINTS, SNAPROW, INDEX = ('RECORD',), ('POINTS',), ('SNAPSHOT_ROW',), ('ROW_INDEX',)

def predicate(op, left, right):
    if e.tagged(left, 'STACK') or e.tagged(right, 'STACK'):
        assert e.tagged(left, 'STACK') and e.tagged(right, 'STACK')
        left, right = left[1], right[1]
    return g.predicate(op, left, right)


class State(g.State):
    def __init__(self, side, phase):
        super().__init__(side)
        self.side, self.phase = side, phase
        self.mem = {i: ('PRIVATE_ENTRY', i) for i in range(-FRAME, 16)}
        self.public = {}
        self.read_set = Counter()
        self.r = [0] + [('DEAD_GPR', side, i) for i in range(1, 32)]
        self.f = [('DEAD_FP', side, i) for i in range(32)]
        self.r[16], self.r[29] = RECORD, ('STACK', -FRAME)
        for reg in (*range(20, 24), 28, 30):
            self.r[reg] = ('ENTRY', reg)
        self.fcsr, self.condition = ('START_CSR', phase), ('START_CONDITION', phase)
        self.hi, self.lo = ('START_HI', phase), ('START_LO', phase)
        self.store(e.add(RECORD, 0x38), 4, POINTS)
        self.store(('STACK', 0x2F8 - FRAME), 4, ('LAST',))
        for reg, offset in [(16, 0x64), (17, 0x68), (18, 0x6C), (19, 0x70)]:
            self.store(('STACK', offset - FRAME), 4, ('ENTRY', reg))
        self.store(('STACK', 0x74 - FRAME), 4, ('RETURN',))
        for reg in range(20, 32, 2):
            offset = 0x30 + (reg - 20) * 4
            self.store(('STACK', offset - FRAME), 4, ('ENTRY_FP', reg + 1))
            self.store(('STACK', offset + 4 - FRAME), 4, ('ENTRY_FP', reg))
        self.trace = []
        if phase == 'row':
            self.r[7] = INDEX
            self.r[17] = ('STACK', 0x2F4 - FRAME)
            self.r[18] = SNAPROW
            self.r[19] = e.scale(INDEX, 24)
            self.r[10 if side == 'retail' else 9] = SNAPROW
            self.r[12], self.r[13] = ('STACK', 0xE8 - FRAME), 0x39
            end = 0xE8 if side == 'retail' else 0x2E8
            self.r[11] = self.r[31] = ('STACK', end - FRAME)
            self.f[26 if side == 'retail' else 30] = ('DAMPING',)
            self.f[18 if side == 'retail' else 26] = ('CEILING',)
            self.f[28] = 0x3F000000
            scale = 16 if side == 'retail' else 24
            self.f[scale], self.f[scale + 1] = ('SCALE_LOW',), ('SCALE_HIGH',)
            self.store(('STACK', 0x7C - FRAME), 4, ('NEGATIVE_GRAVITY',))
            self.store(('STACK', 0x84 - FRAME), 4, ('GRAVITY_SQUARE',))

    def load(self, address, size, pool=b''):
        assert size in (1, 2, 4)
        if e.tagged(address, 'STACK'):
            offset = address[1]
            assert -FRAME <= offset and offset + size <= 16 and offset % size == 0
            return g.join([self.mem[offset + i] for i in range(size)])
        value = g.join([self.public.get(e.add(address, i), ('MEMORY_BYTE', self.epoch, e.add(address, i)))
                        for i in range(size)])
        self.read_set[address, size, value] += 1
        return value

    def store(self, address, size, value):
        assert size in (1, 2, 4)
        if e.tagged(address, 'STACK'):
            offset = address[1]
            assert -FRAME <= offset and offset + size <= 16 and offset % size == 0
            for i in range(size):
                self.mem[offset + i] = g.byte(value, 8 * (size - i - 1))
        else:
            assert not e.has_tag(address, 'SNAPSHOT_ROW'), ('snapshot modified', address)
            self.trace.append(('WRITE', address, size, value))
            for i in range(size):
                self.public[e.add(address, i)] = g.byte(value, 8 * (size - i - 1))

    def frame(self):
        return tuple(self.mem[i] for i in range(-FRAME, 16))


class Program(g.Program):
    def __init__(self, words, terms):
        e.Program.__init__(self, words, b'', oracle.ENTRY)
        self.terms, self.seen = terms, set()

    def step(self, state, word):
        op, fmt, ft, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 0 and fn == 33 and any(e.tagged(state.r[reg], 'STACK') for reg in (fmt, ft)) \
                and not any(isinstance(state.r[reg], int) for reg in (fmt, ft)):
            stack, index = (state.r[fmt], state.r[ft]) if e.tagged(state.r[fmt], 'STACK') else (state.r[ft], state.r[fmt])
            assert not e.has_tag(index, 'STACK')
            state.r[fs] = ('INDEXED_STACK', stack[1], index)
        elif op == 0 and fn in (42, 43):
            state.r[fs] = e.boolean(predicate('SLT' if fn == 42 else 'ULT', state.r[fmt], state.r[ft]))
        elif op in (53, 61):
            address = e.add(state.r[fmt], ((word & 65535) ^ 32768) - 32768)
            if op == 53:
                state.f[ft + 1], state.f[ft] = state.load(address, 4), state.load(e.add(address, 4), 4)
            else:
                state.store(address, 4, state.f[ft + 1])
                state.store(e.add(address, 4), 4, state.f[ft])
        elif op == 17 and fmt in (16, 17, 20):
            if fmt == 16 and fn == 6:
                state.f[fd] = state.f[fs]
                return
            assert (fmt == 16 and fn in (0, 1, 2, 3, 4, 5, 7, 13, 33, 50, 60, 62)) or \
                   (fmt == 17 and fn in (0, 2, 32)) or (fmt == 20 and fn == 32), ('unsupported FP', hex(word))
            def value(register):
                if fmt != 17:
                    return state.f[register]
                low, high = state.f[register], state.f[register + 1]
                if e.tagged(low, 'LOW') and e.tagged(high, 'HIGH') and low[1] == high[1]:
                    return low[1]
                return ('FP64', high, low)
            args = (value(fs), value(ft)) if fn in (0, 1, 2, 3, 50, 60, 62) else (value(fs),)
            observation = (fmt, fn, args, state.fcsr)
            state.trace.append(('FP', observation))
            result = self.terms.term('FP_VALUE', *observation)
            state.fcsr = self.terms.term('FP_STATUS', *observation)
            if fn in (50, 60, 62):
                state.condition = result
            elif fmt == 16 and fn == 33 or fmt == 17 and fn in (0, 2):
                state.f[fd], state.f[fd + 1] = ('LOW', result), ('HIGH', result)
            else:
                state.f[fd] = result
        else:
            super().step(state, word)
        state.r[0] = 0

    def call(self, state, target):
        assert target in (oracle.QUERY, oracle.RNG, oracle.EMIT), ('unexpected suffix provider', hex(target))
        count = oracle.COUNTS[target]
        args = tuple(state.r[4:4 + min(count, 4)]) + tuple(
            state.load(e.add(state.r[29], 16 + 4 * i), 4) for i in range(max(0, count - 4)))
        ordinal = sum(state.calls.values())
        state.calls[target] += 1
        state.trace.append(('CALL', target, args, state.fcsr))
        state.trace.append(('CALL_PRIVATE', state.frame()))
        state.trace.append(('CALL_PUBLIC', tuple(sorted(state.public.items(), key=repr))))
        state.epoch += 1
        for address in state.public:
            state.public[address] = ('PROVIDER_BYTE', ordinal, address)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            state.r[reg] = ('CALLER', ordinal, reg)
        for reg in range(20):
            state.f[reg] = ('CALLER_FP', ordinal, reg)
        for index in range(max(4, count)):
            state.store(e.add(state.r[29], 4 * index), 4, ('CALL_HOME', ordinal, index))
        state.r[2], state.r[31] = ('RESULT', target, ordinal), ('CALL_RETURN', ordinal)
        state.hi, state.lo = ('CALL_HI', ordinal), ('CALL_LO', ordinal)
        state.fcsr, state.condition = ('CALL_CSR', ordinal), ('CALL_CONDITION', ordinal)

    def paths(self, start, stops, initial):
        active, answers, work = [(start, initial)], {}, 0
        while active:
            pc, state = active.pop()
            work += 1
            state.steps += 1
            assert work < 600000 and state.steps < 1800, ('unbounded proof', work, pc)
            if state.steps > 1 and pc in stops:
                key = (stops[pc], tuple(sorted(state.facts.items(), key=repr)))
                assert key not in answers, ('duplicate proof path', pc)
                answers[key] = state
                continue
            word = self.instruction(pc)
            op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
            if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or op == 17 and rs == 8:
                if op == 17:
                    condition = state.condition if rt & 1 else e.negate(state.condition)
                    likely = bool(rt & 2)
                elif op == 1:
                    condition = predicate('SLT', state.r[rs], 0)
                    condition = e.negate(condition) if rt & 1 else condition
                    likely = bool(rt & 2)
                else:
                    condition = predicate('EQ', state.r[rs], state.r[rt]) if op in (4, 5, 20, 21) else predicate('SLT', 0, state.r[rs])
                    condition = e.negate(condition) if op in (5, 21, 6, 22) else condition
                    likely = op >= 20
                for taken in e.choices(state, condition):
                    successor = deepcopy(state)
                    e.assume(successor, condition, taken)
                    if taken or not likely:
                        self.step(successor, self.instruction(pc + 4))
                    target = pc + 4 + 4 * (((word & 65535) ^ 32768) - 32768) if taken else pc + 8
                    active.append((target, successor))
            elif op == 3:
                state.r[31] = oracle.ENTRY + pc + 8
                self.step(state, self.instruction(pc + 4))
                self.call(state, ((oracle.ENTRY + pc + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2))
                active.append((pc + 8, state))
            elif op == 0 and word & 63 == 8:
                assert state.r[rs] == ('RETURN',)
                self.step(state, self.instruction(pc + 4))
                active.append((-4, state))
            else:
                self.step(state, word)
                active.append((pc + 4, state))
        return answers


def roles(state, end):
    if end == 'return':
        assert state.r[29] == ('STACK', 0) and state.r[31] == ('RETURN',)
        assert all(state.r[i] == ('ENTRY', i) for i in (*range(16, 24), 28, 30))
        assert state.f[20:] == [('ENTRY_FP', i) for i in range(20, 32)]
        return ()
    if end == 'audio':
        return (state.r[16], state.r[29])
    side = state.side
    end_offset = 0xE8 if side == 'retail' else 0x2E8
    assert state.r[11] == state.r[31] == ('STACK', end_offset - FRAME)
    return (state.r[7], state.r[17], state.r[18], state.r[19], state.r[10 if side == 'retail' else 9],
            state.r[12], state.r[13], state.f[26 if side == 'retail' else 30],
            state.f[18 if side == 'retail' else 26], state.f[28],
            tuple(state.f[16:18] if side == 'retail' else state.f[24:26]))


def prove(truth, candidate, phase):
    terms = Terms()
    start = {'gravity': 175 * 4, 'row': 212 * 4, 'audio': 438 * 4}[phase]
    stops = {-4: 'return'} if phase == 'audio' else {212 * 4: 'row', 438 * 4: 'audio'}
    answers = []
    for side, words in [('retail', truth), ('raw', candidate)]:
        program = Program(words, terms)
        answers.append(program.paths(start, stops, State(side, phase)))
    left, right = answers
    assert left.keys() == right.keys(), ('path predicates', phase, len(left), len(right))
    for key, a in left.items():
        b = right[key]
        if phase == 'row':
            for state in (a, b):
                assert state.r[7] == e.add(INDEX, -1), 'row index backedge'
                assert state.r[19] == e.add(e.scale(INDEX, 24), -24), 'point stride backedge'
                assert state.r[18] == e.add(SNAPROW, -12)
                assert state.r[10 if state.side == 'retail' else 9] == e.add(SNAPROW, -12)
                assert all(state.r[i] == ('ENTRY', i) for i in (*range(20, 24), 28, 30))
                assert state.r[16] == RECORD and state.r[29] == ('STACK', -FRAME)
                assert state.r[17] == ('STACK', 0x2F4 - FRAME)
                assert state.r[12] == ('STACK', 0xE8 - FRAME) and state.r[13] == 0x39
                assert state.f[26 if state.side == 'retail' else 30] == ('DAMPING',)
                assert state.f[18 if state.side == 'retail' else 26] == ('CEILING',)
                assert state.f[28] == 0x3F000000
                scale = 16 if state.side == 'retail' else 24
                assert state.f[scale:scale + 2] == [('SCALE_LOW',), ('SCALE_HIGH',)]
                assert state.load(('STACK', 0x7C - FRAME), 4) == ('NEGATIVE_GRAVITY',)
                assert state.load(('STACK', 0x84 - FRAME), 4) == ('GRAVITY_SQUARE',)
        for name, x, y in [('effects', a.trace, b.trace), ('private', a.frame(), b.frame()),
                           ('objects', a.public, b.public), ('reads', a.read_set, b.read_set),
                           ('FP status', a.fcsr, b.fcsr), ('FP condition', a.condition, b.condition),
                           ('live roles', roles(a, key[0]), roles(b, key[0]))]:
            if x != y:
                detail = next((i for i, (u, v) in enumerate(zip(x, y)) if u != v), None) if isinstance(x, (list, tuple)) else None
                raise AssertionError(('relation', phase, key[0], name, detail,
                    repr(x[detail] if detail is not None else x)[:420],
                    repr(y[detail] if detail is not None else y)[:420]))
    return dict(phase=phase, paths=len(left), equal_paths=len(left),
                abstract_terms=len(terms.values), ordered_effects_and_FP_status=True,
                all_private_bytes=True, public_memory_and_read_multiset=True, loop_live_roles=True)



def alternate(word):
    op, fmt, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0:
        fields = (16, 11) if fn in (0, 2, 3) else (21, 16, 11) if fn in (4, 33, 35, 36, 37, 42, 43) else \
                 (11,) if fn in (16, 18) else (21, 16) if fn in (25, 26, 27) else (21,) if fn == 8 else ()
    elif op == 17:
        fields = (16,) if fmt in (0, 4) else ()
    elif op == 3:
        fields = ()
    elif op in (1, 6, 7, 22, 23, 49, 53, 57, 61):
        fields = (21,)
    elif op == 15:
        fields = (16,)
    else:
        fields = (21, 16)
    for shift in fields:
        reg = word >> shift & 31
        if reg in (14, 15):
            word = word & ~(31 << shift) | (29 - reg) << shift
    return word


def controls(truth, candidate):
    changed = [alternate(word) for word in candidate]
    assert changed != candidate
    positive = [prove(truth, changed, phase) for phase in ('gravity', 'row', 'audio')]

    transform = source.PIN['private_transformation']
    branch = transform['old_to_new'][str(transform['sites']['norm-branch'])]
    controls = []
    for name, phase, old, new in [
        ('wrong-square-home', 'gravity', 0xE7AA0084, 0xE7AA0088),
        ('wrong-point-stride', 'row', 0x2673FFE8, 0x2673FFEC),
        ('ordinary-zero-norm-delay', 'row', candidate[branch], candidate[branch] & ~(2 << 16)),
        ('gravity-multiply-operand-order', 'row', 0x46024082, 0x46081082),
        ('wrong-audio-volume', 'audio', 0x24067530, 0x2406752F),
    ]:
        bad = candidate[:]
        if name == 'ordinary-zero-norm-delay':
            at = branch
        else:
            assert bad.count(old) == 1, (name, bad.count(old))
            at = bad.index(old)
        assert old != new and bad[at] == old
        bad[at] = new
        try:
            prove(truth, bad, phase)
        except AssertionError as error:
            reason = str(error)
            assert not any(word in reason for word in ('unsupported', 'unbounded proof', 'escaped code')), (name, reason)
        else:
            raise AssertionError(('ineffective symbolic control', name))
        controls.append(dict(name=name, phase=phase, changed_word=at, rejected=reason[:220]))
    return dict(independent_allocation_positive=positive, effective_controls=controls)


def main():
    from tools.tests import game_strip_update_151ad174_normalization as normalization
    from tools.tests import game_strip_update_151ad174_lifetime_relation as entry
    raw, refs = oracle.payload(source.OUT/'v82.o', source.NAME)
    bound = oracle.bound_blob(raw, refs, oracle.SYMS)
    candidate, transformation = normalization.derive(bound)
    assert json.loads(json.dumps(transformation)) == source.PIN['private_transformation']
    truth = list(struct.unpack('>494I', (source.OUT/'retail.bin').read_bytes()))
    prefix = entry.prefix_controls(truth, bound)
    snapshot = entry.snapshot_controls(truth, bound)
    assert candidate[:175] == bound[:175]
    phases = [prove(truth, candidate, phase) for phase in ('gravity', 'row', 'audio')]
    negative = controls(truth, candidate)
    assert [v['paths'] for v in phases] == [2, 288, 4]
    for label in ('strict', 'layout'):
        data, bindings = oracle.payload(source.OUT/('strip-update-padded-'+label+'.o'),source.NAME)
        assert oracle.bound_blob(data, bindings, oracle.SYMS) == truth
    (source.OUT/'intermediate.bin').write_bytes(struct.pack('>494I', *candidate))
    report = dict(prefix=prefix, snapshot=snapshot, phases=phases, controls=negative,
        private_normalization=transformation, source_installed=source.installed(),c_match_credit=0,
        domain='Mapped disjoint record/points/frame/snapshots, count0..20 and row0..18, stable ordinary memory, opaque conforming providers and nontrapping FP. No fault-state, timing or host claim.')
    (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(phases=[v['paths']for v in phases],negative_controls=5,independent_allocation_positive=True)),flush=True)
