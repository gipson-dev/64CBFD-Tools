"""Complete retained dispatcher connected to second-table callback 9."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
from unittest.mock import patch
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_random_targets_1518f1a0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_random_targets_1518f1a0_guest as g
from tools.tests import game_dual_record_animation_update_1513cfe4_oracle as ram
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x1513CFE4;RETURN=0x1513D098
@lru_cache(None)
def original():
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',(o/'baseline/conker/asm/nonmatchings/game_169510/func_1513CFE4.s').read_text());blob=bytes.fromhex(''.join(w for _,_,w in rows));rom=(r/'conker/conker.us.bin').read_bytes();old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));assert len(rows)==195 and blob==rom[0x16A494:0x16A7A0]==old[at:at+len(blob)]
 table=rom[0x22E820:0x22E8D0];assert len(table)==176 and struct.unpack_from('>I',table,36)[0]==g.ENTRY;at=elf_slot_offset(old,ram.SECOND,176);assert old[at:at+176]==table
 return[int(w,16)for _,_,w in rows]
def fixture(c,p):
 m=g.fixture(c)
 # This older helper predates CBFD_CONSUMER_ROOT; scope its ROM read.
 with patch.object(ram.c,'ROOT',r):m.update(ram.fixture(p))
 return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,p,poison=False,invert=False):
  super().__init__(parent,c,memory=fixture(c,p),entry=PARENT,arguments=(c.object,),connected=dict(zip(range(g.ENTRY,g.ENTRY+484,4),leaf)));self.outer=c;self.parent_case=p;self.pending=None;self.children=0;self.outer_calls=[];self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x1513D09C]^=0x04000000
 def record_call(self,t):
  if t in(g.RNG,g.FRNG):return super().record_call(t)
  args=tuple(self.arguments(1));self.outer_calls.append((t,args));self.events.append(('CALL',t,args))
  if t==g.ENTRY:
   assert args==(self.outer.object,);self.c=replace(self.outer,phase=self.outer.phase-32);self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.calls),len(self.fp_operations))
  else:assert t==ram.RELEASE,hex(t)
 def child_return(self):
  (memory,calls,ops,csr,result),nc,no=self.pending;got=(g.public(self.memory,self.c),self.calls[nc:],self.fp_operations[no:],self.fcsr,self.r[2]);want=(g.public(memory,self.c),calls,ops,csr,result);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);self.pending=None;self.children+=1;self.c=self.outer
  if self.poison:self.r[2]=0
 def hook(self,t):
  if t in(g.RNG,g.FRNG):return super().hook(t)
  assert t==ram.RELEASE;g.put(self.memory,ram.MARK,self.outer.object)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
 def verify(self):
  assert self.pending is None;csr=g.initial_fcsr(self.outer);expected_calls=[];expected_ops=[];old=ram.effect
  def effect(memory,case,stage,home,record,order='big'):
   nonlocal csr
   if stage==1:
    assert record==self.outer.object and case.second==9
    after,calls,ops,csr,_=g.reference(memory,replace(self.outer,phase=self.outer.phase-32),csr);memory.clear();memory.update(after);expected_calls.extend(calls);expected_ops.extend(ops)
   else:old(memory,case,stage,home,record,order)
  try:ram.effect=effect;want=ram.reference(self.initial,self.parent_case)
  finally:ram.effect=old
  assert want['status']=='return';assert(g.public(self.memory,self.outer),self.outer_calls,self.calls,self.fp_operations,self.fcsr)==(g.public(want['memory'],self.outer),want['calls'],expected_calls,expected_ops,csr),dict(case=str(self.parent_case),calls=self.outer_calls,wanted=want['calls']);assert self.children==int(bool(self.parent_case.enabled&1)and self.parent_case.second==9);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent=original();streams=[g.bound_blob(*g.payload(o/f,'func_1518F1A0'),g.symbols())for f in('original-target.o','selected-owner.o','normalized-target.o')];count=children=0;seen=set()
 # Full parent, including lifetime, both fade fields, cursor wrap/bounce/removal and exit.
 for enabled,second,flags,(cursor,rate),ticks,mode in itertools.product((0,1),(0,9),(0,1,0x18000000,0x400,0x800,0x1000),((0,10),(65530,10),(-1,-10)),(0,1,2),(0,1)):
  p=ram.Case(enabled=enabled,second=second,flags=flags,timer=20,threshold=301,scale=2,cursor=g.u32(cursor),rate=g.u32(rate),ticks=ticks,second_answer=1);c=g.Case(timers=(-1,3,-1),delta=ticks,mode=mode,phase=8*(mode&1),rm=mode,seed=count);models=[Connected(parent,w,c,p).run().verify()for w in streams];assert g.state(models[0],False)==g.state(models[1],False)==g.state(models[2],False)and models[0].outer_calls==models[1].outer_calls==models[2].outer_calls;seen.update(x for x in models[0].visits if PARENT<=x<PARENT+780);count+=1;children+=models[0].children
 p=ram.Case(second=9,rate=0,ticks=0);c=g.Case(timers=(3,3,3));base=Connected(parent,streams[0],c,p).run().verify();controls=[]
 for name,kw in(('zero-callback-return',dict(poison=True)),('inverted-status-consumer',dict(invert=True))):
  bad=Connected(parent,streams[0],c,p,**kw).run();assert bad.pending is None and bad.children==1 and bad.outer_calls!=base.outer_calls and bad.outer_calls[-1][0]==ram.RELEASE;controls.append(dict(name=name,complete_parent_execution=True,rejected=True))
 q=dict(parent_words_pinned=195,parent_frame=32,parent_words_executed=len(seen),second_table_bytes_pinned=176,table_selector=9,cases_per_stream=count,streams=3,connected_children_per_stream=children,complete_original_parent_on_qualified_paths=True,independent_complete_parent_reference=True,child_full_memory_calls_ordered_FP_FCSR_and_return_qualified=True,return_one_keeps_record_alive=True,animation_rate_consumed_by_parent=True,other_callbacks_opaque_and_not_qualified=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
