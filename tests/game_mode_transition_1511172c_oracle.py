"""Private independent state-transition oracle; no match credited."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_mode_transition_1511172c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
STATEPTR=0x800B0DF0; FLAG=0x80038080; TABLE=0x800891BC; BLOCK=0x800DBE80
RELEASE=0x10004074; RESET=0x15111858; CLEAN=0x1510D694; LOAD=0x1502B7F0
STATE0=0x30000;STATE1=0x31000;TABLEDATA=0x70000
u32=lambda n:n&0xffffffff
@dataclass(frozen=True)
class Case:
 mode:int;current:int;status:int;flag:int;allocated:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for base in (STATE0,STATE1):m.update({base+i:(i*23+c.seed*7+0x31)&255 for i in range(64)})
 put(m,STATEPTR,STATE0);put(m,BLOCK,0x80000 if c.allocated else 0);m[FLAG]=c.flag;m[STATE0+8]=c.status;m[STATE0+9]=c.current;m[STATE1+8]=4;m[STATE1+9]=7
 for i in range(256):put(m,TABLE+4*i,TABLEDATA+4*i);put(m,TABLEDATA+4*i,0x1000+i*512)
 return m
def public(m):return {k:v for k,v in m.items()if not STACK-2048<=k<STACK+2304}
def effect(m,c,target,n):
 if target==CLEAN and n==0 and c.mutation&1:put(m,STATEPTR,STATE1)
 if target==CLEAN and n==0 and c.mutation&2:put(m,TABLE+7*4,TABLEDATA+8*4)
 if target==RELEASE and c.mutation&4:put(m,STATEPTR,STATE1)
 if target==RELEASE and c.mutation&8:put(m,BLOCK,0x81000)
def reference(c,initial):
 m=dict(initial);calls=[];mode=u32(c.mode);s=read(m,STATEPTR)
 if mode==1:
  m[s+8]=1;block=read(m,BLOCK)
  if block:calls.append((RELEASE,(block,)));effect(m,c,RELEASE,0)
  calls.append((RESET,()))
 elif mode!=m[s+9] and m[s+8]==4:
  if m[FLAG]:
   for i in range(360):
    state=read(m,STATEPTR);slot=m[state+9];record=read(m,TABLE+slot*4);value=u32(read(m,record)+i);calls.append((CLEAN,(value,)));effect(m,c,CLEAN,i)
  block=read(m,BLOCK);calls.append((RELEASE,(block,)));effect(m,c,RELEASE,0)
  state=read(m,STATEPTR);m[state+9]=mode&255;state=read(m,STATEPTR);calls.append((LOAD,(BLOCK,2,13,m[state+9])))
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  self.c=c;self.cleans=0;super().__init__(words,fixture(c),c,entry=p.ENTRY,arguments=(u32(c.mode),));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={RELEASE:1,RESET:0,CLEAN:1,LOAD:4};assert t in counts,hex(t);self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  effect(self.memory,self.c,t,self.cleans)
  if t==CLEAN:self.cleans+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};candidate=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});retail=struct.unpack('>75I',(p.out/'original-function.bin').read_bytes());assert tuple(candidate)==retail
 cases=[Case(mode,current,status,flag,allocated,mutation,8*(i&1),i%3) for i,(mode,current,status,flag,allocated,mutation) in enumerate(itertools.product((1,4,6,0x101),(1,4),(0,4),(0,1),(0,1),(0,1,4,11)))]
 visits=set()
 for c in cases:
  m=Oracle(retail,c);m.run();want,calls=reference(c,m.initial);assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,'calls',m.calls[:3],calls[:3]);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:],c;visits.update(m.visits)
 result=dict(cases=len(cases),words_visited=sum(p.ENTRY+4*i in visits for i in range(75)),retail_equals_compiled=True,helper_state_mutations=True,mode_truncation_and_live_table=True,modeled_helpers=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
