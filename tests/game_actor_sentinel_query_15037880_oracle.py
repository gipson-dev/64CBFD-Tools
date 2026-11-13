from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_actor_sentinel_query_15037880_match as packet
root=packet.ROOT;out=packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15037880;ACTORS=0x800cc2d0;VIEWPTR=0x800dbff0;REFERENCE=0x800c3ff4;THRESH=0x8009862c;VIEW=0x40000;VIEW2=0x42000;OUT=0x30000
S=dict(D_800CC2D0=ACTORS,D_800DBFF0=VIEWPTR,D_800C3FF4=REFERENCE,D_8009862C=THRESH)
u32=lambda n:n&0xffffffff
s16=lambda n:((n&65535)^32768)-32768
f32=lambda n:floating(bits(n))
@dataclass(frozen=True)
class Case:
 phase:int=0;index:int=0;mode:int=0;kind:int=0;ref:int=0;threshold:int=0;alias:int=0

def actor(c):return u32(ACTORS+u32(c.index*0x32c))
def output(c):return (OUT,REFERENCE,VIEWPTR,VIEW+0x2f8,actor(c)+0x14,STACK+c.phase-16)[c.alias]
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-1024,1024)}
 for base,n in ((actor(c),0x32c),(VIEW,0x400),(VIEW2,0x400),(OUT,32),(VIEWPTR,16),(REFERENCE,16),(THRESH,4)):
  m.update({u32(base+i):0 for i in range(n)})
 a=actor(c);put(m,a+0x2f8,0xa5f8|c.mode,2);m[a+5]=c.kind;put(m,a+0x14,bits(3.0));put(m,a+0x1c,bits(4.0));put(m,VIEWPTR,VIEW)
 for i,v in enumerate((VIEW2,0x80000000,0x7fc12345)):put(m,VIEW+0x2f8+4*i,v)
 for i,v in enumerate((0x3f800000,0xc0200000,0x40400000)):put(m,VIEW2+0x2f8+4*i,v)
 vals=((0,-7,0),(3,-32768,4),(-32768,1,32767),(32767,-1,-32768))[c.ref]
 for i,v in enumerate(vals):put(m,REFERENCE+2*i,v&65535,2)
 put(m,THRESH,(0,0x41c80000,0x7f800000,0x7fc12345,0xbf800000)[c.threshold]);return m

def reference(c):
 m=fixture(c);a=actor(c);o=output(c);mode=read(m,a+0x2f8,2)&7
 if mode==1:
  for i in range(3):p=read(m,VIEWPTR);put(m,o+4*i,read(m,p+0x2f8+4*i))
  return m,1
 if mode==2:
  if m[a+5]==4:
   x=f32(floating(read(m,a+0x14))-float(s16(read(m,REFERENCE,2))));z=f32(floating(read(m,a+0x1c))-float(s16(read(m,REFERENCE+4,2))));d=f32(f32(x*x)+f32(z*z))
   if floating(read(m,THRESH))<d:return m,1
  for i in range(3):put(m,o+4*i,bits(float(s16(read(m,REFERENCE+i*2,2)))))
  return m,1
 return m,1 if mode==3 else 0
class Machine(FactoryOracle):
 def __init__(self,w,c):self.c=c;super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(u32(c.index),output(c)))
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected hook',hex(t)))
def program(path):raw,refs=payload(path,'func_15037880');return bound_blob(raw,refs,S)
