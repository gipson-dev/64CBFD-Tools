"""Complete original304word dispatcher on explicit idle/default state paths."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_random_sprite_scatter_15179b14_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_random_sprite_scatter_15179b14_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x15179008;RETURN=0x151794B0;ORIGIN_HELPER=0x151794C8;REMAINING=0x800DD436;BYTE_TIMER=0x800DD432;OTHER_TIMER=0x800DD433;STATE=0x800DD434;MODE=0x800DD446;TICKS=0x800BE9E4;JTABLE=0x800A71F0
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();asm=(o/'baseline/conker/asm/1A6360.s').read_text();body=asm.split('glabel func_15179008\n',1)[1].split('endlabel func_15179008',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==304 and blob==rom[0x1A64B8:0x1A6978];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));table=rom[0x24BCB0:0x24BCC4];pos=elf_slot_offset(old,JTABLE,20);assert old[pos:pos+20]==table;return[int(w,16)for _,_,w in rows],table,old[at:at+len(blob)]==blob
def fixture(c,before,mode,ticks):
 m=g.fixture(c);_,table,_=retained()
 for i,v in enumerate(table):m[JTABLE+i]=v
 for i in range(32):m[BYTE_TIMER+i]=(i*13+91)&255
 m[BYTE_TIMER]=240;m[OTHER_TIMER]=20;m[MODE]=mode;m[STATE]=0;g.put(m,REMAINING,before,2);g.put(m,TICKS,ticks);g.put(m,g.ORIGIN,c.origins[0],2);g.put(m,g.ORIGIN+4,c.origins[1],2);return m
def origin_effect(memory,after):
 g.put(memory,REMAINING,after,2);g.put(memory,g.ORIGIN,1234,2);g.put(memory,g.ORIGIN+4,-2345,2)
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,before,after,mode,ticks,poison=None):
  super().__init__(parent,c,memory=fixture(c,before,mode,ticks),entry=PARENT,arguments=(0x87654321,),connected=dict(zip(range(g.ENTRY,g.ENTRY+412,4),leaf)));self.outer=c;self.after=after;self.pending=None;self.parent_calls=[];self.child_count=0;self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==ORIGIN_HELPER:self.parent_calls.append((t,()));self.events.append(('CALL',t,()));return
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(1)));self.parent_calls.append((t,args));self.c=replace(self.outer,count=g.signed(args[0]),phase=self.outer.phase-64);self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.calls),len(self.packets),len(self.fp_operations));return
  super().record_call(t)
 def child_return(self):
  (memory,calls,packets,ops,csr),nc,np,no=self.pending;got=(g.public(self.memory,self.c),self.calls[nc:],self.packets[np:],self.fp_operations[no:],self.fcsr);want=(g.public(memory,self.c),calls,packets,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_count+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t!=ORIGIN_HELPER:return super().hook(t)
  origin_effect(self.memory,self.after)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.fcsr=(self.fcsr&~0x3F000)|self.outer.provider_flags
 def verify(self):
  m=dict(self.initial);timer=m[BYTE_TIMER]-g.read(m,TICKS);assert timer>0 and(m[MODE]>=5 or(m[MODE]==0 and m[STATE]==0));m[BYTE_TIMER]=timer&255;parent=[];calls=[];packets=[];ops=[];csr=self.outer.rm|self.outer.flags
  if g.half(g.read(m,REMAINING,2))!=0:
   parent.append((ORIGIN_HELPER,()));origin_effect(m,self.after);csr=(csr&~0x3F000)|self.outer.provider_flags;n=g.half(g.read(m,REMAINING,2));count=(abs(n)//30)*(-1 if n<0 else 1);parent.append((g.ENTRY,(g.u32(count),)));m,calls,packets,ops,csr=g.reference(m,replace(self.outer,count=count,phase=self.outer.phase-64),csr)
  got=(g.public(self.memory,self.outer),self.parent_calls,self.calls,self.packets,self.fp_operations,self.fcsr);want=(g.public(m,self.outer),parent,calls,packets,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)],calls=self.parent_calls,wanted=parent);assert self.pending is None and self.child_count==len(parent)//2;assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,_,matches=retained();leaves=[g.bound_blob(*g.payload(o/f,'func_15179B14'),g.symbols())for f in('original-target.o','selected-owner.o')];count=children=0;seen=set()
 for before,after,mode,ticks,rm,mutation in itertools.product((0,1,-32768),(-31,-1,0,29,30,90),(0,5,255),(0,2),(0,3),(0,1)):
  c=g.Case(heights=(17,-10000,2147483647),rm=rm,mutation=mutation,phase=8*(rm&1),seed=count);models=[Connected(parent,w,c,before,after,mode,ticks).run().verify()for w in leaves];assert g.state(models[0])==g.state(models[1])and models[0].parent_calls==models[1].parent_calls;seen.update(x for x in models[0].visits if PARENT<=x<PARENT+1216);count+=1;children+=models[0].child_count
 c=g.Case();base=Connected(parent,leaves[0],c,1,60,5,1).run().verify();controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(parent,leaves[0],c,1,60,5,1,poison=value).run().verify();assert(g.public(m.memory,c),m.calls,m.parent_calls)==(g.public(base.memory,c),base.calls,base.parent_calls);controls.append(dict(value=hex(value),complete_parent_execution=True,public_effects_unchanged=True))
 q=dict(parent_words_pinned=304,parent_frame=64,parent_words_executed=len(seen),parent_frozen_ELF_slot_equals_original=matches,actual_parent_source_not_newly_recovered_or_credited=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,complete_original_parent_on_idle_state0_and_default_modes_only=True,independent_complete_parent_reference_on_qualified_paths=True,late_origin_update_and_count_reload_signed_division30_qualified=True,other_FSM_states_RNG_reset_and_backend_implementation_not_qualified=True,entry_void_s32_count_ABI_parent_ignores_result=True,void_return_poison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
