"""Ordered two-quad effects, literal faults and consumed-input GPR relations."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.game_random_targets_1518f1a0_guest import convert_integer
from tools.tests.game_pointer_quad_vertices_150db714_guest import trunc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_oriented_quad_constructor_15165f80_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x15165F80;OUTPUT=0x300000;ALT=0x310000;MARK=0x320000;COEFF=0x800A6C94;GLOBAL=0x800DD470;ALLOC=0x15167A68;SIN=0x15047D60;COS=0x15047C00;ORIGIN=0x1517E05C;u32=lambda v:v&0xFFFFFFFF;signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 values:tuple=(0xFFFFFFFF,0x87654321,0x80000000,0x7FFFFFFF,0x12340081,0xFEDCBA82,0xABCDEF83,0x876543FF,0xF00DCAFE)
 success:int=1
 sine:int=fp.bits(.33333334)
 cosine:int=fp.bits(-.7777778)
 mutation:int=0
 connected:int=0
 phase:int=0
 seed:int=0
 rm:int=0
 flags:int=4
 provider_flags:int=0x12004

def symbols():return dict(D_800A6C94=COEFF,func_15167A68=ALLOC,sinf=SIN,cosf=COS,func_1517E05C=ORIGIN)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def observation(m):return tuple(data(m,p,n)for p,n in((OUTPUT-16,200),(ALT-16,200),(MARK,32),(COEFF,4),(GLOBAL,6)))
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-2048,1024)}
 for p,n in((OUTPUT-16,200),(ALT-16,200),(MARK,32),(COEFF-8,20),(GLOBAL-8,24)):m.update({p+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for i,v in enumerate(c.values):put(m,STACK+c.phase+4*i,v)
 put(m,COEFF,0x3C8EFA35);return m
def effect(m,c,t):
 home=STACK+c.phase;frame=home-56;put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:put(m,COEFF,fp.bits(.5));m[OUTPUT+0x94]=0xE1;m[ALT+0x94]=0xE2
 if c.mutation&2:
  # Home mutation is a guest-only experiment, not a portable C alias claim.
  if t==ALLOC:put(m,home,0 if c.values[0]==0xFFFFFFFF else 0xFFFFFFFF)
  for i in(1,3,4,5,6):put(m,home+4*i,u32(c.values[i]^(0xAA55FF00+i)))
 if c.mutation&4 and t in(SIN,COS):put(m,frame+0x30,ALT if t==SIN else OUTPUT)
 if c.mutation&8 and t==SIN:put(m,frame+0x2C,fp.bits(-3.75))

def reference(initial,c,initial_csr=None):
 m=dict(initial);home=STACK+c.phase;frame=home-56;calls=[];packets=[];ops=[];csr=c.rm|c.flags if initial_csr is None else initial_csr;y=c.values[2]
 for i in(0,1,3):put(m,home+4*i,c.values[i])
 def operation(kind,a,b=0):
  nonlocal csr
  ops.append((kind,a,b,csr,observation(m)))
  if kind==32:v,flags=convert_integer(a,csr&3)
  elif kind==13:v,flags=trunc(a)
  elif kind==7:return a^0x80000000
  else:v,flags=arithmetic(a,b,kind,csr&3)
  csr=(csr&~0x3F000)|flags;return v
 def call(t,args):
  nonlocal csr
  args=tuple(map(u32,args));calls.append((t,args));packets.append((t,observation(m)))
  if t==ORIGIN and c.connected:
   for i,v in enumerate(args):put(m,GLOBAL+2*i,v,2)
   return GLOBAL
  effect(m,c,t);csr=(csr&~0x3F000)|c.provider_flags
  if t==ALLOC:return OUTPUT if c.success else 0
  return c.sine if t==SIN else c.cosine if t==COS else 0xDEADBEEF
 p=call(ALLOC,(4,c.values[8],168,1,c.values[7]&255,1));angle=read(m,home)
 if p:
  if angle==0xFFFFFFFF:
   for base in(0,0x40):
    for off in(0x12,0x22,0x32,0x42):put(m,p+base+off,y,2)
    for off in(0x16,0x26,0x36,0x46):put(m,p+base+off,0,2)
   m[p+0x95]=0
  else:
   converted=operation(32,angle);put(m,frame+0x30,p);rad=operation(2,converted,read(m,COEFF));put(m,frame+0x2C,rad);sine=call(SIN,(rad,));p=read(m,frame+0x30);cosrad=read(m,frame+0x2C);value=operation(13,operation(2,sine,fp.bits(127.)));m[p+0x91]=value&255;cosine=call(COS,(cosrad,));negative=operation(7,cosine);p=read(m,frame+0x30);value=operation(2,negative,fp.bits(127.));m[p+0x95]=1;m[p+0x90]=operation(13,value)&255
  for base in(0,0x40):
   for off,value in((0x18,0x2000),(0x1A,0x2000),(0x28,0x2800),(0x2A,0x2000),(0x38,0x2800),(0x3A,0x2800),(0x48,0x2000),(0x4A,0x2800)):put(m,p+base+off,value,2)
  x,z=read(m,home+4),read(m,home+12)
  for off,value,n in((0x9A,y,2),(0x9E,1,2),(0x92,read(m,home+20),1),(0x93,read(m,home+20),1),(0x98,x,2),(0x9C,z,2),(0x96,read(m,home+16),2),(0x94,read(m,home+24),1)):put(m,p+off,value,n)
  call(ORIGIN,(x,y,z))
 return m,calls,packets,ops,csr

def origin_code():
 rom=(r/'conker/conker.us.bin').read_bytes();return dict(zip(range(ORIGIN,ORIGIN+28,4),struct.unpack_from('>7I',rom,0x1AB50C)))
class Code(TrackedCode):
 def __getitem__(self,pc):
  w=super().__getitem__(pc);m=self.owner;op=w>>26
  if op in(4,5):m.operands.append((pc,'branch',op,m.r[w>>21&31],m.r[w>>16&31]))
  elif op==3:m.operands.append((pc,'jal',((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2)))
  elif op==0 and w&63==8:m.operands.append((pc,'jr',m.r[w>>21&31]))
  return w
class Machine(FactoryOracle):
 def __init__(self,words,c,raw=False,memory=None,entry=None,connected=None,arguments=None):
  self.c=c;self.raw=raw;self.ops=[];self.operands=[];self.packets=[];self.timeline=[];super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,s=symbols(),arguments=c.values if arguments is None else arguments,connected=origin_code()if c.connected and connected is None else connected);self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:];self.code=Code(self.code,self)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.timeline.append((self.current_pc,'R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.timeline.append((self.current_pc,'W',p,n,v&((1<<(8*n))-1)))
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;pc=self.current_pc;imm=((w&65535)^32768)-32768
  if op in(35,36,40,41,43,49,57):self.operands.append((pc,'memory',op,u32(self.r[rs]+imm),self.r[rt]&((1<<(8*{40:1,41:2,43:4}[op]))-1)if op in(40,41,43)else self.f[rt]if op==57 else None))
  elif op==9:self.operands.append((pc,'addiu',self.r[rs],imm))
  elif op==15:self.operands.append((pc,'lui',w&65535))
  elif op==0:self.operands.append((pc,'R',fn,self.r[rs],self.r[rt]))
  elif op==17:self.operands.append((pc,'COP1',w&0x03FFFFFF,self.r[rt]if rs==4 else self.f[rd],self.f[rt]if rs==16 else 0))
  else:raise AssertionError(('unmodeled consumed inputs',hex(w)))
  if op==17 and(rs==20 and fn==32 or rs==16 and fn in(0,2,7,13)):
   a,b=self.f[rd],self.f[rt]if fn in(0,2)else 0;event=(fn,a,b,self.fcsr,observation(self.memory));self.ops.append(event);self.timeline.append((pc,'FP',event))
   if fn==32:v,flags=convert_integer(a,self.fcsr&3)
   elif fn==13:v,flags=trunc(a)
   elif fn==7:v,flags=a^0x80000000,None
   else:v,flags=arithmetic(a,b,fn,self.fcsr&3)
   self.f[w>>6&31]=v
   if flags is not None:self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  if t in(SIN,COS):args=(self.f[12],)
  else:assert t in(ALLOC,ORIGIN),hex(t);args=tuple(map(u32,self.arguments(6 if t==ALLOC else 3)))
  self.actual_args=args;self.calls.append((t,args));self.packets.append((t,observation(self.memory)));self.operands.append((self.current_pc,'call_RA',self.r[31]));self.timeline.append((self.current_pc,'CALL',t,args))
 def hook(self,t):
  effect(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.fcsr=(self.fcsr&~0x3F000)|self.c.provider_flags;self.r[2]=OUTPUT if t==ALLOC and self.c.success else 0 if t==ALLOC else 0xDEADBEEF
  if t in(SIN,COS):self.f[0]=self.c.sine if t==SIN else self.c.cosine

def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.packets,m.ops,m.operands,m.trace,m.timeline,m.current_pc,m.delay_of)
def raw_relation(a,b):
 assert(a.memory,a.f,a.fcsr,a.hi,a.lo,a.calls,a.packets,a.ops,a.operands,a.trace,a.timeline)==(b.memory,b.f,b.fcsr,b.hi,b.lo,b.calls,b.packets,b.ops,b.operands,b.trace,b.timeline),'raw consumed operands/access/FP/calls relation'
 assert all(a.r[i]==b.r[i]for i in(*range(16,24),28,29,30,31))
def check(words,c,raw=False):
 m=Machine(words,c,raw).run();memory,calls,packets,ops,csr=reference(fixture(c),c);a=(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr);z=(public(memory,c),calls,packets,ops,csr);assert a==z,dict(case=str(c),raw=raw,parts=[x==y for x,y in zip(a,z)],ops=m.ops,wanted_ops=ops);return m
def cases():
 rows=[]
 for i,(angle,success,mutation,rm)in enumerate(itertools.product((0xFFFFFFFF,0,1,0x1000001,0x7FFFFFFF,0x80000000),(0,1),range(16),range(4))):
  values=(angle,0x87654321,0x80000000,0x7FFFFFFF,0x12340081,0xFEDCBA82,0xABCDEF83,(0,255,0x87654380)[i%3],0xF00DCAFE);pairs=((fp.bits(.33333334),fp.bits(-.7777778)),(0,0x80000000),(1,0x80000001),(fp.bits(1.),fp.bits(-1.)))
  rows.append(Case(values=values,success=success,mutation=mutation,rm=rm,phase=8*(rm&1),seed=i,sine=pairs[i%4][0],cosine=pairs[i%4][1]))
 return rows
def main():
 streams=[bound_blob(*payload(o/f,'func_15165F80'),symbols())for f in('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o')];assert all(w==streams[0]for w in streams[:4]);rows=cases();seen=set()
 for c in rows:
  models=[check(w,c,i==4)for i,w in enumerate(streams)];assert all(state(m)==state(models[0])for m in models[1:4]);raw_relation(models[0],models[4]);seen.update(p for p in models[0].visits if ENTRY<=p<ENTRY+408)
 cuts=connected=0
 for c in(Case(success=0),Case(),Case(values=replace(Case(),values=(33,*Case().values[1:])).values,mutation=15,phase=8,rm=3),Case(values=(0x7FFFFFFF,*Case().values[1:]),mutation=1,rm=2)):
  c=replace(c,connected=1);models=[check(w,c,i==4)for i,w in enumerate(streams)];assert all(state(m)==state(models[0])for m in models[1:4]);raw_relation(models[0],models[4]);connected+=1
  for cut in range(models[0].all_accesses):
   faults=[]
   for i,w in enumerate(streams):
    m=Machine(w,c,i==4);m.cut=cut
    try:m.run();raise AssertionError('missing injected access boundary')
    except AccessBoundary:faults.append(m)
   assert all(state(m)==state(faults[0])for m in faults[1:4]);raw_relation(faults[0],faults[4]);cuts+=1
 assert len(seen)==102,(len(seen),sorted(set(range(ENTRY,ENTRY+408,4))-seen))
 controls=[]
 for name,word,new,c in [('angle-gate',0x14610010,0x10610010,Case()),('captured-y',0x00C08025,0x00A08025,Case()),('quad-count',0x24060002,0x24060001,Case()),('UV',0x24032000,0x24032001,Case()),('allocation-selector',0xAFAE0010,0xAFA00010,Case()),('trig-scale',0x3C0142FE,0x3C0142FC,Case(values=(33,*Case().values[1:]))),('angular-mode',0xA0EA0095,0xA0E00095,Case(values=(33,*Case().values[1:])))]:
  wrong=streams[0][:];at=wrong.index(word);wrong[at]=new;m=Machine(wrong,c).run();memory,calls,packets,ops,csr=reference(fixture(c),c);assert(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr)!=(public(memory,c),calls,packets,ops,csr),name;controls.append(dict(name=name,offset=at*4,comparison_mismatch=True))
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,executed_retail_words=len(seen),literal_full_private_fault_quadruples=cuts,raw_same_memory_FP_preserved_register_and_consumed_operand_fault_relations=cuts,raw_full_fault_register_identity_not_claimed=True,complete_public_reference_with_FP_memory_observers=True,all_four_rounding_modes_signed_conversion_and_truncation=True,guest_only_incoming_home_and_private_slot_mutations=True,connected_original_origin_cases_per_stream=connected,original_origin_body_words=7,original_origin_slot_words=9,trig_and_allocator_backends_opaque=True,effective_comparison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
