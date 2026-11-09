"""Ordered secondary camera reference and bounded literal MIPS checks."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments import game_secondary_camera_position_1512e4b0_match as match
root=match.ROOT;out=root/match.BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

ENTRY,ACTORS,PI,SIN,COS,CAMERA,ALT=0x1512E4B0,0x800CC2D0,0x800A3730,0x15047D60,0x15047C00,0x30000,0x34000
SYMS=dict(D_800CC2D0=ACTORS,D_800A3730=PI,sinf=SIN,cosf=COS)
u32=lambda v:v&0xFFFFFFFF
half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 view:int=0
 heading:int=0
 speed:int=0
 x:int=0x42C80000
 y:int=0xC1200000
 z:int=0x43480000
 results:tuple=(0x3F000000,0xBF400000)
 mutation:int=0
 phase:int=0
 camera:int=CAMERA
 pi:int=0x40490FDB

def record(c,s=SYMS):return u32(s['D_800CC2D0']+(1 if c.view==3 else 0)*812)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,4096)}
 for base,size in((c.camera,0x9A0),(ALT,0x9A0),(s['D_800CC2D0'],26*812)):
  m.update({u32(base+i):(i*29+0x5A)&255 for i in range(size)})
 for j in range(26):
  a=u32(s['D_800CC2D0']+j*812)
  for offset,w in((20,bits(j+1.)),(24,bits(j-3.)),(28,bits(-j-5.)),(64,bits(j/4.))):put(m,u32(a+offset),w)
  put(m,u32(a+0x2E4),j*13,2)
 a=record(c,s)
 for off,w in((20,c.x),(24,c.y),(28,c.z),(64,c.speed)):put(m,u32(a+off),w)
 put(m,u32(a+0x2E4),c.heading&65535,2);put(m,u32(a+0x2E6),0x7ABC,2)
 m[u32(c.camera+0x23D)]=c.view;put(m,s['D_800A3730'],c.pi)
 for p,w in {**trig.GLOBALS,**trig.COS_GLOBALS}.items():put(m,p,w)
 return m

def effect(m,c,stage,home,s=SYMS):
 if stage==0:
  if c.mutation&1:
   for off,w in((0x2BC,0xC2FA0000),(0x2C0,0x41D00000),(0x2C4,0x43430000)):put(m,u32(c.camera+off),w)
  if c.mutation&2:
   a=record(c,s);put(m,u32(a+20),0x3F800000);put(m,u32(a+64),0x7F800000);put(m,u32(a+0x2E4),0x8000,2)
  if c.mutation&4:put(m,s['D_800A3730'],0x3F000000)
  if c.mutation&8:m[u32(c.camera+0x23D)]=3 if c.view!=3 else 0
  if c.mutation&16:
   for off,w in((0x2BC,0x41A80000),(0x2C0,0xC2100000),(0x2C4,0x42E00000)):put(m,ALT+off,w)
  if c.mutation&64:put(m,home,ALT)
 else:
  if c.mutation&32:
   for base in(c.camera,ALT):put(m,u32(base+0x2C4),0xC2C00000)
  if c.mutation&64:put(m,home,c.camera)

def snapshot(m,c,stage,args,home,s=SYMS):
 offsets=(0x2BC,0x2C0,0x2C4,0x2F8,0x2FC,0x300)
 return(stage,args,read(m,home),tuple(read(m,u32(c.camera+j))for j in offsets),tuple(read(m,ALT+j)for j in offsets),read(m,s['D_800A3730']),m[u32(c.camera+0x23D)])

def heading_angle(m,c,s=SYMS):
 a=record(c,s);heading=half(-half(read(m,u32(a+0x2E4),2)))
 adjusted=fp(bits(float(heading)),fp(read(m,u32(a+64)),bits(10.),'mul'),'add')
 narrow=half(trunc(adjusted))
 return fp(fp(bits(float(narrow)),read(m,s['D_800A3730']),'mul'),bits(1800.),'div'),adjusted

def reference(initial,c,home=None,s=SYMS,connected=False):
 m=dict(initial);home=STACK+c.phase if home is None else home;a=record(c,s);cam=c.camera
 put(m,u32(cam+0x2BC),read(m,u32(a+20)))
 put(m,u32(cam+0x2C0),fp(read(m,u32(a+24)),bits(150.),'add'))
 put(m,u32(cam+0x2C4),read(m,u32(a+28)))
 angle,adjusted=heading_angle(m,c,s);put(m,home,cam);calls=[];snapshots=[]
 for stage,name in enumerate(('sinf','cosf')):
  args=(angle,);calls.append((s[name],args));snapshots.append(snapshot(m,c,stage,args,home,s))
  value=trig.reference(angle,cosine=bool(stage))if connected else c.results[stage]
  if not connected:effect(m,c,stage,home,s)
  cam=read(m,home)
  offset=fp(value,bits(60.),'mul')
  if stage==0:
   x=read(m,u32(cam+0x2BC));y=read(m,u32(cam+0x2C0));put(m,u32(cam+0x2FC),y)
   put(m,u32(cam+0x2F8),fp(x,offset,'sub'))
  else:put(m,u32(cam+0x300),fp(read(m,u32(cam+0x2C4)),offset,'sub'))
 return m,calls,snapshots,angle,adjusted

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,arguments=None,real=False):
  self.snapshots=[];self.draw=0;self.semantic_home=STACK+c.phase;self.real=real
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(u32(c.camera),)if arguments is None else arguments)
  self.saved_f=self.f[20:].copy()
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(7,13):
   prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
   try:self.f[w>>6&31]=(self.f[w>>11&31]^0x80000000)if w&63==7 else trunc(self.f[w>>11&31])
   finally:self.own_instruction=prior
  else:super().execute(w)
 def record_call(self,t):
  stage=0 if t==self.syms['sinf']else 1;assert t in(self.syms['sinf'],self.syms['cosf'])
  args=(self.f[12],);self.calls.append((t,args));self.snapshots.append(snapshot(self.memory,self.case,stage,args,self.semantic_home,self.syms));self.events.append(('CALL',t,args))
 def hook(self,t):
  stage=0 if t==self.syms['sinf']else 1;effect(self.memory,self.case,stage,self.semantic_home,self.syms)
  for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.results[stage];self.hi,self.lo=0xA5000010,0xA5000011

def cases():
 headings=(0,1,0x7FFF,0x8000,0xFFFF,0x7FFE,0x8001)
 speeds=(bits(0.),bits(.125),bits(-.125),bits(3276.8),bits(-3276.8),bits(1e8),bits(-1e8),bits(214748352.),bits(214748368.),bits(-214748364.8),0x4DCCCCCD,0xCDCCCCCD,0x7F800000,0x7FC01234,0x80000000)
 for view in range(256):yield Case(view=view,heading=headings[view%len(headings)],speed=speeds[view%len(speeds)],phase=(view&1)*8)
 for h,v,view,phase in itertools.product(headings,speeds,(0,3),(0,8)):yield Case(view=view,heading=h,speed=v,phase=phase)
 for mutation,view,phase in itertools.product(range(128),(0,3),(0,8)):
  yield Case(view=view,heading=0xFFFF,speed=bits(17.25),mutation=mutation,phase=phase,results=((0x80000000,0x3F000000,0xBF800000,0x40000000)[mutation%4],(0x3F800000,0xBF400000,0,0x80000000)[mutation%4]))
 for camera,view in itertools.product((ACTORS+0x28,0xFFFFFE00),(0,3)):
  yield Case(view=view,camera=camera,heading=0x7FFF,speed=bits(.25),mutation=1)

def native_cases():
 seen=set()
 for c in cases():
  c=replace(c,phase=0)
  if c.camera!=CAMERA or c.mutation&64 or c in seen:continue
  seen.add(c)
  m=fixture(c);_,_,_,_,adjusted=reference(m,c);v=floating(adjusted)
  if math.isfinite(v)and -(2**31)<=v<2**31:yield c

def public(m):return{a:v for a,v in m.items()if not STACK-4096<=a<STACK+4096}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,home=None,s=SYMS,connected=False,semantic=False):
 expected,calls,snaps,_,_=reference(initial,c,home,s,connected)
 observed=m.snapshots
 if semantic:
  # A private input-home store is not a public semantic counterexample.
  observed=[v[:2]+v[3:]for v in observed];snaps=[v[:2]+v[3:]for v in snaps]
 assert(public(m.memory),m.calls,observed)==(public(expected),calls,snaps),c
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[31]==m.before[31]and m.f[20:]==m.saved_f,c

def raw_words():
 text,fs,rs=parse_object(out/'qualified-owner.o');f=fs['func_1512E4B0'];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']}
 return bound_blob(text[f['value']:f['value']+f['size']],refs,SYMS)

def guest_checks():
 rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>77I',rom,0x15B960));raw=raw_words();assert raw==truth
 visits=set();n=accesses=0
 for c in cases():
  initial=fixture(c);pair=[]
  for words in(truth,raw):
   m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m);visits.update(m.visits)
  assert state(pair[0])==state(pair[1]);n+=1;accesses+=pair[0].all_accesses
  if n%256==0:print('guest cases',n,flush=True)
 assert len(visits)==77,len(visits)
 faults=delay=0
 for c in(Case(),Case(view=3,mutation=127),Case(heading=0x8000,speed=bits(-1e8)),Case(camera=ACTORS+0x28),Case(camera=0xFFFFFE00)):
  initial=fixture(c);full=Oracle(truth,initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(truth,raw):
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);faults+=1;delay+=pair[0].delay_of is not None
 report=dict(cases_per_body=n,visited_body_words=77,padding_words=3,accesses_per_body=accesses,fault_prefix_pairs=faults,delay_slot_faults=delay,all_selector_bytes=True,wide_heading_then_halfword_wrap=True,post_trig_camera_reloads=True,guest_only_invalid_conversion_alias_and_home_cases=True,native_cases=len(list(native_cases())),hardware_FCSR_or_payload_claim=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report
