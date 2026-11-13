from dataclasses import dataclass
from pathlib import Path
import itertools, struct, subprocess
from tools.experiments import game_checksum_record_spawn_match as packet
payload=packet.payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
R=packet.ROOT;O=packet.OUT;NAME='func_150AEB9C'
OWNER=0x30000;TABLE=0x50000;TABLE2=0x51000;OUT=0x60000;COUNT=0x800886e0;PTR=0x800886e4;ROWS=0x800dce50;BEGIN=0x15001a08;END=0x15001b08;FACTORY=0x151491f4
ROM_WINDOW=(R/'conker/conker.us.bin').read_bytes()[0x2d4b0+0x1a08:0x2d4b0+0x1b08]
assert len(ROM_WINDOW)==256
SYMS=dict(func_15001A08=BEGIN,D_15001B08=END,D_800DCE50=ROWS,D_800886E0=COUNT,D_800886E4=PTR,func_151491F4=FACTORY)
@dataclass(frozen=True)
class Case:
 owner:int=OWNER;count:int=3;fail:int=9;mismatch:int=0;mutation:int=0;phase:int=0

def words(path):
 raw,refs=payload(path,NAME);return bound_blob(raw,refs,SYMS)
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,2048)}
 for base,n in ((OWNER,512),(TABLE,128),(TABLE2,128),(OUT,1024),(COUNT,8),(ROWS,0x340)):
  m.update({base+i:(i*29+0x5a)&255 for i in range(n)})
 put(m,COUNT,c.count);put(m,PTR,TABLE)
 for t in (TABLE,TABLE2):
  for i in range(16):m[t+i*4]=i+(0x30 if t==TABLE else 0x70);put(m,t+i*4+2,(-300+i*47)&65535,2)
 for i,b in enumerate(ROM_WINDOW):m[BEGIN+i]=b
 if c.mismatch:m[END-1]^=1
 return m
class Machine(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=0x150aeb9c,s={},arguments=(c.owner,));self.n=0
 def execute(self,w):
  if w>>26==0 and w&63==0x26:
   self.r[(w>>11)&31]=self.r[(w>>21)&31]^self.r[(w>>16)&31];self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t==FACTORY;self.calls.append((t,tuple(self.arguments(8))))
 def hook(self,t):
  assert t==FACTORY
  n=self.n;self.n+=1
  if c_mut:=self.case.mutation:
   if n==0:
    if c_mut&1:put(self.memory,COUNT,1)
    if c_mut&2:put(self.memory,PTR,TABLE2)
    if c_mut&4:self.memory[self.case.owner+0x3b]^=0x5a
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0 if n==self.case.fail else OUT+n*0x100

def reference(c):
 m=fixture(c);calls=[]
 if c.owner==0:return m,calls
 checksum=0
 for at in range(BEGIN,END,4):checksum=((checksum^read(m,at))<<1)&0xffffffff
 if checksum!=0xb4e42d60:
  put(m,ROWS+0x8c,0);put(m,ROWS+0x22c,0)
 i=0
 while i<((read(m,COUNT)^0x80000000)-0x80000000):
  table=read(m,PTR);life=read(m,table+i*4+2,2);life=((life^0x8000)-0x8000)&0xffffffff
  calls.append((FACTORY,(life,0,0xffffffff,1,0x27,8,255,0)))
  if i==0:
   if c.mutation&1:put(m,COUNT,1)
   if c.mutation&2:put(m,PTR,TABLE2)
   if c.mutation&4:m[OWNER+0x3b]^=0x5a
  if i==c.fail:break
  out=OUT+i*0x100;put(m,out+0x28,c.owner);m[out+0x2c]=m[c.owner+0x3b];m[out+0x2d]=m[read(m,PTR)+i*4]
  i+=1
 return m,calls

def run():
 programs=[words(O/'retail.o'),words(O/'after.o'),words(O/'generated.o'),words(O/'generic.o')];total=0
 for owner,count,fail,mismatch,mutation in itertools.product((0,OWNER),(-1,0,1,3),(0,1,9),(0,1),range(8)):
  c=Case(owner,count,fail,mismatch,mutation);states=[]
  for w in programs:
   m=Machine(w,c).run();public={a:v for a,v in m.memory.items() if not STACK-2048<=a<STACK+2048};states.append((public,m.calls))
  assert states.count(states[0])==4,(c,[x[1] for x in states])
  expected,calls=reference(c);public={a:v for a,v in expected.items() if not STACK-2048<=a<STACK+2048};assert states[0]==(public,calls),(c,states[0][1],calls);total+=1
 print('retail and candidate agree:',total,'ordinary and factory-mutation scenarios')
def aliases():
 programs=[words(O/'retail.o'),words(O/'after.o'),words(O/'generated.o'),words(O/'generic.o')];total=0;stopped=0
 for offset,fail,mismatch in itertools.product(range(-0x100,0x41,4),(0,9),(0,1)):
  c=Case(owner=STACK+offset,count=2,fail=fail,mismatch=mismatch);states=[]
  for w in programs:
   m=Machine(w,c);error=''
   try:m.run()
   except (AssertionError,KeyError) as e:
    if not (isinstance(e,KeyError) or str(e).startswith("('saved register',") or str(e).startswith("('unowned jump',") or str(e).startswith("('unmapped read',")):raise
    error=type(e).__name__+':'+str(e)
   public={a:v for a,v in m.memory.items() if not STACK-2048<=a<STACK+2048};span=tuple(m.memory.get(c.owner+i)for i in range(128));states.append((error,public,m.calls,span))
  assert states.count(states[0])==4,(c,[x[0]for x in states]);total+=1;stopped+=bool(states[0][0])
 print('overlap cases',total,'incomplete',stopped)
