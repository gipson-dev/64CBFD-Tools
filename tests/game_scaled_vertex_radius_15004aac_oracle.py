import itertools,json,math,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_scaled_vertex_radius_15004aac_match as p
out=p.out;root=p.root
from tools.experiments import game_scaled_vertex_radius_15004aac_match as p
norm=p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=p.ENTRY;RECORD=0x30000;VERTICES=0x31000;COUNTERS=0x800BE2A0
@dataclass(frozen=True)
class Case:
 vertices:tuple;scales:tuple;radius:int;maximum:int;seed:int=0;phase:int=0

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 m.update({RECORD+i:(i*19+37)&255 for i in range(96)})
 m.update({VERTICES+i:(i*23+41)&255 for i in range(16*max(1,len(c.vertices)))})
 for i in range(6):m[COUNTERS+i]=0
 put(m,RECORD+0x16,len(c.vertices),2);put(m,RECORD+0x28,VERTICES)
 for i,s in enumerate(c.scales):put(m,RECORD+0x2c+4*i,bits(s))
 for i,v in enumerate(c.vertices):
  for j,x in enumerate(v):put(m,VERTICES+16*i+2*j,x,2)
 put(m,RECORD+0x50,c.radius,2);put(m,RECORD+0x52,c.maximum,2)
 for i in range(3):put(m,COUNTERS+2*i,(65535 if c.seed==1 else 17+i),2)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+512}
def reference(c,m):
 m=dict(m);maximum=0
 for v in c.vertices:
  x,y,z=[rounded(float(a)*b) for a,b in zip(v,c.scales)]
  d=math.trunc(rounded(rounded(z*z)+rounded(rounded(x*x)+rounded(y*y))))
  assert 0<=d<=0x7fffffff
  maximum=max(maximum,d)
 if maximum:
  radius=math.trunc(rounded(math.sqrt(rounded(float(maximum)))))
  if c.radius==0:
   put(m,RECORD+0x50,radius,2);put(m,RECORD+0x52,radius,2);idx=1
  elif c.radius<radius or c.maximum<radius:idx=0
  else:idx=2
  at=COUNTERS+2*idx;put(m,at,read(m,at,2)+1,2)
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,entry=ENTRY):
  super().__init__(words,fixture(c),c,entry=entry,arguments=(RECORD,0x12345678),connected=connected)
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,fs,fd,fn=w>>26,(w>>21)&31,(w>>11)&31,(w>>6)&31,w&63
  if op==17 and fmt==20 and fn==32:
   x=self.f[fs];x=x if x<0x80000000 else x-0x100000000;self.f[fd]=bits(rounded(float(x)))
  elif op==17 and fmt==16 and fn==13:
   x=floating(self.f[fs]);assert math.isfinite(x) and -0x80000000<=x<0x80000000;self.f[fd]=math.trunc(x)&0xffffffff
  elif op==17 and fmt==16 and fn==4:
   x=floating(self.f[fs]);assert x>=0 and math.isfinite(x);self.f[fd]=bits(rounded(math.sqrt(x)))
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def load_words():
 global candidate,fixed,retail
 raw,refs=p.payload(out/'independent-selected.o');lookup={v[1]:v[2][1] for v in p.symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())};syms={nm:lookup[nm] for es in refs.values() for _,nm in es};candidate=p.bound_blob(raw,refs,syms);fixed,nrefs=norm.normalize(raw,refs);fixed=p.bound_blob(fixed,nrefs,syms);retail=struct.unpack_from('>81I',(root/'conker/conker.us.bin').read_bytes(),p.ROM)
def cases():
 vertices=((),((0,0,0),),((3,4,0),),((-3,4,-12),),((1,2,3),(-8,4,-2),(0,0,0)))
 return [Case(v,s,r,m,seed) for v,s,r,m,seed in itertools.product(vertices,((1.,1.,1.),(0.5,-2.,1.25)),(0,3,5,20),(0,5,20),(0,1))]
def main():
 load_words()
 assert tuple(fixed)==retail;visits=set();cs=cases()
 for c in cs:
  machines=[]
  for program in (retail,candidate,fixed):
   x=Oracle(program,c);x.run();assert x.r[16:24]==x.before[16:24] and x.r[28:]==x.before[28:] and x.f[20:]==x.before_f[20:];assert public(x.memory)==public(reference(c,x.initial)),c;machines.append(x)
  a,b,z=machines;assert public(a.memory)==public(b.memory);assert (a.memory,a.r,a.f,a.trace)==(z.memory,z.r,z.f,z.trace);visits.update(a.visits)
 report=dict(cases=len(cs),retail_words_visited=sum(ENTRY+4*i in visits for i in range(81)),memory_and_saved_abi_match=True,normalized_complete_state=True,finite_valid_nonaliased_input_only=True,guards=27,source_installed=False)
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
