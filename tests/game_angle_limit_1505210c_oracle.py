"""Independent float32 projections, ordered wraps/clamps and hostile float ABI."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_angle_limit_1505210c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY=0x1505210C;COS=0x150AD780;SIN=0x150AD78C;ANGLE=0x150484A0;ACTOR=0x20000;OUTPUT=0x40000;ALT=0x40100
SYMS=dict(D_80099330=0x80099330,D_80099334=0x80099334,D_80099338=0x80099338,func_150AD780=COS,func_150AD78C=SIN,func_150484A0=ANGLE)
u32=lambda v:v&0xFFFFFFFF
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))
same=lambda a,b:a==b or math.isnan(floating(a))and math.isnan(floating(b))
@dataclass(frozen=True)
class Case:
 heading:int=0x42B40000
 x:int=0x41480000
 z:int=0xC1C80000
 limit:int=0x43340000
 returns:tuple=(0x3F400000,0xBF000000,0x3F000000,0xBF800000)
 effects:int=0
 phase:int=0
 output:int=OUTPUT
def args(c):return(ACTOR,c.x,c.z,c.output,c.limit)
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((ACTOR,812),(OUTPUT,32),(ALT,32)):m.update({base+i:(i*29+0x59)&255 for i in range(-8,n+8)})
 put(m,ACTOR+64,c.heading)
 for n,v in(('D_80099330',0x3C8EFA35),('D_80099334',0x42652EE0),('D_80099338',0x42652EE0)):put(m,s[n],v)
 return m
def effect(m,c,stage,s=SYMS):
 if c.effects&1:
  put(m,ACTOR+64,bits(17.25+stage));put(m,s['D_80099330'],bits(.5));put(m,s['D_80099334'],bits(2.0+stage));put(m,s['D_80099338'],bits(-3.0-stage))
 if c.effects&2:put(m,c.output,0xBAAD0000+stage)
 if c.effects&4:
  home=STACK+c.phase;put(m,home+4,bits(88.5));put(m,home+8,bits(-99.25));put(m,home+12,ALT);put(m,home+16,bits(7.5+stage))
def snapshot(m,c):return tuple(read(m,p)for p in(ACTOR+64,c.output,ALT))
def finish(first,second,limit):
 if floating(first)>=180:first=sub(first,bits(360.))
 if floating(second)>=180:second=sub(second,bits(360.))
 negative=limit^0x80000000
 if floating(limit)<floating(first):first=limit
 if floating(first)<floating(negative):first=negative
 if floating(limit)<floating(second):second=limit
 if floating(second)<floating(negative):second=negative
 return first,second
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);home=STACK+c.phase;put(m,home+12,c.output);calls=[];observations=[];radians=mul(c.heading,read(m,s['D_80099330']));negz=c.z^0x80000000
 for stage,t in enumerate((s['func_150AD780'],s['func_150AD78C'],s['func_150484A0'],s['func_150484A0']),1):
  if stage<=2:a=(radians,)
  elif stage==3:
   primary=add(mul(c.x,c.returns[0]),mul(negz,c.returns[1]));secondary=add(mul(c.x^0x80000000,c.returns[1]),mul(negz,c.returns[0]));a=(primary,bits(1.))
  else:a=(secondary,bits(1.))
  calls.append((t,a));observations.append(snapshot(m,c));effect(m,c,stage,s)
  if stage==3:first=mul(c.returns[2],read(m,s['D_80099334']))
  if stage==4:second=mul(c.returns[3],read(m,s['D_80099338']))
 first,second=finish(first,second,read(m,home+16));put(m,read(m,home+12),second);return m,calls,observations,first
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:return DirectionOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  assert t in(self.syms['func_150AD780'],self.syms['func_150AD78C'],self.syms['func_150484A0']);a=(self.f[12],)if t!=self.syms['func_150484A0']else(self.f[12],self.f[14]);self.calls.append((t,a));self.observations.append(snapshot(self.memory,self.case));self.events.append(('CALL',t,a))
 def hook(self,t):
  stage=len(self.calls);assert stage in range(1,5);effect(self.memory,self.case,stage,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.returns[stage-1];self.hi,self.lo=0xA5000010,0xA5000011
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);a,n=fs['func_1505210C']['value'],fs['func_1505210C']['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def check(m,c=Case(),s=SYMS,caller=False):
 want,calls,observations,value=reference(m.initial,c,s);assert len(m.calls)==len(calls)
 for actual,expected in zip(m.calls,calls):assert actual[0]==expected[0]and len(actual[1])==len(expected[1])and all(same(a,b)for a,b in zip(actual[1],expected[1])),('float ABI',actual,expected,c)
 assert m.observations==observations,('early output or stale snapshot',c)
 # Arithmetic NaNs are compared by class; copies/ordered predicates retain exact bits.
 pointer=read(want,STACK+c.phase+12);av=read(m.memory,pointer);ev=read(want,pointer);assert same(av,ev),('secondary',hex(av),hex(ev),c)
 actual=dict(m.memory);put(actual,pointer,ev);assert public(actual)==public(want),('public',c)
 assert same(m.f[0],value),('primary',hex(m.f[0]),hex(value),c)
 assert all(actual[p]==want[p]for p in m.initial if STACK+c.phase<=p<STACK+c.phase+512),('caller storage',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[];special=(0,0x80000000,0x3F800000,0xBF800000,0x40490FDB,0x7F800000,0xFF800000,0x7FC12345)
 for a,b,limit in itertools.product((0.,-0.,1.,3.1415925,6.283185,-3.1415925),(0.,1.,3.1415925,6.283185,-3.1415925),(180.,0.,-0.,90.,-90.)):
  result.append(replace(Case(),returns=(bits(.75),bits(-.5),bits(a),bits(b)),limit=bits(limit),phase=(len(result)&1)*8))
 for index,word in enumerate(special):
  for field in('heading','x','z','limit'):
   for effect in(0,1,2,4,7):result.append(replace(Case(),**{field:word},effects=effect,phase=(index&1)*8))
  for stage in range(4):
   values=list(Case().returns);values[stage]=word;result.append(replace(Case(),returns=tuple(values)))
 for a in range(64):result.append(replace(Case(),x=bits(a-32.25),z=bits(a*.5-19.),effects=a%8,phase=(a&1)*8))
 for p in(OUTPUT,ACTOR+64,STACK+128):
  for effect in(0,1,2,4,7):result.append(replace(Case(),output=p,effects=effect,phase=8))
 return result
def main():
 paths={'raw':out/'qualified-owner.o','padded':out/'qualified-padded/game_77AD0.c.o','retail':out/'retail-linked.o'};counts={};coverage={}
 for label,path in paths.items():
  ws=words(path)if label!='retail'else list(struct.unpack('>85I',(root/'conker/conker.us.bin').read_bytes()[0x7F5BC:0x7F710]));seen=set()
  for c in cases():m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=len(seen&set(range(ENTRY,ENTRY+340,4)));assert coverage[label]==85
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+index*0x100 if n.startswith('func_')else 0x80300000+low+index*0x10000)for index,n in enumerate(SYMS)}
  for phase in(0,8):
   c=replace(Case(),phase=phase,effects=7);m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=counts,total=sum(counts.values()),coverage=coverage,independent_rebases=rebases,ordered_NaN_comparisons=True,NaN_payload_or_FCSR_claimed=False,all_public_bytes=True,saved_FPR_pairs=True,guest_home_mutations=True,actor_and_caller_stack_aliases=True,bounded_helpers=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
