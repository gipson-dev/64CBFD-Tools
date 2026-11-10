"""Sound-slot allocation model; current/proposed C and original MIPS compared."""
import itertools,json,struct,subprocess,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();out=root/"conker/build/game-actor-audio-15060778-match"
from tools.tests import game_actor_audio_handle_15060778_oracle as common
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY,TABLE,BANK,MIX,VOICE,OTHER,NEWVOICE,MARK=0x10010BE8,0x800425E0,0x8003E368,0x80041FD8,0x90000,0xA1000,0xA2000,0x60000
ACTIVE,STOP,RATIO,PLAY=0x100173C4,0x10017594,0x10019AB0,0x10017438
COUNTS={ACTIVE:1,STOP:1,RATIO:1,PLAY:8}
u32,s16,signed=common.u32,common.s16,common.signed

@dataclass(frozen=True)
class Case:
 handle:int=0x1235
 sound:int=0x123
 volume:int=24000
 pan:int=64
 cents:int=-100
 mix:int=17
 bus:int=1
 global_mix:int=9
 occupied:int=0
 active:int=0
 reserved:int=0
 matching:bool=True
 generation:int=0x1230
 mutation:int=0
 phase:int=0
 seed:int=0

def fixture(c):
 assert not (STACK-2048 <= VOICE+4095 and VOICE < STACK+2304)
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for base,n in((TABLE,192),(BANK,4),(MIX,1),(VOICE,4096),(OTHER,256),(NEWVOICE,256),(MARK,32)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for i in range(16):
  p=TABLE+i*12;put(m,p,0x100+i,2);put(m,p+2,c.generation+i*16,2);put(m,p+4,0x8000 if c.reserved>>i&1 else 0,2);put(m,p+8,VOICE+i*256 if c.occupied>>i&1 else 0)
 p=TABLE+(c.handle&15)*12;put(m,p,c.handle if c.matching else(c.handle^0x10),2);put(m,BANK,0x70000);m[MIX]=c.global_mix&255
 for i,v in enumerate((c.cents,c.mix,c.bus),4):put(m,STACK+c.phase+i*4,u32(v))
 return m

def public(m):return common.public(m)

def canonical(t,a):
 a=list(map(u32,a))
 if t==RATIO:a[0]=u32(signed(a[0]))
 if t==PLAY:
  a[1]=u32(s16(a[1]));a[2]&=65535;a[3]&=255;a[5]&=255;a[6]&=255
 return tuple(a)

def provider(m,c,t,a):
 put(m,MARK,read(m,MARK)+1)
 if t==ACTIVE:
  i=(a[0]-TABLE-8)//12;assert 0<=i<16
  value=1 if c.active>>i&1 else 0
  if c.mutation&1:put(m,TABLE+i*12+4,read(m,TABLE+i*12+4,2)^0x8000,2)
  if c.mutation&2:put(m,a[0],OTHER)
  if c.mutation&4:m[MIX]^=255
  return value
 if t==STOP:
  m[a[0]+0x40]^=0x55
  if c.mutation&8:m[MIX]=(m[MIX]+1)&255
  return 0xDEADBEEF
 if t==RATIO:
  if c.mutation&16:put(m,BANK,0x71000);m[MIX]^=255
  return 0x3F123456 if a[0]&1 else 0x3FA54321
 assert t==PLAY
 put(m,a[7],NEWVOICE)
 if c.mutation&16:put(m,a[7]-6,0xDEAD,2)
 return 0xBAD00BAD

def reference(initial,c):
 m=dict(initial);calls=[];handle=c.handle&65535;i=handle&15;slot=TABLE+12*i
 def call(t,*a):
  a=canonical(t,a);calls.append((t,a));return provider(m,c,t,a)
 def busy(p):return read(m,p+8)!=0 and call(ACTIVE,p+8)!=0
 if read(m,slot,2)==handle and handle:
  if busy(slot):call(STOP,read(m,slot+8));put(m,slot+8,0)
 elif busy(slot)or read(m,slot+4,2)&0x8000:
  i=0;slot=TABLE
  if busy(slot)or read(m,slot+4,2)&0x8000:
   for i in range(1,16):
    slot=TABLE+12*i
    if not busy(slot)and not(read(m,slot+4,2)&0x8000):break
   else:i=16
 if c.volume&65535<100 or i>=16 or u32(c.sound)==0 or(u32(c.sound)&0x7FFF)>=0x6E3:return m,calls,0
 slot=TABLE+12*i;answer=read(m,slot+2,2);n=(answer+16)&65535
 if n<16:n+=16
 put(m,slot,answer,2);put(m,slot+2,n,2);put(m,slot+4,c.sound,2)
 if read(m,slot+8):m[read(m,slot+8)+0x54]=5
 mix=c.mix&255;g=m[MIX]
 mix=(mix+g)&255 if(mix&127)+g<128 else mix|127
 pitch=call(RATIO,s16(c.cents))
 call(PLAY,read(m,BANK),s16(c.sound&0x7FFF),c.volume&65535,c.pan&255,pitch,mix,c.bus&255,slot+8)
 return m,calls,answer

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY):
  self.c=c;super().__init__(words,memory,c,entry=entry,arguments=(u32(c.handle),u32(c.sound),u32(c.volume),u32(c.pan)))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.raw_calls=[]
 def record_call(self,t):
  assert t in COUNTS,hex(t)
  a=tuple(map(u32,self.arguments(COUNTS[t])));self.raw_calls.append((t,a));a=canonical(t,a);self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  value=provider(self.memory,self.c,t,self.calls[-1][1])
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t==RATIO:self.f[0]=value;self.r[2]=0xCAFE0000
  else:self.r[2]=value

def symbols():
 s={}
 for line in subprocess.check_output(['mips-linux-gnu-nm','-n',str(root/'conker/build/conker.us.elf')],text=True).splitlines():
  v=line.split()
  if len(v)==3:
   try:s[v[2]]=int(v[0],16)
   except ValueError:pass
 assert s['alCents2Ratio']==RATIO
 return s

def words(path,s,name='func_10010BE8'):
 t,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};return bound_blob(t[a:a+n],refs,s)

def cases():
 cs=[]
 for i,matching,occupied,active,reserved,mutation in itertools.product(range(16),(False,True),(0,0xFFFF),(0,0xFFFF),(0,0xFFFF),(0,1,2,4,8,16)):
  cs.append(Case(handle=0x100+i,matching=matching,occupied=occupied,active=active,reserved=reserved,mutation=mutation))
 for free in range(16):
  cs.append(Case(handle=0x123F,matching=False,occupied=65535,active=65535,reserved=65535^(1<<free)))
  cs.append(Case(handle=0x123F,matching=False,occupied=65535,active=65535^(1<<free),reserved=0))
  cs.append(Case(handle=0x123F,matching=False,occupied=65535^(1<<free),active=65535,reserved=0))
 for field,values in {'handle':(0,1,15,16,65535,0xABCD1235,0xFFFF0000),'sound':(0,1,0x6E2,0x6E3,0x7FFF,0x8000,0x8001,0x80000000,0xFFFFFFFF),'volume':(0,1,99,100,65535,0x1234FFFF),'pan':(0,127,128,255,0x12340081),'cents':(-32769,-32768,0,32767,32768,0x12348000),'mix':(0,1,126,127,128,129,255,0x12340081),'bus':(0,255,0x12340081),'global_mix':(0,1,126,127,128,255),'generation':(0,1,15,16,0xFFEF,0xFFF0,0xFFFF)}.items():
  for value in values:cs.append(replace(Case(occupied=65535,active=0),**{field:value}))
 for byte in range(256):
  cs.append(Case(mix=byte,global_mix=17));cs.append(Case(mix=129,global_mix=byte))
 for generation in(0,1,15,16,0xFFEF,0xFFF0,0xFFFF):cs.append(Case(handle=0x1000,generation=generation))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]

def check(m,c,homes=True):
 expected,calls,answer=reference(m.initial,c)
 assert m.calls==calls,('calls',c,m.calls,calls)
 assert public(m.memory)==public(expected),('public-memory',c)
 assert m.r[2]==answer,('return',c,m.r[2],answer)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('saved-ABI',c)
 if homes:
  home=STACK+c.phase
  for i,v in enumerate((c.handle,c.sound,c.volume,c.pan)):assert read(m.memory,home+4*i)==u32(v),('argument-home',c,i)
  assert all(m.memory[home+i]==m.initial[home+i]for i in range(16,32)),('stack-args',c)

def main():
 cs=cases();s=symbols();rom=(root/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack('>164I',rom[0x10BE8:0x10E78]));programs={'proposed':words(out/'public-audit/init-proposal.o',s),'before':words(out/'public-audit/init-before.o',s),'retail':retail};coverage={};missing={}
 for label,ws in programs.items():
  seen=set()
  for c in cs:
   m=Oracle(ws,fixture(c),c);m.run();check(m,c,homes=label!='before');seen.update(m.visits)
  coverage[label]=len(seen&set(range(ENTRY,ENTRY+656,4)))
  missing[label]=[(pc-ENTRY)//4 for pc in range(ENTRY,ENTRY+656,4)if pc not in seen]
 r=dict(cases_per_body=len(cs),executions=len(cs)*len(programs),coverage=coverage,missing=missing,all_slots_and_scan_failures=True,generation_wrap=True,all_mix_and_global_mix_bytes=True,upper_handle_bits=True,callback_mutations=True,programs_bound_once=True,helper_algorithms_qualified=False)
 (out/'init-guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
