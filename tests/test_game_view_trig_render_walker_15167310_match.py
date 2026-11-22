"""Six focused source, ABI, callback, guard and complete-image gates."""
import unittest
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
from tools.tests import game_view_trig_render_walker_15167310_guest as guest
from tools.tests import game_view_trig_render_walker_15167310_native as native
from tools.tests import game_view_trig_render_walker_15167310_callers as callers
from tools.tests import game_view_trig_render_walker_15167310_faults as faults
from tools.tests import game_view_trig_render_walker_15167310_boundaries as boundaries
from tools.tests import game_view_trig_render_walker_15167310_roles as roles
class ViewTrigRenderWalker(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_header_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['changed_bytes'],442);self.assertEqual(self.report['header_consumers'],305)
 def test_02_guest_live_views_and_callbacks(self):
  r=guest.main();self.assertEqual(r['guest_rebase_runs'],36);self.assertTrue(all(v['cases']==1376 and not v['unexecuted']for v in r['streams'].values()))
 def test_03_native_SDK32_and_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),13)
 def test_04_actual_direct_caller_window(self):self.assertEqual(callers.main()['cases'],12)
 def test_05_raw_public_and_normalized_full_fault_prefixes(self):self.assertEqual(faults.main()['access_fault_triples'],1714)
 def test_06_derived_roles_padders_and_carry_controls(self):
  self.assertTrue(roles.main()['derived_words_equal']);r=boundaries.main();self.assertEqual(r['GNU_links'],12);self.assertEqual(r['effective_malformed_controls'],8)
if __name__=='__main__':unittest.main(verbosity=2)
