"""ROM-free selected-view source scope and variable-shift domain checks."""
import unittest

from tools.experiments import game_view_pass_dispatch as source
from tools.tests import game_view_pass_dispatch_oracle as model


class ViewPassDispatchCandidateTests(unittest.TestCase):
    def test_source_uses_one_typed_cursor_and_existing_profile(self):
        self.assertIn('Gfx *func_15019464(Gfx *commands, s16 view)',source.SELECTED)
        self.assertNotIn('temp_s0',source.SELECTED)
        self.assertIn('((u32)view * 0x180)',source.SELECTED)
        self.assertIn('(1U << view)',source.SELECTED)
        self.assertNotIn('volatile',source.SELECTED)
        self.assertEqual(len(list(source.index_variants())),6)
        self.assertEqual(len(list(source.shift_variants())),2)
        before='s32 func_15019464(Gfx *p,s16 v){return 0;}\ns32 neighbor(){return 9;}\n'
        after=source.recover(before)
        self.assertEqual(after.count(source.SELECTED.rstrip()),1)
        self.assertIn('s32 neighbor(){return 9;}',after)

    def test_native_domain_preserves_guest_only_shift_boundaries(self):
        rows=[(view,flags,pattern) for view in model.VIEWS for flags in range(16) for pattern in range(5)]
        native=model.native_rows(rows)
        self.assertLess(len(native),len(rows))
        self.assertIn((0xFFFFFFFF,4,0),native)
        self.assertNotIn((0xFFFFFFFF,0,0),native)
        self.assertIn((31,0,0),native)
        self.assertIn((0x80008000,0,1),native)


if __name__=='__main__':
    unittest.main()
