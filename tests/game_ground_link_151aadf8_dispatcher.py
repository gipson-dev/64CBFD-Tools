"""Execute the complete original callback dispatcher and connected constructor."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_ground_link_151aadf8_recovery as source
from tools.tests import game_ground_link_151aadf8_oracle as g
R,P=source.ROOT,source.OUT
ENTRY=0x15158D2C;SIZE=0x278;TABLE,ROWS,FILTERS,ROW=0x8008AFD0,0x8008B02C,0x800A6200,0x90000
HELPERS={0x15159084:2,0x15159120:2,0x15159184:2,0x15159230:3,0x151592B8:2}
@dataclass(frozen=True)
class Case(g.Case):
 gate:int=0;timer:int=0;motion:int=0;last:int=0;span:int=0;enabled:int=1;suppress:int=0;slot:int=14;category:int=0
def cases():
 for seed,route,mode,phase in itertools.product((0,2,12),range(4),range(8),(0,8)):
  yield Case(seed,route,31,phase,mode&1,(mode>>1)&1,(mode>>2)&1,mode%3,mode%3,1,0,(0,13,14,27)[mode%4],mode%5)
 for suppress,enabled,slot,phase in itertools.product((0,1,2),(0,1),(0,14,27),(0,8)):
  yield Case(2,3,31,phase,0,1,1,2,1,enabled,suppress,slot,4)
def fixture(c,callbacks):
 m=g.fixture(c)
 for p,n in((TABLE,len(callbacks)),(ROWS,20),(FILTERS,28*8),(ROW,28)):m.update({p+i:0xff for i in range(n)})
 for i,v in enumerate(callbacks):m[TABLE+i]=v
 for i in range(5):g.put(m,ROWS+4*i,ROW)
 m[ROW+c.slot]=14
 for i in range(28):g.put(m,FILTERS+8*i,0xffffffff);g.put(m,FILTERS+8*i+4,0xffffffff)
 if c.suppress:g.put(m,FILTERS+8*c.slot+4*(c.suppress-1),0)
 m[g.OWNER+0x1d]=c.category
 for i in range(5):m[g.OWNER+0x2c+i]=(c.seed+i)%3
 m[g.OWNER+0x31]=c.enabled
 return m
def before_constructor(initial,c):
 m=dict(initial);m[g.OWNER+0x2c]=c.gate;m[g.OWNER+0x2d]=c.timer if not c.gate else 2
 m[g.OWNER+0x2e]=0 if c.gate else(1 if not c.timer else c.motion)
 m[g.OWNER+0x2f]=c.span;m[g.OWNER+0x30]=c.last
 for i in range(12):m[g.OWNER+0x20+i]=m[g.ACTOR+0x14+i]
 return m
class Dispatcher(g.Oracle):
 def __init__(self,body,parent,initial,c):
  code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(body),4),body));FactoryOracle.__init__(self,parent,initial,c,entry=ENTRY,s={},arguments=(g.OWNER,),connected=code)
  self.service=g.Service(self.memory,c);self.target_calls=[];self.parent_calls=[];self.saved={i:self.r[i]for i in(*range(16,24),28,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==0 and w&63==4:
   self.r[w>>11&31]=g.u32(self.r[w>>16&31]<<(self.r[w>>21&31]&31));self.r[0]=0;return
  return super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(self.arguments(1));assert a==(g.OWNER,),('callback owner',a);self.target_calls.append(a)
  elif t in HELPERS:self.parent_pending=t,tuple(self.arguments(HELPERS[t]));self.parent_calls.append(self.parent_pending)
  else:super().record_call(t)
 def hook(self,t):
  if t not in HELPERS:return super().hook(t)
  target,args=self.parent_pending;assert target==t and args[0]==g.ACTOR
  assert args[1]==(g.OWNER+0x20 if t==0x15159230 else self.case.category)
  if t==0x15159230:assert args[2]==(self.case.seed+3)%3
  answer={0x15159084:self.case.gate,0x15159120:self.case.timer,0x15159184:self.case.motion,0x15159230:self.case.span,0x151592B8:self.case.last}[t]
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef;self.r[2]=answer
def programs():
 code={'retail':list(struct.unpack('>166I',(P/'retail.bin').read_bytes()))}
 for label,file in(('raw','v42.o'),('strict','ground-link-padded-strict.o'),('layout','ground-link-padded-layout.o')):
  b,r=payload(P/file,'func_151AADF8');code[label]=bound_blob(b,r,g.SYMS)
 return code
def verify(words,parent,c,callbacks):
 initial=fixture(c,callbacks);expected=before_constructor(initial,c);invoke=bool(c.enabled and not c.suppress)
 if invoke:expected,calls=g.reference(expected,replace(c,phase=c.phase-80))
 else:calls=[]
 machine=Dispatcher(words,parent,initial,c).run()
 assert len(machine.target_calls)==int(invoke),('callback count',c,len(machine.target_calls))
 assert machine.service.calls==calls,('callback trace',c)
 assert g.public(machine.memory)==g.public(expected),('public memory',c)
 assert all(machine.r[i]==value for i,value in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
 return machine
def main():
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();parent=list(struct.unpack_from('>158I',rom,ENTRY-0x14fd2b50));callbacks=rom[0x22fa90:0x22fa90+92];assert struct.unpack_from('>I',callbacks,56)[0]==g.ENTRY
 at=elf_slot_offset(elf,TABLE,92);assert elf[at:at+92]==callbacks
 coverage=set();counts={}
 for label,words in programs().items():
  n=0
  for c in cases():m=verify(words,parent,c,callbacks);coverage|=m.visits&set(range(ENTRY,ENTRY+SIZE,4));n+=1
  counts[label]=n
 bad=bytearray(callbacks);struct.pack_into('>I',bad,56,0x151AAABC)
 try:verify(programs()['raw'],parent,Case(2,3,31),bytes(bad))
 except(AssertionError,KeyError,ValueError):negative=True
 else:raise AssertionError('ineffective callback-table control')
 at=elf_slot_offset(elf,ENTRY,SIZE)
 report=dict(dispatcher_words=158,dispatcher_words_visited=len(coverage),unvisited_offsets=[hex(a-ENTRY)for a in range(ENTRY,ENTRY+SIZE,4)if a not in coverage],cases_per_stream=counts,complete_original_dispatcher_executed=True,dispatcher_production_literal=elf[at:at+SIZE]==struct.pack('>158I',*parent),callback_table_production_literal=True,effective_wrong_callback_control=negative,bounded_dispatcher_helpers=5,source_installed=source.installed(),c_match_credit=0)
 (P/'dispatcher-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
