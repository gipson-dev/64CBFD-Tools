"""Independent water/stun branches, callback effects and the retail mixed-float ABI."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_water_stun_150585f0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_water_stun_150585f0_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS;ACTOR=0x20000;CHILDREN=(0x50000,0x51000)
CALL_NAMES=('func_1505A3A8','func_1505E874','func_1506B078','func_150599C8');FLOAT_GLOBALS=('D_80099478','D_8009947C','D_80099480','D_80099484')
frozen=(out/'frozen'/qualify.ELF).read_bytes();DEFAULTS={n:struct.unpack_from('>I',frozen,qualify.elf_slot_offset(frozen,int(n.split('_')[1],16),4))[0]for n in FLOAT_GLOBALS}
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
same=lambda a,b:a==b or math.isnan(floating(a))and math.isnan(floating(b))
@dataclass(frozen=True)
class Case:
 state:int=1
 water:int=1
 stun:int=2
 health:int=1
 timer:int=3
 delta:int=1
 scale_byte:int=127
 y:int=0x41C80000
 level:int=0x42C80000
 yvel:int=0x41A00000
 speed:int=0x40A00000
 xzvel:int=0x41200000
 history:int=0xC1200000
 flags:int=0xA5A58100
 recovery_flags:int=0
 heading:int=0x8123
 saved:int=0xF088
 carry:int=5
 child:int=1
 gate:int=1
 resource:int=0xAB
 effects:int=0
 alias:int=0
 unused_argument:int=0x3E800000
 phase:int=0
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((ACTOR,812),*((p,512)for p in CHILDREN)):
  for i in range(-16,n+16):m[base+i]=(i*29+0x59)&255
 for name in(*FLOAT_GLOBALS,'D_800CC264','D_800BE616','D_800C3E78'):
  for i in range(-16,32):m.setdefault(s[name]+i,(i*13+0xA5)&255)
 put(m,ACTOR,c.state);put(m,ACTOR+244,c.flags);put(m,ACTOR+248,0xA5A5FFFF)
 for off,v in((24,c.y),(32,c.yvel),(36,bits(3.)),(40,c.speed),(60,c.xzvel),(184,bits(7.)),(280,c.level),(460,c.history)):put(m,ACTOR+off,v)
 for off,v in((118,c.heading),(120,0x1324),(122,c.saved),(268,c.timer),(540,0x8142)):put(m,ACTOR+off,v,2)
 for off,v in((128,0x71),(129,0x83),(131,0x95),(173,c.water),(260,c.stun),(265,c.scale_byte),(267,c.recovery_flags),(458,c.health),(568,c.carry),(570,0xA7)):m[ACTOR+off]=v
 child=CHILDREN[c.child-1]if c.child else 0
 if c.alias:child=(ACTOR+260, s['D_800C3E78'],ACTOR+173)[c.alias-1]-125
 put(m,ACTOR+796,child);put(m,s['D_800CC264'],c.delta,2);m[s['D_800BE616']]=c.gate;m[s['D_800C3E78']]=c.resource
 for n,v in DEFAULTS.items():put(m,s[n],v)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def digest(m,s=SYMS):
 h=2166136261
 for base,n in((ACTOR,812),*((p,512)for p in CHILDREN),*((s[n],4)for n in FLOAT_GLOBALS),(s['D_800CC264'],2),(s['D_800BE616'],1),(s['D_800C3E78'],1)):
  for i in range(n):h=((h^m[base+i])*16777619)&0xFFFFFFFF
 return h
def effect(m,c,kind,s=SYMS):
 if c.effects&1:
  m[ACTOR+173]=1;m[ACTOR+260]=0 if kind else 1;m[ACTOR+458]=1;put(m,ACTOR,1)
 if c.effects&2:
  for n,v in zip(FLOAT_GLOBALS,(bits(-2.),bits(500.),bits(.5),bits(100.))):put(m,s[n],v)
  put(m,s['D_800CC264'],-1,2);m[s['D_800BE616']]=0;m[s['D_800C3E78']]=0x31
 if c.effects&4:
  put(m,ACTOR+268,-3,2);put(m,ACTOR+796,CHILDREN[1]);m[ACTOR+260]=0 if kind else 0xFE
 if c.effects&8:
  put(m,ACTOR+24,bits(70.));put(m,ACTOR+32,bits(-5.));put(m,ACTOR+122,0xCDEF,2);m[ACTOR+267]=4;m[ACTOR+568]=9 if kind==2 else 7
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);calls=[];obs=[]
 def call(kind,args):calls.append((s[CALL_NAMES[kind]],args));obs.append(digest(m,s));effect(m,c,kind,s)
 def f(off):return floating(read(m,ACTOR+off))
 def storef(off,v):put(m,ACTOR+off,bits(v))
 scale=bits(float(m[ACTOR+265])*floating(read(m,s['D_80099478'])));call(0,(0,ACTOR,0x3F800000,scale,0))
 if f(460)<floating(read(m,s['D_8009947C'])):put(m,ACTOR+460,read(m,ACTOR+24))
 if 0<m[ACTOR+173]<10:
  storef(36,0.)
  if f(32)<60.:storef(32,f(32)*floating(read(m,s['D_80099480'])))
  threshold=bits(floating(bits(f(280)-60.))+40.)
  if floating(threshold)<f(24):
   for off in(129,131,173):m[ACTOR+off]=0
   storef(184,0.);storef(36,4.)
 if not m[s['D_800BE616']]or read(m,ACTOR)!=1:put(m,ACTOR+540,0,2)
 stun=m[ACTOR+260]
 if stun!=255:
  if stun!=254 and(m[ACTOR+458]or read(m,ACTOR)!=1):m[ACTOR+260]=(stun-1)&255
  put(m,ACTOR+268,s16(read(m,ACTOR+268,2))-s16(read(m,s['D_800CC264'],2)),2)
  if f(40)<floating(read(m,s['D_80099484']))and read(m,ACTOR+244)&0x100:put(m,ACTOR+268,0,2)
  if s16(read(m,ACTOR+268,2))<=0:
   child=read(m,ACTOR+796)
   if child:m[child+125]=0
   put(m,ACTOR+268,0,2);call(1,(m[s['D_800C3E78']],ACTOR))
  if not m[ACTOR+260]:
   heading=read(m,ACTOR+122,2);storef(60,0.);m[ACTOR+129]=0;put(m,ACTOR+120,heading,2);put(m,ACTOR+118,heading,2)
   if m[ACTOR+173]:
    storef(32,0.)
    if read(m,ACTOR)==1:call(2,())
   elif read(m,ACTOR)==1:put(m,ACTOR+248,read(m,ACTOR+248)&0xFFFF7FFF);storef(36,4.)
   if m[ACTOR+568]:m[ACTOR+570]=m[ACTOR+568]
  elif not m[ACTOR+267]&2:
   heading=read(m,ACTOR+118,2)^(0x8000 if m[ACTOR+267]&4 else 0);m[ACTOR+128]=10;call(3,(ACTOR,12,heading))
 return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,c.unused_argument));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];frame=(-words[0])&65535;self.argument_home_store=(0xAFA50000|(frame+4))in words[:20]
 def record_call(self,t):
  assert t in[self.syms[n]for n in CALL_NAMES],hex(t);kind=[self.syms[n]for n in CALL_NAMES].index(t)
  if kind==0:args=(self.f[12],self.r[5],self.r[6],self.r[7],self.get(self.r[29]+16,4))
  elif kind==1:args=(self.r[4]&255,self.r[5])
  elif kind==2:args=()
  else:args=(self.r[4],self.r[5]&255,self.r[6]&65535)
  self.calls.append((t,args));self.observations.append(digest(self.memory,self.syms));self.events.append(('CALL',t,args))
 def hook(self,t):
  kind=[self.syms[n]for n in CALL_NAMES].index(t);effect(self.memory,self.case,kind,self.syms)
  for i in range(5 if kind==0 else 4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xA5;self.hi,self.lo=0xA5000010,0xA5000011
def words(p,s=SYMS):return bound_blob(*qualify.payload(p),s)
def check(m,c=Case(),s=SYMS):
 want,calls,obs=reference(m.initial,c,s);assert len(m.calls)==len(calls),('count',c,m.calls,calls)
 for a,b in zip(m.calls,calls):assert a[0]==b[0]and len(a[1])==len(b[1])and all(same(x,y)for x,y in zip(a[1],b[1])),('ABI',c,a,b)
 assert m.observations==obs,('snapshots',c,m.observations,obs)
 assert public(m.memory)==public(want),('public',c,[(hex(p),v,want.get(p))for p,v in public(m.memory).items()if want.get(p)!=v][:6])
 home=STACK+c.phase+4
 assert all(m.memory[p]==v for p,v in m.initial.items()if STACK+c.phase<=p<STACK+c.phase+512 and not(m.argument_home_store and home<=p<home+4))
 if m.argument_home_store:assert read(m.memory,home)==c.unused_argument
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[Case()]
 for stun,water in itertools.product((0,1,2,127,253,254,255),(0,1,9,10,255)):result.append(replace(Case(),stun=stun,water=water))
 for state,health,gate in itertools.product((0,1,2,0xFFFFFFFF),(0,1),(0,1)):result.append(replace(Case(),state=state,health=health,gate=gate))
 for state,water,carry in itertools.product((0,2,0xFFFFFFFF),(0,1),(0,5)):result.append(replace(Case(),state=state,water=water,carry=carry,stun=1))
 for timer,delta in itertools.product((0,1,2,0x7FFF,0x8000,0xFFFF),(0,1,0x7FFF,0x8000,0xFFFF)):result.append(replace(Case(),timer=timer,delta=delta))
 for v in(0,0x80000000,0x426FFFFF,0x42700000,0x42700001,0x7F800000,0xFF800000,0x7FC12345):result.append(replace(Case(),yvel=v))
 for v in(0x429FFFFF,0x42A00000,0x42A00001,0x7F800000,0xFF800000,0x7FC12345):result.append(replace(Case(),y=v))
 for v in(0,0x7F800000,0xFF800000,0x7FC12345):result.append(replace(Case(),history=v))
 threshold=floating(DEFAULTS['D_80099484'])
 for v,flags in itertools.product((bits(threshold-1.),bits(threshold),bits(threshold+1.),0x7FC12345,0x7F800000,0xFF800000),(0,0x100)):result.append(replace(Case(),speed=v,flags=flags))
 for flags,heading in itertools.product((0,2,4,6),(0,0x8000,0xFFFF)):result.append(replace(Case(),recovery_flags=flags,heading=heading))
 for child,carry in itertools.product((0,1,2),(0,1,255)):result.append(replace(Case(),child=child,carry=carry,stun=1,timer=0))
 for e in range(16):result.append(replace(Case(),effects=e,stun=1,timer=0))
 for b in range(256):result.append(replace(Case(),scale_byte=b,stun=255))
 for a in(1,2,3):result.append(replace(Case(),alias=a,stun=2,timer=0))
 for v in(0,0x80000000,0x3D4CCCCD,0x3DCCCCCD,0x3E800000,0x7FC12345,0x7F800000,0xFF800000):result.append(replace(Case(),unused_argument=v))
 return[replace(c,phase=(i&1)*8)for i,c in enumerate(result)]
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_83300.c.o','retail':out/'retail-linked.o'};cs=cases();coverage={}
 for name,p in paths.items():
  seen=set()
  for c in cs:m=Oracle(words(p),fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  coverage[name]=len(seen&set(range(ENTRY,ENTRY+len(words(p))*4,4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(SYMS)}
  for c in(Case(),replace(Case(),stun=1,timer=0,effects=15),replace(Case(),stun=255)):
   m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=len(cs),executions=len(cs)*3,coverage=coverage,independent_rebases=rebases,all_public_bytes=True,all_scale_bytes=True,physical_child_aliases=True,signed_timer_and_delta_wrap=True,water_height_velocity_and_stun_boundaries=True,mixed_float_integer_and_fifth_stack_argument=True,unused_second_float_argument=True,raw_argument_home_profile=True,normalized_and_retail_preserve_argument_home=True,late_resource_and_recovery_reloads=True,saved_ABI_and_caller_homes=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
