"""ROM-free donor scope, original binding and scanner return-screen checks."""
import unittest

from tools.experiments import game_actor_mode_flags as source
from tools.experiments import game_texture_vertex_span_returns as returns


class ActorModeFlagCandidateTests(unittest.TestCase):
    def test_actor_source_and_makefile_change_only_the_owned_target(self):
        before='s32 func_1507DF10();\ns32 neighbor() { return 7; }\ns32 func_1507DF10() { return 0; }\n'
        actual=source.recover(before)
        self.assertIn('s32 neighbor() { return 7; }',actual)
        self.assertEqual(actual.count(source.BODY.rstrip()),1)
        self.assertNotIn('s32 func_1507DF10();',actual)
        self.assertIn('actor->unk94 |= 0x40;\n            actor->unk94 &= ~0x200;',source.BODY)
        line='$(BUILD_DIR)/$(SRC_DIR)/game_433F0.c.o: RETAIL_RODATA_SYMBOL := jtbl_800966C0_game\n'
        result=source.recovered_makefile('before\n'+line+'after\n')
        self.assertEqual(result.replace('$(BUILD_DIR)/$(SRC_DIR)/game_A9D90.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009B884_game\n',''),
            'before\n'+line+'after\n')
        with self.assertRaises(AssertionError):
            source.recovered_makefile(result)

    def test_return_groups_are_bounded_and_preserve_the_scanner(self):
        groups=(returns.scalar_variants,returns.local_variants,returns.exit_variants)
        self.assertEqual([len(list(group())) for group in groups],[11,13,8])
        names=[]
        for group in groups:
            for name,body in group():
                names.append(name)
                self.assertEqual(body.count('func_1510D0EC(resource, &extent, 3, 0)'),1)
                self.assertEqual(body.count('*(s8 *)commands'),3)
                self.assertNotIn('volatile',body)
        self.assertEqual(len(names),len(set(names)))
        with self.assertRaises(AssertionError):
            returns.finish('not the complete scanner','return 0;')


if __name__=='__main__':
    unittest.main()
