"""Independent bone-hit byte reference with bounded mutable helper services."""
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
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_bone_hit_151aabc4_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
A,M1,M2,MARK,TABLE,COEF=0x30000,0x50000,0x60000,0x70000,0x800A8F70,0x800A8FCC
SELECT,BONE,PREP,QUERY,EMIT,TRAIL=0x151D8E20,0x15142314,0x1504715C,0x1504697C,0x151DBCBC,0x15153F18
COUNTS={SELECT:0,BONE:3,PREP:2,QUERY:4,EMIT:7,TRAIL:5};u32=lambda n:n&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n));public=lambda m:{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
HOLES=(53,54,55)
@dataclass(frozen=True)
class Case:
 seed:int=0;bone:int=0;route:int=0;hit:int=1;mutation:int=0;phase:int=0;native:int=1
def cases():
 for seed,hit in itertools.product(range(256),(0,1)):yield Case(seed=seed,bone=seed%4,hit=hit,mutation=seed%32,phase=(seed&1)*8)
 for bone,route,hit,mutation,phase in itertools.product(range(4),range(3),(0,1),(0,1,2,4,8,16,31),(0,8)):
  yield Case(seed=bone*31+mutation,bone=bone,route=route,hit=hit,mutation=mutation,phase=phase)
 for bone in(0x100,0x87654302,0xFFFFFF03,255,0xFFFFFFFE):
  for hit in(0,1):yield Case(seed=197,bone=bone,hit=hit,mutation=31,phase=8,native=0)
def bone_values(c):return(bits(c.seed*.125-11.),(0,0x80000000,0x4B7FFFFF,0x4B800001,0xCB800001,0x4C000000,0x3F800001,0xBF800001)[c.seed%8],bits(c.seed*-.25+17.))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((A,512),(M1,64),(M2,64),(MARK,4),(TABLE,256)):m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i in range(4):m[TABLE+i]=(c.seed+i*7)&255
 for i in range(5):put(m,COEF+4*i,bits((c.seed-120+i)*.125))
 put(m,A+0x1D4,0 if c.route==2 else M1);return m
def trail_bytes(m,p):return bytes(0 if i in HOLES else m[p+i]for i in range(68))
def fill_surface(m,p,c,ordinal):
 for i in range(36):m[p+i]=(i*11+c.seed+ordinal*7)&255
 put(m,p,bits((c.seed-128)*.25+ordinal*2.))
class Service:
 def __init__(self,m,c,home):self.m=m;self.c=c;self.home=home;self.calls=[];self.bone=self.surface=self.query=self.position=None
 def invoke(self,t,args):
  m,c=self.m,self.c;ordinal=len(self.calls);normal=list(args);observed=b''
  if t==BONE:
   normal[0]='matrix2'if args[0]==M2 else'matrix1';assert args[0]in(M1,M2);self.bone=args[2];normal[2]='bone-output'
  elif t==PREP:self.surface=args[0];normal[:2]=['surface','actor'];assert args[1]==A
  elif t==QUERY:
   self.query=args[0];normal[0]='query';normal[3]='surface';assert args[3]==self.surface
   observed=data(m,args[0],12)+data(m,args[3],36)
  elif t==EMIT:
   normal[3:5]=['vertices','position'];assert args[3]==self.surface+4;self.position=args[4]
   observed=data(m,args[3],18)+data(m,args[4],12)
  elif t==TRAIL:
   normal[:3]=['angles','trail','surface'];assert args[2]==self.surface
   observed=data(m,args[0],8)+trail_bytes(m,args[1])+data(m,args[2],36)
  self.calls.append((t,tuple(normal),observed))
  if t==BONE:
   for i,v in enumerate(bone_values(c)):put(m,args[2]+4*i,v)
  if t in(PREP,QUERY):fill_surface(m,self.surface,c,ordinal)
  put(m,MARK,u32(0x13579BDF+ordinal*0x10203+t))
  if c.mutation&1 and t==SELECT:
   put(m,A+0x1D4,M2)
   for i in range(4):m[TABLE+i]=(c.seed+i*17+33)&255
  if c.mutation&2 and self.bone is not None:
   for i in range(3):put(m,self.bone+4*i,bits((ordinal+1)*(i-1)*.375))
  if c.mutation&4 and self.surface is not None:fill_surface(m,self.surface,c,ordinal+11)
  if c.mutation&8 and self.position is not None:
   for i in range(3):put(m,self.position+4*i,bits((ordinal+1)*(i+1)*-.5))
  if c.mutation&16 and t==EMIT:
   for i in range(5):put(m,COEF+4*i,bits((ordinal+i-5)*.125))
  if t==SELECT:return c.seed&255
  if t==QUERY:return c.hit
  return 0xE5000000+ordinal
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;s=Service(m,c,home)
 if c.route==1 or not read(m,A+0x1D4):return m,[]
 b,surface,q,point,angles,trail=home-12,home-48,home-64,home-80,home-156,home-148
 selector=s.invoke(SELECT,());s.invoke(BONE,(read(m,A+0x1D4),m[TABLE+(c.bone&255)],b));s.invoke(PREP,(surface,A))
 upper=fp(read(m,b+4),bits(50.),'add','left');lower=fp(upper,bits(100.),'sub','left')
 for off,v in((0,read(m,b)),(4,upper),(8,read(m,b+8))):put(m,q+off,v)
 if s.invoke(QUERY,(q,0,lower,surface)):
  for off,v in((0,read(m,b)),(4,read(m,surface)),(8,read(m,b+8))):put(m,point+off,v)
  s.invoke(EMIT,(selector,0x42200000,150,surface+4,point,255,1))
  for i in range(12):m[trail+i]=m[point+i]
  for off,value in((12,bits(2.5)),(16,read(m,COEF)),(20,read(m,COEF+4)),(24,read(m,COEF+8)),(28,read(m,COEF+12)),(32,read(m,COEF+16)),(56,0),(64,0)):put(m,trail+off,value)
  for off,value in((36,3),(38,3),(40,3),(42,1),(44,30),(46,20),(48,155),(50,100),(60,16),(62,15)):put(m,trail+off,value,2)
  m[trail+52]=selector
  for off,value in((0,0),(2,255),(4,-64),(6,26)):put(m,angles+off,value,2)
  s.invoke(TRAIL,(angles,trail,surface,255,1))
 return m,s.calls
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(0 if c.route==1 else A,c.bone));self.service=Service(self.memory,c,self.target_home);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer
def programs():
 syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};programs={'retail':list(struct.unpack('>126I',(P/'retail.bin').read_bytes()))}
 for label,path in(('raw',P/'v13.o'),('strict',P/'bone-padded-strict.o'),('layout',P/'bone-padded-layout.o')):
  raw,refs=payload(path,'func_151AABC4');programs[label]=bound_blob(raw,refs,syms)
 return programs
def verify(words,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c).run()
 assert public(m.memory)==public(expected),('public',asdict(c))
 assert m.service.calls==calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
 assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp;return m
def main():
 code=programs();seen={k:set()for k in code};n=0;kind=Counter()
 for c in cases():
  for label,words in code.items():seen[label].update(verify(words,c).visits)
  n+=1;kind['native'if c.native else'guest-only']+=1
 controls=[];words=code['raw'];c=Case(seed=197,bone=2,mutation=31)
 for label,old,new in(('upper-bound',0x3C014248,0x3C014249),('fresh-matrix',0x8CE401D4,0x01C02025),('retained-hit',0x27A90078,0x27A900BC),('count-value',0x240E0003,0x240E0004),('selector-field',0xA3AE0068,0xA3AE0069)):
  bad=words[:];assert bad.count(old)==1,(label,old);bad[bad.index(old)]=new
  try:verify(bad,c)
  except(AssertionError,ValueError,KeyError):controls.append(label)
  else:raise AssertionError(('ineffective semantic control',label))
 report=dict(cases_per_stream=n,case_kinds=dict(kind),streams=list(code),target_words_visited={k:len(v)for k,v in seen.items()},trail_defined_bytes=65,angle_defined_bytes=8,trail_padding_uncredited_bytes=3,effective_controls=controls,source_installed=source.installed(),c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
