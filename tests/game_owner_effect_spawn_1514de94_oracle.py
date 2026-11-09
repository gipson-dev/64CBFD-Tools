"""Independent call contract and literal fault model for the owner effect spawner."""
from dataclasses import dataclass
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

ENTRY=0x1514DE94
OWNER,EFFECT,RECORD,MARK=0x30000,0x50000,0x60000,0x70000
PATTERNS=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC01234,0x7F801234,0xFFFFFFFF)
WINDOW,END=0x15099734,0x15099C00

@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 effect:int=EFFECT
 record:int=RECORD
 mode:int=0
 mutation:int=0
 phase:int=0
 seed:int=0

def symbols():
 return {n:int(n.split('_')[1],16)for n in('D_800A58AC','D_800A58B8','D_800A58C4','D_800A5E04','D_800BE9B4','func_15160CDC','func_15083568','func_15160A58','func_1514EC1C')}

def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,512)}
 for p,n in((OWNER,1024),(EFFECT,256),(RECORD,256),(MARK,32)):
  m.update({p+i:(i*29+c.seed)&255 for i in range(n)})
 for j,name in enumerate(('D_800A58AC','D_800A58B8','D_800A58C4')):
  for i in range(3):put(m,s[name]+4*i,PATTERNS[(c.seed+j*3+i)%len(PATTERNS)])
 put(m,s['D_800A5E04'],0x3C088723 if c.seed==0 else PATTERNS[c.seed%len(PATTERNS)])
 m[s['D_800BE9B4']]=c.mode
 return m

def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}

def effect(m,c,s,ordinal,home):
 put(m,MARK+4*ordinal,0x12340000+ordinal)
 if c.mutation&1 and ordinal<3:put(m,home,OWNER+16*(ordinal+1))
 if c.mutation&2 and ordinal==1:
  m[s['D_800BE9B4']]^=255
 if c.mutation&4:
  for n in('D_800A58AC','D_800A58B8','D_800A58C4'):
   for i in range(12):m[s[n]+i]^=0x5A
  put(m,s['D_800A5E04'],0xBF800000)

def reference(initial,c=Case(),s=None):
 s=symbols()if s is None else s;m=dict(initial);calls=[];snaps=[];home=STACK+c.phase;put(m,home,c.owner)
 def call(ordinal,name,args):
  calls.append((s[name],args));snaps.append((data(m,s['D_800A58AC'],12),data(m,s['D_800A58B8'],12),data(m,s['D_800A58C4'],12),read(m,EFFECT+56),read(m,OWNER+56)))
  effect(m,c,s,ordinal,home)
 call(0,'func_15160CDC',(read(m,home),12,s['D_800A58AC'],s['D_800A58B8'],read(m,s['D_800A5E04']),2,300,255,255,255,255,0,1,1,255,1))
 call(1,'func_15083568',(read(m,home),60,0x3F800000,0))
 if m[s['D_800BE9B4']]==0:put(m,c.effect+56,2400)
 call(2,'func_15160A58',(read(m,home),0,s['D_800A58C4'],2,300,11,255,255,255,2,0,0xFFFFFFFF,0,0,255,1))
 call(3,'func_1514EC1C',(c.record,read(m,home),25))
 return m,calls,snaps

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,syms=None,connected=None):
  self.s=symbols()if syms is None else syms;self.snaps=[];self.ordinal=0;self.target_entries=[]
  super().__init__(words,memory,c,entry=entry,arguments=(c.owner,),connected=connected)
 def record_call(self,t):
  counts={self.s['func_15160CDC']:16,self.s['func_15083568']:4,self.s['func_15160A58']:16,self.s['func_1514EC1C']:3,ENTRY:1}
  assert t in counts,('Unbounded owner-effect provider',hex(t));a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.target_entries.append(a);return
  self.snaps.append((data(self.memory,self.s['D_800A58AC'],12),data(self.memory,self.s['D_800A58B8'],12),data(self.memory,self.s['D_800A58C4'],12),read(self.memory,EFFECT+56),read(self.memory,OWNER+56)))
 def hook(self,t):
  c=self.case;ordinal=self.ordinal;self.ordinal+=1;effect(self.memory,c,self.s,ordinal,STACK+c.phase)
  value=(0xDEADBEEF,c.effect,c.record,0xABCD1234)[ordinal]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.snaps,m.current_pc,m.delay_of,m.all_accesses)
