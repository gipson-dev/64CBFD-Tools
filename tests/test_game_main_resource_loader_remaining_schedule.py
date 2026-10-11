"""Qualify the complete loader's recovered first-loop delay initialization."""
import csv
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_remaining_schedule as schedule
from tools.tests import test_game_main_resource_loader_private_layout as previous
from tools.tests import test_game_main_resource_loader as recovery
from tools.experiments import game_main_resource_loader_guarded_match as matching


class GameMainResourceLoaderRemainingScheduleTests(previous.GameMainResourceLoaderPrivateLayoutTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-main-resource-loader-remaining-schedule-test'
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
            assert schedule.BANKED in (cls.root/cls.paths['source']).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('checkpoint-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.checkpointHashes = json.loads(manifest.read_text())
        assert cls.checkpointHashes['source'] == 'e4f9fce4dedc2af6b504ce2ad7b23c253ef9254e4ba92bad340663ea4d30e0f9'
        assert cls.checkpointHashes['elf'] == '6fb98976111c9c1fa5a47bfcd078f8272a4b90535f273cf5fe5bc8532f5aac5c'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.checkpointHashes[name]
        for module, field, value in (
                (previous.layout, 'SELECTED', schedule.SELECTED),
                (previous.layout, 'install', schedule.install),
                (previous.layout.count, 'SELECTED', schedule.SELECTED),
                (recovery.screen, 'QUALIFIED', schedule.SELECTED)):
            selection = patch.object(module, field, value)
            selection.start()
            cls.addClassCleanup(selection.stop)
        cls.meta, cls.raw = schedule.measure(cls.root, cls.out, 'selected', schedule.SELECTED)
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
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (274, 0x78, 22))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.meta['saved_registers'], list(range(16, 23)))
        self.assertIn(22, self.meta['opening_zero_destinations'])
        self.assertEqual(self.meta['private_S5_stores'], [])
        self.assertEqual(self.meta['request_output_stack'], 0x6C)
        self.assertEqual(self.meta['private_stack_offsets'], [0x4C, 0x50, 0x54, 0x68])
        self.assertFalse(self.meta['masked_initial_count_store'])
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.raw)
        matching.validate_current_guards(self.root)
        self.receipt('shape', words=274, frame=0x78, raw_differences=22,
            original_first_count_private_store_and_delay_initialization=True,
            complete_body_still_nonmatching=True, new_guards=0)

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
        self.assertEqual(source, schedule.install(banked))
        actual = (self.root/self.paths['elf']).read_bytes()
        expected = bytearray(self.checkpoint)
        offset = recovery.elf_slot_offset(self.checkpoint, recovery.screen.ENTRY, 274*4)
        struct.pack_into('>274I', expected, offset, *matching.installed_words(self.root, self.raw))
        self.assertEqual(bytes(expected), actual)
        self.assertEqual(recovery.metadata(self.checkpoint), recovery.metadata(actual))
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
            changed_extent_bytes=0, changed_metadata_bytes=0,
            all_other_ELF_bytes_names_values_extents_data_layout_guards_conversion_rows_exact=True, protected_data=audit)

    def test_12_exact_remaining_difference_groups(self):
        spills = {0x98, 0x9C, 0xB8, 0xC8, 0xD8, 0xF0, 0x108, 0x384,
            0x3AC, 0x3C4, 0x3D4, 0x3EC, 0x3FC, 0x414}
        request = {0xB0, 0xB4}
        cleanup = {0x3BC, 0x3C0, 0x3CC, 0x3E4, 0x3E8, 0x3F4}
        different = {i*4 for i, (actual, retail) in enumerate(zip(self.raw, self.retail)) if actual != retail}
        self.assertEqual(different, spills | request | cleanup)
        for offset in spills:
            actual, retail = self.raw[offset//4], self.retail[offset//4]
            self.assertEqual(actual >> 16, retail >> 16)
            self.assertEqual(actual >> 21 & 31, 29)
            self.assertIn(actual & 65535, (0x50, 0x54))
            self.assertEqual(retail & 65535, (actual & 65535)+8)
        self.assertEqual((self.raw[0xB0//4], self.raw[0xB4//4]), (0x100000DA, 0x24160001))
        self.assertEqual((self.retail[0xB0//4], self.retail[0xB4//4]), (0x100000DB, 0x24020001))
        for offset in (0x3BC, 0x3E4):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0x8E040000, 0x8E020000))
        for offset in (0x3C0, 0x3E8):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0x50800005, 0x50400005))
        for offset in (0x3CC, 0x3F4):
            self.assertEqual((self.raw[offset//4], self.retail[offset//4]), (0, 0x00402025))
        banked_meta, banked = schedule.measure(self.root, self.out, 'banked', schedule.BANKED)
        self.assertEqual((banked_meta['body_words'], banked_meta['frame'], banked_meta['differences']), (274, 0x78, 24))
        changed = {i*4 for i, (old, new) in enumerate(zip(banked, self.raw)) if old != new}
        self.assertEqual(changed, {0x1A4, 0x1B8})
        self.assertEqual(self.raw[0x1A4//4], 0xAFA6004C)
        self.assertEqual(self.raw[0x1B8//4], 0x00008825)
        self.receipt('remaining', private_spill_references=sorted(spills),
            request_return_words=sorted(request), cleanup_register_transfers=sorted(cleanup),
            total_raw_differences=22, all_other_252_words_directly_exact=True,
            only_two_independent_initialization_words_changed=sorted(changed),
            private_faults_not_qualified=True, new_guards=0)


if __name__ == '__main__':
    unittest.main()
