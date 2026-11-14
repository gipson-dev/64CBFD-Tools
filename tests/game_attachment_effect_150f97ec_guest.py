"""Bounded independent retail and private-candidate helper call comparison."""
from pathlib import Path
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-attachment-effect-150f97ec-durable'
syms={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
ENTRY=0x150f97ec;ACTOR=0x30000;MATRIX=0x50000
TRANS,FLOAT,INTEGER,EFFECT=(syms[n] for n in ('func_15145EA4','func_150ADA68','func_150ADA20','func_15102B38'))
SLOT=syms['D_80088B50'];POINT=syms['D_800A1C48'];OTHER=syms['D_800A1C54']
rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>89I',rom,0x126c9c));candidate=bound_blob(*payload(out/'candidate-1.o','func_150F97EC'),syms)
def fixture(seed,attached,index):
 m={STACK+i:(i*17+seed*13+0x67)&255 for i in range(-2048,512)}
 for base,n in ((ACTOR,0x200),(MATRIX,0x4000),(SLOT,1),(POINT,24)):
  m.update({base+i:(i*29+seed*19+0x31)&255 for i in range(n)})
 put(m,ACTOR+0x1d4,MATRIX if attached else 0);m[SLOT]=index
 for i,v in enumerate((-124.,-8.,28.,-170.,-8.,28.)):put(m,POINT+4*i,bits(v))
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,selector,context,mutation,rand):
  self.selector=selector;self.context=context;self.mutation=mutation;self.random=rand;self.nfloat=0;self.nint=0;self.records=[]
  super().__init__(words,memory,Case(),entry=ENTRY,s={},arguments=(ACTOR,selector,context))
 def record_call(self,t):
  n={TRANS:4,FLOAT:0,INTEGER:0,EFFECT:14}[t];a=tuple(self.arguments(n));extra=None
  if t==TRANS:extra=(read(self.memory,a[0]),read(self.memory,a[1]))
  if t==EFFECT:extra=(read(self.memory,a[4]),read(self.memory,a[4]+4),tuple(read(self.memory,a[8]+4*i) for i in range(3)))
  self.calls.append((t,a));self.events.append(('CALL',t,a));self.records.append((t,a,extra))
 def hook(self,t):
  args=self.calls[-1][1];value=0;fp=None
  if t==TRANS:
   dest=read(self.memory,args[1]);
   for i,v in enumerate((1.25,-2.5,3.75)):put(self.memory,dest+4*i,bits(v))
   if self.mutation:self.memory[SLOT]=7
  elif t==FLOAT:
   fp=bits((.25,.5,.75)[self.nfloat]);self.nfloat+=1
  elif t==INTEGER:value=self.random[self.nint];self.nint+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=value
  if fp is not None:self.f[0]=fp
def validate(m,attached,index,selector,context,mutation,rand):
 if not attached:assert m.records==[];return
 assert [x[0] for x in m.records]==[TRANS,FLOAT,FLOAT,INTEGER,INTEGER,FLOAT,EFFECT]
 _,a,extra=m.records[0];assert a[2:]==(MATRIX+index*64,1) and extra[0]==POINT
 _,a,extra=m.records[-1]
 assert a[:4]==(ACTOR,7 if mutation else index,POINT,OTHER)
 assert a[5:8]==(rand[0]%3+4,rand[1]%156+100,bits(625.0))
 assert a[9:]==(255,0,0xffffffff,selector&255,context&0xffffffff)
 assert extra==(bits(35.0),bits(2.25),(bits(1.25),bits(-2.5),bits(3.75)))
 assert m.nfloat==3 and m.nint==2
count=0
for attached,index,selector,mutation,seed,rand in itertools.product((0,1),(0,5),(0x100,0x1ff),(0,1),(0,1),((0,0),(0xffffffff,0xffffffff),(7,155))):
 initial=fixture(seed,attached,index)
 for words in (truth,candidate):
  m=Oracle(words,initial.copy(),selector,0x87654321,mutation,rand).run();validate(m,attached,index,selector,0x87654321,mutation,rand)
 count+=1
controls=((0x3c014160,0x3c014170),(0x24010003,0x24010004),(0x27280064,0x27280065))
for old,new in controls:
 altered=list(candidate);assert altered.count(old)==1;altered[altered.index(old)]=new
 initial=fixture(0,1,5);rand=(7,155)
 try:
  m=Oracle(altered,initial,0x1ff,0x87654321,0,rand).run();validate(m,1,5,0x1ff,0x87654321,0,rand)
 except AssertionError:pass
 else:raise AssertionError(('ineffective negative control',hex(old)))
report={'cases_per_stream':count,'retail_words':len(truth),'candidate_words':len(candidate),'effective_negative_controls':len(controls),'finite_values_only':True,'helpers_modeled':True,'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
