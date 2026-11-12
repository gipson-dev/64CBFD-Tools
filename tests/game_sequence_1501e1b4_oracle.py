"""Guest execution for the timed sequence transition and helper effects."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_sequence_1501e1b4_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY=0x1501e1b4;PRED=0x1501e05c;FADE=0x1517ee40;SYNC=0x1000e17c;MODE=0x151f2cdc;AUDIO=0x151f2d6c;FINISH=0x1501df04
STATE=0x800c3c88;TIMER=STATE+1;ACTIVE=0x800c35ea;LIMIT=0x800c3640;CURRENT=0x800c35b0;TRIGGER=0x8008fd84;DELTA=0x800bea08
STACK=g.STACK;put,read=g.put,g.read
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 slot:int;state:int;active:int;predicate:int;gap:int;query:int;delta:int;timer:int;phase:int;mutation:int=0
 actor:int=0;mode:int=0;amount:int=0;fcsr:int=0

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for a,n in ((STATE,16),(ACTIVE,8),(LIMIT,16),(CURRENT,16),(TRIGGER,8),(DELTA,8)):m.update({a+i:(i*13+91)&255 for i in range(n)})
 put(m,STATE,c.state,1);put(m,TIMER,c.timer,1);put(m,ACTIVE+c.slot,c.active,1);put(m,CURRENT+4*c.slot,100)
 put(m,LIMIT+4*c.slot,(100+c.gap)&0xffffffff);put(m,TRIGGER,0xab,1);put(m,DELTA,c.delta&0xffffffff)
 return m
def public(m):return {k:v for k,v in m.items() if not STACK-1024<=k<STACK+1024}
def effect_pred(m,c):
 if c.mutation:put(m,LIMIT+4*c.slot,200);put(m,CURRENT+4*c.slot,101)
def reference(initial,c):
 m=dict(initial);calls=[]
 if c.state==0:
  if c.active==1:
   calls.append((PRED,(c.slot,)));effect_pred(m,c)
   if c.predicate:
    limit=read(m,LIMIT+4*c.slot);current=read(m,CURRENT+4*c.slot);put(m,TRIGGER,0,1)
    if signed(limit-current)>=91:
     put(m,STATE,1,1);put(m,TIMER,30,1);calls.extend(((FADE,(0,0,0,30,1,0)),(SYNC,()),(MODE,())))
     if c.query==1:calls.append((AUDIO,(0,0x2b02)))
     else:
      calls.append((MODE,()))
      if c.query==2:calls.append((AUDIO,(0,0x2b02)))
 elif c.state==1:
  if c.delta<c.timer:put(m,TIMER,(c.timer-c.delta)&255,1)
  else:
   put(m,TIMER,0,1);put(m,STATE,2,1);calls.append((FINISH,(c.slot,)));put(m,STATE,0,1)
 return public(m),calls

class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.case=c;super().__init__(code,fixture(c),c,entry=ENTRY);self.r[4]=c.slot;self.before=self.r[:]
 def record_call(self,t):
  n={PRED:1,FADE:6,SYNC:0,MODE:0,AUDIO:2,FINISH:1};assert t in n,hex(t)
  self.calls.append((t,tuple(map(g.u32,self.arguments(n[t])))))
 def hook(self,t):
  c=self.case
  if t==PRED:effect_pred(self.memory,c)
  elif t==FINISH:put(self.memory,STATE,0x99,1)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
  self.r[2]=c.predicate if t==PRED else c.query if t==MODE else 0x12345678

def run(s):
 one,_=match.pad_both(s);raw,refs=match.payload(one);codes=(s['raw_words'],s['retail_words'],tuple(bound_blob(raw,refs,s['symbols'])));assert codes[0]==codes[1]==codes[2]
 count=0;visits=set()
 for slot,state,active,pred,gap,query,phase,mutation in itertools.product(range(2),(0,1,2,255),(0,1),(0,1),(90,91),range(3),(0,8),(0,1)):
  c=Case(slot,state,active,pred,gap,query,(gap-90)*30,30,phase,mutation);expected,calls=reference(fixture(c),c)
  for code in codes:
   m=Oracle(code,c).run();assert (public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
   assert m.r[29]==STACK+c.phase;visits.update(m.visits)
  count+=1
 for delta,timer in itertools.product((-2147483648,-1,0,1,29,30,31,2147483647),(0,1,30,255)):
  c=Case(1,1,1,0,0,0,delta,timer,0);expected,calls=reference(fixture(c),c)
  for code in codes:
   m=Oracle(code,c).run();assert (public(m.memory),m.calls)==(expected,calls),c
  count+=1
 return dict(cases=count,bodies=3,words_visited=len(visits),scope='modeled helper results and side effects; valid slots')
