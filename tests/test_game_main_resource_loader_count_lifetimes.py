"""Qualify the complete original-frame loader and its committed-baseline delta."""
import csv
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_count_lifetimes as count
from tools.tests import test_game_main_resource_loader as recovery
from tools.tests import test_game_main_resource_loader_lifetimes as previous


class GameMainResourceLoaderCountLifetimeTests(previous.GameMainResourceLoaderLifetimeTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-main-resource-loader-count-lifetimes-test'
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
            assert count.flow.lifetime.SELECTED in (cls.root/cls.paths['source']).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('checkpoint-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.checkpointHashes = json.loads(manifest.read_text())
        assert cls.checkpointHashes['source'] == '25fd41ff70c4fb4db5c7649c74c27fbd4d72ed10831f95ffcb1abdaf75f18a52'
        assert cls.checkpointHashes['elf'] == '2129eb586ceac58a8201542a83a62601853a16d8589f49596fdeb137fb02fcaf'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.checkpointHashes[name]
        cls.selection = patch.object(recovery.screen, 'QUALIFIED', count.SELECTED)
        cls.selection.start()
        cls.addClassCleanup(cls.selection.stop)
        cls.meta, cls.raw = count.measure(cls.root, cls.out, 'selected', count.SELECTED)
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
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (274, 0x78, 98))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.meta['saved_registers'], list(range(16, 23)))
        self.assertIn(22, self.meta['opening_zero_destinations'])
        self.assertEqual(self.meta['private_S5_stores'], [])
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.raw)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse(any(row['function'] == recovery.screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('shape', words=274, slot_words=274, frame=0x78, retail_frame=0x78,
            raw_differences=98, saved_registers=list(range(16, 23)), early_status_S6=True,
            private_count_pointer_copy_removed=True, matching_not_achieved=True, new_guards=0)

    def test_02_full_reference_and_all_retail_words(self):
        self.rawReached = set()
        recovery.GameMainResourceLoaderTests.test_02_full_reference_and_all_retail_words(self)
        unreachable = {recovery.screen.ENTRY+0x48}
        self.assertEqual(self.rawReached,
            set(range(recovery.screen.ENTRY, recovery.screen.ENTRY+274*4, 4))-unreachable)
        self.receipt('current-coverage', reached_current_words=len(self.rawReached),
            statically_unreachable_duplicate_compare=sorted(unreachable))

    def test_06_effective_compiled_semantic_controls(self):
        controls = (
            ('identity-signed', 'identity >= 0xBB', '(u32)identity >= 0xBB', recovery.fixture(identity=-1), dict(identity=-1)),
            ('cached-presence', 'D_800D19A0[identity] != NULL', 'D_800D19A0[identity] == NULL', recovery.fixture(present=True), {}),
            ('request-kind', '&output, 7, 0, 2, 1, identity', '&output, 6, 0, 2, 1, identity', recovery.fixture(), {}),
            ('publication-offset', '(u8 *)block + 0x38', '(u8 *)block + 0x30', recovery.fixture(), {}),
            ('cached-count', 'index < D_800C4778[identity]', 'index < 2', recovery.fixture(first_count=2, second_count=0),
                dict(actions={('child', 0): ((recovery.address('D_800C4778'), 1, 2),)})),
            ('extras-flag', 'if (extras != 0)', 'if (extras == 0)', recovery.fixture(), dict(extras=1)),
            ('config-mask', '& 0x4000', '& 0x2000', recovery.fixture(flags=0x4000), dict(results=dict(auxiliary=1))),
            ('auxiliary-error', 'failed |= 8', 'failed |= 4', recovery.fixture(flags=0x4000), dict(results=dict(auxiliary=1))),
            ('skip-free', 'func_10004074(D_800D19A0[identity] - 0x38)', '(void)(D_800D19A0[identity] - 0x38)',
                recovery.fixture(), dict(results=dict(secondary=4))),
            ('clear-before-free', 'func_10004074(*cleanupSlot);\n            *cleanupSlot = NULL;',
                '*cleanupSlot = NULL;\n            func_10004074(*cleanupSlot);', recovery.fixture(), dict(results=dict(secondary=4))),
        )
        for name, before, after, memory, settings in controls:
            body = count.SELECTED.replace(before, after)
            self.assertNotEqual(body, count.SELECTED)
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
        count_source = count.install(banked)
        words = self.raw
        if source != count_source:
            from tools.experiments import game_main_resource_loader_private_layout as layout
            layout_source = layout.install(count_source)
            if source == layout_source:
                latest, words = count.measure(self.root, self.out, 'latest-private-layout', layout.SELECTED)
                self.assertEqual((latest['body_words'], latest['frame'], latest['differences']), (274, 0x78, 24))
            else:
                from tools.experiments import game_main_resource_loader_remaining_schedule as schedule
                self.assertEqual(source, schedule.install(layout_source))
                latest, words = count.measure(self.root, self.out, 'latest-remaining-schedule', schedule.SELECTED)
                self.assertEqual((latest['body_words'], latest['frame'], latest['differences']), (274, 0x78, 22))
            self.assertEqual((latest['diagnostics'], latest['pool_bytes']), ('', 0))
        actual = (self.root/self.paths['elf']).read_bytes()
        expected = bytearray(self.checkpoint)
        offset = recovery.elf_slot_offset(self.checkpoint, recovery.screen.ENTRY, 274*4)
        struct.pack_into('>274I', expected, offset, *words)
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
            code, detail = self.run_native('native-'+profile[1:], recovery.NATIVE+count.SELECTED+
                recovery.NATIVE_REFERENCE+recovery.NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''))
        body = count.SELECTED.replace('func_10004074(D_800D19A0[identity] - 0x38);',
            '(void)(D_800D19A0[identity] - 0x38);')
        self.assertNotEqual(body, count.SELECTED)
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
        self.assertEqual(count.install(banked).count(count.SELECTED), 1)
        for stale in ('', count.install(banked), banked+banked):
            with self.assertRaises(ValueError):
                count.install(stale)
        for name, before, after, settings in (
                ('incoming-status', '    failed = 0;\n', '', dict(unused=0x80000000, extras=0)),
                ('request-error', '        failed = 1;\n        goto done;',
                    '        failed = 0;\n        goto done;', dict(results=dict(request=0)))):
            body = count.SELECTED.replace(before, after)
            self.assertNotEqual(body, count.SELECTED)
            with patch.object(recovery.screen, 'ENTRY', 0x15400000):
                _, words = recovery.screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            correct = recovery.MainOracle(self.retail, recovery.fixture(), **settings).run()
            wrong = recovery.MainOracle(words, recovery.fixture(), entry=0x15400000, **settings).run()
            self.assertNotEqual((correct.r[2], correct.calls), (wrong.r[2], wrong.calls))
        self.receipt('scratch', cases=cases, executions=cases*2,
            incoming_second_word_ignored_on_early_returns_and_both_extras_gates=True,
            effective_stale_install_guards=3, effective_status_and_request_error_controls=2)


if __name__ == '__main__':
    unittest.main()
