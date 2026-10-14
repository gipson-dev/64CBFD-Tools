"""Two private vector snapshots, raw actor copies and bounded RNE subtraction."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_vector_snapshot_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.tests import test_game_actor_mask_scan_match as scan
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

STACK, ACTOR, TABLE, PARENT, PARENT_ROM = image.STACK, 0x21000, 0x80086110, 0x1506AC8C, 0x9813C
RAW = (0, 0x80000000, 1, 0x807FFFFF, 0x3F800000, 0xC0200000,
    0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0x7F7FFFFF, 0xA55A00FF)
NUMERIC = tuple(map(bits, (0.0, -0.0, 1.0, -1.0, 2.5, -2.5, 128.0, -128.0,
    0.125, -0.125, 16777216.0, -16777216.0, 7.0, -7.0, 1048576.0, -1048576.0)))


def controls():
    return {
        'wrong-coordinate': source.SELECTED.replace('actor + 0x14', 'actor + 0x10'),
        'reversed-difference': source.SELECTED.replace(source.DIFFERENCE[0],
            '    difference[0] = *(f32 *)(D_800D1560 + 0) - *(f32 *)(D_800D1570 + 0);'),
        'sum-not-difference': source.SELECTED.replace(' - *(f32 *)', ' + *(f32 *)'),
        'swapped-vectors': source.SELECTED.replace('func_151D3480(position, difference,', 'func_151D3480(difference, position,'),
        'wrong-kind': source.SELECTED.replace('difference, NULL, 0,', 'difference, NULL, 1,'),
        'wrong-slot': source.SELECTED.replace('0xFF, 1', '0xFE, 1'),
    }


def wrong_layout():
    return source.SELECTED.replace('    f32 position[3];\n    f32 difference[3];',
        '    f32 difference[3];\n    f32 position[3];')


def fixture(position=None, config=0, actor=ACTOR, symbols=None, phase=0):
    s = symbols or source.SYMBOLS
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for i in range(-0x600, 0x140, 4):
        put(memory, STACK + i, bits(float(i // 4 % 17 - 8)))
    for base in (ACTOR - 32, actor - 32, s['D_800D1560'] - 32, s['D_800D1570'] - 32, TABLE):
        for i in range(128):
            memory.setdefault(base + i, 0xA5)
    for i, value in enumerate(position or (0x3F800000, 0xC0200000, 0x7F812345)):
        put(memory, actor + 0x14 + i * 4, value)
    for i in range(3):
        put(memory, s['D_800D1560'] + i * 4, NUMERIC[(config + i) & 15])
        put(memory, s['D_800D1570'] + i * 4, NUMERIC[((config >> 4) + i * 3) & 15])
    put(memory, TABLE + 4 * 4, source.ENTRY)
    return memory


def effects(mode, actor, symbols):
    if mode == 1:
        return ((actor + 0x14, 0x12345678, 4), (symbols['D_800D1560'], 0x76543210, 4),
            (symbols['D_800D1570'] + 8, 0xFEDCBA98, 4))
    return ()


def difference(left, right):
    return bits(floating(left) - floating(right))


def reference(memory, actor=ACTOR, mode=0, phase=0, symbols=None, argument=0x8765ABCD):
    s, result = symbols or source.SYMBOLS, dict(memory)
    frame, events = STACK + phase - 0x38, []
    put(result, frame + 0x1C, 0xDEAD0000)
    put(result, STACK + phase, actor)
    put(result, STACK + phase + 4, argument)
    def get(address):
        value = read(result, address)
        events.append(('R', address, 4, value))
        return value
    # Retail load/store order matters only to the separately declared guest-private aliases.
    bx, ax, px = get(s['D_800D1570']), get(s['D_800D1560']), get(actor + 0x14)
    dx = difference(bx, ax)
    put(result, frame + 0x2C, px)
    py, by, az = get(actor + 0x18), get(s['D_800D1570'] + 4), get(s['D_800D1560'] + 8)
    put(result, frame + 0x30, py)
    pz, ay, bz = get(actor + 0x1C), get(s['D_800D1560'] + 4), get(s['D_800D1570'] + 8)
    put(result, frame + 0x20, dx)
    put(result, frame + 0x34, pz)
    put(result, frame + 0x24, difference(by, ay))
    put(result, frame + 0x28, difference(bz, az))
    position = tuple(read(result, frame + 0x2C + i * 4) for i in range(3))
    direction = tuple(read(result, frame + 0x20 + i * 4) for i in range(3))
    args = (frame + 0x2C, frame + 0x20, 0, 0, 255, 1)
    calls = [(s['func_151D3480'], args, position, direction)]
    events.append(('CALL', s['func_151D3480'], args))
    for address, value, size in effects(mode, actor, s):
        put(result, address, value, size)
        events.append(('W', address, size, value))
    return external(result), public(events), calls


class VectorOracle(scan.MaskOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, mode=0, symbols=None,
            entry=source.ENTRY, arguments=None, connected=None, fault=None):
        super().__init__(words, memory, phase, mode, symbols or source.SYMBOLS, entry,
            arguments or (actor, 0x8765ABCD), connected, fault=fault)
        self.actor = actor

    def record_call(self, target):
        if target == source.ENTRY:
            self.callbacks.append(self.arguments(2))
            return
        assert target == self.symbols['func_151D3480'], hex(target)
        args = self.arguments(6)
        position = tuple(self.get(args[0] + i * 4, 4) for i in range(3))
        direction = tuple(self.get(args[1] + i * 4, 4) for i in range(3))
        self.calls.append((target, args, position, direction))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == self.symbols['func_151D3480']
        for address, value, size in effects(self.mode, self.actor, self.symbols):
            self.put(address, value, size)
        if self.mode == 2:
            for base in self.calls[-1][1][:2]:
                for i in range(3):
                    self.put(base + i * 4, 0xC5000000 + i, 4)
        for i in range(6):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344


class GameActorVectorSnapshotMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-vector-snapshot-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', layout='conker/retail_layout.us.txt',
            assembly='conker/asm/97AA0.s', table='conker/asm/data/22ABD0.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '026132cc793e9a4c00c612958f706583f14ef65fd8452481aee7dbfed0a66c68'
        assert cls.baseline['elf'] == '79f140332385316ef3a26372c7d231a89bf02c37a398f151ac03ac79568949a0'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = source.recovered_owner(cls.owner_before)
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>40I', cls.rom, source.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, phase=0, mode=0, symbols=None, entry=source.ENTRY, bodies=None):
        expected = reference(memory, actor, mode, phase, symbols)
        models = [VectorOracle(w, memory, actor, phase, mode, symbols, entry).run()
            for w in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual((external(model.memory), public(model.events), model.calls), expected)
            self.assertEqual(model.r[2], 0x11223344)
        self.assertEqual(scan.state(models[0]), scan.state(models[1]))
        return models

    def test_01_complete_direct_words_profiles_and_real_frame_measurement(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (40, 56, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.meta['relocations'][0x88], [('R_MIPS_26', 'func_151D3480')])
        measured = json.loads((self.root / 'conker/build/game-actor-vector-snapshot/measurements.json').read_text())
        self.assertEqual(len(measured), 96)
        self.assertEqual([m['name'] for m in measured if m['differences'] == 0],
            ['order0-position-qualifier0-o2g3', 'order0-position-qualifier2-o2g3'])
        self.assertEqual({m['frame'] for m in measured}, {56})
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-layout', wrong_layout())
        self.assertEqual(sum(a != b for a, b in zip(wrong, self.retail)), 8)
        self.receipt('shape', words=40, frame=56, direct_C=True, guards=0,
            measurements=96, exact_plain_and_unused_argument_qualifier_only=True,
            private_position_offset=44, private_difference_offset=32, wrong_layout_words=8,
            frame_decoded_from_actual_SP_adjustment_not_first_instruction=True)

    def test_02_actor_bit_copies_finite_differences_and_mutation_coverage(self):
        cases, seen = 0, set()
        for indices in itertools.product(range(len(RAW)), repeat=3):
            config = (indices[0] * 17 + indices[1] * 31 + indices[2] * 13) & 255
            position = tuple(RAW[i] for i in indices)
            for phase, mode in itertools.product((0, 8), range(3)):
                for model in self.compare(fixture(position, config), phase=phase, mode=mode):
                    seen.update(model.visits)
                cases += 1
        for config, phase, mode in itertools.product(range(256), (0, 8), range(3)):
            self.compare(fixture(config=config), phase=phase, mode=mode)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 160, 4)))
        self.receipt('guest', cases=cases, actor_patterns=12 ** 3, all_16_by_16_numeric_pairs_per_axis=True,
            independent_raw_copy_and_RNE_reference=True, full_modeled_states_and_external_order=True,
            all40_words_reached=True, numeric_difference_inputs_finite_bounded_only=True,
            copied_NaN_payloads_not_general_arithmetic_or_FCSR_acceptance=True)

    def test_03_public_private_and_global_home_aliases(self):
        cases = 0
        links = {}
        for phase, mode in itertools.product((0, 8), range(3)):
            frame = STACK + phase - 0x38
            for actor in (ACTOR, source.SYMBOLS['D_800D1560'] - 0x14,
                    source.SYMBOLS['D_800D1570'] - 0x14, frame + 0x14,
                    STACK + phase - 0x14, STACK + phase - 0x10):
                self.compare(fixture((0x3F800000, 0x40000000, 0x40400000), 37, actor), actor, phase, mode)
                cases += 1
            for name, key, address in (('position', 'D_800D1560', frame + 0x2C),
                    ('difference', 'D_800D1570', frame + 0x20),
                    ('home0', 'D_800D1560', STACK + phase), ('home1', 'D_800D1570', STACK + phase + 4)):
                symbols = dict(source.SYMBOLS, **{key: address})
                if (name, phase) not in links:
                    with patch.object(source, 'SYMBOLS', symbols):
                        _, emitted = source.compile_candidate(self.root, self.out, 'alias-' + name + '-%d' % phase)
                    original = self.rebased_original(source.ENTRY, symbols, 'alias-original-' + name + '-%d' % phase)
                    links[name, phase] = (original, emitted)
                original, emitted = links[name, phase]
                self.assertEqual(emitted, original)
                self.compare(fixture(config=37, symbols=symbols), phase=phase, mode=mode,
                    symbols=symbols, bodies=(original, emitted))
                cases += 1
        self.receipt('aliases', cases=cases, incoming_homes_and_two_private_vectors=True,
            public_global_actor_aliases_and_callback_input_changes=True,
            private_retail_load_store_order_qualified_not_portable_C_promises=True)

    def test_04_required_float_bytes_and_wrong_layout_effective(self):
        cases = 0
        for phase, base in itertools.product((0, 8), (ACTOR + 0x14, 0x800D1560, 0x800D1570)):
            for byte in range(12):
                memory = fixture()
                del memory[base + byte]
                models = [VectorOracle(w, memory, phase=phase) for w in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                    self.assertEqual(model.calls, [])
                self.assertEqual(scan.state(models[0]), scan.state(models[1]))
                cases += 1
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-layout-alias', wrong_layout())
        actor = STACK - 0x38 + 0x14
        memory = fixture((0x3F800000, 0x40000000, 0x40400000), 37, actor)
        models = [VectorOracle(w, memory, actor=actor).run() for w in (self.retail, wrong)]
        self.assertNotEqual(models[0].calls[-1][2:], models[1].calls[-1][2:])
        self.receipt('inputs', required_byte_fault_prefixes=cases, no_null_actor_gate_added=True,
            wrong_real_array_order_changes_private_aliased_payload=True)

    def test_05_six_effective_compiled_semantic_controls(self):
        memory = fixture((0x3F800000, 0xC0200000, 0x7F812345), 37)
        expected = reference(memory)
        for name, body in controls().items():
            _, wrong = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            model = VectorOracle(wrong, memory).run()
            self.assertNotEqual((external(model.memory), public(model.events), model.calls), expected, name)
        self.receipt('controls', effective_compiled_controls=list(controls()))

    def test_06_complete_owner_padders_neighbors_and_pools(self):
        objects = [compile_owner(self.root, self.out, text, 'owner-' + name)
            for name, text in (('before', self.owner_before), ('after', self.owner_after))]
        self.assertEqual(objects[0][1], objects[1][1])
        for name in ('before', 'after'):
            obj = self.out / ('owner-' + name + '.o')
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
        before, after = [parse_object(p[0]) for p in objects]
        self.assertEqual(set(before[1]), set(after[1]))
        neighbors = set(before[1]) - {source.FUNCTION}
        for name in neighbors:
            a, b = before[1][name], after[1][name]
            self.assertEqual(before[0][a['value']:a['value'] + a['size']], after[0][b['value']:b['value'] + b['size']], name)
            relative = lambda obj, f: {at - f['value']: uses for at, uses in obj[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(before, a), relative(after, b), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for kind in ('layout', 'slice'):
            path = self.out / ('owner-padded-' + kind + '.s')
            kwargs = dict(word_patches_path=self.root / self.paths['guards'])
            text = pad_c_object.emit_padded_assembly(objects[1][0], self.root / self.paths['layout'], 'generated_97AA0', **kwargs) if kind == 'layout' else emit_padded_assembly(
                objects[1][0], self.root / self.paths['assembly'], filename='generated_97AA0', **kwargs)
            path.write_text(text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        self.assertEqual(padded[0], padded[1])
        target = padded[0][1][source.FUNCTION]
        self.assertEqual(target['size'], 160)
        raw, isolated, _ = parse_object(self.out / 'selected.o')
        start = isolated[source.FUNCTION]['value']
        self.assertEqual(padded[0][0][target['value']:target['value'] + 160], raw[start:start + 160])
        self.receipt('owner', neighbors=len(neighbors), both_complete_padders=True,
            pools_neighbor_bytes_relocations_fixed=True, previous_creator_and_mask_scan_fixed=True)

    def test_07_literal_image_source_and_protected_history(self):
        current_source = (self.root / self.paths['source']).read_text()
        self.assertIn(current_source, (self.owner_before, self.owner_after))
        expected = bytearray(self.before)
        if current_source == self.owner_after:
            offset = image.elf_slot_offset(self.before, source.ENTRY, 160)
            expected[offset:offset + 160] = struct.pack('>40I', *self.retail)
            with patch.object(image.screen, 'ENTRY', source.ENTRY):
                size = image.elf_symbol_size_offset(self.before, source.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected, size)[0], 12)
            struct.pack_into('>I', expected, size, 160)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        for name in set(self.paths) - {'source', 'elf'}:
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), before, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=current_source == self.owner_after,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            only_target160_bytes_and_exact_named_size12_to160=True, protected_data=data)

    def test_08_actual_native32_raw_copies_numeric_grid_and_public_aliases(self):
        raw = ','.join('0x%Xu' % value for value in RAW)
        numeric = ','.join('0x%Xu' % value for value in NUMERIC)
        deltas = ','.join('0x%Xu' % difference(b, a) for b, a in itertools.product(NUMERIC, NUMERIC))
        fixture_c = '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
static union {u32 align;u8 bytes[96];} actor,first,second;
#define D_800D1560 (first.bytes+32)
#define D_800D1570 (second.bytes+32)
static u8 *input;static u32 wanted[6];static int mode,count,error;
static const u32 raw[]={''' + raw + '''},numeric[]={''' + numeric + '''},delta[]={''' + deltas + '''};
void func_151D3480(f32 *position,f32 *direction,void *optional,u8 kind,u8 slot,s32 context){
 int i;count++;if(optional||kind||slot!=255||context!=1)error=1;
 for(i=0;i<3;i++)if(((u32*)position)[i]!=wanted[i]||((u32*)direction)[i]!=wanted[i+3])error=2;
 if(mode==1){*(u32*)(input+0x14)=0x12345678u;*(u32*)D_800D1560=0x76543210u;*(u32*)(D_800D1570+8)=0xFEDCBA98u;}
 if(mode==2){for(i=0;i<3;i++){((u32*)position)[i]=((u32*)direction)[i]=0xC5000000u+(u32)i;}}
}
''' + source.SELECTED + '''
static void (*volatile invoke)(u8*,s32)=func_1506A79C;
int run(void){int p,g,m,alias,i;u8 expectedActor[96],expectedFirst[96],expectedSecond[96];
 if(sizeof(void*)!=4||sizeof(f32)!=4)return 10;
 for(p=0;p<1728;p++)for(m=0;m<3;m++)for(alias=0;alias<4;alias++){
  for(i=0;i<96;i++)actor.bytes[i]=first.bytes[i]=second.bytes[i]=0xA5;
  input=alias==0?actor.bytes:alias==1?D_800D1560-0x14:alias==2?D_800D1570-0x14:D_800D1560-0x10;
  *(u32*)(input+0x14)=raw[p%12];*(u32*)(input+0x18)=raw[p/12%12];*(u32*)(input+0x1C)=raw[p/144];
  g=p&255;for(i=0;i<3;i++){int a=(g+i)&15,b=((g>>4)+i*3)&15;
   *(u32*)(D_800D1560+i*4)=numeric[a];*(u32*)(D_800D1570+i*4)=numeric[b];wanted[i+3]=delta[b*16+a];}
  for(i=0;i<3;i++)wanted[i]=*(u32*)(input+0x14+i*4);
  for(i=0;i<96;i++){expectedActor[i]=actor.bytes[i];expectedFirst[i]=first.bytes[i];expectedSecond[i]=second.bytes[i];}
  mode=m;count=error=0;invoke(input,(s32)0x8765ABCDu);if(error||count!=1)return 11;
  if(m==1){u8 *expectedInput=alias==0?expectedActor:alias==1?expectedFirst+12:alias==2?expectedSecond+12:expectedFirst+16;
   *(u32*)(expectedInput+0x14)=0x12345678u;*(u32*)(expectedFirst+32)=0x76543210u;*(u32*)(expectedSecond+40)=0xFEDCBA98u;}
  for(i=0;i<96;i++)if(actor.bytes[i]!=expectedActor[i]||first.bytes[i]!=expectedFirst[i]||second.bytes[i]!=expectedSecond[i])return 12;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, success in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
                '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode == 0, success, (name, result.returncode))
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=1728 * 3 * 4,
            precomputed_guest_checked_RNE_grid=True, raw_actor_payload_bits_and_all_input_canaries=True,
            six_native_compiled_controls_effective=True, bounded_32_bit_SSE_domain_only=True)

    def test_09_original_dispatcher_vector_setup_and_table4(self):
        parent = list(struct.unpack_from('>38I', self.rom, PARENT_ROM))
        functions, _, addresses = image.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(addresses['func_1506AC8C'], PARENT)
        self.assertEqual(functions['func_1506AC8C'], list(struct.unpack_from('>41I', self.rom, PARENT_ROM)))
        self.assertEqual(functions['func_1506AC8C'][38:], [0, 0, 0])
        offset = image.elf_slot_offset(self.before, TABLE + 16, 4)
        self.assertEqual(self.before[offset:offset + 4], struct.pack('>I', source.ENTRY))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22ABE0)[0], source.ENTRY)
        cases, seen = 0, set()
        for config, mode, phase in itertools.product((0, 37, 128, 255), range(3), (0, 8)):
            memory = fixture(config=config)
            initialized = dict(memory)
            for i in range(3):
                put(memory, ACTOR + 0x2C + i * 4, NUMERIC[(config + i) & 15])
                put(memory, 0x800CC254 + i * 4, NUMERIC[((config >> 4) + i * 3) & 15])
            initialized.update(memory)
            for i in range(3):
                put(initialized, 0x800D1560 + i * 4, read(memory, ACTOR + 0x2C + i * 4))
                put(initialized, 0x800D1570 + i * 4, read(memory, 0x800CC254 + i * 4))
            expected_storage, _, calls = reference(initialized, mode=mode, phase=phase - 0x18)
            models = []
            for body in (self.retail, self.words):
                connected = dict(zip(range(source.ENTRY, source.ENTRY + 160, 4), body))
                model = VectorOracle(parent, memory, phase=phase, mode=mode, entry=PARENT,
                    arguments=(ACTOR, 4, 0x8765ABCD), connected=connected).run()
                self.assertEqual(model.callbacks, [(ACTOR, 0x8765ABCD)])
                self.assertEqual((external(model.memory), model.calls), (expected_storage, calls))
                seen.update(model.visits)
                models.append(model)
            self.assertEqual(scan.state(models[0]), scan.state(models[1]))
            cases += 1
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + 160, 4)) <= seen)
        self.receipt('connected', cases=cases, original_dispatcher38_words_and_alignment_tail=True,
            verified_table_index4_and_forwarded_arguments=True, real_parent_vector_setup=True,
            downstream_564_word_provider_not_emulated_or_claimed=True)

    def rebased_original(self, entry, symbols, name):
        assembly = self.out / 'original.s'
        if not assembly.exists():
            block = (self.root / self.paths['assembly']).read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
            assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
                '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
                'endlabel ' + source.FUNCTION + '\n')
        obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(assembly)], check=True, capture_output=True)
        script = self.out / (name + '.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
        return list(struct.unpack_from('>40I', source.compiler.sections(elf)['.text'][1]))

    def test_10_three_independent_carry_boundary_links(self):
        cases = 0
        for index, (entry, first, second) in enumerate(((source.ENTRY, 0x800D1560, 0x800D1570),
                (0x15207FF0, 0x80107FFC, 0x80118004), (0x15318004, 0x80218004, 0x80207FFC))):
            symbols = dict(D_800D1560=first, D_800D1570=second,
                func_151D3480=source.SYMBOLS['func_151D3480'] + index * 0x200000)
            original = self.rebased_original(entry, symbols, 'rebase-' + str(index))
            with patch.object(source, 'ENTRY', entry), patch.object(source, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'rebase-source-' + str(index))
            self.assertEqual(original, emitted)
            for config, mode, phase in itertools.product((0, 37, 128, 255), range(3), (0, 8)):
                self.compare(fixture(config=config, symbols=symbols), phase=phase, mode=mode,
                    symbols=symbols, entry=entry, bodies=(original, emitted))
                cases += 1
        self.receipt('rebases', independent_original_source_links=3, cases=cases,
            actual_HI_LO_carries_and_JAL=True, complete_words_and_states=True)

    def test_11_all_fired_own_access_cuts_and_wrong_layout_negative(self):
        pairs, domains = 0, 0
        for phase, mode in itertools.product((0, 8), range(3)):
            frame = STACK + phase - 0x38
            for actor in (ACTOR, 0x800D1560 - 0x14, 0x800D1570 - 0x14,
                    frame + 0x14, STACK + phase - 0x14, STACK + phase - 0x10):
                memory = fixture((0x3F800000, 0x40000000, 0x40400000), 37, actor)
                complete = VectorOracle(self.words, memory, actor, phase, mode).run()
                self.assertEqual(complete.accesses, 22)
                for cut in range(22):
                    models = [VectorOracle(w, memory, actor, phase, mode, fault=cut) for w in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(scan.AccessFault):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                    self.assertEqual(scan.state(models[0]), scan.state(models[1]))
                    self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                    pairs += 1
                domains += 1
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-layout-fault', wrong_layout())
        models = [VectorOracle(w, fixture(), fault=8) for w in (self.retail, wrong)]
        for model in models:
            with self.assertRaises(scan.AccessFault):
                model.run()
        self.assertNotEqual(scan.state(models[0]), scan.state(models[1]))
        self.receipt('faults', domains=domains, fired_pairs=pairs, all_full_modeled_states=True,
            wrong_layout_cut8_negative_effective=True, provider_accesses_not_counted_as_own=True,
            hardware_PC_BD_complete_FCSR_other_rounding_modes_not_claimed=True)

    def test_12_effective_whole_image_source_and_guard_corruptions(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        path = self.root / self.paths['elf']
        data = path.read_bytes()
        target = image.elf_slot_offset(data, source.ENTRY, 160)
        for offset in (0, target, target + 159, image.elf_slot_offset(data, 0x1506AAE0, 156), len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['source']
        bad_text = path.read_text() + '\n'
        with patch.object(Path, 'read_text', lambda p, *a, **k: bad_text if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['guards']
        bad_bytes = path.read_bytes() + b'\n'
        with patch.object(Path, 'read_bytes', lambda p, *a, **k: bad_bytes if p == path else read_bytes(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        self.receipt('image-controls', target_previous_scan_header_tail_source_guard_mutations_effective=True)


if __name__ == '__main__':
    unittest.main()
