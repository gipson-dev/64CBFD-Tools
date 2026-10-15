"""Frustum float-call ABI, phase homes, side-plane stores and closed image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_frustum_plane_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.check_game_data_layout import audit_layout
from tools.tests import view_frustum_plane_checkpoint as checkpoint
from tools.tests import game_sine_checkpoint
from tools.tests import view_fov_transfer_checkpoint

COS, SIN, BASE, SCALE_H, SCALE_V = 0x15047C00, 0x15047D60, 0x800BE628, 0x80096900, 0x80096904
VIEWS, ALTERNATE = 0x24000, 0x28000
ANGLES = ((0, 0), (0x80000000, 0), (bits(30.0), bits(60.0)), (bits(-90.0), bits(120.0)),
    (bits(179.0), bits(-45.0)), (0x7F7FFFFF, bits(1.0)), (1, 0x80000001), (bits(0.25), bits(0.125)))
RETURNS = (0, 0x80000000, 0x3F3504F3, 0xBF3504F3, 0x7F7FFFFF, 0x7F800000, 0x7FC12345, 0x7F812345)


def mul(left, right):
    return bits(floating(left) * floating(right))


def fixture(index, x, y, alias, phase):
    frame = machine.STACK + phase - 0x40
    view = (VIEWS, SCALE_H - 0x88, BASE - 0x88)[alias]
    table = (view - ((index * 0x180) & 0xFFFFFFFF)) & 0xFFFFFFFF
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x180)}
    for start, size in ((view - 16, 0x1A0), (ALTERNATE - 16, 0x1A0), (BASE - 16, 32), (SCALE_H - 32, 64)):
        memory.update({start + i: (i * 13 + 0xA5) & 255 for i in range(size)})
    put(memory, BASE, table)
    put(memory, SCALE_H, 0x3C8EFA35)
    put(memory, SCALE_V, 0x3C8EFA35)
    put(memory, view + 0x74, x)
    put(memory, view + 0x78, y)
    return memory, view, (index,), frame


def effects(memory, view, ordinal, mode):
    if ordinal == 1 and mode == 1:
        put(memory, view + 0x78, bits(240.0))
        put(memory, BASE, ALTERNATE)
        put(memory, SCALE_H, bits(2.0))
        put(memory, SCALE_V, bits(-0.5))
    if ordinal == 2 and mode == 2:
        put(memory, SCALE_V, 0x80000000)
    if ordinal == 4 and mode == 3:
        put(memory, view + 0x88, 0x7FC000A5)


def returned(seed, ordinal):
    return RETURNS[(seed + ordinal * 3) % len(RETURNS)]


def reference(memory, view, seed, mode):
    result, calls = dict(memory), []
    horizontal = mul(mul(read(result, view + 0x74), 0x3F000000) ^ 0x80000000, read(result, SCALE_H))
    half_vertical = mul(read(result, view + 0x78), 0x3F000000)
    calls.append((COS, horizontal))
    c0 = returned(seed, 1)
    effects(result, view, 1, mode)
    calls.append((SIN, horizontal))
    s0 = returned(seed, 2)
    effects(result, view, 2, mode)
    for offset, value in ((0x9C, s0), (0x90, s0), (0x94, c0 ^ 0x80000000),
            (0x88, c0), (0x98, 0), (0x8C, 0)):
        put(result, view + offset, value)
    vertical = mul(half_vertical, read(result, SCALE_V))
    calls.append((COS, vertical))
    c1 = returned(seed, 3)
    effects(result, view, 3, mode)
    calls.append((SIN, vertical))
    s1 = returned(seed, 4) ^ 0x80000000
    effects(result, view, 4, mode)
    for offset, value in ((0xA0, 0), (0xA8, s1), (0xB4, s1), (0xAC, 0),
            (0xA4, c1 ^ 0x80000000), (0xB0, c1)):
        put(result, view + offset, value)
    return result, calls


class PlaneOracle(machine.BurstOracle):
    def __init__(self, words, memory, args, view, seed=0, mode=0, phase=0, fault=None):
        super().__init__(words, memory, actor=view, phase=phase, mode=mode, entry=source.ENTRY,
            arguments=args, symbols={'unused': 0})
        self.view, self.seed = view, seed
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = faults.TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 236:
            if self.accesses == self.root_fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        assert target in (COS, SIN), hex(target)
        self.calls.append((target, self.f[12]))
        self.events.append(('CALL', target, self.f[12]))

    def hook(self, target):
        ordinal = len(self.calls)
        effects(self.memory, self.view, ordinal, self.mode)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.f[0] = returned(self.seed, ordinal)


class ViewFrustumPlaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>61I', cls.rom, source.ROM))
        cls.original = cls.root / source.PATHS['original']

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, text=True, check=True)
        return obj

    def test_01_full_owner_static_home_lifetimes_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        old, w0 = build.compile_owner(self.root, self.out, before, 'owner-before')
        new, w1 = build.compile_owner(self.root, self.out, source.recover(before), 'owner-after')
        t0, f0, r0 = parse_object(old)
        t1, f1, r1 = parse_object(new)
        self.assertEqual(set(f0), set(f1))
        self.assertEqual(w0, '')
        self.assertEqual(w1, '')
        for name in set(f0) - {source.FUNCTION}:
            a, b = f0[name], f1[name]
            self.assertEqual(a['size'], b['size'], name)
            self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
            relative = lambda table, info: {at - info['value']: value for at, value in table.items() if info['value'] <= at < info['value'] + info['size']}
            self.assertEqual(relative(r0, a), relative(r1, b), name)
        self.assertEqual(normalized_pools(old), normalized_pools(new))
        raw, functions = build.link_owner(self.root, self.out, new, source.OWNER)
        info = functions[source.FUNCTION]
        self.assertEqual(info['size'], 236)
        words = list(struct.unpack_from('>59I', raw, info['value']))
        self.assertEqual([i for i, (a, b) in enumerate(zip(words, self.retail)) if a != b], [21, 22, 24, 25])
        patched = list(words)
        for offset, expected, replacement in source.GUARDS:
            self.assertEqual(words[offset // 4], expected)
            self.assertEqual(expected & 0xFFFF0000, replacement & 0xFFFF0000)
            self.assertEqual(expected >> 21 & 31, 29)
            self.assertEqual(replacement - expected, 4)
            patched[offset // 4] = replacement
        self.assertEqual(patched, self.retail[:59])
        self.assertEqual(self.retail[59:], [0, 0])
        homes = {}
        for i, word in enumerate(words):
            if word >> 26 in (49, 57) and word >> 21 & 31 == 29:
                homes.setdefault(word & 65535, []).append((i, word >> 26))
        self.assertEqual(homes, {0x20: [(21, 57), (22, 49)], 0x30: [(24, 57), (25, 49)],
            0x28: [(19, 57), (37, 49)], 0x24: [(40, 57), (41, 49)], 0x34: [(43, 57), (47, 49)]})
        self.assertLess(22, 40)
        self.assertLess(25, 43)
        guards = self.out / 'qualified-guards.csv'
        guards.write_bytes((self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        primary = pad_c_object.emit_padded_assembly(new, self.root / 'conker/retail_layout.us.txt', source.OWNER,
            word_patches_path=guards)
        primary_obj = self.assemble(primary, 'primary-padded')
        extracted, unresolved = emit_function(t1, f1[source.FUNCTION], r1, source.FUNCTION,
            nm_anchors(self.root / source.PATHS['elf']))
        self.assertFalse(unresolved)
        compact = self.assemble(extracted, 'selected-compact')
        selected_guards = self.out / 'selected-guards.csv'
        selected_guards.write_text(guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)
        generated_obj = self.assemble(emit_padded_assembly(compact, self.original, filename=source.OWNER,
            word_patches_path=selected_guards), 'generated-padded')
        for artifact in (primary_obj, generated_obj):
            data, f = build.link_owner(self.root, self.out, artifact, source.OWNER)
            self.assertEqual(data[f[source.FUNCTION]['value']:f[source.FUNCTION]['value'] + 244], self.rom[source.ROM:source.ROM + 244])
        self.receipt('owners', neighbors=len(f0) - 1, warnings=0, body_words=59, slot_words=61, frame=64,
            guards=4, disjoint_first_and_second_phase_home_lifetimes=True, both_actual_padders=True,
            retained_words_sizes_relative_relocations_and_pools=True)

    def words(self):
        data, functions = build.link_owner(self.root, self.out, self.out / 'generated-padded.o', source.OWNER)
        return list(struct.unpack_from('>61I', data, functions[source.FUNCTION]['value']))

    def test_02_independently_assembled_original_and_rebased_links(self):
        original = self.assemble(self.original.read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',236\n', 'original-retail')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        anchors.update(build.load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt')))
        for phase, base in enumerate((source.ENTRY, 0x16108000)):
            spans = []
            for index, artifact in enumerate((original, self.out / 'primary-padded.o', self.out / 'generated-padded.o')):
                text, f, relocations = parse_object(artifact)
                info = dict(f[source.FUNCTION], size=244)
                asm, unresolved = emit_function(text, info, relocations, source.FUNCTION, anchors)
                self.assertFalse(unresolved)
                single = self.assemble(asm, 'rebase-input-%d-%d' % (phase, index))
                symbols = {symbol for at, entries in relocations.items() if info['value'] <= at < info['value'] + 244 for _, symbol in entries}
                values = {symbol: (0x17008000 + i * 4 if symbol in ('cosf', 'sinf') else
                    0x90007FFC + (i % 4) * 4 + (i // 4) * 0x10000) for i, symbol in enumerate(sorted(symbols))} if phase else {symbol: anchors[symbol] for symbol in symbols}
                script = single.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                elf = single.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(single)], capture_output=True, text=True, check=True)
                spans.append(sections(elf)['.text'][1][:244])
            self.assertEqual(spans[0], spans[1])
            self.assertEqual(spans[0], spans[2])

    def test_03_mips_float_ABI_cached_inputs_live_scale_aliases_and_signs(self):
        words, cases, seen = self.words(), 0, set()
        for index, angles, alias, mode, seed, phase in itertools.product((0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000),
                ANGLES, range(3), range(4), range(8), (0, 8)):
            memory, view, args, _ = fixture(index, *angles, alias, phase)
            expected, calls = reference(memory, view, seed, mode)
            models = [PlaneOracle(body, memory, args, view, seed, mode, phase).run() for body in (self.retail, words)]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual({a: v for a, v in model.memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180},
                    {a: v for a, v in expected.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180})
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 236, 4)))
        self.receipt('mips', cases=cases, reached_words=len(seen), alignment_nops=2,
            one_signed_index_and_F12_F0_helper_ABI=True, cached_view_and_half_vertical_live_second_scale=True,
            guest_index_wrap_base_and_scale_aliases=True, helper_return_sign_zero_NaN_bits=True,
            full_available_instruction_state_equal=True, helpers_bounded_atomic=True,
            no_FCSR_exception_trig_accuracy_or_gameplay_claim=True)

    def test_04_every_fired_root_memory_prefix(self):
        words, cuts = self.words(), 0
        for alias, mode, seed, phase in itertools.product(range(3), (0, 1, 2), (0, 6), (0, 8)):
            memory, view, args, _ = fixture(0xFFFFFFFF, bits(120.0), bits(-90.0), alias, phase)
            finished = PlaneOracle(self.retail, memory, args, view, seed, mode, phase).run()
            for cut in range(finished.accesses):
                models = [PlaneOracle(body, memory, args, view, seed, mode, phase, cut) for body in (self.retail, words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cuts += 1
        self.receipt('faults', fired_prefixes=cuts, actual_root_memory_instructions=True,
            helpers_atomic_bounded_no_arbitrary_helper_or_portable_C_fault_claim=True)

    def test_05_compiled_semantic_and_guard_corruption_controls(self):
        before = (self.out / 'before-owner').read_text()
        for label, body in (('stride', source.BODY.replace('index * 0x180', 'index * 0x184')),
                ('vertical-sign', source.BODY.replace('value = -value;', 'value = value;')),
                ('reload-half', source.BODY.replace('verticalAngle = halfVertical *', 'halfVertical = view->unk78 * 0.5f;\n    verticalAngle = halfVertical *'))):
            self.assertNotEqual(body, source.BODY)
            obj, _ = build.compile_owner(self.root, self.out, source.recover(before, body), 'negative-' + label)
            data, f = build.link_owner(self.root, self.out, obj, source.OWNER)
            info = f[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
            self.assertNotEqual(words, self.retail[:len(words)])
            memory, view, args, _ = fixture(1, bits(60.0), bits(120.0), 0, 0)
            mode = 1 if label == 'reload-half' else 0
            expected, calls = reference(memory, view, 2, mode)
            model = PlaneOracle(words, memory, args, view, 2, mode).run()
            self.assertTrue(model.calls != calls or any(model.memory[a] != v for a, v in expected.items()
                if not machine.STACK - 0x600 <= a < machine.STACK + 0x180))
        for old, new in (('0xE7AC0020,0xE7AC0024', '0xE7AC0021,0xE7AC0024'),
                (',-,-,Coalesce', ',R_MIPS_LO16:D_80096900,-,Coalesce')):
            path = self.out / 'negative-guards.csv'
            rows = source.GUARD_ROWS.replace(old, new)
            self.assertNotEqual(rows, source.GUARD_ROWS)
            path.write_text((self.out / 'selected-guards.csv').read_text().splitlines()[0] + '\n' + rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.out / 'selected-compact.o', self.original, filename=source.OWNER,
                    word_patches_path=path)

    def test_06_native32_planes_helper_contracts_and_controls(self):
        prelude = r'''typedef unsigned char u8;typedef int s32;typedef unsigned int u32;typedef float f32;
typedef struct {u8 p0[0x74];f32 unk74,unk78;u8 p7c[12];f32 unk88,unk8C,unk90,unk94,unk98,unk9C;
 f32 unkA0,unkA4,unkA8,unkAC,unkB0,unkB4;u8 tail[200];} struct259;
_Static_assert(sizeof(void *)==4&&sizeof(struct259)==0x180,"32-bit SDK layout");
_Static_assert(__builtin_offsetof(struct259,unk74)==0x74&&__builtin_offsetof(struct259,unk88)==0x88&&
 __builtin_offsetof(struct259,unkB4)==0xB4,"field offsets");
s32 D_800BE628;f32 D_80096900,D_80096904;
static union {u32 align;u8 bytes[0x600];} storage,expected,other;
static int mode,seed,error,events;static u32 wanted[4],answers[4];static u8 *view;
static u32 get(u8 *p,int o){return *(u32 *)(p+o);}
static void set(u8 *p,int o,u32 w){*(u32 *)(p+o)=w;}
static f32 from(u32 w){union {u32 w;f32 f;} x;x.w=w;return x.f;}
static u32 bits(f32 f){union {u32 w;f32 f;} x;x.f=f;return x.w;}
static u32 product(u32 a,u32 b){f32 f=from(a)*from(b);return bits(f);}
static u32 values[7]={0,0x80000000,0x3F3504F3,0xBF3504F3,0x7F7FFFFF,0x7F800000,0x7FC12345};
static void effect(u8 *p,u32 *base,u32 *h,u32 *v,int ordinal){
 if(ordinal==1&&mode==1){set(p,0x78,0x43700000);*base=(u32)other.bytes;*h=0x40000000;*v=0xBF000000;}
 if(ordinal==2&&mode==2)*v=0x80000000;if(ordinal==4&&mode==3)set(p,0x88,0x7FC000A5);}
static f32 result(f32 angle,int sine){u32 base,h,v;int ordinal=events+1;
 if(events>=4||sine!=(events&1)||bits(angle)!=wanted[events]){error=1;return 0;}
 base=(u32)D_800BE628;h=bits(D_80096900);v=bits(D_80096904);
 effect(view,&base,&h,&v,ordinal);D_800BE628=(s32)base;D_80096900=from(h);D_80096904=from(v);
 return from(answers[events++]);}
f32 cosf(f32 angle){return result(angle,0);}f32 sinf(f32 angle){return result(angle,1);}
''' + source.BODY
        suffix = r'''
static int run(void){u32 angles[8][2]={{0,0},{0x80000000,0},{0x41F00000,0x42700000},
 {0xC2B40000,0x42F00000},{0x43330000,0xC2340000},{0x7F7FFFFF,0x3F800000},
 {1,0x80000001},{0x3E800000,0x3E000000}};
 int index,a,i,ordinal=0,cases=0;u32 base,h,v,halfVertical,x,y;u8 *p;
 for(index=0;index<4;index++)for(a=0;a<8;a++)for(mode=0;mode<4;mode++)for(seed=0;seed<7;seed++,ordinal++,cases++){
  for(i=0;i<0x600;i++)storage.bytes[i]=expected.bytes[i]=other.bytes[i]=(u8)(i*13+ordinal+0xA5);
  view=storage.bytes+index*0x180;p=expected.bytes+index*0x180;
  set(view,0x74,angles[a][0]);set(view,0x78,angles[a][1]);set(p,0x74,angles[a][0]);set(p,0x78,angles[a][1]);
  D_800BE628=(s32)storage.bytes;base=(u32)storage.bytes;D_80096900=D_80096904=from(0x3C8EFA35);h=v=0x3C8EFA35;
  error=events=0;for(i=0;i<4;i++)answers[i]=values[(seed+(i+1)*3)%7];
  x=product(product(get(p,0x74),0x3F000000)^0x80000000,h);halfVertical=product(get(p,0x78),0x3F000000);
  wanted[0]=wanted[1]=x;effect(p,&base,&h,&v,1);effect(p,&base,&h,&v,2);
  set(p,0x88,answers[0]);set(p,0x8C,0);set(p,0x90,answers[1]);set(p,0x94,answers[0]^0x80000000);set(p,0x98,0);set(p,0x9C,answers[1]);
  y=product(halfVertical,v);wanted[2]=wanted[3]=y;effect(p,&base,&h,&v,3);effect(p,&base,&h,&v,4);
  set(p,0xA0,0);set(p,0xA4,answers[2]^0x80000000);set(p,0xA8,answers[3]^0x80000000);
  set(p,0xAC,0);set(p,0xB0,answers[2]);set(p,0xB4,answers[3]^0x80000000);
  func_1501B22C(index);
  if(error||events!=4||(u32)D_800BE628!=base||bits(D_80096900)!=h||bits(D_80096904)!=v)return 1;
  for(i=0;i<0x600;i++)if(storage.bytes[i]!=expected.bytes[i])return 2;
 }return cases==896?0:81;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status));__builtin_unreachable();}
'''
        for label, flags, body, status in (('O2', '-O2', source.BODY, 0), ('O0', '-O0', source.BODY, 0),
                ('negative-stride', '-O2', source.BODY.replace('index * 0x180', 'index * 0x184'), 1),
                ('negative-sign', '-O2', source.BODY.replace('value = -value;', 'value = value;'), 2),
                ('negative-reload', '-O2', source.BODY.replace('verticalAngle = halfVertical *', 'halfVertical = view->unk78 * 0.5f;\n    verticalAngle = halfVertical *'), 1)):
            path = self.out / ('native-' + label + '.c')
            path.write_text(prelude.replace(source.BODY, body) + suffix)
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', flags, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign', '-fno-strict-aliasing',
                '-fwrapv', '-fno-builtin', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label)
        self.receipt('native', cases_per_profile=896, profiles=['O2', 'O0'], native32_SSE2_stack_realign_required=True,
            full_storage_and_four_float_calls_compared=True, cached_view_pending_half_and_live_scale=True,
            finite_inputs_quiet_NaN_inf_zero_helper_returns=True, compiled_controls_fired=True,
            no_partial_alias_index_wrap_FCSR_retail_trig_or_gameplay_claim=True)

    def test_07_installed_source_guards_progress_and_closed_image(self):
        source.freeze(self.root, self.out)
        owner_path = source.PATHS['owner']
        text = (self.root / owner_path).read_text()
        text = view_fov_transfer_checkpoint.previous_input(text.encode(), owner_path, self.root).decode()
        self.assertEqual(text, source.recover((self.out / 'before-owner').read_text()))
        owner = view_fov_transfer_checkpoint.previous_input((self.root / owner_path).read_bytes(), owner_path, self.root)
        self.assertEqual(hashlib.sha256(owner).hexdigest(), checkpoint.AFTER['owner'])
        guards = view_fov_transfer_checkpoint.previous_input((self.root / source.PATHS['guards']).read_bytes(), source.PATHS['guards'], self.root)
        self.assertEqual(guards, (self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        for key in ('progress', 'makefile', 'functions', 'structs', 'variables', 'original'):
            current = view_fov_transfer_checkpoint.previous_input((self.root / source.PATHS[key]).read_bytes(), source.PATHS[key], self.root)
            self.assertEqual(current, (self.out / ('before-' + key)).read_bytes(), key)
        before, current = (self.out / 'before-elf').read_bytes(), (self.root / source.PATHS['elf']).read_bytes()
        installed_hash = hashlib.sha256(current).hexdigest()
        current = game_sine_checkpoint.previous_input(current, source.PATHS['elf'], self.root)
        expected = bytearray(before)
        at = image.elf_slot_offset(before, source.ENTRY, 244)
        expected[at:at + 244] = self.rom[source.ROM:source.ROM + 244]
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(before, source.FUNCTION)
        self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
        struct.pack_into('>I', expected, size, 236)
        self.assertEqual(current, bytes(expected), 'Only the frustum slot and its public code extent may change')
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256(current).hexdigest(),
            raw_installed_ELF_sha256=installed_hash, pinned_later_sine_projection=True,
            changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + 244], expected[at:at + 244])),
            body_words=59, slot_words=61, alignment_nops=2, new_guards=4,
            every_other_ELF_byte_and_all_headers_progress_Makefile_fixed=True, protected_data=data)

    def test_08_effective_installed_and_frozen_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key in ('elf', 'owner', 'guards', 'progress', 'makefile', 'functions', 'structs', 'variables', 'original'):
            path = self.root / source.PATHS[key]
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_guards_progress_and_closed_image()
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_installed_source_guards_progress_and_closed_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: b'changed baseline' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable view-plane input'):
                self.test_07_installed_source_guards_progress_and_closed_image()

    def test_09_pinned_inverse_and_unknown_input_controls(self):
        self.test_07_installed_source_guards_progress_and_closed_image()
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, path, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data, self.root / path, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data + b'\n', path, self.root), data + b'\n')
        rb = Path.read_bytes
        path = self.out / 'after-owner'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'view-plane fixture'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
