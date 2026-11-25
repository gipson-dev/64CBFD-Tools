"""Independent packet schema and bounded original/raw MIPS execution."""
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
from tools.experiments import game_composite_preset_150b5a3c_match as p
ROOT,OUT=p.ROOT,p.OUT;ENTRY=0x150b5a3c;SUBMIT=0x15152b38;OTHER=0x150b5e34;TAIL=0x150b6000;POINT,ALT,MARK=0x30000,0x31000,0x35000;COEFF=(0x8009fca0,0x8009fca4,0x8009fca8)
u32=lambda n:n&0xffffffff
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def home(c):return STACK+c.phase
def packet(c):return home(c)-116
def public(m,c):return {a:v for a,v in m.items()if not home(c)-2048<=a<home(c)+1024}
@lru_cache(maxsize=1)
def coefficient_words():
 elf=(OUT/'baseline/conker/build/conker.us.elf').read_bytes();rom=(ROOT/'conker/conker.us.bin').read_bytes()
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(ROOT/'conker');result=[]
 for a in COEFF:
  p=elf_slot_offset(elf,a,4);blob=elf[p:p+4];assert blob==rom[start+a-base:start+a-base+4];result.append(int.from_bytes(blob,'big'))
 return tuple(result)
@dataclass(frozen=True)
class Case:
 mode:int=0
 extra:int=0x87654321
 seed:int=0
 phase:int=0
 mutation:int=0
 rm:int=0
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 ghost_homes:bool=False
 point:int=POINT
 caller_record:int=0
 caller_actor:int=0
def arguments(c):return c.point,c.mode,u32(c.extra)
def fixture(c):
 m={home(c)+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,1024)}
 for p,n in[(POINT,12),(ALT,12),(MARK,16)]:m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for p in(POINT,ALT):
  for i,v in enumerate(c.coords):put(m,p+4*i,v)
 for a,v in zip(COEFF,coefficient_words()):put(m,a,v)
 put(m,MARK,0);return m
# Scalar field spans are also the endian map for native packet observations.
FIELDS4=(0,4,8,12,16,20,24,28,32,36,40,52,56,92,96,108)
FIELDS2=(44,46,48,50,60,62,64,100,102,104)
HOLES=(89,90,91,107)
def expected_packet(m,c):
 result={i:m[packet(c)+i]for i in range(116)}
 words={0:5,4:5,8:read(m,c.point),12:read(m,c.point+4),16:read(m,c.point+8),20:bits(20.),24:read(m,COEFF[0]),28:read(m,COEFF[1]),32:read(m,COEFF[2]),36:bits(39.),40:bits(35.),52:3,56:2,92:0x200005,96:0x60600,108:bits(1.)}
 halves={44:0,46:255,48:-31,50:80,60:20,62:30,64:1,100:8,102:31,104:1}
 small={66:4,67:2,68:3,69:255,70:255,71:255,72:255,73:0,74:0,75:0,76:0,77:255,78:255,79:255,80:255,81:0,82:0,83:0,84:0,85:255,86:0,87:3,88:36,106:0,112:255,113:0,114:255,115:255}
 assert set(words)==set(FIELDS4)and set(halves)==set(FIELDS2)
 for at,v in words.items():put(result,at,v)
 for at,v in halves.items():put(result,at,v,2)
 result.update(small);assert set(result)-set(HOLES)==set(wordsByte for at in words for wordsByte in range(at,at+4))|set(halfByte for at in halves for halfByte in range(at,at+2))|set(small)
 return bytes(result[i]for i in range(116))
def observation(m,c,t,args,fcsr):
 passed=data(m,args[0],116 if t==SUBMIT else 12)
 return public(m,c),passed,data(m,home(c),12),fcsr
def effect(m,c,t,args):
 put(m,MARK,read(m,MARK)+1)
 if t==SUBMIT:
  if c.mutation&1:
   for i,v in enumerate((bits(-4.5),bits(6.25),bits(-8.))):put(m,c.point+4*i,v)
  if c.mutation&2:
   for a,v in zip(COEFF,(bits(2.),bits(-3.),bits(4.))):put(m,a,v)
   if c.caller_record:m[c.caller_record+0xc]=0x72;m[c.caller_record+1]=0x83;put(m,c.caller_record+0x28,0x38000);put(m,0x8009fc9c,bits(.75))
   if c.caller_actor:put(m,c.caller_actor+0x1d4,0x61000)
  if c.mutation&4:
   for i in range(116):m[args[0]+i]=(i*7+c.seed*11+0x31)&255
  if c.ghost_homes:put(m,home(c),ALT);put(m,home(c)+4,0xabcd0072);put(m,home(c)+8,0xfedcba98)
 elif t==OTHER:
  if c.mutation&8:put(m,args[0]+8,bits(-9.5))
  if c.ghost_homes:put(m,home(c)+4,0xffff0083);put(m,home(c)+8,0x12345678)
 else:assert t==TAIL
 return u32(0x6abc0000+read(m,MARK)*0x100+c.seed)
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];fcsr=c.rm
 for i,v in enumerate(arguments(c)):put(m,home(c)+4*i,v)
 for i,v in enumerate(expected_packet(m,c)):m[packet(c)+i]=v
 for t in(SUBMIT,OTHER,TAIL):
  args=(packet(c)if t==SUBMIT else read(m,home(c)),m[home(c)+7],read(m,home(c)+8));calls.append((t,args));obs.append(observation(m,c,t,args,fcsr));value=effect(m,c,t,args);fcsr=c.rm|(0x100*(len(calls)))
 return m,calls,obs,fcsr,value
class Machine(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,memory=None,args=None,connected=None):
  self.c=c;self.fcsr=c.rm;super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:];self.observations=[];self.provider_count=0
 def record_call(self,t):
  assert t in(SUBMIT,OTHER,TAIL),hex(t);a=tuple(map(u32,self.arguments(3)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(observation(self.memory,self.c,t,a,self.fcsr));self.provider_count+=1
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value;self.fcsr=self.c.rm|0x100*self.provider_count
def symbols():return dict(func_15152B38=SUBMIT,func_150B5E34=OTHER,func_150B6000=TAIL,**dict(zip(('D_8009FCA0','D_8009FCA4','D_8009FCA8'),COEFF)))
def programs():return[bound_blob(*payload(OUT/f,'func_150B5A3C'),symbols())for f in['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o']]
def raw_program():return bound_blob(*payload(OUT/'selected-final/owner-candidate.o','func_150B5A3C'),symbols())
def cases():
 rows=[Case(mode=i,extra=u32(i*0x87654321),seed=i&15,phase=(i&1)*8,mutation=i%16,rm=i%4)for i in range(256)]
 rows +=[Case(mode=255,extra=v,mutation=mutation,phase=phase,rm=rm)for v,mutation,phase,rm in itertools.product((0,0x80000000,0xffffffff),range(16),(0,8),range(4))]
 rows +=[Case(mode=255,mutation=i,ghost_homes=True,phase=8)for i in range(16)]
 rows +=[Case(coords=(v,0x80000000,0x00000001),mode=17,rm=rm)for v,rm in itertools.product((0x7f7fffff,0xff7fffff,0x00800000,0x80800000),range(4))]
 return rows
def check(words,c,entry=None):
 m=Machine(words,c,entry=ENTRY if entry is None else entry).run();expected,calls,obs,fcsr,value=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert m.observations==obs,(c,'boundary observations');assert public(m.memory,c)==public(expected,c)and data(m.memory,packet(c),116)==data(expected,packet(c),116),(c,'memory');assert m.fcsr==fcsr and m.r[2]==value;assert m.r[29]==home(c)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def main():
 streams=[*programs(),raw_program()];visits=set();count=0
 for c in cases():
  pair=[check(words,c)for words in streams];a=pair[0];assert all((a.memory,a.calls,a.observations,a.r,a.f,a.fcsr,a.hi,a.lo)==(b.memory,b.calls,b.observations,b.r,b.f,b.fcsr,b.hi,b.lo)for b in pair[1:]);visits.update(a.visits);count+=1
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 prefixes=0
 for c in[Case(),Case(mutation=15,phase=8),Case(ghost_homes=True,mutation=15)]:
  full=Machine(programs()[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in programs():
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+508,4));q=dict(cases_per_stream=count,streams=5,retail_equal_streams=4,access_fault_quads=prefixes,raw_fault_order_not_claimed=True,all127_words_visited=True,complete116_byte_packet=True,initialized_packet_bytes=112,unspecified_bytes=4,all256_mode_bytes=True,extra32_boundaries=True,public_and_passed_packet_mutations=True,guest_only_home_mutations=True,full_private_frame_and_registers_equal=True,no_FP_arithmetic_in_target=True,source_installed=p.installed(),matching_credit=0)
 (OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
