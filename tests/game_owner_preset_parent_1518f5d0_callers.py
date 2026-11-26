"""Complete preset-selector wrapper and ten-word parent ABI/returned pointer."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_owner_preset_parent_1518f5d0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_owner_preset_parent_1518f5d0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;ENTRY=0x1518F51C;SELECT=0x1518FDC4;TABLE=0x8008D630
def original():
 text=(o/'baseline/conker/asm/1BA1D0.s').read_text().split('glabel func_1518F51C\n',1)[1].split('endlabel func_1518F51C',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));at=int(rows[0][0],16);elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();start=elf_slot_offset(elf,ENTRY,len(blob));assert blob==g.rom()[at:at+len(blob)]==elf[start:start+len(blob)];return [int(w,16)for _,_,w in rows]
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==g.ENTRY+0x14C and self.owner.in_child:self.owner.child_return()
  if pc==ENTRY+0xA4 and self.owner.pending is not None:self.owner.parent_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,wrapper,parent,c,nonnull=1,selected=1,index=0,variant=0,provider=False,poison=None,wrong_stride=False):
  m=g.fixture(c)
  for i in range(3):
   g.put(m,TABLE+4*i,g.DESCRIPTOR+512*i)
   for j in range(512):m[g.DESCRIPTOR+512*i+j]=(j*31+i*17+c.seed)&255
  self.wrapper_case=c;self.nonnull=nonnull;self.selected=selected;self.index=index;self.variant=variant;self.provider=provider;self.poison=poison;self.wrong_stride=wrong_stride;self.pending=None;self.parent_count=0;self.selector_count=0;code={}if provider else dict(zip(range(g.ENTRY,g.ENTRY+500,4),parent));arguments=(g.ACTOR if nonnull else 0,variant,c.lifetime,c.first,c.second,c.preset,c.value,c.extra,c.channel,c.context);super().__init__(wrapper,c,memory=m,entry=ENTRY,arguments=arguments,connected=code);self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t==SELECT:
   a=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,a));self.events.append(('CALL',t,a));assert a==(g.ACTOR,g.STACK+self.wrapper_case.phase-56+0x33,self.variant&255);self.selector_count+=1;return
  if t==g.ENTRY:
   a=tuple(map(g.u32,self.arguments(10)));expected=(g.ACTOR,g.DESCRIPTOR+self.index*512+(self.variant&255)*80,g.u32(g.half(self.wrapper_case.lifetime)),g.u32(g.sbyte(self.wrapper_case.first)),g.u32(g.sbyte(self.wrapper_case.second)),g.u32(g.sbyte(self.wrapper_case.preset)),self.wrapper_case.value&255,g.u32(self.wrapper_case.extra),self.wrapper_case.channel&255,g.u32(self.wrapper_case.context))
   assert a==expected or(self.wrong_stride and a[:1]+a[2:]==expected[:1]+expected[2:]),(a,expected);self.calls.append((t,a));self.events.append(('CALL',t,a));self.outer=replace(self.wrapper_case,lifetime=a[2],first=a[3],second=a[4],preset=a[5],value=a[6],extra=a[7],channel=a[8],context=a[9],descriptor_pointer=a[1],phase=self.wrapper_case.phase-56);self.c=self.outer;self.home=self.r[29];self.pending=(g.reference(self.memory,self.outer),len(self.calls),len(self.observations),len(self.fp_operations));return
  super().record_call(t)
 def parent_return(self):
  want,calls,obs,ops=self.pending;actual=(g.public(self.memory,self.outer),self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr,self.r[2]);assert actual==want,dict(components=[a==b for a,b in zip(actual,want)]);self.pending=None;self.parent_count+=1;self.outer=self.wrapper_case;self.c=self.outer;self.home=g.STACK+self.outer.phase
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t==g.ENTRY:
   assert self.provider;want,_,_,_=self.pending;memory,calls,obs,ops,csr,value=want;self.memory.update(memory);self.calls.extend(calls);self.observations.extend(obs);self.fp_operations.extend(ops);self.fcsr=csr;self.pending=None;self.parent_count+=1;self.outer=self.wrapper_case;self.c=self.outer;self.home=g.STACK+self.outer.phase
  elif t==SELECT:self.memory[self.calls[-1][1][1]]=self.index;value=self.selected
  else:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB7000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA7000000+i
  self.f[:20]=[0xA7000000+i for i in range(20)];self.hi,self.lo=0xA7000010,0xA7000011;self.r[2]=g.u32(value)
 def verify(self,poison=False):
  assert self.pending is None and not self.in_child;expected=int(bool(self.nonnull and self.selected));assert self.parent_count==expected and self.selector_count==int(bool(self.nonnull));value=g.main_pointer(self.wrapper_case)if expected and self.wrapper_case.allocated else 0;assert self.r[2]==(self.poison if poison else value);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def observable(m):return g.public(m.memory,m.wrapper_case),m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]
def hits(data,needle):
 result=[];at=data.find(needle)
 while at!=-1:
  if at%4==0:result.append(at)
  at=data.find(needle,at+1)
 return result
def main():
 wrapper=original();assert len(wrapper)==45 and wrapper[0]==0x27BDFFC8;parents=[g.bound_blob(*g.payload(o/f,'func_1518F5D0'),g.symbols())for f in('original-target.o','selected-owner.o')];seen=set();count=0;connected=0
 for nonnull,selected,index,variant,allocated,success,mutation in itertools.product((0,1),(0,1),(0,2),(0,1,0xABCD0003),(0,1),(0,1),(0,1)):
  c=g.Case(preset=23 if mutation else 255,lifetime=0xFFFFFFFF if success else 0x12348000,allocated=allocated,success=success,parent_mutation=mutation,mutation=mutation,rm=3 if mutation else 0);models=[Connected(wrapper,p,c,nonnull,selected,index,variant).run().verify()for p in parents];provider=Connected(wrapper,parents[0],c,nonnull,selected,index,variant,provider=True).run().verify();assert g.state(models[0])==g.state(models[1]);assert observable(models[0])==observable(provider),dict(components=[a==b for a,b in zip(observable(models[0]),observable(provider))]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+180);count+=1;connected+=models[0].parent_count
 base=Connected(wrapper,parents[0],g.Case(),variant=1).run().verify();controls=[]
 for poison in(0,1,0xFFFFFFFF):
  m=Connected(wrapper,parents[0],g.Case(),variant=1,poison=poison).run().verify(poison=True);assert observable(m)!=observable(base);controls.append(dict(parent_return_poison=poison,wrapper_returns_changed_pointer=True))
 changed=wrapper[:];index=(0x1518F594-ENTRY)//4;assert changed[index]==0x00084100;changed[index]=0x000840C0;m=Connected(changed,parents[0],g.Case(),variant=1,wrong_stride=True).run().verify();assert observable(m)!=observable(base);controls.append(dict(name='wrong-preset-stride40',complete_execution=True,comparison_rejected=True))
 jal=0x0C000000|((g.ENTRY&0x0FFFFFFF)>>2);direct=hits(g.rom(),struct.pack('>I',jal));assert direct==[0x1BCA68],direct;pointers=hits(g.rom(),struct.pack('>I',g.ENTRY));assert len(seen)==45,(len(seen),sorted(set(range(ENTRY,ENTRY+180,4))-seen))
 q=dict(wrapper_words=45,wrapper_frame=56,wrapper_ASM_ROM_frozen_ELF_equal=True,complete_original_wrapper_executed=True,cases_per_wrapper_per_stream=count,connected_parents_per_stream=connected,streams=2,wrapper_words_executed=45,all_ten_argument_widths_and_80byte_preset_stride_qualified=True,all_raw_and_original_private_states_equal=True,independent_semantic_parent_provider_counterpart=True,provider_private_stack_identity_not_claimed=True,null_actor_failed_selector_failed_allocator_and_passthrough_return_qualified=True,aligned_direct_JAL_offsets=[hex(x)for x in direct],aligned_pointer_offsets=[hex(x)for x in pointers],selector_and_table_fixture_opaque_not_original_selector_implementation=True,no_new_wrapper_or_helper_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
