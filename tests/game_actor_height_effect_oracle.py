"""Actor-height effect: bit-preserving capture, narrow arguments and original callers.

Seeded automatic padding and overlapping guest records are machine contracts;
native checks use disjoint typed objects and compare initialized packet fields.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.experiments import game_actor_height_effect_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD
ACTOR,EFFECT,GATE,CLASSIFY,FACTORY,COPY=0x240000,0x200000,0x800C35EA,0x1510F8CC,0x151491F4,0x10022EC0
CONSTRUCTOR,ALLOC,ZERO,HEAP,REGISTER=0x15149130,0x15167A68,0x100226F0,0x10003C6C,0x15168A4C
SYMS=dict(D_800C35EA=GATE,func_1510F8CC=CLASSIFY,func_151491F4=FACTORY,memcpy=COPY)
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345)
@dataclass(frozen=True)
class Case:
 actor:int=ACTOR
 gate:int=0
 kind:int=15
 effect:int=0x8000
 variant:int=0xFF
 flags:int=0x80000001
 allocated:bool=True
 mutation:int=0
 pattern:int=0
 phase:int=0
 record:int=EFFECT
 head:int=0

def half(v):return(((v&65535)^32768)-32768)&0xFFFFFFFF
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
 for base,length in((c.actor or ACTOR,416),(c.record,160)):
  m.update({base+i:(i*13+0x59)&255 for i in range(-16,length)})
 m[s['D_800C35EA']]=c.gate
 if c.head:m.update({c.head+i:(i*7+0x69)&255 for i in range(32)})
 put(m,0x800DCE50+(c.flags&255)*0x1A0+35*4,c.head)
 if c.actor:
  for off,p in((20,0),(24,1),(28,2),(384,3)):put(m,c.actor+off,FLOATS[(c.pattern+p)&7])
  put(m,c.actor+388,c.kind&0xFFFFFFFF)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def projection(m,c):
 return public(m),bytes(m[c.actor+i]for i in range(400))if c.actor else b''
def mutate(m,c,s,bit):
 if c.mutation&bit and c.actor:
  for off,v in((20,0x42040000),(24,0xC2300000),(28,0x425C0000),(384,0x3F000000),(388,0x12345678)):put(m,c.actor+off,v)
  m[s['D_800C35EA']]=1
def copy_bytes(m,d,s,n):
 for i in range(n):m[d+i]=m[s+i]
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];packet=None
 if not c.actor:return m,calls,packet
 p=STACK+c.phase-24;put(m,p,read(m,c.actor+20));put(m,p+8,read(m,c.actor+28))
 if m[s['D_800C35EA']]==1:return m,calls,packet
 put(m,p+4,read(m,c.actor+384));put(m,p+16,0)
 kind=read(m,c.actor+388);calls.append((s['func_1510F8CC'],(kind,)));mutate(m,c,s,1)
 m[p+12]=int(kind&31 in(15,17));packet=bytes(m[p+i]for i in range(20))
 calls.append((s['func_151491F4'],(half(c.effect),0xFFFFFFFF,1,1,0,20,c.variant&255,c.flags&0xFFFFFFFF)));mutate(m,c,s,2)
 if c.allocated:
  calls.append((s['memcpy'],(c.record+40,p,20)));copy_bytes(m,c.record+40,p,20)
 return m,calls,packet

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None):
  self.c,self.s,self.trace,self.packet,self.copied=c,s,[],None,None
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.actor,c.effect&0xFFFFFFFF,c.variant&0xFFFFFFFF,c.flags&0xFFFFFFFF),connected=connected)
 def execute(self,w):
  if w>>26==32:
   offset=((w&65535)^32768)-32768;v=self.get((self.r[(w>>21)&31]+offset)&0xFFFFFFFF,1)
   self.r[(w>>16)&31]=((v^128)-128)&0xFFFFFFFF
  else:super().execute(w)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  sizes={self.s['func_1510F8CC']:1,self.s['func_151491F4']:8,self.s['memcpy']:3,CONSTRUCTOR:9,ALLOC:6,ZERO:2,HEAP:5,REGISTER:2}
  assert t in sizes,hex(t);args=self.arguments(sizes[t]);self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.s['func_151491F4']:self.packet=bytes(self.memory[STACK+self.c.phase-24+i]for i in range(20))
  if t==self.s['memcpy']:self.copied=bytes(self.memory[args[1]+i]for i in range(args[2]))
 def hook(self,t):
  c,s=self.c,self.s;args=self.calls[-1][1];result=0
  if t==s['func_1510F8CC']:result=args[0]&31;mutate(self.memory,c,s,1)
  elif t in(s['func_151491F4'],HEAP):mutate(self.memory,c,s,2);result=c.record if c.allocated else 0
  elif t==s['memcpy']:copy_bytes(self.memory,*args);result=args[0]
  elif t==ZERO:
   for i in range(args[1]):self.memory[args[0]+i]=0
  else:assert t==REGISTER;result=0xDEAD0001
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[source.FUNCTION];asm,unknown=emit_function(text,f,rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def guest_suite():
 count=aliases=cuts=delaycuts=0;seen=set()
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(D_800C35EA=0x81007FFF+j*0x10000,func_1510F8CC=entry+0x10000,func_151491F4=entry+0x20000,memcpy=entry+0x30000)
  images=[linked(o/n,'rebase-%d-%d'%(j,k),entry,s)for k,n in enumerate(('original-func_151A0A10.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_1CC440.c.o'))];assert all(w==images[0]for w in images)
  for kind,effect,variant,flags,allocated,mutation,phase in itertools.product((0,10,15,17,31,0xFFFFFFEF),(0,0x8000,0xFFFF),(0,0xFFFFFF80),(0,0xFFFFFFFF),(False,True),(0,3),(0,8)):
   c=Case(kind=kind,effect=effect,variant=variant,flags=flags,allocated=allocated,mutation=mutation,pattern=kind&7,phase=phase);initial=fixture(c,s);want,calls,packet=reference(initial,c,s)
   models=[Oracle(w,initial,c,entry,s).run()for w in images[:2]]
   for m in models:assert projection(m.memory,c)==projection(want,c)and m.calls==calls and m.packet==packet,(c,'semantics')
   assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace;seen.update(models[0].visits);count+=1
  if j==0:
   for actor,gate in itertools.product((0,ACTOR),(0,1,2,255)):
    c=Case(actor=actor,gate=gate);initial=fixture(c);want,calls,p=reference(initial,c)
    if not actor:
     for i in range(416):initial.pop(ACTOR+i,None)
    if gate==1 and actor:
     for i in range(384,392):initial.pop(actor+i,None)
    models=[Oracle(w,initial,c).run()for w in images[:2]]
    assert models[0].calls==models[1].calls==calls and complete(models[0])==complete(models[1]);seen.update(models[0].visits);count+=1
   for actor,record,phase,mutation in itertools.product((ACTOR,STACK+128),(EFFECT,ACTOR-20,STACK-64,STACK-60,STACK-68,STACK-40),(0,8),(0,3)):
    if record in(STACK-64,STACK-60,STACK-68,STACK-40):record+=phase
    c=Case(actor=actor,record=record,phase=phase,mutation=mutation);initial=fixture(c);want,calls,p=reference(initial,c)
    try:models=[Oracle(w,initial,c).run()for w in images[:2]]
    except AssertionError as error:raise AssertionError(('alias execution',c,str(error)))from error
    for m in models:
     assert public(m.memory)==public(want)and m.calls==calls and m.packet==p,(c,'alias')
     assert bytes(m.memory[c.record+40+i]for i in range(20))==bytes(want[c.record+40+i]for i in range(20))
    assert complete(models[0])==complete(models[1]);aliases+=1
   # Keep the rejected unshifted stack layout as an effective control: at
   # phase8 its destination is precisely the saved-RA slot. Both streams
   # overwrite that slot with the captured zero X word and reject return0.
   bad=Case(record=STACK-68,phase=8);pair=[]
   for w in images[:2]:
    m=Oracle(w,fixture(bad),bad)
    try:m.run()
    except AssertionError as error:assert error.args[0]==('unowned jump',0),error
    else:raise AssertionError('Ineffective saved-RA overwrite control')
    assert read(m.memory,STACK+bad.phase-36)==0;pair.append(m)
   assert complete(pair[0])==complete(pair[1])and pair[0].trace==pair[1].trace
   for c in(Case(actor=0),Case(gate=1),Case(allocated=False),Case(kind=10),Case(kind=15),Case(kind=17),Case(kind=31)):
    initial=fixture(c);good=Oracle(images[0],initial,c).run()
    for cut in range(good.root_accesses):
     pair=[]
     for w in images[:2]:
      m=Oracle(w,initial,c);m.root_fault=cut
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('unfired fault')
      assert m.root_accesses==cut;pair.append(m)
     assert complete(pair[0])==complete(pair[1])and pair[0].trace==pair[1].trace
     assert(pair[0].current_pc,pair[0].delay_of)==(pair[1].current_pc,pair[1].delay_of);cuts+=1;delaycuts+=pair[0].delay_of is not None
 assert len(seen&set(range(source.ENTRY,source.ENTRY+232,4)))==58
 return dict(cases=count,executions=count*2,guest_alias_cases=aliases,saved_RA_overwrite_controls=1,independent_rebases=3,visited_words=58,fault_cuts=cuts,delay_fault_cuts=delaycuts,all_four_images_equal=True,NULL_and_gate1_read_boundaries=True,provider_capture_and_narrow_arguments=True,original_guest_padding_retained=True,portable_padding_or_overlap_claim=False)

def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();connected={};descriptions=((CLASSIFY,0x13CD7C,3),(FACTORY,0x1766A4,28),(CONSTRUCTOR,0x1765E0,49),(ALLOC,0x194F18,28),(REGISTER,0x195EFC,20),(COPY,0x22EC0,11))
 for va,at,n in descriptions:
  words=list(struct.unpack_from('>%dI'%n,rom,at));assert words==list(struct.unpack_from('>%dI'%n,elf,source.elf_slot_offset(elf,va,n*4)));connected.update({va+4*i:w for i,w in enumerate(words)})
 images=[linked(o/n,'connected-%d'%i)for i,n in enumerate(('original-func_151A0A10.o','selected-final.o'))];count=0;seen=set()
 for kind,effect,variant,flags,allocated,mutation,phase,head in itertools.product((0,10,15,17,31,0xFFFFFFEF),(0,0x8000,0xFFFF),(0,255),(0,1),(False,True),(0,2),(0,8),(0,0x230000)):
  c=Case(kind=kind,effect=effect,variant=variant,flags=flags,allocated=allocated,mutation=mutation,phase=phase,head=head);initial=fixture(c);_,_,packet=reference(initial,c);models=[Oracle(w,initial,c,connected=connected).run()for w in images];m=models[0]
  assert complete(m)==complete(models[1])and m.trace==models[1].trace;seen.update(m.visits)
  expected=(half(effect),0xFFFFFFFF,1,1,0,20,variant,flags)
  assert[(a)for t,a in m.calls if t==FACTORY]==[expected]
  assert[a for t,a in m.calls if t==CONSTRUCTOR]==[(expected[0],expected[1],1,0xFFFFFFFF,1,0,20,variant,flags)]
  assert[a for t,a in m.calls if t==ALLOC]==[(35,flags,60,1,variant,1)]
  assert[a for t,a in m.calls if t==HEAP]==[(60,1,1,0,1)]
  if allocated:
   assert m.packet==m.copied==packet and bytes(m.memory[EFFECT+40+i]for i in range(20))==packet
   assert m.memory[EFFECT]==35 and m.memory[EFFECT+1]==flags&255 and m.memory[EFFECT+12]==variant
   assert read(m.memory,EFFECT+14,2)==effect&65535
   assert bytes(m.memory[EFFECT+i]for i in(13,16,17,18,19))==bytes((1,255,1,255,0))
   assert bytes(m.memory[EFFECT+i]for i in(2,3,36,37,38,39))==bytes(initial[EFFECT+i]for i in(2,3,36,37,38,39))
   assert read(m.memory,EFFECT+4)==0 and read(m.memory,EFFECT+8)==head
   assert read(m.memory,0x800DCE50+flags*0x1A0+35*4)==EFFECT
   if head:assert read(m.memory,head+4)==EFFECT
   assert all(m.memory[EFFECT+20+i]==0 for i in range(16))
   assert bytes(m.memory[EFFECT+60+i]for i in range(100))==bytes(initial[EFFECT+60+i]for i in range(100))
  else:assert not any(t in(ZERO,REGISTER,COPY)for t,a in m.calls)
  count+=1
 visits={hex(va):len(seen&set(range(va,va+n*4,4)))for va,_,n in descriptions}
 return dict(cases=count,executions=count*2,retained_helper_words=139,helper_visited_words=visits,actual_classifier_factory_constructor_allocator_registration_memcpy=True,full_header_and_payload_checked=True,empty_and_nonempty_list_insertion=True,actual_caller_list_rows=[0,1],wide_context_arguments_checked_with_opaque_factory=True,heap_and_zero_bounded=True,gameplay_acceptance_claim=False)

class CallerOracle(TimingOracle):
 def __init__(self,words,memory,entry,returned,phase=0,window=False):
  self.returned=returned;connected=None
  if window:
   rom=(o/'before-conker_conker.us.bin').read_bytes();connected=dict(zip(range(0x15029BA4,0x15029BB8,4),struct.unpack_from('>5I',rom,0x57054)))
  super().__init__(words,memory,phase=phase,entry=entry,arguments=(0x12345678,),connected=connected)
  if window:
   self.r[29]-=0x750;self.r[2]=self.r[1]=0x40
   put(self.memory,self.r[29]+0xD4,0xDEAD0000);put(self.memory,self.r[29]+0xD0,self.before[16])
 def record_call(self,t):
  assert t==source.ENTRY;args=self.arguments(4);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.returned

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
 sites=[i*4 for i,w in enumerate(ws)if w==jal];assert len(sites)==3 and 0x5666C in sites and not any(w==source.ENTRY for w in ws)
 count=0
 for va,at,effect in((0x1506FBE8,0x9D098,70),(0x1506FC1C,0x9D0CC,40)):
  words=list(struct.unpack_from('>13I',rom,at));assert words==list(struct.unpack_from('>13I',elf,source.elf_slot_offset(elf,va,52)))
  assert sum(at<=p<at+52 for p in sites)==1
  for actor,returned,phase in itertools.product((0,ACTOR),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
   m=fixture(Case());put(m,0x800D154C,actor);q=CallerOracle(words,m,va,returned,phase).run();assert q.calls==[(source.ENTRY,(actor,effect,255,0))];count+=1
 words=list(struct.unpack_from('>8I',rom,0x5665C));window_count=0
 for actor,variant,returned,phase in itertools.product((0,ACTOR),range(256),(0,0xC0DEC0DE),(0,8)):
  m=fixture(Case());sp=STACK+phase-0x750;put(m,sp+0x764,actor);m[sp+0x773]=variant
  q=CallerOracle(words,m,0x150291AC,returned,phase,True).run();assert q.calls==[(source.ENTRY,(actor,40,variant,1))]and q.r[2]==1;window_count+=1
 return dict(full_wrapper_cases=count,full_wrapper_words_each=13,wrapper_void_signatures=True,original_command_window_cases=window_count,command_window_words=8,original_parent_epilogue_words=5,command_window_overwrites_result_with1=True,full_large_parent_claim=False,aligned_JAL_sites=[hex(p)for p in sites],literal_function_pointers=0,all_four_arguments_qualified=True,shared_headers_unchanged=True)

def controls():
 b=source.SELECTED
 changes={'wrong_x':('actor + 0x14','actor + 0x18'),'wrong_z':('actor + 0x1C','actor + 0x14'),'wrong_height':('actor + 0x180','actor + 0x18'),'nonzero':('payload.zero = 0.0f','payload.zero = 1.0f'),'kind10':('case 10:\n                    payload.selected = 0','case 10:\n                    payload.selected = 1'),'kind15':('case 15:\n                case 17:','case 15:\n                    payload.selected = 0;\n                    break;\n                case 17:'),'kind17':('case 15:\n                case 17:\n                    payload.selected = 1','case 15:\n                    payload.selected = 1;\n                    break;\n                case 17:\n                    payload.selected = 0'),'gate_nonzero':('D_800C35EA != 1','D_800C35EA == 0'),'short_effect':('func_151491F4(effect,','func_151491F4((u8)effect,'),'variant0':('0x14, variant, flags','0x14, 0, flags'),'flags':('variant, flags)','variant, flags ^ 1)'),'size':('1, 1, 0, 0x14','1, 1, 0, 0x10'),'destination':('record + 0x28','record + 0x24'),'short_copy':('&payload, 0x14','&payload, 0x10')}
 out={n:b.replace(a,z)for n,(a,z)in changes.items()};assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(ActorHeightEffectPayload)==20&&__builtin_offsetof(ActorHeightEffectPayload,selected)==12&&__builtin_offsetof(ActorHeightEffectPayload,zero)==16)?1:-1];
typedef struct {u8 pad0[20];f32 x,middle,z;u8 gap20[0x160];f32 height;u32 kind;} Actor;
typedef char ActorABI[(__builtin_offsetof(Actor,height)==384&&__builtin_offsetof(Actor,kind)==388)?1:-1];
static struct{u32 pre[4];Actor actor;u32 post[4];}actualActor,expectedActor;
static union{u64 align;u8 bytes[160];}actualOutput,expectedOutput;
u8 D_800C35EA;static u32 n,scenario,allocated,mutation,phase,error;static s16 wantedEffect;static u8 wantedVariant;static s32 wantedFlags;static u8 want[20];
static const u32 floats[]={0,0x80000000u,0x3F800000u,0xC0200000u,1,0x80000001u,0x7F7FFFFFu,0x7FC12345u};
static void bytes(void*d,const void*s,u32 count){u32 i;for(i=0;i<count;i++)((u8*)d)[i]=((const u8*)s)[i];}
static void change(Actor*p){u32 v;v=0x42040000u;bytes(&p->x,&v,4);v=0xC2300000u;bytes(&p->middle,&v,4);v=0x425C0000u;bytes(&p->z,&v,4);v=0x3F000000u;bytes(&p->height,&v,4);p->kind=0x12345678u;}
u32 func_1510F8CC(u32 v){if(phase++!=0||v!=(n*0x1020304u&0xFFFFFFE0u)|(n&31u))error=1;if(mutation&1){change(&actualActor.actor);D_800C35EA=1;}return v&31;}
struct260 *func_151491F4(s16 effect,s8 death,s8 update,u8 enabled,u8 selector,s32 size,u8 variant,s32 flags){if(phase++!=1||effect!=wantedEffect||death!=-1||update!=1||enabled!=1||selector||size!=20||variant!=wantedVariant||flags!=wantedFlags)error=1;if(mutation&2){change(&actualActor.actor);D_800C35EA=1;}return allocated?(struct260*)actualOutput.bytes:NULL;}
void *memcpy(void*d,const void*s,u32 count){u32 i;const u8*b=s;if(phase++!=2||d!=actualOutput.bytes+40||count!=20){error=1;return d;}for(i=0;i<20;i++)if((i<13||i>=16)&&b[i]!=want[i])error=1;bytes(d,s,count);return d;}
'''
 # Parenthesize the complete expected classifier word before comparison.
 t=t.replace('v!=(n*0x1020304u&0xFFFFFFE0u)|(n&31u)','v!=((n*0x1020304u&0xFFFFFFE0u)|(n&31u))')
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+'\n'
 t+=r'''
typedef void(*Spawn)(u8*,s16,u8,s32);
static int one(Spawn fn,u32 gate,u32 nullActor){u32 i,v;u8 *a=(u8*)&actualActor,*e=(u8*)&expectedActor;u32 active=!nullActor&&gate!=1;
 for(i=0;i<sizeof(actualActor);i++)a[i]=e[i]=(u8)(i*13+n);for(i=0;i<160;i++)actualOutput.bytes[i]=expectedOutput.bytes[i]=(u8)(i*17+n);
 v=floats[n&7];bytes(&actualActor.actor.x,&v,4);bytes(want,&v,4);v=floats[(n+1)&7];bytes(&actualActor.actor.middle,&v,4);v=floats[(n+2)&7];bytes(&actualActor.actor.z,&v,4);bytes(want+8,&v,4);v=floats[(n+3)&7];bytes(&actualActor.actor.height,&v,4);bytes(want+4,&v,4);
 actualActor.actor.kind=(n*0x1020304u&0xFFFFFFE0u)|(n&31u);want[12]=(n&31)==15||(n&31)==17;v=0;bytes(want+16,&v,4);
 bytes(&expectedActor,&actualActor,sizeof(actualActor));if(active&&mutation){change(&expectedActor.actor);}
 wantedEffect=(s16)n;wantedVariant=(u8)(n>>8);wantedFlags=(s32)(n*0x1020304u^0x80000001u);D_800C35EA=(u8)gate;phase=error=0;
 fn(nullActor?NULL:(u8*)&actualActor.actor,wantedEffect,wantedVariant,wantedFlags);
 if(error||phase!=(active?(allocated?3:2):0)||D_800C35EA!=(active&&mutation?1:gate))return 1;
 for(i=0;i<sizeof(actualActor);i++)if(a[i]!=e[i])return 1;
 if(active&&allocated)for(i=0;i<20;i++)if(i<13||i>=16)expectedOutput.bytes[40+i]=want[i];
 for(i=0;i<160;i++)if(!(active&&allocated&&i>=53&&i<=55)&&actualOutput.bytes[i]!=expectedOutput.bytes[i])return 1;
 return 0;
}
static int check(Spawn fn){u32 gate,nullActor;
 for(n=0;n<65536;n++)for(scenario=0;scenario<8;scenario++){allocated=scenario&1;mutation=scenario>>1;if(one(fn,0,0))return 1;}
 for(n=0;n<256;n++)for(gate=0;gate<256;gate++)for(nullActor=0;nullActor<2;nullActor++){allocated=1;mutation=3;if(one(fn,gate,nullActor))return 1;}
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(%s))return %d;\n'%(name,20+i)
 return t+'return 0;}\n'+START

def native_suite():
 unit=o/'native-height.c';unit.write_text(native_harness())
 for opt in('O0','O2','O3'):
  exe=o/('native-height-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=655360,effective_controls=14,UBSan_trapping=True,all65536_effect_halfwords=True,all256_variants=True,all256_gate_values_and_NULL=True,typed_disjoint_objects=True,whole_actor_and_output_fences=True,padding_value_claim=False,captured_float_bits_and_live_provider_mutations=True)
