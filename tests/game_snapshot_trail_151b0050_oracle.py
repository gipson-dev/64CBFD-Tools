"""Independent snapshot/trail model, including zero multiply and exposed vectors."""
from pathlib import Path
from dataclasses import dataclass,asdict
import itertools,json,struct
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_snapshot_trail_151b0050_match as source
p=source.OUT;ENTRY=source.ENTRY;FRAME=128;OUTPUT=0x60000
elf=(source.FROZEN/'conker/build/conker.us.elf').read_bytes();SYMS={row[1]:row[2][1]for row in symbol_rows(elf)}
RNG,REAL,DIRECTION,SUBMIT=[SYMS[n]for n in('func_150ADA20','func_150ADA68','func_15143794','func_151DA6F8')]
GLOBALS=[SYMS[n]for n in('D_800AA28C','D_800AA290','D_800AA294','D_800AA298','D_800AA29C')]
CONSTANTS=[struct.unpack_from('>I',elf,elf_slot_offset(elf,at,4))[0]for at in GLOBALS]
COUNTS={RNG:0,REAL:0,DIRECTION:4,SUBMIT:18};put,read=o.put,o.read
sx=lambda n:(((n&65535)^32768)-32768)&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 seed:int=0
 duration:int=0
 color:int=0
 request:int=0
 pitch:int=0
 heading:int=0
 channel:int=0
 mutation:int=0
 pattern:int=0
 phase:int=0

def args(c):
 return(1,7,o.bits(1.25+c.seed),o.bits(-2.5-c.seed),o.bits(3.75+c.seed),0,0,0,c.pitch,c.heading,0,0,0,0,c.channel)

def fixture(c):
 m={o.STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
 assert OUTPUT>=o.STACK+1024 or OUTPUT+128<=o.STACK-1024
 m.update({OUTPUT+i:(i*29+c.seed*11+0x5A)&255 for i in range(128)})
 for at,value in zip(GLOBALS,CONSTANTS):put(m,at,value)
 if c.pattern in(2,4):put(m,GLOBALS[2],0x80000000)
 for i,value in enumerate(args(c)):put(m,o.STACK+c.phase+i*4,value)
 return m

class Service:
 def __init__(self,m,c,home):self.m,self.c,self.home=m,c,home;self.calls=[];self.physical=[];self.packets=[];self.counts=dict.fromkeys(COUNTS,0)
 def invoke(self,target,args):
  m,c=self.m,self.c;index=self.counts[target];ordinal=len(self.calls);self.counts[target]+=1;self.physical.append((target,tuple(args)))
  if target==DIRECTION:
   assert len(args)==4
   normalized=(sx(args[0]),sx(args[1]),args[2],'DIRECTION');self.calls.append((target,normalized))
   for i,value in enumerate((o.bits(7.25+c.seed),o.bits(-8.5-c.seed),o.bits(9.75+c.seed))):put(m,args[3]+4*i,value)
   return 0
  if target==SUBMIT:
   assert len(args)==18
   pos=tuple(read(m,args[0]+4*i)for i in range(3));direction=tuple(read(m,args[1]+4*i)for i in range(3));self.packets.append((pos,direction))
   a=list(args);a[0:2]=['POSITION','DIRECTION']
   for i in(4,7,10,11,16):a[i]&=255
   for i in(3,13,14):a[i]=sx(a[i])
   self.calls.append((target,tuple(a)))
   for i,value in enumerate((*pos,*direction)):put(m,OUTPUT+4*i,value)
   for off,field in((24,2),(28,3),(32,4),(36,5),(40,6),(44,16)):put(m,OUTPUT+off,a[field])
   if c.mutation&4:m[args[0]+1]^=0x5A;m[args[1]+10]^=0xA7
   return OUTPUT
  assert target in(REAL,RNG)and not args
  self.calls.append((target,()))
  if c.mutation&1:
   values=(o.bits(2.+ordinal*.25),o.bits(1.+ordinal*.125),0x80000000 if c.pattern in(2,4) else o.bits(4.+ordinal*.5),o.bits(.125+ordinal*.0625),o.bits(1.5+ordinal*.125))
   for at,value in zip(GLOBALS,values):put(m,at,value)
  if c.mutation&2 and ordinal==0:
   for off,value in((8,o.bits(91.25)),(12,o.bits(-92.5)),(16,o.bits(93.75)),(32,0xABCD8001),(36,0x1234FFFF),(56,0xABCDEF80)):put(m,self.home+off,value)
  if target==RNG:
   assert index<3;return(c.duration,c.color,c.request)[index]&0xFFFFFFFF
  assert index<3
  if index==1 and c.pattern in(1,2,3):return{1:0x7FC12345,2:0x80000000,3:0x7F800000}[c.pattern]
  return(o.bits(.125+c.seed*.03125),o.bits(.25+c.seed*.0625),o.bits(.75-c.seed*.03125))[index]

def reference(initial,c):
 m=dict(initial);home=o.STACK+c.phase;position=home-12;direction=home-24;s=Service(m,c,home)
 for i,value in enumerate(args(c)[2:5]):put(m,position+i*4,value)
 first=s.invoke(REAL,());speed=o.add(o.mul(first,read(m,GLOBALS[0])),read(m,GLOBALS[1]))
 s.invoke(DIRECTION,(sx(read(m,home+38,2)),sx(read(m,home+34,2)),speed,direction))
 extent=s.invoke(REAL,());duration=s.invoke(RNG,());color=s.invoke(RNG,());time=s.invoke(REAL,());request=s.invoke(RNG,())
 a=(position,direction,o.add(o.mul(extent,0),read(m,GLOBALS[2])),sx(duration%20+31),(color%101+155)&255,o.add(o.mul(time,read(m,GLOBALS[3])),read(m,GLOBALS[4])),(request&1)+3,1,o.bits(1.),o.bits(1.),0,0,0,16,15,0,read(m,home+59,1),1)
 s.invoke(SUBMIT,a);return m,s.calls,s.packets

class Oracle(Trace):
 def __init__(self,words,m,c,entry=ENTRY,arguments=None,connected=None):
  self.fp=[];self.loads={};self.boundaries=[]
  FactoryOracle.__init__(self,words,m,c,entry=entry,s={},arguments=args(c)if arguments is None else arguments,connected=connected)
  self.service=Service(self.memory,c,o.STACK+c.phase);self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def get(self,at,n):return FactoryOracle.get(self,at,n)
 def record_call(self,target):assert target in COUNTS,hex(target);self.pending=tuple(self.arguments(COUNTS[target]))
 def hook(self,target):
  self.boundaries.append((target,self.pending,tuple(self.get(self.r[29]+i,1)for i in range(FRAME+60))))
  result=self.service.invoke(target,self.pending)
  for i in range(max(4,COUNTS[target])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF
  if target==REAL:self.f[0]=result
  else:self.r[2]=result

def verify(words,c):
 initial=fixture(c);expected,calls,packets=reference(initial,c);m=Oracle(words,initial,c).run()
 assert o.public(m.memory)==o.public(expected),('public',asdict(c))
 assert m.service.calls==calls and m.service.packets==packets,('calls',asdict(c),m.service.calls,calls)
 assert m.r[2]==1 and tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g and tuple(m.f[20:])==m.saved_fp
 return m

def cases():
 for i,(pitch,heading,mutation,pattern,phase)in enumerate(itertools.product((0,1,0x7FFF,0x8000,0xFFFF,0x12348001),(0,1,0x7FFF,0x8000,0xFFFF,0xABCD8001),range(8),range(4),(0,8))):
  yield Case(seed=i%8,duration=(0,19,20,0xFFFFFFFF)[i%4],color=(0,100,101,0x80000000)[i%4],request=(0,1,0x80000000,0xFFFFFFFF)[i%4],pitch=pitch,heading=heading,channel=(0,0xABCD0080,0x123400FF,0xFFFFFFFF)[i%4],mutation=mutation,pattern=pattern,phase=phase)
 for seed,mutation,phase in itertools.product(range(8),range(8),(0,8)):
  yield Case(seed=seed,duration=0xFFFFFFFF,color=0x80000000,request=1,pitch=0xABCD8000,heading=0x1234FFFF,channel=0xABCD0080,mutation=mutation,pattern=4,phase=phase)

def derive(words):
 assert words==source.PIN['bound_source_words'],'source words or bindings changed'
 assert len(words)==90 and words[0]==0x27BDFF80
 result=words[:];changes=[]
 for i,w in enumerate(words):
  if w>>21&31==29 and w>>26 in(35,43,49,57)and 0x58<=w&65535<=0x64:
   result[i]=(w&0xFFFF0000)|((w&65535)-8);changes.append(i)
 assert changes==[26,28,30,32,35,42,43,49]
 return result



def main(retail,raw,derived):
 count=ops=0;seen=[set(),set(),set()]
 for c in cases():
  a,b,d=verify(retail,c),verify(raw,c),verify(derived,c)
  assert a.memory==d.memory and a.boundaries==d.boundaries and a.fp==b.fp==d.fp
  for coverage,m in zip(seen,(a,b,d)):coverage.update(m.visits)
  count+=1;ops+=len(a.fp)
 report=dict(cases=count,ordered_FP_observations=ops,coverage=[len(x)for x in seen],complete_derived_RAM_and_provider_frames_equal=True,all18_arguments_and_both_vectors_checked=True,c_match_credit=0)
 (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
