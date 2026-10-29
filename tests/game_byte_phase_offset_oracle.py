"""Signed byte phase updates, live alias order and original cosine/caller routes."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_byte_phase_offset_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_record_planar_phase_oracle import trig,TRIG_TABLE

PHASE,RATE,AMP,FIRST,SECOND,ALT_PHASE,ALT_AMP,ALT_FIRST,ALT_SECOND,OWNER=(0x200000+0x1000*i for i in range(10))
TRIG,TICKS=0x151423D8,0x800BE9E4
CALLERS=((0x15131D9C,0x15F24C,0xA8,0xAA,0xAC),(0x15192308,0x1BF7B8,0xAC,0xAE,0xA8))
u32=lambda n:n&0xFFFFFFFF
s8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
 angles:tuple=(17,201)
 rates:tuple=(3,241)
 amplitudes:tuple=(0x40400000,0xC1000000)
 base:int=0x3F400000
 results:tuple=(0x3FA00000,0xBF000000)
 ticks:int=3
 mode:int=0
 phase:int=0
 phases:int=PHASE
 rate:int=RATE
 amp:int=AMP
 first:int=FIRST
 second:int=SECOND

def symbols():return dict(func_151423D8=TRIG,D_800BE9E4=TICKS)
def args(c):return(c.phases,c.rate,c.base,c.amp,c.first,c.second)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def fixture(c=Case(),s=None,table=None):
 s=s or symbols();m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2304)}
 for base in(PHASE,RATE,AMP,FIRST,SECOND,ALT_PHASE,ALT_AMP,ALT_FIRST,ALT_SECOND,OWNER,c.phases,c.rate,c.amp,c.first,c.second,s['D_800BE9E4']):
  if not STACK-2048<=base<STACK+2304:
   for i in range(-16,256):m.setdefault(u32(base+i),(i*13+0x59)&255)
 for p in(c.first,c.second,ALT_FIRST,ALT_SECOND):put(m,p,0x43210000)
 for p in(c.amp,ALT_AMP):
  for i,v in enumerate(c.amplitudes):put(m,p+4*i,v)
 for p in(c.phases,ALT_PHASE):
  for i,v in enumerate(c.angles):m[p+i]=v
 for i,v in enumerate(c.rates):m[c.rate+i]=v
 put(m,s['D_800BE9E4'],c.ticks)
 if table is not None:
  assert len(table)==260
  m.update({TRIG_TABLE+i:b for i,b in enumerate(table)})
 return m

def observe(m,c,s):return(m[c.phases],m[c.phases+1],read(m,s['D_800BE9E4']),read(m,c.first),read(m,c.second))
def effect(m,c,home,ordinal,s):
 if ordinal==0:
  if c.mode&1:put(m,c.amp,0xC0F00000);m[c.phases+1]=0x91
  if c.mode&2:
   for at,value in((0,ALT_PHASE),(8,0xC0200000),(12,ALT_AMP),(16,ALT_FIRST),(20,ALT_SECOND)):put(m,home+at,value)
 else:
  if c.mode&4:put(m,read(m,home+12)+4,0x41380000);put(m,s['D_800BE9E4'],0x87654321);m[c.rate]=0xA7
  if c.mode&8:
   for at,value in((8,0x3F100000),(12,ALT_AMP),(20,ALT_SECOND)):put(m,home+at,value)

def result(sample,amplitude,base):return bits(floating(bits(floating(sample)*floating(amplitude)))+floating(base))
def reference(initial,c=Case(),s=None,connected=False,home=None):
 s=s or symbols();m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];snapshots=[]
 for at,value in((0,c.phases),(8,c.base),(12,c.amp),(16,c.first),(20,c.second)):put(m,home+at,value)
 rate0=s8(m[c.rate]);ticks=read(m,s['D_800BE9E4']);p0=m[c.phases];p1=m[c.phases+1]
 value=u32(p0+rate0*ticks);m[c.phases]=value&255
 ticks=read(m,s['D_800BE9E4']);rate1=s8(m[c.rate+1]);m[c.phases+1]=(p1+rate1*ticks)&255
 angle=(value-64)&255
 for ordinal in range(2):
  if ordinal==0:put(m,home,c.phases)
  else:angle=(m[read(m,home)+1]-64)&255
  calls.append((s['func_151423D8'],(angle,)));snapshots.append(observe(m,c,s))
  sample=trig(m,angle)if connected else c.results[ordinal]
  if connected:put(m,home-24,angle)
  else:
   effect(m,c,home,ordinal,s)
   for i in range(4):put(m,home-24+4*i,0xB5000000+i)
  amplitude=read(m,read(m,home+12)+4*ordinal);base=read(m,home+8);output=read(m,home+16+4*ordinal)
  put(m,output,result(sample,amplitude,base))
 return m,calls,snapshots

class OffsetOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=args(c)if arguments is None else arguments)
  self.ordinal=0;self.snapshots=[];self.target_entries=[]
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==7:self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
  else:super().execute(word)
 def record_call(self,t):
  n={source.ENTRY:6,self.syms['func_151423D8']:1}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==source.ENTRY:self.target_home=self.r[29];self.target_entries.append(a)
  else:self.snapshots.append(observe(self.memory,self.case,self.syms))
 def hook(self,t):
  assert t==self.syms['func_151423D8']and self.ordinal<2
  effect(self.memory,self.case,self.target_home,self.ordinal,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=self.case.results[self.ordinal];self.ordinal+=1

def helpers(rom):return dict(zip(range(TRIG,TRIG+108,4),struct.unpack_from('>27I',rom,0x16F888)))
def caller_case(c,index):
 _,_,phase,rate,base=CALLERS[index]
 return replace(c,phases=OWNER+phase,rate=OWNER+rate,amp=OWNER+0xB0,first=OWNER+0x38,second=OWNER+0x3C)
def caller_machine(rom,words,c=Case(),index=0,connected=False,table=None,caller_words=None):
 c=caller_case(c,index);entry,pos,_,_,base=CALLERS[index];initial=fixture(c,table=table);put(initial,OWNER+base,c.base)
 code=helpers(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
 body=struct.unpack_from('>20I',rom,pos)if caller_words is None else caller_words
 m=OffsetOracle(body,initial,c,entry=entry,connected=code,arguments=(OWNER,0x87654321))
 return m,initial,c
