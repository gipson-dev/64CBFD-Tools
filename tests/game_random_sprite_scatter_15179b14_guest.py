"""Captured origins/sentinel, signed RNG, partial descriptor and literal faults."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_random_targets_1518f1a0_guest import convert_integer,fp
from tools.tests import game_selected_vertex_sprite_oracle as sprite
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_random_sprite_scatter_15179b14_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x15179B14;ORIGIN=0x800DD438;SENTINEL=0x800A7208;RNG=0x150ADA20;HEIGHT=0x1510F8D8;COLOR=0x1516865C;CREATE=0x15168800;ALLOCATE=0x15167A68;COPY=0x10023A10;TEXTURES=0x8008CA4C;HEADER=0x270000;OUTPUT=0x250000;MARK=0x290000;u32=lambda v:v&0xFFFFFFFF;signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000;half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 count:int=2
 origins:tuple=(-32768,32767)
 sentinel:int=0xC61C4000
 integers:tuple=(0xFFFFFFFF,0x80000000,499,500,0x7FFFFFFF,0)
 heights:tuple=(-10000,10,16777217)
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
def symbols():return dict(D_800DD438=ORIGIN,D_800A7208=SENTINEL,func_150ADA20=RNG,func_1510F8D8=HEIGHT,func_1516865C=COLOR,func_15168800=CREATE)
def public(memory,c):return{a:v for a,v in memory.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((OUTPUT-16,0x1000),(HEADER,16),(MARK,16),(ORIGIN-8,24),(SENTINEL-8,24)):assert not STACK+c.phase-2048<=base<STACK+c.phase+1024;m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i in range(256):put(m,TEXTURES+4*i,HEADER)
 put(m,HEADER+6,c.width,2);put(m,HEADER+8,c.tall,2);put(m,ORIGIN,c.origins[0],2);put(m,ORIGIN+2,1234,2);put(m,ORIGIN+4,c.origins[1],2);put(m,SENTINEL,c.sentinel);return m
def effect(m,c,stage,n,p=None):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:
  put(m,ORIGIN,123+n,2);put(m,ORIGIN+4,-456-n,2);put(m,SENTINEL,fp.bits(37.+n))
 if c.mutation&2 and stage==COLOR:
  put(m,p+0x84,0xABCDEF00+n);m[p+0xA2]=0x80+n
def remainder(a,b):a=signed(a);q=(abs(a)//b)*(-1 if a<0 else 1);return a-q*b
def initialize(m,p):sprite.initialize(m,p,(255,)*4,dict(D_8008CA4C=TEXTURES))
def reference(initial,c,initial_csr=None):
 m=dict(initial);home=STACK+c.phase;p=home-272+72;calls=[];packets=[];operations=[];csr=c.rm|c.flags if initial_csr is None else initial_csr;counts={RNG:0,HEIGHT:0,COLOR:0,CREATE:0};ox=half(read(m,ORIGIN,2));oz=half(read(m,ORIGIN+4,2));limit=signed(c.count)
 if limit<=0:return m,calls,packets,operations,csr
 sentinel=read(m,SENTINEL)
 def call(t,args):
  nonlocal csr
  calls.append((t,tuple(map(u32,args))));counts[t]+=1;n=counts[t]
  if t==COLOR:initialize(m,p)
  if t==CREATE:
   packets.append(sprite.data(m,p,168))
   if c.connected&2:calls.append((ALLOCATE,(14,0,184,1,255,1)))
  if not(t==COLOR and c.connected&1):effect(m,c,t,n,p)
  if t==CREATE and c.outcome:
   out=OUTPUT+192*(n-1)
   if c.connected&2:calls.append((COPY,(p,out+16,168)))
   for i,v in enumerate(packets[-1]):m[out+16+i]=v
  if not(t==COLOR and c.connected&1):csr=(csr&~0x3F000)|c.provider_flags
  return c.integers[(n-1)%len(c.integers)]if t==RNG else c.heights[(n-1)%len(c.heights)]if t==HEIGHT else 0
 for i in range(limit):
  x=remainder(call(RNG,()),500)+ox;z=remainder(call(RNG,()),500)+oz;height=call(HEIGHT,(x,10000,z,0));operations.append((32,u32(height),0,csr));converted,flags=convert_integer(height,csr&3);csr=(csr&~0x3F000)|flags;operations.append((50,sentinel,converted,csr));condition=fp.floating(sentinel)==fp.floating(converted);csr=(csr&~(0x3F000|0x800000))|(0x800000 if condition else 0)
  if not condition:
   for off,v,n in((0x80,0,4),(0x8A,128,2),(0x8C,x,2),(0x8E,height,2),(0x90,z,2),(0x94,25,2),(0x92,25,2),(0x96,0,2),(0xA2,14,1),(0xA0,18,1),(0x98,0x9804,2),(0xA1,0,1)):put(m,p+off,v,n)
   call(COLOR,(p,255,255,255,255));call(CREATE,(p,255,0))
 return m,calls,packets,operations,csr
@lru_cache(None)
def helper_words():
 rom=(r/'conker/conker.us.bin').read_bytes();old=(o/'baseline/conker/build/conker.us.elf').read_bytes();result={}
 for entry,offset,n in((COLOR,0x195B0C,105),(CREATE,0x195CB0,28)):
  blob=rom[offset:offset+4*n];at=elf_slot_offset(old,entry,len(blob));assert old[at:at+len(blob)]==blob;result[entry]=list(struct.unpack('>'+str(n)+'I',blob))
 return result
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.counts={RNG:0,HEIGHT:0,COLOR:0,CREATE:0};self.packets=[];self.fp_operations=[];code={}if connected is None else dict(connected)
  for flag,target in((1,COLOR),(2,CREATE)):
   if c.connected&flag:code.update(zip(range(target,target+4*len(helper_words()[target]),4),helper_words()[target]))
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(u32(c.count),)if arguments is None else arguments,s=symbols(),connected=code);self.counts={RNG:0,HEIGHT:0,COLOR:0,CREATE:0};self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:
   a=self.f[fs];self.fp_operations.append((32,a,0,self.fcsr));v,flags=convert_integer(a,self.fcsr&3);self.f[fd]=v;self.fcsr=(self.fcsr&~0x3F000)|flags
  elif op==17 and fmt==16 and fn==50:
   a,b=self.f[fs],self.f[rt];assert math.isfinite(fp.floating(a))and math.isfinite(fp.floating(b));self.fp_operations.append((50,a,b,self.fcsr));self.condition=fp.floating(a)==fp.floating(b);self.fcsr=(self.fcsr&~(0x3F000|0x800000))|(0x800000 if self.condition else 0)
  else:super().execute(w)
 def record_call(self,t):
  counts={RNG:0,HEIGHT:4,COLOR:5,CREATE:3,ALLOCATE:6,COPY:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in self.counts:self.counts[t]+=1
  if t==CREATE:self.packets.append(sprite.data(self.memory,a[0],168))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];n=self.counts.get(t,0);value=0xDEADBEEF
  if t==RNG:value=c.integers[(n-1)%len(c.integers)];effect(self.memory,c,t,n)
  elif t==HEIGHT:value=c.heights[(n-1)%len(c.heights)];effect(self.memory,c,t,n)
  elif t==COLOR:initialize(self.memory,a[0]);effect(self.memory,c,t,n,a[0])
  elif t in(CREATE,ALLOCATE):
   n=self.counts[CREATE];effect(self.memory,c,CREATE,n);value=OUTPUT+192*(n-1)if c.outcome else 0
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
 m=Machine(words,c).run();memory,calls,packets,ops,csr=reference(m.initial,c);got=(public(m.memory,c),m.calls,m.packets,m.fp_operations,m.fcsr);want=(public(memory,c),calls,packets,ops,csr);assert got==want,dict(case=str(c),parts=[a==b for a,b in zip(got,want)],calls=m.calls,wanted_calls=calls,FP=m.fp_operations,wanted_FP=ops);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(count=count,origins=origins,heights=heights,outcome=outcome,mutation=mutation,rm=rm,phase=8*(rm&1))for count,origins,heights,outcome,mutation,rm in itertools.product((-1,0,1,3),((-32768,32767),(123,-456)),((-10000,10,16777217),(2147483647,-2147483648,-10000)),(0,1),(0,1,2,3),range(4))]
 rows +=[Case(count=2,connected=connected,width=width,tall=tall,outcome=outcome,rm=rm,heights=(17,-10000))for connected,(width,tall),outcome,rm in itertools.product((1,2,3),((0,0),(47,31),(65535,65535)),(0,1),range(4))]
 rows +=[Case(count=3,sentinel=sentinel,heights=heights,rm=rm,provider_flags=0x1004)for sentinel,heights,rm in itertools.product((0x80000000,fp.bits(16777216.),0xC61C4000),((0,-10000,1),(16777217,2147483647,-2147483648)),range(4))]
 return[replace(c,seed=i)for i,c in enumerate(rows)]
def divisor_guard_proof(words):
 assert words[0x54//4]==0x241301F4
 for branch,li,second in((0x6C,0x78,0x7C),(0xA4,0xB0,0xB4)):
  assert words[branch//4]==0x16600002 and words[li//4]==0x2401FFFF and words[second//4]==0x16610004
 for at in range(0x58,0x16C,4):
  w=words[at//4];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op in(8,9,10,11,12,13,14,15,32,33,34,35,36,37,38):assert rt!=19
  if op==0 and fn in(0,2,3,4,6,7,16,18,32,33,34,35,36,37,38,39,42,43):assert rd!=19
  if op==17 and rs==0:assert rt!=19
 return dict(divisor_s3=500,zero_and_minus_one_guards_always_branch=True,no_direct_loop_write_to_s3=True,callee_preserves_s3_required_and_checked=True)
def main():
 files=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o');streams=[bound_blob(*payload(o/f,'func_15179B14'),symbols())for f in files];assert all(w==streams[0]for w in streams);rows=cases();seen=set()
 proof=divisor_guard_proof(streams[0])
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+412)
 cuts=0
 for c in(Case(count=0),Case(count=1,heights=(-10000,)),Case(count=1,heights=(17,),mutation=3,phase=8)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in streams:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);cuts+=1
 dead={ENTRY+at for at in(0x74,0x84,0x88,0x8C,0xAC,0xBC,0xC0,0xC4)};assert seen==set(range(ENTRY,ENTRY+412,4))-dead,(len(seen),[hex(x-ENTRY)for x in sorted(set(range(ENTRY,ENTRY+412,4))-seen)])
 q=dict(cases_per_stream=len(rows),streams=5,preserved_words=103,executed_words=len(seen),fault_prefix_quintuples=cuts,unreached_constant_divisor_break_guard_offsets=[hex(x-ENTRY)for x in sorted(dead)],constant_divisor_guard_proof=proof,independent_public_memory_calls_all168_packet_bytes_ordered_FP_FCSR_equal=True,full_private_states_trace_and_literal_faults_equal=True,signed_RNG_modulo500_captured_short_origins_and_mutable_sentinel=True,all_four_rounding_modes_finite_height_conversion_and_compare=True,connected_original_palette105_and_factory28_with_opaque_allocator_copy=True,other_helpers_and_unmatched_height_backend_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
