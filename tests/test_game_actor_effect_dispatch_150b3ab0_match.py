"""Qualify the direct-C actor-effect dispatcher and original caller window."""
import os
import struct
import subprocess
import sys
import unittest
from tools.experiments import game_actor_effect_dispatch_150b3ab0_match as source

class ActorEffectDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.installed = source.prepare()

    def check_module(self, name, markers):
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(source.ROOT), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-m', 'tools.tests.game_actor_effect_dispatch_150b3ab0_' + name],
                                cwd=source.ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, (name, result.stdout, result.stderr))
        for marker in markers:
            self.assertIn(marker, result.stdout)

    def test_guest(self):
        self.check_module('guest', ['"cases_per_stream": 72', '"slot_home_mutation": true', '"packet_and_position_padding": true'])

    def test_native(self):
        self.check_module('native', ['"cases_per_configuration": 36', '"alias_modes": 2', '"ubsan": true'])

    def test_caller(self):
        self.check_module('caller', ['"cases_per_stream": 24', '"caller": "func_1506FC9C"', '"bounded_window": true'])

    def test_faults(self):
        self.check_module('fault', ['"fault_prefixes": 71', '"retail_equals_c": true'])

    def test_padders_and_rebases(self):
        self.check_module('padders', ['"padders": 2', '"gnu_links": 12'])

    def test_actual_make_and_image(self):
        self.check_module('image', ['"strict_exclusions": 0', '"caller_functions_unchanged": 328'])

    def test_input_line_endings(self):
        self.assertEqual(source.input_digest('conker/Makefile', b'a\r\nb\n'), source.input_digest('conker/Makefile', b'a\nb\n'))
        self.assertNotEqual(source.input_digest('conker/conker.us.bin', b'a\r\n'), source.input_digest('conker/conker.us.bin', b'a\n'))

    def test_direct_call_census(self):
        rom = (source.ROOT / 'conker/conker.us.bin').read_bytes()
        jal = struct.pack('>I', 0x0d42ceac)
        pointer = struct.pack('>I', 0x150b3ab0)
        self.assertEqual([i for i in range(0x2d4b0, 0x22d710, 4) if rom[i:i+4] == jal], [0x9d160])
        self.assertEqual([i for i in range(0, len(rom) - 3, 4) if rom[i:i+4] == pointer], [])

if __name__ == '__main__':
    unittest.main()
