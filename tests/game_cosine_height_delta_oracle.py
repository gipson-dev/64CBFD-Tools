"""Bounded f32 and guest ABI qualification; no hardware FCSR claim."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests import game_actor_phase_motion_oracle as phase
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_cosine_height_delta_match as source
r=Path.cwd();o=r/source.BUILD
ENTRY,ACTOR,STACK,COS,TICKS=0x151162D4,phase.ACTOR,phase.STACK,0x15047C00,0x800BE9E4
SYMS={'cosf':COS,'D_800BE9E4':TICKS}
@dataclass(frozen=True)
class Case:
 height:int=127
 offset:int=0x3F400000
 packed:int=0xFFFF8001
 counter:int=0xFFFFFFFF
 ticks:int=1
 mode:int=0
 pattern:int=0
 phase:int=0

def half(v):return ((v&65535)^32768)-32768
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 m.update({ACTOR+i:(i*13+0x59)&255 for i in range(-16,176)})
 for a,v,n in [(ACTOR+18,c.height,2),(ACTOR+24,c.offset,4),(ACTOR+60,c.packed,4),(ACTOR+124,c.counter,4),(s['D_800BE9E4'],c.ticks,4)]:put(m,a,v,n)
 return m
def provider(arg,c):
 values=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xBE800000,0x3EAAAAAB,1)
 return values[((arg>>17)+c.pattern)&7]
def mutate(m,c,s):
 if c.mode&1:put(m,ACTOR+18,0xFFEF,2)
 if c.mode&2:put(m,ACTOR+24,0xC1200000)
 if c.mode&4:put(m,ACTOR+60,0x12345678)
 if c.mode&8:put(m,ACTOR+124,0xFFFFFFFE)
 if c.mode&16:put(m,s['D_800BE9E4'],0xFFFFFFF1)
def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+128}
def reference(initial,c,s=SYMS):
 m=dict(initial);height=half(read(m,ACTOR+18,2));prev=half(math.trunc(floating(bits(float(height)+floating(read(m,ACTOR+24))))))
 packed=read(m,ACTOR+60);amp=bits(float(half(packed)));speed=packed>>16
 arg=bits(floating(bits(float(signed(read(m,ACTOR+124)))))*floating(0x3BB40000));ret=provider(arg,c)
 mutate(m,c,s);value=bits(floating(ret)*floating(amp));counter=read(m,ACTOR+124);height=half(read(m,ACTOR+18,2))
 put(m,ACTOR+24,value);ticks=read(m,s['D_800BE9E4']);put(m,ACTOR+124,(counter+speed*ticks)&0xFFFFFFFF)
 total=bits(float(height)+floating(value));delta=math.trunc(floating(bits(floating(total)-float(prev))))
 put(m,ACTOR+92,delta&65535,2);return m,[(s['cosf'],(arg,))]
class Oracle(phase.Oracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,fault=None):
  super().__init__(w,m,c,entry,s,connected,fault)
 def record_call(self,t):
  assert t in(self.s['cosf'],ENTRY),hex(t)
  args=(self.f[12],)if t==self.s['cosf']else(self.r[4],)
  self.calls.append((t,args));self.events.append(('CALL',t,args))
  self.observations.append((t,read(self.memory,ACTOR+60),read(self.memory,ACTOR+124),read(self.memory,ACTOR+18,2)))
 def hook(self,t):
  assert t==self.s['cosf'];result=provider(self.f[12],self.c);mutate(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=result
  self.lo,self.hi=0xA5000010,0xA5000011
def linked(obj,label,entry,s):
 raw,rs=payload(obj,'func_151162D4');assert len(raw)==236
 from tools.pad_generated_object import parse_object
 text,fs,relocations=parse_object(obj);asm,unknown=emit_function(text,fs['func_151162D4'],relocations,'func_151162D4',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151162D4','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_151162D4.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o'))]
 assert all(w==result[0]for w in result);return result
def compare(words,c,s=SYMS,entry=ENTRY):
 initial=fixture(c,s);want,calls=reference(initial,c,s);models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:assert public(m.memory)==public(want)and m.calls==calls,(c,'public or call mismatch')
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
 return models[0]
def guest_suite():
 count=aliases=cuts=delays=0;seen=set()
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else {'cosf':entry+0x10000,'D_800BE9E4':0x81007FFC+j*4}
  words=images('height-rebase-'+str(j),entry,s)
  for height,packed,counter,mode,pattern,sp in itertools.product((-32768,0,32767),(0,0xFFFF,0x80008000,0xFFFFFFFF),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,31),(0,3),(0,8)):
   c=Case(height,0x3F400000,packed,counter,0xFFFFFFFF,mode,pattern,sp);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if j==0:
   for index,at in enumerate((ACTOR+16,ACTOR+24,ACTOR+60,ACTOR+92,ACTOR+124)):
    a=dict(s,D_800BE9E4=at);aw=images('height-alias-'+str(index),entry,a)
    for sp in(0,8):compare(aw,Case(height=12,offset=0,counter=0x80000000,mode=31,phase=sp),a,entry);aliases+=1
   for c in(Case(),Case(mode=31),Case(phase=8),Case(mode=31,phase=8)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except phase.faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective height access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
 return dict(cases=count,executions=count*4,independent_rebases=3,reachable_words=59,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,all59_words_visited=True,full_state_and_access_trace_equal=True,finite_f32_to_s32_with_low_halfword_store=True,hardware_FCSR_claim=False)

import sys
g=sys.modules[__name__]
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_trig_match import COS_GLOBALS
from tools.tests.test_game_cosine_match import reference as cosine_reference
from tools.tests.game_actor_phase_motion_oracle import WindowCode

PARENT,LOOKUP,FOLLOW=0x1511A738,0x15022B08,0x1511A494
class Caller(g.Oracle):
 def record_call(self,t):
  if t in(self.s['cosf'],g.ENTRY):return super().record_call(t)
  assert t in(LOOKUP,FOLLOW);a=self.arguments(2 if t==LOOKUP else 3);self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==self.s['cosf']:return super().hook(t)
  assert t in(LOOKUP,FOLLOW)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.lookup_result if t==LOOKUP else 0x87654321
def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 target=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target]
 pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==g.ENTRY]
 assert sites==[0x147C48]and pointers==[0x22D8DC],(sites,pointers)
 window=list(struct.unpack_from('>34I',rom,0x147BE8));assert before[elf_slot_offset(before,PARENT,136):elf_slot_offset(before,PARENT,136)+136]==rom[0x147BE8:0x147C70]
 roots=g.images('height-parent');seen=set();cases=0
 for gate,lookup,mode,sp,pattern,counter in itertools.product((0,1,255),(0,1),(0,31),(0,8),(0,7),(0,0x80000000)):
  c=g.Case(mode=mode,phase=sp,pattern=pattern,counter=counter);initial=g.fixture(c);initial[0x800C35EA]=gate;g.put(initial,0x800DBEF4,g.ACTOR-0xA0*7)
  prepared=dict(initial)
  if gate==1 and lookup:g.put(prepared,g.ACTOR+124,0);g.put(prepared,g.ACTOR+24,0)
  want,calls=g.reference(prepared,c);calls=[*(((LOOKUP,(7,0)),)if gate==1 else ()), (g.ENTRY,(g.ACTOR,)),*calls,(FOLLOW,(g.ACTOR,g.ACTOR+128,g.ACTOR+132))]
  models=[]
  for root,poison in itertools.product(roots,(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
   code={g.ENTRY+4*i:w for i,w in enumerate(root)};m=Caller(window,initial,c,PARENT,connected=code);m.lookup_result=lookup
   m.stop_pc=None;m.poison_pc=0x1511A7A0;m.poison_value=poison;m.code=WindowCode(dict(m.code),m);m.run()
   assert g.public(m.memory)==g.public(want)and m.calls==calls,(gate,lookup,mode,'caller result')
   assert m.r[2]==0x87654321 and m.r[29]==g.STACK+sp
   seen.update(m.visits);models.append(m)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  cases+=1
 assert set(range(PARENT,PARENT+136,4))<=seen
 return dict(cases=cases,executions=cases*16,original_parent_words=34,all_parent_words_visited=True,ignored_return_poison_values=4,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,lookup_and_follow_are_bounded_models=True,hardware_or_full_gameplay_claim=False)

class Connected(g.Oracle):
 def hook(self,t):raise AssertionError(('Original cosine must execute',hex(t)))
def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 cosine=list(struct.unpack_from('>88I',rom,0x750B0));assert before[elf_slot_offset(before,g.COS,352):elf_slot_offset(before,g.COS,352)+352]==rom[0x750B0:0x75210]
 code={g.COS+4*i:w for i,w in enumerate(cosine)};roots=g.images('height-connected');count=0;seen=set()
 for counter,packed,sp in itertools.product((0,1,91,182,65535,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,0x10001,0xFFFF8001,0x80007FFF),(0,8)):
  c=g.Case(counter=counter,packed=packed,phase=sp);initial=g.fixture(c)
  base,data=g.sections(o/'before-conker_build_conker.us.elf')['.game_data']
  for a in COS_GLOBALS:g.put(initial,a,int.from_bytes(data[a-base:a-base+4],'big'))
  for a,v in COS_GLOBALS.items():assert g.read(initial,a)==v,(hex(a),'Original cosine constant changed')
  angle=g.bits(g.floating(g.bits(float(g.signed(counter))))*g.floating(0x3BB40000));result=cosine_reference(angle)
  original=g.provider;g.provider=lambda a,c:result
  try:want,calls=g.reference(initial,c)
  finally:g.provider=original
  models=[Connected(w,initial,c,connected=code).run()for w in roots]
  for m in models:assert g.public(m.memory)==g.public(want)and m.calls==calls;seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  count+=1
 return dict(cases=count,executions=count*4,original_helper_slot_words=88,helper_body_words=85,helper_words_visited=sum(g.COS+4*i in seen for i in range(85)),original_retail_constants=True,independent_cosine_reference=True,hardware_FCSR_claim=False)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
text=source.HEADERS+source.SELECTED;start=text.index('/* Advance the cosine');headers,body=text[:start],text[start:]
prefix=r'''
typedef char correct_size[sizeof(CosineHeightRecord)==128?1:-1];
typedef char correct_phase[__builtin_offsetof(CosineHeightRecord,phase)==124?1:-1];
typedef char correct_delta[__builtin_offsetof(CosineHeightRecord,delta)==92?1:-1];
typedef char correct_packed[__builtin_offsetof(CosineHeightRecord,packed)==60?1:-1];
typedef char correct_offset[__builtin_offsetof(CosineHeightRecord,offset)==24?1:-1];
typedef char correct_height[__builtin_offsetof(CosineHeightRecord,height)==18?1:-1];
typedef char correct_pointer[sizeof(void *)==4?1:-1];
s32 D_800BE9E4;
static struct {u32 first;CosineHeightRecord record;u32 last;} actual;
static CosineHeightRecord expected;
static u32 et,actualArg,expectedArg;static int calls,mode,pattern;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 synth(u32 arg){static const u32 values[8]={0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xBE800000,0x3EAAAAAB,0x3F7FFFFF};return real(values[((arg>>17)+(u32)pattern)&7]);}
static void effect(CosineHeightRecord *a,int isExpected){
 if(mode&1)a->height=-17;
 if(mode&2)a->offset=-10.0f;
 if(mode&4)a->packed=0x12345678;
 if(mode&8)a->phase=0xFFFFFFFE;
 if(mode&16){if(isExpected)et=0xFFFFFFF1;else D_800BE9E4=(s32)0xFFFFFFF1;}
}
f32 cosf(f32 a){f32 v=synth(word(a));actualArg=word(a);calls++;effect(&actual.record,0);return v;}
static f32 multiply(f32 a,f32 b){volatile f32 v=a*b;return v;}
static f32 add(f32 a,f32 b){volatile f32 v=a+b;return v;}
static f32 subtract(f32 a,f32 b){volatile f32 v=a-b;return v;}
static s32 sign16(u32 x){return (s32)(x&32767)-(s32)(x&32768);}
static void reference(void){
 u32 packed=(u32)expected.packed;u32 speed=packed>>16;
 s32 previous=sign16((u32)(s32)add((f32)expected.height,expected.offset));
 f32 amplitude=(f32)sign16(packed),angle=multiply((f32)(s32)expected.phase,real(0x3BB40000));
 f32 response=synth(word(angle)),value;
 expectedArg=word(angle);effect(&expected,1);value=multiply(response,amplitude);
 expected.offset=value;expected.phase=expected.phase+speed*et;
 expected.delta=(s16)sign16((u32)(s32)subtract(add((f32)expected.height,value),(f32)previous));
}
static int one(u32 low,int p){
 static const u32 phase[8]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xFFFF0001,0x12345678,0xFFFF};
 static const u32 ticks[5]={0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF};
 static const u32 offsets[4]={0x3F400000,0xBF400000,0x3FC00000,0xBFC00000};int i;
 actual.first=actual.last=0xBAADF00D;
 for(i=0;i<128;i++)((u8 *)&actual.record)[i]=((u8 *)&expected)[i]=(u8)(i*13+0x59);
 actual.record.height=expected.height=(s16)(low^(u32)(p*8191));
 actual.record.offset=expected.offset=real(offsets[p]);
 actual.record.packed=expected.packed=(s32)((low<<16)|((low*40503+17)&65535));
 actual.record.phase=expected.phase=phase[(low+(u32)p)&7];
 et=ticks[(low+(u32)p)%5];D_800BE9E4=(s32)et;
 calls=0;mode=(int)((low*7+(u32)p*13)&31);pattern=(int)((low+(u32)p)&7);
 if(low==65536){actual.record.height=expected.height=32767;actual.record.offset=expected.offset=1.5f;actual.record.packed=expected.packed=0x18001;actual.record.phase=expected.phase=0;et=1;D_800BE9E4=1;mode=0;pattern=7;}
 func_151162D4(&actual.record);reference();
 if(calls!=1||actualArg!=expectedArg||actual.first!=0xBAADF00D||actual.last!=0xBAADF00D||(u32)D_800BE9E4!=et)return 1;
 for(i=0;i<128;i++)if(((u8 *)&actual.record)[i]!=((u8 *)&expected)[i])return 1;
 return 0;
}
static int run(void){u32 low;int p;for(low=0;low<65536;low++)for(p=0;p<4;p++)if(one(low,p))return 1;if(one(65536,0))return 1;return 0;}
'''
def harness(b):return headers+prefix[:prefix.index('static int one')]+b+prefix[prefix.index('static int one'):]+START
controls={
 'unsigned_amplitude':body.replace('(s16)(record->packed & 0xFFFF)','(u16)(record->packed & 0xFFFF)'),
 'signed_speed':body.replace('(record->packed >> 16) & 0xFFFF','record->packed >> 16'),
 'wrong_amplitude_half':body.replace('record->packed & 0xFFFF','record->packed >> 16'),
 'unsigned_phase_float':body.replace('(f32)(s32)record->phase','(f32)record->phase'),
 'wrong_phase_scale':body.replace('0.0054931640625f','0.00390625f'),
 'previous_s32':body.replace('s16 previousHeight','s32 previousHeight'),
 'previous_without_offset':body.replace('(f32)record->height + record->offset','(f32)record->height'),
 'previous_without_truncation':body.replace('s16 previousHeight','f32 previousHeight').replace('previousHeight = (s32)','previousHeight = '),
 'no_phase_advance':body.replace('record->phase += (u32)speed * (u32)D_800BE9E4;','record->phase += 0;'),
 'unit_ticks':body.replace('(u32)speed * (u32)D_800BE9E4','(u32)speed'),
 'phase_overwrite':body.replace('record->phase +=','record->phase ='),
 'omit_height':body.replace('((f32)record->height + offset)','(offset)'),
 'reverse_delta':body.replace('((f32)record->height + offset) - (f32)previousHeight','(f32)previousHeight - ((f32)record->height + offset)'),
 'late_amplitude':body.replace(' * amplitude;',' * (s16)(record->packed & 0xFFFF);'),
 'late_speed':body.replace('(u32)speed * (u32)D_800BE9E4','((u32)record->packed >> 16) * (u32)D_800BE9E4')}
def native_suite():
 results=[]
 for name,b,opt,negative in [('positive-'+opt,body,opt,False)for opt in ('-O0','-O2','-O3')]+[(n,b,'-O2',True)for n,b in controls.items()]:
  assert not negative or b!=body,name
  p=o/('native-'+name+'.c');p.write_text(harness(b));exe=p.with_suffix('')
  command=native_command(opt)+['-Wno-unused-but-set-variable','-fsanitize=float-cast-overflow','-o',str(exe),str(p)]
  q=subprocess.run(command,cwd=r,capture_output=True,text=True);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==(1 if negative else 0),(name,q.returncode,q.stderr)
  results.append(dict(name=name,exit=q.returncode,optimization=opt,control=negative))
 q=dict(complete=True,positive_cases_each=262145,profiles=['O0','O2','O3'],effective_controls=len(controls),controls_exit_by_semantic_mismatch=True,UBSan_and_float_cast_overflow_trapping=True,full_record_and_canaries_checked=True,callback_argument_bits_checked=True,all65536_low_halfwords=True,all65536_speed_halfwords=True,defined_finite_float_to_s32_domain=True,portable_alias_or_hardware_FCSR_claim=False,results=results)
 return q
