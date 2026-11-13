"""Original power-function call window with the exponential body connected."""
import itertools
import struct

from tools.experiments import game_exponential_1504a2b0_match as packet
from tools.tests import game_exponential_1504a2b0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary

START, END = 0x1504A4F0, 0x1504A5BC


class Caller(g.Oracle):
    def __init__(self, window, program, left, right):
        connected = dict(zip(range(g.ENTRY, g.ENTRY+4*len(program), 4), program))
        connected[END] = 0
        super().__init__(window, g.fixture(), 0, entry=START, connected=connected)
        self.f[0] = left; self.f[14] = right
        self.code = WindowCode(self.code, self); self.code.ends = (END,)

    def record_call(self, target):
        assert target == g.ENTRY
        self.calls.append((target, self.f[12]))


def run(state):
    rom = (packet.ROOT/'conker/conker.us.bin').read_bytes()
    window = struct.unpack_from('>5I', rom, START-0x15000000+0x2D4B0)
    assert window == (0x460E0302,0x0D4128AC,0,0x1000002F,0x46000506)
    count = 0
    for a, b in itertools.product((-.75,-.25,0.,.125,1.,4.,15.), (-5.,-1.,.25,1.,3.)):
        left, right = g.bits(a), g.bits(b)
        arg = g.bits(g.f32(a*b)); expected = g.reference(arg)
        for program in g.programs(state):
            m = Caller(window, program, left, right)
            try:
                m.run()
                raise AssertionError('caller escaped its window')
            except WindowBoundary:
                pass
            assert m.calls == [(g.ENTRY, arg)] and m.f[20] == expected, (a,b,m.calls,m.f[20],expected)
        count += 1
    return {'cases':count, 'caller':'func_1504A400', 'window':'0x1504A4F0..0x1504A500',
            'raw_retail_and_both_padders':True}
