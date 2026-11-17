"""Independent strip geometry/display-list model and original instruction runner."""
from pathlib import Path
from dataclasses import dataclass,asdict
from collections import Counter
import itertools
import json
import struct
import sys
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.experiments import game_strip_draw_151ad92c_private_recovery as source
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.check_game_data_layout import load_section

p=source.OUT
r=source.ROOT
SYMS={row[1]:row[2][1]for row in symbol_rows((source.FROZEN/'conker/build/conker.us.elf').read_bytes())}
ENTRY=0x151AD92C
RECORD=o.RECORD
POINTS=o.POINTS
VERTICES,OTHER_VERTICES=0x80000,0x82000
OUTPUT,OTHER_OUTPUT=0x90000,0x94000
TABLE=SYMS['D_80090B60']
BANK=SYMS['D_800BE9C0']
MODE=SYMS['D_800D2C9C']
SUBMIT=SYMS['func_15094FE8']
data_at,data=load_section(source.FROZEN/'conker/build/conker.us.elf','.game_data')
table=data[TABLE-data_at:TABLE-data_at+56*12]
assert len(table)==672
u32=lambda value:value&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
 seed:int=0
 count:int=20
 bank:int=0
 texture:int=54
 width:int=32
 height:int=32
 pattern:int=0
 phase:int=0
 viewport:int=0
 mutation:int=0

def fixture(c):
 m={o.STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,512)}
 for base,size in ((RECORD,128),(POINTS,480),(VERTICES,2560),(OTHER_VERTICES,2560),(OUTPUT,4096),(OTHER_OUTPUT,4096)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 m.update({TABLE+i:value for i,value in enumerate(table)})
 o.put(m,RECORD+0x38,POINTS);o.put(m,RECORD+0x40,c.texture,2);m[RECORD+0x42]=c.count
 o.put(m,RECORD+0x48,VERTICES)
 for i in range(20):
  triples=((i*.25,200.-i*19.,-i*.5),(1200.+i,20.-i*9.,3.*i),(0.,0.,0.),(-20.+i*3.,i*11.,5.-i),(float(i%3),float(i%2),float(i%5)),(i*3.,0.,0.),(0.,0.,i*4.))
  values=triples[c.pattern%len(triples)]
  for j,value in enumerate(values):o.put(m,POINTS+24*i+4*j,o.bits(value))
 o.put(m,TABLE+c.texture*12+6,c.width,2);o.put(m,TABLE+c.texture*12+8,c.height,2)
 m[BANK]=c.bank
 o.put(m,MODE,u32(0x87654321+c.seed*0x10203))
 return m

class Service:
 def __init__(self,m,c):self.m,self.c,self.calls=m,c,[]
 def invoke(self,args):
  m,c=self.m,self.c
  self.calls.append(tuple(args))
  for i,value in enumerate((0xE7000000,0,0xFA000000,u32(0x102030FF+c.seed))):o.put(m,args[0]+i*4,value)
  answer=OTHER_OUTPUT+24 if c.mutation&2 else args[0]+16
  if c.mutation&1:
   o.put(m,RECORD+0x48,OTHER_VERTICES);m[BANK]^=1;m[RECORD+0x42]=1
   o.put(m,RECORD+0x40,55 if c.texture==54 else 54,2)
  if c.mutation&4:
   o.put(m,TABLE+c.texture*12+6,999,2);o.put(m,TABLE+c.texture*12+8,1001,2)
   o.put(m,MODE,0x001234AB)
  if c.mutation&8:
   o.put(m,POINTS,o.bits(99.));m[VERTICES+12]=0xA7;m[OTHER_VERTICES+12]=0xC3
  return answer

def reference(initial,c,output=OUTPUT):
 m=dict(initial);service=Service(m,c)
 get=lambda address:o.read(m,address)
 count=m[RECORD+0x42];texture=o.read(m,RECORD+0x40,2)
 width=o.read(m,TABLE+texture*12+6,2);height=o.read(m,TABLE+texture*12+8,2)-1
 shift=5 if texture==54 else 4
 zero,one,four,hundred=[o.bits(value)for value in(0.,1.,4.,100.)]
 def vertex(sample,corner,component,value):
  address=get(RECORD+0x48)+(m[BANK]*count+sample)*64+corner*16+component*2
  o.put(m,address,o.narrow(value),2)
 for sample in range(count):
  point=get(RECORD+0x38)+24*sample
  x,y,z=[get(point+4*j)for j in range(3)]
  if sample+1!=count:dx,dy,dz=[o.sub(get(point+24+4*j),value)for j,value in enumerate((x,y,z))]
  else:dx,dy,dz=zero,one,zero
  negative=dy^0x80000000;squared=o.mul(negative,negative)
  length=o.square_root(o.add(o.mul(dz,dz),squared))
  if o.floating(length)!=0.:
   reciprocal=o.div(one,length);nx,ny,nz=zero,o.mul(dz,reciprocal),o.mul(negative,reciprocal)
  else:nx,ny,nz=hundred,zero,zero
  nx,ny,nz=[o.mul(value,four)for value in(nx,ny,nz)]
  for j,value in enumerate((x,y,z)):vertex(sample,0,j,o.add(value,(nx,ny,nz)[j]))
  vertex(sample,2,0,o.sub(x,nx));vertex(sample,2,1,o.sub(y,ny))
  length=o.square_root(o.add(squared,o.mul(dx,dx)))
  vertex(sample,2,2,o.sub(z,nz))
  if o.floating(length)!=0.:
   reciprocal=o.div(one,length);nx,ny,nz=o.mul(negative,reciprocal),o.mul(dx,reciprocal),zero
  else:nx,ny,nz=one,zero,one
  nx,ny,nz=[o.mul(value,four)for value in(nx,ny,nz)]
  for j,value in enumerate((x,y,z)):vertex(sample,1,j,o.add(value,(nx,ny,nz)[j]))
  for j,value in enumerate((x,y,z)):vertex(sample,3,j,o.sub(value,(nx,ny,nz)[j]))
 def emit(a,b):
  nonlocal output
  o.put(m,output,u32(a));o.put(m,output+4,u32(b));output+=8
 for a,b in((0xD9FFFFFF,0x400),(0xD9FFFDFF,0),(0xD7000002,0xFFFFFFFF),(0xE7000000,0)):emit(a,b)
 output=service.invoke((output,TABLE+o.read(m,RECORD+0x40,2)*12,0,0,0,0,0,0,256,256,62))
 emit(0xFC121824,0xFF33FFFF)
 emit(0xEF000000|((get(MODE)|0x80000|0x2C0F)&0xFFFFFF),0x552078)
 u=u32((width+0x100)<<21);start=0x100;end=height+0x100
 for sample in range(count-1):
  emit(0x01008010,get(RECORD+0x48)+(m[BANK]*count+sample)*64)
  for word in(0x05000208,0x05020A08,0x0502040A,0x05040C0A,0x0504060E,0x05040E0C):emit(word,0)
  emit(0x02140000,u|u32(start<<shift));emit(0x02140008,u|u32(end<<shift))
  emit(0x0506000E,0);emit(0x0500080E,0)
  if sample==0:emit(0x05040200,0);emit(0x05060400,0)
  start+=height;end+=height
 return m,service.calls,output

class Oracle(Trace):
 def execute(self,word):
  if word>>26==0 and word&63==0x26:
   rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
   if rd:self.r[rd]=u32(self.r[rs]^self.r[rt])
   self.r[0]=0;return
  return super().execute(word)
 def __init__(self,words,initial,c):
  self.fp=[];self.loads=Counter();self.boundaries=[]
  FactoryOracle.__init__(self,words,initial,c,entry=ENTRY,s={},arguments=(OUTPUT,RECORD,c.viewport))
  self.service=Service(self.memory,c)
  self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30])
  self.saved_fp=tuple(self.f[20:])
 def record_call(self,target):
  assert target==SUBMIT,hex(target)
  self.pending=tuple(self.arguments(11))
 def hook(self,target):
  assert target==SUBMIT
  assert self.get(self.target_home+8,4)==u32(self.case.viewport),('incoming viewport word',asdict(self.case))
  self.boundaries.append((self.r[29],tuple(self.memory[self.target_home+i]for i in range(-304,16))))
  answer=self.service.invoke(self.pending)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.hi=self.lo=0xDEADBEEF
  self.r[2]=answer

def verify(words,c):
 initial=fixture(c);expected,calls,answer=reference(initial,c)
 machine=Oracle(words,initial,c).run()
 assert o.public(machine.memory)==o.public(expected),('public',asdict(c),next(((hex(at),value,expected.get(at))for at,value in o.public(machine.memory).items()if value!=expected.get(at)),None))
 assert machine.service.calls==calls,('calls',asdict(c),machine.service.calls,calls)
 assert machine.r[2]==answer,('return',asdict(c),hex(machine.r[2]),hex(answer))
 assert tuple(machine.r[16:24])+(machine.r[28],machine.r[29],machine.r[30])==machine.saved_g
 assert tuple(machine.f[20:])==machine.saved_fp
 return machine

def cases():
 for seed in range(256):
  yield Case(seed=seed,bank=seed&1,texture=54+(seed>>1&1),pattern=seed%7,phase=(seed&1)*8,viewport=u32(seed*0x1234ABCD),mutation=seed%16)
 for count,bank,texture,pattern in itertools.product((0,1,2,3,19,20),(0,1),(54,55),range(5)):
  yield Case(seed=7,count=count,bank=bank,texture=texture,pattern=pattern,phase=8,mutation=15)
 for width,height,bank,texture in itertools.product((0,1,32,65535),(0,1,32,65535),(0,1),(54,55)):
  yield Case(count=3,width=width,height=height,bank=bank,texture=texture,pattern=2)
 for pattern,bank,texture,mutation in itertools.product((2,5,6),(0,1),(54,55),range(8)):
  yield Case(count=3,pattern=pattern,bank=bank,texture=texture,mutation=mutation)
 for value in(0,1,0x7FFF,0x8000,0xFFFF,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
  yield Case(count=2,viewport=value,pattern=2)

def main():
 source.check_inputs()
 label='selected'
 raw,refs=o.payload(p/'owner.o','func_151AD92C')
 programs={'retail':list(struct.unpack('>464I',(p/'retail.bin').read_bytes())),'raw':o.bound_blob(raw,refs,SYMS)}
 coverage={key:set()for key in programs};n=0;equal_fp=equal_private=equal_provider=operations=0;first_difference=None
 for c in cases():
  executions={key:verify(words,c)for key,words in programs.items()}
  for key,machine in executions.items():coverage[key].update(machine.visits)
  left,right=executions['retail'],executions['raw'];operations+=len(left.fp)
  equal_fp+=left.fp==right.fp;equal_private+=left.memory==right.memory;equal_provider+=left.boundaries==right.boundaries
  if first_difference is None and left.fp!=right.fp:
   first_difference=next((dict(index=i,retail=a,raw=b)for i,(a,b)in enumerate(zip(left.fp,right.fp))if a!=b),dict(lengths=[len(left.fp),len(right.fp)]))
  n+=1
  if n%128==0:print(json.dumps(dict(label=label,cases=n)),flush=True)
 assert n==544
 report=dict(label=label,cases=n,streams=list(programs),words_visited={key:len(value)for key,value in coverage.items()},
  ordered_FP_operations=operations,ordered_FP_equal_cases=equal_fp,complete_RAM_equal_cases=equal_private,provider_frame_equal_cases=equal_provider,first_FP_difference=first_difference,
  public_bytes_calls_and_return_equal=True,all_preserved_registers=True,incoming_viewport_full_word=True,
  source_installed=False,c_match_credit=0,domain='Finite disjoint mapped record/points/vertices/display lists with one opaque texture provider. Not private/FCSR proof.')
 with(p/'guest-report.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
 assert equal_fp<n and equal_private<n and equal_provider<n,report
 source.check_inputs()
 print(json.dumps(report),flush=True)

if __name__=='__main__':main()
