"""Original jump-table dispatch, actual owner/selector loads and complete epilogue."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_attachment_vector_effect_150fb324_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_attachment_vector_effect_150fb324_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
PARENT=0x150265CC;WINDOW=0x15028810;RETURN=0x150288F0;JTABLE=0x80096CEC
def retained():
 text=(o/'baseline/conker/asm/50D80.s').read_text().split('glabel func_150265CC\n',1)[1].split('endlabel func_150265CC',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(blob)==3451*4;rom=(g.r/'conker/conker.us.bin').read_bytes();assert blob==rom[0x53A7C:0x57068];elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,PARENT,len(blob));linked=elf[at:at+len(blob)];changes=[hex(PARENT+i)for i in range(0,len(blob),4)if blob[i:i+4]!=linked[i:i+4]];(o/'parent-linked-differences.json').write_text(json.dumps(changes,indent=2)+'\n')
 sizes=[v[2]for _,n,v,_ in symbol_rows(elf)if n=='func_150265CC'];assert sizes==[12];assert linked[:12]==bytes.fromhex('0000102503e0000800000000')
 at=elf_slot_offset(elf,JTABLE,37*4);table=elf[at:at+37*4];targets=struct.unpack('>37I',table);types=[i+0x74 for i,v in enumerate(targets)if v==0x150288E4];assert types,targets
 return {int(p,16):int(w,16)for _,p,w in rows},table,types
class Code(g.Code):
 def __getitem__(self,pc):
  m=self.owner
  if pc==RETURN and m.pending:
   m.pending=False;m.child_returns+=1
   if m.poison is not None:m.r[2]=m.poison
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,leaf,c,route,parent,table,kind,raw=False,poison=None):
  super().__init__(leaf,c,raw);self.entry=WINDOW;self.code=Code({**self.code,**parent},self);h=g.STACK+c.phase;self.before[29]=h+0x750;self.memory[g.ACTOR+4]=kind if route==1 else 0x40;g.put(self.memory,h+0x764,0 if route==0 else g.ACTOR);self.memory[h+0x773]=c.selector&255;g.put(self.memory,h+0xD4,self.before[31]);g.put(self.memory,h+0xD0,self.before[16]);self.memory.update({JTABLE+i:v for i,v in enumerate(table)});self.initial=dict(self.memory);self.parent_calls=[];self.pending=False;self.child_returns=0;self.poison=poison;self.route=route
 def execute(self,w):
  if g.ENTRY<=self.current_pc<g.ENTRY+404:return super().execute(w)
  return g.FactoryOracle.execute(self,w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(3));assert args==(g.ACTOR,self.c.selector&255,1),args;self.parent_calls.append((t,args));self.pending=True;return
  return super().record_call(t)
 def verify(self):
  entered=self.route==1
  if entered:memory,calls,packets,ops,csr=g.reference(self.initial,replace(self.c,selector=self.c.selector&255,context=1))
  else:memory,calls,packets,ops,csr=self.initial,[],[],[],self.c.rm|self.c.flags
  assert(g.public(self.memory,self.c),self.calls,self.packets,self.ops,self.fcsr)==(g.public(memory,self.c),calls,packets,ops,csr)
  assert self.child_returns==int(entered)and not self.pending
  assert self.r[2]==1 and self.r[29]==g.STACK+self.c.phase+0x750
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,table,types=retained();streams=[g.bound_blob(*g.payload(o/f,'func_150FB324'),g.symbols())for f in('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o')];seen=set();count=children=0
 for route,enabled,selector,mutation,phase in itertools.product(range(3),(0,1),(0,1,255,0x87654380),range(8),(0,8)):
  c=g.Case(enabled=enabled,selector=selector,mutation=mutation,phase=phase,rm=count&3,seed=count);models=[Connected(w,c,route,parent,table,types[count%len(types)],i==4).run().verify()for i,w in enumerate(streams)];assert all(g.state(m)==g.state(models[0])for m in models[1:4]);g.raw_relation(models[0],models[4]);seen.update(p for p in models[0].visits if PARENT<=p<PARENT+3451*4);count+=1;children+=models[0].child_returns
 controls=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):m=Connected(streams[0],g.Case(),1,parent,table,types[0],poison=value).run().verify();assert m.r[2]==1;controls.append(hex(value))
 q=dict(parent_words_pinned=3451,parent_frame=1872,parent_words_executed=len(seen),jump_table_entries_pinned=37,actor_types_reaching_original_target=types,bounded_window_start=hex(WINDOW),cases_per_stream=count,streams=5,connected_children_per_stream=children,actual_owner_load_SP764_selector_load_SP773_and_context_one=True,actual_null_owner_likely_branch_default_route_jump_table_and_complete_epilogue=True,independent_public_reference_and_full_normalized_state=True,raw_private_frame_and_schedule_relation=True,entry_void_three_argument_ABI_and_ignored_result=True,return_poison_controls=controls,current_production_parent_is_retained_12_byte_stub=True,original_retail_caller_only_no_parent_matching_credit=True,other_parent_paths_and_global_allocator_extents_not_claimed=True,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
