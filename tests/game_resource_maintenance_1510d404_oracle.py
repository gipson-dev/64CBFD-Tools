"""Independent bounded cache-maintenance state machine and real MIPS bodies."""
import itertools,json,re,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_resource_maintenance_1510d404_candidates import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1510D404;ROM=0x13A8B4;DECODE=0x10006240;FREE=0x10004074;DIAG=0x150AD770
ARENA,ALTERNATE=0x50000,0x52000
u32=lambda x:x&0xFFFFFFFF
signed=lambda x:(u32(x)^0x80000000)-0x80000000
byte=lambda x:((x&255)^128)-128
SYMS={n:int(n.split('_')[1],16)for n in('D_800D9F58','D_800D9F5C','D_800DBDBC','D_8003C8E0','D_800DBDBA','D_800D9F60','D_800BC448','D_800B0E58','D_800D9F68','D_8003809C','func_150AD770','func_10004074','func_10006240')}
@dataclass(frozen=True)
class Case:
 first:int=5
 last:int=7
 states:tuple=(0,1,0x40)
 counter:int=3
 freeze:int=0
 effects:int=0
 decoder:int=0
 phase:int=0
 diagnostic_stop:bool=False

class DiagnosticBoundary(Exception):pass

def indexes(c):
 return sorted({0,100,7761,*range(max(0,c.first-1),min(7762,c.last+2))})
def pointer(c,i):return ARENA+((i-c.first)%8)*64
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(ARENA,ALTERNATE):m.update({base+i:(i*29+0x59)&255 for i in range(-16,8*64+16)})
 for i in indexes(c):
  m[s['D_800BC448']+i]=0;m[s['D_800D9F68']+i]=200;put(m,s['D_800B0E58']+i*4,pointer(c,i))
  p=pointer(c,i);put(m,p,0xFFFFFFF0+u32(i-c.first)*0x100);put(m,p+4,0x20+u32(i-c.first))
 if 0<=c.first<=c.last<7762:
  for i in range(c.first,c.last+1):m[s['D_800BC448']+i]=c.states[(i-c.first)%len(c.states)]&255
 put(m,s['D_800D9F58'],c.first);put(m,s['D_800D9F5C'],c.last);put(m,s['D_800DBDBC'],93);put(m,s['D_8003C8E0'],0x13579BDF);put(m,s['D_8003809C'],0x456789AB);m[s['D_800DBDBA']]=c.counter;m[s['D_800D9F60']]=c.freeze
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def observe(m,c,s,i):
 globals=tuple(read(m,s[n])for n in('D_800D9F58','D_800D9F5C','D_800DBDBC','D_8003C8E0','D_8003809C'))+(m[s['D_800DBDBA']],m[s['D_800D9F60']])
 return globals+(None,)if i is None else globals+(i,m[s['D_800BC448']+i],read(m,s['D_800B0E58']+i*4),m[s['D_800D9F68']+i])
def effect(m,c,s,stage,i,args):
 if stage=='diagnostic':put(m,s['D_800D9F58'],9);put(m,s['D_800D9F5C'],11);return
 if stage=='decode':put(m,args[1],0xD3C0DE01);put(m,args[1]+4,0xD3C0DE02)
 if c.effects&1:put(m,s['D_800D9F58'],1);put(m,s['D_800D9F5C'],100)
 if c.effects&2:m[s['D_800BC448']+i]=0x63 if stage=='decode'else 0x51;m[s['D_800D9F68']+i]=201
 if c.effects&4:put(m,s['D_800B0E58']+i*4,ALTERNATE)
 if c.effects&8 and i+1<7762:m[s['D_800BC448']+i+1]=0x40
 if c.effects&16:put(m,s['D_8003809C'],0x98765432)

def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 def call(t,args,i,stage):
  args=tuple(map(u32,args));calls.append((t,args));observations.append(observe(m,c,s,i))
  if stage=='diagnostic'and c.diagnostic_stop:return False
  effect(m,c,s,stage,i,args);return True
 last=signed(read(m,s['D_800D9F5C']))
 if last==-1:return m,calls,observations,False
 count=m[s['D_800DBDBA']]
 if count==0 and m[s['D_800D9F60']]:return m,calls,observations,False
 if count:m[s['D_800DBDBA']]=(count-1)&255
 first=signed(read(m,s['D_800D9F58']));put(m,s['D_800D9F58'],0xFFFF);put(m,s['D_800D9F5C'],-1)
 if first<0 or last>=7763:
  put(m,s['D_8003C8E0'],0x0C000046)
  if not call(s['func_150AD770'],(),None,'diagnostic'):return m,calls,observations,True
 put(m,s['D_800DBDBC'],-1)
 for i in range(first,last+1):
  assert 0<=i<7762,'Invalid nonempty table access outside qualified domain'
  p=s['D_800BC448']+i;cache=s['D_800B0E58']+i*4;state=byte(m[p])
  if state==0:continue
  if state<4:
   m[p]=(state-1)&255
   if byte(m[p])==0:
    put(m,s['D_800DBDBC'],i);call(s['func_10004074'],(read(m,cache),),i,'free');put(m,cache,-1);continue
  elif state&0x40:
   entry=read(m,cache);temporary=read(m,entry);offset=read(m,entry+4)
   call(s['func_10006240'],(u32(temporary+offset),entry,read(m,s['D_8003809C'])),i,'decode');call(s['func_10004074'],(temporary,),i,'free');m[p]&=~0x40
  else:continue
  if i<signed(read(m,s['D_800D9F58'])):put(m,s['D_800D9F58'],i)
  if i>signed(read(m,s['D_800D9F5C'])):put(m,s['D_800D9F5C'],i)
 put(m,s['D_800DBDBC'],-2);return m,calls,observations,False

class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),entry=ENTRY,s=SYMS):
  super().__init__(ws,memory,c,entry=entry,s=s,arguments=(0x12345678,0x89ABCDEF,0x87654321,0x76543210));self.observations=[];self.current=None;self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  s,c=self.syms,self.case;counts={s['func_150AD770']:0,s['func_10004074']:1,s['func_10006240']:3};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])))
  if t==s['func_150AD770']:self.current=None
  elif t==s['func_10006240']:
   found=[i for i in range(c.first,c.last+1)if pointer(c,i)==args[1]];assert len(found)==1,(c,args);self.current=found[0]
  elif self.calls and self.calls[-1][0]==s['func_10006240']:assert self.current is not None
  else:self.current=signed(read(self.memory,s['D_800DBDBC']))
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(observe(self.memory,c,s,self.current))
 def hook(self,t):
  s,c=self.syms,self.case;stage='diagnostic'if t==s['func_150AD770']else'decode'if t==s['func_10006240']else'free'
  if stage=='diagnostic'and c.diagnostic_stop:raise DiagnosticBoundary
  effect(self.memory,c,s,stage,self.current,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(c.decoder)if stage=='decode'else 0xDEADBEEF

def words(path,s=SYMS):
 raw,fs,rs=parse_object(path);f=fs['func_1510D404'];return bound_blob(raw[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']},s)
def cases():
 for bits in range(256):yield Case(last=5,states=(bits,))
 for counter,freeze,last in itertools.product(range(256),(0,1),(-1,5)):yield Case(last=last,counter=counter,freeze=freeze,states=(3,))
 for first,states,effects,decoder in itertools.product((0,5,7759),((0,1,2),(3,4,127),(0x40,0xC0,255)),(0,1,2,4,8,16,31),(0,-1,64)):
  yield Case(first=first,last=first+2,states=states,effects=effects,decoder=decoder)
 for first,last in((7763,7762),(7764,7763),(-1,-2),(17,16)):yield Case(first=first,last=last)
 yield Case(first=-1,last=0,diagnostic_stop=True)
def check_one(m,initial,c,s=SYMS):
 want,calls,observations,stop=reference(initial,c,s)
 try:m.run();assert not stop
 except DiagnosticBoundary:assert stop
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c
 if not stop:
  assert all(m.r[r]==m.before[r]for r in(*range(16,24),28,29,30,31)),c
  assert m.f[20:]==m.before_f[20:],c
  assert all(m.memory[p]==v for p,v in initial.items()if STACK+c.phase<=p<STACK+1024),c
 return m
def main():
 names=('retail-reference.o','qualified-baseline.o','qualified-counter.o','qualified-equal.o');programs=[words(out/n)for n in names];visited=set();count=prefixes=0
 for c in cases():
  initial=fixture(c);pair=[check_one(Oracle(ws,initial,c),initial,c)for ws in programs];visited.update(pair[0].visits);count+=1;prefixes+=c.diagnostic_stop
 rebases=0
 for j in range(6):
  s={k:v+j*(0x20000 if k.startswith('func_')else 0x108000)for k,v in SYMS.items()};entry=ENTRY+j*0x10000;ps=[words(out/n,s)for n in names]
  for c in(Case(),Case(last=-1),Case(counter=0,freeze=1),Case(states=(1,2,3)),Case(states=(64,65,127),effects=31),Case(first=-1,last=0,diagnostic_stop=True)):
   initial=fixture(c,s)
   for ws in ps:check_one(Oracle(ws,initial,c,entry,s),initial,c,s)
   rebases+=1
 report=dict(cases_per_body=count,executions=count*len(programs),covered_retail_words=len(visited),retail_words=129,private_candidates_uncredited=True,diagnostic_prefix_cases=prefixes,SDK_providers_bounded=True,rebase_layouts=6,rebase_cases=rebases,callee_saved_lifetimes_and_stack_boundary=True)
 assert count==1474 and len(visited)==129
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
