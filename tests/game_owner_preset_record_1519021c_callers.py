"""Complete original parent, six argument homes and consumed child pointer."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_owner_preset_record_1519021c_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_owner_preset_record_1519021c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;ENTRY=0x1518F5D0;MAIN=0x80000;DESCRIPTOR=0x90000;ALLOC=0x151D2F00;RESOURCE=0x151D2AB0;EVENT=0x1000FA64
def original():
 text=(o/'baseline/conker/asm/1BA1D0.s').read_text().split('glabel func_1518F5D0\n',1)[1].split('endlabel func_1518F5D0',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));at=int(rows[0][0],16);assert blob==g.rom()[at:at+len(blob)];elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();live=(r/'conker/build/conker.us.elf').read_bytes();start=elf_slot_offset(elf,ENTRY,len(blob));assert elf[start:start+len(blob)]==live[start:start+len(blob)]!=blob;assert 'void *func_1518F5D0()'in(o/'baseline/conker/src/game/generated_1BA1D0.c').read_text();return [int(w,16)for _,_,w in rows]
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==0x1518F71C and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,selector=0,allocated=True,provider=False,poison=None):
  m=g.fixture(c)
  for base,n in((MAIN,256),(DESCRIPTOR,96)):m.update({base+i:(i*19+c.seed+0x75)&255 for i in range(n)})
  self.outer=c;self.allocated=allocated;self.provider=provider;self.poison=poison;self.selector=selector;self.pending=None;self.child_count=0;self.child_answer=None;self.parent_observations=[];code={}if provider else dict(zip(range(g.ENTRY,g.ENTRY+436,4),leaf));arguments=(g.ACTOR,DESCRIPTOR,c.lifetime,0xABCD0080,0x123400FF,selector,0xABCDEF7F,8,c.channel,c.context);super().__init__(parent,c,memory=m,entry=ENTRY,arguments=arguments,connected=code);self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(map(g.u32,self.arguments(6)));self.calls.append((t,a));self.events.append(('CALL',t,a));assert a==(MAIN,g.ACTOR,self.selector&255,g.u32(g.half(self.outer.lifetime)),self.outer.channel&255,g.u32(self.outer.context)),a;self.c=replace(self.outer,parent=a[0],actor=a[1],preset=a[2],lifetime=a[3],channel=a[4],context=a[5],phase=self.outer.phase-200);self.home=self.r[29];self.pending=(g.reference(self.memory,self.c,home=self.home,arguments=a,initial_fcsr=self.fcsr),len(self.calls),len(self.observations),len(self.fp_operations));return
  if t in(ALLOC,RESOURCE,EVENT)or(t==g.COPY and self.pending is None):
   n={ALLOC:4,RESOURCE:1,EVENT:12,g.COPY:3}[t];a=tuple(map(g.u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.parent_observations.append((t,a,g.data(self.memory,a[0],14)if t==ALLOC else g.data(self.memory,a[1],a[2])if t==g.COPY else b''));return
  super().record_call(t)
 def child_return(self):
  want,calls,obs,ops=self.pending;actual=(g.public(self.memory,self.c),self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr,self.r[2]);assert actual==want,dict(components=[a==b for a,b in zip(actual,want)]);self.child_answer=self.r[2];self.pending=None;self.child_count+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t==g.ENTRY:
   assert self.provider;want,_,_,_=self.pending;memory,calls,obs,ops,csr,value=want;self.memory.update(memory);self.calls.extend(calls);self.observations.extend(obs);self.fp_operations.extend(ops);self.fcsr=csr;self.child_answer=value;self.pending=None;self.child_count+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  elif t==ALLOC:value=MAIN if self.allocated else 0
  elif t==RESOURCE:value=0x12345678
  elif t==EVENT:value=0x87654321
  elif t==g.COPY and self.pending is None:
   a=self.calls[-1][1]
   for i,b in enumerate(g.data(self.memory,a[1],a[2])):self.memory[a[0]+i]=b
   value=0xDEADBEEF
  else:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA6000000+i
  self.f[:20]=[0xA6000000+i for i in range(20)];self.r[2]=value
 def verify(self,poison=False):
  assert self.pending is None;assert self.r[2]==(MAIN if self.allocated else 0);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:]
  expected=0 if not self.allocated or self.selector&255==255 else 1;assert self.child_count==expected
  if self.allocated:assert g.read(self.memory,MAIN+0x84)==(self.poison if poison else self.child_answer)if self.child_count else g.read(self.memory,MAIN+0x84)==0
  return self
def observable(m):return g.public(m.memory,m.outer),m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2],m.parent_observations
def hits(data,needle):
 result=[];at=data.find(needle)
 while at!=-1:
  if at%4==0:result.append(at)
  at=data.find(needle,at+1)
 return result
def main():
 parent=original();assert len(parent)==125 and parent[0]==0x27BDFF38;leaves=[g.bound_blob(*g.payload(o/f,'func_1519021C'),g.symbols())for f in('original-target.o','selected-owner.o')];seen=set();children=0;rows=list(itertools.product((0,23,24,127,128,255),(0xFFFFFFFF,0,0x8000,0x7FFF),(0,1),(0,1),(0,1)))
 for selector,life,allocated,success,mutation in rows:
  c=g.Case(lifetime=life,success=success,mutation=mutation,rm=3 if mutation else 0,seed=selector);models=[Connected(parent,leaf,c,selector,allocated).run().verify()for leaf in leaves];provider=Connected(parent,leaves[0],c,selector,allocated,provider=True).run().verify();assert g.state(models[0])==g.state(models[1]);assert observable(models[0])==observable(provider),dict(selector=selector,life=life,parts=[a==b for a,b in zip(observable(models[0]),observable(provider))]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+500);children+=models[0].child_count
 base=Connected(parent,leaves[0],g.Case()).run().verify();controls=[]
 for poison in(0,1,0xFFFFFFFF):
  other=Connected(parent,leaves[0],g.Case(),poison=poison).run().verify(poison=True);assert g.read(base.memory,MAIN+0x84)!=g.read(other.memory,MAIN+0x84);controls.append(dict(return_poison=poison,changed_actual_parent_child_store=True))
 jal=0x0C000000|((g.ENTRY&0x0FFFFFFF)>>2);direct=hits(g.rom(),struct.pack('>I',jal));assert direct==[0x1BCBC4],direct;pointers=hits(g.rom(),struct.pack('>I',g.ENTRY));assert len(seen)==125,(len(seen),sorted(set(range(ENTRY,ENTRY+500,4))-seen))
 q=dict(parent_words_pinned=125,parent_frame=200,parent_ASM_ROM_equal=True,production_parent_still_stub_and_full_slot_unchanged_from_frozen_ELF=True,complete_original_parent_executed=True,cases_per_parent_per_stream=len(rows),connected_children_per_stream=children,streams=2,parent_words_executed=125,six_arguments_signed_s16_life_s8_selector_and_u8_channel_qualified=True,all_raw_and_original_private_states_equal=True,independent_semantic_leaf_provider_counterpart=True,provider_private_stack_identity_not_claimed=True,parent_consumes_child_pointer_at_main84_and_returns_main_record=True,allocation_failure_selector_minus1_and_child_null_paths_qualified=True,aligned_direct_JAL_offsets=[hex(x)for x in direct],aligned_pointer_offsets=[hex(x)for x in pointers],other_parent_services_opaque=True,no_new_parent_or_helper_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
