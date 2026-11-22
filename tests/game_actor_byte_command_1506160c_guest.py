"""Byte-command priority, packed gates, access order and incoming o32 homes."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY=0x1506160C;ACTOR=0x30000;GATES=0x800DBFF4;SIZE=0x400
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 command:int=2
 first:int=0xAB
 second:int=0xCD
 slot:int=0
 priority:int=0
 flags:int=0xA5
 forced:int=0
 gates:tuple=(0,0,0,0)
 phase:int=0
 seed:int=0
def arguments(c):return(ACTOR,u32(c.command),u32(c.first),u32(c.second),u32(c.slot))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-64,128)}
 m.update({ACTOR+i:(i*19+0xA5+c.seed)&255 for i in range(-16,SIZE+16)})
 m.update({GATES+i:((i*23+c.seed)&255)if i>=4 else c.gates[i] for i in range(256)})
 m[ACTOR+0xA]=c.priority;m[ACTOR+0xF]=c.flags;m[ACTOR+0x2FD]=c.forced
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-64<=a<STACK+128}
def reference(initial,c):
 m=dict(initial);command,first,second,slot=(x&255 for x in(c.command,c.first,c.second,c.slot))
 f=ACTOR+0xF;selected=ACTOR+0xB+slot
 if command>=8:
  mask=1<<(slot&31)
  if command==10:
   m[f]=(m[f]|u32(mask<<4))&255;first=0
  else:
   if command==8:m[f]=(m[f]|mask)&255;first=0
   else:m[f]=(m[f]&~mask)&255;first=255
   high=u32(mask<<4)
   if m[f]&high:m[selected]=first
   m[f]&=(~high)&255
  if m[ACTOR+0x2FD]or m[GATES+slot]:m[selected]=first
 else:
  if command<m[ACTOR+0xA]:return m
  # Independent command table describes only the fields written by each mode.
  updates={1:{0xA:0,7:first,8:first},2:{0xA:2,8:first,9:second},
           4:{0xA:4,7:0,8:255,9:32},5:{0xA:5,8:0,9:32},6:{0xA:6,8:0,9:8}}
  for offset,value in updates.get(command,{}).items():m[ACTOR+offset]=value
  if read(m,GATES):m[ACTOR+7]=m[ACTOR+8]
 return m
class Oracle(FactoryOracle):
 def __init__(self,ws,c,entry=ENTRY,connected=None,memory=None,args=None):
  self.c=c
  super().__init__(ws,fixture(c)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==39:
   self.r[w>>11&31]=u32(~(self.r[w>>21&31]|self.r[w>>16&31]));self.r[0]=0
  else:super().execute(w)
 def record_call(self,target):
  assert target==ENTRY,hex(target);a=tuple(map(u32,self.arguments(5)));self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):raise AssertionError(('unexpected opaque helper',hex(target)))
@lru_cache(maxsize=1)
def streams():
 raw=json.loads((out/'high-mask/words.json').read_text());truth=list(struct.unpack_from('>108I',(root/'conker/conker.us.bin').read_bytes(),0x8EABC));assert raw==truth
 return raw,truth
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of)
def check(ws,c):
 m=Oracle(ws,c).run();assert public(m.memory)==public(reference(m.initial,c)),c
 assert not m.calls and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f==m.before_f,c
 return m
def cases():
 for command,slot,priority,forced,gate in itertools.product(range(256),range(4),(0,255),(0,1),(0,1)):
  yield Case(command=command,slot=slot,priority=priority,forced=forced,gates=tuple(gate if i==slot else 0 for i in range(4)))
 for command,flags,slot in itertools.product((8,9,10),range(256),range(4)):yield Case(command=command,flags=flags,slot=slot)
 for command,priority,gates in itertools.product(range(8),range(256),((0,0,0,0),(0,0,0,1))):yield Case(command=command,priority=priority,gates=gates)
 for command,slot,flags,forced,phase in itertools.product((8,9,10),range(256),(0,255),(0,1),(0,8)):
  yield Case(command=command,slot=slot,flags=flags,forced=forced,phase=phase)
 for command,first,second,slot in itertools.product((0xFFFFFF08,0x12340002,0x8000000A),(0x123456AB,0xFFFFFFFF),(0x876543CD,0x80000000),(0x11223300,0xFFFFFFFF)):
  yield Case(command=command,first=first,second=second,slot=slot,forced=1)
def main():
 count=0;visits=set()
 for c in cases():
  a,b=[check(ws,c)for ws in streams()];assert state(a)==state(b);visits.update(a.visits);count+=1
 # Retail contains one duplicated comparison unreachable from either predecessor.
 missed=[i for i in range(108)if ENTRY+4*i not in visits]
 faults=0
 for c in(Case(command=4,gates=(0,0,0,1)),Case(command=2,priority=255),Case(command=8,slot=4,flags=255,forced=1),Case(command=9,slot=3,flags=255),Case(command=10,slot=255,phase=8)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   pair=[]
   for ws in streams():
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:pass
    pair.append(state(m))
   assert pair[0]==pair[1];faults+=1
 r=dict(cases_per_stream=count,streams=2,body_words=108,frame=0,target_executed_words=108-len(missed),unexecuted_indices=missed,
  access_fault_pairs=faults,all_256_commands_flags_priorities_and_guest_slots=True,high_input_bits_narrowed=True,
  incoming_o32_argument_homes_preserved=True,slot4_flag_alias_guest_only=True,slots_above3_guest_only=True,
  native_domain='High commands use slots0..3; guest execution additionally qualifies the retail masked shift and surrounding RDRAM accesses.',source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
