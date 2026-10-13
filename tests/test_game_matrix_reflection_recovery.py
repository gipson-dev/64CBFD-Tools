"""Qualify complete reflection semantics, separating private layout from matching."""
import hashlib
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_candidates as screen
from tools.tests import test_game_area_sampler_recovery as area
from tools.tests import test_game_record_matrix_update_match as matrices
from tools.tests import test_game_matrix_list_transform_match as unpack
from tools.tests import test_game_scaled_matrix_match as pack
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests import test_game_actor_renderer_install_match as native
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_actor_callback_frame_trace as observer
from tools.tests.test_game_actor_command_stream_match import AccessFault

STACK = area.STACK
ACTOR, RECORD, INPUT, OUTPUT, ALTERNATE, OTHER = 0x10000, 0x12000, 0x20000, 0x24000, 0x28000, 0x14000
WIDTHS = dict(guMtxIdentF=1, guMtxL2F=2, guMtxF2L2=2, bcopy=3,
    func_150A7A48=3, func_150A8050=4, func_150AD960=4, func_15034728=1)


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x800 <= a < STACK + 0x180}


def fixture(mode=0, count=2, fixed=0, alias=0, distance=5.0, enabled=1):
    memory = {STACK + i: 165 for i in range(-0x800, 0x180)}
    for base, size in ((ACTOR, 0x200), (OTHER, 0x200), (RECORD, 16),
            (INPUT, 320), (OUTPUT, 320), (ALTERNATE, 320)):
        memory.update({base + i: 165 for i in range(size)})
    put(memory, ACTOR + 0x9C, enabled)
    put(memory, ACTOR + 0x1D4, INPUT)
    put(memory, OTHER + 0x1D4, 0xABCDEFA0)
    for base in (INPUT, OUTPUT, ALTERNATE):
        for i in range(4):
            values = list(matrices.identity())
            values[0], values[5], values[10] = map(bits, (1.0 + i / 4, 0.5, 2.0))
            values[3], values[7], values[11], values[15] = map(bits, (7.0, 8.0, 9.0, 3.0))
            values[12:15] = map(bits, (i + 2.0, i + 5.0, i - 3.0))
            if base == INPUT and fixed & 1:
                payload = pack.fixed_payload(values)
                memory.update({base + i * 64 + j: b for j, b in enumerate(payload)})
            else:
                for j, value in enumerate(values):
                    put(memory, base + i * 64 + j * 4, value)
    output = (OUTPUT, INPUT, INPUT + 64)[alias]
    # Slot nine is intentionally unlike the angle: it exists even though unused.
    floats = (2.5, 1.5, -3.25, 1234.5, 0.0, -2.5, distance + 1.5,
        8.75, 20.0, 100.0, 200.0)
    args = (ACTOR, RECORD, mode & 0xFFFFFFFF, INPUT, output, count & 0xFFFFFFFF,
        *map(bits, floats), fixed & 1, fixed >> 1)
    return memory, args


class Helpers:
    """Existing bounded matrix models; not execution of the opaque SDK providers."""
    def __init__(self, memory, args, phase=0, distance=30, action=None):
        self.memory, self.args, self.phase = memory, args, phase
        self.distance, self.action = distance, action
        self.calls = []
        self.applied = False

    def words(self, address):
        return tuple(read(self.memory, address + i * 4) for i in range(16))

    def destination(self, address):
        return 'private-matrix' if STACK - 0x800 <= address < STACK else address

    def call(self, name, args):
        m = self.memory
        if name == 'guMtxIdentF':
            packet, destination = (), args[0]
            values = matrices.identity()
        elif name == 'func_150A8050':
            packet, destination = args[1:], args[0]
            values = matrices.rotation(args[1:])
        elif name == 'func_150A7A48':
            left, right = self.words(args[0]), self.words(args[1])
            packet, destination = (left, right, self.destination(args[2])), args[2]
            values = matrices.multiply(left, right)
        elif name == 'guMtxL2F':
            packet = (args[1], bytes(m[args[1] + i] for i in range(64)))
            unpack.convert(m, args[0], args[1])
            values, destination = self.words(args[0]), args[0]
        elif name == 'guMtxF2L2':
            packet = (self.words(args[0]), args[1])
            payload = pack.fixed_payload(packet[0])
            m.update({args[1] + i: b for i, b in enumerate(payload)})
            values = None
        elif name == 'bcopy':
            payload = bytes(m[args[0] + i] for i in range(args[2]))
            packet = (payload, self.destination(args[0]), self.destination(args[1]), args[2])
            m.update({args[1] + i: b for i, b in enumerate(payload)})
            values = None
        elif name == 'func_150AD960':
            packet = tuple(map(signed, args))
            values = None
        else:
            assert name == 'func_15034728'
            packet = (args[0], read(m, args[0] + 0x1D4))
            put(m, args[0] + 0x1D4, ALTERNATE)
            put(m, args[0] + 0x54, 0x12345678)
            values = None
        self.calls.append((name, packet))
        if values is not None:
            for i, value in enumerate(values):
                put(m, destination + i * 4, value)
        if self.action and not self.applied:
            kind, slot, value = self.action
            if name == kind:
                put(m, STACK + self.phase + slot * 4, value)
                self.applied = True
        return self.distance & 0xFFFFFFFF if name == 'func_150AD960' else 0


def reference(memory, args, phase=0, distance_result=30, action=None):
    memory = dict(memory)
    for i, value in enumerate(args):
        put(memory, STACK + phase + i * 4, value)
    helpers = Helpers(memory, args, phase, distance_result, action)
    scratch = STACK + phase - 0x190
    reflection, minus, plus, converted = (scratch + off for off in (0x150, 0x110, 0xD0, 0x84))
    helpers.call('guMtxIdentF', (reflection,))
    arg = lambda n: read(memory, STACK + phase + n * 4)
    flt = lambda n: floating(arg(n))
    mode = arg(2)
    if mode not in (0, 1, 2):
        return memory, helpers.calls
    put(memory, reflection + (20 if mode in (0, 1) else 0), bits(-1.0))
    if mode == 2:
        helpers.call('func_150A8050', (minus, 0, bits(-flt(10)), 0))
        helpers.call('func_150A8050', (plus, 0, arg(10), 0))
    source, cursor = arg(3), arg(4)
    input_fixed, output_fixed = arg(17), arg(18)
    index = 0
    if signed(arg(5)) > 0:
        while True:
            current = source + index * 64
            if input_fixed:
                helpers.call('guMtxL2F', (converted, current))
                current = converted
            else:
                for offset, value in ((12, 0), (28, 0), (44, 0), (60, bits(1.0))):
                    put(memory, current + offset, value)
            if mode in (0, 1):
                helpers.call('func_150A7A48', (current, reflection, cursor))
                value = floating(read(memory, current + 52))
                delta = matrices.rounded(value - flt(7))
                put(memory, cursor + 52, bits(matrices.rounded(value - matrices.rounded(delta + delta))))
            else:
                helpers.call('bcopy', (current, cursor, 64))
                for axis in range(3):
                    at = cursor + 48 + axis * 4
                    put(memory, at, bits(matrices.rounded(floating(read(memory, at)) - flt(6 + axis))))
                for matrix in (minus, reflection, plus):
                    helpers.call('func_150A7A48', (cursor, matrix, cursor))
                for axis in range(3):
                    at = cursor + 48 + axis * 4
                    put(memory, at, bits(matrices.rounded(floating(read(memory, at)) + flt(6 + axis))))
            if output_fixed:
                destination = arg(4) + index * 64
                helpers.call('bcopy', (destination, converted, 64))
                helpers.call('guMtxF2L2', (converted, destination))
            index += 1
            cursor += 64
            if index == arg(5):
                break
            assert index < 8, 'bounded reference count exceeded'
    if mode in (0, 1):
        distance = matrices.rounded(flt(12) - flt(7))
    else:
        result = helpers.call('func_150AD960', tuple(int(flt(n)) & 0xFFFFFFFF for n in (6, 8, 11, 13)))
        distance = matrices.rounded(float(signed(result)))
    near, far, opacity = flt(14), flt(15), flt(16)
    if far < distance:
        value = 0
    elif distance < near:
        value = matrices.rounded(matrices.rounded(opacity / 10.0) * distance) if mode == 0 and distance < 10 else opacity
    else:
        value = matrices.rounded(opacity - matrices.rounded(matrices.rounded(opacity * matrices.rounded(distance - near)) /
            matrices.rounded(far - near)))
    assert 0 <= value < 2**32, 'native-defined unsigned conversion domain'
    put(memory, arg(1) + 4, int(value), 1)
    actor = arg(0)
    if actor and read(memory, actor + 0x9C):
        saved = read(memory, actor + 0x1D4)
        put(memory, actor + 0x1D4, arg(4))
        helpers.call('func_15034728', (actor,))
        put(memory, arg(0) + 0x1D4, saved)
    return memory, helpers.calls


class ReflectionOracle(area.AreaOracle):
    def __init__(self, words, memory, args, phase=0, distance=30, action=None, entry=screen.ENTRY):
        super().__init__(words, memory, args, phase=phase, entry=entry)
        for i, value in enumerate(args):
            put(self.memory, STACK + phase + i * 4, value)
        self.helpers = Helpers(self.memory, args, phase, distance, action)
        self.raw_calls = []

    def record_call(self, target):
        assert self.fcsr == self.initial_fcsr
        self.active = next(name for name, address in screen.SYMBOLS.items() if address == target)
        self.active_args = self.arguments(WIDTHS[self.active])
        self.raw_calls.append((self.active, self.active_args))

    def hook(self, target):
        result = self.helpers.call(self.active, self.active_args)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class FaultOracle(ReflectionOracle):
    def __init__(self, *args, fault=None, **kwargs):
        self.own_instruction = False
        super().__init__(*args, **kwargs)
        self.fault, self.accesses = fault, 0

    def execute(self, word):
        self.dispatched_word = word
        self.own_instruction = True
        try:
            super().execute(word)
        finally:
            self.own_instruction = False

    def fired_access(self):
        if self.own_instruction:
            if self.fault == self.accesses:
                raise AccessFault
            self.accesses += 1

    def get(self, address, size):
        self.fired_access()
        return super().get(address, size)

    def put(self, address, value, size):
        self.fired_access()
        return super().put(address, value, size)


class GameMatrixReflectionRecoveryTests(unittest.TestCase):
    maxDiff = None
    run_native = native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-recovery-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', makefile='conker/Makefile', assembly='conker/asm/61D10.s', layout='conker/retail_layout.us.txt')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == '38ac5d5272b5800ff666bb1d284ccfa12409f3a25fa06b38068cd9d337973561'
        cls.body = screen.qualified_body()
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, phase=0, distance=30, action=None, words=None):
        expected, calls = reference(memory, args, phase, distance, action)
        pair = [ReflectionOracle(w, memory, args, phase, distance, action).run() for w in (self.retail, self.words if words is None else words)]
        for model in pair:
            self.assertEqual(public(model.memory), public(expected))
            self.assertEqual(model.helpers.calls, calls)
        if words is None:
            self.assertEqual(pair[0].memory, pair[1].memory)
        return pair

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (486, 400, 347, 0))
        self.assertNotEqual(self.words, self.retail)
        self.receipt('shape', words=486, frame=400, differences=347, matching_credit=0, production_installed=False)

    def test_02_complete_modes_flags_counts_falloff_and_callback(self):
        cases = 0
        for mode, count, fixed, distance, enabled, phase in itertools.product(
                (0, 1, 2, 3, -1), (-1, 0, 1, 2, 3), range(4), (0.0, 5.0, 10.0, 20.0, 21.0, 60.0, 100.0, 101.0), (0, 1, 256), (0, 8)):
            memory, args = fixture(mode, count, fixed, distance=distance, enabled=enabled)
            self.compare(memory, args, phase, int(distance))
            cases += 1
        self.receipt('guest', cases=cases, full_public_memory_and_helper_packets=True,
            full_sampled_private_RAM_equal=True, full_register_fault_state_not_qualified=True,
            hardware_and_provider_implementation_not_claimed=True)

    def test_03_in_place_and_cross_matrix_aliases(self):
        cases = 0
        for mode, fixed, alias, phase in itertools.product(range(3), range(4), (1, 2), (0, 8)):
            # Float-input/fixed-output cross-aliases change the next input's representation.
            count = 1 if fixed == 2 and alias == 2 else 2
            memory, args = fixture(mode, count, fixed, alias)
            self.compare(memory, args, phase)
            cases += 1
        self.receipt('aliases', cases=cases, input_output_overlap=True)

    def test_04_live_count_output_and_post_callback_actor_homes(self):
        records = []
        for mode, phase, action in itertools.product(range(3), (0, 8),
                (('func_150A7A48', 5, 1), ('func_150A7A48', 4, ALTERNATE), ('func_15034728', 0, OTHER))):
            memory, args = fixture(mode, 2, 2)
            pair = self.compare(memory, args, phase, action=action)
            self.assertTrue(all(model.helpers.applied for model in pair))
            records.append(dict(mode=mode, phase=phase, action=action))
        self.receipt('homes', cases=len(records), all_three_live_home_contracts=True)

    def test_05_all_seven_production_inputs_remain_unchanged(self):
        for name, path in self.paths.items():
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / path).read_bytes(), before, name)
        self.receipt('production', inputs=7, all_fixed=True, no_installation_or_matching_credit=True)

    def test_06_mixed_format_alias_keeps_the_original_provider_boundary(self):
        memory, args = fixture(0, 2, 2, 2)
        records = []
        for words in (self.retail, self.words):
            model = ReflectionOracle(words, memory, args)
            with self.assertRaises(AssertionError):
                model.run()
            self.assertEqual(model.active, 'guMtxF2L2')
            records.append(model)
        self.assertEqual(records[0].helpers.calls, records[1].helpers.calls)
        self.assertEqual(public(records[0].memory), public(records[1].memory))
        packets = [model.helpers.words(model.active_args[0]) for model in records]
        self.assertEqual(packets[0], packets[1])
        self.receipt('provider-boundary', both_reach_same_rejected_conversion=True,
            original_and_candidate_packet=[hex(v) for v in packets[0]],
            finite_exact_signed32_fixed_domain_only=True, final_mixed_format_result_unqualified=True)

    def native_source(self, body):
        records = []
        for mode, count, distance, enabled in itertools.product(range(4), (-1, 0, 1, 2),
                (0.0, 5.0, 10.0, 20.0, 21.0, 60.0, 100.0, 101.0), (0, 256)):
            memory, args = fixture(mode, count, 0, distance=distance, enabled=enabled)
            expected, calls = reference(memory, args, distance_result=int(distance))
            original = ReflectionOracle(self.retail, memory, args, distance=int(distance)).run()
            self.assertEqual((public(original.memory), original.helpers.calls), (public(expected), calls))
            arrays = []
            for mem, base in ((memory, INPUT), (memory, OUTPUT), (expected, INPUT), (expected, OUTPUT)):
                arrays.append('{' + ','.join('0x%XU' % read(mem, base + i * 4) for i in range(64)) + '}')
            records.append('{%d,%d,%d,%d,%d,0x%XU,{%s},%s}' % (mode, count, int(distance), enabled,
                read(expected, RECORD + 4, 1), read(expected, ACTOR + 0x54),
                ','.join('0x%XU' % v for v in args[6:17]), ','.join(arrays)))
        header = r'''
typedef unsigned char u8; typedef unsigned int u32; typedef int s32; typedef float f32;
typedef struct {u32 data[16];} Mtx;
typedef union {u32 u;f32 f;} Word;
static union {u32 align;u8 bytes[0x200];} actorStore;
static u8 record[16];static f32 input[4][4][4],output[4][4][4],alternate[4][4];
static s32 error,distanceResult;
static f32 asfloat(u32 value){Word w;w.u=value;return w.f;}
static u32 asbits(f32 value){Word w;w.f=value;return w.u;}
void guMtxIdentF(f32 m[4][4]){s32 i,j;for(i=0;i<4;i++)for(j=0;j<4;j++)m[i][j]=i==j;}
void guMtxL2F(f32 m[4][4],Mtx *p){error=20;}
void guMtxF2L2(f32 m[4][4],Mtx *p){error=21;}
void bcopy(const void *from,void *to,u32 size){u8 saved[64];u32 i;
 if(size!=64){error=22;return;}for(i=0;i<size;i++)saved[i]=((const u8 *)from)[i];
 for(i=0;i<size;i++)((u8 *)to)[i]=saved[i];}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){
 if(x!=0 || y!=0 || z!=0){error=23;}guMtxIdentF(m);
 if(asbits(y)&0x80000000U){m[1][0]=asfloat(0x80000000U);m[2][1]=asfloat(0x80000000U);}
 else{m[0][2]=asfloat(0x80000000U);}}
void func_150A7A48(f32 left[4][4],f32 right[4][4],f32 out[4][4]){
 f32 saved[4][4],v; s32 i,j,k;
 for(i=0;i<4;i++)for(j=0;j<4;j++){v=left[i][0]*right[0][j];
 for(k=1;k<4;k++){v=v+left[i][k]*right[k][j];}saved[i][j]=v;}
 for(i=0;i<4;i++)for(j=0;j<4;j++)out[i][j]=saved[i][j];}
s32 func_150AD960(s32 x,s32 z,s32 px,s32 pz){
 if(x!=2 || z!=-3 || px!=-2 || pz!=8){error=24;}return distanceResult;}
void func_15034728(u8 *actor){
 if(actor!=actorStore.bytes || *(void **)(actor+0x1D4)!=output)error=25;
 *(void **)(actor+0x1D4)=alternate;*(u32 *)(actor+0x54)=0x12345678;}
struct Case {s32 mode,count,distance,enabled;u32 alpha,marker,args[11],input[64],output[64],wantInput[64],wantOutput[64];};
static const struct Case cases[]={
'''
        runner = r'''
static int fail(u32 tag,u32 n,u32 i){u32 data[3]={tag,n,i};
 __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
int run(void){u32 n,i,j;const struct Case *v;f32 f[11];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){v=&cases[n];error=0;distanceResult=v->distance;
 for(i=0;i<0x200;i++){actorStore.bytes[i]=165;}for(i=0;i<16;i++){record[i]=165;}
 for(i=0;i<64;i++){((f32 *)input)[i]=asfloat(v->input[i]);((f32 *)output)[i]=asfloat(v->output[i]);}
 for(i=0;i<11;i++)f[i]=asfloat(v->args[i]);
 *(u32 *)(actorStore.bytes+0x9C)=v->enabled;*(void **)(actorStore.bytes+0x1D4)=input;
 func_15034F30(actorStore.bytes,record,v->mode,(u8 *)input,(u8 *)output,v->count,
 f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],f[9],f[10],0,0);
 if(error || record[4]!=v->alpha || *(u32 *)(actorStore.bytes+0x54)!=v->marker || *(void **)(actorStore.bytes+0x1D4)!=input)return fail(1,n,error);
 for(j=0;j<64;j++)if(asbits(((f32 *)input)[j])!=v->wantInput[j] || asbits(((f32 *)output)[j])!=v->wantOutput[j])return fail(2,n,j);
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        return header + ',\n'.join(records) + '\n};\n' + body + '\n' + runner

    def test_07_native32_actual_body_and_effective_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(self.body), profile)[0], 0)
        controls = {
            'wrong-ramp': self.body.replace('nearDistance = 10.0f;', 'nearDistance = 9.0f;'),
            'byte-gate': self.body.replace('*(u32 *)(actor + 0x9C)', 'actor[0x9F]'),
            'wrong-restore': self.body.replace('= saved;', '= saved + 4;'),
            'wrong-distance-slots': self.body.replace('(s32)pointX, (s32)pointZ', '(s32)pointZ, (s32)pointX'),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, self.body)
            self.assertNotEqual(self.run_native(name, self.native_source(body))[0], 0, name)
        self.receipt('native', cases_per_profile=256, profiles=['O2', 'O0'], effective_negatives=4,
            float_buffers_and_zero_angle_only=True, finite_unsigned_conversion_domain=True,
            full19_argument_slots=True, opaque_distance_and_callback_providers=True)

    def test_08_complete_owner_neighbors_pools_and_both_padders(self):
        before = (self.root / screen.SOURCE).read_text()
        after = screen.recovered_owner(before, self.body)
        objects = [compile_owner(self.root, self.out, owner, 'owner-' + name)
            for name, owner in (('before', before), ('after', after))]
        self.assertEqual(objects[0][1], objects[1][1])
        a, b = (parse_object(obj) for obj, _ in objects)
        names = set(a[1]) - {screen.FUNCTION}
        self.assertEqual(names, set(b[1]) - {screen.FUNCTION})
        for name in names:
            old, new = a[1][name], b[1][name]
            self.assertEqual(a[0][old['value']:old['value'] + old['size']], b[0][new['value']:new['value'] + new['size']], name)
            relocations = lambda obj, meta: {at - meta['value']: uses for at, uses in obj[2].items()
                if meta['value'] <= at < meta['value'] + meta['size']}
            self.assertEqual(relocations(a, old), relocations(b, new), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            assembly = self.out / (script + '.s')
            args = [str(objects[1][0]), str(self.root / 'conker/retail_layout.us.txt'), 'generated_61D10', str(assembly)] if script == 'pad_c_object.py' else [
                str(objects[1][0]), str(self.root / 'conker/asm/61D10.s'), str(assembly), '--filename', 'generated_61D10']
            result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                '--word-patches', str(self.root / self.paths['guards'])], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            obj = assembly.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(assembly)], check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'], 1944)
        self.receipt('owner', neighbors=len(names), full_owner_and_both_padders=True,
            pools_and_neighbor_relocations_fixed=True, production_guard_manifest_unchanged=True)

    def test_09_public_agreement_is_not_literal_private_frame_identity(self):
        memory, args = fixture(0, 1, 1)
        pair = self.compare(memory, args)
        calls = [next(args for name, args in model.raw_calls if name == 'guMtxL2F') for model in pair]
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(pair[0].memory, pair[1].memory)
        self.assertEqual(pair[0].f, pair[1].f)
        changed = [i for i in range(32) if pair[0].r[i] != pair[1].r[i]]
        self.assertEqual(changed, [9, 13])
        _, old_words = screen.compile_candidate(self.root, self.out, 'old-private-control',
            dict(screen.candidates())['do-count-o1-a0'])
        old = self.compare(memory, args, words=old_words)[1]
        old_calls = next(args for name, args in old.raw_calls if name == 'guMtxL2F')
        self.assertEqual(old_calls[0] - calls[0][0], 12)
        self.assertNotEqual(old.memory, pair[0].memory)
        self.receipt('private-boundary', conversion_destinations=[hex(args[0]) for args in calls],
            old_conversion_destination=hex(old_calls[0]), exact_sampled_RAM_and_FPRs=True,
            changed_return_GPRs=changed, full_state_identity=False,
            candidate_installed=False, matching_credit=0)

    def test_10_original_caller_windows_forward_all19_slots(self):
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        class WindowDone(Exception):
            pass
        class Window(area.AreaOracle):
            def record_call(self, target):
                assert target == screen.ENTRY
                self.forwarded = self.arguments(19)
                raise WindowDone
        floats = tuple(map(bits, (0.5, -1.5, 2.25, 4.5, 90.0, 8.0, 20.0, 180.0)))
        results = []
        for second, phase in itertools.product((False, True), (0, 8)):
            entry, end = (0x15035C68, 0x15035D24) if second else (0x15035A70, 0x15035AEC)
            words = list(struct.unpack_from('>%dI' % ((end - entry) // 4), rom, entry - 0x15000000 + 0x2D4B0))
            memory, _ = fixture(0, 2)
            for i, value in enumerate(floats):
                put(memory, STACK + phase + 0xE0 + i * 4, value)
            for i, value in enumerate(map(bits, (7.0, 8.0, 9.0))):
                put(memory, ACTOR + 0x14 + i * 4, value)
            put(memory, RECORD, OUTPUT)
            put(memory, STACK + phase + 0xD8, 2 if second else 1)
            put(memory, STACK + phase + 0xC0, INPUT)
            put(memory, OTHER + 3, 64, 1)
            put(memory, OTHER + 0x34, 1)
            put(memory, OTHER + 0x48, 0)
            model = Window(words, memory, (ACTOR, RECORD, 0, 0), phase=phase, entry=entry)
            model.r[20], model.r[17], model.r[18] = ACTOR, RECORD, 2
            if second:
                model.r[16], model.r[3], model.r[10] = OTHER, OUTPUT, 192
            with self.assertRaises(WindowDone):
                model.run()
            expected = (0 if second else ACTOR, RECORD, 2 if second else 1, INPUT, OUTPUT, 2,
                *floats[:5], *map(bits, (7.0, 8.0, 9.0)), *floats[5:7], bits(48.0) if second else floats[7],
                int(second), int(second))
            self.assertEqual(tuple(model.forwarded), expected)
            results.append(dict(entry=hex(entry), phase=phase, words=len(words), arguments=[hex(v) for v in expected]))
        self.receipt('callers', real_call_sites=2, windows=results, slots=19,
            caller_prefix_seeded=True, full_parent_body_not_qualified=True)

    def test_11_missing_unused_float_slot_is_an_effective_ABI_negative(self):
        body = self.body.replace('f32 unused,\n    f32 angle', 'f32 angle')
        self.assertNotEqual(body, self.body)
        _, words = screen.compile_candidate(self.root, self.out, 'negative-missing-slot9', body)
        memory, args = fixture(1, 0, enabled=0)
        good = ReflectionOracle(self.words, memory, args).run()
        bad = ReflectionOracle(words, memory, args).run()
        self.assertNotEqual(public(good.memory), public(bad.memory))
        self.receipt('ABI-negative', missing_slot9_compiled=True,
            actual_public_result_changes=True, m2c_omission_not_copied=True)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        forms = list(screen.layout_candidates())
        self.assertEqual(len(forms), 56)
        for name, body in forms:
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            self.assertEqual((meta['body_words'], meta['frame']), (486, 400), name)
            self.assertEqual(words, self.words, name)
        self.receipt('layouts', complete_forms=56, literal_arrays=1,
            three_existing_locals_restore_private_matrix_address=True, arbitrary_padding_not_added=True)

    def test_13_owned_frame_capture_keeps_original_extent_and_object_identity(self):
        adapter = SimpleNamespace(SELECTED=self.body, compile_candidate=screen.compile_candidate)
        with patch.object(observer, 'screen', adapter):
            record = observer.trace(self.root, self.out, 'frame-selected', self.body)
        self.assertTrue(record['code_unchanged'])
        events = [e for e in record['events'] if e['event'] == 'frame-write']
        self.assertEqual([e['frame'] for e in events], [88, 104, 400])
        self.assertEqual((events[-1]['locals'], events[-1]['saved'], events[-1]['outgoing']), (296, 88, 16))
        definitions = {r['storage']: r['length'] for r in record['records']['optimizer'] if r['name'] == 'def'}
        self.assertEqual(definitions, dict(M=292, P=76))
        offsets = sorted({r['offset'] for r in record['records']['optimizer'] if r['storage'] == 'M' and r.get('offset') is not None})
        self.assertTrue({-268, -192, -128, -64}.issubset(offsets))
        self.receipt('frame', frame=400, locals=296, saved=88, outgoing=16, M_definition=292,
            parameter_bytes=76, matrix_offsets=[-268, -192, -128, -64],
            fired_capture=True, normal_traced_object_and_pools_identical=True)

    def test_14_independent_original_links_and_rebased_semantic_contract(self):
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + screen.FUNCTION + '\n', 1)[1]
        assembly = self.out / 'original.s'
        assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + screen.FUNCTION + '\n' + original.split('endlabel ' + screen.FUNCTION, 1)[0] +
            'endlabel ' + screen.FUNCTION + '\n')
        obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(assembly)], check=True, capture_output=True)
        cases = 0
        for index, delta in enumerate((0, 0x200000, 0x400000)):
            entry = screen.ENTRY + delta
            symbols = {name: value + delta for name, value in screen.SYMBOLS.items()}
            with patch.multiple(screen, ENTRY=entry, SYMBOLS=symbols):
                _, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(index), self.body)
                script = self.out / ('original-' + str(index) + '.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
                retail = list(struct.unpack_from('>486I', screen.compiler.sections(elf)['.text'][1]))
                if index == 0:
                    self.assertEqual(retail, self.retail)
                    self.assertEqual(candidate, self.words)
                self.assertNotEqual(retail, candidate)
                for mode, fixed, count, phase in itertools.product(range(3), range(4), (0, 1, 2), (0, 8)):
                    memory, args = fixture(mode, count, fixed)
                    expected, calls = reference(memory, args, phase)
                    for words in (retail, candidate):
                        model = ReflectionOracle(words, memory, args, phase, entry=entry).run()
                        self.assertEqual((public(model.memory), model.helpers.calls), (public(expected), calls))
                    cases += 1
        self.receipt('rebases', independently_assembled_original_links=3, cases=cases,
            matched=False, full_semantic_helper_packets=True, code_and_helper_relocations=True)

    def test_15_literal_fired_fault_prefix_retains_saved_role_boundary(self):
        records = []
        for phase in (0, 8):
            memory, args = fixture(0, 1, 1)
            for cut in (0, 1):
                pair = []
                for words in (self.retail, self.words):
                    model = FaultOracle(words, memory, args, phase=phase, fault=cut)
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    self.assertIn(model.dispatched_word >> 26, (35, 43, 49, 53, 57, 61))
                    pair.append(model)
                states = [(model.memory, model.r, model.f, model.fcsr, model.events) for model in pair]
                self.assertEqual(states[0] == states[1], cut == 0)
                if cut == 1:
                    self.assertNotEqual(pair[0].memory, pair[1].memory)
                records.append(dict(phase=phase, cut=cut, states_equal=states[0] == states[1],
                    words=[hex(model.dispatched_word) for model in pair]))
        self.receipt('fault-boundary', fired_pairs=4, records=records,
            first_memory_state_difference=1, source_saved_role_schedule_unmatched=True,
            hardware_PC_BD_FCSR_not_qualified=True)


if __name__ == '__main__':
    unittest.main()
