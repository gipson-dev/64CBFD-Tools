"""Actor oscillation: explicit f32 rounding, ordered callbacks and original trig code."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.experiments import game_actor_phase_motion_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD
ACTOR,TRIG,INNER=0x220000,0x15048A40,0x150489B0
SYMS=dict(func_15048A40=TRIG,D_800A0D48=0x800A0D48,D_800A0D4C=0x800A0D4C,D_800A0D50=0x800A0D50,D_800A0D54=0x800A0D54,D_800BE9E4=0x800BE9E4)
OFFSETS=(0x7C,0x80,0x84)
CONSTANTS=(0x41233333,0x448D4000,0x3F8CCCCD,0x3F8CCCCD)
PATTERNS=(0,1,7,8,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x55555555)
@dataclass(frozen=True)
class Case:
 phases:tuple=(0,0x80000000,0xFFFFFFFF)
 ticks:int=1
 mode:int=0
 pattern:int=0
 phase:int=0

def fixture(c=Case(),s=SYMS,table=False):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 m.update({ACTOR+i:(i*13+0x59)&255 for i in range(-16,176)})
 for off,v in zip(OFFSETS,c.phases):put(m,ACTOR+off,v)
 for name,v in zip(('D_800A0D48','D_800A0D4C','D_800A0D50','D_800A0D54'),CONSTANTS):put(m,s[name],v)
 put(m,s['D_800BE9E4'],c.ticks)
 if table:
  base,data=sections(o/'before-conker_build_conker.us.elf')['.game_data']
  m.update({va:data[va-base]for va in range(0x8009A020,0x8009A724)})
 return m

def provider(angle,pattern):
 if pattern==0:return bits((angle-128)/128.0)
 if pattern==1:return bits((((angle*17)&255)-128)/256.0)
 values=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0x3EAAAAAB,0x3F7FFFFF,1)
 return values[(angle+pattern)&7]

def trig(m,angle):
 a=(angle-64)&255
 if a>=193:return read(m,0x8009A620-a*4)
 if a>=129:return read(m,0x8009A020+a*4)^0x80000000
 if a>=65:return read(m,0x8009A420-a*4)^0x80000000
 return read(m,0x8009A220+a*4)

def mutate(m,c,s,n):
 if n==1 and c.mode&1:
  for i,off in enumerate(OFFSETS):put(m,ACTOR+off,0xFFFFF803+i*0x108)
 if c.mode&2:
  for name,v in zip(('D_800A0D48','D_800A0D4C','D_800A0D50','D_800A0D54'),(0x40200000,0xC1200000,0x3F400000,0xBFC00000)):put(m,s[name],v)
 if n==3 and c.mode&4:
  for i,off in enumerate(OFFSETS):put(m,ACTOR+off,0x7FFFFFF0+i*0x1000)
 if c.mode&8:put(m,s['D_800BE9E4'],(0xFFFFFFF0+n*7)&0xFFFFFFFF)
 if n==2 and c.mode&16:put(m,ACTOR+0x12,0xA55A,2)
 if n==3 and c.mode&16:put(m,ACTOR,0xC0F00000)
 if n==2 and c.mode&32:put(m,ACTOR+0x84,0x12345678)

def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);calls=[]
 def call(n,off):
  angle=(signed(read(m,ACTOR+off))>>3)&255;calls.append((s['func_15048A40'],(angle,)))
  if connected:calls.append((INNER,((angle-64)&255,)));return trig(m,angle)
  result=provider(angle,c.pattern);mutate(m,c,s,n);return result
 value=call(1,0x7C);product=bits(floating(value)*floating(read(m,s['D_800A0D48'])))
 total=bits(floating(product)+floating(read(m,s['D_800A0D4C'])));value=math.trunc(floating(total));assert -32768<=value<=32767
 put(m,ACTOR+0x12,value&65535,2)
 value=call(2,0x80);put(m,ACTOR,bits(floating(value)*floating(read(m,s['D_800A0D50']))))
 value=call(3,0x84);product=bits(floating(value)*floating(read(m,s['D_800A0D54'])))
 phases=[read(m,ACTOR+off)for off in OFFSETS];put(m,ACTOR+8,product)
 for off,phase,factor in zip(OFFSETS,phases,(12,16,24)):put(m,ACTOR+off,(phase+read(m,s['D_800BE9E4'])*factor)&0xFFFFFFFF)
 return m,calls

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+128}

class WindowStop(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.stop_pc:raise WindowStop
  if pc==self.owner.poison_pc:self.owner.r[2]=self.owner.poison_value
  return super().__getitem__(pc)

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  self.c,self.s,self.trace=c,s,[];self.provider_count=0
  self.stop_pc,self.poison_pc,self.poison_value=None,None,0
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,),connected=connected)
  self.root_fault=fault
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(7,13):
   rd,fd=w>>11&31,w>>6&31
   if w&63==7:self.f[fd]=self.f[rd]^0x80000000
   else:
    v=floating(self.f[rd]);assert math.isfinite(v)and -2147483648<=v<2147483648
    self.f[fd]=math.trunc(v)&0xFFFFFFFF
  else:super().execute(w)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t in(self.s['func_15048A40'],INNER,source.ENTRY),hex(t)
  args=self.arguments(1);self.calls.append((t,args));self.events.append(('CALL',t,args))
  self.observations.append((t,tuple(read(self.memory,ACTOR+off)for off in(0,8,0x7C,0x80,0x84)),read(self.memory,ACTOR+0x12,2)))
 def hook(self,t):
  assert t==self.s['func_15048A40'];self.provider_count+=1;angle=self.calls[-1][1][0]
  result=provider(angle,self.c.pattern);mutate(self.memory,self.c,self.s,self.provider_count)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=result;self.hi,self.lo=0xA5000010,0xA5000011

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def images(label,entry=source.ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_150DE6D8.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_10B7D0.c.o'))]
 assert all(w==result[0]for w in result);return result

def compare(words,c,s=SYMS,entry=source.ENTRY,initial=None,connected=None):
 initial=fixture(c,s)if initial is None else initial;want,calls=reference(initial,c,s,bool(connected));models=[Oracle(w,initial,c,entry,s,connected).run()for w in words]
 for m in models:
  assert public(m.memory)==public(want),(c,'public memory',[(hex(a),v,want.get(a))for a,v in public(m.memory).items()if want.get(a)!=v][:8])
  assert m.calls==calls,(c,'calls',m.calls,calls)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
 return models[0]

def guest_suite():
 count=aliases=cuts=delays=0;seen=set()
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else {**dict(zip(('D_800A0D48','D_800A0D4C','D_800A0D50','D_800A0D54','D_800BE9E4'),(0x81007FFC+j*0x10000,0x82008000+j*0x10000,0x8300FFFC+j*0x10000,0x84008004+j*0x10000,0x85007FFC+j*0x10000))), 'func_15048A40':entry+0x10000}
  words=images('phase-rebase-'+str(j),entry,s)
  for v,ticks,mode,pattern,phase in itertools.product(PATTERNS[:6],(0,1,0xFFFFFFFF,0x80000000),(0,1,2,4,8,16,31,63),(0,1,2,3),(0,8)):
   c=Case((v,v^0x80000000,v^0xFFFFFFFF),ticks,mode,pattern,phase);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+232);count+=1
  if j==0:
   for angle in range(256):compare(words,Case((angle*8,((angle+85)&255)*8,((angle+170)&255)*8),0xFFFFFFFF,pattern=angle%4));count+=1
   variants=[dict(s,D_800BE9E4=ACTOR+off)for off in OFFSETS]+[dict(s,D_800A0D54=ACTOR),dict(s,D_800A0D4C=ACTOR+4),dict(s,D_800A0D48=ACTOR+0x7C)]
   for index,a in enumerate(variants):
    aw=images('phase-alias-'+str(index),entry,a)
    for phase in(0,8):compare(aw,Case((0x3F800000,8,16),1,phase=phase),a);aliases+=1
   for c in(Case(),Case(mode=63),Case(phase=8),Case(mode=2,pattern=2)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective phase access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,232,4)),sorted(set(range(0,232,4))-seen)
 return dict(cases=count,executions=4*count,root_words_visited=58,independent_rebases=3,guest_alias_cases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,full_state_and_access_trace_equal=True,finite_f32_to_s16_only=True,FCSR_or_invalid_conversion_claim=False)

def connected_suite():
 from tools.match_progress import load_elf_functions
 fs,_,addresses=load_elf_functions(str(r/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');rom=(o/'before-conker_conker.us.bin').read_bytes();code={}
 for name,va,n,at in(('func_15048A40',TRIG,12,0x75EF0),('func_150489B0',INNER,36,0x75E60)):
  words=list(struct.unpack_from('>%dI'%n,rom,at));assert fs[name]==words and addresses[name]==va;code.update({va+4*i:w for i,w in enumerate(words)})
 words=images('phase-connected');seen=set();count=0
 for angle,ticks,phase in itertools.product(range(256),(0,1,0xFFFFFFFF),(0,8)):
  c=Case((angle*8,((angle+85)&255)*8,((angle+170)&255)*8),ticks,phase=phase);m=compare(words,c,initial=fixture(c,table=True),connected=code);seen.update(m.visits);count+=1
 return dict(cases=count,executions=4*count,retained_helper_words=48,wrapper_words_visited=sum(TRIG+4*i in seen for i in range(12)),quadrant_words_visited=sum(INNER+4*i in seen for i in range(36)),all256_table_angles=True,original_table_bytes=True,gameplay_or_hardware_claim=False)

def run_window(model,stop,registers,poison_pc=None,poison=0):
 model.stop_pc,model.poison_pc,model.poison_value=stop,poison_pc,poison
 model.code=WindowCode(dict(model.code),model)
 for reg,value in registers.items():model.r[reg]=model.before[reg]=value&0xFFFFFFFF
 try:model.run()
 except WindowStop:pass
 else:raise AssertionError('Window did not reach the declared boundary')
 assert stop in model.visits
 return model

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();target=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target]
 pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 assert sites==[]and pointers==[0x22D990],(sites,pointers)
 base,data=sections(o/'before-conker_build_conker.us.elf')['.game_data'];table=0x80088C90;producer=0x1509EBBC;delta=source.ENTRY-source.ROM
 registration=list(struct.unpack_from('>9I',rom,producer-delta));registrations=0
 for index,phase in itertools.product((0,47,48,49,63),(0,8)):
  c=Case(phase=phase);initial=fixture(c);initial.update({table+i:data[table-base+i]for i in range(64*12)});put(initial,0x260008,index)
  m=run_window(Oracle(registration,initial,c,producer),producer+36,{16:0x260000,2:ACTOR});expected=dict(initial);callback=read(initial,table+index*12);put(expected,ACTOR+0x38,callback)
  assert public(m.memory)==public(expected)and m.r[2]==ACTOR
  if index==48:assert callback==source.ENTRY
  registrations+=1
 roots=images('phase-callers');cases=0;seen=set();window_words={}
 for lane in(0,1):
  start,stop,after=(0x15113ED4,0x15113F08,0x15113EF0)if lane==0 else(0x15113F94,0x1511400C,0x15113FC8)
  window=list(struct.unpack_from('>%dI'%((stop-start)//4),rom,start-delta));window_words[hex(start)]=len(window)
  for gate,iteration,mode,pattern,phase,seed in itertools.product((0,1),(0,)if lane==0 else(0,1),(0,63),(0,2),(0,8),(0,0xFFFFFFFF)):
   c=Case((seed,seed^0x80000000,seed^0xFFFFFFFF),0xFFFFFFFF,mode,pattern,phase);initial=fixture(c);initial[ACTOR+0x6E]=gate;put(initial,ACTOR+0x38,source.ENTRY);put(initial,0x80087380,0x87654321);put(initial,0x800D23C0,0x270000);put(initial,0x270002,iteration+1,2)
   prepared=dict(initial)
   if lane and iteration and not gate:
    for at,v in((0x5A,111),(0x5C,222),(0x5E,333)):put(prepared,ACTOR+at,v,2)
    put(prepared,ACTOR+0x80,0x11223344)
   want,calls=reference(prepared,c)if not gate else(prepared,[])
   if not gate:calls=[(source.ENTRY,(ACTOR,)),*calls]
   models=[]
   for root,poison in itertools.product(roots,(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
    code={source.ENTRY+4*i:w for i,w in enumerate(root)};m=Oracle(window,initial,c,start,connected=code)
    registers={4:iteration+1,16:ACTOR,17:iteration,18:1 if not lane else 0,19:111,20:222,21:333,22:0x11223344,23:0,30:0}
    m=run_window(m,stop,registers,after,poison);assert public(m.memory)==public(want)and m.calls==calls,(lane,c,gate,iteration,'caller state')
    assert m.r[2]==0x87654321 and m.r[16]==ACTOR and m.r[29]==STACK+phase
    models.append(m);seen.update(m.visits)
   for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
   cases+=1
 return dict(cases=cases,executions=cases*16,original_window_words=window_words,registration_window_words=9,registration_cases=registrations,table_row=48,table_row_bytes=12,record_callback_offset=56,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,return_poison_values=4,ignored_return_proven=True,branch_gate_and_second_iteration_paths=True,full_large_parent_claim=False)

def native_harness(body):
 return source.HEADERS+r'''
typedef char actor_size_is_136[sizeof(ActorPhaseMotion)==136?1:-1];
typedef char phase_x_is_124[__builtin_offsetof(ActorPhaseMotion,phaseX)==124?1:-1];
typedef char pitch_is_18[__builtin_offsetof(ActorPhaseMotion,pitch)==18?1:-1];
typedef char pointer_is_four[sizeof(void *)==4?1:-1];
f32 D_800A0D48,D_800A0D4C,D_800A0D50,D_800A0D54;
s32 D_800BE9E4;
static struct {u32 first;ActorPhaseMotion actor;u32 last;} actual;
static ActorPhaseMotion expected;
static f32 ec[4];static u32 et,logs[3],expectedLogs[3];
static int calls,expectedCalls,mode,pattern;
static f32 value(u32 bits) {union{u32 u;f32 f;}v;v.u=bits;return v.f;}
static u32 word(f32 number) {union{u32 u;f32 f;}v;v.f=number;return v.u;}
static f32 synth(u32 angle) {
 static const u32 values[8]={0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0x3EAAAAAB,0x3F7FFFFF,1};
 if(pattern==0)return (f32)((s32)angle-128)/128.0f;
 if(pattern==1)return (f32)((s32)((angle*17)&255)-128)/256.0f;
 return value(values[(angle+(u32)pattern)&7]);
}
static void effect(ActorPhaseMotion *a,int n,int isExpected) {
 f32 *constants[4]={&D_800A0D48,&D_800A0D4C,&D_800A0D50,&D_800A0D54};
 if(n==1&&(mode&1)) {a->phaseX=0xFFFFF803;a->phaseY=0xFFFFF90B;a->phaseZ=0xFFFFFA13;}
 if(mode&2) {
  static const u32 values[4]={0x40200000,0xC1200000,0x3F400000,0xBFC00000};int i;
  for(i=0;i<4;i++) {if(isExpected)ec[i]=value(values[i]);else *constants[i]=value(values[i]);}
 }
 if(n==3&&(mode&4)) {a->phaseX=0x7FFFFFF0;a->phaseY=0x80000FF0;a->phaseZ=0x80001FF0;}
 if(mode&8) {u32 v=0xFFFFFFF0u+(u32)n*7;if(isExpected)et=v;else D_800BE9E4=(s32)v;}
 if(n==2&&(mode&16))a->pitch=(s16)0xA55A;
 if(n==3&&(mode&16))a->x=-7.5f;
 if(n==2&&(mode&32))a->phaseZ=0x12345678;
}
f32 func_15048A40(u8 angle) {
 f32 result=synth(angle);if(calls>=3)__builtin_trap();logs[calls++]=angle;effect(&actual.actor,calls,0);return result;
}
''' + body+r'''
static f32 multiply(f32 a,f32 b) {volatile f32 result=a*b;return result;}
static f32 add(f32 a,f32 b) {volatile f32 result=a+b;return result;}
static f32 expectedCall(u32 phase) {
 u32 angle=(u32)((s32)phase>>3)&255;f32 result=synth(angle);
 expectedLogs[expectedCalls++]=angle;effect(&expected,expectedCalls,1);return result;
}
static void reference(void) {
 f32 v;u32 x,y,z;
 v=expectedCall(expected.phaseX);expected.pitch=(s16)add(multiply(v,ec[0]),ec[1]);
 v=expectedCall(expected.phaseY);expected.x=multiply(v,ec[2]);
 v=expectedCall(expected.phaseZ);v=multiply(v,ec[3]);
 x=expected.phaseX;y=expected.phaseY;z=expected.phaseZ;expected.z=v;
 expected.phaseX=x+et*12;expected.phaseY=y+et*16;expected.phaseZ=z+et*24;
}
static int one(u32 low,int p) {
 static const u32 high[4]={0,0x80000000,0x7FFF0000,0xFFFF0000};
 static const u32 ticks[5]={0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF};
 static const u32 constants[4]={0x41233333,0x448D4000,0x3F8CCCCD,0x3F8CCCCD};
 f32 *c[4]={&D_800A0D48,&D_800A0D4C,&D_800A0D50,&D_800A0D54};int i;
 actual.first=actual.last=0xBAADF00D;
 for(i=0;i<(int)sizeof(expected);i++)((u8 *)&actual.actor)[i]=((u8 *)&expected)[i]=(u8)(i*13+0x59);
 actual.actor.phaseX=expected.phaseX=high[p]|low;
 actual.actor.phaseY=expected.phaseY=~(high[p]|low);
 actual.actor.phaseZ=expected.phaseZ=0x80000000u|low*0x10001u;
 for(i=0;i<4;i++)*c[i]=ec[i]=value(constants[i]);
 et=ticks[(low+(u32)p)%5];D_800BE9E4=(s32)et;
 calls=expectedCalls=0;mode=(int)((low*7+(u32)p*13)&63);pattern=(int)((low+(u32)p)&3);
 func_150DE6D8(&actual.actor);reference();
 if(calls!=3||expectedCalls!=3||actual.first!=0xBAADF00D||actual.last!=0xBAADF00D)return 1;
 for(i=0;i<3;i++)if(logs[i]!=expectedLogs[i])return 1;
 for(i=0;i<(int)sizeof(expected);i++)if(((u8 *)&actual.actor)[i]!=((u8 *)&expected)[i])return 1;
 for(i=0;i<4;i++)if(word(*c[i])!=word(ec[i]))return 1;
 if((u32)D_800BE9E4!=et)return 1;
 return 0;
}
static int run(void) {u32 low;int p;for(low=0;low<65536;low++)for(p=0;p<4;p++)if(one(low,p))return 1;return 0;}
''' + START

def native_controls():
 s=source.SELECTED
 result={
  'wrong_angle_shift':s.replace('>> 3','>> 4'),
  'wrong_third_phase':s.replace('(s32)actor->phaseZ >> 3','(s32)actor->phaseX >> 3'),
  'wrong_pitch_scale':s.replace('* D_800A0D48','* D_800A0D50'),
  'missing_pitch_bias':s.replace(' + D_800A0D4C',''),
  'round_instead_of_truncate':s.replace(' + D_800A0D4C;',' + D_800A0D4C + 0.5f;'),
  'wrong_x_field':s.replace('actor->x =','actor->y ='),
  'wrong_z_scale':s.replace('* D_800A0D54','* D_800A0D50'),
  'wrong_x_step':s.replace('* 12;','* 16;'),
  'wrong_y_step':s.replace('* 16;','* 24;'),
  'wrong_z_step':s.replace('* 24;','* 12;'),
  'missing_z_step':s.replace('actor->phaseZ += (u32)D_800BE9E4 * 24;','(void)actor->phaseZ;'),
  'missing_second_callback':s.replace('func_15048A40((u8)((s32)actor->phaseY >> 3))','0.0f'),
 }
 marker='void func_150DE6D8(ActorPhaseMotion *actor) {'
 captured=s.replace(marker,marker+'\n    u32 px=actor->phaseX,py=actor->phaseY,pz=actor->phaseZ;')
 for name,var in(('phaseX','px'),('phaseY','py'),('phaseZ','pz')):captured=captured.replace('(s32)actor->'+name+' >> 3','(s32)'+var+' >> 3')
 result['phases_captured_before_callbacks']=captured
 result['ticks_captured_before_callbacks']=s.replace(marker,marker+'\n    u32 ticks=(u32)D_800BE9E4;').replace('+= (u32)D_800BE9E4','+= ticks')
 captured=s.replace(marker,marker+'\n    f32 c0=D_800A0D48,c1=D_800A0D4C,c2=D_800A0D50,c3=D_800A0D54;')
 for name,var in(('D_800A0D48','c0'),('D_800A0D4C','c1'),('D_800A0D50','c2'),('D_800A0D54','c3')):captured=captured.replace('* '+name,'* '+var).replace('+ '+name,'+ '+var)
 result['constants_captured_before_callbacks']=captured
 assert len(result)==15 and all(v!=s for v in result.values());return result

def native_suite():
 for label,body in [('positive',source.SELECTED),*native_controls().items()]:
  unit=o/('native-phase-'+label+'.c');unit.write_text(native_harness(body))
  for opt in('O0','O2','O3')if label=='positive'else('O2',):
   exe=o/('native-phase-'+label+'-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(label,opt,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==(0 if label=='positive'else 1),(label,opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=262144,all65536_low_halfwords=True,all64_callback_modes=True,high_word_extremes=4,effective_controls=15,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,finite_f32_to_s16_only=True,unsigned_phase_wrap=True,portable_alias_or_FCSR_claim=False)
