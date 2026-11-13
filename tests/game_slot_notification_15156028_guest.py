from pathlib import Path
import itertools,struct,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle, Case, STACK, put, read
ENTRY=0x15156028;BASE=0x800CC2D0;RELEASE=0x1516972C;RECORD=0x30000;EVENT=0x90000;MARK=0xa0000
lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
raw,refs=payload(out/'durable-after.o','func_15156028');candidate=bound_blob(raw,refs,{n:lookup[n] for rows in refs.values() for _,n in rows});retail=list(struct.unpack_from('>88I',(root/'conker/conker.us.bin').read_bytes(),0x1834D8));guarded,gr=payload(out/'durable-generated.o','func_15156028');padded=bound_blob(guarded,gr,{n:lookup[n] for rows in gr.values() for _,n in rows});assert len(candidate)==88 and padded==retail
u32=lambda x:x&0xffffffff
def signed(x):return ((x&0xffffffff)^0x80000000)-0x80000000
def quotient(value):
 v=signed(value-BASE);return -(abs(v)//812) if v<0 else v//812
def fixture(first,second,tag,kind,phase,alias):
 record=(RECORD,EVENT-16,STACK+phase+0x50)[alias];event=(EVENT,EVENT,STACK+phase+0x20)[alias]
 m={STACK+i:(i*17+0xa5)&255 for i in range(-0x600,0x180)}
 for base,size in ((RECORD-32,160),(EVENT-32,160),(MARK,8)):m.update({base+i:(i*11+9)&255 for i in range(size)})
 put(m,event,u32(BASE+first));put(m,event+4,u32(BASE+second));m[record+16]=tag
 return m,(record,event,kind)
def public(m):return {a:b for a,b in m.items() if not STACK-0x600<=a<STACK+0x18}
def reference(mem,args,phase):
 m=dict(mem);record,event,kind=args;put(m,STACK+phase+8,kind);calls=[];kind&=255
 if kind==0:
  first=quotient(read(m,event))
  if 0<=first<25 and first==m[record+16]:
   calls.append((RELEASE,(record,)));m[record+17]^=0x5a;put(m,MARK,0x13579bdf)
 elif kind==45:
  first=quotient(read(m,event));second=quotient(read(m,event+4))
  if 0<=first<25 and 0<=second<25:
   if first==m[record+16]:m[record+16]=second
   elif second==m[record+16]:m[record+16]=first
 return public(m),calls
class Machine(FactoryOracle):
 def __init__(self,program,m,args,phase):super().__init__(program,m,Case(phase=phase),entry=ENTRY,arguments=args)
 def record_call(self,target):
  assert target==RELEASE;args=tuple(self.arguments(1));self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==RELEASE;p=self.calls[-1][1][0];self.memory[p+17]^=0x5a;put(self.memory,MARK,0x13579bdf)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
offsets=(-812,-811,-1,0,812,24*812,25*812,0x7fffffff);count=0;visited=set()
for first,second,tag,kind,phase,alias in itertools.product(offsets,offsets,(0,1,24,255),(0,45,0x12d,2),(0,8),(0,1,2)):
 initial,args=fixture(first,second,tag,kind,phase,alias);wanted=reference(initial,args,phase)
 for label,program in (('retail',retail),('candidate',candidate),('padded',padded)):
  m=Machine(program,initial,args,phase).run();actual=public(m.memory);differences=[(hex(k),actual.get(k),wanted[0].get(k)) for k in actual.keys()|wanted[0].keys() if actual.get(k)!=wanted[0].get(k)];assert (actual,m.calls)==wanted,(label,first,second,tag,kind,phase,alias,m.calls,wanted[1],differences[:12],m.trace,m.r);visited.update(m.visits)
 count+=1
print(count,'retail, raw-C, and padded guest cases; bounded values, input/output alias and caller stack tested; visited',len(visited),'instruction locations',flush=True)
extra=0
for first,second,tag,kind,phase in itertools.product((-0x80000000,0x7fffffff,-813,25*812),(-0x80000000,0x7fffffff,0,24*812),(0,24,255),(0,45),(0,8)):
 initial,args=fixture(first,second,tag,kind,phase,0);wanted=reference(initial,args,phase)
 for program in (retail,candidate,padded):
  m=Machine(program,initial,args,phase).run();assert (public(m.memory),m.calls)==wanted,(first,second,tag,kind,phase)
 extra+=1
for kind in range(256):
 initial,args=fixture(0,812,0,kind,0,0);wanted=reference(initial,args,0)
 for program in (retail,candidate,padded):
  m=Machine(program,initial,args,0).run();assert (public(m.memory),m.calls)==wanted,kind
print(extra,'signed-boundary cases plus all 256 opcode bytes per body',flush=True)
