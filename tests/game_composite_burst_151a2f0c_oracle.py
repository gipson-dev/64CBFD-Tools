"""Independent 116-byte packet model and full-instruction MIPS ABI oracle."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_composite_burst_151a2f0c_recovery as m
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

ENTRY,INPUT,MARK,SUBMIT=0x151A2F0C,0x30000,0x50000,0x15152B38
CONSTANTS={0x800A8D30:0x3CA3D70A,0x800A8D34:0x3D1096BB,0x800A8D38:0xBE89374C}
data=lambda mem,p,n:bytes(mem[p+i]for i in range(n))
public=lambda mem:{a:b for a,b in mem.items()if not STACK-4096<=a<STACK+512}
rounded=lambda n:floating(bits(n))
f=lambda mem,p:floating(read(mem,p))

@dataclass(frozen=True)
class Case:
 seed:int=0
 enabled:int=0
 mutation:int=0
 phase:int=0

def cases():return[Case(seed,enabled,mutation,(seed%2)*8)for seed,enabled,mutation in itertools.product(range(256),range(2),range(2))]

def fixture(c):
 mem={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,512)}
 mem.update({INPUT+i:0xA5 for i in range(192)});put(mem,MARK,0)
 for va,word in CONSTANTS.items():put(mem,va,word)
 values={0x38:(0.,-0.,.25,1.5,20.,-17.,1024.,65536.)[c.seed%8],0x3C:(-.5,0.,1.25,17.,-20.,3.,-.25,-32768.)[c.seed%8],0x40:(c.seed-128)*.25,0x44:(c.seed%7-3)*1.5,0x48:c.seed*.125,0x4C:-1.25+(c.seed%3)*.5,0x50:2.5,0x54:-3.75}
 for off,value in values.items():put(mem,INPUT+off,bits(value))
 put(mem,INPUT+0x68,(0x80100021&~0x1000)|(0x1000 if c.enabled else 0));mem[INPUT+12]=c.seed;mem[INPUT+1]=(c.seed*13+7)&255
 return mem

def effect(mem,c,packet):
 put(mem,MARK,0x13579BDF)
 if c.mutation:
  for i in range(116):mem[packet+i]^=0x5A
  put(mem,INPUT+0xB4,1234,2);mem[INPUT+12]=0x81;mem[INPUT+1]=0xFE

def reference(c):
 mem=fixture(c);home=STACK+c.phase-116;packet={i:mem[home+i]for i in range(116)}
 for off,value in((0,8),(4,6)):put(packet,off,value)
 for index in range(3):
  value=f(mem,INPUT+0x40+4*index)
  if read(mem,INPUT+0x68)&0x1000:value=rounded(value+f(mem,INPUT+0x4C+4*index))
  put(packet,8+4*index,bits(value))
 for off,va in((0x14,0x800A8D30),(0x18,0x800A8D34)):
  half=rounded(rounded(f(mem,INPUT+0x38)+f(mem,INPUT+0x3C))*.5)
  put(packet,off,bits(rounded(half*f(mem,va))))
 for off,word in((0x1C,CONSTANTS[0x800A8D38]),(0x20,0),(0x24,bits(8.)),(0x28,bits(10.)),(0x5C,0x200005),(0x60,0x60600),(0x6C,bits(1.)),(0x34,3),(0x38,1)):put(packet,off,word)
 for off,value in((0x2C,0),(0x2E,255),(0x30,-64),(0x32,86),(0x3C,17),(0x3E,18),(0x40,1),(0x64,7),(0x66,36),(0x68,1)):put(packet,off,value,2)
 fixed={0x42:4,0x43:2,0x44:3,0x45:255,0x46:200,0x47:200,0x48:255,0x49:0,0x4A:55,0x4B:55,0x4C:0,0x4D:255,0x4E:255,0x4F:255,0x50:255,0x51:0,0x52:0,0x53:0,0x54:0,0x55:255,0x56:0,0x57:1,0x58:36,0x6A:0,0x70:255,0x71:0,0x72:255,0x73:255}
 packet.update(fixed);blob=bytes(packet[i]for i in range(116))
 for i,value in enumerate(blob):mem[home+i]=value
 args=(home,mem[INPUT+12],mem[INPUT+1]);effect(mem,c,home)
 return mem,[(SUBMIT,args)],[blob]

class Machine(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(INPUT,));self.packets=[]
 def record_call(self,target):
  assert target==SUBMIT,hex(target);args=tuple(self.arguments(3));assert args[0]==STACK+self.case.phase-116
  self.calls.append((target,args));self.events.append(('CALL',target,args));self.packets.append(data(self.memory,args[0],116))
 def hook(self,target):
  assert target==SUBMIT;effect(self.memory,self.case,self.calls[-1][1][0])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x6ABC0000+self.case.seed

def main():
 m.check_inputs();streams=m.programs();visited={label:set()for label in streams};corpus=cases()
 for index,c in enumerate(corpus):
  expected,calls,packets=reference(c)
  for label,words in streams.items():
   q=Machine(words,c).run();assert q.calls==calls,(index,label,'calls',q.calls,calls)
   assert q.packets==packets,(index,label,'packet',[p.hex()for p in q.packets],[p.hex()for p in packets])
   assert public(q.memory)==public(expected),(index,label,'public memory')
   assert q.r[2]==0x6ABC0000+c.seed;visited[label].update(q.visits)
 assert all(len(v)==145 for v in visited.values()),{k:len(v)for k,v in visited.items()}
 report=dict(cases_per_stream=len(corpus),streams=list(streams),words_visited={k:len(v)for k,v in visited.items()},all_mode_and_extra_byte_values=True,complete_packet_bytes_and_home=True,provider_packet_and_record_mutation=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();print(json.dumps(report),flush=True)
if __name__=='__main__':main()
