"""Six focused direct-source, ABI, caller, padder and literal-image gates."""
import unittest
from tools.experiments import game_sprite_frame_update_15168870_match as packet
from tools.tests import game_sprite_frame_update_15168870_guest as guest
from tools.tests import game_sprite_frame_update_15168870_native as native
from tools.tests import game_sprite_frame_update_15168870_callers as callers
from tools.tests import game_sprite_frame_update_15168870_faults as faults
from tools.tests import game_sprite_frame_update_15168870_boundaries as boundaries
class SpriteFrameUpdater(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owner_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['changed_bytes'],359)
 def test_02_independent_guest_and_rebases(self):
  r=guest.main();self.assertEqual(r['guest_rebase_runs'],36);self.assertTrue(all(v['cases']==2658 for v in r['streams'].values()))
 def test_03_native_SDK32_aliases_and_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),15)
 def test_04_complete_registered_update_dispatcher(self):self.assertEqual(callers.main()['cases_per_stream'],2304)
 def test_05_full_access_prefix_state(self):self.assertEqual(faults.main()['access_fault_triples'],103)
 def test_06_both_padders_rebases_and_exact_comparison_controls(self):
  r=boundaries.main();self.assertEqual(r['GNU_links'],12);self.assertEqual(r['effective_comparison_controls'],4)
if __name__=='__main__':unittest.main(verbosity=2)
