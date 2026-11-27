"""Phase/fall state, wrapped duration, ordered FP and literal memory fault cuts."""
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
from tools.experiments import game_phase_height_update_1511f788_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x1511F788;ACTOR=0x300000;ALT=0x310000;MARK=0x320000;GATE=0x800BE9B4;TICKS=0x800BE9E4;RNG=0x150ADA20;COS=0x15047C00
u32=lambda v:v&0xFFFFFFFF;signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000;half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 object:int=ACTOR
 gate:int=1
 height:int=-9999
 offset:int=fp.bits(3.25)
 duration:int=0x7FFFFFFF
 phase_value:int=0x87654321
 mode:int=1
 timer:int=0xFFFFFFFF
 ticks:int=1
 integer:int=0x87654380
 cosine:int=fp.bits(-.33333334)
 mutation:int=0
 phase:int=0
 seed:int=0
 rm:int=0
 flags:int=4
 provider_flags:int=0x12004
def symbols():return dict(D_800BE9B4=GATE,D_800BE9E4=TICKS,func_150ADA20=RNG,cosf=COS)
def frame(c):return STACK+c.phase-48
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-2048<=p<STACK+c.phase+2048}
def observation(m):return data(m,ACTOR,0x140),data(m,ALT,0xA0),m[GATE],read(m,TICKS),data(m,MARK,16)
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
 for p,n in((ACTOR,0x140),(ALT,0xA0),(MARK,16),(GATE-8,20),(TICKS-8,20)):m.update({p+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for p in(ACTOR,ACTOR+0xA0,ALT):
  for off,v,n in((0x12,c.height if p==c.object else 32767,2),(0x18,c.offset if p==c.object else fp.bits(-.5),4),(0x3C,c.duration,4),(0x5C,0x8001,2),(0x6E,0,1),(0x6F,0x40,1),(0x7C,c.phase_value if p==c.object else 0x80000001,4),(0x80,c.mode,4),(0x84,c.timer,4),(0x38,ENTRY,4)):put(m,p+off,u32(v),n)
 m[GATE]=c.gate&255;put(m,TICKS,c.ticks);return m
def effect(m,c,t):
 p=c.object;put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:
  put(m,TICKS,0xFFFFFFFF if t==RNG else 0x80000001);m[GATE]^=0x80;put(m,p+0x3C,read(m,p+0x3C)^0xFFFFFFFF);put(m,p+0x7C,0x7FFFFFFF if t==RNG else 0x80000000)
 if c.mutation&2:
  put(m,p+0x12,-10000 if t==RNG else -9999,2);put(m,p+0x18,fp.bits(-7.25));put(m,p+0x80,(c.mode+1)&3);put(m,p+0x84,0x7FFFFFFF)
 if c.mutation&4:
  # These unescaped-home mutations are guest-only architectural probes.
  h=STACK+c.phase;s=frame(c);put(m,h,ALT if t==RNG else c.object);put(m,s+0x24,0x80000000 if t==RNG else 0x7FFFFFFF);put(m,s+0x1E,0x8001 if t==RNG else 0x7FFF,2)
def quotient(v):
 v=signed(u32(v*60));return u32((abs(v)//60)*(-1 if v<0 else 1))
def reference(initial,c,initial_csr=None):
 m=dict(initial);owner=c.object;h=STACK+c.phase;s=frame(c);calls=[];packets=[];ops=[];csr=c.rm|c.flags if initial_csr is None else initial_csr;gate=m[GATE]
 def operation(fn,a,b=0):
  nonlocal csr
  ops.append((fn,a,b,csr,observation(m)))
  v,flags=convert_integer(a,csr&3)if fn==32 else trunc(a)if fn==13 else arithmetic(a,b,fn,csr&3)
  csr=(csr&~0x3F000)|flags;return v
 def call(t,args):
  nonlocal csr
  calls.append((t,tuple(map(u32,args))));packets.append((t,observation(m)));effect(m,c,t);csr=(csr&~0x3F000)|c.provider_flags;return c.integer if t==RNG else c.cosine
 a=operation(32,u32(half(read(m,owner+0x12,2))));previous=operation(13,operation(0,a,read(m,owner+0x18)));put(m,s+0x1E,previous,2);threshold=quotient(read(m,owner+0x3C))
 if gate:
  put(m,s+0x24,threshold);put(m,h,owner);value=call(RNG,());owner=read(m,h);threshold=read(m,s+0x24);put(m,owner+0x7C,value&65535)
 phase=read(m,owner+0x7C);put(m,h,owner);put(m,s+0x24,threshold);radians=operation(2,operation(32,phase),0x3BB40000);cosine=call(COS,(radians,));owner=read(m,h);threshold=read(m,s+0x24);offset=operation(2,cosine,fp.bits(25.));oldphase=read(m,owner+0x7C);mode=read(m,owner+0x80);put(m,owner+0x18,offset);put(m,owner+0x7C,u32(oldphase+10*read(m,TICKS)))
 if mode==1:
  timer=u32(read(m,owner+0x84)+read(m,TICKS));put(m,owner+0x84,timer)
  if signed(threshold)<signed(timer):put(m,owner+0x80,2)
 elif mode==2:
  height=u32(half(read(m,owner+0x12,2))-read(m,TICKS));put(m,owner+0x12,height,2)
  if half(read(m,owner+0x12,2))<-10000:m[owner+0x6E]=1
 height=read(m,owner+0x12,2);old=read(m,s+0x1E,2);a=operation(32,u32(half(height)));b=operation(32,u32(half(old)));new=operation(0,a,read(m,owner+0x18));delta=operation(13,operation(1,new,b));put(m,owner+0x5C,delta,2)
 return m,calls,packets,ops,csr
class Code(TrackedCode):
 def __getitem__(self,pc):
  w=super().__getitem__(pc);m=self.owner;op=w>>26
  if op in(4,5,6,7,20,21):m.operands.append((m.npc(pc),'branch',op,m.r[w>>21&31],m.r[w>>16&31]))
  elif op==3:m.operands.append((m.npc(pc),'jal',((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2)))
  return w
class Machine(FactoryOracle):
 def __init__(self,words,c,raw=False):
  self.c=c;self.raw=raw;self.ops=[];self.operands=[];self.packets=[];self.timeline=[]
  super().__init__(words,fixture(c),c,entry=ENTRY,s=symbols(),arguments=(c.object,));self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:];self.code=Code(self.code,self)
 def npc(self,p):
  if self.raw and ENTRY+0x50<=p<ENTRY+0x74:return p+4
  if self.raw and p==ENTRY+0x74:return ENTRY+0x50
  return p
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.timeline.append((self.npc(self.current_pc),'R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.timeline.append((self.npc(self.current_pc),'W',p,n,v&((1<<(8*n))-1)))
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;pc=self.npc(self.current_pc);imm=((w&65535)^32768)-32768
  if op in(32,33,35,36,40,41,43,49,57):self.operands.append((pc,'memory',op,u32(self.r[rs]+imm)))
  elif op==9:self.operands.append((pc,'addiu',self.r[rs],imm))
  elif op in(10,11,12,13):self.operands.append((pc,'immediate',op,self.r[rs],w&65535))
  elif op==15:self.operands.append((pc,'lui',w&65535))
  elif op==0:
   values=(self.r[rt],w>>6&31)if fn in(0,2,3)else(self.lo,)if fn==18 else(self.hi,)if fn==16 else(self.r[rs],self.r[rt]);self.operands.append((pc,'R',fn,values))
  elif op==17:
   operand=self.r[rt]if rs==4 else self.f[rd]if rs in(16,20)else self.f[rd];other=self.f[rt]if rs==16 and fn in(0,1,2)else 0
   self.operands.append((pc,'COP1',rs,fn,rd,w>>6&31,operand,other))
  else:raise AssertionError(('unmodeled instruction',hex(w)))
  if op==17 and(rs==20 and fn==32 or rs==16 and fn in(0,1,2,13)):
   a,b=self.f[rd],self.f[rt]if fn in(0,1,2)else 0;self.ops.append((fn,a,b,self.fcsr,observation(self.memory)));v,flags=convert_integer(a,self.fcsr&3)if fn==32 else trunc(a)if fn==13 else arithmetic(a,b,fn,self.fcsr&3);self.f[w>>6&31]=v;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t in(RNG,COS),hex(t);args=()if t==RNG else(self.f[12],);self.calls.append((t,args));self.packets.append((t,observation(self.memory)));self.operands.append((self.npc(self.current_pc),'call_RA',self.r[31]))
 def hook(self,t):
  effect(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.c.integer)if t==RNG else 0xDEADBEEF;self.fcsr=(self.fcsr&~0x3F000)|self.c.provider_flags
  if t==COS:self.f[0]=self.c.cosine
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.packets,m.ops,m.operands,m.trace,m.timeline,m.current_pc,m.delay_of)
def raw_relation(a,b):
 assert(a.memory,a.f,a.fcsr,a.hi,a.lo,a.calls,a.packets,a.ops,a.trace,a.timeline)==(b.memory,b.f,b.fcsr,b.hi,b.lo,b.calls,b.packets,b.ops,b.trace,b.timeline),'raw full memory/FP/access relation'
 assert sorted(a.operands)==sorted(b.operands),'raw consumed inputs under MFLO scheduling'
 assert all(a.r[i]==b.r[i]for i in(*range(16,24),28,29,30,31))
def check(words,c,raw=False):
 m=Machine(words,c,raw).run();memory,calls,packets,ops,csr=reference(fixture(c),c);got=(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr);want=(public(memory,c),calls,packets,ops,csr)
 assert got==want,dict(case=str(c),raw=raw,parts=[x==y for x,y in zip(got,want)],ops=m.ops,want_ops=ops)
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[];durations=(0,1,35791394,35791395,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xFDDDDDDD);ticks=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,10001,65535,65536);heights=(-32768,-10000,-9999,32767)
 for i,(gate,mode,mutation,rm,heightindex)in enumerate(itertools.product((0,1,255),range(4),range(4),range(4),range(4))):
  rows.append(Case(gate=gate,mode=mode,mutation=mutation,height=heights[heightindex],duration=durations[(i//4)%8],ticks=ticks[(i//16)%8],phase_value=(0,1,0x7FFFFFFF,0x80000000)[i%4],integer=(0,0xFFFFFFFF,0x80000000,0x87654380)[(i//4)%4],cosine=(0,0x80000000,fp.bits(.33333334),fp.bits(-.7777778))[i%4],timer=(0,1,0x7FFFFFFF,0xFFFFFFFF)[i%4],phase=8*(i&1),seed=i,rm=rm))
 rows.extend([Case(mutation=7,rm=3,phase=8),Case(gate=0,mutation=4,mode=2),Case(offset=0x7FC12345,cosine=0x7FC12345)])
 return rows
def main():
 files=('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o');streams=[bound_blob(*payload(o/f,'func_1511F788'),symbols())for f in files];assert all(w==streams[0]for w in streams[:4]);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c,i==4)for i,w in enumerate(streams)];assert all(state(m)==state(models[0])for m in models[1:4]);raw_relation(models[0],models[4]);seen.update(p for p in models[0].visits if ENTRY<=p<ENTRY+420)
 unreachable={ENTRY+x for x in(0x5C,0x6C,0x70,0x74)};assert set(range(ENTRY,ENTRY+420,4))-seen==unreachable
 cuts=0
 for c in(Case(gate=0,mode=0),Case(),Case(mode=2,mutation=7,phase=8,rm=3),Case(mode=1,mutation=4,rm=2)):
  full=check(streams[0],c)
  for cut in range(full.all_accesses):
   faults=[]
   for i,w in enumerate(streams):
    m=Machine(w,c,i==4);m.cut=cut
    try:m.run();raise AssertionError('missing injected access boundary')
    except AccessBoundary:faults.append(m)
   assert all(state(m)==state(faults[0])for m in faults[1:4]);raw_relation(faults[0],faults[4]);cuts+=1
 controls=[]
 for name,word,new,c in [('duration-factor',0x2402003C,0x2402003D,Case()),('phase-mask',0x3049FFFF,0x30497FFF,Case(integer=0xFFFFFFFF)),('amplitude',0x3C0141C8,0x3C0141C0,Case()),('phase-step',0x000D6840,0x000D6880,Case()),('fall-boundary',0x29A1D8F0,0x29A1D8F1,Case(gate=0,mode=2,height=-9999,ticks=1)),('delta',0x460A3401,0x460A3400,Case())]:
  wrong=streams[0][:];at=wrong.index(word);wrong[at]=new;m=Machine(wrong,c).run();memory,calls,packets,ops,csr=reference(fixture(c),c);assert(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr)!=(public(memory,c),calls,packets,ops,csr),name;controls.append(dict(name=name,offset=at*4,comparison_mismatch=True))
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,retail_words=105,executed_reachable_words=len(seen),unreachable_preserved_offsets=['0x5C','0x6C','0x70','0x74'],stable_divisor_60_CFG_proof=True,literal_full_private_fault_quadruples=cuts,raw_full_memory_FP_access_and_consumed_input_fault_relations=cuts,raw_full_dead_GPR_fault_identity_not_claimed=True,no_frame_or_private_home_remap=True,all_FP_operands_order_FCSR_and_public_observers_qualified=True,all_32bit_duration_contract_is_wrapped_low_word_then_signed_divide=True,helpers_opaque=True,private_incoming_and_local_home_mutations_guest_only=True,effective_comparison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
