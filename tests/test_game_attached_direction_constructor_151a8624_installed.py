"""Installed attached direction constructor: retail words, padding, guest and native checks."""
from pathlib import Path
import os
import subprocess
import sys
import unittest

from tools.experiments.game_remaining_donor_candidates import compile_owner


class AttachedDirectionConstructor151A8624Tests(unittest.TestCase):
    def test_installed_owner(self):
        root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path.cwd())).resolve()
        out = root / 'conker/build/game-attached-direction-constructor-151a8624-screen'
        out.mkdir(parents=True, exist_ok=True)
        owner = (root / 'conker/src/game/generated_1D4E00.c').read_text()
        self.assertIn('s32 func_151A8624(u8 *owner', owner)
        compile_owner(root, out, owner, 'baseline')
        compile_owner(root, out, owner, 'selected')
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(root))
        for part in ('guard', 'padder', 'behavior', 'native'):
            module = 'tools.tests.game_attached_direction_constructor_151a8624_' + part
            result = subprocess.run([sys.executable, '-m', module], cwd=root, env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, module + '\n' + result.stdout + '\n' + result.stderr)
            print(module + ': ' + result.stdout.strip(), flush=True)


if __name__ == '__main__':
    unittest.main()
