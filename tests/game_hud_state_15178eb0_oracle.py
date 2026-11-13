from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_hud_state_15178eb0_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
INIT=0x15178eb0;TRANS=0x15178efc;HANDLE=0x800dd430;RATE=0x800dd432;COLOR=0x800dd433;MODE=0x800dd434;COUNT=0x800dd436;LIST=0x800dd440;TIMER=0x800dd444;STATUS=0x800dd446
DISPOSE=0x1516972c;FREE=0x10004074;SOUND=0x100111c8
A=0x60000;B=0x61000;OBJECT=0x70000
S=dict(D_800DD430=HANDLE,D_800DD432=RATE,D_800DD433=COLOR,D_800DD434=MODE,D_800DD436=COUNT,D_800DD440=LIST,D_800DD444=TIMER,D_800DD446=STATUS,func_1516972C=DISPOSE,func_10004074=FREE,func_100111C8=SOUND)
@dataclass(frozen=True)
class Case:
 phase:int;state:int;status:int;array:int;plan:int
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-256,128)}
 for base,n in ((HANDLE,32),(A,1200),(B,1200)):
  m.update({base+i:0xa5 for i in range(n)})
 for base in (A,B):
  for i in range(300):put(m,base+4*i,0)
 for i in (0,1,149,150,299):
  put(m,A+4*i,OBJECT+16*i);put(m,B+4*i,OBJECT+0x4000+16*i)
 put(m,LIST,A if c.array else 0);put(m,HANDLE,0x9876,2);put(m,COUNT,0x1234,2);put(m,TIMER,0x4321,2)
 m[MODE]=0x71;m[RATE]=0x72;m[COLOR]=0x73;m[STATUS]=c.status&255
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+256}
def action(m,c,target,ordinal):
 if target==DISPOSE and ordinal==1 and c.plan==1:put(m,LIST,B)
 if target==DISPOSE and ordinal==1 and c.plan==2:put(m,HANDLE,0x4567,2);m[STATUS]=9
 if target==FREE and c.plan==2:put(m,LIST,B)
 if target==SOUND and c.plan==2:put(m,TIMER,0x1111,2);put(m,COUNT,0x2222,2)
def reference(c,entry):
 m=fixture(c);calls=[];ordinal=0
 if entry==INIT:
  m[MODE]=m[STATUS]=0;put(m,TIMER,600,2);m[RATE]=240;m[COLOR]=20;put(m,COUNT,0,2);put(m,LIST,0)
 else:
  if c.state==2:
   m[MODE]=m[STATUS]=0
   if read(m,LIST):
    for i in range(300):
     base=read(m,LIST);p=read(m,base+4*i)
     if p:
      ordinal+=1;calls.append((DISPOSE,(p,)));action(m,c,DISPOSE,ordinal)
      put(m,read(m,LIST)+4*i,0)
    p=read(m,LIST);calls.append((FREE,(p,)));action(m,c,FREE,ordinal);put(m,LIST,0)
   calls.append((SOUND,(read(m,HANDLE,2),)));action(m,c,SOUND,ordinal)
   put(m,TIMER,0,2);put(m,COUNT,0,2)
  elif c.state==3:
   if m[STATUS]==0:put(m,TIMER,600,2)
   elif m[STATUS]==3:m[STATUS]=1
   m[MODE]=c.state&255
  else:m[MODE]=c.state&255
 return public(m),calls
class Machine(FactoryOracle):
 def __init__(self,w,c,entry):
  self.entrypoint=entry;self.dispose_count=0
  super().__init__(w,fixture(c),c,entry=entry,s=S,arguments=(c.state,))
 def record_call(self,t):
  assert t in (DISPOSE,FREE,SOUND),hex(t)
  a=tuple(self.r[4:5]);self.calls.append((t,a))
  if t==DISPOSE:self.dispose_count+=1
 def hook(self,t):
  action(self.memory,self.case,t,self.dispose_count)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
def program(path,name):
 d,r=payload(path,name);return bound_blob(d,r,S)
def streams(name,offset,n):
 rom=(root/'conker/conker.us.bin').read_bytes()
 return [struct.unpack_from('>%dI'%n,rom,offset)]+[program(out/(x+'.o'),name)for x in ('after','generated','generic')]
def run():
 progs={INIT:streams('func_15178EB0',0x1a6360,19),TRANS:streams('func_15178EFC',0x1a63ac,67)}
 count=0
 for phase,state,status,array,plan in itertools.product((0,8),(0,1,2,3,0xffffffff),(0,1,3,255),(0,1),range(3)):
  c=Case(phase,state,status,array,plan)
  for entry in (INIT,TRANS):
   want,calls=reference(c,entry)
   for words in progs[entry]:
    m=Machine(words,c,entry).run()
    assert (public(m.memory),m.calls)==(want,calls),(c,hex(entry),m.calls,calls)
  count+=1
 print('independent reset/transition model',count,'cases per entry across four streams, with list mutation during disposal',flush=True)
