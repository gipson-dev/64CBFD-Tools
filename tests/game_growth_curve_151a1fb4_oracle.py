"""Independent finite fourteen-short growth model and MIPS ABI oracle."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_growth_curve_151a1fb4_recovery as prior
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

r=prior.ROOT;o=prior.OUT
ENTRY,INPUT,OUTPUT,DT,TABLE,DESCRIPTOR=0x151A1FB4,0x30000,0x50000,0x800BE9A4,0x80090B60,0x80090D34
S=dict(func_150ADA20=0x150ADA20,func_150ADA68=0x150ADA68,func_151423D8=0x151423D8,func_15167D84=0x15167D84,memcpy=prior.symbols()['memcpy'],D_800BE9A4=DT,D_80090B60=TABLE,D_80090D34=DESCRIPTOR)
u32=lambda n:n&0xffffffff
s16=lambda n:((n&65535)^32768)-32768
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}
f=lambda m,p:floating(read(m,p))
rounded=lambda x:floating(bits(x))
signed_div=lambda a,b:(abs(a)//abs(b))*(-1 if(a<0)!=(b<0)else 1)

@dataclass(frozen=True)
class Case:
 seed:int=0
 phase:int=0
 initial_phase:float=1.25
 dt:float=1.0
 rate:float=1.0
 mutation:int=0
 success:int=1

def fixture(c):
 mem={STACK+i:0xCD for i in range(-4096,1024)}
 mem.update({INPUT+i:0xA5 for i in range(256)})
 mem.update({OUTPUT+i:0x5A for i in range(4096)})
 mem.update({TABLE+i:0 for i in range(1024)})
 for p,v in((INPUT+0x28,1.25+c.seed),(INPUT+0x2C,-2.5-c.seed),(INPUT+0x30,3.75+c.seed/2),(INPUT+0x34,3.5),(INPUT+0x38,c.initial_phase),(INPUT+0x3C,c.rate),(DT,c.dt)):
  put(mem,p,bits(v))
 for off,v in((0x40,16+(c.seed%4)*4),(0x42,3),(0x44,40),(0x46,20),(0x48,4),(0x4A,12)):put(mem,INPUT+off,v,2)
 mem[INPUT+12]=(c.seed*17)&255;mem[INPUT+1]=(255-c.seed*13)&255
 mem[TABLE+0x1D8]=1
 return mem

def integer(i,c):return(0,1,2,5,17,255,0xffffffff,3)[(i+c.seed+i//8)%8]
def real(i,c):return(0.0,.25,.5,.75,-.5,1.25,-1.5,2.0)[(i+c.seed)%8]
def trig(i,angle,c):return(0.0,.25,-.5,.75,-1.0,1.5)[(i+angle+c.seed)%6]

def mutate(mem,c,kind,index,packet=None):
 if kind=='integer'and index%8==5 and c.mutation&1:
  for p,v in((INPUT+0x28,-8.0),(INPUT+0x2C,9.0),(INPUT+0x30,-10.0)):put(mem,p,bits(v))
  put(mem,INPUT+0x40,20,2);put(mem,INPUT+0x42,7,2);put(mem,INPUT+0x44,55,2);put(mem,INPUT+0x46,9,2);put(mem,INPUT+0x48,10,2);put(mem,INPUT+0x4A,17,2)
  mem[INPUT+12]=0x81;mem[INPUT+1]=0xFE
 if kind=='integer'and index%8==6 and c.mutation&8 and packet is not None:put(mem,packet+40,64,2)
 if kind=='submit'and index==0 and c.mutation&2:put(mem,INPUT+0x38,bits(2.25))
 if kind=='integer'and index%8==0 and c.mutation&4 and packet is not None:
  put(mem,packet+0x34,0x220,2)

def reference(c):
 mem=fixture(c);packet={i:0xCD for i in range(56)};calls=[];packets=[];curves=[];ri=si=fi=emits=0
 def store(off,v,n):put(packet,off,v,n)
 def rng():
  nonlocal ri
  calls.append((S['func_150ADA20'],()));v=integer(ri,c)
  # The opaque provider can retain the previous packet pointer. Model that
  # packet separately from physical stack homes in this finite semantic screen.
  mutate(mem,c,'integer',ri)
  if ri%8==0 and c.mutation&4 and emits:store(0x34,0x220,2)
  if ri%8==6 and c.mutation&8 and emits:store(40,64,2)
  ri+=1;return v
 def sine(angle):
  nonlocal si
  angle&=255;calls.append((S['func_151423D8'],(angle,)));v=trig(si,angle,c);si+=1;return v
 phase=rounded(f(mem,INPUT+0x38)+rounded(f(mem,INPUT+0x3C)*f(mem,DT)));put(mem,INPUT+0x38,bits(phase))
 if phase>1:
  for off,v,n in((0,DESCRIPTOR,4),(4,0xC0001,4),(12,0,2),(22,0,2),(24,0,2),(31,18,1),(32,0,2),(34,0,2),(36,2000,2),(38,2000,2),(42,0,1),(44,5,1),(45,0,1),(46,0,1),(47,0,1),(48,0,1),(49,0,1),(50,0,1),(52,0x120,2)):store(off,v,n)
  while phase>1:
   angleA=rng()&255;angleB=rng()&255
   aq=sine(angleA-64);ap=sine(angleA);bq=sine(angleB-64);bp=sine(angleB)
   calls.append((S['func_150ADA68'],()));rv=real(fi,c);fi+=1
   radius=rounded(rv*f(mem,INPUT+0x34));planar=rounded(radius*bp)
   tx=rounded(f(mem,INPUT+0x28)+rounded(planar*aq));ty=rounded(f(mem,INPUT+0x2C)-rounded(radius*bq));tz=rounded(f(mem,INPUT+0x30)+rounded(planar*ap))
   if rng()&1:store(52,read(packet,52,2)|4,2)
   if rng()&1:store(52,read(packet,52,2)|8,2)
   value=rng();life=s16(value%u32(s16(read(mem,INPUT+0x42,2))+1)+s16(read(mem,INPUT+0x40,2)));store(14,life,2)
   value=rng();size=s16(value%u32(s16(read(mem,INPUT+0x46,2))+1)+s16(read(mem,INPUT+0x44,2)))
   peak=s16(mem[TABLE+0x1D8]*signed_div(256,life));store(40,peak,2);quarter=peak>>2;half=peak>>1
   curve=[0]*14
   curve[0]=s16(signed_div(255,peak-s16(peak-quarter)));curve[1]=curve[4]=peak;curve[2]=s16(peak-quarter)
   curve[3]=s16(signed_div(size,peak-s16(half)));curve[5]=curve[6]=curve[10]=s16(half)
   curve[7]=s16(signed_div(255,half));curve[8]=s16(quarter);curve[9]=s16(signed_div(255,quarter))
   value=rng();curve[11]=s16(value%u32(s16(read(mem,INPUT+0x4A,2))+1)+s16(read(mem,INPUT+0x48,2)))
   curve[12]=s16(read(packet,40,2))>>1;curve[13]=s16(rng()%81+80)
   for off,value in((16,tx),(18,ty),(20,tz)):store(off,int(value),2)
   for off,value in((28,tx),(30,ty),(29,tz)):store(off,int(rounded(value*256)),1)
   args=(STACK+c.phase-60,0,28,0xffffffff,mem[INPUT+12],mem[INPUT+1]);calls.append((S['func_15167D84'],args));packets.append(bytes(packet[i]for i in range(56)))
   mutate(mem,c,'submit',emits)
   answer=OUTPUT+emits*128 if c.success==1 or c.success==2 and emits%2==0 else 0
   if answer:
    for i,v in enumerate(packets[-1]):mem[answer+16+i]=v
    mem[answer+72]=255
    calls.append((S['memcpy'],(answer+80,STACK+c.phase-88,28)))
    curvebytes=struct.pack('>14h',*curve);curves.append(curvebytes)
    for i,v in enumerate(curvebytes):mem[answer+80+i]=v
   emits+=1;assert emits<16
   phase=rounded(f(mem,INPUT+0x38)-1.0);put(mem,INPUT+0x38,bits(phase))
 return mem,calls,packets,curves

class Machine(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(INPUT,))
  self.ri=self.si=self.fi=self.emits=0;self.packets=[];self.curves=[];self.packet=None
 def record_call(self,t):
  assert t in(S['func_150ADA20'],S['func_150ADA68'],S['func_151423D8'],S['func_15167D84'],S['memcpy']),hex(t)
  n={S['func_151423D8']:1,S['func_15167D84']:6,S['memcpy']:3}.get(t,0);a=tuple(u32(v)for v in self.arguments(n));self.actual_args=a
  if t==S['func_15167D84']:
   assert a[0]==STACK+self.case.phase-60,('packet home',hex(a[0]))
   self.packet=a[0];self.packets.append(data(self.memory,a[0],56))
  if t==S['memcpy']:
   assert a[1]==STACK+self.case.phase-88,('curve home',hex(a[1]))
   self.curves.append(data(self.memory,a[1],28))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;a=self.actual_args;value=0
  if t==S['func_150ADA20']:
   value=integer(self.ri,c);mutate(self.memory,c,'integer',self.ri,self.packet);self.ri+=1
  elif t==S['func_150ADA68']:value=bits(real(self.fi,c));self.fi+=1
  elif t==S['func_151423D8']:value=bits(trig(self.si,a[0],c));self.si+=1
  elif t==S['func_15167D84']:
   mutate(self.memory,c,'submit',self.emits)
   value=OUTPUT+self.emits*128 if c.success==1 or c.success==2 and self.emits%2==0 else 0
   if value:
    for i,v in enumerate(self.packets[-1]):self.memory[value+16+i]=v
    self.memory[value+72]=a[3]&255
   self.emits+=1
  elif t==S['memcpy']:
   for i,v in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=v
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=u32(value)
  if t in(S['func_150ADA68'],S['func_151423D8']):self.f[0]=value

def main():
 assert prior.check_inputs()
 streams=prior.programs()
 visited={label:set()for label in streams};count=0
 cases=[Case(seed=seed,initial_phase=p,dt=dt,mutation=mut,success=success,phase=(seed%2)*8)for seed,p,dt,mut,success in itertools.product(range(8),(-1.,0.,1.,1.25,2.75),(0.,.5),range(16),range(3))]
 for index,c in enumerate(cases):
  expected,calls,packets,curves=reference(c)
  for label,words in streams.items():
   q=Machine(words,c).run()
   assert q.calls==calls,(index,label,'calls',c,q.calls,calls)
   assert q.packets==packets,(index,label,'packet',c,[p.hex()for p in q.packets],[p.hex()for p in packets])
   assert q.curves==curves,(index,label,'curve',c,[p.hex()for p in q.curves],[p.hex()for p in curves])
   assert public(q.memory)==public(expected),(index,label,'public memory',c)
   visited[label].update(q.visits)
  count+=1
  if index%200==0:print(json.dumps(dict(cases=count,total=len(cases))),flush=True)
 assert prior.check_inputs()
 report=dict(cases_per_stream=count,streams=list(streams),exact_exposed_packet_and_curve_homes=True,words_visited={k:len(v)for k,v in visited.items()},scope='finite semantic check; separate frame, FP/FCSR, native32, caller and production gates',source_installed=prior.installed(),c_match_credit=0)
 (o/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
