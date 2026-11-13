from pathlib import Path
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT
ENTRY,FREE=0x1517ABB0,0x10004074
GROUPS,DESC,COUNTS=0x800DD460,0x800A7230,0x800C4310
ROOTS=(0x250000,0x260000);ALT=(0x252000,0x262000);ARENA=0x300000
@dataclass(frozen=True)
class Case:
 count0:int;count1:int;slots0:int;slots1:int;pattern:int;mode:int;enabled:int;phase:int=0
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for group in range(2):
  put(m,GROUPS+4*group,ROOTS[group] if c.enabled&(1<<group) else 0)
  for j in range(8):m[DESC+8*group+j]=0
  m[DESC+8*group]=group;m[DESC+8*group+1]=(c.slots0,c.slots1)[group]
  put(m,COUNTS+2*group,(c.count0,c.count1)[group],2)
  for alt in range(2):
   base=(ROOTS,ALT)[alt][group]
   for row in range(3):
    at=ARENA+group*0x1000+alt*0x400+row*0x80;put(m,base+4*row,at)
    for col in range(3):
     for j in range(8):m[at+8*col+j]=(group*13+row*7+col*3+j+0x40)&255
     index=group*9+row*3+col+alt
     payload=0 if (index+c.pattern)%5==0 else 0x350000+index*16
     put(m,at+8*col,payload);m[at+8*col+4]=(0,1,2,255)[(index+c.pattern)%4]
 return m
def effect(m,mode,ordinal):
 if ordinal!=1:return
 if mode==1:m[DESC+1]=1
 elif mode==2:put(m,COUNTS,1,2)
 elif mode==3:put(m,GROUPS,ALT[0])
 elif mode==4:m[DESC]=1
class Expiry(Oracle):
 def __init__(self,words,m,c):
  self.case=c;self.frees=0
  super().__init__(words,m,0,c.phase,ENTRY)
 def record_call(self,t):
  assert t==FREE
  args=tuple(self.arguments(1));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==FREE;self.frees+=1;effect(self.memory,self.case.mode,self.frees)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def reference(initial,c):
 m=dict(initial);calls=[]
 for group in range(2):
  d=DESC+8*group
  if read(m,GROUPS+4*group):
   row=0;count=read(m,COUNTS+2*m[d],2)
   while row<count:
    slots=m[d+1]
    if slots:
     col=0
     while True:
      p=read(m,GROUPS+group*4);rowptr=read(m,p+row*4);entry=rowptr+col*8;allocation=read(m,entry)
      if allocation:
       age=m[entry+4]
       if age:m[entry+4]=(age-1)&255
       else:
        calls.append((FREE,(allocation,)));effect(m,c.mode,len(calls));p=read(m,GROUPS+group*4);rowptr=read(m,p+row*4);put(m,rowptr+col*8,0)
       slots=m[d+1]
      col+=1
      if not col<slots:break
     count=read(m,COUNTS+2*m[d],2)
    row+=1
 return m,calls
def run():
 obj=out/'variant-split.o';_,fs,_=parse_object(obj);pos=fs['func_1517ABB0']['value']
 raw=list(struct.unpack('>84I',sections(out/'variant-split.elf')['.text'][1][pos:pos+336]))
 retail=list(struct.unpack_from('>84I',(root/'conker/conker.us.bin').read_bytes(),0x1A8060));total=0;seen=set()
 for count0,count1,slots0,slots1,pattern,mode,enabled in itertools.product((0,1,3),(0,2),(0,1,3),(0,2),(0,1,2,3),(0,1,2,3,4),(0,1,2,3)):
  c=Case(count0,count1,slots0,slots1,pattern,mode,enabled);initial=fixture(c);wanted,calls=reference(initial,c)
  models=[Expiry(w,initial,c).run() for w in (retail,raw)]
  for m in models:
   public=lambda memory:{a:b for a,b in memory.items() if not STACK-256<=a<STACK+256}
   assert public(m.memory)==public(wanted) and m.calls==calls,(c,m.calls,calls)
  assert models[0].trace==models[1].trace and models[0].memory==models[1].memory,(c,'trace or state')
  seen.update(p-ENTRY for p in models[0].visits);total+=1
 print(total,'guest cases; visited',len(seen),'of 84 words; provider mutation and live reloads checked',flush=True)
 aliases=0
 for age,phase in itertools.product((0,1),(0,8)):
  c=Case(1,0,1,0,0,0,1,phase);initial=fixture(c);put(initial,ROOTS[0],DESC);initial[DESC+4]=age
  models=[Expiry(w,initial,c).run() for w in (retail,raw)]
  assert models[0].memory==models[1].memory and models[0].calls==models[1].calls and models[0].trace==models[1].trace
  aliases+=1
 for phase in (0,8):
  c=Case(1,0,1,0,0,0,1,phase);initial=fixture(c);base=STACK+phase+64;entry=STACK+phase+128
  put(initial,GROUPS,base);put(initial,base,entry);put(initial,entry,0x350000);initial[entry+4]=0
  models=[Expiry(w,initial,c).run() for w in (retail,raw)]
  assert models[0].memory==models[1].memory and models[0].calls==models[1].calls and models[0].trace==models[1].trace
  aliases+=1
 print(aliases,'descriptor and caller-stack alias cases',flush=True)
 return dict(cases=total,visited=len(seen),aliases=aliases,missing=[hex(i) for i in range(0,336,4) if i not in seen])
if __name__=='__main__':print(run())
