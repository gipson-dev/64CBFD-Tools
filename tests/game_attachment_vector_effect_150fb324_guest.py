"""Attachment vectors: literal normalized faults and explicit raw schedule relation."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_attachment_vector_effect_150fb324_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x150FB324;ACTOR=0x300000;ALT=0x310000;BANK=0x320000;OTHER=0x330000;MARK=0x340000;TABLE=0x800A1D30;MATRIX=0x15145EA4;FIRST=0x150FEC28;LAST=0x151D4408
u32=lambda v:v&0xFFFFFFFF
HOMES={0x44:0x78,0x48:0x74,**{i:i-8 for i in range(0x4C,0x7C,4)}}
PERM={0x11C:0x138,0x120:0x120,0x124:0x12C,0x128:0x13C,0x12C:0x140,0x130:0x130,0x134:0x11C,0x138:0x124,0x13C:0x128,0x140:0x134}
INVERSE={v:k for k,v in PERM.items()}
@dataclass(frozen=True)
class Case:
 enabled:int=1
 selector:int=0x87654380
 context:int=0x80000000
 points:tuple=tuple(fp.bits(v)for v in(1.,-2.,3.,.25,1.5,-.5,7.,-4.,.125))
 mutation:int=0
 phase:int=0
 seed:int=0
 rm:int=0
 flags:int=4
 provider_flags:int=0x12004

def symbols():return dict(D_800A1D30=TABLE,D_800A1D3C=TABLE+12,D_800A1D48=TABLE+24,D_800A1D54=TABLE+36,func_15145EA4=MATRIX,func_150FEC28=FIRST,func_151D4408=LAST)
def frame(c):return STACK+c.phase-160
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+2048}
def address(p,c,raw=False):
 if raw:
  d=p-frame(c);base=d&~3
  if base in HOMES:return frame(c)+HOMES[base]+(d&3)
 return p
def raw_address(p,c):
 d=p-frame(c);base=d&~3;inv={v:k for k,v in HOMES.items()}
 return frame(c)+inv[base]+(d&3)if base in inv else p
def fixture(c,raw=False):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
 # The actual fixture allocation is0x3C0 bytes, covering the helper's full
 # 64-byte matrix at bank+0x380. No nominal struct255-size assumption is used.
 for p,n in((ACTOR,0x200),(ALT,0x200),(BANK,0x3C0),(OTHER,0x3C0),(MARK,32),(TABLE,48)):
  m.update({p+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for p in(ACTOR,ALT):put(m,p+0x1D4,BANK if c.enabled else 0)
 for i,v in enumerate((o/'table-presets.bin').read_bytes()):m[TABLE+i]=v
 return{raw_address(p,c):v for p,v in m.items()}if raw else m
def packet(m,t,args):
 if t==MATRIX:
  assert args[3]==3
  return tuple(data(m,read(m,args[0]+i*4),12)for i in range(3)),data(m,args[2],64)
 if t==FIRST:return tuple(data(m,args[i],12)for i in(2,3,4))
 assert t==LAST
 return data(m,args[0],12),data(m,args[1],12),data(m,args[2],64)
def effect(m,c,t,args):
 put(m,MARK,read(m,MARK)+1)
 if t==MATRIX:
  for i in range(3):
   p=read(m,args[1]+4*i)
   for j in range(3):put(m,p+4*j,c.points[i*3+j])
 if c.mutation&1:
  for p in(ACTOR,ALT):put(m,p+0x1D4,OTHER)
  put(m,TABLE,fp.bits(19.));put(m,BANK+0x380,0x12345678)
 if c.mutation&2:
  h=STACK+c.phase;put(m,h,ALT if t==MATRIX else ACTOR);put(m,h+4,0x876543FF if t==MATRIX else 0xABCDEF00);put(m,h+8,0xFEDCBA98 if t==MATRIX else 0x13579BDF)
 if c.mutation&4:
  if t==MATRIX:put(m,read(m,args[0]),fp.bits(-17.25))
  elif t==FIRST:put(m,args[2]+4,fp.bits(7.));put(m,args[3]+8,fp.bits(8.));put(m,args[4],fp.bits(9.))
def reference(initial,c):
 m=dict(initial);h=STACK+c.phase;s=frame(c);calls=[];packets=[];ops=[];csr=c.rm|c.flags
 for i,v in enumerate((ACTOR,c.selector,c.context)):put(m,h+4*i,v)
 for dst,src in zip((0x68,0x5C,0x50,0x44),range(0,48,12)):
  for i in range(12):m[s+dst+i]=m[TABLE+src+i]
 def call(t,args):
  nonlocal csr
  args=tuple(map(u32,args));calls.append((t,args));packets.append((t,packet(m,t,args)));effect(m,c,t,args);csr=(csr&~0x3F000)|c.provider_flags
 if read(m,ACTOR+0x1D4):
  for i,p in enumerate((s+0x68,s+0x50,s+0x44)):put(m,s+0x38+4*i,p)
  for i,p in enumerate((s+0x94,s+0x88,s+0x7C)):put(m,s+0x2C+4*i,p)
  matrix=read(m,ACTOR+0x1D4)+0x380;put(m,s+0x78,matrix);call(MATRIX,(s+0x38,s+0x2C,matrix,3))
  # Match the three ordered scalar subtractions, including FCSR, independently
  # from their emitted stack-load/store scheduling.
  for i in range(3):
   a,b=read(m,s+0x7C+4*i),read(m,s+0x88+4*i);ops.append((1,a,b,csr));v,flags=arithmetic(a,b,1,csr&3);csr=(csr&~0x3F000)|flags;put(m,s+0x7C+4*i,v)
  call(FIRST,(read(m,h),14,s+0x68,s+0x5C,s+0x94,read(m,h+4)&255,read(m,h+8)))
  call(LAST,(s+0x88,s+0x7C,matrix,read(m,h),fp.bits(1.),read(m,h+4)&255,read(m,h+8)))
 return m,calls,packets,ops,csr
class Code(TrackedCode):
 def __getitem__(self,pc):
  w=super().__getitem__(pc);m=self.owner
  if m.stop_pc==pc:raise StutterBoundary
  return w
class StutterBoundary(Exception):pass
class Machine(FactoryOracle):
 def __init__(self,words,c,raw=False):
  self.c=c;self.raw=raw;self.stop_pc=None;self.ops=[];self.operands=[];self.packets=[];self.timeline=[];self.access_pcs=[];self.defined_pointer_cells=set()
  super().__init__(words,fixture(c,raw),c,entry=ENTRY,s=symbols(),arguments=(ACTOR,c.selector,c.context));self.initial=dict(self.memory);self.fcsr=c.rm|c.flags;self.before_f=self.f[:];self.code=Code(self.code,self)
 def npc(self,p):
  if self.raw and ENTRY<=p<ENTRY+400:
   off=p-ENTRY;pre=off+(4 if off>=0xC4 else 0);return ENTRY+INVERSE.get(pre,pre)
  return p
 def addr(self,p):return address(p,self.c,self.raw)
 def pv(self,p,v):return self.addr(v)if p in self.defined_pointer_cells else v
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.access_pcs.append(self.npc(self.current_pc));self.timeline.append((self.npc(self.current_pc),'R',self.addr(p),n,self.pv(p,v)))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:
   if n==4 and p-frame(self.c)in(0x10,0x38,0x3C,0x40):self.defined_pointer_cells.add(p)
   self.access_pcs.append(self.npc(self.current_pc));self.timeline.append((self.npc(self.current_pc),'W',self.addr(p),n,self.pv(p,v&((1<<(8*n))-1))))
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;pc=self.npc(self.current_pc);imm=((w&65535)^32768)-32768
  if op in(35,36,43,49,57):self.operands.append((pc,'memory',op,self.addr(u32(self.r[rs]+imm))))
  elif op==9:self.operands.append((pc,'addiu',self.addr(u32(self.r[rs]+imm)))if rs==29 else(pc,'addiu',self.r[rs],imm))
  elif op==15:self.operands.append((pc,'lui',w&65535))
  elif op==0:self.operands.append((pc,'R',fn,self.r[rs],self.r[rt]))
  elif op==17:self.operands.append((pc,'COP1',w&0x03FFFFFF,self.r[rt]if rs==4 else self.f[rd],self.f[rt]if rs==16 else 0))
  else:raise AssertionError(('unmodeled consumed inputs',hex(w)))
  if op==17 and rs==16 and fn==1:
   a,b=self.f[rd],self.f[rt];self.ops.append((1,a,b,self.fcsr));v,flags=arithmetic(a,b,1,self.fcsr&3);self.f[w>>6&31]=v;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t in(MATRIX,FIRST,LAST),hex(t);args=tuple(map(u32,self.arguments(4 if t==MATRIX else 7)));self.actual_args=args;canonical=list(args)
  for i in((0,1)if t==MATRIX else(2,3,4)if t==FIRST else(0,1)):canonical[i]=self.addr(canonical[i])
  self.calls.append((t,tuple(canonical)));self.packets.append((t,packet(self.memory,t,args)));self.operands.append((self.npc(self.current_pc),'call_RA',self.npc(self.r[31])))
 def hook(self,t):
  effect(self.memory,self.c,t,self.actual_args)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF;self.fcsr=(self.fcsr&~0x3F000)|self.c.provider_flags
def canonical_memory(m):
 result={m.addr(p):v for p,v in m.memory.items()}
 if m.raw:
  for p in m.defined_pointer_cells:put(result,m.addr(p),m.addr(read(m.memory,p)))
 return result
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.packets,m.ops,m.operands,m.trace,m.timeline,m.current_pc,m.delay_of)
def ordered(m,values,drop_extra=False):return sorted(v for v in values if not(drop_extra and v[0]==ENTRY+0xC4))
def raw_relation(a,b,complete=True):
 assert canonical_memory(b)==a.memory,('frame-memory',[(hex(p),a.memory.get(p),canonical_memory(b).get(p))for p in a.memory if a.memory[p]!=canonical_memory(b).get(p)][:5])
 assert(a.f,a.fcsr,a.hi,a.lo,a.calls,a.packets,a.ops)==(b.f,b.fcsr,b.hi,b.lo,b.calls,b.packets,b.ops),'raw FP/calls/packets'
 assert ordered(a,a.operands,True)==ordered(b,b.operands),'raw consumed operands under instruction permutation'
 assert ordered(a,a.timeline,True)==ordered(b,b.timeline),'raw memory events under explicit schedule permutation'
 assert all(a.r[i]==b.r[i]for i in(*range(16,24),28,29,30))and a.r[31]==b.npc(b.r[31])
def check(words,c,raw=False):
 m=Machine(words,c,raw).run();memory,calls,packets,ops,csr=reference(fixture(c),c);got=(public(m.memory,c),m.calls,m.packets,m.ops,m.fcsr);want=(public(memory,c),calls,packets,ops,csr)
 assert got==want,dict(case=str(c),raw=raw,parts=[a==b for a,b in zip(got,want)],calls=m.calls,want_calls=calls,ops=m.ops,want_ops=ops)
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[];points=[tuple(fp.bits(v)for v in(1.,-2.,3.,.25,1.5,-.5,7.,-4.,.125)),(0,0x80000000,1,0x80000001,1,0x80000000,0x80000000,0,1),tuple(fp.bits(v)for v in(1e20,3.,-1e20,1.,-1e20,3.,1e20,1.,-1e20)),(0x7F7FFFFF,0,1,0xFF7FFFFF,0x80000000,0x80000001,0x7F7FFFFF,0x80000000,1)]
 for i,(enabled,selector,mutation,rm)in enumerate(itertools.product((0,1),(0,1,255,0x87654380),range(8),range(4))):rows.append(Case(enabled=enabled,selector=selector,context=(0,1,0xFFFFFFFF,0x80000000)[i%4],mutation=mutation,rm=rm,phase=8*(i&1),seed=i,points=points[(i//4)%4]))
 return rows
def main():
 files=('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o');streams=[bound_blob(*payload(o/f,'func_150FB324'),symbols())for f in files];assert all(w==streams[0]for w in streams[:4]);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c,i==4)for i,w in enumerate(streams)];assert all(state(m)==state(models[0])for m in models[1:4]);raw_relation(models[0],models[4]);seen.update(p for p in models[0].visits if ENTRY<=p<ENTRY+404)
 cuts=rawcuts=stutters=0
 for c in(Case(enabled=0),Case(),Case(mutation=7,phase=8,rm=3),Case(mutation=2,rm=2)):
  normal=check(streams[0],c);rawfull=check(streams[4],c,True)
  for cut in range(normal.all_accesses):
   faults=[]
   for w in streams[:4]:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('missing normalized fault')
    except AccessBoundary:faults.append(m)
   assert all(state(m)==state(faults[0])for m in faults[1:]);cuts+=1
  # Raw faults are intentionally different in the reordered block. Keep each
  # raw event/value and FP/call prefix, without claiming a false full-state
  # equality to a retail fault at a different independent schedule frontier.
  normal_events={v[0]:v for v in normal.timeline if v[0]!=ENTRY+0xC4}
  for cut in range(rawfull.all_accesses):
   m=Machine(streams[4],c,True);m.cut=cut
   try:m.run();raise AssertionError('missing raw fault')
   except AccessBoundary:pass
   assert m.trace==rawfull.trace[:cut]and m.access_pcs==rawfull.access_pcs[:cut]
   assert all(normal_events[v[0]]==v for v in m.timeline)
   assert m.ops==normal.ops[:len(m.ops)]and m.calls==normal.calls[:len(m.calls)]and m.packets==normal.packets[:len(m.packets)];rawcuts+=1
  if c.enabled:
   n=normal.access_pcs.index(ENTRY+0xC4);m=Machine(streams[0],c);m.cut=n
   try:m.run();raise AssertionError('missing extra home fault')
   except AccessBoundary:pass
   raw=Machine(streams[4],c,True);raw.stop_pc=ENTRY+0xC4
   try:raw.run();raise AssertionError('missing raw home stutter')
   except StutterBoundary:pass
   assert read(m.memory,STACK+c.phase)==raw.r[13]==ACTOR
   assert canonical_memory(raw)==m.memory and ordered(m,m.timeline)==ordered(raw,raw.timeline);stutters+=1
 assert len(seen)==101,(len(seen),sorted(set(range(ENTRY,ENTRY+404,4))-seen))
 controls=[]
 for name,word,new in [('effect-id',0x2405000E,0x2405000F),('transform-count',0x24070003,0x24070002),('vector-subtraction',0x46062201,0x46062200),('selector',0x93AC00A7,0x93AC00A6),('matrix-bias',0x24C60380,0x24C60340),('direction-home',0x27A5007C,0x27A50088)]:
  wrong=streams[0][:];at=wrong.index(word);wrong[at]=new
  try:m=Machine(wrong,Case()).run()
  except AssertionError:
   # An invalid helper contract must be rejected explicitly; these two controls
   # violate its count/bank precondition rather than produce a valid packet.
   assert name=='transform-count';controls.append(dict(name=name,contract_rejected=True));continue
  _,calls,packets,ops,csr=reference(fixture(Case()),Case());assert(m.calls,m.packets,m.ops,m.fcsr)!=(calls,packets,ops,csr),name;controls.append(dict(name=name,comparison_mismatch=True))
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,executed_retail_words=len(seen),literal_full_private_fault_quadruples=cuts,raw_ordered_fault_prefixes=rawcuts,extra_owner_read_stutter_boundaries=stutters,all_original_normalized_faults_retained=True,raw_full_fault_identity_not_claimed=True,raw_full_frame_private_pointer_and_consumed_input_schedule_relation=True,raw_reordering_not_erased_from_fault_checks=True,matrix_fixture_extent=0x3C0,matrix_bias=0x380,matrix_access_bytes=64,all_COP1_subtraction_operands_order_and_FCSR_qualified=True,incoming_home_mutations_guest_only=True,helper_backends_opaque=True,effective_comparison_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
