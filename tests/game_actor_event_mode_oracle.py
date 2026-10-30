"""Actor event-mode selection, live helper state and original table dispatch."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-actor-event-mode-match';F='func_150D0650';ENTRY=0x150D0650;BODY=212;SIZE=224;ACTOR=0x30000;GATE=0x60000;ALT=0x61000;META=0x62000
SYMS=dict(D_800D2E4C=0x800D2E4C,D_800CC335=0x800CC335,func_1509BE40=0x1509BE40,func_15123934=0x15123934,func_151239CC=0x151239CC,func_151254F4=0x151254F4)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 gate:int=0
 query:int=0
 check:int=1
 selector:int=1
 flags:int=0
 mutation:int=0
 phase:int=0
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(512)});put(m,ACTOR+0x2C,0x87654321);put(m,ACTOR+0x134,0x12345678);put(m,ACTOR+0x84,c.flags);put(m,ACTOR+0x190,0x7FC12345);put(m,s['D_800D2E4C'],GATE);m[GATE]=c.gate;m[ALT]=0x80;m[s['D_800CC335']]=c.selector;return m
def effect(m,c,kind,s=SYMS,sp=None):
 mu=c.mutation
 if kind==1:
  if mu&1:put(m,ACTOR+0x2C,0x71234567);put(m,ACTOR+0x134,0x89ABCDEF);put(m,ACTOR+0x84,0x50)
  if mu&16:put(m,s['D_800D2E4C'],ALT)
  if mu&8 and sp is not None:
   for i in range(4):put(m,sp+4*i,0xB5000000+i)
 if kind in(2,3)and mu&2:put(m,ACTOR+0x84,0x80000002);m[s['D_800CC335']]=0;put(m,ACTOR+0x190,0x7F101010)
 if kind==4 and mu&4:put(m,ACTOR+0x84,read(m,ACTOR+0x84)^4);put(m,ACTOR+0x190,0x12345678);put(m,ACTOR+0x194,0x11223344)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 def call(kind,name,args):
  calls.append((s[name],tuple(map(u32,args))))
  if kind==4:observations.append((read(m,ACTOR+0x84),read(m,ACTOR+0x190)))
  effect(m,c,kind,s)
 if m[read(m,s['D_800D2E4C'])]&0x80:return m,calls,observations
 call(1,'func_1509BE40',(0,0x2000,0xBB))
 if u32(c.query)!=0xFFFFFFFF:
  call(2,'func_15123934',(ACTOR,read(m,ACTOR+0x2C),0,read(m,ACTOR+0x134),8))
  if c.check:
   put(m,ACTOR+0x84,read(m,ACTOR+0x84)|0x1000000);call(4,'func_151254F4',(ACTOR,m[s['D_800CC335']]-1));put(m,ACTOR+0x190,0x42C80000)
 else:
  call(3,'func_151239CC',(ACTOR,8))
  if c.check:call(4,'func_151254F4',(ACTOR,0));put(m,ACTOR+0x190,0)
 return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def cases():return tuple(Case(*args)for args in itertools.product((0,0x80,0xFF),(-1,0,0x80000000),(0,1,0xFFFFFFFF),(0,1,255),(0,0xFFFFFF,0xFFFFFFFF),(0,1,2,4,8,16,31),(0,8)))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,));self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def record_call(self,t):
  counts={self.syms['func_1509BE40']:3,self.syms['func_15123934']:5,self.syms['func_151239CC']:2,self.syms['func_151254F4']:2,ENTRY:1};assert t in counts;args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.syms['func_151254F4']:self.observations.append((read(self.memory,ACTOR+0x84),read(self.memory,ACTOR+0x190)))
 def hook(self,t):
  kind={self.syms['func_1509BE40']:1,self.syms['func_15123934']:2,self.syms['func_151239CC']:3,self.syms['func_151254F4']:4}[t];effect(self.memory,self.case,kind,self.syms,self.r[29]);result=self.case.query if kind==1 else self.case.check if kind in(2,3)else 0xDEADBEEF
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(result);self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>56I',sections(p.with_suffix('.elf'))['.text'][1][:SIZE]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.observations,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls,observations=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]and ps[0][-3:]==[0,0,0];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(gate=0x80),Case(mutation=31),Case(query=-1,mutation=31),Case(check=0)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 c=Case(gate=0x80);initial={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};put(initial,SYMS['D_800D2E4C'],GATE);initial[GATE]=0x80
 for words in ps:m=Oracle(words,initial,c);m.r[4]=0;m.run();assert public(m.memory)==public(initial)and not m.calls
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800D2E4C=0x80007FF0+k*0x100000,D_800CC335=0x8001FFF0+k*0x100000,**{n:0x10008000+j*0x10000+k*0x100000 for j,n in enumerate(('func_1509BE40','func_15123934','func_151239CC','func_151254F4'))});programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for gate,query,check,mu in itertools.product((0,0x80),(-1,0),(0,1),(0,31)):
   c=Case(gate=gate,query=query,check=check,mutation=mu);initial=fixture(c,s);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 aliases=0
 for at in(ACTOR+0x84,ACTOR+0x190):
  for query in(-1,0):
   s=dict(SYMS,D_800CC335=at);c=Case(query=query,mutation=31);initial=fixture(c,s);programs=[linked(p,'alias-'+str(aliases)+'-'+str(i),s)for i,p in enumerate(objects)];machines=[]
   for words in programs:m=Oracle(words,initial,c,s);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E188)[0]==ENTRY and(0x800896C8-0x80089670)//4==22;window=struct.unpack_from('>10I',rom,0x15D6EC);cc=0
 for selector,query,check,mu in itertools.product((0,22),(-1,0),(0,1),(0,31)):
  c=Case(query=query,check=check,mutation=mu);initial=fixture(c);put(initial,0x800B0DF0,META);initial[META+15]=selector;put(initial,0x800896C8,ENTRY);want,calls,obs=reference(initial,c)if selector else(initial,[],[]);machines=[]
  for program in ps:
   code=dict(zip(range(ENTRY,ENTRY+SIZE,4),program));code[0x15130264]=0;m=Oracle(window,initial,c,entry=0x1513023C,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(0x15130264,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.observations)==(public(want),([(ENTRY,(ACTOR,))]+calls)if selector else[],obs);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);cc+=1
 return dict(cases=count,executions=count*3,covered_words=53,compiler_words=53,slot_words=56,alignment_words=3,frame=40,guards=0,access_prefix_pairs=prefixes,sparse_disabled_actor=True,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,registration_table='D_80089670',registration_index=22,registration_stride=4,registration_ROM='0x22E188',caller_window_entry='0x1513023C',caller_window_ROM='0x15D6EC',caller_window_words=10,caller_window_cases=cc,zero_selector_skips_dispatch=True,result_register_ignored=True,literal_full_state_equal=True,bounded_helper_models=True,original_helpers_executed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):return dict(wrong_gate=body.replace('0x80','0x40'),wrong_sentinel=body.replace('!= -1','!= 0'),wrong_query=body.replace('0xBB','0xBA'),wrong_slot=body.replace(', 8)',', 7)'),wrong_flags=body.replace('0x1000000','0x2000000'),wrong_selector=body.replace('D_800CC335 - 1','D_800CC335'),wrong_active_timer=body.replace('100.0f','99.0f'),wrong_fallback_timer=body.replace('= 0.0f','= 1.0f'),wrong_live_argument=body.replace('actor + 0x2C','actor + 0x30'))
def native_harness(selected):
 head,body=selected.split('/* Select',1);body='/* Select'+body;bad=controls(body);assert all(v!=body for v in bad.values());rows=[];kinds={SYMS['func_1509BE40']:1,SYMS['func_15123934']:2,SYMS['func_151239CC']:3,SYMS['func_151254F4']:4}
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 gate,query,check,selector,flags,mutation,out2C,out134,outFlags,outTimer,marker,finalSelector,alt,calls,kinds[3],args[15],observations[2];}Fixture;
static const Fixture*current;static u8 actor[512]__attribute__((aligned(8))),gateByte,altByte;u8 *D_800D2E4C;u8 D_800CC335;static u32 calls,bad,observed,observations[2];
static void checkCall(u32 kind,u32 a,u32 b,u32 c,u32 d,u32 e){u32 i,values[5]={a,b,c,d,e},n=calls++;if(n>=current->calls||n>=3){bad=1;return;}if(current->kinds[n]!=kind)bad=1;for(i=0;i<5;i++)if(values[i]!=current->args[n*5+i])bad=1;}
static u32 owner(u8*p){if(p!=actor)bad=1;return 0x30000;}
static void effect(u32 kind){u32 mu=current->mutation;if(kind==1){if(mu&1){*(u32*)(actor+0x2C)=0x71234567;*(u32*)(actor+0x134)=0x89ABCDEF;*(u32*)(actor+0x84)=0x50;}if(mu&16)D_800D2E4C=&altByte;}if((kind==2||kind==3)&&(mu&2)){*(u32*)(actor+0x84)=0x80000002;D_800CC335=0;*(u32*)(actor+0x190)=0x7F101010;}if(kind==4&&(mu&4)){*(u32*)(actor+0x84)^=4;*(u32*)(actor+0x190)=0x12345678;*(u32*)(actor+0x194)=0x11223344;}}
s32 func_1509BE40(s32 count,...){__builtin_va_list ap;s32 mask,opcode;__builtin_va_start(ap,count);mask=__builtin_va_arg(ap,s32);opcode=__builtin_va_arg(ap,s32);__builtin_va_end(ap);checkCall(1,count,mask,opcode,0,0);effect(1);return(s32)current->query;}
s32 func_15123934(u8*a,s32 b,s32 c,s32 d,s32 e){checkCall(2,owner(a),b,c,d,e);effect(2);return(s32)current->check;}
s32 func_151239CC(u8*a,s32 b){checkCall(3,owner(a),b,0,0,0);effect(3);return(s32)current->check;}
void func_151254F4(u8*a,s32 b){checkCall(4,owner(a),b,0,0,0);observed++;observations[0]=*(u32*)(actor+0x84);observations[1]=*(u32*)(actor+0x190);effect(4);}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items())
 for c in cases():
  if c.phase:continue
  want,calls,obs=reference(fixture(c),c);ks=[kinds[t]for t,a in calls];args=[list(a)+[0]*(5-len(a))for t,a in calls];args+= [[0]*5 for i in range(3-len(args))];flat=sum(args,[]);values=[c.gate,u32(c.query),u32(c.check),c.selector,c.flags,c.mutation,read(want,ACTOR+0x2C),read(want,ACTOR+0x134),read(want,ACTOR+0x84),read(want,ACTOR+0x190),int(bool(obs)and bool(c.mutation&4)),want[SYMS['D_800CC335']],int(read(want,SYMS['D_800D2E4C'])==ALT),len(calls)];array=lambda v:'{'+','.join('0x%Xu'%u32(x)for x in v)+'}';rows.append('{'+','.join('0x%Xu'%u32(x)for x in values)+','+array(ks+[0]*(3-len(ks)))+','+array(flat)+','+array(obs[0]if obs else(0,0))+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Update)(u8*);
static s32 check(Update fn){u32 n,i,value;u8 expected;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;calls=bad=observed=0;observations[0]=observations[1]=0;for(i=0;i<512;i++)actor[i]=(u8)(i*29+0x59);*(u32*)(actor+0x2C)=0x87654321;*(u32*)(actor+0x134)=0x12345678;*(u32*)(actor+0x84)=current->flags;*(u32*)(actor+0x190)=0x7FC12345;gateByte=(u8)current->gate;altByte=0x80;D_800D2E4C=&gateByte;D_800CC335=(u8)current->selector;fn(actor);if(bad||calls!=current->calls||observed!=(current->calls==3))return 1;if(D_800D2E4C!=(current->alt?&altByte:&gateByte)||D_800CC335!=current->finalSelector||gateByte!=current->gate||altByte!=0x80)return 2;if(observations[0]!=current->observations[0]||observations[1]!=current->observations[1])return 3;
 for(i=0;i<512;i++){expected=(u8)(i*29+0x59);value=0;if(i>=0x2C&&i<0x30)value=current->out2C;else if(i>=0x84&&i<0x88)value=current->outFlags;else if(i>=0x134&&i<0x138)value=current->out134;else if(i>=0x190&&i<0x194)value=current->outTimer;else if(i>=0x194&&i<0x198&&current->marker)value=0x11223344;else{if(actor[i]!=expected)return 4;continue;}expected=(u8)(value>>(8*(i&3)));if(actor[i]!=expected)return 5;}
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u8*)',all_actor_and_global_bytes_checked=True,all_helper_arguments_checked=True,setter_observations_checked=True,variadic_query_prototype=True,private_outgoing_home_mutation_portable_claimed=False)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
