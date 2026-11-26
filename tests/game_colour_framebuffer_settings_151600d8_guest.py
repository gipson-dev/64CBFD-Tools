"""Ordered settings model, actual default helper, opaque ABI and full frames."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x151600d8;PROVIDER=0x151422dc;META=0x800a6540;COEFFS=(0x800a6674,0x800a6678,0x800a667c,0x800a6680);OBJECT=0x30000
LABELS=(0,0x3c,0x78,0xb4,0xf0);FILES=(8,0x44,0x80,0xbc,0xfc);LINES=(452,457,462,467,473);DEFAULTS=(0,0,500,500,65536);MINIMUMS=(-2000,-2000,0,0,0);MAXIMUMS=(2000,2000,2000,2000,65536)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
 actual:bool=True
 values:tuple=DEFAULTS
 mode:int=0
 alias:int=0
 pattern:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
def symbols(c):
 s={'func_151422DC':PROVIDER}
 for offset in(*LABELS,*FILES):s[f'D_{0x800a6540+offset:08X}']=META+offset
 for i,name in enumerate(('D_800A6674','D_800A6678','D_800A667C','D_800A6680')):s[name]=COEFFS[i]if not c.alias else c.object+24+(0 if c.alias==1 else 4*i if c.alias==2 else 4*((i+1)%4))
 return s
@lru_cache(maxsize=1)
def original_data():return(r/'conker/conker.us.bin').read_bytes()[0x24b000:0x24b150]
@lru_cache(maxsize=1)
def helper_words():return struct.unpack('>7I',(o/'default-provider-original.bin').read_bytes())
def coefficients(c):
 vals=(0x3a83126f,bits(.5),bits(-.75),0,0x80000000,1,0x00800000,bits(1.25));return tuple(vals[(c.pattern+i)%len(vals)]if c.pattern else vals[0]for i in range(4))
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-192,192)};m.update({c.object-16+i:(i*29+0x5a)&255 for i in range(80)});m.update({META+i:v for i,v in enumerate(original_data())});s=symbols(c)
 for i,v in enumerate(coefficients(c)):put(m,s[('D_800A6674','D_800A6678','D_800A667C','D_800A6680')[i]],v)
 return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-192<=a<STACK+c.phase+192}
def int_float(word,rm):
 n=((word&0xffffffff)^0x80000000)-0x80000000;z=bits(float(n));v=floating(z)
 if rm==1:z=fp.next_down(z)if n>0 and v>n else fp.next_up(z)if n<0 and v<n else z
 elif rm==2 and v<n:z=fp.next_up(z)
 elif rm==3 and v>n:z=fp.next_down(z)
 return z,0x1004 if floating(z)!=n else 0
def call_args(index):return tuple(map(u32,(index,META+LABELS[index],MINIMUMS[index],MAXIMUMS[index],DEFAULTS[index],META+FILES[index],LINES[index])))
def effect(m,c,index):
 s=symbols(c)
 if c.mode&1:
  for i,name in enumerate(('D_800A6674','D_800A6678','D_800A667C','D_800A6680')):put(m,s[name],bits((index+1)*(i+1)*-.125))
 if c.mode&2:
  for i in range(4):put(m,c.object+24+4*i,bits((index+1)*(i+1)*.25))
 if c.mode&4:put(m,c.object+40,0xa6000000+index)
def provider_fcsr(c,index):return c.rm|((0x10 if index&1 else 0x20)if c.mode&8 else 0)
def reference(initial,c,s0,s1,ra,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase;sp=home-48;put(m,sp+44,ra);put(m,sp+40,s1);put(m,sp+36,s0);put(m,home,c.object);calls=[];obs=[];ops=[];fcsr=c.rm if initial_fcsr is None else initial_fcsr;s=symbols(c)
 for index in range(5):
  args=call_args(index)
  for offset,value in((16,args[4]),(20,args[5]),(24,args[6])):put(m,sp+offset,value)
  calls.append((PROVIDER,args));obs.append((public(m,c),fcsr,bytes(m[sp+i]for i in range(52))))
  if c.actual:
   for i in range(4):put(m,sp+4*i,args[i])
   answer=args[4]
  else:
   effect(m,c,index)
   for i in range(7):put(m,sp+4*i,0xb5000000+i)
   fcsr=provider_fcsr(c,index);answer=u32(c.values[index])
  if index<4:
   ops.append((32,answer,None,fcsr));value,flags=int_float(answer,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;coefficient=read(m,s[('D_800A6674','D_800A6678','D_800A667C','D_800A6680')[index]]);ops.append((2,value,coefficient,fcsr));value,flags=arithmetic(value,coefficient,2,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;put(m,c.object+24+4*index,value)
  else:put(m,c.object+40,answer)
 return m,calls,obs,ops,fcsr,1
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;code={}if connected is None else dict(connected)
  if c.actual:code.update(zip(range(PROVIDER,PROVIDER+28,4),helper_words()))
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=code);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.observations=[];self.fp_operations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:
   self.fp_operations.append((32,self.f[fs],None,self.fcsr));self.f[fd],flags=int_float(self.f[fs],self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn in(0,2):
   self.fp_operations.append((fn,self.f[fs],self.f[rt],self.fcsr));self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t==PROVIDER,hex(t);args=tuple(self.arguments(7));self.calls.append((t,args));sp=STACK+self.c.phase-48;self.observations.append((public(self.memory,self.c),self.fcsr,bytes(self.memory[sp+i]for i in range(52))))
 def hook(self,t):
  assert t==PROVIDER and not self.c.actual;index=len(self.calls)-1;effect(self.memory,self.c,index)
  for i in range(7):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(self.c.values[index]);self.hi,self.lo=0xa5000010,0xa5000011;self.fcsr=provider_fcsr(self.c,index)
def observable(m):return m.memory,m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.fp_operations,m.trace
def check(words,c):
 m=Machine(words,c).run();wanted=reference(m.initial,c,m.before[16],m.before[17],m.before[31]);actual=observable(m);assert actual==wanted,dict(case=str(c),components=[a==b for a,b in zip(actual,wanted)],memory_differences=[hex(a)for a in m.memory if m.memory[a]!=wanted[0].get(a)][:8]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(actual=True,pattern=p,alias=a,rm=rm,phase=8*(rm&1),object=STACK+32 if stack else OBJECT)for p,a,rm,stack in itertools.product(range(8),range(4),range(4),range(2))]
 values=(0,1,0xffffffff,0x7fffffff,0x80000000,0x01000001,0xfeffffff,65536)
 rows +=[Case(actual=False,values=tuple(values[(pattern+i)%8]for i in range(5)),mode=mode,alias=alias,pattern=pattern,rm=rm,phase=8*(rm&1))for pattern,mode,alias,rm in itertools.product(range(8),range(16),range(4),range(4))]
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];cache={};seen=set();rows=cases()
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_151600D8'),symbols(c))for f in files]
  streams=cache[key];assert all(ws==streams[0]for ws in streams);models=[check(ws,c)for ws in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in(Case(),Case(actual=False,values=(1,0x7fffffff,0x80000000,0x01000001,17),mode=15,alias=2)):
  streams=[bound_blob(*payload(o/f,'func_151600D8'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in streams:
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 controls=[];c=Case(actual=False,values=(17,19,23,29,31),mode=15);words=bound_blob(*payload(o/'original-target.o','func_151600D8'),symbols(c))
 for name,old,new in [('return',0x24020001,0x24020000),('line',0x240f01c4,0x240f01c5),('store',0xe62a0000,0xe62a0004),('index',0x24100002,0x24100003),('multiply',0x46083282,0x46083280)]:
  assert words.count(old)>=1;wrong=[new if w==old else w for w in words];m=Machine(wrong,c).run();assert observable(m)!=reference(m.initial,c,m.before[16],m.before[17],m.before[31]);controls.append(dict(name=name,complete_supported_execution=True,rejected=True))
 assert set(range(ENTRY,ENTRY+412,4))<=seen
 q=dict(cases_per_stream=len(rows),streams=5,executed_target_words=103,actual_default_provider_words=7,actual_helper_connected_cases=sum(c.actual for c in rows),opaque_provider_contract_cases=sum(not c.actual for c in rows),fault_prefix_quintuples=prefixes,all_direct_streams_complete_machine_frame48_borrowed_home_ABI_return_and_provider_observations_equal=True,ordered_signed32_conversion_MUL_operands_and_FCSR=True,all_four_rounding_modes_and_INT32_boundaries=True,all7_outgoing_words_and_distinct_label_file_line_bindings=True,coefficient_output_overlaps_and_stack_owner_guest_only=True,finite_FP_model_not_hardware=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
