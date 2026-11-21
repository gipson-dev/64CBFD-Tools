"""Orbit setup model with pure finite trig providers and original queue helper."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_camera_orbit_15125a6c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,HELPER,SINE,COSINE=0x15125A6C,468,0x1512D560,0x15047D60,0x15047C00
CAMERA,ACTOR,ACTOR2,QUEUE=0x30000,0x50000,0x51000,0x60000
BASE,SELECTOR,FACTOR,PHASE_FACTOR,QUEUE_PTR=0x800C3600,0x800DBFF4,0x800A3550,0x800A3554,0x800DC2B0
SYMS={'func_1512D560':HELPER,'sinf':SINE,'cosf':COSINE,'D_800C3600':BASE,'D_800DBFF4':SELECTOR,
 'D_800A3550':FACTOR,'D_800A3554':PHASE_FACTOR,'D_800C3614':BASE+0x14,'D_800C3618':BASE+0x18,
 'D_800C361C':BASE+0x1C,'D_800C3624':BASE+0x24,'D_800C365C':BASE+0x5C,'D_800DC2B0':QUEUE_PTR}
LUT=tuple(map(bits,(0.0,-0.0,0.25,-0.5,0.75,-1.0,1.25,2.0)))
@dataclass(frozen=True)
class Case:
 phase:int=0;mode:int=42;pending:int=0;flags:int=0;heading:int=0x42B40000;x:int=0x42CA8000;y:int=0xC1A20000;z:int=0x3E000000
 factor:int=0x3C8EFA35;phase_factor:int=0x3C8EFA35;profile:int=0;mutation:int=0;index:int=0;cursor:int=0;alias:int=0;actor_present:int=1
def trig(target,value,c):return LUT[((value>>20)^(value>>8)^(3 if target==COSINE else 0)^c.profile)&7]
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base,n in((CAMERA,0xA00),(ACTOR,0x340),(ACTOR2,0x340),(QUEUE,4*0xB0),(BASE,0x60),(SELECTOR,16)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 p=(BASE if c.alias else ACTOR)if c.actor_present else 0
 put(m,CAMERA+0x3D0,p);put(m,CAMERA+0x2C,c.flags);m[CAMERA+0x23E]=c.mode;m[CAMERA+0x7E4]=c.pending;m[CAMERA+0x23D]=c.index
 if p:
  for at,v in((0x14,c.x),(0x18,c.y),(0x1C,c.z),(0x40,c.heading)):put(m,p+at,v)
 for at,v in((0x14,bits(-17.5)),(0x18,bits(31.25)),(0x1C,bits(60.5)),(0x40,bits(-45.0))):put(m,ACTOR2+at,v)
 put(m,FACTOR,c.factor);put(m,PHASE_FACTOR,c.phase_factor);put(m,QUEUE_PTR,QUEUE)
 for i in range(4):put(m,QUEUE+i*0xB0+0xAC,c.cursor)
 return m
def append_queue(m,camera,command,payload):
 q=read(m,QUEUE_PTR)+m[camera+0x23D]*0xB0;i=read(m,q+0xAC)
 assert 0<=i<20;i&=0xFFFFFFFF;put(m,q+i*8,command);put(m,q+i*8+4,payload)
 put(m,q+0xAC,0 if i+1==20 else i+1)
def effect(m,c,command):
 if not c.mutation:return
 if command==5:
  put(m,CAMERA+0x3D0,ACTOR2);put(m,FACTOR,bits(0.03125));put(m,PHASE_FACTOR,bits(-0.015625))
  m[CAMERA+0x23D]=(c.index+1)%4;m[CAMERA+0x7E4]=0x55;m[CAMERA+0x23E]=0
 elif command==6:m[CAMERA+0x7E4]=0x55
 elif command==7:m[BASE+0x5C]=0x7D
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}
def reference(initial,c):
 m=dict(initial);calls=[];snapshots=[]
 def command(mode,payload):
  calls.append((HELPER,(CAMERA,mode,payload)))
  if mode==7:snapshots.append(bytes(m[BASE+i]for i in range(0x60)))
  append_queue(m,CAMERA,mode,payload);effect(m,c,mode)
 def math(target,arg):calls.append((target,(arg,)));return trig(target,arg,c)
 if m[CAMERA+0x23E]==42:
  heading=read(m,read(m,CAMERA+0x3D0)+0x40)
  if read(m,CAMERA+0x2C)!=0x40000:command(5,0);m[CAMERA+0x7E4]=1
  m[SELECTOR]=3;put(m,BASE,1);put(m,BASE+4,0)
  angle=mul(heading,read(m,FACTOR));first=math(SINE,angle)
  phase=mul(sub(heading,bits(90.0)),read(m,PHASE_FACTOR));second=math(SINE,phase)
  put(m,BASE+0x14,add(mul(second,bits(46.0)),add(read(m,read(m,CAMERA+0x3D0)+0x14),mul(bits(138.0),first))))
  put(m,BASE+0x18,add(read(m,read(m,CAMERA+0x3D0)+0x18),bits(96.0)))
  first=math(COSINE,angle);second=math(COSINE,phase)
  put(m,BASE+0x1C,add(mul(second,bits(46.0)),add(read(m,read(m,CAMERA+0x3D0)+0x1C),mul(bits(138.0),first))))
  put(m,BASE+0x20,0);put(m,BASE+0x24,bits(-180.0));put(m,BASE+8,0);put(m,BASE+0x28,sub(heading,bits(180.0)));m[BASE+0x5C]=0
  command(7,BASE)
 elif m[CAMERA+0x7E4]:command(6,0);m[CAMERA+0x7E4]=0
 return public(m,c),calls,snapshots
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;self.snapshots=[]
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=helper_code()if connected else None)
 def record_call(self,t):
  if t==HELPER:
   args=tuple(self.arguments(3));assert args[0]==CAMERA and args[1]in(5,6,7)
   if args[1]==7:self.snapshots.append(bytes(self.memory[BASE+i]for i in range(0x60)))
  else:assert t in(SINE,COSINE),hex(t);args=(self.f[12],)
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  if t==HELPER:
   args=self.calls[-1][1];append_queue(self.memory,*args);effect(self.memory,self.c,args[1]);answer=0xA5000000
  else:answer=trig(t,self.calls[-1][1][0],self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t!=HELPER:self.f[0]=answer
def helper_code():
 rom=(root/'conker/conker.us.bin').read_bytes();raw=rom[0x15AA10:0x15AAB4]
 baseline=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(baseline,HELPER,len(raw));assert baseline[at:at+len(raw)]==raw
 return dict(zip(range(HELPER,HELPER+164,4),struct.unpack('>41I',raw)))
def programs():return[bound_blob(*payload(p,'func_15125A6C'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def corpus():
 for mode,pending,mutation in itertools.product(range(256),(0,1,128,255),(0,1)):
  if mode!=42:yield Case(mode=mode,pending=pending,actor_present=0,mutation=mutation)
 for phase,flags,heading,coeff,profile,mutation,index,cursor,alias in itertools.product((0,8),(0,0x40000,0x40001),
  (bits(-180.0),0x80000000,0,bits(22.5),bits(90.0),bits(179.75)),(0,1),(0,1),(0,1),(0,3),(0,19),(0,1)):
  yield Case(phase=phase,flags=flags,heading=heading,phase_factor=bits(-0.03125)if coeff else 0x3C8EFA35,
   profile=profile,mutation=mutation,index=index,cursor=cursor,alias=alias,pending=128)
 for pending,flags,index,cursor in itertools.product(range(256),(0,0x40000,0x40001),(0,1),(18,19)):
  yield Case(pending=pending,flags=flags,index=index,cursor=cursor,heading=bits(1e10))
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.snapshots,m.current_pc,m.delay_of)
def static_reachable(words):
 pending=[0];seen=set();instructions=set()
 while pending:
  i=pending.pop()
  if i in seen:continue
  assert 0<=i<len(words);seen.add(i);instructions.add(i)
  w=words[i];op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op in(4,5,20,21):
   displacement=((w&65535)^32768)-32768;target=i+1+displacement
   always=rs==rt;take_always=always and op in(4,20);never=always and op in(5,21)
   if not never:instructions.add(i+1);pending.append(target)
   if not take_always:
    if op not in(20,21):instructions.add(i+1)
    pending.append(i+2)
  elif op==3:
   target=((ENTRY+4*i+4)&0xF0000000)|((w&0x3FFFFFF)<<2);assert not ENTRY<=target<ENTRY+SIZE
   instructions.add(i+1);pending.append(i+2)
  elif op==0 and w&63==8:assert rs==31;instructions.add(i+1)
  else:pending.append(i+1)
 return instructions
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  initial=fixture(c);expected=reference(initial,c);states=[]
  for words in streams:
   m=Machine(words,c,dict(initial)).run();assert(public(m.memory,c),m.calls,m.snapshots)==expected,c
   states.append(state(m));coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE)
  assert states[0]==states[1]==states[2],c;count+=1
 reachable=static_reachable(streams[0]);assert set(range(117))-reachable=={104}
 assert coverage==reachable,sorted(reachable-coverage)
 connected=0;helper_visits=set()
 for mode,pending,flags,index,cursor in itertools.product((0,42),(0,255),(0,0x40000,0x40001),(0,1,3),(0,18,19)):
  c=Case(mode=mode,pending=pending,flags=flags,index=index,cursor=cursor);initial=fixture(c);expected=reference(initial,c);states=[]
  for words in streams:
   m=Machine(words,c,dict(initial),True).run();assert(public(m.memory,c),m.calls,m.snapshots)==expected,c
   states.append(state(m));helper_visits.update((pc-HELPER)//4 for pc in m.visits if HELPER<=pc<HELPER+164)
  assert states[0]==states[1]==states[2];connected+=1
 assert helper_visits==set(range(41)),sorted(set(range(41))-helper_visits)
 controls={0x18:0x2401002B,0x100:0x3C01800D,0x194:0xAC20365C,0x38:0xE7A40034}
 examples=[Case(flags=f,mutation=m,heading=bits(22.5))for f,m in itertools.product((0,0x40000,0x40001),(0,1))]+[Case(mode=0,pending=1,actor_present=0)]
 rejected=[]
 for offset,replacement in controls.items():
  changed=list(streams[0]);assert changed[offset//4]!=replacement;changed[offset//4]=replacement;failures=0
  for c in examples:
   try:
    initial=fixture(c);m=Machine(changed,c,dict(initial)).run();failures+=(public(m.memory,c),m.calls,m.snapshots)!=reference(initial,c)
   except(AssertionError,KeyError,OverflowError):failures+=1
  assert failures,offset;rejected.append({'offset':offset,'failures':failures})
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_offsets':[416],
  'all_normal_entry_reachable_words_covered':True,'all_117_payload_words_identical':True,
  'original_queue_cases_per_stream':connected,'original_queue_covered_words':len(helper_visits),
  'controls':rejected,'pure_finite_trig_contract':True,'full_memory_registers_private_bytes_ordered_trace_equal':True,'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
