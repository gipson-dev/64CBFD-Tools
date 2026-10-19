"""Float32 barrier geometry and literal guest ABI, not hardware/FCSR emulation."""
from dataclasses import dataclass
import math

from tools.experiments import game_barrier_crossing_candidates as source
from tools.tests import game_actor_sine_selector_oracle as previous
from tools.tests.game_actor_target_timer_oracle import signed

core, STACK = previous.core, previous.STACK
put, read = previous.put, previous.read
bits, floating, f32 = previous.bits, previous.floating, previous.f32
NODES, COUNT, HEIGHT = 0x800D2350, 0x80087290, 0x15085DA8
BANKS = (0x20000, 0x22000)
SEGMENTS = ((NODES, 4), (COUNT, 2), *((b, 4096) for b in BANKS))


@dataclass(frozen=True)
class Case:
    point: tuple = (50., 2.75, -10.)
    delta: tuple = (0., 20.)
    count: int = 2
    band: int = 2
    first: tuple = (0, 0)
    second: tuple = (100, 0)
    neighbors: tuple = (1, 255, 255, 255, 255)
    first_type: int = 1
    second_type: int = 1
    first_band: int = 2
    second_band: int = 99
    extra: int = 0
    mutation: int = 0


def cases():
    yield Case()
    for count in (-32768, -1, 0, 1, 2, 4, 255, 256):
        yield Case(count=count)
    for x in (-1., -0., 0., .125, 50., 100., 100.125):
        for first, second in (((0, 0), (100, 0)), ((100, 0), (0, 0))):
            yield Case(point=(x, 0., -10.), first=first, second=second)
    for z, dz in ((0., 20.), (0., -20.), (-10., 10.), (10., -10.),
                  (-10., 0.), (10., 0.), (0., 0.), (-10., -20.), (10., 20.)):
        yield Case(point=(50., 0., z), delta=(0., dz))
    for index in range(5):
        yield Case(neighbors=tuple(1 if i == index else 255 for i in range(5)))
    for neighbors in ((0, 1, 255, 255, 255), (255, 1, 1, 255, 255), (255,) * 5,
                      (254, 255, 255, 255, 255)):
        yield Case(neighbors=neighbors, count=1)
    for first_type in (0, 1, 2, 255):
        for second_type in (0, 1, 2, 255):
            yield Case(first_type=first_type, second_type=second_type)
    for band in (-1, 0, 1, 2, 127, 128, 255, 256, 0x10002, 0xFFFFFFFF):
        yield Case(band=band)
    for band in (0, 1, 2, 255):
        yield Case(first_band=band)
        yield Case(second_band=band)
    for coords in (((-32768, -32768), (32767, 32767)),
                   ((32767, -32768), (-32768, 32767)), ((0, 0), (0, 0)),
                   ((0, -100), (0, 100)), ((100, 100), (-100, -100))):
        yield Case(first=coords[0], second=coords[1], point=(-10., 0., 0.), delta=(20., 0.))
    for extra in (1, 2, 3):
        yield Case(count=4, extra=extra)
    for mutation in range(1, 7):
        yield Case(mutation=mutation)
    for axis in range(3):
        for value in (math.nan, math.inf, -math.inf):
            p = list(Case().point)
            p[axis] = value
            yield Case(point=tuple(p))
    for axis in range(2):
        for value in (math.nan, math.inf, -math.inf):
            d = list(Case().delta)
            d[axis] = value
            yield Case(delta=tuple(d))
    yield Case(point=(50., 0., -10.), delta=(1.e10, 20.))


def initial(case):
    rows = [(NODES, BANKS[0], 4), (COUNT, case.count, 2)]
    for bank, base in enumerate(BANKS):
        for i in range(256):
            rows.extend(((base + i * 16 + 14, 0, 1), (base + i * 16 + 6, 0, 1)))
        for i, coords, kind, band in ((0, case.first, case.first_type, case.first_band),
                (1, case.second, case.second_type, case.second_band),
                (254, case.second, case.second_type, case.second_band)):
            at = base + i * 16
            rows.extend(((at, coords[0], 2), (at + 2, -32768, 2),
                (at + 4, coords[1] + bank * 5, 2), (at + 6, band, 1), (at + 14, kind, 1)))
            rows.extend((at + 9 + j, 255, 1) for j in range(5))
        rows.extend((base + 9 + j, value, 1) for j, value in enumerate(case.neighbors))
        if case.extra:
            z = 5 if case.extra != 3 else -5
            x = 200 if case.extra == 1 else 0
            for i, px in ((2, x), (3, x + 100)):
                at = base + i * 16
                rows.extend(((at, px, 2), (at + 4, z, 2), (at + 6, 2, 1), (at + 14, 1, 1)))
                rows.extend((at + 9 + j, 3 if i == 2 and j == 0 else 255, 1) for j in range(5))
    return rows


def changes(case):
    return {
        0: [], 1: [(COUNT, 0, 2)], 2: [(NODES, BANKS[1], 4)],
        3: [(BANKS[0] + 14, 2, 1)], 4: [(BANKS[0] + 6, 3, 1)],
        5: [(BANKS[0] + 16, 25, 2)], 6: [(COUNT, 1, 2)],
    }[case.mutation]


def fixture(case):
    m = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x400, 0x100)}
    for base, size in SEGMENTS:
        m.update({base + i: 0xA5 for i in range(size)})
    for a, value, size in initial(case):
        put(m, a, value, size)
    return m


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x400 <= a < STACK + 0x100}


def equivalent(a, b):
    return a == b or (math.isnan(floating(a)) and math.isnan(floating(b)))


def reference(memory, case):
    m = memory.copy()
    for a, value, size in changes(case):
        put(m, a, value, size)
    x, _, z = map(f32, case.point)
    dx, dz = map(f32, case.delta)
    count, nodes = signed(read(m, COUNT, 2), 16), read(m, NODES, 4)
    minimum, last = f32(100.), None
    crossings = []
    add = lambda a, b: f32(a + b)
    mul = lambda a, b: f32(a * b)
    for i in range(max(0, count)):
        first = nodes + i * 16
        if read(m, first + 14, 1) != 1 or read(m, first + 6, 1) != (case.band & 0xFFFFFFFF):
            continue
        for j in range(5):
            other = read(m, first + 9 + j, 1)
            if other == 255 or i >= other:
                continue
            second = nodes + other * 16
            if read(m, second + 14, 1) != 1:
                continue
            ax, az = (f32(signed(read(m, first + offset, 2), 16)) for offset in (0, 4))
            bx, bz = (f32(signed(read(m, second + offset, 2), 16)) for offset in (0, 4))
            nx, nz = f32(bz - az), -f32(bx - ax)
            constant = -add(mul(ax, nx), mul(nz, az))
            start = add(add(mul(x, nx), mul(z, nz)), constant)
            end = add(add(mul(add(x, dx), nx), mul(add(z, dz), nz)), constant)
            if not ((end < 0. <= start) or (start < 0. <= end)):
                continue
            a, b = -start if start < 0. else start, -end if end < 0. else end
            last = f32(a / add(a, b))
            nx, nz = -nz, nx
            constant = -add(mul(ax, nx), mul(nz, az))
            cx, cz = add(mul(last, dx), x), add(mul(last, dz), z)
            a = add(add(mul(cx, nx), mul(cz, nz)), constant)
            b = add(add(mul(bx, nx), mul(nz, bz)), constant)
            accepted = (0. < b and 0. < a <= b) or (b < 0. and a < 0. and b <= a)
            crossings.append((i, j, last, accepted))
            if accepted and last < minimum:
                minimum = last
    if minimum <= 1.:
        assert last is not None
        result = mul(f32(math.sqrt(add(mul(dx, dx), mul(dz, dz)))), last)
    else:
        result = -1.
    return bits(result), m, [(HEIGHT, bits(case.point[1]))], crossings, minimum


class CrossingModel(previous.SelectorModel):
    def __init__(self, words, memory, case, phase=0, connected=None):
        core.CopyModel.__init__(self, words, memory,
            (0, 0, bits(case.point[2]), bits(case.delta[0])), phase=phase,
            connected=connected, entry=source.ENTRY)
        self.case, self.condition, self.requested = case, False, None
        self.f[12], self.f[14] = bits(case.point[0]), bits(case.point[1])
        self.f[20:] = [0x3F800000 + i for i in range(20, 32)]
        self.saved_f = self.f[20:].copy()
        put(self.memory, STACK + phase + 16, bits(case.delta[1]), 4)

    def record_call(self, target):
        assert target == HEIGHT, hex(target)
        self.calls.append((target, self.f[12]))
        self.events.append(('CALL', target, self.f[12]))

    def hook(self, target):
        assert target == HEIGHT
        self.in_hook = True
        try:
            for a, value, size in changes(self.case):
                self.put(a, value, size)
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xA5000000 + i, 4)
            for r in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[r] = 0xA5000000 + r
            self.r[2] = self.case.band & 0xFFFFFFFF
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            self.condition = not self.condition
        finally:
            self.in_hook = False


def native_harness(body, corpus):
    rows = []
    for case in corpus:
        expected = reference(fixture(case), case)[0]
        values = (*map(bits, case.point + case.delta), *case.first, *case.second,
            *case.neighbors, case.count, case.band & 0xFFFFFFFF, case.first_type,
            case.second_type, case.first_band, case.second_band, case.extra,
            case.mutation, expected)
        fields = ['0x%Xu' % (v & 0xFFFFFFFF) for v in values]
        rows.append('{{%s},{%s},{%s},{%s},%s}' % (
            ','.join(fields[:5]), ','.join(fields[5:7]), ','.join(fields[7:9]),
            ','.join(fields[9:14]), ','.join(fields[14:])))
    return r'''
typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
static union{double align;u8 bytes[4096];} banks[2],wanted[2];
s16 D_80087290;u8*D_800D2350;
static s16 wantedCount;static u8*wantedNodes;
struct Case{u32 args[5];s32 first[2],second[2];u32 neighbors[5];s32 count;u32 band;
 u32 firstType,secondType,firstBand,secondBand,extra,mutation,expected;};
static const struct Case cases[]={ROWS};static const struct Case*c;static u32 calls,error;
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void node(u8*p,s32 x,s32 z,u32 type,u32 band){u32 j;*(s16*)p=(s16)x;
 *(s16*)(p+2)=-32768;*(s16*)(p+4)=(s16)z;p[6]=band;p[14]=type;for(j=0;j<5;j++)p[9+j]=255;}
static void setup(void){u32 i,b,j;u8*p;s32 z,x;
 for(b=0;b<2;b++){for(i=0;i<4096;i++)banks[b].bytes[i]=0xA5;
  for(i=0;i<256;i++){banks[b].bytes[i*16+14]=0;banks[b].bytes[i*16+6]=0;}
  p=banks[b].bytes;node(p,c->first[0],c->first[1]+b*5,c->firstType,c->firstBand);
  node(p+16,c->second[0],c->second[1]+b*5,c->secondType,c->secondBand);
  node(p+254*16,c->second[0],c->second[1]+b*5,c->secondType,c->secondBand);
  for(j=0;j<5;j++)p[9+j]=c->neighbors[j];
  if(c->extra){z=c->extra==3?-5:5;x=c->extra==1?200:0;
   node(p+32,x,z,1,2);node(p+48,x+100,z,1,2);p[32+9]=3;}}
 D_800D2350=banks[0].bytes;D_80087290=(s16)c->count;calls=error=0;}
s32 func_15085DA8(f32 y){u32 b,i;calls++;if(word(y)!=c->args[1])error=21;
 if(c->mutation==1)D_80087290=0;
 if(c->mutation==2)D_800D2350=banks[1].bytes;
 if(c->mutation==3)banks[0].bytes[14]=2;
 if(c->mutation==4)banks[0].bytes[6]=3;
 if(c->mutation==5)*(s16*)(banks[0].bytes+16)=25;
 if(c->mutation==6)D_80087290=1;
 for(b=0;b<2;b++)for(i=0;i<4096;i++)wanted[b].bytes[i]=banks[b].bytes[i];
 wantedCount=D_80087290;wantedNodes=D_800D2350;return (s32)c->band;}
f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
BODY
void _start(void){u32 n,b,i,result;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;setup();result=word(func_15086D94(real(c->args[0]),real(c->args[1]),real(c->args[2]),real(c->args[3]),real(c->args[4])));
 if(!same(result,c->expected))error=22;if(calls!=1)error=23;
 if(D_80087290!=wantedCount||D_800D2350!=wantedNodes)error=24;
 for(b=0;b<2;b++)for(i=0;i<4096;i++)if(banks[b].bytes[i]!=wanted[b].bytes[i])error=25;
 if(error)break;}
 __asm__ volatile("int $0x80"::"a"(1),"b"(error));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows)).replace('BODY', body)
