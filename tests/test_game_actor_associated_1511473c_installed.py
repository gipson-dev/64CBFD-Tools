"""Regression checks for the installed actor-associated update."""
from pathlib import Path
import csv
import os
import struct
import subprocess
import sys
import unittest

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-actor-associated-update-1511473c-screen'
NAME = 'func_1511473C'


class InstalledActorAssociatedUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'conker/src/game/generated_13D350.c'
        OUT.mkdir(parents=True, exist_ok=True)
        cls.raw, diagnostics = compile_owner(ROOT, OUT, source.read_text(), 'installed')
        if diagnostics:
            raise AssertionError(diagnostics)
        cls.guarded = ROOT / 'conker/build/src/game/generated_13D350.c.o'
        cls.env = dict(os.environ, CBFD_CONSUMER_ROOT=str(ROOT),
                       ACTOR_ASSOC_RAW=str(cls.raw), ACTOR_ASSOC_GUARDED=str(cls.guarded),
                       ACTOR_ASSOC_SOURCE=str(source), PYTHONDONTWRITEBYTECODE='1')

    def test_fresh_source_and_installed_slot(self):
        symbols = {r[1]: r[2][1] for r in symbol_rows((ROOT / 'conker/build/conker.us.elf').read_bytes())}
        actual = bound_blob(*payload(self.guarded, NAME), symbols)
        retail = list(struct.unpack_from('>91I', (ROOT / 'conker/conker.us.bin').read_bytes(), 0x141bec))
        self.assertEqual(actual, retail)
        raw, relocs = payload(self.raw, NAME)
        words = struct.unpack('>91I', raw)
        bound = bound_blob(raw, relocs, symbols)
        with (ROOT / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = [row for row in csv.DictReader(stream) if row['function'] == NAME]
        self.assertEqual(len(rows), 33)
        offsets = {int(row['offset'], 0) for row in rows}
        self.assertEqual({i * 4 for i, (a, b) in enumerate(zip(bound, retail)) if a != b}, offsets)
        for row in rows:
            offset = int(row['offset'], 0)
            self.assertEqual(words[offset // 4], int(row['expected'], 0))
            self.assertEqual(';'.join('%s:%s' % pair for pair in relocs.get(offset, [])) or '-',
                             row['expected_relocations'])

    def test_installed_guest_and_native_behavior(self):
        for module in ('behavior', 'alias', 'global_mutation', 'extended', 'caller', 'native', 'controls'):
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, '-m',
                    'tools.tests.game_actor_associated_1511473c_' + module],
                    cwd=ROOT, env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
