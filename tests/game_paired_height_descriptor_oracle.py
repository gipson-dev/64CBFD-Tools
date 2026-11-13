import itertools,sys,struct
from pathlib import Path
from dataclasses import dataclass
from tools.experiments import game_paired_height_descriptor_screen as packet
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
QUERY=0x15045800; FACTORY=0x1513418c;COPY=0x10022ec0;OWNER=0x30000;CTX=0x48000;OUT=0x50000
@dataclass(frozen=True)
class Case:
 phase:int=0;owner:int=OWNER;context:int=CTX;hit:int=0;allocated:int=0;mutation:int=0;seed:int=0

def blob(path,name,syms):
 t,fs,rs=parse_object(path); f=fs[name];a=f['value'];return bound_blob(t[a:a+f['size']],{i-a:r for i,r in rs.items()if a<=i<a+f['size']},syms)
def fixture(c,syms):
 m={STACK+c.phase+i:(i*17+c.seed*31+165)&255 for i in range(-2048,2048)}
 for base in(OWNER,CTX,OUT):
  for i in range(256):m.setdefault(base+i,(i*29+c.seed*13+90)&255)
 for i,v in enumerate((1.25,4.5,-3.0)):put(m,c.owner+0x14+4*i,bits(v))
 for i,v in enumerate((100.0,9.0,2.0)):put(m,syms[i],bits(v))
 return m
class Machine(FactoryOracle):
 def __init__(self,ws,c,m,syms,entry,connected=None):
  self.c=c;self.const=syms;super().__init__(ws,m,c,entry=entry,s={},arguments=(c.owner,c.context),connected=connected)
 def record_call(self,t):
  a=tuple(self.r[4:8]);snap=()
  if t==QUERY:snap=bytes(self.memory[a[0]+i] for i in range(12))
  elif t==FACTORY:snap=bytes(self.memory[a[0]+i] for i in range(48))
  elif t==COPY:snap=bytes(self.memory[a[1]+i] for i in range(a[2]))
  else:raise AssertionError(hex(t))
  self.calls.append((t,a,snap))
 def hook(self,t):
  c=self.c; a=self.calls[-1][1]
  if t==QUERY:
   put(self.memory,a[3],bits(18.5))
   if c.mutation&1:put(self.memory,c.owner+0x18,bits(7.5))
   if c.mutation&2:self.memory[c.owner+0x3b]^=0x55
   value=c.hit
  elif t==FACTORY:value=OUT if c.allocated else 0
  else:
   assert t==COPY and a[2]==12
   src=bytes(self.memory[a[1]+i] for i in range(12))
   for i,v in enumerate(src):self.memory[a[0]+i]=v
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010,0xa5000011;self.r[2]=value


def programs(state,name):
 offset=0x410 if name.endswith("5F94") else 0x450
 cs=[0x800a0000+offset+4*i for i in range(3)]
 symbols={f'D_800A{x:04X}':0x800a0000+x for x in range(offset,offset+12,4)}
 symbols.update(func_15045800=QUERY,func_1513418C=FACTORY,memcpy=COPY)
 return cs,[blob(state[name][label],name,symbols) for label in ('after','retail','generated','generic')]

def run_case(ws,c,cs,entry):
 states=[]
 for w in ws:
  m=Machine(w,c,fixture(c,cs),cs,entry)
  try:
   m.run()
   public={a:v for a,v in m.memory.items() if not STACK+c.phase-2048<=a<STACK+c.phase+2048}
   states.append(('ok',public,m.calls,m.r[2]))
  except AssertionError as e:
   if not (str(e).startswith("('saved register',") or str(e).startswith("('unowned jump',") or str(e).startswith("('unmapped read',")):raise
   states.append(('incomplete-alias-cases',str(e),m.memory,m.calls))
 assert all(item==states[0] for item in states), (c,[(s[0],s[2:] if len(s)>2 else s[1:]) for s in states])
 return states[0][0]

def assert_semantic(c,cs,name,m):
 """Independent field/ABI assertions for the bounded non-overlapping cases."""
 home=STACK+c.phase;point=home-0x4c;payload=home-0x3c;desc=home-0x30
 initial=fixture(c,cs);query=m.calls[0]
 expected_point=struct.pack('>III',bits(1.25),bits(104.5),bits(-3.0))
 assert query==(QUERY,(point,0,bits(-95.5),c.context+0x34),expected_point),query
 after_y=7.5 if c.mutation&1 else 4.5
 height=18.5 if c.hit else after_y+9.0
 expected_payload=bytearray(initial[payload+i] for i in range(12))
 expected_payload[0:4]=struct.pack('>I',c.context);expected_payload[4]=1;expected_payload[8:12]=struct.pack('>I',bits(height))
 expected=bytearray(initial[desc+i] for i in range(48))
 def store(off,data):expected[off:off+len(data)]=data
 store(0,b'\0'*8);expected[8]=initial[c.owner+0x3b]^(0x55 if c.mutation&2 else 0)
 store(12,struct.pack('>I',c.owner));expected[16]=0;store(20,b'\0'*12)
 first=name.endswith('5F94');store(32,struct.pack('>I',bits(25.0 if first else 80.0)));store(36,struct.pack('>I',bits(2.0)))
 store(40,struct.pack('>H',300));store(42,bytes((10,4 if first else 5,1 if first else 2,2 if first else 3)))
 assert m.calls[1]==(FACTORY,(desc,12,255,0),bytes(expected)),m.calls[1]
 if c.allocated:
  assert m.calls[2]==(COPY,(OUT+0x58,payload,12,0xa5000007),bytes(expected_payload)),m.calls[2]
  assert bytes(m.memory[OUT+0x58+i] for i in range(12))==expected_payload
  assert m.r[2]==OUT and len(m.calls)==3
 else:assert m.r[2]==0 and len(m.calls)==2

def ordinary(state):
 counts={}
 for name in state:
  cs,ws=programs(state,name);assert ws[1]==ws[2]==ws[3]
  n=0
  for phase,hit,allocated,mutation,seed in itertools.product((0,8),(0,1),(0,1),range(4),range(3)):
   c=Case(phase=phase,hit=hit,allocated=allocated,mutation=mutation,seed=seed)
   assert run_case(ws,c,cs,int(name[5:],16))=='ok'
   for w in ws:
    m=Machine(w,c,fixture(c,cs),cs,int(name[5:],16)).run();assert_semantic(c,cs,name,m)
   n+=1
  counts[name]=n
 return counts

def aliases(state):
 report={}
 for name in state:
  cs,ws=programs(state,name);counts={'ok':0,'incomplete-alias-cases':0}
  for role,delta,hit,allocated in itertools.product(('owner','context'),range(-0x100,0x41,4),(0,1),(0,1)):
   c=Case(hit=hit,allocated=allocated,**{role:STACK+delta})
   counts[run_case(ws,c,cs,int(name[5:],16))]+=1
  report[name]=counts
 return report
