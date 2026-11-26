"""Camera truncation, signed/unsigned draws, partial packet and fresh slot stores."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_pointer_quad_vertices_150db714_guest import trunc
from tools.tests.game_random_targets_1518f1a0_guest import fp
from tools.tests import game_selected_vertex_sprite_oracle as sprite
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_display_sprite_slot_15179600_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x15179600;CAMERA_PTR=0x800DBFF0;COUNT=0x800DD436;TABLE_PTR=0x800DD440;CAMERA=0x300000;FOLLOW=0x301000;TABLE=0x320000;TABLE_ALT=0x321000;OUTPUT=0x250000;HEADER=0x270000;MARK=0x290000;TEXTURES=0x8008CA4C;RNG=0x150ADA20;COLOR=0x1516865C;CREATE=0x15168800;ALLOCATE=0x15167A68;COPY=0x10023A10;u32=lambda x:x&0xFFFFFFFF;signed=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000;half=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 randomize:int=1
 value:int=0x89ABCDEF
 camera:tuple=(fp.bits(123.75),fp.bits(-456.5),fp.bits(32767.75))
 integers:tuple=(0xFFFFFFFF,0x80000000,499,0xFFFFFFFF)
 slot:int=0
 after:int=7
 outcome:int=1
 mutation:int=0
 connected:int=0
 width:int=47
 tall:int=31
 rm:int=0
 flags:int=4
 provider_flags:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(D_800DBFF0=CAMERA_PTR,D_800DD436=COUNT,D_800DD440=TABLE_PTR,func_150ADA20=RNG,func_1516865C=COLOR,func_15168800=CREATE)
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((OUTPUT-16,2048),(HEADER,16),(MARK,16),(CAMERA,1024),(FOLLOW,1024),(COUNT-8,32),(CAMERA_PTR-8,24)):
  assert not STACK+c.phase-2048<=base<STACK+c.phase+1024;m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for table in(TABLE,TABLE_ALT):
  for index in set(range(-4,312))|{-32768,32767,c.slot,c.after}:
   for j in range(-4,8):m[u32(table+4*index+j)]=(j*7+index+c.seed)&255
 for i in range(256):put(m,TEXTURES+4*i,HEADER)
 put(m,HEADER+6,c.width,2);put(m,HEADER+8,c.tall,2);put(m,CAMERA_PTR,CAMERA);put(m,COUNT,c.slot,2);put(m,TABLE_PTR,TABLE)
 for p in(CAMERA,FOLLOW):
  for off,value in zip((0x2F8,0x2FC,0x300),c.camera):put(m,p+off,value)
 return m
def effect(m,c,stage,n,p=None):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:
  if stage==COLOR:put(m,CAMERA_PTR,FOLLOW)
  if stage==RNG:
   put(m,CAMERA_PTR,CAMERA)
   for off,v in zip((0x2F8,0x2FC,0x300),(999.5+n,-33.25-n,777.75+n)):put(m,CAMERA+off,fp.bits(v))
  put(m,COUNT,c.after if stage==CREATE else 1+n,2)
  if stage==CREATE:put(m,TABLE_PTR,TABLE_ALT)
 if c.mutation&2 and stage==COLOR:put(m,p+0xA4,0xABCDEF01);m[p+0xA2]=0x80
 if c.mutation&4 and stage in(COLOR,RNG):
  home=STACK+c.phase;put(m,home,0 if n&1 else 1);put(m,home+4,0x13570000+n)
def remainder(v):v=signed(v);return v-(abs(v)//500)*(-500 if v<0 else 500)
def initialize(m,p):sprite.initialize(m,p,(255,255,255,80),dict(D_8008CA4C=TEXTURES))
def reference(initial,c,initial_csr=None):
 m=dict(initial);home=STACK+c.phase;p=home-248+40;put(m,home,c.randomize);put(m,home+4,c.value);calls=[];packets=[];ops=[];csr=c.rm|c.flags if initial_csr is None else initial_csr;counts={RNG:0,COLOR:0,CREATE:0}
 def call(t,args):
  nonlocal csr
  calls.append((t,tuple(map(u32,args))));counts[t]+=1;n=counts[t]
  if t==COLOR:initialize(m,p)
  if t==CREATE:
   packets.append(sprite.data(m,p,168))
   if c.connected&2:calls.append((ALLOCATE,(14,0,184,1,255,1)))
  if not(t==COLOR and c.connected&1):effect(m,c,t,n,p);csr=(csr&~0x3F000)|c.provider_flags
  if t==CREATE and c.outcome:
   if c.connected&2:calls.append((COPY,(p,OUTPUT+16,168)))
   for i,v in enumerate(packets[-1]):m[OUTPUT+16+i]=v
  return c.integers[(n-1)%len(c.integers)]if t==RNG else OUTPUT if t==CREATE and c.outcome else 0
 for off,v,n in((0xA0,17,1),(0x8A,51,2),(0xA2,1,1),(0x98,0,2)):put(m,p+off,v,n)
 call(COLOR,(p,255,255,255,80));viewer=read(m,CAMERA_PTR);origin=[]
 for off in(0x2F8,0x2FC,0x300):
  value=read(m,viewer+off);ops.append((13,value,0,csr));v,flags=trunc(value);csr=(csr&~0x3F000)|flags;origin.append(signed(v))
 x=u32(remainder(call(RNG,()))+origin[0]);z=u32(remainder(call(RNG,()))+origin[2]);y=u32(origin[1]+500)if read(m,home)==0 else u32(remainder(call(RNG,()))+origin[1]);variation=u32(call(RNG,()))%10
 for off,v,n in((0x9C,0,2),(0x9E,0,2),(0x92,4,2),(0x94,variation+35,2),(0x98,0x8C00,2),(0xA1,variation+10,1),(0x8E,y,2),(0x8C,x,2),(0x90,z,2),(0x80,read(m,home+4),4),(0x84,read(m,COUNT,2),2)):put(m,p+off,v,n)
 object=call(CREATE,(p,255,0))
 if object:put(m,u32(read(m,TABLE_PTR)+4*half(read(m,COUNT,2))),object);put(m,COUNT,half(read(m,COUNT,2))+1,2)
 return m,calls,packets,ops,csr
@lru_cache(None)
def helper_words():
 rom=(r/'conker/conker.us.bin').read_bytes();old=(o/'baseline/conker/build/conker.us.elf').read_bytes();result={}
 for entry,offset,n in((COLOR,0x195B0C,105),(CREATE,0x195CB0,28)):
  blob=rom[offset:offset+4*n];at=elf_slot_offset(old,entry,len(blob));assert old[at:at+len(blob)]==blob;result[entry]=list(struct.unpack('>'+str(n)+'I',blob))
 return result
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.packets=[];self.fp_operations=[];code={}if connected is None else dict(connected)
  for flag,target in((1,COLOR),(2,CREATE)):
   if c.connected&flag:code.update(zip(range(target,target+4*len(helper_words()[target]),4),helper_words()[target]))
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(u32(c.randomize),u32(c.value))if arguments is None else arguments,s=symbols(),connected=code);self.counts={RNG:0,COLOR:0,CREATE:0};self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   fs,fd=w>>11&31,w>>6&31;a=self.f[fs];self.fp_operations.append((13,a,0,self.fcsr));v,flags=trunc(a);self.f[fd]=v;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  n={RNG:0,COLOR:5,CREATE:3,ALLOCATE:6,COPY:3};assert t in n,hex(t);a=tuple(map(u32,self.arguments(n[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in self.counts:self.counts[t]+=1
  if t==CREATE:self.packets.append(sprite.data(self.memory,a[0],168))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];n=self.counts.get(t,0);value=0xDEADBEEF
  if t==RNG:value=c.integers[(n-1)%len(c.integers)];effect(self.memory,c,t,n)
  elif t==COLOR:initialize(self.memory,a[0]);effect(self.memory,c,t,n,a[0])
  elif t in(CREATE,ALLOCATE):
   effect(self.memory,c,CREATE,self.counts[CREATE]);value=OUTPUT if c.outcome else 0
   if t==CREATE and value:
    for i,v in enumerate(self.packets[-1]):self.memory[value+16+i]=v
  elif t==COPY:
   assert a[2]==168
   for i,v in enumerate(sprite.data(self.memory,a[0],168)):self.memory[a[1]+i]=v
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value);self.fcsr=(self.fcsr&~0x3F000)|c.provider_flags
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.packets,m.fp_operations,m.current_pc,m.delay_of,m.condition,m.trace)
def check(words,c):
 m=Machine(words,c).run();memory,calls,packets,ops,csr=reference(m.initial,c);got=(public(m.memory,c),m.calls,m.packets,m.fp_operations,m.fcsr);want=(public(memory,c),calls,packets,ops,csr);assert got==want,dict(case=str(c),parts=[a==b for a,b in zip(got,want)],calls=m.calls,wanted=calls,FP=m.fp_operations,wantedFP=ops);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(randomize=mode,value=value,slot=slot,outcome=outcome,mutation=mutation,rm=rm,phase=8*(rm&1))for mode,value,slot,outcome,mutation,rm in itertools.product((0,1,0x80000000),(0,0x89ABCDEF),(-32768,0,299,32767),(0,1),(0,1,2,3),range(4))]
 rows +=[Case(camera=tuple(map(fp.bits,xyz)),integers=draws,rm=rm,mutation=4,phase=8*(rm&1))for xyz,draws,rm in itertools.product(((-32768.75,32767.75,-0.),(2147483648.,-2147483648.,16777216.)),((0,499,500,0xFFFFFFFF),(0x80000000,0x7FFFFFFF,999,0xFFFFFC19)),range(4))]
 rows +=[Case(connected=connected,width=w,tall=h,outcome=outcome,rm=rm)for connected,(w,h),outcome,rm in itertools.product((1,2,3),((0,0),(47,31),(65535,65535)),(0,1),range(4))]
 return[replace(c,seed=i)for i,c in enumerate(rows)]
def raw_fault_relation(original,raw):
 assert original.memory==raw.memory and original.f==raw.f and original.trace==raw.trace and original.calls==raw.calls and original.fp_operations==raw.fp_operations and(original.fcsr,original.hi,original.lo,original.current_pc,original.delay_of,original.condition)==(raw.fcsr,raw.hi,raw.lo,raw.current_pc,raw.delay_of,raw.condition)
 mapping={10:15,15:25,25:10,11:24,24:9,9:11};pc=original.current_pc-ENTRY
 if 0x114<=pc<=0x16C:
  assert all(original.r[i]==raw.r[i]for i in range(32)if i not in mapping)
  for off,reg in((0x114,10),(0x118,11),(0x124,15),(0x128,24),(0x12C,25),(0x130,9)):
   if off<pc:assert raw.r[reg]==original.r[mapping[reg]],(hex(pc),reg)
 else:assert original.r==raw.r,(hex(pc),[(i,original.r[i],raw.r[i])for i in range(32)if original.r[i]!=raw.r[i]])
def main():
 files=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o');streams=[bound_blob(*payload(o/f,'func_15179600'),symbols())for f in files];literal=[streams[i]for i in(0,2,3,4)];assert all(w==literal[0]for w in literal);rows=cases();seen=set()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+432)
 cuts=0
 for c in(Case(),Case(randomize=0,outcome=0),Case(mutation=7,phase=8)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for i,m in enumerate(models)if i!=1);raw_fault_relation(models[0],models[1]);cuts+=1
 assert len(seen)==108,len(seen)
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,preserved_words=108,executed_words=len(seen),normalized_fault_prefix_quadruples=cuts,raw_fault_prefix_role_relations=cuts,normalized_full_private_states_and_faults_equal=True,raw_completion_private_states_equal_under_qualified_providers=True,raw_fault_memory_order_FP_and_explicit_live_GPR_relation_equal=True,raw_full_private_fault_GPR_identity_not_claimed=True,independent_reference_public_memory_calls_all168_packet_bytes_and_FP_equal=True,captured_camera_and_signed_modulo500_unsigned_modulo10=True,fresh_post_factory_index_table_and_increment_reload=True,guest_only_incoming_home_mutations=True,finite_truncation_and_bounded_invalid_software_model_not_hardware=True,connected_original_palette105_and_factory28_with_opaque_allocator_copy=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
