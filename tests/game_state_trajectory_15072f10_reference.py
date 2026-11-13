from importlib.machinery import SourceFileLoader
from pathlib import Path
import itertools
from tools.tests import game_state_trajectory_15072f10_oracle as G
put=G.put;read=G.read;bits=G.bits;floating=G.floating
f32=lambda x:floating(bits(x))
s8=lambda n:(n^128)-128
s16=lambda n:(n^32768)-32768

def reference(c):
 m=G.fixture(c);home=G.STACK+c.phase;actor=read(m,G.CURRENT);pitch=s8(m[actor+0x1d1]);state=read(m,actor+0x31c);put(m,state+0x24,(read(m,state+0x24,2)-1)&65535,2)
 actor=read(m,G.CURRENT);state=read(m,actor+0x31c);yaw=(read(m,actor+0x7a,2)-s16(read(m,state+0x12,2)))&65535
 first=(yaw,bits(2000.0),bits(f32(float(pitch*200)*0.0054931640625)),home-4,home-8,home-12)
 x,z,y=((11.25,-22.5,33.75)if not c.output else(-1.25,2.5,-3.75))
 for ptr,v in ((first[5],y),(first[3],x),(first[4],z)):put(m,ptr,bits(v))
 if c.mutation&1:put(m,G.CURRENT,G.ACTOR2)
 if c.mutation&2:put(m,G.SCALE,bits(-.5))
 if c.mutation&4:m[G.PLAYER]=0x6c
 actor=read(m,G.CURRENT);scale=floating(read(m,G.SCALE));ax,ay,az=[floating(read(m,actor+off))for off in (0x14,0x18,0x1c)];height=s16(read(m,actor+0xd6,2));wx=f32(f32(x*scale)+ax);wz=f32(f32(z*scale)+az);wy=f32(f32(y*scale)+ay)
 args=(actor,bits(ax),bits(f32(ay+float(height))),bits(az),bits(wx),bits(wy),bits(wz),m[G.PLAYER],18);put(m,G.MARK,0x13579bdf)
 return G.public(m,c),[(G.VECTOR,first),(G.SUBMIT,args)],0xdeadbeef

def run():
 programs=G.programs();count=0
 for pitch,timer,angle,offset,mutation,output,phase in itertools.product((-128,-1,0,1,127),(-32768,-1,0,1,32767),(0,0xffff),(-32768,0,32767),range(8),(0,1),(0,8)):
  c=G.Case(phase,pitch,timer,angle,offset,mutation,output);initial=G.fixture(c);expected=reference(c)
  for w in programs:
   machine=G.Machine(w,c,initial.copy()).run();actual=(G.public(machine.memory,c),machine.calls,machine.r[2]);assert actual==expected,(c,actual[1:],expected[1:])
  count+=1
 print('independent model cases',count)
