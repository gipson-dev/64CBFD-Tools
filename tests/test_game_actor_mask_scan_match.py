"""Signed snapshot scan, callback ABI, literal owner/image and bounded faults."""
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

from tools.experiments import game_actor_mask_scan_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

STACK, TABLE, PARENT, PARENT_ROM = image.STACK, 0x80086110, 0x1506AC8C, 0x9813C
POSITIVE = sorted(set(range(4096)) | {1 << i for i in range(31)} |
    {0x7FFFFFFF ^ (1 << i) for i in range(31)} | {0x7FFFFFFF} |
    {(i * 1664525 + 1013904223) & 0x7FFFFFFF for i in range(64)})
NEGATIVE = (0x80000000, 0xFFFFFFFF, 0x80000001, 0xFFFFFFFE,
    0x87654321, 0xA55A00FF, 0xC0000000, 0xF000000F)


def controls():
    return {
        'unsigned-mask': source.SELECTED.replace('s32 mask =', 'u32 mask ='),
        'wrong-stride': source.SELECTED.replace('0x32C', '0x330'),
        'wrong-vector': source.SELECTED.replace('actor, D_800D1560,', 'actor, D_800D1570,'),
        'wrong-flag': source.SELECTED.replace('0xFF, 1', '0xFE, 1'),
        'selected-only-step': source.SELECTED.replace('        actor += 0x32C;\n', '').replace(
            '0xFF, 1);', '0xFF, 1);\n            actor += 0x32C;'),
        'live-mask': source.SELECTED.replace('0xFF, 1);', '0xFF, 1);\n            mask = D_800CC260;'),
    }


def fixture(mask=5, symbols=None, phase=0):
    s = symbols or source.SYMBOLS
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x180, 0x100)}
    for base in (s['D_800CC260'], s['D_800D1560'], s['D_800D1570'], TABLE):
        memory.update({base + i: 0xA5 for i in range(64)})
    memory.update({(s['D_800CC2D0'] + i * 0x32C + 0x3B) & 0xFFFFFFFF: 0xA5 for i in range(96)})
    put(memory, s['D_800CC260'], mask)
    put(memory, TABLE + 10 * 4, source.ENTRY)
    return memory


def effects(mode, count, args, symbols):
    if mode == 1 and count == 1:
        return ((symbols['D_800CC260'], 0, 4),)
    if mode == 2:
        return ((symbols['D_800CC260'], 0xFFFFFFFF, 4),
            (symbols['D_800D1560'], count * 0x1020304 & 0xFFFFFFFF, 4))
    if mode == 3:
        return (((args[0] + 0x3B) & 0xFFFFFFFF, count & 255, 1),
            (symbols['D_800D1570'], count ^ 0x12345678, 4))
    return ()


def reference(memory, mode=0, symbols=None, limit=None, initial=None):
    s, result, calls = symbols or source.SYMBOLS, dict(memory), []
    value = signed(read(result, s['D_800CC260'])) if initial is None else signed(initial)
    # Enumerate finite bit positions independently; negative fixtures stop at a declared call boundary.
    for slot in range(31 if value >= 0 else 96):
        if (value >> slot) & 1:
            args = ((s['D_800CC2D0'] + slot * 0x32C) & 0xFFFFFFFF,
                s['D_800D1560'], s['D_800D1570'], 0, 255, 1)
            calls.append((s['func_15137610'], *args))
            if limit is not None and len(calls) == limit:
                break
            for address, data, size in effects(mode, len(calls), args, s):
                put(result, address, data, size)
    return external(result), calls


class CallBoundary(Exception):
    pass


class AccessFault(Exception):
    pass


class MaskOracle(TriangleOracle):
    def __init__(self, words, memory, phase=0, mode=0, symbols=None,
            entry=source.ENTRY, arguments=(0x12345678, 0xFEDCBA98), connected=None,
            limit=None, fault=None):
        self.own_instruction = False
        self.accesses, self.fault = 0, fault
        super().__init__(words, memory, phase=phase, entry=entry,
            arguments=arguments, connected=connected)
        self.symbols, self.mode, self.limit, self.phase = symbols or source.SYMBOLS, mode, limit, phase
        self.callbacks = []

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
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording:
            self.access()
        super().put(address, value, size)

    def record_call(self, target):
        if target == source.ENTRY:
            self.callbacks.append(self.arguments(2))
            return
        assert target == self.symbols['func_15137610'], hex(target)
        args = self.arguments(6)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))
        if self.limit is not None and len(self.calls) == self.limit:
            raise CallBoundary

    def hook(self, target):
        assert target == self.symbols['func_15137610']
        for address, value, size in effects(self.mode, len(self.calls), self.calls[-1][1:], self.symbols):
            self.put(address, value, size)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        if self.mode == 3:
            for i in range(2):
                self.put(STACK + self.phase + i * 4, 0xC5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]


def state(model):
    return (model.memory, model.r, model.f, model.lo, model.condition,
        model.events, model.calls, model.callbacks, model.accesses)


class GameActorMaskScanMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-mask-scan-match-test'
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
        assert cls.baseline['source'] == 'e7a27f6806b4971ae868dfd528d584d29f2411fdcb9a5478695119cf398b3c3e'
        assert cls.baseline['elf'] == '66e3339437aff16ec21f47afc3029e67deaa476a3b7571887d1e25b5b5365f90'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = source.recovered_owner(cls.owner_before)
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>39I', cls.rom, source.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, mask=5, mode=0, phase=0, symbols=None, entry=source.ENTRY,
            bodies=None, arguments=(0x12345678, 0xFEDCBA98), initial=None):
        memory = fixture(mask, symbols, phase)
        expected, calls = reference(memory, mode, symbols, initial=initial)
        models = [MaskOracle(words, memory, phase, mode, symbols, entry, arguments).run()
            for words in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual((external(model.memory), model.calls), (expected, calls))
            reads = [e for e in public(model.events) if e[0] == 'R']
            address = (symbols or source.SYMBOLS)['D_800CC260']
            expected_reads = [] if STACK - 0x600 <= address < STACK + 0x140 else [
                ('R', address, 4, mask if initial is None else initial)]
            self.assertEqual(reads, expected_reads)
        self.assertEqual(state(models[0]), state(models[1]))
        return models

    def test_01_direct_complete_slot_and_source_profile_bank(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (39, 48, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        measured = json.loads((self.root / 'conker/build/game-actor-mask-scan/measurements.json').read_text())
        exact = [m for m in measured if m['differences'] == 0]
        self.assertEqual(len(measured), 96)
        self.assertEqual(len(exact), 24)
        self.assertEqual({m['profile'] for m in exact}, {'o2g3'})
        self.assertEqual(self.meta['relocations'][0x68], [('R_MIPS_26', 'func_15137610')])
        self.receipt('shape', words=39, frame=48, direct_C=True, guards=0,
            measurements=96, exact_O2_g3_forms=24, selected_plain_nonvolatile=True)

    def test_02_positive_bits_snapshot_mutations_and_complete_word_coverage(self):
        cases, seen = 0, set()
        for mask, mode, phase in itertools.product(POSITIVE, range(4), (0, 8)):
            for model in self.compare(mask, mode, phase):
                seen.update(model.visits)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 156, 4)))
        self.receipt('guest', cases=cases, low_12_bit_masks=4096, positive_patterns=len(POSITIVE),
            all_31_single_bits_and_complements=True, provider_modes=4, SP_phases=2,
            full_modeled_states_and_independent_external_reference=True, all_39_words_reached=True)

    def test_03_negative_masks_keep_signed_nontermination_prefix(self):
        cases = 0
        for mask, mode, phase in itertools.product(NEGATIVE, range(4), (0, 8)):
            memory = fixture(mask, phase=phase)
            expected, calls = reference(memory, mode, limit=64)
            models = [MaskOracle(w, memory, phase, mode, limit=64) for w in (self.retail, self.words)]
            for model in models:
                with self.assertRaises(CallBoundary):
                    model.run()
                self.assertEqual((external(model.memory), model.calls), (expected, calls))
                self.assertGreaterEqual(model.calls[-1][1], source.SYMBOLS['D_800CC2D0'] + 63 * 0x32C)
            self.assertEqual(state(models[0]), state(models[1]))
            cases += 1
        self.receipt('negative-prefix', cases=cases, calls_per_prefix=64,
            sign_extension_after_bit31=True, global_mutation_does_not_end_snapshot_scan=True,
            finite_observation_only=True, full_infinite_execution_or_hardware_timing_not_claimed=True)

    def test_04_ignored_arguments_no_vector_dereference_and_home_aliases(self):
        cases = 0
        for mask, phase in itertools.product((0, 1, 5, 0x40000000), (0, 8)):
            memory = {a: v for a, v in fixture(mask).items() if STACK - 0x180 <= a < STACK + 0x100 or
                source.SYMBOLS['D_800CC260'] <= a < source.SYMBOLS['D_800CC260'] + 4}
            models = [MaskOracle(w, memory, phase, arguments=(0xDEADCAFE, 0x80000001)).run() for w in (self.retail, self.words)]
            self.assertEqual(state(models[0]), state(models[1]))
            self.assertEqual(models[0].calls, reference(memory)[1])
            cases += 1
        for phase in (0, 8):
            for home, value in ((0, 5), (4, 2)):
                symbols = dict(source.SYMBOLS, D_800CC260=STACK + phase + home)
                with patch.object(source, 'SYMBOLS', symbols):
                    _, words = source.compile_candidate(self.root, self.out, 'home%d-phase%d' % (home, phase))
                original = self.rebased_original(source.ENTRY, symbols, 'home%d-phase%d' % (home, phase))
                self.compare(0xA5A5A5A5, 3, phase, symbols, bodies=(original, words), arguments=(5, 2), initial=value)
                cases += 1
        self.receipt('inputs', cases=cases, ignored_unmapped_incoming_arguments=True,
            vectors_and_actors_not_dereferenced_by_scan=True, incoming_home_global_aliases=True,
            guest_aliases_not_portable_C_guarantees=True)

    def test_05_effective_compiled_semantic_and_unsigned_controls(self):
        for name, body in controls().items():
            _, wrong = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            mask, mode = (0x80000000, 1) if name == 'unsigned-mask' else (5, 1)
            memory = fixture(mask)
            model = MaskOracle(wrong, memory, mode=mode, limit=64)
            try:
                model.run()
            except (CallBoundary, AssertionError):
                pass
            expected, calls = reference(memory, mode, limit=64 if name == 'unsigned-mask' else None)
            self.assertNotEqual((external(model.memory), model.calls), (expected, calls), name)
        self.receipt('controls', effective_compiled_controls=list(controls()),
            unsigned_negative_scan_is_not_equivalent=True)

    def test_06_complete_owner_and_both_padders(self):
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
        self.assertEqual(target['size'], 156)
        raw, isolated, _ = parse_object(self.out / 'selected.o')
        start = isolated[source.FUNCTION]['value']
        self.assertEqual(padded[0][0][target['value']:target['value'] + 156], raw[start:start + 156])
        self.receipt('owner', neighbors=len(neighbors), both_complete_padders=True,
            pools_neighbor_bytes_relocations_unchanged=True, preceding_direct_creator_unchanged=True)

    def test_07_literal_whole_image_and_protected_history(self):
        current_source = (self.root / self.paths['source']).read_text()
        self.assertIn(current_source, (self.owner_before, self.owner_after))
        expected = bytearray(self.before)
        if current_source == self.owner_after:
            offset = image.elf_slot_offset(self.before, source.ENTRY, 156)
            expected[offset:offset + 156] = struct.pack('>39I', *self.retail)
            with patch.object(image.screen, 'ENTRY', source.ENTRY):
                size = image.elf_symbol_size_offset(self.before, source.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected, size)[0], 12)
            struct.pack_into('>I', expected, size, 156)
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
            only_target156_bytes_and_named_size12_to156=True, protected_data=data)

    def test_08_actual_native32_snapshot_and_negative_prefix(self):
        fixture_c = '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
static s32 D_800CC260;static u8 D_800CC2D0[96*812],D_800D1560[16],D_800D1570[16];
static int mode,count,error,negative;static u32 original;static void *escape[5];
s32 func_15137610(u8 *actor,u8 *first,u8 *second,s32 zero,u8 flag,s32 context){
 u32 slot=0,ordinal=0;
 for(slot=0;slot<96;slot++){u32 bit=slot<32?(original>>slot)&1:original>>31;
  if(bit){if(ordinal==(u32)count)break;ordinal++;}}
 if(actor!=D_800CC2D0+slot*812||first!=D_800D1560||second!=D_800D1570||zero||flag!=255||context!=1)error=1;
 count++;if(count==64)__builtin_longjmp(escape,1);
 if(mode==1&&count==1)D_800CC260=0;
 if(mode==2){D_800CC260=-1;D_800D1560[0]=(u8)count;}
 if(mode==3){D_800D1570[0]=(u8)count;}return 0;
}
''' + source.SELECTED + '''
static void (*volatile invoke)(s32,s32)=func_1506AAE0;
static int check(u32 mask){u32 i,wanted=0;original=mask;D_800CC260=(s32)mask;count=error=0;
 negative=(mask>>31)!=0;
 if(__builtin_setjmp(escape)==0){invoke(0x12345678,(s32)0xFEDCBA98u);if(negative)return 10;}
 else {if(!negative||count!=64||error)return 11;return 0;}
 for(i=0;i<31;i++)wanted+=(mask>>i)&1;
 if(error||(u32)count!=wanted){return 12;}return 0;}
int run(void){u32 i;int result;if(sizeof(void*)!=4||sizeof(s32)!=4)return 13;
 for(mode=0;mode<4;mode++){
  for(i=0;i<65536;i++){result=check(i);if(result)return result;}
  for(i=0;i<31;i++){result=check(1u<<i);if(result)return result;
   result=check(0x7FFFFFFFu^(1u<<i));if(result)return result;}
  {static const u32 masks[]={0x80000000u,0xFFFFFFFFu,0x80000001u,0xFFFFFFFEu,0x87654321u,0xA55A00FFu,0xC0000000u,0xF000000Fu};
   for(i=0;i<8;i++){result=check(masks[i]);if(result)return result;}}
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, success in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode == 0, success, (name, result.returncode))
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=4 * (65536 + 62 + 8),
            actual_typed_source_and_all_low16_masks=True, six_effective_compiled_negatives=True,
            negative_observation_stops_at_actual_callback64=True, backed_32_bit_pointer_domain_only=True)

    def test_09_original_indirect_dispatcher_and_table_entry(self):
        parent = list(struct.unpack_from('>38I', self.rom, PARENT_ROM))
        functions, _, addresses = image.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(addresses['func_1506AC8C'], PARENT)
        self.assertEqual(functions['func_1506AC8C'], list(struct.unpack_from('>41I', self.rom, PARENT_ROM)))
        self.assertEqual(functions['func_1506AC8C'][38:], [0, 0, 0])
        table_offset = image.elf_slot_offset(self.before, TABLE + 10 * 4, 4)
        self.assertEqual(self.before[table_offset:table_offset + 4], struct.pack('>I', source.ENTRY))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22ABF8)[0], source.ENTRY)
        seen, cases = set(), 0
        for mask, mode, phase in itertools.product((0, 1, 5, 0x40000000, 0x7FFFFFFF), range(4), (0, 8)):
            memory = fixture(mask)
            actor = 0x21000
            memory.update({actor + i: (i * 13 + 0xA5) & 255 for i in range(64)})
            memory.update({0x800CC254 + i: (i * 17 + 0x35) & 255 for i in range(12)})
            initialized = dict(memory)
            for i in range(3):
                put(initialized, source.SYMBOLS['D_800D1560'] + i * 4, read(memory, actor + 0x2C + i * 4))
                put(initialized, source.SYMBOLS['D_800D1570'] + i * 4, read(memory, 0x800CC254 + i * 4))
            expected, calls = reference(initialized, mode)
            models = []
            for body in (self.retail, self.words):
                connected = dict(zip(range(source.ENTRY, source.ENTRY + 156, 4), body))
                model = MaskOracle(parent, memory, phase, mode, entry=PARENT,
                    arguments=(actor, 10, 0xFEDCBA98), connected=connected).run()
                self.assertEqual(model.callbacks, [(actor, 0xFEDCBA98)])
                self.assertEqual((external(model.memory), model.calls), (expected, calls))
                seen.update(model.visits)
                models.append(model)
            self.assertEqual(state(models[0]), state(models[1]))
            cases += 1
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + 156, 4)) <= seen)
        self.receipt('connected', cases=cases, actual_original_dispatcher38_words=True,
            complete_original_12_byte_alignment_tail_checked=True, actual_table_word_verified=True,
            parent_vector_setup_compared_to_independent_storage=True,
            callback_table_index10_and_two_forwarded_homes=True, full_target_coverage=True,
            downstream_vector_provider_is_bounded_not_emulated=True)

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
        return list(struct.unpack_from('>39I', source.compiler.sections(elf)['.text'][1]))

    def test_10_independent_original_and_three_carry_boundary_links(self):
        cases = 0
        for index, (entry, mask, actors, first, second) in enumerate(((source.ENTRY, 0x800CC260, 0x800CC2D0, 0x800D1560, 0x800D1570),
                (0x15207FF0, 0x80107FFC, 0x80118004, 0x80207FFC, 0x80218004),
                (0x15318004, 0x80218004, 0x80207FFC, 0x80318004, 0x80307FFC))):
            symbols = dict(D_800CC260=mask, D_800CC2D0=actors, D_800D1560=first,
                D_800D1570=second, func_15137610=source.SYMBOLS['func_15137610'] + index * 0x200000)
            original = self.rebased_original(entry, symbols, 'rebase-' + str(index))
            with patch.object(source, 'ENTRY', entry), patch.object(source, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'rebase-source-' + str(index))
            self.assertEqual(original, emitted)
            for value, mode, phase in itertools.product((0, 1, 5, 0x40000000, 0x7FFFFFFF), range(4), (0, 8)):
                self.compare(value, mode, phase, symbols, entry, bodies=(original, emitted))
                cases += 1
        self.receipt('rebases', independent_original_source_links=3, cases=cases,
            actual_HI_LO_carry_boundaries_and_JAL=True, full_words_and_modeled_states=True)

    def test_11_fired_own_access_cuts_and_profile_frame_negative(self):
        pairs, domains = 0, 0
        for mask, mode, phase in itertools.product((0, 1, 2, 5, 0x40000000, 0x7FFFFFFF), range(4), (0, 8)):
            memory = fixture(mask)
            complete = MaskOracle(self.words, memory, phase, mode).run()
            self.assertEqual(complete.accesses, 13 + 2 * mask.bit_count())
            for cut in range(complete.accesses):
                models = [MaskOracle(w, memory, phase, mode, fault=cut) for w in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                self.assertEqual(state(models[0]), state(models[1]))
                self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                pairs += 1
            domains += 1
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-O1-frame', profile='o1g3')
        models = [MaskOracle(w, fixture(), fault=0) for w in (self.retail, wrong)]
        for model in models:
            with self.assertRaises(AccessFault):
                model.run()
        self.assertNotEqual(state(models[0]), state(models[1]))
        self.receipt('faults', domains=domains, fired_pairs=pairs, complete_modeled_states=True,
            provider_reads_writes_not_counted_as_encoded_accesses=True, O1_frame_negative_effective=True,
            hardware_PC_BD_full_FCSR_not_claimed=True)

    def test_12_effective_whole_image_source_and_history_corruptions(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        path = self.root / self.paths['elf']
        data = path.read_bytes()
        target = image.elf_slot_offset(data, source.ENTRY, 156)
        for offset in (0, target, target + 155, image.elf_slot_offset(data, 0x1506AA48, 152), len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_literal_whole_image_and_protected_history()
        path = self.root / self.paths['source']
        bad_text = path.read_text() + '\n'
        with patch.object(Path, 'read_text', lambda p, *a, **k: bad_text if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_whole_image_and_protected_history()
        path = self.root / self.paths['guards']
        bad_bytes = path.read_bytes() + b'\n'
        with patch.object(Path, 'read_bytes', lambda p, *a, **k: bad_bytes if p == path else read_bytes(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_whole_image_and_protected_history()
        self.receipt('image-controls', target_parent_header_tail_source_guard_mutations_effective=True)


if __name__ == '__main__':
    unittest.main()
