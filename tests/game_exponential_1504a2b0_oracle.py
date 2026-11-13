"""Finite binary32 guest model; not an FCSR or N64 hardware emulator."""
import math
import random
import struct

from tools.experiments import game_exponential_1504a2b0_match as packet
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put

ENTRY = 0x1504A2B0
SYMBOLS = {'D_800990A0':0x800990A0, 'D_800990A4':0x800990A4, 'D_800990A8':0x800990A8}


def program(path, symbols=SYMBOLS):
    text, funcs, refs = parse_object(path)
    f = funcs[packet.NAME]; a = f['value']; n = f['size']
    return bound_blob(text[a:a+n], {i-a:r for i,r in refs.items() if a <= i < a+n}, symbols)


def fixture(symbols=SYMBOLS):
    memory = {}
    for name, value in [('D_800990A0',0x3F317218), ('D_800990A4',0x7F7FFFFF), ('D_800990A8',0x3F317218)]:
        put(memory, symbols[name], value)
    return memory


def f32(value):
    return floating(bits(value))


def reference(word):
    x = floating(word); magnitude = abs(x)
    if magnitude < 2.0**-23:
        return bits(1.)
    n = math.trunc(f32(magnitude / floating(0x3F317218)))
    if n >= 1025:
        return 0x7F7FFFFF if x >= 0 else 0
    remainder = f32(magnitude-f32(f32(float(n))*floating(0x3F317218)))
    result = term = 1.; index = 1
    while True:
        previous = result
        term = f32(term*f32(remainder/f32(float(index))))
        result = f32(result+term)
        index += 1
        if result == previous:
            break
        assert index < 1000
    for _ in range(n):
        result = f32(result+result)
    return bits(result if x >= 0 else 1.0/result)


class Oracle(TriangleOracle):
    def __init__(self, words, memory, value, entry=ENTRY, connected=None):
        super().__init__(words, memory, entry=entry, arguments=(0,), outputs=(0,0,0), connected=connected)
        self.f[12] = value
        self.initial_mem = dict(memory)

    def execute(self, word):
        op, rs, rt, rd, fd, fn = word>>26, word>>21&31, word>>16&31, word>>11&31, word>>6&31, word&63
        if op == 17 and rs == 16 and fn == 5:
            self.f[fd] = self.f[rd]&0x7FFFFFFF
        elif op == 17 and rs == 16 and fn == 13:
            x = floating(self.f[rd])
            self.f[fd] = (math.trunc(x)&0xFFFFFFFF) if math.isfinite(x) and -2147483648 <= x < 2147483648 else 0x80000000
        elif op == 10:
            self.r[rt] = int(signed(self.r[rs]) < (((word&65535)^32768)-32768))
        else:
            super().execute(word)
        self.r[0] = 0

    def record_call(self, target):
        raise AssertionError(('unexpected call', hex(target)))

    def hook(self, target):
        raise AssertionError(('unexpected call', hex(target)))


def cases():
    values = [bits(v) for v in (0.,-0.,1.,-1.,.01,-.01,.5,-.5,2.,-2.,10.,-10.,80.,-80.,88.,-88.,100.,-100.,700.,-700.,710.,-710.,1000.,-1000.)]
    for n in (0.,2**-23,math.log(2.),2*math.log(2.),80.,88.,100.,700.,710.):
        x = bits(n)
        for delta in (-2,-1,0,1,2):
            if x+delta >= 0:
                values.extend([x+delta, (x+delta)|0x80000000])
    rng = random.Random(1504)
    values.extend(bits(rng.uniform(-715.,715.)) for _ in range(400))
    return sorted(set(values))


def programs(state, symbols=SYMBOLS):
    result = [program(state[n], symbols) for n in ('after','retail','generated','generic')]
    assert result[1] == result[2] == result[3]
    return result


def run(state):
    visited = set(); all_programs = programs(state)
    for value in cases():
        expected = reference(value); states = []
        for words in all_programs:
            m = Oracle(words, fixture(), value).run()
            assert m.f[0] == expected, (hex(value), hex(expected), hex(m.f[0]))
            assert m.memory == m.initial_mem
            states.append((m.f[0], [(e[1],e[2],e[3]) for e in m.events if e[0] == 'R']))
        assert states.count(states[0]) == len(states), (hex(value), states)
        visited.update(m.visits)
    return {'finite_cases':len(cases()), 'raw_retail_and_both_padders':True,
            'retail_words_visited':len(visited), 'scope':'modeled finite binary32; no FCSR or hardware proof'}
