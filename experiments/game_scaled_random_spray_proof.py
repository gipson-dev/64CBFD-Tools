"""Framed counted-loop obligations, with explicit finite multiplication commutation.

This checks instruction dependencies and valid C values, not raw private RAM,
FCSR, fault order, NaN payloads or hardware exceptions. The count is signed;
0 <= index < count <= INT_MAX makes its increment defined. Products and float
conversions must be finite and representable. Providers obey O32 and may retain
and change the three escaped output objects, but not unescaped parameter/saved
homes. Multiplication operand commutation is an explicit numeric lemma.
"""
from collections import Counter

from tools.experiments import game_scaled_random_spray as source
from tools.experiments.game_quad_edge_loop_values import Machine, STACK, add, MASK, SAVED, abi_expected

INPUTS = (('x-word',), ('y-word',), ('z-word',), ('count-word',), ('scale',), ('flags-word',), ('context-word',))


def layout(words):
    if len(words) != 118 or words[0] != 0x27BDFF08 or words[-2:] != [0x03E00008, 0x27BD00F8]:
        raise ValueError('Unknown spray body/frame/return')
    if words[14] != 0x1A200059 or words[102] != 0x5611FFB9:
        raise ValueError('Unknown spray signed-entry/likely-loop CFG')
    if [(i, ((w & 0x3FFFFFF) << 2) | (source.ENTRY & 0xF0000000)) for i, w in enumerate(words) if w >> 26 == 3] != [
            (34, source.DIRECTION), (99, source.FACTORY)]:
        raise ValueError('Unknown spray provider bindings')
    return dict(loop=32, back=102)


class SprayMachine(Machine):
    def __init__(self, words):
        self.words, self.layout = list(words), layout(list(words))
        self.r = [0, *(('entry-gpr', i) for i in range(1, 32))]
        self.f = [('entry-fpr', i) for i in range(32)]
        self.r[29], self.r[4:8] = STACK, INPUTS[:4]
        self.memory, self.operations, self.calls, self.guards = {}, [], [], []
        self.hi, self.lo, self.pc, self.epoch = ('entry-hi',), ('entry-lo',), 0, ('entry',)
        self.returned = None
        for i in range(4, 7):
            self.store(STACK + i * 4, 4, INPUTS[i])

    def ordinary(self, word):
        op, rs, rt, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 57:
            immediate = ((word & 65535) + 32768) % 65536 - 32768
            self.store(add(self.r[rs], immediate & MASK), 4, self.f[rt])
        elif op == 17 and rs == 16 and fn in (0, 2):
            left, right = self.f[fs], self.f[rt]
            if fn == 2 and repr(left) > repr(right):
                left, right = right, left
            self.f[fd] = ('mul.s-finite-commutative' if fn == 2 else 'add.s-ordered', left, right)
            self.operations.append(self.f[fd])
        else:
            super().ordinary(word)

    def homes(self):
        return tuple(self.load(STACK - 248 + at, 4) for at in (0xF0, 0xEC, 0xE8))

    def call(self, target):
        ordinal = len(self.calls)
        where = tuple(STACK - 248 + at for at in (0xF0, 0xEC, 0xE8))
        if target == source.DIRECTION:
            args = tuple(self.r[4:8])
            if args != (64, *where):
                raise ValueError('Spray direction flag or escaped output identity changed')
            old = tuple(self.load(at, 4) if all(at + i in self.memory for i in range(4)) else ('first-uninitialized', j)
                for j, at in enumerate(where))
            self.calls.append((target, args, old))
            outputs = tuple(('direction-value', ordinal, j, old) for j in range(3))
        elif target == source.FACTORY:
            args = tuple(self.r[4:8]) + tuple(self.load(self.r[29] + i * 4, 4) for i in range(4, 31))
            old = self.homes()
            self.calls.append((target, args, old))
            outputs = tuple(('factory-output-home', ordinal, j, old, args) for j in range(3))
        else:
            raise ValueError('Unknown spray provider')
        for at, value in zip(where, outputs):
            self.store(at, 4, value)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = ('provider-gpr', ordinal, i)
        for i in range(20):
            self.f[i] = ('provider-fpr', ordinal, i)
        self.hi, self.lo = ('provider-hi', ordinal), ('provider-lo', ordinal)
        self.r[2] = ('provider-result', ordinal)
        for i in range(31 if target == source.FACTORY else 4):
            self.store(self.r[29] + i * 4, 4, ('provider-outgoing-home', ordinal, i))

    def run(self, stop=None, positive=True, continuation=False, skip_initial=False):
        for step in range(250):
            if self.pc == stop and (step or not skip_initial):
                return self
            if not 0 <= self.pc < len(self.words):
                raise ValueError('Spray proof left text')
            pc, word = self.pc, self.words[self.pc]
            op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
            if op == 3:
                self.r[31] = ('call-continuation', len(self.calls))
                self.ordinary(self.words[pc + 1])
                self.call(((word & 0x3FFFFFF) << 2) | (source.ENTRY & 0xF0000000))
                self.pc += 2
            elif op == 0 and word & 63 == 8:
                if word != 0x03E00008 or pc != 116:
                    raise ValueError('Unknown spray proof return')
                target = self.r[31]
                self.ordinary(self.words[pc + 1])
                self.returned = (target, tuple(self.r[i] for i in SAVED), tuple(self.f[20:]))
                if self.returned != abi_expected():
                    raise ValueError('Spray return ABI differs')
                return self
            elif op in (6, 21):
                if pc == 14 and op == 6 and self.r[rs] == INPUTS[3] and rt == 0:
                    take = not positive
                    self.guards.append(('count<=0', self.r[rs], take))
                elif pc == 102 and op == 21:
                    take = continuation
                    self.guards.append(('index!=count', self.r[rs], self.r[rt], take))
                else:
                    raise ValueError('Unknown spray proof predicate')
                if take or op == 6:
                    self.ordinary(self.words[pc + 1])
                immediate = ((word & 65535) + 32768) % 65536 - 32768
                self.pc = pc + 1 + immediate if take else pc + 2
            else:
                self.ordinary(word)
                self.pc += 1
        raise ValueError('Spray proof crossed its one-step obligation')


def stable(machine):
    return (tuple(machine.r[i] for i in (*range(17, 24), 28, 29, 30)), tuple(machine.f[20:]),
        tuple(machine.load(STACK - 248 + i, 1) for i in range(0x88, 0xC0)),
        tuple(machine.load(STACK + i, 1) for i in range(16, 28)))


def equal(left, right, name):
    if left != right:
        raise ValueError('Spray loop obligation failed: ' + name)


def prove(raw, normalized):
    starts = []
    for words in (raw, normalized):
        empty = SprayMachine(words).run(positive=False)
        if empty.calls or empty.operations:
            raise ValueError('Empty spray called providers or evaluated FP')
        start = SprayMachine(words).run(stop=32)
        equal(start.r[16], 0, 'index base')
        equal(start.r[17], INPUTS[3], 'count snapshot')
        starts.append(start)
    equal(stable(starts[0]), stable(starts[1]), 'entry protected state and live roles')
    equal(Counter(starts[0].operations), Counter(starts[1].operations), 'doubled scale graph')
    for continuing in (False, True):
        results = []
        for start in starts:
            machine = start.clone()
            machine.r[16] = ('arbitrary-index',)
            for j, at in enumerate((0xF0, 0xEC, 0xE8)):
                machine.store(STACK - 248 + at, 4, ('arbitrary-escaped-home', j))
            machine.calls, machine.guards, machine.operations = [], [], []
            machine.run(stop=32, continuation=continuing, skip_initial=True)
            equal(len(machine.calls), 2, 'one direction and factory call per iteration')
            if continuing:
                equal(machine.r[16], add(('arbitrary-index',), 1), 'induction successor')
                equal(stable(machine), stable(start), 'loop protected state')
            results.append(machine)
        a, b = results
        equal(a.calls, b.calls, 'all factory words and escaped home observations')
        equal(a.guards, b.guards, 'loop continuation predicate')
        equal(Counter(a.operations), Counter(b.operations), 'FP graph under finite multiplication lemma')
        if continuing:
            equal(a.homes(), b.homes(), 'retained provider home effects')
        else:
            equal(a.returned, b.returned, 'exit ABI')
    return dict(empty_paths=2, arbitrary_index_continue_exit_obligations=2,
        complete_31_physical_words_and_escaped_home_observations=True,
        count_scale_coordinate_flag_context_snapshots_and_ABI_equal=True,
        finite_multiplication_commutation_explicit=True, no_raw_private_fault_FCSR_or_hardware_claim=True)
