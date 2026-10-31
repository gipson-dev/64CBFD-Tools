"""Parity request and byte-copy ABI; complete guest state, bounded allocation."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests import game_actor_phase_motion_oracle as phase
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_parity_descriptor_create_match as source
r=Path.cwd();o=r/source.BUILD
ENTRY,R,O,STACK=0x151A90C0,phase.ACTOR,0x240000,phase.STACK
CREATE,COPY=0x151A8B20,0x10022EC0
SYMS=dict(func_151A8B20=CREATE,memcpy=COPY,D_800A8F58=0x800A8F58,D_800A8F5C=0x800A8F5C,D_800A8F60=0x800A8F60,D_800A8F64=0x800A8F64)
DEFINED=(0,*range(4,39))
@dataclass(frozen=True)
class Case:
 selector:int=1
 allocated:bool=True
 mode:int=0
 alias:int=0
 pattern:int=0
 phase:int=0
def constants(c):
 if c.pattern==0:
  base,data=sections(o/'before-conker_build_conker.us.elf')['.game_data']
  return tuple(int.from_bytes(data[at-base:at-base+4],'big')for at in(0x800A8F58,0x800A8F5C,0x800A8F60,0x800A8F64))
 return (0x80000000,0x7F800000,0xFF800000,0x7FC12345)if c.pattern==1 else(1,0x7F7FFFFF,0xFF7FFFFF,0xBF800000)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base,n in((R,256),(O,256)):m.update({base+i:(i*13+0x59)&255 for i in range(n)})
 for name,v in zip(tuple(SYMS)[2:],constants(c)):put(m,s[name],v)
 return m
def result(c):
 if not c.allocated:return 0
 return (O,R-128,STACK+c.phase-40-128,STACK+c.phase-48-128)[c.alias]
def effect(m,c,s,packet):
 if c.mode&1:put(m,R+24,0xDEADBEEF)
 if c.mode&2:
  for name in tuple(SYMS)[2:]:put(m,s[name],0x3F800000)
 if c.mode&4:put(m,packet+8,0xC1200000)
 if c.mode&8:m[O+128]=0xED
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+128}
def reference(initial,c,s=SYMS,root_sp=None):
 m=dict(initial);sp=STACK+c.phase-88 if root_sp is None else root_sp;packet,tag=sp+48,sp+40
 m[packet]=2;put(m,packet+4,R);parity=c.selector&1
 put(m,packet+8,read(m,s['D_800A8F58'if parity else'D_800A8F5C']))
 put(m,packet+12,read(m,s['D_800A8F60'if parity else'D_800A8F64']))
 for i in range(5):put(m,packet+16+4*i,0)
 m[packet+36]=1;m[packet+37]=255;m[packet+38]=0;m[tag]=c.selector&255
 request=bytes(m[packet+i]for i in range(40));calls=[(s['func_151A8B20'],(packet,0xFFFFFFFF,1,255,0),request)]
 effect(m,c,s,packet);allocated=result(c)
 if allocated:
  dest=(allocated+128)&0xFFFFFFFF;calls.append((s['memcpy'],(dest,tag,1),bytes((m[tag],))));m[dest]=m[tag]
 return m,calls
class TrackedCode(phase.faults.TrackedCode):
 def __getitem__(self,pc):
  prev,w=self.last_pc,self.last_word;value=super().__getitem__(pc)
  if w>>26==17 and w>>21&31==8 and pc==prev+4:self.owner.delay_of=prev
  return value
class Oracle(phase.Oracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,fault=None):
  super().__init__(w,m,c,entry,s,connected,fault);self.r[5]=self.before[5]=c.selector&0xFFFFFFFF;self.code=TrackedCode(dict(self.code),self)
 def record_call(self,t):
  if t==self.s['func_151A8B20']:
   args=tuple(self.r[4:8])+(read(self.memory,self.r[29]+16),);assert args==(self.r[29]+48,0xFFFFFFFF,1,255,0)
   value=bytes(self.memory[args[0]+i]for i in range(40));self.constructor_memory=dict(self.memory);self.constructor_sp=self.r[29]
  elif t==self.s['memcpy']:
   args=tuple(self.r[4:7]);assert args[1:]==(self.r[29]+40,1);value=bytes((self.memory[args[1]],))
  else:raise AssertionError(hex(t))
  self.calls.append((t,args,value));self.events.append(('CALL',t,args));self.observations.append((t,value))
 def hook(self,t):
  if t==self.s['func_151A8B20']:effect(self.memory,self.c,self.s,self.r[4]);value=result(self.c)
  else:
   assert t==self.s['memcpy'];value=self.r[4];self.put(value,self.memory[self.r[5]],1)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry,s):
 raw,_=payload(obj,'func_151A90C0');assert len(raw)==236
 text,fs,relocations=parse_object(obj);asm,unknown=emit_function(text,fs['func_151A90C0'],relocations,'func_151A90C0',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151A90C0','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_151A90C0.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_1D4E00.c.o'))]
 assert all(w==result[0]for w in result);return result
def compare(words,c,s=SYMS,entry=ENTRY):
 initial=fixture(c,s);want,calls=reference(initial,c,s);models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:assert public(m.memory)==public(want)and m.calls==calls,(c,'public or call mismatch',m.calls,calls)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
 return models[0]
def guest_suite():
 count=aliases=cuts=delays=0;seen=set()
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(zip(SYMS,(entry+0x10000,entry+0x20000,0x81007FFC+j*4,0x8200FFFC+j*4,0x83008000+j*4,0x8400FFFC+j*4)))
  words=images('request-rebase-'+str(j),entry,s)
  for selector,allocated,mode,pattern,sp in itertools.product((0,1,2,5,255,256,32767,0x80000000,0xFFFFFFFF,0x1234ABCD),(False,True),(0,15),(0,1,2),(0,8)):
   c=Case(selector,allocated,mode,0,pattern,sp);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if j==0:
   for alias,sp in itertools.product(range(4),(0,8)):compare(words,Case(mode=15,alias=alias,phase=sp));aliases+=1
   for index,at in enumerate((R,R+4,R+8,R+12)):
    a=dict(s,D_800A8F58=at);aw=images('request-alias-'+str(index),entry,a)
    for sp in(0,8):compare(aw,Case(mode=15,phase=sp),a,entry);aliases+=1
   for c in(Case(),Case(selector=0),Case(allocated=False),Case(mode=15,phase=8),Case(alias=2)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except phase.faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective request access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
 return dict(cases=count,executions=count*4,independent_rebases=3,reachable_words=59,compiler_words=59,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,full_state_and_access_trace_equal=True,request_bytes=40,defined_request_bytes=len(DEFINED),guest_padding_preserved=True,low_byte_payload_bytes=1,allocation_failure_and_aliases=True,hardware_FCSR_or_complete_allocator_claim=False)

import sys
g=sys.modules[__name__]
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_actor_phase_motion_oracle import WindowCode,run_window
PARENT,OTHER0,OTHER1=0x151A9060,0x1515A974,0x15012020
class Caller(g.Oracle):
 def record_call(self,t):
  if t in(g.ENTRY,OTHER0,OTHER1):
   args=(self.r[4],self.r[5]);self.calls.append((t,args,None));self.events.append(('CALL',t,args));return
  return super().record_call(t)
 def hook(self,t):
  if t not in(OTHER0,OTHER1):return super().hook(t)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 target=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target];pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==g.ENTRY]
 assert sites==[]and pointers==list(range(0x234444,0x23445C,4)),(sites,pointers)
 table=struct.unpack_from('>8I',rom,0x234444);assert table==(g.ENTRY,)*6+(OTHER0,OTHER1)
 window=list(struct.unpack_from('>24I',rom,0x1D6510));at=elf_slot_offset(before,PARENT,96);assert before[at:at+96]==rom[0x1D6510:0x1D6570]
 roots=g.images('request-parent');seen=set();cases=0
 for index,null,allocated,mode,sp,flags in itertools.product((-1,0,1,2,3,4,5,6,7,8,0x80000000,0x7FFFFFFF),(False,True),(False,True),(0,15),(0,8),(0,128)):
  c=g.Case(index&0xFFFFFFFF,allocated,mode,0,0,sp);initial=g.fixture(c);g.put(initial,g.R+24,index&0xFFFFFFFF);initial[g.R+22]=flags
  for i,t in enumerate(table):g.put(initial,0x8008F984+4*i,0 if null and i==index else t)
  prepared=dict(initial);prepared[g.R+22]|=4;valid=0<=index<8;callback=0 if not valid or null else table[index]
  if callback==g.ENTRY:want,calls=g.reference(prepared,c,root_sp=g.STACK+sp-24-88);calls=[(g.ENTRY,(g.R,index),None),*calls]
  else:want,calls=prepared,([]if callback==0 else[(callback,(g.R,index),None)])
  models=[]
  for root,poison in itertools.product(roots,(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
   code={g.ENTRY+4*i:w for i,w in enumerate(root)};m=Caller(window,initial,c,PARENT,connected=code);m.stop_pc=None;m.poison_pc=0x151A90AC;m.poison_value=poison;m.code=WindowCode(dict(m.code),m);m.run()
   assert g.public(m.memory)==g.public(want)and m.calls==calls,(index,null,allocated,mode,'caller result',m.calls,calls)
   assert m.r[2]==1 and m.r[29]==g.STACK+sp;models.append(m);seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  cases+=1
 assert set(range(PARENT,PARENT+96,4))<=seen
 return dict(cases=cases,executions=cases*16,original_parent_words=24,all_parent_words_visited=True,ignored_return_poison_values=4,callback_table='D_8008F984',callback_indices=list(range(6)),caller_always_returns_one=True,invalid_and_null_entry_controls=True,other_two_callbacks_are_bounded=True,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,hardware_or_full_gameplay_claim=False)

class Prefix(g.phase.Oracle):
 def record_call(self,t):
  assert t==g.COPY;args=tuple(self.r[4:7]);assert args==(self.r[29]+76,self.packet,40)
  value=bytes(self.memory[args[1]+i]for i in range(40));self.calls.append((t,args,value));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError('The original memcpy must execute')
def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 copy=list(struct.unpack_from('>11I',rom,0x22EC0));at=elf_slot_offset(before,g.COPY,44);assert before[at:at+44]==rom[0x22EC0:0x22EEC]
 prefix=list(struct.unpack_from('>10I',rom,0x1D5FD0));asm=(o/'before-conker_asm_1D4E00.s').read_text();block=asm.split('glabel func_151A8B20\n',1)[1].split('endlabel func_151A8B20',1)[0]
 import re
 assert prefix==[int(w,16)for w in re.findall(r'/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]{8})\s*\*/',block)][:10]
 code={g.COPY+4*i:w for i,w in enumerate(copy)};roots=g.images('request-copy-connected');cases=prefixes=0;seen=set();prefix_seen=set()
 for selector,allocated,mode,alias,sp,pattern in itertools.product((0,1,255,0xFFFFFFFF),(False,True),(0,15),range(4),(0,8),(0,1)):
  c=g.Case(selector,allocated,mode,alias,pattern,sp);initial=g.fixture(c);want,calls=g.reference(initial,c);models=[g.Oracle(w,initial,c,connected=code).run()for w in roots]
  for m in models:assert g.public(m.memory)==g.public(want)and m.calls==calls;seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  if alias==0 and not allocated:
   prefix_models=[]
   for m in models:
    packet=m.constructor_sp+48;child=Prefix(prefix,m.constructor_memory,c,g.CREATE,{},code);child.packet=packet
    child.code[g.CREATE+40]=struct.unpack_from('>I',rom,0x1D5FD0+40)[0]
    regs={4:packet,5:0xFFFFFFFF,6:1,7:255,29:m.constructor_sp,31:0x151A9188}
    child=run_window(child,g.CREATE+40,regs);destination=m.constructor_sp-168+76
    assert bytes(child.memory[destination+i]for i in range(40))==bytes(m.constructor_memory[packet+i]for i in range(40))
    assert child.calls==[(g.COPY,(destination,packet,40),bytes(m.constructor_memory[packet+i]for i in range(40)))]
    prefix_models.append(child);prefix_seen.update(child.visits)
   for m in prefix_models[1:]:assert complete(m)==complete(prefix_models[0])and m.trace==prefix_models[0].trace
   prefixes+=1
  cases+=1
 assert set(range(g.COPY,g.COPY+44,4))<=seen and set(range(g.CREATE,g.CREATE+40,4))<=prefix_seen
 return dict(cases=cases,executions=cases*4,original_memcpy_words=11,all_memcpy_words_visited=True,allocator_prefix_words=10,prefix_cases=prefixes,prefix_executions=prefixes*4,all_prefix_words_visited=True,original_request_copy_bytes=40,guest_padding_copied_verbatim=True,allocator_remainder_is_bounded=True,complete_allocator_or_hardware_claim=False)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
guest=g
text=source.HEADERS+source.SELECTED;start=text.index('/* Create a parity');headers,body=text[:start],text[start:]
prefix=r'''
typedef char packet_layout[sizeof(ParitySpawnRequest)==40&&__builtin_offsetof(ParitySpawnRequest,owner)==4&&__builtin_offsetof(ParitySpawnRequest,primary)==8&&__builtin_offsetof(ParitySpawnRequest,secondary)==12&&__builtin_offsetof(ParitySpawnRequest,enabled)==36&&__builtin_offsetof(ParitySpawnRequest,flags)==38?1:-1];
typedef char pointer_width[sizeof(void *)==4?1:-1];
static union {u32 align;u8 bytes[256];} owner,expectedOwner;
static struct {u32 first;u8 bytes[256];u32 last;} object;
static u8 expectedObject[256];static int allocated,mode,calls,copies,error;
static u32 selector,ec[4],observed[5],expectedArgs[5];static ParitySpawnRequest requestCopy,expected;
f32 D_800A8F58,D_800A8F5C,D_800A8F60,D_800A8F64;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void effect(ParitySpawnRequest *p,int isExpected){
 if(mode&1){u8 *a=isExpected?expectedOwner.bytes:owner.bytes;a[24]=0xEF;a[25]=0xBE;a[26]=0xAD;a[27]=0xDE;}
 if(mode&2){if(isExpected){ec[0]=ec[1]=ec[2]=ec[3]=0x3F800000;}else D_800A8F58=D_800A8F5C=D_800A8F60=D_800A8F64=1.0f;}
 if(mode&4)p->primary=-10.0f;
 if(mode&8){if(isExpected)expectedObject[128]=0xED;else object.bytes[128]=0xED;}
}
u8 *func_151A8B20(ParitySpawnRequest *p,s32 a,s32 b,s32 c,s32 d){
 int i;calls++;observed[0]=(u32)p->owner;observed[1]=(u32)a;observed[2]=(u32)b;observed[3]=(u32)c;observed[4]=(u32)d;
 for(i=0;i<40;i++)if(i==0||(i>=4&&i<39))((u8 *)&requestCopy)[i]=((u8 *)p)[i];
 effect(p,0);return allocated?object.bytes:(u8 *)0;
}
void *memcpy(void *dst,const void *src,size_t n){
 copies++;if(dst!=object.bytes+128||n!=1){error=1;return dst;}
 object.bytes[128]=*(const u8 *)src;return dst;
}
static void reference(void){
 int i;u32 p=selector&1;
 expected.kind=2;expected.owner=owner.bytes;expected.primary=real(ec[p?0:1]);expected.secondary=real(ec[p?2:3]);
 for(i=0;i<5;i++)expected.zero[i]=0.0f;
 expected.enabled=1;expected.mode=-1;expected.flags=0;
 expectedArgs[0]=(u32)owner.bytes;expectedArgs[1]=0xFFFFFFFF;expectedArgs[2]=1;expectedArgs[3]=255;expectedArgs[4]=0;
 effect(&expected,1);if(allocated)expectedObject[128]=(u8)selector;
}
'''
tail=r'''
static int one(u32 low,int p){
 static const u32 high[4]={0,0x80000000,0xFFFF0000,0x7FFF0000};
 static const u32 values[3][4]={{CONSTANTS},{0x80000000,0x7F800000,0xFF800000,0x7FC12345},{1,0x7F7FFFFF,0xFF7FFFFF,0xBF800000}};
 int i,pattern=(int)(low%3);ParitySpawnRequest beforeExpected;
 selector=high[p]|low;allocated=p&1;mode=(int)((low*7+(u32)p*13)&15);calls=copies=error=0;object.first=object.last=0xBAADF00D;
 for(i=0;i<256;i++){owner.bytes[i]=expectedOwner.bytes[i]=(u8)(i*13+0x59);object.bytes[i]=expectedObject[i]=(u8)(i*7+0xA5);}
 for(i=0;i<40;i++){((u8 *)&requestCopy)[i]=0xA5;((u8 *)&expected)[i]=0xA5;}
 for(i=0;i<4;i++)ec[i]=values[pattern][i];
 D_800A8F58=real(ec[0]);D_800A8F5C=real(ec[1]);D_800A8F60=real(ec[2]);D_800A8F64=real(ec[3]);
 reference();
 beforeExpected=expected;
 /* The provider observes the request before its own mutation. */
 if(mode&4)beforeExpected.primary=real(values[pattern][(selector&1)?0:1]);
 func_151A90C0(owner.bytes,(s32)selector);
 if(calls!=1||copies!=allocated||error||object.first!=0xBAADF00D||object.last!=0xBAADF00D)return 1;
 for(i=0;i<5;i++)if(observed[i]!=expectedArgs[i])return 1;
 for(i=0;i<40;i++)if((i==0||(i>=4&&i<39))&&((u8 *)&requestCopy)[i]!=((u8 *)&beforeExpected)[i])return 1;
 for(i=0;i<256;i++)if(owner.bytes[i]!=expectedOwner.bytes[i]||object.bytes[i]!=expectedObject[i])return 1;
 if(word(D_800A8F58)!=ec[0]||word(D_800A8F5C)!=ec[1]||word(D_800A8F60)!=ec[2]||word(D_800A8F64)!=ec[3])return 1;
 return 0;
}
static int run(void){u32 low;int p;for(low=0;low<65536;low++)for(p=0;p<4;p++)if(one(low,p))return 1;return 0;}
'''
tail=tail.replace('CONSTANTS',','.join('0x%Xu'%v for v in guest.constants(guest.Case())))
def harness(b):return headers+prefix+b+tail+START
controls={
 'wrong_kind':body.replace('request.kind = 2','request.kind = 3'),
 'missing_owner':body.replace('request.owner = owner','request.owner = NULL'),
 'wrong_parity_bit':body.replace('selector & 1','(selector >> 1) & 1'),
 'wrong_primary_pair':body.replace('parity ? D_800A8F58 : D_800A8F5C','parity ? D_800A8F5C : D_800A8F58'),
 'wrong_secondary_pair':body.replace('parity ? D_800A8F60 : D_800A8F64','parity ? D_800A8F64 : D_800A8F60'),
 'nonzero_tail':body.replace('request.zero[4] = 0.0f','request.zero[4] = 1.0f'),
 'disabled_request':body.replace('request.enabled = 1','request.enabled = 0'),
 'wrong_mode':body.replace('request.mode = -1','request.mode = 0'),
 'wrong_flags':body.replace('request.flags = 0','request.flags = 1'),
 'wrong_tag_byte':body.replace('tag[0] = selector','tag[0] = selector >> 8'),
 'wrong_lifetime':body.replace('&request, -1, 1, 0xFF, 0','&request, 0, 1, 0xFF, 0'),
 'wrong_option':body.replace('&request, -1, 1, 0xFF, 0','&request, -1, 0, 0xFF, 0'),
 'wrong_final_option':body.replace('&request, -1, 1, 0xFF, 0','&request, -1, 1, 0xFF, 1'),
 'wrong_copy_destination':body.replace('created + 0x80','created + 0x81'),
 'missing_copy':body.replace('if (created != NULL)','if (0 && created != NULL)')}
def native_suite():
 results=[]
 for name,b,opt,negative in [('positive-'+opt,body,opt,False)for opt in ('-O0','-O2','-O3')]+[(n,b,'-O2',True)for n,b in controls.items()]:
  assert not negative or b!=body,name
  p=o/('native-'+name+'.c');p.write_text(harness(b));exe=p.with_suffix('');cmd=native_command(opt)+['-Wno-unused-but-set-variable','-o',str(exe),str(p)]
  q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==(1 if negative else 0),(name,q.returncode,q.stderr);results.append(dict(name=name,optimization=opt,control=negative,exit=q.returncode))
 q=dict(complete=True,positive_cases_each=262144,profiles=['O0','O2','O3'],effective_controls=len(controls),controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all65536_low_selector_values=True,defined_request_bytes=36,padding_bytes_not_fixed=True,allocation_failure_and_success=True,complete_owner_output_and_provider_log=True,canaries_checked=True,nonfinite_global_bits_preserved=True,portable_alias_or_hardware_FCSR_claim=False,results=results)
 return q
