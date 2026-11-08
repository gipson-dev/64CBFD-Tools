"""Independent effect-choice semantics and original predicate/lookup control flow."""
import itertools
import struct
from dataclasses import dataclass
from functools import lru_cache

from tools.experiments import game_actor_choice_15146970_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_record_vertex_callback_1513e83c_oracle import rd, wr, u32, state
from tools.tests.game_animation_timeline_oracle import signed

ENTRY, PREDICATE, LOOKUP = source.ENTRY, 0x151420F8, 0x150A2AEC
WORLD, ACTORS, CHOICES, TABLE = 0x800BE9F0, 0x800CC2D0, 0x800A56D0, 0x800A56E4
SIX, ENABLED, COUNT, DESCRIPTOR_BASE, BITS = 0x800A5200, 0x800D2340, 0x800D3094, 0x800D3098, 0x800D30F0
DESCRIPTORS, SHIFT, COLLISION = 0x50000, 0x10026800, 0x150A1DA0
IDS = (0x401D, 0x401E, 0x401F, 0x4020, 0x4021)
OFFSETS = (80, 88, 72, 156, 148, 64, 164, 56, 48)


@lru_cache(maxsize=2)
def artifacts(root):
    rom = (root/'conker/conker.us.bin').read_bytes()
    elf = (root/'conker/build/conker.us.elf').read_bytes()
    at = source.elf_slot_offset(elf, SIX, 24)
    return rom, struct.unpack_from('>6I', elf, at)


@dataclass(frozen=True)
class Case:
    kind: int = 0
    world: int = 4
    predicate: int = 1
    lookup: int = -1
    delta: int = 3*0x32C
    phase: int = 0
    connected: int = 0
    masked: int = 0
    match: int = -1
    mutation: int = 0


def actor(case):
    return u32(ACTORS+case.delta)


def actor_index(case):
    value = signed(u32(case.delta))
    return (abs(value)//0x32C)*(-1 if value < 0 else 1)


def fixture(case=Case()):
    memory = {STACK+case.phase+i: (i*17+0xA5)&255 for i in range(-1024, 512)}
    for p, n in ((actor(case), 64), (WORLD, 4), (CHOICES, 20), (TABLE, 36), (SIX, 24),
                 (ENABLED, 2), (COUNT, 4), (DESCRIPTOR_BASE, 4)):
        for i in range(n):
            memory.setdefault(u32(p+i), (i*29+0x5A)&255)
    wr(memory, WORLD, case.world, 4)
    for i, value in enumerate(IDS):
        wr(memory, CHOICES+i*4, value, 4)
    for i, value in enumerate(artifacts(source.ROOT)[1]):
        wr(memory, SIX+i*4, value, 4)
    for i, value in enumerate(OFFSETS):
        wr(memory, TABLE+i*4, ENTRY+value, 4)
    index = actor_index(case)
    wr(memory, ENABLED, (1 << index) if case.masked and 0 <= index < 16 else 0, 2)
    wr(memory, COUNT, 4096, 4)
    wr(memory, DESCRIPTOR_BASE, DESCRIPTORS, 4)
    ids = artifacts(source.ROOT)[1] if case.kind == 1 else IDS
    chosen = (ids[case.match]&4095) if 0 <= case.match < len(ids) else -1
    for value in ids:
        identity = value&4095
        p = u32(BITS+index*24+(identity//64)*8)
        for i in range(8):
            memory.setdefault(u32(p+i), 0)
        bits = (1 << (chosen&63)) if chosen >= 0 and identity//64 == chosen//64 else 0
        wr(memory, p, bits>>32, 4)
        wr(memory, p+4, bits&0xFFFFFFFF, 4)
    return memory


def public(memory, case):
    home = STACK+case.phase
    return {p: b for p, b in memory.items() if not home-1024 <= p < home+512}


def effect(memory, case):
    if case.mutation:
        wr(memory, WORLD, 99, 4)
        memory[actor(case)] ^= 7


def lookup_value(case, ids):
    if case.connected < 2:
        return u32(case.lookup)
    if 0 <= case.match < len(ids):
        return ids[case.match]&4095
    return 0xFFFFFFFF


def reference(initial, case=Case()):
    memory, calls = dict(initial), []
    kind = u32(case.kind)
    fixed = {0: 0, 2: 2, 3: 3, 4: 4, 5: 5, 7: 15, 8: 16}
    if kind in fixed:
        result = fixed[kind]
    elif kind == 1:
        if rd(memory, WORLD, 4) != 4:
            result = 1
        else:
            calls.append((PREDICATE, (actor(case),)))
            value = u32(case.predicate)
            if case.connected:
                ids = artifacts(source.ROOT)[1]
                calls.append((LOOKUP, (u32(actor_index(case)), 6, ids)))
                value = lookup_value(case, ids) != 0xFFFFFFFF
            effect(memory, case)
            result = 6 if value else 3
    elif kind == 6:
        calls.append((LOOKUP, (u32(actor_index(case)), 5, IDS)))
        effect(memory, case)
        result = -1 if lookup_value(case, IDS) == 0xFFFFFFFF else 6
    else:
        result = -1
    return public(memory, case), calls, u32(result)


class Oracle(FactoryOracle):
    def __init__(self, words, memory, case=Case(), entry=ENTRY, connected=None, arguments=None):
        rom = artifacts(source.ROOT)[0]
        code = {}
        if case.connected:
            code.update(zip(range(PREDICATE, PREDICATE+136, 4), struct.unpack_from('>34I', rom, 0x16F5A8)))
        if case.connected >= 2:
            code.update(zip(range(LOOKUP, LOOKUP+440, 4), struct.unpack_from('>110I', rom, 0xCFF9C)))
        code.update(connected or {})
        self.semantic_calls, self.collisions, self.shifts = [], [], []
        super().__init__(words, memory, case, entry=entry, connected=code,
                         arguments=(u32(case.kind), actor(case)) if arguments is None else arguments)

    def record_call(self, target):
        counts = {ENTRY: 2, PREDICATE: 1, LOOKUP: 3, SHIFT: 4, COLLISION: 3}
        assert target in counts, hex(target)
        args = tuple(map(u32, self.arguments(counts[target])))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if target == PREDICATE:
            self.semantic_calls.append((target, args))
        elif target == LOOKUP:
            ids = tuple(rd(self.memory, args[2]+i*4, 4) for i in range(args[1]))
            self.semantic_calls.append((target, (args[0], args[1], ids)))

    def hook(self, target):
        case, args = self.case, self.calls[-1][1]
        high, value = 0, 0
        if target == PREDICATE:
            value = u32(case.predicate)
            effect(self.memory, case)
        elif target == LOOKUP:
            value = u32(case.lookup)
            effect(self.memory, case)
        elif target == SHIFT:
            self.shifts.append(args)
            assert args[2] == 0 and args[3] < 64
            shifted = ((args[0] << 32) | args[1]) >> args[3]
            high, value = shifted >> 32, shifted&0xFFFFFFFF
        elif target == COLLISION:
            self.collisions.append(args)
            self.assert_collision(args)
            ids = artifacts(source.ROOT)[1] if case.kind == 1 else IDS
            wanted = (ids[case.match]&4095) if 0 <= case.match < len(ids) else -1
            identity = (args[1]-DESCRIPTORS)//0x34
            value = int(identity != wanted)
        else:
            raise AssertionError(hex(target))
        for i in range(4):
            self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2], self.r[3] = (u32(high), u32(value)) if target == SHIFT else (u32(value), 0xA5000003)

    def assert_collision(self, args):
        assert args[0] == actor(self.case) and args[2] == 1
        assert (args[1]-DESCRIPTORS)%0x34 == 0


def cases():
    for kind in (*range(256), -1, 0x80000000, 0x101, 0x10006, 0x7FFFFFFF):
        yield Case(kind=kind)
    for world, value, phase, mutation in itertools.product((0, 4, 47), (0, 1, -1, 0x80000000), (0, 8), (0, 1)):
        yield Case(kind=1, world=world, predicate=value, phase=phase, mutation=mutation)
    for delta, value, phase, mutation in itertools.product((0, 812, 812*20+17, -813, 0x7FFFFFFF, -0x80000000), (-1, 0, 0x80000000), (0, 8), (0, 1)):
        yield Case(kind=6, delta=delta, lookup=value, phase=phase, mutation=mutation)
    for kind, masked, match, phase in itertools.product((1, 6), (0, 1), range(-1, 6), (0, 8)):
        yield Case(kind=kind, connected=2, masked=masked, match=match, phase=phase)
    for value, phase, mutation in itertools.product((-1, 0, 0x80000000), (0, 8), (0, 1)):
        yield Case(kind=1, connected=1, lookup=value, phase=phase, mutation=mutation)


def native_cases():
    return [c for c in cases() if not c.connected and 0 <= c.delta < 812*32-64]


def native_harness(body=None):
    body = source.SELECTED if body is None else body
    rows = []
    for c in native_cases():
        expected = reference(fixture(c), c)[2]
        rows.append('{0x%Xu,0x%Xu,0x%Xu,0x%Xu,%d,%d,0x%Xu}' % (u32(c.kind), u32(c.world), u32(c.predicate), u32(c.lookup), c.delta, c.mutation, expected))
    return '''#include <ultra64.h>
_Static_assert(sizeof(void *)==4 && sizeof(s32)==4,"O32 widths");
u8 actorArena[812*32] __asm__("D_800CC2D0");
s32 D_800BE9F0;
static s32 predicateAnswer, lookupAnswer, calls, mutation;
static u8 *currentActor;
static u32 seenIndex, seenCount, seenIds[5];
static void effect(void){if(mutation){D_800BE9F0=99;currentActor[0]^=7;}}
s32 func_151420F8(u8 *p){if(p!=currentActor)return 0;calls=1;effect();return predicateAnswer;}
s32 func_150A2AEC(s32 index,s32 count,s32 *ids){int i;calls=2;seenIndex=(u32)index;seenCount=count;for(i=0;i<5;i++)seenIds[i]=ids[i];effect();return lookupAnswer;}
''' + body + '''
typedef s32(*Classifier)(s32,u8 *);
static Classifier classifier=func_15146970;
struct Row{u32 kind,world,predicate,lookup;int delta,mutation;u32 expected;};
static const struct Row rows[]={''' + ',\n'.join(rows) + '''};
int run(void){unsigned i,j;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
 const struct Row *r=&rows[i];int shouldCall;u32 answer;
 currentActor=actorArena+r->delta;currentActor[0]=90;D_800BE9F0=(s32)r->world;
 predicateAnswer=(s32)r->predicate;lookupAnswer=(s32)r->lookup;mutation=r->mutation;calls=0;
 shouldCall=r->kind==6?2:r->kind==1&&r->world==4?1:0;
 answer=(u32)classifier((s32)r->kind,currentActor);
 if(answer!=r->expected||calls!=shouldCall)return 1;
 if((u32)D_800BE9F0!=(shouldCall&&mutation?99:r->world))return 1;
 if(currentActor[0]!=(shouldCall&&mutation?93:90))return 1;
 if(shouldCall==2){if(seenIndex!=(u32)(r->delta/812)||seenCount!=5)return 1;for(j=0;j<5;j++)if(seenIds[j]!=0x401Du+j)return 1;}
}return 0;}
void _start(void){int answer=run();__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
