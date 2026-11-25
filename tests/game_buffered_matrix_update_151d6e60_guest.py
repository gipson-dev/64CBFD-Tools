"""Direct literal execution and independent ordered matrix reference."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_buffered_matrix_update_151d6e60_match as target_packet
o=target_packet.OUT;ENTRY=0x151d6e60;ANGLE=0x15144aa8;ROTATE=0x150a8050;OBJECT=0x30000;POSITION=0x60000;OTHER=0x64000;PAGE=0x800be9c0;SCALE=0x800ab278;bits,floating=fp.bits,fp.floating
@dataclass(frozen=True)
class Case:
 page:int=0
 mode:int=0
 alias:int=0
 pattern:int=0
 rm:int=0
 phase:int=0
 angle:int=bits(.125)
 scale:int=0x3f0d0e56
 position_alias:int=0
 object:int=OBJECT
def symbols(c):return dict(func_15144AA8=ANGLE,func_150A8050=ROTATE,D_800BE9C0=c.object+0xac if c.alias&1 else PAGE,D_800AB278=c.object+0xac if c.alias&2 else SCALE)
def position(c):return(POSITION,c.object+0x7c-0x14,c.object+0xbc-0x14)[c.position_alias]
def matrix(c):return tuple(bits(((i*3+c.pattern*5)%19-9)*.125)if i!=15 else bits(1.)for i in range(16))
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-256,256)}
 for base,n in((c.object-16,0x90),(POSITION-16,64),(OTHER-16,64)):m.update({base+i:(i*29+0x5a)&255 for i in range(n)})
 for page in(range(256)if c.alias else{c.page,c.page^1}):
  for i,w in enumerate(matrix(c)):put(m,c.object+0x7c+page*64+4*i,w)
 for p in(POSITION,OTHER):
  for i,v in enumerate((1.5,-2.75,3.125)):put(m,p+0x14+4*i,bits(v+c.pattern))
 put(m,c.object+0x4c,position(c));s=symbols(c);put(m,s['D_800AB278'],c.scale);m[s['D_800BE9C0']]=c.page;return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-256<=a<STACK+c.phase+256}
def effect(m,c,t,args):
 s=symbols(c)
 if t==ROTATE:
  for i,w in enumerate(matrix(c)):put(m,args[0]+4*i,w)
 if c.mode&1:m[s['D_800BE9C0']]^=1
 if c.mode&2:
  for p in(POSITION,OTHER):
   for i,v in enumerate((-4.25,5.5,-6.75)):put(m,p+0x14+4*i,bits(v+(1 if t==ROTATE else 2)))
 if c.mode&4:put(m,c.object+0x4c,OTHER)
 if c.mode&8:put(m,s['D_800AB278'],bits(-.75 if t==ANGLE else 1.25))
def provider_fcsr(c,t):return c.rm|(0x10 if t==ANGLE else 0x20)
def reference(initial,c,s0,ra,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase;put(m,home-8,s0);put(m,home-4,ra);calls=[];obs=[];operations=[];fcsr=c.rm if initial_fcsr is None else initial_fcsr;s=symbols(c)
 def calc(a,b,fn):
  nonlocal fcsr
  operations.append((fn,a,b,fcsr));v,flags=arithmetic(a,b,fn,c.rm);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,args):
  nonlocal fcsr
  calls.append((t,args));obs.append((public(m,c),fcsr));effect(m,c,t,args)
  for i in range(4):put(m,home-32+4*i,0xb5000000+i)
  fcsr=provider_fcsr(c,t)
 call(ANGLE,(0,));angle=calc(c.angle,bits(25.),0);call(ROTATE,(c.object+0x7c+64*m[s['D_800BE9C0']],0,angle,0));scale=read(m,s['D_800AB278'])
 for off,src in((0xac,0x14),(0xb0,0x18),(0xb4,0x1c)):
  value=read(m,read(m,c.object+0x4c)+src)
  if src==0x18:value=calc(value,bits(120.),0)
  put(m,c.object+64*m[s['D_800BE9C0']]+off,value)
 for off in(0x7c,0x80,0x84,0x8c,0x90,0x94,0x9c,0xa0,0xa4):
  dest=c.object+64*m[s['D_800BE9C0']]+off;put(m,dest,calc(read(m,dest),scale,2))
 return m,calls,obs,operations,fcsr,1
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=ENTRY,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.observations=[];self.frames=[];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,2):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;self.fp_operations.append((fn,self.f[fs],self.f[rt],self.fcsr));value,flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t in(ANGLE,ROTATE),hex(t);args=tuple(self.arguments(1 if t==ANGLE else 4));self.calls.append((t,args));self.observations.append((public(self.memory,self.c),self.fcsr));self.frames.append(bytes(self.memory[STACK+self.c.phase-32+i]for i in range(32)))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=self.c.angle if t==ANGLE else 0xa5000002;self.hi,self.lo=0xa5000010,0xa5000011;self.fcsr=provider_fcsr(self.c,t)
def check(words,c):
 m=Machine(words,c).run();expected=reference(m.initial,c,m.before[16],m.before[31]);actual=(m.memory,m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]);assert actual==expected,(c,'complete memory/ordered FP/provider/return comparison');assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(page=page,pattern=page%3,rm=rm,phase=8*(rm&1))for page,rm in itertools.product(range(256),range(4))]
 rows +=[Case(page=page,mode=mode,position_alias=alias,rm=rm,pattern=(mode+alias)%3)for page,mode,alias,rm in itertools.product((0,1),range(16),range(3),range(4))]
 rows +=[Case(alias=alias,page=page,mode=mode,rm=rm)for alias,page,mode,rm in itertools.product((1,2,3),(0,1),(0,3,8,15),range(4))]
 rows +=[Case(angle=bits(a),scale=bits(s),rm=rm,object=STACK+32 if mode else OBJECT)for a,s,rm,mode in itertools.product((0.,-0.,-.125,100.25),(.125,-.5,1.25),range(4),(0,1))]
 return rows
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.frames,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];rows=cases();seen=set();cache={};streams=None
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_151D6E60'),symbols(c))for f in files]
  streams=cache[key];assert all(ws==streams[0]for ws in streams);models=[check(ws,c)for ws in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in(Case(),Case(alias=1,mode=15),Case(alias=2,mode=3),Case(object=STACK+32,mode=15)):
  streams=[bound_blob(*payload(o/f,'func_151D6E60'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert seen==set(range(ENTRY,ENTRY+416,4));controls=[];c=Case(mode=15);words=bound_blob(*payload(o/'original-target.o','func_151D6E60'),symbols(c))
 for name,old,new in [('angle-offset',0x3c0141c8,0x3c0141c0),('position-offset',0x3c0142f0,0x3c0142ee),('return',0x24020001,0x24020000),('basis-store',0xe468007c,0xe4680088)]:
  wrong=list(words);assert wrong.count(old)==1,name;wrong[wrong.index(old)]=new;m=Machine(wrong,c).run();wanted=reference(m.initial,c,m.before[16],m.before[31]);assert(m.memory,m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2])!=wanted;controls.append(dict(name=name,supported_complete_execution=True,rejected=True))
 q=dict(cases_per_stream=len(rows),streams=5,all_streams_direct_retail_identical=True,executed_words=len(seen),fault_prefix_quintuples=prefixes,complete_memory_frame32_ABI_return_provider_and_FP_order_equal=True,all_unsigned_page_bytes_guest=True,source_matrix_coefficient_and_page_aliases=True,provider_mutations=True,all_four_rounding_modes_and_provider_sticky_FCSR=True,finite_arithmetic_model_only=True,not_hardware_or_full_provider_implementation_qualification=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
