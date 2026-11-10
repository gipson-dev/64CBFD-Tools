"""Independent actor/child contract, helper clobbers, aliases and signed controls."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_actor_state_1504be2c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_actor_state_1504be2c_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS
ACTOR=0x20000;OTHER=0x21000;CHILD=0x30000;ALT=0x31000;INPUT=0x60000;MAG=0x60100;OUTPUT=0x60200;CONTROL=0x50000;CONTROL2=0x50100
half=lambda n:((n&65535)^32768)-32768
byte=lambda n:((n&255)^128)-128
u32=lambda n:n&0xFFFFFFFF
mul=lambda a,b:bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
 type:int=0xAA
 flags:int=0
 phasebyte:int=254
 state:int=0
 heading:int=0x8001
 input:int=0xFFFF
 magnitude:int=0x40A00000
 damping:int=0xC1200000
 control:int=0x81
 gate:int=0
 first:int=1
 second:int=0xFFFFFFFF
 effects:int=0
 phase:int=0
 inputptr:int=INPUT
 magptr:int=MAG
 outputptr:int=OUTPUT

def args(c):return ACTOR,c.inputptr,c.magptr,c.outputptr
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((ACTOR,812),(OTHER,812),(CHILD,512),(ALT,512),(INPUT,16),(MAG,16),(OUTPUT,16),(CONTROL,8),(CONTROL2,8)):m.update({base+i:(i*29+0x59)&255 for i in range(-8,n+8)})
 for base,child in((ACTOR,CHILD),(OTHER,ALT)):
  put(m,base+0x31C,child);put(m,base+0x84,c.type,2);put(m,base+0x54,c.damping)
 for base in(CHILD,ALT):
  m[base+11]=c.phasebyte;m[base+22]=c.flags;put(m,base+14,c.state,2);put(m,base+20,c.heading,2)
 put(m,INPUT,c.input,2);put(m,MAG,c.magnitude);m[CONTROL+3]=c.control;m[CONTROL2+3]=c.control^255
 for n,v,size in(('D_800991D8',0x3CC90FDB,4),('D_800CC2B4',0xDEADBEEF,4),('D_800CC284',CONTROL,4),('D_800CC2B2',0xA5A5,2),('D_800C35EA',c.gate,1)):put(m,s[n],v,size)
 return m

def effect(m,c,stage,s=SYMS):
 if stage==1:
  if c.effects&1:put(m,ACTOR+0x31C,ALT)
  if c.effects&2:put(m,ACTOR+0x84,0x2C,2);put(m,ACTOR+0x54,bits(-17.5))
  if c.effects&4:put(m,s['D_800CC284'],CONTROL2);m[s['D_800C35EA']]=1
  if c.effects&8:m[read(m,ACTOR+0x31C)+22]^=255
 if stage>=2 and c.effects&32:put(m,ACTOR+0x31C,CHILD if stage==2 else ALT)
 if c.effects&16:
  home=STACK+c.phase;put(m,home,OTHER);put(m,home+4,INPUT);put(m,home+12,OUTPUT+1)

def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def snapshot(m):return tuple((p,m[p])for p in sorted(public(m)))
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);home=STACK+c.phase;actor,inputp,magp,outp=args(c);put(m,home+8,magp);put(m,home+12,outp)
 phase=m[read(m,actor+0x31C)+11];angle=mul(bits(float(phase)),read(m,s['D_800991D8']));put(m,s['D_800CC2B4'],bits(16.))
 child=read(m,actor+0x31C)
 if read(m,child+14,2)==0:put(m,child+14,0xA6,2);child=read(m,actor+0x31C)
 m[child+60]=5
 if floating(read(m,magp))>4. and read(m,actor+0x84,2)==0xAA:
  m[read(m,actor+0x31C)+60]=1;put(m,read(m,actor+0x31C)+16,read(m,inputp,2),2)
 calls=[];observations=[]
 def call(target,argv):
  calls.append((target,argv));observations.append(snapshot(m));effect(m,c,len(calls),s)
 put(m,home,actor);put(m,home+4,inputp);call(s['func_150AD78C'],(angle,));actor=read(m,home)
 child=read(m,actor+0x31C);m[child+11]=(m[child+11]+2)&255
 m[actor+170]=25 if m[read(m,actor+0x31C)+22]else 50 if read(m,actor+132,2)==0xA7 else 32
 type=read(m,actor+132,2);put(m,actor+84,mul(read(m,actor+84),bits(.5)))
 if type in(0x2C,0xE0):m[read(m,home+12)]=(byte(m[read(m,s['D_800CC284'])+3])>>1)&255
 else:
  put(m,home,actor);call(s['func_150ADA20'],());actor=read(m,home)
  if c.first&63==0:
   put(m,home,actor);call(s['func_150ADA20'],());actor=read(m,home);put(m,read(m,actor+0x31C)+20,(c.second%25000)-12500,2)
  put(m,s['D_800CC2B2'],read(m,read(m,actor+0x31C)+20,2),2)
  if m[read(m,actor+0x31C)+22]:
   v=half(read(m,s['D_800CC2B2'],2));put(m,s['D_800CC2B2'],(abs(v)//3)*(-1 if v<0 else 1),2)
 if m[s['D_800C35EA']]==0 and m[read(m,actor+0x31C)+22]==0:put(m,actor+642,30,2);m[actor+630]=0
 return m,calls,observations

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def record_call(self,t):
  assert t in(self.syms['func_150AD78C'],self.syms['func_150ADA20'],self.syms['func_1507EB2C']);a=(self.f[12],)if t!=self.syms['func_150ADA20']else();self.calls.append((t,a));self.observations.append(snapshot(self.memory));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t!=self.syms['func_1507EB2C'],'Static dead helper became reachable';stage=len(self.calls);effect(self.memory,self.case,stage,self.syms)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=bits(-99.5);self.r[2]=u32(self.case.first if stage==2 else self.case.second);self.hi,self.lo=0xA5000010,0xA5000011

def words(p,s=SYMS):return bound_blob(*qualify.payload(p),s)
def check(m,c=Case(),s=SYMS,caller=False):
 want,calls,obs=reference(m.initial,c,s);assert m.calls==calls,('calls',m.calls,calls,c);assert m.observations==obs,('helper boundary',c)
 actual=dict(m.memory)
 # Float arithmetic is compared by NaN class; stored nonarithmetic bits remain exact.
 for base in(ACTOR,OTHER):
  a,b=read(actual,base+84),read(want,base+84)
  if math.isnan(floating(a))and math.isnan(floating(b)):put(actual,base+84,b)
 assert public(actual)==public(want),('public bytes',[(hex(p),v,want.get(p))for p,v in public(actual).items()if want.get(p)!=v][:12],c)
 assert all(actual[p]==want[p]for p in m.initial if STACK+c.phase<=p<STACK+c.phase+512),('caller storage',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]

def cases():
 result=[]
 for type,flags,state,speed,first in itertools.product((0x2C,0xE0,0xAA,0xA7,0x1234),(0,1,128,255),(0,0x8000),(0x407FFFFF,0x40800000,0x40800001),(0,1)):
  result.append(replace(Case(),type=type,flags=flags,state=state,magnitude=speed,first=first,phase=(len(result)&1)*8))
 for n in range(256):
  result.append(replace(Case(),type=0x2C,control=n,phasebyte=n));result.append(replace(Case(),flags=n,heading=(n*257)&65535,first=0,second=u32(n*0x1020305)))
 for value in(0,0x80000000,0x7F800000,0xFF800000,0x7FC12345,1,0x80000001):
  for field in('magnitude','damping'):
   result.append(replace(Case(),**{field:value}))
 for effects in range(64):
  for type in(0xAA,0x2C):result.append(replace(Case(),effects=effects,type=type,first=0))
 for field,ps in(('inputptr',(CHILD+20,CHILD+16,ACTOR+132)),('magptr',(ACTOR+84,)),('outputptr',(CHILD+11,CHILD+22,ACTOR+630,INPUT))):
  for p in ps:result.append(replace(Case(),**{field:p},type=0x2C if field=='outputptr'else 0xAA))
 for n in(0,1,2,3,32767,32768,65535):result.append(replace(Case(),flags=1,heading=n))
 return result

def main():
 paths={'raw':out/'selected.o','padded':out/'qualified-padded/game_77AD0.c.o','retail':out/'retail-linked.o'};counts={};coverage={}
 for label,p in paths.items():
  seen=set()
  for c in cases():m=Oracle(words(p),fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=len(seen&set(range(ENTRY,ENTRY+(584 if label=='raw'else 588),4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n.startswith('func_')else 0x80300000+low+i*0x10000)for i,n in enumerate(SYMS)}
  for phase in(0,8):
   c=replace(Case(),phase=phase,effects=47,first=0);m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 # An incoming-home alias is a guest extension outside portable C. Raw saves
 # A1 early, while retail preserves that home until sine. Qualify and disclose
 # the two profiles explicitly rather than silently claiming equivalence.
 c=replace(Case(),magptr=STACK+4);initial=fixture(c);put(initial,STACK+4,bits(9.));machines={}
 for label,p in paths.items():m=Oracle(words(p),initial,c);m.run();machines[label]=m
 assert public(machines['padded'].memory)==public(machines['retail'].memory)!=public(machines['raw'].memory)
 report=dict(cases_per_body=counts,total=sum(counts.values()),coverage=coverage,independent_rebases=rebases,static_dead_helper_unreached=True,guest_home_alias_profiles={'normalized_equals_retail':True,'raw_early_A1_save_differs':True},void_ABI=True,signed_pointer_byte=True,unsigned_RNG_modulo=True,helper_child_redirection=True,all_public_bytes=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
