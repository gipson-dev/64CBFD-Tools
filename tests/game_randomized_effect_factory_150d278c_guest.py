"""Ordered finite random arithmetic, palette snapshot and original payload tail."""
from pathlib import Path
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import itertools,json,math,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_randomized_effect_factory_150d278c_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x150D278C;INPUT=0x30000;ALT=0x50000;OUTPUT=0x60000;MARK=0x70000;FRNG=0x150ADA68;RNG=0x150ADA20;COPY=0x10022EC0;FACTORY=0x15149130;PALETTE=0x800A0990;CONSTANTS=tuple(range(0x800A099C,0x800A09B0,4));NAMES=tuple('D_%08X'%a for a in CONSTANTS);bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 parameters:int=0
 created:int=0
 command:int=0xABCDEF01
 floats:tuple=tuple(map(bits,(.125,.375,.625)))
 integers:tuple=(0xFFFFFFFF,2,0x80000000,7)
 priority:int=0xABCD0080
 context:int=0x12345678
 success:int=1
 mutation:int=0
 private:int=0
 alias:int=0
 copy:int=0
 phase:int=0
 seed:int=0
 rm:int=0
def symbols():return dict(func_150ADA68=FRNG,func_150ADA20=RNG,memcpy=COPY,func_15149130=FACTORY,D_800A0990=PALETTE,**dict(zip(NAMES,CONSTANTS)))
def input_pointer(c):return c.parameters if c.parameters else STACK+c.phase+64 if c.alias==2 else INPUT
def result(c):return c.created if c.created else INPUT-0x28 if c.alias==1 else OUTPUT
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,4096)}
 for base,n in((INPUT-64,320),(ALT,192),(OUTPUT-32,256),(MARK,16)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 m.update({PALETTE+i:b for i,b in enumerate(rom()[0x245450:0x24545C])})
 for i,a in enumerate(CONSTANTS):put(m,a,struct.unpack_from('>I',rom(),0x24545C+4*i)[0])
 return m
def divide(a,b,rm):
 x,y=floating(a),floating(b);assert math.isfinite(x)and math.isfinite(y)and y!=0;exact=Fraction(x)/Fraction(y);z=bits(float(exact));v=Fraction(floating(z))
 if v!=exact:
  if rm==1:z=fp.next_down(z)if exact>0 and v>exact else fp.next_up(z)if exact<0 and v<exact else z
  elif rm==2 and v<exact:z=fp.next_up(z)
  elif rm==3 and v>exact:z=fp.next_down(z)
 return z,0x1004 if Fraction(floating(z))!=exact else 0
def effect(m,c,t,n,home):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation:
  if t==FRNG:
   for i,a in enumerate(CONSTANTS):put(m,a,bits((.5,.75,.25,.125,.375)[i]))
  if t==COPY and n==1:
   for i in range(9):m[PALETTE+i]=(i*37+c.seed+0x15)&255
  if t==RNG and n==2:
   for i in range(9):m[PALETTE+i]^=0x5A
  if t in(FRNG,FACTORY):
   p=input_pointer(c)
   for i in range(64):m[p+i]=(m[p+i]+n+1)&255
 if c.private and t==FRNG and n==1:
  put(m,home,0x11223344);put(m,home+4,ALT);put(m,home+8,0xABCD00FE);put(m,home+12,0xFEDCBA98)
def reference(initial,c,home=None,arguments=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;cmd,src,priority,context=(c.command,input_pointer(c),c.priority,c.context)if arguments is None else arguments;frame=home-168;packet=frame+0x48;calls=[];obs=[];ops=[];counts={};csr=c.rm
 for i,v in enumerate((src,priority,context),1):put(m,home+4*i,v)
 put(m,packet,cmd)
 def calc(a,b,fn):
  nonlocal csr
  ops.append((fn,a,b,csr));v,flags=divide(a,b,csr&3)if fn==3 else arithmetic(a,b,fn,csr&3);csr=(csr&~0x3F000)|flags;return v
 def call(t,args):
  args=tuple(map(u32,args));calls.append((t,args));counts[t]=counts.get(t,0)+1;n=counts[t];obs.append((t,args,tuple(m[args[1]+i]for i in range(args[2]))if t==COPY else()))
  if t==COPY:
   for i in range(args[2]):m[args[0]+i]=m[args[1]+i]
  effect(m,c,t,n,home)
  return c.floats[n-1]if t==FRNG else c.integers[n-1]if t==RNG else result(c)if t==FACTORY and c.success else 0
 sample=call(FRNG,());put(m,packet+4,calc(calc(sample,sample,0),read(m,CONSTANTS[0]),2));sample=call(FRNG,());rate=calc(calc(sample,read(m,CONSTANTS[1]),2),read(m,CONSTANTS[2]),0);inverse=calc(bits(1.),rate,3);put(m,packet+8,rate);put(m,packet+12,inverse);sample=call(FRNG,());speed=calc(calc(sample,read(m,CONSTANTS[3]),2),read(m,CONSTANTS[4]),0);put(m,packet+16,speed)
 if call(RNG,())&1:ops.append((7,speed,0,csr));put(m,packet+16,speed^0x80000000)
 put(m,packet+20,0);put(m,packet+24,0);call(COPY,(packet+28,read(m,home+4),64));palette=bytes(m[PALETTE+i]for i in range(9));index=(call(RNG,())%3)&255
 for i in range(3):m[packet+92+i]=palette[3*index+i]
 lifetime=call(RNG,())%101+100;created=call(FACTORY,(lifetime,0xFFFFFFFF,50,0xFFFFFFFF,1,0,96,m[home+11],read(m,home+12)))
 if created:call(COPY,(created+0x28,packet,96))
 return public(m,c),calls,obs,ops,csr
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.home=STACK+c.phase;self.counts={};self.observations=[];self.fp_operations=[];code=dict(connected or{})
  if c.copy:code.update(zip(range(COPY,COPY+44,4),struct.unpack_from('>11I',rom(),0x22EC0)))
  args=(c.command,input_pointer(c),u32(c.priority),u32(c.context))if arguments is None else arguments;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args,s=symbols(),connected=code);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3,7):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;a,b=self.f[fs],self.f[rt];self.fp_operations.append((fn,a,b if fn!=7 else 0,self.fcsr))
   if fn==7:self.f[fd]=a^0x80000000
   else:self.f[fd],flags=divide(a,b,self.fcsr&3)if fn==3 else arithmetic(a,b,fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3F000)|flags
  elif w>>26==0 and w&63 in(0x19,0x1B):
   a,b=u32(self.r[w>>21&31]),u32(self.r[w>>16&31])
   if w&63==0x19:product=a*b;self.lo,self.hi=product&0xFFFFFFFF,product>>32
   else:assert b;self.lo,self.hi=a//b,a%b
  else:super().execute(w)
 def record_call(self,t):
  counts={FRNG:0,RNG:0,COPY:3,FACTORY:9};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append((t,args,tuple(self.memory[args[1]+i]for i in range(args[2]))if t==COPY else()))
  if t==COPY and self.c.copy:assert not self.c.mutation and not self.c.private;effect(self.memory,self.c,t,self.counts[t],self.home)
 def hook(self,t):
  c=self.c;args=self.calls[-1][1];n=self.counts[t]
  if t==COPY:
   for i in range(args[2]):self.memory[args[0]+i]=self.memory[args[1]+i]
  effect(self.memory,c,t,n,self.home);value=c.floats[n-1]if t==FRNG else c.integers[n-1]if t==RNG else result(c)if t==FACTORY and c.success else args[0]if t==COPY else 0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value
def observable(m):return public(m.memory,m.c),m.calls,m.observations,m.fp_operations,m.fcsr
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)],actual_calls=m.calls,want_calls=want[1],actual_FP=m.fp_operations,want_FP=want[3]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(floats=tuple(map(bits,f)),integers=integers,success=s,mutation=mode,private=private,alias=alias,rm=rm,phase=8*(rm&1),seed=rm+mode)for f,integers,s,mode,private,alias,rm in itertools.product(((0.,.25,.5),(-0.,.75,1.),(.125,.375,.625),(-1.,-.5,-.25)),((0,0,0,7),(1,1,100,0xFFFFFFFF),(0x80000000,2,101,7),(0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,7)),(0,1),(0,1),(0,1),(0,1,2),range(4))]
 rows.extend(Case(copy=1,success=s,integers=(parity,colour,lifetime,7),rm=rm)for s,parity,colour,lifetime,rm in itertools.product((0,1),(0,1),(0,1,2),(0,100,101),range(4)));return rows
def pin():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes()
 for entry,at,n in((PALETTE,0x245450,12),*( (a,0x24545C+4*i,4)for i,a in enumerate(CONSTANTS)),(FACTORY,0x1765E0,196),(COPY,0x22EC0,44)):
  start=elf_slot_offset(elf,entry,n);assert elf[start:start+n]==rom()[at:at+n],hex(entry)
 counts={}
 for fn in('func_150ADA20','func_150ADA68'):
  text=(o/'baseline/conker/asm/nonmatchings/game_DAE50'/(fn+'.s')).read_text();rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));at=int(rows[0][0],16);entry=int(rows[0][1],16);start=elf_slot_offset(elf,entry,len(blob));assert blob==rom()[at:at+len(blob)]==elf[start:start+len(blob)];counts[fn]=len(rows)
 return counts
def main():
 pins=pin();files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_150D278C'),symbols())for f in files];assert all(w==streams[0]for w in streams);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+408)
 prefixes=0
 for c in(Case(success=0),Case(),Case(mutation=1,private=1,alias=1),Case(copy=1)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 missing=sorted(set(range(ENTRY,ENTRY+408,4))-seen);assert missing==[ENTRY+0xFC],missing
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_words=[hex(x)for x in missing],unreachable_word_is_constant_divisor_break7=True,fault_prefix_quintuples=prefixes,all_raw_and_literal_full_private_completion_and_fault_states_equal=True,independent_reference_public_memory_calls_payload96_ordered_FP_and_FCSR_equal=True,unwritten_payload5F_copied_from_original_guest_stack_byte=True,palette9_snapshotted_before_mutating_rng=True,unsigned_remainder_and_s16_lifetime100_through200=True,all_four_rounding_modes=True,finite_FP_and_nonzero_divisor_model_not_hardware=True,alias_output_over_original_input_and_caller_stack_input=True,guest_private_home_probes_not_portable_C=True,actual11word_memcpy_connected_on_nonmutating_provider_paths=True,handwritten_RNG_and_float_wrapper_pins=pins,existing49word_factory11word_copy_and_palette12_floats5_ROM_ELF_pinned=True,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
