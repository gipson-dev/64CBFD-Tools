"""Bounded actor-target timer reference and literal guest runner, not FCSR emulation."""
from dataclasses import dataclass
import math
import struct

from tools.experiments import game_actor_target_timer_candidates as source
from tools.tests import test_game_route_record_copy_match as core
from tools.tests.test_game_random_selector_outputs_match import RandomOutputsOracle, next_seed

STACK, put, read = core.STACK, core.put, core.read
ACTORS, CONTEXT, MODE, THRESHOLDS, PROBABILITY = 0x800CC2D0, 0x800D23B0, 0x800E0BD0, 0x80087320, 0x800872E8
LIMIT, NOTIFY, RANDOM, SCRIPT, SEED, SCALE = 0x8009DA8C, 0x1508EB90, 0x150ADA68, 0x1509BFB0, 0x800885B0, 0x8009F740
BANKS, NESTED = (0x20000, 0x22000), 0x26000
SEGMENTS = ((BANKS[0], 0x1800), (BANKS[1], 0x1800), (ACTORS, 26*0x32C),
            (NESTED, 27*0x130), (THRESHOLDS-768, 1536),
            (MODE, 1), (CONTEXT, 4), (LIMIT, 4))


def bits(value): return struct.unpack('>I', struct.pack('>f', value))[0]
def floating(value): return struct.unpack('>f', struct.pack('>I', value))[0]
def f32(value): return floating(bits(value))
def signed(value, width=32): return (value & ((1 << (width-1))-1)) - (value & (1 << (width-1)))
def public(memory): return {a:v for a,v in memory.items() if not STACK-0x400 <= a < STACK+0x100}
def writes(model): return [e for e in model.events if e[0]=='W' and not STACK-0x400 <= e[1] < STACK+0x100]


@dataclass(frozen=True)
class Case:
    slot:int = 0
    target:int = 1
    x:float = 2000.
    z:float = 0.
    timer:int = 0
    threshold:int = 0
    thresholds:tuple|None = None
    mode:int = 0
    probability:int = 50
    sample:float = .5
    mask:int = 0xFFFFFFFF
    notify_change:int = 0
    random_change:int = 0


def cases():
    for at in (0., 2000., 5000.):
        boundary = bits(at)
        values = [floating(v) for v in (boundary-1, boundary, boundary+1)] if at else [0.]
        for x in values:
            for timer, threshold in ((0,0), (1,0), (1,1), (-1,-2), (-1,-1), (32768,32767), (-2147483648,-32768)):
                yield Case(x=x, timer=timer, threshold=threshold)
    for slot in (0,7,25):
        for target in (-2147483648,-257,-1,0,1,15,16,25):
            yield Case(slot=slot,target=target,x=-3000.,z=4000.,timer=1,threshold=-1)
    for mode in (-128,-1,0,1,127):
        for probability in (-128,-1,0,49,50,51,100,127):
            yield Case(mode=mode,probability=probability)
    for sample in (0.,floating(0x3F000001),.9999,1.,-.25,1.25):
        yield Case(sample=sample,probability=50)
    for n in range(4):
        for r in range(4):
            yield Case(slot=7,timer=1,threshold=0,notify_change=n,random_change=r)
    for mask in (0,1,0x10000,0x20000,0x80000000):
        yield Case(timer=1,mask=mask)
    for at in (2000.,5000.):
        for word in (bits(at)-1,bits(at),bits(at)+1):
            for timer in (1,4,7):yield Case(x=floating(word),timer=timer,thresholds=(0,3,6))


def initial(case):
    actor=ACTORS+case.slot*0x32C; target=ACTORS+max(case.target,0)*0x32C
    rows=[(CONTEXT,BANKS[0],4),(LIMIT,bits(5000.),4),(MODE,case.mode,1),
          (actor+0x31C,NESTED+case.slot*0x130,4),(actor+0x14,bits(0.),4),(actor+0x1C,bits(0.),4),
          (BANKS[0]+0x11C+case.slot*4,case.target,4),(BANKS[0]+0x29C+case.slot*4,case.timer,4),
          (BANKS[0]+0x16C0+case.slot*4,case.mask,4),(BANKS[1]+0x29C+case.slot*4,7,4),
          (PROBABILITY+case.mode,case.probability,1)]
    if case.target >= 0:
        rows += [(target+0x14,bits(case.x),4),(target+0x1C,bits(case.z),4)]
    rows += [(THRESHOLDS+(case.mode*3+i)*2,(case.thresholds or (case.threshold,)*3)[i],2) for i in range(3)]
    return rows


def fixture(case):
    m={STACK+i:0xA5 for i in range(-0x400,0x100)}
    for base,size in SEGMENTS:m.update({base+i:0xA5 for i in range(size)})
    for address,value,size in initial(case):put(m,address,value,size)
    return m


def changes(case, target):
    actor=ACTORS+case.slot*0x32C; timer=BANKS[0]+0x29C+case.slot*4
    if target==NOTIFY:
        return {0:[],1:[(CONTEXT,BANKS[1],4),(timer,5,4)],
                2:[(CONTEXT,BANKS[1],4)],3:[(actor+0x31C,NESTED+26*0x130,4)]}[case.notify_change]
    return {0:[],1:[(MODE,-1,1),(PROBABILITY-1,-128,1),(actor+0x31C,NESTED+26*0x130,4)],
            2:[(MODE,127,1),(PROBABILITY+127,127,1),(actor+0x31C,NESTED+26*0x130,4)],
            3:[(CONTEXT,BANKS[1],4),(timer,9,4)]}[case.random_change]


def reference(memory,case,real_seed=None):
    m=memory.copy(); stores=[];calls=[]
    def store(a,v,n):
        put(m,a,v,n);stores.append(('W',a,n,v&((1<<(8*n))-1)))
    def call(target):
        calls.append(target)
        for a,v,n in changes(case,target):store(a,v,n)
    state=read(m,CONTEXT,4); ts=state+0x11C+case.slot*4; timer=state+0x29C+case.slot*4
    actor=ACTORS+case.slot*0x32C
    store(read(m,actor+0x31C,4)+0x129,read(m,ts,4),1)
    target=signed(read(m,ts,4))
    if target<0:return m,stores,calls,0
    other=ACTORS+target*0x32C
    dx=f32(floating(read(m,other+0x14,4))-floating(read(m,actor+0x14,4)))
    dz=f32(floating(read(m,other+0x1C,4))-floating(read(m,actor+0x1C,4)))
    distance=f32(math.sqrt(f32(f32(dx*dx)+f32(dz*dz))))
    category=0 if floating(read(m,LIMIT,4))<distance else 1 if 2000.<distance else 2
    mode=signed(read(m,MODE,1),8)
    if signed(read(m,THRESHOLDS+(mode*3+category)*2,2),16)<signed(read(m,timer,4)):
        store(timer,0,4)
        current=read(m,CONTEXT,4);mask=(0x10000 << (read(m,ts,4)&31))&0xFFFFFFFF
        if mask&read(m,current+case.slot*4+0x16C0,4):call(NOTIFY)
    if read(m,timer,4)==0:
        store(read(m,actor+0x31C,4)+0x12A,0,1)
        if real_seed is None:
            call(RANDOM);sample=f32(case.sample)
        else:
            calls.append(RANDOM);seed=next_seed(read(m,SEED,8));store(SEED,seed,8)
            sample=f32(f32(float(seed&65535))*floating(read(m,SCALE,4)))
        mode=signed(read(m,MODE,1),8);prob=signed(read(m,PROBABILITY+mode,1),8)
        if prob<math.trunc(f32(sample*100.)):
            store(read(m,actor+0x31C,4)+0x12A,1,1)
    return m,stores,calls,category


class TimerModel(RandomOutputsOracle,core.CopyModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY):
        core.CopyModel.__init__(self,words,memory,(case.slot,),phase=phase,connected=connected,entry=entry)
        self.case=case;self.condition=False;self.requested=None

    def get(self,address,size):
        self.requested=('R',address,size);return super().get(address,size)

    def put(self,address,value,size):
        self.requested=('W',address,size);return super().put(address,value,size)

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==4:
            fs,fd=word>>11&31,word>>6&31
            self.f[fd]=bits(math.sqrt(floating(self.f[fs])));return
        super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            self.caller_args.append((self.r[4],));return
        assert target in (NOTIFY,RANDOM,SCRIPT),hex(target)
        args=tuple(self.r[4:7]) if target==NOTIFY else tuple(self.r[4:8]) if target==SCRIPT else ()
        if target==NOTIFY:assert args==(self.case.slot,0x61,0x2000)
        self.calls.append(target);self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target in (NOTIFY,RANDOM,SCRIPT)
        self.in_hook=True
        try:
            for a,v,n in changes(self.case,NOTIFY if target==SCRIPT else target):self.put(a,v,n)
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.r[2]=0x12345678 if target!=RANDOM else 0x3456
            self.f[:20]=[0xA5000000+i for i in range(20)]
            if target==RANDOM:self.f[0]=bits(self.case.sample)
        finally:self.in_hook=False


def native_harness(body,corpus):
    """Translate guest word values and pointer fields, not guest byte-order aliases."""
    offsets=[];total=0
    for base,size in SEGMENTS:
        total=(total+15)&~15;offsets.append(total);total+=size
    def patch_row(a,v,n):
        pointer=a==CONTEXT or ACTORS<=a<ACTORS+26*0x32C and (a-ACTORS)%0x32C==0x31C
        return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,pointer)
    rows=[];patches=[]
    for c in corpus:
        m=fixture(c);_,stores,calls,_=reference(m,c)
        lists=[initial(c),[(a,v,n) for _,a,n,v in stores],changes(c,NOTIFY),changes(c,RANDOM)]
        spans=[]
        for actions in lists:
            spans.extend((len(patches),len(actions)));patches.extend(patch_row(*p) for p in actions)
        rows.append('{%d,0x%Xu,%s,%d,%d}'%(c.slot,bits(c.sample),','.join(map(str,spans)),
                    calls.count(NOTIFY),calls.count(RANDOM)))
    defines=[]
    for name,address,ctype in (('D_800CC2D0',ACTORS,'u8*'),('D_800D23B0',CONTEXT,'s32*'),
        ('D_800E0BD0',MODE,'s8*'),('D_80087320',THRESHOLDS,'s16*'),
        ('D_800872E8',PROBABILITY,'s8*'),('D_8009DA8C',LIMIT,'f32*')):
        value='((%s)address(0x%Xu,actual))'%(ctype,address)
        if name not in ('D_800CC2D0','D_80087320','D_800872E8'):value='(*'+value+')'
        defines.append('#define '+name+' '+value)
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static u8 *address(u32 a,u8 *buffer){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return buffer+regions[i][2]+a-regions[i][0];
 __builtin_trap();}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Case{s32 slot;u32 sample,init,count,expected,changes,notify,nc,random,rc,notifies,randoms;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 callsN,callsR,error;
static void apply(u8 *buffer,u32 first,u32 count){u32 i,v;u8*p;const struct Patch*q;
 for(i=0;i<count;i++){q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,buffer);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(s16*)p=(s16)v;else *(u32*)p=v;}}
DEFINES
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
s32 func_1508EB90(s32 slot,s32 command,s32 value){
 if(slot!=c->slot||command!=0x61||value!=0x2000)error=22;
 callsN++;apply(actual,c->notify,c->nc);return 0x12345678;}
f32 func_150ADA68(void){callsR++;apply(actual,c->random,c->rc);return real(c->sample);}
BODY
void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;callsN=callsR=error=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->init,c->count);apply(wanted,c->init,c->count);apply(wanted,c->expected,c->changes);
 func_1508D850(c->slot);
 if(callsN!=c->notifies||callsR!=c->randoms)error=23;
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])error=21;
 if(error)break;}
 __asm__ volatile("int $0x80"::"a"(1),"b"(error));__builtin_unreachable();}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
    'PATCHES',','.join(patches)).replace('CASES',',\n'.join(rows)).replace('DEFINES','\n'.join(defines)).replace('BODY',body)
