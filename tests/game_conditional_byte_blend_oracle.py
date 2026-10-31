"""Conditional byte blend: bounded nontrapping FP control and observed pointer return."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.experiments import game_conditional_byte_blend_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
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
RECORD,OWNER,PEER,FLAGS=0x220000,0x230000,0x240000,0x250000
CALLER,CLEANUP,TABLE,TICKS=0x15154C90,0x1516972C,0x8008ACC8,0x800BE9E4
SYMS=dict(D_800AAEA8=0x800AAEA8)
VALUES=(0,0x80000000,1,0x80000001,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x437F0000,0x43800000,0x4EFFFFFF,0x4F000000,0x4F000001,0x4F7FFFFF,0x4F800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
 flags:int=0x2000
 gate:int=0
 current:int=0x437F0000
 target:int=0x437F0000
 coefficient:int=0x3ECCCCCD
 fcsr:int=0
 phase:int=0
 alias:int=0
 omit:bool=False

def packed(v):
 try:return bits(v)
 except OverflowError:return bits(math.copysign(math.inf,v))
def blend_value(old,target,coefficient):
 difference=packed(floating(target)-floating(old));scaled=packed(floating(difference)*floating(coefficient))
 return packed(floating(old)+floating(scaled))
def converted(word):
 v=floating(word)
 if not math.isfinite(v):return 255
 n=math.trunc(v);return n&255 if 0<=n<2**32 else 255

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
 m.update({RECORD+i:(i*13+0x59)&255 for i in range(-16,144)})
 put(m,RECORD+0x70,OWNER);put(m,OWNER+0x36C,FLAGS);put(m,FLAGS,c.flags,2)
 put(m,OWNER+0x3D4,PEER);put(m,PEER+0x19E,c.gate,2)
 put(m,RECORD+0x74,c.current);put(m,RECORD+0x78,c.target);put(m,s['D_800AAEA8'],c.coefficient)
 if c.alias==1:put(m,OWNER+0x36C,RECORD+0x2E);put(m,RECORD+0x2E,c.flags,2)
 if c.alias==2:put(m,OWNER+0x3D4,RECORD+0x76-0x19E)
 if c.omit:
  if not c.flags&0x2000:
   for i in range(4):del m[OWNER+0x3D4+i]
  if not c.flags&0x2000 or c.gate:
   for i in range(4):del m[RECORD+0x78+i]
 return m

def reference(initial,s=SYMS):
 m=dict(initial);owner=read(m,RECORD+0x70);flags=read(m,read(m,owner+0x36C),2);target=0
 if flags&0x2000 and read(m,read(m,owner+0x3D4)+0x19E,2)==0:target=read(m,RECORD+0x78)
 value=blend_value(read(m,RECORD+0x74),target,read(m,s['D_800AAEA8']));put(m,RECORD+0x74,value)
 m[RECORD+0x2E]=converted(read(m,RECORD+0x74));return m,RECORD+0x70

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+128}

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  self.c,self.s,self.trace=c,s,[];self.fcsr=c.fcsr;self.control=[];self.raw_cursor_live=False;self.force_zero=False;self.after_root=0x15154D04
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected)
  self.root_fault=fault
 def execute(self,w):
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):
   prior=self.fcsr;AreaOracle.execute(self,w);self.control.append((self.current_pc,w,prior,self.fcsr))
  elif op==17 and rs==16 and fn in(0,1,2):
   a,b=floating(self.f[w>>11&31]),floating(self.f[w>>16&31]);v=(a+b)if fn==0 else(a-b)if fn==1 else(a*b);self.f[w>>6&31]=packed(v)
  elif op==32:
   off=((w&65535)^32768)-32768;v=self.get((self.r[w>>21&31]+off)&0xFFFFFFFF,1);self.r[w>>16&31]=((v^128)-128)&0xFFFFFFFF
  else:super().execute(w)
  if w==0x24830070:self.raw_cursor_live=True
  if w==0x00601025:self.raw_cursor_live=False
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t in(source.ENTRY,CLEANUP),hex(t);a=self.arguments(1);self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==CLEANUP:assert self.fcsr==self.c.fcsr,'temporary conversion control leaked to cleanup'
 def hook(self,t):
  assert t==CLEANUP;self.memory[RECORD+0x60]=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=source.ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_151CB510.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_1F4650.c.o'))]
 assert result[0]==result[2]==result[3]
 assert[i for i,(a,b)in enumerate(zip(result[0],result[1]))if a!=b]==[7,12,14,15,23,26,56]
 return result
def state(m,ignore_v1=False):
 regs=list(m.r)
 if ignore_v1:
  if m.raw_cursor_live:regs[2]=regs[3]
  regs[3]=0
 return(regs,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.fcsr,m.control)
def compare(words,c,s=SYMS,entry=source.ENTRY,initial=None):
 initial=fixture(c,s)if initial is None else initial;want,result=reference(initial,s);models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:
  assert public(m.memory)==public(want),(c,'memory')
  assert m.r[2]==result and m.r[4]==RECORD and m.r[29]==STACK+c.phase and m.fcsr==c.fcsr,(c,'ABI/FCSR')
 assert state(models[0])==state(models[2])==state(models[3])
 assert state(models[0],True)==state(models[1],True),(c,'raw observable state')
 assert set(i for i,(a,b)in enumerate(zip(models[0].r,models[1].r))if a!=b)<={3}
 return models[0]

def guest_suite():
 count=aliases=cuts=delays=0;seen=set();paths=set()
 for layout,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if layout==0 else dict(D_800AAEA8=0x81008000+layout*0x10000);words=images('blend-rebase-'+str(layout),entry,s)
  if layout==0:
   corpus=(Case(flags,gate,current,target,coefficient,fcsr,phase)for flags,gate,current,target,coefficient,fcsr,phase in itertools.product((0,0x2000,0xFFFF),(0,1),VALUES,(0,0x437F0000,0x4F000000,0x7FC12345),(0,0x3ECCCCCD,0x3F800000),(0,0x00801004),(0,8)))
  else:corpus=(Case(flags,gate,current,0x437F0000,fcsr=0x00801004)for flags,gate,current in itertools.product((0,0x2000),(0,1),VALUES))
  for c in corpus:
   m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1;paths.add(tuple(p-entry for p in sorted(m.visits)if entry+0x7C<=p<entry+0xD8))
  if layout==0:
   for rm,value in itertools.product(range(4),(0,0x3F800000,0x4F000000,0x4F7FFFFF)):
    c=Case(current=value,target=value,fcsr=0xA5000000|rm);compare(words,c);count+=1
   for c in(Case(flags=0,omit=True),Case(gate=1,omit=True),Case(flags=0xDFFF,omit=True)):
    compare(words,c);count+=1
   for coefficient in(0,0x7F800000,0xFF800000,0x7FC12345):compare(words,Case(current=0x7F7FFFFF,target=0xFF7FFFFF,coefficient=coefficient));count+=1
   for alias,current,gate,phase in itertools.product((1,2),(0,0x437F0000,0x4F000000),(0,1),(0,8)):
    c=Case(current=current,gate=gate,phase=phase,alias=alias);compare(words,c);aliases+=1
   for offset in(0x74,0x78,0x2C):
    a=dict(s,D_800AAEA8=RECORD+offset);aw=images('blend-coefficient-alias-'+str(offset),entry,a);compare(aw,Case(),a);aliases+=1
   for c in(Case(flags=0,omit=True),Case(gate=1,omit=True),Case(),Case(current=0x4F000000),Case(current=0x7FC12345),Case(current=0xBF800000)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective blend access cut')
      models.append(m)
     assert state(models[0])==state(models[2])==state(models[3]);assert state(models[0],True)==state(models[1],True)
     cuts+=1;delays+=models[0].delay_of is not None
 dead={13*4,50*4};assert seen==set(range(0,236,4))-dead,sorted(set(range(0,236,4))-seen)
 assert len(paths)>=3,'missing valid/fallback/invalid conversion paths'
 return dict(cases=count,executions=4*count,root_words_visited=57,compiler_words=59,unreachable_offsets=sorted(dead),independent_rebases=3,guest_alias_cases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,conversion_path_shapes=len(paths),raw_difference_only_caller_clobbered_v1=True,returned_blend_address=True,temporary_conversion_FCSR_restored=True,nondefault_rounding_exact_arithmetic_only=True,arithmetic_rounding_flags_and_hardware_traps_claimed=False)

def half(v):return((v&65535)^32768)-32768
def caller_reference(initial,c,force_zero=False):
 m=dict(initial);calls=[];flags=read(m,RECORD+0x24,2);expired=False
 if flags&1:
  value=(half(read(m,RECORD+0x22,2))-signed(read(m,TICKS)))&65535;put(m,RECORD+0x22,value,2);expired=half(value)<0
 method=m[RECORD+0x68]&15
 if method and not expired:
  assert method==4;calls.append((source.ENTRY,(RECORD,)));m,result=reference(m)
  if force_zero:result=0
  if not result:expired=True
 if flags&8:
  timer=half(read(m,RECORD+0x22,2));limit=half(read(m,RECORD+0x26,2))
  if timer<limit:
   candidate=half(timer*half(read(m,RECORD+0x28,2)))
   if candidate<m[RECORD+0x2E]:m[RECORD+0x2E]=candidate&255
 if expired:calls.append((CLEANUP,(RECORD,)));m[RECORD+0x60]=1
 return m,calls

class ReturnControl(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.after_root and self.owner.force_zero:self.owner.r[2]=0
  return super().__getitem__(pc)

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();delta=source.ENTRY-source.ROM
 parent=list(struct.unpack_from('>60I',rom,CALLER-delta));words=images('blend-callers');base,data=sections(o/'before-conker_build_conker.us.elf')['.game_data']
 assert struct.unpack_from('>I',data,TABLE+16-base)[0]==source.ENTRY
 target=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target];pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY];assert sites==[]and pointers==[0x22F798]
 count=0;seen=set();cleanups=0
 for flags,timer,ticks,method,current,peer,phase in itertools.product((0,1,8,9),(-1,0,7),(0,1),(0,4,0xA4),(0,0x437F0000,0x4F000000),(0,1),(0,8)):
  c=Case(gate=peer,current=current,phase=phase,fcsr=0x00801004);initial=fixture(c);put(initial,RECORD+0x24,flags,2);put(initial,RECORD+0x22,timer&65535,2);put(initial,RECORD+0x26,10,2);put(initial,RECORD+0x28,3,2);initial[RECORD+0x68]=method;put(initial,TICKS,ticks)
  initial.update({TABLE+i:data[TABLE-base+i]for i in range(64)});want,calls=caller_reference(initial,c);models=[]
  for root in words:
   code={source.ENTRY+4*i:w for i,w in enumerate(root)};m=Oracle(parent,initial,c,CALLER,connected=code).run();assert public(m.memory)==public(want)and m.calls==calls and m.fcsr==c.fcsr,(c,flags,timer,ticks,method,'parent')
   models.append(m);seen.update(m.visits)
  assert state(models[0])==state(models[2])==state(models[3]);assert state(models[0],True)==state(models[1],True)
  count+=1;cleanups+=any(t==CLEANUP for t,a in calls)
 positive_words=sum(CALLER+4*i in seen for i in range(60));controls=0
 for current in(0,0x437F0000,0x4F000000,0x7FC12345):
  c=Case(current=current);initial=fixture(c);put(initial,RECORD+0x24,0,2);initial[RECORD+0x68]=4;put(initial,TICKS,0);initial.update({TABLE+i:data[TABLE-base+i]for i in range(64)})
  want,calls=caller_reference(initial,c,True);code={source.ENTRY+4*i:w for i,w in enumerate(words[0])};m=Oracle(parent,initial,c,CALLER,connected=code);m.force_zero=True;m.code=ReturnControl(dict(m.code),m);m.run()
  assert public(m.memory)==public(want)and m.calls==calls and any(t==CLEANUP for t,a in calls);seen.update(m.visits);controls+=1
 assert set(CALLER+4*i for i in range(60))<=seen
 return dict(cases=count,executions=4*count,original_parent_words=60,parent_words_visited=60,positive_parent_words_visited=positive_words,cleanup_cases=cleanups,cleanup_is_bounded_model=True,registration_table='D_8008ACC8',method_slot=4,registration_pointer_ROM=0x22F798,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,callback_return_used=True,returned_blend_address=True,effective_zero_return_controls=controls,hardware_or_complete_cleanup_claim=False)

def native_harness(body,control=False):
 return source.HEADERS+('\n#define CONTROL 1\n'if control else'\n#define CONTROL 0\n')+r'''
typedef char pointer_is_four[sizeof(void *)==4?1:-1];
typedef char record_size_is_124[sizeof(ConditionalByteBlend)==124?1:-1];
typedef char blend_at_112[__builtin_offsetof(ConditionalByteBlend,blend)==112?1:-1];
typedef char owner_flags_at_876[__builtin_offsetof(ConditionalBlendOwner,flags)==876?1:-1];
typedef char owner_peer_at_980[__builtin_offsetof(ConditionalBlendOwner,peer)==980?1:-1];
f32 D_800AAEA8;
static struct {u32 first;ConditionalByteBlend record;u32 last;} actual;
static ConditionalByteBlend expected;
static ConditionalBlendOwner owner;
static ConditionalBlendPeer peer;
static u16 flags;
static f32 value(u32 bits) {union{u32 u;f32 f;}v;v.u=bits;return v.f;}
static u32 word(f32 number) {union{u32 u;f32 f;}v;v.f=number;return v.u;}
static f32 subtract(f32 a,f32 b) {volatile f32 v=a-b;return v;}
static f32 multiply(f32 a,f32 b) {volatile f32 v=a*b;return v;}
static f32 add(f32 a,f32 b) {volatile f32 v=a+b;return v;}
''' + body+r'''
static int one(u16 f,u16 gate,f32 old,f32 target) {
 f32 goal,v;ConditionalBlendState *answer;int i;
 actual.first=actual.last=0xBAADF00D;flags=f;peer.gate=gate;
 owner.flags=&flags;owner.peer=(!CONTROL&&!(flags&0x2000))?(ConditionalBlendPeer *)0:&peer;
 for(i=0;i<(int)sizeof(expected);i++)((u8 *)&actual.record)[i]=((u8 *)&expected)[i]=(u8)(i*13+0x59);
 actual.record.blend.owner=expected.blend.owner=&owner;
 actual.record.blend.current=expected.blend.current=old;
 actual.record.blend.target=expected.blend.target=target;
 D_800AAEA8=value(0x3ECCCCCD);
 goal=((flags&0x2000)&&!gate)?target:0.0f;
 v=add(old,multiply(subtract(goal,old),D_800AAEA8));
 expected.blend.current=v;expected.output=(u32)v;
 answer=func_151CB510(&actual.record);
 if(answer!=&actual.record.blend||actual.first!=0xBAADF00D||actual.last!=0xBAADF00D)return 1;
 for(i=0;i<(int)sizeof(expected);i++)if(((u8 *)&actual.record)[i]!=((u8 *)&expected)[i])return 1;
 if(flags!=f||peer.gate!=gate||owner.flags!=&flags||word(D_800AAEA8)!=0x3ECCCCCD)return 1;
 return 0;
}
static int run(void) {
 static const u32 edge[14]={0,0x80000000,0x3F000000,0xBF000000,0x3F7FFFFF,0x437EFFFF,0x437F0000,0x437F0001,0x43800000,0x4B7FFFFF,0x4EFFFFFF,0x4F000000,0x4F000001,0x4F7FFFFF};
 u32 low;int p;u16 f,gate;
 for(low=0;low<65536;low++)for(p=0;p<4;p++) {
  f=(p==0)?(u16)low:0x2000;gate=(p==2)?1:(p==3)?(u16)low:0;
  if(one(f,gate,(f32)low/128.0f,(f32)((low*17)&65535)/128.0f))return 1;
 }
 for(p=0;p<14;p++)if(one(0x2000,0,value(edge[p]),value(edge[p])))return 1;
 return 0;
}
''' + START

def native_controls():
 s=source.SELECTED
 result={
  'wrong_flag_bit':s.replace('0x2000','0x1000'),
  'inverted_peer_gate':s.replace('owner->peer->gate == 0','owner->peer->gate != 0'),
  'missing_enabled_target':s.replace('target = blend->target;','target = 0.0f;'),
  'wrong_disabled_target':s.replace('target = 0.0f;','target = 1.0f;'),
  'current_instead_of_target':s.replace('target = blend->target;','target = blend->current;'),
  'wrong_coefficient':s.replace('* D_800AAEA8','* 0.5f'),
  'missing_current_store':s.replace('blend->current += (target - blend->current) * D_800AAEA8;','(void)target;'),
  'wrong_output_field':s.replace('record->output =','record->reserved00[0x2D] ='),
  'wrong_output_mask':s.replace('(u32)blend->current;','((u32)blend->current) & 0x7F;'),
  'incorrect_saturation':s.replace('record->output = (u32)blend->current;','record->output = blend->current > 255.0f ? 255 : (u32)blend->current;'),
  'shifted_conversion':s.replace('record->output = (u32)blend->current;','record->output = ((u32)blend->current) >> 1;'),
  'null_return':s.replace('return blend;','return (ConditionalBlendState *)0;'),
  'owner_return':s.replace('return blend;','return (ConditionalBlendState *)owner;'),
  'record_return':s.replace('return blend;','return (ConditionalBlendState *)record;'),
  'rounded_conversion':s.replace('record->output = (u32)blend->current;','record->output = (u32)(blend->current + 0.5f);'),
 }
 assert len(result)==15 and all(v!=s for v in result.values());return result

def native_suite():
 for label,body in [('positive',source.SELECTED),*native_controls().items()]:
  unit=o/('native-byte-blend-'+label+'.c');unit.write_text(native_harness(body,label!='positive'))
  for opt in('O0','O2','O3')if label=='positive'else('O2',):
   exe=o/('native-byte-blend-'+label+'-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-fsanitize=float-cast-overflow','-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(label,opt,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==(0 if label=='positive'else 1),(label,opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=262158,all65536_flags=True,all65536_peer_gates=True,effective_controls=15,controls_exit_by_semantic_mismatch=True,UBSan_and_float_cast_overflow_trapping=True,defined_finite_unsigned_conversion_domain=True,disabled_owner_peer_can_be_null=True,exact_returned_blend_pointer=True,portable_alias_or_hardware_FCSR_claim=False)
