"""Qualify the complete loader and every bounded normalization guard."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_guarded_match as matching
from tools.tests import test_game_main_resource_loader_remaining_schedule as previous
from tools.tests import test_game_main_resource_loader as recovery


class GameMainResourceLoaderGuardedMatchTests(previous.GameMainResourceLoaderRemainingScheduleTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        history = cls.out
        cls.out = cls.root/'conker/build/game-main-resource-loader-guarded-match-test'
        cls.out.mkdir(exist_ok=True)
        for name in cls.paths:
            data = (history/('before-'+name)).read_bytes()
            assert hashlib.sha256(data).hexdigest() == cls.baseline[name]
            path = cls.out/('before-'+name)
            if not path.exists():
                path.write_bytes(data)
            assert path.read_bytes() == data
        manifest = cls.out/'checkpoint.json'
        if not manifest.exists():
            assert hashlib.sha256((cls.root/cls.paths['guards']).read_bytes()).hexdigest() == matching.GUARDS_SHA
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('checkpoint-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.checkpointHashes = json.loads(manifest.read_text())
        assert cls.checkpointHashes['source'] == matching.SOURCE_SHA
        assert cls.checkpointHashes['elf'] == 'c4f1a877f41ffc7b442de46f68bae070e47fbb192776913d3d8fa14c785e93c4'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.checkpointHashes[name]
        cls.checkpoint = (cls.out/'checkpoint-elf').read_bytes()
        cls.meta, cls.raw = matching.schedule.measure(cls.root, cls.out, 'selected', matching.SELECTED)
        _, functions, relocations = recovery.parse_object(cls.out/'selected.o')
        base = functions[recovery.screen.FUNCTION]['value']
        cls.suffix = matching.guard_text(cls.raw, cls.retail, {offset-base:value for offset,value in relocations.items()
            if base <= offset < base+1096})
        cls.guards = cls.out/'qualified-guards.csv'
        cls.guards.write_bytes((cls.out/'checkpoint-guards').read_bytes()+cls.suffix)
        cls.fields = next(csv.reader(io.StringIO((cls.out/'checkpoint-guards').read_text())))
        cls.only = cls.out/'only-guards.csv'
        cls.only.write_text(','.join(cls.fields)+'\n'+cls.suffix.decode('ascii'))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split(
            'glabel '+recovery.screen.FUNCTION, 1)[1].split('endlabel '+recovery.screen.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+recovery.screen.FUNCTION+assembly+'endlabel '+recovery.screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+recovery.screen.FUNCTION+
            '\n.type '+recovery.screen.FUNCTION+',@function\n'+recovery.screen.FUNCTION+':\n'+assembly+
            '\n.size '+recovery.screen.FUNCTION+',.-'+recovery.screen.FUNCTION+'\n')
        cls.assemble('padded', recovery.emit_padded_assembly(cls.out/'selected.o', cls.slot,
            word_patches_path=cls.only, filename='generated_6A3D0'))

    def test_01_complete_slot_fitting_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (274, 0x78, 22))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.meta['saved_registers'], list(range(16, 23)))
        self.assertIn(22, self.meta['opening_zero_destinations'])
        self.assertEqual(self.meta['private_S5_stores'], [])
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.retail)
        self.assertEqual(matching.normalized(self.raw, self.retail), self.retail)
        matching.validate_current_guards(self.root)
        self.receipt('shape', words=274, frame=0x78, raw_differences=22,
            production_padded_differences=0, directly_exact_raw_words=252,
            expected_word_and_empty_relocation_guards=22, guarded_not_direct_C_match=True)

    def test_07_complete_owner_and_both_real_padders(self):
        recovery.GameMainResourceLoaderTests.test_07_complete_owner_and_both_real_padders(self)
        parsed = []
        for route in ('pad_c_object.py', 'pad_generated_object.py'):
            outputs = []
            for i, name in enumerate(('owner-before', 'owner-after')):
                obj = self.out/(name+'.o')
                asm = self.out/('guarded-'+route+'-'+str(i)+'.s')
                args = [str(obj), str(self.out/'before-layout'), 'generated_6A3D0', str(asm)] if route == 'pad_c_object.py' else [
                    str(obj), str(self.root/'conker/asm/6A3D0.s'), str(asm), '--filename', 'generated_6A3D0']
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches',
                    str(self.guards if i else self.out/'before-guards')], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                    check=True, capture_output=True)
                outputs.append(recovery.parse_object(asm.with_suffix('.o')))
            start = outputs[1][1][recovery.screen.FUNCTION]['value']
            end = start+1096
            expected = bytearray(outputs[0][0])
            expected[start:end] = outputs[1][0][start:end]
            self.assertEqual(bytes(expected), outputs[1][0])
            self.assertEqual({o:v for o,v in outputs[0][2].items() if not start <= o < end},
                {o:v for o,v in outputs[1][2].items() if not start <= o < end})
            self.assertEqual(outputs[1][0][start:end], recovery.parse_object(self.out/'padded.o')[0][:1096])
            parsed.append(outputs[1])
        self.assertEqual(parsed[0], parsed[1])
        self.receipt('guarded-owner', neighbors=14, actual_padders=2,
            all_non_target_bytes_extents_relocations_pools_preserved=True)

    def test_08_immutable_baseline_and_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            self.assertEqual(hashlib.sha256((self.out/('checkpoint-'+name)).read_bytes()).hexdigest(), self.checkpointHashes[name])
        self.assertEqual(matching.parent_source(self.root).encode('ascii'), (self.out/'checkpoint-source').read_bytes())
        guard_data = (self.root/self.paths['guards']).read_bytes()
        installed = guard_data != (self.out/'checkpoint-guards').read_bytes()
        self.assertEqual(guard_data, self.guards.read_bytes() if installed else (self.out/'checkpoint-guards').read_bytes())
        actual = matching.parent_elf(self.root, self.checkpoint)
        expected = bytearray(self.checkpoint)
        offset = recovery.elf_slot_offset(self.checkpoint, recovery.screen.ENTRY, 1096)
        if installed:
            struct.pack_into('>274I', expected, offset, *self.retail)
        self.assertEqual(bytes(expected), actual)
        self.assertEqual(recovery.metadata(self.checkpoint), recovery.metadata(actual))
        for name, path in self.paths.items():
            if name not in ('elf', 'guards'):
                data = matching.parent_source(self.root).encode('ascii') if name == 'source' else (self.root/path).read_bytes()
                self.assertEqual(data, (self.out/('checkpoint-'+name)).read_bytes())
        audit = recovery.audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=installed, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a,b in zip(self.checkpoint, actual)),
            only_target_bytes_change=True, all_other_metadata_extents_data_conversion_inputs_exact=True,
            source_unchanged_after_exact_child_projection=True,
            guard_history_exact_only_22_rows_appended=installed, protected_data=audit)

    def test_10_actual_parent_main_extras_relocator_buffer_chain(self):
        recovery.GameMainResourceLoaderTests.test_10_actual_parent_main_extras_relocator_buffer_chain(self)
        raw = self.raw
        try:
            self.raw = self.link('padded')
            recovery.GameMainResourceLoaderTests.test_10_actual_parent_main_extras_relocator_buffer_chain(self)
        finally:
            self.raw = raw
        self.receipt('guarded-chain', cases_per_raw_or_padded_pass=768, passes=2,
            original_raw_and_actual_padded_main_with_banked_parent_extras_relocator_buffer=True,
            deeper_helpers_heap_hardware_runtime_still_bounded=True)

    def test_11_ignored_incoming_word_and_install_guards(self):
        cases = 0
        fitted = self.link('padded')
        for identity, unused, present, extras in itertools.product(
                (-1, 7, 186, 187, 255, 0x7FFFFFFF), (0, 1, 0xFFFFFFFF, 0x80000000), (False, True), (0, 1)):
            self.compare(recovery.fixture(identity=identity, present=present),
                forms=(self.retail, self.raw, fitted), identity=identity, unused=unused, extras=extras)
            cases += 1
        self.receipt('scratch', cases=cases, forms=3, ignored_second_word_and_both_extras_gates=True)

    def test_13_all_guard_words_and_relocations_fail_closed(self):
        rows = list(csv.DictReader(io.StringIO(self.guards.read_text())))
        history = list(csv.DictReader(io.StringIO((self.out/'checkpoint-guards').read_text())))
        target = rows[len(history):]
        self.assertEqual(tuple(int(row['offset'], 0) for row in target), matching.OFFSETS)
        self.assertTrue(all(row['expected_relocations'] == row['replacement_relocations'] == '-' for row in target))
        self.assertEqual(self.guards.read_bytes(), (self.out/'checkpoint-guards').read_bytes()+self.suffix)
        attempts = 0
        for index, row in enumerate(target):
            for field, value, message in (
                    ('expected', '0x%08X'%(int(row['expected'], 0)^1), 'stale word patch'),
                    ('expected_relocations', 'R_MIPS_HI16:D_800D19A0', 'stale relocations')):
                changed = [dict(row) for row in rows]
                changed[len(history)+index][field] = value
                stale = self.out/'stale-guards.csv'
                with stale.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n')
                    writer.writeheader()
                    writer.writerows(changed)
                with self.assertRaisesRegex(ValueError, message):
                    recovery.emit_padded_assembly(self.out/'selected.o', self.slot,
                        word_patches_path=stale, filename='generated_6A3D0')
                result = subprocess.run(['python3', str(self.root/'tools/pad_c_object.py'),
                    str(self.out/'owner-after.o'), str(self.out/'before-layout'), 'generated_6A3D0',
                    str(self.out/'stale.s'), '--word-patches', str(stale)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout+result.stderr)
                attempts += 2
        self.receipt('stale', guards=22, actual_padders=2, fired_rejections=attempts,
            every_expected_word_and_relocation_corruption_rejected=True)

    def test_14_every_stack_and_public_fault_prefix(self):
        cases = pairs = 0
        fitted = self.link('padded')
        for first, failure, optional, phase in itertools.product((0, 2),
                ('request', 'extras', 'secondary', 'auxiliary', 'third', 'fourth'), (0, 7), (0, 8)):
            memory = recovery.fixture(first_count=first, flags=0x4000, optional=optional)
            settings = dict(phase=phase, results={failure:0 if failure == 'request' else 4})
            complete = recovery.MainOracle(self.retail, memory, **settings).run()
            for ordinal in range(complete.accesses):
                models = [recovery.MainOracle(words, memory, **settings) for words in (self.retail, fitted)]
                for model in models:
                    model.fault = ordinal
                    with self.assertRaises(recovery.guest.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, ordinal)
                self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r),
                    (models[1].memory, models[1].events, models[1].calls, models[1].r))
                pairs += 1
            cases += 1
        self.receipt('all-access-faults', cases=cases, fired_original_padded_pairs=pairs,
            full_private_and_public_partial_memory_access_call_and_register_traces_equal=True,
            raw_C_private_faults_not_claimed=True, guest_model_not_hardware=True)

    def test_15_exact_guard_successor_recognition(self):
        before = (self.out/'checkpoint-guards').read_bytes()
        current = before+self.suffix
        path = self.root/self.paths['guards']
        read_bytes = Path.read_bytes
        for data in (before, current):
            with patch.object(Path, 'read_bytes', lambda p: data if p == path else read_bytes(p)):
                self.assertEqual(matching.current_guard_bytes(self.root, before), data)
        altered = (bytes([before[0]^1])+current[1:], current+b'\n',
            current[:-1], before+self.suffix.replace(b'0x8FA', b'0x8FB', 1))
        for data in altered:
            self.assertNotEqual(data, current)
            with patch.object(Path, 'read_bytes', lambda p: data if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    matching.current_guard_bytes(self.root, before)
                with self.assertRaises(AssertionError):
                    matching.validate_current_guards(self.root)
        self.receipt('successor', original_and_exact_22_row_successor_accepted=True,
            fired_manifest_mutation_rejections=len(altered)*2,
            immutable_prefix_extra_bytes_truncation_or_changed_guard_rejected=True)


if __name__ == '__main__':
    unittest.main()
