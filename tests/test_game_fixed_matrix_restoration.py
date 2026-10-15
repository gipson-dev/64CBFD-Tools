"""Original matrix words, bounded rounding, alias order and immutable inputs."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_fixed_matrix_restoration as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import game_fixed_matrix_oracle as model
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import fixed_matrix_checkpoint as checkpoint
from tools.tests import view_orthographic_setup_checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    expected = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, 464)
    expected[at:at + 464] = rom[source.ROM:source.ROM + 464]
    rows = [(offset, fields) for offset, name, fields, _ in machine.symbol_rows(before) if name == source.FUNCTION]
    assert len(rows) == 1 and rows[0][1][1:] == (source.ENTRY, 256, 18, 0, 5)
    struct.pack_into('>I', expected, rows[0][0] + 8, 464)
    return bytes(expected)


class FixedMatrixRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>116I', cls.rom, source.ROM))
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.SOURCE, 'qualified')
        cls.raw, cls.functions, cls.relocations = parse_object(cls.obj)
        cls.words = list(struct.unpack_from('>116I', cls.raw, cls.functions[source.FUNCTION]['value']))
        cls.old_obj, cls.old_diagnostics = build.compile_owner(cls.root, cls.out, (cls.out / 'before-owner').read_text(), 'before-C')
        data, functions, _ = parse_object(cls.old_obj)
        info = functions[source.FUNCTION]
        cls.old_words = list(struct.unpack_from('>64I', data, info['value']))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    @classmethod
    def assemble(cls, assembly, label):
        path = cls.out / (label + '.s')
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly +
            '\n.type guMtxF2L,@function\n.size guMtxF2L,464\n')
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, check=True)
        return obj

    def test_01_original_slot_both_padders_and_independent_rebases(self):
        self.assertEqual((self.diagnostics, self.old_diagnostics, self.relocations), ('', '', {}))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.old_words, list(struct.unpack_from('>64I', self.rom, 0x21D1B0)))
        self.assertEqual(self.functions[source.FUNCTION]['size'], 464)
        original = (self.out / 'before-assembly').read_text()
        isolated = self.assemble(original, 'isolated-original')
        for name, emitter in (('c-padder', lambda: pad_c_object.emit_padded_assembly(self.obj,
                self.root / source.PATHS['layout'], 'guMtxF2L', word_patches_path=self.root / source.PATHS['guards'])),
                ('generated-padder', lambda: emit_padded_assembly(self.obj, self.out / 'before-assembly',
                    filename='guMtxF2L', word_patches_path=self.root / source.PATHS['guards']))):
            padded = self.assemble(emitter(), name)
            for delta in (0, 0x1000000):
                outputs = []
                for label, obj in (('original', isolated), ('padded', padded)):
                    script = self.out / ('%s-%s-%X.ld' % (name, label, delta))
                    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                    elf = script.with_suffix('.elf')
                    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                        '-e', source.FUNCTION, '-o', str(elf), str(obj)], capture_output=True, check=True)
                    outputs.append(sections(elf)['.text'][1][:464])
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(outputs[0], struct.pack('>116I', *self.retail))
        self.receipt('shape', code_words=115, slot_words=116, guards=0, calls=0, frame=0,
            relocations=0, original_CVT_instructions=16, original_halfword_stores=32,
            both_padders_and_independent_rebases=True, old_C_exact_other_function_words=64)

    def test_02_bounded_rounding_all_modes_memory_and_order(self):
        cases = 0
        coverage = set()
        for mode, pattern, rotation, phase in itertools.product(range(4), range(3), range(16), (0, 8)):
            memory = model.fixture(pattern, rotation)
            expected, events = model.reference(memory, mode=mode)
            instances = [model.FixedOracle(words, memory, mode=mode, phase=phase).run() for words in (self.retail, self.words)]
            for instance in instances:
                self.assertEqual((instance.memory, instance.events), (expected, events))
                self.assertEqual(instance.accesses, 48)
                coverage.update(instance.visits)
            self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
            cases += 1
        self.assertEqual(coverage, set(range(source.ENTRY, source.ENTRY + 460, 4)))
        self.receipt('rounding', cases=cases, modes=['nearest-even', 'toward-zero', 'toward-positive', 'toward-negative'],
            exact_scaled_finite_valid_signed_domain=True, all_115_reachable_words=True,
            complete_return_state_memory_and_order=True, no_hardware_FCSR_flags_traps_invalid_or_subnormal_claim=True)

    def test_03_overlapping_buffers_and_every_fired_prefix(self):
        cases = 0
        for delta, mode, pattern in itertools.product((-16, 0, 2, 4, 8, 16, 32, 48), range(4), range(4)):
            destination = model.INPUT + delta
            memory = model.fixture(pattern, output=destination, alias=True)
            expected, events = model.reference(memory, destination, mode)
            instances = [model.FixedOracle(words, memory, destination, mode).run() for words in (self.retail, self.words)]
            for instance in instances:
                self.assertEqual((instance.memory, instance.events), (expected, events))
            self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
            cases += 1
        prefixes = 0
        for mode, destination in itertools.product(range(4), (model.OUTPUT, model.INPUT, model.INPUT + 2)):
            memory = model.fixture(output=destination, alias=destination != model.OUTPUT)
            for cut in range(48):
                instances = []
                for words in (self.retail, self.words):
                    instance = model.FixedOracle(words, memory, destination, mode, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        instance.run()
                    instances.append(instance)
                self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
                self.assertEqual((instances[0].current_pc, instances[0].delay_of), (instances[1].current_pc, instances[1].delay_of))
                prefixes += 1
        self.receipt('aliases', cases=cases, fired_prefixes=prefixes, full_state_PC_delay_identity=True,
            all_48_accesses_include_return_delay_halfword=True, two_byte_output_alignment_guest_only=True,
            no_portable_native_alias_fault_or_hardware_exception_claim=True)

    def test_04_old_C_and_compiled_CVT_and_store_order_negatives(self):
        differences = []
        for mode in range(4):
            memory = model.fixture()
            expected, _ = model.reference(memory, mode=mode)
            old = model.FixedOracle(self.old_words, memory, mode=mode).run()
            differs = old.memory != expected
            self.assertEqual(differs, mode != 1)
            differences.append(differs)
        assembly = (self.out / 'before-assembly').read_text()
        wrong_round = self.assemble(assembly.replace('cvt.w.s', 'trunc.w.s'), 'negative-truncation')
        raw, functions, _ = parse_object(wrong_round)
        words = list(struct.unpack_from('>116I', raw, functions[source.FUNCTION]['value']))
        memory = model.fixture()
        expected, _ = model.reference(memory)
        self.assertNotEqual(model.FixedOracle(words, memory).run().memory, expected)
        lines = assembly.splitlines(True)
        stores = [i for i, line in enumerate(lines) if 'sh ' in line]
        self.assertEqual(len(stores), 32)
        a, b = stores[1:3]
        lines[a], lines[b] = lines[b], lines[a]
        wrong_order = self.assemble(''.join(lines), 'negative-halfword-order')
        raw, functions, _ = parse_object(wrong_order)
        words = list(struct.unpack_from('>116I', raw, functions[source.FUNCTION]['value']))
        expected, events = model.reference(memory)
        wrong = model.FixedOracle(words, memory).run()
        self.assertEqual(wrong.memory, expected)
        self.assertNotEqual(wrong.events, events)
        self.receipt('negatives', old_C_disjoint_state_mismatch_by_mode=differences,
            assembled_truncation_changes_output=True, assembled_store_swap_same_output_wrong_access_order=True)

    def test_05_pinned_capture_and_unknown_input_controls(self):
        source.freeze(self.root, self.out)
        rb = Path.read_bytes
        for key in source.BASELINE:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'immutable fixed-matrix input'):
                    source.freeze(self.root, self.out)
        with self.assertRaisesRegex(ValueError, 'progress row'):
            source.expected_progress(b'wrong')
        path = self.out / 'baseline.json'
        rt = Path.read_text
        with patch.object(Path, 'read_text', lambda p, *a, **k: '{}' if p == path else rt(p, *a, **k)):
            with self.assertRaisesRegex(ValueError, 'fixed-matrix manifest'):
                source.freeze(self.root, self.out)

    def test_06_native32_actual_old_C_and_independent_rounding_witness(self):
        records = []
        for mode, pattern, rotation in itertools.product(range(4), range(3), range(16)):
            memory = model.fixture(pattern, rotation)
            expected, _ = model.reference(memory, mode=mode)
            truncated, _ = model.reference(memory, mode=1)
            rows = [mode, int(expected != truncated),
                [model.read(memory, model.INPUT + i * 4) for i in range(16)],
                [model.read(expected, model.OUTPUT + i * 4) for i in range(16)],
                [model.integer(model.scaled(model.read(memory, model.INPUT + i * 4)), mode) for i in range(16)]]
            literal = lambda values: '{' + ','.join('0x%Xu' % value for value in values) + '}'
            records.append('{%d,%d,%s,%s,%s}' % (rows[0], rows[1], *(literal(value) for value in rows[2:])))
        old = build.body((self.out / 'before-owner').read_text(), source.FUNCTION).replace('void guMtxF2L(', 'void old_guMtxF2L(', 1)
        program = '''typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct {s32 m[4][4];} Mtx;
#define FTOFIX32(x) (long)((x)*(float)0x00010000)
''' + old + '''
typedef struct {u32 mode,different,input[16],packed[16],integers[16];} Case;
static Case cases[]={''' + ',\n'.join(records) + '''};
static struct {u32 before[4];Mtx matrix;u32 after[4];} output;
static int run(void){u32 saved,control,mapping[]={0,3,2,1},counts[4]={0,0,0,0};int n,i,different;
 if(sizeof(void*)!=4||sizeof(long)!=4||sizeof(Mtx)!=64)return 90;
 __asm__ volatile("stmxcsr %0":"=m"(saved));
 for(n=0;n<(int)(sizeof(cases)/sizeof(cases[0]));n++){
  Case *c=&cases[n];control=(saved&~0x6000u)|(mapping[c->mode]<<13);
  __asm__ volatile("ldmxcsr %0"::"m"(control));
  for(i=0;i<16;i++){union{u32 u;f32 f;}v;u32 converted;volatile f32 scaled;
   v.u=c->input[i];scaled=v.f*65536.0f;
   __asm__ volatile("cvtss2si %1,%0":"=r"(converted):"x"(scaled));
   if(converted!=c->integers[i])return 1;
  }
  for(i=0;i<4;i++)output.before[i]=output.after[i]=0xA55A1234u;
  for(i=0;i<16;i++)((u32*)&output.matrix)[i]=0xDEADBEEFu;
  old_guMtxF2L((f32(*)[4])c->input,&output.matrix);
  different=0;for(i=0;i<16;i++)if(((u32*)&output.matrix)[i]!=c->packed[i])different=1;
  if(different!=(int)c->different)return 2;
  for(i=0;i<4;i++)if(output.before[i]!=0xA55A1234u||output.after[i]!=0xA55A1234u)return 3;
  if(different)counts[c->mode]++;
 }
 __asm__ volatile("ldmxcsr %0"::"m"(saved));
 return counts[0]&&counts[2]&&counts[3]&&!counts[1]?0:4;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        path = self.out / 'native-old-C-rounding-witness.c'
        path.write_text(program)
        for profile in ('-O2', '-O0'):
            binary = path.with_suffix('.' + profile[1:])
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-fno-strict-aliasing', '-fwrapv', '-frounding-math', '-fno-builtin', '-ffp-contract=off',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, 0, profile)
        self.receipt('native-witness', cases_per_profile=len(records), profiles=['O2', 'O0'],
            actual_old_C_and_SSE_current_rounding_instruction=True, independent_fraction_reference=True,
            old_C_counterexamples_in_nearest_positive_and_negative_modes=True, canaries_checked=True,
            native_logical_word_endian_conversion_only=True, no_execution_of_MIPS_assembly_or_N64_hardware_claim=True)

    def test_07_actual_projection_family_to_actual_converter(self):
        from tools.tests import test_game_view_projection_family as family_tests
        from tools.tests import game_view_projection_family_oracle as family
        family_tests.ViewProjectionFamilyTests.setUpClass()
        qualified = family_tests.ViewProjectionFamilyTests

        class Connected(family.FamilyOracle):
            def execute(self, word):
                if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 36:
                    self.f[word >> 6 & 31] = model.integer(self.f[word >> 11 & 31], self.rounding_mode)
                else:
                    super().execute(word)

        cases = 0
        coverage = set()
        for mode, root, index, sdk_mode, page, phase in itertools.product(range(4),
                (family.PARENT, family.WRAPPER, family.CHILD), (0, 1, 3), (0, 1, 3), (0, 128), (0, 8)):
            memory = family.fixture(page=page)
            args = (index, model.bits(1.25), model.bits(-2.5), model.bits(1.0))
            if root == family.PARENT:
                args += (0,)
            elif root == family.CHILD:
                normalization = family.BASE + 2 if sdk_mode == 3 else family.VIEWS + index * 0x180 + 0xB8
                args = (index, normalization, model.bits(45), model.bits(60), model.bits(0.125), model.bits(1000), model.bits(1))

            def fixed_effect(memory, packet):
                converted, _ = model.reference(memory, packet[1], mode, source_address=packet[0])
                memory.clear()
                memory.update(converted)

            with patch.object(family, 'fixed_effect', fixed_effect):
                expected = family.reference(memory, args, sdk_mode=sdk_mode, root=root)
            instances = []
            for table, fixed in ((qualified.retail, self.retail), (qualified.words, self.words)):
                connected = {entry + i * 4: word for entry, words in table.items() if entry != root for i, word in enumerate(words)}
                connected.update({source.ENTRY + i * 4: word for i, word in enumerate(fixed)})
                instance = Connected(table[root], memory, args, sdk_mode=sdk_mode, phase=phase, root=root, connected=connected)
                instance.rounding_mode = mode
                instance.run()
                self.assertEqual((family.parent.external(instance.memory), instance.calls), expected)
                instances.append(instance)
                coverage.update(pc for pc in instance.visits if source.ENTRY <= pc < source.ENTRY + 464)
            self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
            cases += 1
        self.assertEqual(coverage, set(range(source.ENTRY, source.ENTRY + 460, 4)))
        self.receipt('connected', cases=cases, actual_parent_wrapper_child_and_converter=True,
            all_115_converter_words_executed=True, complete_RAM_return_state_and_SDK_packets=True,
            projection_float_provider_still_bounded=True, no_actual_guPerspectiveF_FCSR_flags_or_gameplay_claim=True)

    def test_08_installed_source_progress_and_independent_closed_image(self):
        source.freeze(self.root, self.out)
        before = (self.out / 'before-elf').read_bytes()
        expected = {
            'owner': source.SOURCE.encode(),
            'assembly': source.ASM_COMMENT.encode() + (self.out / 'before-assembly').read_bytes(),
            'elf': expected_image(before, self.rom),
            'progress': source.expected_progress((self.out / 'before-progress').read_bytes()),
        }
        for key, path in source.PATHS.items():
            current = view_orthographic_setup_checkpoint.previous_input((self.root / path).read_bytes(), path, self.root)
            self.assertEqual(current, expected[key] if key in expected else (self.out / ('before-' + key)).read_bytes(), key)
        for key in ('owner', 'assembly'):
            self.assertEqual((self.root / source.PATHS[key]).read_text(), expected[key].decode())
        current = expected['elf']
        self.assertEqual(hashlib.sha256(current).hexdigest(), checkpoint.AFTER['elf'])
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256((self.root / source.PATHS['elf']).read_bytes()).hexdigest(),
            restoration_checkpoint_ELF_sha256=checkpoint.AFTER['elf'], historical_restoration_changed_bytes=sum(a != b for a, b in zip(before, current)),
            code_slot_bytes=464, extent=[256, 464], no_symbol_reordering_or_non_target_definition_changes=True,
            every_other_historical_ELF_byte_fixed=True, unchanged_guards_profiles_headers_and_callers=True,
            only_progress_change='guMtxF2L c -> asm', no_new_C_match_credit=True, protected_data=data)

    def test_09_effective_installed_source_image_and_progress_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_08_installed_source_progress_and_independent_closed_image()
        for key in ('owner', 'assembly'):
            path = self.root / source.PATHS[key]
            with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_08_installed_source_progress_and_independent_closed_image()
        path = self.root / source.PATHS['elf']
        current = rb(path)
        row = next(row for row in machine.symbol_rows(current) if row[1] == source.FUNCTION)
        offsets = (elf_slot_offset(current, source.ENTRY, 4), elf_slot_offset(current, 0x151EFD00, 4), row[0] + 8, row[3])
        for offset in offsets:
            bad = bytearray(current)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_08_installed_source_progress_and_independent_closed_image()
        before = bytearray((self.out / 'before-elf').read_bytes())
        row = next(row for row in machine.symbol_rows(before) if row[1] == source.FUNCTION)
        before[row[0] + 7] ^= 1
        with self.assertRaises(AssertionError):
            expected_image(bytes(before), self.rom)

    def test_10_exact_inverse_unknown_inputs_and_capture_controls(self):
        self.test_08_installed_source_progress_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            before = checkpoint.fixture(self.root, 'before', key)
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current, self.root / relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
            for stage in ('before', 'after'):
                path = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixed-matrix checkpoint fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Unexpected installed fixed-matrix input'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
