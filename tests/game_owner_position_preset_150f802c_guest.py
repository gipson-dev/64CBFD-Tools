"""Independent descriptor/tail schema and bounded original/raw guest execution."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.tests.test_game_actor_burst_consumer_match import TrackedCode
from tools.experiments import game_owner_position_preset_150f802c_match as p
r,o=p.ROOT,p.OUT;OUT=o;ENTRY=0x150f802c;FACTORY=0x1513264c;COPY=0x10022ec0;POINT,OUTPUT,MARK=0x30000,0x60000,0x35000;COEFF=0x800a1bdc;CONSTANT=0x800a5480
u32=lambda n:n&0xffffffff
HOLES=(89,90,91,105,107,113,118,119)
@dataclass(frozen=True)
class Case:
 parameter:int=0x12348001
 slot:int=255
 context:int=0x87654321
 seed:int=0
 phase:int=0
 mutation:int=0
 rm:int=0
 outcome:int=1
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75),bits(-4.5),bits(5.25),bits(-6.75))
 ghost_homes:bool=False
 point:int=POINT
def home(c):return STACK+c.phase
def packet(c):return home(c)-144
def tail(c):return home(c)-20
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return {a:v for a,v in m.items()if not home(c)-4096<=a<home(c)+1024}
@lru_cache(maxsize=1)
def constants():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();start,base,_,_=load_game_data_layout(r/'conker');values=[]
 for address,n in [(COEFF,4),(CONSTANT,12)]:
  at=elf_slot_offset(elf,address,n);blob=elf[at:at+n];assert blob==rom[start+address-base:start+address-base+n];values.extend(int.from_bytes(blob[i:i+4],'big')for i in range(0,n,4))
 return tuple(values)
def arguments(c):return c.point,u32(c.parameter),u32(c.slot),u32(c.context)
def fixture(c):
 m={home(c)+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,1024)}
 for p,n in [(c.point,68),(OUTPUT-32,612),(MARK,16)]:m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(c.coords):put(m,c.point+4*i,v)
 values=constants();put(m,COEFF,values[0])
 for i,v in enumerate(values[1:]):put(m,CONSTANT+4*i,v)
 put(m,MARK,0);return m
def expected_packet(m,c):
 result={i:m[packet(c)+i]for i in range(124)};words={0:bits(1.),4:bits(1.),8:read(m,COEFF),12:read(m,COEFF),16:read(m,c.point+12),20:read(m,c.point+16),24:read(m,c.point+20),28:bits(1.),32:bits(1.),36:bits(1.),40:read(m,c.point),44:read(m,c.point+4),48:read(m,c.point+8),52:0,56:0,60:0,64:read(m,CONSTANT),68:read(m,CONSTANT+4),72:read(m,CONSTANT+8),76:0,80:0x980,92:0,108:0,120:0}
 halves={84:c.parameter,86:47,114:1,116:255};small={88:0,96:255,97:20,98:0,99:0,100:0,101:0,102:0,103:0,104:0,106:0,112:0}
 assert {i for at in words for i in range(at,at+4)}|{i for at in halves for i in range(at,at+2)}|set(small)==set(range(124))-set(HOLES)
 for at,v in words.items():put(result,at,v)
 for at,v in halves.items():put(result,at,v,2)
 result.update(small);return bytes(result[i]for i in range(124))
def expected_tail(m,c):return b''.join(v.to_bytes(4,'big')for v in(c.point,*[read(m,c.point+4*i)for i in range(3)],0))
def observation(m,c,t,args,fcsr):return public(m,c),data(m,args[0]if t==FACTORY else args[1],124 if t==FACTORY else args[2]),data(m,home(c),16),fcsr
def effect(m,c,t,args):
 put(m,MARK,read(m,MARK)+1)
 if t==FACTORY:
  if c.mutation&1:
   for i in range(68):m[c.point+i]=(i*13+c.seed)&255
  if c.mutation&2:
   put(m,COEFF,bits(-10.))
   for i in range(3):put(m,CONSTANT+4*i,0x41000000+0x10000*i)
  if c.mutation&4:
   for i in range(124):m[args[0]+i]=(i*7+c.seed*11+0x31)&255
  if c.ghost_homes:
   for i,v in enumerate((0x31000,0xabcdef01,0x1234007f,0xfedcba98)):put(m,home(c)+4*i,v)
  return OUTPUT if c.outcome else 0
 assert t==COPY and 0<=args[2]<=64;copied=data(m,args[1],args[2])
 for i,v in enumerate(copied):m[args[0]+i]=v
 return args[0]
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];fcsr=c.rm
 for i,v in enumerate(arguments(c)[1:],1):put(m,home(c)+4*i,v)
 for i,v in enumerate(expected_tail(m,c)):m[tail(c)+i]=v
 for i,v in enumerate(expected_packet(m,c)):m[packet(c)+i]=v
 def call(t,args):
  nonlocal fcsr
  calls.append((t,args));obs.append(observation(m,c,t,args,fcsr));v=effect(m,c,t,args);fcsr=c.rm|0x100*len(calls);return v
 value=call(FACTORY,(packet(c),3,255,0,180,c.slot&255,u32(c.context)))
 if value:value=call(COPY,(value+0x170,tail(c),20))
 return m,calls,obs,fcsr,value
class Machine(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,memory=None,args=None,connected=None):
  self.c=c;self.fcsr=c.rm;self.provider_count=0;self.observations=[];self.frames=[]
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:];self.current_pc=self.delay_of=None;self.code=TrackedCode(self.code,self)
 def record_call(self,t):
  assert t in(FACTORY,COPY),hex(t);args=tuple(map(u32,self.arguments(7 if t==FACTORY else 3)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(observation(self.memory,self.c,t,args,self.fcsr));self.frames.append(data(self.memory,home(self.c)-200,200));self.provider_count+=1
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value;self.fcsr=self.c.rm|0x100*self.provider_count
def symbols():return dict(func_1513264C=FACTORY,memcpy=COPY,D_800A1BDC=COEFF,D_800A5480=CONSTANT)
def programs():
 return [bound_blob(*payload(o/f,'func_150F802C'),symbols())for f in ['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o']]
def raw_program():return bound_blob(*payload(o/'selected-final/owner-candidate.o','func_150F802C'),symbols())
def check(words,c,entry=ENTRY):
 m=Machine(words,c,entry).run();expected,calls,obs,fcsr,value=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert m.observations==obs,(c,'provider observations');assert public(m.memory,c)==public(expected,c)and data(m.memory,packet(c),144)==data(expected,packet(c),144),(c,'memory');assert m.fcsr==fcsr and m.r[2]==value and m.r[29]==home(c)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(slot=i,parameter=(0,1,0xffff,0x8000,0x7fff,0x12348001,0xffffffff,0x87654321)[i&7],context=u32(i*0x87654321),mutation=i%8,rm=i%4,seed=i&15,phase=(i&1)*8,outcome=i&1)for i in range(256)]
 rows +=[Case(slot=255,parameter=p,context=context,mutation=mutation,outcome=outcome,phase=phase,rm=rm)for p,context,mutation,outcome,phase,rm in itertools.product((0x7fff,0x8000),(0,0x80000000,0xffffffff),(0,7),(0,1),(0,8),range(4))]
 rows +=[Case(ghost_homes=True,mutation=i%8,outcome=i&1,phase=(i&1)*8,seed=i)for i in range(16)]
 rows +=[Case(coords=(v,0x80000000,1,0x7fc12345,0x7f800000,0xff800000),outcome=outcome,rm=rm)for v,outcome,rm in itertools.product((0x7f7fffff,0xff7fffff,0x00800000,0x80800000),(0,1),range(4))]
 return rows
def main():
 g=sys.modules[__name__];o=OUT
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 files=['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o','selected-final/owner-candidate.o'];streams=[g.bound_blob(*g.payload(o/f,'func_150F802C'),g.symbols())for f in files];assert all(w==streams[0]for w in streams[:4])
 def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.frames,m.trace,m.current_pc,m.delay_of,m.condition
 seen=set()
 for c in g.cases():
  models=[g.check(w,c)for w in streams];a=models[0];assert all(state(m)==state(a)for m in models[1:4]);assert all((m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.frames)==(a.memory,a.r,a.f,a.fcsr,a.hi,a.lo,a.calls,a.observations,a.frames)for m in models[4:]);seen.update(a.visits)
 prefixes=0
 for c in[g.Case(),g.Case(mutation=7,phase=8),g.Case(ghost_homes=True,mutation=7,outcome=0)]:
  full=g.Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in streams[:4]:
    m=g.Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert seen==set(range(g.ENTRY,g.ENTRY+400,4))
 controls=[]
 for name,find,change in [('tail-copy-width',lambda w:w>>26==9 and w>>16&31==6 and w&65535==20,lambda w:w-4),('resource-id',lambda w:w>>26==9 and w&65535==47,lambda w:w-1),('parameter-offset',lambda w:w>>26==33 and w&65535==0xce,lambda w:w-2)]:
  ws=list(streams[0]);at=next(i for i,w in enumerate(ws)if find(w));ws[at]=change(ws[at]);c=Case(mutation=7);m=Machine(ws,c).run();assert m.r[29]==home(c)and len(m.calls)==2
  expected,calls,obs,fcsr,value=reference(m.initial,c);assert m.calls!=calls or m.observations!=obs or public(m.memory,c)!=public(expected,c);controls.append(dict(name=name,supported_complete_execution=True,rejected=True))

 q=dict(cases_per_stream=len(g.cases()),streams=5,retail_equal_streams=4,all100_words_visited=True,access_fault_quads=prefixes,descriptor_bytes=124,initialized_bytes=116,unspecified_bytes=8,tail_bytes=20,full200byte_frames_and_return_registers_equal=True,effective_controls=controls,raw_fault_order_not_claimed=True,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
