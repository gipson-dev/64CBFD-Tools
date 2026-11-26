"""Complete original dispatch parent on disabled and oriented-emitter event paths."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_optional_emitter_150d728c_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_optional_emitter_150d728c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x15081E78;RETURN=0x15081F48;OBJECT=0x310000;OWNER=0x320000;COUNTER=0x330000;JTABLE=0x8009CBE4
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();asm=(o/'baseline/conker/asm/AEB40.s').read_text();body=asm.split('glabel func_15081E78\n',1)[1].split('endlabel func_15081E78',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(blob)==1864 and blob==rom[0xAF328:0xAFA70];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));table=rom[0x2416A4:0x2416E8];pos=elf_slot_offset(old,JTABLE,68);assert old[pos:pos+68]==table;events=[i+2 for i,v in enumerate(struct.unpack('>17I',table))if v==0x15081F24];assert events;return[int(w,16)for _,_,w in rows],table,events,old[at:at+len(blob)]==blob
def fixture(c,enabled,counter):
 m=g.fixture(c);_,table,_,_=retained()
 for base,n in((OBJECT-16,0xA0),(OWNER-16,0x340),(COUNTER-16,0x200)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(c.position,c.direction):
  for i,v in enumerate(c.values):g.put(m,p+4*i,v)
 for i,v in enumerate(table):m[JTABLE+i]=v
 m[OBJECT+0x59]=enabled;g.put(m,OWNER+0x31C,COUNTER if counter else 0);g.put(m,COUNTER+0x1AA,32767,2);return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,enabled,counter,event,poison=None):
  super().__init__(parent,c,memory=fixture(c,enabled,counter),entry=PARENT,connected=dict(zip(range(g.ENTRY,g.ENTRY+392,4),leaf)));self.r[4:7]=[OWNER,OBJECT,event];self.outer=c;self.pending=None;self.parent_calls=[];self.child_count=0;self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(5)));assert args==(OBJECT+0x44,OBJECT+8,OBJECT+0x38,255,1);self.parent_calls.append((t,args));self.c=replace(self.outer,phase=self.outer.phase-944);self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.calls),len(self.ops),len(self.observed));return
  super().record_call(t)
 def child_return(self):
  (memory,calls,ops,obs,csr),nc,no,np=self.pending;got=(g.public(self.memory,self.c),self.calls[nc:],self.ops[no:],self.observed[np:],self.fcsr);want=(g.public(memory,self.c),calls,ops,obs,csr);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_count+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def verify(self):
  c=self.outer;m=dict(self.initial);pointer=g.read(m,OWNER+0x31C)
  if pointer:g.put(m,pointer+0x1AA,g.read(m,pointer+0x1AA,2)+1,2)
  enabled=m[OBJECT+0x59];parent=[];calls=[];ops=[];obs=[];csr=c.csr
  if enabled:
   parent.append((g.ENTRY,(OBJECT+0x44,OBJECT+8,OBJECT+0x38,255,1)));m,calls,ops,obs,csr=g.reference(m,replace(c,phase=c.phase-944),csr)
  got=(g.public(self.memory,c),self.parent_calls,self.calls,self.ops,self.observed,self.fcsr,self.r[2]);want=(g.public(m,c),parent,calls,ops,obs,csr,1 if enabled else 0);assert got==want,dict(parts=[a==b for a,b in zip(got,want)]);assert self.pending is None and self.child_count==bool(enabled);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,_,events,matches=retained();leaves=[g.bound_blob(*g.payload(o/f,'func_150D728C'),g.symbols())for f in('original-target.o','selected-owner.o')];count=children=0;seen=set()
 for enabled,counter,mutation,connected,phase in itertools.product((0,1),(0,1),range(8),(0,1),(0,8)):
  c=g.Case(matrix=OBJECT+0x44,position=OBJECT+8,direction=OBJECT+0x38,mutation=mutation,connected=connected,phase=phase,seed=count);models=[Connected(parent,w,c,enabled,counter,events[0]).run().verify()for w in leaves];assert g.state(models[0])==g.state(models[1]);seen.update(x for x in models[0].visits if PARENT<=x<PARENT+1864);count+=1;children+=models[0].child_count
 c=g.Case(matrix=OBJECT+0x44,position=OBJECT+8,direction=OBJECT+0x38);base=Connected(parent,leaves[0],c,1,1,events[0]).run().verify();controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(parent,leaves[0],c,1,1,events[0],value).run().verify();assert(g.public(m.memory,c),m.calls,m.r[2])==(g.public(base.memory,c),base.calls,1);controls.append(dict(value=hex(value),complete_parent_return=True,public_effects_unchanged=True))
 q=dict(parent_words_pinned=466,parent_frame=944,parent_words_executed=len(seen),parent_frozen_ELF_slot_equals_original=matches,actual_parent_source_not_newly_recovered_or_credited=True,pinned_jump_table_bytes=68,selected_original_event=events[0],cases_per_stream=count,streams=2,connected_children_per_stream=children,complete_original_parent_on_disabled_and_selected_event_paths_only=True,independent_complete_parent_reference_on_qualified_paths=True,counter_halfword_increment_and_saved_result_restore_qualified=True,other_event_and_state_paths_not_executed_or_claimed=True,first_large_caller_only_static_ABI_context_qualified=True,entry_void_five_word_ABI_and_ignored_result=True,void_return_poison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
