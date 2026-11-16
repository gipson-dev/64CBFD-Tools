"""Independent ordered descriptor/call model and complete nonfaulting MIPS state."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_owner_setup_151a3390_recovery as m
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,OWNER,MARK=0x151A3390,0x30000,0x50000
TARGETS=(0x151A3504,0x151A4590,0x151A499C,0x10010154,0x15160A58)
COUNTS=dict(zip(TARGETS,(2,2,2,5,16)))
BITS=(0,0x80000000,1,0x3F800001,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)
data=lambda mem,p,n:bytes(mem[p+i]for i in range(n))
public=lambda mem:{p:v for p,v in mem.items()if not STACK-2048<=p<STACK+512}

@dataclass(frozen=True)
class Case:
 seed:int=0
 mutation:int=0
 alias:int=0
 phase:int=0
 home_mutation:int=0
 channel:int=0

def cases():return[Case(i,mutation,alias,(i&1)*8,mutation,(i|((0,0x12340000,0xFFFFFF00,0x80000000)[i%4])))for i in range(256)for mutation in range(2)for alias in range(3)]
def owner(c):return OWNER if not c.alias else STACK+c.phase-48+(0 if c.alias==1 else 5)-0x3B

def fixture(c):
 mem={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,512)}
 mem.update({OWNER+i:(i*13+c.seed)&255 for i in range(128)})
 mem[owner(c)+0x3B]=c.seed
 put(mem,0x800A8D50,BITS[c.seed%8]);put(mem,0x800A8D54,BITS[(c.seed+3)%8])
 for i in range(5):put(mem,MARK+4*i,0)
 return mem

def effect(mem,c,ordinal,home):
 put(mem,MARK+4*ordinal,0x12340000+ordinal)
 if c.mutation:
  mem[owner(c)+0x3B]^=0x51+ordinal
  put(mem,0x800A8D50,0xBF800000+ordinal);put(mem,0x800A8D54,0x40000000+ordinal)
  for i in range(48):mem[home-48+i]^=0x35+ordinal
 if c.home_mutation:mem[home+7]=(c.channel+ordinal*29+7)&255

def reference(c,initial=None):
 mem=fixture(c)if initial is None else dict(initial);home=STACK+c.phase;p=home-48;v=home-60
 put(mem,home+4,c.channel);put(mem,p,owner(c));mem[p+4]=mem[owner(c)+0x3B];mem[p+5]=1
 for at in(8,12,16):put(mem,p+at,0)
 for at,value in((0x2B,1),(0x2C,255),(0x2D,8),(0x2E,31),(0x28,2),(0x29,4),(0x2A,1)):mem[p+at]=value
 for at,value in((0x18,170),(0x1A,40),(0x1C,7)):put(mem,p+at,value,2)
 put(mem,p+0x14,read(mem,0x800A8D50));put(mem,p+0x20,0x41F00000);put(mem,p+0x24,read(mem,0x800A8D54))
 packets=[data(mem,p,48)];calls=[]
 for ordinal,target in enumerate(TARGETS):
  channel=mem[home+7]
  if ordinal==0:args=(p,channel)
  elif ordinal in(1,2):args=(owner(c),channel)
  elif ordinal==3:args=(0x1AA,owner(c),0x55F0,1000,4000)
  else:
   for i in range(3):put(mem,v+4*i,0)
   packets.append(data(mem,v,12));args=(owner(c),1,v,2,300,80,255,255,117,255,0,0xFFFFFFFF,0,0,channel,1)
  calls.append((target,args));effect(mem,c,ordinal,home)
 return mem,calls,packets

class Machine(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None):
  super().__init__(words,fixture(c),c,entry=entry,arguments=(owner(c),c.channel),connected=connected)
  self.packets=[];self.frames=[]
  self.f[20:22]=[BITS[c.seed%8],BITS[(c.seed+5)%8]];self.initial_fp=self.f[:];self.initial_regs=self.r[:];self.saved_f=self.f[20:]
 def record_call(self,target):
  assert target in COUNTS,('unexpected provider',hex(target));ordinal=len(self.calls)
  args=tuple(self.arguments(COUNTS[target]));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==TARGETS[0]:self.packets.append(data(self.memory,args[0],48))
  if target==TARGETS[-1]:self.packets.append(data(self.memory,args[2],12))
  self.frames.append(data(self.memory,STACK+self.case.phase-152,168))
 def hook(self,target):
  ordinal=len(self.calls)-1;effect(self.memory,self.case,ordinal,STACK+self.case.phase)
  for i in range(max(4,COUNTS[target])):self.put(self.r[29]+4*i,0xB5000000+ordinal*32+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg+ordinal*32
  self.f[:20]=[0xA5000000+i+ordinal*32 for i in range(20)]
  self.hi,self.lo=0xABC00000+ordinal,0xDEF00000+ordinal;self.condition=bool(ordinal&1)
  self.r[2]=(0x80000000+self.case.seed*0x10203+ordinal)&0xFFFFFFFF

def signature(q):return q.memory,tuple(q.r),tuple(q.f),q.hi,q.lo,q.condition,q.calls,q.packets,q.frames,q.events

def check(words,c):
 expected,calls,packets=reference(c);q=Machine(words,c)
 try:q.run()
 except AssertionError as error:
  if not str(error)and q.f[20:]!=q.saved_f:raise AssertionError(('saved FPR',q.f[20:],q.saved_f))from error
  raise
 assert q.calls==calls,('calls',c,q.calls,calls)
 assert q.packets==packets,('packets',c,[p.hex()for p in q.packets],[p.hex()for p in packets])
 assert public(q.memory)==public(expected),('public memory',c)
 assert all(q.r[i]==q.initial_regs[i]for i in(*range(16,24),28,29,30,31)),('saved GPR',c)
 assert q.f[20:]==q.initial_fp[20:],('saved FPR',c)
 assert q.r[2]==(0x80000000+c.seed*0x10203+4)&0xFFFFFFFF
 return q

def main():
 m.check_inputs();streams=m.programs();visited={label:set()for label in streams};corpus=cases()
 for c in corpus:
  baseline=None
  for label,words in streams.items():
   q=check(words,c);visited[label].update(q.visits)
   if baseline is None:baseline=signature(q)
   else:assert signature(q)==baseline,('full machine state',label,c)
 assert all(len(v)==93 for v in visited.values()),{k:len(v)for k,v in visited.items()}
 report=dict(cases_per_stream=len(corpus),streams=list(streams),words_visited={k:len(v)for k,v in visited.items()},five_call_order=True,all_16_final_arguments=True,complete_frame_and_register_equality=True,saved_F20_F21=True,guest_parameter_home_mutation=True,guest_owner_identity_aliases=True,all_48_descriptor_bytes=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
