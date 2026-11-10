"""Independent 25-actor search, live callback effects and five-byte script publication."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_proximity_cone_150768dc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_proximity_cone_150768dc_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS;ARRAY=SYMS['D_800CC2D0'];DEFS=0x60000;SCRIPT=0x90000
CALL_NAMES=('func_1505A72C','func_1505A630','func_1507BB28')
u32=lambda n:n&0xFFFFFFFF
s8=lambda n:((n&255)^128)-128
sub=lambda a,b:bits(floating(a)-floating(b))
same=lambda a,b:a==b or math.isnan(floating(a))and math.isnan(floating(b))
@dataclass(frozen=True)
class Case:
 own:int=0
 candidates:tuple=(1,2)
 command:int=10
 cross:int=1
 script:int=5
 lookup:int=0xA1
 width:int=128
 heading:int=0
 offset:int=0
 distance:int=0x41F00000
 angle:int=0x0800
 gate:int=0
 y:int=0
 effects:int=0
 phase:int=0

def fixture(c=Case(),s=SYMS):
 array=s['D_800CC2D0'];m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((array,26*812),(DEFS,187*32),(s['D_800D1C90'],187*4),(SCRIPT,1024)):
  for i in range(-16,n+16):m.setdefault(base+i,(i*29+0x59)&255)
 for name in('D_800D154C','D_800D1890','D_800D1891','D_800D1892','D_800D1893'):
  for i in range(-16,32):m.setdefault(s[name]+i,(i*13+0xA5)&255)
 for i in range(26):
  a=array+i*812;put(m,a,1 if i in c.candidates else 0);m[a+4]=i%3;m[a+458]=1;put(m,a+248,0x8020);put(m,a+118,c.heading,2);m[a+714]=c.offset&255;put(m,a+536,SCRIPT+i*5);m[a+168]=0xE1;m[a+546]=0xA9;m[a+562]=0xC3
  for off,v in((20,bits(float(i*3))),(24,c.y if i in c.candidates else 0),(28,bits(float(-i)))):put(m,a+off,v)
 current=array+c.own*812;put(m,current+24,0)
 for i in range(187):put(m,s['D_800D1C90']+i*4,DEFS+i*32);m[DEFS+i*32+23]=c.width
 for i in c.candidates:
  a=array+i*812
  if c.gate==1:put(m,a,0)
  if c.gate==2:m[a+458]=0
  if c.gate==3:put(m,a+248,0x8000)
  if c.gate==4:m[a+4]=m[current+4]
 put(m,s['D_800D154C'],current)
 for n,v in(('D_800D1890',c.command),('D_800D1891',c.cross),('D_800D1892',c.script),('D_800D1893',c.lookup)):m[s[n]]=v
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def digest(m,s=SYMS):
 h=2166136261
 for base,n in((s['D_800CC2D0'],26*812),(DEFS,187*32),(s['D_800D1C90'],187*4),(SCRIPT,1024),*((s[name],n)for name,n in(('D_800D154C',4),('D_800D1890',1),('D_800D1891',1),('D_800D1892',1),('D_800D1893',1)))):
  for i in range(n):h=((h^m[base+i])*16777619)&0xFFFFFFFF
 return h
def distance(c,index):return c.distance if index==(c.candidates[0]if c.candidates else 0)else bits(floating(c.distance)-float(index&3))
def effect(m,c,kind,index,s=SYMS):
 current=read(m,s['D_800D154C']);other=s['D_800CC2D0']+((c.own+1)%26)*812
 if c.effects&1:m[other+168]=0x81;put(m,s['D_800D154C'],other)
 if c.effects&2:
  m[s['D_800D1891']]=1;m[s['D_800D1892']]=9;m[s['D_800D1893']]=0x31
 if c.effects&4:
  a=read(m,s['D_800D154C']);put(m,a+118,0xFE00,2);m[a+714]=0x81;m[a+4]=2;m[DEFS+2*32+23]=251 if kind==1 else 3
 if c.effects&8:
  a=read(m,s['D_800D154C']);m[a+168]=0x99 if kind==2 else 0x81
  if index>=0:
   target=s['D_800CC2D0']+index*812;put(m,target+20,bits(999.));put(m,target+28,bits(-777.))
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);calls=[];obs=[];closest=bits(float(m[s['D_800D1890']]*8));current=read(m,s['D_800D154C']);m[current+168]=0;own=(read(m,s['D_800D154C'])-s['D_800CC2D0'])//812
 def actor():return read(m,s['D_800D154C'])
 def call(kind,index,args):calls.append((s[CALL_NAMES[kind]],args));obs.append(digest(m,s));effect(m,c,kind,index,s)
 for index in range(25):
  candidate=s['D_800CC2D0']+index*812
  if not read(m,candidate)or not m[candidate+458]or not read(m,candidate+248)&0x20 or index==own:continue
  current=actor()
  if not m[s['D_800D1891']]and m[current+4]==m[candidate+4]:continue
  y=floating(sub(read(m,current+24),read(m,candidate+24)))
  if abs(y)>50.:continue
  call(0,index,(current,candidate));d=distance(c,index)
  if not floating(d)<floating(closest):continue
  current=actor();width=m[read(m,s['D_800D1C90']+m[current+4]*4)+23];args=(sub(read(m,candidate+20),read(m,current+20)),sub(read(m,current+28),read(m,candidate+28)),0);call(1,index,args)
  current=actor();angle=(c.angle&65535)>>8;delta=((read(m,current+118,2)>>8)+s8(m[current+714])-angle+width//2)&255
  if delta<width:m[current+168]=index+128;closest=d
 current=actor()
 if m[current+168]:
  arg=m[s['D_800D1893']];call(2,-1,(0,arg));put(m,actor()+536,SCRIPT+40);current=actor();put(m,current+536,read(m,current+536)-5);script=m[s['D_800D1892']]
  if script:
   target=s['D_800CC2D0']+(m[actor()+168]&127)*812;put(m,target+536,0);m[target+562]=script;m[target+546]=own&255
 return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.last_index=-1
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==5:self.f[w>>6&31]=self.f[w>>11&31]&0x7FFFFFFF;return
  return super().execute(w)
 def record_call(self,t):
  assert t in[self.syms[n]for n in CALL_NAMES],hex(t);kind=[self.syms[n]for n in CALL_NAMES].index(t)
  if kind==0:args=tuple(self.arguments(2));self.last_index=(args[1]-self.syms['D_800CC2D0'])//812
  elif kind==1:args=(self.f[12],self.f[14],self.r[6])
  else:args=tuple(self.arguments(2))
  self.calls.append((t,args));self.observations.append(digest(self.memory,self.syms));self.events.append(('CALL',t,args))
 def hook(self,t):
  kind=[self.syms[n]for n in CALL_NAMES].index(t);effect(self.memory,self.case,kind,self.last_index if kind!=2 else-1,self.syms)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=distance(self.case,self.last_index)if kind==0 else 0xA5000000;self.r[2]=(self.case.angle&65535)if kind==1 else SCRIPT+40;self.hi,self.lo=0xA5000010,0xA5000011
def words(p,s=SYMS):return bound_blob(*qualify.payload(p),s)
def check(m,c=Case(),s=SYMS):
 want,calls,obs=reference(m.initial,c,s);assert len(m.calls)==len(calls),('count',c,len(m.calls),len(calls))
 for a,b in zip(m.calls,calls):assert a[0]==b[0]and len(a[1])==len(b[1])and all(same(x,y)for x,y in zip(a[1],b[1])),('ABI',c,a,b)
 assert m.observations==obs,('snapshots',c,m.observations,obs)
 assert public(m.memory)==public(want),('public',c,[(hex(p),v,want.get(p))for p,v in public(m.memory).items()if want.get(p)!=v][:6])
 assert all(m.memory[p]==v for p,v in m.initial.items()if STACK+c.phase<=p<STACK+c.phase+512)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[Case(),replace(Case(),candidates=()),replace(Case(),candidates=(25,)),replace(Case(),candidates=(0,)),replace(Case(),own=25,candidates=(0,24)),replace(Case(),candidates=tuple(range(26)))]
 for gate,cross in itertools.product(range(5),(0,1)):result.append(replace(Case(),gate=gate,cross=cross))
 for width,angle in itertools.product((0,1,2,127,128,255),(0,0x0100,0x7F00,0x8000,0xFF00)):result.append(replace(Case(),width=width,angle=angle))
 for heading,offset in itertools.product((0,0x7F00,0x8000,0xFFFF),(-128,-1,0,127)):result.append(replace(Case(),heading=heading,offset=offset))
 for y in(0,0x4247FFFF,0x42480000,0x42480001,0xC2480000,0xC2480001,0x7FC12345,0x7F800000,0xFF800000):result.append(replace(Case(),y=y))
 for d in(0,0x80000000,0xBF800000,0x42A00000,0x429FFFFF,0x42A00001,0x7FC12345,0x7F800000,0xFF800000):result.append(replace(Case(),distance=d))
 for e in range(16):result.append(replace(Case(),effects=e))
 for command,script in itertools.product((0,1,255),(0,1,255)):result.append(replace(Case(),command=command,script=script))
 return[replace(c,phase=(i&1)*8)for i,c in enumerate(result)]
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_A28B0.c.o','retail':out/'retail-linked.o'};cs=cases();coverage={}
 for name,p in paths.items():
  seen=set()
  for c in cs:m=Oracle(words(p),fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  coverage[name]=len(seen&set(range(ENTRY,ENTRY+640,4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(SYMS)}
  for c in( Case(),replace(Case(),effects=15),replace(Case(),own=25,candidates=(24,))):
   m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=len(cs),executions=len(cs)*3,coverage=coverage,independent_rebases=rebases,all_public_bytes=True,all_25_scan_slots=True,slot25_excluded=True,strict_distance_ties=True,NaN_height_and_distance_cases=True,live_actor_and_script_reload_effects=True,saved_GPR_FPR_and_caller_homes=True,void_no_arguments=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
