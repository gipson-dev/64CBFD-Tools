"""Framed, finite-value loop obligation checker for the recovered quad emitter.

This is an instruction-level dependency check, not an IEEE solver or a proof of
raw private RAM, access order, FCSR, traps or asynchronous/volatile memory. FP
operations remain uninterpreted, except commutative finite non-NaN addition.
The C contract requires valid disjoint vertices, kind 0..2, representable signed
conversions, count <= 0 or >= 2, and nonzero unsigned divisors on executed paths.
Providers obey O32 and may change external memory and outgoing register homes,
but cannot access unescaped locals or incoming parameter homes. Each call gets
a new external-memory epoch and arbitrary caller-saved GPR/FPR/HI/LO results.
"""
from collections import Counter
from copy import deepcopy

from tools.experiments.game_quad_edge_emitter import ENTRY, RANDOM, FACTORY

STACK = 0x10000000
MASK = 0xFFFFFFFF
ARGUMENTS = (('vertices',), ('origin-x',), ('origin-z',), ('preset-word',),
    ('scale',), ('kind',), ('x-count',), ('z-count',), ('flags-word',), ('context',))
SAVED = (*range(16, 24), 28, 29, 30, 31)


def signed(value):
    return (value + 0x80000000) % 0x100000000 - 0x80000000


def add(left, right):
    if isinstance(left, int) and isinstance(right, int):
        return (left + right) & MASK
    if left == 0:
        return right
    if right == 0:
        return left
    if isinstance(left, int):
        left, right = right, left
    if isinstance(left, tuple) and left[0] == 'address' and isinstance(right, int):
        return add(left[1], (left[2] + right) & MASK)
    if isinstance(right, int):
        return ('address', left, signed(right))
    return ('addu', left, right)


def integer(name, left, right):
    if isinstance(left, int) and isinstance(right, int):
        operations = {'sll': lambda: left << right, 'sra': lambda: signed(left) >> right,
            'andi': lambda: left & right, 'subu': lambda: left - right,
            'or': lambda: left | right}
        return operations[name]() & MASK
    if name == 'or' and right == 0:
        return left
    if name == 'or' and left == 0:
        return right
    return (name, left, right)


def floating(name, left, right=None):
    if right is None:
        return (name, left)
    if name == 'add.s' and repr(left) > repr(right):
        left, right = right, left
    return (name, left, right)


def byte(value, position):
    return value >> (24 - position * 8) & 255 if isinstance(value, int) else ('byte', value, position)


def join(values):
    if all(isinstance(v, int) for v in values):
        return sum(value << ((len(values) - i - 1) * 8) for i, value in enumerate(values))
    if len(values) == 4 and all(isinstance(v, tuple) and v[0] == 'byte' for v in values):
        if [v[2] for v in values] == list(range(4)) and all(v[1] == values[0][1] for v in values):
            return values[0][1]
    return ('bytes', *values)


def contains_frame_address(term):
    if isinstance(term, int):
        return STACK - 400 <= term < STACK + 40
    return isinstance(term, tuple) and any(contains_frame_address(item) for item in term)


def layout(words):
    backs = [(i, i + 1 + signed16(w)) for i, w in enumerate(words)
        if w >> 26 == 21 and signed16(w) < 0]
    if len(backs) != 2 or not backs[0][1] > backs[1][1]:
        raise ValueError('Expected inner and outer likely-backedge structure')
    (inner_branch, inner), (outer_branch, outer) = backs
    if words[inner_branch] >> 21 & 31 != 20:
        raise ValueError('Inner induction role is not S4')
    calls = [((w & 0x3FFFFFF) << 2) | (ENTRY & 0xF0000000) for w in words if w >> 26 == 3]
    if calls != [RANDOM, RANDOM, RANDOM, FACTORY]:
        raise ValueError('Unknown emitter provider sequence')
    if words[-2:] != [0x03E00008, 0x27BD0190]:
        raise ValueError('Unknown emitter return/frame')
    return dict(inner=inner, outer=outer, inner_branch=inner_branch, outer_branch=outer_branch,
        edge_register=words[outer_branch] >> 21 & 31)


def signed16(word):
    return ((word & 65535) + 32768) % 65536 - 32768


class Machine:
    def __init__(self, words, kind):
        if kind not in (0, 1, 2):
            raise ValueError('The copied tables have three valid kinds')
        self.words, self.layout = list(words), layout(list(words))
        self.r = [0, *(('entry-gpr', i) for i in range(1, 32))]
        self.f = [('entry-fpr', i) for i in range(32)]
        self.r[29], self.r[4:8] = STACK, ARGUMENTS[:4]
        self.memory, self.operations, self.calls, self.guards = {}, [], [], []
        self.hi, self.lo, self.pc, self.epoch = ('entry-hi',), ('entry-lo',), 0, ('entry',)
        self.returned = None
        for i in range(4, 10):
            self.store(STACK + i * 4, 4, kind if i == 5 else ARGUMENTS[i])

    def clone(self):
        return deepcopy(self)

    def load(self, where, size):
        private = isinstance(where, int) and STACK - 400 <= where < STACK + 40
        if private:
            values = [self.memory.get(where + i) for i in range(size)]
            if any(value is None for value in values):
                raise ValueError('Uninitialized private proof read at ' + hex(where - STACK))
            return values[0] if size == 1 else join(values)
        if contains_frame_address(where):
            raise ValueError('Unresolved symbolic private-frame address')
        if size == 1:
            return ('external-byte', self.epoch, where)
        return ('external-word', self.epoch, where)

    def store(self, where, size, value):
        if not isinstance(where, int) or not STACK - 400 <= where <= STACK + 40 - size:
            raise ValueError('Emitter store escaped the framed C contract')
        if size not in (1, 4):
            raise ValueError('Unknown framed store size')
        for i in range(size):
            self.memory[where + i] = value if size == 1 else byte(value, i)

    def ordinary(self, word):
        op, rs, rt, rd, shift, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        immediate = signed16(word)
        if word == 0:
            return
        if op == 9:
            self.r[rt] = add(self.r[rs], immediate & MASK)
        elif op == 15 and rs == 0:
            self.r[rt] = (word & 65535) << 16
        elif op == 12:
            self.r[rt] = integer('andi', self.r[rs], word & 65535)
        elif op in (35, 36, 49, 53):
            where = add(self.r[rs], immediate & MASK)
            value = self.load(where, 1 if op == 36 else 4)
            if op in (49, 53):
                self.f[rt] = value
                if op == 53:
                    self.f[rt + 1] = self.load(add(where, 4), 4)
            else:
                self.r[rt] = value
        elif op in (40, 43, 61):
            where = add(self.r[rs], immediate & MASK)
            self.store(where, 1 if op == 40 else 4, self.f[rt] if op == 61 else self.r[rt])
            if op == 61:
                self.store(add(where, 4), 4, self.f[rt + 1])
        elif op == 0:
            if fn in (0, 3) and rs == 0:
                self.r[rd] = integer('sll' if fn == 0 else 'sra', self.r[rt], shift)
            elif fn in (33, 35, 37) and shift == 0:
                self.r[rd] = add(self.r[rs], self.r[rt]) if fn == 33 else integer(
                    'subu' if fn == 35 else 'or', self.r[rs], self.r[rt])
            elif fn == 27 and rd == 0 and shift == 0:
                self.hi, self.lo = ('urem', self.r[rs], self.r[rt]), ('udiv', self.r[rs], self.r[rt])
            elif fn == 16 and rs == rt == shift == 0:
                self.r[rd] = self.hi
            else:
                raise ValueError('Unsupported integer proof instruction: %08X' % word)
        elif op == 17:
            fs, fd = rd, shift
            if rs == 0 and word & 2047 == 0:
                self.r[rt] = self.f[fs]
            elif rs == 4 and word & 2047 == 0:
                self.f[fs] = self.r[rt]
            elif rs == 16 and fn in (0, 1, 2, 3, 13) and (fn != 13 or rt == 0):
                names = {0: 'add.s', 1: 'sub.s', 2: 'mul.s', 3: 'div.s', 13: 'trunc.w.s'}
                self.f[fd] = floating(names[fn], self.f[fs], None if fn == 13 else self.f[rt])
                self.operations.append(self.f[fd])
            elif rs == 20 and fn == 32 and rt == 0:
                self.f[fd] = floating('cvt.s.w', self.f[fs])
                self.operations.append(self.f[fd])
            else:
                raise ValueError('Unsupported floating proof instruction: %08X' % word)
        else:
            raise ValueError('Unsupported ordinary proof instruction: %08X' % word)
        self.r[0] = 0
        if self.r[26:28] != [('entry-gpr', 26), ('entry-gpr', 27)]:
            raise ValueError('Reserved kernel register changed')

    def call(self, target):
        ordinal = len(self.calls)
        args = () if target == RANDOM else tuple(self.r[4:8]) + tuple(
            self.load(self.r[29] + i * 4, 4) for i in range(4, 31))
        self.calls.append((target, args))
        self.epoch = ('after-provider', ordinal)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = ('provider-gpr', ordinal, i)
        for i in range(20):
            self.f[i] = ('provider-fpr', ordinal, i)
        self.hi, self.lo = ('provider-hi', ordinal), ('provider-lo', ordinal)
        self.r[2] = ('provider-result', ordinal)
        for i in range(4):
            self.store(self.r[29] + i * 4, 4, ('provider-home', ordinal, i))

    def run(self, stop=None, positive=True, inner_continue=False, skip_initial_stop=False):
        for step in range(1000):
            if self.pc == stop and (step or not skip_initial_stop):
                return self
            if not 0 <= self.pc < len(self.words):
                raise ValueError('Proof left emitter text')
            word, pc = self.words[self.pc], self.pc
            op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
            if op == 3:
                target = ((word & 0x3FFFFFF) << 2) | (ENTRY & 0xF0000000)
                self.r[31] = ('call-continuation', len(self.calls))
                self.ordinary(self.words[pc + 1])
                self.call(target)
                self.pc += 2
            elif op == 0 and word & 63 == 8:
                if rs != 31 or pc != len(self.words) - 2:
                    raise ValueError('Unknown proof return')
                returned = self.r[31]
                self.ordinary(self.words[pc + 1])
                self.returned = (returned, tuple(self.r[i] for i in SAVED), tuple(self.f[20:]))
                return self
            elif op in (4, 5, 21, 22):
                left, right = self.r[rs], self.r[rt]
                if op == 22:
                    if left not in (ARGUMENTS[6], ARGUMENTS[7]) or rt:
                        raise ValueError('Unknown symbolic count predicate')
                    take = not positive
                    self.guards.append(('count<=0', left, take))
                elif left == right or isinstance(left, int) and isinstance(right, int):
                    take = (left == right) if op == 4 else (left != right)
                elif pc == self.layout['inner_branch']:
                    if op != 21:
                        raise ValueError('Unknown inner continuation predicate')
                    take = inner_continue
                    self.guards.append(('index!=count', left, right, take))
                elif op == 5 and right == 0 and self.words[pc + 2] == 0x0007000D:
                    take = True
                    self.guards.append(('divisor!=0', left))
                else:
                    raise ValueError('Unresolved symbolic branch at %X: %r' % (pc * 4, (left, right)))
                if take or op in (4, 5):
                    self.ordinary(self.words[pc + 1])
                self.pc = pc + 1 + signed16(word) if take else pc + 2
            else:
                self.ordinary(word)
                self.pc += 1
        raise ValueError('Proof step bound exceeded; no bounded loop proof allowed')


def abi_expected():
    registers = [0, *(('entry-gpr', i) for i in range(1, 32))]
    registers[29] = STACK
    return (registers[31], tuple(registers[i] for i in SAVED), tuple(('entry-fpr', i) for i in range(20, 32)))


def roles(state, preset_home, next_home):
    return (tuple(state.r[i] for i in (16, 17, 20, 21, 22, 23, 30)),
        tuple(state.f[i] for i in (18, 26, 28, 30)),
        tuple(state.load(STACK - 400 + i, 4) for i in (preset_home, 0xE4, 0xE8, 0xEC, 0xF0, next_home, 0x138, 0x150)),
        tuple(state.load(STACK - 400 + i, 1) for i in (*range(0x114, 0x11D), *range(0x120, 0x138))))


def require_equal(left, right, label):
    if left != right:
        raise ValueError('Quad loop dependency obligation failed: ' + label)


def protected(state):
    offsets = (*range(0x88, 0xE0), *range(0x114, 0x11D), *range(0x120, 0x138),
        *range(0x150, 0x154), *range(0x190, 0x1B8))
    return tuple(state.load(STACK - 400 + i, 1) for i in offsets)


def successor(state, edge):
    require_equal(state.r[state.layout['edge_register']], edge + 1, 'outer-edge successor')
    require_equal(state.r[21], add(ARGUMENTS[0], (edge + 1) * 12), 'cursor successor')
    require_equal((state.r[29], state.f[28], state.f[30]),
        (STACK - 400, ARGUMENTS[4], 0x3F000000), 'outer live frame/FP roles')


def prove_kind(raw, retail, kind):
    """Check entry, four outer cases and one arbitrary inner induction step.

    Mathematical induction is on j, with j=0 at entry and j'=j+1 at each
    continuation. In 0<=j<count<=INT_MAX no signed increment overflows. The
    exit guard and count snapshot are compared symbolically, not sampled.
    """
    starts = []
    for words in (raw, retail):
        machine = Machine(words, kind)
        starts.append(machine.run(machine.layout['outer']))
        require_equal((machine.r[machine.layout['edge_register']], machine.r[21], machine.r[29], machine.f[28], machine.f[30]),
            (0, ARGUMENTS[0], STACK - 400, ARGUMENTS[4], 0x3F000000), 'outer invariant base case')
    require_equal(Counter(starts[0].operations), Counter(starts[1].operations), 'entry FP graph')
    prefix_rows, step_rows = [], []
    for edge in range(4):
        for positive in (False, True):
            pair = []
            for entry in starts:
                machine = entry.clone()
                for register in (*range(1, 16), *range(16, 24), 24, 25, 30, 31):
                    machine.r[register] = ('edge-cut-gpr', edge, register)
                machine.f[:28] = [('edge-cut-fpr', edge, register) for register in range(28)]
                machine.r[1] = 3
                machine.r[machine.layout['edge_register']] = edge
                machine.r[21] = add(ARGUMENTS[0], edge * 12)
                machine.epoch = ('edge', edge)
                machine.calls, machine.guards, machine.operations = [], [], []
                machine.run(machine.layout['inner'] if positive else machine.layout['outer'],
                    positive=positive, skip_initial_stop=not positive)
                require_equal(protected(machine), protected(entry), 'constant frame across edge setup')
                pair.append(machine)
            require_equal(pair[0].guards, pair[1].guards, 'count selection edge %d' % edge)
            require_equal(Counter(pair[0].operations), Counter(pair[1].operations), 'edge FP graph %d' % edge)
            if not positive:
                if edge == 3:
                    for machine in pair:
                        require_equal(machine.returned, abi_expected(), 'empty-edge return ABI')
                else:
                    for machine in pair:
                        successor(machine, edge)
                prefix_rows.append((edge, 'empty'))
                continue
            require_equal(roles(pair[0], 0xE0, 0x108), roles(pair[1], 0xF4, 0x104), 'positive-edge live roles')
            for machine in pair:
                require_equal(machine.r[20], 0, 'j=0 base case')
            prefix_rows.append((edge, 'positive'))
            for continuing in (False, True):
                steps = []
                for before in pair:
                    machine = before.clone()
                    machine.r[20] = machine.f[18] = ('index',)
                    machine.epoch = ('iteration', edge)
                    machine.calls, machine.guards, machine.operations = [], [], []
                    machine.run(machine.layout['inner'] if continuing else machine.layout['outer'],
                        inner_continue=continuing, skip_initial_stop=continuing)
                    require_equal(protected(machine), protected(before), 'constant frame across arbitrary iteration')
                    if continuing:
                        gprs, fprs, homes, tables = roles(before, 0xE0 if before is pair[0] else 0xF4,
                            0x108 if before is pair[0] else 0x104)
                        expected = (gprs[:2] + (add(('index',), 1),) + gprs[3:],
                            (add(('index',), 1),) + fprs[1:], homes, tables)
                        require_equal(roles(machine, 0xE0 if before is pair[0] else 0xF4,
                            0x108 if before is pair[0] else 0x104), expected, 'stable per-edge snapshots in induction')
                    steps.append(machine)
                require_equal(steps[0].calls, steps[1].calls, 'three RNG calls and full 31-word factory packet')
                require_equal(steps[0].guards, steps[1].guards, 'divisors and symbolic continuation')
                require_equal(Counter(steps[0].operations), Counter(steps[1].operations), 'iteration FP graph')
                for machine in steps:
                    guard = machine.guards[-1]
                    require_equal(guard, ('index!=count', add(('index',), 1), ARGUMENTS[6 if edge % 2 == 0 else 7], continuing),
                        'j+1 versus exact per-edge count')
                if continuing:
                    require_equal(roles(steps[0], 0xE0, 0x108), roles(steps[1], 0xF4, 0x104), 'inductive live-role preservation')
                    for machine in steps:
                        require_equal(machine.r[20], add(('index',), 1), 'j successor')
                        require_equal(machine.f[18], machine.r[20], 'likely-delay-slot index transfer')
                elif edge == 3:
                    for machine in steps:
                        require_equal(machine.returned, abi_expected(), 'positive-edge return ABI')
                else:
                    for machine in steps:
                        successor(machine, edge)
                step_rows.append((edge, continuing))
    return dict(kind=kind, outer_cases=prefix_rows, induction_steps=step_rows)


def prove(raw, retail):
    rows = [prove_kind(raw, retail, kind) for kind in range(3)]
    return dict(kinds=rows,
        outer_cases=sum(len(row['outer_cases']) for row in rows),
        induction_steps=sum(len(row['induction_steps']) for row in rows),
        symbolic_index_and_count=True, full_factory_words=31, opaque_calls_per_iteration=4,
        arbitrary_provider_clobbers_and_external_epochs=True,
        finite_non_nan_addition_commutation_assumed=True,
        no_raw_private_fault_FCSR_or_trap_equivalence_claim=True,
        not_installation_qualification=True)
