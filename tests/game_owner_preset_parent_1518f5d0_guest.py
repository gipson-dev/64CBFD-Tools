"""Complete preset parent, captured descriptor and connected original child."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_owner_preset_record_1519021c_guest as child
from tools.tests.game_payload_effect_factory_oracle import data
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_owner_preset_parent_1518f5d0_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x1518F5D0;ACTOR=child.ACTOR;MAIN=0x80000;DESCRIPTOR=0x90000;ALLOC=0x151D2F00;RESOURCE=0x151D2AB0;EVENT=0x1000FA64;CALLBACK=0x1518E298;COPY=child.COPY;u32=child.u32;half=child.half;bits=child.bits;sbyte=lambda x:((x&255)^128)-128
@dataclass(frozen=True)
class Case(child.Case):
 first:int=0xABCD0080
 second:int=0x123400FF
 value:int=0xFEDCBA7F
 extra:int=8
 allocated:int=1
 parent_mutation:int=0
 main_alias:int=0
 descriptor_pointer:int=0

def symbols():return dict(func_151D2F00=ALLOC,func_1519021C=child.ENTRY,func_151D2AB0=RESOURCE,func_1000FA64=EVENT,func_1518E298=CALLBACK,memcpy=COPY)
rom=child.rom
def main_pointer(c):return DESCRIPTOR if c.main_alias==1 else ACTOR if c.main_alias==2 else MAIN
def descriptor(c):return c.descriptor_pointer if c.descriptor_pointer else STACK+c.phase+64 if c.main_alias==3 else DESCRIPTOR
def args(c):return tuple(map(u32,(ACTOR,descriptor(c),c.lifetime,c.first,c.second,c.preset,c.value,c.extra,c.channel,c.context)))
def public(m,c):return child.public(m,c)
def fixture(c):
 m=child.fixture(c)
 for base,n in((MAIN,256),(DESCRIPTOR,256)):m.update({base+i:(i*19+c.seed+0x75)&255 for i in range(n)})
 return m
def effect(m,c,t):
 put(m,child.MARK+4,read(m,child.MARK+4)+1)
 if c.parent_mutation:
  if t in(ALLOC,RESOURCE):
   for i,v in enumerate((bits(-7.5),bits(19.25),bits(-3.5))):put(m,ACTOR+0x14+4*i,v)
   m[ACTOR+0x3B]^=0x55
  if t==COPY:put(m,main_pointer(c)+0x78,0x13579BDF)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;frame=home-200;packet=frame+0x58;header=frame+0xB8;actor,preset,life,first,second,selector,value,extra,channel,context=args(c);life=half(life);csr=c.rm;calls=[];obs=[];ops=[]
 put(m,home+8,u32(c.lifetime));put(m,home+12,u32(c.first));put(m,home+10,life,2)
 put(m,packet,0)
 for i,b in enumerate(data(m,preset,80)):m[packet+4+i]=b
 m[packet+0x58]=first&255;m[packet+0x59]=second&255;m[packet+0x5A]=value&255;put(m,header,actor);m[header+4]=m[actor+0x3B];put(m,header+6,300 if life==-1 else life,2);m[header+8]=0 if life==-1 else 1
 for i in range(9,13):m[header+i]=0
 m[header+13]=1;a=(header,u32(extra+96),channel&255,u32(context));calls.append((ALLOC,a));obs.append((ALLOC,a,data(m,header,16),b''));answer=main_pointer(c)if c.allocated else 0
 if answer:
  for i,b in enumerate(data(m,header,16)):m[answer+16+i]=b
  for off in(32,36,40):put(m,answer+off,0)
  m[answer+24]&=253
 effect(m,c,ALLOC)
 if not answer:return public(m,c),calls,obs,ops,csr,0
 a=(answer+48,packet,92);calls.append((COPY,a));obs.append((COPY,a,data(m,packet,92),b''))
 for i,b in enumerate(data(m,packet,92)):m[a[0]+i]=b
 effect(m,c,COPY)
 if sbyte(selector)!=-1:
  a=(answer,actor,selector&255,u32(life),channel&255,u32(context));calls.append((child.ENTRY,a));cc=replace(c,parent=answer,actor=actor,preset=selector&255,lifetime=u32(life),channel=channel&255,phase=c.phase-200);cm,cs,co,cp,csr,value=child.reference(m,cc,home=frame,arguments=a,initial_fcsr=csr);m.update(cm);calls.extend(cs);obs.extend(co);ops.extend(cp);put(m,answer+0x84,value)
 else:put(m,answer+0x84,0)
 a=(read(m,answer+0x78),);calls.append((RESOURCE,a));obs.append((RESOURCE,a,b'',b''));effect(m,c,RESOURCE);coords=[]
 for i in range(3):
  a=read(m,actor+0x14+4*i);ops.append((13,a,0,csr));v,flags=child.trunc(a);csr=(csr&~0x3F000)|flags;coords.append(u32(half(v)))
 a=(77,*coords,15000,2000,800,CALLBACK,answer,actor,0,0);calls.append((EVENT,a));obs.append((EVENT,a,b'',b''));effect(m,c,EVENT);return public(m,c),calls,obs,ops,csr,answer
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==ENTRY+0x14C and self.owner.in_child:self.owner.child_return()
  return super().__getitem__(pc)
@lru_cache(maxsize=1)
def child_words():
 at=0x1BD6CC;words=list(struct.unpack_from('>109I',rom(),at));elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();start=elf_slot_offset(elf,child.ENTRY,436);assert elf[start:start+436]==rom()[at:at+436];return words
class Machine(child.Machine):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  code=dict(zip(range(child.ENTRY,child.ENTRY+436,4),child_words()));code.update(connected or{});self.outer=c;self.in_child=False;self.child_count=0;super().__init__(words,c,memory=fixture(c)if memory is None else memory,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=code);self.code=ReturnCode(self.code);self.code.owner=self
 def child_return(self):self.in_child=False;self.child_count+=1;self.c=self.outer;self.home=STACK+self.outer.phase
 def record_call(self,t):
  if self.in_child:return super().record_call(t)
  counts={ALLOC:4,COPY:3,child.ENTRY:6,RESOURCE:1,EVENT:12};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==child.ENTRY:self.in_child=True;self.c=replace(self.outer,parent=a[0],actor=a[1],preset=a[2],lifetime=a[3],channel=a[4],context=a[5],phase=self.outer.phase-200);self.home=self.r[29];return
  self.observations.append((t,a,data(self.memory,a[0],16)if t==ALLOC else data(self.memory,a[1],a[2])if t==COPY else b'',b''))
  if t==COPY and self.outer.copy:assert not self.outer.parent_mutation;effect(self.memory,self.outer,t)
 def hook(self,t):
  if self.in_child:return super().hook(t)
  c=self.outer;a=self.calls[-1][1]
  if t==ALLOC:
   value=main_pointer(c)if c.allocated else 0
   if value:
    for i,b in enumerate(data(self.memory,a[0],16)):self.memory[value+16+i]=b
    for off in(32,36,40):put(self.memory,value+off,0)
    self.memory[value+24]&=253
  elif t==COPY:
   for i,b in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=b
   value=0xDEADBEEF
  else:assert t in(RESOURCE,EVENT);value=0x87654321
  effect(self.memory,c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA6000000+i
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=u32(value)
def observable(m):return public(m.memory,m.outer),m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]
state=child.state
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);actual=observable(m);assert actual==want,dict(case=str(c),components=[a==b for a,b in zip(actual,want)],actual_calls=m.calls,wanted_calls=want[1]);assert not m.in_child and all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def pin():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes()
 for entry,at,n in((ALLOC,0x2003B0,144),(COPY,0x22EC0,44)):
  start=elf_slot_offset(elf,entry,n);assert elf[start:start+n]==rom()[at:at+n],hex(entry)
 child_words()
def cases():
 rows=[Case(preset=p,lifetime=l,allocated=a,success=s,parent_mutation=m,mutation=m,main_alias=alias,rm=rm,seed=p+rm,phase=8*(rm&1))for p,l,a,s,m,alias,rm in itertools.product((0,23,24,128,255),(0xFFFFFFFF,0x8000,0x7FFF),(0,1),(0,1),(0,1),(0,1,2,3),(0,3))]
 rows.extend(Case(preset=p,copy=1,success=s,allocated=a,rm=rm)for p,s,a,rm in itertools.product((0,24,255),(0,1),(0,1),range(4)));return rows
def main():
 pin();files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_1518F5D0'),symbols())for f in files];assert all(w==streams[0]for w in streams);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+500)
 prefixes=0
 for c in(Case(),Case(allocated=0),Case(preset=255),Case(preset=24,parent_mutation=1,main_alias=1),Case(copy=1)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert len(seen)==125,(len(seen),sorted(set(range(ENTRY,ENTRY+500,4))-seen))
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=125,fault_prefix_quintuples=prefixes,all_raw_and_literal_full_private_completion_and_fault_states_equal=True,independent_reference_public_memory_calls_header16_payload92_FP_return_and_FCSR_equal=True,unwritten_header3_packet5_and_extra_tail4_preserved_in_guest=True,captured_descriptor_before_aliasing_allocator_and_late_actor_resource_reloads=True,actual109word_child_connected=True,actual11word_memcpy_connected_on_nonmutating_paths=True,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
