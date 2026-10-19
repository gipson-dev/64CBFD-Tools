"""Float32 pair-position/mask reference with explicit opaque provider effects."""
from dataclasses import dataclass, replace
import math

from tools.experiments import game_actor_pair_visibility_candidates as source
from tools.tests import game_actor_sine_selector_oracle as previous

core, STACK = previous.core, previous.STACK
put, read = previous.put, previous.read
bits, floating, f32 = previous.bits, previous.floating, previous.f32
CONTEXT, MODE, TABLE = 0x800D23B0, 0x800E0BD0, 0x800872C4
LOOKUP, QUERY, BARRIER = 0x1505EEF4, 0x150AC9C0, 0x15086D94
ACTORS, NESTED = 0x30000, 0x32000
BANKS = (0x20000, 0x22000)
ALIAS = CONTEXT - 0x16C0
SEGMENTS = ((BANKS[0], 0x1900), (BANKS[1], 0x1900), (ACTORS, 0x32C * 2),
    (NESTED, 0x140 * 2), (MODE, 1), (TABLE - 256, 512), (ALIAS, 0x1900))


@dataclass(frozen=True)
class Case:
    first: int = 0
    second: int = 1
    found: tuple = (True, True)
    active: tuple = (0, 0)
    kinds: tuple = (0, 0)
    nested_kinds: tuple = (0, 0)
    heights: tuple = (-321, 257)
    points: tuple = ((1.25, 2.5, 3.75), (10.5, 20.75, -4.25))
    shorts: tuple = ((-32768, 17, 32767), (32767, -12345, -32768))
    mode: int = 2
    table: int = 1
    query: int = 0
    hit: float = 100.
    writes: bool = True
    barrier: float = -1.
    mutation: int = 0
    alias: bool = False


def cases():
    yield Case()
    for a in (0, 1, 255):
        for b in (0, 1, 255):
            for ka, kb in ((0, 0), (31, 0), (0, 31), (31, 31)):
                yield Case(active=(a, b), kinds=(ka, kb))
    for a, b in ((9, 0), (0, 9), (137, 137), (8, 10), (255, 255)):
        yield Case(active=(1, 1), nested_kinds=(a, b))
    for mode in range(-128, 128):
        yield Case(mode=mode, active=(0, 1), table=-1 if mode & 1 else -32768)
    for table in (-32768, -1, 0, 1, 32767):
        yield Case(active=(1, 0), table=table)
    for found in ((False, False), (False, True), (True, False)):
        yield Case(found=found)
    plain = Case(points=((0., 0., 0.), (3., 0., 4.)))
    for hit in (0., floating(bits(5.) - 1), 5., floating(bits(5.) + 1), 100., math.nan, math.inf, -math.inf):
        for barrier in (-1., -0., 0., .5, math.nan, math.inf, -math.inf):
            yield replace(plain, query=1, hit=hit, barrier=barrier)
    for query in (0, -1, 2, 0x80000000):
        yield replace(plain, query=query, hit=6.)
    yield replace(plain, query=0, writes=False)
    for mutation in range(1, 7):
        yield replace(plain, mutation=mutation)
    for index in range(32):
        yield replace(plain, first=index, second=31-index)
    for key in (0x1000, 0xF001, 0x10001, -1, -2147483648, 2147483647):
        yield replace(plain, first=key, second=key, found=(False, False))
    yield replace(plain, first=0, second=2, alias=True)
    for actor in range(2):
        for axis in range(3):
            for value in (math.nan, math.inf, -math.inf):
                points = [list(p) for p in plain.points]
                points[actor][axis] = value
                yield replace(plain, points=tuple(tuple(p) for p in points), query=1, hit=5.)


def signed(v, width=32):
    return ((v & ((1 << width) - 1)) ^ (1 << (width - 1))) - (1 << (width - 1))


def bank(case):
    return ALIAS if case.alias else BANKS[0]


def initial(case):
    rows = []
    for i in range(2):
        actor, nested = ACTORS + i * 0x32C, NESTED + i * 0x140
        rows.extend(((actor, case.kinds[i], 4), (actor + 0x31C, nested, 4),
            (nested + 0x84, case.active[i], 1), (nested + 0x75, case.nested_kinds[i], 1),
            (nested + 0x114, case.heights[i], 2)))
        rows.extend((actor + 0x14 + n * 4, bits(v), 4) for n, v in enumerate(case.points[i]))
        rows.extend((actor + 0x1A4 + n * 2, v, 2) for n, v in enumerate(case.shorts[i]))
    rows.extend((base + 0x16C0 + i * 4, (i * 0x01010101) ^ 0x80402010, 4)
        for base in (*BANKS, ALIAS) for i in range(32) if base != ALIAS or i != 0)
    rows.extend(((MODE, case.mode, 1), (TABLE + case.mode * 2, case.table, 2), (CONTEXT, bank(case), 4)))
    return rows


def fixture(case):
    m = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x600, 0x100)}
    for base, size in SEGMENTS:
        m.update({base + i: 0xA5 for i in range(size)})
    for a, value, size in initial(case):
        put(m, a, value, size)
    return m


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x600 <= a < STACK + 0x100}


def changes(case, target, ordinal=0):
    if case.mutation == 1 and target == LOOKUP and ordinal == 0:
        return [(ACTORS + 0x32C + 0x14, bits(13.), 4), (MODE, 0, 1), (TABLE, -1, 2)]
    if case.mutation == 2 and target == LOOKUP and ordinal == 1:
        return [(CONTEXT, BANKS[1], 4), (NESTED + 0x84, 1, 1), (NESTED + 0x114, 32767, 2)]
    if case.mutation == 3 and target == QUERY:
        return [(CONTEXT, BANKS[1], 4), (ACTORS + 0x14, bits(999.), 4), (ACTORS + 0x1C, bits(-999.), 4)]
    if case.mutation == 4 and target == BARRIER:
        return [(CONTEXT, BANKS[1], 4)]
    if case.mutation == 5 and target == QUERY:
        return [(bank(case) + 0x16C0 + case.first * 4, 0x40000000, 4)]
    if case.mutation == 6 and target == BARRIER:
        return [(bank(case) + 0x16C0 + case.second * 4, 0x80000000, 4)]
    return []


def reference(memory, case):
    m, calls, stores, transcript = memory.copy(), [], [], []
    def store(a, value, size):
        value &= (1 << (size * 8)) - 1
        put(m, a, value, size)
        stores.append((a, size, value))
    def provider(target, args, ordinal=0):
        calls.append((target, *args))
        writes = changes(case, target, ordinal)
        for a, value, size in writes:
            store(a, value, size)
        transcript.append((target, args, writes))
    for i, key in enumerate((case.first, case.second)):
        provider(LOOKUP, (key & 0xFFFF0FFF,), i)
    clear = broad = 0
    if all(case.found):
        def point(i, opposite):
            actor, nested = ACTORS + i * 0x32C, NESTED + i * 0x140
            p = [floating(read(m, actor + at, 4)) for at in (0x14, 0x18, 0x1C)]
            if read(m, nested + 0x84, 1):
                p[1] = f32(p[1] + f32(f32(signed(read(m, nested + 0x114, 2), 16)) * .75))
                if read(m, nested + 0x75, 1) & 127 == 9:
                    p[1] = f32(p[1] - 50.)
            elif read(m, actor, 4) == 31:
                p[1] = f32(p[1] + 80.)
            elif opposite and signed(read(m, TABLE + signed(read(m, MODE, 1), 8) * 2, 2), 16) != -1:
                p = [f32(signed(read(m, actor + at, 2), 16)) for at in (0x1A4, 0x1A6, 0x1A8)]
            else:
                p[1] = f32(p[1] + 40.)
            return p
        active = read(m, NESTED + 0x84, 1)
        other_active = read(m, NESTED + 0x140 + 0x84, 1)
        a, b = point(0, other_active), point(1, active)
        d = [f32(v - u) for u, v in zip(a, b)]
        squares = [f32(v * v) for v in d]
        distance = f32(math.sqrt(f32(f32(squares[0] + squares[1]) + squares[2])))
        provider(QUERY, (*map(bits, a + d), 0, 0, 0, 0, 0, 0, 0, 0, bits(0.)))
        broad = not case.query or distance < f32(case.hit)
        clear = broad
        if clear:
            provider(BARRIER, tuple(map(bits, (*a, d[0], d[2]))))
            if f32(case.barrier) > 0.:
                clear = False
    for enabled, mask in ((clear, 1), (broad, 0x10000)):
        if enabled:
            for a, b in ((case.first, case.second), (case.second, case.first)):
                at = (read(m, CONTEXT, 4) + ((a & 0xFFFFFFFF) << 2) + 0x16C0) & 0xFFFFFFFF
                store(at, read(m, at, 4) | ((mask << (b & 31)) & 0xFFFFFFFF), 4)
    return m, calls, stores, transcript


class PairModel(previous.SelectorModel):
    def __init__(self, words, memory, case, phase=0, connected=None, entry=source.ENTRY):
        core.CopyModel.__init__(self, words, memory, (case.first, case.second), phase=phase,
            connected=connected, entry=entry)
        self.case, self.condition, self.requested = case, False, None
        self.lookup_ordinal, self.raw_calls, self.outputs = 0, [], []
        self.f[20:] = [0x3F800000 + i for i in range(20, 32)]
        self.saved_f = self.f[20:].copy()

    def args(self, count):
        return tuple(self.r[4 + i] if i < 4 else read(self.memory, self.r[29] + i * 4, 4) for i in range(count))

    def record_call(self, target):
        if target == source.ENTRY:
            self.caller_args.append(tuple(self.r[4:6]))
            return
        if target == LOOKUP:
            args = (self.r[4],)
        elif target == QUERY:
            args = (self.f[12], self.f[14], *self.args(15)[2:])
            self.outputs = args[8:12]
            if len(set(self.outputs)) != 4 or any(p & 3 for p in self.outputs):
                raise AssertionError('Pair query output pointers are not distinct aligned cells')
        elif target == BARRIER:
            args = (self.f[12], self.f[14], *self.args(5)[2:])
        else:
            raise AssertionError('Unexpected pair provider: %X' % target)
        self.current_args = args
        self.raw_calls.append((target, *args))
        logical = args[:8] + (0,) * 4 + args[12:] if target == QUERY else args
        self.calls.append((target, *logical))
        self.events.append(('CALL', target))

    def hook(self, target):
        self.in_hook = True
        try:
            for a, value, size in changes(self.case, target, self.lookup_ordinal):
                self.put(a, value, size)
            if target == LOOKUP:
                result = ACTORS + self.lookup_ordinal * 0x32C if self.case.found[self.lookup_ordinal] else 0
                self.lookup_ordinal += 1
            elif target == QUERY:
                result = self.case.query
                if self.case.writes:
                    for i, address in enumerate(self.outputs):
                        self.put(address, bits(self.case.hit) if i == 3 else ACTORS + i * 4, 4)
            else:
                result = 0xDEADC0DE
            for i in range(15 if target == QUERY else 5 if target == BARRIER else 4):
                self.put(self.r[29] + i * 4, 0xBA000000 + i, 4)
            for reg in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[reg] = 0xA5000000 + reg
            self.r[2] = result & 0xFFFFFFFF
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            if target == BARRIER:
                self.f[0] = bits(self.case.barrier)
            self.condition = not self.condition
        finally:
            self.in_hook = False


def native_harness(body, corpus):
    offsets, total = [], 0
    for _, size in SEGMENTS:
        total = (total + 15) & ~15
        offsets.append(total)
        total += size
    patches, calls, rows = [], [], []
    def append(entries):
        first = len(patches)
        for a, value, size in entries:
            pointer = size == 4 and (a == CONTEXT or a in (ACTORS + 0x31C, ACTORS + 0x32C + 0x31C))
            patches.append('{0x%Xu,0x%Xu,%d,%d}' % (a, value & 0xFFFFFFFF, size, pointer))
        return first, len(patches) - first
    for case in corpus:
        _, _, stores, transcript = reference(fixture(case), case)
        first, count = append(initial(case))
        wanted, written = append((a, value, size) for a, size, value in stores)
        call_first = len(calls)
        ordinal = 0
        for target, args, effects in transcript:
            effect_first, effect_count = append(effects)
            if target == LOOKUP:
                result = ACTORS + ordinal * 0x32C if case.found[ordinal] else 0
                ordinal += 1
            else:
                result = case.query if target == QUERY else bits(case.barrier)
            args = (*args, *(0 for _ in range(15 - len(args))))
            calls.append('{0x%Xu,{%s},0x%Xu,%d,%d}' % (target,
                ','.join('0x%Xu' % a for a in args), result & 0xFFFFFFFF, effect_first, effect_count))
        rows.append('{%s}' % ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in (
            first, count, wanted, written, call_first, len(transcript), case.first, case.second, bits(case.hit), case.writes)))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];fail(29);}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 target,a[15],result,first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,callFirst,callCount,a,b,hit,writes;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 ordinal;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void apply(u8*b,u32 first,u32 count){u32 i,v;const struct Patch*q;u8*p;
 for(i=0;i<count;i++){q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(s16*)p=(s16)v;else*(u32*)p=v;}}
static const struct Call*invoke(u32 target,u32 n,const u32*a){u32 i;const struct Call*q;
 if(ordinal>=c->callCount)fail(22);q=calls+c->callFirst+ordinal++;
 if(q->target!=target)fail(22);for(i=0;i<n;i++){
 if(target==0x15086D94u||(target==0x150AC9C0u&&(i<6||i==14))){if(!same(a[i],q->a[i]))fail(23);}
 else if(a[i]!=q->a[i])fail(23);}
 apply(actual,q->first,q->count);return q;}
#define D_800D23B0 (*(s32*)address(0x800D23B0u,actual))
#define D_800E0BD0 (*(s8*)address(0x800E0BD0u,actual))
#define D_800872C4 ((s16*)address(0x800872C4u,actual))
u8*func_1505EEF4(s32 key){u32 a[]={(u32)key};const struct Call*q=invoke(0x1505EEF4u,1,a);return q->result?address(q->result,actual):NULL;}
s32 func_150AC9C0(f32 x,f32 y,f32 z,f32 dx,f32 dy,f32 dz,s32 zeroA,s32 zeroB,
 void**outA,void**outB,void**outC,f32*distance,s32 zeroC,s32 zeroD,f32 zeroE){
 u32 a[]={word(x),word(y),word(z),word(dx),word(dy),word(dz),(u32)zeroA,(u32)zeroB,0,0,0,0,(u32)zeroC,(u32)zeroD,word(zeroE)};
 const struct Call*q=invoke(0x150AC9C0u,15,a);
 if(!outA||!outB||!outC||!distance||outA==outB||outA==outC||outB==outC)fail(26);
 if(c->writes){*outA=address(0x30000u,actual);*outB=address(0x30004u,actual);*outC=address(0x30008u,actual);*distance=real(c->hit);}return(s32)q->result;}
f32 func_15086D94(f32 x,f32 y,f32 z,f32 dx,f32 dz){u32 a[]={word(x),word(y),word(z),word(dx),word(dz)};return real(invoke(0x15086D94u,5,a)->result);}
f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
BODY
void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;ordinal=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 func_1508C1A4((s32)c->a,(s32)c->b);if(ordinal!=c->callCount)fail(25);
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(24);
 }fail(0);}
'''.replace('SIZE', str(total)).replace('REGIONS', ','.join('{0x%Xu,%d,%d}' % (base, size, offset)
        for (base, size), offset in zip(SEGMENTS, offsets))).replace('PATCHES', ','.join(patches)).replace(
        'CALLS', ',\n'.join(calls)).replace('CASES', ',\n'.join(rows)).replace('BODY', body)
