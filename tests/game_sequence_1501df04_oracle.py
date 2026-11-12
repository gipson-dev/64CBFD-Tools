"""Bounded guest model for sequence completion and actor-byte cleanup."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_sequence_1501df04_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY=0x1501df04;POLL=0x100127d0;STOP=0x151f2ba8;FIND=0x15072208;RELEASE=0x15060f28;ADVANCE=0x1501de18;FADE=0x1517ee40;SYNC=0x1000e17c
ACTORS=0x800cc2d0;END=0x800d121c;PENDING=0x800c3c99;BUSY=0x800c35c4;FLAG_A=0x800c35a9;FLAG_B=0x800c3c8a;FLAG_C=0x800c3c8d;CLEAR=0x800c3663;MODE=0x800dbff4;FINISH=0x800c3672
STACK=g.STACK;put,read=g.put,g.read
@dataclass(frozen=True)
class Case:
 slot:int;provider:int;found:int;pattern:int;fa:int;fb:int;fc:int;phase:int
 actor:int=0;mode:int=0;amount:int=0;fcsr:int=0

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for a in range(ACTORS,END):m[a]=(a*13+91)&255
 for i in range(25):put(m,ACTORS+i*0x32c,i%2);put(m,ACTORS+i*0x32c+0xa4,0x31425364)
 for a,v in ((PENDING,int(c.pattern!=0)),(BUSY,0),(FLAG_A,c.fa),(FLAG_B,c.fb),(FLAG_C,c.fc),(CLEAR,9),(MODE,8),(FINISH,7)):put(m,a,v,1)
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}
def advance(m,c,n):
 if c.pattern==1 or (c.pattern==2 and n>=2):put(m,PENDING,0,1)
 if c.pattern==3:put(m,BUSY,1,1)
def reference(initial,c):
 m=dict(initial);calls=[(POLL,())]
 if c.provider:calls.append((STOP,()))
 calls.append((FIND,(ACTORS,0)))
 if c.found:calls.append((RELEASE,(ACTORS+0x32c,0)))
 pending=read(m,PENDING,1);calls.append((ADVANCE,(c.slot,)));advance(m,c,1);n=1
 if pending and not read(m,BUSY,1):
  while True:
   pending=read(m,PENDING,1);n+=1;calls.append((ADVANCE,(c.slot,)));advance(m,c,n)
   if not pending or read(m,BUSY,1):break
 assert n<=3
 if not c.fa and c.fb!=1 and not c.fc:calls.append((FADE,(0,0,0,30,0,0)))
 for i in range(25):
  if read(m,ACTORS+i*0x32c):put(m,ACTORS+i*0x32c+0xa4,0,1)
 put(m,CLEAR,0,1);calls.append((SYNC,()));put(m,MODE,9,1);put(m,FINISH,9,1);put(m,MODE,4,1);put(m,FINISH,1,1)
 return public(m),calls

class Oracle(g.Oracle):
 def __init__(self,code,c):self.case=c;self.advances=0;super().__init__(code,fixture(c),c,entry=ENTRY);self.r[4]=c.slot;self.before=self.r[:]
 def record_call(self,t):
  counts={POLL:0,STOP:0,FIND:2,RELEASE:2,ADVANCE:1,FADE:6,SYNC:0};assert t in counts,hex(t)
  self.calls.append((t,tuple(map(g.u32,self.arguments(counts[t])))))
 def hook(self,t):
  c=self.case;value=0x12345678
  if t==POLL:value=c.provider
  elif t==FIND:value=ACTORS+0x32c if c.found else 0
  elif t==ADVANCE:self.advances+=1;advance(self.memory,c,self.advances)
  elif t==SYNC:assert read(self.memory,CLEAR,1)==0;put(self.memory,MODE,9,1);put(self.memory,FINISH,9,1)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=value

def words(path,state):raw,refs=match.payload(path);return tuple(bound_blob(raw,refs,state['symbols']))
def run(s):
 one,_=match.pad_both(s);codes=(s['raw_words'],s['retail_words'],words(one,s));assert codes[1]==codes[2]
 count=0;seen=set()
 for slot,provider,found,pattern,fa,fb,fc,phase in itertools.product(range(2),range(2),range(2),range(4),range(2),range(2),range(2),(0,8)):
  c=Case(slot,provider,found,pattern,fa,fb,fc,phase);expected,calls=reference(fixture(c),c)
  for code in codes:
   m=Oracle(code,c).run();assert (public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
   assert m.r[29]==STACK+c.phase;seen.update(m.visits)
  count+=1
 return dict(cases=count,bodies=3,words_visited=len(seen),scope='25 actor records and bounded modeled helper mutations')
