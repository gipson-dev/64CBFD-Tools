"""Qualify the complete retail-length loader and audit the banked recovery."""
import csv
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_lifetimes as lifetime
from tools.tests import test_game_main_resource_loader as recovery
from tools.experiments import game_main_resource_loader_guarded_match as matching


class GameMainResourceLoaderLifetimeTests(recovery.GameMainResourceLoaderTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-main-resource-loader-lifetimes-test'
        cls.out.mkdir(exist_ok=True)
        original = cls.root/'conker/build/game-main-resource-loader-test'
        cls.paths = dict(source=lifetime.loader.SOURCE, elf='conker/build/conker.us.elf',
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
            assert lifetime.BANKED in (cls.root/cls.paths['source']).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('checkpoint-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.checkpointHashes = json.loads(manifest.read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.checkpointHashes[name]
        cls.selection = patch.object(lifetime.loader, 'QUALIFIED', lifetime.SELECTED)
        cls.selection.start()
        cls.addClassCleanup(cls.selection.stop)
        cls.meta, cls.raw = lifetime.loader.compile_candidate(cls.root, cls.out, 'selected')
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.checkpoint = (cls.out/'checkpoint-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>274I', cls.rom, lifetime.loader.ROM))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split(
            'glabel '+lifetime.loader.FUNCTION, 1)[1].split('endlabel '+lifetime.loader.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+lifetime.loader.FUNCTION+assembly+'endlabel '+lifetime.loader.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+lifetime.loader.FUNCTION+
            '\n.type '+lifetime.loader.FUNCTION+',@function\n'+lifetime.loader.FUNCTION+':\n'+assembly+
            '\n.size '+lifetime.loader.FUNCTION+',.-'+lifetime.loader.FUNCTION+'\n')
        cls.assemble('padded', recovery.emit_padded_assembly(cls.out/'selected.o', cls.slot,
            filename='generated_6A3D0'))

    def test_01_complete_slot_fitting_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (274, 0x80, 271))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.raw)
        matching.validate_current_guards(self.root)
        self.receipt('shape', words=274, slot_words=274, frame=0x80, retail_frame=0x78,
            raw_differences=271, matching_not_achieved=True, new_guards=0)

    def compare(self, memory, forms=None, **settings):
        models = super().compare(memory, forms=forms, **settings)
        if hasattr(self, 'rawReached') and forms is None:
            self.rawReached.update(models[1].visits)
        return models

    def test_02_full_reference_and_all_retail_words(self):
        self.rawReached = set()
        super().test_02_full_reference_and_all_retail_words()
        unreachable = {lifetime.loader.ENTRY+0x44}
        self.assertEqual(self.rawReached,
            set(range(lifetime.loader.ENTRY, lifetime.loader.ENTRY+274*4, 4))-unreachable)
        self.receipt('current-coverage', reached_current_words=len(self.rawReached),
            statically_unreachable_duplicate_compare=sorted(unreachable))

    def test_08_immutable_baseline_and_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            self.assertEqual(hashlib.sha256((self.out/('checkpoint-'+name)).read_bytes()).hexdigest(), self.checkpointHashes[name])
        source = (self.root/lifetime.loader.SOURCE).read_text()
        banked = (self.out/'checkpoint-source').read_text()
        if source == banked:
            for name, path in self.paths.items():
                self.assertEqual((self.root/path).read_bytes(), (self.out/('checkpoint-'+name)).read_bytes())
            self.receipt('linked', installed=False, immutable_recovery_and_checkpoint_verified=True)
            return
        lifetime_source = lifetime.install(banked)
        words = self.raw
        if source == lifetime_source:
            self.assertEqual(source, lifetime_source)
        else:
            from tools.experiments import game_main_resource_loader_count_lifetimes as count
            count_source = count.install(lifetime_source)
            if source == count_source:
                latest, words = lifetime.loader.compile_candidate(self.root, self.out, 'latest-count-lifetime', count.SELECTED)
                self.assertEqual((latest['body_words'], latest['frame'], latest['differences']), (274, 0x78, 98))
            else:
                from tools.experiments import game_main_resource_loader_private_layout as layout
                layout_source = layout.install(count_source)
                if source == layout_source:
                    latest, words = lifetime.loader.compile_candidate(self.root, self.out, 'latest-private-layout', layout.SELECTED)
                    self.assertEqual((latest['body_words'], latest['frame'], latest['differences']), (274, 0x78, 24))
                else:
                    from tools.experiments import game_main_resource_loader_remaining_schedule as schedule
                    self.assertEqual(source, schedule.install(layout_source))
                    latest, words = lifetime.loader.compile_candidate(self.root, self.out, 'latest-remaining-schedule', schedule.SELECTED)
                    self.assertEqual((latest['body_words'], latest['frame'], latest['differences']), (274, 0x78, 22))
            self.assertEqual((latest['diagnostics'], latest['pool_bytes']), ('', 0))
        actual = (self.root/self.paths['elf']).read_bytes()
        expected = bytearray(self.checkpoint)
        offset = recovery.elf_slot_offset(self.checkpoint, lifetime.loader.ENTRY, 274*4)
        struct.pack_into('>274I', expected, offset, *matching.installed_words(self.root, words))
        extent = recovery.installed.symbol_size_offset(self.checkpoint, lifetime.loader.FUNCTION, lifetime.loader.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.checkpoint, extent)[0], 272*4)
        struct.pack_into('>I', expected, extent, 274*4)
        previous, current = recovery.metadata(self.checkpoint), recovery.metadata(actual)
        self.assertEqual(previous[:2], current[:2])
        self.assertEqual(previous[3], current[3])
        symbols = previous[2].copy()
        target = next(s for s in symbols if s[0] == lifetime.loader.FUNCTION.encode() and s[1] == lifetime.loader.ENTRY)
        self.assertEqual(target[2], 272*4)
        symbols[target] -= 1
        symbols[(target[0], target[1], 274*4, *target[3:])] += 1
        self.assertEqual(+symbols, current[2])
        changed_metadata = 0
        for table in current[4:]:
            start, end = table[4], table[4]+table[5]
            changed_metadata += sum(a != b for a, b in zip(self.checkpoint[start:end], actual[start:end]))
            expected[start:end] = actual[start:end]
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            if name == 'guards':
                matching.current_guard_bytes(self.root, (self.out/'checkpoint-guards').read_bytes())
            elif name not in ('source', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), (self.out/('checkpoint-'+name)).read_bytes())
        audit = recovery.audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=True, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a, b in zip(self.checkpoint, actual)),
            changed_target_bytes=sum(a != b for a, b in zip(self.checkpoint[offset:offset+1096], actual[offset:offset+1096])),
            changed_extent_bytes=sum(a != b for a, b in zip(self.checkpoint[extent:extent+4], actual[extent:extent+4])),
            changed_metadata_bytes_including_extent=changed_metadata,
            all_other_ELF_bytes_names_values_data_layout_guards_conversion_rows_exact=True, protected_data=audit)

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
        self.assertEqual(lifetime.install(banked).count(lifetime.SELECTED), 1)
        for stale in ('', lifetime.install(banked), banked+banked):
            with self.assertRaises(ValueError):
                lifetime.install(stale)
        body = lifetime.SELECTED.replace('    failed = 0;\n', '')
        self.assertNotEqual(body, lifetime.SELECTED)
        with patch.object(lifetime.loader, 'ENTRY', 0x15400000):
            _, words = lifetime.loader.compile_candidate(self.root, self.out, 'negative-incoming-status', body)
        settings = dict(unused=0x80000000, extras=0)
        correct = recovery.MainOracle(self.retail, recovery.fixture(), **settings).run()
        wrong = recovery.MainOracle(words, recovery.fixture(), entry=0x15400000, **settings).run()
        self.assertNotEqual((correct.r[2], correct.calls), (wrong.r[2], wrong.calls))
        self.receipt('scratch', cases=cases, executions=cases*2,
            incoming_second_word_ignored_on_early_returns_and_both_extras_gates=True,
            effective_stale_install_guards=3, effective_incoming_status_control=True)


if __name__ == '__main__':
    unittest.main()
