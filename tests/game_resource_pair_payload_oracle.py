"""Resource-pair payload: opaque storage, exact guest copy, and bounded ABI probes."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.experiments import game_resource_pair_payload_match as source
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
LOOKUP,CTOR,COPY,TONE,RECORD,ALLOC,REGISTER,ZERO,HEAP=0x15083E90,0x15149130,0x10022EC0,0x800AA418,0x240000,0x15167A68,0x15168A4C,0x100226F0,0x10003C6C
SYMS=dict(func_15083E90=LOOKUP,func_15149130=CTOR,memcpy=COPY,D_800AA418=TONE)
FLOATS=(0,0x80000000,0x3F666666,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345)
POOL=0x800CC2D0
@dataclass(frozen=True)
class Case:
 effect:int=0x8000
 variant:int=255
 flags:int=0
 allocated:bool=True
 resources:int=3
 mutation:int=0
 pattern:int=0
 phase:int=0
 record:int=RECORD
 head:int=0

def half(v):return(((v&65535)^32768)-32768)&0xFFFFFFFF
def fixture(c=Case(),s=SYMS,pool=False,shape=0):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,2048)}
 m.update({c.record+i:(i*13+0x59)&255 for i in range(-16,1536)})
 put(m,s['D_800AA418'],FLOATS[c.pattern%8])
 if pool:
  m.update({POOL+i:0xA5 for i in range(26*0x32C)})
  for i in range(26):put(m,POOL+i*0x32C,0);m[POOL+i*0x32C+0x3B]=0
  if shape:
   a,b=((shape-1)%26,25-(shape-1)%26)
   put(m,POOL+a*0x32C,1);m[POOL+a*0x32C+0x3B]=23
   put(m,POOL+b*0x32C,0x80000000);m[POOL+b*0x32C+0x3B]=22
  if shape==27:
   # An inactive earlier match is skipped; the earliest active duplicate wins.
   put(m,POOL,0);m[POOL+0x3B]=23
   for i,key in ((1,23),(24,22),(25,23)):put(m,POOL+i*0x32C,1);m[POOL+i*0x32C+0x3B]=key
  put(m,0x800DCE50+(c.flags&255)*0x1A0+35*4,c.head)
  if c.head:m.update({c.head+i:(i*7+0x69)&255 for i in range(32)})
 return m
def pair(c):return (0x280000 if c.resources&1 else 0,0x290000 if c.resources&2 else 0)
def pool_lookup(m,key):
 if not key:return 0
 return next((POOL+i*0x32C for i in range(26)if read(m,POOL+i*0x32C) and m[POOL+i*0x32C+0x3B]==key),0)
def mutate(m,c,s,when):
 if when==1:
  if c.mutation&1:put(m,s['D_800AA418'],0x3F123456)
  if c.mutation&4:m[STACK+c.phase-36]=0
 elif when==2 and c.mutation&2:put(m,s['D_800AA418'],0x42C80000)
def copy_bytes(m,d,s,n):
 for i in range(n):m[d+i]=m[s+i]
def reference(initial,c,s=SYMS,pool=False):
 m=dict(initial);p=STACK+c.phase-1456;calls=[]
 m[p+0x584]=23;m[p+0x58C]=22
 calls.append((s['func_15083E90'],(23,)));first=pool_lookup(m,23)if pool else pair(c)[0];mutate(m,c,s,1);put(m,p+0x580,first)
 key=m[p+0x58C];calls.append((s['func_15083E90'],(key,)));second=pool_lookup(m,key)if pool else(pair(c)[1]if key==22 else 0);put(m,p+0x588,second)
 for at,v in ((0x590,0x41900000),(0x594,0),(0x598,0x437A0000),(0x59C,0x3B83126F),(0x5A0,read(m,s['D_800AA418']))):put(m,p+at,v)
 calls.append((s['func_15149130'],(half(c.effect),0xFFFFFFFF,0xFFFFFFFF,1,1,21,1448,c.variant&255,c.flags&0xFFFFFFFF)))
 mutate(m,c,s,2);packet=bytes(m[p+i]for i in range(1448));returned=0
 if c.allocated:
  put(m,STACK+c.phase-4,c.record);calls.append((s['memcpy'],(c.record+40,p,1448)));copy_bytes(m,c.record+40,p,1448);returned=read(m,STACK+c.phase-4)
 return m,calls,packet,returned
def public(m):return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+2048}

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  self.c,self.s,self.trace,self.packet=c,s,[],None
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.effect&0xFFFFFFFF,c.variant&0xFFFFFFFF,c.flags&0xFFFFFFFF),connected=connected)
  self.root_fault=fault
 def execute(self,w):
  if w>>26==32:
   off=((w&65535)^32768)-32768;v=self.get((self.r[w>>21&31]+off)&0xFFFFFFFF,1);self.r[w>>16&31]=((v^128)-128)&0xFFFFFFFF
  else:super().execute(w)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  sizes={self.s['func_15083E90']:1,self.s['func_15149130']:9,self.s['memcpy']:3,ALLOC:6,REGISTER:2,ZERO:2,HEAP:5}
  assert t in sizes,hex(t);args=self.arguments(sizes[t]);self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.s['memcpy']:self.packet=bytes(self.memory[args[1]+i]for i in range(1448))
 def hook(self,t):
  c,s=self.c,self.s;args=self.calls[-1][1];result=0
  if t==s['func_15083E90']:
   index=sum(t0==t for t0,a in self.calls)-1
   result=pair(c)[index]if args[0]in(23,22)else 0
   if index==0:mutate(self.memory,c,s,1)
  elif t in(s['func_15149130'],HEAP):mutate(self.memory,c,s,2);result=c.record if c.allocated else 0
  elif t==s['memcpy']:copy_bytes(self.memory,*args);result=0x12345678
  elif t==ZERO:
   for i in range(args[1]):self.memory[args[0]+i]=0
  else:assert t==REGISTER
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def compare(images,c,s=SYMS,entry=source.ENTRY):
 initial=fixture(c,s);want,calls,packet,returned=reference(initial,c,s);models=[Oracle(w,initial,c,entry,s).run()for w in images[:2]]
 for m in models:
  assert public(m.memory)==public(want) and m.calls==calls and m.r[2]==returned,(c,'state')
  if c.allocated:
   assert m.packet==packet and bytes(m.memory[c.record+40+i]for i in range(1448))==bytes(want[c.record+40+i]for i in range(1448)),(c,'copy')
 assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace
 return models[0]
def guest_suite():
 count=aliases=cuts=delaycuts=0;seen=set()
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(func_15083E90=entry+0x10000,func_15149130=entry+0x20000,memcpy=entry+0x30000,D_800AA418=0x81008000+j*0x10000)
  images=[linked(o/n,'pair-rebase-%d-%d'%(j,k),entry,s)for k,n in enumerate(('original-func_151B5240.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_1E26F0.c.o'))];assert all(w==images[0]for w in images)
  for effect,variant,flags,allocated,mutation,phase in itertools.product((0,0x8000,0xFFFF,0x12348001),(0,255,0xABC00180),(0,0x80000000,0xFFFFFFFF),(False,True),(0,1,2,4),(0,8)):
   c=Case(effect,variant,flags,allocated,(effect+variant)&3,mutation,(effect+variant+flags)%8,phase);m=compare(images,c,s,entry);seen.update(m.visits);count+=1
  if j==0:
   for v in range(256):
    c=Case(variant=0x12340000|v,pattern=v%8);m=compare(images,c);seen.update(m.visits);count+=1
   for offset,phase,mutation in itertools.product((0,4,8),(0,8),(0,1,2,4)):
    c=Case(record=STACK+phase-1496+offset,phase=phase,mutation=mutation);compare(images,c);aliases+=1
   bad=Case(record=STACK-1500);pair_models=[]
   for w in images[:2]:
    m=Oracle(w,fixture(bad),bad)
    try:m.run()
    except AssertionError as error:assert error.args[0][0]=='unowned jump',error
    else:raise AssertionError('Ineffective overwritten saved-RA control')
    pair_models.append(m)
   assert complete(pair_models[0])==complete(pair_models[1])
   for c in (Case(),Case(allocated=False),Case(phase=8),Case(allocated=False,phase=8)):
    initial=fixture(c);good=Oracle(images[0],initial,c).run()
    for cut in range(good.root_accesses):
     pair_models=[]
     for w in images[:2]:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective resource-pair prefix cut')
      pair_models.append(m)
     a,b=pair_models;assert complete(a)==complete(b) and a.trace==b.trace and (a.current_pc,a.delay_of)==(b.current_pc,b.delay_of);cuts+=1;delaycuts+=a.delay_of is not None
 assert len(seen)==58*3
 return dict(cases=count,executions=count*2,all_four_images_equal=True,independent_rebases=3,visited_words=58,guest_alias_cases=aliases,original_pointer_spill_lifetime=True,saved_RA_overwrite_controls=1,fault_cuts=cuts,delay_fault_cuts=delaycuts,all256_variants=True,seeded_full1448_byte_copy=True,portable_uninitialized_value_claim=False,portable_overlap_or_FCSR_claim=False)

def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();descriptions=((LOOKUP,0xB1340,72),(CTOR,0x1765E0,49),(ALLOC,0x194F18,28),(REGISTER,0x195EFC,20),(COPY,0x22EC0,11));connected={}
 for va,at,n in descriptions:
  words=list(struct.unpack_from('>%dI'%n,rom,at));assert words==list(struct.unpack_from('>%dI'%n,elf,source.elf_slot_offset(elf,va,n*4)));connected.update({va+4*i:w for i,w in enumerate(words)})
 images=[linked(o/n,'pair-connected-%d'%i)for i,n in enumerate(('original-func_151B5240.o','selected-final.o'))];count=0;seen=set()
 for shape,effect,variant,flags,allocated,phase in itertools.product(range(28),(0x8000,0xFFFF),(0,255),(0,1),(False,True),(0,8)):
  c=Case(effect,variant,flags,allocated,pattern=shape%8,phase=phase,head=0x230000 if shape&1 else 0);initial=fixture(c,pool=True,shape=shape);want,calls,packet,returned=reference(initial,c,pool=True);models=[Oracle(w,initial,c,connected=connected).run()for w in images];a,b=models
  assert complete(a)==complete(b) and a.trace==b.trace;seen.update(a.visits)
  assert [row for row in a.calls if row[0]in(LOOKUP,CTOR,COPY)]==calls
  assert [args for t,args in a.calls if t==ALLOC]==[(35,flags,1488,1,variant,1)]
  assert [args for t,args in a.calls if t==HEAP]==[(1488,1,1,0,1)]
  assert a.r[2]==returned
  if allocated:
   assert a.packet==packet and bytes(a.memory[RECORD+40+i]for i in range(1448))==packet
   assert a.memory[RECORD]==35 and a.memory[RECORD+1]==flags and a.memory[RECORD+12]==variant and read(a.memory,RECORD+14,2)==effect
   assert bytes(a.memory[RECORD+i]for i in(13,16,17,18,19))==bytes((1,255,255,1,21))
   assert read(a.memory,RECORD+4)==0 and read(a.memory,RECORD+8)==c.head and read(a.memory,0x800DCE50+flags*0x1A0+35*4)==RECORD
   assert all(a.memory[RECORD+20+i]==0 for i in range(16))
   assert bytes(a.memory[RECORD+1488+i]for i in range(48))==bytes(initial[RECORD+1488+i]for i in range(48))
  else:assert not any(t in(ZERO,REGISTER,COPY)for t,args in a.calls)
  count+=1
 visits={hex(va):len(seen&set(range(va,va+n*4,4)))for va,at,n in descriptions}
 return dict(cases=count,executions=count*2,retained_helper_words=180,helper_visited_words=visits,original_lookup_constructor_allocator_registration_memcpy=True,all26_resource_slots_and_inactive_duplicates=True,constructor_size_word=1448,actual_heap_request=1488,full_header_and_seeded_payload_checked=True,heap_and_zero_bounded=True,portable_legacy_pointer_spelling_claim=False,gameplay_or_hardware_claim=False)

class CallerOracle(TimingOracle):
 def __init__(self,words,memory,returned,phase,base,previous,enabled):
  self.returned=returned;rom=(o/'before-conker_conker.us.bin').read_bytes();epilogue=dict(zip(range(0x15029BA4,0x15029BB8,4),struct.unpack_from('>5I',rom,0x57054)))
  super().__init__(words,memory,phase=phase,entry=0x15027DC4,arguments=(0,),connected=epilogue)
  self.r[29]-=0x750;self.r[16]=0x280000;self.r[2]=base;put(self.memory,self.r[29]+0xD4,0xDEAD0000);put(self.memory,self.r[29]+0xD0,self.before[16]);put(self.memory,self.r[29]+0x75C,previous);self.memory[self.r[16]+4]=enabled
 def execute(self,w):
  if w>>26==32:
   off=((w&65535)^32768)-32768;v=self.get((self.r[w>>21&31]+off)&0xFFFFFFFF,1);self.r[w>>16&31]=((v^128)-128)&0xFFFFFFFF
  else:super().execute(w)
 def record_call(self,t):
  assert t==source.ENTRY;args=self.arguments(3);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.returned
def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);sites=[i*4 for i,w in enumerate(ws)if w==jal];assert sites==[0x5529C] and not any(w==source.ENTRY for w in ws)
 words=list(struct.unpack_from('>14I',rom,0x55274));count=0
 for base,previous,enabled,variant,returned,phase in itertools.product((0,0x8000,0xFFFFFFFF),(0,1,0xFFFFFFFE),(0,1,255),(0,255),(0,0xC0DEC0DE),(0,8)):
  memory=fixture();memory[STACK+phase-0x750+0x773]=variant;m=CallerOracle(words,memory,returned,phase,base,previous,enabled).run();effect=5000 if enabled else(base-previous)&0xFFFFFFFF
  assert m.calls==[(source.ENTRY,(half(effect),variant,0))] and m.r[2]==1;count+=1
 return dict(cases=count,original_window_words=14,original_parent_epilogue_words=5,all_three_arguments_checked=True,result_overwritten_with1=True,aligned_JAL_sites=[hex(x)for x in sites],aligned_literal_pointers=0,full_large_parent_claim=False)

def controls():
 b=source.SELECTED
 changes={'id23':('entries[0].id = 23','entries[0].id = 24'),'id22':('entries[1].id = 22','entries[1].id = 21'),'lookup23':('func_15083E90(23)','func_15083E90(24)'),'lookup22':('func_15083E90(payload.entries[1].id)','func_15083E90(23)'),'extent':('250.0f','125.0f'),'height':('18.0f','19.0f'),'zero':('payload.zero = 0.0f','payload.zero = 1.0f'),'factor':('payload.factor = D_800AA418','payload.factor = 0.0f'),'inverse':('1.0f / payload.extent','2.0f / payload.extent'),'effect':('func_15149130(effect,','func_15149130((u8)effect,'),'variant':('0x5A8, variant, flags','0x5A8, 0, flags'),'flags':('variant, flags)','variant, flags ^ 1)'),'size':('21, 0x5A8','21, 0x5A4'),'destination':('record + 0x28','record + 0x24'),'copy_length':('&payload, 0x5A8','&payload, 0x5A4'),'null_return':('return record;','return NULL;'),'skip_copy':('if (record != NULL)','if (0 && record != NULL)')}
 result={name:b.replace(a,z)for name,(a,z)in changes.items()};assert all(x!=b for x in result.values());return result
def native_harness():
 t=source.HEADERS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(ResourcePairPayload)==1448&&__builtin_offsetof(ResourcePairPayload,entries)==0x580&&__builtin_offsetof(ResourcePairPayload,height)==0x590&&__builtin_offsetof(ResourcePairPayload,factor)==0x5A0)?1:-1];
static u32 n,scenario,phase,error,wantedEffect,wantedVariant,wantedFlags,captured;
static u8 resources[2][32];static union{u64 align;u8 bytes[1536];}output;
f32 D_800AA418;
static u32 word(f32 f){u32 v;__builtin_memcpy(&v,&f,4);return v;}
static f32 real(u32 v){f32 f;__builtin_memcpy(&f,&v,4);return f;}
u8 *func_15083E90(u8 id){u32 index=phase++;if(index>1||id!=(index?22:23))error=1;if(!index&&(scenario&4))D_800AA418=real(0x3F123456u);return scenario&2?resources[index&1]:NULL;}
void *func_15149130(s16 effect,s8 death,s8 update,s8 state,u8 enabled,u8 kind,s32 size,u8 variant,s32 flags){if(phase++!=2||effect!=(s16)wantedEffect||death!=-1||update!=-1||state!=1||enabled!=1||kind!=21||size!=1448||variant!=wantedVariant||(u32)flags!=wantedFlags)error=1;captured=word(D_800AA418);D_800AA418=real(0x42C80000u);return scenario&1?output.bytes:NULL;}
void *memcpy(void*d,const void*s,u32 count){const ResourcePairPayload*p=s;u32 i;u8 *dst=d;const u8*src=s;
 if(phase++!=3||d!=output.bytes+40||count!=1448){error=1;return d;}
 if(p->entries[0].resource!=(scenario&2?resources[0]:NULL)||p->entries[1].resource!=(scenario&2?resources[1]:NULL)||p->entries[0].id!=23||p->entries[1].id!=22||word(p->height)!=0x41900000u||word(p->zero)||word(p->extent)!=0x437A0000u||word(p->inverseExtent)!=0x3B83126Fu||word(p->factor)!=captured)error=1;
 /* The native ABI probe observes and transfers initialized fields only.
    The original complete copy is separately executed in the guest suite. */
 {static const u16 offsets[]={0x580,0x581,0x582,0x583,0x584,0x588,0x589,0x58a,0x58b,0x58c,0x590,0x591,0x592,0x593,0x594,0x595,0x596,0x597,0x598,0x599,0x59a,0x59b,0x59c,0x59d,0x59e,0x59f,0x5a0,0x5a1,0x5a2,0x5a3};for(i=0;i<30;i++)dst[offsets[i]]=src[offsets[i]];}
 return resources[0];}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,name)+'\n'
 t+=r'''
typedef void*(*Create)(s16,u8,s32);
static const u32 floats[]={0,0x80000000u,0x3F666666u,0xC0200000u,1,0x80000001u,0x7F7FFFFFu,0x7FC12345u};
static int check(Create fn){u32 i;for(n=0;n<65536;n++)for(scenario=0;scenario<8;scenario++){
 void*ret;u32 factor=floats[n&7];wantedEffect=n;wantedVariant=(u8)(n>>8);wantedFlags=n*0x1020304u^0x80000001u;D_800AA418=real(factor);phase=error=0;
 for(i=0;i<40;i++)output.bytes[i]=0xA5;for(i=1488;i<1536;i++)output.bytes[i]=0x5A;
 ret=fn((s16)n,(u8)wantedVariant,(s32)wantedFlags);
 if(error||phase!=(scenario&1?4:3)||ret!=(scenario&1?output.bytes:NULL))return 1;
 if(captured!=((scenario&4)?0x3F123456u:factor)||word(D_800AA418)!=0x42C80000u)return 1;
 for(i=0;i<40;i++)if(output.bytes[i]!=0xA5)return 1;for(i=1488;i<1536;i++)if(output.bytes[i]!=0x5A)return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(%s))return %d;\n'%(name,20+i)
 return t+'return 0;}\n'+START
def native_suite():
 unit=o/'native-resource-pair.c';unit.write_text(native_harness())
 for opt in ('O0','O2','O3'):
  exe=o/('native-resource-pair-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=524288,effective_controls=17,UBSan_trapping=True,all65536_effect_halfwords=True,all256_variants=True,all_initialized_payload_fields_checked=True,provider_mutation_capture=True,return_pointer_and_fences=True,memcpy_native_probe_initialized_fields_only=True,portable_uninitialized_or_overlap_claim=False)
