"""Bounded radial callback loop with live table and argument-home mutations."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_radial_dispatch_1514c2f0_match as p
from tools.experiments import game_radial_dispatch_1514c2f0_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_actor_state_tick_integration import symbol_rows
SINE=0x151423D8;TABLE=0x8008AA00;CB=0x18010000;ALT=0x18010004
@dataclass(frozen=True)
class Case:
 x:int=0x41200000
 y:int=0xC1200000
 z:int=0x40A00000
 radius:int=0x40000000
 start:int=250
 step:int=7
 count:int=3
 selector:int=2
 arg8:int=0x81234567
 arg9:int=0x3F400000
 arg10:int=0xAABBCCDD
 arg11:int=0xFE
 mode:int=1
 fail:int=100
 mutation:int=0
 phase:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)};m.update({TABLE+i:0 for i in range(1024)});put(m,TABLE+c.selector*4,CB if c.mode else 0);return m
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def sine(a):return bits((float(a&255)-128.)/128.)
def addmul(base,radius,sample):return bits(rounded(floating(base)+rounded(floating(radius)*floating(sample))))
def effect(m,c,t,ordinal):
 if t==SINE and ordinal==0 and c.mutation&1:put(m,TABLE+c.selector*4,ALT)
 if t in(CB,ALT)and ordinal==0:
  if c.mutation&2:put(m,TABLE+c.selector*4,0)
  if c.mutation&4:m[STACK+c.phase+23]=0xFE
  if c.mutation&8:put(m,TABLE+c.selector*4,ALT)
def reference(initial,c):
 m=dict(initial);calls=[];angle=c.start&255;sin_count=cb_count=0;home=STACK+c.phase
 for i in range(max(0,c.count)):
  a=(angle-64)&255;calls.append((SINE,(a,)));effect(m,c,SINE,sin_count);sin_count+=1;quarter=sine(a)
  calls.append((SINE,(angle,)));effect(m,c,SINE,sin_count);sin_count+=1;sample=sine(angle);pointz=addmul(c.z,c.radius,sample);target=read(m,TABLE+c.selector*4)
  if target:
   args=(1,i,addmul(c.x,c.radius,quarter),c.y,pointz,c.x,c.y,c.z,angle,c.start&255,c.radius,c.arg8,c.arg9,c.arg10,c.arg11&255);calls.append((target,args));effect(m,c,target,cb_count);stop=cb_count==c.fail;cb_count+=1
   if stop:break
  step=m[home+23];step=step-256 if step&128 else step;angle=(angle+step)&255
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=p.ENTRY,connected=None):
  self.c=c;self.sin_count=0;self.cb_count=0;args=(0,0,c.z,c.radius,c.start,c.step,c.count,c.selector,c.arg8,c.arg9,c.arg10,c.arg11);super().__init__(words,fixture(c),c,entry=entry,arguments=args,connected=connected);self.f[12]=c.x;self.f[14]=c.y;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in(0,2,6,7):
   if fn==6:self.f[fd]=self.f[rd]
   elif fn==7:self.f[fd]=self.f[rd]^0x80000000
   else:
    a,b=floating(self.f[rd]),floating(self.f[rt]);self.f[fd]=bits(rounded(a+b if fn==0 else a*b))
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  sizes={SINE:1,CB:15,ALT:15};assert t in sizes,hex(t);self.calls.append((t,tuple(self.arguments(sizes[t]))))
 def hook(self,t):
  if t==SINE:
   ordinal=self.sin_count;self.sin_count+=1;value=sine(self.calls[-1][1][0])
  else:ordinal=self.cb_count;self.cb_count+=1;value=int(ordinal!=self.c.fail)
  effect(self.memory,self.c,t,ordinal)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True
  if t==SINE:self.f[0]=value
  else:self.r[2]=value
def words(path):
 raw,refs=p.payload(path);lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};return p.bound_blob(raw,refs,{name:lookup[name]for es in refs.values()for _,name in es})
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs);lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};symbols={name:lookup[name]for es in refs.values()for _,name in es};programs=(p.bound_blob(raw,refs,symbols),p.bound_blob(normal,nrefs,symbols),struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));cases=[]
 for i,(count,mode,fail,step,mutation)in enumerate(itertools.product((-1,0,1,2,4),(0,1),(0,1,100),(-128,-2,0,7,127),(0,1,2,4,8,15))):cases.append(Case(count=count,mode=mode,fail=fail,step=step,mutation=mutation,phase=(i&1)*8,seed=i%5))
 visits=set()
 for c in cases:
  models=[]
  for ws in programs:
   m=Oracle(ws,c);m.run();want,calls=reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not STACK-1024<=a<STACK+1024};assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];models.append(m)
  a,b,d=models;assert (b.memory,b.r,b.f,b.calls,b.trace,b.current_pc,b.delay_of)==(d.memory,d.r,d.f,d.calls,d.trace,d.current_pc,d.delay_of);visits.update(b.visits)
 r=dict(cases=len(cases),executions=3*len(cases),visited_words=len([v for v in visits if p.ENTRY<=v<p.ENTRY+384]),missing=[i for i in range(96)if p.ENTRY+4*i not in visits],raw_public_and_normalized_complete_state=True,table_and_step_home_mutations_guest_only=True,FCSR_hardware_and_full_callbacks_not_qualified=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
