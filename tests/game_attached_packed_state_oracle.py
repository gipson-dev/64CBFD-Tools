"""Packed attached state: exact bounded conversions, aliases and command callback."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-attached-packed-state-15073B38-match';F='func_15073B38';ENTRY=0x15073B38;BODY=240
ACTOR,CHILD,TABLE=0x30000,0x60000,0x800863FC
SYMS=dict(D_800D154C=0x800D154C,D_800D1580=0x800D1580)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 word:int=0xABCD1234
 phase:int=0
 fcsr:int=0
 seed:int=0
 alias:int=0

def child(c,s=SYMS):return (CHILD,s['D_800D1580']-0xA8,s['D_800D1580']-0xAC)[c.alias]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,512)}
 for base,n in ((ACTOR,0x340),(child(c,s)-16,0xD0),(s['D_800D154C']-16,32),(s['D_800D1580']-16,32)):
  for i in range(n):m[u32(base+i)]=(i*29+c.seed*11+0x59)&255
 put(m,s['D_800D154C'],ACTOR);put(m,ACTOR+0x31C,child(c,s));put(m,s['D_800D1580'],c.word);return m

def reference(initial,c,s=SYMS):
 m=dict(initial)
 # Deliberately reload the packed word and object pointer for each store.
 p=read(m,read(m,s['D_800D154C'])+0x31C);put(m,p+0xA8,bits(float(read(m,s['D_800D1580'])&65535)))
 value=float((read(m,s['D_800D1580'])>>16)&255);p=read(m,read(m,s['D_800D154C'])+0x31C);m[p+0xAC]=int(value)&255
 value=(read(m,s['D_800D1580'])>>24)&255;p=read(m,read(m,s['D_800D154C'])+0x31C);m[p+0xAD]=value
 return m

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
 def execute(self,word):
  if word>>26==17 and (word>>21&31 in (2,6) or (word>>21&31==16 and word&63==36)):AreaOracle.execute(self,word)
  else:super().execute(word)
 def record_call(self,target):
  assert target==ENTRY;self.calls.append((target,()));self.events.append(('CALL',target,()))
 def hook(self,target):raise AssertionError(('No opaque helper expected',target))

def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:fs[F]['size']];return list(struct.unpack('>%dI'%(len(data)//4),data))
def state(m,raw=False):
 regs=m.r[:]
 # The four guarded words form one closed, caller-clobbered GP allocation cycle.
 # Original and padded states compare literally; raw C projects only those roles.
 if raw:
  for i in (8,9,24,25):regs[i]=0
 return(regs,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition,m.fcsr)
def verify(m,initial,c,s=SYMS):
 assert m.memory==reference(initial,c,s) and not m.calls,c
 assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28] and m.f[20:]==m.before_f[20:] and m.fcsr==c.fcsr
def compare(ms):
 assert state(ms[0])==state(ms[2]);assert state(ms[0],True)==state(ms[1],True)
def cases():
 lows=(0,1,127,128,255,256,32767,32768,65534,65535)
 for i in range(256):yield Case((i<<24)|(i<<16)|(i*257),seed=i%3,fcsr=(0,3,0xA5A50003)[i%3])
 for low,mode,flag,phase,fcsr in itertools.product(lows,(0,1,127,128,255),(0,1,127,128,255),(0,8),(0,1,2,3,0xA5A50003)):
  yield Case((flag<<24)|(mode<<16)|low,phase,fcsr)

def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[2] and len(ps[0])==60
 visited=set();count=0
 for c in cases():
  initial=fixture(c);ms=[]
  for words in ps:
   m=Oracle(words,initial,c);m.run();verify(m,initial,c);ms.append(m)
  compare(ms);visited.update(ms[0].visits);count+=1
 prefixes=delays=0
 for c in (Case(),Case(0xFFFFFFFF,alias=1),Case(0x80FF1234,alias=2)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    ms.append(m)
   compare(ms);prefixes+=1;delays+=ms[0].delay_of is not None
 aliases=0
 for alias,word,fcsr in itertools.product((1,2),(0,1,0xFFFF,0x00FF0000,0x80001234,0xFFFFFFFF),(0,3,0xA5A50003)):
  c=Case(word,fcsr=fcsr,alias=alias);initial=fixture(c);ms=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);ms.append(m)
  compare(ms);aliases+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000)):
  s=dict(D_800D154C=0x80017FF0+k*0x100000,D_800D1580=0x8002FFF0+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for word,alias in itertools.product((0,0x7F80FFFF,0xFFFFFFFF),(0,1,2)):
   c=Case(word,alias=alias);initial=fixture(c,s);ms=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);ms.append(m)
   compare(ms);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22B0E4)[0]==ENTRY;from tools.patch_generated_slice_ld import load_game_data_layout;rom_start,vram,rom_end,owners=load_game_data_layout(r/'conker');assert(rom_start,vram)==(0x2275E0,0x80082B20);pointer_VA=vram+0x22B0E4-rom_start;assert pointer_VA==0x80086624;index=(pointer_VA-TABLE)//4;assert index==138
 window=list(struct.unpack_from('>6I',rom,0x98360));assert window==[0x10800009,0x0004C080,0x03D8C821,0x8F390000,0x0320F809,0]
 caller_cases=0
 for word,alias,fcsr in itertools.product((0,1,0xFFFF,0x80FF1234,0xFFFFFFFF),(0,1,2),(0,3)):
  c=Case(word,fcsr=fcsr,alias=alias);initial=fixture(c);put(initial,TABLE+index*4,ENTRY);ms=[]
  for program in ps:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[0x1506AEC8]=code[0x1506AED8]=0;m=Oracle(window,initial,c,entry=0x1506AEB0,connected=code);m.r[4]=index;m.r[30]=TABLE;m.code=WindowCode(m.code,m);m.code.ends=(0x1506AEC8,0x1506AED8)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing callback window boundary')
   assert m.memory==reference(initial,c) and m.calls==[(ENTRY,())] and m.fcsr==fcsr;ms.append(m)
  compare(ms);caller_cases+=1
 result=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,body_words=60,covered_words=len(visited&set(range(ENTRY,ENTRY+BODY,4))),unreachable_word_indices=[i for i in range(60)if ENTRY+4*i not in visited],frame=0,guards=4,access_prefix_pairs=prefixes,delay_slot_memory_cuts=delays,rebase_layouts=2,rebase_cases=rebased,guest_alias_cases=aliases,caller_window_words=6,caller_cases=caller_cases,callback_table='D_800863FC',callback_index=138,callback_pointer_VA=hex(pointer_VA),game_data_ROM_start=hex(rom_start),callback_pointer_ROM='0x22B0E4',callback_window_ROM='0x98360',bounded_FP_values_are_exact=True,FCSR_restored=True,void_result_not_interpreted=True,original_and_padded_literal_full_state_equal=True,raw_differs_only_closed_caller_clobbered_GP_cycle=True,full_parent_or_gameplay_claimed=False)
 return result

def controls(body):
 cached=body.replace('D_800D1580','packed').replace('    f32 mode;','    f32 mode;\n    s32 packed = D_800D1580;')
 swapped=body.replace('->mode =','->temporary =').replace('->flags =','->mode =').replace('->temporary =','->flags =')
 return dict(low_mask=body.replace('& 0xFFFF','& 0xFF'),low_sign=body.replace('(f32)(D_800D1580 & 0xFFFF)','(f32)(s16)(D_800D1580 & 0xFFFF)'),mode_mask=body.replace('& 0xFF);','& 0x7F);'),mode_shift=body.replace('>> 16','>> 15'),flag_shift=body.replace('>> 24','>> 23'),flag_mask=body.replace('(u8)(D_800D1580 >> 24)','(u8)((D_800D1580 >> 24) & 0x7F)'),swapped_fields=swapped,skip_value=body.replace('    ((GameAttachedPackedState *)D_800D154C->unk31C)->value = value;','    (void)value;'),mode_increment=body.replace('->mode = (u8)mode;','->mode = (u8)mode + 1;'),cached_word=cached)

def compiled_controls(selected):
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 headers,body=selected.split('/* Decode',1);body='/* Decode'+body;results={}
 samples=[Case(w,alias=a)for w,a in itertools.product((0,1,0x8000,0xFFFF,0x00FF0000,0x80FF1234,0xFFFFFFFF),(0,1,2))]
 for name,bad in controls(body).items():
  assert bad!=body;obj,diag=compile_owner(r,o,headers+bad,'control-'+name);assert not diag,diag;words=linked(obj,'linked-control-'+name);witness=None
  for c in samples:
   initial=fixture(c);m=Oracle(words,initial,c);m.run()
   if m.memory!=reference(initial,c):witness=dict(word=hex(c.word),alias=c.alias);break
  assert witness is not None,('Ineffective compiled semantic control',name);results[name]=witness
 return dict(count=len(results),semantic_witnesses=results,guest_only_controls=['cached_word'],compiler_or_oracle_errors_accepted=False)

def harness(selected):
 from tools.tests.test_game_row_destination_fill import START
 headers,body=selected.split('/* Decode',1);body='/* Decode'+body;bad=controls(body);bad.pop('cached_word')
 code=headers+'\n'.join(text.replace(F,'test_'+name)for name,text in dict(selected=body,**bad).items())
 code+=r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(s32)==4,"word");
_Static_assert(__builtin_offsetof(GameAttachedPackedState,value)==0xA8,"value offset");
_Static_assert(__builtin_offsetof(GameAttachedPackedState,mode)==0xAC,"mode offset");
_Static_assert(__builtin_offsetof(GameAttachedPackedState,flags)==0xAD,"flag offset");
static struct127 actor;static GameAttachedPackedState attached;
struct127 *D_800D154C;s32 D_800D1580;
typedef void(*Fn)(void);
static s32 check(Fn fn,u32 word){u32 i;GameAttachedPackedState expected;u8 *p=(u8*)&attached,*e=(u8*)&expected;u8 *a=(u8*)&actor;
 for(i=0;i<sizeof(attached);i++)p[i]=e[i]=(u8)(i*29+0x59);
 for(i=0;i<sizeof(actor);i++)a[i]=(u8)(i*13+0xA5);
 actor.unk31C=(struct126*)&attached;D_800D154C=&actor;D_800D1580=(s32)word;
 expected.value=(f32)(word&65535);expected.mode=(u8)((word>>16)&255);expected.flags=(u8)(word>>24);
 fn();if(D_800D154C!=&actor||(u32)D_800D1580!=word||actor.unk31C!=(struct126*)&attached)return 1;
 for(i=0;i<sizeof(attached);i++)if(p[i]!=e[i])return 2;
 for(i=0;i<sizeof(actor);i++)if((i<0x31C||i>=0x320)&&a[i]!=(u8)(i*13+0xA5))return 3;
 return 0;}
static const u32 lows[]={0,1,127,128,32767,32768,65535};
static const u32 samples[]={0,1,0x8000,0xFFFF,0x00FF0000,0x80FF1234,0xFFFFFFFF};
static s32 witness(Fn fn){u32 i;for(i=0;i<7;i++)if(check(fn,samples[i]))return 1;return 0;}
static int run(void){u32 low,mode,flag,k;
 for(k=0;k<7;k++)for(mode=0;mode<256;mode++)for(flag=0;flag<256;flag++)if(check(test_selected,(flag<<24)|(mode<<16)|lows[k]))return 10;
 for(low=0;low<65536;low++)for(k=0;k<3;k++)if(check(test_selected,((k==0?0:k==1?0x80FFu:0xFF80u)<<16)|low))return 11;
'''
 for i,name in enumerate(bad):code+='if(!witness(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,dict(cases_per_profile=655360,negative_controls=len(bad),SDK32=True,all_low_halfwords=True,all_mode_flag_byte_pairs=True,entire_actor_and_attached_canaries_checked=True,global_input_and_owner_preserved=True,guest_alias_or_transient_FCSR_claimed=False)

def run_native(selected):
 from tools.tests.test_game_projected_packet_draw import native_command
 text,counts=harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=counts['cases_per_profile'],UBSan=True)
 return dict(profiles=reports,**counts)
