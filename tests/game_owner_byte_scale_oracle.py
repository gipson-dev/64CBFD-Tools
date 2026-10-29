"""Byte scale semantics and original callback window; bounded FP conversion model."""
from dataclasses import dataclass
import math,struct
from tools.experiments import game_owner_byte_scale_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,LINK,DATA=0x200000,0x210000,0x220000
SCALE,TABLE,WINDOW,END=0x800A04C0,0x80089914,0x15132278,0x151322B8
@dataclass(frozen=True)
class Case:
 byte:int=173
 scale:int=0x4013020D
 owner:int=OWNER
 link:int=LINK
 data:int=DATA
 phase:int=0
 fcsr:int=0
 seed:int=0

def fixture(c=Case(),symbols=None):
 s=symbols or dict(D_800A04C0=SCALE);m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,length in((c.owner,0x200),(c.link,0x100),(c.data,0x100),(s['D_800A04C0'],4),(TABLE,32)):
  m.update({base+i:(i*13+c.seed+0xA5)&255 for i in range(length)})
 put(m,c.owner+0x170,c.link);put(m,c.link+0x14,c.data);put(m,c.data+0x2F,c.byte,1);put(m,s['D_800A04C0'],c.scale);put(m,TABLE+24,source.ENTRY)
 return m

def converted(value):
 # Independent public result, including bounded guest-only invalid-conversion cases.
 if not math.isfinite(value):return 255
 integer=math.trunc(value)
 return integer&255 if 0<=integer<2**32 else 255

def reference(initial,c=Case(),symbols=None):
 s=symbols or dict(D_800A04C0=SCALE);m=dict(initial);link=read(m,c.owner+0x170);data=read(m,link+0x14);value=m[data+0x2F]
 product=floating(bits(value*floating(read(m,s['D_800A04C0']))));put(m,c.owner+0x70,converted(product),1)
 return m,1

class ScaleOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,symbols=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=symbols or dict(D_800A04C0=SCALE),connected=connected,arguments=(c.owner,))
  self.fcsr=self.initial_fcsr=c.fcsr
 def execute(self,word):
  op,rs,fn=word>>26,word>>21&31,word&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,word)
  else:super().execute(word)
 def record_call(self,target):
  assert target==source.ENTRY;args=(self.r[4],);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('unexpected external call',target))
 def run(self):
  result=super().run();assert self.fcsr==self.initial_fcsr;return result

def caller_machine(rom,words,c=Case(),selector=6,gate=0):
 initial=fixture(c);put(initial,c.owner+0x72,selector,1)
 connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected[END]=0
 m=ScaleOracle(struct.unpack_from('>16I',rom,0x15F728),initial,c,entry=WINDOW,connected=connected)
 m.r[16]=c.owner;m.r[5]=gate;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 return m,initial

def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.fcsr)
