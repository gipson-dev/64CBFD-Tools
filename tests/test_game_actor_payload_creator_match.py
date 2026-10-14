"""Actor/payload creator ABI, untouched padding and literal linked restoration."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_payload_creator_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.tests import test_game_record_constructor_match as shared
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_matrix_reflection_roles import state
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

ACTOR, DATA, CREATED = 0x21000, 0x22000, 0x23000
TABLE, PARENT, PARENT_ROM = 0x80086110, 0x1506AC8C, 0x9813C
CREATE_ARGS = (10, 7, 0x23, 0xFFFFFFFF, 1, 0x21, 16, 255, 1)
PATTERNS = (0, 1, 0x80000000, 0xFFFFFFFF, 0x7FFFFFFF, 0x12345678,
    0x3F800000, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0xA55A00FF)


def controls():
    return {
        'wrong-selector': source.SELECTED.replace('actor[0x3B]', 'actor[0x3A]'),
        'wrong-kind': source.SELECTED.replace('7, 0x23', '7, 0x24'),
        'short-copy': source.SELECTED.replace('memcpy(created + 0x28, &packet, sizeof(packet))', 'memcpy(created + 0x28, &packet, 12)'),
        'wrong-destination': source.SELECTED.replace('memcpy(created + 0x28', 'memcpy(created + 0x2C'),
        'swapped-payload': source.SELECTED.replace('packet.payload = *data;', 'packet.payload.first = data->second;\n    packet.payload.second = data->first;'),
    }


def fixture(selector=0, first=0, second=0, data=DATA, phase=0, result=CREATED, seed=0):
    memory = {shared.STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR - 16, 256), (DATA - 16, 128), (CREATED - 16, 256),
            (0x800D1560, 32), (0x800CC254, 12), (TABLE, 64)):
        memory.update({base + i: (i * 13 + seed * 11 + 0xA5) & 255 for i in range(size)})
    shared.put(memory, data, first)
    shared.put(memory, data + 4, second)
    shared.put(memory, ACTOR + 0x3B, selector, 1)
    shared.put(memory, TABLE + 9 * 4, source.ENTRY)
    return memory, (ACTOR, data)


def mutate(memory, args):
    actor, data = args
    shared.put(memory, actor + 0x3B, 0x5A, 1)
    shared.put(memory, data, 0x76543210)
    shared.put(memory, data + 4, 0xFEDCBA98)


def reference(memory, args, result=CREATED, mode=0, phase=0, connected=False):
    memory = dict(memory)
    frame = shared.STACK + phase - 0x48
    packet = frame + 0x34
    actor, data = args
    shared.put(memory, frame + 0x48, actor)
    shared.put(memory, frame + 0x4C, data)
    shared.put(memory, packet, actor)
    shared.put(memory, packet + 4, shared.read(memory, actor + 0x3B, 1), 1)
    shared.put(memory, packet + 8, shared.read(memory, data))
    shared.put(memory, packet + 12, shared.read(memory, data + 4))
    if mode == 3:
        mutate(memory, args)
    if mode == 2 and result:
        shared.put(memory, result + 4, 0x12345678)
    if connected and result:
        for offset, value, size in ((0xE, 10, 2), (0x10, 7, 1), (0x11, 0x23, 1),
                (0x12, 255, 1), (0xD, 1, 1), (0x13, 0x21, 1)):
            shared.put(memory, result + offset, value, size)
        for i in range(16):
            shared.put(memory, result + 0x14 + i, 0, 1)
    calls = [('create', CREATE_ARGS)]
    if result:
        payload = bytes(memory[packet + i] for i in range(16))
        calls.append(('copy', (result + 0x28) & 0xFFFFFFFF, payload, 16))
        for i in range(16):
            shared.put(memory, (result + 0x28 + i) & 0xFFFFFFFF, memory[packet + i], 1)
    return memory, calls


class PacketOracle(shared.ConnectedConstructorOracle):
    def __init__(self, words, memory, args, result=CREATED, mode=0, phase=0,
            entry=source.ENTRY, symbols=None, connected=None, parent=False):
        super().__init__(words, memory, args, result, mode, phase, entry, symbols, connected)
        self.packet_args = (args[0], args[2]) if parent else args

    def record_call(self, target):
        if target == source.ENTRY:
            self.calls.append(('callback', self.arguments(2)))
        else:
            super().record_call(target)

    def hook(self, target):
        super().hook(target)
        if target == self.symbols['func_15149130'] and self.mode == 3:
            mutate(self.memory, self.packet_args)


class AccessFault(Exception):
    pass


class FaultOracle(PacketOracle):
    def __init__(self, *args, fault=None, **kwargs):
        self.own_instruction = False
        self.fault, self.accesses = fault, 0
        super().__init__(*args, **kwargs)

    def execute(self, word):
        self.dispatched_word = word
        self.own_instruction = True
        try:
            super().execute(word)
        finally:
            self.own_instruction = False

    def access(self):
        if self.own_instruction:
            if self.accesses == self.fault:
                raise AccessFault
            self.accesses += 1

    def get(self, address, size):
        self.access()
        return super().get(address, size)

    def put(self, address, value, size):
        self.access()
        return super().put(address, value, size)


class GameActorPayloadCreatorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-payload-creator-match-test'
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
        assert cls.baseline['source'] == '23b0c8294804b32d6cafef604dc9fe48d366b19c5effbe831be2b53c8a0f6541'
        assert cls.baseline['elf'] == '3ce90848e52416e7cfdf8ee344df140963443f82c84c46621ca42663acd2bf27'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = source.recovered_owner(cls.owner_before, source.SELECTED)
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>38I', cls.rom, source.ROM))
        cls.parent = list(struct.unpack_from('>38I', cls.rom, PARENT_ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, result=CREATED, mode=0, phase=0, words=None):
        expected, calls = reference(memory, args, result, mode, phase)
        models = [PacketOracle(w, memory, args, result, mode, phase).run() for w in (self.retail, self.words if words is None else words)]
        for model in models:
            self.assertEqual(external(model.memory), external(expected))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], (result + 0x28) & 0xFFFFFFFF if result else 0)
        if words is None:
            self.assertEqual(state(models[0]), state(models[1]))
        return models

    def test_01_complete_direct_slot_and_all_real_source_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (38, 72, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.meta['relocations'], {108: [('R_MIPS_26', 'func_15149130')], 128: [('R_MIPS_26', 'memcpy')]})
        measured = json.loads((self.root / 'conker/build/game-actor-payload-creator/measurements.json').read_text())
        self.assertEqual(len(measured), 64)
        exact = [x['name'] for x in measured if x['differences'] == 0]
        self.assertEqual(exact, ['created1-volatile0-snapshot0-o2g3', 'created1-volatile2-snapshot0-o2g3'])
        self.receipt('shape', words=38, frame=72, direct_C_match=True, guards=0,
            complete_source_profile_measurements=64, two_exact_forms=exact,
            selected_nonvolatile_arguments=True, packet_offset=52)

    def test_02_all_selector_bytes_payload_bits_failures_clobbers_and_padding(self):
        cases, coverage = 0, set()
        for selector, result, mode, phase in itertools.product(range(256), (0, CREATED), range(4), (0, 8)):
            memory, args = fixture(selector, PATTERNS[selector % 12], PATTERNS[(selector * 5 + 3) % 12], seed=selector)
            models = self.compare(memory, args, result, mode, phase)
            for model in models:
                coverage.update(model.visits)
            if result:
                packet = next(c[2] for c in models[0].calls if c[0] == 'copy')
                base = shared.STACK + phase - 0x48 + 0x34
                self.assertEqual(packet[5:8], bytes(memory[base + i] for i in range(5, 8)))
            cases += 1
        for first, second, result, mode, phase in itertools.product(PATTERNS, PATTERNS, (0, CREATED), range(4), (0, 8)):
            memory, args = fixture(0xA5, first, second)
            self.compare(memory, args, result, mode, phase)
            cases += 1
        self.assertEqual(cases, 6400)
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + 152, 4)) <= coverage)
        self.receipt('guest', cases=cases, all_selector_bytes=True, arbitrary_payload_bit_patterns=True,
            failure_and_success=True, nine_slot_creator_packets=True, all38_words_reached=True,
            full_modeled_states_equal=True, three_private_padding_bytes_untouched=True,
            outgoing_home_clobbers_and_before_copy_input_mutations=True)

    def test_03_public_and_guest_private_aliases_preserve_sequential_copies(self):
        cases = 0
        for phase, mode, offset, destination in itertools.product((0, 8), range(4),
                (None, 0x30, 0x38, 0x3C, -0x14, -0x10, -0xC, -8, 0, 4), (CREATED, ACTOR, DATA, 'self', 'plus4')):
            data = DATA if offset is None else ACTOR + offset if offset >= 0x30 else shared.STACK + phase + offset
            result = shared.STACK + phase - 0x48 + 0x34 - 0x28 + (4 if destination == 'plus4' else 0) if isinstance(destination, str) else destination
            memory, args = fixture(0x81, 0x80000000, 0x7F812345, data=data, phase=phase)
            self.compare(memory, args, result, mode, phase)
            cases += 1
        self.assertEqual(cases, 400)
        self.receipt('aliases', cases=cases, actor_and_payload_destinations=True,
            guest_private_argument_homes_and_packet_aliases=True, forward_memcpy_overlap=True,
            private_partial_struct_overlap_not_portable_C_claim=True)

    def test_04_required_inputs_are_read_even_when_creation_fails(self):
        memory, args = fixture(0xFF, 0x12345678, 0x87654321)
        for missing in (ACTOR + 0x3B, *range(DATA, DATA + 8)):
            absent = dict(memory)
            del absent[missing]
            for words in (self.words, self.retail):
                with self.assertRaises((AssertionError, KeyError)):
                    PacketOracle(words, absent, args, 0).run()
        absent = {a: b for a, b in memory.items() if not CREATED - 16 <= a < CREATED + 240}
        self.compare(absent, args, result=0)
        self.receipt('lazy', required_actor_and_all_eight_payload_bytes=True,
            failure_skips_copy_and_requires_no_destination=True)

    def test_05_wrong_private_layout_and_semantic_mutations_are_effective(self):
        meta, wrong = source.compile_candidate(self.root, self.out, 'wrong-packet-layout', source.BASE)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (38, 72, 4))
        memory, args = fixture(0x87, 0x80000000, 0x7F812345)
        models = [PacketOracle(w, memory, args).run() for w in (self.retail, wrong)]
        self.assertNotEqual(state(models[0]), state(models[1]))
        self.assertNotEqual(models[0].calls[-1], models[1].calls[-1])
        for name, body in controls().items():
            _, words = source.compile_candidate(self.root, self.out, name, body)
            model = PacketOracle(words, memory, args).run()
            expected, calls = reference(memory, args)
            self.assertNotEqual((external(model.memory), model.calls), (external(expected), calls), name)
        self.receipt('controls', real_four_word_private_layout_negative=True, semantic_negatives=5,
            no_private_offset_guards_added=True)

    def test_06_complete_copied_owner_and_both_padders_keep_neighbors_and_pools(self):
        objects = [compile_owner(self.root, self.out, body, 'owner-' + name)
            for name, body in (('before', self.owner_before), ('after', self.owner_after))]
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
        self.assertEqual(target['size'], 152)
        raw, isolated, _ = parse_object(self.out / 'selected.o')
        start = isolated[source.FUNCTION]['value']
        self.assertEqual(padded[0][0][target['value']:target['value'] + 152], raw[start:start + 152])
        self.receipt('owner', neighbors=len(neighbors), both_complete_padders=True,
            pools_and_neighbor_relocations_unchanged=True, target_direct_words_preserved=True)

    def test_07_whole_linked_image_source_history_and_protected_data(self):
        current_source = (self.root / self.paths['source']).read_text()
        self.assertIn(current_source, (self.owner_before, self.owner_after))
        installed = current_source == self.owner_after
        expected = bytearray(self.before)
        if installed:
            offset = shared.elf_slot_offset(self.before, source.ENTRY, 152)
            expected[offset:offset + 152] = struct.pack('>38I', *self.retail)
            with patch.object(shared.screen, 'ENTRY', source.ENTRY):
                size_offset = shared.elf_symbol_size_offset(self.before, source.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected, size_offset)[0], 12)
            struct.pack_into('>I', expected, size_offset, 152)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        for name in set(self.paths) - {'source', 'elf'}:
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), before, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=installed, changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            only_target_slot_and_exact_size_field_changed=True, symbol_size_change=[12, 152] if installed else None,
            guards_profile_layout_conversion_rows_fixed=True, protected_data=data)

    def test_08_actual_native32_body_defined_bytes_and_canaries(self):
        fixture_c = '''typedef unsigned char u8;typedef signed char s8;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void *)0)
''' + source.OWNER_RECORD + source.PACKET + source.DECLARATIONS + '''
static union {u32 alignment;u8 bytes[256];} actor, input, output;
static u8 *result;static int calls, copies, error, mode;
void *func_15149130(s16 duration,s8 index,s8 kind,s8 origin,u8 active,u8 render,s32 size,u8 slot,s32 context){
 calls++;if(duration!=10||index!=7||kind!=0x23||origin!=-1||active!=1||render!=0x21||size!=16||slot!=255||context!=1)error=1;
 if(mode){actor.bytes[0x3B]=0x5A;*(u32 *)(input.bytes+16)=0x76543210;*(u32 *)(input.bytes+20)=0xFEDCBA98;}return result;}
void *memcpy(void *to,const void *from,unsigned int n){unsigned int i;copies++;if(n!=16)error=2;
 for(i=0;i<n;i++){((u8 *)to)[i]=((const u8 *)from)[i];}return to;}
''' + source.SELECTED + '''
int run(void){int selector,fail,changed,i;u32 first,second;u8 expected[256];
 if(sizeof(void*)!=4||sizeof(ActorPayload97AA0)!=16||sizeof(ObjectSelector97AA0)!=8)return 10;
 for(selector=0;selector<256;selector++)for(fail=0;fail<2;fail++)for(changed=0;changed<2;changed++){
  for(i=0;i<256;i++)actor.bytes[i]=input.bytes[i]=output.bytes[i]=expected[i]=0xA5;
  actor.bytes[0x3B]=(u8)selector;first=(u32)selector*1664525u+0x80000000u;second=first^0x7F812345u;
  *(u32 *)(input.bytes+16)=first;*(u32 *)(input.bytes+20)=second;result=fail?NULL:output.bytes;mode=changed;calls=copies=error=0;
  if(!fail){*(u8 **)(expected+0x28)=actor.bytes;expected[0x2C]=(u8)selector;*(u32 *)(expected+0x30)=first;*(u32 *)(expected+0x34)=second;}
  func_1506AA48(actor.bytes,(PayloadPair97AA0 *)(input.bytes+16));
  if(error||calls!=1||copies!=!fail)return 11;
  for(i=0;i<256;i++)if((fail||i<0x2D||i>0x2F)&&output.bytes[i]!=expected[i])return 12;
 }return 0;}
void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
'''
        for profile in ('-O2', '-O0'):
            path = self.out / ('native-' + profile[1:] + '.c')
            path.write_text(fixture_c)
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)
        for name, body in controls().items():
            path = self.out / ('native-negative-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', '-O2', '-std=c99', '-fno-strict-aliasing',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0, name)
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=1024, actual_typed_body=True,
            defined_packet_bytes_and_all_destination_canaries=True, padding_contents_not_portably_fixed=True,
            five_semantic_controls_effective_in_native_execution=True)

    def test_09_original_table_dispatcher_creator_wrapper_and_memcpy(self):
        create = list(struct.unpack_from('>49I', self.rom, 0x1765E0))
        copy = list(struct.unpack_from('>11I', self.rom, 0x22EC0))
        functions, _, addresses = shared.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(create, functions['func_15149130'])
        self.assertEqual(copy, functions['memcpy'])
        self.assertEqual((addresses['func_15149130'], addresses['memcpy']),
            (source.compiler.SYMBOLS['func_15149130'], source.compiler.SYMBOLS['memcpy']))
        connected = {source.compiler.SYMBOLS['func_15149130'] + i * 4: w for i, w in enumerate(create)}
        connected.update({source.compiler.SYMBOLS['memcpy'] + i * 4: w for i, w in enumerate(copy)})
        cases, coverage = 0, set()
        for result, selector, phase, allocator_clobber in itertools.product((0, CREATED), (0, 128, 255), (0, 8), (0, 1)):
            memory, args = fixture(selector, 0x80000000, 0x7F812345)
            for address, value in ((ACTOR + 0x2C, 0x3F800000), (ACTOR + 0x30, 0x40000000),
                    (ACTOR + 0x34, 0x40400000), (0x800CC254, 0x40800000),
                    (0x800CC258, 0x40A00000), (0x800CC25C, 0x40C00000)):
                shared.put(memory, address, value)
            expected = dict(memory)
            for src, dst in ((ACTOR + 0x2C, 0x800D1560), (ACTOR + 0x30, 0x800D1564),
                    (ACTOR + 0x34, 0x800D1568), (0x800CC254, 0x800D1570),
                    (0x800CC258, 0x800D1574), (0x800CC25C, 0x800D1578)):
                shared.put(expected, dst, shared.read(expected, src))
            expected, _ = reference(expected, args, result, 0, phase - 0x18, connected=True)
            models = []
            for words in (self.retail, self.words):
                code = dict(connected)
                code.update({source.ENTRY + i * 4: w for i, w in enumerate(words)})
                model = PacketOracle(self.parent, memory, (ACTOR, 9, DATA), result, allocator_clobber,
                    phase, PARENT, connected=code, parent=True).run()
                self.assertEqual(external(model.memory), external(expected))
                self.assertIn(('callback', (ACTOR, DATA)), model.calls)
                self.assertIn(('create', CREATE_ARGS), model.calls)
                self.assertIn(('allocate', (0x23, 1, 56, 1, 255, 1)), model.calls)
                self.assertEqual(sum(c[0] == 'copy' for c in model.calls), bool(result))
                coverage.update(model.visits)
                models.append(model)
            self.assertEqual(state(models[0]), state(models[1]))
            cases += 1
        self.assertEqual(cases, 24)
        self.assertTrue(set(range(source.compiler.SYMBOLS['memcpy'], source.compiler.SYMBOLS['memcpy'] + 44, 4)) <= coverage)
        self.receipt('connected', cases=cases, real_table_index=9, original_dispatcher_words=38,
            original_creator_words=49, original_memcpy_words=11, full_modeled_states_equal=True,
            generic_allocator_and_bzero_bounded=True, full_hardware_gameplay_not_claimed=True)

    def test_10_independent_original_links_and_three_rebased_layouts(self):
        block = (self.root / self.paths['assembly']).read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        assembly = self.out / 'original.s'
        assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
            'endlabel ' + source.FUNCTION + '\n')
        original = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(original), str(assembly)], check=True, capture_output=True)
        cases = 0
        for index, delta in enumerate((0, 0x200000, 0x400000)):
            entry = source.ENTRY + delta
            symbols = {k: v + delta for k, v in source.compiler.SYMBOLS.items()}
            script = self.out / ('rebase-' + str(index) + '.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(original)], check=True, capture_output=True)
            original_words = list(struct.unpack_from('>38I', source.compiler.sections(elf)['.text'][1]))
            with patch.object(source, 'ENTRY', entry), patch.object(source.compiler, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'rebase-source-' + str(index))
                self.assertEqual(emitted, original_words)
                for result, phase, selector in itertools.product((0, CREATED), (0, 8), (0, 128, 255)):
                    memory, args = fixture(selector, 0x80000000, 0x7F812345)
                    models = [PacketOracle(w, memory, args, result, phase=phase, entry=entry, symbols=symbols).run()
                        for w in (original_words, emitted)]
                    self.assertEqual(state(models[0]), state(models[1]))
                    expected, calls = reference(memory, args, result, phase=phase)
                    self.assertEqual((external(models[1].memory), models[1].calls), (external(expected), calls))
                    cases += 1
        self.receipt('rebases', independent_original_source_links=3, cases=cases,
            complete_words_and_full_modeled_states_equal=True, both_JAL_relocations=True)

    def test_11_all_fired_access_cuts_and_wrong_layout_negative(self):
        domains = pairs = 0
        for phase, mode, result, alias in itertools.product((0, 8), range(4), (0, CREATED),
                (DATA, ACTOR + 0x38, 'packet', 'payload', 'home0', 'home1')):
            data = {'packet': shared.STACK + phase - 0x14, 'payload': shared.STACK + phase - 0xC,
                'home0': shared.STACK + phase, 'home1': shared.STACK + phase + 4}.get(alias, alias)
            memory, args = fixture(0x87, 0x80000000, 0x7F812345, data=data)
            completed = [FaultOracle(w, memory, args, result, mode, phase).run() for w in (self.retail, self.words)]
            self.assertEqual([m.accesses for m in completed], [18, 18])
            for cut in range(18):
                models = []
                for words in (self.retail, self.words):
                    model = FaultOracle(words, memory, args, result, mode, phase, fault=cut)
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    models.append(model)
                self.assertEqual(state(models[0]), state(models[1]))
                self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                pairs += 1
            domains += 1
        self.assertEqual((domains, pairs), (96, 1728))
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-layout-fault', source.BASE)
        memory, args = fixture()
        models = []
        for words in (self.retail, wrong):
            model = FaultOracle(words, memory, args, fault=5)
            with self.assertRaises(AccessFault):
                model.run()
            self.assertEqual(model.accesses, 5)
            models.append(model)
        self.assertNotEqual(state(models[0]), state(models[1]))
        self.receipt('faults', domains=domains, fired_pairs=pairs, all_full_modeled_states_equal=True,
            wrong_layout_cut5_negative_effective=True, provider_accesses_not_counted_as_own_instructions=True,
            hardware_PC_BD_full_FCSR_not_claimed=True)

    def test_12_whole_image_source_and_guard_corruption_controls(self):
        read, read_text = Path.read_bytes, Path.read_text
        elf = self.root / self.paths['elf']
        data = elf.read_bytes()
        target = shared.elf_slot_offset(data, source.ENTRY, 152)
        for offset in (0, target, target + 151, shared.elf_slot_offset(data, PARENT, 152), len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == elf else read(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_whole_linked_image_source_history_and_protected_data()
        path = self.root / self.paths['source']
        original = path.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: original + '\n' if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_whole_linked_image_source_history_and_protected_data()
        path = self.root / self.paths['guards']
        bad = path.read_bytes() + b'\n'
        with patch.object(Path, 'read_bytes', lambda p, *a, **k: bad if p == path else read(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_whole_linked_image_source_history_and_protected_data()
        self.receipt('image-controls', target_parent_header_tail_source_guard_mutations_all_effective=True)


if __name__ == '__main__':
    unittest.main()
