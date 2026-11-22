"""All cooldown bytes, signed steps, first-zero selection and ordered fresh records."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_record_sound_scheduler_150d0730_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY=0x150D0730;SETUP=0x151827D0;QUERY=0x150A29C8;RNG=0x150ADA20;SOUND=0x10010F88
TIMER=0x800D98F0;STEP=0x800BE9E4;POINTER=0x800D3098;RECORDS=0x30000;OTHER=0x40000;RECORD_SIZE=52;COUNT=73
INDICES=(0x15,0x1A,0x1B,0x1C,0x1D,0x20)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 timer:int=0
 step:int=1
 replies:tuple=(1,1,1,1,1,0)
 randoms:tuple=(0xFFFFFFFF,0x80000000)
 coordinates:tuple=(0x8000,0xFFFF,0x7FFF)
 mode:int=0
 phase:int=0
 argument:int=0x87654321
 fcsr:int=0
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for base in(RECORDS,OTHER):
  m.update({base+i:(i*19+0xA5)&255 for i in range(-16,COUNT*RECORD_SIZE+16)})
  for index in range(COUNT):
   for j in range(3):put(m,base+index*RECORD_SIZE+2*j,c.coordinates[(index+j)%3]^(0x5555 if base==OTHER else 0),2)
 for p in(TIMER-1,TIMER+1):m[p]=0xA5
 m[TIMER]=c.timer;put(m,STEP,c.step);put(m,POINTER,RECORDS);return m
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def snapshot(m):return(m[TIMER],read(m,STEP),read(m,POINTER),*(read(m,base+i*52+2*j,2)for base in(RECORDS,OTHER)for i in INDICES for j in range(3)))
def effect(m,c,t,args,ordinal):
 if t==SETUP:
  if c.mode&1:m[TIMER]^=0x80;put(m,STEP,0xFFFFFFFF)
  return 0xABCDEF00
 if t==QUERY:
  if c.mode&2:
   put(m,POINTER,OTHER);put(m,OTHER+args[1]*52+2,0x8001,2)
  return c.replies[INDICES.index(args[1])]
 if t==RNG:
  if c.mode&4:
   put(m,POINTER,OTHER if ordinal==1 else RECORDS)
   for i in INDICES:
    for j in range(3):put(m,RECORDS+i*52+2*j,0x8000+0x111*ordinal+j,2)
  return c.randoms[ordinal-1]
 assert t==SOUND
 if c.mode&8:m[TIMER]=17
 return 0xBEEF
def reference(initial,c,provider=None):
 m=dict(initial);calls=[];observations=[];counts={}
 def call(t,*args):
  args=tuple(map(u32,args));calls.append((t,args));observations.append(snapshot(m));counts[t]=counts.get(t,0)+1
  return effect(m,c,t,args,counts[t])if provider is None else provider(m,c,t,args,counts[t])
 call(SETUP)
 if m[TIMER]:
  m[TIMER]=((m[TIMER]-signed(read(m,STEP)))&255)if signed(read(m,STEP))<m[TIMER]else 0
 else:
  selected=next((index for index in INDICES if not call(QUERY,0,index)),0)
  if selected:
   m[TIMER]=(call(RNG)&127)+128;choice=call(RNG)%3+108;p=read(m,POINTER)+selected*52
   call(SOUND,choice,24000,0,0,0,*(half(read(m,p+2*j,2))for j in range(3)),800,1500)
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(c.argument,)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.counts={};self.observations=[]
 def record_call(self,t):
  counts={SETUP:0,QUERY:2,RNG:0,SOUND:10,ENTRY:1};assert t in counts,hex(t)
  args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append(snapshot(self.memory))
 def clobber(self,value):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def hook(self,t):self.clobber(effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t]))
@lru_cache(maxsize=1)
def streams():
 ws=json.loads((out/'program.json').read_text());truth=list(struct.unpack_from('>97I',(root/'conker/conker.us.bin').read_bytes(),0xFDBE0));assert ws==truth;return ws,truth
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c):
 m=Oracle(ws,c).run();expected,calls,observations=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert m.observations==observations,(c,'boundary state')
 assert public(m.memory)==public(expected),(c,'memory')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def cases():
 yield from(Case(timer=t,step=s,phase=phase)for t,s,phase in itertools.product(range(256),(0,1,2,127,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,8)))
 for selection,answer,mode,phase in itertools.product(range(7),(1,0x80000000,0xFFFFFFFF),(0,2,4,8,14),(0,8)):
  yield Case(replies=tuple(0 if i==selection else answer for i in range(6)),mode=mode,phase=phase)
 yield from(Case(randoms=(a,b),coordinates=coords)for a,b in itertools.product((0,1,127,128,255,0x7FFFFFFF,0x80000000,0xFFFFFFFF),repeat=2)for coords in((0,1,32767),(32768,65535,0)))
 yield from(Case(timer=t,step=0x80000000,mode=1)for t in(0,1,127,128,255))
def main():
 visits=set();count=0
 for c in cases():
  a,b=[check(ws,c)for ws in streams()];assert state(a)==state(b);visits.update(a.visits);count+=1
 faults=0
 for c in(Case(),Case(timer=255,step=0x80000000),Case(replies=(0,)*6,mode=14,phase=8),Case(replies=(1,)*6)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   pair=[]
   for ws in streams():
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    pair.append(state(m))
   assert pair[0]==pair[1];faults+=1
 assert all(ENTRY+4*i in visits for i in range(97))
 r=dict(cases_per_stream=count,streams=2,target_executed_words=97,access_fault_pairs=faults,
  all_256_cooldown_bytes=True,signed_step_extremes=True,ordered_first_zero_selection=True,unsigned_independent_randoms=True,
  signed_coordinates=True,late_record_pointer_and_coordinate_loads=True,provider_internals_contracted=True,
  source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
