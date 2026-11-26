"""Both complete original sprite consumers and the actual zero-random provider."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_seed_sprite_tick_151934b4_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_seed_sprite_tick_151934b4_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;TABLE=0x8008c9c8;TEXTURES=0x8008ca4c;TEXTURE=0x60000;FREE=0x1516972c;FACTORY=0x1513c5b0;COLOURS=0x800ab414
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def original(fn,file):
 full=(o/'baseline'/file).read_text();rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',full);blob=bytes.fromhex(''.join(w for _,_,w in rows));entry=int(rows[0][1],16);offset=int(rows[0][0],16);old=(o/'baseline/conker/build/conker.us.elf').read_bytes();assert blob==rom()[offset:offset+len(blob)]==old[elf_slot_offset(old,entry,len(blob)):elf_slot_offset(old,entry,len(blob))+len(blob)];return entry,[int(w,16)for _,_,w in rows]
def fixture(c,kind,selector,phase,speed,flags,lifetime):
 m=g.fixture(c);m.update({TABLE+i:v for i,v in enumerate(rom()[0x231488:0x2314e0])});g.put(m,TEXTURES,TEXTURE);m.update({TEXTURE+i:0 for i in range(16)});m[TEXTURE+4]=4
 if kind=='large':
  g.put(m,c.object+0x98,phase&65535,2);g.put(m,c.object+0x9a,speed&65535,2);g.put(m,c.object+0xa8,flags,2);m[c.object+0xb0]=0;m[c.object+0xb2]=selector&255
 else:
  for offset in range(0x1c,0x33):m[c.object+offset]=0
  g.put(m,c.object+0x38,lifetime&65535,2);m[c.object+0x3a]=0;m[c.object+0x2f]=selector&255;m[c.object+0x48]=255;g.put(m,c.object+0x44,0,2)
 return m
def large_phase(phase,speed,flags,delta):
 p=g.s16(phase)
 if not g.s16(speed):return p
 p=g.s16(p+g.s32(speed*delta));limit=1023
 if p>limit:
  if flags&64:p=limit-p%limit
  elif flags&4:p=-1
  else:
   while p>limit:p=g.s16(p-limit)
 elif p<0:
  if flags&64:p=(-p)%limit
  elif flags&4:p=-1
  else:
   while p<0:p=g.s16(p+limit)
 return p
class ReturnCode(dict):
 def __getitem__(self,pc):
  if self.owner.pending is not None and pc==self.owner.child_return_pc:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,kind,selector,phase,speed,flags,lifetime,poison=None,force_phase=None,invert=False):
  memory=fixture(c,kind,selector,phase,speed,flags,lifetime);entry=0x15168870 if kind=='large'else 0x15167e0c;code=dict(zip(range(g.ENTRY,g.ENTRY+424,4),leaf));super().__init__(parent,c,memory=memory,entry=entry,arguments=(c.object,),connected=code);self.outer=c;self.kind=kind;self.selector=selector;self.pending=None;self.child_checks=0;self.post_calls=[];self.post_observations=[];self.poison=poison;self.force_phase=force_phase;self.child_return_pc=0x15168a00 if kind=='large'else 0x15167eb0;self.parent_frame=24 if kind=='large'else 32;self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x15168a0c]=0x53010004
  self.expected_children=int(selector==15)
  if kind=='large':self.expected_free=large_phase(phase,speed,flags,c.delta)==-1
  else:self.expected_free=lifetime!=32767 and g.s16(lifetime-c.delta)<=0
 def record_call(self,t):
  if t==g.ENTRY:
   assert tuple(self.arguments(1))==(self.outer.object,);self.c=replace(self.outer,phase=self.outer.phase-self.parent_frame);self.pending=(g.reference(self.memory,self.c,self.r[16],self.r[31],initial_fcsr=self.fcsr),len(self.calls),len(self.observations),len(self.fp_operations));return
  if t==FREE:self.post_calls.append((t,tuple(self.arguments(1))));self.post_observations.append((dict(self.memory),self.fcsr));return
  super().record_call(t)
 def child_return(self):
  expected,calls,obs,ops=self.pending;actual=(self.memory,self.calls[calls:],self.observations[obs:],self.fp_operations[ops:],self.fcsr);assert actual==expected,dict(reason='connected seed reference',components=[a==b for a,b in zip(actual,expected)],case=str(self.c));self.pending=None;self.child_checks+=1;self.c=self.outer
  if self.kind=='large':self.expected_free=g.s16(g.read(self.memory,self.outer.object+0x98,2))==-1
  if self.poison is not None:self.r[2]=self.poison
  if self.force_phase is not None:g.put(self.memory,self.outer.object+0x98,self.force_phase&65535,2)
 def hook(self,t):
  if t!=FREE:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xb6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa6000000+i
  self.f[:20]=[0xa6000000+i for i in range(20)];self.hi,self.lo=0xa6000010,0xa6000011
 def verify(self):
  assert self.pending is None and self.child_checks==self.expected_children
  assert self.post_calls==([(FREE,(self.outer.object,))]if self.expected_free else[]),(self.kind,self.outer,self.expected_free,self.post_calls)
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
class Provider(g.Machine):
 def __init__(self,leaf,provider,c,colours):
  m=g.fixture(c);m.update({COLOURS+15+i:v for i,v in enumerate(colours)});connected=dict(zip(range(g.HELPER,g.HELPER+452,4),provider));super().__init__(leaf,c,memory=m,connected=connected);self.factory_calls=[];self.colours=colours
 def record_call(self,t):
  if t!=FACTORY:return super().record_call(t)
  args=tuple(self.arguments(14));desc=args[0];assert args[1:4]==(0,0,0)and args[4:7]==(g.bits(float(self.c.x)),g.bits(float(self.c.floor)),g.bits(float(self.c.z)))and args[7:12]==(g.bits(30.),g.bits(30.),0,0,0)and args[12:]==(self.c.channel,self.c.context),args
  assert g.read(self.memory,desc)==0x67b02 and g.read(self.memory,desc+4,2)==300 and self.memory[desc+6]==0x38 and self.memory[desc+0x10]==255 and g.read(self.memory,desc+0x18)==0x440001 and g.read(self.memory,desc+0x22,2)==1
  assert bytes(self.memory[desc+0x12+i]for i in range(3))==self.colours
  self.factory_calls.append((args,bytes(self.memory[desc+i]for i in range(38))))
 def hook(self,t):
  assert t==FACTORY
  for i in range(4):self.put(self.r[29]+4*i,0xb8000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa8000000+i
  self.f[:20]=[0xa8000000+i for i in range(20)];self.hi,self.lo=0xa8000010,0xa8000011
def main():
 parents={kind:original(fn,file)[1]for kind,fn,file in [('large','func_15168870','conker/asm/nonmatchings/game_1944C0/func_15168870.s'),('compact','func_15167E0C','conker/asm/nonmatchings/game_1944C0/func_15167E0C.s')]};assert len(parents['large'])==111 and len(parents['compact'])==195
 leaves=[g.bound_blob(*g.payload(o/f,'func_151934B4'),g.symbols(g.Case()))for f in('original-target.o','selected-owner.o')];counts={};children={}
 for kind in parents:
  count=child=0
  for selector,phase,speed,flags,lifetime,delta,variant,rm in itertools.product((15,-1,3),(-1,0,1023,32767),(-1,0,1),(0,4,64),(0,32767),(-1,1),(0,1),range(4)):
   c=g.Case(y=-1,delta=delta,variant=variant,mode=1,rm=rm,phase=8*(rm&1));models=[Connected(parents[kind],leaf,c,kind,selector,phase,speed,flags,lifetime).run().verify()for leaf in leaves];a,b=models;assert g.state(a)==g.state(b)and a.post_calls==b.post_calls and a.post_observations==b.post_observations;count+=1;child+=a.child_checks
  counts[kind]=count;children[kind]=child
 controls=[]
 for poison in(0,1,0xffffffff):
  m=Connected(parents['large'],leaves[0],g.Case(y=-1),'large',15,0,0,0,0,poison=poison).run().verify();assert m.post_calls==[(FREE,(g.OBJECT,))];controls.append(dict(name='ignored-void-return-'+hex(poison),complete_parent_execution=True,expiration_unchanged=True))
 for name,kw in [('force-phase-zero',dict(force_phase=0)),('invert-phase-consumer',dict(invert=True))]:
  m=Connected(parents['large'],leaves[0],g.Case(y=-1),'large',15,0,0,0,0,**kw).run();assert m.pending is None and m.child_checks==1 and not m.post_calls;controls.append(dict(name=name,complete_parent_execution=True,wrong_expiration_rejected=True))
 entry,provider=original('func_151DBCBC','conker/asm/nonmatchings/game_2062D0/func_151DBCBC.s');assert entry==g.HELPER and len(provider)==113;old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,COLOURS+15,3);colours=old[at:at+3];assert colours==rom()[0x24fee3:0x24fee6];connections=0
 for x,z,channel,context,rm in itertools.product((-32768,32767),(-17,32767),(0,255),(0,255),range(4)):
  c=g.Case(y=-1,x=x,z=z,channel=channel,context=context,rm=rm);models=[Provider(leaf,provider,c,colours).run()for leaf in leaves];a,b=models;assert g.state(a)==g.state(b)and a.factory_calls==b.factory_calls and len(a.factory_calls)==1;assert g.s16(g.read(a.memory,c.object+0x98,2))==-1;connections+=1
 q=dict(parent_words_pinned={'large':111,'compact':195},parent_frames={'large':24,'compact':32},parents_linked_byte_exact=True,cases_per_parent_per_stream=counts,connected_children_per_parent_per_stream=children,streams=2,complete_original_parents_on_qualified_paths=True,void_return_register_ignored_and_phase_expiration_qualified=True,child_full_memory_frame72_FP_HILO_and_saved_ABI_reference_equal=True,actual113word_zero_random_provider_connections_per_stream=connections,actual14argument_factory_packet_positions_metadata_and_original_colour_row=True,random_provider_arm_and_other_table_entries_not_qualified=True,opaque_factory_and_expiration_helpers=True,no_new_parent_or_provider_matching_credit=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
