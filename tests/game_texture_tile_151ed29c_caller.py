"""Run the original drawing-helper call window through its return."""
from pathlib import Path
import importlib.util,itertools,json,os,struct,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
from tools.tests import game_texture_tile_151ed29c_guest as g
g.programs[1]=bound_blob(*payload(out/os.environ.get('TILE_OBJECT','coords-02.o'),'func_151ED29C'),g.symbols)
start,end=0x151ed46c,0x151ed48c;window=list(struct.unpack_from('>8I',g.rom,start-0x15000000+0x2d4b0))
class Caller(g.Machine):
    def __init__(self,program,m):
        code={g.entry+4*i:w for i,w in enumerate(program)};code[end]=0
        super().__init__(window,m,Case(),entry=start,s={},arguments=(),connected=code)
        self.r[16]=g.commands;self.r[18]=g.image
        self.code=WindowCode(self.code,self);self.code.ends=(end,)
    def record_call(self,t):
        assert t==g.entry;self.calls.append((t,self.r[4],self.r[5],self.r[6]))
cases=0
for w,h,fmt,size in itertools.product((0,1,3,16,255,65535),(0,1,4,65535),(0,3,7),range(4)):
    initial=g.fixture(w,h,fmt,size)
    for i in range(0x80,0x100):initial[STACK+i]=(i*13+3)&255
    expected=initial.copy();g.put(expected,STACK+0x9c,0)
    expected=g.reference(expected,sizeout=STACK+0xb0)
    for p in g.programs:
        machine=Caller(p,initial.copy())
        try:machine.run()
        except WindowBoundary:pass
        else:raise AssertionError('Expected caller continuation')
        assert machine.memory==expected and machine.r[16]==g.commands+32
        assert machine.calls==[(g.entry,g.commands,g.image,STACK+0xb0)]
    cases+=1
report={'caller':'func_151ED430','call_site':'0x151ed478','cases':cases,'streams':2,
        'stack_output_and_delay_slot':True,'bounded_window_only':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
