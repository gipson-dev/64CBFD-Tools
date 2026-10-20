"""Independent route/frontier reference and mutable bounded helper providers."""

from dataclasses import dataclass, replace
import math
import random

from tools.experiments import game_route_node_search_candidates as source
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_record_neighbor_visit_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating, signed


NODES, COUNT, SELECTED, DISTANCE = 0x800D2350, 0x80087290, 0x80087298, 0x800D2354
LOOKUP, LENGTH = 0x15086C70, 0x15086BD0
BANK, ALT_BANK, GOALS, AVOID = 0x20000, 0x22000, 0x24000, 0x24200
REGIONS = ((BANK, 3200), (ALT_BANK, 3200), (GOALS, 128), (AVOID, 128),
           (NODES, 8), (COUNT, 16))


def f32(value):
    return floating(bits(value))


def byte(value):
    return ((value & 255) ^ 128) - 128


def half(value):
    return ((value & 65535) ^ 32768) - 32768


def private(address):
    return STACK - 0x2000 <= address < STACK + 0x100


@dataclass(frozen=True)
class Case:
    start: int = 0
    goals: tuple = (5,)
    avoid: tuple = ()
    count: object = None
    avoid_count: object = None
    node_count: object = None
    coords: tuple = ((0, 0, 0), (100, 0, 0), (0, 0, 100),
                     (200, 0, 0), (100, 0, 100), (300, 0, 0))
    edges: tuple = ((1, 2), (3, 4), (4,), (5,), (5,), ())
    special: tuple = ()
    length: object = None
    actions: tuple = ()
    alias: int = 0


def arguments(case):
    goal_address = (GOALS, SELECTED, DISTANCE)[case.alias]
    return (case.start & 0xFFFFFFFF,
            (len(case.goals) if case.count is None else case.count) & 0xFFFFFFFF,
            (len(case.avoid) if case.avoid_count is None else case.avoid_count) & 0xFFFFFFFF,
            goal_address, AVOID)


def initial(case):
    rows = [(NODES, BANK, 4), (DISTANCE, 0xA5A5A5A5, 4), (SELECTED, 0xA5, 1),
            (COUNT, len(case.coords) if case.node_count is None else case.node_count, 2)]
    for base in (BANK, ALT_BANK):
        for index, coords in enumerate(case.coords):
            rows.extend((base + index * 16 + axis * 2, value, 2) for axis, value in enumerate(coords))
            neighbors = case.edges[index] if index < len(case.edges) else ()
            assert len(neighbors) <= 5
            rows.extend((base + index * 16 + 9 + i, value, 1)
                        for i, value in enumerate((*neighbors, *((255,) * (5 - len(neighbors))))))
    for base, values in ((GOALS, case.goals), (AVOID, case.avoid)):
        rows.extend((base + i, values[i] if i < len(values) else 255, 1) for i in range(128))
    if case.alias:
        rows.append((arguments(case)[3], case.goals[0], 1))
    return rows


def fixture(case):
    memory = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x2000, 0x100)}
    for base, size in REGIONS:
        memory.update({base + i: 0xA5 for i in range(size)})
    for a, v, n in initial(case):
        put(memory, a, v, n)
    return memory


def public(memory):
    return {a: v for a, v in memory.items() if not private(a)}


def provider(case, target, args, occurrence):
    writes = [(a, v, n) for t, k, a, v, n in case.actions if (t, k) == (target, occurrence)]
    result = (0x81000000 + args[0] if args[0] in case.special else 0) if target == LOOKUP else bits(
        f32(abs(args[0] - args[1]) * 1.75 + 0.25 if case.length is None else case.length))
    return result, writes


def reference(memory, case):
    m = memory.copy()
    calls, stores, transcript, occurrences = [], [], [], {}
    def store(a, v, n=4):
        put(m, a, v, n)
        stores.append((a, n, v & ((1 << (8 * n)) - 1)))
    def call(target, *args):
        k = occurrences.get(target, 0)
        occurrences[target] = k + 1
        calls.append((target, *args))
        result, writes = provider(case, target, args, k)
        for a, v, n in writes:
            store(a, v, n)
        transcript.append((target, args, result, writes))
        return result
    def finish(value):
        return value & 0xFFFFFFFF, m, calls, stores, transcript

    start, raw_count, raw_avoid, goals, avoid = arguments(case)
    start, goal_count, avoid_count = signed(start), byte(raw_count), byte(raw_avoid)
    store(SELECTED, 255, 1)
    store(DISTANCE, 0)
    if goal_count <= 0 or start < 0 or start >= half(read(m, COUNT, 2)):
        return finish(255)
    targets = [read(m, goals + i, 1) for i in range(goal_count)]
    if start in targets:
        store(SELECTED, start, 1)
        return finish(start)
    nodes = read(m, NODES, 4)
    costs = {i: 1000000 for i in range(half(read(m, COUNT, 2)))}
    parents, queue = {}, []

    def neighbors(index):
        return [read(m, nodes + index * 16 + 9 + i, 1) for i in range(5)]
    def edge_length(left, right):
        values = []
        for axis in range(3):
            a = half(read(m, nodes + left * 16 + axis * 2, 2))
            b = half(read(m, nodes + right * 16 + axis * 2, 2))
            values.append(f32(a - b))
        x, y, z = values
        return math.trunc(f32(math.sqrt(f32(f32(f32(x * x) + f32(y * y)) + f32(z * z)))))
    def penalty(index):
        return 5000 if index in [read(m, avoid + i, 1) for i in range(max(avoid_count, 0))] else 0

    for other in neighbors(start):
        if other != 255:
            queue.append(other)
            parents[other] = start
            costs[other] = half(edge_length(start, other)) + penalty(other)
    path = []
    for _ in range(1000):
        viable = [(costs[n], i) for i, n in enumerate(queue) if n != 255 and costs[n] < 1000000]
        if not viable:
            break
        _, index = min(viable)
        current = queue[index]
        if index == len(queue) - 1:
            queue.pop()
        else:
            queue[index] = 255
        if current in targets:
            store(SELECTED, current, 1)
            at = current
            while at != start:
                path.append(at)
                at = parents[at]
                if len(path) >= 64:
                    raise ValueError('Outside bounded retail path workspace')
            path.append(start)
            break
        current_cost = costs[current]
        for other in neighbors(current):
            if other in (255, start):
                continue
            value = edge_length(current, other) + current_cost + penalty(other)
            if value >= costs[other]:
                continue
            costs[other], parents[other] = value, current
            if other not in queue:
                if 255 in queue:
                    queue[queue.index(255)] = other
                else:
                    queue.append(other)
    else:
        raise ValueError('Outside bounded terminating route fixtures')
    if len(path) < 2:
        return finish(255)
    at = len(path) - 2
    answer = path[at]
    special = [bool(call(LOOKUP, n)) for n in path]
    chosen = special[at] and (not special[at + 1] or at > 0 and not special[at - 1])
    distance = f32(0.0)
    while at > 0:
        before = at - 1
        if special[before]:
            while before >= 0 and special[before]:
                before -= 1
            before += 1
        distance = f32(distance + floating(call(LENGTH, path[at], path[before])))
        if not chosen:
            chosen = True
            if special[at]:
                answer = path[before]
        at = before
    store(DISTANCE, math.trunc(distance))
    return finish(answer)


class SearchOracle(TriangleOracle):
    def __init__(self, words, memory, case, phase=0, entry=source.ENTRY):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=arguments(case))
        self.case, self.occurrences = case, {}
    def record_call(self, target):
        assert target in (LOOKUP, LENGTH), hex(target)
        self.calls.append((target, *self.arguments(1 if target == LOOKUP else 2)))
    def hook(self, target):
        args = self.arguments(1 if target == LOOKUP else 2)
        k = self.occurrences.get(target, 0)
        self.occurrences[target] = k + 1
        result, writes = provider(self.case, target, args, k)
        for a, v, n in writes:
            self.put(a, v, n)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.condition = bool(len(self.calls) & 1)
        if target == LENGTH:
            self.f[0] = result
        else:
            self.r[2] = result
    def execute(self, word):
        op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
        if op == 32:
            self.r[rt] = byte(self.get((self.r[rs] + half(word)) & 0xFFFFFFFF, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        elif op == 17 and rs == 16 and word & 63 == 4:
            value = floating(self.f[word >> 11 & 31])
            self.f[word >> 6 & 31] = bits(math.sqrt(value) if value >= 0 else math.nan)
        elif op == 0 and word & 63 == 38:
            self.r[word >> 11 & 31] = self.r[rs] ^ self.r[rt]
            self.r[0] = 0
        else:
            super().execute(word)


def cases():
    base = Case()
    yield base
    for value in (0, -1, 127, 128, 255, 0x12340080, 0x80000001):
        yield replace(base, count=value)
        yield replace(base, avoid_count=value, avoid=(1,))
    for value in (-1, 6, 127, 0x7FFFFFFF, 0x80000000):
        yield replace(base, start=value)
    for value in (-1, 0, 1, 6):
        yield replace(base, node_count=value, count=0 if value == 1 else None)
    for n in range(1, 8):
        yield replace(base, goals=(5,) * n)
        yield replace(base, avoid=(1,) * n)
    for values in ((0,), (1,), (2,), (3,), (4,), (1, 3), (3, 1), (5, 3), (199,)):
        yield replace(base, goals=values)
    for mask in range(64):
        yield replace(base, special=tuple(i for i in range(6) if mask >> i & 1))
    for length in (0.0, -0.0, 0.999, 1.5, -5.75, 12345.75):
        yield replace(base, length=length)
    for alias in (1, 2):
        yield replace(base, goals=(0,), alias=alias)
    yield replace(base, edges=((), (), (), (), (), ()))
    yield replace(base, edges=((0, 1, 1, 2, 255), (3, 0), (4,), (5,), (5,), ()))
    yield Case(coords=((0, 0, 0), (100, 0, 0), (-100, 0, 0)), edges=((1, 2), (), ()), goals=(1, 2))
    yield Case(coords=((0, 0, 0), (32000, 32000, 0), (100, 0, 0)), edges=((1, 2), (), ()), goals=(1, 2))
    yield Case(coords=((-32768, -32768, -32768), (32767, 32767, 32767)), edges=((1,), ()), goals=(1,))
    yield Case(start=199, goals=(199,), coords=tuple((i, 0, 0) for i in range(200)), edges=())
    yield Case(goals=(199,), coords=tuple((i, 0, 0) for i in range(200)), edges=((199,),))
    yield replace(base, actions=((LOOKUP, 0, NODES, ALT_BANK, 4),))
    yield replace(base, actions=((LOOKUP, 1, SELECTED, 77, 1), (LENGTH, 0, DISTANCE, 1234, 4)))
    # Long paths exercise byte workspaces and consecutive-special compression.
    for n in (4, 8, 16, 32, 63):
        yield Case(coords=tuple((i * 10, 0, 0) for i in range(n)),
                   edges=tuple((i + 1,) if i + 1 < n else () for i in range(n)),
                   goals=(n - 1,), special=tuple(i for i in range(n) if i % 3))
    rng = random.Random(0x15086364)
    for _ in range(80):
        n = rng.randrange(3, 17)
        coords = tuple(tuple(rng.randrange(-1000, 1001) for _ in range(3)) for _ in range(n))
        edges = tuple(tuple(rng.sample(range(n), rng.randrange(min(n, 5) + 1))) for _ in range(n))
        yield Case(coords=coords, edges=edges, goals=tuple(rng.sample(range(n), rng.randrange(1, min(n, 7)))),
                   avoid=tuple(rng.sample(range(n), rng.randrange(min(n, 6)))),
                   special=tuple(i for i in range(n) if rng.randrange(2)))


def native_harness(body, corpus):
    offsets, total = [], 0
    for _, size in REGIONS:
        total = (total + 15) & ~15
        offsets.append(total)
        total += size
    patches, calls, rows = [], [], []
    def literal(a, v, n):
        return '{0x%Xu,0x%Xu,%d,%d}' % (a, v & 0xFFFFFFFF, n, a == NODES and n == 4)
    for case in corpus:
        result, _, _, stores, transcript = reference(fixture(case), case)
        first = len(patches)
        patches.extend(literal(*p) for p in initial(case))
        count = len(patches) - first
        wanted = len(patches)
        patches.extend(literal(a, v, n) for a, n, v in stores)
        written = len(patches) - wanted
        call_first = len(calls)
        for target, args, value, writes in transcript:
            begin = len(patches)
            patches.extend(literal(*p) for p in writes)
            calls.append('{0x%Xu,%d,{%s},0x%Xu,%d,%d}' % (
                target, len(args), ','.join(str(a) + 'u' for a in (*args, *((0,) * (2 - len(args))))),
                value, begin, len(patches) - begin))
        fields = (first, count, wanted, written, call_first, len(transcript), *arguments(case), result)
        rows.append('{' + ','.join('0x%Xu' % v for v in fields) + '}')
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];fail(29);}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 target,n,a[2],result,first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,call_first,call_count,start,goals,avoid,list,excluded,result;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 ordinal;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static void apply(u8*b,u32 first,u32 count){u32 i,v;const struct Patch*q;u8*p;
 for(i=0;i<count;i++){q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(s16*)p=(s16)v;else*(u32*)p=v;}}
static u32 invoke(u32 target,u32 n,const u32*a){u32 i;const struct Call*q;
 if(ordinal>=c->call_count)fail(22);q=calls+c->call_first+ordinal++;
 if(target!=q->target||n!=q->n)fail(22);for(i=0;i<n;i++)if(a[i]!=q->a[i])fail(23);
 apply(actual,q->first,q->count);return q->result;}
#define D_800D2350 (*(u8**)address(0x800D2350u,actual))
#define D_80087290 (*(s16*)address(0x80087290u,actual))
#define D_80087298 (*address(0x80087298u,actual))
#define D_800D2354 (*(s32*)address(0x800D2354u,actual))
s32 func_15086C70(s32 index){u32 a[]={(u32)index};return invoke(0x15086C70u,1,a);}
f32 func_15086BD0(s32 a,s32 b){u32 v[]={(u32)a,(u32)b};return real(invoke(0x15086BD0u,2,v));}
f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
BODY
__attribute__((force_align_arg_pointer)) void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;ordinal=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 if((u32)func_15086364(c->start,(s8)c->goals,(s8)c->avoid,address(c->list,actual),address(c->excluded,actual))!=c->result)fail(21);
 if(ordinal!=c->call_count)fail(25);for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(24);
 }fail(0);}
'''.replace('SIZE', str(total)).replace('REGIONS', ','.join(
        '{0x%Xu,%d,%d}' % (a, n, o) for (a, n), o in zip(REGIONS, offsets))).replace(
        'PATCHES', ','.join(patches)).replace('CALLS', ',\n'.join(calls)).replace(
        'CASES', ',\n'.join(rows)).replace('BODY', body)
