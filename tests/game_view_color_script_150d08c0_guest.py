"""Ordered script queries, palette stores, fresh loads and unsigned FP fallbacks."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct,sys
from tools.experiments import game_view_color_script_150d08c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY=0x150D08C0;QUERY=0x1509BE40;SUBMIT=0x1509BFB0;SMOOTH=0x150495B0
VIEW=0x30000;SIZE=0x9A0;GLOBALS=tuple(range(0x800888C0,0x800888E4,4))
bits,floating,u32=fp.bits,fp.floating,fp.u32
@dataclass(frozen=True)
class Case:
 replies:tuple=(1,0,0,1)
 flags:int=0x13579BDF
 colors:tuple=(bits(63.75),bits(255.5),bits(256.25))
 current:tuple=(bits(10.),bits(30.),bits(90.))
 velocity:tuple=(bits(1.),bits(-2.),bits(3.))
 dt:int=bits(.125)
 mode:int=0
 phase:int=0
 fcsr:int=0

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 m.update({VIEW+i:(i*19+0xA5)&255 for i in range(-16,SIZE+16)})
 put(m,VIEW+0x84,c.flags);put(m,VIEW+0x7B4,c.dt)
 for p,v in zip(GLOBALS,c.current+(bits(12.),bits(34.),bits(56.))+c.velocity):put(m,p,v)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def snapshot(m):return (read(m,VIEW+0x84),read(m,VIEW+0x7B4),*(read(m,p)for p in GLOBALS))
def conversion(word):
 value=floating(word)
 return u32(math.trunc(value))&255 if math.isfinite(value)and -1.<value<4294967296. else 255
def effect(m,c,t,args,ordinal):
 if t==QUERY:
  if c.mode&1 and ordinal==1:put(m,VIEW+0x84,read(m,VIEW+0x84)^0xF0F0FFFF)
  return u32(c.replies[(0x403D,0x4043,0x4044,0x4045).index(args[1])])
 if t==SMOOTH:
  put(m,args[0],c.colors[ordinal-1]);put(m,args[2],bits(float(ordinal)))
  if c.mode&2:
   put(m,VIEW+0x7B4,bits(.25*ordinal))
   if ordinal==2:put(m,GLOBALS[0],bits(511.5))
  return 0xABCDEF00+ordinal
 assert t==SUBMIT
 if c.mode&4:
  for j,p in enumerate(GLOBALS[:3]):put(m,p,bits(17.25+ordinal*31+j))
 return 0x12340000+ordinal

def reference(initial,c,provider=None):
 m=dict(initial);calls=[];observations=[];counts={}
 def call(t,*args):
  args=tuple(map(u32,args));calls.append((t,args));observations.append(snapshot(m));counts[t]=counts.get(t,0)+1
  return effect(m,c,t,args,counts[t])if provider is None else provider(m,c,t,args,counts[t])
 if call(QUERY,1,0x403D,6,0x9000):
  put(m,VIEW+0x84,read(m,VIEW+0x84)|0x80021000)
  if call(QUERY,1,0x4043,6,0x9000):palette=(64.,255.,255.)
  elif call(QUERY,1,0x4044,6,0x9000):palette=(255.,64.,255.)
  elif call(QUERY,1,0x4045,6,0x9000):palette=(255.,255.,64.)
  else:palette=(255.,255.,255.)
  for p,v in zip(GLOBALS[3:6],palette):put(m,p,bits(v))
 else:
  for p in GLOBALS[3:6]:put(m,p,bits(255.))
  put(m,VIEW+0x84,read(m,VIEW+0x84)&0x7FFDEFFF)
  put(m,VIEW+0x84,read(m,VIEW+0x84)|8)
 for i in range(3):call(SMOOTH,GLOBALS[i],read(m,GLOBALS[3+i]),GLOBALS[6+i],bits(4.),bits(6.),read(m,VIEW+0x7B4))
 for i,selector in enumerate((0x30F5,0x30F4,0x30F3,0x30FA,0x30F9,0x30F8)):
  call(SUBMIT,1,selector,0x12,conversion(read(m,GLOBALS[i%3])))
 return m,calls,observations

class Oracle(fp.Oracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c
  FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(VIEW,)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr;self.counts={};self.observations=[]
 def record_call(self,t):
  assert t in(QUERY,SUBMIT,SMOOTH,ENTRY),hex(t)
  args=tuple(map(u32,self.arguments(6 if t==SMOOTH else 1 if t==ENTRY else 4)))
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append(snapshot(self.memory))
 def clobber(self,value):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def hook(self,t):self.clobber(effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t]))

@lru_cache(maxsize=1)
def streams():
 ws=json.loads((out/'program.json').read_text());truth=list(struct.unpack_from('>372I',(root/'conker/conker.us.bin').read_bytes(),0xFDD70));assert ws==truth;return ws,truth
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c):
 m=Oracle(ws,c).run();expected,calls,observations=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert m.observations==observations,(c,'call snapshots',m.observations,observations)
 assert public(m.memory)==public(expected),(c,'memory')
 assert m.fcsr==c.fcsr,(c,'FCSR save/restore',hex(m.fcsr),hex(c.fcsr))
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m

def cases():
 replies=((0,1,1,1),(1,1,1,1),(1,0,1,1),(1,0,0,1),(1,0,0,0),(0xFFFFFFFF,0,0x80000000,0))
 yield from(Case(replies=q,flags=f,mode=mode,phase=phase,fcsr=rm|sticky)for q,f,mode,phase,rm,sticky in itertools.product(replies,(0,0xFFFFFFFF,0x13579BDF),(0,7),(0,8),range(4),(0,0x54)))
 values=(0,0x80000000,bits(-.5),bits(-1.),bits(63.75),bits(255.),bits(256.),bits(511.5),bits(2147483520.),bits(2147483648.),bits(4294967040.),bits(4294967296.),0x7F800000,0xFF800000,0x7FC00001)
 yield from(Case(colors=(v,)*3,mode=mode,fcsr=rm|0x54)for v,mode,rm in itertools.product(values,(0,7),range(4)))
def main():
 count=0;visits=set()
 for c in cases():
  a,b=[check(ws,c)for ws in streams()];assert state(a)==state(b);visits.update(a.visits);count+=1
 faults=0
 for c in(Case(),Case(replies=(0,0,0,0),mode=7,phase=8),Case(colors=(bits(4294967296.),)*3)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   pair=[]
   for ws in streams():
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    pair.append(state(m))
   assert pair[0]==pair[1];faults+=1
 missed=[i for i in range(372)if ENTRY+4*i not in visits]
 r=dict(cases_per_stream=count,streams=2,target_executed_words=372-len(missed),unexecuted_word_indices=missed,
  body_words=372,access_fault_pairs=faults,all_four_rounding_modes=True,FCSR_restoration=True,
  invalid_float_conversions_guest_only=True,fresh_color_and_timestep_loads=True,ordered_provider_snapshots=True,
  provider_internals_contracted=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
