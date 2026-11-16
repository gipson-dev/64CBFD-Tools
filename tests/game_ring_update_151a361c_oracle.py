"""Independent ordered ring model, signed wrapping and nonfaulting guest aliases."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_ring_update_151a361c_recovery as m
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,OWNER,RECORDS,STATE,TICK,STEP=0x151A361C,0x30000,0x50000,0x70000,0x800BE9E4,0x800BE9A4
s8=lambda n:((n&255)^128)-128
s16=lambda n:((n&65535)^32768)-32768
rounded=lambda n:floating(bits(n))
data=lambda mem,p,n:bytes(mem[p+i]for i in range(n))
public=lambda mem:{p:v for p,v in mem.items()if not STACK-2048<=p<STACK+512}

@dataclass(frozen=True)
class Case:
 cap:int=4
 head:int=0
 tail:int=3
 count:int=4
 flags:int=0
 tick:int=1
 scale:int=1
 pattern:int=0
 phase:int=0
 seed:int=0
 alias:int=0
 step:float=0.5
 rate:float=0.25
 byte_step:int=-3

def state(c):return STATE if c.alias==0 else OWNER-0x20 if c.alias==1 else RECORDS-0x18

def fixture(c):
 mem={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,512)}
 mem.update({OWNER+i:(i*19+c.seed+37)&255 for i in range(-64,0x120)})
 mem.update({RECORDS+i:(i*13+c.seed+11)&255 for i in range(-64,24*max(8,c.cap)+64)})
 p=state(c)
 for i in range(80):mem.setdefault(p+i,(i*7+c.seed+9)&255)
 mem[OWNER+0x25]=c.cap;mem[OWNER+0x2C]=c.count&255;mem[OWNER+0x2D]=c.head;mem[OWNER+0x2E]=c.tail
 put(mem,OWNER+0x94,RECORDS);put(mem,OWNER+0x98,p)
 for i in range(max(8,c.cap)):
  at=RECORDS+24*i
  for j,value in enumerate((i+0.25,-i-0.5,i*2.0+1.0,(i-3)*0.5)):put(mem,at+4*j,bits(value))
  put(mem,at+0x10,(-32768,-1,0,1,32767)[(c.pattern+i)%5],2)
  put(mem,at+0x12,(-1,0,1,3,32767)[(c.pattern+2*i)%5],2)
  mem[at+0x14]=(i*42+c.seed+33)&255
 put(mem,p+0x1C,c.scale,2);put(mem,p+0x24,bits(c.rate));mem[p+0x2A]=c.byte_step&255;mem[p+0x30]=c.flags&255;mem[p+0x4C]=(c.seed*13+17)&255
 put(mem,TICK,c.tick);put(mem,STEP,bits(c.step))
 return mem

def reference(c,initial=None):
 mem=fixture(c)if initial is None else dict(initial);p=read(mem,OWNER+0x98);records=read(mem,OWNER+0x94)
 if s8(mem[OWNER+0x2C])<2 and mem[p+0x30]&1:return mem,0
 mem[p+0x4C]=(mem[p+0x4C]+s8(mem[p+0x2A])*read(mem,TICK))&255
 cursor=s8(mem[OWNER+0x2E]);outer=inner=0
 while cursor!=s8(mem[OWNER+0x2D]):
  outer+=1;assert outer<=c.cap+1,('reference outer domain',c)
  cursor-=1
  if cursor<0:cursor=mem[OWNER+0x25]-1
  at=records+24*cursor;delay=s16(read(mem,at+0x12,2))
  if delay>0:put(mem,at+0x12,delay-read(mem,TICK),2)
  else:put(mem,at+0x10,s16(read(mem,at+0x10,2))-read(mem,TICK)*s16(read(mem,p+0x1C,2)),2)
  mem[at+0x14]=255
  product=rounded(floating(read(mem,STEP))*floating(read(mem,p+0x24)))
  put(mem,at+0xC,bits(rounded(floating(read(mem,at+0xC))+product)))
  if s16(read(mem,at+0x10,2))<0:
   mem[p+0x30]&=253
   while cursor!=s8(mem[OWNER+0x2D]):
    inner+=1;assert inner<=c.cap+1,('reference inner domain',c)
    mem[OWNER+0x2D]=(s8(mem[OWNER+0x2D])+1)&255
    if mem[OWNER+0x25]==s8(mem[OWNER+0x2D]):mem[OWNER+0x2D]=0
    mem[OWNER+0x2C]=(s8(mem[OWNER+0x2C])-1)&255
   put(mem,records+24*s8(mem[OWNER+0x2D])+0x10,0,2)
 if s8(mem[OWNER+0x2C])>0:
  at=records+24*s8(mem[OWNER+0x2D])
  # Preserve the original overlapping word-copy order rather than a memmove.
  for i in range(3):put(mem,OWNER+0x54+4*i,read(mem,at+4*i))
 else:
  for i in range(3):put(mem,OWNER+0x54+4*i,0)
 return mem,1

class Machine(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(OWNER,));self.initial_regs=self.r[:];self.initial_fp=self.f[:]
 def record_call(self,target):raise AssertionError(('unexpected call',hex(target)))
 def hook(self,target):raise AssertionError(('unexpected helper',hex(target)))

def signature(q):return q.memory,tuple(q.r),tuple(q.f),q.hi,q.lo,q.condition,q.calls
def check(words,c):
 expected,answer=reference(c);q=Machine(words,c).run()
 assert q.memory==expected,('memory',c,[(hex(k),expected.get(k),q.memory.get(k))for k in expected if expected.get(k)!=q.memory.get(k)][:10])
 assert q.r[2]==answer,('return',c,q.r[2],answer)
 assert all(q.r[i]==q.initial_regs[i]for i in(*range(16,24),28,29,30,31))and q.f[20:]==q.initial_fp[20:]
 return q

def cases():
 result=[]
 ticks=(-2147483648,-1,0,1,2,2147483647)
 for cap,ends,count,flags,pattern in itertools.product((1,2,4,7),range(4),(-128,-1,0,1,2,7,127),(0,1,2,3),range(5)):
  head,tail=((0,0),(0,cap-1),(cap-1,0),(cap-1,cap-1))[ends];seed=len(result)
  result.append(Case(cap,head,tail,count,flags,ticks[(seed+pattern)%6],(-32768,-3,0,1,32767)[seed%5],pattern,(seed&1)*8,seed,0,(-0.5,0.,0.5)[seed%3],(-2.,0.25,1.)[seed//3%3],(-128,-3,0,1,127)[seed%5]))
 for byte in range(256):
  result.append(Case(7,0,6,s8(byte),byte, ticks[byte%6],(-32768,1,32767)[byte%3],byte%5,(byte&1)*8,byte,0))
 for alias,seed in itertools.product((1,2),range(128)):
  result.append(Case(7,seed%7,(seed+4)%7,s8(seed*5),seed&3,ticks[seed%6],(-32768,-1,0,32767)[seed%4],seed%5,(seed&1)*8,seed,alias))
 return result

def native_cases():
 normal=[c for c in cases()if c.alias==0];matrix=normal[:-256]
 result=[matrix[i*len(matrix)//768]for i in range(768)]+normal[-256:]
 assert len(result)==1024;return result

def main():
 m.check_inputs();streams=m.programs();visited={label:set()for label in streams};corpus=cases()
 for c in corpus:
  baseline=None
  for label,words in streams.items():
   q=check(words,c);visited[label].update(q.visits)
   if baseline is None:baseline=signature(q)
   else:assert signature(q)==baseline,('complete state',label,c)
 dead={ENTRY+0xAC,ENTRY+0x188};wanted=set(range(ENTRY,ENTRY+420,4))-dead
 assert all(v==wanted for v in visited.values()),{k:sorted(wanted-v)for k,v in visited.items()}
 report=dict(cases_per_stream=len(corpus),streams=list(streams),reachable_words=103,unreachable_retail_offsets=['0xAC','0x188'],all_105_words_retained=True,all_signed_count_bytes=True,owner_state_and_ring_state_guest_aliases=True,complete_memory_and_register_equality=True,frame_unchanged=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
