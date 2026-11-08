"""Ordered actor-record search model with the original 64-bit shift helper."""
import itertools
import struct
from dataclasses import dataclass
from functools import lru_cache

from tools.experiments import game_actor_record_list_150a2aec_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_record_vertex_callback_1513e83c_oracle import rd, wr, u32, state

ENTRY, SHIFT, COLLISION = source.ENTRY, 0x10026800, 0x150A1DA0
ENABLED, LIMIT, POINTER, MASKS, ACTORS = 0x800D2340, 0x800D3094, 0x800D3098, 0x800D30F0, 0x800CC2D0
LIST, RECORDS, ALT, MARK = 0x30000, 0x50000, 0x70000, 0x90000
U64 = (1 << 64)-1


@lru_cache(maxsize=2)
def artifacts(root):
    return (root/'conker/conker.us.bin').read_bytes(), (root/'conker/build/conker.us.elf').read_bytes()


@dataclass(frozen=True)
class Case:
    index: int = 3
    count: int = 4
    ids: tuple = (0x401F, 0x4040, 0x407F, 0x40BF)
    limit: int = 192
    enabled: int = 8
    hit: int = 2
    rejection: int = 1
    mutation: int = 0
    private_count: int = 0
    alias: int = 0
    phase: int = 0


def list_address(case):
    home = STACK+case.phase
    return LIST if not case.alias else home+4 if case.alias == 1 else home-64


def wanted(case):
    return (case.ids[case.hit]&4095) if 0 <= case.hit < len(case.ids) else -1


def actor(index):
    return u32(ACTORS+u32(index)*0x32C)


def masked(case):
    return u32(case.index) < 16 and bool(case.enabled & (1 << case.index))


def fixture(case=Case()):
    home = STACK+case.phase
    memory = {home+i: (i*17+0xA5)&255 for i in range(-1024, 512)}
    for p, n in ((ENABLED, 2), (LIMIT, 4), (POINTER, 4), (LIST, 64), (MARK, 16)):
        for i in range(n):
            memory.setdefault(u32(p+i), (i*29+90)&255)
    wr(memory, ENABLED, case.enabled, 2)
    wr(memory, LIMIT, case.limit, 4)
    wr(memory, POINTER, RECORDS, 4)
    for i, value in enumerate(case.ids):
        wr(memory, list_address(case)+4*i, value, 4)
    wr(memory, home+4, case.count, 4)
    if masked(case):
        for value in (*case.ids, 0, case.count, 1, 2, 63, 64, 127, 191, 4095):
            identity = value&4095
            p = u32(MASKS+case.index*24+(identity>>6)*8)
            for i in range(8):
                memory.setdefault(u32(p+i), 0)
            bits = (1 << (wanted(case)&63)) if wanted(case) >= 0 and identity>>6 == wanted(case)>>6 else 0
            wr(memory, p, bits>>32, 4)
            wr(memory, p+4, bits&0xFFFFFFFF, 4)
    return memory


def public(memory, case):
    home = STACK+case.phase
    return {p: value for p, value in memory.items() if not home-1024 <= p < home+512}


def effect(memory, case, ordinal, args, identity, home, identities):
    for i, value in enumerate((*args, identity)):
        wr(memory, MARK+i*4, value, 4)
    if ordinal == 1:
        if case.mutation & 1:
            wr(memory, LIMIT, 2, 4)
        if case.mutation & 2:
            wr(memory, POINTER, ALT, 4)
        if case.mutation & 4:
            wr(memory, identities+4, 0x4000 | (wanted(case)&4095), 4)
        if case.mutation & 8:
            wr(memory, ENABLED, 0xFFFF, 2)
        if case.private_count:
            wr(memory, home+4, case.private_count, 4)


def reference(initial, case=Case(), home=None, identities=None):
    memory, calls = dict(initial), []
    home = STACK+case.phase if home is None else home
    identities = list_address(case) if identities is None else identities
    wr(memory, home+4, case.count, 4)
    use_mask = u32(case.index) < 16 and bool(rd(memory, ENABLED, 2) & (1 << case.index))
    i, ordinal = 0, 0
    if case.count <= 0:
        return public(memory, case), calls, 0xFFFFFFFF
    while True:
        identity = rd(memory, identities+i*4, 4)&4095
        if identity < rd(memory, LIMIT, 4):
            if use_mask:
                p = u32(MASKS+u32(case.index)*24+(identity>>6)*8)
                high, low = rd(memory, p, 4), rd(memory, p+4, 4)
                args = (high, low, 0, identity&63)
                calls.append((SHIFT, args))
                for j, value in enumerate(args):
                    wr(memory, home-64+j*4, value, 4)
                if (((high << 32) | low) >> (identity&63)) & 1:
                    return public(memory, case), calls, identity
            else:
                base = rd(memory, POINTER, 4)
                args = (actor(case.index), u32(base+identity*0x34), 1)
                calls.append((COLLISION, args))
                ordinal += 1
                result = 0 if identity == wanted(case) else u32(case.rejection)
                effect(memory, case, ordinal, args, identity, home, identities)
                for j in range(4):
                    wr(memory, home-64+j*4, 0xB5000000+j, 4)
                if result == 0:
                    return public(memory, case), calls, identity
        i += 1
        if i == signed(rd(memory, home+4, 4)):
            break
        assert i < 32, 'Unbounded reference input'
    return public(memory, case), calls, 0xFFFFFFFF


class Oracle(FactoryOracle):
    def __init__(self, words, memory, case=Case(), entry=ENTRY, connected=None, arguments=None):
        rom, _ = artifacts(source.ROOT)
        code = {} if entry == SHIFT else dict(zip(range(SHIFT, SHIFT+44, 4), struct.unpack_from('>11I', rom, 0x26800)))
        code.update(connected or {})
        self.target_home, self.identities = STACK+case.phase, list_address(case)
        self.collisions = []
        super().__init__(words, memory, case, entry=entry, connected=code,
                         arguments=(u32(case.index), u32(case.count), list_address(case)) if arguments is None else arguments)

    def execute(self, word):
        op, rs, rt, rd_, sa, fn = word>>26, word>>21&31, word>>16&31, word>>11&31, word>>6&31, word&63
        if op == 55 or (op == 0 and fn in (22, 60, 63)):
            prior = self.own_instruction
            self.own_instruction, self.dispatched_word = True, word
            try:
                if op == 55:
                    offset = ((word&65535)^32768)-32768
                    self.r[rt] = self.get(u32(self.r[rs]+offset), 8)
                elif fn == 22:
                    self.r[rd_] = (self.r[rt]&U64) >> (self.r[rs]&63)
                elif fn == 60:
                    self.r[rd_] = (self.r[rt] << (sa+32))&U64
                else:
                    value = self.r[rt]&U64
                    value = value-(1 << 64) if value >> 63 else value
                    self.r[rd_] = u32(value >> (sa+32))
                self.r[0] = 0
            finally:
                self.own_instruction = prior
            return
        return super().execute(word)

    def record_call(self, target):
        assert target in (ENTRY, SHIFT, COLLISION), hex(target)
        args = tuple(map(u32, self.arguments(4 if target == SHIFT else 3)))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if target == ENTRY:
            self.target_home, self.identities = self.r[29], args[2]

    def hook(self, target):
        assert target == COLLISION
        args = self.calls[-1][1]
        base = rd(self.memory, POINTER, 4)
        identity = u32(args[1]-base)//0x34
        assert args == (actor(self.case.index), u32(base+identity*0x34), 1)
        self.collisions.append(args)
        result = 0 if identity == wanted(self.case) else u32(self.case.rejection)
        effect(self.memory, self.case, len(self.collisions), args, identity, self.target_home, self.identities)
        for i in range(4):
            self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = result


def cases():
    for index, enabled, count, hit, phase in itertools.product((0, 3, 15, 16, 25, -1, 0x80000000), (0, 0xFFFF), (-1, 0, 1, 4), (-1, 0, 3), (0, 8)):
        yield Case(index=index, enabled=enabled, count=count, hit=hit, phase=phase)
    for identity, flag, limit, phase in itertools.product((0, 1, 31, 32, 63, 64, 65, 95, 127, 128, 191, 4095), (0, 0xFFFFF000), (0, 192, 0xFFFFFFFF), (0, 8)):
        yield Case(count=1, ids=(identity|flag,), hit=0, limit=limit, phase=phase)
    for mutation, hit, rejection, phase in itertools.product(range(16), (-1, 3), (1, -1), (0, 8)):
        yield Case(enabled=0, ids=(4, 3, 7, 9), mutation=mutation, hit=hit, rejection=rejection, phase=phase)
    for alias, private_count, enabled in itertools.product((0, 1, 2), (0, 1, 2), (0, 8)):
        yield Case(ids=(63, 1, 7, 8, 9), count=5, hit=4, alias=alias, private_count=private_count, enabled=enabled)
    yield Case(count=0x7FFFFFFF, ids=(1,), hit=0)
    yield Case(count=-0x80000000)


def native_cases():
    return [c for c in cases() if 0 <= c.index < 26 and c.limit <= 192 and not c.alias and not c.private_count and c.count <= len(c.ids)]


def native_harness(body=None):
    body = source.SELECTED if body is None else body
    prefix = (source.ROOT/source.SOURCE).read_text().split('s32 func_150A09D0()', 1)[0]
    rows = []
    for c in native_cases():
        _, calls, expected = reference(fixture(c), c)
        collision_count = sum(target == COLLISION for target, args in calls)
        ids = ','.join('0x%Xu' % u32(v) for v in c.ids)+(',' if len(c.ids) < 8 else '')+','.join('0' for _ in range(8-len(c.ids)))
        rows.append('{%d,%d,0x%Xu,%d,%d,%d,%d,%d,0x%Xu,{%s}}' % (c.index, c.count, c.limit, c.enabled, c.hit, c.rejection, c.mutation, collision_count, expected, ids))
    return prefix+'''
_Static_assert(sizeof(void *)==4 && sizeof(struct127)==812 && sizeof(GeneratedCDE80Record)==52,"O32 records");
struct127 D_800CC2D0[26];
static GeneratedCDE80Record records[192], alternate[192];
GeneratedCDE80Record *D_800D3098;
s32 D_800D3094;
u64 D_800D30F0[48];
u16 D_800D2340;
static s32 ids[8], wanted, rejection, mutation, calls, expectedIndex;
static u32 mark[4];
s32 func_150A1DA0(struct127 *a,s32 descriptor,s32 mode){
 GeneratedCDE80Record *p=(GeneratedCDE80Record *)(u32)descriptor;s32 identity=p-D_800D3098;int result;
 if(a!=&D_800CC2D0[expectedIndex]||mode!=1||identity<0||identity>=192)return 12345;
 calls++;result=identity==wanted?0:rejection;
 mark[0]=(u32)a;mark[1]=(u32)p;mark[2]=mode;mark[3]=identity;
 if(calls==1){if(mutation&1)D_800D3094=2;if(mutation&2)D_800D3098=alternate;if(mutation&4)ids[1]=0x4000|(wanted&4095);if(mutation&8)D_800D2340=0xFFFF;}
 return result;
}
''' + body + '''
typedef s32(*Lookup)(s32,s32,s32 *);static Lookup lookup=func_150A2AEC;
struct Row{s32 index,count;u32 limit;s32 enabled,hit,rejection,mutation,expectedCalls;u32 expected;u32 ids[8];};
static const struct Row rows[]={''' + ',\n'.join(rows) + '''};
int run(void){unsigned i,j;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
 const struct Row *r=&rows[i];u32 answer,expectedPointer;int useMask;
 for(j=0;j<8;j++)ids[j]=(s32)r->ids[j];
 for(j=0;j<48;j++)D_800D30F0[j]=0;
 wanted=r->hit>=0?(s32)(r->ids[r->hit]&4095):-1;
 if(r->index<16 && wanted>=0 && wanted<192)D_800D30F0[r->index*3+(wanted>>6)]=1ULL<<(wanted&63);
 D_800D2340=r->enabled;D_800D3094=(s32)r->limit;D_800D3098=records;
 calls=0;for(j=0;j<4;j++)mark[j]=0;expectedIndex=r->index;mutation=r->mutation;rejection=r->rejection;
 answer=(u32)lookup(r->index,r->count,ids);if(answer!=r->expected||calls!=r->expectedCalls)return 1;
 useMask=r->index<16&&(r->enabled&(1<<r->index));
 if(useMask&&calls)return 1;
 expectedPointer=(u32)(calls&&(mutation&2)?alternate:records);
 if((u32)D_800D3098!=expectedPointer)return 1;
 if((u32)D_800D3094!=(calls&&(mutation&1)?2:r->limit))return 1;
 if(D_800D2340!=(calls&&(mutation&8)?0xFFFF:r->enabled))return 1;
 if(calls&&(mark[0]!=(u32)&D_800CC2D0[r->index]||mark[2]!=1))return 1;
}return 0;}
void _start(void){int answer=run();__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
