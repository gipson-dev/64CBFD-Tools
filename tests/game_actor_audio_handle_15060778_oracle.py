"""Independent actor-audio model and guest call-clobber qualification."""
import itertools,json,math,struct,sys,subprocess
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();out=root/"conker/build/game-actor-audio-15060778-match"
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY=0x15060778;ACTOR=0x30000;MARK=0x60000
QUERY,UPDATE,SPATIAL,CREATE,POSITION=0x1001147C,0x1000F85C,0x1000F91C,0x10010BE8,0x10010E78
COUNTS={QUERY:1,UPDATE:3,SPATIAL:10,CREATE:7,POSITION:11}
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
s16=lambda v:((v&65535)^32768)-32768
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
floating=lambda i:struct.unpack('>f',struct.pack('>I',i))[0]

@dataclass(frozen=True)
class Case:
 sound:int=0x123
 volume:int=0x5DC0
 pitch:int=-100
 near:int=500
 far:int=2500
 flags:int=3
 handle1:int=0x1234
 handle2:int=0x4321
 material:int=0x180
 actor_pitch:int=7
 coords:tuple=(0x41280000,0xC1CC0000,0x3F800000)
 query:int=0x123
 created:int=0xFEDC
 mutation:int=0
 phase:int=0
 seed:int=0
 actor:int=ACTOR

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for base,n in ((ACTOR,812),(MARK,32)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR+0x8C,c.handle1,2);put(m,ACTOR+0x8E,c.handle2,2);put(m,ACTOR+0x184,c.material);m[ACTOR+0x13F]=c.actor_pitch
 for at,v in zip((20,24,28),c.coords):put(m,ACTOR+at,v)
 for i,v in enumerate((c.near,c.far,c.flags),4):put(m,STACK+c.phase+i*4,u32(v))
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}

def canonical(t,a):
 a=list(a)
 if t==QUERY:a[0]&=65535
 elif t==UPDATE:a[0]&=65535;a[1]=u32(s16(a[1]))
 elif t==SPATIAL:
  a[0]&=65535;a[1]&=65535;a[2]=u32(s16(a[2]));a[3]&=255
  for i in range(5,10):a[i]=u32(s16(a[i]))
 elif t==CREATE:
  a[0]&=65535;a[2]&=65535;a[3]&=255;a[4]=u32(s16(a[4]));a[5]&=255;a[6]&=255
 elif t==POSITION:
  a[0]&=65535;a[2]&=65535;a[3]=u32(s16(a[3]));a[4]&=255
  for i in range(6,11):a[i]=u32(s16(a[i]))
 else:raise AssertionError(hex(t))
 return tuple(map(u32,a))

def provider(m,c,t,a):
 # Effects are deliberately opaque helper fixtures; they do not recover the helpers.
 put(m,MARK,read(m,MARK)+1)
 if t==QUERY and c.mutation:
  put(m,ACTOR+0x8C,0xBEEF,2);put(m,ACTOR+0x8E,0xCAFE,2)
  put(m,ACTOR+0x184,0x80);m[ACTOR+0x13F]=255
  for at,v in zip((20,24,28),(bits(-32768.75),bits(32767.75),bits(-0.75))):put(m,ACTOR+at,v)
 if t==UPDATE and a[1]==16 and c.mutation:
  put(m,ACTOR+0x184,0);m[ACTOR+0x13F]=1
 return u32(c.query)if t==QUERY else c.created&65535 if t in(CREATE,POSITION)else 0xDEADBEEF

def reference(initial,c):
 m=dict(initial);calls=[];mode=c.flags&3;slot=0;handle=0
 effect=0 if c.flags&8 else (read(m,c.actor+0x184)>>3)&0x30
 if mode==1:slot=c.actor+0x8C
 elif mode in(2,3):slot=c.actor+0x8E
 if slot:handle=read(m,slot,2)
 def call(t,*a):
  a=canonical(t,a);calls.append((t,a));return provider(m,c,t,a)
 def coords():return tuple(u32(math.trunc(floating(read(m,c.actor+at))))for at in(20,24,28))
 sound=u32(c.sound);volume=c.volume&65535
 if mode==3:
  found=call(QUERY,handle)
  if found==sound:
   if c.flags&4:call(SPATIAL,handle,volume+effect*50,u32(c.pitch+m[c.actor+0x13F]*10),effect,0,*coords(),c.near,c.far)
   else:call(UPDATE,handle,16,c.pitch);call(UPDATE,handle,8,volume+effect*50)
   return m,calls,sound
  sound|=0x8000
 if c.flags&4:answer=call(POSITION,handle,sound,volume+effect*50,c.pitch,effect,0,*coords(),c.near,c.far)
 else:answer=call(CREATE,handle,sound,volume+effect*50,64,c.pitch,effect,1)
 if slot:put(m,slot,answer,2)
 return m,calls,sound

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,connected=None):
  self.c=c;super().__init__(words,memory,c,entry=entry,arguments=(u32(c.sound),c.actor,u32(c.volume),u32(c.pitch)),connected=connected)
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.raw_calls=[]
 def execute(self,w):
  if w>>26==0 and w&63==0x26:
   self.r[w>>11&31]=u32(self.r[w>>21&31]^self.r[w>>16&31]);self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in COUNTS,hex(t)
  a=tuple(map(u32,self.arguments(COUNTS[t])));self.raw_calls.append((t,a));a=canonical(t,a);self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  value=provider(self.memory,self.c,t,self.calls[-1][1])
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def words(path,name= 'func_15060778'):
 t,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};syms={}
 for vs in refs.values():
  for _,name in vs:syms[name]=int(name.split('_')[1],16)
 return bound_blob(t[a:a+n],refs,syms)

def cases():
 cs=[]
 for flags,match,mut in itertools.product(range(256),(False,True),(0,1)):
  cs.append(Case(flags=flags,query=0x123 if match else -1,mutation=mut,volume=65535 if flags&16 else 24000))
 for field,values in {'sound':(0,1,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF),'volume':(0,1,99,100,65535,0x1234FFFF),'pitch':(-32769,-32768,32767,32768,0x7FFF0000,-0x7FFF0000),'handle1':(0,15,16,65535),'handle2':(0,15,16,65535),'material':(0,0x80,0x100,0x180,0xFFFFFFFF),'actor_pitch':(0,1,255),'created':(0,1,65535),'near':(-32769,-32768,32767,32768),'far':(-32769,-32768,32767,32768)}.items():
  for value,flags in itertools.product(values,(0,1,2,3,4,5,6,7)):
   cs.append(replace(Case(flags=flags),**{field:value}))
 for i in range(3):
  for f in(-2147483648.,-65536.75,-32768.75,-0.0,0.0,0.75,32767.75,65535.75,2147483520.):
   xyz=list(Case().coords);xyz[i]=bits(f)
   for flags in(4,7):cs.append(Case(flags=flags,coords=tuple(xyz)))
 cs.append(Case(actor=0,flags=8))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]

def check(m,c):
 expected,calls,sound=reference(m.initial,c)
 assert m.calls==calls,('calls',c,m.calls,calls)
 assert public(m.memory)==public(expected),('public-memory',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('saved-ABI',c)
 home=STACK+c.phase
 assert read(m.memory,home)==sound,('sound-home',c,hex(read(m.memory,home)),hex(sound))
 assert read(m.memory,home+8)==u32(c.volume)and read(m.memory,home+12)==u32(c.pitch),('argument-homes',c)
 assert all(m.memory[home+i]==m.initial[home+i]for i in range(4,8)),('actor-home',c)
 assert all(m.memory[home+i]==m.initial[home+i]for i in range(16,32)),('stack-args',c)

def main():
 cs=cases();retail=list(struct.unpack('>174I',(root/'conker/conker.us.bin').read_bytes()[0x8DC28:0x8DEE0]));programs={'raw':words(out/'public-audit/game-proposal.o'),'retail':retail};coverage={};traces=0
 for label,ws in programs.items():
  seen=set()
  for c in cs:
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  coverage[label]=len(seen&set(range(ENTRY,ENTRY+696,4)))
 r=dict(cases_per_body=len(cs),executions=len(cs)*len(programs),coverage=coverage,all_flag_bytes=True,helper_clobbers=True,late_actor_mutations=True,full_volume_overflow=True,programs_bound_once=True,NaN_Inf_invalid_float_conversion_qualified=False)
 (out/'audio-guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
