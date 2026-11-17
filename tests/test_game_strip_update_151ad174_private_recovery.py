"""Private full callback behavior and explicit remaining matching boundaries."""
import hashlib,json,struct,unittest
from tools.experiments import game_strip_update_151ad174_private_recovery as m
from tools.tests import game_strip_update_151ad174_private_oracle as guest,game_strip_update_151ad174_private_native as native,game_strip_update_151ad174_private_caller as caller,game_strip_update_151ad174_private_observation as observation
class StripUpdatePrivateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check()
 def tearDown(self):self.assertEqual(m.check_inputs(),1506)
 def test_01_owner_abi_registration_and_constants(self):
  q=json.loads((m.OUT/'source-report.json').read_text());self.assertEqual((q['raw_words'],q['retail_words'],q['frame'],q['neighbors']),(487,494,776,32));self.assertTrue(q['pools_unchanged']);self.assertEqual(q['registered_secondary_categories'],[47,78]);self.assertEqual(q['c_match_credit'],0)
 def test_02_complete_guest_outputs_and_live_reload_contracts(self):
  guest.main();q=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(q['cases'],544);self.assertTrue(q['public_bytes_and_calls_equal'])
 def test_03_retail_threshold_witness_rejects_prior_movement_bug(self):
  truth=list(struct.unpack('>494I',(m.OUT/'retail.bin').read_bytes()));c=guest.Case(pattern=5,z_velocity=guest.bits(14.));self.assertEqual([t for t,a in guest.verify(truth,c).service.calls],[guest.RNG,guest.EMIT]);self.assertEqual(guest.verify(truth,guest.replace(c,count=19)).service.calls,[])
  bad=m.PIN['body'].replace('fabsf(velocity[2])','fabsf(force[2])');self.assertNotEqual(bad,m.PIN['body']);obj,diagnostics=m.compile_owner(m.ROOT,m.OUT,m.recover((m.FROZEN/m.SOURCE).read_text(),bad),'wrong-force-score');self.assertFalse(diagnostics)
  raw,refs=guest.payload(obj,m.NAME);self.assertEqual(hashlib.sha256(raw).hexdigest(),m.PIN['bad_force_sha256'])
  with self.assertRaises(AssertionError)as error:guest.verify(guest.bound_blob(raw,refs,guest.SYMS),c)
  self.assertIn(error.exception.args[0][0],('public','calls'))
  (m.OUT/'threshold-control.json').write_text(json.dumps(dict(original_count20_requests_sound=True,original_count19_quiet=True,wrong_force_score_rejected=True,c_match_credit=0),indent=2)+'\n')
 def test_04_native_profiles_and_effective_negatives(self):
  native.main();q=json.loads((m.OUT/'native/native-report.json').read_text());self.assertTrue(q['passes']);self.assertEqual((q['cases'],len(q['runs'])),(544,7))
 def test_05_complete_registered_list_caller(self):
  caller.main();q=json.loads((m.OUT/'caller-report.json').read_text());self.assertEqual(q['cases_per_stream'],64);self.assertTrue(q['one_pointer_void_ABI']);self.assertTrue(q['complete_public_RAM_and_calls_compared']);self.assertEqual(q['effective_controls'],['wrong callback pointer'])
 def test_06_private_and_ordered_trace_keeps_matching_uncredited(self):
  observation.main();q=json.loads((m.OUT/'private-observation.json').read_text());self.assertEqual(q[0]['return_different_words'],[-652,-644,-604,-600]);self.assertFalse(q[0]['ordered_FP_equal']);self.assertTrue(all(v['private_different_bytes']==0 for v in q[0]['boundaries'][:6]));self.assertEqual(q[1]['return_private_different_bytes'],0);self.assertTrue(q[1]['ordered_FP_equal'])
if __name__=='__main__':unittest.main()
