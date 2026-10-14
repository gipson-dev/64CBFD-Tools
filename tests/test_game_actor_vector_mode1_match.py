"""Qualify the complete mode-1 callback using the mode-0 snapshot gates."""
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_vector_mode1_candidates as source
from tools.tests import test_game_actor_vector_snapshot_match as vector


class GameActorVectorMode1MatchTests(vector.GameActorVectorSnapshotMatchTests):
    BUILD_NAME = 'game-actor-vector-mode1-match-test'
    SOURCE_PIN = '2693d762473eda06176457fb4bfa041c953b53258e6ca84a3c443f8bd039e422'
    ELF_PIN = '3f55344bf1320fc76c68057c98eb1f6dfbf80489a62e084bca4a0aa97d59b33c'

    @classmethod
    def setUpClass(cls):
        # The inherited gates run sequentially with a bounded target binding.
        binding = patch.object(vector, 'source', source)
        binding.start()
        cls.addClassCleanup(binding.stop)
        super().setUpClass()

    def test_13_mode0_neighbor_and_named_symbol_corruptions(self):
        read_bytes = Path.read_bytes
        path = self.root / self.paths['elf']
        data = path.read_bytes()
        with patch.object(vector.image.screen, 'ENTRY', source.ENTRY):
            size = vector.image.elf_symbol_size_offset(data, source.FUNCTION)
        for offset in (vector.image.elf_slot_offset(data, 0x1506A79C, 160),
                vector.image.elf_slot_offset(data, 0x1506A864, 260), size - 8, size):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k:
                    bytes(bad) if p == path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_literal_image_source_and_protected_history()
        self.assertEqual(self.retail[35], 0x24070001)
        original_mode0 = struct.unpack_from('>40I', self.rom, 0x97C4C)
        self.assertEqual(original_mode0[35], 0x00003825)
        self.assertEqual(sum(a != b for a, b in zip(original_mode0, self.retail)), 1)
        self.assertEqual((source.MODE, source.TABLE_INDEX, source.TABLE_ROM), (1, 7, 0x22ABEC))
        installed = (self.root / self.paths['source']).read_text() == self.owner_after
        slot = vector.image.elf_slot_offset(data, source.ENTRY, 160)
        code_changes = sum(a != b for a, b in zip(self.before[slot:slot + 160], data[slot:slot + 160]))
        size_changes = sum(a != b for a, b in zip(self.before[size:size + 4], data[size:size + 4]))
        self.assertEqual((code_changes, size_changes), (123, 1) if installed else (0, 0))
        self.receipt('mode-controls', original_mode0_neighbor_and_prior_spawn_protected=True,
            named_symbol_name_and_size_mutations_effective=True,
            instruction_changed_bytes=code_changes, symbol_size_changed_bytes=size_changes,
            sole_mode0_vs_mode1_instruction_is_actual_JAL_delay=True)


if __name__ == '__main__':
    import unittest
    unittest.main()
