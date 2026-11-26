"""Complete original parent with first-table selector7 and the recovered leaf."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_particle_ring_tick_150b40e8_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_particle_ring_tick_150b40e8_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x15147740;FREE=0x1516972c;TABLE=0x8008a200
@lru_cache(maxsize=1)
def callback_table():
 table=(r/'conker/conker.us.bin').read_bytes()[0x22ecc0:0x22ecfc];assert table[28:32]==bytes.fromhex('150b40e8');return table
class ReturnCode(dict):
 def __getitem__(self,pc):
  if self.owner.pending is not None and pc==0x151477cc:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,selector,flags,lifetime,poison=None,invert=False):
  memory=g.fixture(c);memory[c.object+0x2f]=selector;memory[c.object+0x30]=0;memory[c.object+0x24]=255;g.put(memory,c.object+0x1e,flags,2);g.put(memory,c.object+0x1c,lifetime&65535,2);memory.update({TABLE+i:v for i,v in enumerate(callback_table())})
  code=dict(zip(range(g.ENTRY,g.ENTRY+428,4),leaf));super().__init__(parent,c,memory=memory,entry=PARENT,arguments=(c.object,),connected=code);self.outer=c;self.pending=None;self.child_checks=0;self.post_calls=[];self.post_observations=[];self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x151477d0]=0x10400002
  signed16=lambda v:((v&65535)^32768)-32768
  expired=bool(flags&1 and signed16(lifetime-c.delta)<0);self.expected_children=int(selector==7 and not expired);self.expected_free=selector>=15 or expired or bool(self.expected_children and g.s8(c.count)<2 and c.flags&1)
 def record_call(self,t):
  if t==g.ENTRY:
   assert tuple(self.arguments(1))==(self.outer.object,);self.c=replace(self.outer,phase=self.outer.phase-32);self.pending=(g.reference(self.memory,self.c,initial_fcsr=self.fcsr),len(self.fp_operations));return
  assert t==FREE,hex(t);self.post_calls.append((t,tuple(self.arguments(1))));self.post_observations.append((dict(self.memory),self.fcsr))
 def child_return(self):
  expected,ops=self.pending;actual=(self.memory,self.fp_operations[ops:],self.fcsr,self.r[2]);assert actual==expected[:4],dict(reason='connected leaf reference',case=str(self.c),components=[a==b for a,b in zip(actual,expected[:4])]);self.pending=None;self.child_checks+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  assert t==FREE
  for i in range(4):self.put(self.r[29]+4*i,0xb6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa6000000+i
  self.f[:20]=[0xa6000000+i for i in range(20)];self.hi,self.lo=0xa6000010,0xa6000011
 def verify(self):
  assert self.pending is None and self.child_checks==self.expected_children
  assert self.post_calls==([(FREE,(self.outer.object,))]if self.expected_free else[]),(self.outer,self.post_calls,self.expected_free)
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',(o/'func_15147740-original.s').read_text());blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==100 and blob==(r/'conker/conker.us.bin').read_bytes()[0x174bf0:0x174d80];parent=[int(w,16)for _,_,w in rows];before=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(before,PARENT,len(blob));assert before[at:at+len(blob)]==blob
 leaves=[g.bound_blob(*g.payload(o/f,'func_150B40E8'),g.symbols(g.Case()))for f in('original-target.o','selected-owner.o')];count=children=0
 for selector,flags,lifetime,delta,leaf_count,leaf_flag,rm in itertools.product((0,7,15,255),(0,1,16,17),(-1,0,10),(-1,0,1),(0,3),(0,1),range(4)):
  c=g.Case(delta=delta,count=leaf_count,flags=leaf_flag,lifetime=1,rm=rm,phase=8*(rm&1));models=[Connected(parent,leaf,c,selector,flags,lifetime).run().verify()for leaf in leaves];a,b=models;assert g.state(a)==g.state(b)and a.post_calls==b.post_calls and a.post_observations==b.post_observations;count+=1;children+=a.child_checks
 controls=[]
 for name,c,kwargs,expected in [('force-zero-success',g.Case(),dict(poison=0),True),('force-one-failure',g.Case(count=0,flags=1),dict(poison=1),False),('invert-zero-test',g.Case(),dict(invert=True),True)]:
  m=Connected(parent,leaves[0],c,7,0,10,**kwargs).run();assert m.pending is None and m.child_checks==1 and bool(m.post_calls)==expected;assert m.r[29]==m.before[29]and m.r[31]==m.before[31];controls.append(dict(name=name,complete_parent_execution=True,changed_expiration_decision=True))
 q=dict(parent_words_pinned=100,parent_frame=32,parent_linked_byte_exact=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,actual_unsigned_first_selector7_JALR_and_zero_result_consumer=True,lifetime_and_invalid_unsigned_selector_paths=True,second_dispatch_zero_skip_third_disabled_or_minus_one=True,full_parent_execution_on_qualified_paths=True,child_memory_ABI_HILO_FP_and_return_reference_equal=True,opaque_expiration_helper_not_full_implementation=True,no_new_parent_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
