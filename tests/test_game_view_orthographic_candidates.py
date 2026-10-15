"""Standalone source recovery, signed-default aliases and SDK profile controls."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.experiments import game_view_orthographic_setup as source
from tools.tests import game_view_orthographic_oracle as model


class OrthographicSetupCandidateTests(unittest.TestCase):
    def test_recovery_preserves_other_functions_and_unused_argument(self):
        before = 'extern u8 *D_800BE628;\n\ns32 func_1510B070() { return 0; }\ns32 unchanged() { return 0; }\n'
        after = source.recover(before)
        self.assertIn('void func_1510B070(s32 unused)', after)
        self.assertIn('s32 unchanged() { return 0; }', after)
        self.assertEqual(after.count(source.DECLARATIONS), 1)
        self.assertNotIn('PROJECTION_VIEWS_138520[unused]', after)
        self.assertEqual(len(list(source.variants())), 20)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))

    def test_signed_field_aliases_and_fail_closed_sdk_profile(self):
        memory = model.fixture(-32768, 32767, view=2)
        expected, packet = model.packet_and_defaults(memory)
        self.assertEqual(model.read(expected, model.NEAR), model.bits(-32768))
        self.assertEqual(packet[2], model.bits(32767))
        self.assertEqual(packet[4], model.bits(-32768))
        with self.assertRaisesRegex(ValueError, 'plain SDK C'):
            source.compile_sdk(Path('.'), Path('.'), '#pragma GLOBAL_ASM("x")', 'conker/src/x.c', 'x')
        plan = SimpleNamespace(stdout='../ido/ido5.3_recomp/cc -c -O2 -o build/x.o src/x.c\n', stderr='')
        with patch.object(source.subprocess, 'run', return_value=plan):
            with self.assertRaisesRegex(ValueError, 'SDK compiler profile'):
                source.compile_sdk(Path('.'), Path('.'), 'void x(void) {}', 'conker/src/x.c', 'x')


if __name__ == '__main__':
    unittest.main()
