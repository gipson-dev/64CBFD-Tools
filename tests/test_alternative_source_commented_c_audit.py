"""Comment discovery requires a complete body and cannot alter real C."""
import unittest

from tools.experiments.alternative_source_commented_c_audit import adjacent_asm_function, commented_definitions, expand
from tools.experiments.alternative_source_c_inventory import definitions


class CommentedCAuditTests(unittest.TestCase):
    def test_line_comments_blank_lines_nested_braces_and_pointer_returns(self):
        text = '''const char *literal = "// void fake(void) { }";
// void * *func_15000000(int x) {
//     if (x) { return 0; }

//     return 0;
// }
int real(void) { return 3; } // void func_15000010(void) { }
'''
        rows = commented_definitions(text)
        self.assertEqual([row['function'] for row in rows], ['func_15000000'])
        self.assertTrue(rows[0]['complete_body'])
        self.assertIn('if (x) { return 0; }', rows[0]['body'])

    def test_block_documentation_and_dereference_operators(self):
        text = '''/*
 * void func_15000000(int *p) {
 *     *p = 3;
 * }
 */
/* void func_15000010(int *p) {
    *p = 4;
} */
'''
        rows = commented_definitions(text)
        self.assertEqual([row['function'] for row in rows], ['func_15000000', 'func_15000010'])
        self.assertIn('*p = 3;', rows[0]['body'])
        self.assertIn('*p = 4;', rows[1]['body'])

    def test_incomplete_body_does_not_discard_complete_sibling(self):
        rows = commented_definitions('// void func_15000000(void) { return; }\n// void func_15000010(void) {\n')
        self.assertEqual([row['complete_body'] for row in rows], [True, False])
        self.assertIsNone(rows[1]['body'])

    def test_explanatory_prose_is_not_a_function_definition(self):
        text = '''// The code itself (especially a later block) {
//     needs more work.
// }
// u32 random_u32(void) { return 3; }
// CustomType named_helper(void) { return 0; }
'''
        self.assertEqual([row['function'] for row in commented_definitions(text)], ['random_u32'])
        self.assertEqual([row['function'] for row in commented_definitions(text, {'named_helper'})],
            ['random_u32', 'named_helper'])

    def test_prose_parentheses_cannot_swallow_the_following_real_header(self):
        text = '''// copy data forward to storage (when selected != 0) or
// re-read it, and clear the output.
// s32 func_151F4F38(void *arg0, s32 arg1, s32 arg2) {
//     return 1;
// }
'''
        self.assertEqual([row['function'] for row in commented_definitions(text)], ['func_151F4F38'])

    def test_prose_apostrophes_cannot_hide_a_real_commented_body(self):
        text = "// target's expected code follows\n// s32 func_15000000(void) { return 1; }\n// caller's code follows\n"
        self.assertEqual([row['function'] for row in commented_definitions(text)], ['func_15000000'])

    def test_adjacent_assembly_claim_is_explicit_not_a_guessed_name(self):
        text = '#pragma GLOBAL_ASM("asm/example/func_150ADA20.s")\n// RNG draft\n// s32 random_u32(void) { return 1; }\n'
        self.assertEqual(adjacent_asm_function(text, 3), 'func_150ADA20')
        self.assertIsNone(adjacent_asm_function('int real(void) { return 1; }\n// draft\n', 2))

    def test_expansion_removes_only_selected_stub_and_private_prototype(self):
        text = '''#include "original.h"
int func_15000000(void);
int preserved(void) { return 3; }
int func_15000000(void) { return 0; }
#pragma GLOBAL_ASM("asm/function.s")
// void func_15000000(void) { call(); }
'''
        row = commented_definitions(text)[0]
        result = expand(text, row)
        self.assertEqual([row['function'] for row in definitions(result)], ['preserved', 'func_15000000'])
        self.assertIn('int preserved(void) { return 3; }', result)
        self.assertIn('#include "original.h"', result)
        self.assertNotIn('int func_15000000(void);', result)
        self.assertNotIn('#pragma GLOBAL_ASM', result)
        self.assertIn('void func_15000000(void) { call(); }', result)


if __name__ == '__main__':
    unittest.main()
