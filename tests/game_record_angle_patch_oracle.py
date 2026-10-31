"""Direct angle patch: sentinel/cache order, live flags and indirect retail callers."""
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
r=Path.cwd();o=r/'conker/build/game-record-angle-patch-150C7C90-match';F='func_150C7C90';ENTRY=0x150C7C90;BODY=236
ACTOR,COMMANDS,ALTERNATE,OBJECTS=0x30000,0x50000,0x60000,0x70000
LOOKUP=0x151149AC;SYMS=dict(func_151149AC=LOOKUP)
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 cached:int=0
 sentinel:int=3
 heading:int=0
 flags:int=0xA7
 mutation:int=0
 phase:int=0
 seed:int=0
 lookup_slot:int=2

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
 for base,n in ((ACTOR,160),(COMMANDS,80),(ALTERNATE,80),(OBJECTS,800)):
  for i in range(n):m[base+i]=(i*29+c.seed*11+0x59)&255
 for i in range(10):put(m,COMMANDS+8*i,0xA5123FFF^(i<<12));put(m,ALTERNATE+8*i,0x5AABCDE0+i)
 m[COMMANDS+c.sentinel*8]=0xF2;m[COMMANDS+8*8]=0xF3
 put(m,ACTOR+0x1C,COMMANDS);put(m,ACTOR+0x7C,c.cached);put(m,ACTOR+0x3C,c.flags);put(m,ACTOR+0x38,ENTRY)
 for i in range(5):m[OBJECTS+i*160+0x72]=(0x30+i)&255;put(m,OBJECTS+i*160+0x12,c.heading,2)
 m[OBJECTS+c.lookup_slot*160+0x72]=c.flags&255
 if c.lookup_slot<4:m[OBJECTS+(c.lookup_slot+1)*160+0x72]=c.flags&255
 put(m,0x800DBEF0,5);put(m,0x800DBEF4,OBJECTS)
 return m
def chosen(initial):
 index=read(initial,ACTOR+0x7C);base=read(initial,ACTOR+0x1C)
 if not index:
  while initial[u32(base+index*8)]!=0xF2:index+=1;assert index<10
 return index,u32(base+index*8)
def effect(m,c,record):
 if c.mutation&1:put(m,ACTOR+0x3C,read(m,ACTOR+0x3C)^0x8000)
 if c.mutation&2:put(m,ACTOR+0x1C,ALTERNATE);put(m,ACTOR+0x7C,5)
 if c.mutation&4:put(m,record,0x13579BDF)
 if c.mutation&8:put(m,OBJECTS+c.lookup_slot*160+0x12,c.heading^0xFFFF,2)
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def reference(initial,c,s=SYMS):
 m=dict(initial);index,record=chosen(m)
 if read(m,ACTOR+0x7C)==0:put(m,ACTOR+0x7C,index)
 args=(read(m,ACTOR+0x3C)&255,);observations=[(read(m,ACTOR+0x7C),read(m,ACTOR+0x1C),read(m,record))];calls=[(s['func_151149AC'],args)];effect(m,c,record)
 angle=-669-signed16(read(m,OBJECTS+c.lookup_slot*160+0x12,2))
 if read(m,ACTOR+0x3C)&0x8000:angle=836-angle
 angle%=1024;put(m,record,read(m,record)&0xFFFFF000);put(m,record,read(m,record)|angle)
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,arguments=None):
  self.observations=[];self.selected_record=chosen(memory)[1];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,)if arguments is None else arguments);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(self.syms['func_151149AC'],ENTRY),hex(t);a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_151149AC']:self.observations.append((read(self.memory,ACTOR+0x7C),read(self.memory,ACTOR+0x1C),read(self.memory,self.selected_record)))
 def hook(self,t):
  assert t==self.syms['func_151149AC'];effect(self.memory,self.case,self.selected_record)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=OBJECTS+self.case.lookup_slot*160
def linked(obj,label,s=SYMS,entry=ENTRY):
 from tools.experiments.alternative_source_draft_word_screen import emit_function
 from tools.pad_generated_object import parse_object
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;n=len(payload(obj,F)[0]);p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(n//4),sections(p.with_suffix('.elf'))['.text'][1][:n]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations)
def verify(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def cases():
 headings=(-32768,-2717,-1693,-669,-668,-1,0,355,1505,1506,2529,32767)
 return [Case(cached,at,h,flags,mu,phase,seed=h&255)for cached,at,h,flags,mu,phase in itertools.product((0,1,7),(0,1,3,7),headings,(0xA7,0xABCD80A7),(0,1,2,4,8,15),(0,8))]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in (Case(),Case(sentinel=0),Case(cached=7,heading=-32768,mutation=15),Case(heading=32767,flags=0x80A7,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for entry,target in((0x15001000,0x10008000),(0x1F008000,0x10018000),(0x1000FFF0,0x10028000)):
  s=dict(func_151149AC=target);programs=[linked(p,'rebase-'+str(rebased)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for c in (Case(),Case(sentinel=0),Case(cached=7,heading=32767,mutation=15)):
   initial=fixture(c);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helpers=dict(zip(range(LOOKUP,LOOKUP+28*4,4),struct.unpack_from('>28I',rom,0x141E5C)));connected_count=0
 for slot,cached,heading,mirror in itertools.product(range(5),(0,3),(-32768,-669,1505,32767),(0,0x8000)):
  c=Case(cached=cached,heading=heading,flags=0xA7|mirror,lookup_slot=slot);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c,connected=helpers);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 assert struct.unpack_from('>I',rom,0x22D888)[0]==ENTRY;caller_count=0
 for pc,off,n in((0x15113EE0,0x141390,5),(0x15113FB8,0x141468,4)):
  window=list(struct.unpack_from('>%dI'%n,rom,off));assert window[:2]==[0x8E190038,0x02002025]
  for cached,heading,mu in itertools.product((0,3),(-32768,-669,1505,32767),(0,15)):
   c=Case(cached=cached,heading=heading,mutation=mu);initial=fixture(c);want,calls,obs=reference(initial,c)
   for target in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),target));code[pc+4*n]=0;m=Oracle(window,initial,c,entry=pc,connected=code,arguments=());m.r[16]=ACTOR;m.r[30]=7;m.code=WindowCode(m.code,m);m.code.ends=(pc+4*n,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing indirect caller boundary')
    assert(public(m.memory),m.calls,m.observations)==(public(want),[(ENTRY,(ACTOR,))]+calls,obs)
    assert m.r[29]==STACK and m.r[16]==ACTOR and m.r[30]==(8 if n==5 else 7)
   caller_count+=1
 return dict(cases=count,executions=count*3,covered_words=len(visited),compiler_words=59,frame=32,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,original_lookup_words=28,connected_lookup_cases=connected_count,first_match_and_last_slot_lookup=True,original_indirect_call_windows=2,caller_words=9,caller_cases=caller_count,caller_ROM=['0x141390','0x141468'],callback_pointer_ROM='0x22D888',signed_sentinel_and_cached_zero_rescan=True,live_heading_flags_and_captured_record=True,two_separate_word_stores=True,all_signed_halfword_heading_native_scope=True,literal_full_state_equal=True,full_parent_gameplay_or_hardware_claimed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import compile_owner
import sys
oracle=sys.modules[__name__]

def controls(body):
 return dict(inverted_cache_gate=body.replace('actor + 0x7C) == 0','actor + 0x7C) != 0'),wrong_sentinel=body.replace('!= -14','!= -13'),wrong_selected_stride=body.replace(' + index * 8',' + index * 4'),byte_heading=body.replace('*(s16 *)(func_151149AC','*(s8 *)(func_151149AC'),wrong_selector=body.replace('*(u32 *)(actor + 0x3C) & 0xFF','*(u32 *)(actor + 0x3C) >> 8'),wrong_bias=body.replace('-669 -','-668 -'),wrong_mirror_constant=body.replace('836 - angle','835 - angle'),wrong_mirror_bit=body.replace('& 0x8000','& 0x4000'),wrong_negative_wrap=body.replace('angle += 1024','angle += 1023'),wrong_positive_wrap=body.replace('angle -= 1024','angle -= 1023'),wrong_boundary=body.replace('angle >= 1024','angle > 1024'),wrong_preservation_mask=body.replace('~0xFFF','~0x3FF'),wrong_low_bits=body.replace('|= angle;','|= angle + 1;'))
def harness(selected):
 body=selected[selected.index('/* Patch'):];bad=controls(body);assert len(bad)==13 and all(text!=body for text in bad.values())
 pre=r'''#include <ultra64.h>
_Static_assert(sizeof(void*)==4,"native32");
static u8 actor[160] __attribute__((aligned(8))),commands[80] __attribute__((aligned(8))),alternate[80] __attribute__((aligned(8))),object[160] __attribute__((aligned(8)));
static s32 currentIndex,currentSentinel,currentCached,currentHeading,currentMutation;static u32 currentFlags,bad,calls;
u8 *func_151149AC(u8 selector){
 if(calls||selector!=(currentFlags&255)||*(s32*)(actor+0x7C)!=currentIndex||*(u8**)(actor+0x1C)!=commands)bad=1;calls++;
 if(currentMutation&1)*(u32*)(actor+0x3C)^=0x8000;
 if(currentMutation&2){*(u8**)(actor+0x1C)=alternate;*(s32*)(actor+0x7C)=5;}
 if(currentMutation&4)*(u32*)(commands+currentIndex*8)=0x13579BDFu;
 if(currentMutation&8)*(s16*)(object+0x12)=(s16)(currentHeading^0xFFFF);
 return object;
}
'''
 pre+='\n'.join(text.replace('func_150C7C90','test_'+name)for name,text in dict(selected=body,**bad).items())
 pre+=r'''
typedef void(*Fn)(u8*);
static s32 check(Fn fn,s32 heading,s32 mirror,s32 cached,s32 sentinel,s32 mutation){
 u8 wantActor[160],wantCommands[80],wantAlternate[80],wantObject[160];s32 i,index,angle,liveHeading;u32 word,flags;
 currentCached=cached;currentSentinel=sentinel;currentHeading=heading;currentMutation=mutation;currentIndex=index=cached?cached:sentinel;currentFlags=0x123400A7u|(mirror?0x8000u:0);calls=bad=0;
 for(i=0;i<160;i++){actor[i]=(u8)(i*13+0x57);object[i]=(u8)(i*29+0x63);}for(i=0;i<80;i++){commands[i]=(u8)(i*17+0x6B);alternate[i]=(u8)(i*11+0x38);}
 for(i=0;i<10;i++)*(u32*)(commands+i*8)=0xA5123FFFu^((u32)i<<12);commands[sentinel*8]=0xF2;commands[64]=0xF3;
 *(u8**)(actor+0x1C)=commands;*(s32*)(actor+0x7C)=cached;*(u32*)(actor+0x3C)=currentFlags;*(s16*)(object+0x12)=(s16)heading;
 for(i=0;i<160;i++){wantActor[i]=actor[i];wantObject[i]=object[i];}for(i=0;i<80;i++){wantCommands[i]=commands[i];wantAlternate[i]=alternate[i];}
 *(s32*)(wantActor+0x7C)=index;flags=currentFlags;
 if(mutation&1)flags^=0x8000;*(u32*)(wantActor+0x3C)=flags;
 if(mutation&2){*(u8**)(wantActor+0x1C)=alternate;*(s32*)(wantActor+0x7C)=5;}
 if(mutation&4)*(u32*)(wantCommands+index*8)=0x13579BDFu;
 liveHeading=heading;if(mutation&8){liveHeading=(s16)(heading^0xFFFF);*(s16*)(wantObject+0x12)=(s16)liveHeading;}
 angle=-669-liveHeading;if(flags&0x8000)angle=836-angle;angle%=1024;if(angle<0)angle+=1024;
 word=*(u32*)(wantCommands+index*8);*(u32*)(wantCommands+index*8)=(word&0xFFFFF000u)|(u32)angle;
 fn(actor);if(bad||calls!=1)return 1;
 for(i=0;i<160;i++)if(actor[i]!=wantActor[i]||object[i]!=wantObject[i])return 2;
 for(i=0;i<80;i++)if(commands[i]!=wantCommands[i]||alternate[i]!=wantAlternate[i])return 3;
 return 0;
}
static s32 witness(Fn fn){s32 h,k,m,c,s;static const s32 headings[]={-32768,-2717,-1693,-669,-668,-1,0,355,1505,1506,2529,32767};
 for(h=0;h<12;h++)for(m=0;m<2;m++)for(k=0;k<4;k++)for(c=0;c<2;c++)for(s=0;s<8;s++)if(check(fn,headings[h],m,c?7:0,s,k?((1<<k)-1):0))return 1;return 0;}
static int run(void){s32 h,m,k;for(h=-32768;h<=32767;h++)for(m=0;m<2;m++)for(k=0;k<4;k++)if(check(test_selected,h,m,(h&8)?7:0,h&7,k?((1<<k)-1):0))return 10;
'''
 for i,name in enumerate(bad):pre+='if(!witness(test_'+name+'))return '+str(20+i)+';\n'
 pre+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return pre,dict(cases_per_profile=65536*2*4,negative_controls=13,all_signed_halfword_headings=True,every_sentinel_position=True,cached_and_uncached_paths=True,entire_actor_command_alternate_and_object_bytes_checked=True,helper_mutations_and_preserved_upper_bits=True,guest_alias_or_hardware_claimed=False)
def run_native(selected):
 text,counts=harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=counts['cases_per_profile'],UBSan=True)
 return dict(profiles=reports,**counts)
def compiled_controls(selected):
 headers,body=selected.split('/* Patch',1);body='/* Patch'+body;results={}
 for name,source in controls(body).items():
  obj,diag=compile_owner(r,o,headers+source,'control-'+name);assert not diag,diag;words=oracle.linked(obj,'linked-control-'+name);witness=None
  for c in oracle.cases():
   initial=oracle.fixture(c);m=oracle.Oracle(words,initial,c);m.run()
   try:oracle.verify(m,initial,c)
   except AssertionError:witness=dict(cached=c.cached,sentinel=c.sentinel,heading=c.heading,flags=c.flags,mutation=c.mutation);break
  assert witness is not None,('ineffective compiled control',name);results[name]=witness
 return dict(count=len(results),semantic_witnesses=results,compiler_or_oracle_errors_accepted=False)
