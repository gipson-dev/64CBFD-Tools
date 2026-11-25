"""Independent scalar state machine and ordinary heap-record guest qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,random,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_height_interpolation_151155c0_match as p
o=p.OUT;ENTRY=0x151155c0;POINT=0x30000
u32=lambda v:v&0xffffffff
s32=lambda v:((v&0xffffffff)^0x80000000)-0x80000000
s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 current:int=100
 origin:int=50
 target:int=300
 divisor:int=5
 holdByte:int=0
 hold:int=0
 flags:int=4
 phase:int=0
 seed:int=0
 rm:int=0
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,256)};m.update({POINT+i:(i*29+c.seed*11+0x5a)&255 for i in range(-32,192)})
 for a,v,n in [(0x12,c.current,2),(0x3c,(c.holdByte<<24)|(c.divisor<<16)|(c.target&65535),4),(0x7c,c.origin,4),(0x80,c.hold,4)]:put(m,POINT+a,v,n)
 m[POINT+0x4f]=c.flags;return m
def reference(initial,c):
 m=dict(initial);old=s16(c.current);height=old;origin=s32(c.origin);hold=s32(c.hold);target=s16(c.target);wait=(c.holdByte&255)+1
 if origin==0:origin=old;put(m,POINT+0x7c,origin,4)
 if not c.divisor:return m,None
 numerator=s32(target-origin);step=(abs(numerator)//c.divisor)*(-1 if numerator<0 else 1);remainder=numerator-step*c.divisor
 if hold==0:
  if origin==height:
   if c.flags&4:hold=wait
  else:
   height=s16(height-step);inside=height>origin if origin<target else height<origin
   if not inside:height=s16(origin);hold=-wait
 if hold>0:
  candidate=s16(height+step);inside=candidate<target if origin<target else candidate>target
  height=candidate if inside else target;hold=wait if inside else hold-1
 if hold<0:hold+=1
 put(m,POINT+0x12,height,2);put(m,POINT+0x80,hold,4);put(m,POINT+0x5c,height-old,2)
 return m,(u32(step),u32(remainder))
class GuestTrap(Exception):pass
class Machine(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(POINT,));self.fcsr=c.rm;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==13:
   # GNU's first break argument occupies the upper ten bits of the code field.
   assert (w>>6)&1023==0;raise GuestTrap((w>>16)&1023)
  if w>>26==0 and w&63==26 and not self.r[w>>16&31]:
   left=self.r[w>>21&31];self.lo=0xffffffff if s32(left)>=0 else 1;self.hi=left;self.r[0]=0;return
  super().execute(w)
 def record_call(self,t):raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('Unexpected provider',hex(t)))
def check(words,c):
 m=Machine(words,c);expected,hilo=reference(dict(m.memory),c)
 if not c.divisor:
  try:m.run();raise AssertionError('Missing divide-zero trap')
  except GuestTrap as error:assert error.args==(7,),error
  assert m.memory==expected and m.fcsr==c.rm;return m
 m.run();assert m.memory==expected,(c,'memory',{hex(a):(v,expected.get(a))for a,v in m.memory.items()if expected.get(a)!=v});assert(m.lo,m.hi)==hilo,(c,'hilo',m.lo,m.hi,hilo)
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f==m.before_f and m.fcsr==c.rm and not m.calls;return m
def cases():
 rows=[Case(divisor=d,holdByte=d&255,flags=f,seed=d&31,rm=d&3,hold=(0,1,-1,3,-3)[d%5],current=(100,-100,32767,-32768)[d%4],target=(300,-300,32767,-32768)[d%4],origin=(0,50,-50,0x7fffffff,0x80000000)[d%5])for d,f in itertools.product(range(1,256),(0,4,255))]
 rows +=[Case(current=h,origin=origin,target=target,hold=hold,holdByte=wait,divisor=divisor,flags=flags)for h,origin,target,hold,wait,divisor,flags in itertools.product((-32768,0,32767),(0,1,-1),(0,-32768,32767),(0,1,-1),(0,255),(1,255),(0,4))]
 rng=random.Random(151155);rows +=[Case(current=rng.randrange(-32768,32768),origin=rng.getrandbits(32),target=rng.randrange(-32768,32768),hold=rng.getrandbits(32),holdByte=rng.randrange(256),divisor=rng.randrange(1,256),flags=rng.randrange(256),phase=(i&1)*8,seed=i&31,rm=i&3)for i in range(512)]
 rows +=[Case(divisor=0,current=h,origin=origin,hold=hold,flags=f)for h,origin,hold,f in itertools.product((-32768,0,32767),(0,1,-1),(0,1,-1),(0,4))]
 return rows

from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition
def main():
 files=['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o','selected-final/owner-candidate.o'];streams=[list(struct.unpack('>103I',payload(o/f,'func_151155C0')[0]))for f in files];assert all(ws==streams[0]for ws in streams[:4]);seen=set();prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in streams];a=models[0];assert all(state(m)==state(a)for m in models[1:4]);assert models[-1].r[2]==a.r[2]or not c.divisor;seen.update(a.visits)
 for c in[Case(),Case(origin=100,current=100,flags=4),Case(hold=-1),Case(divisor=0)]:
  full=check(streams[0],c)
  for cut in range(full.all_accesses):
   models=[]
   for ws in streams[:4]:
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert seen=={ENTRY+4*i for i in range(103)if i not in(34,35,36)}
 q=dict(cases_per_stream=len(cases()),streams=5,retail_equal_streams=4,all100_feasible_words_visited=True,unreachable_minus_one_divisor_guard_words=[34,35,36],access_fault_quads=prefixes,raw_public_memory_callee_state_HI_LO_and_normal_return_checked=True,raw_scratch_GPR_and_fault_order_not_claimed=True,divide_zero_machine_break7_checked=True,record_bytes=160,frame=0,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
