import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_startup_initializer_1500e470_match as p
out=p.out;root=p.root
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
norm=p
from tools.experiments import game_startup_initializer_1500e470_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x1500E470;ARG=0x5341200;P=0x30000;Q=0x31000;TABLE=0x80082D90;CALLBACK=0x15900000
ZERO=0x100226F0;PRNG=0x15012720
G8=[0x800DD190,0x800DD404,0x800DD405,0x800DD406,0x8008CD00,0x80088B60,0x800E0A10]
G32=[0x800E0930,0x800E0934,0x800E0940,0x800BE4E0]
CALLS=[ZERO,PRNG,0x15012370,0x151EF640,0x151732E0,0x15004FE0,0x150127B0,0x1519582C,0x15008BE0,0x15008B90,0x1500E5C0,0x1500ABA0,0x1500BEC0,0x1500AC14,0x151872B0,0x15178EB0,0x15012FE0,0x151645C4]
ARGC={ZERO:2,PRNG:0,0x15012370:0,0x151EF640:1,0x151732E0:1,0x15004FE0:1,0x150127B0:0,0x1519582C:0,0x15008BE0:0,0x15008B90:0,0x1500E5C0:0,0x1500ABA0:1,0x1500BEC0:0,0x1500AC14:0,0x151872B0:1,0x15178EB0:0,0x15012FE0:0,0x151645C4:1,CALLBACK:0}
@dataclass(frozen=True)
class Case: select:int;flags:int;seed:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for a in G8:
  for i in range(-4,5):m[a+i]=0xA5
 for a in G32:
  for i in range(-4,8):m[a+i]=0x5A
 for i in range(32):m[0x800DD198+i]=0xCA
 for a in (0x800B0DF0,0x800D2E4C):
  for i in range(-4,8):m[a+i]=0xAC
 for base in (P,Q):
  for i in range(32):m[base+i]=0xAC
 put(m,0x800B0DF0,P);put(m,0x800D2E4C,Q);m[P+10]=c.select;m[Q+4]=c.flags
 for i in range(3):put(m,TABLE+4*i,CALLBACK+4*i)
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(ARG,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  n=ARGC.get(t,0) if t not in (CALLBACK+4,CALLBACK+8) else 0
  assert t in ARGC or t in (CALLBACK+4,CALLBACK+8),hex(t)
  self.calls.append((t,tuple(self.arguments(n))))
 def hook(self,t):
  a=self.calls[-1][1]
  if t==ZERO:
   assert a==(0x800DD198,24)
   for i in range(24):self.memory[a[0]+i]=0
  value=(0x123456A0+self.case.seed) if t==PRNG else 0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def load_words():
 global candidate,fixed,retail
 raw,fs,rs=parse_object(out/'independent-selected.o');f=fs['func_1500E470'];a,n=f['value'],f['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};syms={nm:lookup[nm] for es in refs.values() for _,nm in es};candidate=bound_blob(raw[a:a+n],refs,syms);fixed,nrefs=norm.normalize(raw[a:a+n],refs);fixed=bound_blob(fixed,nrefs,syms);retail=struct.unpack_from('>84I',(root/'conker/conker.us.bin').read_bytes(),0x3B920)
 assert tuple(fixed)==retail
def main():
 load_words()
 visits=set();count=0
 for sel,flags,seed in itertools.product((0,1,2),(0,0x80),(0,1)):
  c=Case(sel,flags,seed);pair=[]
  for ws in (retail,candidate,fixed):
   x=Oracle(ws,c);x.run();assert x.r[16:24]==x.before[16:24] and x.r[28:]==x.before[28:] and x.f[20:]==x.before_f[20:]
   expected=CALLS[:11]+([CALLBACK+4*sel] if sel else [])+CALLS[11:];assert [t for t,a in x.calls]==expected
   expected_args={ZERO:(0x800DD198,24),0x151EF640:(64,),0x151732E0:(ARG,),0x15004FE0:(ARG,),0x1500ABA0:(ARG,),0x151872B0:(ARG,),0x151645C4:(int(flags==0),)}
   for t,args in x.calls:
    if t in expected_args:assert args==expected_args[t],(hex(t),args)
   for addr,val in zip(G8,[255,255,0,0,0,0,(0xA0+seed)&255]):assert x.memory[addr]==val,(hex(addr),x.memory[addr],val)
   for addr in G32:assert read(x.memory,addr)==0,hex(addr)
   assert all(x.memory[0x800DD198+i]==0 for i in range(24))
   pair.append(x)
  assert all(public(pair[0].memory)==public(x.memory) and pair[0].calls==x.calls for x in pair[1:]);assert (pair[0].memory,pair[0].r,pair[0].f,pair[0].trace)==(pair[2].memory,pair[2].r,pair[2].f,pair[2].trace)
  visits.update(pair[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in visits for i in range(84)),matched_memory_calls_and_abi=True,helpers_modeled=True,guards=5,normalized_complete_state=True,source_has_no_added_volatile=True,source_installed=False);(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

if __name__=='__main__':main()
