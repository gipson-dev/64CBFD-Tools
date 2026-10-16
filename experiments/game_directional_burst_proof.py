"""Two-path, ordered-FP value proof under a framed, defined-conversion contract.

Memory is ordinary and nonvolatile; opaque providers cannot inspect or overwrite
the unescaped private frame or incoming homes. Float-to-integer conversions must
be defined. Operation dependencies and operand order are checked, not the raw
private RAM, fault order, FCSR, NaN payloads or hardware exception environment.
"""
from collections import Counter

from tools.experiments import game_directional_burst as source
from tools.experiments.game_quad_edge_loop_values import Machine, STACK, MASK, add, abi_expected

ARGUMENTS = (('x-word',), ('y-word',), ('z-word',), ('angle-word',),
    ('compact-word',), ('flags-word',), ('context-word',))


class BurstMachine(Machine):
    def __init__(self, words, compact):
        self.words = list(words)
        if self.words[0] != 0x27BDFF00 or compact not in (False, True):
            raise ValueError('Burst proof requires the original frame and one of two paths')
        self.r = [0, *(('entry-gpr', i) for i in range(1, 32))]
        self.f = [('entry-fpr', i) for i in range(32)]
        self.r[29], self.r[4:8] = STACK, ARGUMENTS[:4]
        self.memory, self.operations, self.calls, self.guards = {}, [], [], []
        self.hi, self.lo, self.pc, self.epoch = ('entry-hi',), ('entry-lo',), 0, ('entry',)
        self.returned, self.compact = None, compact
        for i in range(4, 7):
            self.store(STACK + i * 4, 4, ARGUMENTS[i])

    def store(self, where, size, value):
        if not isinstance(where, int) or not STACK - 256 <= where <= STACK + 28 - size:
            raise ValueError('Burst store escaped its private frame/incoming homes')
        return super().store(where, size, value)

    def load(self, where, size):
        if size == 2 and not isinstance(where, int):
            raise ValueError('Unknown symbolic halfword base')
        if size == 2 and not STACK - 256 <= where < STACK + 28:
            if where != source.DEFAULT_ANGLE:
                raise ValueError('Unknown burst default-angle binding')
            return ('external-u16', self.epoch, where)
        return super().load(where, size)

    def ordinary(self, word):
        op, rs, rt, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op in (33, 37):
            immediate = ((word & 65535) + 32768) % 65536 - 32768
            value = self.load(add(self.r[rs], immediate & MASK), 2)
            self.r[rt] = ('sign16', value) if op == 33 else value
        elif op == 57:
            immediate = ((word & 65535) + 32768) % 65536 - 32768
            self.store(add(self.r[rs], immediate & MASK), 4, self.f[rt])
        elif op == 0 and fn == 26 and fs == fd == 0:
            self.hi, self.lo = ('srem', self.r[rs], self.r[rt]), ('sdiv', self.r[rs], self.r[rt])
        elif op == 17 and rs == 16 and fn == 7 and rt == 0:
            self.f[fd] = ('neg.s', self.f[fs])
            self.operations.append(self.f[fd])
        elif op == 17 and rs == 16 and fn == 0:
            # Unlike the previous loop checker, keep even ADD operands ordered.
            self.f[fd] = ('add.s', self.f[fs], self.f[rt])
            self.operations.append(self.f[fd])
        else:
            super().ordinary(word)
        self.r[0] = 0
        if self.r[26:28] != [('entry-gpr', 26), ('entry-gpr', 27)]:
            raise ValueError('Burst proof changed a kernel register')

    def call(self, target):
        ordinal = len(self.calls)
        expected = (source.RANDOM, source.COSINE, source.SINE, source.COSINE,
            source.SMALL if self.compact else source.LARGE)
        if ordinal >= 5 or target != expected[ordinal]:
            raise ValueError('Unknown burst call sequence or binding')
        count = 0 if target == source.RANDOM else 1 if target in (source.COSINE, source.SINE) else 31 if target == source.SMALL else 49
        args = tuple(self.r[4:4 + min(4, count)]) + tuple(self.load(self.r[29] + i * 4, 4) for i in range(4, count))
        self.calls.append((target, args))
        self.epoch = ('after-provider', ordinal)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = ('provider-gpr', ordinal, i)
        for i in range(20):
            self.f[i] = ('provider-fpr', ordinal, i)
        self.hi, self.lo = ('provider-hi', ordinal), ('provider-lo', ordinal)
        self.r[2] = ('provider-result', ordinal)
        if target in (source.COSINE, source.SINE):
            self.f[0] = ('provider-float-result', ordinal, args)
        for i in range(4):
            self.store(self.r[29] + i * 4, 4, ('provider-home', ordinal, i))

    def run(self):
        for _ in range(500):
            if not 0 <= self.pc < len(self.words):
                raise ValueError('Burst proof left its instruction stream')
            word, pc = self.words[self.pc], self.pc
            op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
            if op == 3:
                self.r[31] = ('call-continuation', len(self.calls))
                self.ordinary(self.words[pc + 1])
                self.call(((word & 0x3FFFFFF) << 2) | (source.ENTRY & 0xF0000000))
                self.pc += 2
            elif op == 0 and word & 63 == 8:
                if word != 0x03E00008 or pc != len(self.words) - 2:
                    raise ValueError('Unknown burst return')
                returned = self.r[31]
                self.ordinary(self.words[pc + 1])
                self.returned = (returned, tuple(self.r[i] for i in (*range(16, 24), 28, 29, 30, 31)), tuple(self.f[20:]))
                if self.returned != abi_expected() or len(self.calls) != 5 or len(self.guards) != 2:
                    raise ValueError('Burst ABI or complete path obligation failed')
                return self
            elif op in (4, 5):
                left, right = self.r[rs], self.r[rt]
                if left == right:
                    take = op == 4
                elif left == ARGUMENTS[4] and right == 0:
                    take = not self.compact if op == 4 else self.compact
                    self.guards.append(('compact', self.compact, op))
                else:
                    raise ValueError('Unknown burst branch predicate')
                self.ordinary(self.words[pc + 1])
                delta = ((word & 65535) + 32768) % 65536 - 32768
                if take and delta < 0:
                    raise ValueError('Unexpected backwards burst control')
                self.pc = pc + 1 + delta if take else pc + 2
            else:
                self.ordinary(word)
                self.pc += 1
        raise ValueError('Burst proof exceeded its straight-line path bound')


def prove(raw, normalized):
    for compact in (False, True):
        a, b = (BurstMachine(words, compact).run() for words in (raw, normalized))
        if a.calls != b.calls or a.returned != b.returned or a.guards != b.guards or Counter(a.operations) != Counter(b.operations):
            raise ValueError('Burst ordered value/call/ABI dependency proof failed')
    return dict(paths=2, calls_per_path=5, factory_words=[49, 31],
        full_physical_packets_equal=True, ordered_FP_operation_multiset_equal=True,
        no_commutative_FP_or_constant_arithmetic_lemma_used=True,
        ABI_and_return_equal=True, opaque_providers_and_external_epochs=True,
        no_raw_private_fault_FCSR_or_hardware_equivalence_claim=True)
