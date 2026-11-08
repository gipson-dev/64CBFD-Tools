"""Independent ordered RAM model and bounded original cross-product execution."""
import itertools
import math
import random
import struct
from dataclasses import dataclass
from functools import lru_cache

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_record_vertex_callback_1513e83c_oracle import rd, wr, u32, state
from tools.experiments import game_triangle_facing_1510e670_match as source

ENTRY, CROSS, TABLE = source.ENTRY, 0x150AD8B0, 0x800D3300
OFFSETS, VERTICES = 0x30000, 0x31000


@lru_cache(maxsize=2)
def original_cross(root):
    return struct.unpack_from('>19I', (root/'conker/conker.us.bin').read_bytes(), 0xDAD60)


@dataclass(frozen=True)
class Case:
    index: int = 0
    points: tuple = ((0, 0, 0), (1, 0, 0), (0, 0, 1))
    absent: bool = False
    phase: int = 0
    alias: int = 0
    forced: int | None = None


def fixture(case=Case()):
    memory = {STACK+case.phase+i: (i*17+0xA5)&255 for i in range(-512, 1024)}
    entry = u32(TABLE+u32(case.index)*16)
    frame = STACK+case.phase-88
    vertices = VERTICES if not case.alias else frame+(0x38 if case.alias == 1 else 0x2C)
    addresses = (vertices, vertices+8, vertices+16)
    for p, n in ((entry, 16), (OFFSETS, 32), (vertices, 40)):
        for i in range(n):
            memory.setdefault(u32(p+i), (i*29+0x5A)&255)
    wr(memory, entry+4, 0 if case.absent else OFFSETS, 4)
    # Treat stored words as unsigned byte offsets, not vertex indices.
    base = u32(vertices-0x1000)
    wr(memory, entry+8, base, 4)
    for i, p in enumerate(addresses):
        wr(memory, OFFSETS+i*4, u32(p-base), 4)
        for j, value in enumerate(case.points[i]):
            wr(memory, p+j*2, value, 2)
    return memory


def half(value):
    return ((value&65535)^32768)-32768


def mul(a, b):
    return floating(bits(a*b))


def difference(a, b):
    return floating(bits(a-b))


def cross(a, b):
    return (difference(mul(a[1], b[2]), mul(a[2], b[1])),
            difference(mul(a[2], b[0]), mul(a[0], b[2])),
            difference(mul(a[0], b[1]), mul(a[1], b[0])))


def public(memory, case):
    home = STACK+case.phase
    return {p: b for p, b in memory.items() if not home-512 <= p < home+1024}


def reference(initial, case=Case()):
    memory = dict(initial)
    entry = u32(TABLE+u32(case.index)*16)
    offsets, base = rd(memory, entry+4, 4), rd(memory, entry+8, 4)
    if not offsets:
        return public(memory, case), [], 0
    first, second, third = [u32(base+rd(memory, offsets+i*4, 4)) for i in range(3)]
    frame = STACK+case.phase-88
    for destination, p in ((frame+0x38, second), (frame+0x2C, third)):
        for i in range(3):
            value = half(rd(memory, p+2*i, 2))-half(rd(memory, first+2*i, 2))
            wr(memory, destination+4*i, bits(float(value)), 4)
    a, b = ([floating(rd(memory, frame+offset+i*4, 4)) for i in range(3)] for offset in (0x38, 0x2C))
    calls = [(CROSS, tuple(bits(v) for v in a+b))]
    values = cross(a, b)
    for i in (2, 0, 1):
        wr(memory, frame+0x20+i*4, bits(values[i]), 4)
    if case.forced is not None:
        wr(memory, frame+0x24, case.forced, 4)
    return public(memory, case), calls, int(not floating(rd(memory, frame+0x24, 4)) < 0.0)


class Oracle(FactoryOracle):
    def __init__(self, words, memory, case=Case(), entry=ENTRY, connected=None, arguments=None):
        code = {}
        if case.forced is None:
            code.update(zip(range(CROSS, CROSS+76, 4), original_cross(source.ROOT)))
        code.update(connected or {})
        self.semantic_calls = []
        super().__init__(words, memory, case, entry=entry, arguments=(u32(case.index),) if arguments is None else arguments, connected=code)

    def execute(self, word):
        op, fmt, ft, fs, fd, fn = word>>26, word>>21&31, word>>16&31, word>>11&31, word>>6&31, word&63
        if op == 17 and fmt == 20 and fn == 32:
            self.f[fd] = bits(float(signed(self.f[fs])))
            return
        if op == 17 and fmt == 16:
            a, b = floating(self.f[fs]), floating(self.f[ft])
            if fn == 1:
                self.f[fd] = bits(difference(a, b))
            elif fn == 2:
                self.f[fd] = bits(mul(a, b))
            elif fn == 6:
                self.f[fd] = self.f[fs]
            elif fn == 60:
                self.condition = a < b
            else:
                raise AssertionError(('Foreign triangle FP instruction', hex(word)))
            self.r[0] = 0
            return
        return super().execute(word)

    def record_call(self, target):
        count = 3 if target == CROSS else 1 if target == ENTRY else None
        assert count is not None, hex(target)
        args = tuple(map(u32, self.arguments(count)))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if target == CROSS:
            self.semantic_calls.append((target, tuple(rd(self.memory, p+i*4, 4) for p in args[:2] for i in range(3))))

    def hook(self, target):
        assert target == CROSS and self.case.forced is not None
        args = self.calls[-1][1]
        a, b = ([floating(rd(self.memory, p+i*4, 4)) for i in range(3)] for p in args[:2])
        values = cross(a, b)
        for i in (2, 0, 1):
            self.put(args[2]+i*4, bits(values[i]), 4)
        self.put(args[2]+4, self.case.forced, 4)
        for i in range(4):
            self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]


def cases():
    points = (((0, 0, 0), (1, 2, 0), (0, 0, 1)),
              ((0, 0, 0), (0, 0, 1), (1, 2, 0)),
              ((0, 0, 0), (0, 0, 0), (0, 0, 0)),
              ((-32768, 32767, -32768), (32767, -32768, 32767), (32767, 1, -32768)))
    for index, p, absent, phase in itertools.product((0, 1, 15, 0xFFFF, -1, -32768, 0x7FFFFFFF, -0x80000000), points, (False, True), (0, 8)):
        yield Case(index=index, points=p, absent=absent, phase=phase)
    generator = random.Random(0x1510E670)
    for i in range(128):
        yield Case(index=i%16, points=tuple(tuple(generator.randrange(-32768, 32768) for _ in range(3)) for _ in range(3)))
    for alias, p in itertools.product((1, 2), points):
        yield Case(alias=alias, points=p)
    for forced in (0, 0x80000000, 0x3F800000, 0xBF800000, 0x7F800000, 0xFF800000, 0x7FC12345):
        yield Case(forced=forced)


def native_harness(body=None):
    body = source.SELECTED if body is None else body
    rows = []
    for case in cases():
        if case.alias or not 0 <= case.index < 16:
            continue
        _, _, value = reference(fixture(case), case)
        flat = ','.join(str(v) for point in case.points for v in point)
        rows.append('{%d,%d,%d,0x%Xu,%d,{%s}}' % (case.index, case.absent, case.forced is not None, case.forced or 0, value, flat))
    return '''#include <ultra64.h>
_Static_assert(sizeof(void *)==4 && sizeof(s32)==4 && sizeof(f32)==4,"O32 widths");
u32 tableStorage[64] __asm__("D_800D3300");
static s16 vertices[3][4];
static u32 offsets[3];
static u32 forced; static s32 overrideNormal, calls;
static u32 observed[6];
static u32 fb(f32 v) { union { f32 f; u32 u; } a; a.f=v; return a.u; }
void func_150AD8B0(f32 *a, f32 *b, f32 *out) {
    f32 x, y, z; int i; calls++;
    for(i=0;i<3;i++){observed[i]=fb(a[i]);observed[3+i]=fb(b[i]);}
    x=a[1]*b[2]-a[2]*b[1]; y=a[2]*b[0]-a[0]*b[2]; z=a[0]*b[1]-a[1]*b[0];
    out[2]=z;out[0]=x;out[1]=y;
    if(overrideNormal){union{u32 u;f32 f;}v;v.u=forced;out[1]=v.f;}
}
''' + body + '''
typedef s32 (*Predicate)(s32);
static Predicate predicate=func_1510E670;
struct Row { s32 index, absent, overrideNormal; u32 forced; s32 expected; s16 points[9]; };
static const struct Row rows[]={''' + ',\n'.join(rows) + '''};
int run(void) {
    u32 mxcsr=0x1F80; unsigned i,j,k; __asm__ volatile("ldmxcsr %0"::"m"(mxcsr));
    for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        const struct Row *r=&rows[i];s32 answer;u32 before[64];
        for(j=0;j<64;j++)tableStorage[j]=0xA5000000u+j;
        for(j=0;j<3;j++){for(k=0;k<3;k++)vertices[j][k]=r->points[j*3+k];vertices[j][3]=1234;offsets[j]=(u32)&vertices[j][0]-(u32)&vertices[0][0];}
        tableStorage[r->index*4+1]=r->absent?0:(u32)offsets;
        tableStorage[r->index*4+2]=(u32)&vertices[0][0];
        for(j=0;j<64;j++)before[j]=tableStorage[j];
        calls=0;overrideNormal=r->overrideNormal;forced=r->forced;
        answer=predicate(r->index);
        if(answer!=r->expected || calls!=!r->absent)return 1;
        for(j=0;j<64;j++)if(tableStorage[j]!=before[j])return 1;
        for(j=0;j<3;j++)for(k=0;k<3;k++)if(vertices[j][k]!=r->points[j*3+k])return 1;
        if(!r->absent)for(j=0;j<3;j++){
            if(observed[j]!=fb((f32)((s32)r->points[3+j]-r->points[j])))return 1;
            if(observed[3+j]!=fb((f32)((s32)r->points[6+j]-r->points[j])))return 1;
        }
    }
    return 0;
}
void _start(void) { int answer=run();__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
