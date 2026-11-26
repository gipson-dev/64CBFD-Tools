"""Signed halfword transitions, frame72, seven arguments and literal fault cuts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_seed_sprite_tick_151934b4_match as target_packet
o=target_packet.OUT;ENTRY=0x151934b4;HELPER=0x151dbcbc;TIMER=0x800be9e4;OBJECT=0x30000;MARK=0x90000
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff;s32=lambda v:((v&0xffffffff)^0x80000000)-0x80000000;s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 extent:int=10
 threshold:int=10
 growth:int=12
 fall:int=0
 y:int=0
 floor:int=0
 x:int=11
 z:int=-17
 variant:int=1
 delta:int=1
 channel:int=0xab
 context:int=0xcd
 mode:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
def symbols(c):return dict(D_800BE9E4=c.object+0xa4 if c.mode&4 else TIMER,func_151DBCBC=HELPER)
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,256)};m.update({c.object-32+i:(i*29+0x5a)&255 for i in range(256)});m.update({MARK+i:0xa5 for i in range(16)})
 for off,v in ((0x94,c.fall),(0x96,c.threshold),(0x98,11),(0x9c,c.x),(0x9e,c.y),(0xa0,c.z),(0xa2,22),(0xa4,c.extent),(0xa6,c.floor),(0xaa,c.growth)):put(m,c.object+off,v&65535,2)
 m[c.object+0xb3]=c.variant&255;m[c.object+0xc]=c.channel;m[c.object+1]=c.context;put(m,symbols(c)['D_800BE9E4'],c.delta&0xffffffff);return m
def effect(m,c,sp,vector):
 put(m,MARK,0x13579bdf)
 if c.mode&1:put(m,vector,bits(99.));put(m,c.object+0x98,1234,2);m[c.object+0xc]^=0x55
 if c.mode&2:put(m,c.object+0xaa,0x7fff,2);put(m,symbols(c)['D_800BE9E4'],0x80000000)
 for i in range(4):put(m,sp+4*i,0xb7000000+i)
def reference(initial,c,saved_s0,ra,initial_fcsr=None):
 m=dict(initial);sp=STACK+c.phase-72;owner=c.object;put(m,sp+0x28,saved_s0);put(m,sp+0x2c,ra);fcsr=c.rm if initial_fcsr is None else initial_fcsr;calls=[];observations=[];ops=[]
 if s16(read(m,owner+0xa4,2))<s16(read(m,owner+0x96,2)):
  growth=s16(read(m,owner+0xaa,2));v=growth>>2;div=lambda n:abs(n)//3*(-1 if n<0 else 1);put(m,owner+0xa4,div(v*24)&65535,2);put(m,owner+0xa2,div(v*6)&65535,2);put(m,owner+0xaa,(growth+read(m,symbols(c)['D_800BE9E4']))&65535,2)
 else:
  fall=s16(read(m,owner+0x94,2)+1);put(m,owner+0x94,fall&65535,2)
  if fall>20:fall=20;put(m,owner+0x94,20,2)
  dy=s32(fall*read(m,symbols(c)['D_800BE9E4']))>>1;put(m,owner+0x9e,(s16(read(m,owner+0x9e,2))-dy)&65535,2)
  if s16(read(m,owner+0x9e,2))<s16(read(m,owner+0xa6,2)):
   if m[owner+0xb3]==1:
    for off,dest in ((0x9c,0x38),(0xa6,0x3c),(0xa0,0x40)):
     v=s16(read(m,owner+off,2));ops.append((32,v&0xffffffff,fcsr));fcsr&=~0x3f000;put(m,sp+dest,bits(float(v)))
    args=(5,bits(30.),255,0,sp+0x38,m[owner+0xc],m[owner+1]);put(m,sp+0x10,args[4]);put(m,sp+0x14,args[5]);put(m,sp+0x18,args[6]);calls.append((HELPER,args));observations.append((tuple(read(m,sp+0x38+4*i)for i in range(3)),fcsr));effect(m,c,sp,sp+0x38);fcsr=(fcsr&3)|0x1004
   put(m,owner+0x98,65535,2)
 return m,calls,observations,ops,fcsr
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.fp_operations=[];self.observations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==20 and w&63==32:
   fs,fd=w>>11&31,w>>6&31;v=self.f[fs];self.fp_operations.append((32,v,self.fcsr));self.f[fd]=bits(float(s32(v)));self.fcsr&=~0x3f000
  else:super().execute(w)
 def record_call(self,t):
  assert t==HELPER,hex(t);args=tuple(self.arguments(7));self.calls.append((t,args));self.observations.append((tuple(read(self.memory,args[4]+4*i)for i in range(3)),self.fcsr))
 def hook(self,t):
  assert t==HELPER;effect(self.memory,self.c,self.r[29],self.calls[-1][1][4])
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa7000000+i
  self.f[:20]=[0xa7000000+i for i in range(20)];self.hi,self.lo=0xa7000010,0xa7000011;self.fcsr=(self.fcsr&3)|0x1004
def observable(m):return m.memory,m.calls,m.observations,m.fp_operations,m.fcsr
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c,m.before[16],m.before[31]);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)],diff=[hex(a)for a in m.memory if m.memory[a]!=want[0].get(a)][:8]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(extent=-1,threshold=1,growth=g,delta=d,rm=rm,phase=8*(rm&1))for g,d,rm in itertools.product((-32768,-32767,-4,-1,0,1,4,32767),(0,1,-1,0x7fffffff,0x80000000,65536),range(4))]
 rows.extend(Case(fall=f,y=y,floor=floor,variant=v,delta=d,rm=rm,phase=8*(rm&1))for f,y,floor,v,d,rm in itertools.product((-32768,-1,0,19,20,32767),(-32768,-1,0,32767),(-32768,0,32767),(0,1,128),(-1,0,1,0x80000000),range(4)))
 rows.extend(Case(mode=mode,rm=rm,phase=phase,object=STACK+32 if stack else OBJECT,x=-32768,z=32767,delta=d)for mode,rm,phase,stack,d in itertools.product(range(8),range(4),(0,8),(0,1),(-1,1)))
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];cache={};seen=set();rows=cases();calls=0
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_151934B4'),symbols(c))for f in files]
  models=[check(w,c)for w in cache[key]];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits);calls+=len(models[0].calls)
 prefixes=0
 for c in (Case(y=-1),Case(extent=-1,threshold=1,growth=-32768),Case(variant=128,y=-1),Case(mode=3,y=-1,object=STACK+32)):
  streams=[bound_blob(*payload(o/f,'func_151934B4'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing fault cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 controls=[];c=Case(y=-1);words=bound_blob(*payload(o/'original-target.o','func_151934B4'),symbols(c))
 for name,old,new in [('phase',0x2409ffff,0x2409fffe),('kind',0x24040005,0x24040004),('size',0x3c0541f0,0x3c0541e0),('coordinate',0x860d009c,0x860d009e),('channel-sign',0x920f000c,0x820f000c)]:
  assert old in words;wrong=[new if w==old else w for w in words];m=Machine(wrong,c).run();assert observable(m)!=reference(m.initial,c,m.before[16],m.before[31]),name;controls.append(dict(name=name,complete_supported_execution=True,rejected=True))
 missing=set(range(ENTRY,ENTRY+424,4))-seen;assert missing=={ENTRY+x for x in(0x64,0x74,0x78,0x7c,0x98,0xa8,0xac,0xb0,0xc0)},[hex(a)for a in sorted(missing)]
 q=dict(cases_per_stream=len(rows),streams=5,opaque_effect_calls_per_stream=calls,executed_words=len(seen),unreachable_retail_traps_and_duplicate_loads=[hex(a)for a in sorted(missing)],fault_prefix_quintuples=prefixes,complete_memory_frame72_borrowed_outgoing_homes_saved_ABI_GPR_FPR_HILO_and_FCSR=True,signed_halfword_wrap_and_unsigned_product_boundaries=True,all_four_rounding_modes=True,seven_argument_types_values_and_position_vector_observed=True,opaque_provider_public_mutations_and_clobbers=True,void_return_register_not_a_semantic_result=True,source_installed=target_packet.installed(),matching_credit=0,effective_controls=controls);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
