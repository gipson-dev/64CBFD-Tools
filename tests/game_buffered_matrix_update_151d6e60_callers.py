"""Execute the complete original callback consumer with opaque post helpers."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_buffered_matrix_update_151d6e60_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_buffered_matrix_update_151d6e60_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x151572d0;REFRESH=0x1503f4b0;FREE=0x1516972c;TIMER=0x800be9e4;TABLE=0x8008ad90;MARK=0x70000
@lru_cache(maxsize=1)
def callback_table():
 table=(r/'conker/conker.us.bin').read_bytes()[0x22f850:0x22f890];assert table[28:32]==bytes.fromhex('151d6e60');return table
def parent_source():
 text=(o/'baseline/conker/asm/183640.s').read_text();return 'glabel func_151572D0\n'+text.split('glabel func_151572D0\n',1)[1].split('endlabel func_151572D0',1)[0]+'endlabel func_151572D0\n'
class ReturnCode(dict):
 def __getitem__(self,pc):
  m=self.owner
  if m.pending is not None and pc in(0x15157348,0x15157384):m.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,selectors,flags,remaining,delta,poison=None,invert=False):
  memory=g.fixture(c);memory[c.object+0x10]=flags;memory[c.object+0x11]=selectors[0]&255;memory[c.object+0x12]=selectors[1]&255;memory[c.object+0x43]=200
  for off,v in((0x16,remaining),(0x64,20),(0x66,3)):g.put(memory,c.object+off,v,2)
  g.put(memory,c.object+0x68,MARK);g.put(memory,TIMER,delta);g.put(memory,MARK,0)
  table=callback_table()
  memory.update({TABLE+i:v for i,v in enumerate(table)})
  connected=dict(zip(range(g.ENTRY,g.ENTRY+416,4),leaf));super().__init__(parent,c,memory=memory,entry=PARENT,arguments=(c.object,),connected=connected)
  self.outer=c;self.pending=None;self.children=[];self.child_checks=0;self.post_calls=[];self.post_observations=[];self.poison=poison
  self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x1515734c]=0x10400002;self.code[0x15157388]=0x10400002
  signed=lambda v:((v&65535)^32768)-32768
  self.expected_expired=bool(flags&1 and signed(remaining-delta)<0)
  self.expected_children=0 if self.expected_expired else sum(v!=-1 for v in selectors)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(1));assert args==(self.outer.object,);self.children.append(args);self.c=replace(self.outer,phase=self.outer.phase-32);self.pending=(g.reference(self.memory,self.c,self.r[16],self.r[31],initial_fcsr=self.fcsr),len(self.calls),len(self.observations),len(self.fp_operations));return
  if t in(REFRESH,FREE):
   args=tuple(self.arguments(1));self.post_calls.append((t,args));self.post_observations.append((dict(self.memory),self.fcsr));return
  super().record_call(t)
 def child_return(self):
  expected,calls,obs,ops=self.pending
  got=(self.memory,self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr,self.r[2]);assert got==expected,dict(reason='connected child reference',case=str(self.c),completed_children=self.child_checks,components_equal=[a==b for a,b in zip(got,expected)],actual_FCSR=self.fcsr,expected_FCSR=expected[-2],memory_differences=[hex(a)for a in self.memory if self.memory[a]!=expected[0].get(a)][:8])
  self.pending=None;self.child_checks+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t not in(REFRESH,FREE):return super().hook(t)
  g.put(self.memory,MARK,g.read(self.memory,MARK)+1)
  for i in range(4):self.put(self.r[29]+4*i,0xb6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa6000000+i
  self.f[:20]=[0xa6000000+i for i in range(20)];self.r[2]=0xdeadbeef;self.hi,self.lo=0xa6000010,0xa6000011;self.fcsr=self.outer.rm|0x100
 def verify(self):
  assert self.pending is None and self.child_checks==self.expected_children and len(self.children)==self.expected_children
  expected=[(FREE,(self.outer.object,))]if self.expected_expired else[(REFRESH,(MARK,))];assert self.post_calls==expected
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',parent_source());blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==84 and blob==(r/'conker/conker.us.bin').read_bytes()[0x184780:0x1848d0];parent=[int(w,16)for _,_,w in rows]
 before=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(before,PARENT,len(blob));linked_exact=before[at:at+len(blob)]==blob
 count=children=0;visits=set();base_symbols=g.symbols(g.Case());leaves=[g.bound_blob(*g.payload(o/f,'func_151D6E60'),base_symbols)for f in('original-target.o','selected-owner.o')]
 for selectors,flags,remaining,delta,page,mode,rm in itertools.product(((7,-1),(-1,3),(7,3),(-1,-1)),(0,1,0x20,0x21),(-1,0,10),(1,0xffffffff),(0,1),(0,15),range(4)):
  c=g.Case(page=page,mode=mode,rm=rm,phase=8*(rm&1));assert g.symbols(c)==base_symbols
  models=[Connected(parent,leaf,c,selectors,flags,remaining,delta).run().verify()for leaf in leaves];a,b=models;assert g.state(a)==g.state(b)and a.post_calls==b.post_calls and a.post_observations==b.post_observations;count+=1;children+=a.child_checks;visits.update(a.visits)
 controls=[];c=g.Case();leaf=g.bound_blob(*g.payload(o/'original-target.o','func_151D6E60'),g.symbols(c))
 for name,extra in [('zero-child-result',dict(poison=0)),('inverted-consumer-test',dict(invert=True))]:
  for selectors in((7,-1),(-1,3)):
   m=Connected(parent,leaf,c,selectors,0,10,1,**extra).run();assert m.pending is None and m.child_checks==1 and m.post_calls==[(FREE,(c.object,))];assert m.r[29]==m.before[29]and m.r[31]==m.before[31]
  controls.append(dict(name=name,both_indexed_sites_execute_to_completion=True,wrong_zero_test_reaches_release_instead_of_refresh=True))
 missing=[hex(v)for v in range(PARENT,PARENT+336,4)if v not in visits]
 assert set(missing)=={'0x15157354','0x15157390'},missing
 q=dict(parent_words_pinned=84,parent_frame=32,parent_linked_body_byte_exact=linked_exact,cases_per_stream=count,streams=2,connected_children_per_stream=children,two_indexed_sites_and_skip_lifetime_paths=True,child_full_memory_frame_provider_FP_and_return_reference_equal=True,complete_original_parent_executed_with_opaque_post_helpers=True,unchanged_parent_source_and_owner_preserved=True,no_new_parent_matching_credit=True,original_one_return_unreachable_zero_branch_words=missing,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
