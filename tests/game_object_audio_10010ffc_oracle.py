"""Affected Init caller model and original/raw execution qualification."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();out=root/"conker/build/game-actor-audio-15060778-match"
from tools.tests import game_actor_audio_handle_15060778_oracle as common, game_sound_slot_10010be8_oracle as alloc
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK

ENTRY,ACTOR,TABLE,RECORD,BUS,MARK=0x10010FFC,0x30000,0x800D1C90,0xB0000,0x80041FD9,0x60000
u32,s16,bits,floating=common.u32,common.s16,common.bits,common.floating
@dataclass(frozen=True)
class Case:
 handle:int=0xABCD1234
 sound:int=0x123
 volume:int=24000
 pitch:int=-100
 effect:int=17
 actor:int=ACTOR
 state:int=1
 camera:int=0
 identity:int=1
 height:int=80
 scale:int=0x3F800000
 coords:tuple=(0x41280000,0xC1CC0000,0x3F800000)
 bus:int=9
 created:int=0xFEDC
 mutation:int=0
 phase:int=0
 seed:int=0

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for base,n in((ACTOR,812),(TABLE,1024),(RECORD,256*44),(BUS,1),(MARK,32)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR,c.state);m[ACTOR+4]=c.identity;put(m,ACTOR+0x318,c.camera);put(m,ACTOR+0x14C,c.scale)
 for at,v in zip((20,24,28),c.coords):put(m,ACTOR+at,v)
 for i in range(256):put(m,TABLE+i*4,RECORD+i*44);put(m,RECORD+i*44+14,c.height,2)
 m[BUS]=c.bus&255
 for i,v in enumerate((c.effect,c.actor),4):put(m,STACK+c.phase+i*4,u32(v))
 return m

def reference(initial,c):
 m=dict(initial);calls=[]
 if not c.actor or read(m,c.actor)==0:return m,calls,0
 handle=c.handle&65535;volume=c.volume&65535
 if read(m,c.actor+0x318):t=common.CREATE;a=(handle,c.sound,volume,64,s16(c.pitch),c.effect,c.bus)
 else:
  volume=(3*volume>>2)&65535;identity=m[c.actor+4]
  scale=floating(bits(float(read(m,read(m,TABLE+identity*4)+14,2))))*floating(read(m,c.actor+0x14C))if identity!=255 else 0.0
  scale=floating(bits(scale))
  if scale>256.0:scale=1.0
  elif scale<80.0:scale=0.3125
  else:scale=floating(bits(scale*0.00390625))
  far=math.trunc(floating(bits(2000.0*scale)))+501
  coords=tuple(u32(math.trunc(floating(read(m,c.actor+at))))for at in(20,24,28))
  t=common.POSITION;a=(handle,c.sound,volume,s16(c.pitch),c.effect,0,*coords,500,far)
 a=common.canonical(t,a);calls.append((t,a));answer=common.provider(m,c,t,a)&65535
 return m,calls,answer

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c):
  self.c=c;super().__init__(words,memory,c,entry=ENTRY,arguments=(u32(c.handle),u32(c.sound),u32(c.volume),u32(c.pitch)))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(common.CREATE,common.POSITION),hex(t)
  a=common.canonical(t,tuple(map(u32,self.arguments(common.COUNTS[t]))));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  value=common.provider(self.memory,self.c,t,self.calls[-1][1])
  for i in range(max(4,common.COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def cases():
 cs=[Case(actor=0),Case(state=0)]
 for camera,height,scale,volume in itertools.product((0,1),(0,1,79,80,81,255,256,257,65535),(bits(-1.),bits(0.),bits(.5),bits(1.),bits(2.)),(0,1,99,100,65535)):
  cs.append(Case(camera=camera,height=height,scale=scale,volume=volume))
 for value in(0x429FFFFF,0x42A00000,0x42A00001,0x437FFFFF,0x43800000,0x43800001):cs.append(Case(height=1,scale=value))
 for field,values in{'handle':(0,1,65535,0xFFFF0000,0xABCDFFFF),'pitch':(-32769,-32768,32767,32768),'effect':(0,255,0x12340081),'created':(0,1,65535),'identity':(0,186,187,254,255),'state':(0,1,0x80000000,0xFFFFFFFF),'sound':(0,0x7FFF,0x80000000)}.items():
  for v,camera in itertools.product(values,(0,1)):cs.append(replace(Case(camera=camera),**{field:v}))
 for byte in range(256):cs.append(Case(camera=1,bus=byte,effect=byte))
 for f in(-32768.75,-32768.,-.75,-0.,0.,.75,32767.,32767.75):cs.append(Case(coords=(bits(f),bits(-.75),bits(1.))))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]

def native_cases():return[c for c in cases()if c.identity<187 or c.identity==255]

def check(m,c):
 expected,calls,answer=reference(m.initial,c)
 assert m.calls==calls,('calls',c,m.calls,calls)
 assert common.public(m.memory)==common.public(expected),('public-memory',c)
 assert m.r[2]==answer,('return',c,m.r[2],answer)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('saved-ABI',c)

def main():
 cs=cases();s=alloc.symbols();rom=(root/'conker/conker.us.bin').read_bytes();programs={'before':alloc.words(out/'public-audit/init-before.o',s,'func_10010FFC'),'proposed':alloc.words(out/'public-audit/init-proposal.o',s,'func_10010FFC'),'retail':list(struct.unpack('>115I',rom[0x10FFC:0x111C8]))};coverage={};missing={}
 for label,ws in programs.items():
  seen=set()
  for c in cs:
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  coverage[label]=len(seen&set(range(ENTRY,ENTRY+460,4)));missing[label]=[(pc-ENTRY)//4 for pc in range(ENTRY,ENTRY+460,4)if pc not in seen]
 r=dict(cases_per_body=len(cs),executions=len(cs)*len(programs),coverage=coverage,missing=missing,native_defined_cases=len(native_cases()),upper_handle_bits=True,scale_thresholds=True,all_bus_bytes=True,indirect_table_ids_187_to_254_guest_only=True,programs_bound_once=True)
 (out/'caller-guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
