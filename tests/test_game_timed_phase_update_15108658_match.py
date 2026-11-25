import unittest
from tools.experiments import game_timed_phase_update_15108658_match as packet,game_timed_phase_update_15108658_make as make,game_timed_phase_update_15108658_image as image
from tools.tests import game_timed_phase_update_15108658_guest as guest,game_timed_phase_update_15108658_symbolic as symbolic,game_timed_phase_update_15108658_callers as callers,game_timed_phase_update_15108658_native as native,game_timed_phase_update_15108658_boundaries as boundaries
class TimedPhaseUpdateTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(105,46,2));self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['access_fault_quads'],140)
 def test_03_guards_and_GNU(self):
  q=boundaries.main();self.assertEqual((q['guarded_word_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['raw_binding_positions_pinned'],q['GNU_links']),(92,118,9,20))
 def test_04_observer_proof_and_bounded_caller(self):
  self.assertEqual(symbolic.main()['predicate_assignments'],1024);self.assertEqual(callers.main()['actual_parent_words_executed'],23)
 def test_05_native_ABI_and_controls(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
