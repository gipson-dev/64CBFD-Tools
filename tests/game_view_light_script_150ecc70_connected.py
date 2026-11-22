"""Literal variadic packing and scalar smoothing; selected script leaves contracted."""
from pathlib import Path
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_view_light_script_150ecc70_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_light_script_150ecc70_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
BUFFER=0x800D2F60;COUNT=0x800D3840
PROVIDERS=((g.QUERY,0xC92F0,92),(g.SUBMIT,0xC9460,92),(g.SMOOTH,0x76A60,54))
TABLES=((g.QUERY,0x80088498,1),(g.QUERY,0x80088498,3),(g.SUBMIT,0x800884D4,2),(g.SUBMIT,0x800884D4,3),(g.SUBMIT,0x800884D4,8))
@lru_cache(maxsize=1)
def inputs():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={};leaves={}
 for entry,offset,n in PROVIDERS:
  data=rom[offset:offset+4*n];at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==data
  code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,data)))
 for target,table,index in TABLES:
  at=elf_slot_offset(elf,table+index*4,4);leaves[target,index]=struct.unpack_from('>I',elf,at)[0]
 assert len(set(leaves.values()))==5
 return code,leaves
def fixture(c,leaves):
 m=g.fixture(c);m.update({BUFFER+i:0xA5 for i in range(64)});g.put(m,COUNT,0x12345678)
 for target,table,index in TABLES:g.put(m,table+index*4,leaves[target,index])
 return m
def smooth(m,args,fcsr):
 p,target,v,strength,damping,dt=args
 def calc(a,b,fn):
  nonlocal fcsr
  result,flags=g.fp.arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3F000)|flags;return result
 difference=calc(target,g.read(m,p),1);direction=-1 if g.floating(difference)<0 else 1
 delta=calc(calc(calc(calc(difference,strength,2),g.read(m,v),1),damping,2),dt,2)
 g.put(m,v,calc(g.read(m,v),delta,0))
 next_value=calc(calc(g.read(m,v),dt,2),g.read(m,p),0)
 next_direction=-1 if g.floating(target)<g.floating(next_value)else 1
 if direction==next_direction:g.put(m,p,next_value)
 else:g.put(m,p,target);g.put(m,v,0)
 return fcsr
def reference(initial,c,leaves):
 leaf_calls=[];fcsr=c.fcsr
 def provider(m,c,t,args,ordinal):
  nonlocal fcsr
  if t==g.SMOOTH:fcsr=smooth(m,args,fcsr);return 0
  old=g.read(m,COUNT);packed=(args[1]&0xFFF,args[2],*args[3:]);assert len(packed)==args[0]+2
  for i,v in enumerate(packed):g.put(m,BUFFER+4*i,v)
  g.put(m,COUNT,args[0]+2)
  leaf_calls.append((leaves[t,((args[1]&0xF000)>>12)-1],(args[1]&0xFFF,args[2],BUFFER),packed,g.read(m,COUNT)))
  value=g.effect(m,c,t,args,ordinal);g.put(m,COUNT,old);return value
 m,calls,observations=g.reference(initial,c,provider);return m,calls,observations,leaf_calls,fcsr
class Connected(g.Oracle):
 def __init__(self,words,c,entry=g.ENTRY,arguments=None,standalone=None):
  code,self.leaf_targets=inputs();self.reverse={v:k[0] for k,v in self.leaf_targets.items()};self.leaves=[];self.standalone=standalone
  super().__init__(words,c,entry=entry,arguments=arguments,connected=code,memory=fixture(c,self.leaf_targets))
 def record_call(self,t):
  if t not in self.reverse:return super().record_call(t)
  a=tuple(map(g.u32,self.arguments(3)));count=g.read(self.memory,COUNT)
  self.leaves.append((t,a,tuple(g.read(self.memory,BUFFER+4*i)for i in range(count)),count))
 def hook(self,t):
  assert t in self.reverse,hex(t)
  if self.standalone is not None:value=0x87654321
  else:
   target=self.reverse[t];args=self.calls[-1][1];assert self.calls[-1][0]==target
   value=g.effect(self.memory,self.c,target,args,self.counts[target])
  self.clobber(value)
def main():
 code,leaves=inputs();count=0;visits=set()
 for replies,position,velocity,dt,mode,phase,rm in itertools.product(((0,0,0,0),(1,1,0,0),(1,0,1,0),(1,0,0,1),(1,0,0,0)),(0.,300.),(-40.,40.),(0.,.125,1.),(0,5),(0,8),range(4)):
  c=g.Case(replies=replies,current=(g.bits(position),)*3,velocity=(g.bits(velocity),)*3,dt=g.bits(dt),mode=mode,phase=phase,fcsr=rm);pair=[]
  for ws in g.streams():
   m=Connected(ws,c).run();expected,calls,observations,leaf_calls,fcsr=reference(m.initial,c,leaves)
   assert m.calls==calls and m.observations==observations,(c,'call boundary')
   assert m.leaves==leaf_calls,(c,'packed leaf arguments',m.leaves,leaf_calls)
   assert g.public(m.memory)==g.public(expected),(c,'connected memory')
   assert m.fcsr==fcsr,(c,'connected FCSR',m.fcsr,fcsr)
   pair.append(g.observable(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 standalone=0
 for target,n,phase in itertools.product((g.QUERY,g.SUBMIT),range(9),(0,8)):
  flags=0x403B if target==g.QUERY else 0x9000;args=(n,flags,0x12,*range(0x71000000,0x71000000+n))
  ws=[code[target+4*i]for i in range(92)];c=g.Case(phase=phase)
  m=Connected(ws,c,entry=target,arguments=args,standalone=True).run();old=g.read(m.initial,COUNT)
  assert g.read(m.memory,COUNT)==old and m.r[2]==0x87654321
  wanted=(flags&0xFFF,0x12,*args[3:]);assert m.leaves==[(leaves[target,((flags&0xF000)>>12)-1],(flags&0xFFF,0x12,BUFFER),wanted,n+2)]
  visits.update(m.visits);standalone+=1
 coverage={hex(t):sum(t+4*i in visits for i in range(n))for t,_,n in PROVIDERS}
 assert coverage[hex(g.QUERY)]==coverage[hex(g.SUBMIT)]==92
 r=dict(target_cases_per_stream=count,streams=2,standalone_wrapper_cases=standalone,counts_zero_through_eight=True,
  provider_executed_words=coverage,original_provider_words=[92,92,54],current_provider_bytes_equal=True,
  selected_leaf_addresses={str(k):hex(v)for k,v in leaves.items()},leaf_semantics_contracted=True,
  full_variadic_payload_and_count_restore=True,independent_scalar_smoothing=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
