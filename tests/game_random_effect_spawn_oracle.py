"""Direct random effect spawn: hard-float ABI, defined descriptor bytes and providers.

Guest execution retains all forty copied bytes, including seeded private padding.
Native validation reads only initialized descriptor fields; it makes no portable
claim about the values of automatic padding or untouched descriptor bytes.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_random_effect_spawn_match as source
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
RNG,SPAWN,FACTORY,SETTER,SEED=0x151EF610,0x1513C5B0,0x1513C350,0x1513E13C,0x80091970
RESULT,COPIED=0x30000,0x40000
SYMS=dict(func_151EF610=RNG,func_1513C5B0=SPAWN)
FLOATS=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)
RANDOMS=(0,1,4095,4096,4097,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFEFFF,0xFFFFF000,0xFFFFF001,0xFFFFFFFF)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def next_seed(n):return u32(u32(n*4+2)*u32(n*4+3))>>2
def phase(n):
 n=signed(n);rem=(abs(n)%4096)*(-1 if n<0 else 1);return rem+0x4000
@dataclass(frozen=True)
class Case:
 random:int=0
 x:int=0x3F800000
 y:int=0x80000000
 z:int=0x7FA12345
 allocated:bool=True
 connected_rng:bool=False
 seed:int=0
 phase:int=0
def home(c):return STACK+c.phase
def value(c):return next_seed(c.seed)if c.connected_rng else c.random
def expected_fields(c):
 m={};put(m,0,0x20014);put(m,4,1,2);put(m,6,0x38,1);put(m,8,0);put(m,12,phase(value(c)))
 for i,v in enumerate((255,255,0,0,0,255)):put(m,16+i,v,1)
 put(m,24,0x30001);return m
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,n in((RESULT-16,320),(COPIED-16,72),(SEED-4,12)):
  m.update({base+i:0xA5 for i in range(n)})
 put(m,SEED,c.seed);return m
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def helpers(c):
 rom=(r/'conker/conker.us.bin').read_bytes();result={}
 for va,at,n in((SPAWN,0x169A60,40),)+(((RNG,0x21CAC0,12),)if c.connected_rng else()):
  result.update(zip(range(va,va+4*n,4),struct.unpack_from('>%dI'%n,rom,at)))
 return result
class WindowBoundary(Exception):pass
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.descriptors=[];self.early=[];self.window_stop=None
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(0x87654321,0xFEDCBA98,c.z),connected=connected)
  self.f[12],self.f[14]=c.x,c.y;self.r[6]=c.z;self.before=self.r[:];self.saved_f=self.f[20:]
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
 def execute(self,w):
  if self.current_pc==self.window_stop:raise WindowBoundary
  super().execute(w)
 def record_call(self,t):
  counts={self.syms['func_151EF610']:0,self.syms['func_1513C5B0']:14,FACTORY:11,SETTER:7,ENTRY:3};assert t in counts,('unknown-call',hex(t))
  a=(self.f[12],self.f[14],self.r[6])if t==ENTRY else tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_151EF610']:
   p=home(self.c)-40;assert self.memory[p+6]==0x38 and read(self.memory,p+8)==0,('early-descriptor',);self.early.append((p,self.memory[p+6],read(self.memory,p+8)))
  if t==self.syms['func_1513C5B0']:
   self.validate_descriptor(a[0]);want=(a[0],0,0,0,self.c.x,self.c.y,self.c.z,0x42DC0000,0x42DC0000,0,0,0,255,0);assert a==want,('spawn-packet',a,want)
 def validate_descriptor(self,p):
  assert p==home(self.c)-40,('descriptor-address',hex(p),hex(home(self.c)-40))
  expected=expected_fields(self.c);assert all(self.memory[p+i]==v for i,v in expected.items()),('descriptor-fields',[(i,self.memory[p+i],v)for i,v in expected.items()if self.memory[p+i]!=v])
  self.descriptors.append(bytes(self.memory[p+i]for i in range(40)))
 def hook(self,t):
  a=self.calls[-1][1];c=self.c
  if t==self.syms['func_151EF610']:v=value(c)
  elif t==FACTORY:
   assert a==(home(c)-40,0,0,0,0,0,0,0,0,255,0),('factory-packet',a)
   self.validate_descriptor(a[0]);v=RESULT if c.allocated else 0
   if c.allocated:
    for i in range(40):put(self.memory,COPIED+i,self.memory[a[0]+i],1)
  elif t==SETTER:
   want=(RESULT,c.x,c.y,c.z,0x42DC0000,0x42DC0000,0);assert a==want,('setter-packet',a,want);v=0x76543210
  elif t==self.syms['func_1513C5B0']:
   v=RESULT if c.allocated else 0
   if c.allocated:
    for i in range(40):put(self.memory,COPIED+i,self.memory[a[0]+i],1)
  else:raise AssertionError(('unbounded-call',hex(t)))
  for i in range(4):self.put(self.r[29]+i*4,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=u32(v)
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.descriptors,m.early)
def check(m,c,connected=False):
 assert m.r[2]==(RESULT if c.allocated else 0),('result',m.r[2]);assert len(m.early)==1 and len(m.descriptors)==(2 if connected else 1)
 want=fixture(c)
 if c.connected_rng:put(want,SEED,next_seed(c.seed))
 if c.allocated:
  for i,v in enumerate(m.descriptors[0]):put(want,COPIED+i,v,1)
 assert public(m.memory)==public(want),('public',)
 assert m.r[29]==home(c)and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f
 if connected:assert sum(t==SETTER for t,a in m.calls)==int(c.allocated)
def corpus():
 for i,(random,allocated,p,phase_)in enumerate(itertools.product(RANDOMS,(False,True),range(12),(0,8))):
  yield Case(random,FLOATS[p],FLOATS[(p+3)%12],FLOATS[(p+7)%12],allocated,False,0,phase_)
 for n in range(256):yield Case(0,FLOATS[n%12],FLOATS[(n+1)%12],FLOATS[(n+2)%12],bool(n&1),True,u32(n*0x1020304),8*(n&1))
def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();hv=set();n=0
 for i,c in enumerate(corpus()):
  conn=helpers(c)if c.connected_rng or i%3==0 else None;ms=[Oracle(w,fixture(c),c,connected=conn).run()for w in ws]
  for m in ms:check(m,c,bool(conn))
  assert state(ms[0])==state(ms[1])==state(ms[2]),c;visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));hv.update(ms[0].visits&set(helpers(c))if conn else set());n+=1
 assert len(visits)==58
 cuts=delays=0
 for c in(Case(),Case(0xFFFFFFFF,allocated=False,phase=8),Case(0x80000000)):
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
  s={k:entry+0x20000+j*0x10000 for j,k in enumerate(SYMS)};bw=[linked(p,'rebased-%d-%d'%(i,j),entry,s)for j,p in enumerate(objects)]
  for c in(Case(),Case(0xFFFFFFFF,allocated=False),Case(0x80000000,phase=8)):
   ms=[Oracle(w,fixture(c),c,entry,s).run()for w in bw]
   for m in ms:check(m,c)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),original_provider_words=40,original_RNG_words=12,helper_words_visited=len(hv),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,complete_register_memory_trace_and_fault_context_equal=True,hard_float_f12_f14_a2=True,guest_all40_descriptor_bytes_equal=True,portable_padding_value_equality_claimed=False,negative_RNG_results_are_bounded_extension_cases=True,bounded_factory_and_setter=True)
def controls(body):
 edits={'category':('descriptor.category = 0x38','descriptor.category = 0x39'),'zero-field':('descriptor.zero = 0','descriptor.zero = 1'),'unsigned-remainder':('random % 0x1000','(u32)random % 0x1000'),'modulus':('random % 0x1000','random % 0x800'),'phase-base':('+ 0x4000','+ 0x2000'),'flags':('descriptor.flags = 0x20014','descriptor.flags = 0x20010'),'count':('descriptor.count = 1','descriptor.count = 2'),'color0':('descriptor.color[0] = 255','descriptor.color[0] = 254'),'color5':('descriptor.color[5] = 255','descriptor.color[5] = 0'),'mode':('descriptor.mode = 0x30001','descriptor.mode = 0x30000'),'xyz-order':('0, 0, 0, x, y, z,','0, 0, 0, z, y, x,'),'dimension':('110.0f, 110.0f','100.0f, 110.0f'),'channel':('0, 0, 0, 255, 0);','0, 0, 0, 254, 0);')}
 result={}
 for name,(a,b)in edits.items():assert body.count(a)==1,(name,a);result[name]=body.replace(a,b,1)
 return result
def compiled_controls():
 effective={};cases=[Case(random,0x3F800000,0x40000000,0x40400000)for random in RANDOMS]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag;words=linked(obj,'IDO-linked-'+name)
  for c in cases:
   try:m=Oracle(words,fixture(c),c).run();check(m,c)
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]in('early-descriptor','descriptor-fields','spawn-packet','result','public'),(name,e);effective[name]='descriptor/ABI disagreement';break
  else:raise AssertionError('Ineffective compiled control '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_failures_counted=False)
def native_harness(body):
 text=(r/'conker/src/game_169510.c').read_text().replace('struct210 *func_1513C5B0(', 'void *func_1513C5B0(');a,b=source.function_span(text,'func_1513C5B0');provider=text[a:b].replace('void *func_1513C5B0(','static struct210 *actualSpawn(')
 return source.HEADERS+r'''
typedef char DescriptorBytes[sizeof(RandomEffectDescriptor)==40?1:-1];
typedef char DescriptorModeOffset[__builtin_offsetof(RandomEffectDescriptor,mode)==24?1:-1];
typedef char SDKPointerBytes[sizeof(void*)==4?1:-1];
struct210 *func_1513C350(struct210 *,s32,u8,u8,u8,s32,s32,struct167 *,s32,u8,s32);
void func_1513E13C(struct210 *,f32,f32,f32,f32,f32,u8);
static u32 scripted,seed,expectedRandom,seedStart;static int connectedRng,allocate,error,rngCalls,spawnCalls,factoryCalls,setterCalls;
static u32 wantX,wantY,wantZ;static struct210 record;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static s32 expectedPhase(u32 u){s32 n=(s32)u;return(n>=0?(s32)(u%4096):-(s32)((0u-u)%4096))+0x4000;}
__attribute__((noinline)) s32 func_151EF610(void){rngCalls++;if(connectedRng){u32 a=seed*4+2,b=seed*4+3;seed=(a*b)>>2;return(s32)seed;}return(s32)scripted;}
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
'''+provider+r'''
#pragma GCC diagnostic pop
'''+body+r'''
static int descriptorValid(RandomEffectDescriptor *d){return d->category==0x38&&d->zero==0&&d->phase==expectedPhase(expectedRandom)&&d->flags==0x20014&&d->count==1&&d->color[0]==255&&d->color[1]==255&&d->color[2]==0&&d->color[3]==0&&d->color[4]==0&&d->color[5]==255&&d->mode==0x30001;}
__attribute__((noinline)) struct210 *func_1513C350(struct210 *descriptor,s32 table,u8 tag0,u8 tag1,u8 variant,s32 count,s32 user,struct167 *payload,s32 extra,u8 channel,s32 context){
 factoryCalls++;if(!descriptorValid((RandomEffectDescriptor*)descriptor)||table||tag0||tag1||variant||count||user||payload||extra||channel!=255||context)error=2;
 return allocate?&record:NULL;
}
__attribute__((noinline)) void func_1513E13C(struct210 *p,f32 x,f32 y,f32 z,f32 width,f32 height,u8 request){
 setterCalls++;if(!allocate||p!=&record||word(x)!=wantX||word(y)!=wantY||word(z)!=wantZ||word(width)!=0x42DC0000||word(height)!=0x42DC0000||request)error=3;
}
__attribute__((noinline)) struct210 *func_1513C5B0(s32 descriptor,s32 table,u8 tag0,u8 tag1,f32 x,f32 y,f32 z,f32 width,f32 height,u8 request,u8 variant,s32 extra,u8 channel,s32 context){
 spawnCalls++;if(rngCalls!=1||!descriptorValid((RandomEffectDescriptor*)descriptor)||table||tag0||tag1||word(x)!=wantX||word(y)!=wantY||word(z)!=wantZ||word(width)!=0x42DC0000||word(height)!=0x42DC0000||request||variant||extra||channel!=255||context){error=1;return NULL;}
 return actualSpawn(descriptor,table,tag0,tag1,x,y,z,width,height,request,variant,extra,channel,context);
}
static const u32 floats[12]={0,0x80000000u,1,0x007FFFFFu,0x00800000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u,0x7FA12345u};
static int one(void){struct210 *result;u32 expectedSeed=seedStart;int i;u8 *p=(u8*)&record;union{u32 u;f32 f;}x,y,z;
 seed=seedStart;expectedRandom=connectedRng?((seed*4+2)*(seed*4+3))>>2:scripted;
 if(connectedRng)expectedSeed=expectedRandom;
 for(i=0;i<(int)sizeof(record);i++)p[i]=(u8)(i*13+0xA5);
 rngCalls=spawnCalls=factoryCalls=setterCalls=error=0;x.u=wantX;y.u=wantY;z.u=wantZ;result=func_1500F290(x.f,y.f,z.f);
 if(error)return error;if(result!=(allocate?&record:NULL)||rngCalls!=1||spawnCalls!=1||factoryCalls!=1||setterCalls!=allocate||seed!=expectedSeed)return 4;
 for(i=0;i<(int)sizeof(record);i++)if(p[i]!=(u8)(i*13+0xA5))return 5;return 0;
}
static int run(void){u32 n,p;int sign,result;
 connectedRng=0;seedStart=0x12345678;
 for(n=0;n<8192;n++)for(sign=0;sign<2;sign++)for(p=0;p<12;p++)for(allocate=0;allocate<2;allocate++){
 scripted=sign?0u-n:n;wantX=floats[p];wantY=floats[(p+3)%12];wantZ=floats[(p+7)%12];result=one();if(result)return result;}
 for(n=0;n<256;n++)for(allocate=0;allocate<2;allocate++){
 connectedRng=1;seedStart=n*0x1020304u;wantX=floats[n%12];wantY=floats[(n+1)%12];wantZ=floats[(n+2)%12];result=one();if(result)return result;}
 return 0;}
'''+START
def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=393728,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in range(1,6),(name,code);effective[name]=code
 return dict(cases_per_profile=393728,profiles=profiles,SDK32_layout=True,real_spawn_wrapper_C=True,RNG_algorithm_independently_reconstructed=True,negative_RNG_values_are_bounded_extension_cases=True,initialized_descriptor_bytes_only=True,portable_padding_value_equality_claimed=False,float_bit_patterns=12,record_canaries_checked=True,negative_controls=len(effective),effective_native_controls=effective,legacy_provider_pointer_conversion_warning_scoped_to_existing_wrapper=True,bounded_factory_and_setter=True)
def caller_suite():
 rom=source.snapshot(o)['conker/conker.us.bin'];jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')]
 assert calls==[0x3C908,0x3C928,0x3C940,0x3C958]and not pointers
 const=list(struct.unpack_from('>7I',rom,0x23AD10));ws=[linked(p,'caller-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];n=0;visits=set()
 windows=((0x1500F444,0x1500F46C,0,0),(0x1500F46C,0x1500F484,1,0xC29C0000),(0x1500F484,0x1500F49C,2,0xC4260000),(0x1500F49C,0x1500F4C4,3,0xC4390000))
 for entry,stop,index,z in windows:
  at=entry-0x15000000+0x2D4B0;window=list(struct.unpack_from('>%dI'%((stop-entry)//4),rom,at))
  for p,allocated,phase_,rng_mode in itertools.product(range(12),(False,True),(0,8),(False,True)):
   values=list(const)
   if p:values[0]=FLOATS[(p+3)%12];values[index+1]=FLOATS[p]
   c=Case(RANDOMS[p],values[index+1],values[0],z,allocated,rng_mode,u32(p*0x1020304),phase_);mem=fixture(c)
   for i,v in enumerate(values):put(mem,0x80096250+4*i,v)
   for i in range(16):put(mem,0x800D98D0+i,0xA5,1)
   ms=[]
   for w in ws:
    conn=helpers(c);conn.update(zip(range(ENTRY,ENTRY+232,4),w));m=Oracle(window+[0],mem,c,entry=entry,connected=conn);m.r[16]=0x800D98D0;m.f[20]=c.y;m.saved_f=m.f[20:];m.window_stop=stop
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    ms.append(m);root=[a for t,a in m.calls if t==ENTRY];assert root==[(c.x,c.y,c.z)],('caller-ABI',root)
    assert read(m.memory,0x800D98D0+4*index)==(RESULT if allocated else 0),('caller-result',index)
    expected=fixture(c)
    if c.connected_rng:put(expected,SEED,next_seed(c.seed))
    if c.allocated:
     for i,v in enumerate(m.descriptors[0]):put(expected,COPIED+i,v,1)
    for i,v in enumerate(values):put(expected,0x80096250+i*4,v)
    for i in range(16):put(expected,0x800D98D0+i,0xA5,1)
    put(expected,0x800D98D0+4*index,RESULT if allocated else 0)
    assert public(m.memory)==public(expected),('caller-public',);assert m.r[29]==home(c)and m.r[16]==0x800D98D0 and m.f[20]==c.y
   assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits&set(range(entry,stop,4)));n+=1
 assert len(visits)==32
 return dict(cases=n,original_windows=4,window_words=[10,6,6,10],caller_words_visited=len(visits),aligned_ROM_JALs=[hex(x)for x in calls],aligned_literal_pointers=0,hard_float_f12_f14_a2_checked=True,all_four_result_stores_checked=True,natural_retail_constants_included=True,full_parent_or_hardware_claimed=False)
