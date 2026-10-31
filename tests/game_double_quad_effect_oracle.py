"""Two quad UV blocks, narrowed fields, failed allocation and original origin writer."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_double_quad_effect_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.game_animation_timeline_oracle import bits
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
ALLOC,ORIGIN,GLOBAL,OUTPUT,MARK,ACTOR,FACTOR=0x15167A68,0x1517E05C,0x800DD470,0x28000,0x70000,0x60000,0x8009A104
SYMS=dict(func_15167A68=ALLOC,func_1517E05C=ORIGIN,D_800DD470=GLOBAL)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 values:tuple=(0xAABBCCDD,0x12345678,0x87654321,0xFEDCBA98,0x7FFFFFFF,0x80000000,0x12340081,0xFEDCBA82,0xABCDEF83,0xF00DCAFE)
 outcome:bool=True
 effect:int=1
 phase:int=0
 seed:int=0
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2048)}
 for base,n in ((OUTPUT-32,640),(MARK,32),(ACTOR-32,768),(s['D_800DD470']-8,32)):
  m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(n)})
 for i,v in enumerate(c.values[4:],4):put(m,STACK+c.phase+4*i,v)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def effects(m,c,home):
 put(m,MARK,0x12345678)
 if c.effect&1:put(m,OUTPUT+4,0x78,1);put(m,OUTPUT+0x92,0xE2,1)
 if c.effect&2:
  for i,v in enumerate(c.values):put(m,home+4*i,u32(v^0xAA55FF00^(i*0x01020304)))
def fields(m,c,values,s=SYMS):
 put(m,OUTPUT+0x95,2,1)
 for base in (0,0x40):
  for off,v in ((0x18,0x2000),(0x1A,0x2000),(0x28,0x2800),(0x2A,0x2000),(0x38,0x2800),(0x3A,0x2800),(0x48,0x2000),(0x4A,0x2800)):put(m,OUTPUT+base+off,v,2)
 for off,v,n in ((0x9E,1,2),(0x92,values[6],1),(0x93,values[6],1),(0x98,values[2],2),(0x9A,values[3],2),(0x9C,values[4],2),(0x96,values[5],2),(0x94,values[7],1),(0xA0,values[0],1),(0xA1,values[1],1)):put(m,OUTPUT+off,v,n)
 for i,v in enumerate(values[2:5]):put(m,s['D_800DD470']+2*i,v,2)
def reference(initial,c,s=SYMS,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial)
 for i,v in enumerate(c.values[:4]):put(m,home+4*i,v)
 calls=[(s['func_15167A68'],(4,u32(c.values[9]),168,1,c.values[8]&255,1))];effects(m,c,home)
 if c.outcome:
  values=tuple(read(m,home+4*i)for i in range(10));fields(m,c,values,s);calls.append((s['func_1517E05C'],tuple(values[2:5])))
 return m,calls
def linked(obj,label,entry=ENTRY,s=SYMS,function=F):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def origin_object():
 text=(r/'conker/asm/1A89B0.s').read_text();a=text.index('glabel func_1517E05C');b=text.index('endlabel func_1517E05C',a);p=o/'original-origin.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.section .text\n'+text[a:b]+'.size func_1517E05C, . - func_1517E05C\n');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
def origin_code(s=SYMS,label='origin'):
 words=linked(origin_object(),label,s['func_1517E05C'],s,'func_1517E05C');assert len(words)==7
 if s==SYMS:assert struct.pack('>7I',*words)==(r/'conker/conker.us.bin').read_bytes()[0x1AB50C:0x1AB528]
 return dict(zip(range(s['func_1517E05C'],s['func_1517E05C']+28,4),words))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,args=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=c.values if args is None else args)
 def record_call(self,t):
  counts={self.syms['func_15167A68']:6,self.syms['func_1517E05C']:3,ENTRY:10};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==self.syms['func_15167A68'];c=self.case;effects(self.memory,c,self.target_home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=OUTPUT if c.outcome else 0
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses)
def observable(m):return(m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.r[16:24],m.r[28:32],m.f[20:])
def check(m,initial,c,s=SYMS,home=None):
 want,calls=reference(initial,c,s,home);assert(public(m.memory),m.calls)==(public(want),calls),c
def cases():
 base=Case().values
 for n in range(256):yield Case(values=tuple(u32(v^(n*(2*i+1)))for i,v in enumerate(base)),outcome=bool(n&1),effect=n%4,phase=8 if n&2 else 0,seed=n)
 for field,value,outcome,effect,phase in itertools.product(range(10),(0,1,0x7F,0x80,0xFF,0x7FFF,0x8000,0xFFFF,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(False,True),(0,1,3),(0,8)):
  values=list(base);values[field]=value;yield Case(values=tuple(values),outcome=outcome,effect=effect,phase=phase)
def guest_suite():
 objects=('original-'+F+'.o','qualified-padded.o','selected-final.o');ws=[linked(o/n,'guest-'+str(i))for i,n in enumerate(objects)];assert ws[0]==ws[1]and ws[0]!=ws[2];helper=origin_code();visited=set();corpus=list(cases());raw_different=False
 for c in corpus:
  initial=fixture(c);ms=[]
  for w in ws:m=Oracle(w,initial,c,connected=helper).run();check(m,initial,c);ms.append(m);visited.update(m.visits)
  assert state(ms[0])==state(ms[1]);assert observable(ms[0])==observable(ms[2]);raw_different|=ms[0].r!=ms[2].r
 assert set(range(ENTRY,ENTRY+236,4))<=visited and set(helper)<=visited and raw_different;cuts=delays=0
 for c in (Case(outcome=False),Case(),Case(effect=3,phase=8)):
  initial=fixture(c);normal=Oracle(ws[0],initial,c,connected=helper).run()
  for cut in range(normal.all_accesses):
   ms=[]
   for w in ws:
    m=Oracle(w,initial,c,connected=helper);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    ms.append(m)
   assert state(ms[0])==state(ms[1]);assert observable(ms[0])==observable(ms[2]);assert(ms[0].current_pc,ms[0].delay_of)==(ms[2].current_pc,ms[2].delay_of);cuts+=1;delays+=ms[0].delay_of is not None
 rebase=0
 for entry,alloc,origin,global_address in ((0x17007FFC,0x17168000,0x1717FFFC,0x802D7FFC),(0x2500FFFC,0x25168000,0x25170000,0x803D8000)):
  s=dict(func_15167A68=alloc,func_1517E05C=origin,D_800DD470=global_address);programs=[linked(o/n,'rebase-'+str(entry)+'-'+str(i),entry,s)for i,n in enumerate(objects)];helper=origin_code(s,'origin-'+str(entry))
  for c in (Case(),Case(outcome=False),Case(effect=3,phase=8)):
   initial=fixture(c,s);ms=[Oracle(w,initial,c,entry,s,helper).run()for w in programs]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])and observable(ms[0])==observable(ms[2]);rebase+=1
 return dict(cases=len(corpus),normalized_executions=2*len(corpus),raw_executions=len(corpus),body_words=59,guards=30,bindings=2,all_target_and_origin_words_exercised=True,original_origin_words=7,access_cuts=cuts,delay_cuts=delays,rebase_cases=rebase,raw_complete_RAM_preserved_registers_and_trace_equal=True,dead_caller_saved_registers_not_equal=True,guest_incoming_home_mutation=True,allocation_failure_preserves_constructor_outputs=True,portable_guest_home_mutation_or_hardware_claimed=False)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>31I',rom,0xA220C);ws=[linked(o/n,'caller-'+str(i))for i,n in enumerate(('original-'+F+'.o','qualified-padded.o','selected-final.o'))];helper=origin_code(label='caller-origin');count=0
 class WindowExit(Exception):pass
 class WindowCode(faults.TrackedCode):
  def __getitem__(self,pc):
   if pc==0x15074DD8:self.owner.current_pc=pc;raise WindowExit
   return super().__getitem__(pc)
 for x,y,z,angle,f0,outcome,phase in itertools.product((-65537.0,32768.0),(1.75,-32769.0),(65536.0,-1.5),(0,0xFFFF),(0.0,16.0),(False,True),(0,8)):
  values=(int(256-f0*.5),192-(angle>>8),int(x),int(y),int(z),16,20,0,255,0);c=Case(values=tuple(map(u32,values)),outcome=outcome,effect=1,phase=phase);initial=fixture(c)
  for at,v in ((ACTOR+0x14,bits(x)),(ACTOR+0x18,bits(y)),(ACTOR+0x1C,bits(z)),(FACTOR,bits(.5))):put(initial,at,v)
  put(initial,ACTOR+0x76,angle,2);ms=[]
  for w in ws:
   code=dict(helper);code.update(zip(range(ENTRY,ENTRY+236,4),w));code[0x15074DD8]=0;m=Oracle(parent,initial,c,entry=0x15074D5C,connected=code,args=(0,0,0,0));m.r[16]=ACTOR;m.f[0]=bits(f0);m.code=WindowCode(m.code,m)
   try:m.run()
   except WindowExit:pass
   else:raise AssertionError('Original caller window did not exit')
   want,calls=reference(initial,c);assert(public(m.memory),m.calls)==(public(want),[(ENTRY,c.values),*calls]);ms.append(m)
  assert state(ms[0])==state(ms[1])and observable(ms[0])==observable(ms[2]);count+=1
 return dict(cases=count,original_window_words=31,parent='func_15074C80',call_ROM='0xA2280',ten_arguments=True,float_truncation_and_angle_setup=True,allocation_failure_and_success=True,return_ignored=True,original_origin_writer_connected=True,full_parent_or_gameplay_claimed=False)
def controls(body):
 return dict(wrong_allocation_kind=body.replace('func_15167A68(4,','func_15167A68(5,'),wrong_allocation_size=body.replace('0xA8','0xA4'),wrong_selector=body.replace('1, selector, 1','1, selector + 1, 1'),wrong_success_gate=body.replace('created != NULL','created != NULL && first == 0'),wrong_quad_count=body.replace('quad != 2','quad != 1'),wrong_coordinate=body.replace('0x2000','0x2001'),wrong_count_field=body.replace('created[0x95] = 2','created[0x95] = 1'),wrong_phase=body.replace('created + 0x9E) = 1','created + 0x9E) = 0'),wrong_lifetime=body.replace('created[0x92] = lifetime','created[0x92] = mode'),wrong_step=body.replace('created + 0x96) = step','created + 0x96) = x'),wrong_first=body.replace('created[0xA0] = first','created[0xA0] = second'),wrong_mode=body.replace('created[0x94] = mode','created[0x94] = lifetime'),narrow_origin_argument=body.replace('func_1517E05C(x, y, z)','func_1517E05C((s16)x, y, z)'),missing_origin=body.replace('        func_1517E05C(x, y, z);',''))
def compiled_controls():
 receipt={};corpus=[Case(effect=0),Case(effect=1),Case(outcome=False)]
 for n,body in controls(source.SELECTED).items():
  assert body!=source.SELECTED;obj,diag=source.compile_owner(r,o,source.HEADERS+body,'control-'+n);assert not diag;words=linked(obj,'control-linked-'+n)
  for i,c in enumerate(corpus):
   initial=fixture(c);m=Oracle(words,initial,c,connected=origin_code(label='control-origin-'+n)).run()
   try:check(m,initial,c)
   except AssertionError:receipt[n]=i;break
  assert n in receipt,('Ineffective control',n)
 return dict(count=len(receipt),effective_IDO_controls=receipt,compiler_or_oracle_errors_accepted=False)
def native_harness(body):
 return source.HEADERS+body+r'''
static u8 storage[640] __attribute__((aligned(4))),expected[640] __attribute__((aligned(4)));
static u32 values[10],outcome,effect,requests,origins,error;static s16 globalOrigin[3];
static void half(u8 *p,u32 v){*(u16 *)p=(u16)v;}
__attribute__((noinline)) void *func_15167A68(s32 kind,s32 category,s32 size,s32 flag,u8 selector,u8 retain) {
 requests++;if(kind!=4||(u32)category!=values[9]||size!=168||flag!=1||selector!=(u8)values[8]||retain!=1)error=1;
 if(effect){storage[36]=0x78;storage[32+0x92]=0xE2;}return outcome?storage+32:NULL;
}
__attribute__((noinline)) void func_1517E05C(s32 x,s32 y,s32 z) {
 u32 i;origins++;if((u32)x!=values[2]||(u32)y!=values[3]||(u32)z!=values[4])error=2;
 for(i=0;i<640;i++)if(storage[i]!=expected[i])error=3;
 globalOrigin[0]=(s16)x;globalOrigin[1]=(s16)y;globalOrigin[2]=(s16)z;
}
static int run(void) {
 u32 n,i,quad,base;u8 *p=expected+32;
 for(n=0;n<65536;n++)for(outcome=1;outcome<2;outcome--)for(effect=0;effect<2;effect++) {
  values[0]=0xA5A50000u|n*7;values[1]=0xF00D0000u|(n>>8);values[2]=0x87650000u|n;values[3]=0x43210000u|(n*31&65535);values[4]=0xBABA0000u|(n*137&65535);values[5]=0xABCD0000u|(n*3&65535);values[6]=n;values[7]=n>>8;values[8]=n>>8;values[9]=n^0xFEDCBA98u;
  requests=origins=error=0;for(i=0;i<640;i++)storage[i]=expected[i]=(u8)(i*29+n);for(i=0;i<3;i++)globalOrigin[i]=(s16)(0x5AA5+i);
  if(effect){expected[36]=0x78;p[0x92]=0xE2;}
  if(outcome) {
   p[0x95]=2;for(quad=0;quad<2;quad++){base=quad*64;half(p+base+0x18,0x2000);half(p+base+0x1A,0x2000);half(p+base+0x28,0x2800);half(p+base+0x2A,0x2000);half(p+base+0x38,0x2800);half(p+base+0x3A,0x2800);half(p+base+0x48,0x2000);half(p+base+0x4A,0x2800);}
   half(p+0x9E,1);p[0x92]=p[0x93]=(u8)values[6];half(p+0x98,values[2]);half(p+0x9A,values[3]);half(p+0x9C,values[4]);half(p+0x96,values[5]);p[0x94]=(u8)values[7];p[0xA0]=(u8)values[0];p[0xA1]=(u8)values[1];
  }
  func_15166118((s32)values[0],(s32)values[1],(s32)values[2],(s32)values[3],(s32)values[4],(s32)values[5],(s32)values[6],(s32)values[7],(u8)values[8],(s32)values[9]);
  if(error||requests!=1||origins!=outcome)return error?error:4;
  for(i=0;i<640;i++)if(storage[i]!=expected[i])return 5;
  for(i=0;i<3;i++)if(globalOrigin[i]!=(s16)(outcome?values[i+2]:0x5AA5+i))return 6;
 }
 return 0;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def native_suite():
 profiles={};negative={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,cases=262144,UBSan=True)
 for n,body in controls(source.SELECTED).items():
  p=o/('native-control-'+n+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,7)and not q.stdout and not q.stderr,(n,q.returncode,q.stderr);negative[n]=q.returncode
 return dict(cases_per_profile=262144,all65536_low_halfword_patterns=True,all256_selector_and_byte_patterns=True,profiles=profiles,negative_controls=len(negative),effective_native_controls=negative,SDK32_layout=True,all640_record_and_canary_bytes_checked=True,void_return_not_interpreted=True,full_word_origin_arguments_and_allocation_failure=True,portable_guest_home_mutation_or_hardware_claimed=False)
