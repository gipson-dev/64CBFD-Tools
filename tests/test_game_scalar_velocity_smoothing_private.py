"""Reproduce private scalar semantics while proving no production files change."""
from pathlib import Path
import hashlib,json,os,unittest
from tools.experiments import game_scalar_velocity_smoothing_candidates as source
from tools.tests import game_scalar_velocity_smoothing_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ScalarVelocitySmoothingPrivateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD/('public-private-run-'+str(os.getpid()));cls.output.mkdir(parents=True,exist_ok=False)
  cls.names=(source.SOURCE,'conker/build/conker.us.elf','conker/build/src/game/generated_76A60.c.o','conker/retail_word_patches.us.csv','conker/progress.csv')
  cls.before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()for n in cls.names}
  cls.screen=source.prepare(ROOT,cls.output);cls.semantic=oracle.qualify(ROOT,cls.output)
 def test_normal_profile_owner_and_actual_nonmatch(self):
  self.assertEqual((self.screen['candidate_words'],self.screen['candidate_frame'],self.screen['real_word_differences']),(55,16,38));self.assertEqual((self.screen['retail_words'],self.screen['retail_frame'],self.screen['owner_neighbors']),(54,24,1));self.assertEqual(self.screen['matching_credit'],0);self.assertFalse(self.screen['installed'])
 def test_finite_guest_native_aliases_and_negative_controls(self):
  self.assertEqual((self.semantic['finite_guest_cases'],self.semantic['retail_reachable_words']),(1072,52));self.assertGreater(self.semantic['snap_cases'],0);self.assertGreater(self.semantic['accepted_cases'],0)
  for row in self.semantic['native']:self.assertEqual(row['cases'],536);self.assertTrue(row['UBSan']);self.assertEqual(len(row['negative_controls']),8);self.assertTrue(row['all_controls_effective'])
 def test_production_inputs_unchanged(self):
  self.assertEqual(self.before,{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()for n in self.names})
