"""Complete leaf semantics, guarded scheduling, public aliases and closed image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from tools.tests import remaining_donor_checkpoint as donor_checkpoint
from unittest.mock import patch

from tools.experiments import game_actor_threshold_flags_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests import test_game_actor_burst_consumer_match as consumer
from tools.tests import test_game_actor_effect_packet_match as effect
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

ACTOR, CLOCK = 0x21000, source.SYMBOLS['D_800BE9E4']
BASELINE_ELF = '4e8749bc86fc0700b3236924fcf7c087d3f741cd969d632a70482e34ab320df4'
MODES = ((7, 33, -7), (-7, -32768, 32767), (32767, 0, -32768), (32767, 32767, 32767))
VALUES = (-32768, -32767, -8, -7, -6, -1, 0, 1, 6, 7, 8, 32, 33, 34, 32766, 32767)


def expected_threshold_image(before, words):
    expected = bytearray(before)
    offset = image.elf_slot_offset(before, source.ENTRY, 188)
    expected[offset:offset + 188] = struct.pack('>47I', *words)
    with patch.object(image.screen, 'ENTRY', source.ENTRY):
        size = image.elf_symbol_size_offset(before, source.FUNCTION)
    if struct.unpack_from('>I', before, size)[0] != 12:
        raise ValueError('Expected original 12-byte threshold symbol')
    struct.pack_into('>I', expected, size, 188)
    return bytes(expected)


def installed_guards(before):
    words = [0] * 47
    words[0] = 0x84830038
    for offset, expected, _ in source.GUARDS:
        words[offset // 4] = expected
    return before + effect.csv_rows(source.guard_rows(words, {})).encode('ascii')


def half(value):
    return value - 65536 if value & 32768 else value


def fixture(value=-8, mode=0, clock=0xFFFFFFFF, actor=ACTOR, seed=0):
    memory = {producer.STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    memory.update({actor + i: (i * 13 + seed * 17 + 0xA5) & 255 for i in range(-16, 0x90)})
    for offset, number in ((0x34, 32767), (0x36, -32768), (0x38, value), (0x44, 0xA5FE),
            (0x50, MODES[mode][0]), (0x52, -32767 + seed), (0x54, MODES[mode][1]),
            (0x56, 127 + seed), (0x58, MODES[mode][2]), (0x5A, -32768 + seed)):
        put(memory, actor + offset, number, 2)
    put(memory, CLOCK, clock)
    return memory


def reference(memory, actor=ACTOR):
    result = dict(memory)
    value = half(read(result, actor + 0x38, 2))
    if value < half(read(result, actor + 0x54, 2)):
        put(result, actor + 0x3F, value * half(read(result, actor + 0x56, 2)), 1)
    if value < half(read(result, actor + 0x58, 2)):
        delta = (half(read(result, actor + 0x5A, 2)) * read(result, CLOCK)) & 0xFFFFFFFF
        axis0, axis1 = (half(read(result, actor + offset, 2)) for offset in (0x34, 0x36))
        put(result, actor + 0x34, axis0 + delta, 2)
        put(result, actor + 0x36, axis1 + delta, 2)
        value = half(read(result, actor + 0x38, 2))
    if value < half(read(result, actor + 0x50, 2)):
        flags = read(result, actor + 0x44, 2)
        put(result, actor + 0x2F, 0x15, 1)
        put(result, actor + 0x44, flags | 0x201, 2)
        intensity = value * half(read(result, actor + 0x52, 2))
        put(result, actor + 0x14, 0xC000F)
        for offset in (0x42, 0x41, 0x40):
            put(result, actor + offset, intensity, 1)
    return result


class ThresholdOracle(producer.BurstOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, fault=None):
        super().__init__(words, memory, actor=actor, phase=phase, symbols=source.SYMBOLS,
            entry=source.ENTRY, arguments=(actor, 0x8765ABCD))
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = consumer.TrackedCode(self.code, self)

    def execute(self, word):
        super().execute(word)
        if word >> 26 == 0 and word & 63 == 25:
            self.hi = ((self.r[word >> 21 & 31] * self.r[word >> 16 & 31]) >> 32) & 0xFFFFFFFF

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 188:
            if self.accesses == self.root_fault:
                raise consumer.AccessBoundary
            self.accesses += 1


class GameActorThresholdFlagsMatchTests(unittest.TestCase):
    write_rows = staticmethod(consumer.GameActorBurstConsumerMatchTests.write_rows)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-threshold-flags-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(owner=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', assembly='conker/asm/1D43B0.s',
            layout='conker/retail_layout.us.txt', table='conker/asm/data/22FF90.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == BASELINE_ELF
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.meta, cls.raw = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.object = cls.out / 'selected.o'
        text, _, cls.relocations = parse_object(cls.object)
        cls.object_words = list(struct.unpack_from('>47I', text))
        cls.rows = source.guard_rows(cls.object_words, cls.relocations)
        cls.guards = cls.out / 'guards.csv'
        cls.write_rows(cls.guards, cls.rows)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>47I', cls.rom, source.ROM))
        block = (cls.out / 'before-assembly').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        cls.asm = cls.out / 'target.s'
        cls.asm.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
            'endlabel ' + source.FUNCTION + '\n')
        cls.layout = cls.out / 'layout.csv'
        cls.layout.write_text('section,filename,function,address,end\n'
            'game,generated_1D43B0,func_151A77C0,0x151A77C0,0x151A787C\n')
        cls.original = cls.assemble('original', cls.asm.read_text())
        cls.padded = [cls.assemble('padded%d' % index, assembly) for index, assembly in enumerate((
            emit_padded_assembly(cls.object, cls.asm, filename='generated_1D43B0', word_patches_path=cls.guards),
            pad_c_object.emit_padded_assembly(cls.object, cls.layout, 'generated_1D43B0', word_patches_path=cls.guards)))]
        cls.words = cls.link(cls.padded[0], 'qualified')

    @classmethod
    def assemble(cls, name, assembly):
        path = cls.out / (name + '.s')
        path.write_text(assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
            check=True, capture_output=True)
        return obj

    @classmethod
    def link(cls, obj, name, entry=source.ENTRY, clock=CLOCK):
        script = cls.out / (name + '.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
            '--defsym=D_800BE9E4=0x%X' % clock, '-o', str(elf), str(obj)], check=True, capture_output=True)
        return list(struct.unpack_from('>47I', sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_both_actual_padders_and_independent_data_carries(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (47, 0, 26, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.relocations, {0xC: [('R_MIPS_HI16', 'D_800BE9E4')],
            0x44: [('R_MIPS_LO16', 'D_800BE9E4')]})
        for index, (entry, clock) in enumerate(((source.ENTRY, CLOCK), (0x15207FF0, 0x90007FFC),
                (0x15218008, 0x91008004), (0x15328000, 0x9200FFFF))):
            original = self.link(self.original, 'original%d' % index, entry, clock)
            for pad, obj in enumerate(self.padded):
                self.assertEqual(self.link(obj, 'padded%d-%d' % (pad, index), entry, clock), original)
                self.assertEqual(parse_object(obj)[1][source.FUNCTION]['size'], 188)
                self.assertEqual(parse_object(obj)[2], self.relocations)
        self.receipt('shape', words=47, frame=0, raw_differences=26, guards=26,
            actual_padders=2, independent_links=4, original_HI_LO_carries=True)

    def test_02_all_stale_word_and_relocation_controls_fire(self):
        checks = 0
        for index in range(len(self.rows)):
            for field, bad in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_26:wrong_symbol')):
                rows = [dict(row) for row in self.rows]
                rows[index][field] = bad
                path = self.out / 'corrupt-guards.csv'
                self.write_rows(path, rows)
                for emit in (
                        lambda: emit_padded_assembly(self.object, self.asm, filename='generated_1D43B0', word_patches_path=path),
                        lambda: pad_c_object.emit_padded_assembly(self.object, self.layout, 'generated_1D43B0', word_patches_path=path)):
                    with self.assertRaisesRegex(ValueError, 'stale word patch|stale relocations'):
                        emit()
                    checks += 1
        self.receipt('guards', fired_controls=checks, no_relocation_guards_or_extent_changes=True)

    def test_03_signed_thresholds_wrapping_semantics_and_every_word(self):
        cases, seen = 0, set()
        for value, mode, clock, phase in itertools.product(VALUES, range(4),
                (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF), (0, 8)):
            memory = fixture(value, mode, clock, seed=cases & 255)
            expected = reference(memory)
            models = [ThresholdOracle(body, memory, phase=phase).run() for body in (self.retail, self.words, self.raw)]
            for model in models:
                self.assertEqual(model.memory, expected)
                self.assertEqual(model.calls, [])
                self.assertEqual(model.r[29], producer.STACK + phase)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 188, 4)))
        self.receipt('guest', cases=cases, all47_words_reached=True,
            signed_strict_thresholds_and_low_byte_half_word_wrapping=True,
            raw_public_semantics_and_guarded_complete_states=True)

    def test_04_fired_access_prefixes_public_clock_aliases_and_raw_schedule_witness(self):
        cuts, aliases, witnesses = 0, 0, 0
        for actor, mode in itertools.product((ACTOR, *(CLOCK - offset for offset in
                (0x14, 0x34, 0x38, 0x3C, 0x40, 0x44, 0x50, 0x54, 0x58, 0x5C))), range(4)):
            memory = fixture(actor=actor, mode=mode, clock=0xFFFFFFFF)
            complete = ThresholdOracle(self.retail, memory, actor).run()
            for body in (self.words, self.raw):
                self.assertEqual(ThresholdOracle(body, memory, actor).run().memory, reference(memory, actor))
            aliases += actor != ACTOR
            for cut in range(complete.accesses):
                models = [ThresholdOracle(body, memory, actor, fault=cut) for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(consumer.AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                if actor == ACTOR and mode == 0:
                    raw = ThresholdOracle(self.raw, memory, actor, fault=cut)
                    with self.assertRaises(consumer.AccessBoundary):
                        raw.run()
                    witnesses += producer.complete_state(raw) != producer.complete_state(models[0])
                cuts += 1
        self.assertGreater(witnesses, 0)
        self.receipt('prefixes', fired_pairs=cuts, public_alias_domains=aliases,
            actual_PC_and_modeled_BD_preserved=True, raw_schedule_witnesses=witnesses,
            no_native_alias_or_hardware_EPC_claim=True)

    def test_05_complete_owner_neighbors_pools_and_existing_guards(self):
        before = (self.out / 'before-owner').read_text()
        old_obj, old_warnings = compile_owner(self.root, self.out, before, 'owner-before')
        new_obj, new_warnings = compile_owner(self.root, self.out, source.recovered_owner(before), 'owner-after')
        self.assertEqual(old_warnings, new_warnings)
        old_text, old_funcs, old_reloc = parse_object(old_obj)
        new_text, new_funcs, new_reloc = parse_object(new_obj)
        self.assertEqual(set(old_funcs), set(new_funcs))
        for name, old in old_funcs.items():
            new = new_funcs[name]
            if name == source.FUNCTION:
                self.assertEqual(new['size'], 188)
                self.assertEqual(new_text[new['value']:new['value'] + 188], struct.pack('>47I', *self.object_words))
                continue
            self.assertEqual(new['size'], old['size'], name)
            self.assertEqual(new_text[new['value']:new['value'] + new['size']], old_text[old['value']:old['value'] + old['size']], name)
            relative = lambda table, f: {at - f['value']: v for at, v in table.items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(new_reloc, new), relative(old_reloc, old), name)
        self.assertEqual(normalized_pools(new_obj), normalized_pools(old_obj))
        guards = self.out / 'owner-guards.csv'
        guards.write_bytes(installed_guards((self.out / 'before-guards').read_bytes()))
        for index, assembly in enumerate((emit_padded_assembly(new_obj, self.out / 'before-assembly',
                filename='generated_1D43B0', word_patches_path=guards),
                pad_c_object.emit_padded_assembly(new_obj, self.out / 'before-layout', 'generated_1D43B0', word_patches_path=guards))):
            text, funcs, _ = parse_object(self.assemble('owner-pad%d' % index, assembly))
            target = funcs[source.FUNCTION]
            self.assertEqual(text[target['value']:target['value'] + 188], parse_object(self.padded[index])[0][:188])
        self.receipt('owner', neighbors=len(old_funcs) - 1, raw_words_relative_relocs_pools_warnings_fixed=True,
            both_complete_padders_and_prior34_owner_guards_preserved=True)

    def test_06_six_effective_compiled_semantic_controls(self):
        controls = dict(strict=source.SELECTED.replace('value <', 'value <='),
            signed=source.SELECTED.replace('(s16 *)(params + 4)', '(u16 *)(params + 4)'),
            alpha=source.SELECTED.replace('arg0[0x3F]', 'arg0[0x3E]'),
            mask=source.SELECTED.replace('0x201', '0x200'),
            gate=source.SELECTED.replace('if (value < *(s16 *)params)', 'if (value >= *(s16 *)params)'),
            word=source.SELECTED.replace('0xC000F', '0xC000E'))
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            _, words = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            mismatches = 0
            for value, mode in itertools.product((-8, -7, 0, 7, 33, 32767), range(4)):
                memory = fixture(value, mode)
                mismatches += ThresholdOracle(words, memory).run().memory != reference(memory)
            self.assertGreater(mismatches, 0, name)
        self.receipt('controls', six_complete_source_semantic_controls_effective=True)

    def test_07_closed_image_source_guard_prefix_and_authentic_table20(self):
        before_owner = (self.out / 'before-owner').read_text()
        after = source.recovered_owner(before_owner)
        current_owner = (self.root / source.SOURCE).read_text()
        self.assertIn(current_owner, (before_owner, after))
        installed = current_owner == after
        before = (self.out / 'before-elf').read_bytes()
        expected = expected_threshold_image(before, self.retail) if installed else before
        current = donor_checkpoint.previous_input((self.root / self.paths['elf']).read_bytes(), self.paths['elf'], self.root)
        self.assertEqual(current, expected, 'Undeclared whole ELF change')
        for name in set(self.paths) - {'owner', 'elf'}:
            prior = (self.out / ('before-' + name)).read_bytes()
            expected_input = installed_guards(prior) if name == 'guards' and installed else prior
            if name == 'progress':
                from tools.experiments.game_byte_exact_donor_candidates import expected_donor_progress
                expected_input = expected_donor_progress(expected_input, self.root)
            self.assertEqual(donor_checkpoint.previous_input((self.root / self.paths[name]).read_bytes(), self.paths[name], self.root), expected_input, name)
        table_word = struct.unpack_from('>I', self.rom, 0x2314D8)[0]
        self.assertEqual(table_word, source.ENTRY)
        self.assertEqual(current[image.elf_slot_offset(current, 0x8008CA18, 4):][:4], struct.pack('>I', table_word))
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', installed=installed, changed_bytes=sum(a != b for a, b in zip(before, current)),
            protected_data=data, authentic_D_8008C9C8_index20=True, dispatcher_not_identified_or_claimed=True)

    def test_08_effective_closed_image_source_and_guard_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        elf = self.root / self.paths['elf']
        data = rb(elf)
        for address, size in ((source.ENTRY, 188), (0x151A7610, 432), (0x151A787C, 140), (0x8008CA18, 4)):
            bad = bytearray(data)
            bad[image.elf_slot_offset(data, address, size)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, v=bytes(bad): v if p == elf else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_closed_image_source_guard_prefix_and_authentic_table20()
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(data, source.FUNCTION)
        bad = bytearray(data)
        bad[size + 3] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == elf else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_guard_prefix_and_authentic_table20()
        before = (self.out / 'before-elf').read_bytes()
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(before, source.FUNCTION)
        bad = bytearray(before)
        bad[size + 3] ^= 1
        with self.assertRaisesRegex(ValueError, 'original 12-byte'):
            expected_threshold_image(bytes(bad), self.retail)
        guards = self.root / self.paths['guards']
        prior = rb(guards)
        with patch.object(Path, 'read_bytes', lambda p: prior + b'\n' if p == guards else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_guard_prefix_and_authentic_table20()
        owner = self.root / source.SOURCE
        prior_source = rt(owner)
        with patch.object(Path, 'read_text', lambda p, *a, **k: prior_source + '\n' if p == owner else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_guard_prefix_and_authentic_table20()
        self.receipt('image-controls', seven_current_and_one_baseline_size_corruptions_rejected=True, no_reset_or_exclusions=True)

    def test_09_native32_every_signed_state_both_profiles(self):
        native = '''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;
s32 D_800BE9E4;static u8 actor[128] __attribute__((aligned(16))),expected[128] __attribute__((aligned(16)));
''' + source.SELECTED + '''
static const s16 thresholds[4][3]={{7,33,-7},{-7,-32768,32767},{32767,0,-32768},{32767,32767,32767}};
static int run(void){u32 i,j,mode,clock,delta,intensity;s32 value;
if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 80;
for(mode=0;mode<4;mode++)for(clock=0;clock<2;clock++)for(i=0;i<65536;i++){
 for(j=0;j<128;j++)actor[j]=(j*13+i*17+0xA5)&255;
 *(s16*)(actor+0x34)=32767;*(s16*)(actor+0x36)=-32768;*(u16*)(actor+0x38)=i;
 *(u16*)(actor+0x44)=0xA5FE;
 *(s16*)(actor+0x50)=thresholds[mode][0];*(u16*)(actor+0x52)=i*257+1;
 *(s16*)(actor+0x54)=thresholds[mode][1];*(u16*)(actor+0x56)=i*13+127;
 *(s16*)(actor+0x58)=thresholds[mode][2];*(u16*)(actor+0x5A)=i*19+32768;
 D_800BE9E4=(s32)(clock?0x80000000u:0xFFFFFFFFu);
 for(j=0;j<128;j++)expected[j]=actor[j];
 value=i<32768?(s32)i:(s32)i-65536;
 if(value<thresholds[mode][1])expected[0x3F]=(u32)value*(u32)*(s16*)(expected+0x56);
 if(value<thresholds[mode][2]){delta=(u32)*(s16*)(expected+0x5A)*(u32)D_800BE9E4;
  *(u16*)(expected+0x34)=(u32)32767+delta;*(u16*)(expected+0x36)=0xFFFF8000u+delta;}
 if(value<thresholds[mode][0]){expected[0x2F]=0x15;*(u16*)(expected+0x44)|=0x201;
  intensity=(u32)value*(u32)*(s16*)(expected+0x52);*(u32*)(expected+0x14)=0xC000F;
  expected[0x40]=expected[0x41]=expected[0x42]=intensity;}
 func_151A77C0(actor);for(j=0;j<128;j++)if(actor[j]!=expected[j])return 1;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status));__builtin_unreachable();}
'''
        for name, profile, body, code in (('selected-O2', '-O2', source.SELECTED, 0),
                ('selected-O0', '-O0', source.SELECTED, 0),
                ('signed-control', '-O2', source.SELECTED.replace('(s16 *)(params + 4)', '(u16 *)(params + 4)'), 1)):
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, code, name)
        self.receipt('native', cases_per_profile=524288, profiles=['O2', 'O0'],
            all_signed_states_four_threshold_modes_two_clock_words=True, unsigned_threshold_control_fired=True,
            disjoint_native_storage_only=True)


if __name__ == '__main__':
    unittest.main()
