"""Planar phase offsets: literal read order, alias effects and retained trig callers."""
from dataclasses import dataclass
from tools.experiments import game_record_planar_phase_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
RECORD,AMP,PHASE,RATE,ALT,ALT_AMP,ALT_PHASE,ALT_RATE=(0x200000+i*0x10000 for i in range(8))
TRIG_TABLE=0x8009A220
SYMBOLS=dict(func_151423D8=source.TRIG,D_800BE9E4=source.TICKS)
mul=lambda a,b:bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
 angles:tuple=(17,201)
 rates:tuple=(3,241)
 amplitudes:tuple=(0x40400000,0xC1000000)
 results:tuple=(0x3FA00000,0xBF000000)
 ticks:int=3
 mode:int=0
 phase:int=0
 record:int=RECORD
 amp:int=AMP
 phases:int=PHASE
 rate:int=RATE

def fixture(c=Case(),symbols=SYMBOLS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(RECORD,AMP,PHASE,RATE,ALT,ALT_AMP,ALT_PHASE,ALT_RATE,c.record,c.amp,c.phases,c.rate,symbols['D_800BE9E4']):
  if not STACK-1024<=base<STACK+1024:
   for i in range(-16,256):m[(base+i)&MASK]=(i*13+0x59)&255
 for base in(c.record,ALT):
  for i,value in enumerate((bits(1.25),bits(-2.5),bits(3.75))):put(m,base+0x58+4*i,value)
  put(m,base+0xB4,bits(0.5))
 for base in(c.amp,ALT_AMP):
  for i,v in enumerate(c.amplitudes):put(m,base+4*i,v)
 for base in(c.phases,ALT_PHASE):
  for i,v in enumerate(c.angles):m[base+i]=v
 for base in(c.rate,ALT_RATE):
  for i,v in enumerate(c.rates):m[base+i]=v
 put(m,symbols['D_800BE9E4'],c.ticks&MASK)
 return m

def effect(m,c,sp,ordinal,symbols):
 if ordinal==0:
  if c.mode&1:put(m,c.amp,bits(-7.5));m[c.phases+1]=0x91
  if c.mode&2:
   for at,value in((sp,ALT),(sp+4,ALT_AMP),(sp+8,ALT_PHASE),(sp+12,ALT_RATE)):put(m,at,value)
 else:
  if c.mode&4:put(m,read(m,sp+4)+4,bits(11.5));put(m,symbols['D_800BE9E4'],0x87654321);m[read(m,sp+12)]=0xA7;m[read(m,sp+8)+1]=0xF3
  if c.mode&8:
   for at,value in((sp,ALT),(sp+4,ALT_AMP),(sp+8,ALT_PHASE),(sp+12,ALT_RATE)):put(m,at,value)
def clobber(m,sp):
 for i in range(4):put(m,sp-24+4*i,0xB5000000+i)
def finish(m,record,amp,phases,rate,result,symbols):
 put(m,record+0x54,mul(result,read(m,amp+4)))
 ticks=read(m,symbols['D_800BE9E4']);r0=m[rate];p0=m[phases];p1=m[phases+1]
 m[phases]=(p0+r0*ticks)&255
 ticks=read(m,symbols['D_800BE9E4']);r1=m[rate+1];m[phases+1]=(p1+r1*ticks)&255
def reference(initial,c=Case(),symbols=SYMBOLS):
 m=dict(initial);sp=STACK+c.phase;calls=[]
 for address,value in((sp-4,0xDEAD0000),(sp,c.record),(sp+4,c.amp),(sp+12,c.rate)):put(m,address,value)
 angle=(m[c.phases]-64)&255;put(m,sp+8,c.phases);calls.append((symbols['func_151423D8'],(angle,)));effect(m,c,sp,0,symbols);clobber(m,sp)
 amp=read(m,sp+4);record=read(m,sp);phases=read(m,sp+8);put(m,record+0x4C,mul(c.results[0],read(m,amp)))
 angle=(m[phases+1]-64)&255;calls.append((symbols['func_151423D8'],(angle,)));effect(m,c,sp,1,symbols);clobber(m,sp)
 amp=read(m,sp+4);record=read(m,sp);rate=read(m,sp+12);phases=read(m,sp+8);finish(m,record,amp,phases,rate,c.results[1],symbols)
 return m,calls
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def trig(m,angle):
 angle&=255;index=64-(angle&63)if angle&64 else angle&63;v=read(m,TRIG_TABLE+4*index)
 return v if angle&192 in(0,192)else v^0x80000000
def actual_reference(initial,c=Case()):
 m=dict(initial);result=trig(m,m[c.phases]-64);put(m,c.record+0x4C,mul(result,read(m,c.amp)))
 result=trig(m,m[c.phases+1]-64);finish(m,c.record,c.amp,c.phases,c.rate,result,SYMBOLS);return m

class PhaseOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  args=(c.record,c.amp,c.phases,c.rate)if arguments is None else arguments
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args,connected=connected)
  self.case,self.symbols=c,symbols;self.child_sp=STACK+c.phase;self.trace=[];self.trig_calls=0;self.target_entries=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def execute(self,word):
  if word>>26==17 and(word>>21)&31==16 and word&63==7:self.f[(word>>6)&31]=self.f[(word>>11)&31]^0x80000000;return
  super().execute(word)
 def record_call(self,target):
  sizes={source.ENTRY:4,self.symbols['func_151423D8']:1,source.DAMP:2};assert target in sizes,hex(target);args=self.arguments(sizes[target])
  if target==source.ENTRY:self.child_sp=self.r[29];self.target_entries.append(args)
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==self.symbols['func_151423D8'];ordinal=self.trig_calls;assert ordinal<2;effect(self.memory,self.case,self.child_sp,ordinal,self.symbols)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=self.case.results[ordinal];self.trig_calls+=1
