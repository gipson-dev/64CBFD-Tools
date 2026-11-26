"""Complete original selected callback consumer with the default provider."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_colour_framebuffer_settings_151600d8_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x1515ffec;FREE=0x1516972c;TABLE=0x8008b0d0;TIMER=0x800be9e4
@lru_cache(maxsize=1)
def callback_table():
 table=(r/'conker/conker.us.bin').read_bytes()[0x22fb90:0x22fb98];assert table==bytes.fromhex('151600d8150ce200');return table
class ReturnCode(dict):
 def __getitem__(self,pc):
  if self.owner.pending is not None and pc==0x15160060:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,selector,flags,lifetime,delta,poison=None,invert=False):
  memory=g.fixture(c);memory[c.object+14]=flags;memory[c.object+15]=selector&255;g.put(memory,c.object+18,lifetime&65535,2);g.put(memory,TIMER,delta&0xffffffff);memory.update({TABLE+i:v for i,v in enumerate(callback_table())})
  connected=dict(zip(range(g.ENTRY,g.ENTRY+412,4),leaf));super().__init__(parent,c,memory=memory,entry=PARENT,arguments=(c.object,),connected=connected);self.outer=c;self.pending=None;self.child_checks=0;self.post_calls=[];self.post_observations=[];self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x15160064]=0x10400002
  signed16=lambda v:((v&65535)^32768)-32768
  self.expired=bool(flags&1 and signed16(lifetime-delta)<0);self.expected_children=int(selector==0 and not self.expired)
 def record_call(self,t):
  if t==g.ENTRY:
   assert tuple(self.arguments(1))==(self.outer.object,);self.c=replace(self.outer,phase=self.outer.phase-32);self.pending=(g.reference(self.memory,self.c,self.r[16],self.r[17],self.r[31],initial_fcsr=self.fcsr),len(self.calls),len(self.observations),len(self.fp_operations));return
  if t==FREE:self.post_calls.append((t,tuple(self.arguments(1))));self.post_observations.append((dict(self.memory),self.fcsr));return
  super().record_call(t)
 def child_return(self):
  expected,calls,obs,ops=self.pending;actual=(self.memory,self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr,self.r[2]);assert actual==expected,dict(reason='connected settings reference',case=str(self.c),components=[a==b for a,b in zip(actual,expected)])
  self.pending=None;self.child_checks+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t!=FREE:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xb6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa6000000+i
  self.f[:20]=[0xa6000000+i for i in range(20)];self.hi,self.lo=0xa6000010,0xa6000011
 def verify(self):
  assert self.pending is None and self.child_checks==self.expected_children
  assert self.post_calls==([(FREE,(self.outer.object,))]if self.expired else[]),(self.outer,self.expired,self.post_calls)
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',(o/'original-parent.s').read_text());blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==41 and blob==(r/'conker/conker.us.bin').read_bytes()[0x18d49c:0x18d540];parent=[int(w,16)for _,_,w in rows];before=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(before,PARENT,len(blob));assert before[at:at+len(blob)]==blob
 leaves=[g.bound_blob(*g.payload(o/f,'func_151600D8'),g.symbols(g.Case()))for f in('original-target.o','selected-owner.o')];count=children=0;visits=set()
 for selector,flags,lifetime,delta,actual,mode,pattern,rm in itertools.product((0,-1),(0,1,32,33),(-1,0,10),(-65536,-1,0,1,65536),(False,True),(0,15),(0,7),range(4)):
  c=g.Case(actual=actual,values=(0xffffffff,0x7fffffff,0x80000000,0x01000001,0xff000000),mode=mode,pattern=pattern,rm=rm,phase=8*(rm&1));models=[Connected(parent,leaf,c,selector,flags,lifetime,delta).run().verify()for leaf in leaves];a,b=models;assert g.state(a)==g.state(b)and a.post_calls==b.post_calls and a.post_observations==b.post_observations;count+=1;children+=a.child_checks;visits.update(a.visits)
 controls=[]
 for name,kwargs in [('force-zero-success',dict(poison=0)),('invert-zero-test',dict(invert=True))]:
  m=Connected(parent,leaves[0],g.Case(),0,0,10,1,**kwargs).run();assert m.pending is None and m.child_checks==1 and m.post_calls==[(FREE,(g.OBJECT,))];assert m.r[29]==m.before[29]and m.r[31]==m.before[31];controls.append(dict(name=name,complete_parent_execution=True,wrong_expiration_reaches_free=True))
 missing=[hex(pc)for pc in range(PARENT,PARENT+164,4)if pc not in visits];assert missing==['0x1516006c'],missing
 q=dict(parent_words_pinned=41,parent_frame=32,parent_linked_byte_exact=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,actual_signed_selector0_and_minus_one_skip=True,callback_A0_owner_and_status_consumer_qualified=True,complete_original_parent_execution_on_selected_paths=True,source_owner_argument_now_explicit_with_parent_bytes_unchanged=True,actual7word_default_provider_and_opaque_contract_connected=True,child_full_memory_frame48_borrowed_home_FP_and_return_reference_equal=True,other_table_entry_not_executed_or_newly_qualified=True,unreachable_authentic_child_zero_result_word=missing,opaque_expiration_helper_not_full_implementation=True,no_new_parent_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
