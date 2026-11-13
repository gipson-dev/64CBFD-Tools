"""Execute the retail call-site window with its child and real length helper."""
from pathlib import Path
import importlib.util, itertools, json, struct, sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
from tools.tests import game_line_record_1512dd50_guest as g
START, END = 0x1512f58c, 0x1512fdf0
parent = list(struct.unpack_from('>10I', g.rom, 0x15ca3c))

class Caller(g.Machine):
    def __init__(self, child, memory, case):
        connected = dict(g.connected)
        connected.update({g.ENTRY+4*i:w for i,w in enumerate(child)})
        FactoryOracle.__init__(self, parent, memory, case, entry=START, s={}, connected=connected, arguments=())
        self.r[16] = g.OWNER
        self.r[1] = 0xfffffff7
        self.code = WindowCode(self.code, self)
        self.code.ends = (END,)
    def record_call(self, target):
        if target == g.ENTRY:
            self.calls.append((target, (self.r[4],)))
        else:
            super().record_call(target)

programs = [bound_blob(*payload(out/p, 'func_1512DD50'), {'func_150AD930':g.HELPER})
            for p in ('retail.o', 'explicit-padded.o')]
assert programs[0] == programs[1]
count = 0
for flags, value, phase in itertools.product((0,8,0xffffffff,0x81234567), (0,0x80000081,0xffffffff), (0,8)):
    c = g.Case((1,-2,3), 3, (0.5,1.0,2.0,-0.25), value, ~value & 0xffffffff, 0xe1, phase)
    initial = g.fixture(c)
    put(initial, g.OWNER+0x84, flags)
    put(initial, STACK+phase+0x24, 0x87654321)
    expected_input = initial.copy()
    put(expected_input, g.OWNER+0x84, (flags | 0x200) & 0xfffffff7)
    put(expected_input, g.OWNER+0x134, 0)
    expected, vector = g.reference(expected_input, c)
    for program in programs:
        machine = Caller(program, initial.copy(), c)
        try:
            machine.run()
        except WindowBoundary:
            pass
        else:
            raise AssertionError('Expected continuation boundary')
        public = {a:v for a,v in machine.memory.items() if not STACK-512 <= a < STACK+512}
        assert public == expected
        assert machine.calls == [(g.ENTRY,(g.OWNER,)), (g.HELPER,vector)]
        assert machine.r[31] == 0x87654321
    count += 1
report = {'caller_window':hex(START), 'continuation':hex(END), 'cases':count,
          'streams':len(programs), 'connected_retail_helper':True, 'bounded_window_only':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
