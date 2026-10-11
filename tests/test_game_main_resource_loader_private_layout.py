"""Qualify the complete loader's count schedule and three recovered slots."""
import csv
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_private_layout as layout
from tools.tests import test_game_main_resource_loader as recovery
from tools.tests import test_game_main_resource_loader_count_lifetimes as previous


class GameMainResourceLoaderPrivateLayoutTests(previous.GameMainResourceLoaderCountLifetimeTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-main-resource-loader-private-layout-test'
        cls.out.mkdir(exist_ok=True)
        original = cls.root/'conker/build/game-main-resource-loader-test'
        cls.paths = dict(source=recovery.screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt')
        cls.baseline = json.loads((original/'baseline.json').read_text())
        for name in cls.paths:
            data = (original/('before-'+name)).read_bytes()
            assert hashlib.sha256(data).hexdigest() == cls.baseline[name]
            if not (cls.out/('before-'+name)).exists():
                (cls.out/('before-'+name)).write_bytes(data)
            assert (cls.out/('before-'+name)).read_bytes() == data
        manifest = cls.out/'checkpoint.json'
        if not manifest.exists():
            assert layout.BANKED in (cls.root/cls.paths['source']).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('checkpoint-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.checkpointHashes = json.loads(manifest.read_text())
        assert cls.checkpointHashes['source'] == 'd36a98c471e7c89e7be7931aca89a24e273f163b76f6f3cd535371c43349b7aa'
        assert cls.checkpointHashes['elf'] == '0f7e54c89e620884ea89018e2747ae83d5765672022a06043d8b13490ec3e3bc'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.checkpointHashes[name]
        for module, field in ((layout.count, 'SELECTED'), (recovery.screen, 'QUALIFIED')):
            selection = patch.object(module, field, layout.SELECTED)
            selection.start()
            cls.addClassCleanup(selection.stop)
        cls.meta, cls.raw = layout.measure(cls.root, cls.out, 'selected', layout.SELECTED)
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.checkpoint = (cls.out/'checkpoint-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>274I', cls.rom, recovery.screen.ROM))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split(
            'glabel '+recovery.screen.FUNCTION, 1)[1].split('endlabel '+recovery.screen.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+recovery.screen.FUNCTION+assembly+'endlabel '+recovery.screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+recovery.screen.FUNCTION+
            '\n.type '+recovery.screen.FUNCTION+',@function\n'+recovery.screen.FUNCTION+':\n'+assembly+
            '\n.size '+recovery.screen.FUNCTION+',.-'+recovery.screen.FUNCTION+'\n')
        cls.assemble('padded', recovery.emit_padded_assembly(cls.out/'selected.o', cls.slot, filename='generated_6A3D0'))

    def test_01_complete_slot_fitting_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (274, 0x78, 24))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.meta['saved_registers'], list(range(16, 23)))
        self.assertIn(22, self.meta['opening_zero_destinations'])
        self.assertEqual(self.meta['private_S5_stores'], [])
        self.assertEqual(self.meta['request_output_stack'], 0x6C)
        self.assertEqual(self.meta['private_stack_offsets'], [0x4C, 0x50, 0x54, 0x68])
        self.assertFalse(self.meta['masked_initial_count_store'])
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.raw)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse(any(row['function'] == recovery.screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('shape', words=274, frame=0x78, raw_differences=24,
            original_request_output_boundary_half_index_slots=True,
            original_saved_S0_S6_and_continuous_S5=True, unmasked_halfword_store_and_event_order_restored=True,
            remaining_main_word_spills_request_return_cleanup_registers_and_initial_delay=True,
            matching_not_achieved=True, new_guards=0)

    def test_06_effective_compiled_semantic_controls(self):
        main = layout.MAIN
        controls = (
            ('identity-signed', 'identity >= 0xBB', '(u32)identity >= 0xBB', recovery.fixture(identity=-1), dict(identity=-1)),
            ('cached-presence', main+' != NULL', main+' == NULL', recovery.fixture(present=True), {}),
            ('request-kind', '&output, 7, 0, 2, 1, identity', '&output, 6, 0, 2, 1, identity', recovery.fixture(), {}),
            ('publication-offset', '(u8 *)block + 0x38', '(u8 *)block + 0x30', recovery.fixture(), {}),
            ('cached-count', 'index < D_800C4778[identity]', 'index < 2', recovery.fixture(first_count=2, second_count=0),
                dict(actions={('child', 0): ((recovery.address('D_800C4778'), 1, 2),)})),
            ('extras-flag', 'if (extras != 0)', 'if (extras == 0)', recovery.fixture(), dict(extras=1)),
            ('config-mask', '& 0x4000', '& 0x2000', recovery.fixture(flags=0x4000), dict(results=dict(auxiliary=1))),
            ('auxiliary-error', 'failed |= 8', 'failed |= 4', recovery.fixture(flags=0x4000), dict(results=dict(auxiliary=1))),
            ('skip-free', 'func_10004074('+main+' - 0x38)', '(void)('+main+' - 0x38)',
                recovery.fixture(), dict(results=dict(secondary=4))),
            ('clear-before-free', 'func_10004074(*cleanupSlot);\n            *cleanupSlot = NULL;',
                '*cleanupSlot = NULL;\n            func_10004074(*cleanupSlot);', recovery.fixture(), dict(results=dict(secondary=4))),
        )
        for name, before, after, memory, settings in controls:
            body = layout.SELECTED.replace(before, after)
            self.assertNotEqual(body, layout.SELECTED)
            with patch.object(recovery.screen, 'ENTRY', 0x15400000):
                _, words = recovery.screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            correct = recovery.MainOracle(self.retail, memory, **settings).run()
            wrong = recovery.MainOracle(words, memory, entry=0x15400000, **settings).run()
            self.assertNotEqual((recovery.preparation.public(correct.memory), recovery.preparation.events(correct.events), correct.calls, correct.r[2]),
                (recovery.preparation.public(wrong.memory), recovery.preparation.events(wrong.events), wrong.calls, wrong.r[2]))
        self.receipt('controls', freshly_compiled_effective_controls=len(controls))

    def test_08_immutable_baseline_and_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            self.assertEqual(hashlib.sha256((self.out/('checkpoint-'+name)).read_bytes()).hexdigest(), self.checkpointHashes[name])
        source = (self.root/recovery.screen.SOURCE).read_text()
        banked = (self.out/'checkpoint-source').read_text()
        if source == banked:
            for name, path in self.paths.items():
                self.assertEqual((self.root/path).read_bytes(), (self.out/('checkpoint-'+name)).read_bytes())
            self.receipt('linked', installed=False, immutable_recovery_and_checkpoint_verified=True)
            return
        self.assertEqual(source, layout.install(banked))
        actual = (self.root/self.paths['elf']).read_bytes()
        expected = bytearray(self.checkpoint)
        offset = recovery.elf_slot_offset(self.checkpoint, recovery.screen.ENTRY, 274*4)
        struct.pack_into('>274I', expected, offset, *self.raw)
        self.assertEqual(bytes(expected), actual)
        self.assertEqual(recovery.metadata(self.checkpoint), recovery.metadata(actual))
        for name, path in self.paths.items():
            if name not in ('source', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), (self.out/('checkpoint-'+name)).read_bytes())
        audit = recovery.audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=True, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a, b in zip(self.checkpoint, actual)),
            changed_target_bytes=sum(a != b for a, b in zip(self.checkpoint[offset:offset+1096], actual[offset:offset+1096])),
            changed_extent_bytes=0, changed_metadata_bytes=0,
            all_other_ELF_bytes_names_values_extents_data_layout_guards_conversion_rows_exact=True, protected_data=audit)

    def test_09_actual_native32_complete_loader(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], recovery.NATIVE+layout.SELECTED+
                recovery.NATIVE_REFERENCE+recovery.NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''))
        before = 'func_10004074('+layout.MAIN+' - 0x38);'
        body = layout.SELECTED.replace(before, '(void)('+layout.MAIN+' - 0x38);')
        self.assertNotEqual(body, layout.SELECTED)
        code, _ = self.run_native('native-negative', recovery.NATIVE+body+recovery.NATIVE_REFERENCE+recovery.NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', cases_per_profile=6048, profiles=['O2', 'O0'],
            complete_C_every_modeled_memory_byte_and_helper_trace_reference=True,
            effective_missing_main_free_control=True)

    def test_11_ignored_incoming_word_and_install_guards(self):
        cases = 0
        for identity in (-1, 7, 186, 187, 255, 0x7FFFFFFF):
            for unused in (0, 1, 0xFFFFFFFF, 0x80000000):
                for present in (False, True):
                    for extras in (0, 1):
                        self.compare(recovery.fixture(identity=identity, present=present),
                            identity=identity, unused=unused, extras=extras)
                        cases += 1
        banked = (self.out/'checkpoint-source').read_text()
        self.assertEqual(layout.install(banked).count(layout.SELECTED), 1)
        for stale in ('', layout.install(banked), banked+banked):
            with self.assertRaises(ValueError):
                layout.install(stale)
        for name, before, after, settings in (
                ('incoming-status', '    failed = 0;\n', '', dict(unused=0x80000000, extras=0)),
                ('request-error', '        failed = 1;\n        goto done;',
                    '        failed = 0;\n        goto done;', dict(results=dict(request=0)))):
            body = layout.SELECTED.replace(before, after)
            self.assertNotEqual(body, layout.SELECTED)
            with patch.object(recovery.screen, 'ENTRY', 0x15400000):
                _, words = recovery.screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            correct = recovery.MainOracle(self.retail, recovery.fixture(), **settings).run()
            wrong = recovery.MainOracle(words, recovery.fixture(), entry=0x15400000, **settings).run()
            self.assertNotEqual((correct.r[2], correct.calls), (wrong.r[2], wrong.calls))
        self.receipt('scratch', cases=cases, executions=cases*2,
            incoming_second_word_ignored_on_early_returns_and_both_extras_gates=True,
            effective_stale_install_guards=3, effective_status_and_request_error_controls=2)

    def test_12_exact_remaining_difference_groups(self):
        spills = {0x98, 0x9C, 0xB8, 0xC8, 0xD8, 0xF0, 0x108, 0x384,
            0x3AC, 0x3C4, 0x3D4, 0x3EC, 0x3FC, 0x414}
        initialization = {0x1A4, 0x1B8}
        request = {0xB0, 0xB4}
        cleanup = {0x3BC, 0x3C0, 0x3CC, 0x3E4, 0x3E8, 0x3F4}
        different = {i*4 for i, (actual, retail) in enumerate(zip(self.raw, self.retail)) if actual != retail}
        self.assertEqual(different, spills | initialization | request | cleanup)
        for offset in spills:
            actual, retail = self.raw[offset//4], self.retail[offset//4]
            self.assertEqual(actual >> 16, retail >> 16)
            self.assertEqual(actual >> 21 & 31, 29)
            self.assertIn(actual & 65535, (0x50, 0x54))
            self.assertEqual(retail & 65535, (actual & 65535)+8)
        self.assertEqual(self.raw[0x1A4//4], self.retail[0x1B8//4])
        self.assertEqual(self.raw[0x1B8//4], self.retail[0x1A4//4])
        self.assertEqual((self.raw[0xB0//4], self.raw[0xB4//4]), (0x100000DA, 0x24160001))
        self.assertEqual((self.retail[0xB0//4], self.retail[0xB4//4]), (0x100000DB, 0x24020001))
        for offset in (0x3BC, 0x3E4):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0x8E040000, 0x8E020000))
        for offset in (0x3C0, 0x3E8):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0x50800005, 0x50400005))
        for offset in (0x3CC, 0x3F4):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0, 0x00402025))
        self.receipt('remaining', private_spill_references=sorted(spills),
            independent_initialization_words=sorted(initialization), request_return_words=sorted(request),
            cleanup_register_transfers=sorted(cleanup), total_raw_differences=len(different),
            all_other_250_words_directly_exact=True, private_faults_not_qualified=True, new_guards=0)


if __name__ == '__main__':
    unittest.main()
