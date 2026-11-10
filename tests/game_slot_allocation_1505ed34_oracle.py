"""Independent slot-priority model, opaque effects and complete guest machine pairs."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-slot-allocation-1505ED34-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,TABLE,CLEAN,INIT,MARK=0x1505ED34,0x800CC2D0,0x15060F28,0x1505F188,0x70000
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 empty:int=-1
 clear:int=-1
 recycle:int=-1
 pattern:int=1
 reserved:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 poison:int=0
 sparse:int=0
def symbols():return dict(D_800CC2D0=TABLE,D_800CC4A4=TABLE+0x1D4,func_15060F28=CLEAN,func_1505F188=INIT)
def slot_states(c):
 states=[u32(c.pattern) for _ in range(26)];states[25]=u32(c.reserved)
 for slot,value in((c.recycle,39),(c.clear,39),(c.empty,0)):
  if slot>=0:states[slot]=value
 pointers=[0x30000+64*i for i in range(26)]
 if c.clear>=0:pointers[c.clear]=0
 return states,pointers
def selection(c):
 states,pointers=slot_states(c)
 free=[i for i in range(25) if states[i]==0]
 detached=[i for i in range(25) if states[i]==39 and pointers[i]==0]
 recycled=[i for i in range(25) if states[i]==39]
 chosen=(free or detached or recycled or [25])[0]
 return chosen,bool(states[chosen])
def fixture(c,s=None):
 s=s or symbols();table=s['D_800CC2D0'];m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
 for base,n in((table-16,26*812+32),(MARK,32)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 states,pointers=slot_states(c)
 for i in range(26):put(m,table+i*812,states[i]);put(m,table+i*812+0x1D4,pointers[i])
 put(m,MARK,0);put(m,MARK+4,0)
 if c.sparse:
  chosen,_=selection(c);keep=set(range(table+chosen*812,table+(chosen+1)*812))
  for i in range(26):
   keep.update(range(table+i*812,table+i*812+4))
   if states[i]==39:keep.update(range(table+i*812+0x1D4,table+i*812+0x1D8))
  m={a:v for a,v in m.items() if not table-16<=a<table+26*812+16 or a in keep}
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def effect(m,c,kind,actor,s=None):
 s=s or symbols();table=s['D_800CC2D0'];slot=(actor-table)//812
 assert 0<=slot<26 and actor==table+slot*812
 if kind=='cleanup':
  put(m,MARK,read(m,MARK)+1);put(m,actor+0x50,0xC1EA0000|slot)
  if c.mutation&1:put(m,actor,0)
  if c.mutation&2:put(m,table+((slot+1)%26)*812,0)
  if c.mutation&4:put(m,actor+0x1D4,0)
 else:
  put(m,MARK+4,read(m,MARK+4)+1);put(m,actor+0x54,0x1A170000|slot)
  if c.mutation&8:put(m,actor,0x2468ACE0)
  if c.mutation&16:put(m,table,0xFFFFFFFF)
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);table=s['D_800CC2D0'];chosen,cleanup=selection(c);actor=table+chosen*812;calls=[]
 if cleanup:calls.append((s['func_15060F28'],(actor,0)));effect(m,c,'cleanup',actor,s)
 calls.append((s['func_1505F188'],(actor,)));effect(m,c,'init',actor,s)
 return m,calls,actor
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();super().__init__(ws,memory,c,entry=entry,arguments=(),connected=connected)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=u32(0x9E3779B9*(reg+1)+c.poison)
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={self.s['func_15060F28']:2,self.s['func_1505F188']:1,ENTRY:0};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  a=self.calls[-1][1];assert t in(self.s['func_15060F28'],self.s['func_1505F188'])
  if t==self.s['func_15060F28']:assert a[1]==0
  effect(self.memory,self.c,'cleanup'if t==self.s['func_15060F28']else'init',a[0],self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_1505ED34']['value'],fs['func_1505ED34']['size'];return bound_blob(text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def check(m,c,s=None):
 expected,calls,value=reference(m.initial,c,s);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory)==public(expected),(c,'public');assert m.r[2]==value,(c,'pointer-return')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'saved-ABI')
def cases():
 cs=[]
 for slot in range(25):
  cs.extend((Case(empty=slot),Case(clear=slot),Case(recycle=slot),Case(empty=slot,clear=(slot+7)%25,recycle=(slot+13)%25),Case(clear=slot,recycle=(slot+7)%25)))
 for pattern,reserved,mutation in itertools.product((1,39,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,39,0x80000000,0xFFFFFFFF),(0,1,2,4,8,16,31)):
  cs.append(Case(pattern=pattern,reserved=reserved,mutation=mutation))
 for mutation,mode in itertools.product((0,1,2,4,8,16,31),range(4)):
  cs.append(Case(empty=24 if mode==0 else -1,clear=24 if mode==1 else -1,recycle=24 if mode==2 else -1,mutation=mutation))
 cs.extend(Case(empty=n,sparse=1)for n in(0,1,24));cs.extend((Case(clear=0,sparse=1),Case(clear=24,sparse=1),Case(recycle=24,sparse=1),Case(reserved=0,sparse=1),Case(sparse=1)))
 cs.extend(replace(c,poison=v)for c,v in itertools.product((Case(empty=0),Case(clear=24),Case(recycle=24),Case()),(0,0x12345678,0xFFFFFFFF)))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();retail=struct.unpack_from('>95I',(root/'conker/conker.us.bin').read_bytes(),0x8C1E4);raw=words(out/'selected.o');assert list(retail)==raw;seen=set();calls=0
 for c in cs:
  models=[]
  for ws in(raw,retail):
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+380);models.append(m)
  a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls,a.hi,a.lo)==(b.memory,b.r,b.f,b.trace,b.calls,b.hi,b.lo),(c,'complete-machine');calls+=len(a.calls)
 result=dict(cases=len(cs),executions=2*len(cs),complete_machine_and_trace_pairs=len(cs),coverage=len(seen),missing=[i for i in range(95)if i not in seen],helper_calls=calls,opaque_helper_effects=True,callee_argument_homes_clobbered=True,poisoned_noninputs=True,sparse_short_circuit_cases=sum(c.sparse for c in cs),hardware_or_full_callees_qualified=False)
 (out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
