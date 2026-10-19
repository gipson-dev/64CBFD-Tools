"""Independent neighbor-row reference and explicit two-helper mutation providers."""
from dataclasses import dataclass
import math

from tools.experiments import game_weighted_target_selection_candidates as source
from tools.tests import game_actor_sine_selector_oracle as previous

STACK,put,read=previous.STACK,previous.put,previous.read
bits,floating,f32,signed=previous.bits,previous.floating,previous.f32,previous.signed
public=previous.public
CONTEXT,ACTORS=0x800D23B0,0x800CC2D0
BANKS=(0x20000,0x22000,0x24000)
PREPARE,SCAN=0x1508C5B8,0x1508A1BC
FAVOR,UNIT=0x8009DA60,0x8009DA64
SCALES={FAVOR:0x3F4CCCCD,UNIT:0x3B808081}
SEGMENTS=tuple((b,0x1800) for b in BANKS)+((ACTORS,16*0x32C),(CONTEXT,4),(0x8009DA60,8))


@dataclass(frozen=True)
class Case:
    count:int=4
    current:int=3
    active:tuple=()
    positions:tuple=(0,)
    sentinel:int=16
    scores:tuple=()
    weights:tuple=(255,)
    preferred:int=-1
    points:tuple=()
    mutation:int=0


def cases():
    for count in (-2147483648,-1,0,1,2,8,9,16):yield Case(count=count)
    for current in (0,1,7,15):yield Case(count=16,current=current)
    for active in ((0,),(-1,),(-2147483648,),(1,),(2147483647,),(0,1,-1,1)):
        yield Case(active=active)
    for position in (-1,0,1,7,14,15):
        for sentinel in (0,4,15,16):yield Case(positions=(position,),sentinel=sentinel)
    for weight in (0,1,127,128,254,255):
        for score in (-2147483648,-2,-1,0,1,9999999,10000000,10000001,123456789):
            yield Case(scores=(score,),weights=(weight,))
    for preferred in (-1,0,1,2,3):yield Case(scores=(1000,1000,1000,1000),preferred=preferred)
    for mutation in range(1,5):yield Case(mutation=mutation,preferred=1,scores=(1000,20,300,400))
    yield Case(mutation=3,preferred=1,scores=(10,1000,300,400))
    yield Case(positions=(15,7,0),points=((-1000.25,2000.5),(0.125,-2.75),(3.,4.),(8.,-7.)))


def initial(case):
    rows=[(CONTEXT,BANKS[0],4)]
    for bank,base in enumerate(BANKS):
        rows.extend(((base+4,case.current if not bank else (case.current+1)&15,4),
            (base+0x10,case.count if not bank else 0,4),
            (base+0x11C+case.current*4,case.preferred if not bank else 0,4)))
        for i in range(16):
            rows.append((base+0x39C+i*4,(case.active[i%len(case.active)] if case.active else 1) if not bank else 0,4))
            weight=case.weights[i%len(case.weights)] if not bank else (255 if bank==1 else 255 if i!=1 else 1)
            rows.append((base+case.current*16+0x15B4+i,weight,1))
            position=case.positions[i%len(case.positions)]
            score=case.scores[i%len(case.scores)] if case.scores else 400+i*100
            for j in range(16):
                value=-1 if bank or j==case.sentinel else case.current if j==position else (case.current+1)&15
                rows.extend(((base+0x5DC+(i*16+j)*4,value,4),(base+0x9DC+(i*16+j)*4,score if not bank else 10000000,4)))
    for i in range(16):
        x,z=case.points[i%len(case.points)] if case.points else (i*300.,i*400.)
        rows.extend(((ACTORS+i*0x32C+0x14,bits(x),4),(ACTORS+i*0x32C+0x1C,bits(z),4)))
    rows.extend((a,v,4) for a,v in SCALES.items());return rows


def fixture(case):
    memory={STACK+i:0xA5 for i in range(-0x500,0x100)}
    for base,size in SEGMENTS:memory.update({base+i:0xA5 for i in range(size)})
    for a,v,n in initial(case):put(memory,a,v,n)
    return memory


def changes(case,ordinal):
    base=BANKS[0]
    if case.mutation==1:return [(CONTEXT,BANKS[ordinal+1],4)]
    if case.mutation==2:return [(base+0x10,0,4),(base+4,(case.current+1)&15,4)] if not ordinal else []
    if case.mutation==3:
        return [(base+0x39C,0,4)] if not ordinal else [(base+0x9DC+16*4,10,4),
            (base+0x11C+case.current*4,1,4),(base+case.current*16+0x15B4+1,128,1)]
    if case.mutation==4:
        return [(FAVOR,bits(.25),4)] if not ordinal else [(UNIT,bits(.5),4),
            (ACTORS+0x14,bits(99.5),4),(ACTORS+0x1C,bits(-123.25),4)]
    return []


def reference(memory,case):
    m=memory.copy();initial_context=read(m,CONTEXT,4)
    count=signed(read(m,initial_context+0x10,4));current=signed(read(m,initial_context+4,4))
    active=initial_context+0x39C;neighbors=initial_context+0x5DC
    distances=initial_context+0x9DC;targets=initial_context+0x11C
    calls=[(PREPARE,0,1 if count<9 else 4),(SCAN,)]
    stores=[]
    for ordinal in range(2):
        for a,v,n in changes(case,ordinal):put(m,a,v,n);stores.append((a,n,v&((1<<(n*8))-1)))
    context=read(m,CONTEXT,4);selected=-1;best=10000000
    if count>0:
        scale=floating(read(m,UNIT,4));favor=floating(read(m,FAVOR,4))
        if count>16:raise ValueError('Outside the bounded completed row reference')
        for i in range(count):
            if signed(read(m,active+i*4,4))<=0 or i==current:continue
            score=None
            for j in range(16):
                at=i*16+j;neighbor=signed(read(m,neighbors+at*4,4))
                if neighbor==-1:break
                if neighbor==current:
                    score=signed(read(m,distances+at*4,4));break
            if score is None or score==-1:continue
            weight=f32(read(m,context+current*16+0x15B4+i,1)*scale)
            if signed(read(m,targets+current*4,4))==i:weight=f32(weight*favor)
            value=f32(f32(score)*weight)
            if not -2147483648<=value<2147483648:raise ValueError('Out-of-range native float cast')
            score=math.trunc(value)
            if score<best:best,selected=score,i
    a=(context+current*4+0x49C)&0xFFFFFFFF
    put(m,a,selected,4);stores.append((a,4,selected&0xFFFFFFFF))
    if selected!=-1:
        actor=(ACTORS+current*0x32C)&0xFFFFFFFF;target=(ACTORS+selected*0x32C)&0xFFFFFFFF
        dx=f32(floating(read(m,actor+0x14,4))-floating(read(m,target+0x14,4)))
        dz=f32(floating(read(m,actor+0x1C,4))-floating(read(m,target+0x1C,4)))
        best=math.trunc(f32(math.sqrt(f32(f32(dx*dx)+f32(dz*dz)))))
    a=(read(m,CONTEXT,4)+current*4+0x45C)&0xFFFFFFFF
    put(m,a,best,4);stores.append((a,4,best&0xFFFFFFFF))
    return m,calls,stores,selected,best


class WeightedModel(previous.SelectorModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY):
        previous.core.CopyModel.__init__(self,words,memory,(),phase=phase,connected=connected,entry=entry)
        self.case=case;self.condition=False;self.ordinal=0;self.requested=None
        self.f[20:]=[0x3F800000+i for i in range(20,32)];self.saved_f=self.f[20:].copy()

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append(());return
        assert target in (PREPARE,SCAN),hex(target)
        row=(target,*self.r[4:6]) if target==PREPARE else (target,)
        self.calls.append(row);self.events.append(('CALL',*row))

    def hook(self,target):
        assert target==(PREPARE if not self.ordinal else SCAN)
        self.in_hook=True
        try:
            for a,v,n in changes(self.case,self.ordinal):self.put(a,v,n)
            # O32 callees may overwrite the caller-supplied incoming argument area.
            for i in range(4):self.put(self.r[29]+i*4,0xBA000000+self.ordinal*16+i,4)
            self.ordinal+=1
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.r[2]=0xDEADC0DE;self.f[:20]=[0xA5000000+i for i in range(20)]
        finally:self.in_hook=False


def native_harness(body,corpus):
    offsets=[];total=0
    for _,size in SEGMENTS:total=(total+15)&~15;offsets.append(total);total+=size
    patches=[];rows=[]
    def row(a,v,n):return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,a==CONTEXT)
    for case in corpus:
        memory=fixture(case);_,calls,stores,_,_=reference(memory,case)
        first=len(patches);patches.extend(row(*p) for p in initial(case));count=len(patches)-first
        wanted=len(patches);patches.extend(row(a,v,n) for a,n,v in stores);written=len(patches)-wanted
        changes_rows=[]
        for ordinal in range(2):
            at=len(patches);patches.extend(row(*p) for p in changes(case,ordinal));changes_rows.extend((at,len(patches)-at))
        rows.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d}'%(first,count,wanted,written,*changes_rows,calls[0][2]))
    defines=['#define D_800D23B0 (*(s32*)address(0x%Xu,actual))'%CONTEXT,
        '#define D_800CC2D0 ((u8*)address(0x%Xu,actual))'%ACTORS]
    defines+=['#define D_%08X (*(f32*)address(0x%Xu,actual))'%(a,a) for a in SCALES]
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static u8*address(u32 a,u8*buffer){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return buffer+regions[i][2]+a-regions[i][0];__builtin_trap();}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Case{u32 first,count,wanted,written,first0,count0,first1,count1,budget;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 number,error;
static void apply(u8*buffer,u32 first,u32 count){u32 i,v;u8*p;const struct Patch*q;for(i=0;i<count;i++){
 q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,buffer);if(q->n==1)*p=(u8)v;else*(u32*)p=v;}}
DEFINES
s32 func_1508C5B8(s32 slot,s32 budget){if(number++!=0||slot||budget!=(s32)c->budget)error=22;apply(actual,c->first0,c->count0);return 123;}
s32 func_1508A1BC(void){if(number++!=1)error=23;apply(actual,c->first1,c->count1);return -123;}
f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
BODY
void _start(void){u32 n,i;s32 result;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;number=error=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 result=func_1508B9BC();if(result)error=21;if(number!=2)error=24;
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])error=25;if(error)break;}
 __asm__ volatile("int $0x80"::"a"(1),"b"(error));__builtin_unreachable();}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
        'PATCHES',','.join(patches)).replace('CASES',',\n'.join(rows)).replace('DEFINES','\n'.join(defines)).replace('BODY',body)
