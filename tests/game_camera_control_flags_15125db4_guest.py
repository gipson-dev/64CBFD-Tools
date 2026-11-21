"""Independent byte-memory model for the camera control-bit filter."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,sys
from tools.experiments import game_camera_control_flags_15125db4_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15125DB4;SIZE=900;HELPER=0x1509BFB0
CAMERA,STATE,STATE2,FLAGS,FLAGS2,ACTOR,MARK=0x30000,0x50000,0x52000,0x54000,0x54100,0x60000,0x70000
BUSY,TABLE,DISABLED,TICKS=0x80084480,0x800BE710,0x800C3671,0x800BE9E4
SYMS={'func_1509BFB0':HELPER,'D_80084480':BUSY,'D_800BE710':TABLE,'D_800C3671':DISABLED,'D_800BE9E4':TICKS}
signed16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 phase:int=0;mode:int=0;pre_busy:int=0;global_busy:int=0;flags:int=0;flags84:int=0;runtime:int=0;external:int=0
 ad:int=0;physics:int=0;extra:int=0;running:int=0;state95:int=0;lock:int=0;equipped:int=0;selector:int=0
 index:int=0;timer:int=0;ticks:int=1;alias:int=0;mutation:int=0;table:int=0xA5FF;state197:int=1
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base,n in((CAMERA,0xA00),(STATE,0x340),(STATE2,0x340),(FLAGS,32),(FLAGS2,32),(ACTOR,0x340),(MARK,16)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 pointer=(FLAGS,CAMERA+0x36A,STATE+0x7C,STATE+0x94,TABLE+signed16(c.index)*2,CAMERA+0x84A)[c.alias]
 for at,v in((0x2C,c.flags),(0x84,c.flags84),(0x5F0,c.runtime),(0x3D0,ACTOR),(0x3D4,STATE),(0x36C,pointer)):put(m,CAMERA+at,v)
 for at,v in((0x36A,0xA5FF),(0x368,c.index),(0x5FC,c.lock),(0x73C,c.selector),(0x84A,c.timer)):put(m,CAMERA+at,v,2)
 m[CAMERA+0x23E]=c.mode;m[ACTOR+0xAD]=c.ad
 for at,v in((0x120,c.pre_busy),(0x7D,c.physics),(0x1AC,c.extra),(0x27,c.running),(0x95,c.state95),(0x1B3,c.equipped),(0x197,c.state197)):m[STATE+at]=v
 for at,v in((0x120,1),(0x7D,0),(0x1AC,0),(0x27,0),(0x95,1),(0x1B3,0),(0x197,1)):m[STATE2+at]=v
 put(m,BUSY,c.global_busy,2);put(m,TABLE+signed16(c.index)*2,c.table,2);m[DISABLED]=c.external;put(m,TICKS,c.ticks)
 put(m,FLAGS,0xC3FF,2);put(m,FLAGS2,0xF5F3,2);put(m,MARK,0);return m
def effect(m,c):
 put(m,MARK,1)
 if c.mutation==1:
  put(m,CAMERA+0x36C,FLAGS2);put(m,CAMERA+0x3D4,STATE2);put(m,CAMERA+0x36A,0xF5DF,2);m[CAMERA+0x23E]=0x29
 elif c.mutation==2:
  m[DISABLED]^=1;put(m,CAMERA+0x5F0,read(m,CAMERA+0x5F0)^0x80);put(m,TICKS,2)
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}
def reference(initial,c):
 m=dict(initial);calls=[];mode=m[CAMERA+0x23E]
 def camera_clear(mask):put(m,CAMERA+0x36A,read(m,CAMERA+0x36A,2)&~mask,2)
 def linked_clear(mask):p=read(m,CAMERA+0x36C);put(m,p,read(m,p,2)&~mask,2)
 def camera_set(mask):put(m,CAMERA+0x36A,read(m,CAMERA+0x36A,2)|mask,2)
 def linked_set(mask):p=read(m,CAMERA+0x36C);put(m,p,read(m,p,2)|mask,2)
 if m[read(m,CAMERA+0x3D4)+0x120]or read(m,BUSY,2):
  put(m,CAMERA+0x36A,0,2);linked_clear(31);return public(m,c),calls
 if mode:
  if mode in(2,18,19,10,52,16,15):
   if mode==15:calls.append((HELPER,(3,0x9000,0x18,0x25,0x13,480)));effect(m,c)
   linked_set(16);camera_set(16);linked_clear(15)
  else:put(m,CAMERA+0x36A,read(m,TABLE+signed16(read(m,CAMERA+0x368,2))*2,2),2)
  if mode in(3,13,26,42):camera_clear(15);linked_clear(15)
  if mode==41:linked_set(16);camera_set(16)
 elif read(m,CAMERA+0x2C)&0x100:camera_clear(15);linked_clear(15)
 if m[read(m,CAMERA+0x3D0)+0xAD]==1 and read(m,CAMERA+0x2C)&0x80:camera_clear(28);linked_clear(12)
 if read(m,CAMERA+0x84)&0x200000:camera_clear(15)
 if m[DISABLED]or read(m,CAMERA+0x5F0)&0x80:camera_clear(31);linked_clear(31)
 p=read(m,CAMERA+0x3D4)
 if m[p+0x7D]or m[p+0x1AC]or m[p+0x27]:camera_clear(16);linked_clear(16)
 p=read(m,CAMERA+0x3D4)
 if m[p+0x95]or(signed16(read(m,CAMERA+0x5FC,2))and m[p+0x1B3]):camera_clear(31);linked_clear(31)
 flags=read(m,CAMERA+0x2C);selector=signed16(read(m,CAMERA+0x73C,2))
 if(flags&0x100 and selector==0)or selector==3:camera_clear(16);linked_clear(16)
 if read(m,CAMERA+0x2C)&0x40 and signed16(read(m,CAMERA+0x84A,2)):
  put(m,CAMERA+0x84A,signed16(read(m,CAMERA+0x84A,2))-read(m,TICKS),2)
  camera_clear(16);linked_clear(16)
  if signed16(read(m,CAMERA+0x84A,2))<=0:put(m,CAMERA+0x84A,0,2)
 return public(m,c),calls
class Machine(FactoryOracle):
 def __init__(self,words,c,m):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,))
 def record_call(self,t):
  assert t==HELPER;args=tuple(self.arguments(6));assert args[0]==3
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==HELPER;effect(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():return[bound_blob(*payload(p,'func_15125DB4'),SYMS)for p in(out/'image-qualification/retail.o',out/'source-screen/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def corpus():
 flags=(0,0x40,0x80,0x100,0xC0,0x140,0x180,0x1C0)
 for mode,flag in itertools.product(range(256),flags):yield Case(mode=mode,flags=flag,timer=17,selector=1)
 for mode,flag in itertools.product((0,15),(0,0x40)):yield Case(mode=mode,ad=1,flags=flag,timer=2,selector=1)
 modes=(0,2,3,10,13,15,16,18,19,26,41,42,52,255)
 for mode,mask in itertools.product(modes,range(128)):
  yield Case(mode=mode,flags=0x1C0,flags84=0x200000 if mask&1 else 0,ad=1 if mask&2 else 0,
   runtime=0x80 if mask&4 else 0,external=1 if mask&8 else 0,physics=1 if mask&16 else 0,
   state95=1 if mask&32 else 0,equipped=1 if mask&64 else 0,lock=1,selector=1,timer=17)
 for phase,mode,timer,ticks,alias,mutation in itertools.product((0,8),(0,15,41),(-32768,-1,0,1,16,32767),(-32768,-1,0,1,16,32767,0x7FFFFFFF,0x80000000),(0,1,2,3,4,5),(0,1,2)):
  yield Case(phase=phase,mode=mode,flags=0x40,timer=timer,ticks=ticks,alias=alias,mutation=mutation,selector=1)
 for mode,gate,value in itertools.product(modes,('pre_busy','global_busy','extra','running','state95','equipped','ad'),(0,1,128,255)):
  yield replace(Case(mode=mode,flags=0x180,selector=1,lock=1),**{gate:value})
 for mode,index,selector in itertools.product(modes,(-32768,-1,0,3,32767),(-32768,-1,0,1,3,32767)):
  yield Case(mode=mode,index=index,selector=selector,flags=0x140,timer=1)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];count=0;coverage=set()
 for c in corpus():
  initial=fixture(c);expected=reference(initial,c);states=[]
  for words in streams:
   m=Machine(words,c,dict(initial)).run();assert(public(m.memory,c),m.calls)==expected,c
   states.append(state(m));coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE)
   assert m.r[29]==STACK+c.phase
  assert states[0]==states[1]==states[2],c;count+=1
 assert coverage==set(range(225)),sorted(set(range(225))-coverage)
 controls={0x00C:0xAFBF0028,0x02C:0x17000007,0x0AC:0x24070024,0x1E0:0x314BFFE3,0x344:0x006FC021}
 # Use broad representative cases so every control must alter an observation.
 examples=[Case(mode=mode,global_busy=gate,flags=flags,ad=ad,timer=1,ticks=1,selector=1)
  for mode,gate,flags,ad in itertools.product((0,2,3,15,41),(0,1),(0x80,0x1C0),(0,1))]
 rejected=[]
 for at,replacement in controls.items():
  words=list(streams[0]);assert words[at//4]!=replacement;words[at//4]=replacement;failed=0
  for c in examples:
   try:
    initial=fixture(c);m=Machine(words,c,dict(initial)).run();failed+=(public(m.memory,c),m.calls)!=reference(initial,c)or state(m)!=state(Machine(streams[0],c,dict(initial)).run())
   except(AssertionError,KeyError):failed+=1
  assert failed,hex(at);rejected.append({'offset':at,'failures':failed})
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'controls':rejected,
  'word_identity':True,'full_memory_registers_private_bytes_and_ordered_trace_equal':True,'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
