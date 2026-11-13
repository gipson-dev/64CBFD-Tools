"""Original indirect caller window, through the next helper boundary."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable'
from tools.tests import game_intro_init_15010880_guest as g
PARENT=0x1500e53c;NEXT=0x1500aba0;MODE=g.symbols['D_800B0DF0'];TABLE=g.symbols['D_80082D90'];OBJECT=0x340000
rom=Path('conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>12I',rom,0x3b9ec))
assert struct.unpack_from('>I',rom,0x2278a0)[0]==g.ENTRY and TABLE+20*4==0x80082de0
class Stop(Exception):pass
class Caller(g.Machine):
 def __init__(self,child,m,c):
  connected={g.ENTRY+4*i:w for i,w in enumerate(child)}
  FactoryOracle.__init__(self,parent,m,c,entry=PARENT,s=g.symbols,arguments=(),connected=connected)
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,()));return
  if t==NEXT:self.calls.append((t,tuple(self.arguments(1))));return
  super().record_call(t)
 def hook(self,t):
  if t==NEXT:raise Stop
  super().hook(t)
def main():
 programs=[bound_blob(*payload(out/p,g.NAME),g.symbols) for p in ('retail.o','padded.o')];assert programs[0]==programs[1]
 count=0
 for mode,flag,result,am,fm,phase in itertools.product((0,20),(0,0x40),(0,1),(0,1),(0,1,2,3),(0,8)):
  c=g.Case(0x81234567,flag,result,am,fm,phase);initial=g.fixture(c);initial.update({MODE+i:0 for i in range(-4,12)});initial.update({TABLE+i:0 for i in range(4*24)});initial.update({OBJECT+i:0 for i in range(32)})
  put(initial,MODE,OBJECT);initial[OBJECT+10]=mode;put(initial,TABLE+20*4,g.ENTRY)
  if mode:
   expected,calls=g.reference(initial,c);calls=[(g.ENTRY,())]+calls
  else:expected,calls=g.public(initial),[]
  calls.append((NEXT,(read(initial,STACK+phase+0x18),)))
  for program in programs:
   m=Caller(program,initial.copy(),c)
   try:m.run()
   except Stop:pass
   else:raise AssertionError('Expected next-helper boundary')
   assert g.public(m.memory)==expected and m.calls==calls,(c,mode,m.calls,calls)
  count+=1
 report={'caller':'func_1500E470','window_start':hex(PARENT),'next_helper':hex(NEXT),'table_index':20,'cases':count,'streams':2,'bounded_window_only':True}
 (out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
