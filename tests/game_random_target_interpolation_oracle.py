"""Bounded float32 target interpolation, helper effects and indirect callback ABI."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-random-target-interpolation-match';F='func_1518F384';ENTRY=0x1518F384;ACTOR=0x30000;MARK=0x70000
SYMS=dict(func_150ADA68=0x150ADA68,D_800A7B74=0x800A7B74,D_800A7B78=0x800A7B78)
@dataclass(frozen=True)
class Case:
 first:int=0
 second:int=0
 pattern:int=0
 random:int=1
 mutation:int=0
 phase:int=0
def values(c):
 return((bits(20),bits(-10),bits(3),bits(80),bits(5),bits(-4),bits(7),bits(9)),
 (0x80000000,0,0x80000000,0,0x80000000,0,0x80000000,0),
 (0x7F7FFFFF,0xFF7FFFFF,bits(1),0xFF7FFFFF,0x7F7FFFFF,bits(-1),0x7F7FFFFF,0xFF7FFFFF),
 (0x7F800000,0xFF800000,bits(1),0x7F800000,0x7F800000,bits(2),0xFF800000,0x7F800000),
 (0x7FC12345,bits(-1),0xFFC54321,bits(1),0x7FC67890,bits(3),0x7FC13579,0xFFC24680),
 (1,0x80000001,2,0x80000002,1,0x80000001,3,0x80000003))[c.pattern]
def random_value(c,n):return((0,0),(0x3F000000,0x3F400000),(0x3F800000,0xBF800000),(0x7FC12345,0x7F800000))[c.random][n-1]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(512)})
 for at,value in zip((0x110,0x114,0x118,0x11C,0x120,0x128,0x2C,0x30),values(c)):put(m,ACTOR+at,value)
 put(m,ACTOR+0x12C,c.first,2);put(m,ACTOR+0x12E,c.second,2);put(m,s['D_800A7B74'],0x3EB7CED9);put(m,s['D_800A7B78'],0x3E3E76C9);put(m,MARK,0);return m
def effect(m,c,n,s=SYMS):
 if c.mutation==1 and n==1:
  for at,v in((0x110,bits(40)),(0x114,bits(10)),(0x11C,bits(60)),(0x120,bits(20)),(0x128,bits(13)),(0x2C,bits(-5)),(0x30,bits(6))):put(m,ACTOR+at,v)
  put(m,ACTOR+0x12E,1,2);put(m,s['D_800A7B74'],bits(0.5));put(m,s['D_800A7B78'],bits(0.25))
 elif c.mutation==2 and n==1:
  put(m,ACTOR+0x12E,0,2);put(m,ACTOR+0x11C,bits(-4));put(m,ACTOR+0x120,bits(-8));put(m,ACTOR+0x128,bits(55));put(m,s['D_800A7B74'],bits(1));put(m,s['D_800A7B78'],0x80000000)
 elif c.mutation==3:
  put(m,ACTOR+0x12C,0x8000,2);put(m,ACTOR+0x12E,0,2);put(m,ACTOR+0x2C,bits(n*3));put(m,ACTOR+0x30,bits(n*-2))
 elif c.mutation==4:
  put(m,ACTOR+0x118,bits(n*17));put(m,ACTOR+0x128,bits(n*-11));put(m,s['D_800A7B74'],0);put(m,s['D_800A7B78'],bits(1))
 put(m,MARK,n)
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[];n=0
 for flag,upper,lower,target in((0x12C,0x110,0x114,0x118),(0x12E,0x11C,0x120,0x128)):
  if read(m,ACTOR+flag,2)==0:
   observations.append(tuple(read(m,ACTOR+x)for x in(0x118,0x128,0x2C,0x30)));calls.append((s['func_150ADA68'],()));n+=1;effect(m,c,n,s);lo=read(m,ACTOR+lower);hi=read(m,ACTOR+upper);put(m,ACTOR+flag,1,2);put(m,ACTOR+target,add(mul(random_value(c,n),sub(hi,lo)),lo))
 current=read(m,ACTOR+0x30);target=read(m,ACTOR+0x128);first_current=read(m,ACTOR+0x2C);put(m,ACTOR+0x30,add(current,mul(sub(target,current),read(m,s['D_800A7B74']))));put(m,ACTOR+0x2C,add(first_current,mul(sub(read(m,ACTOR+0x118),first_current),read(m,s['D_800A7B78']))));return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.n=0;self.observations=[];self.target_function_entry=ENTRY if connected else entry;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,))
 def record_call(self,t):
  assert t in(self.syms['func_150ADA68'],ENTRY);a=(ACTOR,)if t==ENTRY else();self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.observations.append(tuple(read(self.memory,ACTOR+x)for x in(0x118,0x128,0x2C,0x30)))
 def hook(self,t):
  assert t==self.syms['func_150ADA68'];assert self.r[29]==STACK+self.case.phase-32;assert read(self.memory,self.r[29]+20)==getattr(self,'expected_target_ra',self.before[31]);assert read(self.memory,self.r[29]+32)==ACTOR
  if self.r[31]==self.target_function_entry+0x60:assert read(self.memory,self.r[29]+24)==ACTOR+0x110
  self.n+=1;effect(self.memory,self.case,self.n,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=random_value(self.case,self.n)
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>54I',sections(p.with_suffix('.elf'))['.text'][1][:216]))
def cases():
 for args in itertools.product((0,1,0xFFFF,0x8000),(0,1,0xFFFF,0x8000),range(6),range(4),range(5),(0,8)):yield Case(*args)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.n,m.observations)
def verify(m,initial,c,s=SYMS):
 want,calls,observations=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations,m.r[2])==(public(want),calls,observations,1),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];case_count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);case_count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));prefixes=0
 for c in(Case(first=1,second=1),Case(),Case(mutation=1),Case(first=0,second=1,mutation=2,phase=8),Case(pattern=4,mutation=4)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 sparse=0;c=Case(first=1,second=1);initial=fixture(c);needed={ACTOR+x+i for x,n in((0x12C,4),(0x118,4),(0x128,4),(0x2C,8))for i in range(n)}|{a+i for a in(SYMS['D_800A7B74'],SYMS['D_800A7B78'])for i in range(4)};initial={a:b for a,b in initial.items()if a in needed or STACK-256<=a<STACK+256}
 for words in programs:m=Oracle(words,initial,c).run();assert m.calls==[]and m.r[2]==1;sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(func_150ADA68=0x10007FF0+k*0x10000,D_800A7B74=0x80007FF0+k*0x100000,D_800A7B78=0x80018000+k*0x100000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for first,second,pattern,mu,phase in itertools.product((0,0xFFFF),(0,0x8000),(0,4),(0,2,4),(0,8)):
   c=Case(first=first,second=second,pattern=pattern,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E850)[0]==ENTRY;window=list(struct.unpack_from('>5I',rom,0x141390));caller_count=0
 for first,second,mu,phase in itertools.product((0,0xFFFF),(0,0x8000),(0,1,2,4),(0,8)):
  c=Case(first=first,second=second,mutation=mu,phase=phase);initial=fixture(c);put(initial,ACTOR+0x38,ENTRY);want,calls,observations=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+216,4),words));code[0x15113EF4]=0;m=Oracle(window,initial,c,entry=0x15113EE0,connected=code);m.r[16]=ACTOR;m.r[30]=7;m.before=m.r[:];m.expected_target_ra=0x15113EF0;m.code=WindowCode(m.code,m);m.code.ends=(0x15113EF4,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing callback boundary')
   assert(public(m.memory),m.calls,m.observations,m.r[30])==(public(want),[(ENTRY,(ACTOR,))]+calls,observations,8)
  caller_count+=1
 report=dict(private_only=True,installed=False,matching_credit=0,cases=case_count,executions=case_count*3,covered_words=54,frame=32,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,quiet_NaN_and_float_boundaries=True,helper_field_and_constant_mutations=True,helper_boundary_observations=True,providers_bounded=True,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,registration_table='D_80089D60',registration_index=12,registration_ROM='0x22E850',original_caller_windows=[dict(entry='0x15113EE0',ROM='0x141390',words=5,cases=caller_count,result_ignored=True,callback_installation_precondition=True,complete_parent_claimed=False)],hardware_FCSR_or_complete_random_or_parent_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_1518F384';prefix=selected[:selected.index('/* Initialize')];body=selected[selected.index('/* Initialize'):]
 cached=body.replace('D_800A7B74','cachedSecond').replace('D_800A7B78','cachedFirst').replace('    RandomTargets1BA1D0 *targets =','    f32 cachedSecond = D_800A7B74;\n    f32 cachedFirst = D_800A7B78;\n    RandomTargets1BA1D0 *targets =')
 mutants=dict(inverted_first=body.replace('targets->firstReady == 0','targets->firstReady != 0'),inverted_second=body.replace('targets->secondReady == 0','targets->secondReady != 0'),wrong_range=body.replace('targets->firstUpper - targets->firstLower','targets->firstUpper + targets->firstLower'),wrong_target=body.replace('targets->secondTarget =','targets->firstTarget ='),missing_ready=body.replace('targets->firstReady = 1','targets->firstReady = 0'),cached_factors=cached,wrong_coordinate=body.replace('(targets->firstTarget -','(targets->secondTarget -'),wrong_result=body.replace('return 1;','return 0;'));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
 typedef struct{u32 first,second,random,mutation,before[8],after[8],wantFirst,wantSecond,factors[2],calls,observations[8];} Fixture;
 static const Fixture*current;static u8 actor[512] __attribute__((aligned(8)));f32 D_800A7B74,D_800A7B78;static u32 calls,marker,badArgs;
 static const u32 offsets[]={0x110,0x114,0x118,0x11C,0x120,0x128,0x2C,0x30};
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static u32 floatBits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 static s32 isNan(u32 u){return(u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu)!=0;}
 static s32 equal(u32 a,u32 b){return a==b||(isNan(a)&&isNan(b));}
 static void set(u32 offset,f32 f){*(f32*)(actor+offset)=f;}
 static void effect(u32 n){u32 mode=current->mutation;
  if(mode==1&&n==1){set(0x110,40.0f);set(0x114,10.0f);set(0x11C,60.0f);set(0x120,20.0f);set(0x128,13.0f);set(0x2C,-5.0f);set(0x30,6.0f);*(s16*)(actor+0x12E)=1;D_800A7B74=0.5f;D_800A7B78=0.25f;}
  else if(mode==2&&n==1){*(s16*)(actor+0x12E)=0;set(0x11C,-4.0f);set(0x120,-8.0f);set(0x128,55.0f);D_800A7B74=1.0f;D_800A7B78=asFloat(0x80000000u);}
  else if(mode==3){*(s16*)(actor+0x12C)=(s16)0x8000;*(s16*)(actor+0x12E)=0;set(0x2C,(f32)(n*3));set(0x30,(f32)(-(s32)n*2));}
  else if(mode==4){set(0x118,(f32)(n*17));set(0x128,(f32)(-(s32)n*11));D_800A7B74=0.0f;D_800A7B78=1.0f;}
  marker=n;
 }
 f32 func_150ADA68(void){static const u32 results[4][2]={{0,0},{0x3F000000,0x3F400000},{0x3F800000,0xBF800000},{0x7FC12345,0x7F800000}};static const u32 observedOffsets[]={0x118,0x128,0x2C,0x30};u32 i,n=calls++;if(n>=current->calls||n>=2){badArgs=1;return 0.0f;}for(i=0;i<4;i++)if(!equal(*(u32*)(actor+observedOffsets[i]),current->observations[n*4+i]))badArgs=1;effect(n+1);return asFloat(results[current->random][n]);}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls,observations=q.reference(initial,c);obs=[v for row in observations for v in row]+[0]*(8-4*len(observations));before=[q.read(initial,q.ACTOR+x)for x in(0x110,0x114,0x118,0x11C,0x120,0x128,0x2C,0x30)];after=[q.read(want,q.ACTOR+x)for x in(0x110,0x114,0x118,0x11C,0x120,0x128,0x2C,0x30)]
  row=[c.first,c.second,c.random,c.mutation,before,after,q.read(want,q.ACTOR+0x12C,2),q.read(want,q.ACTOR+0x12E,2),[q.read(want,q.SYMS[x])for x in('D_800A7B74','D_800A7B78')],len(calls),obs];rows.append(row)
 def literal(x):return'{'+','.join(literal(v)for v in x)+'}'if isinstance(x,list)else'0x%08Xu'%x
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(literal(x)for x in rows)+'\n};\n'
 text+=r'''
 typedef s32(*Fn)(u8*);
 static s32 check(Fn fn){u32 n,i,j,skip;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;for(i=0;i<512;i++)actor[i]=(u8)(i*29+0x59);for(i=0;i<8;i++)*(u32*)(actor+offsets[i])=c->before[i];*(s16*)(actor+0x12C)=(s16)c->first;*(s16*)(actor+0x12E)=(s16)c->second;D_800A7B74=asFloat(0x3EB7CED9u);D_800A7B78=asFloat(0x3E3E76C9u);calls=marker=badArgs=0;
  if(fn(actor)!=1||badArgs||calls!=c->calls||marker!=calls||(u16)*(s16*)(actor+0x12C)!=c->wantFirst||(u16)*(s16*)(actor+0x12E)!=c->wantSecond)return 1;
  if(floatBits(D_800A7B74)!=c->factors[0]||floatBits(D_800A7B78)!=c->factors[1])return 2;
  for(i=0;i<8;i++)if(!equal(*(u32*)(actor+offsets[i]),c->after[i]))return 3;
  for(i=0;i<512;i++){skip=i>=0x12C&&i<0x130;for(j=0;j<8;j++)if(i>=offsets[j]&&i<offsets[j]+4)skip=1;if(!skip&&actor[i]!=(u8)(i*29+0x59))return 4;}
  }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(RandomTargets1BA1D0)!=32)return 90;{s32 result=check(test_selected);if(result)return 10+result;}
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
