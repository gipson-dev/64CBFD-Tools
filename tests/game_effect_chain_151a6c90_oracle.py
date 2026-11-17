"""Independent effect-chain reference and normal guest-ABI execution."""
from pathlib import Path
from dataclasses import dataclass,asdict
from collections import Counter
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments import game_effect_chain_151a6c90_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
A,COEF,MARK=0x30000,0x800A8DB0,0x70000
RNG,REAL,BURST,ONE,TWO,THREE,FOUR,FIVE=0x150ADA20,0x150ADA68,0x151A6F00,0x151D5334,0x151D3FF4,0x151D5514,0x151541B8,0x151D5404
HOLES=(2,3,0x12,0x13,0x5A,0x5B)
COUNTS={RNG:0,REAL:0,BURST:4,ONE:7,TWO:3,THREE:3,FOUR:7,FIVE:8}
u32=lambda v:v&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
@dataclass(frozen=True)
class Case:
 seed:int=0;slot:int=255;context:int=1;mutation:int=0;phase:int=0
def cases():
 for slot,phase in itertools.product(range(256),(0,8)):
  yield Case(seed=slot,slot=slot,context=(0,1,0x80000000,0xffffffff)[slot%4],mutation=slot%16,phase=phase)
 for seed,slot,mutation in itertools.product(range(8),(0x12340080,0xfffffffe,0x100),(0,15)):
  yield Case(seed=seed,slot=slot,context=0x87654321,mutation=mutation,phase=(seed&1)*8)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((A,64),(COEF,4),(MARK,4)):m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,v in enumerate((c.seed*.125-11.,c.seed*-.25+13.,-0. if c.seed&1 else 0.)) :put(m,A+20+4*i,bits(v))
 put(m,COEF,bits((1.,-.5,0.,8.)[c.seed%4]));return m
def masked_packet(m,p):return bytes(0 if i in HOLES else m[p+i]for i in range(92))
class Service:
 def __init__(self,m,c,home):self.m=m;self.c=c;self.home=home;self.calls=[];self.counts=Counter();self.packet=None;self.position=None
 def invoke(self,t,args):
  m,c=self.m,self.c;ordinal=len(self.calls);index=self.counts[t];self.counts[t]+=1;observed=b'';normal=list(args)
  if t==BURST:self.packet=args[0];normal[0]='packet';observed=masked_packet(m,args[0])
  elif t not in(RNG,REAL):self.position=args[0];normal[0]='position';observed=data(m,args[0],12)
  self.calls.append((t,tuple(normal),observed))
  put(m,MARK,u32(0x13579BDF+ordinal*0x10203+t))
  if c.mutation&1:
   for i in range(3):put(m,A+20+4*i,bits((ordinal+1)*(i+1)*.375))
  if c.mutation&2:put(m,COEF,bits((ordinal-5)*.125))
  if c.mutation&4 and self.position is not None:
   for i in range(3):put(m,self.position+4*i,bits((ordinal+1)*(i-1)*.5))
  if c.mutation&8 and self.packet is not None:
   for i in range(92):
    if i not in HOLES:m[self.packet+i]=(i*7+ordinal*13+c.seed)&255
  if t==RNG:return(0,1,3,4,0x7fffffff,0x80000000,0xfffffffe,0xffffffff)[(c.seed+3*index)%8]
  if t==REAL:return bits((0.,.25,.5,.9999999403953552,-.5,2.)[c.seed%6])
  return 0xE5000000+ordinal
def reference(initial,c):
 m=dict(initial);s=Service(m,c,STACK+c.phase);p=s.home-104;q=s.home-12
 for i in range(3):put(m,q+4*i,read(m,A+20+4*i))
 value=s.invoke(RNG,());put(m,p,(value&3)+6,2)
 for i in range(12):m[p+4+i]=m[q+i]
 for off,value,size in((0x10,80,2),(0x14,bits(60.),4),(0x18,0,2),(0x1A,255,2),(0x1C,-63,2),(0x1E,80,2),(0x20,0,4),(0x24,bits(35.),4),(0x28,bits(10.),4),(0x2C,bits(40.),4),(0x30,0,4),(0x34,0,4),(0x38,0,4),(0x3C,read(m,COEF),4),(0x40,bits(.5),4),(0x44,bits(-1.),4),(0x48,bits(-1.),4),(0x4C,bits(-2.),4),(0x50,bits(4.),4),(0x54,0,1),(0x55,0,1),(0x56,50,2),(0x58,25,2)):put(m,p+off,value,size)
 slot=c.slot&255;ctx=u32(c.context)
 s.invoke(BURST,(p,0,slot,ctx));s.invoke(ONE,(q,bits(506.),bits(1013.),0x3A8163D3,5,slot,ctx));s.invoke(TWO,(q,slot,ctx));s.invoke(THREE,(q,slot,ctx))
 sample=s.invoke(REAL,());random=s.invoke(RNG,())
 speed=fp(fp(sample,bits(4.),'mul','left'),bits(12.),'add','left')
 s.invoke(FOUR,(q,speed,0x3FD20C49,bits(float(random%56+200)),0,slot,ctx))
 s.invoke(FIVE,(q,bits(1502.),bits(3000.),0x39AEC33E,12,15,255,0))
 return m,s.calls
class Oracle(FactoryOracle):
 def __init__(self,words,m,c):
  super().__init__(words,m,c,entry=ENTRY,s={},arguments=(A,c.slot,c.context));self.service=Service(self.memory,c,self.target_home);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:self.f[fd]=bits(float((self.f[fs]^0x80000000)-0x80000000));return
  if op==17 and fmt==16 and fn in(0,1,2,3):self.f[fd]=fp(self.f[fs],self.f[ft],('add','sub','mul','div')[fn],'left');return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer
  if t==REAL:self.f[0]=answer
def programs():
 syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};programs={'retail':list(struct.unpack('>154I',(P/'retail.bin').read_bytes()[:616]))}
 for label,path in(('raw',P/'v2.o'),('strict',P/'q2-padded-strict.o'),('layout',P/'q2-padded-layout.o')):
  raw,refs=payload(path,'func_151A6C90');programs[label]=bound_blob(raw,refs,syms)
 return programs
def verify(words,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c).run()
 assert public(m.memory)==public(expected),('public',asdict(c))
 assert m.service.calls==calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
 assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
 return m
def main():
 code=programs();seen={k:set()for k in code};n=0
 for c in cases():
  for label,words in code.items():seen[label].update(verify(words,c).visits)
  n+=1
 controls=[];words=code['raw'];c=Case(seed=7,mutation=15)
 for label,old,new in(('count',0x25CF0006,0x25CF0007),('duration',0x240A0050,0x240A0051),('snapshot',0xC4840014,0xC4840010),('kind',0x00002825,0x24050001),('rate',0x34E763D3,0x34E763D2)):
  bad=words[:];assert bad.count(old)==1,(label,old);bad[bad.index(old)]=new
  try:verify(bad,c)
  except(AssertionError,ValueError,KeyError):controls.append(label)
  else:raise AssertionError(('ineffective negative',label))
 report=dict(cases_per_stream=n,streams=list(code),target_words_visited={k:len(v)for k,v in seen.items()},packet_defined_bytes=86,padding_uncredited_bytes=6,effective_controls=controls,normal_disjoint_stack_only=True,source_installed=source.installed(),c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
