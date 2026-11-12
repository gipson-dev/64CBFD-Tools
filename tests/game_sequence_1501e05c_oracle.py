"""Bounded MIPS model for sequence-transition input gating."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_sequence_1501e05c_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY=0x1501e05c;HELPER=0x1501d2c4;SCENE=0x800be9f0;TRIGGER=0x8008fd84;EVENT=0x800c35e8;BUTTONS=0x800be710;MODE=0x8000030c;CURRENT=0x800c35b0;LIMIT=0x800c3640;LOCK=0x800c3c9c;OVERRIDE=0x800d2e40;FORCE=0x800c3c99
STACK=g.STACK;put,read=g.put,g.read
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 slot:int;scene:int;trigger:int;event:int;buttons:int;hw:int;lock:int;override:int;force:int;answer:int;mutation:int;phase:int
 start:int=300;actor:int=0;mode:int=0;amount:int=0;fcsr:int=0

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for a,n in ((SCENE,4),(TRIGGER,1),(EVENT,4),(BUTTONS,2),(MODE,4),(CURRENT,8),(LIMIT,8),(LOCK,1),(OVERRIDE,1),(FORCE,1)):m.update({a+i:0 for i in range(n)})
 put(m,SCENE,c.scene);put(m,TRIGGER,c.trigger,1);put(m,EVENT, c.event,1);put(m,EVENT+c.slot, c.event,1);put(m,BUTTONS,c.buttons,2);put(m,MODE,c.hw)
 put(m,CURRENT,c.start&0xffffffff);put(m,CURRENT+4*c.slot,c.start&0xffffffff);put(m,LIMIT+4*c.slot,(c.start+31)&0xffffffff)
 put(m,LOCK,c.lock,1);put(m,OVERRIDE,c.override,1);put(m,FORCE,c.force,1);return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}
def effect(m,c):
 if c.mutation:put(m,FORCE,1,1);put(m,CURRENT+4*c.slot,0xffffffff);put(m,LIMIT+4*c.slot,0)
def reference(initial,c):
 m=dict(initial);calls=[];scene=read(m,SCENE)
 if scene==29:
  if read(m,TRIGGER,1):put(m,TRIGGER,0,1);return public(m),calls,1
  if read(m,EVENT,1)!=5:return public(m),calls,0
 if scene==33:
  return public(m),calls,int(bool(read(m,BUTTONS,2)&0x1000) and read(m,MODE)==1 and signed(read(m,CURRENT))>=301)
 if not read(m,BUTTONS,2)&0x20 or read(m,LOCK,1):return public(m),calls,0
 if read(m,OVERRIDE,1):return public(m),calls,1
 calls.append((HELPER,(scene,read(m,EVENT+c.slot,1))));effect(m,c)
 if c.answer and (read(m,FORCE,1) or signed(read(m,CURRENT+4*c.slot)+30)<signed(read(m,LIMIT+4*c.slot))):return public(m),calls,1
 return public(m),calls,0
class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.case=c;super().__init__(code,fixture(c),c,entry=ENTRY);self.r[4]=c.slot;self.before=self.r[:]
 def record_call(self,t):
  assert t==HELPER;self.calls.append((t,tuple(map(g.u32,self.arguments(2)))))
 def hook(self,t):
  assert t==HELPER;effect(self.memory,self.case)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=self.case.answer
def run(s):
 one,_=match.pad_both(s);raw,refs=match.payload(one);codes=(s['raw_words'],s['retail_words'],tuple(bound_blob(raw,refs,s['symbols'])));assert codes[0]==codes[1]==codes[2]
 count=0;seen=set()
 for slot,scene,trigger,event,buttons,hw,lock,override,force,answer,mutation,start in itertools.product(range(2),(29,33,17),(0,0x80),(4,5),(0,0x20,0x1000,0x1020),(0,1),(0,1),(0,1),(0,1),(0,1),(0,1),(300,301)):
  c=Case(slot,scene,trigger,event,buttons,hw,lock,override,force,answer,mutation,8 if slot else 0,start);expected,calls,result=reference(fixture(c),c)
  for code in codes:
   m=Oracle(code,c).run();assert (public(m.memory),m.calls,m.r[2])==(expected,calls,result),(c,m.calls,calls,m.r[2],result)
   assert m.r[29]==STACK+c.phase;seen.update(m.visits)
  count+=1
 return dict(cases=count,bodies=3,words_visited=len(seen),scope='valid two-slot inputs and modeled helper side effects')
