"""Ordered live-context stores and explicit asset/weight providers, not full gameplay."""
from dataclasses import dataclass

from tools.experiments import game_mode_context_init_candidates as source
from tools.tests import game_cyclic_weight_profiles_oracle as weight

core, STACK = weight.core, weight.STACK
put, read, bits = weight.put, weight.read, weight.bits
KEY, CONTEXT, MODE = 0x800D2E48, 0x800D23B0, 0x800E0BD0
LIMITS, VALUES, RATES = 0x800872B0, 0x800872F8, 0x800872F0
LOOKUP, WEIGHTS, FIND, RANDOM, COUNT = 0x1509B570, 0x1508BC20, 0x1509B704, 0x150ADA68, 0x8008FD8C
RODATA, RODATA_ROM, RODATA_SIZE = 0x80087000, 0x22BAC0, 0x600
TABLE_BYTES = b''
JUMP, JUMP_BYTES = source.TABLE, b''


@dataclass(frozen=True)
class Case:
    key: int = 0xB7
    mode: int = 2
    found: bool = True
    lookup_change: int = 0
    weight_change: int = 0
    mode_alias: bool = False


def banks(case):
    return (MODE - 0x1700 if case.mode_alias else 0x20000, 0x22000)


def signed(value, width=32):
    return ((value & ((1 << width) - 1)) ^ (1 << (width - 1))) - (1 << (width - 1))


def cases():
    for key in (-2147483648, -1, 0, 0xB6, *range(0xB7, 0xC0), 0x100B7, 0x7FFFFFFF):
        for found in (False, True):
            yield Case(key=key, found=found)
    for mode in range(-128, 128):
        yield Case(mode=mode)
    for key in (0xB7, 0xB9, 0xBC, 0xBE):
        for change in range(1, 4):
            yield Case(key=key, lookup_change=change)
    for key in (0xB7, 0xBE):
        for change in range(1, 5):
            yield Case(key=key, weight_change=change)
    for mode in (0, 1, 2, 4, -1):
        yield Case(mode=mode, mode_alias=True)
    yield Case(found=False, lookup_change=2)


def initial(case):
    return [(KEY, case.key, 4), (CONTEXT, banks(case)[1], 4), (MODE, case.mode, 1)]


def fixture(case):
    if len(TABLE_BYTES) != RODATA_SIZE:
        raise ValueError('Missing pinned mode-context ROM table backing')
    m = {STACK + i: (i * 19 + 0xA5) & 255 for i in range(-0x800, 0x100)}
    for base in banks(case):
        m.update({base + i: 0xA5 for i in range(0x1900)})
    for base, size in ((KEY, 4), (CONTEXT, 4), (MODE, 1), (COUNT, 1)):
        m.update({base + i: 0xA5 for i in range(size)})
    m.update({RODATA + i: value for i, value in enumerate(TABLE_BYTES)})
    m.update({JUMP + i: value for i, value in enumerate(JUMP_BYTES)})
    for a, value, size in initial(case):
        put(m, a, value, size)
    return m


def public(memory):
    return {a: value for a, value in memory.items() if not STACK - 0x800 <= a < STACK + 0x100}


def effects(case, target, memory):
    if target == LOOKUP:
        return {0: [], 1: [(KEY, 0xBC, 4)], 2: [(CONTEXT, banks(case)[0], 4)],
            3: [(MODE, -1, 1)]}[case.lookup_change]
    result = [(read(memory, CONTEXT, 4) + 0x15B4, 0xB6, 1)]
    result += {0: [], 1: [(CONTEXT, banks(case)[1], 4)], 2: [(MODE, 4, 1)],
        3: [(VALUES + signed(read(memory, MODE, 1), 8) * 4, 0x3F600001, 4)],
        4: [(KEY, -1, 4)]}[case.weight_change]
    return result


def reference(memory, case, real_weights=None):
    m, stores, calls = memory.copy(), [], []
    def store(a, value, size):
        put(m, a, value, size)
        stores.append((a, value & ((1 << (size * 8)) - 1), size))
    def provider(target):
        for a, value, size in effects(case, target, m):
            store(a, value, size)
    key = read(m, KEY, 4)
    calls.append((LOOKUP, key))
    provider(LOOKUP)
    if not case.found:
        return m, calls, stores
    if key not in (0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBD, 0xBE):
        store(CONTEXT, 0, 4)
        return m, calls, stores
    store(CONTEXT, banks(case)[0], 4)
    calls.append((WEIGHTS,))
    if real_weights is None:
        provider(WEIGHTS)
    else:
        if real_weights not in (0, 2):
            raise ValueError('Unqualified connected weight count')
        for row in range(real_weights):
            for i, value in enumerate((85, 170)):
                store(read(m, CONTEXT, 4) + 0x15B4 + row * 16 + i, value, 1)
    for offset in (0x1700, 0x1701, 0x1703, 0x1702, 0x1704):
        store(read(m, CONTEXT, 4) + offset, 0, 1)
    store(read(m, CONTEXT, 4) + 0x16BC, key, 2)
    mode = signed(read(m, MODE, 1), 8)
    store(read(m, CONTEXT, 4) + 0x16B8, read(m, LIMITS + mode * 4, 4), 4)
    store(read(m, CONTEXT, 4) + 0x1745, 0, 1)
    for offset in range(0, 64, 4):
        store(read(m, CONTEXT, 4) + 0x16C0 + offset, 0, 4)
        mode = signed(read(m, MODE, 1), 8)
        store(read(m, CONTEXT, 4) + 0x1868 + offset, read(m, VALUES + mode * 4, 4), 4)
        for base in (0x17A8, 0x17E8, 0x1828):
            store(read(m, CONTEXT, 4) + base + offset, 0, 4)
    mode = signed(read(m, MODE, 1), 8)
    store(read(m, CONTEXT, 4) + 0xC, signed(read(m, RATES + mode, 1), 8), 4)
    return m, calls, stores


class InitModel(weight.WeightModel):
    def __init__(self, words, memory, case, phase=0, connected=None, entry=source.ENTRY):
        self.requests = []
        core.CopyModel.__init__(self, words, memory, (), phase=phase, connected=connected, entry=entry)
        self.case, self.condition, self.requested = case, False, None
        self.f[20:] = [0x3F800000 + i for i in range(20, 32)]
        self.saved_f = self.f[20:].copy()
        self.nested_calls, self.rng_calls = [], 0

    def record_call(self, target):
        if target == source.ENTRY:
            self.caller_args.append(())
            return
        if target == LOOKUP:
            self.calls.append((target, self.r[4]))
        elif target == WEIGHTS:
            self.calls.append((target,))
        elif target == FIND:
            self.nested_calls.append((target, self.r[4]))
        elif target == RANDOM:
            self.rng_calls += 1
        else:
            raise AssertionError('Unexpected mode-context helper: %X' % target)
        self.events.append(('CALL', target, self.r[4] if target in (LOOKUP, FIND) else None))

    def hook(self, target):
        self.in_hook = True
        try:
            if target in (LOOKUP, WEIGHTS):
                for a, value, size in effects(self.case, target, self.memory):
                    self.put(a, value, size)
                value = banks(self.case)[0] if target == LOOKUP and self.case.found else 0
            elif target == FIND:
                value = banks(self.case)[0] - 32 if self.case.found else 0
            elif target == RANDOM:
                value = 0x12345678
            else:
                raise AssertionError('Unexpected mode-context provider')
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xBA000000 + i, 4)
            for r in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[r] = 0xA5000000 + r
            self.r[2] = value
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            if target == RANDOM:
                self.f[0] = bits(.25)
            self.condition = not self.condition
        finally:
            self.in_hook = False


def native_harness(body, corpus):
    rows, patches = [], []
    def append(entries):
        at = len(patches)
        patches.extend('{0x%Xu,0x%Xu,%d}' % (a, value & 0xFFFFFFFF, size) for a, value, size in entries)
        return at, len(patches) - at
    for case in corpus:
        memory = fixture(case)
        _, calls, writes = reference(memory, case)
        first = append(initial(case))
        expected = append(writes)
        lookup = append(effects(case, LOOKUP, memory))
        for a, value, size in effects(case, LOOKUP, memory):
            put(memory, a, value, size)
        put(memory, CONTEXT, banks(case)[0], 4)
        weights = append(effects(case, WEIGHTS, memory))
        values = (*banks(case), case.key & 0xFFFFFFFF, int(case.found), int(case.mode_alias),
            len(calls), *first, *expected, *lookup, *weights)
        rows.append('{%s}' % ','.join('0x%Xu' % value for value in values))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void*)0)
struct Memory{u8 banks[2][0x1900];s32 context,key;s8 mode;u8 tables[0x600];};
static struct Memory actual __attribute__((aligned(16))),wanted __attribute__((aligned(16)));
static f32 limits[512],values[512];static s8 rates[512];
static const u8 tables[]={TABLES};
struct Patch{u32 a,v,n;};static const struct Patch patches[]={PATCHES};
struct Case{u32 bank0,bank1,key,found,alias,calls,first,count,want,written,lookup,lookupCount,weights,weightCount;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 calls,error;
static __attribute__((noreturn)) void fail(u32 v){__asm__ volatile("int $0x80"::"a"(1),"b"(v));__builtin_unreachable();}
static u8*address(u32 a,struct Memory*m){u32 base,i;for(i=0;i<2;i++){base=i?c->bank1:c->bank0;
 if(a>=base&&a-base<0x1900)return m->banks[i]+a-base;}
 if(a>=0x80087000u&&a-0x80087000u<0x600)return m->tables+a-0x80087000u;
 if(a==0x800D23B0u)return (u8*)&m->context;if(a==0x800D2E48u)return (u8*)&m->key;
 if(a==0x800E0BD0u)return (u8*)&m->mode;fail(29);}
static void apply(struct Memory*m,u32 first,u32 count){u32 i,j,v;u8*p;const struct Patch*q;
 for(i=0;i<count;i++){q=patches+first+i;v=q->v;p=address(q->a,m);
  if(q->a==0x800D23B0u)v=v?(u32)address(v,&actual):0;
  if(q->a>=0x80087000u&&q->a-0x80087000u<0x600){for(j=0;j<q->n;j++)p[j]=v>>((q->n-1-j)*8);}
  else if(q->n==1)*p=(u8)v;else if(q->n==2)*(u16*)p=(u16)v;else*(u32*)p=v;}}
static u32 be(u32 a){u8*p=address(a,&actual);return (u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static void refresh(void){s32 i;for(i=0;i<512;i++){((u32*)limits)[i]=((u32*)values)[i]=0xA5A5A5A5u;rates[i]=(s8)0xA5;}
 for(i=-128;i<128;i++){((u32*)limits)[128+i]=be(0x800872B0u+i*4);((u32*)values)[128+i]=be(0x800872F8u+i*4);
 rates[128+i]=*(s8*)address(0x800872F0u+i,&actual);}}
#define D_800D2E48 actual.key
#define D_800D23B0 actual.context
#define D_800E0BD0 (*(s8*)address(0x800E0BD0u,&actual))
#define D_800872B0 (limits+128)
#define D_800872F8 (values+128)
#define D_800872F0 (rates+128)
u8*func_1509B570(s32 key){if(calls++!=0||(u32)key!=c->key)error=20;
 apply(&actual,c->lookup,c->lookupCount);refresh();return c->found?actual.banks[0]:NULL;}
void func_1508BC20(void){if(calls++!=1)error=21;apply(&actual,c->weights,c->weightCount);refresh();}
BODY
void _start(void){u32 n,i;s32 result;u8*a=(u8*)&actual,*w=(u8*)&wanted;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases+n;calls=error=0;
  for(i=0;i<sizeof(actual);i++)a[i]=w[i]=0xA5;for(i=0;i<0x600;i++)actual.tables[i]=wanted.tables[i]=tables[i];
  apply(&actual,c->first,c->count);apply(&wanted,c->first,c->count);apply(&wanted,c->want,c->written);refresh();
  result=func_15089BC0();if(result!=0)error=22;if(calls!=c->calls)error=23;
  for(i=0;i<sizeof(actual);i++)if(a[i]!=w[i])error=24;if(error)break;}
 fail(error);}
'''.replace('TABLES', ','.join(str(v) for v in TABLE_BYTES)).replace('PATCHES', ',\n'.join(patches)).replace(
        'CASES', ',\n'.join(rows)).replace('BODY', body)
