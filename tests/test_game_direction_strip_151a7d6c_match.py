"""Qualify the renderer proposal or installed owner without production mutations."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import unittest

from tools.experiments import game_direction_strip_151a7d6c_candidates as source
from tools.experiments.game_paired_ground_constructor_match import payload


class DirectionStrip151A7D6CMatchTests(unittest.TestCase):
    def test_qualified_owner(self):
        root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path.cwd())).resolve()
        protected = (source.SOURCE, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/progress.csv')
        fingerprints = {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                        for p in protected}
        installed = source.PLACEHOLDER not in (root / source.SOURCE).read_text()
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_direction_strip_151a7d6c_candidates',
                       'tools.experiments.game_direction_strip_151a7d6c_match',
                       'tools.tests.game_direction_strip_151a7d6c_padder',
                       'tools.tests.game_direction_strip_151a7d6c_oracle',
                       'tools.tests.game_direction_strip_151a7d6c_extended',
                       'tools.tests.game_direction_strip_151a7d6c_native'):
            result = subprocess.run([sys.executable, '-m', module], cwd=root,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0,
                             module + '\n' + result.stdout + '\n' + result.stderr)
            print(module + ': ' + result.stdout.strip(), flush=True)
        report = json.loads((root / source.BUILD / 'selected-report.json').read_text())
        self.assertEqual((report['words'], report['frame'], report['exact_words'],
                          report['different_words'], report['neighbors']),
                         (373, 200, 216, 157, 22))
        self.assertEqual(report['raw_sha256'],
                         '2dbcf5d06e42583aeec00dd7a6ddb273a4888f04e5555c0d5fd1605678331280')
        self.assertEqual(report['installed'], installed)
        self.assertEqual(payload(root / source.BUILD / 'retail.o', source.FUNCTION)[1],
                         payload(root / source.BUILD / 'selected.o', source.FUNCTION)[1])
        self.assertEqual(fingerprints,
                         {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                          for p in protected})


if __name__ == '__main__':
    unittest.main()
