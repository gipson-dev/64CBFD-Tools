"""Both complete recovered callers, timer reload and staged-output aliases."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_randomized_effect_factory_150d278c_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_randomized_effect_factory_150d278c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;ACTOR=0x90000;EVENT=0xA0000;DELTA=0x800BE9E4
def original(fn):
 text=(o/'baseline/conker/asm/FFBA0.s').read_text();body=text.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(w for _,_,w in rows));at=int(rows[0][0],16);entry=int(rows[0][1],16);elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();start=elf_slot_offset(elf,entry,len(blob));assert blob==g.rom()[at:at+len(blob)]==elf[start:start+len(blob)];return entry,[int(w,16)for _,_,w in rows]
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==self.owner.return_pc and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,kind,active=1,timer=0,delta=1,selector=0x34,matched=1,alias=False,provider=False,poison=None):
  m=g.fixture(c);m.update({ACTOR+i:(i*19+c.seed+0x75)&255 for i in range(256)});m[ACTOR+0x78]=active;g.put(m,ACTOR+0x28,c.command);g.put(m,ACTOR+0x2C,4);g.put(m,ACTOR+0x30,3);g.put(m,ACTOR+0x34,timer);m[ACTOR+0xC]=c.priority&255;m[ACTOR+1]=c.context&255;m[ACTOR+0x79]=0xA7;m[EVENT]=0xA7 if matched else 0xA6;g.put(m,DELTA,delta)
  self.outer=c;self.kind=kind;self.frame=32 if kind=='tick'else 24;self.return_pc=0x150D2748 if kind=='tick'else 0x150D3348;entry=0x150D26F0 if kind=='tick'else 0x150D32FC;args=(ACTOR,)if kind=='tick'else(ACTOR,EVENT,selector);code={}if provider else dict(zip(range(g.ENTRY,g.ENTRY+408,4),leaf));super().__init__(parent,c,memory=m,entry=entry,arguments=args,connected=code);self.pending=None;self.child_count=0;self.provider=provider;self.poison=poison;self.owner_alias=alias;self.code=ReturnCode(self.code);self.code.owner=self
 def record_call(self,t):
  if t!=g.ENTRY:return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(4)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.c=replace(self.outer,command=args[0],parameters=args[1],priority=args[2],context=args[3],phase=self.outer.phase-self.frame,created=ACTOR if self.owner_alias else g.OUTPUT);self.home=self.r[29];self.pending=(g.reference(self.memory,self.c,home=self.home,arguments=args),len(self.calls),len(self.observations),len(self.fp_operations));self.child_args=args
 def child_return(self):
  want,calls,obs,ops=self.pending;actual=(g.public(self.memory,self.c),self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr);assert actual==want,dict(components=[a==b for a,b in zip(actual,want)],kind=self.kind);self.pending=None;self.child_count+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t!=g.ENTRY:return super().hook(t)
  assert self.provider;want,_,_,_=self.pending;memory,calls,obs,ops,csr=want;self.memory.update(memory);self.calls.extend(calls);self.observations.extend(obs);self.fp_operations.extend(ops);self.fcsr=csr
  for target,_ in calls:self.counts[target]=self.counts.get(target,0)+1
  self.pending=None;self.child_count+=1;self.c=self.outer;self.home=g.STACK+self.outer.phase
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA6000000+i
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=0xDEADBEEF
 def verify(self):
  assert self.pending is None and self.child_count in(0,1);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def observable(m):return g.public(m.memory,m.outer),m.calls,m.observations,m.fp_operations,m.fcsr
def hits(data,needle):
 result=[];at=data.find(needle)
 while at!=-1:
  if at%4==0:result.append(at)
  at=data.find(needle,at+1)
 return result
def main():
 parents={kind:original(fn)[1]for kind,fn in [('tick','func_150D26F0'),('event','func_150D32FC')]};assert [len(parents[k])for k in('tick','event')]==[39,23];leaves=[g.bound_blob(*g.payload(o/f,'func_150D278C'),g.symbols())for f in('original-target.o','selected-owner.o')];counts={};children={};seen={k:set()for k in parents}
 for kind in parents:
  rows=[dict(active=a,timer=t,delta=d,alias=bool(alias))for a,t,d,alias in itertools.product((0,1,2,3),(0,1,0xFFFFFFFF,0x80000000),(1,2),(0,1))]if kind=='tick'else[dict(selector=s,matched=m,alias=bool(alias))for s,m,alias in itertools.product((0x34,0x35,0x12340034,0xFF),(0,1),(0,1))]
  count=child=0;entry=0x150D26F0 if kind=='tick'else 0x150D32FC
  for options in rows:
   for success,mutation,rm in itertools.product((0,1),(0,1),(0,3)):
    c=g.Case(success=success,mutation=mutation,rm=rm,phase=8*(rm&1),priority=255,context=128);models=[Connected(parents[kind],leaf,c,kind,**options).run().verify()for leaf in leaves];provider=Connected(parents[kind],leaves[0],c,kind,provider=True,**options).run().verify();assert g.state(models[0])==g.state(models[1]);assert observable(models[0])==observable(provider);seen[kind].update(x for x in models[0].visits if entry<=x<entry+4*len(parents[kind]));count+=1;child+=models[0].child_count
  counts[kind]=count;children[kind]=child
 for kind in parents:
  base=Connected(parents[kind],leaves[0],g.Case(),kind).run().verify();assert base.child_count==1
  for poison in(0,1,0xFFFFFFFF):
   other=Connected(parents[kind],leaves[0],g.Case(),kind,poison=poison).run().verify();assert observable(base)==observable(other)
 controls=[]
 for name,kind,index,word in [('timer-post-update','tick',(0x150D2768-0x150D26F0)//4,0x01F87023),('event-selector','event',(0x150D3314-0x150D32FC)//4,0x24010035)]:
  before=Connected(parents[kind],leaves[0],g.Case(success=0),kind).run().verify();changed=parents[kind][:];changed[index]=word;after=Connected(changed,leaves[0],g.Case(success=0),kind).run().verify();assert observable(before)!=observable(after);controls.append(dict(name=name,complete_parent_execution=True,wrong_behavior_rejected=True))
 jal=0x0C000000|((g.ENTRY&0x0FFFFFFF)>>2);direct=hits(g.rom(),struct.pack('>I',jal));assert direct==[0xFFBF0,0x1007F0];pointers=hits(g.rom(),struct.pack('>I',g.ENTRY));missing={}
 for kind in parents:
  entry=0x150D26F0 if kind=='tick'else 0x150D32FC;missing[kind]=sorted(set(range(len(parents[kind])))-{(x-entry)//4 for x in seen[kind]})
 assert missing==dict(tick=[33],event=[]),missing
 q=dict(parent_words_pinned=dict(tick=39,event=23),parent_frames=dict(tick=32,event=24),parents_ASM_ROM_frozen_ELF_equal=True,complete_original_parents_executed=True,cases_per_parent_per_stream=counts,connected_children_per_parent_per_stream=children,streams=2,parent_words_executed={k:len(v)for k,v in seen.items()},unreachable_constant_divisor_break_indices=missing,all_4argument_signed_widths_and_byte_forwarding_qualified=True,full_raw_and_original_private_states_equal=True,independent_semantic_leaf_provider_counterpart=True,provider_private_stack_identity_not_claimed=True,both_callers_ignore_child_V0_six_poison_cases=True,parent_void_returns_not_independently_equated=True,post_child_timer_range_and_base_reloaded_including_owner_alias=True,allocator_return_aliases_owner_and_staged_input=True,aligned_direct_JAL_offsets=[hex(x)for x in direct],aligned_pointer_offsets=[hex(x)for x in pointers],additional_parent_RNG_opaque=True,no_new_parent_or_helper_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
