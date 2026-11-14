from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-owner-chain-create-150c0ac0-screen';conker=root/'conker';entry=0x150c0ac0
syms={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};ALLOC=syms['func_15167A68'];COPY=syms['memcpy'];DESC=0x30000;RESOURCE=0x31000;POS=0x32000;OUTPUT=0x50000
programs={'retail':list(struct.unpack_from('>94I',(conker/'conker.us.bin').read_bytes(),0xedf70)),'raw':bound_blob(*payload(Path(__import__('os').environ.get('OWNER_CHAIN_RAW',out/'selected.o')),'func_150C0AC0'),syms),'guarded':bound_blob(*payload(Path(__import__('os').environ.get('OWNER_CHAIN_PADDED',out/'guarded.o')),'func_150C0AC0'),syms)};assert programs['retail']==programs['guarded']
s16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Scenario:
 count:int=3;flags:int=0;resource:int=1;allocate:int=1;mutation:int=0;slot:int=0xff;context:int=1;desc:int=DESC;result:int=OUTPUT

def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,256)}
 for base,length in ((c.desc-0x40,0x180),(RESOURCE-16,96),(POS-16,64),(c.result-32,0x200)):
  m.update({base+i:(i*13+0x53)&255 for i in range(length)})
 for n in (-32768,-4,-2,-1,0,1,2,3,5,20):
  for i in range(2):m[(c.result+0x48+n*8-4+i)&0xffffffff]=0xa5
 put(m,c.desc,POS);put(m,c.desc+8,RESOURCE if c.resource else 0);put(m,c.desc+0x14,c.count&65535,2);m[c.desc+0x18]=c.flags
 put(m,RESOURCE,0x12345678 if c.resource==1 else 0);put(m,RESOURCE+0x14,0x7fc12345);put(m,RESOURCE+0x1c,0x80000000);put(m,POS,0x3f800000);put(m,POS+8,0xffc56789)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+256}
def tr(q):return [x for x in q.trace if not STACK-512<=x[1]<STACK+256]
def alter(m,c):
 if c.mutation&1:m[c.desc+0x18]^=2
 if c.mutation&2:put(m,c.desc+0x14,3,2)
def reference(initial,c):
 m=initial.copy();calls=[];size=(s16(read(m,c.desc+0x14,2))*8+0x48)&0xffffffff
 if not(m[c.desc+0x18]&2):
  ptr=read(m,c.desc+8)
  if not ptr or not read(m,ptr):return public(m),calls,0
 calls.append((ALLOC,(0x25,c.context&0xffffffff,size,1,c.slot&255,1)));alter(m,c)
 if not c.allocate:return public(m),calls,0
 r=c.result;calls.append((COPY,((r+0x18)&0xffffffff,c.desc,0x1c)))
 for i in range(0x1c):m[(r+0x18+i)&0xffffffff]=m[(c.desc+i)&0xffffffff]
 put(m,r+0x40,r+0x48)
 if m[c.desc+0x18]&2:
  pos=read(m,r+0x18);put(m,r+0x34,read(m,pos));put(m,r+0x38,read(m,pos+8))
 else:
  pos=read(m,r+0x20);put(m,r+0x34,read(m,pos+0x14));put(m,r+0x38,read(m,pos+0x1c))
 put(m,r+0x3c,0);put(m,r+0x44,0xffff,2);put(m,r+0x46,0,2)
 index=0
 while index<s16(read(m,c.desc+0x14,2))-1:
  ptr=read(m,r+0x40);put(m,(ptr+index*8+4)&0xffffffff,index+1,2);index=s16(index+1)
  assert index<100
 count=s16(read(m,c.desc+0x14,2));ptr=read(m,r+0x40);put(m,(ptr+count*8-4)&0xffffffff,0xffff,2);put(m,r+0x10,1);put(m,r+0x14,0)
 return public(m),calls,r
class Oracle(FactoryOracle):
 def __init__(self,words,m,c,connected=None):
  self.c=c;super().__init__(words,m,BaseCase(),entry=entry,s={},arguments=(c.desc,c.slot,c.context),connected=connected)
 def record_call(self,t):
  n={ALLOC:6,COPY:3}.get(t);assert n is not None,hex(t);a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1]
  if t==ALLOC:alter(self.memory,c);value=c.result if c.allocate else 0
  else:
   assert t==COPY and a[2]==28
   for i in range(28):self.memory[(a[0]+i)&0xffffffff]=self.memory[(a[1]+i)&0xffffffff]
   value=a[0]
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value&0xffffffff
