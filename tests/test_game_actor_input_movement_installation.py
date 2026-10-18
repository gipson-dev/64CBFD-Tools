"""Whole-image movement installation, exact history and real installed words."""
import csv
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_installation as install
from tools.tests import movement_install_checkpoint as checkpoint
from tools.tests import test_game_actor_input_movement_tail_match as prior


class MovementInstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / install.BUILD

    def test_01_complete_prelink_prediction_and_guard_extension(self):
        expected = install.expected_inputs(self.root, self.out)
        self.assertEqual({k: install.digest(v) for k, v in expected.items()}, checkpoint.AFTER)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual((self.out / 'prelink-baseline.elf').read_bytes(), checkpoint.fixture(self.root, 'before', 'elf'))
        self.assertEqual((self.out / 'prelink-prediction.elf').read_bytes(), expected['elf'])
        before = checkpoint.fixture(self.root, 'before', 'guards')
        self.assertTrue(expected['guards'].startswith(before))
        old = list(csv.DictReader(io.StringIO(before.decode())))
        rows = list(csv.DictReader(io.StringIO(expected['guards'].decode())))[len(old):]
        self.assertEqual(len(rows), 134)
        self.assertEqual({(r['filename'], r['function']) for r in rows}, {('generated_11FF10', 'func_150F34F4')})
        self.assertFalse(any(r['omit'] == 'true' for r in rows))
        self.assertEqual(sum(r['expected_relocations'] != r['replacement_relocations'] for r in rows), 2)
        proof = json.loads((self.out / 'prelink-prediction.json').read_text())
        self.assertEqual(tuple(proof[k] for k in ('changed_ELF_bytes', 'code_bytes', 'extent_bytes', 'metadata_bytes', 'exact_symbol_groups', 'metadata_exclusions')),
                         (3579, 3010, 2, 567, 22, 0))

    def test_02_exact_history_and_effective_corruption_controls(self):
        controls = 0
        original_read, original_text = Path.read_bytes, Path.read_text
        for key, path in checkpoint.PATHS.items():
            old, new = checkpoint.fixture(self.root, 'before', key), checkpoint.fixture(self.root, 'after', key)
            for value in (old, new):
                self.assertEqual(checkpoint.previous_input(value, self.root / path, self.root), old)
                bad = bytearray(value)
                bad[len(bad) // 2] ^= 1
                with self.assertRaisesRegex(ValueError, 'Unexpected live movement input'):
                    checkpoint.previous_input(bytes(bad), self.root / path, self.root)
                controls += 1
            for stage in ('before', 'after'):
                target = self.out / (stage + '-' + key)
                value = checkpoint.raw_read(target)
                bad = bytearray(value)
                bad[len(bad) // 2] ^= 1
                reader = checkpoint.raw_read
                with patch.object(checkpoint, 'raw_read', lambda p: bytes(bad) if p == target else reader(p)):
                    with self.assertRaisesRegex(ValueError, 'Changed immutable movement fixture'):
                        checkpoint.previous_input(new, self.root / path, self.root)
                controls += 1
        unaffected = self.root / 'conker/Makefile'
        outside = self.root.parent / 'unrelated' / 'conker/build/conker.us.elf'
        self.assertEqual(checkpoint.previous_input(b'untouched', unaffected, self.root), b'untouched')
        self.assertEqual(checkpoint.previous_input(b'untouched', outside, self.root), b'untouched')
        with checkpoint.historical_view(self.root):
            for key, path in checkpoint.PATHS.items():
                self.assertEqual((self.root / path).read_bytes(), checkpoint.fixture(self.root, 'before', key))
                self.assertEqual(checkpoint.raw_read(self.root / path), original_read(self.root / path))
            self.assertEqual(unaffected.read_bytes(), original_read(unaffected))
            self.assertEqual((self.root / checkpoint.PATHS['record_gate_owner']).read_text(),
                             checkpoint.fixture(self.root, 'before', 'record_gate_owner').decode())
            with self.assertRaises(RuntimeError):
                with checkpoint.historical_view(self.root):
                    pass
            controls += 1
        with self.assertRaisesRegex(RuntimeError, 'view cleanup control'):
            with checkpoint.historical_view(self.root):
                raise RuntimeError('view cleanup control')
        self.assertIs(Path.read_bytes, original_read)
        self.assertIs(Path.read_text, original_text)
        prediction = self.out / 'initial-prediction.json'
        reader = checkpoint.raw_text
        with patch.object(checkpoint, 'raw_text', lambda p: '{}' if p == prediction else reader(p)):
            with self.assertRaisesRegex(ValueError, 'immutable movement prediction'):
                checkpoint.verify(self.root)
        controls += 1
        (self.out / 'history-controls.json').write_text(json.dumps(dict(effective_controls=controls,
            three_exact_members=True, unrelated_and_outside_paths_not_masked=True,
            original_readers_restored_after_exception=True, older_sources_and_hashes_unchanged=True), indent=2) + '\n')

    def test_03_all_named_serialization_groups_have_effective_controls(self):
        controls = 0
        for i, (names, order, definitions) in enumerate(install.SERIALIZATION):
            changed = list(install.SERIALIZATION)
            changed[i] = (names, tuple(reversed(order)), definitions)
            with patch.object(install, 'SERIALIZATION', tuple(changed)):
                self.assertNotEqual(install.expected_inputs(self.root, self.out)['elf'], checkpoint.fixture(self.root, 'after', 'elf'))
            controls += 1
            changed = list(install.SERIALIZATION)
            wrong = list(definitions)
            wrong[0] = (wrong[0][0] ^ 4, *wrong[0][1:])
            changed[i] = (names, order, tuple(wrong))
            with patch.object(install, 'SERIALIZATION', tuple(changed)), self.assertRaises(AssertionError):
                install.expected_inputs(self.root, self.out)
            controls += 1
        self.assertEqual((len(install.SERIALIZATION), sum(len(g[0]) for g in install.SERIALIZATION), controls), (22, 54, 44))
        (self.out / 'serialization-controls.json').write_text(json.dumps(dict(effective_controls=controls,
            exact_groups=22, exact_definitions=54, metadata_exclusions=0), indent=2) + '\n')

    def test_04_actual_installed_ELF_and_all_protected_members(self):
        row = install.audit(self.root, self.out)
        self.assertEqual((row['installed'], row['compared_bodies'], row['target_words']), (True, 6057, 959))
        self.assertEqual(row['successor_SHA'], checkpoint.AFTER['elf'])
        self.assertTrue(row['actual_target_object_identical'])
        path = self.root / 'conker/build/src/game/generated_11FF10.c.o'
        original = install.recovery.parts
        data, bindings = original(path)
        wrong = bytearray(data)
        wrong[0] ^= 1
        for changed in ((bytes(wrong), bindings), (data, {})):
            with patch.object(install.recovery, 'parts', lambda p: changed if p == path else original(p)):
                with self.assertRaisesRegex(ValueError, 'actual object bytes or relocations'):
                    install.audit(self.root, self.out)
        (self.out / 'actual-object-controls.json').write_text(json.dumps(dict(effective_controls=2,
            actual_object_not_just_linked_words=True), indent=2) + '\n')


class InstalledMovementBehaviorTests(prior.MovementTailMatchTests):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        checkpoint.verify(root, installed=True)
        actual = checkpoint.raw_read(root / checkpoint.PATHS['elf'])
        offset = install.elf_slot_offset(actual, install.recovery.ENTRY, install.recovery.SIZE)
        installed_words = list(struct.unpack_from('>959I', actual, offset))
        cls.view = checkpoint.historical_view(root)
        cls.view.__enter__()
        try:
            super().setUpClass()
            if cls.words != installed_words:
                raise ValueError('Installed movement behavior suite would test a different object')
            cls.words = installed_words
            cls.harness.words = installed_words
        except BaseException:
            cls.view.__exit__(None, None, None)
            raise

    @classmethod
    def tearDownClass(cls):
        cls.view.__exit__(None, None, None)


if __name__ == '__main__':
    unittest.main()
