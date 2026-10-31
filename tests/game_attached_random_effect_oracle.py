"""Ordered effect callbacks and literal guest state; bounded providers, no FCSR claim."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests import game_actor_phase_motion_oracle as phase
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_attached_random_effect_match as source
r=Path.cwd();o=r/source.BUILD
ENTRY,R,A,OTHER,STACK=0x150B5950,phase.ACTOR,0x240000,0x260000,phase.STACK
RNG,EMIT,POSITION=0x150ADA68,0x150B5A3C,0x150B60E0
SYMS=dict(func_150ADA68=RNG,func_150B5A3C=EMIT,func_150B60E0=POSITION,D_8009FC98=0x8009FC98,D_8009FC9C=0x8009FC9C)
@dataclass(frozen=True)
class Case:
 alive:int=1
 same:bool=True
 attached:int=1
 first:int=0
 second:int=0
 mode:int=0
 byte:int=255
 phase:int=0
 pattern:int=0
POINTS=((0,0x80000000,0x3F800000),(0x7FC12345,0x7F800000,0xFFC23456),(1,0x7F7FFFFF,0xFF7FFFFF))
def thresholds():
 base,data=sections(o/'before-conker_build_conker.us.elf')['.game_data']
 return tuple(int.from_bytes(data[at-base:at-base+4],'big')for at in(0x8009FC98,0x8009FC9C))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base,n in((R,64),(A,512),(OTHER,512)):m.update({base+i:(i*13+0x59)&255 for i in range(n)})
 put(m,R+40,A);put(m,R+14,123,2);m[R+44]=c.byte;m[R+1]=c.byte;m[R+12]=c.byte^255
 put(m,A,c.alive);m[A+59]=c.byte if c.same else c.byte^255;put(m,A+468,c.attached)
 for i,v in enumerate(POINTS[c.pattern%3]):put(m,A+20+i*4,v)
 for n,v in zip(('D_8009FC98','D_8009FC9C'),thresholds()):put(m,s[n],v)
 return m
def effect(m,c,s,t,ordinal):
 if c.mode&1:put(m,R+40,OTHER)
 if c.mode&2 and t==s['func_150ADA68']:
  for i,v in enumerate((0x41280000,0xC0600000,0x80000000)):put(m,A+20+4*i,v)
 if c.mode&4:
  put(m,s['D_8009FC98'],0x3F800000);put(m,s['D_8009FC9C'],0xBF800000)
 if c.mode&8:m[R+1]=(c.byte+ordinal*7)&255;m[R+12]=(c.byte-ordinal*3)&255
 if c.mode&16 and t==s['func_150B5A3C']:put(m,A+468,0x345600)
 if c.mode&32:put(m,A,0);m[A+59]^=1
def point(c):return POINTS[(c.pattern+1)%3]
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];ordinal=0
 def call(t,args,payload=None):
  nonlocal ordinal
  ordinal+=1;calls.append((t,args,payload));effect(m,c,s,t,ordinal)
 if read(m,A)==0 or m[R+44]!=m[A+59]:put(m,R+14,65535,2)
 elif read(m,A+468):
  call(s['func_150ADA68'],())
  if floating(c.first)<floating(read(m,s['D_8009FC98'])):
   value=tuple(read(m,A+20+4*i)for i in range(3));call(s['func_150B5A3C'],(m[R+12],m[R+1]),value)
  call(s['func_150ADA68'],())
  if floating(c.second)<floating(read(m,s['D_8009FC9C'])):
   call(s['func_150B60E0'],(A,));call(s['func_150B5A3C'],(m[R+12],m[R+1]),point(c))
 return m,calls
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+128}
class TrackedCode(phase.faults.TrackedCode):
 def __getitem__(self,pc):
  prev,w=self.last_pc,self.last_word;value=super().__getitem__(pc)
  if w>>26==17 and w>>21&31==8 and pc==prev+4:self.owner.delay_of=prev
  return value
class Oracle(phase.Oracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,fault=None):
  super().__init__(w,m,c,entry,s,connected,fault);self.ordinal=0;self.rng_count=0;self.code=TrackedCode(dict(self.code),self)
 def record_call(self,t):
  assert t in(self.s['func_150ADA68'],self.s['func_150B5A3C'],self.s['func_150B60E0'],ENTRY),hex(t)
  a=self.arguments(3)if t==self.s['func_150B5A3C']else self.arguments(2)if t==self.s['func_150B60E0']else()
  if t==self.s['func_150B5A3C']:
   assert a[0]==self.r[29]+40;args=a[1:];value=tuple(read(self.memory,a[0]+4*i)for i in range(3))
  elif t==self.s['func_150B60E0']:assert a[1]==self.r[29]+40;args=a[:1];value=None
  else:args=();value=None
  self.calls.append((t,args,value));self.events.append(('CALL',t,args));self.observations.append((t,read(self.memory,R+40),self.memory[R+1],self.memory[R+12],read(self.memory,A+468)))
 def hook(self,t):
  self.ordinal+=1;result=None
  if t==self.s['func_150ADA68']:result=(self.c.first,self.c.second)[self.rng_count];self.rng_count+=1
  elif t==self.s['func_150B60E0']:
   for i,v in enumerate(point(self.c)):self.put(self.r[5]+4*i,v,4)
  else:assert t==self.s['func_150B5A3C']
  effect(self.memory,self.c,self.s,t,self.ordinal)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if result is not None:self.f[0]=result
def linked(obj,label,entry,s):
 raw,_=payload(obj,'func_150B5950');assert len(raw)==236
 text,fs,relocations=parse_object(obj);asm,unknown=emit_function(text,fs['func_150B5950'],relocations,'func_150B5950',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_150B5950','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_150B5950.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_E2DA0.c.o'))]
 assert all(w==result[0]for w in result);return result
def compare(words,c,s=SYMS,entry=ENTRY):
 initial=fixture(c,s);want,calls=reference(initial,c,s);models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:assert public(m.memory)==public(want)and m.calls==calls,(c,'public or call mismatch',m.calls,calls)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
 return models[0]
def guest_suite():
 count=aliases=cuts=delays=0;seen=set();values=(0,0x3F800000,0x7FC12345,0xBF800000,*thresholds())
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(zip(SYMS,(entry+0x10000,entry+0x20000,entry+0x30000,0x81007FFC+j*4,0x8200FFFC+j*4)))
  words=images('effect-rebase-'+str(j),entry,s)
  for alive,same,attached,rands,mode,sp in itertools.product((0,1),(False,True),(0,1),range(6),(0,63),(0,8)):
   c=Case(alive,same,attached,values[rands],values[(rands+3)%6],mode,255,sp,rands%3);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if j==0:
   for index,at in enumerate((A+20,A+24,A+28,R,R+12)):
    a=dict(s,D_8009FC98=at);aw=images('effect-alias-'+str(index),entry,a)
    for sp in(0,8):compare(aw,Case(mode=63,phase=sp),a,entry);aliases+=1
   for c in(Case(alive=0),Case(same=False),Case(attached=0),Case(),Case(mode=63,phase=8),Case(first=0x3F800000,second=0x3F800000)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except phase.faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective effect access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4))-{60},sorted(set(range(0,236,4))-seen)
 return dict(cases=count,executions=count*4,independent_rebases=3,reachable_words=58,compiler_words=59,unreachable_offsets=[60],aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,full_state_and_access_trace_equal=True,ordered_nan_threshold_comparisons=True,source_pointer_snapshot_and_callback_mutations=True,original_threshold_words=list(thresholds()),hardware_FCSR_or_full_RNG_claim=False)

import sys
g=sys.modules[__name__]
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_actor_phase_motion_oracle import WindowCode
PARENT,RELEASE,DESTRUCTOR=0x15149264,0x1516972C,0x150AE790
def half(v):return((v&65535)^32768)-32768
class Caller(g.Oracle):
 def execute(self,w):
  if w>>26==32:
   rs,rt,offset=w>>21&31,w>>16&31,half(w&65535);value=self.get((self.r[rs]+offset)&0xFFFFFFFF,1)
   self.r[rt]=(value if value<128 else value-256)&0xFFFFFFFF;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:args=(self.r[4],);self.calls.append((t,args,None));self.events.append(('CALL',t,args));return
  if t not in(RELEASE,DESTRUCTOR):return super().record_call(t)
  args=(self.r[4],);self.calls.append((t,args,None));self.events.append(('CALL',t,args))
 def hook(self,t):
  if t not in(RELEASE,DESTRUCTOR):return super().hook(t)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 target=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target];pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==g.ENTRY]
 assert sites==[]and pointers==[0x22F0BC],(sites,pointers)
 window=list(struct.unpack_from('>45I',rom,0x176714));at=elf_slot_offset(before,PARENT,180);assert before[at:at+180]==rom[0x176714:0x1767C8]
 roots=g.images('effect-parent');seen=set();cases=0;cleanup=0
 for gate,enabled,flags,life,destructor,mode,sp in itertools.product((0,1,2),(False,True),(0,1),(-1,3),(False,True),(0,63),(0,8)):
  c=g.Case(alive=int(gate!=0),same=gate!=2,mode=mode,phase=sp);initial=g.fixture(c);g.put(initial,g.R+14,life,2);initial[g.R+13]=flags;initial[g.R+16]=0 if destructor else 255;initial[g.R+17]=69 if enabled else 255
  g.put(initial,0x800BE9E4,5);g.put(initial,0x8008A5FC,g.ENTRY);g.put(initial,0x8008A4C0,DESTRUCTOR)
  prepared=dict(initial)
  if flags:g.put(prepared,g.R+14,(life-5)&65535,2)
  if enabled:want,calls=g.reference(prepared,c);calls=[(g.ENTRY,(g.R,),None),*calls]
  else:want,calls=prepared,[]
  expired=half(g.read(want,g.R+14,2))<0
  if expired and destructor:calls.append((DESTRUCTOR,(g.R,),None))
  if expired:calls.append((RELEASE,(g.R,),None));cleanup+=1
  models=[]
  for root,poison in itertools.product(roots,(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
   code={g.ENTRY+4*i:w for i,w in enumerate(root)};m=Caller(window,initial,c,PARENT,connected=code)
   m.stop_pc=None;m.poison_pc=0x151492B8;m.poison_value=poison;m.code=WindowCode(dict(m.code),m);m.run()
   assert g.public(m.memory)==g.public(want)and m.calls==calls,(gate,enabled,flags,life,destructor,mode,'caller result',m.calls,calls)
   assert m.r[29]==g.STACK+sp;models.append(m);seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  cases+=1
 assert set(range(PARENT,PARENT+180,4))<=seen
 return dict(cases=cases,executions=cases*16,original_parent_words=45,all_parent_words_visited=True,ignored_return_poison_values=4,callback_table='D_8008A4E8',callback_index=69,callback_record_offset=17,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,cleanup_cases=cleanup,destructor_and_cleanup_are_bounded_hooks=True,hardware_or_full_gameplay_claim=False)


TRANSFORM=0x15143134
class Connected(g.Oracle):
 def record_call(self,t):
  if t==TRANSFORM:
   args=self.arguments(3);assert args[0]==0x8009FC30 and args[1]==self.output_pointer
   self.calls.append((t,args,None));self.events.append(('CALL',t,args));return
  if t==self.s['func_150B60E0']:self.output_pointer=self.r[5];self.ordinal+=1
  return super().record_call(t)
 def hook(self,t):
  if t!=TRANSFORM:return super().hook(t)
  for i,v in enumerate(g.point(self.c)):self.put(self.r[5]+4*i,v,4)
  g.effect(self.memory,self.c,self.s,self.s['func_150B60E0'],self.ordinal)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 helper=list(struct.unpack_from('>12I',rom,0xE3590));at=elf_slot_offset(before,g.POSITION,48);assert before[at:at+48]==rom[0xE3590:0xE35C0]
 code={g.POSITION+4*i:w for i,w in enumerate(helper)};roots=g.images('effect-position-connected');count=0;seen=set()
 for mode,first,second,sp,pattern in itertools.product((0,1,2,4,8,16,32,63),(0,0x3F800000),(0,0xBF800000),(0,8),(0,1,2)):
  c=g.Case(mode=mode,first=first,second=second,phase=sp,pattern=pattern);initial=g.fixture(c);nested=[];real_effect=g.effect
  def capture(m,c,s,t,n):
   if t==s['func_150B60E0']:nested.append((TRANSFORM,(0x8009FC30,g.STACK+sp-16,(g.read(m,g.A+468)+0x140)&0xFFFFFFFF),None))
   return real_effect(m,c,s,t,n)
  g.effect=capture
  try:want,plain=g.reference(initial,c)
  finally:g.effect=real_effect
  calls=[]
  for call in plain:
   calls.append(call)
   if call[0]==g.POSITION:calls.append(nested.pop(0))
  assert not nested
  models=[Connected(w,initial,c,connected=code).run()for w in roots]
  for m in models:assert g.public(m.memory)==g.public(want)and m.calls==calls,(c,m.calls,calls);seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  count+=1
 assert set(range(g.POSITION,g.POSITION+48,4))<=seen
 return dict(cases=count,executions=count*4,original_position_helper_words=12,all_helper_words_visited=True,point_source=0x8009FC30,attachment_matrix_offset=0x140,transform_is_bounded_model=True,RNG_is_bounded_float_provider=True,complete_transform_RNG_or_hardware_claim=False)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
guest=g
text=source.HEADERS+source.SELECTED;start=text.index('/* Expire');headers,body=text[:start],text[start:]
prefix=r'''
typedef struct {u8 pad0,kind,pad2[10],selector,padD;s16 life;u8 pad10[24];u8 *actor;u8 tag,pad2D[3];} Effect;
typedef struct {s32 alive;u8 pad4[16];f32 position[3];u8 pad20[27],tag,pad3C[408];u8 *attachment;u8 pad1D8[40];} Actor;
typedef char effect_layout[sizeof(Effect)==48&&__builtin_offsetof(Effect,actor)==40?1:-1];
typedef char actor_layout[sizeof(Actor)==512&&__builtin_offsetof(Actor,attachment)==468?1:-1];
static struct {u32 first;Effect value;u32 last;} actual;
static Effect expected;static Actor actor,expectedActor,other;
typedef struct {u32 target,args[3],point[3];} Call;
static Call logs[5],expectedLogs[5];static int count,expectedCount,rngCount,mode,pattern;
static u32 randoms[2],eFirst,eSecond;
f32 D_8009FC98,D_8009FC9C;
static const u32 points[3][3]={{0,0x80000000,0x3F800000},{0x7FC12345,0x7F800000,0xFFC23456},{1,0x7F7FFFFF,0xFF7FFFFF}};
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void effect(int target,int ordinal,int isExpected){
 Effect *r=isExpected?&expected:&actual.value;Actor *a=isExpected?&expectedActor:&actor;
 if(mode&1)r->actor=(u8 *)&other;
 if((mode&2)&&target==1){a->position[0]=10.5f;a->position[1]=-3.5f;a->position[2]=real(0x80000000);}
 if(mode&4){if(isExpected){eFirst=0x3F800000;eSecond=0xBF800000;}else{D_8009FC98=1.0f;D_8009FC9C=-1.0f;}}
 if(mode&8){r->kind=(u8)(r->tag+ordinal*7);r->selector=(u8)(r->tag-ordinal*3);}
 if((mode&16)&&target==2)a->attachment=(u8 *)0x345600;
 if(mode&32){a->alive=0;a->tag^=1;}
}
static void record(int target,u32 a0,u32 a1,u32 a2,const f32 *point,int isExpected){
 int i,n=isExpected?expectedCount++:count++;Call *c=isExpected?&expectedLogs[n]:&logs[n];if(n>=5)__builtin_trap();
 c->target=(u32)target;c->args[0]=a0;c->args[1]=a1;c->args[2]=a2;
 for(i=0;i<3;i++)c->point[i]=point?word(point[i]):0;
 effect(target,n+1,isExpected);
}
f32 func_150ADA68(void){f32 v=real(randoms[rngCount++]);record(1,0,0,0,0,0);return v;}
s32 func_150B5A3C(f32 *p,s32 selector,s32 kind){record(2,(u32)selector,(u32)kind,0,p,0);return 0x12345678;}
void func_150B60E0(u8 *a,f32 *p){int i;for(i=0;i<3;i++)p[i]=real(points[(pattern+1)%3][i]);record(3,(u32)a,0,0,0,0);}
static void reference(void){
 f32 p[3];int i;
 if(expectedActor.alive==0||expected.tag!=expectedActor.tag){expected.life=-1;return;}
 if(expectedActor.attachment==0)return;
 record(1,0,0,0,0,1);
 if(real(randoms[0])<real(eFirst)){
  for(i=0;i<3;i++)p[i]=expectedActor.position[i];record(2,expected.selector,expected.kind,0,p,1);
 }
 record(1,0,0,0,0,1);
 if(real(randoms[1])<real(eSecond)){
  for(i=0;i<3;i++)p[i]=real(points[(pattern+1)%3][i]);record(3,(u32)&actor,0,0,0,1);record(2,expected.selector,expected.kind,0,p,1);
 }
}
'''
tail=r'''
static int one(u32 value,int p){
 static const u32 values[8]={0,0x3F800000,0x7FC12345,0xBF800000,FIRST,SECOND,0x3DCCCCCD,0x7F800000};
 int i;actual.first=actual.last=0xBAADF00D;
 for(i=0;i<48;i++)((u8 *)&actual.value)[i]=((u8 *)&expected)[i]=(u8)(i*13+0x59);
 for(i=0;i<512;i++)((u8 *)&actor)[i]=((u8 *)&expectedActor)[i]=((u8 *)&other)[i]=(u8)(i*13+0x59);
 actual.value.actor=expected.actor=(u8 *)&actor;actual.value.kind=expected.kind=(u8)value;actual.value.selector=expected.selector=(u8)(value>>8);actual.value.tag=expected.tag=(u8)value;actual.value.life=expected.life=123;
 actor.alive=expectedActor.alive=p==1?0:1;actor.tag=expectedActor.tag=(u8)(value^(p==2?255:0));actor.attachment=expectedActor.attachment=p==3?(u8 *)0:(u8 *)0x234000;
 pattern=(int)(value%3);for(i=0;i<3;i++)actor.position[i]=expectedActor.position[i]=real(points[pattern][i]);
 D_8009FC98=real(eFirst=FIRST);D_8009FC9C=real(eSecond=SECOND);
 randoms[0]=values[(value+(u32)p)&7];randoms[1]=values[((value>>3)+(u32)p)&7];
 mode=(int)((value*7+(u32)p*13)&63);count=expectedCount=rngCount=0;
 func_150B5950((u8 *)&actual.value);reference();
 if(actual.first!=0xBAADF00D||actual.last!=0xBAADF00D||count!=expectedCount||word(D_8009FC98)!=eFirst||word(D_8009FC9C)!=eSecond)return 1;
 for(i=0;i<48;i++)if(((u8 *)&actual.value)[i]!=((u8 *)&expected)[i])return 1;
 for(i=0;i<512;i++)if(((u8 *)&actor)[i]!=((u8 *)&expectedActor)[i])return 1;
 for(i=0;i<count*(int)sizeof(Call);i++)if(((u8 *)logs)[i]!=((u8 *)expectedLogs)[i])return 1;
 return 0;
}
static int run(void){u32 v;int p;for(v=0;v<65536;v++)for(p=0;p<4;p++)if(one(v,p))return 1;return 0;}
'''
first,second=guest.thresholds();tail=tail.replace('FIRST','0x%Xu'%first).replace('SECOND','0x%Xu'%second)
def harness(b):return headers+prefix+b+tail+START
controls={
 'omit_expiry':body.replace('*(s16 *)(record + 0xE) = -1;','*(s16 *)(record + 0xE) = 123;'),
 'wrong_actor_tag':body.replace('actor[0x3B]','actor[0x3A]'),
 'wrong_record_tag':body.replace('record[0x2C]','record[0x2B]'),
 'wrong_kind':body.replace('record[1]','record[0]'),
 'wrong_selector':body.replace('record[0xC]','record[0xD]'),
 'ignore_liveness':body.replace('*(s32 *)actor == 0 || ',' '),
 'missing_attachment_gate':body.replace('*(s32 *)(actor + 0x1D4) != 0','1'),
 'reuse_random_sample':body.replace('sample = func_150ADA68();\n        if (sample < D_8009FC9C)','if (sample < D_8009FC9C)'),
 'wrong_second_threshold':body.replace('sample < D_8009FC9C','sample < D_8009FC98'),
 'inclusive_first_threshold':body.replace('sample < D_8009FC98','sample <= D_8009FC98'),
 'inclusive_second_threshold':body.replace('sample < D_8009FC9C','sample <= D_8009FC9C'),
 'wrong_first_x':body.replace('position[0] = *(f32 *)(actor + 0x14)','position[0] = *(f32 *)(actor + 0x18)'),
 'wrong_first_z':body.replace('position[2] = *(f32 *)(actor + 0x1C)','position[2] = *(f32 *)(actor + 0x18)'),
 'reload_actor_pointer':body.replace('func_150B60E0(actor, position)','func_150B60E0(*(u8 **)(record + 0x28), position)'),
 'skip_second_emission':body.replace('func_150B60E0(actor, position);\n            func_150B5A3C(position, record[0xC], record[1]);','func_150B60E0(actor, position);')}
def native_suite():
 results=[]
 for name,b,opt,negative in [('positive-'+opt,body,opt,False)for opt in ('-O0','-O2','-O3')]+[(n,b,'-O2',True)for n,b in controls.items()]:
  assert not negative or b!=body,name
  p=o/('native-'+name+'.c');p.write_text(harness(b));exe=p.with_suffix('');cmd=native_command(opt)+['-Wno-unused-but-set-variable','-o',str(exe),str(p)]
  q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==(1 if negative else 0),(name,q.returncode,q.stderr);results.append(dict(name=name,optimization=opt,control=negative,exit=q.returncode))
 q=dict(complete=True,positive_cases_each=262144,profiles=['O0','O2','O3'],effective_controls=len(controls),controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all65536_kind_selector_pairs=True,full_records_actor_state_and_call_log=True,canaries_checked=True,ordered_nan_threshold_comparisons=True,cached_actor_across_mutating_callbacks=True,portable_alias_hardware_FCSR_or_complete_RNG_claim=False,results=results)
 return q
