"""Sampled actor byte, connected retail getter and bounded FP-control semantics."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import floating,bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-actor-intensity-byte-match';F='func_1511BA24';ENTRY=0x1511BA24;BODY=224;ACTOR=0x30000;HELPER=0x15188010
SYMS=dict(func_15188010=HELPER,D_800DF7B4=0x800DF7B4,D_800DF70C=0x800DF70C)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def float32(value):
 try:return struct.unpack('>f',struct.pack('>f',value))[0]
 except OverflowError:return math.copysign(math.inf,value)
def converted(value):
 if not math.isfinite(value):return 255
 integer=math.trunc(value);return (integer&255)if 0<=integer<2**32 else 255
VALUES=(0,0x80000000,1,0x80000001,0x3B808080,0x3B808081,0x3B808082,0x3F000000,0x3F7FFFFF,0x3F800000,0x3F800001,0x40000000,0x4B000000,0x4B800000,0x4B808080,0x4B808081,0xBF800000,0xBF000000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
 index:int=1
 count:int=4
 value:int=0x3F000000
 byte:int=173
 phase:int=0
 fcsr:int=0
 seed:int=0
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*29+c.seed*11+0x59)&255 for i in range(256)})
 put(m,ACTOR+0x3C,c.index);m[ACTOR+0x8A]=c.byte
 for i in range(8):put(m,s['D_800DF70C']+36*i,c.value)
 put(m,s['D_800DF7B4'],c.count);return m
def reference(initial,c,s=SYMS,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;output=home-4;index=read(m,ACTOR+0x3C);put(m,output,0)
 if 0<=signed(index)<signed(read(m,s['D_800DF7B4'])):put(m,output,read(m,s['D_800DF70C']+signed(index)*36))
 result=converted(float32(floating(read(m,output))*255.0));m[ACTOR+0x8A]=result or 1
 return m,[(s['func_15188010'],(index,output))]
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def cases():return tuple(Case(i,n,v,b,p,f,seed)for i,n,v,b,p,f,seed in itertools.product((-1,0,1,3,4,0x7FFFFFFF),(0,1,4,-1),VALUES,(0,173),(0,8),(0,0xA5A50003),(0,)))
def native_safe(c):
 if c.phase or c.fcsr:return False
 value=float32(floating(c.value)*255.0)if 0<=c.index<c.count else 0.0
 return math.isfinite(value)and 0<=value<2**32
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,));self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
 def execute(self,word):
  op,rs,fn=word>>26,word>>21&31,word&63
  if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,word)
  elif op==17 and rs==16 and fn==2:
   value=float32(floating(self.f[word>>11&31])*floating(self.f[word>>16&31]));self.f[word>>6&31]=bits(value);self.r[0]=0
  else:super().execute(word)
 def record_call(self,t):
  assert t in(self.syms['func_15188010'],ENTRY);a=tuple(self.arguments(2 if t==self.syms['func_15188010']else 1));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):raise AssertionError(('Getter must execute original instructions',t))
def linked(obj,label,s=SYMS,entry=ENTRY,function=F,nwords=56):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[function],rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()if n!=function));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%nwords,sections(p.with_suffix('.elf'))['.text'][1][:nwords*4]))
def helper_object():
 text=(r/'conker/asm/1B5370.s').read_text();f='func_15188010';part=text[text.index('glabel '+f):text.index('endlabel '+f)+len('endlabel '+f)].replace('glabel '+f,'.globl '+f+'\n.type '+f+',@function\n'+f+':').replace('endlabel '+f,'.size '+f+',.-'+f);p=o/'original-getter.s';p.write_text('.include "asm_processor_prelude.inc"\n.text\n'+part+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
def machine(words,initial,c,s=SYMS,entry=ENTRY,helper=None):
 helper=helper or linked(helper_object(),'getter-program',s,s['func_15188010'],'func_15188010',15);return Oracle(words,initial,c,s,entry,dict(zip(range(s['func_15188010'],s['func_15188010']+60,4),helper)))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition,m.fcsr)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]and m.fcsr==c.fcsr
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];ho=helper_object();helper=linked(ho,'getter-program',SYMS,HELPER,'func_15188010',15);count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=machine(words,initial,c,helper=helper);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited&set(range(ENTRY,ENTRY+BODY,4))==set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+172};assert set(range(HELPER,HELPER+60,4))<=visited
 assert ps[0][41:44]==[0x10000005,0x240FFFFF,0x440F8000];targets={i+1+(((w&65535)^32768)-32768)for i,w in enumerate(ps[0])if w>>26 in(1,4,5,6,7,20,21,22,23)};assert 43 not in targets
 prefixes=0
 for c in(Case(index=-1),Case(value=0x4B800000),Case(value=0x7FC12345)):
  initial=fixture(c);full=machine(ps[0],initial,c,helper=helper);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=machine(words,initial,c,helper=helper);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(func_15188010=0x10008000+k*0x100000,D_800DF7B4=0x80007FF0+k*0x100000,D_800DF70C=0x8001FFF0+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)];h=linked(ho,'getter-rebase-'+str(k),s,s['func_15188010'],'func_15188010',15)
  for index,value in itertools.product((-1,0,3,4),(0,0x3F000000,0x4B800000,0x7FC12345)):
   c=Case(index=index,value=value);initial=fixture(c,s);machines=[]
   for words in programs:m=machine(words,initial,c,s,entry,h);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 aliases=0
 for base in(STACK-4,ACTOR+0x88):
  for value in(0,0x3F000000,0x4B800000,0x7FC12345):
   s=dict(SYMS,D_800DF70C=base);h=linked(ho,'getter-alias-'+str(aliases),s,HELPER,'func_15188010',15);c=Case(index=0,value=value);initial=fixture(c,s);machines=[]
   for words in ps:m=machine(words,initial,c,s,helper=h);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>3I',rom,0x22D7C8)==(ENTRY,0,0);assert(0x80088D08-0x80088C90)//12==10;window=struct.unpack_from('>5I',rom,0x141390);cc=0
 for c in(Case(index=i,value=v,phase=p)for i,v,p in itertools.product((-1,0,3,4),(0,0x3F000000,0x4B800000,0x7FC12345),(0,8))):
  initial=fixture(c);put(initial,ACTOR+0x38,ENTRY);want,calls=reference(initial,c);machines=[]
  for program in ps:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code.update(zip(range(HELPER,HELPER+60,4),helper));code[0x15113EF4]=0;m=Oracle(window,initial,c,entry=0x15113EE0,connected=code);m.r[16]=ACTOR;m.r[30]=7;m.code=WindowCode(m.code,m);m.code.ends=(0x15113EF4,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.r[30],m.fcsr)==(public(want),[(ENTRY,(ACTOR,))]+calls,8,c.fcsr);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);cc+=1
 return dict(cases=count,executions=count*3,covered_words=55,compiler_words=56,slot_words=56,alignment_words=0,unreachable_offsets=[172],unreachable_duplicate_preserved=True,frame=32,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,connected_original_helper_words=15,helper_all_words_exercised=True,registration_table='D_80088C90',registration_index=10,registration_stride=12,registration_ROM='0x22D7C8',caller_window_entry='0x15113EE0',caller_window_ROM='0x141390',caller_window_words=5,caller_window_cases=cc,result_register_ignored=True,literal_full_state_equal=True,FCSR_restored_under_bounded_nontrapping_model=True,hardware_FCSR_or_complete_parent_claimed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):return dict(wrong_scale=body.replace('255.0f','254.0f'),wrong_initial=body.replace('factor = 0.0f','factor = 1.0f'),wrong_index=body.replace('actor + 0x3C','actor + 0x40'),wrong_output=body.replace('actor[0x8A]','actor[0x8B]'),wrong_minimum=body.replace('actor[0x8A] = 1;','actor[0x8A] = 2;'),wrong_gate=body.replace('actor[0x8A] == 0','actor[0x8A] != 0'),missing_minimum=body.replace('actor[0x8A] = 1;',';'),wrong_mask=body.replace('(u32)(factor * 255.0f)','((u32)(factor * 255.0f) & 0x7F)'),wrong_forwarded_index=body.replace('*(s32 *)(actor + 0x3C), &factor','0, &factor'))
def native_harness(selected):
 head,body=selected.split('/* Store',1);body='/* Store'+body;bad=controls(body);assert all(v!=body for v in bad.values());rows=[c for c in cases()if native_safe(c)]
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 index,count,value,byte,result;}Fixture;static const Fixture*current;static u8 actor[256]__attribute__((aligned(8)));static u32 calls,bad;
static f32 asFloat(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
void func_15188010(s32 index,f32*out){calls++;if(index!=(s32)current->index||out==NULL)bad=1;if(index>=0&&index<(s32)current->count)*out=asFloat(current->value);}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items());text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{%su,%su,%su,%su,%su}'%(u32(c.index),u32(c.count),c.value,c.byte,reference(fixture(c),c)[0][ACTOR+0x8A])for c in rows)+'\n};\n'
 text+=r'''
typedef void(*Update)(u8*);
static s32 check(Update fn){u32 n,i;u8 expected;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;calls=bad=0;for(i=0;i<256;i++)actor[i]=(u8)(i*29+0x59);*(u32*)(actor+0x3C)=current->index;actor[0x8A]=(u8)current->byte;fn(actor);if(bad||calls!=1)return 1;for(i=0;i<256;i++){if(i>=0x3C&&i<0x40)expected=(u8)(current->index>>(8*(i-0x3C)));else expected=i==0x8A?(u8)current->result:(u8)(i*29+0x59);if(actor[i]!=expected)return 2;}}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u8*)',all_actor_bytes_checked=True,native_float_to_u32_domain='finite product in [0,2**32)',invalid_or_nonfinite_guest_only=True,helper_model_matches_signed_getter_gate=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
