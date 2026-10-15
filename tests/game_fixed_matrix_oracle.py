"""Bounded finite CVT rounding model on the established instruction oracle."""
from fractions import Fraction
import math

from tools.experiments import game_fixed_matrix_restoration as source
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating

INPUT, OUTPUT = 0x22000, 0x24000
PATTERNS = (
    tuple(bits(x / 65536.0) for x in (1.5, -1.5, 2.5, -2.5, 0.5, -0.5, 2.25, -2.25,
        3.75, -3.75, 0.25, -0.25, 7.5, -7.5, 0, -0.0)),
    tuple(bits(x) for x in (0.0, -0.0, 1, -1, 32767.998046875, -32768, 0.125, -0.125,
        2, -2, 123.5, -123.5, 0.25, -0.25, 0.5, -0.5)),
    tuple(bits(x / 65536.0) for x in (1.25, -1.25, 1.75, -1.75, 3.5, -3.5, 9.5, -9.5,
        31.25, -31.25, 63.75, -63.75, 127.5, -127.5, 1, -1)),
)


def integer(word, mode):
    value = floating(word)
    assert math.isfinite(value), 'outside finite conversion domain'
    exact = Fraction.from_float(value)
    if mode == 0:
        quotient, remainder = divmod(exact.numerator, exact.denominator)
        result = quotient + (remainder * 2 > exact.denominator or
            remainder * 2 == exact.denominator and quotient & 1)
    else:
        result = (math.trunc, math.ceil, math.floor)[mode - 1](exact)
    assert -0x80000000 <= result <= 0x7FFFFFFF, 'outside valid signed conversion domain'
    return result & 0xFFFFFFFF


def scaled(word):
    value = floating(word)
    assert math.isfinite(value), 'outside finite multiplication domain'
    result = bits(value * 65536.0)
    assert Fraction.from_float(floating(result)) == Fraction.from_float(value) * 65536, 'inexact multiply outside bounded domain'
    return result


def fixture(pattern=0, rotation=0, output=OUTPUT, alias=False):
    memory = {machine.STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x600, 0x180)}
    for base in (INPUT, output):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(-128, 384)})
    values = tuple(bits((0, 1 / 65536.0, 0.125, 1)[(i + pattern) % 4]) for i in range(16)) if alias else PATTERNS[pattern]
    for i in range(16):
        put(memory, INPUT + i * 4, values[(i + rotation) % 16])
    return memory


def reference(memory, destination=OUTPUT, mode=0, source_address=INPUT):
    memory, events = dict(memory), []
    for pair in range(8):
        values = []
        for element in (pair * 2, pair * 2 + 1):
            address = source_address + element * 4
            word = read(memory, address)
            events.append(('R', address, 4, word))
            values.append(integer(scaled(word), mode))
        first, second = values
        for address, value in ((destination + 32 + pair * 4, first & 65535),
                (destination + pair * 4, first >> 16),
                (destination + 34 + pair * 4, second & 65535),
                (destination + 2 + pair * 4, second >> 16)):
            put(memory, address, value, 2)
            events.append(('W', address, 2, value))
    return memory, events


class FixedOracle(machine.BurstOracle):
    def __init__(self, words, memory, destination=OUTPUT, mode=0, phase=0, fault=None, entry=source.ENTRY):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(INPUT, destination), fault=fault)
        self.code = faults.TrackedCode(self.code, self)
        self.current_pc, self.delay_of = entry, None
        self.rounding_mode, self.fault, self.accesses = mode, fault, 0

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 in (13, 36):
            mode = 1 if word & 63 == 13 else self.rounding_mode
            self.f[word >> 6 & 31] = integer(self.f[word >> 11 & 31], mode)
        else:
            super().execute(word)

    def access(self):
        if self.own_instruction:
            if self.accesses == self.fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        raise AssertionError('Unexpected fixed converter call: ' + hex(target))
