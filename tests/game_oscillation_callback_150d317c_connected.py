"""Run the original angle helper twice through the recovered callback."""
import itertools,json,struct
from tools.experiments import game_oscillation_callback_150d317c_match as p
from tools.tests import game_oscillation_callback_150d317c_oracle as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
LIMIT=0x800A56A4
class Connected(g.Oracle):
 def hook(self,t):
  assert t==g.SINE;stage=len(self.calls)-1;assert stage in(2,3)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=g.RETURNS[stage];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True
def wrap(value,limit):
 while g.floating(limit)<g.floating(value):value=g.op(value,limit,'-')
 while g.floating(value)<0:value=g.op(value,limit,'+')
 return value
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>24I',rom,0x172018);elf=(p.root/'conker/build/conker.us.elf').read_bytes();limit=struct.unpack_from('>I',elf,elf_slot_offset(elf,LIMIT,4))[0];assert 0<g.floating(limit)<10
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows(elf)};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});connected=dict(zip(range(g.NORMAL,g.NORMAL+96,4),helper));count=0;visits=set()
 for x,y in itertools.product((-20.,-7.,-1.,0.,1.,7.,20.),repeat=2):
  for phase in (0,8):
   c=g.Case(phase=phase);m=Connected(words,c,connected=connected);g.put(m.memory,LIMIT,limit);g.put(m.memory,g.ACTOR+0x128,g.bits(x));g.put(m.memory,g.ACTOR+0x12C,g.bits(y));initial=dict(m.memory)
   expected=dict(initial);px=g.op(g.bits(x),g.op(g.bits(.5),c.step,'*'),'+');py=g.op(g.bits(y),g.op(g.bits(-.25),c.step,'*'),'+');px=wrap(px,limit);py=wrap(py,limit);g.put(expected,g.ACTOR+0x128,px);g.put(expected,g.ACTOR+0x12C,py);g.put(expected,g.ACTOR+0x110,g.op(g.op(g.RETURNS[2],g.bits(2.),'*'),g.bits(10.),'+'));g.put(expected,g.ACTOR+0x114,g.op(g.op(g.RETURNS[3],g.bits(3.),'*'),g.bits(-10.),'+'));g.put(expected,g.ACTOR+0x138,g.bits(2.));expected[g.ACTOR+0x5C]=200
   m.run();assert {a:v for a,v in m.memory.items()if not g.STACK-512<=a<g.STACK+512}=={a:v for a,v in expected.items()if not g.STACK-512<=a<g.STACK+512};assert m.calls==[(g.NORMAL,g.op(g.bits(x),g.bits(.5),'+')),(g.NORMAL,g.op(g.bits(y),g.bits(-.25),'+')),(g.SINE,px),(g.SINE,py)];assert m.r[2]==1 and m.fcsr==c.fcsr;visits.update(pc for pc in m.visits if g.NORMAL<=pc<g.NORMAL+96);count+=1
 r=dict(cases=count,original_angle_helper_words=24,visited_helper_words=len(visits),retail_limit_bits=hex(limit),sine_still_modeled=True,finite_bounded_angles_only=True,source_installed=False);(p.out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
