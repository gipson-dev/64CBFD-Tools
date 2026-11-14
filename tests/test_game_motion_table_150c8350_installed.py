"""Installed motion-table source, retail bytes, guards and behavioral checks."""
from pathlib import Path
import csv, os, struct, subprocess, sys, unittest
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions

class InstalledMotionTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
        cls.out = cls.root / 'conker/build/game-motion-table-150c8350-screen'
        cls.out.mkdir(parents=True, exist_ok=True)
        cls.source = cls.root / 'conker/src/game/generated_F5800.c'
        cls.object, diagnostics = compile_owner(cls.root, cls.out, cls.source.read_text(), 'installed')
        assert not diagnostics, diagnostics
        elf = cls.root / 'conker/build/conker.us.elf'
        cls.symbols = {r[1]: r[2][1] for r in symbol_rows(elf.read_bytes())}
        cls.functions, _, cls.addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        cls.raw = bound_blob(*payload(cls.object, 'func_150C8350'), cls.symbols)
        rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>105I', rom, 0xF5800))
        cls.wrapper = list(struct.unpack_from('>10I', rom, 0xF59A4))

    def test_fresh_source_and_installed_slot(self):
        self.assertEqual(self.addresses['func_150C8350'], 0x150C8350)
        self.assertEqual(self.functions['func_150C8350'], self.retail)
        self.assertEqual(self.functions['func_150C84F4'], self.wrapper)
        self.assertEqual(len(self.raw), 105)
        changed = [i for i, (a, b) in enumerate(zip(self.raw, self.retail)) if a != b]
        self.assertEqual(changed, [42, 44])
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = [r for r in csv.DictReader(stream) if r['filename'] == 'generated_F5800'
                    and r['function'] == 'func_150C8350']
        self.assertEqual(len(rows), 2)
        for row in rows:
            i = int(row['offset'], 0) // 4
            self.assertEqual(self.raw[i], int(row['expected'], 0))
            self.assertEqual(self.retail[i], int(row['replacement'], 0))
            self.assertIn(row['expected_relocations'], ('', '-'))
            self.assertIn(row['replacement_relocations'], ('', '-'))
            self.assertFalse(row['insert_after'])
            self.assertNotEqual(row['omit'].lower(), 'true')

    def test_installed_guest_and_native_behavior(self):
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(self.root), PYTHONDONTWRITEBYTECODE='1',
                   MOTION_TABLE_RAW_OBJECT=str(self.object), MOTION_TABLE_SOURCE=str(self.source),
                   MOTION_TABLE_GUARD_OBJECT=str(self.root / 'conker/build/src/game/generated_F5800.c.o'))
        for name in ('behavior', 'controls', 'alias', 'self_alias', 'caller', 'fault', 'native'):
            with self.subTest(screen=name):
                result = subprocess.run([sys.executable, '-m', 'tools.tests.game_motion_table_150c8350_' + name],
                                        cwd=self.root, env=env, capture_output=True, text=True, timeout=600)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
