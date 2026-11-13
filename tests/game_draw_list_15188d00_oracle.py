from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_draw_list_15188d00_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
ENTRY=0x15188d00;HEAD=0x800df7c8;MATRIX=0x80089470;TABLE=0x8008d590
HANDLERS=(0x151895f4,0x151897a4);OUTPUT=0x30000;NODES=(0x60000,0x60100,0x60200,0x60300)
S=dict(D_800DF7C8=HEAD,D_80089470=MATRIX,D_8008D590=TABLE)
@dataclass(frozen=True)
class Case:
 phase:int;which:int;view:int;length:int;pattern:int;mutation:int;alias:int=0
def output(c):return (OUTPUT,HEAD,NODES[3]+0x20)[c.alias]
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-256,128)}
 for base,n in ((OUTPUT,0x200),(HEAD-16,0x80),(TABLE,0x20),*((x,0x100) for x in NODES)):
  m.update({base+i:(i*37+0x6d)&255 for i in range(n)})
 for i,x in enumerate(NODES):
  m[x]=(i+c.pattern)&1
  put(m,x+0xc,NODES[i+1] if i+1<c.length else 0)
 put(m,HEAD+c.which*4,NODES[0] if c.length else 0)
 for i,x in enumerate(HANDLERS):put(m,TABLE+i*4,x)
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def s16(n):return ((n&65535)^32768)-32768
def emit(m,cursor,w0,w1,first=False):
 if first:put(m,cursor+4,w1);put(m,cursor,w0)
 else:put(m,cursor,w0);put(m,cursor+4,w1)
def effect(m,c,node,cursor,ordinal):
 if c.mutation==1 and ordinal==1:put(m,node+0xc,NODES[2] if c.length>=3 else 0)
 if c.mutation==2 and ordinal==1:put(m,node+0xc,0)
 if c.mutation==3 and ordinal==1 and c.length>=2:m[NODES[1]]^=1
 put(m,cursor,0xA1000000|ordinal);put(m,cursor+4,node)
 return cursor+8
def render(m,c,which,cursor):
 node=read(m,HEAD+which*4);calls=[]
 if node:
  for i,(a,b) in enumerate(((0xDA380003,MATRIX),(0xD9FFFFFF,0x00200004),(0xD9EEFFFF,0),(0xE7000000,0),(0xE2001E01,0),(0xEC000000,255))):
   emit(m,cursor,a,b,i in(0,5));cursor+=8
  while node:
   target=read(m,TABLE+4*m[node]);calls.append((target,(cursor,node,s16(c.view)&0xffffffff)))
   cursor=effect(m,c,node,cursor,len(calls));node=read(m,node+0xc)
 return calls,cursor
def reference(c):
 m=fixture(c);calls,cursor=render(m,c,c.which,output(c))
 return public(m),calls,cursor
class Machine(FactoryOracle):
 def __init__(self,w,c):super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(output(c),c.which,c.view))
 def record_call(self,t):
  assert t in HANDLERS,hex(t);self.calls.append((t,tuple(self.r[4:7])))
 def hook(self,t):
  c=self.case;a=self.calls[-1][1]
  result=effect(self.memory,c,a[1],a[0],len(self.calls))
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=result
def program(path):
 d,r=payload(path,'func_15188D00');return bound_blob(d,r,S)
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 programs=[struct.unpack_from('>82I',rom,0x1b61b0)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
 count=0
 for phase,which,view,length,pattern,mutation,alias in itertools.product((0,8),(-1,0,1,2),(0,1,0x7fff,0x8000,0xffff,0x12345678),range(4),(0,1),range(4),range(3)):
  c=Case(phase,which,view,length,pattern,mutation,alias);want,calls,result=reference(c)
  for words in programs:
   try:m=Machine(words,c).run()
   except Exception as e:raise AssertionError(('guest failed',c)) from e
   assert (public(m.memory),m.calls,m.r[2])==(want,calls,result),(c,m.calls,calls)
  count+=1
 print('independent draw-list model',count,'cases across four streams with head aliases and callback mutation',flush=True)
