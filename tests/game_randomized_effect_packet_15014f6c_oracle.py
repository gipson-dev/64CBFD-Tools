"""Random range snapshots, complete matrix payload and original callback ABI."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RNG,MATRIX,FACTORY,COPY=0x15014F6C,0x150ADA20,0x150A8050,0x15149130,0x10022EC0
ALLOCATE,ZERO=0x15167A68,0x100226F0
SOURCE,OUTPUT=0x30000,0x50000
COUNT,BASE,TABLE=0x800D3094,0x800D3098,0x80082E30
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
PATTERNS=(0,0x80000000,1,0x807FFFFF,0x3F800000,0xBF800000,0x7F800000,0xFF800000,0x7FC12345,0xFFC54321)
@dataclass(frozen=True)
class Case:
    range:int=0xFFFF0001
    flags:int=0x80000001
    variant:int=0x123456E1
    state:int=0x81
    rng:int=0xFFFFFFFF
    outcome:int=1
    mutation:int=0
    phase:int=0
    seed:int=0
    alias:int=0
    x:int=-32768
    y:int=0
    z:int=32767
    angle0:int=0x41F00000
    angle1:int=0xC2700000
    tag:int=0
def symbols(index=0):
    names=('func_150ADA20','func_150A8050','func_15149130','memcpy')
    values=((RNG,MATRIX,FACTORY,COPY),(0x17017FFC,0x17108000,0x1720FFFC,0x17308000),(0x1E017FFC,0x1E108000,0x1E20FFFC,0x1E308000))[index]
    return dict(zip(names,values))
def source_address(c):return STACK+c.phase-0x98+0x7C if c.alias==1 else SOURCE
def result_address(c):return (source_address(c)-0x28 if c.alias==2 else OUTPUT)if c.outcome else 0
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case()):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
    source=source_address(c)
    for base,n in((SOURCE-64,512),(OUTPUT-64,512),(source-64,512),(COUNT-16,64),(BASE-16,64),(TABLE,256)):
        for i in range(n):m.setdefault(u32(base+i),(i*29+c.seed*11+0x5A)&255)
    for off,v,n in((0,c.x,2),(2,c.y,2),(4,c.z,2),(0x0C,c.angle0,4),(0x10,c.angle1,4),
                   (0x16,c.state,1),(0x18,c.range,4),(0x1C,c.flags,4),(0x20,c.variant,4)):
        put(m,source+off,u32(v),n)
    m[source+0x15]=0x5C+(c.tag&3);put(m,COUNT,1);put(m,BASE,source);put(m,TABLE+23*4,ENTRY)
    return m
def stamp(c):
    words=[PATTERNS[(c.seed+i)%len(PATTERNS)]for i in range(16)];words[15]=0x3F800000
    return words
def rng_effect(m,c):
    source=source_address(c)
    if c.mutation&1:
        for off,v in((0x18,0x1234ABCD),(0x1C,0x87654320),(0x20,0xABCDEF01),(0x0C,0xC1200000),(0x10,0x42280000)):put(m,source+off,v)
        for i,v in enumerate((17,-19,23)):put(m,source+2*i,v&65535,2)
    if c.mutation&8:put(m,COUNT,3)
def matrix_effect(m,c):
    if c.mutation&2:
        for i,v in enumerate((-1234,2345,-32768)):put(m,source_address(c)+2*i,v&65535,2)
def factory_effect(m,c):
    if c.mutation&4:
        for i,v in enumerate((101,202,303)):put(m,source_address(c)+2*i,v,2)
def initialize(m,p):
    put(m,p+0x0E,300,2)
    for off,v in((0x0D,0),(0x10,255),(0x11,0x31),(0x12,255),(0x13,0x2A)):m[p+off]=v
    for i in range(16):m[p+0x14+i]=0
def homes(m,sp,n=4):
    for i in range(n):put(m,sp+4*i,0xB5000000+i)
def reference(initial,c=Case(),s=None,home=None,ra=0xDEAD0000,saved_s0=0xA0000010,connected=False):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-0x98;source=source_address(c);packet=sp+0x44
    put(m,sp+0x30,saved_s0);put(m,sp+0x34,ra)
    state=m[source+0x16];variant=read(m,source+0x20);m[source+0x16]=state|4;m[packet+0x51]=variant&255
    mode=int(bool(read(m,source+0x1C)&1));m[packet+0x50]=mode;put(m,packet,source)
    low=read(m,source+0x18)&65535;put(m,packet+4,low)
    high=read(m,source+0x18)>>16&65535;put(m,packet+8,high)
    calls=[(s['func_150ADA20'],())];observations=[]
    rng_effect(m,c);homes(m,sp)
    high,low=read(m,packet+8),read(m,packet+4);limit=u32(high+1);assert limit
    put(m,packet+12,u32(divmod(u32(c.rng),limit)[1]+low))
    a=(packet+16,read(m,source+0x0C),read(m,source+0x10),0);calls.append((s['func_150A8050'],a))
    observations.append(('matrix',a))
    for i,w in enumerate(stamp(c)):put(m,packet+16+4*i,w)
    matrix_effect(m,c);homes(m,sp)
    for i in range(3):put(m,packet+0x40+4*i,bits(float(signed16(read(m,source+2*i,2)))))
    args=(300,0xFFFFFFFF,0x31,0xFFFFFFFF,0,0x2A,0x54,255,0)
    for i,v in enumerate(args[4:],4):put(m,sp+4*i,v)
    calls.append((s['func_15149130'],args));observations.append(('factory',args,data(m,packet,84)))
    factory_effect(m,c);result=result_address(c)
    if connected:calls.append((ALLOCATE,(35,0,124,1,255,1)))
    if result:
        initialize(m,result)
        if connected:calls.append((ZERO,(result+20,16)))
    homes(m,sp,9)
    if result:
        args=(result+40,packet,84);calls.append((s['memcpy'],args));observations.append(('copy',args,data(m,packet,84)))
        for i in range(84):m[u32(args[0]+i)]=m[u32(args[1]+i)]
        homes(m,sp)
    return m,calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=(source_address(c),))
        self.f=[u32(c.seed*0x9E3779B9+i*0x1020304)for i in range(32)];self.saved_f=self.f[20:]
        self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
    def record_call(self,t):
        if t==ENTRY:self.target_home=self.r[29];args=self.arguments(1)
        else:
            counts={self.syms['func_150ADA20']:0,self.syms['func_150A8050']:4,self.syms['func_15149130']:9,self.syms['memcpy']:3,ALLOCATE:6,ZERO:2}
            assert t in counts,hex(t);args=self.arguments(counts[t])
            if t==self.syms['func_150A8050']:self.observations.append(('matrix',tuple(args)))
            elif t==self.syms['func_15149130']:self.observations.append(('factory',tuple(args),data(self.memory,self.target_home-0x54,84)))
            elif t==self.syms['memcpy']:self.observations.append(('copy',tuple(args),data(self.memory,args[1],args[2])))
        args=tuple(map(u32,args));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        c,s=self.case,self.syms;args=self.calls[-1][1];n=4
        if t==s['func_150ADA20']:rng_effect(self.memory,c);value=u32(c.rng)
        elif t==s['func_150A8050']:
            assert args[3]==0,args
            for i,w in enumerate(stamp(c)):put(self.memory,args[0]+4*i,w)
            matrix_effect(self.memory,c);value=0xD00D0000
        elif t in(s['func_15149130'],ALLOCATE):
            if t==ALLOCATE:assert args==(35,0,124,1,255,1),args
            factory_effect(self.memory,c);value=result_address(c)
            if t==s['func_15149130']:
                if value:initialize(self.memory,value)
                n=9
        elif t==ZERO:
            assert args[1]==16
            for i in range(args[1]):self.memory[args[0]+i]=0
            value=0
        else:
            assert t==s['memcpy']and args[2]==84,args
            for i in range(args[2]):self.memory[u32(args[0]+i)]=self.memory[u32(args[1]+i)]
            value=args[0]
        homes(self.memory,self.r[29],n)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value);self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations)
def original_object(core,q,out):
    text=(out/'frozen/conker/asm/nonmatchings/game_40490/func_15014F6C.s').read_text()
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+text+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s=None):
    s=symbols()if s is None else s;a=list(core.bound_blob(q['original'],q['original_refs'],s));b=list(core.bound_blob(q['raw'],q['refs'],s));assert a==b
    return a,b
def cases():
    ranges=(0,0xFFFF,0x10000,0xFFFF0000,0xFFFFFFFF,0x12345678)
    randoms=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)
    return [Case(range=r,flags=f,rng=v,outcome=o,mutation=m,phase=p,seed=(r+v+m)&7,variant=(0xA5C3E100|((r+m)&255)),state=(r+m*29)&255)
            for r,f,v,o,m,p in itertools.product(ranges,(0,1,2,0x80000001,0xFFFFFFFF),randoms,(0,1),(0,1,2,4,8,15),(0,8))]
def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);rows=[(c,symbols(),ENTRY)for c in cases()];seen=set();count=0
    for i in(1,2):rows.extend((Case(range=r,rng=v,mutation=15),symbols(i),0x17007FFC if i==1 else 0x1F00FFFC)for r,v in itertools.product((0,0xFFFF,0xFFFFFFFF),(0,0x80000000,0xFFFFFFFF)))
    for c,s,entry in rows:
        initial=fixture(c);ps=programs(core,q,s);models=[Oracle(body,initial,c,entry=entry,s=s).run()for body in ps]
        wanted,calls,obs=reference(initial,c,s,saved_s0=models[0].before[16])
        for m in models:assert(m.memory,m.calls,m.observations)==(wanted,calls,obs),(c,s);assert m.r[2]==1 and m.f[20:]==m.before_f[20:]
        assert literal(models[0])==literal(models[1]);seen.update(pc-entry for pc in models[0].visits);count+=1
    assert seen==set(range(0,312,4))-{0x90},sorted(set(range(0,312,4))-seen)
    aliases=0
    for c in(Case(alias=a,outcome=o,mutation=mode,range=r)for a,o,mode,r in itertools.product((1,2),(0,1),(0,2,4),(0,0xFFFFFFFF))):
        initial=fixture(c);models=[Oracle(body,initial,c).run()for body in programs(core,q)]
        wanted,calls,obs=reference(initial,c,saved_s0=models[0].before[16])
        assert all((m.memory,m.calls,m.observations)==(wanted,calls,obs)for m in models),c
        assert literal(models[0])==literal(models[1]);aliases+=1
    cuts=0
    for c in(Case(outcome=0),Case(mutation=15),Case(alias=1,mutation=2),Case(alias=2,mutation=4)):
        initial=fixture(c);ps=programs(core,q);full=Oracle(ps[0],initial,c).run()
        for cut in range(full.all_accesses):
            models=[]
            for body in ps:
                m=Oracle(body,initial,c);m.cut=cut
                try:m.run();raise AssertionError(('Unfired randomized packet cut',cut))
                except AccessBoundary:pass
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    return dict(cases=count,reached_words=77,unreachable_break_offset='0x90',alias_cases=aliases,fault_prefix_cuts=cuts,
                full_literal_state=True,independent_complete_memory=True,unsigned_division_and_boundary_ranges=True,
                all84_packet_bytes_and_private_padding=True,synthetic_frame_aliases_guest_only=True)

def connections(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();helpers={}
    for entry,offset,n in((FACTORY,0x1765E0,49),(COPY,0x22EC0,11)):
        helpers.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    public=lambda mem:{a:v for a,v in mem.items()if not STACK-2048<=a<STACK+1024}
    connected=0
    for c in(Case(range=r,rng=v,outcome=o,mutation=m)for r,v,o,m in itertools.product((0,0xFFFF,0xFFFFFFFF),(0,0x80000000,0xFFFFFFFF),(0,1),(0,1,2,4))):
        initial=fixture(c);models=[Oracle(body,initial,c,connected=helpers).run()for body in programs(core,q)]
        wanted,calls,obs=reference(initial,c,saved_s0=models[0].before[16],connected=True)
        assert all(public(m.memory)==public(wanted)and m.calls==calls and m.observations==obs for m in models),c
        assert literal(models[0])==literal(models[1]);connected+=1
    start,end=0x15013050,0x15013090;window=struct.unpack_from('>16I',rom,0x40500);caller=0
    for c,offset in itertools.product((Case(tag=t,outcome=o,mutation=m)for t,o,m in itertools.product(range(4),(0,1),(0,1,2,4,8,15))),(0,0x34)):
        initial=fixture(c);put(initial,BASE,SOURCE-offset);models=[]
        wanted,calls,obs=reference(initial,c,ra=0x15013080,saved_s0=offset)
        for body in programs(core,q):
            code=dict(zip(range(ENTRY,ENTRY+312,4),body));code[end]=0
            m=Oracle(window,initial,c,entry=start,connected=code)
            m.r[16]=offset;m.r[17]=offset//0x34;m.r[18]=BASE;m.r[19]=TABLE;m.before=m.r[:]
            m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run();raise AssertionError('Missing randomized callback boundary')
            except WindowBoundary:pass
            assert(m.memory,m.calls,m.observations)==(wanted,[(ENTRY,(SOURCE,)),*calls],obs),(c,offset,'caller')
            assert m.r[16]==offset and m.r[17]==offset//0x34+1 and m.r[4]==read(m.memory,COUNT)
            models.append(m)
        assert literal(models[0])==literal(models[1]);caller+=1
    return dict(original_factory_and_copy_cases=connected,factory_words=49,copy_words=11,
                bounded_allocator_and_zero=True,caller_cases=caller,caller_words=16,registered_slot=23,
                kind_bytes=[0x5C,0x5D,0x5E,0x5F],caller_start=hex(start),caller_end=hex(end),
                parent_S0_offset_and_live_count_reload=True,full_dispatcher_not_qualified=True)

def native_text(core,selected=None):
    selected=core.SELECTED if selected is None else selected
    return '#include <string.h>\n'+core.ISOLATED_HEADER+selected+r'''
typedef struct {s16 position[3];u8 pad6[6];f32 angle0,angle1;u8 pad14,kind,state,pad17;u32 range,flags,variant;u8 tail24[16];} NativeSource;
typedef char Layout[(sizeof(void*)==4&&sizeof(NativeSource)==0x34&&sizeof(RandomizedEffectPacket40490)==84&&
 __builtin_offsetof(NativeSource,angle0)==12&&__builtin_offsetof(NativeSource,angle1)==16&&
 __builtin_offsetof(NativeSource,state)==0x16&&__builtin_offsetof(NativeSource,range)==24&&
 __builtin_offsetof(NativeSource,flags)==28&&__builtin_offsetof(NativeSource,variant)==32&&
 __builtin_offsetof(RandomizedEffectPacket40490,matrix)==16&&__builtin_offsetof(RandomizedEffectPacket40490,mode)==80&&
 __builtin_offsetof(RandomizedEffectPacket40490,variant)==81)?1:-1];
static NativeSource source,expectedSource;static u32 output[48],expectedOutput[48];
static RandomizedEffectPacket40490 expectedPacket;static u32 stampWords[16],randomWord;
static unsigned mode,success,seed,calls,error;static u32 expectedAngle0,expectedAngle1;
static void bytes(void*d,const void*s,unsigned n){u8*a=d;const u8*b=s;unsigned i;for(i=0;i<n;i++)a[i]=b[i];}
static void fill(void*d,unsigned n,u8 value){u8*a=d;unsigned i;for(i=0;i<n;i++)a[i]=(u8)(value+i*17);}
static int equal(const void*a,const void*b,unsigned n){const u8*x=a,*y=b;unsigned i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static u32 word(f32 v){u32 b;bytes(&b,&v,4);return b;}
static void rngChange(NativeSource*p){p->range=0x1234ABCD;p->flags=0x87654320;p->variant=0xABCDEF01;p->angle0=-10.0f;p->angle1=42.0f;p->position[0]=17;p->position[1]=-19;p->position[2]=23;}
static void matrixChange(NativeSource*p){p->position[0]=-1234;p->position[1]=2345;p->position[2]=-32768;}
static void factoryChange(NativeSource*p){p->position[0]=101;p->position[1]=202;p->position[2]=303;}
s32 func_150ADA20(void){if(calls++!=0)error=1;if(mode&1)rngChange(&source);return(s32)randomWord;}
void func_150A8050(f32 matrix[4][4],f32 a,f32 b,f32 c){
 if(calls++!=1||word(a)!=expectedAngle0||word(b)!=expectedAngle1||word(c)!=0)error=1;
 bytes(matrix,stampWords,64);if(mode&2)matrixChange(&source);
}
struct260 *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,struct37*g,u8 h,s32 i){
 if(calls++!=2||a!=300||b!=-1||c!=0x31||d!=-1||e!=0||f!=0x2A||(u32)g!=84||h!=255||i!=0)error=1;
 if(mode&4)factoryChange(&source);
 if(success){u8*p=(u8*)output;p[14]=44;p[15]=1;p[13]=0;p[16]=255;p[17]=0x31;p[18]=255;p[19]=0x2A;for(i=20;i<36;i++)p[i]=0;}
 return success?(struct260*)output:0;
}
void *memcpy(void*d,const void*s,size_t n){
 const u8*p=s;u8*q=d;unsigned i;
 if(calls++!=3||d!=(u8*)output+40||n!=84||!equal(s,&expectedPacket,82))error=1;
 /* The two C padding bytes are unspecified. Observe and copy them, then
    compare all output bytes without assigning a portable padding value. */
 for(i=0;i<84&&i<n;i++){q[i]=p[i];((u8*)expectedOutput)[40+i]=p[i];}
 return d;
}
static int run(void){
 static const u32 ranges[]={0,0xFFFF,0x10000,0xFFFF0000,0xFFFFFFFF,0x12345678};
 static const u32 randoms[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};
 static const u32 flags[]={0,1,2,0x80000001,0xFFFFFFFF};
 static const u32 patterns[]={0,0x80000000,1,0x807FFFFF,0x3F800000,0xBF800000,0x7F800000,0xFF800000,0x7FC12345,0xFFC54321};
 unsigned r,v,f,o,md,i,count=0,limit,low;u8*p;
 for(r=0;r<6;r++)for(v=0;v<6;v++)for(f=0;f<5;f++)for(o=0;o<2;o++)for(md=0;md<8;md++){
  mode=md;success=o;seed=r+v+md;randomWord=randoms[v];calls=error=0;
  fill(&source,sizeof(source),(u8)(seed+0x5A));fill(output,sizeof(output),0xA5);
  source.position[0]=-32768;source.position[1]=(s16)(seed*157-12345);source.position[2]=32767;
  source.angle0=30.0f;source.angle1=-60.0f;source.range=ranges[r];source.flags=flags[f];source.variant=0xA5C3E100u|((seed*37)&255);source.state=(u8)(seed*29);
  bytes(&expectedSource,&source,sizeof(source));expectedSource.state|=4;
  expectedPacket.owner=(u8*)&source;low=source.range&65535;limit=(source.range>>16)+1;
  expectedPacket.minimum=low;expectedPacket.extraRange=limit-1;expectedPacket.selected=randomWord-(randomWord/limit)*limit+low;
  expectedPacket.mode=(source.flags&1)!=0;expectedPacket.variant=(u8)source.variant;
  if(mode&1)rngChange(&expectedSource);
  expectedAngle0=word(expectedSource.angle0);expectedAngle1=word(expectedSource.angle1);
  for(i=0;i<16;i++)stampWords[i]=patterns[(seed+i)%10];stampWords[15]=0x3F800000;bytes(expectedPacket.matrix,stampWords,64);
  if(mode&2)matrixChange(&expectedSource);
  for(i=0;i<3;i++)expectedPacket.matrix[3][i]=(f32)expectedSource.position[i];
  if(mode&4)factoryChange(&expectedSource);
  bytes(expectedOutput,output,sizeof(output));p=(u8*)expectedOutput;
  if(success){p[14]=44;p[15]=1;p[13]=0;p[16]=255;p[17]=0x31;p[18]=255;p[19]=0x2A;for(i=20;i<36;i++)p[i]=0;}
  if(func_15014F6C((DispatchRecord40490*)&source)!=1||calls!=(success?4u:3u)||error)return 1;
  if(!equal(&source,&expectedSource,sizeof(source))||!equal(output,expectedOutput,sizeof(output)))return 2;
  count++;
 }
 return count==2880?0:3;
}
'''+START

def controls(core):
    s=core.SELECTED
    changes={
      'wrong_state_bit':('source[0x16] |= 4','source[0x16] |= 2'),
      'wrong_mode_bit':('source + 0x1C) & 1','source + 0x1C) & 2'),
      'wrong_variant':('packet.variant = *(u32 *)(source + 0x20)','packet.variant = *(u32 *)(source + 0x20) >> 8'),
      'wrong_minimum_mask':('source + 0x18) & 0xFFFF','source + 0x18) & 0xFF'),
      'wrong_range_shift':('source + 0x18) >> 16','source + 0x18) >> 8'),
      'signed_random_remainder':('(u32)func_150ADA20() % (packet.extraRange + 1)','func_150ADA20() % (s32)(packet.extraRange + 1)'),
      'missing_inclusive_bound':('packet.extraRange + 1','packet.extraRange + 2'),
      'wrong_first_angle':('*(f32 *)(source + 0x0C),','*(f32 *)(source + 0x10),'),
      'wrong_third_angle':('source + 0x10), 0.0f','source + 0x10), 1.0f'),
      'unsigned_coordinate':('*(s16 *)(source + 0)','*(u16 *)(source + 0)'),
      'overwrite_last_matrix_word':('packet.matrix[3][2] = *(s16 *)(source + 4);','packet.matrix[3][2] = *(s16 *)(source + 4); packet.matrix[3][3] = 0.0f;'),
      'wrong_factory_size':('(struct37 *)sizeof(packet)','(struct37 *)(sizeof(packet) - 4)'),
      'wrong_copy_size':('memcpy(result + 0x28, &packet, sizeof(packet))','memcpy(result + 0x28, &packet, sizeof(packet) - 4)'),
      'wrong_copy_destination':('memcpy(result + 0x28','memcpy(result + 0x2C'),
      'wrong_return':('return 1;','return 0;'),
    }
    assert all(s.count(a)==1 for a,b in changes.values())
    return {n:s.replace(a,b)for n,(a,b)in changes.items()}

def native(core,out):
    rows=[('valid-'+opt[1:],None,opt,True)for opt in('-O0','-O2','-O3')]
    rows +=[(name,body,'-O2',False)for name,body in controls(core).items()];records=[]
    for name,body,opt,valid in rows:
        p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
        compile=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
        assert compile.returncode==0 and not compile.stdout and not compile.stderr,(name,compile.stdout,compile.stderr)
        run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
        assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
        records.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
    return dict(cases_per_profile=2880,profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),records=records,
                typed_backing_and_layout_offsets=True,whole_object_canaries=True,portable_padding_value_not_fixed=True,
                synthetic_aliases_guest_only=True)
