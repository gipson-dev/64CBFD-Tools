"""Ordered event contracts, exact guest arithmetic, and callback/record domains."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_first_actor_event_dispatch_150d0e90_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x150D0E90;LOOKUP=0x151149AC;INIT=0x151951E0;SOUND=0x10010154
EFFECT=0x15136C3C;RESET=0x15145A50;STATE=0x1507CD64
ACTOR=0x800CC2D0;ATTACH=0x30000;RECORDS=0x50000;FLAGS=0x60080;OTHER=0x61080
BASE=0x800DBEF4;FLAGSP=0x800DBF94;COUNT=0x800DBEF0;TICKS=0x800BE9E4
COUNTERS=(0x80088890,0x80088894,0x80088898,0x8008889C)
SELECTORS=(250,249,248,251)
COUNTS={LOOKUP:1,INIT:1,SOUND:5,EFFECT:8,RESET:1,STATE:2,ENTRY:1}
u32=lambda n:n&0xFFFFFFFF
s32=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
div160=lambda n:(abs(s32(n))//160)*(-1 if s32(n)<0 else 1)

@dataclass(frozen=True)
class Case:
 ticks:int=1
 counters:tuple=(1000,-1000,77,-77)
 gate:int=0
 mask:int=15
 pattern:int=0
 indices:tuple=(0,1,2,3)
 mode:int=0
 phase:int=0
 unused:int=0x89ABCDEF
 residual:int=0
 missing:bool=False

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
 for start,length in((ACTOR-16,844),(ATTACH-16,0x150),(RECORDS-16,64*160+32),(FLAGS-128,288),(OTHER-128,288)):
  m.update({start+i:(i*19+0xA5)&255 for i in range(length)})
 for i in range(64):m[RECORDS+i*160+0x72]=17
 for ordinal,index in enumerate(c.indices):
  m[RECORDS+(16+index)*160+0x72]=SELECTORS[ordinal]
 for p in(FLAGS,OTHER):
  for i in range(-32,33):put(m,p+i*4,0)
 for ordinal,index in enumerate(c.indices):
  value=((0,2,0x80000000,0xFFFFFFFE)[c.pattern%4]|((c.mask>>ordinal)&1))
  put(m,FLAGS+index*4,value);put(m,OTHER+index*4,u32(value^1))
 put(m,BASE,RECORDS+16*160);put(m,FLAGSP,FLAGS);put(m,COUNT,48)
 put(m,ACTOR+0x31C,ATTACH);m[ATTACH+0x120]=c.gate
 put(m,TICKS,c.ticks)
 for a,v in zip(COUNTERS,c.counters):put(m,a,v)
 return m

def observe(m):
 return tuple(read(m,a)for a in COUNTERS)+(read(m,TICKS),read(m,BASE),read(m,FLAGSP),
        bytes(m[ACTOR+i]for i in range(812)),bytes(m[ATTACH+i]for i in range(0x130)),
        bytes(m[FLAGS-128+i]for i in range(264)),bytes(m[OTHER-128+i]for i in range(264)))

def effect(m,c,t,args,ordinal):
 if t==LOOKUP:
  selector=args[0]&255;index=c.indices[SELECTORS.index(selector)]
  value=0 if c.missing else u32(read(m,BASE)+160*index+c.residual)
  if c.mode&1:put(m,BASE,read(m,BASE)+(160 if ordinal%2 else -160))
  if c.mode&2:put(m,FLAGSP,OTHER if read(m,FLAGSP)==FLAGS else FLAGS)
 elif t==INIT:
  put(m,ACTOR+0x20,0x13570000+ordinal)
  if c.mode&4:m[ATTACH+0x120]=255;put(m,TICKS,7)
  value=0x11223344
 elif t==SOUND:
  put(m,ACTOR+0x24,0x24680000+ordinal)
  if c.mode&8:
   for p in(FLAGS,OTHER):
    for index in c.indices:put(m,p+index*4,read(m,p+index*4)^1)
  value=0x80000000|ordinal
 elif t==EFFECT:put(m,ACTOR+0x28,0x35790000+ordinal);value=0xBEEF
 elif t==RESET:put(m,ACTOR+0x2C,0x468A0000+ordinal);value=0xCAFE
 elif t==STATE:put(m,ACTOR,args[1]);value=0xFFFFFFFF
 else:raise AssertionError(hex(t))
 return u32(value)

def reference(initial,c,connected=False):
 m=dict(initial);calls=[];observations=[];counts={}
 for a,k in zip(COUNTERS,(40,-66,-8,92)):put(m,a,read(m,a)+s32(read(m,TICKS))*k)
 def call(t,*args):
  args=tuple(map(u32,args));calls.append((t,args));observations.append(observe(m))
  counts[t]=counts.get(t,0)+1
  if t==LOOKUP and connected:
   selector=args[0]&255
   for i in range(max(0,s32(read(m,COUNT)))):
    p=read(m,BASE)+160*i
    if m[p+0x72]==selector:return p
   return 0
  return effect(m,c,t,args,counts[t])
 if m[read(m,ACTOR+0x31C)+0x120]==0:
  for selector in SELECTORS:
   record=call(LOOKUP,selector)
   index=div160(u32(record-read(m,BASE)))
   if read(m,u32(read(m,FLAGSP)+index*4))&1:
    if selector!=251:call(INIT,ACTOR)
    call(SOUND,0x627,ACTOR,0x7FFF,200,700)
    if selector==251:
     call(EFFECT,ACTOR,1,1,1,1,0,255,1);call(RESET,ACTOR);call(STATE,ACTOR,6)
 return m,calls,observations

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(c.unused,)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.counts={};self.observations=[]
 def record_call(self,t):
  assert t in COUNTS,hex(t)
  args=tuple(map(u32,self.arguments(COUNTS[t])))
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(observe(self.memory))
  self.counts[t]=self.counts.get(t,0)+1
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def public(m):return{a:v for a,v in m.items()if not STACK-0x400<=a<STACK+0x100}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.observations,m.current_pc,m.delay_of,m.condition)
def streams():
 ws=json.loads((out/'program.json').read_text());rom=(root/'conker/conker.us.bin').read_bytes()
 truth=list(struct.unpack_from('>149I',rom,0xFE340));assert ws==truth
 return ws,truth
def check(ws,c,connected=None):
 m=Oracle(ws,c,connected=connected).run()
 expected,calls,observations=reference(m.initial,c,connected=bool(connected))
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert public(m.memory)==public(expected),(c,'memory')
 assert m.observations==observations,(c,'boundary observations')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 assert read(m.memory,STACK+c.phase)==c.unused
 return m

def main():
 programs=streams();cases=[]
 for mask,gate,pattern,phase in itertools.product(range(16),(0,1,255),range(4),(0,8)):
  cases.append(Case(mask=mask,gate=gate,pattern=pattern,phase=phase))
 cases += [Case(gate=i,unused=u32(i*0x01010101))for i in range(256)]
 for ticks,indices,mode in itertools.product((0,1,-1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),
                  ((0,1,2,3),(-5,3,-1,4),(13,-13,7,-7),(0,0,0,0)),(0,1,2,4,8,15)):
  cases.append(Case(ticks=ticks,indices=indices,mode=mode,counters=(0x7FFFFFFF,0x80000000,0xFFFFFFFF,0)))
 cases += [Case(residual=i,indices=(-2,-1,0,1))for i in(-159,-1,1,159)]
 visits=set()
 for c in cases:
  a,b=[check(ws,c)for ws in programs];assert state(a)==state(b);visits.update(a.visits)
 faults=0
 for c in(Case(),Case(gate=1),Case(mode=15,phase=8),Case(mask=0)):
  m=check(programs[0],c)
  for cut in range(m.all_accesses):
   states=[]
   for ws in programs:
    a=Oracle(ws,c);a.cut=cut
    try:a.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(a))
   assert states[0]==states[1];faults+=1
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 p=elf_slot_offset(elf,LOOKUP,112);assert elf[p:p+112]==rom[0x141E5C:0x141ECC]
 lookup=dict(zip(range(LOOKUP,LOOKUP+112,4),struct.unpack_from('>28I',rom,0x141E5C)))
 connected=0;helper_visits=set()
 for mask,indices,phase in itertools.product(range(16),((0,1,2,3),(3,0,7,2),(31,17,9,24)),(0,8)):
  c=Case(mask=mask,indices=indices,phase=phase)
  a,b=[check(ws,c,lookup)for ws in programs];assert state(a)==state(b)
  helper_visits.update(a.visits);connected+=1
 standalone=0
 for selector,count in((0,48),(0x100,48),(17,48),(250,48),(251,48),(254,48),(250,0),(250,-1)):
  c=Case(indices=(0,1,2,31));memory=fixture(c);put(memory,COUNT,count)
  expected=0
  if selector&255:
   for i in range(max(count,0)):
    p=read(memory,BASE)+160*i
    if memory[p+0x72]==selector&255:expected=p;break
  m=Oracle(list(struct.unpack_from('>28I',rom,0x141E5C)),c,entry=LOOKUP,memory=memory,arguments=(selector,)).run()
  assert m.r[2]==expected and m.r[29]==STACK and m.r[16:24]==m.before[16:24]
  helper_visits.update(m.visits);standalone+=1
 missing_states=[]
 for ws in programs:
  m=Oracle(ws,Case(missing=True))
  try:m.run();raise AssertionError('missing-record contract control was ineffective')
  except AssertionError as e:assert 'unmapped read'in str(e),str(e)
  missing_states.append(state(m))
 assert missing_states[0]==missing_states[1]
 missed=[i for i in range(149)if ENTRY+4*i not in visits]
 report=dict(cases_per_stream=len(cases),streams=2,executed_target_words=149-len(missed),unexecuted_target_words=missed,
             original_lookup_connected_cases_per_stream=connected,lookup_words_executed=sum(LOOKUP+4*i in helper_visits for i in range(28)),
             lookup_words=28,standalone_lookup_cases=standalone,missing_record_guest_fault_control=True,
             access_fault_pairs=faults,all_256_gate_values=True,all_16_event_masks=True,
             mutable_provider_globals=True,signed_nonmultiple_division_guest_only=True,
             counter_overflow_guest_only=True,helper_effects_other_than_lookup_modeled=True,
             raw_and_retail_complete_states_equal=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
