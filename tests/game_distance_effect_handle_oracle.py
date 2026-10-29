"""Distance handle, original trapping distance helper and bounded effect factory."""
from dataclasses import dataclass
import math,struct
from tools.experiments import game_distance_effect_handle_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

DISTANCE,FACTORY,ALLOCATE=0x150AD9A0,0x150E3020,0x15167A68
OUTPUT,RECORD,TABLE,CONSTANT=0x50000,0x60000,0x800D99D0,0x800A1030
WINDOW,END=0x1509D564,0x1509D768
HELPERS=((DISTANCE,0xDAE50,32),(FACTORY,0x1104D0,122))
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 values:tuple=(3,-8,5,-7,2,-4,0x12340081,3)
 distance:int=16777217
 slot:int=128
 outcome:int=1
 occupied:int=0
 phase:int=0
 seed:int=0
 mutation:int=0

def symbols():return dict(func_150AD9A0=DISTANCE,func_150E3020=FACTORY)
def args(c):return tuple(map(u32,c.values))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def fixture(c=Case(),s=None,rom=None):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for p,n in((OUTPUT-32,192),(RECORD-32,96),(TABLE-16,64),(CONSTANT-4,12)):
  m.update({p+i:(i*29+c.seed*7+0x5A)&255 for i in range(n)})
 m[OUTPUT+0x48]=c.slot
 for i,v in enumerate(args(c)):put(m,RECORD+4+4*i,v)
 for i in range(8):put(m,TABLE+4*i,0x70100+32*i if c.occupied&(1<<i)else 0)
 put(m,CONSTANT,0xC61C4000)
 if rom is not None:assert struct.unpack_from('>I',rom,0x245AF0)[0]==read(m,CONSTANT)
 return m

class ArithmeticOverflow(Exception):pass
def checked(n):
 if not -0x80000000<=n<0x80000000:raise ArithmeticOverflow
 return n
def distance_reference(values):
 # Signed SUB absolute values and ADD sums trap; MULT contributes its low word.
 magnitudes=sorted(checked(abs(signed(v)))for v in values)
 low,middle,high=magnitudes
 return checked(checked(high+(low>>2))+((11*middle&0xFFFFFFFF)>>5))
def ratio(n,d):
 a,b=floating(bits(float(signed(n)))),floating(bits(float(signed(d))))
 return bits(a/b if b else math.copysign(math.inf,a)if a else math.nan)
def mutated(c):return tuple(u32(v^(0x11000100+i))for i,v in enumerate(args(c)))if c.mutation else args(c)
def factory_args(c,d):
 a=mutated(c);return(*a[:7],ratio(d,a[7]),0,0,0,0,0,0xFFFFFF9D)
def initialize(m,a):
 for off,value,n in((0x4C,0,4),(0x50,0,4),(0x54,0xC61C4000,4),(0x6C,0,4),
  (0x70,0,1),(0x71,0,1),(0x74,0,4),(0x7C,a[13],2),(0x78,a[12],4),
  (0x28,a[9],4),(0x2C,a[10],4),(0x30,a[11],4),(0x34,a[7],4),
  (0x38,bits(float(signed(a[1]))),4),(0x3C,a[8],4),(0x40,a[6],4),(0x44,0,4),(0x4A,0,2)):
  put(m,OUTPUT+off,value,n)
 for i in range(6):put(m,OUTPUT+0x10+i*4,bits(float(signed(a[i]))))
 free=next((i for i in range(8)if read(m,TABLE+4*i)==0),None)
 if free is not None:put(m,TABLE+4*free,OUTPUT)
 m[OUTPUT+0x48]=0 if free is None else free
def reference(initial,c=Case(),s=None,connected=False):
 s=s or symbols();m=dict(initial);a=args(c);diff=tuple(u32(a[i]-a[i+3])for i in range(3))
 d=distance_reference(diff)if connected else c.distance
 fa=factory_args(c,d);calls=[(s['func_150AD9A0'],diff),(s['func_150E3020'],fa)]
 if connected:
  calls.append((ALLOCATE,(39,0,128,1,255,1)))
  if c.outcome:initialize(m,fa)
 return m,calls,m[OUTPUT+0x48]+1 if c.outcome else 0

class HandleOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=args(c))
 def execute(self,word):
  op,rs,rt,rd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
  if op==0 and fn==38:
   self.r[rd]=u32(self.r[rs]^self.r[rt]);self.r[0]=0
  elif op==17 and rs==16 and fn==7:
   self.f[word>>6&31]=self.f[rd]^0x80000000
  elif op==0 and fn in(32,34):
   # The retained handwritten helper uses trapping ADD/SUB, including delays.
   value=checked(signed(self.r[rs])+(signed(self.r[rt])if fn==32 else -signed(self.r[rt])))
   self.r[rd]=u32(value);self.r[0]=0
  elif op==0 and fn==24:
   value=(signed(self.r[rs])*signed(self.r[rt]))&0xFFFFFFFFFFFFFFFF
   self.hi,self.lo=value>>32,value&0xFFFFFFFF
  else:super().execute(word)
 def record_call(self,t):
  n={source.ENTRY:8,self.syms['func_150AD9A0']:3,self.syms['func_150E3020']:14,ALLOCATE:6}[t]
  a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case
  if t==self.syms['func_150AD9A0']:
   value=c.distance
   if c.mutation:
    for i,v in enumerate(mutated(c)):put(self.memory,self.target_home+4*i,v)
  else:
   assert t in(self.syms['func_150E3020'],ALLOCATE),hex(t)
   value=OUTPUT if c.outcome else 0
  # Legal volatile register and outgoing-home clobbers must survive both calls.
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def helper_code(rom):
 result={}
 for entry,off,n in HELPERS:result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 return result
def caller_machine(rom,words,c=Case(),connected=False):
 initial=fixture(c,rom=rom);code=helper_code(rom)if connected else{}
 code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 m=HandleOracle(struct.unpack_from('>19I',rom,0xCAA14),initial,c,entry=WINDOW,connected=code)
 m.r[16]=RECORD;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 return m,initial
