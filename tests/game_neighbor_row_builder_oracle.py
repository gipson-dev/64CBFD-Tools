"""Independent neighbor ranking, signed cursor, callback and integer trap reference."""
from dataclasses import dataclass, replace
import math

from tools.experiments import game_neighbor_row_builder_candidates as source
from tools.tests import game_actor_pair_scheduler_oracle as previous

core, STACK = previous.core, previous.STACK
put, read, bits, floating, f32, signed = previous.put, previous.read, previous.bits, previous.floating, previous.f32, previous.signed
CONTEXT, PRIMARY, ACTORS, FIELD = 0x800D23B0, 0x8008FD90, 0x800CC2D0, 0x150859AC
FIELD_TABLE, FIELD_VALUES = 0x8009D9A0, 0x800D2148
BANKS = (0x30000, 0x40000)
SEGMENTS = tuple((b - 0x2400, 0x5000) for b in BANKS) + ((ACTORS, 32 * 0x32C),
    (CONTEXT, 4), (PRIMARY, 1), (FIELD_TABLE, 28), (FIELD_VALUES, 32 * 28))


@dataclass(frozen=True)
class Case:
    count: int = 6
    cursor: int = -1
    enabled: int = 0xFFFFFFFF
    primary: int = 2
    mode: int = 0xB8
    multiplier: float = 1.25
    groups: tuple = ()
    teams: tuple = ()
    active: tuple = ()
    states: tuple = ()
    flags: tuple = ()
    special: tuple = ()
    points: tuple = ()
    mask: int = 0xFFFFFFFF
    answers: tuple = (0, 1, 2, 3)
    mutation: int = 0


def cases():
    yield Case()
    for count in (-2147483648, -1, 0, 1, 2, 3, 8, 16, 17, 26): yield Case(count=count)
    for cursor in range(-128, 128): yield Case(cursor=cursor, enabled=0)
    for cursor in (0, 1, 4, 5, 6, 15, 16, 30): yield Case(cursor=cursor)
    for enabled in (0, 1, 2, 0x80000000): yield Case(enabled=enabled)
    for cursor in (-1, 0, 4, 5, 6, 15, 127): yield Case(cursor=cursor, enabled=0)
    for primary in (-128, -1, 0, 1, 6, 127): yield Case(primary=primary)
    for mode in (-32768, -1, 0, 0xB7, 0xB8, 0xB9, 32767):
        yield Case(mode=mode, states=(2, 3, 4, 0, 1, -1), special=(1,))
    for mask in (0, 1, 0x10000, 0x20000, 0xAAAA0000, 0xFFFF):
        yield Case(mask=mask, states=(0, 2, 3), flags=(1,))
    for distance in (2499., 2500., 2501., 2999., 3000., 3001., 32000., 40000.):
        yield Case(points=((0., 0.), (distance, 0.)), teams=(0, 1), flags=(255,), count=2)
    for groups in ((0,), (0, 1), (-1, 0, 1), (0, 1, 1, 0, 3, 4)):
        yield Case(groups=groups)
    for active in ((0,), (-1,), (1, -1, 0, 1, 2, 3)):
        yield Case(active=active)
    yield Case(points=((0., 0.), (3., 4.)), count=16, primary=0)
    yield Case(points=((0., 0.), (3., 4.)), count=26, primary=0)
    for value in (-2., -.25, -0., 0., .25, 1., 1.75, math.nan, math.inf): yield Case(multiplier=value)
    for value in (math.nan, math.inf, -math.inf, 2147483648.):
        yield Case(count=2, points=((0., 0.), (value, 0.)))
    for answer in (-3, -2, -1, 0, 1, 10, 2147483647, -2147483648):
        yield Case(count=2, mode=0xB7, special=(1,), answers=(answer,))
    yield Case(count=2, mode=0xB7, special=(1,), answers=(-3,), points=((0., 0.), (math.inf, 0.)))
    for mutation in range(1, 10):
        yield Case(mode=0xB7, special=(1,), mutation=mutation, count=2 if mutation==8 else 6)


def native_cases():
    return tuple(c for c in cases() if -1 <= c.cursor < 15 and
        c.mutation != 8 and math.isfinite(c.multiplier) and all(math.isfinite(v) and abs(v) < 1e7
        for p in c.points for v in p) and reference(fixture(c), c)[-1] is None)


def initial(case):
    rows = []
    for bank in BANKS:
        rows.extend(((bank + 0x10, case.count, 4), (bank + 0x14, case.enabled, 4),
            (bank + 0x16BC, case.mode, 2),
            (bank + 0x16B8, bits(case.multiplier if bank == BANKS[0] else 2.), 4)))
        for i in range(32):
            rows.extend(((bank + 0xE64 + i*4, case.groups[i%len(case.groups)] if case.groups else i, 4),
                (bank + 0x9C + i*4, case.teams[i%len(case.teams)] if case.teams else 0, 4),
                (bank + 0x39C + i*4, case.active[i%len(case.active)] if case.active else 1, 4),
                (bank + 0x15C + i*4, case.states[i%len(case.states)] if case.states else 0, 4),
                (bank + 0x16C0 + i*4, case.mask, 4)))
        rows.append((bank + 0x1704, case.cursor, 1))
    for i in range(32):
        x,z = case.points[i%len(case.points)] if case.points else (float(i*100),0.)
        rows.extend(((ACTORS+i*0x32C+0x14,bits(x),4),(ACTORS+i*0x32C+0x1C,bits(z),4),
            (ACTORS+i*0x32C+0x65,case.flags[i%len(case.flags)] if case.flags else 0,1),
            (ACTORS+i*0x32C+0x13C,case.special[i%len(case.special)] if case.special else 0,1),
            (FIELD_VALUES+i*28,case.answers[i%len(case.answers)],4)))
    rows.extend(((PRIMARY,case.primary,1),(CONTEXT,BANKS[0],4)))
    return rows


def fixture(case):
    memory = {STACK+i:(i*19+0xA5)&255 for i in range(-0x600,0x100)}
    for base,size in SEGMENTS: memory.update((base+i,0xA5) for i in range(size))
    for at,value,size in initial(case): put(memory,at,value,size)
    return memory


def public(memory): return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x100}


def trunc(value):
    return math.trunc(value) if math.isfinite(value) and -2147483648. <= value < 2147483648. else -2147483648


def changes(case, ordinal):
    if ordinal: return []
    b=BANKS[0]
    return {
        1:[(CONTEXT,BANKS[1],4)],
        2:[(b+0x39C+2*4,0,4),(b+0xE64+3*4,0,4)],
        3:[(PRIMARY,0,1)],
        4:[(b+0x16BC,0xB8,2)],
        5:[(b+0x16B8,bits(-.25),4),(PRIMARY,3,1)],
        6:[(b+0xE64,99,4)],
        7:[(b+0x10,0,4),(b+0x1704,91,1)],
        8:[(CONTEXT,0xFFFFFAE4,4),(PRIMARY,0,1)],
        9:[(b+0x9C,1,4)],
    }.get(case.mutation,[])


def reference(memory, case, actual=False):
    m,calls,stores,transcript=memory.copy(),[],[],[]
    def store(at,value,size):
        at &= 0xFFFFFFFF;value &= (1<<(size*8))-1
        put(m,at,value,size);stores.append((at,size,value))
    def word(at): return signed(read(m,at&0xFFFFFFFF,4))
    b=read(m,CONTEXT,4);groups=b+0xE64;states=b+0x15C;teams=b+0x9C;active=b+0x39C
    neighbors,scores=b+0x5DC,b+0x9DC;count=word(b+0x10);enabled=read(m,b+0x14,4)
    store(b+0x1704,signed(read(m,b+0x1704,1),8)+1,1)
    live=read(m,CONTEXT,4);slot=signed(read(m,live+0x1704,1),8)
    if word(live+0x10)==slot:
        store(live+0x1704,0,1);live=read(m,CONTEXT,4);slot=signed(read(m,live+0x1704,1),8)
    start=slot*16
    if not enabled&(1<<(slot&31)):
        for i in range(16): store(neighbors+(start+i)*4,-1,4)
        return 0,m,calls,stores,transcript,None
    group=word(groups+slot*4);mask=read(m,(live+slot*4+0x16C0)&0xFFFFFFFF,4)
    used=0;nearest=32000
    if count>32:raise ValueError('Outside bounded completed row-builder reference')
    for i in range(max(count,0)):
        if word(active+i*4)<=0 or group==word(groups+i*4):continue
        actor=(ACTORS+i*0x32C)&0xFFFFFFFF;selected=(ACTORS+slot*0x32C)&0xFFFFFFFF
        primary=signed(read(m,PRIMARY,1),8);mode=signed(read(m,(read(m,CONTEXT,4)+0x16BC)&0xFFFFFFFF,2),16)
        if actor:
            dx=f32(floating(read(m,selected+0x14,4))-floating(read(m,actor+0x14,4)))
            dz=f32(floating(read(m,selected+0x1C,4))-floating(read(m,actor+0x1C,4)))
            distance=trunc(f32(math.sqrt(f32(f32(dx*dx)+f32(dz*dz)))))
        else:distance=32000
        score=distance
        if word(teams+slot*4)!=word(teams+i*4):score=signed(score+500)
        if mask&((0x10000<<(i&31))&0xFFFFFFFF):
            if score>=3001 and read(m,actor+0x65,1):score=-1
        else:
            if i>=primary:score=signed(score*2)
            if mode!=0xB8 and word(states+i*4) in (2,3):score=-1
        if mode==0xB7:
            if score==-1:score=distance
            if read(m,actor+0x13C,1):
                if i>=primary:score=signed(score*2)
                ordinal=len(calls);arg=signed(i,16);calls.append((FIELD,arg&0xFFFFFFFF,6))
                answer=word(FIELD_VALUES+arg*28) if actual else case.answers[ordinal%len(case.answers)]
                effects=[] if actual else changes(case,ordinal)
                for at,value,size in effects:store(at,value,size)
                transcript.append((arg,answer,effects))
                denominator=signed(answer+2);primary=signed(read(m,PRIMARY,1),8)
                if denominator==0:return None,m,calls,stores,transcript,7
                if denominator==-1 and score==-2147483648:return None,m,calls,stores,transcript,6
                score=(abs(score)//abs(denominator))*(-1 if (score<0)!=(denominator<0) else 1)
        if i<primary and score!=-1:
            scale=floating(read(m,(read(m,CONTEXT,4)+0x16B8)&0xFFFFFFFF,4))
            score=trunc(f32(f32(score)*scale))
        if score>=0:
            pos=0
            while pos<used and word(scores+(start+pos)*4)<score:pos+=1
            for copy in range(used,pos,-1):
                store(neighbors+(start+copy)*4,word(neighbors+(start+copy-1)*4),4)
                store(scores+(start+copy)*4,word(scores+(start+copy-1)*4),4)
            store(neighbors+(start+pos)*4,i,4);used+=1;store(scores+(start+pos)*4,score,4)
        nearest=min(nearest,distance)
    for i in range(used,16):store(neighbors+(start+i)*4,-1,4)
    current=read(m,CONTEXT,4)
    if (current+0x51C)&0xFFFFFFFF:store(current+slot*4+0x51C,nearest,4)
    return 0,m,calls,stores,transcript,None


class BreakFault(Exception):
    def __init__(self,code):self.code=code


class RowModel(previous.SchedulerModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY):
        core.CopyModel.__init__(self,words,memory,(),phase=phase,connected=connected,entry=entry)
        self.case,self.condition,self.requested=case,False,None
        self.ordinal=0
        self.f[20:]=[0x3F800000+i for i in range(20,32)];self.saved_f=self.f[20:].copy()

    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn==13:self.f[fd]=trunc(floating(self.f[rd]))&0xFFFFFFFF
        elif op==0 and fn==26:
            a,b=signed(self.r[rs]),signed(self.r[rt])
            q=(-1 if a>=0 else 1) if b==0 else -2147483648 if a==-2147483648 and b==-1 else (
                (abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1))
            self.lo=q&0xFFFFFFFF;self.hi=(a if b==0 else a-q*b)&0xFFFFFFFF
        elif op==0 and fn==13:raise BreakFault(word>>16&0x3FF)
        else:super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append(());return
        if target!=FIELD:raise AssertionError('Unexpected row-builder provider %X'%target)
        self.calls.append((target,*self.r[4:6]));self.events.append(('CALL',target,tuple(self.r[4:6])))

    def hook(self,target):
        assert target==FIELD
        self.in_hook=True
        try:
            answer=self.case.answers[self.ordinal%len(self.case.answers)]
            for at,value,size in changes(self.case,self.ordinal):self.put(at,value,size)
            self.ordinal+=1
            for i in range(4):self.put(self.r[29]+i*4,0xBA000000+i,4)
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.r[2]=answer&0xFFFFFFFF;self.f[:20]=[0xA5000000+i for i in range(20)]
            self.condition=not self.condition
        finally:self.in_hook=False


def native_harness(body, corpus):
    offsets, total = [], 0
    for _, size in SEGMENTS:
        total = (total + 15) & ~15; offsets.append(total); total += size
    patches, calls, rows = [], [], []
    def append(entries, translate=True):
        first = len(patches)
        for a,value,size in entries:
            patches.append('{0x%Xu,0x%Xu,%d,%d}' % (a,value&0xFFFFFFFF,size,translate and a==CONTEXT and size==4))
        return first,len(patches)-first
    for case in corpus:
        result,_,_,stores,transcript,trap = reference(fixture(case),case)
        if trap: raise ValueError('Native invalid division is excluded explicitly')
        seeded = initial(case)
        first,count = append(seeded[:-1],False); append(seeded[-1:]); count += 1
        wanted,written = append((a,v,n) for a,n,v in stores)
        call_first = len(calls)
        for arg,answer,effects in transcript:
            effect_first,effect_count = append(effects)
            calls.append('{0x%Xu,0x%Xu,%d,%d}' % (arg&0xFFFFFFFF,answer&0xFFFFFFFF,effect_first,effect_count))
        rows.append('{%s}' % ','.join(str(v) for v in (first,count,wanted,written,call_first,len(transcript),result)))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;
typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static u32 diagnostic[3];
static __attribute__((noreturn)) void fail(u32 code){diagnostic[0]=code;if(code){
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(diagnostic),"d"(sizeof(diagnostic)):"memory");}
 __asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;diagnostic[2]=a;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++){
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];}fail(29);}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 slot,answer,first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,callFirst,callCount,result;};static const struct Case cases[]={CASES};
static const struct Case*c;static u32 number;
static void apply(u8*b,u32 first,u32 count){u32 i,v;u8*p;const struct Patch*q;for(i=0;i<count;i++){
 q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(u16*)p=(u16)v;else*(u32*)p=v;}}
#define D_800D23B0 (*(s32*)address(0x800D23B0u,actual))
#define D_8008FD90 (*(s8*)address(0x8008FD90u,actual))
#define D_800CC2D0 (address(0x800CC2D0u,actual))
static s32 func_150859AC(s16 slot,s32 field){const struct Call*q;if(number>=c->callCount)fail(22);
 q=calls+c->callFirst+number++;if((u32)(s32)slot!=q->slot||field!=6)fail(23);
 apply(actual,q->first,q->count);return (s32)q->answer;}
static f32 sqrtf(f32 v){return __builtin_sqrtf(v);}
BODY
void _start(void){u32 n,i,result;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 diagnostic[1]=n;c=cases+n;number=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 result=(u32)func_1508A1BC();if(result!=c->result)fail(21);if(number!=c->callCount)fail(25);
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(26);}
 fail(0);}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o)
        for (b,n),o in zip(SEGMENTS,offsets))).replace('PATCHES',','.join(patches)).replace(
        'CALLS',','.join(calls)).replace('CASES',',\n'.join(rows)).replace('BODY',body)
