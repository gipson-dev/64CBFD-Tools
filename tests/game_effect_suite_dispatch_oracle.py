"""Six-call suite: byte ABI, argument homes, live category and original callers."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_four_head_lookup_match import payload
r=Path.cwd();o=r/'conker/build/game-effect-suite-dispatch-151C9DE8-match';F='func_151C9DE8';ENTRY=0x151C9DE8;BODY=236
OWNER,OUTPUT=0x30000,0x60000;FACTORY,COPY=0x15149130,0x10022EC0
TARGETS=(0x151C9F38,0x151CC524,0x151CC840,0x151CCF08,0x150BDE90,0x151CB5FC)
NAMES=('func_151C9F38','func_151CC524','func_151CC840','func_151CCF08','func_150BDE90','func_151CB5FC')
SYMS=dict(zip(NAMES,TARGETS),D_800BE9F0=0x800BE9F0,D_8008CD00=0x8008CD00)
COUNTS=(5,6,6,4,3,5);u32=lambda n:n&0xFFFFFFFF;signed8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
 slot:int=1
 kind:int=-1
 selector:int=255
 value:int=1
 category:int=0x27
 flag:int=0
 mode:int=0
 phase:int=0
 seed:int=0
 connected:bool=False
 allocate:bool=True

def home(c):return STACK+c.phase
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,512)}
 for base,n in((OWNER,64),(OUTPUT,128),(s['D_800BE9F0']-4,12),(s['D_8008CD00']-4,12)):
  for i in range(n):m[u32(base+i)]=(i*29+c.seed*11+0x59)&255
 put(m,home(c)+16,c.value);put(m,s['D_800BE9F0'],c.category);m[s['D_8008CD00']]=c.flag
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def args(c):return(OWNER,u32(c.slot),u32(c.kind),u32(c.selector))
def expected_args(c,n,kind,value):
 slot,selector=c.slot&255,c.selector&255
 return((OWNER,4,slot,u32(kind),selector),(OWNER,0,50,255,slot,selector),(OWNER,0,50,255,slot,selector),(OWNER,slot,u32(kind),selector),(OWNER,selector,u32(value)),(OWNER,2,slot,u32(kind),selector))[n-1]
def effects(m,c,s,n,argv):
 if c.mode&32:
  h=n*17
  for value in argv[1:]:h=u32(h*33+value)
  m[OWNER+0x10+n]^=h&255
 if n==1:
  if c.mode&4:m[home(c)+11]=0x80
  if c.mode&8:put(m,home(c)+4,0xFFFFFFFF);put(m,home(c)+12,0)
 if n==4 and c.mode&16:put(m,home(c)+16,c.value^0x89ABCDEF)
 if n==6:
  if c.mode&1:put(m,s['D_800BE9F0'],0 if read(m,s['D_800BE9F0'])==0x27 else 0x27)
  if c.mode&2:m[s['D_8008CD00']]=0x55
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];kind=signed8(c.kind);value=c.value
 for n,name in enumerate(NAMES,1):
  argv=expected_args(c,n,kind,value);calls.append((s[name],argv))
  if n==5 and c.connected:
   packet=home(c)-56;put(m,packet,OWNER);put(m,packet+4,0,2);factory=(300,0xFFFFFFFF,79,0xFFFFFFFF,0,60,8,c.selector&255,u32(value));calls.append((FACTORY,factory));effects(m,c,s,n,argv)
   if c.allocate:
    calls.append((COPY,(OUTPUT+40,packet,8)));data=bytes(m[packet+i]for i in range(8))
    for i,b in enumerate(data):m[OUTPUT+40+i]=b
  else:effects(m,c,s,n,argv)
  if n==1 and c.mode&4:kind=-128
  if n==4 and c.mode&16:value=c.value^0x89ABCDEF
 if read(m,s['D_800BE9F0'])==0x27:m[s['D_8008CD00']]=1
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,arguments=None):
  self.steps=0;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c)if arguments is None else arguments);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  if t in(self.syms[name]for name in NAMES):n=next(i for i,name in enumerate(NAMES,1)if self.syms[name]==t);count=COUNTS[n-1];self.steps+=1
  else:count={ENTRY:5,FACTORY:9,COPY:3}[t]
  argv=tuple(self.arguments(count));self.calls.append((t,argv));self.events.append(('CALL',t,argv))
 def hook(self,t):
  c=self.case;s=self.syms;argv=self.calls[-1][1]
  if t==COPY:
   data=bytes(self.memory[argv[1]+i]for i in range(argv[2]))
   for i,b in enumerate(data):self.memory[argv[0]+i]=b
   value=0xB16B00B5
  elif t==FACTORY:
   effects(self.memory,c,s,5,self.calls[-2][1]);value=OUTPUT if c.allocate else 0
  else:
   n=next(i for i,name in enumerate(NAMES,1)if s[name]==t);effects(self.memory,c,s,n,argv);value=0xDEAD0000+n
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,s=SYMS,entry=ENTRY):
 from tools.experiments.alternative_source_draft_word_screen import emit_function
 from tools.pad_generated_object import parse_object
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;n=len(payload(obj,F)[0]);p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(n//4),sections(p.with_suffix('.elf'))['.text'][1][:n]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def cases():
 rows=[Case(slot=i|0xABCD0000,kind=i|0xCAFE0000,selector=(255-i)|0x81230000,value=(0,0xFFFFFFFF,0x80000000,0x12345678)[i%4],category=(0,0x27,0x26,0xFFFFFFFF,0x127,0x80000027)[i%6],flag=i,mode=i%64,phase=(i&1)*8,seed=i)for i in range(256)]
 rows.extend(Case(slot,kind,selector,0x81234567,cat,flag=255,mode=mode)for slot,kind,selector,cat,mode in itertools.product((0,1,127,128,255),(0,1,127,128,255),(0,1,127,128,255),(0,0x27),(0,3,4,8,16,63)))
 return rows
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=delay=0
 for c in(Case(),Case(category=0),Case(kind=0xFFFFFF80,mode=63,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1;delay+=machines[0].delay_of is not None
 rebased=0
 for k,entry in enumerate((0x17007FFC,0x2500FFFC)):
  s={name:entry+0x10000*(i+1)for i,name in enumerate(NAMES)};s.update(D_800BE9F0=0x80417FFC+k*0x100000,D_8008CD00=0x80428004+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for c in(Case(),Case(mode=63),Case(slot=255,kind=128,selector=128,category=0)):
   initial=fixture(c,s);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(TARGETS[4],TARGETS[4]+31*4,4),struct.unpack_from('>31I',rom,0xEB340)));connected_count=0;hv=set()
 for kind,mode,category,allocate in itertools.product((-128,-1,0,127),(0,3,32,63),(0,0x27),(False,True)):
  c=Case(kind=kind,mode=mode,category=category,connected=True,allocate=allocate);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c,connected=helper);m.run();verify(m,initial,c);hv.update(m.visits);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 assert all(pc in hv for pc in helper);caller_count=0
 for pc,off,n in((0x151C9CCC,0x1F717C,6),(0x15025390,0x52840,10)):
  words=list(struct.unpack_from('>%dI'%n,rom,off));end=pc+4*n if n==6 else 0x150265B4
  for kind,selector,mode,category in itertools.product((-128,-1,0,127),(0,255),(0,35),(0,0x27)):
   c=Case(slot=1 if n==6 else 0,kind=-1 if n==6 else kind,selector=255 if n==6 else selector,mode=mode,category=category);initial=fixture(c);put(initial,0x800DBFF0,OWNER);initial[STACK+0x15F]=kind&255;initial[STACK+0x17B]=selector;want,calls=reference(initial,c)
   for target in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),target));code[end]=0;m=Oracle(words,initial,c,entry=pc,connected=code,arguments=());m.r[4]=OWNER;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    expected_call=(ENTRY,(OWNER,c.slot,u32(c.kind),c.selector,1));assert(public(m.memory),m.calls)==(public(want),[expected_call]+calls)
    assert m.r[29]==STACK
   caller_count+=1
 return dict(cases=count,executions=count*3,covered_words=59,frame=48,guards=0,access_prefix_pairs=prefixes,delay_slot_cuts=delay,rebase_layouts=2,rebase_cases=rebased,original_connected_helper_words=31,connected_cases=connected_count,connected_factory_and_copy_are_ABI_hooks=True,caller_windows=2,caller_words=16,caller_cases=caller_count,caller_JAL_ROM=['0x52858','0x1F718C'],literal_pointer_count=0,unsigned_slot_and_selector_signed_kind=True,latched_unsigned_values_ignore_home_mutations=True,signed_kind_and_fifth_value_home_lifetimes=True,live_category_after_sixth_call=True,void_result_not_interpreted=True,unwritten_connected_packet_bytes_guest_only=True,literal_full_state_equal=True,native_alias_or_full_parent_or_gameplay_claimed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import compile_owner
import sys
oracle=sys.modules[__name__]

def controls(body):
 swapped=body.replace('func_151CC524','temporary_panel').replace('func_151CC840','func_151CC524').replace('temporary_panel','func_151CC840')
 return dict(unsigned_kind=body.replace('slot & 0xFF, kind, selector & 0xFF','slot & 0xFF, (u8)kind, selector & 0xFF'),slot_mask=body.replace('slot & 0xFF','slot & 0x7F'),selector_mask=body.replace('selector & 0xFF','selector & 0x7F'),value_width=body.replace('selector, value);','selector, (u8)value);'),first_mode=body.replace('owner, 4,','owner, 3,'),size=body.replace('0, 50, 255','0, 49, 255'),panel_order=swapped,skip_final=body.replace('    func_151CB5FC(owner, 2, slot, kind, selector);',''),cached_category=body.replace('    func_151C9F38','    s32 category = D_800BE9F0;\n    func_151C9F38',1).replace('if (D_800BE9F0 ==','if (category =='),category=body.replace('== 0x27','== 0x26'),flag=body.replace('D_8008CD00 = 1','D_8008CD00 = 2'),else_clear=body.replace('        D_8008CD00 = 1;\n    }','        D_8008CD00 = 1;\n    } else {\n        D_8008CD00 = 0;\n    }'),owner=body.replace('func_150BDE90(owner,','func_150BDE90(NULL,'))
def harness(selected):
 headers=selected[:selected.index('/* Submit')];body=selected[selected.index('/* Submit'):];bad=controls(body);assert len(bad)==13 and all(text!=body for text in bad.values())
 pre=headers+r'''
_Static_assert(sizeof(void*)==4,"native32");
static u8 object[64];s32 D_800BE9F0;u8 D_8008CD00;
typedef struct {s32 kind,value,category;u32 slot,selector,mode,flag;} Fixture;
static Fixture current;static u32 calls,error;
static u32 canonical(void*p){return p==object?0x30000u:p?0xDEADBEEFu:0;}
static u32 expected(u32 n,u32*a){u32 slot=current.slot,selector=current.selector,kind=(u32)current.kind;
 a[0]=0x30000u;
 if(n==1){a[1]=4;a[2]=slot;a[3]=kind;a[4]=selector;return 5;}
 if(n==2||n==3){a[1]=0;a[2]=50;a[3]=255;a[4]=slot;a[5]=selector;return 6;}
 if(n==4){a[1]=slot;a[2]=kind;a[3]=selector;return 4;}
 if(n==5){a[1]=selector;a[2]=(u32)current.value;return 3;}
 a[1]=2;a[2]=slot;a[3]=kind;a[4]=selector;return 5;}
static u32 hash(u32 n,const u32*a,u32 count){u32 h=n*17,i;for(i=1;i<count;i++)h=h*33+a[i];return h;}
static void observe(u32 n,void*p,const u32*a,u32 count){u32 want[6],i,nargs=expected(n,want);if(n!=++calls||nargs!=count)error=1;
 for(i=0;i<count;i++)if(a[i]!=want[i])error=1;
 if((current.mode&32)&&p)((u8*)p)[0x10+n]^=(u8)hash(n,a,count);
 if(n==6){if(current.mode&1)D_800BE9F0=D_800BE9F0==0x27?0:0x27;if(current.mode&2)D_8008CD00=0x55;}}
__attribute__((noinline,noclone)) void func_151C9F38(void*p,s32 mode,u8 slot,s8 kind,u8 selector){u32 a[]={canonical(p),(u32)mode,slot,(u32)kind,selector};observe(1,p,a,5);}
__attribute__((noinline,noclone)) void func_151CC524(void*p,s32 a1,s32 a2,s32 a3,u8 slot,u8 selector){u32 a[]={canonical(p),(u32)a1,(u32)a2,(u32)a3,slot,selector};observe(2,p,a,6);}
__attribute__((noinline,noclone)) void func_151CC840(void*p,s32 a1,s32 a2,s32 a3,u8 slot,u8 selector){u32 a[]={canonical(p),(u32)a1,(u32)a2,(u32)a3,slot,selector};observe(3,p,a,6);}
__attribute__((noinline,noclone)) s32 func_151CCF08(void*p,s32 slot,s32 kind,s32 selector){u32 a[]={canonical(p),(u32)slot,(u32)kind,(u32)selector};observe(4,p,a,4);return 0x12345678;}
__attribute__((noinline,noclone)) void func_150BDE90(void*p,u8 selector,s32 value){u32 a[]={canonical(p),selector,(u32)value};observe(5,p,a,3);}
__attribute__((noinline,noclone)) void func_151CB5FC(void*p,s32 mode,u8 slot,s8 kind,u8 selector){u32 a[]={canonical(p),(u32)mode,slot,(u32)kind,selector};observe(6,p,a,5);}
'''
 pre+='\n'.join(text.replace('func_151C9DE8','test_'+name)for name,text in dict(selected=body,**bad).items())
 pre+=r'''
typedef void(*Fn)(void*,u8,s8,u8,s32);
static s32 check(Fn fn,s32 kind,u32 slot,u32 selector,s32 value,s32 category,u32 flag,u32 mode){u32 i,n,a[6],count;u8 wanted[64],finalFlag; s32 finalCategory;
 current.kind=kind;current.slot=slot;current.selector=selector;current.value=value;current.category=category;current.flag=flag;current.mode=mode;calls=error=0;
 for(i=0;i<64;i++)object[i]=wanted[i]=(u8)(i*29+0x59);D_800BE9F0=category;D_8008CD00=(u8)flag;
 if(mode&32)for(n=1;n<=6;n++){count=expected(n,a);wanted[0x10+n]^=(u8)hash(n,a,count);}
 finalCategory=(mode&1)?(category==0x27?0:0x27):category;finalFlag=(u8)((mode&2)?0x55:flag);if(finalCategory==0x27)finalFlag=1;
 fn(object,(u8)slot,(s8)kind,(u8)selector,value);
 if(error||calls!=6)return 1;if(D_800BE9F0!=finalCategory||D_8008CD00!=finalFlag)return 2;for(i=0;i<64;i++)if(object[i]!=wanted[i])return 3;return 0;}
static const u32 bytes[]={0,1,128,255},modes[]={0,1,2,3,32,35},flags[]={0,1,255};
static const s32 values[]={0,1,-1,(s32)0x81234567u},categories[]={0,0x27,0x127,-1,(s32)0x80000027u};
static s32 witness(Fn fn){s32 kind;u32 a,b,v,c,f,m;for(kind=-128;kind<128;kind+=127)for(a=0;a<4;a++)for(b=0;b<4;b++)for(v=0;v<4;v++)for(c=0;c<5;c++)for(f=0;f<3;f++)for(m=0;m<6;m++)if(check(fn,kind,bytes[a],bytes[b],values[v],categories[c],flags[f],modes[m]))return 1;return 0;}
static int run(void){s32 kind;u32 a,b,v,c,f,m;for(kind=-128;kind<128;kind++)for(a=0;a<4;a++)for(b=0;b<4;b++)for(v=0;v<4;v++)for(c=0;c<5;c++)for(f=0;f<3;f++)for(m=0;m<6;m++)if(check(test_selected,kind,bytes[a],bytes[b],values[v],categories[c],flags[f],modes[m]))return 10;
'''
 for i,name in enumerate(bad):pre+='if(!witness(test_'+name+'))return '+str(20+i)+';\n'
 pre+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return pre,dict(cases_per_profile=256*4*4*4*5*3*6,negative_controls=len(bad),SDK32=True,all_signed_kind_bytes=True,slot_selector_and_full_word_payload_boundaries=True,live_category_and_existing_flag_checked=True,entire_owner_buffer_preserved_except_provider_effects=True,void_result_not_interpreted=True,guest_home_mutations_or_callee_implementation_claimed=False)
def run_native(selected):
 text,counts=harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=counts['cases_per_profile'],UBSan=True)
 return dict(profiles=reports,**counts)
def compiled_controls(selected):
 headers,body=selected.split('/* Submit',1);body='/* Submit'+body;results={}
 for name,bad in controls(body).items():
  assert bad!=body;obj,diag=compile_owner(r,o,headers+bad,'control-'+name);assert not diag,diag;words=oracle.linked(obj,'linked-control-'+name);witness=None
  for c in oracle.cases():
   initial=oracle.fixture(c);m=oracle.Oracle(words,initial,c);m.run()
   try:oracle.verify(m,initial,c)
   except AssertionError:witness=dict(slot=c.slot,kind=c.kind,selector=c.selector,category=c.category,flag=c.flag,mode=c.mode);break
  assert witness is not None,('ineffective compiled control',name);results[name]=witness
 return dict(count=len(results),semantic_witnesses=results,compiler_or_oracle_errors_accepted=False)
