"""Literal attached payload ABI, original allocator, copy, wrapper and padding."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_attached_effect_payload_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
SPAWN,COPY,ALLOC,ZERO,INIT=0x15149130,0x10022EC0,0x15167A68,0x100226F0,0x151C9AC0
PARENT=0x150ECC00;OWNER,OUTPUT=0x28000,0x30000
SYMS=dict(func_15149130=SPAWN,memcpy=COPY)
u32=lambda v:v&0xFFFFFFFF
s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 values:tuple=(0xA5A50080,0xB6B600FF,0xC7C7007F,0xD8D800FE,0xE9E90001)
 duration:int=0x1234FFFF
 selector:int=0x76540081
 category:int=0xFEDCBA98
 identity:int=0xE1
 outcome:bool=True
 effect:int=0
 phase:int=0
 seed:int=0xA5
 alias:int=0

def home(c):return STACK+c.phase
def actor(c):return OWNER if c.alias==0 else home(c)+4-0x3B if c.alias==1 else home(c)-12-0x3B
def args(c):return(actor(c),*map(u32,c.values),u32(c.duration),u32(c.selector),u32(c.category))
def block(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,512)}
 for base,n in ((OWNER,256),(OUTPUT,256)):
  m.update({base+i:(i*29+c.seed)&255 for i in range(-32,n)})
 put(m,actor(c)+0x3B,c.identity,1)
 for i,v in enumerate(args(c)[4:],4):put(m,home(c)+i*4,v)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+512}
def mutate(m,c,p):
 if c.effect&1:put(m,actor(c)+0x3B,read(m,actor(c)+0x3B,1)^0x55,1)
 if c.effect&2:put(m,p+10,0x12,1);put(m,p+11,0xE7,1)
 if c.effect&4:
  put(m,home(c)+24,0x76540011);put(m,home(c)+28,0xDCBA0082);put(m,home(c)+32,0x87654321)
def reference(initial,c,connected=False):
 m=dict(initial);p=home(c)-12
 # Incoming a1..a3 homes are written before the owner's identity read.
 for i,v in enumerate(c.values[:3],1):put(m,home(c)+4*i,v)
 put(m,p,actor(c));identity=read(m,actor(c)+0x3B,1);put(m,p+4,identity,1)
 for i,v in enumerate(c.values):put(m,p+5+i,v,1)
 duration=s16(c.duration);request=(u32(300 if duration==-1 else duration),0xFFFFFFFF,0x5D,0xFFFFFFFF,int(duration!=-1),0x45,12,c.selector&255,u32(c.category))
 calls=[(SPAWN,request)]
 if connected:calls.append((ALLOC,(35,u32(c.category),52,1,c.selector&255,1)))
 mutate(m,c,p)
 if c.outcome:
  if connected:
   for at,v,n in ((OUTPUT+14,request[0],2),(OUTPUT+16,255,1),(OUTPUT+17,0x5D,1),(OUTPUT+18,255,1),(OUTPUT+13,request[4],1),(OUTPUT+19,0x45,1)):put(m,at,v,n)
   calls.append((ZERO,(OUTPUT+20,16)))
   for i in range(16):put(m,OUTPUT+20+i,0,1)
  calls.append((COPY,(OUTPUT+0x28,p,12)))
  packet=block(m,p,12)
  for i,v in enumerate(packet):put(m,OUTPUT+0x28+i,v,1)
 return m,calls

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>57I',sections(p.with_suffix('.elf'))['.text'][1][:228]))
def helpers(s=SYMS):
 rom=(r/'conker/conker.us.bin').read_bytes();raw=struct.unpack_from('>49I',rom,0x1765E0);code={}
 for i,w in enumerate(raw):
  if w>>26==3:
   dest=(w&0x3FFFFFF)<<2|0x10000000;assert dest in(ALLOC,ZERO),hex(dest)
  code[s['func_15149130']+i*4]=w
 code.update(zip(range(s['memcpy'],s['memcpy']+44,4),struct.unpack_from('>11I',rom,0x22EC0)))
 return code
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,parent=False):
  self.c=c;self.syms=s;self.payload_home=home(c)-(48 if parent else 0);self.cut=None;self.accesses=0;self.trace=[]
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(actor(c),c.selector,c.category)if parent else args(c),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:]
 def execute(self,word):
  if word>>26!=32:return super().execute(word)
  self.own_instruction=True
  try:
   rs,rt=(word>>21)&31,(word>>16)&31;imm=word&65535;address=u32(self.r[rs]+(imm-65536 if imm&32768 else imm));value=self.get(address,1);self.r[rt]=u32(value-256 if value&128 else value);self.r[0]=0
  finally:self.own_instruction=False
 def access(self):
  if self.own_instruction:
   if self.accesses==self.cut:raise faults.AccessBoundary
   self.accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  counts={self.syms['func_15149130']:9,self.syms['memcpy']:3,ALLOC:6,ZERO:2,INIT:3,ENTRY:9};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];value=0x76543210
  if t in(self.syms['func_15149130'],ALLOC):
   mutate(self.memory,c,self.payload_home-12);value=OUTPUT if c.outcome else 0
  elif t==self.syms['memcpy']:
   assert 0<=a[2]<=64
   for i,v in enumerate(block(self.memory,a[1],a[2])):self.memory[a[0]+i]=v
   value=a[0]
  elif t==ZERO:
   assert a==(OUTPUT+20,16)
   for i in range(a[1]):self.memory[a[0]+i]=0
  elif t==INIT:
   if c.effect&1:put(self.memory,actor(c)+0x3B,0x19,1)
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=u32(value)
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses)
def check(m,initial,c,connected=False):
 want,calls=reference(initial,c,connected);assert(public(m.memory),m.calls)==(public(want),calls),c
 if c.outcome:assert block(m.memory,OUTPUT+40,12)==block(want,OUTPUT+40,12),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f
def cases():
 for n in range(256):yield Case(values=tuple(0xA5A50000|((n+i*31)&255)for i in range(5)),identity=n,selector=0xAA550000|n,seed=n,outcome=bool(n&1),duration=(0xFFFF if n&2 else n))
 for d,outcome,effect,phase in itertools.product((0x8000,0xFFFF,0,1,0x7FFF,0xABCDFFFF,0xA5A58001),(False,True),range(8),(0,8)):yield Case(duration=d,outcome=outcome,effect=effect,phase=phase)
 for alias,outcome,seed in itertools.product((1,2),(False,True),(0xA5,0x5A)):yield Case(alias=alias,outcome=outcome,seed=seed)
def guest_suite():
 for value in (0,127,128,255):
  c=Case(identity=value);m=Oracle([0],fixture(c),c);m.execute(0x8082003B);assert m.r[2]==u32(value-256 if value&128 else value)
 words=[linked(o/n,'guest-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert words[0]==words[1]==words[2]
 corpus=list(cases());visited=set();helper_seen=set();executions=0
 for c in corpus:
  initial=fixture(c);models=[]
  for w in words:
   m=Oracle(w,initial,c,connected=helpers()).run();check(m,initial,c,True);models.append(m);executions+=1;visited.update(m.visits)
  assert state(models[0])==state(models[1])==state(models[2]),c
 root=set(range(ENTRY,ENTRY+228,4));assert root<=visited
 for c in (Case(duration=-1),Case(duration=1,outcome=False),Case(duration=0x8000,effect=7,phase=8)):
  initial=fixture(c);reference_machine=Oracle(words[0],initial,c).run()
  for cut in range(reference_machine.accesses):
   models=[]
   for w in words:
    m=Oracle(w,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    models.append(m)
   assert state(models[0])==state(models[1])==state(models[2])
   helper_seen.add((c.duration,cut,models[0].delay_of is not None))
 rebase=0
 for entry,spawn,copy in ((0x17007FFC,0x17147FFC,0x1702FFFC),(0x2500FFFC,0x25140000,0x2502FFFC)):
  s=dict(func_15149130=spawn,memcpy=copy);ws=[linked(o/n,'rebase-'+str(entry)+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert ws[0]==ws[1]==ws[2]
  for c in (Case(),Case(duration=0x8000,effect=7),Case(duration=0,outcome=False)):
   models=[Oracle(w,fixture(c),c,entry,s).run()for w in ws];assert state(models[0])==state(models[1])==state(models[2]);rebase+=1
 return dict(cases=len(corpus),executions=executions,body_words=57,bindings=2,guards=0,all_target_words_exercised=True,original_allocator_words=49,original_allocator_words_visited=sum(p in visited for p in range(SPAWN,SPAWN+196,4)),original_copy_words=11,access_cuts=len(helper_seen),delay_cuts=sum(x[2]for x in helper_seen),rebase_cases=rebase,complete_cross_image_RAM_registers_trace_and_fault_context=True,padding_offsets=[10,11],incoming_home_and_padding_aliases=True,portable_alias_or_hardware_claimed=False)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>28I',rom,0x11A0B0));ws=[linked(o/n,'caller-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0
 for n,outcome,effect,phase in itertools.product((0,127,128,255),(False,True),(0,1),(0,8)):
  c=Case(selector=0x12340000|n,outcome=outcome,effect=effect,phase=phase);initial=fixture(c);models=[]
  for w in ws:
   code=helpers();code.update(zip(range(ENTRY,ENTRY+228,4),w));m=Oracle(parent,initial,c,entry=PARENT,connected=code,parent=True).run();models.append(m)
   calls=m.calls;assert calls[0]==(INIT,(actor(c),n,u32(c.category)))and calls[1]==(ENTRY,(actor(c),0,255,0,255,4,0xFFFFFFFF,n,u32(c.category)))
   packet=block(m.memory,OUTPUT+40,12)if outcome else None
   if packet is not None:assert packet[:4]==actor(c).to_bytes(4,'big')and packet[4:10]==bytes((0x19 if effect else c.identity,0,255,0,255,4))
   assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]
  assert state(models[0])==state(models[1])==state(models[2]);count+=1
 return dict(cases=count,original_wrapper_words=28,wrapper='func_150ECC00',nine_arguments=True,return_ignored=True,original_allocator_and_copy_connected=True,full_higher_parent_or_hardware_claimed=False)
def controls(body):
 return dict(wrong_identity=body.replace('owner[0x3B]','owner[0x3A]'),wrong_first=body.replace('payload.first = first','payload.first = second'),wrong_fifth=body.replace('payload.fifth = fifth','payload.fifth = fourth'),wrong_default=body.replace('? 300 :','? 301 :'),wrong_sentinel=body.replace('duration == -1','duration == 0'),wrong_duration=body.replace('? 300 : duration','? 300 : duration + 1'),wrong_flag=body.replace('? 0 : 1','? 1 : 0'),wrong_kind=body.replace('0x5D','0x5C'),wrong_callback=body.replace('0x45','0x44'),wrong_length=body.replace('sizeof(payload));','sizeof(payload) - 1);'),wrong_destination=body.replace('effect + 0x28','effect + 0x24'),ignore_failure=body.replace('effect != NULL','1'),conditional_copy=body.replace('memcpy(effect + 0x28, &payload, sizeof(payload));','if (selector == 0) memcpy(effect + 0x28, &payload, sizeof(payload));'))
def compiled_controls():
 receipts={};corpus=[Case(),Case(duration=0x8000),Case(duration=0),Case(outcome=False),Case(values=(0x80,0xFF,0x7F,0x55,0xAA))]
 for name,body in controls(source.SELECTED).items():
  assert body!=source.SELECTED;obj,diag=source.compile_owner(r,o,source.HEADERS+body,'control-'+name);assert not diag
  text,fs,rs=parse_object(obj);info=fs[F];asm,unknown=emit_function(text,info,rs,F,SYMS);assert not unknown;p=o/('control-'+name+'-linked');p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%ENTRY+'\n'.join('%s = 0x%X;'%(n,v)for n,v in SYMS.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  words=list(struct.unpack('>%dI'%(info['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:info['size']]))
  for i,c in enumerate(corpus):
   initial=fixture(c);m=Oracle(words,initial,c).run()
   try:check(m,initial,c)
   except AssertionError:receipts[name]=i;break
  assert name in receipts,('Ineffective control',name)
 return dict(count=len(receipts),effective_IDO_controls=receipts,compiler_or_oracle_errors_accepted=False)

def native_harness(body):
 return source.HEADERS+body+r'''
typedef char payload_size_is_12[sizeof(AttachedEffectPayload1199D0)==12?1:-1];
typedef char identity_offset_is_4[__builtin_offsetof(AttachedEffectPayload1199D0,identity)==4?1:-1];
typedef char fifth_offset_is_9[__builtin_offsetof(AttachedEffectPayload1199D0,fifth)==9?1:-1];
static u8 actorBytes[256] __attribute__((aligned(4)));
static u8 outputBytes[256] __attribute__((aligned(4)));
static u8 captured[12],fields[5],identity,selector;
static s16 duration;
static s32 category;
static int success,mutation,requests,copies,error;
__attribute__((noinline)) struct260 *func_15149130(s16 life,s8 a,s8 kind,s8 b,u8 flag,u8 callback,struct37 *size,u8 select,s32 cat) {
 requests++;
 if(life!=(duration==-1?300:duration)||a!=-1||kind!=0x5D||b!=-1||flag!=(duration!=-1)||callback!=0x45||(u32)size!=12||select!=selector||cat!=category)error=1;
 if(mutation)actorBytes[0x3B]^=0x55;
 return success?(struct260 *)outputBytes:NULL;
}
__attribute__((noinline)) void *memcpy(void *destination,const void *sourceBytes,u32 length) {
 const AttachedEffectPayload1199D0 *p=sourceBytes;
 const u8 *src=sourceBytes;u8 *dst=destination;u32 i;
 copies++;
 if(!success||dst!=outputBytes+40||length!=12){error=2;return destination;}
 if(p->owner!=actorBytes||p->identity!=identity||p->first!=fields[0]||p->second!=fields[1]||p->third!=fields[2]||p->fourth!=fields[3]||p->fifth!=fields[4])error=3;
 /* Padding has no portable fixed value; verify that all representation bytes copy. */
 for(i=0;i<12;i++)captured[i]=src[i];
 for(i=0;i<length;i++)dst[i]=src[i];
 return destination;
}
static int run(void) {
 u32 n,i,k;int out,change;
 for(n=0;n<65536;n++)for(out=0;out<2;out++)for(change=0;change<2;change++) {
  duration=(s16)n;identity=(u8)(n^0xA5);selector=(u8)(n>>8);category=(s32)(0xA5A50000u|n);
  success=out;mutation=change;requests=copies=error=0;
  for(i=0;i<256;i++){actorBytes[i]=(u8)(i*17+n);outputBytes[i]=(u8)(i*29+n);}
  actorBytes[0x3B]=identity;
  for(k=0;k<5;k++)fields[k]=(u8)(n+k*31);
  func_150ECA68(actorBytes,fields[0],fields[1],fields[2],fields[3],fields[4],duration,selector,category);
  if(error||requests!=1||copies!=out)return error?error:4;
  for(i=0;i<256;i++) {
   u8 expected=(u8)(i*17+n);if(i==0x3B)expected=identity^(change?0x55:0);
   if(actorBytes[i]!=expected)return 5;
   expected=(out&&i>=40&&i<52)?captured[i-40]:(u8)(i*29+n);
   if(outputBytes[i]!=expected)return 6;
  }
 }
 return 0;
}
'''+START

def native_suite():
 profiles={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('')
  q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
  profiles[opt]=dict(exit=0,cases=262144,UBSan=True)
 controls_effective={}
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,7)and not q.stdout and not q.stderr,(name,q.returncode);controls_effective[name]=q.returncode
 return dict(cases_per_profile=262144,all65536_duration_patterns=True,profiles=profiles,negative_controls=len(controls_effective),effective_native_controls=controls_effective,SDK32_layout=True,owner_and_output_canaries=True,all12_representation_bytes_copied=True,padding_values_not_assumed=True,allocator_mutates_identity_after_capture=True,portable_alias_or_hardware_claimed=False)
