"""Position-effect call sequence, exact argument bits and original caller window."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_position_effect_burst_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
POINT,ALT1,ALT2,MARK=0x200000,0x210000,0x220000,0x230000
WINDOW,END=0x15028A7C,0x15029BA4
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 sample:int=0x3E800000
 random:int=0
 kind:int=0xABCDEF80
 mode:int=0x87654321
 mutation:int=0
 phase:int=0
 result:int=0
 seed:int=0
def symbols():return dict(func_151D5514=0x151D5514,func_151D3FF4=0x151D3FF4,func_150ADA68=0x150ADA68,func_150ADA20=0x150ADA20,func_151541B8=0x151541B8)
def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2304)}
 for base in(POINT,ALT1,ALT2,MARK):
  for i in range(-16,64):m[base+i]=(i*13+c.seed+0xA5)&255
 for base in(POINT,ALT1,ALT2):
  for i,v in enumerate((0x3FC00000,0xC0300000,0x47000001)):put(m,base+4*i,v)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2304}
def effect(m,c,home,ordinal,args):
 put(m,MARK,((read(m,MARK)*33)^ordinal^0x1234)&0xFFFFFFFF)
 if c.mutation&1 and ordinal in(0,1):put(m,args[0]+4*ordinal,(0xC1200000,0x41180000)[ordinal])
 if c.mutation&2 and ordinal==0:
  put(m,home,ALT1);put(m,home+4,0x123400E1);put(m,home+8,0x87654321)
 if c.mutation&4 and ordinal==3:
  put(m,home,ALT2);put(m,home+4,0xFFFF007F);put(m,home+8,0x76543210)
def observation(m,args):return(tuple(read(m,args[0]+4*i)for i in range(3))if args else(),read(m,MARK))
def reference(initial,c=Case(),s=None,home=None,point=POINT):
 s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];snapshots=[]
 for i,v in enumerate((point,c.kind,c.mode)):put(m,home+4*i,u32(v))
 def call(name,args,ordinal):
  calls.append((s[name],args));snapshots.append(observation(m,args));effect(m,c,home,ordinal,args)
 for ordinal,name in enumerate(('func_151D5514','func_151D3FF4')):
  call(name,(read(m,home),read(m,home+4)&255,read(m,home+8)),ordinal)
 call('func_150ADA68',(),2);call('func_150ADA20',(),3)
 width=bits(floating(bits(floating(c.sample)*4.0))+12.0);strength=bits(float(u32(c.random)%56+200))
 call('func_151541B8',(read(m,home),width,0x3FD20C49,strength,0,read(m,home+4)&255,read(m,home+8)),4)
 return m,calls,snapshots
class BurstOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,point=POINT):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(point,u32(c.kind),u32(c.mode)))
  self.ordinal=0;self.snapshots=[];self.strict_calls=True
 def record_call(self,t):
  counts={source.ENTRY:3,self.syms['func_151D5514']:3,self.syms['func_151D3FF4']:3,self.syms['func_150ADA68']:0,self.syms['func_150ADA20']:0,self.syms['func_151541B8']:7};assert t in counts,hex(t)
  args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==source.ENTRY:self.target_home=self.r[29]
  else:self.snapshots.append(observation(self.memory,args))
 def hook(self,t):
  names=('func_151D5514','func_151D3FF4','func_150ADA68','func_150ADA20','func_151541B8');stage=[self.syms[n]for n in names].index(t)
  if self.strict_calls:assert self.ordinal<5 and stage==self.ordinal
  effect(self.memory,self.case,self.target_home,stage,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if stage==2:self.f[0]=self.case.sample
  elif stage==3:self.r[2]=u32(self.case.random)
  elif stage==4:self.r[2]=u32(self.case.result)
  self.ordinal+=1
def caller_machine(rom,words,c=Case()):
 c=replace(c,kind=c.kind&255,mode=1);initial=fixture(c);home=STACK+c.phase
 put(initial,home+0x76C,POINT);put(initial,home+0x773,c.kind,1)
 connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected[END]=0
 m=BurstOracle(struct.unpack_from('>13I',rom,0x55F2C),initial,c,entry=WINDOW,connected=connected);m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 copied=dict(initial)
 for i in range(12):copied[home+0x4C4+i]=initial[POINT+i]
 expected,calls,snapshots=reference(copied,c,home=home,point=home+0x4C4);calls=[(source.ENTRY,(home+0x4C4,c.kind,1))]+calls
 return m,(expected,calls,snapshots)
def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.snapshots)

# The target's two random calls execute the retained literal helpers. Effect
# construction stays at its explicit ABI boundary; no whole-game claim.
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED,SCALE=0x800885B0,0x8009F740
HELPERS=((0x150ADA68,0xDAF18,25),(0x150ADA20,0xDAED0,18))
def connected_fixture(c=Case()):
 m=fixture(c);put(m,SEED,c.seed,8);put(m,SCALE,0x37800080);return m
def connected_reference(initial,c=Case()):
 assert c.mutation in(0,1);s=symbols();home=STACK+c.phase;m=dict(initial);calls=[];snapshots=[]
 for i,v in enumerate((POINT,c.kind,c.mode)):put(m,home+4*i,u32(v))
 def call(name,args,ordinal):
  calls.append((s[name],args));snapshots.append(observation(m,args))
  if ordinal not in(2,3):effect(m,c,home,ordinal,args)
 for ordinal,name in enumerate(('func_151D5514','func_151D3FF4')):call(name,(POINT,c.kind&255,u32(c.mode)),ordinal)
 call('func_150ADA68',(),2);first=next_seed(read(m,SEED,8));put(m,SEED,first,8)
 sample=bits(float(first&65535)*floating(read(m,SCALE)))
 call('func_150ADA20',(),3);second=next_seed(read(m,SEED,8));put(m,SEED,second,8)
 width=bits(floating(bits(floating(sample)*4.0))+12.0);amount=bits(float(u32(second)%56+200))
 call('func_151541B8',(POINT,width,0x3FD20C49,amount,0,c.kind&255,u32(c.mode)),4)
 return m,calls,snapshots
class ConnectedOracle(BurstOracle):
 def __init__(self,words,memory,c,rom):
  code={}
  for entry,pos,n in HELPERS:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
  super().__init__(words,memory,c,connected=code)
 def record_call(self,t):
  super().record_call(t)
  if t in(self.syms['func_150ADA68'],self.syms['func_150ADA20']):
   assert self.ordinal==(2 if t==self.syms['func_150ADA68']else 3);self.ordinal+=1
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  inside=0x150ADA20<=self.current_pc<0x150ADACC
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    a=u32(self.r[rs]+((w&65535)^32768)-32768);assert a%8==0
    if op==55:self.r[rt]=self.get(a,8)
    else:self.put(a,self.r[rt],8)
   finally:self.own_instruction=prior
  elif op==0 and fn in(56,58,60,62,63):
   v=self.r[rt]&((1<<64)-1)
   if fn in(56,60):v<<=sh+(32 if fn==60 else 0)
   elif fn in(58,62):v>>=sh+(32 if fn==62 else 0)
   else:v=(v if v<1<<63 else v-(1<<64))>>(sh+32)
   self.r[rd]=v&((1<<64)-1)
  elif op==0 and fn in(37,38)and inside:self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
  else:
   before=self.r[:]
   if op==0 and fn==27:self.r[rs]=u32(self.r[rs]);self.r[rt]=u32(self.r[rt])
   super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
