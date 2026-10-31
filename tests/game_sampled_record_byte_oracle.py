"""Sampled affine byte: bounded RNE guest model, live records and original getters."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import floating,bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-sampled-record-byte-151638E0-match';F='func_151638E0';ENTRY=0x151638E0;BODY=240
STATE,OTHER,THIRD,TARGET,ALTERNATE=0x30000,0x32000,0x34000,0x60000,0x61000
VECTOR,SCALAR,PRE,PARENT,TABLE=0x15187FC0,0x15188010,0x1515F10C,0x15161804,0x8008B208
SYMS=dict(func_15187FC0=VECTOR,func_15188010=SCALAR,D_800DF7B4=0x800DF7B4,D_800DF700=0x800DF700,D_800DF70C=0x800DF70C)
u32=lambda n:n&0xFFFFFFFF;signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def rounded(v):
 try:return floating(bits(v))
 except OverflowError:return math.copysign(math.inf,v)
def converted(v):
 if not math.isfinite(v):return 255
 n=math.trunc(v);return(n&255)if 0<=n<2**32 else 255
def affine(base,scale,factor):return rounded(floating(base)+rounded(floating(scale)*floating(factor)))
@dataclass(frozen=True)
class Case:
 index:int=1
 count:int=4
 factor:int=0x3F000000
 base:int=0x3F800000
 scale:int=0x437E0000
 mode:int=0
 phase:int=0
 fcsr:int=0
 spill:int=0x3E800000
 flags:int=0
 seed:int=0
 connected:bool=False

def fixture(c,s=SYMS,home=None):
 home=STACK+c.phase if home is None else home;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,512)}
 for base,n in ((STATE,128),(OTHER,128),(THIRD,128),(TARGET,80),(ALTERNATE,80),(s['D_800DF700']-16,36*8+32),(s['D_800DF70C']-16,36*8+32),(s['D_800DF7B4']-4,12)):
  for i in range(n):m[u32(base+i)]=(i*29+c.seed*11+0x59)&255
 for p in(STATE,OTHER,THIRD):
  put(m,p+0x14,TARGET);put(m,p+0x18,c.index);put(m,p+0x1C,c.base);put(m,p+0x20,c.scale);m[p+0x12]=14;m[p+0xE]=c.flags
 for i in range(8):
  for j in range(3):m[s['D_800DF700']+36*i+6+j]=(i*17+j*31+5)&255
  put(m,s['D_800DF70C']+36*i,c.factor)
 put(m,s['D_800DF7B4'],c.count);put(m,home-20,c.spill);put(m,TABLE+14*4,ENTRY);return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def effect(m,c,number,home):
 if number==1:
  if c.mode&1:
   put(m,STATE+0x18,2);put(m,STATE+0x1C,0x40000000);put(m,STATE+0x20,0x3F800000);put(m,STATE+0x14,ALTERNATE)
  if c.mode&4:put(m,home,OTHER)
 else:
  owner=read(m,home)
  if c.mode&2:
   put(m,owner+0x1C,0x40400000);put(m,owner+0x20,0x40000000);put(m,owner+0x14,ALTERNATE)
  if c.mode&8:put(m,home,THIRD)
def reference(initial,c,s=SYMS,home=None,parent=False):
 home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];owner=STATE
 if parent:
  if c.flags&2:put(m,STATE+0x10,0xA55A,2);calls.append((PRE,(read(m,STATE+0x14),STATE)))
  calls.append((ENTRY,(STATE,)))
 put(m,home,owner);index=read(m,owner+0x18);vector,scalar=home-16,home-20;calls.append((s['func_15187FC0'],(index,vector)))
 if not c.connected:
  for i,v in enumerate((0x11,0x22,0x33)):put(m,vector+4*i,v)
  effect(m,c,1,home)
 elif 0<=signed(index)<signed(read(m,s['D_800DF7B4'])):
  for i in range(3):put(m,vector+4*i,m[s['D_800DF700']+signed(index)*36+6+i])
 owner=read(m,home);record=owner+0x18;index=read(m,record);calls.append((s['func_15188010'],(index,scalar)))
 if not c.connected:put(m,scalar,c.factor);effect(m,c,2,home)
 elif 0<=signed(index)<signed(read(m,s['D_800DF7B4'])):put(m,scalar,read(m,s['D_800DF70C']+signed(index)*36))
 value=converted(affine(read(m,record+4),read(m,record+8),read(m,scalar)));target=read(m,read(m,home)+0x14);m[target+0x2F]=value
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,home=None):
  self.home=STACK+c.phase if home is None else home
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(STATE,));self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
 def execute(self,word):
  op,rs,fn=word>>26,word>>21&31,word&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,word)
  elif op==17 and rs==16 and fn in(0,1,2):
   a,b=floating(self.f[word>>11&31]),floating(self.f[word>>16&31]);v=a+b if fn==0 else a-b if fn==1 else a*b;self.f[word>>6&31]=bits(rounded(v));self.r[0]=0
  else:super().execute(word)
 def record_call(self,t):
  assert t in(self.syms['func_15187FC0'],self.syms['func_15188010'],PRE,ENTRY);a=tuple(self.arguments(1 if t==ENTRY else 2));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;args=self.calls[-1][1]
  if t==PRE:put(self.memory,STATE+0x10,0xA55A,2)
  else:
   assert not c.connected,'Connected getters must execute retail instructions'
   if t==self.syms['func_15187FC0']:
    for i,v in enumerate((0x11,0x22,0x33)):put(self.memory,args[1]+4*i,v)
    effect(self.memory,c,1,self.home)
   else:put(self.memory,args[1],c.factor);effect(self.memory,c,2,self.home)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,s=SYMS,entry=ENTRY,function=F,nwords=60):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[function],rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()if n!=function));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%nwords,sections(p.with_suffix('.elf'))['.text'][1][:4*nwords]))
def helper_object(function):
 text=(r/'conker/asm/1B5370.s').read_text();a=text.index('glabel '+function);b=text.index('endlabel '+function,a);p=o/('original-'+function+'.s');p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+text[a:b]+'.size '+function+',.-'+function+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
def helpers(s=SYMS,key='helpers'):
 code={}
 for name,n in(('func_15187FC0',20),('func_15188010',15)):
  words=linked(helper_object(name),key+'-'+name,s,s[name],name,n);code.update(zip(range(s[name],s[name]+4*n,4),words))
 return code
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition,m.fcsr)
def verify(m,initial,c,s=SYMS,home=None,parent=False):
 want,calls=reference(initial,c,s,home,parent);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[2]==1 and m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]and m.fcsr==c.fcsr
def cases():
 values=(0,0x80000000,1,0x3E800000,0x3F000000,0x3F800000,0x3F800001,0x437F0000,0x43800000,0x4F000000,0x4F7FFFFF,0x4F800000,0xBF000000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 for factor,base,scale,mode in itertools.product(values,(0,0x3F800000,0xBF800000,0x437F0000),(0,0x3F000000,0x3F800000,0xBF800000),(0,1,2,3,4,8,12)):
  yield Case(factor=factor,base=base,scale=scale,mode=mode)
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visits=set();count=0
 for c in cases():
  initial=fixture(c);ms=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits);count+=1
 assert visits&set(range(ENTRY,ENTRY+BODY,4))==set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+192}
 connected_count=0;code=helpers();hv=set()
 for index,n,factor,spill,phase in itertools.product((-1,0,3,4),(0,4),(0,0x3F800000,0x7FC12345),(0,0x3F000000,0x7F800000),(0,8)):
  c=Case(index,n,factor,spill=spill,phase=phase,connected=True);initial=fixture(c);ms=[]
  for words in ps:m=Oracle(words,initial,c,connected=code);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);hv.update(ms[0].visits);connected_count+=1
 assert set(code)<=hv
 prefixes=delay=0
 for c in(Case(),Case(factor=0x7FC12345,mode=12),Case(index=-1,connected=True,spill=0x7F800000)):
  initial=fixture(c);full=Oracle(ps[0],initial,c,connected=code if c.connected else None);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for words in ps:
    m=Oracle(words,initial,c,connected=code if c.connected else None);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1;delay+=ms[0].delay_of is not None
 rebased=0
 for k,entry in enumerate((0x17007FFC,0x2500FFFC)):
  s=dict(func_15187FC0=entry+0x10000,func_15188010=entry+0x20000,D_800DF7B4=0x80417FFC+k*0x100000,D_800DF700=0x8042FFF0+k*0x100000,D_800DF70C=0x8043FFF0+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)];hc=helpers(s,'helpers-rebase-'+str(k))
  for c in(Case(),Case(index=-1,connected=True),Case(connected=True),Case(mode=15)):
   initial=fixture(c,s);ms=[]
   for words in programs:m=Oracle(words,initial,c,s,entry,hc if c.connected else None);m.run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 aliases=0
 for base,delta,factor in itertools.product((STATE+0x18,STACK-16),(4,12),(0,0x3F800000,0x7FC12345)):
  s=dict(SYMS,D_800DF700=base,D_800DF70C=base+delta);hc=helpers(s,'helpers-alias-'+str(aliases));c=Case(index=0,factor=factor,connected=True);initial=fixture(c,s);ms=[]
  for words in ps:m=Oracle(words,initial,c,s,connected=hc);m.run();verify(m,initial,c,s);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);aliases+=1
 parent=struct.unpack_from('>23I',(r/'conker/conker.us.bin').read_bytes(),0x18ECB4);caller_cases=0
 for flags,mode,factor,connected in itertools.product((0,2),(0,1,2,12),(0,0x3F800000,0x7FC12345),(False,True)):
  c=Case(index=0,flags=flags,mode=0 if connected else mode,factor=factor,connected=connected);home=STACK-24;initial=fixture(c,home=home);ms=[]
  for program in ps:
   owned=dict(zip(range(ENTRY,ENTRY+BODY,4),program))
   if c.connected:owned.update(code)
   m=Oracle(parent,initial,c,entry=PARENT,connected=owned,home=home);m.run();verify(m,initial,c,home=home,parent=True);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);caller_cases+=1
 return dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,body_words=60,covered_words=59,unreachable_word_indices=[48],unreachable_duplicate_preserved=True,frame=48,guards=0,access_prefix_pairs=prefixes,delay_slot_cuts=delay,rebase_layouts=2,rebase_cases=rebased,guest_alias_cases=aliases,connected_cases=connected_count,original_helper_words=35,helper_coverage=[20,15],invalid_indices_preserve_unwritten_scalar=True,incoming_home_mutations_guest_only=True,live_record_and_target_after_helpers=True,return_value=1,original_caller_words=23,caller_cases=caller_cases,callback_table='D_8008B208',callback_index=14,callback_pointer_ROM='0x22FBF0',optional_parent_helper_is_ABI_hook=True,literal_full_state_equal=True,FP_model='bounded nontrapping RNE; arithmetic exception flags and full FCSR not modeled',native_unwritten_or_out_of_range_or_full_FCSR_claimed=False)

def controls(body):
 def cached(name,type_,expr):
  value=body.replace('    f32 factor;','    f32 factor;\n    '+type_+' '+name+';').replace('    func_15187FC0','    '+name+' = '+expr+';\n    func_15187FC0',1)
  return value
 cached_index=cached('index','s32','record->index').replace('func_15188010(record->index','func_15188010(index')
 cached_base=cached('base','f32','record->base').replace('(u8)(record->base +','(u8)(base +')
 cached_scale=cached('scale','f32','record->scale').replace('record->base + record->scale *','record->base + scale *')
 cached_target=cached('target','struct226 *','state->unk14').replace('state->unk14->unk2F =','target->unk2F =')
 first='    func_15187FC0(record->index, vector);';second='    func_15188010(record->index, &factor);'
 return dict(skip_vector=body.replace(first,'    (void)vector;'),swapped_getters=body.replace(first,'TEMP').replace(second,first).replace('TEMP',second),cached_index=cached_index,cached_base=cached_base,cached_scale=cached_scale,cached_target=cached_target,omit_base=body.replace('record->base + record->scale * factor','record->scale * factor'),omit_scale=body.replace('record->base + record->scale * factor','record->base + factor'),multiply_after_add=body.replace('record->base + record->scale * factor','(record->base + record->scale) * factor'),early_factor_truncation=body.replace('record->scale * factor','record->scale * (u8)factor'),wrong_target_byte=body.replace('->unk2F =','->unk9 ='),return_zero=body.replace('return 1;','return 0;'),zero_unwritten=body.replace('f32 factor;','f32 factor = 0.0f;'))

def compiled_controls(selected):
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 headers,body=selected.split('/* Sample',1);body='/* Sample'+body;results={}
 samples=[Case(factor=0x3F000000,base=0x3F800000,scale=0x40000000,mode=m)for m in (0,1,2,3)]
 samples+=[Case(index=-1,connected=True,spill=0x3F000000),Case(factor=0x3E800000,scale=0x3F000000)]
 hc=helpers(key='control-helpers')
 for name,bad in controls(body).items():
  assert bad!=body;obj,diag=compile_owner(r,o,headers+bad,'control-'+name);assert not diag,diag;text,fs,_=parse_object(obj);words=linked(obj,'linked-control-'+name,nwords=fs[F]['size']//4);witness=None
  for c in samples:
   initial=fixture(c);m=Oracle(words,initial,c,connected=hc if c.connected else None);m.run();want,calls=reference(initial,c)
   observe=lambda rows:[(t,args[0])for t,args in rows]
   if public(m.memory)!=public(want)or m.r[2]!=1 or observe(m.calls)!=observe(calls):witness=dict(index=c.index,factor=hex(c.factor),base=hex(c.base),scale=hex(c.scale),mode=c.mode,connected=c.connected);break
  assert witness is not None,('Ineffective semantic control',name);results[name]=witness
 return dict(count=len(results),semantic_witnesses=results,guest_only_controls=['zero_unwritten'],compiler_or_oracle_errors_accepted=False,internal_scratch_address_differences_not_accepted=True)

def native_cases():
 result=[]
 for factor,base,scale,mode,index,seed in itertools.product((0.,.25,.5,.75,1.,2.,127.,255.),(-1.,0.,.5,1.,127.,255.),(0.,.5,1.,2.,-1.),(0,1,2,3),(0,1,3),(0,1)):
  b,s=(3.,2.)if mode&2 else(2.,1.)if mode&1 else(base,scale);value=rounded(b+rounded(s*factor))
  if math.isfinite(value)and -1<value<256:result.append((bits(factor),bits(base),bits(scale),mode,index,seed))
 for byte,seed in itertools.product(range(256),(0,1)):result.append((bits(byte+.75),bits(0.),bits(1.),0,1,seed))
 return result

def harness(selected):
 from tools.tests.test_game_row_destination_fill import START
 headers,body=selected.split('/* Sample',1);body='/* Sample'+body;bad=controls(body);bad.pop('zero_unwritten')
 code=headers+'\n'.join(text.replace(F,'test_'+name)for name,text in dict(selected=body,**bad).items())
 code+=r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(__builtin_offsetof(struct225,unk18)==0x18,"embedded record");
_Static_assert(__builtin_offsetof(struct225,unk14)==0x14,"target pointer");
_Static_assert(sizeof(GameScalarSample)==12,"record extent");
static struct225 owner;static struct226 targets[2];
typedef struct {u32 factor,base,scale,mode,index,seed;} Fixture;
typedef s32(*Fn)(struct225*);
static Fixture current;static u32 calls,error;
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static GameScalarSample*record(void){return(GameScalarSample*)&owner.unk18;}
__attribute__((noinline,noclone)) void func_15187FC0(s32 index,u32*vector){if(calls!=0||(u32)index!=current.index)error=1;calls++;vector[0]=0x11;vector[1]=0x22;vector[2]=0x33;
 if(current.mode&1){record()->index=2;record()->base=2.f;record()->scale=1.f;owner.unk14=&targets[1];}}
__attribute__((noinline,noclone)) void func_15188010(s32 index,f32*factor){if(calls!=1||(u32)index!=((current.mode&1)?2:current.index))error=1;calls++;*factor=real(current.factor);
 if(current.mode&2){record()->base=3.f;record()->scale=2.f;owner.unk14=&targets[1];}}
static s32 check(Fn fn,Fixture c){u32 i,j;u8 wantedOwner[sizeof(owner)],wantedTargets[sizeof(targets)];u8*p=(u8*)&owner,*t=(u8*)targets;f32 base,scale,product,value;s32 result;
 current=c;calls=error=0;for(i=0;i<sizeof(owner);i++)p[i]=(u8)(i*13+c.seed*17+0xA5);for(i=0;i<sizeof(targets);i++)t[i]=(u8)(i*29+c.seed*11+0x59);
 owner.unk14=&targets[0];record()->index=(s32)c.index;record()->base=real(c.base);record()->scale=real(c.scale);
 for(i=0;i<sizeof(owner);i++)wantedOwner[i]=p[i];for(i=0;i<sizeof(targets);i++)wantedTargets[i]=t[i];
 base=(c.mode&2)?3.f:(c.mode&1)?2.f:real(c.base);scale=(c.mode&2)?2.f:(c.mode&1)?1.f:real(c.scale);product=scale*real(c.factor);value=base+product;
 result=fn(&owner);if(error||calls!=2||result!=1)return 1;
 if(c.mode&1){s32 v=2;u8*q=(u8*)&v;for(j=0;j<4;j++)wantedOwner[0x18+j]=q[j];}
 if(c.mode&3){u8*b=(u8*)&base,*s=(u8*)&scale;struct226*target=&targets[1];u8*q=(u8*)&target;for(j=0;j<4;j++){wantedOwner[0x1C+j]=b[j];wantedOwner[0x20+j]=s[j];wantedOwner[0x14+j]=q[j];}}
 wantedTargets[(c.mode&3?sizeof(struct226):0)+0x2F]=(u8)value;
 for(i=0;i<sizeof(owner);i++)if(p[i]!=wantedOwner[i])return 2;for(i=0;i<sizeof(targets);i++)if(t[i]!=wantedTargets[i])return 3;return 0;}
static const Fixture cases[]={ROWS};
static s32 witness(Fn fn){u32 mode;Fixture c={0x3F000000,0x3F800000,0x40000000,0,1,0};for(mode=0;mode<4;mode++){c.mode=mode;if(check(fn,c))return 1;}return 0;}
static int run(void){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)if(check(test_selected,cases[i]))return 10;
'''
 rows=native_cases();code=code.replace('ROWS',',\n'.join('{'+','.join(hex(v)+'u'for v in row)+'}'for row in rows))
 for i,name in enumerate(bad):code+='if(!witness(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,dict(cases_per_profile=len(rows),negative_controls=len(bad),guest_only_controls=['zero_unwritten'],SDK32=True,finite_defined_u8_conversion_only=True,factor_always_written=True,all_output_bytes_and_fractional_boundaries=True,live_record_and_target_mutations=True,entire_owner_and_both_target_canaries=True,guest_home_alias_nonfinite_or_full_FCSR_claimed=False)

def run_native(selected):
 from tools.tests.test_game_projected_packet_draw import native_command
 text,counts=harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=counts['cases_per_profile'],UBSan=True)
 return dict(profiles=reports,**counts)
