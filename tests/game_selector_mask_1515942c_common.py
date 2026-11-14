from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-selector-mask-1515942c-screen';conker=root/'conker';entry=0x1515942c;s={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};HELPER=s['func_1514ECE0'];ACTOR=0x30000;NODE=0x31000;DATA=0x32000
programs={'retail':list(struct.unpack_from('>90I',(conker/'conker.us.bin').read_bytes(),0x1868dc)),'candidate':bound_blob(*payload(Path(__import__('os').environ.get('SELECTOR_CANDIDATE',out/'selected.o')),'func_1515942C'),s)}
s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Scenario:
 values:tuple;fields:tuple;found:bool;mutate:int=0

def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,256)}
 for base,length in ((ACTOR,0x300),(NODE,0x40),(DATA,0x80)):m.update({base+i:(i*13+0x53)&255 for i in range(length)})
 put(m,ACTOR+0x2f4,NODE);put(m,NODE+0x10,DATA)
 for i,v in enumerate(c.fields):m[DATA+0x2c+i]=v
 for i,v in enumerate(c.values[3:]):put(m,STACK+0x10+4*i,v&0xffffffff)
 return m

def args(c):return (ACTOR,*[v&0xffffffff for v in c.values[:3]])
def selector(v,offset,anymask):return anymask if v==-1 else 1<<((v+offset)&31)
def result(c):
 values=list(map(s16,c.values))
 if c.mutate:values=[s16(0x8000+i*17) for i in range(5)]
 wanted=0;actual=0
 for v,offset,anymask in zip(values,(0,3,6,9,13),(7,0x38,0x1c0,0x1e00,0x3e000)):wanted|=selector(v,offset,anymask)
 for v,offset in zip(c.fields,(0,3,6,9,13)):actual|=1<<((v+offset)&31)
 return int(c.found and (wanted|actual)==wanted)
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+256}
def tr(q):return [x for x in q.trace if not STACK-512<=x[1]<STACK+256]
class Oracle(FactoryOracle):
 def __init__(self,words,m,c,connected=None):self.c=c;super().__init__(words,m,BaseCase(),entry=entry,s={},arguments=args(c),connected=connected)
 def execute(self,w):
  if w>>26==0 and w&63==4:
   rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;self.r[rd]=(self.r[rt]<<(self.r[rs]&31))&0xffffffff;self.r[0]=0;return
  return super().execute(w)
 def record_call(self,t):
  assert t==HELPER,hex(t);a=tuple(self.arguments(3));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==HELPER;a=self.calls[-1][1];put(self.memory,a[2],NODE if self.c.found else 0)
  if self.c.mutate:
   for i in range(5):put(self.memory,STACK+4+i*4,0x8000+i*17)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=int(self.c.found)
