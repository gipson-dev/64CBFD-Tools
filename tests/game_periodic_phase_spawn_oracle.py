"""Periodic phase spawn: unsigned remainders, live fields and bounded break7 paths."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,signed
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-periodic-phase-spawn-match';F='func_150D2374';ENTRY=0x150D2374;BODY=212;ACTOR=0x30000;MARK=0x70000
SYMS=dict(D_800BE9E4=0x800BE9E4,func_150ADA20=0x150ADA20,func_150D2110=0x150D2110)
u32=lambda n:n&0xFFFFFFFF
short=lambda n:((n&65535)^32768)-32768
PAIRS=((0x3F800000,0x40200000),(0,0x80000000),(1,0x80000001),(0x7F7FFFFF,0xFF7FFFFF),(0x7F800000,0xFF800000),(0x7FC12345,0xFFC54321))
class Break7(Exception):pass
@dataclass(frozen=True)
class Case:
 timer:int=0
 ticks:int=1
 lifeRange:int=20
 delayRange:int=10
 random:int=1
 mutation:int=0
 phase:int=0
 baseDelay:int=5
 baseLifetime:int=300
 pair:int=0
 color0:int=0x80
 color1:int=0xFF
 priority:int=0xE1
 owner:int=0x87
def random_value(c,n):return((0,0),(1,2),(0x7FFFFFFF,0x80000000),(0xFFFFFFFF,0xFFFFFFFE),(0x12345678,0x87654321))[c.random][n-1]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(96)})
 for at,v in((0x28,c.baseDelay),(0x2C,c.delayRange),(0x30,c.timer),(0x38,PAIRS[c.pair][0]),(0x3C,PAIRS[c.pair][1])):put(m,ACTOR+at,v)
 put(m,ACTOR+0x34,c.baseLifetime,2);put(m,ACTOR+0x36,c.lifeRange,2)
 for at,v in((0x40,c.color0),(0x41,c.color1),(0xC,c.priority),(1,c.owner)):m[ACTOR+at]=v
 put(m,s['D_800BE9E4'],c.ticks);put(m,MARK,0);return m
def effect(m,c,kind,n,s=SYMS):
 if kind=='random'and n==1:
  if c.mutation==1:
   put(m,ACTOR+0x34,0xFFF9,2);put(m,ACTOR+0x36,3,2);put(m,ACTOR+0x38,0x80000000);put(m,ACTOR+0x3C,0x7FC12345);m[ACTOR+0x40]=0xFE;m[ACTOR+0x41]=0x81;m[ACTOR+0xC]=0x80;m[ACTOR+1]=0xFF;put(m,s['D_800BE9E4'],0xFFFFFFFF)
  if c.mutation==5:put(m,ACTOR+0x36,0xFFFF,2)
 if kind=='factory':
  if c.mutation==2:put(m,ACTOR+0x28,0xFFFFFFF0);put(m,ACTOR+0x2C,0x20);put(m,ACTOR+0x30,0x12345678)
  if c.mutation==4:put(m,ACTOR+0x36,0xFFFF,2);put(m,ACTOR+0x30,0x87654321)
  if c.mutation==6:put(m,ACTOR+0x28,0x88888888);put(m,ACTOR+0x2C,0xFFFFFFFF);put(m,ACTOR+0x30,0x13579BDF)
 if kind=='random'and n==2 and c.mutation==3:put(m,ACTOR+0x28,0xFFFFFFFE);put(m,ACTOR+0x2C,3);m[ACTOR+0xC]=0xFE;m[ACTOR+1]=1
 put(m,MARK,{'random':0x10000,'factory':0x20000}[kind]|n)
def observation(m):return tuple(read(m,ACTOR+at,n)for at,n in((0x30,4),(0x28,4),(0x2C,4),(0x34,2),(0x36,2),(0x38,4),(0x3C,4)))
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[];value=u32(read(m,ACTOR+0x30)-read(m,s['D_800BE9E4']));put(m,ACTOR+0x30,value)
 if signed(value)>=0:return m,calls,observations,None
 calls.append((s['func_150ADA20'],()));observations.append(observation(m));effect(m,c,'random',1,s);divisor=u32(short(read(m,ACTOR+0x36,2))+1)
 if not divisor:return m,calls,observations,0x78
 lifetime=u32(short(u32(random_value(c,1)%divisor+short(read(m,ACTOR+0x34,2)))));args=(lifetime,read(m,ACTOR+0x38),read(m,ACTOR+0x3C),m[ACTOR+0x40],m[ACTOR+0x41],m[ACTOR+0xC],m[ACTOR+1]);calls.append((s['func_150D2110'],args));observations.append(observation(m));effect(m,c,'factory',1,s)
 calls.append((s['func_150ADA20'],()));observations.append(observation(m));effect(m,c,'random',2,s);divisor=u32(read(m,ACTOR+0x2C)+1)
 if not divisor:return m,calls,observations,0xB8
 put(m,ACTOR+0x30,u32(random_value(c,2)%divisor+read(m,ACTOR+0x28)));return m,calls,observations,None
def native_defined(c):return reference(fixture(c),c)[3]is None
def control_safe(c):return c.lifeRange!=0xFFFF and c.delayRange!=0xFFFFFFFF and c.mutation<5
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.n=0;self.observations=[];self.breaks=[];self.divisions=[];self.target_function_entry=ENTRY if connected else entry;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,))
 def execute(self,word):
  op=word>>26;fn=word&63;rs=word>>21&31;rt=word>>16&31
  if op==0 and fn==13:
   code=word>>16&0x3FF;assert code==7;self.breaks.append((self.current_pc,code));raise Break7
  if op==0 and fn==27:
   numerator,denominator=self.r[rs],self.r[rt]
   if denominator:super().execute(word)
   else:self.hi=numerator;self.lo=0xFFFFFFFF
   self.divisions.append((self.current_pc,numerator,denominator,self.lo,self.hi))
  else:super().execute(word)
 def record_call(self,t):
  n=7 if t==self.syms['func_150D2110']else 1 if t==ENTRY else 0;assert t in(self.syms['func_150D2110'],self.syms['func_150ADA20'],ENTRY);a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.observations.append(observation(self.memory))
 def hook(self,t):
  s=self.syms;assert self.r[29]==STACK+self.case.phase-64;assert read(self.memory,self.r[29]+40)==self.before[16];assert read(self.memory,self.r[29]+44)==getattr(self,'expected_target_ra',self.before[31])
  if t==s['func_150ADA20']:
   if self.n:assert read(self.memory,self.r[29]+52)==ACTOR+0x28
   self.n+=1;effect(self.memory,self.case,'random',self.n,s);value=random_value(self.case,self.n)
  else:assert t==s['func_150D2110'];assert read(self.memory,self.r[29]+52)==ACTOR+0x28;effect(self.memory,self.case,'factory',1,s);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>53I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def cases():
 for args in itertools.product((0,1,0xFFFFFFFF),(0,1,0x80000000),(0,0x7FFF,0x8000,0xFFFE,0xFFFF),(0,0x7FFFFFFF,0xFFFFFFFF),range(4),range(5),(0,8)):yield Case(*args)
 for field in('color0','color1','priority','owner'):
  for byte,phase in itertools.product(range(256),(0,8)):yield replace(Case(),**{field:byte,'phase':phase})
 for pair,mutation,phase in itertools.product(range(len(PAIRS)),range(5),(0,8)):yield Case(pair=pair,mutation=mutation,phase=phase)
 for base,lifetime,rnd,phase in itertools.product((0,0xFFFFFFFF),(0,0x7FFF,0x8000,0xFFFF),(0,2,3),(0,8)):yield Case(baseDelay=base,baseLifetime=lifetime,random=rnd,phase=phase)
 for timer,ticks,phase in itertools.product((0x7FFFFFFF,0x80000000),(0,0x7FFFFFFF,0xFFFFFFFF),(0,8)):yield Case(timer=timer,ticks=ticks,phase=phase)
 for mu,first,second,phase in itertools.product((5,6),(0,0xFFFF),(0,0xFFFFFFFF),(0,8)):yield Case(mutation=mu,lifeRange=first,delayRange=second,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.n,m.observations,m.breaks,m.divisions)
def run(m):
 try:m.run()
 except Break7:pass
 return m
def verify(m,initial,c,s=SYMS):
 want,calls,observations,trap=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c;assert m.breaks==([]if trap is None else[(m.target_function_entry+trap,7)]),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];case_count=0;visited=set();normal=set();trap_counts={0x78:0,0xB8:0}
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=run(Oracle(words,initial,c));verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);case_count+=1
  if machines[0].breaks:trap_counts[machines[0].breaks[0][0]-ENTRY]+=1
  else:normal.update(machines[0].visits)
 assert visited==set(range(ENTRY,ENTRY+BODY,4));assert normal==visited-{ENTRY+0x78,ENTRY+0xB8};prefixes=0
 for c in(Case(timer=1),Case(),Case(mutation=1),Case(mutation=3,phase=8),Case(lifeRange=0xFFFF),Case(delayRange=0xFFFFFFFF)):
  initial=fixture(c);full=run(Oracle(programs[0],initial,c))
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:run(m)
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 c=Case(timer=1);initial={a:b for a,b in fixture(c).items()if STACK-256<=a<STACK+256 or ACTOR+0x30<=a<ACTOR+0x34 or SYMS['D_800BE9E4']<=a<SYMS['D_800BE9E4']+4};sparse=0
 for words in programs:m=run(Oracle(words,initial,c));assert m.calls==[]and read(m.memory,ACTOR+0x30)==0;sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800BE9E4=0x80007FF0+k*0x100000,func_150ADA20=0x10007FF0+k*0x10000,func_150D2110=0x10008000+k*0x10000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for timer,first,second,mu,phase in itertools.product((0,1),(0,0xFFFF),(0,0xFFFFFFFF),(0,1,3),(0,8)):
   c=Case(timer=timer,lifeRange=first,delayRange=second,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in ps:verify(run(Oracle(words,initial,c,s,entry)),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22F068)[0]==ENTRY and rom[0xFF8F8:0xFF900]==bytes(8);window=list(struct.unpack_from('>11I',rom,0x176740));caller_count=0
 caller_source=(r/'conker/src/game/done/game_1765E0.c').read_text();assert 'D_8008A4E8[arg0->unk11](arg0);'in caller_source
 for timer,first,second,mu,phase in itertools.product((0,1),(0,0xFFFF),(0,0xFFFFFFFF),(0,1,3),(0,8)):
  c=Case(timer=timer,lifeRange=first,delayRange=second,mutation=mu,phase=phase);initial=fixture(c);initial[ACTOR+0x11]=48;put(initial,0x8008A4E8+48*4,ENTRY);want,calls,observations,trap=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[0x151492BC]=0;m=Oracle(window,initial,c,entry=0x15149290,connected=code);m.r[16]=0x87654321;m.before=m.r[:];m.expected_target_ra=0x151492B8;m.code=WindowCode(m.code,m);m.code.ends=(0x151492BC,)
   try:m.run()
   except WindowBoundary:assert trap is None
   except Break7:assert trap is not None
   else:raise AssertionError('Missing effect-dispatch/trap boundary')
   assert(public(m.memory),m.calls,m.observations)==(public(want),[(ENTRY,(ACTOR,))]+calls,observations)
   if trap is None:assert m.r[4]==ACTOR and read(m.memory,STACK+c.phase+24)==ACTOR
  caller_count+=1
 skipped=0
 for phase in(0,8):
  c=Case(phase=phase);initial=fixture(c);initial[ACTOR+0x11]=255
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[0x151492BC]=0;m=Oracle(window,initial,c,entry=0x15149290,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(0x151492BC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing skipped effect-dispatch boundary')
   assert public(m.memory)==public(initial)and m.calls==[];skipped+=1
 report=dict(private_only=True,installed=False,matching_credit=0,cases=case_count,executions=case_count*3,compiler_words=53,covered_words=53,normal_covered_words=51,trap_offsets=['0x78','0xB8'],trap_cases={hex(k):v for k,v in trap_counts.items()},slot_words=55,alignment_words=2,frame=64,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,integer_wrapping_and_signed_narrowing=True,live_helper_mutations=True,mixed_float_argument_bits=True,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,registration_table='D_8008A4E8',registration_index=48,registration_ROM='0x22F068',original_caller_windows=[dict(entry='0x15149290',ROM='0x176740',words=11,cases=caller_count,result_ignored=True,callback_installation_precondition=True,complete_parent_claimed=False)],skipped_effect_dispatch_executions=skipped,zero_divisor_guest_model_only=True,native_zero_division_claimed=False,complete_PRNG_or_factory_or_parent_claimed=False,hardware_divzero_state_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150D2374';prefix=selected[:selected.index('typedef struct')];body=selected[selected.index('/* Spawn'):];types=selected[selected.index('typedef struct'):selected.index('/* Spawn')]
 mutants=dict(expiry_boundary=body.replace('< 0)', '<= 0)'),wrong_remainder=body.replace('random %','random /'),lifetime_width=body.replace('(s16)(random','(s8)(random'),duration_order=body.replace('state->activeDuration, state->inactiveDuration','state->inactiveDuration, state->activeDuration'),wrong_color=body.replace('state->activeColor, state->inactiveColor','state->inactiveColor, state->inactiveColor'),wrong_priority=body.replace('owner[0xC], owner[1]','owner[1], owner[1]'),wrong_delay_base=body.replace('state->baseDelay','state->timer'),stale_delay_range=body.replace('u32 random;','u32 random;\n    u32 cachedRange = state->delayRange;').replace('% (state->delayRange + 1U)','% (cachedRange + 1U)'))
 assert all(v!=body for v in mutants.values())
 text=prefix+types+r'''
typedef struct {u32 kind,args[7],obs[7],result;} Call;
typedef struct {u32 timer,ticks,lifeRange,delayRange,random,mutation,baseDelay,baseLifetime,pair,color0,color1,priority,owner,safeControl,finalTicks,mark,count;u8 want[96];Call calls[3];} Fixture;
s32 D_800BE9E4;
static u8 actor[96] __attribute__((aligned(8)));
static const Fixture*current;static u32 callIndex,randomIndex,marker,bad;
static const u32 pairs[6][2]={{0x3F800000,0x40200000},{0,0x80000000},{1,0x80000001},{0x7F7FFFFF,0xFF7FFFFF},{0x7F800000,0xFF800000},{0x7FC12345,0xFFC54321}};
static u32 get32(u32 at){return *(u32*)(actor+at);}static u32 get16(u32 at){return *(u16*)(actor+at);}static void p32(u32 at,u32 v){*(u32*)(actor+at)=v;}static void p16(u32 at,u32 v){*(u16*)(actor+at)=(u16)v;}
static u32 floatBits(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}
static const Call* observe(u32 kind){u32 i;static const u32 offsets[7]={0x30,0x28,0x2C,0x34,0x36,0x38,0x3C};const Call*c;if(callIndex>=current->count){bad=1;return 0;}c=current->calls+callIndex++;if(c->kind!=kind)bad=2;for(i=0;i<7;i++)if(c->obs[i]!=(i==3||i==4?get16(offsets[i]):get32(offsets[i])))bad=3;return c;}
static void effect(u32 kind,u32 n){u32 mu=current->mutation;if(kind==1&&n==1){if(mu==1){p16(0x34,0xFFF9);p16(0x36,3);p32(0x38,0x80000000);p32(0x3C,0x7FC12345);actor[0x40]=0xFE;actor[0x41]=0x81;actor[0xC]=0x80;actor[1]=0xFF;D_800BE9E4=(s32)0xFFFFFFFF;}if(mu==5)p16(0x36,0xFFFF);}if(kind==2){if(mu==2){p32(0x28,0xFFFFFFF0);p32(0x2C,0x20);p32(0x30,0x12345678);}if(mu==4){p16(0x36,0xFFFF);p32(0x30,0x87654321);}if(mu==6){p32(0x28,0x88888888);p32(0x2C,0xFFFFFFFF);p32(0x30,0x13579BDF);}}if(kind==1&&n==2&&mu==3){p32(0x28,0xFFFFFFFE);p32(0x2C,3);actor[0xC]=0xFE;actor[1]=1;}marker=(kind==1?0x10000:0x20000)|n;}
s32 func_150ADA20(void){const Call*c=observe(1);effect(1,++randomIndex);return c?(s32)c->result:1;}
void func_150D2110(s16 a,f32 b,f32 c,u8 d,u8 e,u8 f,s32 g){u32 i,args[7];const Call*want=observe(2);args[0]=(u32)(s32)a;args[1]=floatBits(b);args[2]=floatBits(c);args[3]=d;args[4]=e;args[5]=f;args[6]=(u32)g;if(want)for(i=0;i<7;i++)if(args[i]!=want->args[i])bad=4;effect(2,1);}
'''
 text+='\n'.join(v.replace(F,'test_'+n)for n,v in dict(selected=body,**mutants).items())
 rows=[];cc=0
 for c in q.cases():
  if c.phase or not q.native_defined(c):continue
  initial=q.fixture(c);want,calls,observations,trap=q.reference(initial,c);assert trap is None
  native=bytearray(want[q.ACTOR+i]for i in range(96))
  for at,n in((0x28,4),(0x2C,4),(0x30,4),(0x34,2),(0x36,2),(0x38,4),(0x3C,4)):native[at:at+n]=native[at:at+n][::-1]
  scalar=[c.timer,c.ticks,c.lifeRange,c.delayRange,c.random,c.mutation,c.baseDelay,c.baseLifetime,c.pair,c.color0,c.color1,c.priority,c.owner,int(q.control_safe(c)),q.read(want,q.SYMS['D_800BE9E4']),q.read(want,q.MARK),len(calls)]
  def arr(v):return '{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in v)+'}'
  cr=[];rng=0
  for (address,args),obs in zip(calls,observations):
   israndom=address==q.SYMS['func_150ADA20'];rng+=int(israndom);cr.append('{'+str(1 if israndom else 2)+','+arr(list(args)+[0]*(7-len(args)))+','+arr(obs)+',0x%Xu}'%(q.random_value(c,rng)if israndom else 0))
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in scalar)+','+arr(native)+',{'+','.join(cr)+'}}');cc+=int(q.control_safe(c))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Fn)(u8*);
static s32 check(Fn fn,s32 control){u32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;if(control&&!c->safeControl)continue;current=c;callIndex=randomIndex=marker=bad=0;for(i=0;i<96;i++)actor[i]=(u8)(i*29+0x59);p32(0x28,c->baseDelay);p32(0x2C,c->delayRange);p32(0x30,c->timer);p16(0x34,c->baseLifetime);p16(0x36,c->lifeRange);p32(0x38,pairs[c->pair][0]);p32(0x3C,pairs[c->pair][1]);actor[0x40]=(u8)c->color0;actor[0x41]=(u8)c->color1;actor[0xC]=(u8)c->priority;actor[1]=(u8)c->owner;D_800BE9E4=(s32)c->ticks;fn(actor);if(bad||callIndex!=c->count||marker!=c->mark||(u32)D_800BE9E4!=c->finalTicks)return 1;for(i=0;i<96;i++)if(actor[i]!=c->want[i])return 2;}return 0;}
static int run(void){if(sizeof(void*)!=4)return 90;{s32 result=check(test_selected,0);if(result)return 10+result;}
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+',1))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),control_cases=cc,negative_controls=len(mutants))
