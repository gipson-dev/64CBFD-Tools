"""Installed effect update: retail words, padding, guest and native checks."""
from pathlib import Path
import os
import subprocess
import sys
import unittest

from tools.experiments.game_remaining_donor_candidates import compile_owner


class EffectUpdate151A8CECTests(unittest.TestCase):
    def test_installed_owner(self):
        root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path.cwd())).resolve()
        out = root / 'conker/build/game-effect-update-151a8cec-screen'
        out.mkdir(parents=True, exist_ok=True)
        owner = (root / 'conker/src/game/generated_1D4E00.c').read_text()
        self.assertIn('void func_151A8CEC(struct260 *owner)', owner)
        compile_owner(root, out, owner, 'baseline')
        compile_owner(root, out, owner, 'selected')
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(root))
        for part in ('guard', 'padder', 'behavior', 'native'):
            module = 'tools.tests.game_effect_update_151a8cec_' + part
            result = subprocess.run([sys.executable, '-m', module], cwd=root, env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, module + '\n' + result.stdout + '\n' + result.stderr)
            print(module + ': ' + result.stdout.strip(), flush=True)


if __name__ == '__main__':
    unittest.main()
