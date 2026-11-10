"""Independent leaf speed-approach model, flag sweeps and mixed O32 arguments."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_motion_approach_1505a3a8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_motion_approach_1505a3a8_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS;ACTOR=0x20000
FLOAT_GLOBALS=('D_800D1550','D_800994C0','D_800994C4','D_800994C8','D_800994CC','D_800994D0')
DEFAULTS=(0x3F800000,0x3ECCCCCD,0x3FA66666,0x3EB33333,0x3E4CCCCD,0x3C23D70A)
def floating(b):return struct.unpack('>f',struct.pack('>I',b&0xFFFFFFFF))[0]
def bits(f):
 try:return struct.unpack('>I',struct.pack('>f',f))[0]
 except OverflowError:return 0xFF800000 if f<0 else 0x7F800000
def rounded(f):return floating(bits(f))
def same(a,b):return a==b or math.isnan(floating(a))and math.isnan(floating(b))
@dataclass(frozen=True)
class Case:
 state:int=1
 gate:int=0
 field28:int=0x40C00000
 water:int=0
 slow:int=0
 flags:int=0
 extra:int=0
 speed:int=0x41200000
 target:int=0
 acceleration:int=0x3F800000
 deceleration:int=0x40000000
 magnitude:int=0
 globals:tuple=DEFAULTS
 phase:int=0
 alias:int=0
 seed:int=0
def actor(c,s):return ACTOR if not c.alias else s[('D_800D1550','D_800994C0','D_800994D0','D_800CC27C')[c.alias-1]]-60
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+c.seed*7+165)&255 for i in range(-512,512)};a=actor(c,s)
 m.update({a+i:(i*29+c.seed*13+89)&255 for i in range(-16,828)})
 put(m,a,c.state);put(m,a+40,c.field28);put(m,a+60,c.speed)
 for offset,value in ((173,c.water),(168,c.slow),(129,c.flags),(174,c.extra)):m[a+offset]=value&255
 for name,value in zip(FLOAT_GLOBALS,c.globals):put(m,s[name],value)
 m[s['D_800CC27C']]=c.gate&255
 put(m,STACK+c.phase+16,(0x12345600|c.magnitude))
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);a=actor(c,s);f=lambda offset:floating(read(m,a+offset));g=lambda name:floating(read(m,s[name]));r=rounded
 target=floating(c.target);acc=r(floating(c.acceleration)*g('D_800D1550'));dec=r(floating(c.deceleration)*g('D_800D1550'))
 if m[s['D_800CC27C']]and f(40)<5.0 and read(m,a)!=30:acc=0.0
 if read(m,a)==1:
  if m[a+173]:dec=r(dec*g('D_800994C0'));acc=2.0
  if m[a+168]:dec=r(dec*.25)
  flags=m[a+129]
  if flags:
   if flags&64:dec=0.0 if flags&32 else g('D_800994C4')
   else:
    dec=r(dec*g('D_800994C8'))
    if c.magnitude>=46:acc=r(acc*.5)
    if c.magnitude>=91:target=r(target*.5)
  if m[a+174]:dec=r(dec*g('D_800994CC'))
 previous=f(60)
 if target<0.0:dec=r(dec+acc)if previous>0.0 else acc
 elif previous<0.0:acc=r(acc+dec)
 if target<previous:
  put(m,a+60,bits(r(previous-dec)))
  if f(60)<target:put(m,a+60,bits(target))
 else:
  if previous>r(target-1.0):acc=r(acc*g('D_800994D0'))
  put(m,a+60,bits(r(previous+acc)))
  if target<f(60):put(m,a+60,bits(target))
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.case=c;self.syms=s
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(0x87654321,actor(c,s),c.acceleration,c.deceleration))
  self.f[12]=c.target;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected provider',hex(t)))
def words(p,s=SYMS):return bound_blob(*qualify.payload(p),s)
def check(m,c=Case(),s=SYMS):
 expected=reference(m.initial,c,s);a=actor(c,s);actual=public(m.memory);wanted=public(expected)
 assert actual.keys()==wanted.keys(),('public-domain',c)
 assert same(read(actual,a+60),read(wanted,a+60)),('public-speed',c,hex(read(actual,a+60)),hex(read(wanted,a+60)))
 assert all(actual[p]==v for p,v in wanted.items()if not a+60<=p<a+64),('public-bytes',c)
 assert all(m.memory[p]==v for p,v in m.initial.items()if STACK+c.phase<=p<STACK+c.phase+256),('caller-home',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('saved-ABI',c)
 assert same(m.f[0],read(m.initial,a+60)),('incidental-F0',c)
 assert not m.calls,('leaf',c)
def cases():
 cs=[Case()]
 for field in('magnitude','gate','water','slow','flags','extra'):
  for value in range(256):
   c=replace(Case(),flags=1,target=0x41A00000,magnitude=100,gate=1,field28=0x40800000)
   cs.append(replace(c,**{field:value}))
   if field in('water','slow','flags','extra'):cs.append(replace(Case(),flags=1,**{field:value})if field!='flags'else replace(Case(),flags=value))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x41200000,0xC1200000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 for field in('speed','target','acceleration','deceleration','field28'):
  for value in patterns:cs.append(replace(Case(),gate=1,**{field:value}))
 for state,gate,value in itertools.product((0,1,30,0xFFFFFFFF),(0,1),(0x409FFFFF,0x40A00000,0x40A00001,0x7FC12345)):cs.append(replace(Case(),state=state,gate=gate,field28=value,target=0x41A00000))
 for speed,target in itertools.product((0,0x80000000,0xBF800000,0x3F800000,0x41200000,0xC1200000),(0,0x80000000,0xBF800000,0x3F800000,0x41200000,0xC1200000)):cs.append(replace(Case(),speed=speed,target=target))
 for mag,flags in itertools.product((0,1,45,46,47,90,91,92,255),(0,1,32,64,96,255)):cs.append(replace(Case(),target=0x41A00000,flags=flags,magnitude=mag))
 for value in(0x3F7FFFFF,0x3F800000,0x3F800001):cs.append(replace(Case(),target=0x40000000,speed=value))
 for i,value in itertools.product(range(6),(0,0x80000000,0x3F000000,0xBF800000,0x7F800000,0xFF800000,0x7FC12345)):
  gs=list(DEFAULTS);gs[i]=value
  for target in(0,0x41280000):cs.append(replace(Case(),globals=tuple(gs),water=1,slow=1,flags=1,extra=1,target=target))
  if i==0:cs.append(replace(Case(),globals=tuple(gs),target=0x41A00000))
 for alias,speed,target in itertools.product(range(1,5),(0,0x41200000),(0,0x41A00000)):cs.append(replace(Case(),alias=alias,speed=speed,target=target))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();coverage={};trace_pairs=0
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_83300.c.o','retail':out/'retail-linked.o'}
 for name,p in paths.items():
  seen=set()
  for c in cs:
   m=Oracle(words(p),fixture(c),c);m.run();check(m,c);seen.update(m.visits)
   if name=='raw':
    retail=Oracle(words(paths['retail']),fixture(c),c);retail.run();assert m.trace==retail.trace,('access-order',c);trace_pairs+=1
  coverage[name]=len(seen&set(range(ENTRY,ENTRY+548,4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:0x80300000+low+i*0x10000 for i,n in enumerate(SYMS)}
  for c in(Case(),replace(Case(),water=1,slow=1,flags=1,extra=1,magnitude=100,target=0x41A00000),replace(Case(),alias=1)):
   m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=len(cs),executions=len(cs)*3,coverage=coverage,independent_rebases=rebases,raw_retail_access_order_pairs=trace_pairs,all_six_unsigned_bytes=True,all_actor_and_global_bytes=True,physical_global_aliases_guest_only=True,mixed_float_integer_and_fifth_stack_argument=True,caller_homes_and_saved_F20=True,incidental_F0_compared_without_semantic_return_claim=True,FCSR_or_hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
