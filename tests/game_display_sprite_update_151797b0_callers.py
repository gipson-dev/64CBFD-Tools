"""Complete original sprite wrapper, bounded zero frame-speed callback paths."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_display_sprite_update_151797b0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_display_sprite_update_151797b0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x15168870;RETURN=0x15168A00;CALLBACK_TABLE=0x8008C9C8
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();asm=(o/'baseline/conker/asm/nonmatchings/game_1944C0/func_15168870.s').read_text();rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',asm);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==111 and blob==rom[0x195D20:0x195EDC];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));assert old[at:at+len(blob)]==blob;table=rom[0x231488:0x23150C];pos=elf_slot_offset(old,CALLBACK_TABLE,132);assert old[pos:pos+132]==table and struct.unpack_from('>I',table,4)[0]==g.ENTRY and struct.unpack_from('>I',table,12)[0]==0;return[int(w,16)for _,_,w in rows],table
def fixture(c,tag,frame_phase):
 m=g.fixture(c);_,table=retained()
 for i,v in enumerate(table):m[CALLBACK_TABLE+i]=v
 p=g.address(c);g.put(m,p+0x9A,0,2);g.put(m,p+0x98,frame_phase,2);m[p+0xB2]=tag&255;return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,tag,frame_phase,poison=None):
  super().__init__(parent,c,memory=fixture(c,tag,frame_phase),entry=PARENT,arguments=(g.address(c),),connected=dict(zip(range(g.ENTRY,g.ENTRY+776,4),leaf)));self.outer=c;self.pending=None;self.parent_calls=[];self.child_count=0;self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(1)));assert args==(g.address(self.outer),);self.parent_calls.append((t,args));self.c=replace(self.outer,phase=self.outer.phase-24);self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.calls),len(self.fp_operations));return
  super().record_call(t)
 def child_return(self):
  (memory,calls,ops,csr),nc,no=self.pending;got=(g.public(self.memory,self.c),self.calls[nc:],self.fp_operations[no:],self.fcsr);want=(g.public(memory,self.c),calls,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_count+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def verify(self):
  c=self.outer;m=dict(self.initial);p=g.address(c);assert g.read(m,p+0x9A,2)==0;tag=m[p+0xB2];parent=[];calls=[];ops=[];csr=c.rm|c.fp_flags;children=0
  if tag!=255 and g.read(m,CALLBACK_TABLE+4*tag):
   parent.append((g.ENTRY,(p,)));m,calls,ops,csr=g.reference(m,replace(c,phase=c.phase-24),csr);children=1
  if g.half(g.read(m,p+0x98,2))==-1:
   calls.append((g.RELEASE,(p,)));g.effect(m,c,g.RELEASE,p);csr=(csr&~0x3F000)|c.provider_flags
  got=(g.public(self.memory,c),self.parent_calls,self.calls,self.fp_operations,self.fcsr);want=(g.public(m,c),parent,calls,ops,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)],calls=self.calls,wanted=calls);assert self.pending is None and self.child_count==children;assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,_=retained();leaves=[g.bound_blob(*g.payload(o/f,'func_151797B0'),g.symbols())for f in('original-target.o','normalized-target.o')];count=children=0;seen=set()
 for tag,frame_phase,coords,flags,mutation,rm in itertools.product((-1,3,1),(-1,0,900),((0,0,0),(2000,-2000,2000),(-501,501,0)),range(4),(0,2,3),(0,3)):
  c=g.Case(coords=coords,flags=flags,mutation=mutation,rm=rm,phase=8*(rm&1),seed=count);models=[Connected(parent,w,c,tag,frame_phase).run().verify()for w in leaves];assert g.state(models[0])==g.state(models[1])and models[0].parent_calls==models[1].parent_calls;seen.update(x for x in models[0].visits if PARENT<=x<PARENT+444);count+=1;children+=models[0].child_count
 c=g.Case(coords=(2000,-2000,0),flags=2,mutation=2);base=Connected(parent,leaves[0],c,1,0).run().verify();controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(parent,leaves[0],c,1,0,poison=value).run().verify();assert(g.public(m.memory,c),m.calls,m.parent_calls)==(g.public(base.memory,c),base.calls,base.parent_calls);controls.append(dict(value=hex(value),complete_parent_execution=True,public_effects_unchanged=True))
 q=dict(parent_words_pinned=111,parent_frame=24,parent_words_executed=len(seen),callback_table_bytes_pinned=132,callback_table_index=1,parent_frozen_ELF_slot_equals_original=True,actual_parent_source_not_newly_recovered_or_credited=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,complete_original_parent_on_zero_frame_speed_paths_only=True,independent_complete_parent_reference_on_qualified_paths=True,signed_callback_sentinel_minus_one_null_cell_and_live_phase_cleanup_qualified=True,nonzero_frame_speed_animation_paths_not_executed_or_claimed=True,entry_void_SpriteFrameState_pointer_ABI_and_ignored_result=True,void_return_poison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
