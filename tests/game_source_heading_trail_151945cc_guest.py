"""Bounded double/single guest execution, snapshots, classifier gates and faults."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_source_heading_trail_151945cc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ENTRY=0x151945CC;ROM=0x1C1A7C;ACTOR=0x30000;SOURCE=0x31000;MARK=0x70000
SURFACE=0x1504715C;CLASSIFY=0x15134070;SUBMIT=0x15153F18;ATTACH=0x151B4CD0
TABLE=0x800A3FE6;DOUBLE=0x800A82A0;GLOBALS=(0x800A82A8,0x800A82AC,0x800A82B0,0x800A82B4,0x800A82B8)
u32=lambda n:n&0xFFFFFFFF
double_bits=lambda x:struct.unpack('>Q',struct.pack('>d',x))[0]
double_value=lambda x:struct.unpack('>d',struct.pack('>Q',x))[0]
@dataclass(frozen=True)
class Case:
 heading:int=0;kind:int=0;category:int=1;mode:int=0;phase:int=0;seed:int=0;y:int=0x3F800000;alias:int=0;unused:int=0x87654321;double:int=double_bits(270.)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base,n in((ACTOR,0x340),(SOURCE,0x340),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 source=ACTOR if c.alias else SOURCE;put(m,source+0x7A,c.heading,2)
 for off,v in((0x14,bits(10.)),(0x18,c.y),(0x1C,bits(-20.))):put(m,ACTOR+off,v)
 put(m,DOUBLE,c.double,8)
 for a,v in zip(GLOBALS,(0x40D66666,0x40151EB8,0x3F2E147B,0x408CCCCD,0x40A9999A)):put(m,a,v)
 if c.kind!=99:m[u32(TABLE+c.kind*16)]=c.category
 return m

def effect(m,c,t,args):
 source=ACTOR if c.alias else SOURCE
 if t==SURFACE:
  assert args[1]==ACTOR
  for i in range(36):m[args[0]+i]=(i*7+c.seed*11+0x63)&255
  if c.mode&1:
   put(m,source+0x7A,0xFF00,2)
   for i,v in enumerate((42.,-13.,17.)):put(m,ACTOR+0x14+4*i,bits(v))
 elif t==CLASSIFY:
  assert args==(ACTOR,)
  if c.mode&2:
   for i,v in enumerate((-32.,2.,80.)):put(m,ACTOR+0x14+4*i,bits(v))
   for a,v in zip(GLOBALS,(-.5,2.,.25,9.,.75)):put(m,a,bits(v))
   put(m,DOUBLE,double_bits(-100.),8)
  if c.mode&4 and c.kind!=99:m[u32(TABLE+c.kind*16)]^=3
 elif t==SUBMIT:put(m,MARK,0x12345678)
 elif t==ATTACH:
  assert args==(ACTOR,255,1),args;put(m,MARK+4,0x87654321)

def descriptor(m,x,y,z):
 return [(0,4,x),(4,4,y),(8,4,z),(12,4,read(m,GLOBALS[0])),(16,4,read(m,GLOBALS[1])),(20,4,read(m,GLOBALS[2])),
  (24,4,0),(28,4,read(m,GLOBALS[3])),(32,4,read(m,GLOBALS[4])),(36,2,15),(38,2,12),(40,2,3),(42,2,1),
  (44,2,31),(46,2,19),(48,2,155),(50,2,100),(52,1,0),
  (56,4,bits(.5)),(60,2,16),(62,2,15),(64,4,0)]

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None):
  self.c=c;source=ACTOR if c.alias else SOURCE
  super().__init__(words,fixture(c),c,entry=entry,arguments=(source,ACTOR,c.unused),connected=connected)
  self.initial=dict(self.memory);self.obs=[];self.before_f=self.f[:]
 def get_double(self,i):return double_value(self.f[i+1]<<32|self.f[i])
 def set_double(self,i,value):
  value=double_bits(value);self.f[i],self.f[i+1]=value&0xFFFFFFFF,value>>32
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn==33:self.set_double(fd,float(floating(self.f[rd])))
  elif op==17 and rs==17 and fn==0:self.set_double(fd,self.get_double(rd)+self.get_double(rt))
  elif op==17 and rs==17 and fn==32:self.f[fd]=bits(self.get_double(rd))
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(SURFACE,CLASSIFY,SUBMIT,ATTACH,ENTRY),hex(t)
  args=tuple(self.arguments({SURFACE:2,CLASSIFY:1,SUBMIT:5,ATTACH:3,ENTRY:3}[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==SUBMIT:
   angles,trail,surface,channel,category=args
   fields=descriptor(self.memory,0,0,0)
   self.obs=[read(self.memory,angles+2*i,2)for i in range(4)],[(off,n,read(self.memory,trail+off,n))for off,n,_ in fields],bytes(self.memory[surface+i]for i in range(36))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1])
  if self.c.mode&8 and t==SURFACE:
   for i in range(3):put(self.memory,self.target_home+4*i,0xDEAD0000+i)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=u32(self.c.kind)if t==CLASSIFY else 0x87654321

def programs():
 lookup={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 paths=(out/'qualified-source/candidate.o',out/'image-qualification/padded.o',out/'image-qualification/retail.o')
 streams=[bound_blob(*payload(p,'func_151945CC'),lookup)for p in paths]
 truth=list(struct.unpack_from('>114I',(root/'conker/conker.us.bin').read_bytes(),ROM))
 assert streams[1]==streams[2]==truth;assert sum(a!=b for a,b in zip(streams[0],truth))==9
 return streams
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return(m.memory,m.r,m.f,m.calls,m.obs,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def check(words,c):
 m=Oracle(words,c).run();expected=dict(m.initial);sp=STACK+c.phase-176;surface=sp+48
 source=ACTOR if c.alias else SOURCE;heading=(read(expected,source+0x7A,2)>>8)-128
 x=read(expected,ACTOR+0x14);y=bits(float(floating(read(expected,ACTOR+0x18)))+double_value(read(expected,DOUBLE,8)));z=read(expected,ACTOR+0x1C)
 calls=[(SURFACE,(surface,ACTOR)),(CLASSIFY,(ACTOR,))]
 effect(expected,c,SURFACE,calls[0][1]);effect(expected,c,CLASSIFY,calls[1][1])
 if c.kind!=99 and expected[u32(TABLE+c.kind*16)]!=2:
  values=descriptor(expected,x,y,z);values=[(o,n,int(expected[u32(TABLE+c.kind*16)]==1)if o==52 else v)for o,n,v in values]
  assert m.obs==([heading&65535,128,0xFF60,32],values,bytes(expected[surface+i]for i in range(36))),(c,m.obs,values)
  args=(sp+84,sp+92,surface,255,1);calls.append((SUBMIT,args));effect(expected,c,SUBMIT,args)
  args=(ACTOR,255,1);calls.append((ATTACH,args));effect(expected,c,ATTACH,args)
 else:assert m.obs==[]
 assert m.calls==calls,(c,m.calls,calls)
 assert public(m.memory)==public(expected),(c,'public memory')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def main():
 streams=programs();cases=[Case(heading=(i<<8)|low,seed=i%7)for i in range(256)for low in(0,1,255)]
 cases += [Case(heading=h,kind=k,category=c,mode=mode,phase=phase,y=y,alias=mode&1)for h,k,c,mode,phase,y in itertools.product((0,0xFFFF),(0,1,98,99),(0,1,2,255),(0,1,2,4,7,15),(0,8),(0,0x80000000,0x7FC12345,0x7F800000,0xFF800000,1))]
 cases += [Case(kind=k,mode=mode)for k in(-1,100,0x7FFFFFFF,0x80000000,0xFFFFFFFF)for mode in(0,4)]
 cases += [Case(y=0xC3870000,double=double_bits(d),mode=mode)for d in(270.,270.00001,-270.00001,0.0000000001)for mode in(0,2)]
 visits=set()
 for c in cases:
  machines=[check(ws,c)for ws in streams];visits.update(machines[1].visits)
  assert state(machines[0])==state(machines[1])==state(machines[2]),c
 assert {ENTRY+4*i for i in range(114)}<=visits
 faults=0
 for c in(Case(),Case(kind=99),Case(category=2),Case(heading=0xFFFF,mode=15,phase=8)):
  full=check(streams[1],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams[1:]:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1];faults+=1
 r=dict(cases_per_stream=len(cases),streams=3,covered_words=114,heading_high_bytes=256,raw_full_end_state_equals_normalized_original=True,
  normalized_original_access_fault_pairs=faults,full_normalized_fault_state_equal=True,helper_internals_executed=False,
  signed_sparse_classifier_indices_guest_only=True,double_single_rounding_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
