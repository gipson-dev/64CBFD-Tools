"""Ordered finite FP, live callback fields, captured centers and exact wrap effects."""
from pathlib import Path
from dataclasses import dataclass,replace
from fractions import Fraction
from functools import lru_cache
import itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_random_targets_1518f1a0_guest import convert_integer,fp
from tools.tests.game_pointer_quad_vertices_150db714_guest import trunc
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_display_sprite_update_151797b0_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x151797B0;RECORD=0x300000;FOLLOW=0x301000;CAMERA=0x320000;OTHER=0x322000;TABLE=0x330000;ALT_TABLE=0x332000;MARK=0x340000;CAMERA_PTR=0x800DBFF0;ORIGIN=0x800DD438;WIND=0x800DD433;COUNT=0x800DD436;TABLE_PTR=0x800DD440;TICKS=0x800BE9E4;COEFF=0x800A7204;RNG=0x150ADA20;WAVE_A=0x15048A40;WAVE_B=0x150489B0;RELEASE=0x1516972C;QUARTER=0x8009A220;u32=lambda x:x&0xFFFFFFFF;signed=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000;half=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 coords:tuple=(0,0,0)
 camera:tuple=(fp.bits(0.),fp.bits(0.))
 origins:tuple=(0,0,0)
 flags:int=0
 angle:int=0
 speed:int=10
 ticks:int=1
 wind:int=20
 coefficient:int=0x3F638E4C
 draw:int=0xFFFFFFFF
 waves:tuple=(fp.bits(.25),fp.bits(.5))
 slot:int=2
 count:int=3
 mutation:int=0
 alias:int=0
 connected:int=0
 rm:int=0
 fp_flags:int=4
 provider_flags:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(D_800DBFF0=CAMERA_PTR,D_800DD438=ORIGIN,D_800DD433=WIND,D_800DD436=COUNT,D_800DD440=TABLE_PTR,D_800BE9E4=TICKS,D_800A7204=COEFF,func_150ADA20=RNG,func_15048A40=WAVE_A,func_150489B0=WAVE_B,func_1516972C=RELEASE)
def address(c):return ORIGIN-0x9C if c.alias==1 else ORIGIN+2-0x9C if c.alias==2 else COEFF-0x9C if c.alias==3 else RECORD
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
@lru_cache(None)
def table_bytes():
 blob=(r/'conker/conker.us.bin').read_bytes()[0x23ECE0:0x23EDE4];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,QUARTER,260);assert len(blob)==260 and old[at:at+260]==blob;return blob
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((address(c)-16,216),(FOLLOW-16,216),(CAMERA,0x304),(OTHER,0x304),(TABLE-16,1312),(ALT_TABLE-16,1312),(MARK,32),(WIND-16,64),(CAMERA_PTR-8,24),(TICKS-8,24),(COEFF-8,24)):
  assert not STACK+c.phase-2048<=base<STACK+c.phase+1024;m.update({u32(base+i):(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(address(c),FOLLOW):
  put(m,p+0x90,c.flags);put(m,p+0x94,c.slot,2);put(m,p+0x98,0,2);put(m,p+0x9A,0,2)
  for off,v in zip((0x9C,0x9E,0xA0),c.coords):put(m,p+off,v,2)
  put(m,p+0xAE,c.angle,2);m[p+0xB1]=c.speed;m[p+0xB2]=1;m[p+0xB4]=177
 for p in(CAMERA,OTHER):put(m,p+0x2F8,c.camera[0]);put(m,p+0x300,c.camera[1])
 for i,v in enumerate(table_bytes()):m[QUARTER+i]=v
 put(m,CAMERA_PTR,CAMERA);put(m,WIND,c.wind,1);put(m,ORIGIN,c.origins[0],2);put(m,ORIGIN+2,c.origins[1],2);put(m,ORIGIN+4,c.origins[2],2);put(m,COUNT,c.count,2);put(m,TABLE_PTR,TABLE);put(m,TICKS,c.ticks);put(m,COEFF,c.coefficient);return m
@lru_cache(None)
def operation(kind,a,b,rm):
 if kind==32:return convert_integer(a,rm)
 if kind==13:return trunc(a)
 if kind==7:assert math.isfinite(fp.floating(a));return a^0x80000000,0
 if kind in(0,1,2):return arithmetic(a,b,kind,rm)
 x=fp.floating(a);assert math.isfinite(x)
 if kind==3:
  y=fp.floating(b);assert math.isfinite(y)and y!=0;exact=Fraction(x)/Fraction(y);seed=fp.bits(float(exact));assert math.isfinite(fp.floating(seed));candidates={seed,fp.next_down(seed),fp.next_up(seed)}
  finite=[v for v in candidates if math.isfinite(fp.floating(v))];values={v:Fraction(fp.floating(v))for v in finite}
  if rm==0:value=min(finite,key=lambda v:(abs(values[v]-exact),v&1))
  elif rm==2:value=min((v for v in finite if values[v]>=exact),key=lambda v:values[v])
  elif rm==3:value=max((v for v in finite if values[v]<=exact),key=lambda v:values[v])
  else:value=max((v for v in finite if values[v]<=exact),key=lambda v:values[v])if exact>=0 else min((v for v in finite if values[v]>=exact),key=lambda v:values[v])
  if exact==0:return(a^b)&0x80000000,0
  return value,0x1004 if values[value]!=exact else 0
 assert kind==4 and x>=0
 if x==0:return a,0
 exact=Fraction(x);lo=fp.bits(math.sqrt(x))
 while Fraction(fp.floating(lo))**2>exact:lo=fp.next_down(lo)
 hi=fp.next_up(lo)
 while Fraction(fp.floating(hi))**2<exact:lo=hi;hi=fp.next_up(hi)
 if Fraction(fp.floating(lo))**2==exact:return lo,0
 if Fraction(fp.floating(hi))**2==exact:return hi,0
 if rm==2:value=hi
 elif rm in(1,3):value=lo
 else:
  midpoint=(Fraction(fp.floating(lo))+Fraction(fp.floating(hi)))/2;value=lo if exact<midpoint*midpoint else hi if exact>midpoint*midpoint else lo if lo&1==0 else hi
 return value,0x1004
def effect(m,c,t,p):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:
  if t==RNG:
   m[WIND]=53;put(m,COEFF,fp.bits(1.125));put(m,p+0xAE,0xF123,2);m[p+0xB1]=7;put(m,TICKS,2);put(m,CAMERA_PTR,OTHER)
  elif t==WAVE_A:put(m,p+0x9C,-250,2);put(m,p+0xAE,0xC000,2);m[p+0xB1]=99;put(m,TICKS,9)
  elif t==WAVE_B:
   put(m,p+0x9E,375,2)
   for i,v in enumerate((10,-20,30)):put(m,ORIGIN+2*i,v,2)
 if c.mutation&2:
  if t==WAVE_B:put(m,p+0x90,read(m,p+0x90)^3);put(m,p+0x94,3,2);put(m,COUNT,1,2);put(m,TABLE_PTR,ALT_TABLE)
  if t==RELEASE:put(m,p+0x98,-1,2)
 if c.mutation&8 and t in(RNG,WAVE_A,WAVE_B):put(m,STACK+c.phase,FOLLOW if t!=WAVE_A else address(c))
def lookup(m,angle,calc):
 angle&=255
 if angle<=64:return read(m,QUARTER+4*angle)
 if angle<=128:return calc(7,read(m,QUARTER+4*(128-angle)))
 if angle<=192:return calc(7,read(m,QUARTER+4*(angle-128)))
 return read(m,QUARTER+4*(256-angle))
def reference(initial,c,initial_csr=None):
 m=dict(initial);p=address(c);home=STACK+c.phase;put(m,home,p);calls=[];ops=[];csr=c.rm|c.fp_flags if initial_csr is None else initial_csr
 def calc(kind,a,b=0):
  nonlocal csr
  ops.append((kind,u32(a),u32(b),csr));v,flags=operation(kind,u32(a),u32(b),csr&3);csr=(csr&~0x3F000)|flags;return v
 def call(t,args):
  nonlocal csr
  calls.append((t,tuple(map(u32,args))))
  if t in(WAVE_A,WAVE_B)and c.connected:
   angle=args[0]&255
   if t==WAVE_A:angle=(angle-64)&255;calls.append((WAVE_B,(angle,)))
   return lookup(m,angle,calc)
  effect(m,c,t,read(m,home)if t!=RELEASE else args[0]);csr=(csr&~0x3F000)|c.provider_flags;return u32(c.draw)if t==RNG else c.waves[t==WAVE_B]if t in(WAVE_A,WAVE_B)else 0xDEADBEEF
 viewer=read(m,CAMERA_PTR);z=calc(32,half(read(m,p+0xA0,2)));x=calc(32,half(read(m,p+0x9C,2)));dz=calc(1,z,read(m,viewer+0x300));dx=calc(1,x,read(m,viewer+0x2F8));sqz=calc(2,dz,dz);sqx=calc(2,dx,dx);distance=calc(4,calc(0,sqz,sqx));scaled=calc(2,fp.bits(80.),distance);opacity=signed(calc(13,calc(1,fp.bits(80.),calc(3,scaled,fp.bits(1000.)))));angle=read(m,p+0xAE,2);m[p+0xB4]=max(0,opacity)&255
 draw=call(RNG,());angle=u32(angle+(((read(m,WIND,1)<<4)*((draw&255)+128))>>9));converted=calc(32,angle);scaled=calc(2,converted,read(m,COEFF));angle=min(signed(calc(13,scaled)),12800);p=read(m,home);put(m,p+0xAE,angle,2);speed=calc(32,u32(read(m,p+0xB1,1)*read(m,TICKS)))
 index=(read(m,p+0xAE,2)>>8)&255;wave=call(WAVE_A,(index,));p=read(m,home);movement=calc(2,speed,wave);old=calc(32,half(read(m,p+0x9C,2)));index=(read(m,p+0xAE,2)>>8)&255;x=calc(13,calc(0,old,movement));put(m,p+0x9C,x,2);wave=call(WAVE_B,(index,));p=read(m,home);movement=calc(2,speed,wave);old=calc(32,half(read(m,p+0x9E,2)));y=calc(13,calc(1,old,movement));put(m,p+0x9E,y,2)
 centers=[half(read(m,ORIGIN+2*i,2))for i in range(3)];wrapped=False
 for off,center in zip((0x9C,0x9E,0xA0),centers):
  value=half(read(m,p+off,2))
  if value<center-500:put(m,p+off,value+1000,2);wrapped=True
  elif center+500<value:put(m,p+off,value-1000,2);wrapped=True
 flags=read(m,p+0x90)
 if flags&2 and wrapped:put(m,COUNT,half(read(m,COUNT,2))-1,2);put(m,u32(read(m,TABLE_PTR)+4*half(read(m,p+0x94,2))),0);call(RELEASE,(p,))
 elif flags&1:
  if wrapped:put(m,p+0x90,flags^1)
  else:m[p+0xB4]=0
 return m,calls,ops,csr
@lru_cache(None)
def helper_words():
 rom=(r/'conker/conker.us.bin').read_bytes();old=(o/'baseline/conker/build/conker.us.elf').read_bytes();result={}
 for entry,offset,n in((WAVE_A,0x75EF0,12),(WAVE_B,0x75E60,36)):
  blob=rom[offset:offset+4*n];at=elf_slot_offset(old,entry,len(blob));assert old[at:at+len(blob)]==blob;result[entry]=list(struct.unpack('>'+str(n)+'I',blob))
 return result
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.fp_operations=[];code={}if connected is None else dict(connected)
  if c.connected:
   for target,body in helper_words().items():code.update(zip(range(target,target+4*len(body),4),body))
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(address(c),)if arguments is None else arguments,s=symbols(),connected=code);self.initial=dict(self.memory);self.fcsr=c.rm|c.fp_flags;self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and((fmt==20 and fn==32)or(fmt==16 and fn in(0,1,2,3,4,7,13))):
   kind=32 if fmt==20 else fn;a=self.f[fs];b=self.f[rt]if kind in(0,1,2,3)else 0;self.fp_operations.append((kind,a,b,self.fcsr));value,flags=operation(kind,a,b,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  counts={RNG:0,WAVE_A:1,WAVE_B:1,RELEASE:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];p=read(self.memory,STACK+c.phase)if t!=RELEASE else a[0];effect(self.memory,c,t,p);value=c.draw if t==RNG else 0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value);self.fcsr=(self.fcsr&~0x3F000)|c.provider_flags
  if t in(WAVE_A,WAVE_B):self.f[0]=c.waves[t==WAVE_B]
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.current_pc,m.delay_of,m.condition,m.trace)
def raw_relation(a,b):
 assert a.memory==b.memory and a.f==b.f and a.trace==b.trace and a.calls==b.calls and a.fp_operations==b.fp_operations and(a.fcsr,a.hi,a.lo,a.current_pc,a.delay_of,a.condition)==(b.fcsr,b.hi,b.lo,b.current_pc,b.delay_of,b.condition)
 assert all(a.r[i]==b.r[i]for i in range(32)if i not in(2,4,9,10,14,15))
def check(words,c):
 m=Machine(words,c).run();memory,calls,ops,csr=reference(m.initial,c);got=(public(m.memory,c),m.calls,m.fp_operations,m.fcsr);want=(public(memory,c),calls,ops,csr);assert got==want,dict(case=str(c),parts=[a==b for a,b in zip(got,want)],calls=m.calls,wanted=calls,FP=m.fp_operations,wanted_FP=ops,memory=[(hex(a),got[0].get(a),want[0].get(a))for a in got[0].keys()|want[0].keys()if got[0].get(a)!=want[0].get(a)][:8]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 positions=((0,0,0),(-501,0,0),(501,0,0),(0,-501,0),(0,501,0),(0,0,-501),(0,0,501),(2000,2000,2000),(-32768,32767,-32768))
 rows=[Case(coords=coords,flags=flags,angle=angle,mutation=mutation,rm=rm,phase=8*(rm&1),speed=0 if i&1 else 10)for i,coords in enumerate(positions)for flags,angle,mutation,rm in itertools.product(range(4),(0,65535),(0,1),range(4))]
 rows +=[Case(alias=alias,flags=flags,coords=(1200,-1200,999),origins=(-700,600,-500),mutation=mutation,rm=rm,speed=0)for alias,flags,mutation,rm in itertools.product((1,2,3),range(4),(0,1,2,8),range(4))]
 rows +=[Case(angle=phase,coefficient=coefficient,draw=draw,ticks=ticks,rm=rm,flags=3,mutation=3,waves=(fp.bits(1e-8),fp.bits(-1e-8)))for phase,coefficient,draw,ticks,rm in itertools.product((0,32768),(0x3F638E4C,fp.bits(-.5)),(0,0x80000000,0xFFFFFFFF),(0,0x80000001),range(4))]
 rows +=[Case(connected=1,wind=0,draw=0,angle=(65536-256*index)&65535,coefficient=fp.bits(-1.),flags=flags,coords=(-501,0,501),rm=rm)for index,flags,rm in itertools.product((0,1,63,64,65,127,128,129,191,192,193,255),(0,1,2,3),(0,3))]
 return[replace(c,seed=i)for i,c in enumerate(rows)]
def main():
 files=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o');streams=[bound_blob(*payload(o/f,'func_151797B0'),symbols())for f in files];literal=[streams[i]for i in(0,2,3,4)];assert all(w==literal[0]for w in literal);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for i,m in enumerate(models)if i!=1);raw_relation(models[0],models[1]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+776)
 cuts=0
 for c in(Case(),Case(coords=(-2000,2000,-2000),flags=2),Case(coords=(501,501,501),flags=1,mutation=9,phase=8),Case(alias=2,coords=(-1200,1200,0),flags=3)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for i,m in enumerate(models)if i!=1);raw_relation(models[0],models[1]);cuts+=1
 assert len(seen)==194,(len(seen),[hex(x-ENTRY)for x in sorted(set(range(ENTRY,ENTRY+776,4))-seen)])
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,preserved_words=194,executed_words=len(seen),normalized_fault_prefix_quadruples=cuts,raw_fault_memory_FP_and_restricted_GPR_relations=cuts,normalized_full_private_and_fault_states_equal=True,raw_memory_access_and_FP_order_equal_with_explicit_volatile_argument_roles=True,raw_full_private_GPR_identity_not_claimed=True,independent_reference_public_memory_calls_and_ordered_FP_FCSR_equal=True,all_four_rounding_modes_finite_DIV_SQRT_and_integer_conversions=True,original_table_wave_helpers_and_pinned_quarter_wave_data_connected=True,captured_three_origin_aliases_and_late_field_home_mutations=True,guest_only_parameter_home_and_alias_experiments=True,bounded_invalid_conversion_software_results_not_hardware_acceptance=True,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
