"""Complete original dispatcher on bounded mode1 fill-loop paths, void child ABI."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_display_sprite_slot_15179600_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_display_sprite_slot_15179600_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x15179008;RETURN=0x1517921C;ORIGIN_HELPER=0x151794C8;SCATTER=0x15179B14;BYTE_TIMER=0x800DD432;OTHER_TIMER=0x800DD433;STATE=0x800DD434;TIMER=0x800DD444;MODE=0x800DD446;TICKS=0x800BE9E4;JTABLE=0x800A71F0
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();asm=(o/'baseline/conker/asm/1A6360.s').read_text();body=asm.split('glabel func_15179008\n',1)[1].split('endlabel func_15179008',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==304 and blob==rom[0x1A64B8:0x1A6978];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));table=rom[0x24BCB0:0x24BCC4];pos=elf_slot_offset(old,JTABLE,20);assert old[pos:pos+20]==table;return[int(w,16)for _,_,w in rows],table,old[at:at+len(blob)]==blob
def fixture(c,before,timer,ticks):
 m=g.fixture(c);_,table,_=retained()
 for i,v in enumerate(table):m[JTABLE+i]=v
 m[BYTE_TIMER]=240;m[OTHER_TIMER]=20;m[MODE]=1;m[STATE]=0;g.put(m,g.COUNT,before,2);g.put(m,TIMER,timer,2);g.put(m,TICKS,ticks);return m
def effect(memory):g.put(memory,g.MARK+4,g.read(memory,g.MARK+4)+1)
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,before,timer,ticks,poison=None):
  super().__init__(parent,c,memory=fixture(c,before,timer,ticks),entry=PARENT,arguments=(0x87654321,),connected=dict(zip(range(g.ENTRY,g.ENTRY+432,4),leaf)));self.outer=c;self.pending=None;self.parent_calls=[];self.child_count=0;self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t in(ORIGIN_HELPER,SCATTER):
   a=tuple(map(g.u32,self.arguments(1 if t==SCATTER else 0)));self.parent_calls.append((t,a));self.events.append(('CALL',t,a));return
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(2)));assert args==(1,1);self.parent_calls.append((t,args));self.c=replace(self.outer,randomize=g.signed(args[0]),value=args[1],phase=self.outer.phase-64);self.counts={g.RNG:0,g.COLOR:0,g.CREATE:0};self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.calls),len(self.packets),len(self.fp_operations));return
  super().record_call(t)
 def child_return(self):
  (memory,calls,packets,ops,csr),nc,np,no=self.pending;got=(g.public(self.memory,self.c),self.calls[nc:],self.packets[np:],self.fp_operations[no:],self.fcsr);want=(g.public(memory,self.c),calls,packets,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_count+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t not in(ORIGIN_HELPER,SCATTER):return super().hook(t)
  effect(self.memory)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF;self.fcsr=(self.fcsr&~0x3F000)|self.outer.provider_flags
 def verify(self):
  m=dict(self.initial);timer=m[BYTE_TIMER]-g.read(m,TICKS);assert timer>0 and m[MODE]==1;m[BYTE_TIMER]=timer&255;parent=[];calls=[];packets=[];ops=[];csr=self.outer.rm|self.outer.flags;children=0
  if g.half(g.read(m,g.COUNT,2))==300:m[MODE]=2;g.put(m,TIMER,0,2)
  else:
   for i in range(4):
    if g.half(g.read(m,g.COUNT,2))==300:continue
    parent.append((g.ENTRY,(1,1)));c=replace(self.outer,randomize=1,value=1,phase=self.outer.phase-64);m,cc,pp,oo,csr=g.reference(m,c,csr);calls+=cc;packets+=pp;ops+=oo;children+=1
   v=g.half(g.read(m,TIMER,2));assert v<11;g.put(m,TIMER,v+g.read(m,TICKS),2)
  if g.half(g.read(m,g.COUNT,2))!=0:
   parent.append((ORIGIN_HELPER,()));effect(m);csr=(csr&~0x3F000)|self.outer.provider_flags;n=g.half(g.read(m,g.COUNT,2));count=(abs(n)//30)*(-1 if n<0 else 1);parent.append((SCATTER,(g.u32(count),)));effect(m);csr=(csr&~0x3F000)|self.outer.provider_flags
  got=(g.public(self.memory,self.outer),self.parent_calls,self.calls,self.packets,self.fp_operations,self.fcsr);want=(g.public(m,self.outer),parent,calls,packets,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)],parent=self.parent_calls,wanted=parent);assert self.pending is None and self.child_count==children;assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,_,matches=retained();leaves=[g.bound_blob(*g.payload(o/f,'func_15179600'),g.symbols())for f in('original-target.o','selected-owner.o')];count=children=0;seen=set()
 for before,outcome,mutation,timer,ticks,rm in itertools.product((0,1,298,299,300),(0,1),(0,1,2,3),(0,10),(0,2),(0,3)):
  c=g.Case(outcome=outcome,mutation=mutation,rm=rm,phase=8*(rm&1),seed=count);models=[Connected(parent,w,c,before,timer,ticks).run().verify()for w in leaves];assert g.state(models[0])==g.state(models[1])and models[0].parent_calls==models[1].parent_calls;seen.update(x for x in models[0].visits if PARENT<=x<PARENT+1216);count+=1;children+=models[0].child_count
 c=g.Case();base=Connected(parent,leaves[0],c,298,0,1).run().verify();controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(parent,leaves[0],c,298,0,1,poison=value).run().verify();assert(g.public(m.memory,c),m.calls,m.parent_calls)==(g.public(base.memory,c),base.calls,base.parent_calls);controls.append(dict(value=hex(value),complete_parent_execution=True,public_effects_unchanged=True))
 q=dict(parent_words_pinned=304,parent_frame=64,parent_words_executed=len(seen),parent_frozen_ELF_slot_equals_original=matches,actual_parent_source_not_newly_recovered_or_credited=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,complete_original_parent_on_mode1_low_timer_fill_loop_paths_only=True,independent_complete_parent_reference_on_qualified_paths=True,loop_reload_limit300_four_attempts_and_allocation_failure_qualified=True,other_FSM_states_audio_RNG_reset_and_followup_backends_not_qualified=True,origin_and_scatter_followups_are_opaque_contracts=True,entry_void_two_word_ABI_parent_arguments_one_one_and_ignored_result=True,void_return_poison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
