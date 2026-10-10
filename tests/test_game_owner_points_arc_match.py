"""Full arc raw/guarded qualification and exact whole-ELF installation audit."""
import csv
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_matching as matching
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_points_arc_recovery as recovery
from tools.tests import test_game_owner_points_arc_branch_fold as prior
from tools.tests import test_game_owner_points_arc_endpoint_reads as endpoint
from tools.tests import test_game_owner_points_initializer_match as initializer


class GameOwnerPointsArcMatchTests(prior.GameOwnerPointsArcBranchFoldTests):
    @classmethod
    def setUpClass(cls):
        for module, name, value in ((prior, 'fitting', matching),
                (recovery.screen, 'COMPACT', matching.SELECTED), (recovery.screen, 'TYPES', matching.TYPES)):
            handle = patch.object(module, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-match-test'
        cls.meta, cls.words = matching.compile_candidate(cls.root, cls.out, 'recovered')
        cls.raw_meta, cls.raw = matching.source.compile_candidate(cls.root, cls.out, 'raw', matching.SELECTED)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>142I', cls.rom, matching.base.ROM))
        cls.paths = dict(source=matching.base.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(baseline.read_text())
        assert cls.baseline == json.loads((cls.root / 'conker/build/game-owner-points-arc-test/baseline.json').read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.rows = matching.guard_rows(cls.out / 'recovered.o')
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        assert not any(row['function'] == matching.base.FUNCTION for row in cls.old_rows)
        cls.guards = cls.out / 'match-only.csv'
        for path, rows in ((cls.guards, cls.rows), (cls.out / 'qualified-guards.csv', cls.old_rows + cls.rows)):
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        retail = cls.out / 'retail-slot.s'
        retail.write_text(cls.original_fragment(cls))
        assembly = cls.out / 'folded.s'
        assembly.write_text(emit_padded_assembly(cls.out / 'recovered.o', retail,
            word_patches_path=cls.guards, filename='generated_1E0560'))
        cls.folded_obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.folded_obj), str(assembly)],
            check=True, capture_output=True)

    def test_01_complete_source_profile_and_form_discriminators(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (142, 136, 0, 0))
        self.assertEqual((self.raw_meta['body_words'], self.raw_meta['differences']), (144, 138))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.words, self.retail)
        self.assertEqual(matching.normalize(self.raw), self.retail)
        self.assertEqual((matching.SELECTED, matching.TYPES),
            (matching.control.SELECTED, matching.control.TYPES))
        certificate = matching.certify(self.raw)
        self.assertEqual([path['helper_calls'] for path in certificate['symbolic_paths']], [21, 21, 0])
        self.assertEqual([path['public_writes'] for path in certificate['symbolic_paths']], [30, 30, 0])
        self.receipt('shape', dict(selected=self.meta, raw=self.raw_meta, certificate=certificate,
            all_142_retail_words_equal=True, semantic_source_unchanged_since_note1194=True,
            prior35_forms_and_48_retained_suites_reused_not_called_fresh=True,
            plain_C_match_not_claimed=True))

    def test_06_original_relocations_and_independent_symbol_rebases(self):
        prior.GameOwnerPointsArcBranchFoldTests.test_06_original_relocations_and_independent_symbol_rebases(self)
        for index in range(4):
            original = sections(self.out / ('rebase-%d-original.elf' % index))['.text'][1][:568]
            fitted = sections(self.out / ('rebase-%d-folded.elf' % index))['.text'][1][:568]
            self.assertEqual(original, fitted)

    def test_07_actual_owner_neighbors_and_padding_frame_rejection(self):
        relative = str((self.out / 'before-guards').relative_to(self.root))
        with patch.dict(self.paths, guards=relative):
            prior.GameOwnerPointsArcBranchFoldTests.test_07_actual_owner_neighbors_and_padding_frame_rejection(self)

    def test_08_production_data_registration_and_progress_unchanged(self):
        source = (self.root / self.paths['source']).read_text()
        if matching.base.ORIGINAL in source:
            recovery.GameOwnerPointsArcRecoveryTests.test_08_production_data_registration_and_progress_unchanged(self)
            return
        self.assertIn(matching.SELECTED, source)
        before_source = (self.out / 'before-source').read_text()
        expected_source = before_source.replace('/* Non-matching placeholders',
            matching.base.DECLARATIONS + matching.DELTA_TYPE + '\n/* Non-matching placeholders', 1).replace(
                matching.base.ORIGINAL, matching.SELECTED)
        self.assertEqual(source, expected_source)
        with (self.root / self.paths['guards']).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows, self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith(
            (self.out / 'before-guards').read_bytes()))
        self.assertEqual((self.root / self.paths['progress']).read_bytes(), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>142I', expected, elf_slot_offset(before, matching.base.ENTRY, 568), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=matching.base.FUNCTION, ENTRY=matching.base.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 568)
        actual = (self.root / self.paths['elf']).read_bytes()
        expected_metadata, actual_metadata = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(expected_metadata[:4], actual_metadata[:4])
        for section in expected_metadata[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008FAFC - start)[0], matching.base.ENTRY)
        self.receipt('installation', dict(installed=True, all_568_target_bytes_retail_exact=True,
            entire_ELF_only_target_slot_and_symbol_size_semantically_change=True,
            decoded_symbol_and_string_tables_equal=True, old_guard_history_unchanged=True,
            conversion_rows_byte_identical=True, protected_data=audit, registration_unchanged=True))

    def test_11_effective_private_home_controls_and_endpoint_reads(self):
        endpoint.GameOwnerPointsArcEndpointReadTests.test_11_effective_private_home_controls_and_endpoint_reads(self)
        text, functions, _ = parse_object(self.out / 'recovered.o')
        target = functions[matching.base.FUNCTION]
        object_bytes = (self.out / 'recovered.o').read_bytes()
        header = ELF_HEADER.unpack_from(object_bytes)
        headers = [SECTION_HEADER.unpack_from(object_bytes, header[6] + i * header[11])
            for i in range(header[12])]
        names = headers[header[13]]
        strings = object_bytes[names[4]:names[4] + names[5]]
        text_offset = next(section[4] for section in headers
            if strings[section[0]:].split(b'\0', 1)[0] == b'.text')
        for offset in range(0, 144 * 4, 4):
            changed = bytearray(object_bytes)
            struct.pack_into('>I', changed, text_offset + target['value'] + offset, self.raw[offset // 4] ^ 1)
            stale = self.out / 'stale.o'
            stale.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'stale word patch for ' + matching.base.FUNCTION + r'\+0x%X:' % offset):
                emit_padded_assembly(stale, self.out / 'retail-slot.s',
                    word_patches_path=self.guards, filename='generated_1E0560')
        mutations = ((0x70, 0), (0x88, 0), (0x110, self.words[0x110 // 4] ^ (2 << 6)),
            (0x184, self.words[0x184 // 4] ^ (3 << 11)), (0x1FC, 0))
        for offset, replacement in mutations:
            changed = self.words.copy()
            changed[offset // 4] = replacement
            rejected = False
            for first, second in ((True, False), (False, True), (False, False)):
                try:
                    old, new = matching.execute(self.words, first, second), matching.execute(changed, first, second)
                except (ValueError, TypeError, KeyError):
                    rejected = True
                    break
                if any(old[key] != new[key] for key in ('memory', 'calls', 'branches', 'saved_GP', 'saved_FP')):
                    rejected = True
                    break
            self.assertTrue(rejected, hex(offset))
        self.receipt('proof-negatives', dict(actual_padder_stale_words_rejected=144,
            effective_live_Z_half_FP_counter_angle_negatives=len(mutations),
            independent_read_and_private_home_controls_retained=True))


if __name__ == '__main__':
    import unittest
    unittest.main()
