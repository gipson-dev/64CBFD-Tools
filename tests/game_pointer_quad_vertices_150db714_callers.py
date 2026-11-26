"""Complete retail vertex dispatcher, independent leaf provider and return cuts."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_pointer_quad_vertices_150db714_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_pointer_quad_vertices_150db714_guest as g
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x1513DB00;RETURN=0x1513DC2C;FREE=0x100043B4
def original():
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',(o/'baseline/conker/asm/nonmatchings/game_169510/func_1513DB00.s').read_text());blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==295 and blob==g.rom()[0x16AFB0:0x16B44C];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));assert old[at:at+len(blob)]!=blob;return[int(w,16)for _,_,w in rows]
def fixture(c,flags,enabled,visible,attached,animation):
 old=base.Case(view=c.view,width=c.width,height=c.height,fresh=c.fresh,success=c.success,page=c.page,phase=c.phase)
 with patch.object(base,'rom',g.rom):m=base.caller_fixture(old,flags,enabled,visible,attached,animation)
 leaf=g.fixture(c);m.update({a:v for a,v in leaf.items()if g.INPUT<=a<g.INPUT+128 or g.TABLE<=a<g.TABLE+260 or g.COEFFICIENT<=a<g.COEFFICIENT+4 or g.ACTOR+0x110<=a<g.ACTOR+0x124});m[g.ACTOR+0x73]=8;table=g.rom()[0x22E8DC:0x22E978];assert len(table)==156 and struct.unpack_from('>I',table,32)[0]==g.ENTRY
 oldelf=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(oldelf,base.TABLE,156);assert oldelf[at:at+156]==table;return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,flags=0,enabled=1,visible=255,attached=0,animation=255,provider=False,poison=None,has_buffer=None):
  memory=fixture(c,flags,enabled,visible,attached,animation)
  if has_buffer is not None:g.put(memory,g.slot(c),g.BUFFER if has_buffer else 0)
  code={}if provider else dict(zip(range(g.ENTRY,g.ENTRY+712,4),leaf));super().__init__(parent,c,memory=memory,entry=PARENT,arguments=(base.GFX,g.ACTOR,g.u32(c.view)),connected=code);self.outer=c;self.pending=None;self.child_checks=0;self.provider=provider;self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self;self.gl_calls=[]
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(2));assert args==(g.ACTOR,g.u32(g.half(self.outer.view)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.c=replace(self.outer,view=args[1],phase=self.outer.phase-144);self.home=self.r[29];expected=g.reference(self.memory,self.c,home=self.home,initial_fcsr=self.fcsr);self.pending=(expected,len(self.calls),len(self.fp_operations));return
  if t in(g.BACKEND,g.COPY,g.ALLOC,g.ANGLE):return super().record_call(t)
  counts={FREE:2,0x151462C8:9,0x151441A4:14,0x151442FC:14,0x15142B7C:3,0x15142E24:11,0x15142C10:6,0x15142CF0:8,0x1513F4E4:3,0x15142FBC:3};assert t in counts,hex(t);args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args));self.gl_calls.append((t,args))
 def child_return(self):
  want,calls,ops=self.pending;got=(g.public(self.memory,self.c),self.calls[calls:],self.fp_operations[ops:],self.fcsr,self.r[2]);assert got==want,dict(components=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_checks+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t==g.ENTRY:
   assert self.provider;want,_,_=self.pending;memory,calls,ops,csr,value=want;self.memory.update(memory);self.calls.extend(calls);self.events.extend(('CALL',a,b)for a,b in calls);self.fp_operations.extend(ops);self.fcsr=csr;self.pending=None;self.child_checks+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  elif t in(g.BACKEND,g.COPY,g.ALLOC,g.ANGLE):return super().hook(t)
  elif t in(0x151441A4,0x151442FC):
   for i,p in enumerate(self.calls[-1][1][:4]):self.put(p,11*(i+1),2)
   value=0
  elif t==FREE:value=0
  else:value=g.u32(self.calls[-1][1][0]+8)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=g.u32(value)
 def verify(self):
  assert self.pending is None and self.child_checks in(0,1);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def observable(m):return g.public(m.memory,m.outer),m.calls,m.fp_operations,m.fcsr,m.r[2]
def main():
 parent=original();leaves=[g.bound_blob(*g.payload(o/f,'func_150DB714'),g.symbols())for f in('original-target.o','selected-owner.o')];seen=set();count=children=0
 for flags,enabled,view,success,animation,attached in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,255),(0,1,2)):
  c=g.Case(view=view,success=success,rm=(flags+view)&3);kw=dict(flags=flags,enabled=enabled,animation=animation,attached=attached);models=[Connected(parent,leaf,c,**kw).run().verify()for leaf in leaves];provider=Connected(parent,leaves[0],c,provider=True,**kw).run().verify();assert g.state(models[0])==g.state(models[1]);assert observable(models[0])==observable(provider);seen.update(x for x in models[0].visits if PARENT<=x<PARENT+1180);count+=1;children+=models[0].child_checks
 for view,success,rm in itertools.product((0xFFFF,0x12340002),(0,1),range(4)):
  c=g.Case(view=view,success=success,rm=rm);models=[Connected(parent,leaf,c).run().verify()for leaf in leaves];provider=Connected(parent,leaves[0],c,provider=True).run().verify();assert g.state(models[0])==g.state(models[1])and observable(models[0])==observable(provider);count+=1;children+=models[0].child_checks
 for has_buffer in(0,1):
  c=g.Case(view=1);kw=dict(flags=8,visible=0,has_buffer=has_buffer);models=[Connected(parent,leaf,c,**kw).run().verify()for leaf in leaves];provider=Connected(parent,leaves[0],c,provider=True,**kw).run().verify();assert g.state(models[0])==g.state(models[1])and observable(models[0])==observable(provider);seen.update(x for x in models[0].visits if PARENT<=x<PARENT+1180);count+=1;children+=models[0].child_checks
 controls=[]
 for name,c,poison in(('hide-buffer',g.Case(success=1),0),('invent-buffer',g.Case(success=0),g.BUFFER)):
  a=Connected(parent,leaves[0],c).run().verify();z=Connected(parent,leaves[0],c,poison=poison).run().verify();assert a.child_checks==z.child_checks==1 and observable(a)!=observable(z);controls.append(dict(name=name,complete_parent_execution=True,pointer_return_consumer_rejected=True))
 missing=sorted(set(range(295))-{(x-PARENT)//4 for x in seen});assert missing==[115,146],missing;q=dict(original_parent_words_pinned=295,parent_frame=144,parent_ASM_ROM_equal=True,production_dispatcher_still_unrestored_and_unchanged=True,actual_table_entries=39,selector_byte='0x73',table_index=8,signed16_view_and_pointer_return_ABI=True,cases_per_stream=count,connected_children_per_stream=children,streams=2,independent_semantic_leaf_provider_counterpart=True,parent_full_private_literal_stream_identity=True,semantic_provider_private_stack_identity_not_claimed=True,original_parent_words_executed=len(seen),unreachable_duplicate_default_indices=missing,render_services_and_free_opaque=True,no_new_parent_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
