"""Complete original two-bank registered list walker connected to kind0x3E."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_owner_lifecycle_151d2f90_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_owner_lifecycle_151d2f90_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x151670C0;RETURN=0x15167178;REGISTRY=0x8008B4A8;HEADS=0x800DCE50;DEPTH=0x800DD190;NEXT=0x800DD198;KIND=0x3E
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();old=(o/'baseline/conker/build/conker.us.elf').read_bytes();asm=(o/'baseline/conker/asm/nonmatchings/game_1944C0/func_151670C0.s').read_text();rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',asm);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==74 and blob==rom[0x194570:0x194698]and blob==old[(at:=elf_slot_offset(old,PARENT,296)):at+296]
 table=rom[0x22FF68:0x22FF68+101*52];assert len(table)==5252 and struct.unpack_from('>I',table,KIND*52)[0]==g.ENTRY and old[(at:=elf_slot_offset(old,REGISTRY,5252)):at+5252]==table;return[int(w,16)for _,_,w in rows],table
def fixture(c,bank,chain,depth):
 m=g.fixture(c);_,table=retained()
 for i,v in enumerate(table):m[REGISTRY+i]=v
 for i in range(832):m[HEADS+i]=0
 for i in range(32):m[NEXT+i]=(i*11+91)&255
 m[DEPTH]=depth;g.put(m,HEADS+bank*416+KIND*4,c.object if chain else 0);g.put(m,c.object+8,g.FOLLOW if chain==2 else 0);g.put(m,g.FOLLOW+8,0);return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,bank,chain,depth,poison=None):
  super().__init__(parent,c,memory=fixture(c,bank,chain,depth),entry=PARENT,arguments=(),connected=dict(zip(range(g.ENTRY,g.ENTRY+416,4),leaf)));self.outer=c;self.pending=None;self.children=0;self.parent_calls=[];self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(1));self.parent_calls.append((t,args));self.c=replace(self.outer,object=args[0],phase=self.outer.phase-64);self.pending=(g.reference(self.memory,self.c),len(self.calls));return
  super().record_call(t)
 def child_return(self):
  (memory,calls),n=self.pending;assert(g.public(self.memory,self.c),self.calls[n:])==(g.public(memory,self.c),calls);self.pending=None;self.children+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def verify(self):
  m=dict(self.initial);parent_calls=[];providers=[]
  for row in range(2):
   for kind in range(101):
    target=g.read(m,REGISTRY+kind*52)
    if not target:continue
    p=g.read(m,HEADS+row*416+kind*4);m[DEPTH]=(m[DEPTH]+1)&255
    while p:
     assert target==g.ENTRY;g.put(m,NEXT+4*m[DEPTH],g.read(m,p+8));parent_calls.append((target,(p,)));c=replace(self.outer,object=p,phase=self.outer.phase-64);m,calls=g.reference(m,c);providers.extend(calls);p=g.read(m,NEXT+4*m[DEPTH])
    m[DEPTH]=(m[DEPTH]-1)&255
  got=(g.public(self.memory,self.outer),self.parent_calls,self.calls);want=(g.public(m,self.outer),parent_calls,providers);assert got==want,dict(case=str(self.outer),parts=[a==b for a,b in zip(got,want)],memory=[(hex(a),got[0].get(a),want[0].get(a))for a in got[0].keys()|want[0].keys()if got[0].get(a)!=want[0].get(a)][:12],calls=self.parent_calls,wanted=parent_calls,providers=self.calls,wanted_providers=providers);assert self.pending is None and self.children==len(parent_calls);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,_=retained();leaves=[g.bound_blob(*g.payload(o/f,'func_151D2F90'),g.symbols())for f in('original-target.o','selected-owner.o')];count=children=0;seen=set()
 for bank,chain,depth,phase,(gate,flags,available,life,mutation)in itertools.product((0,1),(0,1,2),(0,3),(0,8),((0,0,1,300,0),(0,2,0,300,1),(0,1,1,0,2),(1,3,1,-1,0))):
  c=g.Case(gate=gate,flags=flags,available=available,lifetime=life,mutation=mutation,phase=phase,seed=count);models=[Connected(parent,w,c,bank,chain,depth).run().verify()for w in leaves];assert g.state(models[0])==g.state(models[1])and models[0].parent_calls==models[1].parent_calls;seen.update(x for x in models[0].visits if PARENT<=x<PARENT+296);count+=1;children+=models[0].children
 c=g.Case();base=Connected(parent,leaves[0],c,0,2,0).run().verify();controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(parent,leaves[0],c,0,2,0,poison=value).run().verify();assert(g.public(m.memory,c),m.calls,m.parent_calls)==(g.public(base.memory,c),base.calls,base.parent_calls);controls.append(dict(poisoned_value=hex(value),complete_parent_executed=True,public_effects_unchanged=True))
 q=dict(parent_words_pinned=74,parent_frame=64,parent_words_executed=len(seen),registry_bytes_pinned=5252,registry_index=62,registry_stride=52,cases_per_stream=count,streams=2,connected_children_per_stream=children,complete_original_parent_on_qualified_paths=True,independent_complete_parent_reference=True,two_banks_empty_single_double_chains_and_nested_depth=True,entry_void_struct102_pointer_ABI_and_parent_ignores_return=True,full_private_states_and_saved_ABI_equal=True,opaque_leaf_providers_not_original_helper_execution=True,void_return_poison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
