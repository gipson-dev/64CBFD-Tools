"""Independent descriptor/reference services with aliases and mutable RNG providers."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_scaled_radial_150b85c0_match as source
p=source.OUT;f=source.FROZEN;ENTRY=0x150B85C0;RNG,FACTORY=0x150ADA20,0x15130374
INPUT,OUTPUT,MARK,K=0x30000,0x50000,0x70000,0x8009FD88
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
@dataclass(frozen=True)
class Case:
 slot:int=255;alias:int=0;success:int=1;mutation:int=0;profile:int=0;phase:int=0;seed:int=0;context:int=0x87654321
def cases():
 for slot,alias,success,mutation,profile in itertools.product((0,1,255),range(4),(0,1),(0,1,2,7),range(4)):
  seed=(slot+alias*11+success*13+mutation*17+profile*29)&255
  yield Case(slot,alias,success,mutation,profile,8*(seed&1),seed,0x80000000|seed*0x010101)
def addresses(c):return INPUT,(INPUT+4 if c.alias==2 else INPUT+0x100),(INPUT+8 if c.alias==3 else INPUT+0x100 if c.alias==1 else INPUT+0x104)
def args(c):return(*addresses(c),0xABC00000|c.slot,c.context)
def randoms(c):return((0,0,0,0),(0xffffffff,0xffffffff,1,1),(0x80000000,51,0,1),(10,50,1,0))[c.profile]
def fields():
 return[(0,4),(4,4),(8,2),(10,2),(12,4),(16,4),*((off,1)for off in range(0x14,0x1e)),*((off,2)for off in(0x1e,0x20,0x22)),*((off,4)for off in range(0x24,0x5c,4)),*((off,1)for off in range(0x60,0x66))]
DEFINED=tuple(sorted(off+i for off,n in fields()for i in range(n)));assert len(set(DEFINED))==len(DEFINED)==98
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for a,n in((INPUT,0x120),(OUTPUT,32),(MARK,4),(K,4)):m.update({a+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,val in enumerate((1.25,-2.5,3.75)):put(m,INPUT+4*i,bits(val+c.profile))
 put(m,INPUT+0x100,bits(-0.0 if c.profile==0 else 2.5));put(m,INPUT+0x104,bits(-3.75));put(m,K,bits(.75))
 put(m,STACK+c.phase+16,c.context);return m
def packet(c,home=None):return(STACK+c.phase if home is None else home)-112
class Service:
 def __init__(self,m,c):self.m,self.c=m,c;self.calls=[];self.index=0
 def invoke(self,t,a):
  c,m=self.c,self.m;ordinal=len(self.calls)
  observed=data(m,a[0],112)if t==FACTORY else b'';normalized=('packet',*a[1:])if t==FACTORY else a
  self.calls.append((t,normalized,observed));put(m,MARK,(0x13579bdf+ordinal*0x10203+t)&0xffffffff)
  if t==RNG:
   if c.mutation&1:
    for i in range(3):put(m,INPUT+4*i,bits((ordinal+1)*.25+i+c.profile))
    put(m,INPUT+0x100,bits(ordinal-2.5));put(m,INPUT+0x104,bits(ordinal+3.75))
   if c.mutation&2:put(m,K,bits(ordinal*.125+1.25))
   result=randoms(c)[self.index];self.index+=1;return result
  assert t==FACTORY
  if c.mutation&4:
   for i in range(112):m[a[0]+i]=(c.seed+i*7)&255
  put(m,OUTPUT,0x98765432);return OUTPUT if c.success else 0
def reference(initial,c,home=None,arguments=None):
 m=dict(initial);s=Service(m,c);d=packet(c,home)
 def field(off,v,n=4):put(m,d+off,v,n)
 def rng():return s.invoke(RNG,())
 field(0x1d,41,1);field(8,0xe03,2);field(0,0x200005);field(4,0)
 field(10,rng()%11+35,2);field(12,0);field(16,0)
 for off,v in((0x18,176),(0x19,160),(0x1a,42),(0x14,64),(0x15,11),(0x16,106),(0x17,255)):field(off,v,1)
 field(0x1b,rng()%51+100,1);field(0x1c,255,1);field(0x60,3,1);field(0x61,3,1)
 argv=args(c)if arguments is None else arguments
 pos,height,radius=argv[:3];field(0x28,bits(floating(read(m,radius))*20.));field(0x2c,bits(floating(read(m,height))*20.))
 for i in range(3):field(0x30+4*i,read(m,pos+4*i))
 for off in range(0x3c,0x58,4):field(off,0)
 first=rng();second=rng();field(0x58,0xce01|(0x40 if first&1 else 0)|(0x80 if second&1 else 0))
 for off,v,n in((0x62,255,1),(0x63,255,1),(0x1e,25,2),(0x20,10,2),(0x22,40,2),(0x64,255,1),(0x65,0,1),(0x24,read(m,K),4)):field(off,v,n)
 result=s.invoke(FACTORY,(d,1,0,argv[3]&255,argv[4]));return m,s,result
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None,arguments=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=args(c)if arguments is None else arguments,connected=connected)
  self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  assert t in(RNG,FACTORY);self.pending=t,tuple(self.arguments(0 if t==RNG else 5))
 def hook(self,t):
  answer=self.service.invoke(*self.pending)
  for i in range(4 if t==RNG else 5):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xffffffff
def streams():
 from tools.tests.game_scaled_radial_150b85c0_proof import derive
 lookup={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 raw=bound_blob(*payload(p/'owner.o','func_150B85C0'),lookup)
 return[('original',list(struct.unpack('>119I',(p/'retail.bin').read_bytes()))),('raw',raw),('normalized',derive(raw))]
def main(programs=None):
 programs=streams()if programs is None else programs;reports=[]
 for label,words in programs:
  seen=set();count=0
  for c in cases():
   initial=fixture(c);expected,s,result=reference(initial,c);m=Oracle(words,initial,c).run()
   assert m.service.calls==s.calls and public(m.memory)==public(expected),(label,c,'public/calls')
   assert data(m.memory,packet(c),112)==data(expected,packet(c),112),(label,c,'descriptor')
   assert m.r[2]==result and tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
   seen.update(m.visits&set(range(ENTRY,ENTRY+476,4)));count+=1
  assert len(seen)==119;row=dict(stream=label,cases=count,coverage=len(seen),all112_descriptor_bytes=True,public_return_saved_ABI=True);reports.append(row);print(json.dumps(row),flush=True)
 assert programs[0][1]==programs[2][1]
 report=dict(passes=True,streams=reports,raw_fault_register_identity_unclaimed=True,hardware_FCSR_unclaimed=True,c_match_credit=0)
 (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
