"""Full strip-update source, object, symbolic, execution and caller gates."""
import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.experiments import game_strip_update_151ad174_recovery as m,game_strip_update_151ad174_match as matching
from tools.tests import game_strip_update_151ad174_proof as proof,game_strip_update_151ad174_guest as guest,game_strip_update_151ad174_caller as caller,game_strip_update_151ad174_private_native as native
class StripUpdateMatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_01_both_padders_rebases_and_guard_controls(self):
  row=json.loads((m.OUT/'object-report.json').read_text());self.assertEqual((row['body_words'],row['retail_words'],row['frame'],row['guard_words'],row['insertions'],row['omissions']),(491,494,776,273,3,0));self.assertEqual((row['raw_and_binding_corruptions'],row['stale_CSV_controls'],row['replacement_and_insertion_controls'],row['gnu_links']),(514,1092,279,12));self.assertTrue(row['retired_stub_guard'])
 def test_02_complete_composed_normalization_relation(self):proof.main()
 def test_03_guest_complete_normalized_RAM_and_raw_semantics(self):guest.main()
 def test_04_native_profiles_and_four_effective_controls(self):
  adapter=SimpleNamespace(ROOT=m.ROOT,PACKET=m.ADOPTION.parent,OUT=m.OUT,FROZEN=m.FROZEN,SOURCE=m.SOURCE,PIN=m.PIN,check_inputs=m.check_inputs)
  with patch.object(native,'source',adapter):native.main()
  row=json.loads((m.OUT/'native/native-report.json').read_text());self.assertTrue(row['passes']);self.assertEqual((row['cases'],len(row['runs'])),(544,7))
 def test_05_complete_registered_caller_all_streams(self):
  caller.main();row=json.loads((m.OUT/'caller-report.json').read_text());self.assertEqual(row['cases_per_stream'],64);self.assertTrue(row['complete_normalized_RAM_and_private_stack_compared']);self.assertTrue(row['effective_controls'])
if __name__=='__main__':unittest.main()
