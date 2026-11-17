"""Concrete ordered FP input bits and coefficient loads; no FCSR proof."""
from collections import Counter
from tools.tests import game_strip_update_151ad174_private_oracle as o


class Trace(o.Oracle):
    def __init__(self, *args):
        self.fp = []
        self.loads = Counter()
        super().__init__(*args)

    def get(self, address, size):
        for name in ('D_800A9280', 'D_800A9284', 'D_800A9288'):
            if address == o.SYMS[name]:
                self.loads[name] += 1
        return super().get(address, size)

    def execute(self, word):
        op, fmt, ft, fs, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word & 63
        if op == 17 and fmt in (16, 17, 20) and fn != 6:
            first = self.f[fs] if fmt != 17 else self.f[fs + 1] << 32 | self.f[fs]
            operands = (first,)
            if fn in (0, 1, 2, 3, 50, 60, 62):
                second = self.f[ft] if fmt != 17 else self.f[ft + 1] << 32 | self.f[ft]
                operands += (second,)
            self.fp.append((fmt, fn, operands))
        return super().execute(word)


def compare(truth, candidate, case):
    initial = o.fixture(case)
    expected, calls = o.reference(initial, case)
    left = Trace(truth, initial, case).run()
    right = Trace(candidate, initial, case).run()
    for execution in (left, right):
        assert o.public(execution.memory) == o.public(expected), ('public', o.asdict(case))
        assert execution.service.calls == calls, ('calls', o.asdict(case))
        assert tuple(execution.r[16:24]) + (execution.r[28], execution.r[29], execution.r[30]) == execution.saved_g
        assert tuple(execution.f[20:]) == execution.saved_fp
    assert left.fp == right.fp, ('ordered FP', o.asdict(case))
    assert left.loads == right.loads, ('coefficient loads', o.asdict(case))
    expected_loads = 1 if case.count >= 2 else 0
    assert all(left.loads[name] == expected_loads for name in ('D_800A9280', 'D_800A9284', 'D_800A9288'))
    return left, right


def controls(truth, candidate):
    case = o.Case(seed=7, owner=1, impulse=1, pattern=1)
    baseline = Trace(candidate, o.fixture(case), case).run()
    controls = []
    # These operand swaps preserve the finite arithmetic results, so a public
    # output check alone cannot detect them. The ordered-bit trace must reject.
    for tag, index, expected in [('gravity-multiply-order', 266, 0x46024082),
                                 ('tail-addition-order', 395, 0x4614B500)]:
        bad = candidate[:]
        word = bad[index]
        assert word == expected, ('control instruction changed', tag)
        ft, fs = word >> 16 & 31, word >> 11 & 31
        bad[index] = (word & ~((31 << 16) | (31 << 11))) | fs << 16 | ft << 11
        execution = Trace(bad, o.fixture(case), case).run()
        assert o.public(execution.memory) == o.public(baseline.memory)
        assert execution.service.calls == baseline.service.calls
        assert execution.fp != baseline.fp, ('ineffective FP control', tag)
        try:
            compare(truth, bad, case)
        except AssertionError as error:
            assert error.args[0][0] == 'ordered FP', error
        else:
            raise AssertionError(('operand swap accepted', tag))
        controls.append(dict(name=tag, changed_word=index, ordered_trace_rejected=True,
                             sampled_public_bytes_and_calls_unchanged=True))
    return controls
