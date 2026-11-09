"""Ordered actor update, bounded float32 arithmetic and original cached helpers."""
import itertools,json,math,re,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments.game_actor_angle_resource_150de458_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY=0x150DE458;ACTOR=0x30000;LOAD=0x1510D0EC;QUEUE=0x1510D874
NAMES=('D_800BE9E4','D_80090204','func_1510D0EC','func_1510D874','D_800D9ED0','D_800D9ED8','D_800D9F58','D_800D9F5C','D_80091D20','D_800B0E58','D_800B87A0','D_800BC448','D_800D9F68')
SYMS={n:int(n.split('_')[1],16)for n in NAMES};u32=lambda v:v&0xFFFFFFFF
signed=lambda v:(u32(v)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 seed:int=0
 ticks:int=1
 flags:int=3
 kind:int=12
 variant:int=0
 lifetime:int=1
 pattern:int=0
 mutation:int=0
 capacity:int=0
 phase:int=0
 failure:int=0
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def angles(c):
 patterns=((-0.0,0.,360.),(-1.,359.,361.),(-361.,720.,-720.),(.25,359.75,-.25),(16777216.,-16777216.,1.))
 return tuple(bits(v)for v in patterns[c.pattern%5])
def answer(c,i):return (0x81200000,0xFFFFFFF0,0,0x80000000)[c.seed%4]+i*0x1000&0xFFFFFFFF
def extent(c,i):return(0,1,511,512,513,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[(c.seed+i)%8]
def effect(m,c,s,i):
 if c.mutation&1:put(m,s['D_800BE9E4'],0x87654321);put(m,ACTOR+0x7C,c.variant^1)
 if c.mutation&2:put(m,s['D_80090204']+c.variant*8+4,0x12340000+i);m[ACTOR+0x73]^=3
def queue(m,s,a):
 count=m[s['D_800D9ED0']]
 if count<8:
  p=s['D_800D9ED8']+count*16
  for j in range(3):put(m,p+j*4,a[j])
  m[p+12]=a[3]&255;m[p+13]=a[4]&255;m[s['D_800D9ED0']]=count+1
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)};m.update({ACTOR+i:(i*29+c.seed*11+0x59)&255 for i in range(160)})
 for i,w in enumerate(angles(c)):put(m,ACTOR+4*i,w)
 for i,v in enumerate((-.5,.25,1.5)):put(m,ACTOR+0x60+4*i,bits(v))
 for at,v in zip((0x10,0x12,0x14,0x5A,0x5C,0x5E),(0x7FFF,0x8000,0xFFFF,0x7FFF,0x8000,0xFFFF)):put(m,ACTOR+at,v^((c.seed*317)&65535),2)
 put(m,ACTOR+0x3C,(0,1,0x7FFFFFFF,0xFFFFFFFF)[c.seed%4]);put(m,ACTOR+0x54,c.kind,2);put(m,ACTOR+0x7C,c.variant);m[ACTOR+0x73]=c.flags;m[ACTOR+0x8A]=c.lifetime
 put(m,s['D_800BE9E4'],c.ticks)
 for i,w in enumerate((0x692,0x693,0x694,0x695)):put(m,s['D_80090204']+i*4,w)
 m[s['D_800D9ED0']]=c.capacity;m.update({s['D_800D9ED8']+i:(i*13+0xA5)&255 for i in range(128)})
 put(m,s['D_800D9F58'],0x7FFFFFFF);put(m,s['D_800D9F5C'],0)
 for identity in(0x692,0x693,0x694,0x695):
  put(m,s['D_80091D20']+identity*2,1,2);put(m,s['D_800B0E58']+identity*4,0x81200000+identity*0x1000);put(m,s['D_800B87A0']+identity*2,0x8123,2)
  m[s['D_800BC448']+identity]=(0,127,128,255)[c.seed%4];m[s['D_800D9F68']+identity]=0
 return m
def motion(m,c,s=SYMS):
 if m[ACTOR+0x73]&3==3:
  delta=bits(float(signed(read(m,s['D_800BE9E4']))))
  for i in range(3):
   p=ACTOR+i*4;w=fp(read(m,p),fp(read(m,ACTOR+0x60+i*4),delta,'mul'),'add');put(m,p,w);v=floating(w)
   if v<0:put(m,p,fp(w,bits(360.),'add'))
   elif v>=360:put(m,p,fp(w,bits(360.),'sub'))
  life=m[ACTOR+0x8A];ticks=read(m,s['D_800BE9E4']);put(m,ACTOR+0x5C,half(read(m,ACTOR+0x5C,2))-read(m,ACTOR+0x3C)*ticks,2)
  for p,rate in zip((0x10,0x12,0x14),(0x5A,0x5C,0x5E)):put(m,ACTOR+p,half(read(m,ACTOR+p,2))+half(read(m,ACTOR+rate,2))*read(m,s['D_800BE9E4']),2)
  remaining=signed(life-read(m,s['D_800BE9E4']))
  if remaining>0:m[ACTOR+0x8A]=remaining&255
  else:m[ACTOR+0x6E]=1
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);calls=[];motion(m,c,s);cell=STACK+c.phase-104+0x54
 if read(m,ACTOR+0x54,2)&0x7FFF==12:
  table=s['D_80090204']+read(m,ACTOR+0x7C)*8
  for i in range(2):
   identity=read(m,table+i*4);calls.append((s['func_1510D0EC'],(identity,cell,3,0)))
   if connected:
    put(m,s['D_800D9F58'],min(signed(read(m,s['D_800D9F58'])),signed(identity)));put(m,s['D_800D9F5C'],max(signed(read(m,s['D_800D9F5C'])),signed(identity)))
    address=read(m,s['D_800B0E58']+identity*4);size=read(m,s['D_800B87A0']+identity*2,2);priority=m[s['D_800BC448']+identity];m[s['D_800BC448']+identity]=3 if (priority^128)-128<3 else priority
   else:address=0x80000000 if c.failure else answer(c,i);size=read(m,cell)if c.failure else extent(c,i);effect(m,c,s,i)
   a=(ACTOR,address,u32(address+size-512),4+2*i,5+2*i);calls.append((s['func_1510D874'],a));queue(m,s,a)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,));self.before=self.r[:];self.before_f=self.f[:];self.loads=0
 def record_call(self,t):
  counts={self.syms['func_1510D0EC']:4,self.syms['func_1510D874']:5,ENTRY:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c,s,a=self.case,self.syms,self.calls[-1][1]
  if t==s['func_1510D0EC']:
   assert a[1]==STACK+c.phase-104+0x54 and a[2:]==(3,0),a
   if not c.failure:put(self.memory,a[1],extent(c,self.loads))
   effect(self.memory,c,s,self.loads);value=0x80000000 if c.failure else answer(c,self.loads);self.loads+=1
  else:assert t==s['func_1510D874'];queue(self.memory,s,a);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=SYMS):
 t,fs,rs=parse_object(path);f=fs['func_150DE458'];return bound_blob(t[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']},s)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,s=SYMS,connected=False):
 want,calls=reference(initial,c,s,connected);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[30:]==m.before[30:]and m.f[20:]==m.before_f[20:]
def cases():
 for flags in range(256):yield Case(seed=flags%8,flags=flags,kind=(12,0x800C,0,13)[flags%4],pattern=flags%5,mutation=flags%4)
 for ticks,pattern,kind,variant,capacity in itertools.product((0,1,2,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF),range(5),(12,0x800C,0),(0,1),(0,7,8)):
  yield Case(seed=(ticks+pattern)%8,ticks=ticks,pattern=pattern,kind=kind,variant=variant,capacity=capacity,lifetime=(0,1,255)[capacity%3],mutation=pattern%4,phase=(pattern%2)*8)
def main():
 ps=[words(out/n)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o')];assert ps[0]==ps[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);pair=[]
  for ws in ps:m=Oracle(ws,initial,c).run();check(m,initial,c);pair.append(m)
  assert state(pair[0])==state(pair[1]);visited.update(pair[0].visits);count+=1
  if count%512==0:print('guest',count,flush=True)
 unreachable={36,57,76,118};assert {int((p-ENTRY)/4)for p in visited}==set(range(160))-unreachable
 prefixes=delay=0
 for c in(Case(),Case(pattern=2,ticks=0x80000000,capacity=7,mutation=3),Case(flags=0,kind=0)):
  initial=fixture(c);full=Oracle(ps[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for ws in ps[:2]:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);prefixes+=1;delay+=pair[0].delay_of is not None
 rebases=0
 for j in range(6):
  s={k:v+j*(0x20000 if k.startswith('func_')else 0x108000)for k,v in SYMS.items()};entry=ENTRY+j*0x10000;qs=[words(out/n,s)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o')];assert qs[0]==qs[1]
  for c in(Case(),Case(kind=0,pattern=2),Case(variant=1,mutation=3)):
   initial=fixture(c,s)
   for ws in qs:m=Oracle(ws,initial,c,entry,s).run();check(m,initial,c,s)
   rebases+=1
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'frozen/conker/build/conker.us.elf').read_bytes();asm=(root/'conker/asm/139FC0.s').read_text();code={};production_code={};helpers=[]
 _,production_functions,_=parse_object(root/'conker/build/src/game/generated_139FC0.c.o')
 for function in('func_1510D0EC','func_1510D874'):
  a=asm.index('glabel '+function+'\n');b=asm.index('endlabel '+function,a);rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',asm[a:b]);off,addr=int(rows[0][0],16),int(rows[0][1],16);truth=rom[off:off+len(rows)*4];at=elf_slot_offset(elf,addr,len(truth));baseline_exact=elf[at:at+len(truth)]==truth;code.update(zip(range(addr,addr+len(truth),4),struct.unpack('>%dI'%len(rows),truth)))
  size=production_functions[function]['size'];production=elf[at:at+size];production_code.update(zip(range(addr,addr+size,4),struct.unpack('>%dI'%(size//4),production)));helpers.append(dict(function=function,original_words=len(rows),production_words=size//4,baseline_exact=baseline_exact))
 assert[helper['baseline_exact']for helper in helpers]==[False,True]
 connected=0
 for c in(Case(seed=seed,variant=variant,capacity=capacity,flags=flags)for seed,variant,capacity,flags in itertools.product(range(4),(0,1),(0,7,8),(0,3))):
  initial=fixture(c)
  for connection in(code,production_code):
   pair=[]
   for ws in ps:m=Oracle(ws,initial,c,connected=connection).run();check(m,initial,c,connected=True);pair.append(m)
   assert state(pair[0])==state(pair[1]);connected+=1
 failures=0
 for c in(Case(failure=1,seed=i)for i in range(4)):
  initial=fixture(c);pair=[]
  for ws in ps[:2]:m=Oracle(ws,initial,c).run();check(m,initial,c);pair.append(m)
  assert state(pair[0])==state(pair[1]);failures+=1
 report=dict(cases_per_body=count,executions=count*3,reachable_words=156,retained_unreachable_words=sorted(unreachable),fault_prefix_pairs=prefixes,delay_slot_faults=delay,rebase_layouts=6,rebase_cases=rebases,connected_original_helpers=helpers,connected_cached_resource_cases=connected,guest_only_unwritten_extent_cases=failures,raw_C_public_contract_equal=True,normalized_literal_state_equal=True,hardware_FCSR_claim=False,whole_loader_allocation_decompression_paths_claimed=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
