"""Owner/value payload, raw float representation, returned pointer and caller windows."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_owner_value_payload_match as source
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
SPAWN,COPY,ALLOC,ZERO=0x15149130,0x10022EC0,0x15167A68,0x100226F0
OWNER,OUTPUT=0x28000,0x30000;EXIT=0x15029BA4
SYMS=dict(func_15149130=SPAWN,memcpy=COPY)
FLOATS=(0,0x80000000,0x3F800000,0xBF800000,1,0x007FFFFF,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345,0xFFC12345)
EXTRA=(0,1,16,0x7FFFFFFF,0x80000000,0xFFFFFFF0,0xFFFFFFFF)
u32=lambda v:v&0xFFFFFFFF
s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 duration:int=0xABCD8000
 first:int=0xA5A50080
 second:int=0xB6B600FF
 bits:int=0x7FA12345
 extra:int=0xFFFFFFF0
 selector:int=0x76540081
 category:int=0xFEDCBA98
 outcome:bool=True
 effect:int=0
 phase:int=0
 seed:int=0xA5
def home(c):return STACK+c.phase
def args(c):return tuple(map(u32,(c.owner,c.duration,c.first,c.second,c.bits,c.extra,c.selector,c.category)))
def block(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,0x900)}
 for base,n in ((OWNER,256),(OUTPUT,256)):
  m.update({base+i:(i*29+c.seed)&255 for i in range(-32,n)})
 for i,v in enumerate(args(c)[4:],4):put(m,home(c)+4*i,v)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+0x900}
def mutate(m,c,p):
 if c.effect&1 and c.owner:put(m,c.owner+0x3B,read(m,c.owner+0x3B,1)^0x55,1)
 if c.effect&2:put(m,p+14,0x12,1);put(m,p+15,0xE7,1)
 if c.effect&4:
  for off,v in ((16,0x87654321),(20,0x12345678),(24,0xDCBA0082),(28,0x76543210)):put(m,home(c)+off,v)
def reference(initial,c,connected=False):
 m=dict(initial);p=home(c)-20
 for i,v in enumerate(args(c)[:4]):put(m,home(c)+4*i,v)
 if not c.owner:return m,[],0
 put(m,p,c.owner);put(m,p+4,0);put(m,p+8,c.bits);put(m,p+12,c.first,1);put(m,p+13,c.second,1)
 duration=s16(c.duration);request=(u32(300 if duration<0 else duration),0xFFFFFFFF,0x1B,0xFFFFFFFF,int(duration>=0),0x1B,u32(c.extra+16),c.selector&255,u32(c.category))
 calls=[(SPAWN,request)]
 if connected:calls.append((ALLOC,(35,u32(c.category),u32(c.extra+56),1,c.selector&255,1)))
 mutate(m,c,p)
 if c.outcome:
  if connected:
   for at,v,n in ((OUTPUT+14,request[0],2),(OUTPUT+16,255,1),(OUTPUT+17,0x1B,1),(OUTPUT+18,255,1),(OUTPUT+13,request[4],1),(OUTPUT+19,0x1B,1)):put(m,at,v,n)
   calls.append((ZERO,(OUTPUT+20,16)))
   for i in range(16):put(m,OUTPUT+20+i,0,1)
  calls.append((COPY,(OUTPUT+40,p,16)));packet=block(m,p,16)
  for i,v in enumerate(packet):put(m,OUTPUT+40+i,v,1)
 return m,calls,OUTPUT if c.outcome else 0
def linked(obj,label,entry=ENTRY,s=SYMS,function=F):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def helpers(s=SYMS):
 rom=(r/'conker/conker.us.bin').read_bytes();raw=struct.unpack_from('>49I',rom,0x1765E0);code={s['func_15149130']+i*4:w for i,w in enumerate(raw)};code.update(zip(range(s['memcpy'],s['memcpy']+44,4),struct.unpack_from('>11I',rom,0x22EC0)));return code
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[]
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args(c),connected=connected);self.before=self.r[:];self.saved_f=self.f[20:]
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
  counts={self.syms['func_15149130']:9,self.syms['memcpy']:3,ALLOC:6,ZERO:2,ENTRY:8};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];value=0x76543210
  if t in(self.syms['func_15149130'],ALLOC):mutate(self.memory,c,home(c)-20);value=OUTPUT if c.outcome else 0
  elif t==self.syms['memcpy']:
   assert 0<=a[2]<=64
   for i,v in enumerate(block(self.memory,a[1],a[2])):self.memory[a[0]+i]=v
   value=a[0]
  elif t==ZERO:
   assert a==(OUTPUT+20,16)
   for i in range(a[1]):self.memory[a[0]+i]=0
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=u32(value)
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses)
def check(m,initial,c,connected=False):
 want,calls,result=reference(initial,c,connected);assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,result),c
 if c.owner and c.outcome:assert block(m.memory,OUTPUT+40,16)==block(want,OUTPUT+40,16),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f
def cases():
 for n in range(256):yield Case(first=0xA5A50000|n,second=0xB6B60000|(255-n),bits=FLOATS[n%len(FLOATS)],extra=EXTRA[n%len(EXTRA)],selector=0xAA550000|n,seed=n,outcome=bool(n&1),duration=0xCCCC0000|(n if n&2 else 0x8000))
 for d,bits,outcome,effect,owner,phase in itertools.product((0x8000,0xFFFF,0,1,0x7FFF),FLOATS,(False,True),(0,7),(0,OWNER),(0,8)):yield Case(duration=d,bits=bits,outcome=outcome,effect=effect,owner=owner,phase=phase)
 for extra,outcome in itertools.product(EXTRA,(False,True)):yield Case(extra=extra,outcome=outcome,effect=7)
def guest_suite():
 for value in(0,127,128,255):
  c=Case();initial=fixture(c);put(initial,OWNER,value,1);m=Oracle([0],initial,c);m.execute(0x80820000);assert m.r[2]==u32(value-256 if value&128 else value)
 words=[linked(o/n,'guest-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert words[0]==words[1]==words[2]
 corpus=list(cases());visited=set();cuts=set()
 for c in corpus:
  initial=fixture(c);models=[]
  for w in words:
   m=Oracle(w,initial,c,connected=helpers()).run();check(m,initial,c,True);models.append(m);visited.update(m.visits)
  assert state(models[0])==state(models[1])==state(models[2]),c
 assert set(range(ENTRY,ENTRY+228,4))<=visited
 for c in(Case(owner=0),Case(duration=-1),Case(duration=0,outcome=False),Case(duration=0x8000,effect=7,phase=8)):
  initial=fixture(c);normal=Oracle(words[0],initial,c).run()
  for cut in range(normal.accesses):
   models=[]
   for w in words:
    m=Oracle(w,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    models.append(m)
   assert state(models[0])==state(models[1])==state(models[2]);cuts.add((c.owner,c.duration,cut,models[0].delay_of is not None))
 rebase=0
 for entry,spawn,copy in((0x17007FFC,0x17147FFC,0x1702FFFC),(0x2500FFFC,0x25140000,0x2502FFFC)):
  s=dict(func_15149130=spawn,memcpy=copy);ws=[linked(o/n,'rebase-'+str(entry)+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert ws[0]==ws[1]==ws[2]
  for c in(Case(),Case(owner=0),Case(duration=0x8000,effect=7),Case(duration=0,outcome=False)):
   models=[Oracle(w,fixture(c),c,entry,s).run()for w in ws];assert state(models[0])==state(models[1])==state(models[2]);rebase+=1
 return dict(cases=len(corpus),executions=len(corpus)*3,body_words=57,bindings=2,guards=0,all_target_words_exercised=True,original_allocator_words=49,original_allocator_words_visited=sum(p in visited for p in range(SPAWN,SPAWN+196,4)),original_copy_words=11,access_cuts=len(cuts),delay_cuts=sum(x[3]for x in cuts),rebase_cases=rebase,complete_cross_image_RAM_registers_trace_and_fault_context=True,padding_offsets=[14,15],raw_float_patterns=len(FLOATS),extra_size_wrap_patterns=len(EXTRA),returned_allocation_pointer_verified=True,portable_alias_or_hardware_claimed=False)
class ExitWindow(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==EXIT:self.owner.current_pc=pc;raise ExitWindow
  return super().__getitem__(pc)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ws=[linked(o/n,'caller-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0
 for entry,offset,constant,second in((0x150275FC,0x54AAC,0x80096C70,0),(0x15027638,0x54AE8,0x80096C74,1)):
  parent=list(struct.unpack_from('>15I',rom,offset))
  for d,owner,outcome,bits,phase in itertools.product((0x8000,0xFFFF,0,0x7FFF),(0,OWNER),(False,True),(0x3F800000,0x80000000,0x7FA12345),(0,8)):
   c=Case(owner=owner,duration=u32(s16(d)),first=0xFFFFFFFF,second=second,bits=bits,extra=0,selector=0xA5A50081,category=1,outcome=outcome,phase=phase);initial=fixture(c)
   for at,v in((home(c)+0x768,owner),(home(c)+0x660,d),(home(c)+0x770,c.selector),(constant,bits)):put(initial,at,v)
   models=[]
   for w in ws:
    code=helpers();code.update(zip(range(ENTRY,ENTRY+228,4),w));m=Oracle(parent,initial,c,entry=entry,connected=code);m.code=WindowCode(m.code,m)
    try:m.run()
    except ExitWindow:pass
    else:raise AssertionError('Original caller exit did not fire')
    assert m.calls[0]==(ENTRY,args(c)),(m.calls[0],args(c),c);want,calls,_=reference(initial,c,True);assert(public(m.memory),m.calls[1:],m.r[2])==(public(want),calls,1),c;models.append(m)
   assert state(models[0])==state(models[1])==state(models[2]);count+=1
 return dict(cases=count,original_windows=2,words_per_window=15,parent='func_150265CC',call_ROM=['0x54AD8','0x54B14'],exit='0x15029BA4',eight_arguments=True,return_ignored=True,original_allocator_and_copy_connected=True,full_parent_or_hardware_claimed=False)
def controls(body):
 return dict(wrong_zero=body.replace('payload.zero = 0.0f','payload.zero = value'),wrong_value=body.replace('payload.value = value','payload.value = 0.0f'),wrong_first=body.replace('payload.first = first','payload.first = second'),wrong_default=body.replace('duration = 300','duration = 301'),wrong_negative_gate=body.replace('lifetime < 0','lifetime == -1'),wrong_flag=body.replace('flags = 1','flags = 0'),wrong_kind=body.replace('duration, -1, 0x1B','duration, -1, 0x1A'),wrong_operation=body.replace('flags, 0x1B','flags, 0x1A'),wrong_extra_size=body.replace('extraBytes + sizeof(payload)','extraBytes + sizeof(payload) + 1'),wrong_length=body.replace('sizeof(payload));','sizeof(payload) - 1);'),wrong_destination=body.replace('created + 0x28','created + 0x24'),ignore_failure=body.replace('created != NULL','1'),wrong_return=body.replace('    return created;','    return created == NULL ? NULL : created + 0x28;'),wrong_null_gate=body.replace('owner == NULL','owner != NULL'))
def compiled_controls():
 receipts={};corpus=[Case(),Case(duration=0),Case(owner=0),Case(outcome=False),Case(first=0x7F,second=0x80)]
 for name,body in controls(source.SELECTED).items():
  assert body!=source.SELECTED;obj,diag=source.compile_owner(r,o,source.HEADERS+body,'control-'+name);assert not diag;words=linked(obj,'control-linked-'+name)
  for i,c in enumerate(corpus):
   initial=fixture(c);m=Oracle(words,initial,c).run()
   try:check(m,initial,c)
   except AssertionError:receipts[name]=i;break
  assert name in receipts,('Ineffective control',name)
 return dict(count=len(receipts),effective_IDO_controls=receipts,compiler_or_oracle_errors_accepted=False)

NATIVE_WORD=r'''
static u32 word(const void *p){u32 v;u8 *d=(u8 *)&v;const u8*s=p;u32 i;for(i=0;i<4;i++)d[i]=s[i];return v;}
'''
def native_harness(body):
 return source.HEADERS+body+NATIVE_WORD+r'''
typedef char payload_size_is_16[sizeof(OwnerValuePayload1368C0)==16?1:-1];
typedef char value_offset_is_8[__builtin_offsetof(OwnerValuePayload1368C0,value)==8?1:-1];
typedef char first_offset_is_12[__builtin_offsetof(OwnerValuePayload1368C0,first)==12?1:-1];
static u8 actorBytes[256] __attribute__((aligned(4))),outputBytes[256] __attribute__((aligned(4)));
static u8 captured[16],*output,selector;static s8 first,second;static s16 duration;static s32 category;
static u32 valueBits,extra;static int present,success,requests,copies,error;
__attribute__((noinline)) struct260 *func_15149130(s16 life,s8 a,s8 kind,s8 b,u8 flag,u8 operation,struct37 *size,u8 select,s32 cat) {
 requests++;
 if(!present||life!=(duration<0?300:duration)||a!=-1||kind!=0x1B||b!=-1||flag!=(duration>=0)||operation!=0x1B||(u32)size!=extra+16u||select!=selector||cat!=category)error=1;
 if(present)actorBytes[0x3B]^=0x55;
 return success?(struct260 *)output:NULL;
}
__attribute__((noinline)) void *memcpy(void *destination,const void *sourceBytes,u32 length) {
 const OwnerValuePayload1368C0*p=sourceBytes;const u8*src=sourceBytes;u8*dst=destination;u32 i;copies++;
 if(!present||!success||dst!=output+40||length!=16){error=2;return destination;}
 if(p->owner!=actorBytes||word(&p->zero)!=0||word(&p->value)!=valueBits||p->first!=first||p->second!=second)error=3;
 for(i=0;i<16;i++)captured[i]=src[i];for(i=0;i<length;i++)dst[i]=src[i];return destination;
}
static int run(void) {
 static const u32 floats[]={0,0x80000000u,0x3F800000u,0xBF800000u,1,0x007FFFFFu,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u,0x7FA12345u,0xFFC12345u};
 static const u32 sizes[]={0,1,16,0x7FFFFFFFu,0x80000000u,0xFFFFFFF0u,0xFFFFFFFFu};
 u32 n,i;int owner,out,alias;void *result;union{u32 u;f32 f;}value;
 for(n=0;n<65536;n++)for(owner=0;owner<2;owner++)for(out=0;out<2;out++)for(alias=0;alias<2;alias++) {
  present=owner;success=out;output=alias?actorBytes:outputBytes;duration=(s16)n;first=(s8)n;second=(s8)(n>>8);selector=(u8)(n>>8);category=(s32)(0xA5A50000u|n);valueBits=floats[n%12];value.u=valueBits;extra=sizes[n%7];requests=copies=error=0;
  for(i=0;i<256;i++){actorBytes[i]=(u8)(i*17+n);outputBytes[i]=(u8)(i*29+n);}
  result=func_15109ED4(owner?actorBytes:NULL,duration,first,second,value.f,extra,selector,category);
  if(error||requests!=owner||copies!=(owner&&out))return error?error:4;
  if(result!=(owner&&out?(void *)output:NULL))return 7;
  for(i=0;i<256;i++) {
   u8 expected=(u8)(i*17+n);if(owner&&i==0x3B)expected^=0x55;if(owner&&out&&alias&&i>=40&&i<56)expected=captured[i-40];if(actorBytes[i]!=expected)return 5;
   expected=(owner&&out&&!alias&&i>=40&&i<56)?captured[i-40]:(u8)(i*29+n);if(outputBytes[i]!=expected)return 6;
  }
 }
 return 0;
}
'''+START

def native_neighbor_harness():
 before=source.snapshot(r/source.BUILD)[source.SOURCE].decode();after=source.recovered_owner(before);a,b=source.function_span(after,'func_1510A344');body=after[a:b]
 a=before.index('typedef struct {\n    u8 *owner;\n    u8 ownerId;');b=before.index('extern f32 D_800A2684;',a);declarations=before[a:b]
 return source.HEADERS+declarations+'\nf32 D_800A2684,D_800A2688;\n'+body+NATIVE_WORD+r'''
static u8 actorBytes[256] __attribute__((aligned(4))),outputBytes[256] __attribute__((aligned(4))),captured[20];
static s16 duration;static u8 priority,identity;static s32 last;static int present,success,requests,copies,error;
__attribute__((noinline)) struct260 *func_15149130(s16 life,s8 a,s8 kind,s8 b,u8 flag,u8 operation,struct37 *size,u8 select,s32 category) {
 requests++;if(!present||life!=duration||a!=-1||kind!=0x1C||b!=-1||flag!=1||operation!=0x1C||(u32)size!=20||select!=priority||category!=last)error=1;
 if(present)actorBytes[0x3B]^=0x55;return success?(struct260 *)outputBytes:NULL;
}
__attribute__((noinline)) void *memcpy(void *destination,const void *sourceBytes,u32 length) {
 const OwnerFloatPayload*p=sourceBytes;const u8*src=sourceBytes;u8*dst=destination;u32 i;copies++;
 if(!present||!success||dst!=outputBytes+40||length!=20){error=2;return destination;}
 if(p->owner!=actorBytes||p->ownerId!=identity||word(&p->value0)!=0||word(&p->value1)!=0x3E50E561u||word(&p->value2)!=0x3F526E98u)error=3;
 for(i=0;i<20;i++)captured[i]=src[i];for(i=0;i<length;i++)dst[i]=src[i];return destination;
}
static int run(void) {
 static const s16 lives[]={-32768,-1,0,1,32767};u32 n,i;int owner,out;void *result;union{u32 u;f32 f;}value;
 value.u=0x3E50E561u;D_800A2684=value.f;value.u=0x3F526E98u;D_800A2688=value.f;
 for(n=0;n<256;n++)for(owner=0;owner<2;owner++)for(out=0;out<2;out++) {
  duration=lives[n%5];priority=(u8)n;identity=(u8)n;last=(s32)(0xA5A50000u|n);present=owner;success=out;requests=copies=error=0;
  for(i=0;i<256;i++){actorBytes[i]=(u8)(i*17+n);outputBytes[i]=(u8)(i*29+n);}actorBytes[0x3B]=identity;
  result=func_1510A344(owner?actorBytes:NULL,duration,priority,last);if(error||requests!=owner||copies!=(owner&&out)||result!=(owner&&out?(void *)outputBytes:NULL))return error?error:4;
  for(i=0;i<256;i++) {
   u8 expected=(i==0x3B)?identity^(owner?0x55:0):(u8)(i*17+n);if(actorBytes[i]!=expected)return 5;
   expected=owner&&out&&i>=40&&i<60?captured[i-40]:(u8)(i*29+n);if(outputBytes[i]!=expected)return 6;
  }
 }
 return 0;
}
'''+START
def native_suite():
 profiles={};neighbor={}
 for opt in('-O0','-O2','-O3'):
  for label,harness,cases in(('target',native_harness(source.SELECTED),524288),('neighbor',native_neighbor_harness(),1024)):
   p=o/('native-'+label+'-'+opt[1:]+'.c');p.write_text(harness);exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
   q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(label,opt,q.returncode,q.stdout,q.stderr)
   (profiles if label=='target'else neighbor)[opt]=dict(exit=0,cases=cases,UBSan=True)
 effective={}
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,8)and not q.stdout and not q.stderr,(name,q.returncode);effective[name]=q.returncode
 return dict(cases_per_profile=524288,all65536_duration_and_signed_byte_pairs=True,raw_float_patterns=12,extra_size_wrap_patterns=7,profiles=profiles,negative_controls=len(effective),effective_native_controls=effective,SDK32_layout=True,owner_and_output_canaries=True,all16_representation_bytes_copied=True,padding_values_not_assumed=True,returned_allocation_pointer_verified=True,owner_output_aliases=True,neighbor='func_1510A344',neighbor_cases_per_profile=1024,neighbor_profiles=neighbor,neighbor_signature_casts_qualified=True,portable_guest_alias_or_hardware_claimed=False)
