"""Independent cyclic-weight reference, explicit RNG contracts and legacy scratch limits."""
from dataclasses import dataclass
import math

from tools.experiments import game_cyclic_weight_profiles_candidates as source
from tools.tests import game_actor_target_timer_oracle as previous

core,STACK=previous.core,previous.STACK
put,read,bits,floating,f32,signed=previous.put,previous.read,previous.bits,previous.floating,previous.f32,previous.signed
COUNT,CONTEXT,RANDOM,SEED,SCALE=0x8008FD8C,0x800D23B0,0x150ADA68,0x800885B0,0x8009F740
BANKS=(0x20000,0x24000)
SEGMENTS=((COUNT,1),(CONTEXT,4),(SEED,8),(SCALE,4),*((b,0x3000) for b in BANKS))
SCALE_BITS=0x37800080


@dataclass(frozen=True)
class Case:
    count:int=4
    samples:tuple=(0.2,0.25,0.75,0.75)
    mutation:int=0
    used_mask:int=0
    seed:int|None=None


def cases():
    for count in (-128,-127,-2,-1,0,1,2,3,4,5,6,7,8,9,11,12,15,16,17,19,31,32):
        yield Case(count=count,samples=(0.,0.25) if count>16 else (0.2,0.25,0.75,0.75))
    for count in (1,2,3,4,5,7,8,15,16):
        for sample in (0.,-0.,0.125,0.49999,0.9999847):yield Case(count=count,samples=(sample,0.5))
    for sample in (floating(bits(0.5)-1),0.5,floating(bits(0.5)+1),math.nan):
        yield Case(samples=(0.2,sample))
    for count in (1,3,4,8,15):yield Case(count=count,samples=(1.,0.25))
    for mutation in range(1,7):yield Case(count=8,mutation=mutation)
    # The callback-written scratch is a guest-only control, not behavior of the real RNG.
    for count,mask,first in ((2,1,0.),(4,1,0.),(4,8,0.9),(8,0x55,0.),(16,0xAAAA,0.9)):
        for second in (0.25,0.5,0.75):yield Case(count=count,used_mask=mask,samples=(first,second))
    for count,mask,second in ((4,3,0.75),(4,9,0.25),(8,0xF,0.75)):
        yield Case(count=count,used_mask=mask,samples=(0.,second))


def native_safe(case):
    n=signed(case.count&255,8)
    return not case.used_mask and case.seed is None and (n<=0 or bool(case.samples) and all(
        math.isfinite(value) and 0<=math.trunc(f32(f32(value)*f32(n)))<16
        for value in (case.samples[i%len(case.samples)] for i in range(0,2*n,2))))


def native_cases():
    selected=[c for c in cases() if native_safe(c)]
    for count in (40,63,64,96,126,127):selected.append(Case(count=count,samples=(0.,0.25)))
    return selected


def initial(case):
    return [(COUNT,case.count,1),(CONTEXT,BANKS[0],4),(SEED,case.seed or 0,8),(SCALE,SCALE_BITS,4)]


def fixture(case,poison=0xA5):
    m={STACK+i:poison for i in range(-0x500,0x100)}
    for base,size in SEGMENTS:m.update({base+i:0xA5 for i in range(size)})
    for a,v,n in initial(case):put(m,a,v,n)
    return m


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x500<=a<STACK+0x100}
def public_stores(model):return [row for row in model.stores if not STACK-0x500<=row[0]<STACK+0x100]


def changes(case,number):
    if number!=0:return []
    return {0:[],1:[(CONTEXT,BANKS[1],4)],2:[(COUNT,0,1)],3:[(COUNT,-1,1)],
        4:[(COUNT,1,1),(CONTEXT,BANKS[1],4)],5:[(BANKS[0]+0x15B4,0xD3,1)],
        6:[(COUNT,127,1),(CONTEXT,BANKS[1],4)]}[case.mutation]


def random_value(memory,case,number):
    if case.seed is not None:
        value=previous.next_seed(read(memory,SEED,8));put(memory,SEED,value,8)
        return f32(f32(float(value&65535))*floating(read(memory,SCALE,4))),[(SEED,8,value)]
    stores=[]
    for a,v,n in changes(case,number):put(memory,a,v,n);stores.append((a,n,v&((1<<(n*8))-1)))
    return f32(case.samples[number%len(case.samples)]),stores


def reference(memory,case,endpoint_poison=0xA5):
    m=memory.copy();stores=[];calls=[];n=signed(read(m,COUNT,1),8);base=read(m,CONTEXT,4)+0x15B4
    step=170//max(2,n//2);edge=endpoint_poison
    def random():
        number=len(calls);calls.append((RANDOM,))
        value,writes=random_value(m,case,number);stores.extend(writes);return value
    for row in range(max(0,n)):
        used=[0]*16;position=math.trunc(f32(random()*f32(n)));direction=1 if random()>0.5 else -1
        if case.used_mask:used=[0x80 if case.used_mask>>i&1 else 0 for i in range(16)]
        def occupied(p):
            if 0<=p<16:return used[p]!=0
            if p==16:return edge!=0
            raise ValueError('Outside the explicitly backed guest endpoint')
        for attempt in range(2*n+2):
            if not occupied(position):break
            position+=direction
            if position<0:position=n-1
            if position>=n:position=0
        else:raise ValueError('No free scratch slot in probe')
        if position<16:used[position]=1
        else:edge=1
        value=85;delta=step
        for column in range(n):
            address=base+row*16+position;byte=value&255 if value<256 else 255
            put(m,address,byte,1);stores.append((address,1,byte))
            position+=1
            if position>=n:position=0
            value+=delta
            if value>=256:delta=-delta
    return m,calls,stores


class WeightModel(previous.TimerModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY,used_offset=0x50):
        self.requests=[]
        core.CopyModel.__init__(self,words,memory,(),phase=phase,connected=connected,entry=entry)
        self.case=case;self.condition=False;self.requested=None;self.used_offset=used_offset
        self.f[20:]=[0x3F800000+i for i in range(20,32)];self.saved_f=self.f[20:].copy()

    def gate(self):
        if self.recording and not self.in_hook:self.requests.append(self.requested)
        super().gate()

    def execute(self,word):
        if word>>26==0 and word&63==26:
            a=signed(self.r[word>>21&31]);b=signed(self.r[word>>16&31])
            if b==0:raise AssertionError('Unexpected weight-profile division by zero')
            self.lo=math.trunc(a/b)&0xFFFFFFFF;return
        super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append(());return
        if target!=RANDOM:raise AssertionError('Unexpected weight helper: %X'%target)
        self.calls.append((target,));self.events.append(('CALL',target))

    def hook(self,target):
        if target!=RANDOM:raise AssertionError('Unexpected weight provider')
        self.in_hook=True
        try:
            number=len(self.calls)-1;value,writes=random_value(self.memory,self.case,number)
            for a,n,v in writes:self.put(a,v,n)
            if self.case.used_mask and number&1:
                for i in range(16):self.put(self.r[29]+self.used_offset+i,0x80 if self.case.used_mask>>i&1 else 0,1)
            for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            for i in range(4):self.put(self.r[29]+i*4,0xBA000000+len(self.calls)*16+i,4)
            self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=bits(value)
            self.lo=0xA5000000+number
            self.condition=bool(len(self.calls)&1)
        finally:self.in_hook=False


def native_harness(body,corpus):
    offsets=[];total=0
    for _,size in SEGMENTS:total=(total+15)&~15;offsets.append(total);total+=size
    patches=[];samples=[];effects=[];rows=[]
    def patch_row(a,v,n):
        return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,a==CONTEXT and n==4)
    for case in corpus:
        if not native_safe(case):raise ValueError('Guest-only native case')
        memory=fixture(case);wanted,calls,_=reference(memory,case)
        first=len(patches);patches.extend(patch_row(a,v,n) for a,v,n in initial(case) if a!=SEED)
        patches.extend((patch_row(SEED,0,4),patch_row(SEED+4,0,4)));count=len(patches)-first
        expected=len(patches)
        patches.append(patch_row(COUNT,read(wanted,COUNT,1),1));patches.append(patch_row(CONTEXT,read(wanted,CONTEXT,4),4))
        for bank in BANKS:
            patches.extend(patch_row(bank+i,wanted[bank+i],1) for i in range(0x3000) if wanted[bank+i]!=0xA5)
        expected_count=len(patches)-expected;start=len(samples)
        samples.extend(bits(f32(case.samples[i%len(case.samples)])) for i in range(len(calls)))
        effect_first=len(effects)
        for i in range(len(calls)):
            at=len(patches);patches.extend(patch_row(a,v,n) for a,v,n in changes(case,i));effects.append('{%d,%d}'%(at,len(patches)-at))
        rows.append('{%d,%d,%d,%d,%d,%d,%d}'%(first,count,expected,expected_count,start,len(calls),effect_first))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];fail(29);}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Effect{u32 first,count;};static const struct Effect effects[]={EFFECTS};
struct Case{u32 first,count,expected,expected_count,sample,calls,effect;};static const struct Case cases[]={CASES};
static const u32 samples[]={SAMPLES};static const struct Case*c;static u32 ordinal;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static void apply(u8*b,u32 first,u32 count){u32 i,v;const struct Patch*q;u8*p;
 for(i=0;i<count;i++){q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else*(u32*)p=v;}}
#define D_8008FD8C (*(s8*)address(0x8008FD8Cu,actual))
#define D_800D23B0 (*(s32*)address(0x800D23B0u,actual))
f32 func_150ADA68(void){const struct Effect*e;if(ordinal>=c->calls)fail(22);e=effects+c->effect+ordinal;
 apply(actual,e->first,e->count);return real(samples[c->sample+ordinal++]);}
BODY
void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;ordinal=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->expected,c->expected_count);
 func_1508BC20();if(ordinal!=c->calls)fail(23);for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(21);
 }fail(0);}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
        'PATCHES',','.join(patches)).replace('EFFECTS',','.join(effects)).replace('CASES',',\n'.join(rows)).replace(
        'SAMPLES',','.join('0x%Xu'%v for v in samples)).replace('BODY',body)
