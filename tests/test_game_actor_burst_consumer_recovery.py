"""Bounded semantic and packet recovery; complete word/state matching is open."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_burst_consumer_candidates as source
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating

PARAMS, STACK, CREATED = 0x22000, producer.STACK, producer.CREATED
RNG, RANDOM, TRIG, FACTORY, ANIMATION, MEMCPY = producer.RNG, producer.RANDOM, producer.TRIG, producer.FACTORY, producer.ANIMATION, producer.MEMCPY
FLOATS = tuple(range(0, 0x50, 4))
FIELDS = tuple((at, 4) for at in FLOATS) + ((0x50, 4), (0x54, 2), (0x56, 2), (0x58, 1), (0x5C, 4)) + tuple(
    (at, 1) for at in range(0x60, 0x69)) + ((0x6A, 1), (0x6C, 4), (0x70, 1), (0x72, 2), (0x74, 2))
INTEGER_TAPE = (0, 0xFFFFFFFF, 0x12345678, 0x80000000)
FLOAT_TAPE = tuple(map(bits, (0.0, 0.25, 0.5, 0.75)))
TRIG_TAPE = tuple(map(bits, (0.0, 0.5, -0.5, 1.0)))


def fixture(count=3, seed=0):
    m = producer.fixture(seed=seed)
    m.update({PARAMS + i: 0xA5 for i in range(0x80)})
    put(m, PARAMS, count & 65535, 2)
    for at, value in ((4, 1.5), (8, -2.5), (12, 3.5), (0x14, 2.0),
            (0x20, 1.0), (0x24, 0.5), (0x28, -1.0), (0x2C, 0.25),
            (0x30, 0.5), (0x34, -0.5), (0x38, 1.0), (0x3C, 0.5),
            (0x40, 0.25), (0x44, -1.0), (0x48, 0.5), (0x4C, -4.0), (0x50, 8.0)):
        put(m, PARAMS + at, bits(value))
    for at, value in ((0x10, 90), (0x18, 0), (0x1A, 255), (0x1C, -64), (0x1E, 40), (0x56, 50), (0x58, 25)):
        put(m, PARAMS + at, value & 65535, 2)
    put(m, PARAMS + 0x54, 3, 1)
    put(m, PARAMS + 0x55, 7, 1)
    if seed == 0:
        for at in range(STACK - 0x700, STACK + 0x180):
            m[at] = 0xA5
    return m


def rounded_binary(a, b, operation):
    return bits(operation(floating(a), floating(b)))


def mul(a, b):
    return rounded_binary(a, b, lambda x, y: x * y)


def add(a, b):
    return rounded_binary(a, b, lambda x, y: x + y)


def sub(a, b):
    return rounded_binary(a, b, lambda x, y: x - y)


def signed_half(v):
    return v if v < 32768 else v - 65536


def fnv(records):
    value = 2166136261
    for record in records:
        for word in record:
            value = ((value ^ (word & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return value


class FactoryBoundary(Exception):
    pass


class GuestBreak(Exception):
    pass


class ConsumerOracle(producer.BurstOracle):
    def __init__(self, words, memory, kind=1, slot=255, context=1, phase=0, outcome=0,
            mutation=0, limit=None):
        super().__init__(words, memory, actor=PARAMS, phase=phase,
            symbols=dict(source.SYMBOLS, func_151A6F00=source.ENTRY), entry=source.ENTRY,
            connected=dict(zip(range(MEMCPY, MEMCPY + 44, 4), struct.unpack_from('>11I',
                (Path(__file__).resolve().parents[2] / 'conker/conker.us.bin').read_bytes(), 0x22EC0))),
            arguments=(PARAMS, kind, slot, context), outcome=outcome)
        self.kind, self.mutation, self.limit = kind & 255, mutation, limit
        self.records, self.raw_packets, self.raw_animations, self.raw_copies, self.locations = [], [], [], [], {}
        self.saved_fp_calls = []
        self.factory_count = self.integer_count = self.random_count = 0

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 27 and self.r[word >> 16 & 31] == 0:
            self.lo, self.hi = 0xFFFFFFFF, self.r[word >> 21 & 31]
        elif word >> 26 == 0 and word & 63 == 13:
            raise GuestBreak(word)
        else:
            super().execute(word)

    def record_call(self, target):
        self.saved_fp_calls.append((target, tuple(self.f[20:])))
        if target == RNG:
            self.records.append((1,))
        elif target == RANDOM:
            self.records.append((2,))
        elif target == TRIG:
            self.records.append((3, self.r[4]))
        elif target == FACTORY:
            args = self.arguments(6)
            fields = [(at, size) for at, size in FIELDS if self.kind < 4 or at not in (0x34, 0x38, 0x3C)]
            values = tuple(self.get(args[0] + at, size) for at, size in fields)
            self.records.append((4, *args[1:], *values))
            self.raw_packets.append(bytes(self.memory[args[0] + i] for i in range(0x78)))
            self.locations['descriptor'] = args[0] - (STACK + self.phase - 0x168)
            if self.limit is not None and self.factory_count == self.limit:
                raise FactoryBoundary
        elif target == ANIMATION:
            args = self.arguments(4)
            p = args[0]
            values = tuple(self.get(p + i * 4, 4) - CREATED for i in range(3)) + tuple(
                self.get(p + at, size) for at, size in ((0xC, 4), (0x10, 4), (0x14, 2), (0x16, 1), (0x17, 1)))
            self.records.append((6, *args[1:], *values))
            self.raw_animations.append(bytes(self.memory[p + i] for i in range(28)))
            self.locations['animation'] = p - (STACK + self.phase - 0x168)
        else:
            assert target == MEMCPY
            destination, pointer, size = self.arguments(3)
            self.raw_copies.append((destination, bytes(self.memory[pointer + i] for i in range(size))))
            if size == 16:
                payload = (self.get(pointer, 4), self.get(pointer + 8, 1), self.get(pointer + 9, 1),
                    self.get(pointer + 10, 2), self.get(pointer + 12, 2))
                self.records.append((5, destination - CREATED, *payload))
                self.locations['payload'] = pointer - (STACK + self.phase - 0x168)
            else:
                assert size == 4
                self.records.append((7, destination - CREATED, self.get(pointer, 4)))
                self.locations['scale'] = pointer - (STACK + self.phase - 0x168)

    def hook(self, target):
        if target == RNG and self.mutation and self.integer_count == 0:
            put(self.memory, PARAMS, 0, 2)
            put(self.memory, PARAMS + 4, bits(8.0))
            put(self.memory, PARAMS + 0x3C, bits(1.0))
            put(self.memory, PARAMS + 0x54, 99, 1)
        if target == FACTORY and self.mutation:
            put(self.memory, self.r[4] + 0xC, bits(2.0))
        super().hook(target)


class Reference:
    def __init__(self, memory, kind=1, slot=255, context=1, outcome=0, mutation=0):
        self.m, self.kind, self.slot, self.context = dict(memory), kind & 255, slot & 255, context & 0xFFFFFFFF
        self.outcome, self.mutation = outcome, mutation
        self.records, self.integer_count, self.random_count = [], 0, 0

    def get(self, at, size=4):
        return read(self.m, PARAMS + at, size)

    def integer(self):
        self.records.append((1,))
        if self.mutation and self.integer_count == 0:
            put(self.m, PARAMS, 0, 2)
            put(self.m, PARAMS + 4, bits(8.0))
            put(self.m, PARAMS + 0x3C, bits(1.0))
            put(self.m, PARAMS + 0x54, 99, 1)
        value = INTEGER_TAPE[self.integer_count % 4]
        self.integer_count += 1
        return value

    def random(self):
        self.records.append((2,))
        value = FLOAT_TAPE[self.random_count % 4]
        self.random_count += 1
        return value

    def trig(self, angle):
        self.records.append((3, angle))
        return TRIG_TAPE[angle & 3]

    def run(self, limit=None):
        count = self.get(0, 2)
        duration = self.get(0x10, 2)
        extra = (bits(-18.0), self.get(0x54, 1), self.get(0x55, 1), self.get(0x56, 2), self.get(0x58, 2))
        d = dict.fromkeys(FLOATS, 0)
        d.update({0x1C: bits(1.0), 0x20: bits(1.0), 0x24: bits(1.0), 4: bits(0.25),
            0x50: 0x21E9, 0x54: duration, 0x56: 27, 0x58: 0, 0x5C: 0,
            0x60: 255, 0x61: 1, 0x62: 5, 0x63: 4, 0x64: 0, 0x65: 0, 0x66: 1,
            0x67: 0, 0x68: 0, 0x6A: 0, 0x6C: 0, 0x70: 0, 0x72: 32, 0x74: 7})
        for index in range(min(count, limit) if limit is not None else count):
            r = self.integer()
            a = (r % ((signed_half(self.get(0x1A, 2)) + 1) & 0xFFFFFFFF) + signed_half(self.get(0x18, 2))) & 255
            r = self.integer()
            b = (r % ((signed_half(self.get(0x1E, 2)) + 1) & 0xFFFFFFFF) + signed_half(self.get(0x1C, 2))) & 255
            c0, s0 = self.trig((a - 64) & 255), self.trig(a)
            c1, s1 = self.trig((b - 64) & 255), self.trig(b)
            radius = mul(self.random(), self.get(0x14))
            horizontal = mul(radius, s1)
            d[0x28] = add(self.get(4), mul(horizontal, c0))
            d[0x2C] = sub(self.get(8), mul(radius, c1))
            d[0x30] = add(self.get(12), mul(horizontal, s0))
            if self.kind == 0:
                speed = add(mul(self.random(), self.get(0x24)), self.get(0x20))
                vertical = add(mul(self.random(), self.get(0x2C)), self.get(0x28))
                d[0x34], d[0x38], d[0x3C] = mul(speed, c0), vertical, mul(speed, s0)
            elif self.kind == 1:
                speed = add(mul(self.random(), self.get(0x24)), self.get(0x20))
                h = mul(speed, s1)
                d[0x34], d[0x38], d[0x3C] = mul(h, c0), mul(speed ^ 0x80000000, c1), mul(h, s0)
            elif self.kind == 2:
                d[0x34], d[0x38], d[0x3C] = (self.get(at) for at in (0x30, 0x34, 0x38))
            elif self.kind == 3:
                speed = add(mul(self.random(), self.get(0x24)), self.get(0x20))
                d[0x34], d[0x38], d[0x3C] = (mul(self.get(at), speed) for at in (0x30, 0x34, 0x38))
            scale = add(mul(self.random(), self.get(0x40)), self.get(0x3C))
            d[0xC] = d[8] = scale
            d[0] = mul(scale, bits(30.0))
            d[0x4C] = add(mul(self.random(), self.get(0x48)), self.get(0x44))
            d[0x40] = add(mul(self.random(), self.get(0x50)), self.get(0x4C))
            d[0x48] = add(mul(self.random(), self.get(0x50)), self.get(0x4C))
            fields = [at for at, size in FIELDS if self.kind < 4 or at not in (0x34, 0x38, 0x3C)]
            self.records.append((4, 0, 0, 16, self.slot, self.context, *(d[at] for at in fields)))
            if self.mutation:
                d[0xC] = bits(2.0)
            if self.outcome:
                obj = index * 0x200
                self.records.append((5, obj + 0x170, *extra))
                self.records.append((6, 4, self.slot, self.context, obj + 0x38, obj + 0x3C, obj + 0x40,
                    mul(bits(15.0), d[0xC]), bits(0.125), 300, 0, 1))
                if self.outcome == 2:
                    self.records.append((7, 0x6C0, scale))
        return self.records


class GameActorBurstConsumerRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-burst-consumer-recovery-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(owner='conker/src/game/generated_1D43B0.c', caller=producer.source.SOURCE,
            elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', makefile='conker/Makefile', assembly='conker/asm/1D43B0.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            h = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                h[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(h, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == '50b064c6d7af59a7a78eeece1a2b3c8e32b2886b1695097fd6b43044f2b092ee'
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>315I', (cls.root / 'conker/conker.us.bin').read_bytes(), source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_single_precision_candidate_is_explicitly_nonmatching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (313, 0x168, 143))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertFalse(any(w >> 26 == 17 and w >> 21 & 31 == 17 for w in self.words))
        self.receipt('shape', words=313, frame=360, raw_differences=143, installed=False,
            no_guards_or_padding=True, matching_credit=False)

    def test_02_all_kinds_counts_outcomes_and_callback_mutations(self):
        cases = 0
        for kind, count, outcome, mutation, phase, seed in itertools.product((0, 1, 2, 3, 4, 255, 0x100, 0x103),
                (0, 1, 2, 3, 4), range(3), (0, 1), (0, 8), (0, 1)):
            domain = (kind, count, outcome, mutation, phase, seed)
            memory = fixture(count, seed)
            expected = Reference(memory, kind, 0x123400FF, 0x87654321, outcome, mutation).run()
            models = [ConsumerOracle(body, dict(memory), kind, 0x123400FF, 0x87654321,
                phase, outcome, mutation).run() for body in (self.retail, self.words)]
            for model in models:
                self.assertEqual(model.records, expected, domain)
                self.assertEqual(model.factory_count, count)
            original, candidate = models
            self.assertEqual(candidate.raw_packets, original.raw_packets, ('creation', domain))
            self.assertEqual(candidate.raw_animations, original.raw_animations, ('animation', domain))
            self.assertEqual(candidate.raw_copies, original.raw_copies, ('memcpy', domain))
            self.assertEqual(candidate.locations, original.locations, ('private homes', domain))
            self.assertTrue(producer.complete_state(candidate) == producer.complete_state(original),
                ('complete modeled return state', domain))
            cases += 1
        self.receipt('guest', cases=cases, full0_1_2_3_default_and_masked_kind_semantics=True,
            counts0_through4_all_three_allocation_outcomes=True,
            input_count_snapshot_live_geometry_and_post_factory_rate_feedback=True,
            seeded_guest_creation_animation_and_memcpy_bytes_and_homes_agree=True,
            all_modeled_return_registers_memory_HI_LO_condition_and_access_traces_agree=True,
            instruction_PC_BD_FCSR_and_word_identity_not_qualified=True,
            native_indeterminate_bytes_not_qualified=True)

    def test_03_signed_counts_stop_at_effective_factory_boundaries(self):
        cases = 0
        for count, kind in itertools.product((0x8000, 0xFFFF, 0xFFFE), (0, 1, 2, 3, 4, 255)):
            expected = Reference(fixture(count), kind).run(limit=3)
            models = [ConsumerOracle(body, fixture(count), kind, limit=2) for body in (self.retail, self.words)]
            for model in models:
                with self.assertRaises(FactoryBoundary):
                    model.run()
                self.assertEqual(model.factory_count, 2)
                self.assertEqual(model.records, expected)
            cases += 1
        self.receipt('signed-counts', effective_three_iteration_prefix_cases=cases,
            full65535_iteration_native_or_hardware_runs_not_claimed=True)

    def test_04_zero_divisor_guest_break_and_empty_count_boundaries(self):
        cases = 0
        for field, call_count in ((0x1A, 1), (0x1E, 2)):
            for body in (self.retail, self.words):
                memory = fixture()
                put(memory, PARAMS + field, 0xFFFF, 2)
                model = ConsumerOracle(body, memory)
                with self.assertRaises(GuestBreak):
                    model.run()
                self.assertEqual(model.integer_count, call_count)
                self.assertEqual(model.factory_count, 0)
                cases += 1
                put(memory, PARAMS, 0, 2)
                empty = ConsumerOracle(body, memory).run()
                self.assertEqual(empty.records, [])
        self.receipt('divisor', fired_break7_prefixes=cases, no_native_zero_divisor_claim=True,
            empty_count_skips_division_but_not_initial_parameter_setup=True)

    def test_05_m2c_off_by_one_and_full_word_promotion_gate(self):
        wrong = source.SELECTED.replace('s16 remaining = params->count;', 's16 remaining = params->count - 1;')
        _, words = source.compile_candidate(self.root, self.out, 'wrong-initial-decrement', wrong)
        model = ConsumerOracle(words, fixture(3)).run()
        self.assertEqual(model.factory_count, 2)
        self.assertNotEqual(model.records, Reference(fixture(3)).run())
        models = [ConsumerOracle(body, fixture(seed=1), outcome=2).run() for body in (self.retail, self.words)]
        self.assertEqual(models[0].records, models[1].records)
        self.assertEqual(models[0].raw_packets, models[1].raw_packets)
        self.assertTrue(producer.complete_state(models[0]) == producer.complete_state(models[1]),
            'Recovered modeled return states differ')
        self.receipt('promotion-gate', effective_m2c_count3_yields2_negative=True,
            initialized_semantics_and_complete_raw_creation_packets_agree=True,
            complete_modeled_return_states_agree_but_word_identity_still_fails=True,
            raw_animation_packets_agree=models[0].raw_animations == models[1].raw_animations,
            raw_memcpy_data_agree=models[0].raw_copies == models[1].raw_copies,
            original_locations=models[0].locations, candidate_locations=models[1].locations,
            production_promotion_rejected=True)

    def test_06_matching_length_double_literals_are_not_retail_operations(self):
        body = dict(source.candidates())['literals-size30.0-rate15.0f']
        meta, words = source.compile_candidate(self.root, self.out, 'double-literal-length-control', body)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (315, 0x168, 248))
        self.assertTrue(any(w >> 26 == 17 and w >> 21 & 31 == 17 for w in words))
        self.assertFalse(any(w >> 26 == 17 and w >> 21 & 31 == 17 for w in self.retail))
        self.receipt('double-control', equal_length_frame_not_matching=True,
            new_double_precision_instruction_domain_rejected=True)

    def test_07_production_and_protected_inputs_are_unchanged(self):
        for name, path in self.paths.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + name)).read_bytes(), name)
        self.assertIn(source.ORIGINAL, (self.root / source.SOURCE).read_text())
        self.receipt('protected', whole_ELF_sources_guards_conversion_profile_assembly_fixed=True,
            consumer_still_a_production_placeholder=True)

    def test_08_native32_all_kind_paths_count_snapshot_and_feedback(self):
        cases = list(itertools.product((0, 1, 2, 3, 4, 255), (0, 1, 3), range(3), (0, 1)))
        golden = [fnv(Reference(fixture(count), kind, outcome=outcome, mutation=mutation).run())
            for kind, count, outcome, mutation in cases]
        fields = ','.join('{%d,%d}' % pair for pair in FIELDS)
        program = '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
''' + source.RECORD + '''
static ActorBurstPacket97AA0 packet;
static union {u32 align;u8 bytes[4096];} arena;
static f32 D_800A8DC0=0.25f,D_800A8DC4=0.125f;
static u32 hash;static int integers,randoms,factories,outcome,mutation,mode,words;
static const u32 integerTape[]={0,0xFFFFFFFFu,0x12345678u,0x80000000u};
static const u32 floatTape[]={0,0x3E800000,0x3F000000,0x3F400000};
static const u32 trigTape[]={0,0x3F000000,0xBF000000,0x3F800000};
static const int fields[][2]={''' + fields + '''};
static void finish(int code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static void emit(u32 v){if(++words>20000)finish(20);hash=(hash^v)*16777619u;}
static u32 value(u8 *p,int size){return size==4?*(u32*)p:size==2?*(u16*)p:*p;}
s32 func_150ADA20(void){u32 v;
 emit(1);if(mutation&&!integers){packet.count=0;packet.position[0]=8.0f;packet.scale=1.0f;packet.unk54=99;}
 v=integerTape[integers++&3];return (s32)v;}
f32 func_150ADA68(void){union{u32 i;f32 f;}v;emit(2);v.i=floatTape[randoms++&3];return v.f;}
f32 func_151423D8(u8 angle){union{u32 i;f32 f;}v;emit(3);emit(angle);v.i=trigTape[angle&3];return v.f;}
void *func_15132A4C(void *pointer,s32 resource,s32 val,s32 extra,u8 slot,s32 context){int i;u8 *p=pointer,*result;
 emit(4);emit(resource);emit(val);emit(extra);emit(slot);emit(context);
 for(i=0;i<(int)(sizeof(fields)/sizeof(fields[0]));i++){int at=fields[i][0];if(mode<4||(at!=0x34&&at!=0x38&&at!=0x3C))emit(value(p+at,fields[i][1]));}
 if(mutation)*(f32*)(p+12)=2.0f;
 result=outcome?arena.bytes+factories*0x200:NULL;factories++;return result;}
void *func_15134908(void *pointer,s32 extra,u8 slot,s32 context){u8 *p=pointer;int i;
 emit(6);emit(extra);emit(slot);emit(context);for(i=0;i<3;i++)emit(*(u32*)(p+i*4)-(u32)arena.bytes);
 emit(value(p+12,4));emit(value(p+16,4));emit(value(p+20,2));emit(p[22]);emit(p[23]);
 return outcome==2?arena.bytes+0x680:NULL;}
void *memcpy(void *destination,const void *pointer,unsigned int size){u8 *d=destination;const u8 *p=pointer;unsigned int i;
 if(size==16){emit(5);emit(d-arena.bytes);emit(*(const u32*)p);emit(p[8]);emit(p[9]);emit(*(const u16*)(p+10));emit(*(const u16*)(p+12));}
 else{if(size!=4)finish(21);emit(7);emit(d-arena.bytes);emit(*(const u32*)p);}
 for(i=0;i<size;i++){d[i]=p[i];}return destination;}
''' + source.SELECTED + '''
static const u32 expected[]={''' + ','.join('0x%Xu' % v for v in golden) + '''};
static const int kinds[]={0,1,2,3,4,255},counts[]={0,1,3};
static void (*volatile invoke)(ActorBurstPacket97AA0*,u8,u8,s32)=func_151A6F00;
int run(void){int k,c,o,m,i,n=0;
 if(sizeof(void*)!=4||sizeof(ActorBurstPacket97AA0)!=92||sizeof(BurstCreationDescriptor1D43B0)!=120||sizeof(BurstExtra1D43B0)!=16||sizeof(BurstAnimationPacket1D43B0)!=28)return 10;
 for(k=0;k<6;k++)for(c=0;c<3;c++)for(o=0;o<3;o++)for(m=0;m<2;m++){
  for(i=0;i<4096;i++)arena.bytes[i]=0xA5;
  packet.count=counts[c];packet.duration=90;packet.position[0]=1.5f;packet.position[1]=-2.5f;packet.position[2]=3.5f;
  packet.radius=2.0f;packet.angle0=0;packet.range0=255;packet.angle1=-64;packet.range1=40;
  packet.speed=1.0f;packet.speedRange=0.5f;packet.unk28=-1.0f;packet.unk2C=0.25f;
  packet.direction[0]=0.5f;packet.direction[1]=-0.5f;packet.direction[2]=1.0f;
  packet.scale=0.5f;packet.scaleRange=0.25f;packet.unk44=-1.0f;packet.unk48=0.5f;packet.unk4C=-4.0f;packet.unk50=8.0f;
  packet.unk54=3;packet.unk55=7;packet.unk56=50;packet.unk58=25;
  integers=randoms=factories=words=0;outcome=o;mutation=m;mode=kinds[k];hash=2166136261u;
  invoke(&packet,(u8)mode,255,1);if(hash!=expected[n++]||factories!=counts[c])return 11;
 }return n==108?0:12;}
void _start(void){finish(run());}
'''
        wrong = source.SELECTED.replace('s16 remaining = params->count;',
            's16 remaining = params->count == 3 ? 2 : params->count;')
        for name, body, profile, success in (('O2', source.SELECTED, '-O2', True),
                ('O0', source.SELECTED, '-O0', True), ('wrong-count', wrong, '-O2', False)):
            path = self.out / ('native-' + name + '.c')
            path.write_text(program.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-msse2',
                '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode == 0, success, (name, result.returncode))
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=108,
            independent_RNE_reference_golden_call_trace_hashes=True,
            actual0_1_2_3_default_count_snapshot_and_callback_feedback=True,
            bad_m2c_count_negative_effective=True, native_indeterminate_bytes_and_zero_divisor_excluded=True)

    def test_09_real_declaration_order_recovers_payload_and_scale_homes(self):
        original = ConsumerOracle(self.retail, fixture(seed=1), outcome=2).run()
        measurements = []
        for name, body in source.private_layout_forms():
            meta, words = source.compile_candidate(self.root, self.out, name, body)
            model = ConsumerOracle(words, fixture(seed=1), outcome=2).run()
            self.assertEqual(model.records, original.records)
            self.assertEqual(model.raw_packets, original.raw_packets)
            self.assertEqual(model.locations['descriptor'], 0xE8)
            expected_payload = (0xD4, 0xD0) if 'float1' in name else (0xD8, 0xD4)
            self.assertEqual((model.locations['payload'], model.locations['scale']), expected_payload)
            self.assertEqual(model.locations['animation'], 0x8C if 'pointers1' in name else 0x94)
            self.assertEqual(model.raw_copies == original.raw_copies, 'float1' in name)
            self.assertEqual(model.raw_animations == original.raw_animations, 'pointers1' in name)
            measurements.append(dict(name=name, words=meta['body_words'], differences=meta['differences'],
                locations=model.locations, complete_memcpy_data_matches=model.raw_copies == original.raw_copies,
                complete_animation_matches=model.raw_animations == original.raw_animations))
        self.receipt('private-layout', original=original.locations, measurements=measurements,
            no_dummy_padding_or_unused_declaration_added=True,
            all_four_selected_homes_match_retail_without_larger_struct=True)

    def test_10_mode2_copies_raw_direction_bits_without_float_arithmetic(self):
        patterns = (0, 0x80000000, 0x3F800000, 0x7F800000, 0xFF800000,
            0x7FC01234, 0x7F801234, 0xFFFFFFFF)
        cases = 0
        for index, phase, seed in itertools.product(range(len(patterns)), (0, 8), (0, 1)):
            directions = tuple(patterns[(index + axis) % len(patterns)] for axis in range(3))
            memory = fixture(1, seed)
            for axis, word in enumerate(directions):
                put(memory, PARAMS + 0x30 + axis * 4, word)
            models = [ConsumerOracle(body, dict(memory), kind=2, phase=phase,
                outcome=2).run() for body in (self.retail, self.words)]
            expected = Reference(memory, kind=2, outcome=2).run()
            for model in models:
                self.assertEqual(model.records, expected)
                self.assertEqual(struct.unpack_from('>3I', model.raw_packets[0], 0x34), directions)
            self.assertEqual(models[0].raw_packets, models[1].raw_packets)
            self.assertEqual(models[0].raw_animations, models[1].raw_animations)
            self.assertEqual(models[0].raw_copies, models[1].raw_copies)
            cases += 1
        wrong = source.SELECTED.replace(
            'descriptor.velocity = *(BurstVector1D43B0 *)params->direction;',
            'descriptor.velocity.x = params->direction[0];\n'
            '                descriptor.velocity.y = params->direction[1];\n'
            '                descriptor.velocity.z = params->direction[2];')
        _, words = source.compile_candidate(self.root, self.out, 'scalar-direction-shape-control', wrong)
        self.assertNotEqual(words, self.words)
        model = ConsumerOracle(words, fixture(1), kind=2, outcome=2).run()
        self.assertEqual(model.records, Reference(fixture(1), kind=2, outcome=2).run())
        self.receipt('raw-direction', guest_raw_copy_cases=cases,
            raw_nan_infinity_signed_zero_words_copied_not_arithmetically_transformed=True,
            scalar_copy_shape_control_effective_but_not_a_semantic_rejection=True)

    def test_11_saved_float_roles_and_cached_constants_match_at_real_calls(self):
        cases = 0
        for kind, count, phase, outcome, mutation, seed in itertools.product((0, 1, 2, 3, 4, 255),
                (1, 3), (0, 8), range(3), (0, 1), (0, 1)):
            memory = fixture(count, seed)
            models = [ConsumerOracle(body, dict(memory), kind, phase=phase,
                outcome=outcome, mutation=mutation).run() for body in (self.retail, self.words)]
            self.assertEqual(models[0].saved_fp_calls, models[1].saved_fp_calls,
                (kind, count, phase, outcome, mutation, seed))
            first_target, first_values = models[1].saved_fp_calls[0]
            self.assertEqual(first_target, RNG)
            self.assertEqual((first_values[10], first_values[8]), (bits(15.0), bits(30.0)))
            cases += 1
        _, old = source.compile_candidate(self.root, self.out, 'prior-shared-speed-control', source.PRIVATE_SELECTED)
        original = ConsumerOracle(self.retail, fixture(3), outcome=2).run()
        prior = ConsumerOracle(old, fixture(3), outcome=2).run()
        self.assertEqual(prior.records, original.records)
        self.assertNotEqual(prior.saved_fp_calls, original.saved_fp_calls)
        self.assertEqual(prior.saved_fp_calls[0][1][10], bits(30.0))
        self.receipt('saved-float-roles', real_call_boundary_domains=cases,
            all_F20_through_F31_saved_roles_and_lifetimes_agree=True,
            F30_15_F28_30_cached_before_first_RNG=True,
            prior_shared_speed_control_has_same_public_semantics_but_wrong_saved_roles=True,
            not_a_complete_machine_state_matching_claim=True)

    def test_12_two_missing_words_are_the_actual_velocity_branch_delay_slots(self):
        measurements = []
        for kind, store in ((0, 0xE7A60124), (1, 0xE7A80124)):
            self.assertEqual(self.retail.count(store), 1)
            self.assertEqual(self.words.count(store), 1)
            retail_index, candidate_index = self.retail.index(store), self.words.index(store)
            self.assertEqual(self.retail[retail_index + 1] >> 16, 0x1000)
            self.assertEqual(self.retail[retail_index + 2], 0)
            self.assertEqual(self.words[candidate_index - 1] >> 16, 0x1000)
            original = ConsumerOracle(self.retail, fixture(1), kind=kind, outcome=2).run()
            candidate = ConsumerOracle(self.words, fixture(1), kind=kind, outcome=2).run()
            self.assertEqual(candidate.records, original.records)
            self.assertEqual(candidate.raw_packets, original.raw_packets)
            self.assertTrue(producer.complete_state(candidate) == producer.complete_state(original),
                ('Modeled return state differs', kind))
            measurements.append(dict(kind=kind, retail_store_word=retail_index,
                candidate_delay_store_word=candidate_index,
                retail_branch_delay_word=retail_index + 2))
        self.receipt('branch-delay-boundary', measurements=measurements,
            two_real_idle_delay_words_absent_from_candidate=True,
            no_instruction_insertion_guards_or_fake_padding=True,
            production_promotion_still_rejected=True)

    def test_13_delay_schedule_diagnostic_compares_every_remaining_word(self):
        diagnostic, sites = source.analyze_velocity_delay_schedule(self.words)
        differences = [index for index, (ours, retail) in enumerate(zip(diagnostic, self.retail))
            if ours != retail]
        self.assertEqual(len(diagnostic), 315)
        self.assertEqual(len(sites), 2)
        self.assertEqual(diagnostic, self.retail, 'Differences after diagnostic: %r' % differences)
        corrupted = list(self.words)
        corrupted[0] ^= 8
        changed, _ = source.analyze_velocity_delay_schedule(corrupted)
        self.assertNotEqual(changed, self.retail)
        corrupted = list(self.words)
        corrupted[self.words.index(0xE7A60124)] ^= 4
        with self.assertRaises(ValueError):
            source.analyze_velocity_delay_schedule(corrupted)
        meta, words = source.compile_candidate(self.root, self.out, 'existing-no-unroll-profile',
            profile='retail_no_unroll')
        self.assertEqual(words, self.words)
        self.assertEqual((meta['body_words'], meta['frame']), (313, 0x168))
        self.receipt('schedule-diagnostic', real_branch_sites=sites,
            inverse_two_filled_delay_pairs_and_internal_branch_rebases_match_all315_words=True,
            unrelated_instruction_and_wrong_store_controls_effective=True,
            existing_no_unroll_profile_does_not_recover_idle_slots=True,
            diagnostic_only_not_a_build_transform_or_matching_credit=True)


if __name__ == '__main__':
    unittest.main()
