"""Private wobble qualification with ordered binary32 equations and rotation calls."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_camera_wobble_151256bc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_trig_match import operation as fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,CAMERA,RANDOM,ROTATE,SIN,COS=0x151256BC,616,0x30000,0x150ADA20,0x1508EF80,0x15047D60,0x15047C00
SYMS={**{'D_800A%04X'%n:0x800A0000+n for n in range(0x3534,0x3550,4)},'D_800BE9A4':0x800BE9A4,
 'func_150ADA20':RANDOM,'func_1508EF80':ROTATE,'sinf':SIN,'cosf':COS,'D_8009DC80':0x8009DC80}
COEFFICIENTS=(0x40C90FDB,0x3C8EFA35,0x3D23D70A,0x3D4CCCCD,0x3DA3D70A,0x3D23D70A,0x3D4CCCCD)
LUT=tuple(map(bits,(0.0,-0.0,0.25,-0.5,0.75,-1.0,1.25,2.0)))
@dataclass(frozen=True)
class Case:
 phase:int=0;flags:int=0x80000;secondary:int=0;angle:int=0;amp:int=0;random:int=1;dt:int=0x3F800000;profile:int=0;mutation:int=0;seed:int=0
def trig(target,arg,c):return LUT[((arg>>20)^(arg>>8)^(3 if target==COS else 0)^c.profile)&7]
def fixture(c):
 m={STACK+i:(i*17+c.seed*7+0xA5)&255 for i in range(-1024,512)}
 m.update({CAMERA+i:(i*29+c.seed*11+0x35)&255 for i in range(0x900)})
 for at,v in((0x2C,c.flags),(0x5F0,c.secondary),(0x29C,c.angle),(0x5EC,c.amp)):put(m,CAMERA+at,v)
 for j,at in enumerate((0x2BC,0x2C0,0x2C4,0x2F8,0x2FC,0x300)):put(m,CAMERA+at,bits((j-2.5)*(c.seed+1)*3.25))
 for j,v in enumerate(COEFFICIENTS):put(m,0x800A3534+4*j,v)
 put(m,SYMS['D_800BE9A4'],c.dt);put(m,SYMS['D_8009DC80'],0x3C8EFA35)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def rng_effect(m,c):
 if c.mutation:
  put(m,CAMERA+0x29C,bits(2.25));put(m,CAMERA+0x5EC,bits(-3.5));put(m,CAMERA+0x2C,0 if c.mutation==1 else 0x80000)
  put(m,SYMS['D_800BE9A4'],bits(0.25))
def rotate(m,p,b,a,q,c,record=lambda t,a:None):
 dx=fp(read(m,p),read(m,b),'sub');radians=fp(a,read(m,SYMS['D_8009DC80']),'mul');dz=fp(read(m,p+8),read(m,b+8),'sub')
 def math(t):record(t,(radians,));return trig(t,radians,c)
 co=math(COS);si=math(SIN);x=fp(fp(fp(si,dz,'mul'),fp(co,dx,'mul'),'add'),read(m,b),'add')
 si=math(SIN);co=math(COS);z=fp(fp(fp(co,dz,'mul'),fp(si^0x80000000,dx,'mul'),'add'),read(m,b+8),'add')
 put(m,q,x);put(m,q+8,z)
def reference(initial,c,connected=False):
 m=dict(initial);calls=[]
 def record(t,a):calls.append((t,a))
 def turn(p,b,a,q):
  record(ROTATE,(p,b,a,q));rotate(m,p,b,a,q,c,record if connected else lambda t,a:None)
 flags=read(m,CAMERA+0x2C)
 if flags&0x80000 or(read(m,CAMERA+0x5F0)&8 and not flags&0x40000):
  record(RANDOM,());rng_effect(m,c);r=bits(float(c.random%3));period=read(m,0x800A3534)
  amount=fp(fp(fp(r,r,'add'),read(m,0x800A3538),'mul'),read(m,SYMS['D_800BE9A4']),'mul')
  a=fp(read(m,CAMERA+0x29C),amount,'add');put(m,CAMERA+0x29C,a);wraps=0
  while floating(a)>floating(period):
   a=fp(a,period,'sub');put(m,CAMERA+0x29C,a);wraps+=1;assert wraps<1024
  record(SIN,(a,));value=trig(SIN,a,c);amp=read(m,CAMERA+0x5EC)
  amp=fp(amp,fp(fp(fp(value,bits(4.),'mul'),amp,'sub'),read(m,0x800A353C),'mul'),'add');put(m,CAMERA+0x5EC,amp)
  amount=fp(read(m,CAMERA+0x5EC),read(m,0x800A3540),'mul')
  one,two=(4.,4.)if read(m,CAMERA+0x2C)&0x80000 else(1.,20.)
  turn(CAMERA+0x2F8,CAMERA+0x2BC,fp(amount,bits(one),'mul'),CAMERA+0x2F8)
  turn(CAMERA+0x2BC,CAMERA+0x2F8,fp(amount,bits(two),'mul'),CAMERA+0x2BC)
 else:
  a=read(m,CAMERA+0x29C)
  if floating(a)!=0.:
   a=fp(a,fp(a,read(m,0x800A3544),'mul'),'sub');put(m,CAMERA+0x29C,a)
   record(SIN,(a,));value=trig(SIN,a,c);amp=read(m,CAMERA+0x5EC)
   amp=fp(amp,fp(fp(fp(value,bits(4.),'mul'),amp,'sub'),read(m,0x800A3548),'mul'),'add');put(m,CAMERA+0x5EC,amp)
   amount=fp(read(m,CAMERA+0x5EC),read(m,0x800A354C),'mul')
   turn(CAMERA+0x2F8,CAMERA+0x2BC,amount,CAMERA+0x2F8)
   turn(CAMERA+0x2BC,CAMERA+0x2F8,fp(amount,bits(20.),'mul'),CAMERA+0x2BC)
 return public(m),calls
def helper_code():
 rom=(root/'conker/conker.us.bin').read_bytes();raw=rom[0xBC430:0xBC430+220]
 elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,ROTATE,220);assert elf[at:at+220]==raw
 return dict(zip(range(ROTATE,ROTATE+220,4),struct.unpack('>55I',raw)))
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=helper_code()if connected else None)
 def execute(self,w):
  if w>>26==17 and(w>>21)&31==16 and w&63==7:
   self.f[(w>>6)&31]=self.f[(w>>11)&31]^0x80000000
  else:return super().execute(w)
 def record_call(self,t):
  if t==RANDOM:a=()
  elif t==ROTATE:a=tuple(self.arguments(4))
  else:assert t in(SIN,COS),hex(t);a=(self.f[12],)
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.c;answer=None
  if t==RANDOM:rng_effect(self.memory,c)
  elif t==ROTATE:rotate(self.memory,*self.calls[-1][1],c)
  else:answer=trig(t,self.calls[-1][1][0],c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t==RANDOM:self.r[2]=c.random
  if answer is not None:self.f[0]=answer
def programs():return[bound_blob(*payload(p,'func_151256BC'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def corpus():
 for flags,secondary,random,angle,amp,dt,phase in itertools.product((0,0x40000,0x80000,0xC0000),(0,8),(0,1,2,3,0x80000000,0xFFFFFFFF),
   (0,0x80000000,bits(1.),0x40C90FDB,bits(20.)),(0,bits(-3.)),(0,bits(60.)),(0,8)):
  yield Case(phase,flags,secondary,angle,amp,random,dt,profile=(flags>>18)&3,seed=secondary&1)
 for flags,secondary,mutation,angle in itertools.product((0,0x40000,0x80000,0xC0000),(0,8),(1,2),(bits(-2.),bits(6.4))):
  yield Case(flags=flags,secondary=secondary,mutation=mutation,angle=angle,amp=bits(0.125),random=0xFFFFFFFF)
def compare(words,c,connected=False):
 initial=fixture(c);expected=reference(initial,c,connected);machines=[]
 for stream in words:
  m=Machine(stream,c,dict(initial),connected).run();assert(public(m.memory),m.calls)==expected,(c,m.calls,expected[1])
  machines.append(m)
 assert all(state(m)==state(machines[0])for m in machines[1:]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE);count+=1
 unreachable={29,30,31,78,103};assert coverage==set(range(154))-unreachable,sorted(set(range(154))-coverage)
 connected_count=0;helper_seen=set()
 for flags,secondary,random,angle,phase in itertools.product((0,0x40000,0x80000,0xC0000),(0,8),(0,2,0xFFFFFFFF),(0,bits(3.25)),(0,8)):
  c=Case(phase,flags,secondary,angle,bits(-1.25),random,profile=1);m=compare(streams,c,True)
  helper_seen.update((pc-ROTATE)//4 for pc in m.visits if ROTATE<=pc<ROTATE+220);connected_count+=1
 assert helper_seen==set(range(55)),sorted(set(range(55))-helper_seen)
 fault_cases=0
 examples=[Case(),Case(flags=0,angle=bits(3.25)),Case(flags=0,secondary=8,angle=bits(20.),random=2,dt=bits(60.))]
 for c in examples:
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for w in streams:
    m=Machine(w,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];fault_cases+=1
 controls={22:0x24010002,43:0x460E003E,96:0x46026180,111:0x46087280,134:0x46128000}
 rejected=[]
 samples=examples+[Case(flags=0,secondary=8,random=1),Case(flags=0x80000,random=2),
  Case(angle=COEFFICIENTS[0],random=0),Case(angle=bits(3.25),amp=bits(1.5)),Case(flags=0,angle=bits(3.25),amp=bits(1.5))]
 for index,replacement in controls.items():
  changed=list(streams[0]);assert changed[index]!=replacement;changed[index]=replacement;failures=0
  for c in samples:
   initial=fixture(c)
   m=Machine(changed,c,dict(initial)).run();failures+=(public(m.memory),m.calls)!=reference(initial,c)
  assert failures,index;rejected.append({'word':index,'failures':failures})
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'unreachable_words':sorted(unreachable),
 'unsigned_modulo_proof':'DIVU by 3 produces 0..2; words29..31 correction is unreachable. Words78/103 duplicate loads are skipped by control flow.',
 'original_rotation_cases_per_stream':connected_count,'original_rotation_words_covered':len(helper_seen),
 'access_fault_prefixes':fault_cases,'controls':rejected,'full_memory_private_bytes_registers_calls_and_ordered_accesses_equal':True,
 'trig_scope':'Pure finite deterministic float providers; no polynomial, FCSR exception flag, or hardware claim.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
