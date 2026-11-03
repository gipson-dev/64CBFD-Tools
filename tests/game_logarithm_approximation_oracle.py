"""Independent guest/native semantics for func_1504A620."""

import re
import struct

from tools.experiments import game_logarithm_approximation_match as source
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_table_range_loader import STACK


LN2 = 0x3F317218
ZERO = 0


def rounded(value):
    try:
        return floating(bits(value))
    except OverflowError:
        return float("-inf") if value < 0 else float("inf")


def rounded_bits(value):
    try:
        return bits(value)
    except OverflowError:
        return 0xFF800000 if value < 0 else 0x7F800000


def reference(input_word):
    """Model each single-precision operation and the retail stop comparison."""
    value = floating(input_word)
    if value < 0.0 or value == 0.0:
        return ZERO
    accumulator = 0.0
    while value >= 2.0:
        value = rounded(value * 0.5)
        accumulator = rounded(accumulator + floating(LN2))
    while value < 1.0:
        value = rounded(value * 2.0)
        accumulator = rounded(accumulator - floating(LN2))
    numerator = rounded(value - 1.0)
    denominator = rounded(value + 1.0)
    ratio = rounded(numerator / denominator)
    ratio_squared = rounded(ratio * ratio)
    term = rounded(2.0 * ratio)
    divisor = 1
    for _ in range(128):
        previous = accumulator
        quotient = rounded(term / rounded(float(divisor)))
        accumulator = rounded(accumulator + quotient)
        term = rounded(term * ratio_squared)
        divisor += 2
        if accumulator == previous:
            return rounded_bits(accumulator)
    raise AssertionError(("logarithm reference did not converge", hex(input_word)))


def input_cases():
    """Return 1,040 finite values spanning signs, exponents and mantissas."""
    values = {
        0x00000000, 0x80000000, 0xBF800000, 0xC0000000, 0xFF800000,
        0x00000001, 0x00000002, 0x007FFFFF, 0x00800000, 0x00800001,
        0x3EFFFFFF, 0x3F000000, 0x3F000001, 0x3F7FFFFF, 0x3F800000,
        0x3F800001, 0x3FFFFFFF, 0x40000000, 0x40000001, 0x40490FDB,
        0x7F000000, 0x7F7FFFFF,
    }
    for exponent in range(1, 255):
        base = exponent << 23
        values.update((base, base | 1, base | 0x3FFFFF, base | 0x7FFFFF))
    state = 0x1504A620
    while len(values) < 1040:
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        word = state & 0x7FFFFFFF
        if word < 0x7F800000:
            values.add(word)
    return tuple(sorted(values)[:1040])


def memory_case(phase=0):
    memory = {STACK + phase + i: 0xA5 for i in range(-0x100, 0x100)}
    for address in (0x800990B0, 0x800990B4):
        for index, byte in enumerate(LN2.to_bytes(4, "big")):
            memory[address + index] = byte
    return memory


class LogarithmOracle(TriangleOracle):
    def __init__(self, words, input_word, phase=0):
        super().__init__(words, memory_case(phase), phase=phase,
                         entry=source.ENTRY, arguments=(0, 0, 0, 0))
        self.f[12] = input_word

    def execute(self, word):
        op, fmt, ft, fs, fn = (word >> 26, word >> 21 & 31,
                               word >> 16 & 31, word >> 11 & 31, word & 63)
        if op == 17 and fmt == 16 and fn == 62:
            self.condition = floating(self.f[fs]) <= floating(self.f[ft])
        else:
            super().execute(word)

    def record_call(self, target):
        raise AssertionError(("unexpected logarithm call", hex(target)))

    def hook(self, target):
        raise AssertionError(("unexpected logarithm hook", hex(target)))


def run_suite(natural_words, retail_words):
    natural_visits, retail_visits = set(), set()
    cases = input_cases()
    for input_word in cases:
        expected = reference(input_word)
        models = [LogarithmOracle(words, input_word).run()
                  for words in (natural_words, retail_words)]
        outputs = [model.f[0] for model in models]
        if outputs != [expected, expected]:
            raise AssertionError((hex(input_word), hex(expected),
                                  [hex(value) for value in outputs]))
        if any(model.calls for model in models):
            raise AssertionError("pure logarithm approximation made a call")
        if any(event[0] == "W" and not STACK - 0x100 <= event[1] < STACK + 0x100
               for model in models for event in model.events):
            raise AssertionError("pure logarithm approximation wrote external memory")
        natural_visits.update(models[0].visits)
        retail_visits.update(models[1].visits)
    natural_unreachable = {source.ENTRY + 0x20, source.ENTRY + 0x38}
    retail_unreachable = {source.ENTRY + 0x24, source.ENTRY + 0x40}
    expected_natural = (set(range(source.ENTRY, source.ENTRY + source.NATURAL_SIZE, 4)) -
                        natural_unreachable)
    expected_retail = (set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)) -
                       retail_unreachable)
    if natural_visits != expected_natural or retail_visits != expected_retail:
        raise AssertionError({
            "natural_missing": sorted(expected_natural - natural_visits),
            "retail_missing": sorted(expected_retail - retail_visits),
        })
    return {
        "cases": len(cases),
        "executions": len(cases) * 2,
        "natural_words_covered": len(natural_visits),
        "retail_words_covered": len(retail_visits),
        "natural_unreachable_duplicate_delay_words": ["0x20", "0x38"],
        "retail_unreachable_duplicate_delay_words": ["0x24", "0x40"],
        "negative_infinity_returns_positive_zero": True,
        "positive_subnormal_normalization_covered": True,
        "NaN_and_positive_infinity_nontermination_not_claimed": True,
    }


def semantic_body(owner_text):
    match = re.search(
        r"f32 func_1504A620\(f32 arg0\) \{\n.*?\n\}", owner_text, re.S)
    if not match:
        raise ValueError("Logarithm approximation semantic body changed")
    return match.group(0)


def controls(body):
    rows = {
        "negative-result": body.replace("return 0.0f;", "return 1.0f;", 1),
        "zero-gate": body.replace("arg0 == 0.0f", "arg0 < 0.0f", 1),
        "upper-threshold": body.replace("mantissa >= 2.0f", "mantissa > 2.0f", 1),
        "upper-scale": body.replace("mantissa *= 0.5f", "mantissa *= 0.25f", 1),
        "upper-constant-sign": body.replace("exponent += D_800990B0", "exponent -= D_800990B0", 1),
        "lower-threshold": body.replace("mantissa < 1.0f", "mantissa <= 1.0f", 1),
        "lower-scale": body.replace("mantissa *= 2.0f", "mantissa *= 4.0f", 1),
        "lower-constant-sign": body.replace("exponent -= D_800990B4", "exponent += D_800990B4", 1),
        "ratio-numerator": body.replace("mantissa - 1.0f", "mantissa - 0.5f", 1),
        "ratio-denominator": body.replace("mantissa + 1.0f", "mantissa + 2.0f", 1),
        "ratio-square": body.replace("ratio * ratio", "ratio + ratio", 1),
        "term-scale": body.replace("2.0f * ratio", "1.0f * ratio", 1),
        "divisor-start": body.replace("i = 1;", "i = 3;", 1),
        "divisor-step": body.replace("i += 2;", "i += 4;", 1),
        "convergence": body.replace("exponent != result", "exponent == result", 1),
    }
    for name, changed in rows.items():
        if changed == body:
            raise ValueError("Ineffective logarithm source control: " + name)
    return rows


def native_harness(body, cases=None):
    cases = cases or input_cases()
    rows = ",\n".join("{0x%08Xu,0x%08Xu}" % (word, reference(word))
                      for word in cases)
    return r'''
typedef unsigned int u32; typedef int s32; typedef float f32;
f32 D_800990B0 = 0x1.62E430p-1f;
f32 D_800990B4 = 0x1.62E430p-1f;
static u32 word(f32 value) { union { u32 u; f32 f; } data; data.f=value; return data.u; }
static f32 number(u32 value) { union { u32 u; f32 f; } data; data.u=value; return data.f; }
''' + body + r'''
struct Case { u32 input, expected; };
static const struct Case cases[] = {
''' + rows + r'''
};
static int run(void) {
    u32 index;
    for (index=0; index<sizeof(cases)/sizeof(cases[0]); index++) {
        if (word(func_1504A620(number(cases[index].input))) != cases[index].expected)
            return 1;
    }
    return 0;
}
void _start(void) {
    int result=run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(result));
    __builtin_unreachable();
}
'''
