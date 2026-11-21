"""Independent byte-memory sound callback model and emitted MIPS execution."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_camera_sound_callback_151277b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import test_game_actor_burst_consumer_match as faults
ENTRY,HELPER,TICK=0x151277B0,0x100111C8,0x800BE9E4
SLOT,CAMERA,PRIMARY,SECONDARY,STATE,AUX,MARK=0x30000,0x40000,0x50000,0x51000,0x60000,0x70000,0x71000
SYMS={'func_100111C8':HELPER,'D_800BE9E4':TICK}
@dataclass(frozen=True)
class Case:
 phase:int=0;mode:int=2;state:int=0;counter:int=0;delta:int=0;handle:int=7;flags:int=0xABCDEF80;tick:int=1;mutation:int=0;alias:int=0
 first:int=0x3F800000;second:int=0x3F800000;x:int=0x42CA8000;y:int=0xC1A20000;z:int=0x3E000000;state_pointer:int=0
def state_address(c):return c.state_pointer or(STATE,SLOT+0x24,SLOT+2,SLOT+4,SLOT+6,SLOT)[c.alias]
def product(c):return bits(floating(c.first)*floating(c.second))
def args(c):return(SLOT,*(AUX+i*16 for i in range(5)),state_address(c))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((SLOT-16,80),(CAMERA,0x900),(PRIMARY,0x340),(SECONDARY,0x340),(STATE,8),(AUX,80),(MARK,8)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(m,SLOT+0x18,CAMERA);put(m,SLOT+0x1C,((c.counter&255)<<24)|(((product(c)&0xFFFFFF)+c.delta)&0xFFFFFF))
 put(m,SLOT+0x24,c.handle,2);put(m,SLOT+0x10,c.flags);put(m,CAMERA+0x3D0,PRIMARY);put(m,CAMERA+0x3D4,SECONDARY)
 for at,v in((0x14,c.x),(0x18,c.y),(0x1C,c.z)):put(m,PRIMARY+at,v)
 put(m,SECONDARY+0x174,c.first);put(m,SECONDARY+0x178,c.second);m[SECONDARY+0x197]=c.mode
 put(m,TICK,c.tick);put(m,state_address(c),c.state,2)
 return m
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+1024}
def effect(m,c):
 put(m,MARK,read(m,MARK)^0x13579BDF)
 if c.mutation:
  put(m,SLOT+0x24,0x1234,2);put(m,SLOT+0x10,read(m,SLOT+0x10)^0x10001)
  put(m,SLOT+0x1C,0x543210FE);put(m,state_address(c),0x622,2);put(m,TICK,0x80000000)
def reference(initial,c,include_stack=False):
 m=dict(initial);calls=[];pending=state_address(c);camera=read(m,SLOT+0x18);packed=read(m,SLOT+0x1C)
 secondary=read(m,camera+0x3D4);current=bits(floating(read(m,secondary+0x174))*floating(read(m,secondary+0x178)))&0xFFFFFF
 previous=packed&0xFFFFFF;count=packed>>24;stopped=False
 if read(m,pending,2)==0x622:put(m,pending,0,2)
 for at,to in((0x14,2),(0x18,4),(0x1C,6)):
  actor=read(m,camera+0x3D0);put(m,SLOT+to,int(floating(read(m,actor+at))),2)
 if m[read(m,camera+0x3D4)+0x197]!=2:return(m if include_stack else public(m,c)),calls,1
 if previous==current:count=0
 elif count>=10:stopped=True
 elif(previous-current)&0xFFFFFFFF>100:count=(count+read(m,TICK))&0xFFFFFFFF
 put(m,SLOT+0x1C,(count<<24)|current)
 def release():
  handle=read(m,SLOT+0x24,2)
  if handle:calls.append((HELPER,(handle,)));effect(m,c)
 if stopped:
  if read(m,pending,2)!=0x61C:
   release();put(m,SLOT+0x24,0,2);put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80);put(m,pending,0x61C,2)
 elif read(m,pending,2)==0x61C:
  release();put(m,SLOT+0x24,0,2);put(m,pending,0x61D,2);put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80)
 if read(m,SLOT+0x24,2)==0 and read(m,pending,2)==0:put(m,SLOT+0x10,read(m,SLOT+0x10)&~0x80)
 return(m if include_stack else public(m,c)),calls,0
class Machine(FactoryOracle):
 def __init__(self,words,c,m):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=args(c))
 def record_call(self,t):
  assert t==HELPER,hex(t);a=tuple(self.arguments(1));assert 0<a[0]<=65535,a
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==HELPER;effect(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():return[bound_blob(*payload(p,'func_151277B0'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def corpus():
 for mode,state,counter,delta,handle,mutation,alias in itertools.product((0,2,255),(0,0x622,0x61C,0x61D),(0,9,10,255),(0,100,101,-1),(0,7),(0,1),(0,1)):
  yield Case(mode=mode,state=state,counter=counter,delta=delta,handle=handle,mutation=mutation,alias=alias)
 for mode,state in itertools.product(range(256),(0,0x61C)):
  yield Case(mode=mode,state=state,counter=10,delta=101,phase=8)
 for alias,state,mutation,tick in itertools.product(range(6),(0,0x622,0x61C,0x61D),(0,1),(0,0x7FFFFFFF,0xFFFFFFFF)):
  yield Case(alias=alias,state=state,mutation=mutation,tick=tick,counter=9,delta=101)
 for first,second,delta,counter in itertools.product((bits(0.),0x80000000,bits(1.5),bits(-1.25)),(bits(.5),bits(1.5)),(0,-1,101),(0,10)):
  yield Case(first=first,second=second,delta=delta,counter=counter,state=0x61C)
 for coords in((bits(-32768.),bits(32767.),bits(-3.75)),(bits(-2147483648.),bits(2147483520.),bits(65535.75))):
  yield Case(x=coords[0],y=coords[1],z=coords[2],counter=10,delta=101)
def run():
 streams=programs();assert streams[0]==streams[2]and streams[0]!=streams[1];coverage=set();n=0
 for c in corpus():
  initial=fixture(c);expected=reference(initial,c);states=[]
  for words in streams:
   m=Machine(words,c,dict(initial)).run();assert(public(m.memory,c),m.calls,m.r[2])==expected,c
   states.append((m.memory,m.trace,m.calls,m.r[2],tuple(m.r[i]for i in(*range(16,24),28,29,30,31)),tuple(m.f[20:])))
   coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+496)
  assert states[0]==states[1]==states[2],c;n+=1
 assert coverage==set(range(124)),sorted(set(range(124))-coverage)
 cuts=0
 for c in(Case(counter=10,delta=101),Case(state=0x61C,mutation=1),Case(alias=1,state=0x622),Case(mode=0,phase=8)):
  initial=fixture(c);limit=Machine(streams[0],c,dict(initial)).run().all_accesses
  for cut in range(limit):
   states=[]
   for words in streams:
    m=Machine(words,c,dict(initial));m.cut=cut
    try:m.run();raise AssertionError('missing access boundary')
    except faults.AccessBoundary:pass
    states.append((m.memory,m.trace,m.calls,m.current_pc,m.delay_of))
   assert states[0]==states[1]==states[2],(c,cut);cuts+=1
 rejected=[]
 for index in(26,64,79,114):
  bad=list(streams[0]);bad[index]^=1<<16;failures=0
  for c in(Case(counter=10,delta=101),Case(state=0x61C,mutation=1),Case(mode=0),Case(handle=0)):
   initial=fixture(c)
   try:m=Machine(bad,c,dict(initial)).run();failed=(public(m.memory,c),m.calls,m.r[2])!=reference(initial,c)
   except(AssertionError,KeyError):failed=True
   failures+=failed
  assert failures,index;rejected.append({'word':index,'failures':failures})
 r={'cases_per_stream':n,'streams':3,'covered_words':len(coverage),'fault_prefixes_per_stream':cuts,'effective_controls':rejected,
  'all_public_memory_private_bytes_ordered_accesses_and_preserved_ABI_equal':True,'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
