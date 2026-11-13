from dataclasses import dataclass
from pathlib import Path
import itertools,sys
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_151DCFD8';ENTRY=0x151DCFD8
SYMS=dict(D_800E0A20=0x800E0A20,D_800E0A24=0x800E0A24,D_800E0A28=0x800E0A28,D_800E0A2C=0x800E0A2C,D_8002BD10=0x8002BD10,D_8002BD14=0x8002BD14,D_80042A58=0x80042A58,__osEepromTimerQ=0x80042A78,D_80042A90=0x80042A90,osRecvMesg=0x10023440,func_151DD4E0=0x151DD4E0,__ll_mul=0x10026968,__ull_div=0x10026868,osSetTimer=0x10024A40)
MASK=0xffffffff
@dataclass(frozen=True)
class Case: pending:int;recv:int;remaining:int;write:int;mode:int;clock:int;mutation:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for name,n in (('D_800E0A20',16),('D_8002BD10',8),('D_80042A58',64),('__osEepromTimerQ',24),('D_80042A90',4)):
  base=SYMS[name];m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(m,SYMS['D_800E0A20'],0x30000 if c.pending else 0);m[SYMS['D_800E0A24']]=255;put(m,SYMS['D_800E0A28'],0x50000);put(m,SYMS['D_800E0A2C'],c.remaining&MASK);put(m,SYMS['D_8002BD10'],c.clock,8);return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m,entry=ENTRY,arguments=None,connected=None):self.c=c;super().__init__(words,m,c,entry=entry,s=SYMS,arguments=(c.mode&MASK,) if arguments is None else arguments,connected=connected)
 def record_call(self,t):
  sizes={'osRecvMesg':3,'func_151DD4E0':3,'__ll_mul':4,'__ull_div':4,'osSetTimer':8}
  if t==ENTRY:self.calls.append((t,tuple(self.arguments(1))));return
  name=next(k for k,v in SYMS.items() if v==t);a=tuple(self.arguments(sizes[name]));self.calls.append((t,(a[0],*a[2:]) if name=='osSetTimer' else a))
 def hook(self,t):
  c=self.c;name=next(k for k,v in SYMS.items() if v==t);a=self.calls[-1][1];high=None
  if name=='osRecvMesg':
   value=c.recv
   if c.mutation&1:put(self.memory,SYMS['D_800E0A2C'],9)
  elif name=='func_151DD4E0':
   value=c.write
   if c.mutation&2:put(self.memory,SYMS['D_800E0A2C'],17);self.memory[SYMS['D_800E0A24']]=254;put(self.memory,SYMS['D_800E0A28'],0x60000)
  elif name in ('__ll_mul','__ull_div'):
   x=(a[0]<<32)|a[1];y=(a[2]<<32)|a[3];r=(x*y)&0xffffffffffffffff if name=='__ll_mul' else x//y;high=r>>32;value=r&MASK
  else:assert name=='osSetTimer';value=0xfeedface
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=high if high is not None else value&MASK
  if high is not None:self.r[3]=value
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def reference(initial,c):
 m=initial.copy();calls=[]
 def call(name,*args):calls.append((SYMS[name],tuple(a&MASK for a in args)))
 def done():return public(m),calls,0
 if not read(m,SYMS['D_800E0A20']):return done()
 call('osRecvMesg',SYMS['__osEepromTimerQ'],0,c.mode)
 if c.mutation&1:put(m,SYMS['D_800E0A2C'],9)
 if c.recv==-1:return done()
 n=read(m,SYMS['D_800E0A2C']);n=n-(1<<32) if n&0x80000000 else n
 if n<=0:put(m,SYMS['D_800E0A20'],0);put(m,SYMS['D_800E0A2C'],0);return done()
 call('func_151DD4E0',read(m,SYMS['D_800E0A20']),m[SYMS['D_800E0A24']],read(m,SYMS['D_800E0A28']))
 if c.mutation&2:put(m,SYMS['D_800E0A2C'],17);m[SYMS['D_800E0A24']]=254;put(m,SYMS['D_800E0A28'],0x60000)
 if c.write:put(m,SYMS['D_800E0A20'],0);put(m,SYMS['D_800E0A2C'],0);return done()
 put(m,SYMS['D_800E0A2C'],(read(m,SYMS['D_800E0A2C'])-8)&MASK);m[SYMS['D_800E0A24']]=(m[SYMS['D_800E0A24']]+1)&255;put(m,SYMS['D_800E0A28'],(read(m,SYMS['D_800E0A28'])+8)&MASK)
 clock=read(m,SYMS['D_8002BD10'],8);call('__ll_mul',0,12000,clock>>32,clock&MASK);p=(clock*12000)&0xffffffffffffffff;call('__ull_div',p>>32,p&MASK,0,1000000);deadline=p//1000000
 call('osSetTimer',SYMS['D_80042A58'],deadline>>32,deadline&MASK,0,0,SYMS['__osEepromTimerQ'],SYMS['D_80042A90']);return public(m),calls,1
def words():
 programs=[bound_blob(*payload(out/x,NAME),SYMS) for x in ('retail.o','after.o','generated.o','generic.o')]
 return programs

def run():
 programs=words();assert programs[0]==programs[1]==programs[2]==programs[3]
 count=0;visited=set()
 for pending,recv,remaining,write,mode,clock,mutation in itertools.product((0,1),(-1,0,1),(-1,0,1,8,9),(0,-1),(-1,0,1),(0,0xffffffff,0x100000000,0xffffffffffffffff),(0,1,2,3)):
  c=Case(pending,recv,remaining,write,mode,clock,mutation);initial=fixture(c);expected=reference(initial,c)
  for p in programs:
   m=Machine(p,c,initial.copy()).run();assert (public(m.memory),m.calls,m.r[2])==expected,c;visited.update(m.visits)
  count+=1
 assert set(range(ENTRY,ENTRY+348,4))<=visited
 print(count,'guest cases per stream; every retail instruction visited; EEPROM providers modeled')
