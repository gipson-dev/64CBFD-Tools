"""Independent float32 ranking/cursor reference and bounded opaque pair effects."""
from dataclasses import dataclass
import math

from tools.experiments import game_actor_pair_scheduler_candidates as source
from tools.tests import game_actor_pair_visibility_oracle as previous
from tools.tests import game_actor_sine_selector_oracle as selector

core, STACK = previous.core, previous.STACK
put, read = previous.put, previous.read
bits, floating, f32, signed = previous.bits, previous.floating, previous.f32, previous.signed
CONTEXT, PRIMARY, COUNT = 0x800D23B0, 0x8008FD90, 0x8008FD8C
ACTORS, FORBIDDEN, SENTINEL, PAIR = 0x800CC2D0, 0x800D18A0, 0x8009DA68, 0x1508C1A4
BANKS = (0x20000, 0x22000)
# Only the accessed X/Z/type fields are synthetic backing, not a full game actor pool.
SEGMENTS = ((BANKS[0], 0x1C00), (BANKS[1], 0x1C00), (ACTORS, 256 * 0x32C),
    (CONTEXT, 4), (PRIMARY, 1), (COUNT, 1), (FORBIDDEN, 2), (SENTINEL, 4))


@dataclass(frozen=True)
class Case:
    primary: int = 2
    count: int = 6
    budget: int = 2
    cursor: tuple = (0, 0)
    row: int = 0
    groups: tuple = ()
    targets: tuple = ()
    masks: tuple = ()
    kinds: tuple = ()
    points: tuple = ()
    forbidden: int = 0
    sentinel: float = 10000000.
    mutation: int = 0
    no_pair_writes: bool = False


def cases():
    yield Case()
    for primary in (-128, -1, 0, 1, 2, 3, 7):
        for budget in (0, 1, 4):
            yield Case(primary=primary, budget=budget)
    for count in (-128, -1, 0, 1, 2, 3, 16, 32, 33, 127):
        yield Case(primary=0, count=count, budget=1)
    for cursor in ((0, 254), (0, 255), (254, 255), (255, 255), (1, 4), (4, 5)):
        yield Case(primary=0, cursor=cursor, budget=4)
    for forbidden in (1, 2, 3, 0x8000, 0xFFFF):
        yield Case(primary=0, forbidden=forbidden)
    for groups in ((0,), (0, 1), (-1, 0, 1, 2, 3, 4)):
        yield Case(groups=groups)
    for masks in ((0xFFFFFFFF,), (1, 0x10000, 2, 0x20000, 4, 0x40000), (0x80008000,)):
        yield Case(masks=masks)
    for kinds in ((0,), (0, 255), (255, 128, 127, 1, 0, 254)):
        yield Case(kinds=kinds)
    for target in (-2147483648, -1, 0, 1, 2147483647):
        yield Case(targets=(target,))
    for sentinel in (-math.inf, -1., 0., 4., 16., math.inf, math.nan):
        yield Case(sentinel=sentinel)
    for x in (0., -0., 4., -5., math.inf, -math.inf, math.nan):
        yield Case(points=((x, 4.),), primary=1)
    for mutation in range(1, 7):
        yield Case(mutation=mutation)
    for row in (0, 15, 31, 255):
        yield Case(primary=0, row=row)
    yield Case(primary=1, count=9, targets=(1, 0, 0, 1, 0, 1, 0, 1, 0), budget=4)
    yield Case(primary=2, no_pair_writes=True)


def initial(case):
    rows = [(CONTEXT, BANKS[0], 4), (PRIMARY, case.primary, 1), (COUNT, case.count, 1),
        (FORBIDDEN, case.forbidden, 2), (SENTINEL, bits(case.sentinel), 4)]
    for bank in BANKS:
        for i in range(256):
            rows.extend(((bank + 0xE64 + 4 * i, case.groups[i % len(case.groups)] if case.groups else (i if bank == BANKS[0] else 0), 4),
                (bank + 0x11C + 4 * i, case.targets[i % len(case.targets)] if case.targets else i % 2, 4),
                (bank + 0x16C0 + 4 * i, case.masks[i % len(case.masks)] if case.masks else 0, 4)))
        rows.extend(((bank + 0x1700, case.cursor[0], 1), (bank + 0x1701, case.cursor[1], 1)))
    for i in range(256):
        x, z = case.points[i % len(case.points)] if case.points else (float(i + 3), float(i - 1))
        rows.extend(((ACTORS + i * 0x32C + 0x14, bits(x), 4),
            (ACTORS + i * 0x32C + 0x1C, bits(z), 4),
            (ACTORS + i * 0x32C + 0x128, case.kinds[i % len(case.kinds)] if case.kinds else i & 255, 1)))
    return rows


def fixture(case):
    m = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x600, 0x100)}
    for base, size in SEGMENTS:
        m.update((base + i, 0xA5) for i in range(size))
    for a, v, n in initial(case):
        put(m, a, v, n)
    return m


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x600 <= a < STACK + 0x100}


def address(memory, index, offset=0x16C0):
    return (read(memory, CONTEXT, 4) + (index & 0xFFFFFFFF) * 4 + offset) & 0xFFFFFFFF


def changes(memory, case, args, ordinal):
    rows = []
    if not case.no_pair_writes:
        for a, b in (args, args[::-1]):
            at = address(memory, a)
            value = read(memory, at, 4) | ((0x10001 << (b & 31)) & 0xFFFFFFFF)
            rows.append((at, value, 4))
            # The oracle calls changes with a private copy so self-pairs compose.
            put(memory, at, value, 4)
    if ordinal == 0:
        rows.extend({
            1: [(CONTEXT, BANKS[1], 4)],
            2: [(PRIMARY, 0, 1)],
            3: [(PRIMARY, 3, 1), (COUNT, 9, 1), (BANKS[0] + 0xE68, 2, 4)],
            4: [(SENTINEL, bits(0.), 4), (ACTORS + 0x32C + 0x14, bits(30.), 4)],
            5: [(BANKS[0] + 0x16C0, 0xC0000000, 4), (FORBIDDEN, 3, 2)],
            6: [(COUNT, 2, 1), (ACTORS + 0x128, 255, 1)],
        }.get(case.mutation, []))
    return rows


def snapshot(memory, args):
    return (*args, read(memory, address(memory, args[0]), 4),
        read(memory, address(memory, args[1]), 4))


def reference(memory, case, limit=200):
    m, calls, stores, transcript = memory.copy(), [], [], []
    def store(a, value, size):
        value &= (1 << (size * 8)) - 1
        put(m, a, value, size)
        stores.append((a, size, value))
    def clear(a, b):
        at = address(m, a)
        store(at, read(m, at, 4) & ~((0x10001 << (b & 31)) & 0xFFFFFFFF), 4)
    def pair(a, b):
        if len(calls) >= limit:
            raise ValueError('Outside bounded completed scheduler reference')
        args = (a & 0xFFFFFFFF, b & 0xFFFFFFFF)
        calls.append(snapshot(m, args))
        effects = changes(m.copy(), case, args, len(calls) - 1)
        for at, value, size in effects:
            store(at, value, size)
        transcript.append((args, effects))
    base = read(m, CONTEXT, 4)
    first, second = (read(m, base + off, 1) for off in (0x1700, 0x1701))
    groups = base + 0xE64
    if case.budget:
        primary, primary_count = 0, signed(read(m, PRIMARY, 1), 8)
        sentinel = floating(read(m, SENTINEL, 4))
        while primary < primary_count:
            x = floating(read(m, ACTORS + primary * 0x32C + 0x14, 4))
            count = signed(read(m, COUNT, 1), 8)
            costs, selected = [sentinel] * 3, [-1] * 3
            for candidate in range(primary_count, count):
                if read(m, groups + primary * 4, 4) == read(m, groups + candidate * 4, 4):
                    continue
                if read(m, address(m, primary), 4) & ((0x10001 << (candidate & 31)) & 0xFFFFFFFF):
                    continue
                dx = f32(x - x)
                dz = f32(x - floating(read(m, ACTORS + primary * 0x32C + 0x1C, 4)))
                if primary == signed(read(m, address(m, candidate, 0x11C), 4)):
                    dx, dz = f32(dx * .5), f32(dz * .5)
                cost = f32(f32(dx * dx) + f32(dz * dz))
                if cost < costs[2]:
                    rank = 2
                    while rank > 0 and cost < costs[rank - 1]:
                        rank -= 1
                    costs.insert(rank, cost)
                    selected.insert(rank, candidate)
                    costs, selected = costs[:3], selected[:3]
            for candidate in selected:
                if candidate != -1:
                    clear(primary, candidate)
                    clear(candidate, primary)
                    pair(primary, candidate)
            primary += 1
            primary_count = signed(read(m, PRIMARY, 1), 8)
    budget = case.budget & 0xFFFFFFFF
    while budget:
        kind = read(m, ACTORS + first * 0x32C + 0x128, 1)
        for attempt in range(1, 65):
            count = signed(read(m, COUNT, 1), 8)
            second = (second + 1) & 255
            if second >= count:
                first = (first + 1) & 255
                if first >= count - 1:
                    first = 0
                second = (first + 1) & 255
                kind = read(m, ACTORS + first * 0x32C + 0x128, 1)
            clear(first, second)
            clear(second, first)
            if attempt == 64:
                break
            if read(m, FORBIDDEN, 2) & ((1 << (first & 31)) | (1 << (second & 31))):
                continue
            if kind != read(m, ACTORS + second * 0x32C + 0x128, 1):
                break
        pair(first, second)
        budget = (budget - 1) & 0xFFFFFFFF
    store(read(m, CONTEXT, 4) + 0x1700, first, 1)
    store(read(m, CONTEXT, 4) + 0x1701, second, 1)
    return read(m, address(m, case.row), 4), m, calls, stores, transcript


class SchedulerModel(selector.SelectorModel):
    def __init__(self, words, memory, case, phase=0, connected=None, entry=source.ENTRY, stop_calls=None):
        core.CopyModel.__init__(self, words, memory, (case.row, case.budget), phase=phase,
            connected=connected, entry=entry)
        self.case, self.condition, self.requested = case, False, None
        self.stop_calls = stop_calls
        self.f[20:] = [0x3F800000 + i for i in range(20, 32)]
        self.saved_f = self.f[20:].copy()

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 39:
            rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            self.r[rd] = ~(self.r[rs] | self.r[rt]) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        if target == source.ENTRY:
            self.caller_args.append(tuple(self.r[4:6]))
            return
        if target == previous.LOOKUP:
            if not self.case.no_pair_writes:
                raise AssertionError('Actual null child needs no-pair-writes reference')
            return
        if target != PAIR:
            raise AssertionError('Unexpected scheduler provider: %X' % target)
        self.calls.append(snapshot(self.memory, tuple(self.r[4:6])))
        self.events.append(('CALL', target, tuple(self.r[4:6])))
        if self.stop_calls == len(self.calls):
            raise CallStop()

    def hook(self, target):
        self.in_hook = True
        try:
            if target == previous.LOOKUP:
                effects = []
            else:
                effects = changes(self.memory.copy(), self.case, tuple(self.r[4:6]), len(self.calls) - 1)
            for a, value, size in effects:
                self.put(a, value, size)
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xBA000000 + i, 4)
            for reg in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[reg] = 0xA5000000 + reg
            self.r[2] = 0 if target == previous.LOOKUP else 0xDEADC0DE
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            self.condition = not self.condition
        finally:
            self.in_hook = False


class CallStop(Exception):
    """An explicit call-count gate, not a completed return."""


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
            patches.append('{0x%Xu,0x%Xu,%d,%d}' % (a, value & 0xFFFFFFFF, size, a == CONTEXT and size == 4))
        return first, len(patches) - first
    for case in corpus:
        if case.count > 16:
            raise ValueError('Native corpus must not alias guest cursor bytes through row 16')
        result, _, snapshots, stores, transcript = reference(fixture(case), case)
        first, count = append(initial(case))
        wanted, written = append((a, value, size) for a, size, value in stores)
        call_first = len(calls)
        for snap, (_, effects) in zip(snapshots, transcript):
            effect_first, effect_count = append(effects)
            calls.append('{{%s},%d,%d}' % (','.join('0x%Xu' % v for v in snap), effect_first, effect_count))
        rows.append('{%s}' % ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in
            (first, count, wanted, written, call_first, len(transcript), case.row, case.budget, result)))
    defines = []
    for name, at, ctype, array in (
        ('D_800D23B0', CONTEXT, 's32', False), ('D_8008FD90', PRIMARY, 's8', False),
        ('D_8008FD8C', COUNT, 's8', False), ('D_800D18A0', FORBIDDEN, 'u16', False),
        ('D_8009DA68', SENTINEL, 'f32', False), ('D_800CC2D0', ACTORS, 'u8', True)):
        value = '((%s*)address(0x%Xu,actual))' % (ctype, at)
        defines.append('#define %s %s' % (name, value if array else '(*%s)' % value))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];fail(29);}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 v[4],first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,callFirst,callCount,row,budget,result;};static const struct Case cases[]={CASES};
static const struct Case*c;static u32 number;
static void apply(u8*b,u32 first,u32 count){u32 i,v;u8*p;const struct Patch*q;for(i=0;i<count;i++){
 q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(u16*)p=(u16)v;else*(u32*)p=v;}}
DEFINES
void func_1508C1A4(s32 a,s32 b){const struct Call*q;u8*context;if(number>=c->callCount)fail(22);
 q=calls+c->callFirst+number++;if((u32)a!=q->v[0]||(u32)b!=q->v[1])fail(23);
 context=(u8*)D_800D23B0;if(*(u32*)(context+(u32)a*4+0x16C0)!=q->v[2]||
 *(u32*)(context+(u32)b*4+0x16C0)!=q->v[3])fail(24);apply(actual,q->first,q->count);}
BODY
void _start(void){u32 n,i,result;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;number=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 result=(u32)func_1508C5B8((s32)c->row,(s32)c->budget);if(result!=c->result)fail(21);if(number!=c->callCount)fail(25);
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(26);}
 fail(0);}
'''.replace('SIZE', str(total)).replace('REGIONS', ','.join('{0x%Xu,%d,%d}' % (b, n, o)
        for (b, n), o in zip(SEGMENTS, offsets))).replace('PATCHES', ','.join(patches)).replace(
        'CALLS', ','.join(calls)).replace('CASES', ',\n'.join(rows)).replace('DEFINES', '\n'.join(defines)).replace('BODY', body)
