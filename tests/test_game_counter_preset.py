"""Counter semantics are recovered; reject the nonmatching private instruction schedule."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_counter_preset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_type_preset as previous
from tools.tests import test_game_factory_preset_wrapper as wrapper
from tools.tests import test_game_record_factory as factory
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


def packet(args):
    values = [0] * 49
    for index, value in ((3, 4), (5, 255), (6, 255), (7, 255), (12, 2),
            (27, 512), (28, 512), (31, 30), (34, args[0]), (35, 20),
            (38, 129), (39, 8), (41, 1), (45, 12), (47, args[2] & 255), (48, args[3])):
        values[index] = value & 0xFFFFFFFF
    return tuple(values)


def address(args, table=source.TABLE):
    return (table + args[0]) & 0xFFFFFFFF


class CounterOracle(wrapper.PresetOracle):
    def __init__(self, words, args, value=255, phase=0, mode=0, fault=None,
            entry=source.ENTRY, callee=source.CALLEE, table=source.TABLE):
        super().__init__(words, args, phase, mode, fault, entry, callee)
        self.counter, self.observed = address(args, table), []
        self.memory.update({self.counter + i: v for i, v in enumerate((value, 0xA5, 0x5A, 0xC3))})

    def execute(self, word):
        if word >> 26 == 32:
            # The signed-byte negative control adds LB to this target's instruction set.
            super().execute(word | 0x10000000)
            rt = word >> 16 & 31
            if rt:
                self.r[rt] = ((self.r[rt] ^ 128) - 128) & 0xFFFFFFFF
        else:
            super().execute(word)

    def hook(self, target):
        self.observed.append(read(self.memory, self.counter, 1))
        super().hook(target)
        if self.mode == 2:
            self.put(self.counter, 0x5A, 1)


def external(model):
    return {a: v for a, v in model.memory.items() if not wrapper.STACK - 256 <= a < wrapper.STACK + 256}


def controls():
    return {
        'unsigned-slot': source.SELECTED.replace('arg0 < 4', '(u32)arg0 < 4'),
        'signed-byte': source.SELECTED.replace('(s32)(&D_800DD2A0)[arg0]', '(s32)((signed char *)&D_800DD2A0)[arg0]'),
        'unsigned-threshold': source.SELECTED.replace('(s32)(&D_800DD2A0)[arg0] >= arg1', '(u32)(&D_800DD2A0)[arg0] >= (u32)arg1'),
        'strict-threshold': source.SELECTED.replace('>= arg1', '> arg1'),
        'missing-clear': source.SELECTED.replace('(&D_800DD2A0)[arg0] = 0;', '(&D_800DD2A0)[arg0] = 1;'),
        'late-clear': source.SELECTED.replace('        (&D_800DD2A0)[arg0] = 0;\n', '').replace('(u8)arg2, arg3);', '(u8)arg2, arg3);\n        (&D_800DD2A0)[arg0] = 0;'),
        'wide-flag': source.SELECTED.replace('(u8)arg2', 'arg2'),
        'wrong-actor': source.SELECTED.replace('0, 0, arg0, 0x14,', '0, 0, (arg0 ^ 1), 0x14,'),
        'wrong-last': source.SELECTED.replace('(u8)arg2, arg3)', '(u8)arg2, arg1)'),
        'wrong-preset': source.SELECTED.replace('0x200, 0x200', '0x201, 0x200'),
    }


class CounterPresetCandidateTests(unittest.TestCase):
    def test_scoped_recipes_and_exact_match_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(set(source.PATHS.values())), 52)
        before = 'extern s32 D_800BE9E4;\ns32 func_1516EED4() {\n    return 0;\n}\nvoid other(void) { }\n'
        for body in source.candidates().values():
            self.assertNotIn('volatile', body)
            self.assertTrue(source.recovered_owner(before, body).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        for count, differences, diagnostics in ((85, 78, ''), (84, 1, ''), (84, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))


class CounterPresetRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.recover(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>84I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = previous.ActorPresetMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_noninstallable_owner_and_all_neighbors(self):
        self.assertEqual((len(self.words), self.row['differences']), (85, 76))
        self.assertFalse(self.row['installable'])
        before, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        with self.assertRaises((ValueError, AssertionError)) as rejected:
            emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER,
                word_patches_path=self.out / 'before-guards')
        self.assertIn(source.FUNCTION, str(rejected.exception))
        # The raw index reload replaces retail's pointer-add branch delay.
        self.assertEqual(self.words[10], 0x8FAF00D0)
        self.assertEqual(self.truth[10], 0x01CF1021)
        self.receipt('owner', unchanged_neighbors=len(old[1]) - 1, pools_and_relocations_fixed=True,
            raw_words=85, retail_words=84, positional_differences=76, strict_padder_rejects=True,
            production_installable=False, no_new_guards_or_profiles=True)

    def test_02_signed_slot_threshold_packet_and_pre_provider_clear(self):
        visits, cases, accepted, rejected, private_mismatches = set(), 0, 0, 0, 0
        thresholds = (0x80000000, 0xFFFFFFFF, 0, 1, 127, 128, 254, 255, 256, 0x7FFFFFFF)
        for index in (0x80000000, 0xFFFFFFC0, 0xFFFFFFFF, 0, 1, 2, 3, 4, 0x7FFFFFFF):
            for value in (0, 1, 127, 128, 254, 255):
                for threshold in thresholds:
                    args = (index, threshold, 0xFFFFFF80 | value, (index * 1664525 + threshold) & 0xFFFFFFFF)
                    for phase in (0, 8):
                        for mode in range(3):
                            models = [CounterOracle(w, args, value, phase, mode).run() for w in (self.words, self.truth)]
                            live = signed(index) < 4
                            called = live and value >= signed(threshold)
                            expected = [(source.CALLEE, *packet(args))] if called else []
                            for model in models:
                                self.assertEqual(model.calls, expected)
                                self.assertEqual(model.observed, [0] if called else [])
                                self.assertEqual(read(model.memory, address(args), 1), 0x5A if called and mode == 2 else 0 if called else value)
                                self.assertEqual(model.r[29], wrapper.STACK + phase)
                                reads = [e for e in model.events if e[:3] == ('R', address(args), 1)]
                                self.assertEqual(len(reads), int(live))
                            self.assertEqual(external(models[0]), external(models[1]))
                            private_mismatches += wrapper.state(models[0]) != wrapper.state(models[1])
                            visits |= models[1].visits
                            accepted += called
                            rejected += not called
                            cases += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 336, 4)))
        self.assertGreater(private_mismatches, 0)
        self.receipt('semantics', paired_guest_cases=cases, accepted=accepted, rejected=rejected,
            signed_slot_and_word_threshold=True, no_read_when_slot_ge_four=True,
            complete_packet_and_external_memory_equal=True, counter_cleared_at_provider_entry=True,
            provider_counter_write_survives=True, all_84_retail_instructions_visited=True,
            private_state_mismatches=private_mismatches, not_byte_exact_or_installable=True,
            negative_guest_indices_are_backed_fixtures_not_runtime_actor_validation=True)

    def test_03_effective_guest_controls(self):
        probes = ((0xFFFFFFFF, 0, 0xFFFFFF80, 0x12345678), (0, 0xFFFFFFFF, 0xFFFFFF80, 0x12345678),
            (0, 255, 0xFFFFFF80, 0x12345678))
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            changed = False
            for args in probes:
                a, b = [CounterOracle(w, args, 255, mode=2).run() for w in (words, self.truth)]
                changed |= (a.calls, a.observed, read(a.memory, address(args), 1)) != (b.calls, b.observed, read(b.memory, address(args), 1))
            self.assertTrue(changed, name)
        self.receipt('controls', effective_compiled_guest_negatives=len(controls()),
            late_clear_detected_at_call_and_provider_write=True)

    def test_04_native32_backed_array_signed_boundaries_and_controls(self):
        params = ','.join('%s p%d' % ('s16' if i < 3 else 'u32', i) for i in range(49))
        capture = ','.join('p%d' % i for i in range(49))
        harness = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef short s16;
static u8 backing[96];
#define D_800DD2A0 (backing[64])
static u32 captured[49],count,error,mode;static s32 slot;
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 values[49]={''' + capture + '''};u32 i;count++;if(backing[64+slot])error=1;
 for(i=0;i<49;i++)captured[i]=values[i];if(mode)backing[64+slot]=0x5A;}
''' + source.SELECTED + '''
static void (*volatile invoke)(s32,s32,s32,s32)=func_1516EED4;
static int run(void){s32 slots[8]={-64,-1,0,1,2,3,4,11};
 s32 thresholds[10]={(-2147483647-1),-1,0,1,127,128,254,255,256,2147483647};
 u32 i,j,k,v,n=0,a2,a3,e[49],yes;
 if(sizeof(void*)!=4||sizeof(s32)!=4)return 10;
 for(i=0;i<8;i++)for(v=0;v<256;v++)for(k=0;k<10;k++)for(mode=0;mode<2;mode++){
  slot=slots[i];a2=0xFEDC0000u|(n*31&65535);a3=n*1664525u+1013904223u;n++;
  for(j=0;j<96;j++)backing[j]=0xA5;backing[64+slot]=(u8)v;
  for(j=0;j<49;j++){captured[j]=0xDEADBEEFu;e[j]=0;}
  e[3]=4;e[5]=e[6]=e[7]=255;e[12]=2;e[27]=e[28]=512;e[31]=30;e[34]=(u32)slot;
  e[35]=20;e[38]=129;e[39]=8;e[41]=1;e[45]=12;e[47]=a2&255;e[48]=a3;
  yes=slot<4&&(s32)v>=thresholds[k];count=error=0;
  invoke(slot,thresholds[k],(s32)a2,(s32)a3);
  if(count!=yes||error)return 11;
  if(backing[64+slot]!=(yes?(mode?0x5A:0):v))return 12;
  for(j=0;j<49;j++)if(captured[j]!=(yes?e[j]:0xDEADBEEFu))return 13;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        variants = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]
        variants += [('negative-' + n, b, '-O2', False) for n, b in controls().items()]
        for name, body, profile, expected in variants:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, expected, (name, result.returncode))
        self.receipt('native', cases_per_O2_O0=40960, indices=[-64, -1, 0, 1, 2, 3, 4, 11],
            all_256_counter_bytes_and_ten_signed_thresholds=True, effective_controls=10,
            bounded_array_not_arbitrary_pointer_or_full_runtime_claim=True, explicit_word_capture_provider=True)

    def test_05_real_factory_allocator_null_and_registration(self):
        before = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, before, elf_slot_offset(before, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        counts = dict(rejected=0, null=0, registered=0)
        for i in range(128):
            args = (i % 6, 0 if i % 3 else 256, 0xFFFF0080 | i, i * 1664525 + 1013904223)
            args = tuple(a & 0xFFFFFFFF for a in args)
            called = args[0] < 4 and args[1] <= 255
            result = 0 if i % 4 == 0 else factory.RECORD
            models = []
            for words in (self.words, self.truth):
                model = factory.FactoryOracle(words, args, result, entry=source.ENTRY, connected=connected, chain=True)
                model.memory.update({address(args) + j: v for j, v in enumerate((255, 0xA5, 0x5A, 0xC3))})
                models.append(model.run())
            self.assertEqual(models[0].calls, models[1].calls)
            for model in models:
                self.assertEqual(read(model.memory, address(args), 1), 0 if called else 255)
                if not called:
                    self.assertEqual(model.calls, [])
                    continue
                self.assertEqual(model.calls[0], (source.CALLEE, *packet(args)))
                self.assertEqual(model.calls[1], (0x15167A68, 17, args[3], 76, 0, args[2] & 255, 1))
                self.assertEqual(model.calls[2], (factory.ALLOCATE, 76, 1, 0, 0, 1))
                if result:
                    expected = factory.reference(factory.fixture(packet(args)), packet(args), result)[0]
                    for a in range(factory.RECORD + 14, factory.RECORD + 76):
                        self.assertEqual(model.memory[a], expected[a])
                    self.assertEqual(model.memory[factory.RECORD], 17)
                    self.assertEqual(model.memory[factory.RECORD + 1], args[3] & 255)
                    self.assertEqual(model.memory[factory.RECORD + 12], args[2] & 255)
            counts['rejected' if not called else 'registered' if result else 'null'] += 1
        self.assertTrue(all(counts.values()))
        self.receipt('chain', paired_cases=128, **counts, actual_callee_words=[125, 28],
            null_allocation_keeps_pre_call_clear=True, lower_heap_and_registration_opaque=True)

    def test_06_all_52_production_inputs_and_capture_controls(self):
        source.freeze(self.root, self.out)
        def unchanged():
            for key, relative in source.PATHS.items():
                self.assertEqual((self.root / relative).read_bytes(), (self.out / ('before-' + key)).read_bytes(), key)
        unchanged()
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    unchanged()
        self.receipt('unchanged-inputs', all_52_inputs_fixed=True, all_52_before_capture_flips_rejected=True,
            all_52_live_input_flips_rejected=True,
            protected_data=layout, no_production_source_guard_profile_or_progress_change=True)

    def test_07_fired_fault_prefixes_expose_private_schedule_mismatch(self):
        counts = dict(paired=0, exact=0, different=0)
        for args in ((0, 0, 0xFFFFFF80, 0x12345678), (0, 256, 0xFFFFFF80, 0x12345678), (4, 0, 0xFFFFFF80, 0x12345678)):
            for phase in (0, 8):
                complete = [CounterOracle(w, args, phase=phase, mode=2).run() for w in (self.words, self.truth)]
                for fault in range(min(m.accesses for m in complete)):
                    pair = [CounterOracle(w, args, phase=phase, mode=2, fault=fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    counts['paired'] += 1
                    counts['exact' if wrapper.state(pair[0]) == wrapper.state(pair[1]) else 'different'] += 1
        self.assertGreater(counts['different'], 0)
        self.receipt('prefixes', **counts, every_injected_guest_fault_fired=True,
            private_fault_order_is_not_qualified=True, not_portable_C_fault_or_hardware_acceptance=True)

    def test_09_independent_rebases_and_home_alias_schedule_repair(self):
        data, functions, rel = parse_object(self.obj)
        text, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION,
            {'func_1516D99C': source.CALLEE, 'D_800DD2A0': source.TABLE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        aliases = 0
        for index, (delta, table) in enumerate(((0, source.TABLE), (0x10000, 0x00317FFC), (-0x10000, 0x00528004))):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label, count in (('selected', 85), ('original', 84)):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '--defsym=D_800DD2A0=0x%X' % table,
                    '-o', str(elf), str(self.out / (label + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>%dI' % count, sections(elf)['.text'][1])))
            for args in ((0, 0, 0xFFFFFF80, 0x12345678), (0xFFFFFFFF, 255, 0xFF123456, 0x98765432),
                    (0, 256, 0, 0), (4, 0, 0, 0)):
                pair = [CounterOracle(w, args, entry=entry, callee=callee, table=table).run() for w in outputs]
                self.assertEqual(pair[0].calls, pair[1].calls)
                self.assertEqual(pair[0].observed, pair[1].observed)
                self.assertEqual(external(pair[0]), external(pair[1]))
            if index == 0:
                continue
            for phase in (0, 8):
                for offset in (3, 11, 15):
                    at = wrapper.STACK + phase + offset
                    slot = (at - table) & 0xFFFFFFFF
                    self.assertLess(signed(slot), 4)
                    args = (slot, 0, 0x12345680, 0x765432FF)
                    pair = [CounterOracle(w, args, phase=phase, entry=entry, callee=callee, table=table).run() for w in outputs]
                    self.assertEqual(pair[1].calls, [(callee, *packet(args))])
                    self.assertEqual(pair[0].calls, pair[1].calls)
                    self.assertEqual(pair[0].observed, [0])
                    self.assertEqual(pair[1].observed, [0])
                    aliases += 1
        self.receipt('rebases', independent_original_selected_text_table_call_pairs=3,
            backed_home_alias_cases=aliases, signed_low_carry_boundaries=True,
            selected_preserves_full_inputs_before_aliased_clear=True,
            synthetic_rebased_guest_evidence_not_native_C_or_retail_runtime_alias_claim=True)

    def test_10_diagnostic_closed_delta_and_all_word_corruptions(self):
        fitted = source.diagnostic_fit(self.words)
        self.assertEqual(fitted, self.truth)
        for index in range(85):
            bad = self.words.copy()
            bad[index] ^= 1
            with self.assertRaisesRegex(ValueError, 'diagnostic input'):
                source.diagnostic_fit(bad)
        with self.assertRaisesRegex(ValueError, 'diagnostic input'):
            source.diagnostic_fit(self.words[:-1])
        self.assertFalse(self.row['installable'])
        self.receipt('diagnostic-fit', described_words=84, described_differences=0,
            linked_input_sha256=source.LINKED_SHA256, removed_input_load_offset=40,
            branch_offset_adjustment=-1, closed_temporary_register_cycle=[8, 25, 24, 15, 14, 13, 12, 11, 10, 9],
            opening_T6_index_preserved=True, all_85_word_flips_and_wrong_length_rejected=True,
            production_raw_words=85, no_guard_rows_emitted_or_installed=True,
            not_padded_rebased_private_or_installed_match_qualification=True)


if __name__ == '__main__':
    unittest.main()
