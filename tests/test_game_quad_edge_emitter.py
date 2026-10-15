"""Whole quad-emitter semantics; explicitly reject the remaining layout mismatch."""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_emitter as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault, CallBoundary
from tools.tests.test_game_random_reload_timer_match import TimerOracle, DivideZeroTrap
from tools.tests.test_game_record_ring_shaping_recovery import ShapingOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests import test_game_small_record_factory as factory
from tools.tests import test_game_table_fade_match as archive

VERTICES, OTHER = 0x20000, 0x21000
TABLE = 0x8008CBF4
SAMPLES = ((0, 0, 0), (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF),
    (0x123456AB, 0x87654321, 0x80000001), (0x80000000, 0x7FFFFFFF, 0xFEDCBA98))


def rounded(value):
    return floating(bits(value))


def trunc(value):
    return math.trunc(value) & 0xFFFFFFFF if math.isfinite(value) and -2**31 <= value < 2**31 else 0x80000000


def short(value):
    return ((value + 0x8000) & 0xFFFF) - 0x8000


def divide(left, right):
    if right:
        return rounded(left / right)
    return math.nan if left == 0 else math.copysign(math.inf, left * math.copysign(1, right))


def fixture(table, kind=0, counts=(2, 3), scale=1.0, phase=0, pattern=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    for base in (VERTICES, OTHER):
        memory.update({base + i: 0xA5 for i in range(-16, 80)})
    points = ((-35.25, 10.5, 42.75), (63.5, -22.25, 19.5),
        (91.0, 31.0, -74.5), (-47.5, 18.25, -33.0))
    for i, xyz in enumerate(points):
        for j, value in enumerate(xyz):
            value = value if pattern == 0 else -value * 19.0 if pattern == 1 else value * 1024.0
            put(memory, VERTICES + i * 12 + j * 4, bits(value))
            put(memory, OTHER + i * 12 + j * 4, bits(value + 123.25))
    memory.update({TABLE + i: value for i, value in enumerate(table)})
    put(memory, source.SCALE, bits(731.0))
    args = (VERTICES, bits(12.25), bits(-3.75), 0xABCD0081, bits(scale), kind,
        counts[0] & 0xFFFFFFFF, counts[1] & 0xFFFFFFFF, 0xFEDCBA80, 0x87654321)
    return memory, args


def effects(role, number, incoming, args, mode):
    if mode == 1 and role == 'random' and number == 1:
        return ((args[0], bits(256.5), 4), (args[0] + 16, bits(-1024.25), 4))
    if mode == 2 and role == 'factory' and number == 1:
        return ((source.SCALE, bits(513.0), 4), (TABLE + 24, 0x01020304, 4))
    if mode == 3 and role == 'random' and number == 3:
        return ((incoming, OTHER, 4), (incoming + 4, bits(-91.5), 4),
            (incoming + 8, bits(123.75), 4), (incoming + 12, 0x123456A5, 4),
            (incoming + 16, bits(5.0), 4), (incoming + 20, 2, 4),
            (incoming + 24, 3, 4), (incoming + 28, 2, 4),
            (incoming + 32, 0xFFFFFFFE, 4), (incoming + 36, 0x12345678, 4))
    return ()


def packet(position, color, fixed, mode, extent, delay, lifetime, flags, context):
    p = [0] * 31
    for i, value in enumerate(position):
        p[i] = short(trunc(value)) & 0xFFFFFFFF
    for i, value in ((3, 13), (5, color[0]), (6, color[1]), (7, color[2]),
            (12, 2), (13, fixed[0] >> 8 & 255), (14, fixed[0] & 255),
            (15, fixed[1] >> 8 & 255), (16, fixed[1] & 255), (19, mode),
            (23, short(extent)), (24, short(extent)), (25, delay),
            (26, lifetime), (29, flags & 255), (30, context)):
        p[i] = value & 0xFFFFFFFF
    return tuple(p)


def reference(memory, args, randoms=SAMPLES[0], phase=0, mode=0):
    memory, incoming, calls, packets = dict(memory), STACK + phase, [], []
    current = args[0]
    homes = list(args)
    scale = floating(args[4])
    ranges = [floating(read(memory, TABLE + 12 + i * 4)) for i in range(3)]
    colors = [read(memory, TABLE + 24 + i, 1) for i in range(9)]
    limit = trunc(rounded(ranges[homes[5]] * scale))
    random_count = factory_count = 0

    def mutate(role, number):
        for address, value, size in effects(role, number, incoming, args, mode):
            put(memory, address, value, size)
            if incoming <= address < incoming + 40:
                homes[(address - incoming) // 4] = value

    def draw():
        nonlocal random_count
        calls.append((source.RANDOM,))
        value = randoms[random_count % 3]
        random_count += 1
        mutate('random', random_count)
        return value

    for edge in range(4):
        next_vertex = homes[0] + ((edge + 1) % 4) * 12
        count = signed(homes[6 if edge % 2 == 0 else 7])
        color = colors[homes[5] * 3:homes[5] * 3 + 3]
        fixed = []
        for axis, origin in ((0, homes[1]), (8, homes[2])):
            middle = rounded(rounded(floating(read(memory, next_vertex + axis)) + floating(read(memory, current + axis))) * 0.5)
            delta = rounded(middle - floating(origin))
            fixed.append(trunc(rounded(delta + delta)))
        if count > 0:
            color_mode = homes[3] & 255
            base = trunc(rounded(floating(read(memory, source.SCALE)) * scale))
            width = trunc(rounded(836.0 * scale))
            lifetime = trunc(rounded(143.0 * scale))
            inverse = divide(1.0, rounded(float(count - 1)))
            for index in range(count):
                fraction = rounded(rounded(float(index)) * inverse)
                position = []
                for axis in (0, 4, 8):
                    start = floating(read(memory, current + axis))
                    delta = rounded(floating(read(memory, next_vertex + axis)) - start)
                    position.append(rounded(rounded(delta * fraction) + start))
                delay = (draw() & 31) + 15
                value = draw()
                if not width:
                    return memory, calls, packets, True
                extent = (value % width + base) & 0xFFFFFFFF
                value = draw()
                if not limit:
                    return memory, calls, packets, True
                duration = (value % limit + lifetime) & 0xFFFFFFFF
                p = packet(position, color, fixed, color_mode, extent, delay, duration, homes[8], homes[9])
                packets.append(p)
                calls.append((source.FACTORY, *p))
                factory_count += 1
                mutate('factory', factory_count)
        current += 12
    return memory, calls, packets, False


class EdgeOracle(MaskOracle, TimerOracle, ShapingOracle):
    def __init__(self, words, memory, args, randoms=SAMPLES[0], phase=0, mode=0,
            fault=None, connected=None, entry=source.ENTRY, stop_entry=False, allocation_fail=False):
        self.own_instruction, self.accesses, self.fault = False, 0, fault
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=args, connected=connected)
        self.fcsr = self.initial_fcsr = self.hi = self.lo = 0
        self.input_args, self.incoming, self.phase = args, STACK + phase, phase
        self.randoms, self.random_count, self.factory_count, self.mode = randoms, 0, 0, mode
        self.symbols, self.callbacks, self.packets = {}, [], []
        self.stop_entry, self.allocation_fail = stop_entry, allocation_fail

    def record_call(self, target):
        if target == source.ENTRY:
            self.entry_args = self.arguments(10)
            if self.stop_entry:
                raise CallBoundary
            self.incoming, self.input_args = self.r[29], self.entry_args
            return
        if target == source.RANDOM:
            args = ()
        elif target == source.FACTORY:
            args = self.arguments(31)
            self.factory_count += 1
            self.packets.append(args)
        else:
            counts = {0x15167A68: 6, factory.HEAP: 5, factory.REGISTER: 2}
            args = self.arguments(counts[target])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == source.RANDOM:
            value = self.randoms[self.random_count % 3]
            self.random_count += 1
            role, number = 'random', self.random_count
        elif target == source.FACTORY:
            value, role, number = 0xABCD0000 + self.factory_count, 'factory', self.factory_count
        else:
            value, role, number = 0, 'lower', 0
            record = 0x30000 + (self.factory_count - 1) * 80
            if target == factory.HEAP:
                value = 0 if self.allocation_fail and self.factory_count % 3 == 0 else record
            elif target == factory.REGISTER:
                self.put(self.r[4], self.r[5], 1)
            else:
                raise AssertionError(('unexpected opaque allocator', hex(target)))
        for address, data, size in effects(role, number, self.incoming, self.input_args, self.mode):
            self.put(address, data, size)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value


def public(memory):
    return {a: value for a, value in memory.items() if not STACK - 2048 <= a < STACK + 768}


def state(model):
    return model.memory, model.r, model.f, model.hi, model.lo, model.events, model.calls, model.accesses


def controls():
    return {
        'wrong-count-pair': source.SELECTED.replace('edge == 0 || edge == 2', 'edge == 0 || edge == 1'),
        'wrong-stride': source.SELECTED.replace('nextIndex * 12', 'nextIndex * 4'),
        'integer-table': source.SELECTED.replace('ranges.values[kind] * scale', '*(s32 *)&ranges.values[kind] * scale'),
        'integer-vertices': source.SELECTED.replace('startX = current[0];', 'startX = *(s32 *)current;'),
        'signed-modulo': source.SELECTED.replace('(u32)func_150ADA20() % (u32)width', 'func_150ADA20() % width'),
        'missing-endpoint': source.SELECTED.replace('(f32)((&count)[0] - 1)', '(f32)(&count)[0]'),
        'wide-color': source.SELECTED.replace('color[0], color[1], color[2]', '*(u16 *)color, *(u16 *)(color + 1), *(u16 *)(color + 2)'),
        'cached-vertices': source.SELECTED.replace('startX = current[0];', 'startX = vertices[0];'),
        'wrong-lifetime': source.SELECTED.replace('143.0f * scale', '144.0f * scale'),
    }


class QuadEdgeEmitterTests(unittest.TestCase):
    test_10_all_original_801_archive_fingerprints = archive.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>266I', cls.rom, source.ROM))
        cls.table = cls.rom[0x2316B4:0x2316B4 + 33]

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_scope_neighbors_and_strict_rejection(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['diagnostics'], self.row['pool_bytes']), (266, 416, 149, '', 0))
        self.assertEqual(len(source.PATHS), 62)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        with self.assertRaisesRegex(ValueError, 'not a direct match'):
            source.qualify(self.root, self.out)
        for count, frame, difference, diagnostic, pool in ((265, 400, 0, '', 0), (266, 416, 0, '', 0),
                (266, 400, 1, '', 0), (266, 400, 0, 'warning', 0), (266, 400, 0, '', 48)):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, frame=frame, differences=difference, diagnostics=diagnostic, pool_bytes=pool))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        obj, diagnostics = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(obj), parse_object(self.obj)
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(a - f['value'], r) for a, r in o[2].items() if f['value'] <= a < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        path = self.out / 'unqualified-padded.s'
        path.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
            filename=source.OWNER, word_patches_path=self.out / 'before-guards'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        data, functions = source.build.link_owner(self.root, self.out, path.with_suffix('.o'), source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(f['size'], 1064)
        self.assertEqual(list(struct.unpack_from('>266I', data, f['value'])), self.words)
        self.receipt('shape', **{k: v for k, v in self.row.items() if k != 'different_words'}, neighbors_unchanged=29,
            actual_padder_fits_but_all_149_differences_remain=True,
            installation_rejected=True, no_target_guards_or_profile_changes=True)

    def test_02_complete_public_packets_four_edges_and_live_inputs(self):
        count, private_different, visits = 0, 0, set()
        for kind in range(3):
            for counts in ((0, 0), (-1, 2), (2, -1), (1, 1), (2, 3), (4, 7)):
                for scale in (0.25, 1.0, 2.0, -0.5):
                    for randoms in SAMPLES:
                        for phase in (0, 8):
                            for mode in range(4):
                                memory, args = fixture(self.table, kind, counts, scale, phase, pattern=kind)
                                expected_memory, calls, packets, trapped = reference(memory, args, randoms, phase, mode)
                                self.assertFalse(trapped)
                                models = [EdgeOracle(w, memory, args, randoms, phase, mode).run() for w in (self.truth, self.words)]
                                for model in models:
                                    self.assertEqual(model.calls, calls, (kind, counts, scale, randoms, phase, mode))
                                    self.assertEqual(public(model.memory), public(expected_memory))
                                    self.assertEqual(model.packets, packets)
                                private_different += state(models[0]) != state(models[1])
                                visits |= models[0].visits
                                count += 1
        self.assertTrue(private_different)
        reachable = set(range(source.ENTRY, source.ENTRY + 1064, 4)) - {0x1517038C, 0x15170488}
        self.assertEqual(visits, reachable)
        self.receipt('public', paired_cases=count, all_31_fields=True, whole_four_edges=True,
            every_non_break_word_visited=True, private_different=private_different,
            count_one_invalid_float_cast_is_guest_only=True, physical_home_mutations_not_native_C=True)

    def test_03_both_zero_divisor_traps_and_empty_path(self):
        count = 0
        for phase in (0, 8):
            for counts in ((0, 0), (2, 2)):
                for scale in (0.0, 0.001):
                    memory, args = fixture(self.table, counts=counts, scale=scale, phase=phase)
                    _, calls, _, trapped = reference(memory, args, SAMPLES[2], phase)
                    for words in (self.truth, self.words):
                        model = EdgeOracle(words, memory, args, SAMPLES[2], phase)
                        if trapped:
                            with self.assertRaises(DivideZeroTrap):
                                model.run()
                            self.assertEqual(model.calls, calls)
                        else:
                            model.run()
                            self.assertEqual(model.calls, [])
                    count += 1
        self.receipt('traps', paired_cases=count, both_BREAK7_locations=True,
            scale_zero_and_small_scale_distinguished=True, empty_edges_skip_rng_and_integer_division=True,
            no_native_zero_divisor_or_hardware_exception_claim=True)

    def test_04_effective_compiled_semantic_controls(self):
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '', name)
            mismatch = False
            for kind in range(3):
                memory, args = fixture(self.table, kind, counts=(2, 3))
                wanted = reference(memory, args, SAMPLES[1])[1]
                model = EdgeOracle(words, memory, args, SAMPLES[1])
                try:
                    model.run()
                except AssertionError:
                    self.assertEqual(name, 'wide-color')
                    mismatch = True
                else:
                    mismatch |= model.calls != wanted
            self.assertTrue(mismatch, name)
            effective.append(name)
        self.receipt('controls', effective_compiled_guest_negatives=effective,
            wide_color_alignment_fault_is_guest_only=True)

    def test_05_all_inputs_and_capture_corruptions_fail_closed(self):
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        target = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner((self.out / 'before-preset_owner').read_text()))
        self.receipt('preserved', all_62_production_inputs_unchanged=True, all_62_before_flips_rejected=True,
            manifest_and_placeholder_controls=True, no_production_installation=True)

    def test_06_native32_valid_conversion_domain_O2_O0_and_controls(self):
        prototype = source.build.body((self.out / 'before-preset_owner').read_text(), 'func_1516D4E8').split('{', 1)[0]
        capture = ','.join('arg%d' % i for i in range(31))
        harness = r'''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef float f32;
DECLARATIONS
FloatTable3_19A8B0 D_8008CBF4={{143.0f,30.0f,30.0f}};
FloatTable3_19A8B0 D_8008CC00={{571.0f,130.0f,130.0f}};
ByteTable9_19A8B0 D_8008CC0C={{134,106,60,200,190,180,255,210,128}};
f32 D_800A6E84;
static f32 vertices[12],expectedVertices[12];static u32 samples[3],mode,randomCount,packetCount;
static u32 captured[64][31],wanted[64][31],wantedCount,order[256],orderCount;
static __attribute__((noinline,noclone)) f32 rounded(f32 value){volatile f32 v=value;return v;}
static __attribute__((noinline,noclone)) s32 func_150ADA20(void){u32 v=samples[randomCount%3];
 order[orderCount++]=1;randomCount++;if(mode==1&&randomCount==1){vertices[0]=256.5f;vertices[4]=-1024.25f;}return(s32)v;}
FACTORY
BODY
static void (*volatile invoke)(f32*,f32,f32,u8,f32,s32,s32,s32,u8,s32)=func_151700D8;
static int check(u32 kind,s32 countX,s32 countZ,f32 scale,u32 seed,u32 provider){
 static const f32 points[12]={-35.25f,10.5f,42.75f,63.5f,-22.25f,19.5f,91.0f,31.0f,-74.5f,-47.5f,18.25f,-33.0f};
 static const u8 colors[9]={134,106,60,200,190,180,255,210,128};static const f32 ranges[3]={571.0f,130.0f,130.0f};
 u32 i,j,edge,index,draws=0,limit=(u32)(s32)rounded(ranges[kind]*scale),base,width,life,fixed[2],first,last;
 s32 count;f32 inverse,fraction,position[3],start,delta,middle;u32 *p;
 for(i=0;i<12;i++)vertices[i]=expectedVertices[i]=points[i];
 for(i=0;i<9;i++)D_8008CC0C.values[i]=colors[i];D_800A6E84=731.0f;
 samples[0]=seed*1664525u+1013904223u;samples[1]=seed*1103515245u+12345u;samples[2]=~samples[0];
 wantedCount=0;
 for(edge=0;edge<4;edge++){
  count=(edge&1)?countZ:countX;last=((edge+1)%4)*3;first=edge*3;
  middle=rounded(rounded(expectedVertices[last]+expectedVertices[first])*0.5f);
  delta=rounded(middle-12.25f);fixed[0]=(u32)(s32)rounded(delta+delta);
  middle=rounded(rounded(expectedVertices[last+2]+expectedVertices[first+2])*0.5f);
  delta=rounded(middle+3.75f);fixed[1]=(u32)(s32)rounded(delta+delta);
  if(count<=0)continue;
  base=(u32)(s32)rounded((provider==2&&wantedCount?513.0f:731.0f)*scale);
  width=(u32)(s32)rounded(836.0f*scale);life=(u32)(s32)rounded(143.0f*scale);
  inverse=rounded(1.0f/rounded((f32)(count-1)));
  for(index=0;index<(u32)count;index++){
   fraction=rounded(rounded((f32)index)*inverse);
   for(j=0;j<3;j++){start=expectedVertices[first+j];delta=rounded(expectedVertices[last+j]-start);
    position[j]=rounded(rounded(delta*fraction)+start);}
   if(provider==1&&draws==0){expectedVertices[0]=256.5f;expectedVertices[4]=-1024.25f;}
   p=wanted[wantedCount++];for(i=0;i<31;i++)p[i]=0;
   for(i=0;i<3;i++)p[i]=(u32)(s32)(s16)(s32)position[i];p[3]=13;
   for(i=0;i<3;i++)p[i+5]=colors[kind*3+i];p[12]=2;
   p[13]=fixed[0]>>8&255;p[14]=fixed[0]&255;p[15]=fixed[1]>>8&255;p[16]=fixed[1]&255;p[19]=129;
   p[23]=p[24]=(u32)(s32)(s16)(samples[1]%width+base);p[25]=(samples[0]&31)+15;
   p[26]=(u32)(s32)(s16)(samples[2]%limit+life);p[29]=128;p[30]=0x87654321u;draws+=3;
  }
 }
 mode=provider;randomCount=packetCount=orderCount=0;
 invoke(vertices,12.25f,-3.75f,129,scale,(s32)kind,countX,countZ,128,(s32)0x87654321u);
 if(packetCount!=wantedCount||randomCount!=draws||orderCount!=wantedCount*4)return 10;
 for(i=0;i<orderCount;i++)if(order[i]!=(i%4==3?2u:1u))return 11;
 for(i=0;i<packetCount;i++)for(j=0;j<31;j++)if(captured[i][j]!=wanted[i][j])return 12;
 for(i=0;i<12;i++)if(vertices[i]!=expectedVertices[i])return 13;
 if(D_800A6E84!=(provider==2&&wantedCount?513.0f:731.0f))return 14;return 0;}
static int run(void){static const s32 counts[5]={-1,0,2,3,7};static const f32 scales[4]={-0.5f,0.25f,1.0f,64.0f};
 u32 kind,a,b,s,seed,m;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 15;
 for(kind=0;kind<3;kind++)for(a=0;a<5;a++)for(b=0;b<5;b++)for(s=0;s<4;s++)for(seed=0;seed<4;seed++)for(m=0;m<3;m++){
 r=check(kind,counts[a],counts[b],scales[s],seed,m);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        factory_body = prototype + '{u32 v[31]={' + capture + '''};u32 i;
 order[orderCount++]=2;for(i=0;i<31;i++)captured[packetCount][i]=v[i];packetCount++;
 if(mode==2&&packetCount==1){D_800A6E84=513.0f;D_8008CC0C.values[0]=1;}}
'''
        negatives = {name: body for name, body in controls().items() if name not in ('integer-table', 'integer-vertices', 'wide-color')}
        exits = {}
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in negatives.items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('DECLARATIONS', source.DECLARATIONS).replace('FACTORY', factory_body).replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation', '-Wno-unused-variable']
            if ok:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertIn(result.returncode, (0,) if ok else (10, 11, 12, 13, 14), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=3600, all_31_formally_projected_fields=True,
            four_edge_counts_and_live_vertices_and_global_scale=True, UBSan_selected=True,
            six_effective_native_controls=exits, count_one_and_zero_divisor_invalid_conversions_guest_only=True,
            intentionally_unused_first_table_copy_warning_only=True)

    def test_07_original_fault_prefixes_and_candidate_difference_boundary(self):
        faults, divergent, paired, retail_only, candidate_only = 0, 0, 0, 0, 0
        for phase in (0, 8):
            for counts in ((0, 0), (2, 3)):
                memory, args = fixture(self.table, counts=counts, phase=phase)
                wholes = [EdgeOracle(w, memory, args, SAMPLES[2], phase).run() for w in (self.truth, self.words)]
                for fault in range(max(m.accesses for m in wholes)):
                    models = [EdgeOracle(w, memory, args, SAMPLES[2], phase, fault=fault) for w in (self.truth, self.words)]
                    fired = []
                    for model, whole in zip(models, wholes):
                        fired.append(fault < whole.accesses)
                        if fired[-1]:
                            with self.assertRaises(AccessFault):
                                model.run()
                            faults += 1
                        else:
                            model.run()
                    if all(fired):
                        divergent += state(models[0]) != state(models[1])
                        paired += 1
                    else:
                        retail_only += fired[0]
                        candidate_only += fired[1]
        self.assertGreater(divergent, 0)
        self.receipt('prefixes', fired_memory_cuts=faults, paired_cuts=paired,
            private_divergent=divergent, retail_only_cuts=retail_only, candidate_only_cuts=candidate_only,
            not_claimed_literal_fault_equivalence=True)

    def test_08_original_caller_windows_and_wrapper_ABI(self):
        jal = struct.pack('>I', 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF))
        references = [i for i in range(0, len(self.rom) - 3, 4) if self.rom[i:i + 4] == jal]
        self.assertEqual(references, [0x9B730, 0x9B8D8, 0x19ED88])
        cases = 0
        for entry, rom, words, scale_factor, color, vertex_offset in (
                (0x1506E240, 0x9B6F0, 18, 1.0, 4, 0x94),
                (0x1506E3DC, 0x9B88C, 21, 0.5, 5, 0x84)):
            window = list(struct.unpack_from('>%dI' % words, self.rom, rom))
            for scale in (0.5, 1.0, 2.0):
                memory, args = fixture(self.table, scale=scale)
                pointer, actor = 0x800D154C, 0x24000
                put(memory, pointer, actor)
                put(memory, actor + 0x14, bits(32.5))
                put(memory, actor + 0x1C, bits(-91.25))
                put(memory, actor + 0x14C, bits(scale))
                model = EdgeOracle(window, memory, args, entry=entry, stop_entry=True)
                model.r[30] = pointer
                with self.assertRaises(CallBoundary):
                    model.run()
                self.assertEqual(model.entry_args, (STACK + vertex_offset, bits(32.5), bits(-91.25), color,
                    bits(rounded(scale * scale_factor)), 0, 4, 4, 255, 0))
                cases += 1
        entry, rom, size = 0x151717FC, 0x19ECAC, 61
        wrapper = list(struct.unpack_from('>61I', self.rom, rom))
        memory, _ = fixture(self.table)
        actor = 0x24000
        for offset, value in ((0x10, -123), (0x12, 45), (0x14, 321)):
            put(memory, actor + offset, value, 2)
        args = (actor, bits(10.0), bits(20.0), bits(0.5), bits(-1.25), bits(3.5),
            2, 0xFFFFFF85, 2, 3, bits(0.5), 0xABCD0080, 0x12345678)
        model = EdgeOracle(wrapper, memory, args, entry=entry, stop_entry=True)
        with self.assertRaises(CallBoundary):
            model.run()
        self.assertEqual(model.entry_args, (STACK - 0x30, bits(-122.5), bits(324.5), 0xFFFFFF85,
            bits(0.5), 2, 2, 3, 128, 0x12345678))
        expected = ((-112.5, 43.75, 344.5), (-132.5, 43.75, 344.5),
            (-132.5, 43.75, 304.5), (-112.5, 43.75, 304.5))
        for i, xyz in enumerate(expected):
            self.assertEqual(tuple(read(model.memory, STACK - 0x30 + i * 12 + j * 4) for j in range(3)), tuple(map(bits, xyz)))
        self.receipt('callers', bounded_original_windows=cases, full_original_wrapper_words=size,
            every_aligned_JAL_in_prepared_image=references,
            actual_10_argument_interface=True, wrapper_13_inputs_and_quad=True,
            current_callers_are_not_restored_or_claimed_complete=True)

    def test_09_actual_current_factory_allocator_and_record_fields(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for address, rom, size in ((source.FACTORY, 0x19A998, 100), (0x15167A68, 0x194F18, 28)):
            offset = elf_slot_offset(image, address, size * 4)
            data = image[offset:offset + size * 4]
            self.assertEqual(data, self.rom[rom:rom + size * 4])
            connected.update(zip(range(address, address + size * 4, 4), struct.unpack('>%dI' % size, data)))
        cases = 0
        for kind in range(3):
            for counts in ((0, 0), (2, 3), (4, 2)):
                for failed in (False, True):
                    memory, args = fixture(self.table, kind, counts=counts)
                    memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(4096)})
                    expected_memory, _, packets, _ = reference(memory, args, SAMPLES[2])
                    for number, p in enumerate(packets, 1):
                        if failed and number % 3 == 0:
                            continue
                        record = 0x30000 + (number - 1) * 80
                        put(expected_memory, record, 18, 1)
                        put(expected_memory, record + 1, p[30], 1)
                        put(expected_memory, record + 12, p[29], 1)
                        for offset, index, width in factory.FIRST + factory.REST:
                            put(expected_memory, record + offset, p[index], width)
                        for offset, index, width in ((36, 25, 1), (24, 26, 2),
                                *((i + 25, i, 1) for i in range(13, 23))):
                            put(expected_memory, record + offset, p[index], width)
                        put(expected_memory, record + 37, 0, 1)
                        put(expected_memory, record + 48, 0)
                    models = [EdgeOracle(w, memory, args, SAMPLES[2], connected=connected, allocation_fail=failed).run()
                        for w in (self.truth, self.words)]
                    for model in models:
                        self.assertEqual(model.packets, packets)
                        self.assertEqual(public(model.memory), public(expected_memory))
                    self.assertEqual(public(models[0].memory), public(models[1].memory))
                    cases += 1
        self.receipt('factory', paired_cases=cases, actual_current_factory_allocator_words=128,
            every_packed_record_field_and_allocation_failure_checked=True,
            emitter_is_staged_not_installed=True, heap_registration_providers_opaque=True)

    def test_11_live_private_count_home_and_cached_control(self):
        call = 0x0C000000 | (source.FACTORY >> 2 & 0x3FFFFFF)

        def home(words):
            index = words.index(call) + 2
            for word in words[index:index + 5]:
                if word >> 26 in (5, 21):
                    break
                if word >> 26 == 35 and word >> 21 & 31 == 29:
                    return word & 65535
            return None

        homes = list(map(home, (self.truth, self.words)))
        self.assertEqual(homes, [0x138, 0x194])

        class CountWriter(EdgeOracle):
            def hook(model, target):
                super().hook(target)
                if target == source.FACTORY and model.factory_count == 1:
                    model.put(model.r[29] + model.count_home, 3, 4)

        memory, args = fixture(self.table, counts=(2, 2))
        expected = reference(memory, args, SAMPLES[2])[2]
        extra = list(expected[0])
        for axis in range(3):
            start = floating(read(memory, VERTICES + axis * 4))
            delta = rounded(floating(read(memory, VERTICES + 12 + axis * 4)) - start)
            extra[axis] = short(trunc(rounded(rounded(delta * 2.0) + start))) & 0xFFFFFFFF
        expected = expected[:2] + [tuple(extra)] + expected[2:]
        for words, count_home in zip((self.truth, self.words), homes):
            model = CountWriter(words, memory, args, SAMPLES[2])
            model.count_home = count_home
            model.run()
            self.assertEqual(model.packets, expected)
        _, cached, row = source.measure(self.root, self.out, 'cached-count', source.SELECTED.replace('(&count)[0]', 'count'))
        self.assertEqual((row['words'], row['frame'], row['differences']), (264, 416, 194))
        self.assertIsNone(home(cached))
        model = CountWriter(cached, memory, args, SAMPLES[2])
        model.count_home = homes[1]
        model.run()
        self.assertEqual(len(model.packets), 8)
        self.assertNotEqual(model.packets, expected)
        self.receipt('count-home', original_offset=homes[0], candidate_offset=homes[1],
            original_and_candidate_packets=9, cached_control_packets=8,
            reciprocal_snapshot_not_recomputed=True, guest_only_home_probe=True,
            private_addresses_still_differ=True)

    def test_12_independent_original_and_C_rebases(self):
        text, functions, relocations = parse_object(self.obj)
        symbols = dict(func_150ADA20=source.RANDOM, func_1516D4E8=source.FACTORY,
            D_8008CBF4=TABLE, D_8008CC00=TABLE + 12, D_8008CC0C=TABLE + 24, D_800A6E84=source.SCALE)
        emitted, missing = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        cases = 0
        for number, delta, table, scale in ((0, 0, TABLE, source.SCALE),
                (1, 0x10000, 0x80207FF4, 0x80318004), (2, -0x10000, 0x80418004, 0x80507FFC)):
            entry, random, factory_address = source.ENTRY + delta, source.RANDOM - delta, source.FACTORY - delta
            bindings = dict(func_150ADA20=random, func_1516D4E8=factory_address,
                D_8008CBF4=table, D_8008CC00=table + 12, D_8008CC0C=table + 24, D_800A6E84=scale)
            script = self.out / ('rebase-%d.ld' % number)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name in ('original', 'selected'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, number))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(elf),
                    str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>266I', sections(elf)['.text'][1])))
            if number == 0:
                self.assertEqual(bodies, [self.truth, self.words])
            with patch.multiple(source, ENTRY=entry, RANDOM=random, FACTORY=factory_address, SCALE=scale), patch(__name__ + '.TABLE', table):
                for kind in range(3):
                    for mode in range(4):
                        memory, args = fixture(self.table, kind, counts=(2, 3))
                        expected = reference(memory, args, SAMPLES[2], mode=mode)
                        models = [EdgeOracle(w, memory, args, SAMPLES[2], mode=mode, entry=entry).run() for w in bodies]
                        for model in models:
                            self.assertEqual(model.calls, expected[1])
                            self.assertEqual(model.packets, expected[2])
                            self.assertEqual(public(model.memory), public(expected[0]))
                        cases += 1
        self.receipt('rebases', independent_original_C_links=3, original_all_266_words_anchored=True,
            public_pairs=cases, all_four_calls_and_four_data_HI_LO_pairs=True,
            table_crosses_signed_low_boundary=True, C_still_not_a_literal_match=True)


if __name__ == '__main__':
    unittest.main()
