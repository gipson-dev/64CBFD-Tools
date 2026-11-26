"""Ordered emitter effects, literal faults and explicit raw private-frame relation."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic
from tools.tests.game_random_targets_1518f1a0_guest import fp
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_attached_random_emitter_150e06d8_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x150E06D8;ACTOR=0x300000;ALT=0x302000;BANK=0x310000;OTHER_BANK=0x320000;MARK=0x330000;ALTPOINT=0x340000;TABLE_A=0x800A0F70;TABLE_B=0x800A0F88;PLAYER=0x80088988;MATRIX=0x15145EA4;RNG_I=0x150ADA20;RNG_F=0x150ADA68;EMIT=0x15102B38;u32=lambda x:x&0xFFFFFFFF;s16=lambda x:((x&65535)^32768)-32768;HOMES={0x44:0x60,0x48:0x4C,0x4C:0x48,0x50:0x44,0x54:0x50,0x58:0x54,0x5C:0x58,0x60:0x5C}
class StutterBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
 enabled:int=1
 variant:int=0
 selector:int=255
 context:int=1
 player:int=0
 floats:tuple=(fp.bits(.25),fp.bits(.5),fp.bits(.75))
 ints:tuple=(0xFFFFFFFF,0x80000000)
 point:tuple=(fp.bits(17.25),fp.bits(-2.5),fp.bits(31.))
 mutation:int=0
 phase:int=0
 seed:int=0
 rm:int=0
 flags:int=4
 provider_flags:int=0x12004
def symbols():return dict(D_800A0F70=TABLE_A,D_800A0F88=TABLE_B,D_80088988=PLAYER,func_15145EA4=MATRIX,func_150ADA20=RNG_I,func_150ADA68=RNG_F,func_15102B38=EMIT)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def frame(c):return STACK+c.phase-112
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def mapped_address(p,c,raw):
 if not raw:return p
 off=p-frame(c);word=off&~3
 return frame(c)+HOMES[word]+(off&3)if word in HOMES else p
def raw_address(p,c):
 off=p-frame(c);word=off&~3;inv={v:k for k,v in HOMES.items()};return frame(c)+inv[word]+(off&3)if word in inv else p
def fixture(c,raw=False):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((ACTOR-16,0x220),(ALT-16,0x220),(MARK,64),(ALTPOINT-16,64),(PLAYER-8,20),(TABLE_A-16,80)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(ACTOR,ALT):put(m,p+0x1D4,BANK if c.enabled else 0);m[p+0x3B]=77
 for i,v in enumerate((o/'table-presets.bin').read_bytes()):m[TABLE_A+i]=v
 m[PLAYER]=c.player&255
 return{raw_address(p,c):v for p,v in m.items()}if raw else m
def effect(m,c,t,args,ordinal,raw=False):
 put(m,MARK,read(m,MARK)+1);home=STACK+c.phase
 if t==MATRIX:
  inp,out=read(m,args[0]),read(m,args[1]);assert inp in(TABLE_A,TABLE_A+12)
  for i,v in enumerate(c.point):put(m,out+4*i,v)
  if c.mutation&2:put(m,args[0],TABLE_B);put(m,args[1],ALTPOINT)
 if c.mutation&1:
  m[PLAYER]=(m[PLAYER]+1)&3;put(m,TABLE_A,fp.bits(19.));put(m,ACTOR+0x1D4,OTHER_BANK)
 if c.mutation&4:
  put(m,home,ALT);put(m,home+4,read(m,home+4)^1);put(m,home+8,0x87654380);put(m,home+12,0xFEDCBA98)
 if t==EMIT:put(m,MARK+4,0x13579BDF)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;sp=frame(c);calls=[];packets=[];ops=[];csr=c.rm|c.flags;counts={RNG_I:0,RNG_F:0}
 for i,v in enumerate((ACTOR,c.variant,c.selector,c.context)):put(m,home+4*i,v)
 def call(t,args):
  nonlocal csr
  args=tuple(map(u32,args));calls.append((t,args))
  if t==EMIT:packets.append((data(m,args[4],8),data(m,args[8],12),data(m,args[2],12),data(m,args[3],12),m[args[0]+0x3B]))
  ordinal=counts.get(t,0);effect(m,c,t,args,ordinal);csr=(csr&~0x3F000)|c.provider_flags
  if t in counts:counts[t]+=1;return c.ints[ordinal]if t==RNG_I else c.floats[ordinal]
  return 0xDEADBEEF
 def calc(kind,a,b):
  nonlocal csr
  ops.append((kind,a,b,csr));v,flags=arithmetic(a,b,kind,csr&3);csr=(csr&~0x3F000)|flags;return v
 if read(m,ACTOR+0x1D4):
  put(m,sp+0x54,TABLE_A+12*(c.variant&255));put(m,sp+0x50,sp+0x64);call(MATRIX,(sp+0x54,sp+0x50,read(m,ACTOR+0x1D4)+64*m[PLAYER],1))
  v=call(RNG_F,());put(m,sp+0x5C,calc(0,calc(2,v,fp.bits(1.)),fp.bits(2.)))
  v=call(RNG_F,());put(m,sp+0x58,calc(0,calc(2,v,fp.bits(14.)),fp.bits(28.)))
  first=call(RNG_I,());second=call(RNG_I,());v=call(RNG_F,());size=calc(0,calc(2,v,fp.bits(300.)),fp.bits(400.));variant=read(m,home+4)&255;assert variant in(0,1)
  call(EMIT,(read(m,home),m[PLAYER],TABLE_A+12*variant,TABLE_B+12*variant,sp+0x58,first%3+4,second%156+100,size,sp+0x64,255,0,0xFFFFFFFF,read(m,home+8)&255,read(m,home+12)))
 return m,calls,packets,ops,csr
class Code(TrackedCode):
 def __getitem__(self,pc):
  w=super().__getitem__(pc);m=self.owner
  if m.stop_pc==pc:raise StutterBoundary
  npc=m.npc(pc);op=w>>26
  if op==4:m.operands.append((npc,'beq',m.r[w>>21&31],m.r[w>>16&31]))
  elif op==3:m.operands.append((npc,'jal',((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2)))
  elif op==0 and w&63==8:m.operands.append((npc,'jr',m.npc(m.r[w>>21&31])))
  return w
class Machine(FactoryOracle):
 def __init__(self,words,c,raw=False):
  self.c=c;self.raw=raw;self.ptr_defined=False;self.stop_pc=None;self.access_pcs=[];self.ops=[];self.operands=[];self.packets=[];super().__init__(words,fixture(c,raw),c,entry=ENTRY,s=symbols(),arguments=(ACTOR,c.variant,c.selector,c.context));self.counts={RNG_I:0,RNG_F:0};self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:];self.code=Code(self.code,self)
 def npc(self,p):return p+4 if self.raw and ENTRY+0x38<=p<ENTRY+400 else p
 def address(self,p):return mapped_address(p,self.c,self.raw)
 def pointer_value(self,p,value):return self.address(value)if p==frame(self.c)+0x10 else value
 def get(self,p,n):
  value=super().get(p,n)
  if self.own_instruction:self.access_pcs.append(self.npc(self.current_pc))
  return value
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:
   self.access_pcs.append(self.npc(self.current_pc))
   if p==frame(self.c)+0x10 and n==4:self.ptr_defined=True
 def execute(self,w):
  op,rs,rt,rd,fun=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;npc=self.npc(self.current_pc);imm=s16(w)
  if not(npc==ENTRY+0x38 and not self.raw):
   if op in(35,36,43,49,57):self.operands.append((npc,'memory',op,self.address(u32(self.r[rs]+imm))))
   elif op==9:self.operands.append((npc,'addsp',self.address(u32(self.r[rs]+imm)))if rs==29 else(npc,'addiu',self.r[rs],imm))
   elif op==15:self.operands.append((npc,'lui',w&65535))
   elif op==0:
    values=(self.r[rt],w>>6&31)if fun in(0,2,3)else(self.hi,)if fun==16 else(self.lo,)if fun==18 else(self.r[rs],self.r[rt]);self.operands.append((npc,'R',fun,values))
   elif op==17:
    fmt=rs;self.operands.append((npc,'COP1',w&0x03FFFFFF,self.r[rt]if fmt==4 else self.f[w>>11&31],self.f[rt]if fmt==16 else 0))
   else:raise AssertionError(('unmodeled input observation',hex(w)))
  if op==17 and rs==16 and fun in(0,2):
   a,b=self.f[w>>11&31],self.f[rt];self.ops.append((fun,a,b,self.fcsr));value,flags=arithmetic(a,b,fun,self.fcsr&3);self.f[w>>6&31]=value;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  sizes={MATRIX:4,RNG_I:0,RNG_F:0,EMIT:14};assert t in sizes,hex(t);args=tuple(map(u32,self.arguments(sizes[t])));self.actual_args=args;canonical=list(args)
  for i in((0,1)if t==MATRIX else(4,)if t==EMIT else()):canonical[i]=self.address(canonical[i])
  self.calls.append((t,tuple(canonical)));self.events.append(('CALL',t,tuple(canonical)));self.operands.append((self.npc(self.current_pc),'call_RA',self.npc(self.r[31])))
  if t==EMIT:self.packets.append((data(self.memory,args[4],8),data(self.memory,args[8],12),data(self.memory,args[2],12),data(self.memory,args[3],12),self.memory[args[0]+0x3B]))
 def hook(self,t):
  n=self.counts.get(t,0);effect(self.memory,self.c,t,self.actual_args,n,self.raw)
  if t in self.counts:self.counts[t]+=1
  value=self.c.ints[n]if t==RNG_I else 0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value;self.fcsr=(self.fcsr&~0x3F000)|self.c.provider_flags
  if t==RNG_F:self.f[0]=self.c.floats[n]
def canonical_memory(m):
 result={m.address(p):v for p,v in m.memory.items()}
 if m.raw and m.ptr_defined:put(result,frame(m.c)+0x10,m.address(read(m.memory,frame(m.c)+0x10)))
 return result
def trace(m,drop_extra=False):
 assert len(m.trace)==len(m.access_pcs);return[(pc,kind,m.address(p),n,m.pointer_value(p,v))for pc,(kind,p,n,v)in zip(m.access_pcs,m.trace)if not(drop_extra and pc==ENTRY+0x38)]
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.packets,m.ops,m.operands,m.trace,m.current_pc,m.delay_of)
def raw_relation(a,b,final=False):
 assert canonical_memory(b)==a.memory,('frame memory',[(hex(p),a.memory.get(p),canonical_memory(b).get(p))for p in a.memory if a.memory[p]!=canonical_memory(b).get(p)][:5])
 assert a.f==b.f and(a.fcsr,a.hi,a.lo,a.calls,a.packets,a.ops,a.operands)==(b.fcsr,b.hi,b.lo,b.calls,b.packets,b.ops,b.operands),'used operands/FP/calls'
 assert trace(a,True)==trace(b),'mapped accesses'
 assert all(a.r[i]==b.r[i]for i in(*range(16,24),28,29,30))and a.r[31]==b.npc(b.r[31])
 if final:assert a.r==b.r
def check(words,c,raw=False):
 m=Machine(words,c,raw).run();memory,calls,packets,ops,csr=reference(fixture(c),c);got=(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr);want=(public(memory,c),calls,packets,ops,csr);assert got==want,dict(case=str(c),raw=raw,parts=[a==b for a,b in zip(got,want)],calls=m.calls,want_calls=calls,ops=m.ops,want_ops=ops);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[]
 for i,(enabled,variant,mutation,rm)in enumerate(itertools.product((0,1),(0,1,0x87654300,0x87654301),range(8),range(4))):
  rows.append(Case(enabled=enabled,variant=variant,selector=(0,0x87654380,255)[i%3],context=(0,1,0xFFFFFFFF,0x80000000)[i%4],player=(0,1,3,255)[i%4],floats=(fp.bits((i%5-2)*.25),fp.bits((i%3)*.5),fp.bits((i%7-3)*.25)),ints=((0,0xFFFFFFFF,0x80000000,0x7FFFFFFF)[i%4],(0xFFFFFFFF,0,155,156)[i%4]),mutation=mutation,rm=rm,phase=8*(rm&1),seed=i))
 return rows
def main():
 files=('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-base.o');streams=[bound_blob(*payload(o/f,'func_150E06D8'),symbols())for f in files];assert all(w==streams[0]for w in streams[:4]);rows=cases();seen=set()
 for c in rows:
  models=[check(w,c,i==4)for i,w in enumerate(streams)];assert all(state(m)==state(models[0])for m in models[1:4]);raw_relation(models[0],models[4],True);seen.update(p for p in models[0].visits if ENTRY<=p<ENTRY+404)
 cuts=pairs=stutters=0
 for c in(Case(enabled=0),Case(),Case(variant=1,mutation=7,phase=8,rm=3),Case(variant=0x87654300,mutation=2,rm=2)):
  full=Machine(streams[0],c).run();rawfull=Machine(streams[4],c,True).run();rawpcs=[pc for pc in rawfull.access_pcs];cursor=0
  for cut,npc in enumerate(full.access_pcs):
   models=[]
   for w in streams[:4]:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('missing normalized fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);cuts+=1;raw=Machine(streams[4],c,True)
   if npc==ENTRY+0x38:
    raw.stop_pc=ENTRY+0x38
    try:raw.run();raise AssertionError('missing stutter boundary')
    except StutterBoundary:pass
    assert read(models[0].memory,STACK+c.phase)==raw.r[14]==ACTOR;raw_relation(models[0],raw);stutters+=1
   else:
    assert rawpcs[cursor]==npc;raw.cut=cursor
    try:raw.run();raise AssertionError('missing raw common fault')
    except AccessBoundary:pass
    raw_relation(models[0],raw);pairs+=1;cursor+=1
  assert cursor==len(rawpcs)
 assert len(seen)==101,(len(seen),sorted(set(range(ENTRY,ENTRY+404,4))-seen))
 controls=[];original=streams[0]
 for name,predicate,change in [('gate',lambda w:w>>26==4,lambda w:(w&0x03FFFFFF)|(5<<26)),('range',lambda w:w==0x3C014160,lambda w:w+0x10),('multiply',lambda w:w>>26==17 and w>>21&31==16 and w&63==2,lambda w:w&~63),('signed-divide',lambda w:w>>26==0 and w&63==27,lambda w:w^1),('private-pair-home',lambda w:w>>26==57 and w>>21&31==29 and w&65535==0x5C,lambda w:(w&~65535)|0x58)]:
  at=next(i for i,w in enumerate(original)if predicate(w));wrong=original[:];wrong[at]=change(wrong[at]);c=Case();m=Machine(wrong,c).run();_,calls,packets,ops,_=reference(fixture(c),c);assert(m.calls,m.packets,m.ops)!=(calls,packets,ops),name;controls.append(dict(name=name,offset=at*4,comparison_mismatch=True))
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,executed_retail_words=len(seen),literal_full_private_fault_quadruples=cuts,raw_common_fault_frame_access_and_used_operand_pairs=pairs,extra_owner_read_stutter_boundaries=stutters,raw_fault_identity_not_claimed=True,all_original_normalized_faults_retained=True,ordinary_mapped_o32_stack_home_assumption_explicit=True,raw_frame_bijection_private_pointer_cell_and_closed_GPR_roles_qualified=True,all_consumed_instruction_inputs_compared_under_PC_frame_relation=True,complete_public_memory_14argument_calls_packets_and_FP_FCSR_reference=True,all_four_rounding_modes_and_unsigned_remainders=True,variant_domain_limited_to_pinned_two_entries=True,all_backends_opaque=True,effective_comparison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
