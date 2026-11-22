"""Finite guest contract, original table, helper mutations and fault prefixes."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_surface_angular_effect_15194408_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ENTRY=0x15194408;ROM=0x1C18B8;TABLE=0x800A8280;TABLE_ROM=0x24CD40
ACTOR=0x30000;OTHER=0x31000;MARK=0x70000
ATTACH=0x151AE7B0;SURFACE=0x1504715C;SUBMIT=0x15153F18
CONSTANTS=(0x800A8294,0x800A8298,0x800A829C)
@dataclass(frozen=True)
class Case:
 kind:int=0;mode:int=0;phase:int=0;seed:int=0;y:int=0x3F800000;first:int=OTHER

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base,n in((ACTOR,0x340),(OTHER,0x340),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 m[ACTOR+4]=c.kind
 for off,v in((0x14,bits(10.)),(0x18,c.y),(0x1C,bits(-20.))):put(m,ACTOR+off,v)
 for a,v in zip(CONSTANTS,(0x3E570A3D,0x3ECFDF3B,0x3E99999A)):put(m,a,v)
 rom=(root/'conker/conker.us.bin').read_bytes() if not hasattr(fixture,'rom') else fixture.rom
 fixture.rom=rom
 for i,b in enumerate(rom[TABLE_ROM:TABLE_ROM+20]):m[TABLE+i]=b
 return m

def service(m,c,t,args):
 if t==ATTACH:
  assert args==(ACTOR,0x3F19999A,90,255,1),args
  put(m,MARK,0x12345678)
  if c.mode&1:
   m[ACTOR+4]=255
   for i,v in enumerate((42.,-13.,17.)):put(m,ACTOR+0x14+4*i,bits(v))
 elif t==SURFACE:
  assert args[1]==ACTOR
  for i in range(36):m[args[0]+i]=(i*7+c.seed*11+0x63)&255
  if c.mode&2:
   for i,v in enumerate((-32.,2.,80.)):put(m,ACTOR+0x14+4*i,bits(v))
   for a,v in zip(CONSTANTS,(bits(-0.5),bits(2.0),bits(0.25))):put(m,a,v)
 elif t==SUBMIT:put(m,MARK+4,0x87654321)

def descriptor(m):
 return [(0,4,read(m,ACTOR+0x14)),(4,4,bits(rounded(floating(read(m,ACTOR+0x18))+50.0))),
  (8,4,read(m,ACTOR+0x1C)),(12,4,bits(6.)),(16,4,bits(3.)),
  (20,4,read(m,CONSTANTS[0])),(24,4,read(m,CONSTANTS[1])),(28,4,bits(13.)),(32,4,bits(8.)),
  (36,2,12),(38,2,5),(40,2,3),(42,2,2),(44,2,30),(46,2,30),(48,2,100),(50,2,100),
  (52,1,0),(56,4,read(m,CONSTANTS[2])),(60,2,16),(62,2,15),(64,4,0)]

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None):
  self.c=c;super().__init__(words,fixture(c),c,entry=entry,arguments=(c.first,ACTOR,0x13579BDF),connected=connected)
  self.initial=dict(self.memory);self.obs=[];self.surface_bytes=None;self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn==0:self.f[fd]=bits(rounded(floating(self.f[rd])+floating(self.f[rt])))
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(ATTACH,SURFACE,SUBMIT,ENTRY),hex(t)
  args=tuple(self.arguments({ATTACH:5,SURFACE:2,SUBMIT:5,ENTRY:2}[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==SUBMIT:
   angles,trail,surface,channel,category=args
   self.obs=[read(self.memory,angles+2*i,2)for i in range(4)],[(off,n,read(self.memory,trail+off,n))for off,n,_ in descriptor(self.memory)],bytes(self.memory[surface+i]for i in range(36))
 def hook(self,t):
  args=self.calls[-1][1];service(self.memory,self.c,t,args)
  if self.c.mode&4 and t==ATTACH:
   # Guest-only rewrite of incoming homes: the selected actor is already S0.
   put(self.memory,self.target_home,0xDEADC0DE);put(self.memory,self.target_home+4,OTHER)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=0x87654321

def programs():
 lookup={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 lookup['.rodata']=lookup['jtbl_800A8258_game']
 paths=(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/padded.o')
 streams=[bound_blob(*payload(p,'func_15194408'),lookup)for p in paths]
 truth=list(struct.unpack_from('>96I',fixture.rom if hasattr(fixture,'rom')else(root/'conker/conker.us.bin').read_bytes(),ROM))
 assert streams[0]==streams[1]==streams[2]==truth;return streams

def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return(m.memory,m.r,m.f,m.calls,m.obs,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)

def check(words,c):
 m=Oracle(words,c).run();expected=dict(m.initial)
 if c.kind<5:
  args=(ACTOR,0x3F19999A,90,255,1);service(expected,c,ATTACH,args)
  home=STACK+c.phase;sp=home-152;surface=sp+40
  service(expected,c,SURFACE,(surface,ACTOR))
  expected_fields=descriptor(expected);service(expected,c,SUBMIT,(sp+76,sp+84,surface,255,1))
  assert m.calls==[(ATTACH,args),(SURFACE,(surface,ACTOR)),(SUBMIT,(sp+76,sp+84,surface,255,1))],(c,m.calls)
  assert m.obs==([0,255,0xFFC1,35],expected_fields,bytes(expected[surface+i]for i in range(36))),(c,m.obs)
 else:assert not m.calls and m.obs==[]
 assert public(m.memory)==public(expected),(c,'public memory')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m

def main():
 streams=programs();cases=[Case(kind=i,phase=(i&1)*8,seed=i%7)for i in range(256)]
 cases += [Case(kind=k,mode=mode,phase=phase,seed=(mode+k)%7,y=y,first=first)for k,mode,phase,y,first in itertools.product(range(5),range(8),(0,8),(0,0x80000000,0x7FC12345,0x7F800000,0xFF800000,1),(0,ACTOR,OTHER))]
 visits=set()
 for c in cases:
  machines=[check(ws,c)for ws in streams];visits.update(machines[0].visits)
  assert state(machines[0])==state(machines[1])==state(machines[2]),c
 assert {ENTRY+4*i for i in range(96)}<=visits
 faults=0
 for c in(Case(),Case(kind=4,mode=7,phase=8),Case(kind=5),Case(kind=255)):
  full=check(streams[0],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 r=dict(cases_per_stream=len(cases),streams=3,covered_words=96,all_256_kind_bytes=True,full_emitted_private_state_equal=True,
  access_fault_triples=faults,original_GameData_table=True,mutating_helper_contracts=True,helper_internals_executed=False,
  guest_home_mutations_not_portable_C=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
