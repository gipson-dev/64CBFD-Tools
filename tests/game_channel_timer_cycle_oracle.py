"""Channel timer cycle: original instruction, alias and SDK32 semantics.

No static caller is asserted. Negative scripted RNG returns extend the real
helper's nonnegative range; successful portable cases keep table indices valid.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_channel_timer_cycle_match as source
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
MODE,INDEX,TIMER,TICKS,TABLE,RNG,SEED=0x800D1928,0x800D192C,0x800427F0,0x800BE9E4,0x8009BD10,0x151EF610,0x80091970
SYMS=dict(D_800D1928=MODE,D_800D192C=INDEX,D_800427F0=TIMER,D_800BE9E4=TICKS,D_8009BD10=TABLE,func_151EF610=RNG)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def next_seed(n):return u32(u32(n*4+2)*u32(n*4+3))>>2
def remainder(n):
 n=signed(n);return (abs(n)%7)*(-1 if n<0 else 1)
@dataclass(frozen=True)
class Case:
 mode:int=2
 timer:int=1001
 ticks:int=256
 byte:int=255
 index:int=0
 random:int=0
 actor:int=0x28000
 mutate:bool=False
 connected:bool=False
 seed:int=0x12345678
 phase:int=0

def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base in (c.actor if c.actor else 0x28000,*s.values(),SEED):
  if base==s['func_151EF610']:continue
  m.update({u32(base+i):(i*13+0xA5)&255 for i in range(-16,544)})
 for name,value in [('D_800D1928',c.mode),('D_800D192C',c.index),('D_800427F0',c.timer),('D_800BE9E4',c.ticks)]:put(m,s[name],u32(value))
 for i,n in enumerate((0,1,2,3,4,0,0,0)):put(m,s['D_8009BD10']+4*i,n)
 put(m,SEED,c.seed)
 if c.actor:put(m,c.actor+0x135,c.byte,1)
 return m

def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def effect(m,c,s):
 if c.mutate:
  for name,v in [('D_800D1928',0),('D_800D192C',0x7FFFFFF0),('D_800427F0',77),('D_800BE9E4',0x80000000)]:put(m,s[name],v)
  put(m,s['D_8009BD10'],0x11223344);put(m,c.actor+0x134,0xEE,1)
 if c.connected:put(m,SEED,next_seed(read(m,SEED)))

def reference(initial,c,s=SYMS):
 m=dict(initial);observations=[];mode=read(m,s['D_800D1928'])
 if mode and c.actor:
  timer=signed(read(m,s['D_800427F0']))
  if mode==1:put(m,c.actor+0x1FF,int(timer>=1000),1)
  else:
   index=signed(read(m,s['D_800D192C']))
   if timer>1000 and signed(u32(m[c.actor+0x135]-read(m,s['D_800BE9E4'])))<0:
    index=signed(index+1)
    if index>=5:index=0
    assert 0<=index<8,('fixture-table-domain',index,c)
    put(m,c.actor+0x134,read(m,s['D_8009BD10']+4*index),1)
    observations.append(public(m))
    random=next_seed(read(m,SEED))if c.connected else c.random
    effect(m,c,s)
    put(m,c.actor+0x135,remainder(random)+4,1);put(m,s['D_800D192C'],u32(index))
  put(m,s['D_800427F0'],0)
 return m,observations

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.early=[]
  conn=None
  if c.connected:
   assert not c.mutate
   rom=(r/'conker/conker.us.bin').read_bytes();conn=dict(zip(range(RNG,RNG+48,4),struct.unpack_from('>12I',rom,0x21CAC0)))
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.actor,),connected=conn)
  self.before=self.r[:];self.saved_f=self.f[20:]
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
  assert t==self.syms['func_151EF610'],('unknown-call',hex(t))
  self.calls.append((t,()));self.events.append(('CALL',t,()));self.early.append(public(self.memory))
 def hook(self,t):
  assert t==self.syms['func_151EF610']
  effect(self.memory,self.c,self.syms)
  for i in range(4):self.put(self.r[29]+i*4,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=u32(self.c.random)

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.early
def check(m,c,s=SYMS):
 want,early=reference(fixture(c,s),c,s)
 assert public(m.memory)==public(want),('public-state',c)
 assert m.early==early,('RNG-store-order',c)
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28] and m.r[30]==m.before[30] and m.f[20:]==m.saved_f,('ABI-preservation',c)

def corpus():
 for mode,timer,ticks,index,mutate in itertools.product((0,1,2,-1),(0,999,1000,1001,-1,0x80000000,0x7FFFFFFF),(0,255,256),range(5),(False,True)):
  yield Case(mode,timer,ticks,255,index,0xFFFFFFFF,mutate=mutate)
 for byte in range(256):
  for ticks in(byte,byte+1,0x80000000,0x7FFFFFFF):yield Case(byte=byte,ticks=ticks,index=byte%5,random=u32(byte*0x1020304),phase=8*(byte&1))
 for random in (0,1,6,7,8,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
  for index in range(5):yield Case(random=random,index=index,mutate=True)
 for mode in(0,1,2,-1):yield Case(mode=mode,actor=0)
 for base in(TIMER,MODE,INDEX,TICKS,TABLE):
  for off in(0x134,0x135,0x1FF):
   for mode in(1,2):yield Case(mode=mode,actor=base-off,byte=0,index=0,mutate=True)
 for n in range(128):yield Case(connected=True,seed=u32(n*0x1020304),index=n%5)

def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();hv=set();n=0
 for c in corpus():
  ms=[Oracle(w,fixture(c),c).run()for w in ws]
  for m in ms:check(m,c)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c
  visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));hv.update(ms[0].visits&set(range(RNG,RNG+48,4)));n+=1
 assert len(visits)==58,sorted((p-ENTRY)//4 for p in set(range(ENTRY,ENTRY+232,4))-visits)
 cuts=delays=0
 for c in(Case(mode=0),Case(actor=0),Case(mode=1,timer=999),Case(mode=1),Case(ticks=0),Case(index=4,mutate=True),Case(index=0,random=0x80000000)):
  baseline=Oracle(ws[0],fixture(c),c).run()
  for cut in range(baseline.accesses):
   ms=[Oracle(w,fixture(c),c)for w in ws]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective fault cutoff')
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for i,entry in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  s={k:(entry+0x20000 if k=='func_151EF610' else 0x60007FFC+j*0x10000) for j,k in enumerate(SYMS)}
  bw=[linked(p,'rebased-%d-%d'%(i,j),entry,s)for j,p in enumerate(objects)]
  for c in(Case(),Case(mode=1),Case(index=4,mutate=True)):
   ms=[Oracle(w,fixture(c,s),c,entry,s).run()for w in bw]
   for m in ms:check(m,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),original_RNG_words=12,helper_words_visited=len(hv),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,complete_register_memory_trace_and_fault_context_equal=True,actor_global_aliases=True,captured_index_survives_RNG_mutation=True,negative_RNG_results_are_bounded_extension_cases=True)

def controls(body):
 edits={'negative-mode':('D_800D1928 != 0','D_800D1928 > 0'),'mode-route':('D_800D1928 == 1','D_800D1928 == 2'),'gate-threshold':('D_800427F0 < 1000','D_800427F0 <= 1000'),'cycle-threshold':('D_800427F0 > 1000','D_800427F0 >= 1000'),'remaining-zero':('remaining < 0','remaining <= 0'),'unsigned-remaining':('remaining < 0','(u32)remaining > 0'),'cycle-length':('index >= 5','index >= 4'),'table-value':('D_8009BD10[index];','D_8009BD10[index] + 1;'),'random-modulus':('() % 7 + 4','() % 6 + 4'),'unsigned-remainder':('func_151EF610() % 7','(u32)func_151EF610() % 7'),'random-base':('() % 7 + 4','() % 7 + 3'),'captured-index':('D_800D192C = index;','D_800D192C = (s32)((u32)D_800D192C + 1);'),'clear-scope':('D_800427F0 = 0;','if (D_800D1928 == 1) D_800427F0 = 0;')}
 result={}
 for name,(a,b)in edits.items():assert body.count(a)==1,(name,a);result[name]=body.replace(a,b,1)
 return result

def compiled_controls():
 effective={};cases=[Case(mode=mode,timer=timer,ticks=ticks,index=index,random=random,mutate=True)for mode,timer,ticks,index,random in itertools.product((-1,1,2),(999,1000,1001),(254,255,256,0x80000000,0x7FFFFFFF),(0,3,4),(6,0xFFFFFFFF))]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag;words=linked(obj,'IDO-linked-'+name)
  for c in cases:
   m=Oracle(words,fixture(c),c).run()
   try:check(m,c)
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]in('public-state','RNG-store-order'),(name,e);effective[name]='semantic disagreement';break
  else:raise AssertionError('Ineffective compiled control '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_failures_counted=False)

def caller_suite():
 rom=source.snapshot(o)['conker/conker.us.bin'];entry=ENTRY
 transfers={kind:[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==(op|((entry>>2)&0x3FFFFFF)).to_bytes(4,'big')]for kind,op in(('JAL',0x0C000000),('J',0x08000000))}
 pointer=entry.to_bytes(4,'big');occurrences=[];start=0
 while True:
  at=rom.find(pointer,start)
  if at<0:break
  occurrences.append(at);start=at+1
 assert not any(transfers.values())and not occurrences
 # Effective census controls use deliberately injected encodings, not callers.
 fake=bytearray(rom[:32]);fake[4:8]=(0x0C000000|((entry>>2)&0x3FFFFFF)).to_bytes(4,'big');fake[13:17]=pointer
 assert fake.find(pointer)==13 and int.from_bytes(fake[4:8],'big')&0x3FFFFFF==(entry>>2)&0x3FFFFFF
 return dict(ROM_bytes=len(rom),aligned_JAL=transfers['JAL'],aligned_J=transfers['J'],all_byte_pointer_occurrences=occurrences,effective_census_controls=2,original_caller_found=False,unreachable_claimed=False,ABI='one optional actor pointer in a0; no consistent return value',portable_table_domain='successful accesses limited to initialized cycle indices 0 through 4')

def native_harness(body):
 return r'''
#include <ultra64.h>
typedef struct {u8 pad0[0x400];s32 timer;u8 p1[12];s32 ticks;u8 p2[12];s32 mode,index;u8 p3[24];s32 table[8];u8 p4[32];u32 seed;u8 tail[0xB7C];} Arena;
typedef char ArenaSize[sizeof(Arena)==0x1000?1:-1];
typedef char TimerOffset[__builtin_offsetof(Arena,timer)==0x400?1:-1];
typedef char IndexOffset[__builtin_offsetof(Arena,index)==0x424?1:-1];
typedef char TableOffset[__builtin_offsetof(Arena,table)==0x440?1:-1];
static Arena arena,expected,preRng;static u32 scripted;static int mutate,connected,calls,wantCalls,earlyError;static u8 *active;
#define D_800D1928 arena.mode
#define D_800D192C arena.index
#define D_800427F0 arena.timer
#define D_800BE9E4 arena.ticks
#define D_8009BD10 arena.table
static int same(const Arena *a,const Arena *b){const u8 *x=(const u8*)a,*y=(const u8*)b;int i;for(i=0;i<4096;i++)if(x[i]!=y[i])return 0;return 1;}
static u32 randomNext(u32 n){u32 a=n*4+2,b=n*4+3;return(a*b)>>2;}
static void sideEffect(Arena *a,u8 *actor){if(mutate){a->mode=0;a->index=0x7FFFFFF0;a->timer=77;a->ticks=(s32)0x80000000u;a->table[0]=0x11223344;actor[0x134]=0xEE;}if(connected)a->seed=randomNext(a->seed);}
__attribute__((noinline)) s32 func_151EF610(void){s32 v=(s32)(connected?randomNext(arena.seed):scripted);calls++;if(!same(&arena,&preRng))earlyError=1;sideEffect(&arena,active);return v;}
'''+body+r'''
static void model(u8 *actor){s32 mode=expected.mode;wantCalls=0;if(mode&&actor){s32 timer=expected.timer;if(mode==1){actor[0x1FF]=(u8)(timer>=1000);}else{u32 idx=(u32)expected.index;u32 diff=(u32)actor[0x135]-(u32)expected.ticks;if(timer>1000&&(diff&0x80000000u)){u32 v;idx++;if((s32)idx>=5)idx=0;actor[0x134]=(u8)expected.table[idx];preRng=expected;wantCalls++;v=connected?randomNext(expected.seed):scripted;sideEffect(&expected,actor);actor[0x135]=(u8)(((v&0x80000000u)?-(s32)((0u-v)%7):(s32)(v%7))+4);expected.index=(s32)idx;}}expected.timer=0;}}
static int one(s32 mode,s32 timer,s32 ticks,int byte,int index,int position){int i;u8 *p=(u8*)&arena;u8 *q;for(i=0;i<4096;i++)p[i]=(u8)(i*13+0xA5);arena.mode=mode;arena.timer=timer;arena.ticks=ticks;arena.index=index;for(i=0;i<8;i++)arena.table[i]=i<5?i:0;arena.seed=0x12345678u+(u32)byte;active=position<0?NULL:p+position;if(active)active[0x135]=(u8)byte;expected=arena;q=position<0?NULL:(u8*)&expected+position;model(q);calls=earlyError=0;func_15080348(active);if(earlyError)return 1;if(calls!=wantCalls)return 2;if(!same(&arena,&expected))return 3;return 0;}
static int run(void){static const s32 times[]={-1,0,999,1000,1001,0x7FFFFFFF,(s32)0x80000000u};static const u32 randoms[]={0,6,7,8,0x7FFFFFFF,0x80000000u,0xFFFFFFFFu};static const int aliases[]={0x400-0x134,0x420-0x134,0x424-0x135,0x410-0x135,0x440-0x134,0x400-0x1FF};int b,t,k,mode,result,alias;
for(b=0;b<256;b++)for(t=0;t<7;t++)for(k=0;k<5;k++)for(mode=-1;mode<=2;mode++){scripted=randoms[b%7];mutate=b&1;connected=(b%11)==0;result=one(mode,times[t],(b&4)?(s32)0x80000000u:(b&8)?0x7FFFFFFF:(b&16)?(b?b-1:0):(b&2)?b+1:b,b,k,0x100);if(result)return result;}
for(alias=0;alias<6;alias++)for(t=0;t<7;t++)for(mode=1;mode<=2;mode++){scripted=0xFFFFFFFFu;mutate=1;connected=0;result=one(mode,times[t],256,0,0,aliases[alias]);if(result)return result;}
for(mode=-1;mode<=2;mode++){result=one(mode,1001,256,0,0,-1);if(result)return result;}return 0;}
'''+START

def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=35928,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in(1,2,3),(name,code);effective[name]=code
 return dict(cases_per_profile=35928,profiles=profiles,SDK32_layout=True,whole_arena_canaries_checked=True,native_endian_actor_global_aliases=True,RNG_algorithm_independently_reconstructed=True,negative_RNG_values_are_bounded_extension_cases=True,negative_controls=len(effective),effective_native_controls=effective,portable_table_indices_valid=True)
