"""Bounded camera reset model with helper-mutated camera state."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_camera_reset_15127eb8_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
CAMERA=0x30000;CHILD0=0x32000;CHILD1=0x33000;ACTOR0=0x34000;ACTOR1=0x35000;VIEW0=0x50000;VIEW1=0x51000
VIEWPTR=0x800BE628;SLOTS=0x800DBFF4;ACTORS=0x800CC2D0
ENABLE=0x151239CC;RESET=0x151C9ED4;DIRECTION=0x1510B32C;RELEASE=0x150627D4
u32=lambda n:n&0xffffffff
@dataclass(frozen=True)
class Case:
 slot:int;actor_index:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for base,size in ((CAMERA,0x900),(CHILD0,0x200),(CHILD1,0x200),(ACTOR0,0x32c),(ACTOR1,0x32c),(VIEW0,0x800),(VIEW1,0x800),(ACTORS,0x32c*4),(SLOTS,32)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(size)})
 put(m,CAMERA+0x3d4,CHILD0);put(m,CAMERA+0x3d0,ACTOR0);m[CAMERA+0x23d]=c.slot;m[ACTOR0+0x65]=c.actor_index;m[ACTOR1+0x65]=c.actor_index;put(m,VIEWPTR,VIEW0)
 return m
def public(m):return{k:v for k,v in m.items()if not STACK-2048<=k<STACK+2304}
def effect(m,c,target):
 if target==ENABLE and c.mutation&1:put(m,CAMERA+0x3d4,CHILD1)
 if target==RESET and c.mutation&2:m[CAMERA+0x23d]=(c.slot+1)%4
 if target==DIRECTION and c.mutation&4:put(m,VIEWPTR,VIEW1);m[CAMERA+0x23d]=(c.slot+2)%4
 if target==RELEASE and c.mutation&8:put(m,CAMERA+0x3d0,ACTOR1);m[CAMERA+0x23d]=(c.slot+3)%4

def reference(c,initial):
 m=dict(initial);calls=[(ENABLE,(CAMERA,1))];effect(m,c,ENABLE);child=read(m,CAMERA+0x3d4);m[child+0x197]=0;calls.append((RESET,(CAMERA,)));effect(m,c,RESET)
 for off in (0x19c,0x1a0,0x1a4,0x1a8):put(m,CAMERA+off,0)
 slot=m[CAMERA+0x23d];calls.append((DIRECTION,(slot,0,0,0x3f800000)));effect(m,c,DIRECTION);slot=m[CAMERA+0x23d];put(m,read(m,VIEWPTR)+slot*0x180+0x84,0x3f800000)
 actor=read(m,CAMERA+0x3d0);calls.append((RELEASE,(actor,)));effect(m,c,RELEASE);slot=m[CAMERA+0x23d];m[SLOTS+slot]=2;actor=read(m,CAMERA+0x3d0);idx=m[actor+0x65];selected=actor if idx==0 else ACTORS+(idx-1)*0x32c;mask=~(1<<slot)&255;m[selected+0x2fc]&=mask;slot=m[CAMERA+0x23d];mask=~(1<<slot)&255;m[selected+0x74]&=mask;m[CAMERA+0x23c]=1
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  self.c=c;super().__init__(words,fixture(c),c,entry=p.ENTRY,arguments=(CAMERA,));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==0x27:
   rs,rt,rd=w>>21&31,w>>16&31,w>>11&31;self.r[rd]=u32(~(self.r[rs]|self.r[rt]));self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  count={ENABLE:2,RESET:1,DIRECTION:4,RELEASE:1};assert t in count,hex(t);self.calls.append((t,tuple(self.arguments(count[t]))))
 def hook(self,t):
  effect(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});truth=struct.unpack('>77I',(p.out/'original-function.bin').read_bytes());assert tuple(words)==truth;cases=[Case(slot,idx,mut,8*(i&1),i%3)for i,(slot,idx,mut)in enumerate(itertools.product(range(4),range(4),(0,1,2,4,8,3,12,15)))];visits=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,calls=reference(c,m.initial);assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits.update(m.visits)
 result=dict(cases=len(cases),words_visited=sum(p.ENTRY+4*i in visits for i in range(77)),retail_equals_compiled=True,helper_state_mutations=True,slot_range='0..3',helpers_modeled=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
