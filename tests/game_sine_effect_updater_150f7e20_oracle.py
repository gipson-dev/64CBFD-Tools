"""Sine effect public behavior, bounded conversion control and original call edges."""
from dataclasses import dataclass,replace
import itertools,math,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,SIN,WRAP=0x150F7E20,0x15047D60,0x15144B68
SOURCE,ALT,MARK=0x30000,0x34000,0x70000
u32=lambda n:n&0xFFFFFFFF
VALUES=(0,0x80000000,1,0x80000001,0x3F000000,0x3F7FFFFF,0x3F800000,0x40000000,0x4EFFFFFF,0x4F000000,0x4F000001,0x4F7FFFFF,0x4F800000,0xBF000000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
 remaining:int=0x40000000
 angle:int=0x3F000000
 rate:int=0x3E800000
 center:int=0x41200000
 amplitude:int=0x40800000
 sine:int=0x3F000000
 wrapped:int=0x3F400000
 delta:int=0x3E000000
 scale:int=0x40CF684C
 mode:int=0
 home_mode:int=0
 phase:int=0
 seed:int=0
 fcsr:int=0
 alias:int=0

def symbols(i=0,c=Case()):
 scale,dt,sin,wrap=((0x800A1BD8,0x800BE9A4,SIN,WRAP),(0x80027FFC,0x80038004,0x1701FFFC,0x17118000),(0x9000FFF0,0x90018000,0x1E17FFFC,0x1E288000))[i]
 dt={1:SOURCE+0x30,2:SOURCE+0x2C,3:SOURCE+0x12C,4:SOURCE+0x128}.get(c.alias,dt)
 return dict(D_800A1BD8=scale,D_800BE9A4=dt,sinf=sin,func_15144B68=wrap)

def f32(v):
 try:return bits(v)
 except OverflowError:return bits(math.copysign(math.inf,v))
def mul(a,b):return f32(floating(a)*floating(b))
def add(a,b):return f32(floating(a)+floating(b))
def sub(a,b):return f32(floating(a)-floating(b))
def converted(w):
 f=floating(w)
 if not math.isfinite(f):return 255
 n=math.trunc(f)
 return n&255 if 0<=n<2**32 else 255
def public(m):return {a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def fixture(c=Case(),s=None):
 s=symbols(c=c)if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((SOURCE-32,0x190),(ALT-32,0x190),(MARK,16)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(SOURCE,ALT):
  for off,w in((0x128,c.remaining),(0x12C,c.angle),(0x130,c.rate),(0x134,c.center),(0x138,c.amplitude)):put(m,p+off,w)
 put(m,s['D_800A1BD8'],c.scale);put(m,s['D_800BE9A4'],c.delta);put(m,0x800A56A4,0x40C90FDB);return m
def homes(m,sp):
 for i in range(4):put(m,sp+4*i,0xB5000000+i)
def effect(m,c,s,stage,home,slot):
 p=SOURCE if stage==0 else read(m,home)
 if c.mode&(1<<stage):
  if stage==0:
   for off,v in((0x128,5.5),(0x12C,-0.25),(0x130,0.75),(0x134,-3.0),(0x138,2.0)):put(m,p+off,bits(v))
  else:put(m,p+0x128,bits(0.0625));put(m,p+0x12C,bits(9.0))
  put(m,s['D_800BE9A4'],bits(0.25 if stage==0 else 0.5));put(m,MARK+stage*4,0xA1700000+stage)
 if stage==0 and c.home_mode&1:put(m,home,ALT)
 if stage==1 and c.home_mode&2:put(m,home-40+slot,ALT+0x110)
def wrap_value(angle):
 v=floating(angle);tau=floating(0x40C90FDB);assert math.isfinite(v)and abs(v)<tau*16
 while tau<v:v=floating(sub(bits(v),bits(tau)))
 while v<0:v=floating(add(bits(v),bits(tau)))
 return bits(v)
def reference(initial,c=Case(),s=None,home=None,slot=28,ra=0xDEAD0000,connected=False):
 s=symbols(c=c)if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-40
 put(m,sp+20,ra);m[SOURCE+0x5C]=converted(mul(read(m,SOURCE+0x128),read(m,s['D_800A1BD8'])))
 angle=read(m,SOURCE+0x12C);put(m,home,SOURCE);calls=[(s['sinf'],(angle,))]
 effect(m,c,s,0,home,slot);homes(m,sp);p=read(m,home);block=p+0x110
 value=add(mul(c.sine,read(m,block+0x28)),read(m,block+0x24));put(m,p+0x30,value);put(m,p+0x2C,value)
 dt=read(m,s['D_800BE9A4']);rate=read(m,block+0x20);angle=read(m,block+0x1C);put(m,sp+slot,block)
 argument=add(angle,mul(rate,dt));calls.append((s['func_15144B68'],(argument,)))
 if connected:answer=wrap_value(argument)
 else:effect(m,c,s,1,home,slot);homes(m,sp);answer=c.wrapped
 block=read(m,sp+slot);put(m,block+0x1C,answer)
 put(m,block+0x18,sub(read(m,block+0x18),read(m,s['D_800BE9A4'])))
 return m,calls,int(not floating(read(m,block+0x18))<0)

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None,slot=28):
  super().__init__(words,memory,c,entry=entry,s=symbols(c=c)if s is None else s,connected=connected,arguments=(SOURCE,)if arguments is None else arguments)
  self.fcsr=c.fcsr;self.control=[];self.slot=slot;self.before_f=self.f[:];self.boundary=None
 def execute(self,w):
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):
   old=self.fcsr;AreaOracle.execute(self,w);self.control.append((self.current_pc,w,old,self.fcsr))
  elif op==17 and rs==16 and fn in(0,1,2):
   a,b=self.f[w>>11&31],self.f[w>>16&31];self.f[w>>6&31]=(add if fn==0 else sub if fn==1 else mul)(a,b);self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:self.target_home=self.r[29];a=(self.r[4],)
  else:
   assert t in(self.syms['sinf'],self.syms['func_15144B68']),hex(t);a=(self.f[12],)
   if t==self.syms['sinf']:assert self.fcsr==self.case.fcsr
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  stage=0 if t==self.syms['sinf']else 1;effect(self.memory,self.case,self.syms,stage,self.target_home,self.slot);homes(self.memory,self.r[29])
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.sine if stage==0 else self.case.wrapped
  self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.fcsr,m.control,m.boundary)
def original_object(core,q,out):
 text=(out/'frozen/conker/asm/124920.s').read_text();body=re.search(r'^glabel func_150F7E20\n.*?(?=^glabel |\Z)',text,re.M|re.S).group()
 p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+body+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
 q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s):
 a,b,c=(list(core.bound_blob(q[n],q[r],s))for n,r in(('original','original_refs'),('raw','refs'),('normal','normal_refs')))
 assert a==c and [i for i,(x,y)in enumerate(zip(b,c))if x!=y]==[48,55,59]
 return a,b,c
def verify(m,initial,c,s,slot=28,home=None,ra=0xDEAD0000,connected=False):
 wanted,calls,result=reference(initial,c,s,home,slot,ra,connected)
 assert(m.memory,m.calls,m.r[2])==(wanted,calls,result),(c,slot,[(hex(a),m.memory.get(a),v)for a,v in wanted.items()if m.memory.get(a)!=v][:12],m.calls,calls,m.r[2],result)
 assert m.fcsr==c.fcsr and m.f[20:]==m.before_f[20:]
 return wanted,calls,result
def cases():
 rows=[Case(remaining=v,mode=m,phase=p,fcsr=f,scale=scale,seed=i)for i,(v,m,p,f,scale)in enumerate(itertools.product(VALUES,range(4),(0,8),(0,3,0x00800000),(0x40CF684C,0x3F800000)))]
 rows +=[Case(angle=a,rate=r,sine=s,wrapped=w,mode=m)for a,r,s,w,m in itertools.product((0,0x80000000,0xBF800000,0x40C90FDB),(0,0x3E800000,0xBF000000),(0,0x80000000,0x3F000000,0xBF000000),(0,0x80000000,0x3F800000,0x7FC12345),(0,3))]
 rows +=[Case(home_mode=h,mode=m,phase=p)for h,m,p in itertools.product((1,2,3),range(4),(0,8))]
 rows +=[Case(remaining=r,delta=d)for r,d in((bits(0.125),bits(0.125)),(0,0),(0x80000000,0),(bits(1.0),bits(-0.25)))]
 return rows
def guest(core,q):
 original_object(core,q,core.ROOT/core.BUILD);seen=set();rows=[(c,symbols(c=c),ENTRY)for c in cases()]
 rows +=[(Case(mode=m),symbols(i),0x17508000 if i==1 else 0x1F007FFC)for i,m in itertools.product((1,2),range(4))]
 for c,s,entry in rows:
  initial=fixture(c,s);models=[Oracle(w,initial,c,entry=entry,s=s,slot=24 if i==1 else 28).run()for i,w in enumerate(programs(core,q,s))]
  for i,m in enumerate(models):verify(m,initial,c,s,24 if i==1 else 28)
  assert literal(models[0])==literal(models[2]);assert all((public(m.memory),m.calls,m.r[2])==(public(models[0].memory),models[0].calls,models[0].r[2])for m in models)
  seen.update(pc-entry for pc in models[0].visits)
 assert seen==set(range(0,312,4))-{136},sorted(set(range(0,312,4))-seen)
 aliases=0
 for c in(Case(alias=a,mode=m)for a,m in itertools.product(range(1,5),range(4))):
  s=symbols(c=c);initial=fixture(c,s);models=[Oracle(w,initial,c,s=s,slot=24 if i==1 else 28).run()for i,w in enumerate(programs(core,q,s))]
  for i,m in enumerate(models):verify(m,initial,c,s,24 if i==1 else 28)
  assert literal(models[0])==literal(models[2]);aliases+=1
 cuts=0
 for c in(Case(),Case(mode=3,home_mode=3),Case(remaining=0x4F000001),Case(remaining=0x7FC12345),Case(alias=3,mode=3)):
  s=symbols(c=c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c,s=s).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in(ps[0],ps[2]):
    m=Oracle(w,initial,c,s=s);m.cut=cut
    try:m.run();raise AssertionError('Unfired sine effect access cut')
    except AccessBoundary:pass
    models.append(m)
   assert literal(models[0])==literal(models[1]);cuts+=1
 return dict(cases=len(rows),reached_words=len(seen),unreachable_duplicate_offset=136,alias_cases=aliases,fault_prefix_cuts=cuts,
  independent_complete_memory=True,normalized_original_literal_state=True,raw_public_finite_arithmetic=True,
  raw_private_home_or_NaN_payload_fault_identity_not_claimed=True,bounded_conversion_control_restored_before_sinf=True,
  complete_hardware_FPU_FCSR_and_actual_sinf_accuracy_not_claimed=True)

class CallerCode(WindowCode):
 def __getitem__(self,pc):
  if pc in self.ends:self.owner.boundary=pc
  return super().__getitem__(pc)
def connections(core,q):
 rom=(core.ROOT/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>24I',rom,0x172018);helpercode=dict(zip(range(WRAP,WRAP+96,4),helper));covered=set();count=0
 for c in(Case(angle=bits(a),rate=bits(r),mode=m,phase=p)for a,r,m,p in itertools.product((-12.5,-6.2831854820251465,-0.,0.,0.5,6.2831854820251465,12.5),(-2.,0.,3.),(0,1),(0,8))):
  s=symbols();initial=fixture(c,s);models=[]
  for i,w in enumerate(programs(core,q,s)):
   m=Oracle(w,initial,c,s=s,connected=helpercode,slot=24 if i==1 else 28).run();verify(m,initial,c,s,24 if i==1 else 28,connected=True);models.append(m)
  assert literal(models[0])==literal(models[2]);covered.update(models[0].visits);count+=1
 assert set(range(WRAP,WRAP+96,4))<=covered
 body=struct.unpack_from('>15I',rom,0x16A4E8);caller=0x1513D038;end=0x1513D074;caller_count=0
 for c,remove,nextbyte in itertools.product((Case(),Case(mode=3),Case(delta=0x40800000),Case(remaining=0x7FC12345)),(0,1,255),(0,17,255)):
  s=symbols();initial=fixture(c,s);put(initial,0x80089D48,ENTRY);initial[SOURCE+0x71]=nextbyte;models=[]
  for i,w in enumerate(programs(core,q,s)):
   code=dict(zip(range(ENTRY,ENTRY+312,4),w));code[end]=0;m=Oracle(body,initial,c,entry=caller,s=s,connected=code,slot=24 if i==1 else 28)
   m.r[2]=36;m.r[7]=remove;m.code=CallerCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('Missing registered caller boundary')
   except WindowBoundary:pass
   before=dict(initial);home=STACK+c.phase;put(before,home+0x20,SOURCE);put(before,home+0x1B,remove,1)
   wanted,calls,result=reference(before,c,s,home,24 if i==1 else 28,0x1513D060)
   expected_remove=(remove^128)-128 if result else 1
   assert(m.memory,m.calls,m.r[4],m.r[7],m.r[2],m.boundary)==(wanted,[(ENTRY,(SOURCE,)),*calls],SOURCE,u32(expected_remove),nextbyte,end),(c,remove,nextbyte)
   models.append(m)
  assert literal(models[0])==literal(models[2]);caller_count+=1
 return dict(original_wrap_helper_words=24,original_wrap_cases=count,all_helper_words_reached=True,
  period_bits='40C90FDB',period_endpoint_retained=True,finite_bounded_wrap_domain=True,
  registration_table='D_80089CB8',registration_index=36,registration_ROM='22E808',
  original_caller_window_words=15,caller_window_cases=caller_count,zero_result_sets_remove=True,
  saved_record_and_signed_remove_restored=True,next_callback_byte_reloaded=True,complete_parent_and_sinf_leaf_not_claimed=True)

_native_rows=None
def native_rows():
 global _native_rows
 if _native_rows is not None:return _native_rows
 rows=[]
 for c in(c for c in cases()if not(c.phase or c.home_mode or c.fcsr)):
  initial=fixture(c);product=floating(mul(read(initial,SOURCE+0x128),c.scale))
  if not math.isfinite(product)or not 0<=product<2**32:continue
  wanted,calls,result=reference(initial,c)
  # Native arithmetic checks finite timer outcomes; NaN return cases remain guest-only.
  if not math.isfinite(floating(read(wanted,SOURCE+0x12C))):continue
  values=(c.remaining,c.angle,c.rate,c.center,c.amplitude,c.sine,c.wrapped,c.delta,c.scale,
          calls[0][1][0],calls[1][1][0],read(wanted,SOURCE+0x2C),read(wanted,SOURCE+0x128),read(wanted,SOURCE+0x12C),read(wanted,symbols()['D_800BE9A4']))
  rows.append('{'+','.join('0x%Xu'%v for v in values)+',%d,%d,%d}'%(c.mode,wanted[SOURCE+0x5C],result))
 _native_rows=('\n,'.join(rows),len(rows));return _native_rows
def native_text(core,selected=None):
 rows,n=native_rows();s=core.SELECTED if selected is None else selected
 return '#include <ultra64.h>\n'+s+r'''
typedef struct {u8 before[0x2C];f32 value2C,value30;u8 pad34[0x28];u8 intensity;u8 pad5D[0xB3];SineEffectState124920 state;u8 tail[0x20];} Effect;
typedef char Layout[(sizeof(void*)==4&&__builtin_offsetof(Effect,intensity)==0x5C&&__builtin_offsetof(Effect,state)==0x110&&__builtin_offsetof(SineEffectState124920,remaining)==0x18)?1:-1];
typedef struct {u32 remaining,angle,rate,center,amplitude,sine,wrapped,delta,scale,arg0,arg1,value,finalRemaining,finalAngle,finalDelta;unsigned mode,intensity,result;} Case;
static const Case cases[]={
__ROWS__
};
f32 D_800A1BD8,D_800BE9A4;
static Effect object,expected;static const Case*c;static unsigned calls,error;
static void bytes(void*d,const void*s,unsigned n){u8*p=d;const u8*q=s;unsigned i;for(i=0;i<n;i++)p[i]=q[i];}
static f32 number(u32 w){f32 f;bytes(&f,&w,4);return f;}
static u32 word(f32 f){u32 w;bytes(&w,&f,4);return w;}
static int equal(const void*a,const void*b,unsigned n){const u8*p=a,*q=b;unsigned i;for(i=0;i<n;i++)if(p[i]!=q[i])return 0;return 1;}
float sinf(float angle){
 if(calls++!=0||word(angle)!=c->arg0||object.intensity!=c->intensity)error=1;
 if(c->mode&1){object.state.remaining=5.5f;object.state.phase=-0.25f;object.state.rate=0.75f;object.state.center=-3.0f;object.state.amplitude=2.0f;D_800BE9A4=0.25f;}
 return number(c->sine);
}
f32 func_15144B68(f32 angle){
 if(calls++!=1||word(angle)!=c->arg1||word(object.value2C)!=c->value||word(object.value30)!=c->value)error=1;
 if(c->mode&2){object.state.remaining=0.0625f;object.state.phase=9.0f;D_800BE9A4=0.5f;}
 return number(c->wrapped);
}
static int run(void){unsigned i,j;int result;
 for(i=0;i<__COUNT__;i++){
  c=cases+i;calls=error=0;for(j=0;j<sizeof(object);j++)((u8*)&object)[j]=(u8)(j*29+0x5A);
  object.state.remaining=number(c->remaining);object.state.phase=number(c->angle);object.state.rate=number(c->rate);object.state.center=number(c->center);object.state.amplitude=number(c->amplitude);
  D_800A1BD8=number(c->scale);D_800BE9A4=number(c->delta);bytes(&expected,&object,sizeof(object));
  if(c->mode&1){expected.state.rate=0.75f;expected.state.center=-3.0f;expected.state.amplitude=2.0f;}
  expected.intensity=(u8)c->intensity;expected.value2C=expected.value30=number(c->value);expected.state.remaining=number(c->finalRemaining);expected.state.phase=number(c->finalAngle);
  result=func_150F7E20((u8*)&object);
  if(calls!=2||error||result!=(int)c->result||word(D_800BE9A4)!=c->finalDelta)return 1;
  if(!equal(&object,&expected,sizeof(object)))return 2;
 }
 return 0;
}
'''.replace('__ROWS__',rows).replace('__COUNT__',str(n))+START
def controls(core):
 s=core.SELECTED;changes={
  'wrong_scale':('* D_800A1BD8','* 1.0f'),
  'wrong_byte':('effect[0x5C]','effect[0x5D]'),
  'wrong_sine_angle':('sinf(*(f32 *)(effect + 0x12C))','sinf(*(f32 *)(effect + 0x128))'),
  'wrong_amplitude':('sine * state->amplitude','sine * state->rate'),
  'wrong_center':('+ state->center','- state->center'),
  'missing_second_value':('    *(f32 *)(effect + 0x2C) = value;',''),
  'wrong_phase_gain':('state->rate * D_800BE9A4','state->rate + D_800BE9A4'),
  'wrong_phase_sign':('state->phase + state->rate','state->phase - state->rate'),
  'cached_delta':('    f32 sine;','    f32 cached = D_800BE9A4;\n    f32 sine;'),
  'wrong_timer_sign':('state->remaining -= D_800BE9A4','state->remaining += D_800BE9A4'),
  'wrong_return':('if (state->remaining < 0.0f)','if (state->remaining >= 0.0f)'),
  'zero_expires':('if (state->remaining < 0.0f)','if (state->remaining <= 0.0f)'),
  'stub':('    f32 sine;','    return 0;\n    f32 sine;')}
 assert all(a in s for a,b in changes.values());rows={n:s.replace(a,b)for n,(a,b)in changes.items()}
 rows['cached_delta']=rows['cached_delta'].replace('state->remaining -= D_800BE9A4','state->remaining -= cached')
 return rows
def native(core,out):
 records=[]
 for name,body,opt,valid in [('valid-'+o[1:],None,o,True)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',False)for n,b in controls(core).items()]:
  p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
  build=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
  assert build.returncode==0 and not build.stdout and not build.stderr,(name,build.stdout,build.stderr)
  run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
  assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
  records.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
 return dict(cases_per_profile=native_rows()[1],profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),records=records,
  typed_effect_and_state=True,complete_object_canaries=True,independent_numeric_and_call_expectations=True,
  native_float_to_unsigned_domain='finite product in [0,2**32)',native_final_phase_and_timer_finite=True,
  invalid_alpha_conversion_and_synthetic_stack_aliases_guest_only=True,hardware_FCSR_and_actual_sinf_not_claimed=True)
