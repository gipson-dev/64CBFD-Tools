"""Six focused source, ABI, SDK32, guard and literal-image qualifications."""
import json,struct,unittest
from tools.experiments import game_render_list_parent_151674f8_match as packet
from tools.experiments import game_render_list_parent_151674f8_roles as roles
from tools.tests import game_render_list_parent_151674f8_native as native
from tools.tests import game_render_list_parent_151674f8_callers as callers
from tools.tests import game_render_list_parent_151674f8_qualification_guest as guest
from tools.tests import game_render_list_parent_151674f8_faults as faults
from tools.tests import game_render_list_parent_151674f8_boundaries as boundaries
from tools.experiments.game_paired_ground_constructor_match import payload
class RenderListParent(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owners_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertTrue(self.report['string_pool_completely_reconstructed']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['changed_bytes'],1204);self.assertTrue(self.report['caller_owner_byte_identical'])
 def test_02_closed_roles_both_padders_and_rebases(self):
  plan=json.loads((packet.TOOLROOT/'experiments/game_render_list_parent_151674f8_role_plan.json').read_text());raw,refs=payload(packet.OUT/'selected/candidate.o',packet.FUNCTION);words=list(struct.unpack('>348I',raw));source=[words[i]for i in plan['order']];truth=list(struct.unpack('>348I',payload(packet.OUT/'original-target.o',packet.FUNCTION)[0]))
  self.assertEqual(set(plan['order']),set(range(348)))
  for i in range(43,47):
   for j in range(i+1,47):
    a,b=roles.info(words[i]),roles.info(words[j]);wa,wb=a['write'],b['write'];self.assertFalse(wa and wa in(*b['reads'],wb));self.assertFalse(wb and wb in a['reads'])
  q=roles.prove(source,truth);self.assertEqual(q['register_operand_pairs'],497);self.assertEqual(q['unreachable_words'],[224])
  for pc,shift,reg in((192,21,3),(191,21,4),(193,16,0)):
   bad=source[:];bad[pc]=(bad[pc]&~(31<<shift))|reg<<shift
   with self.assertRaisesRegex(AssertionError,'Reaching definition mismatch'):roles.prove(bad,truth)
  q=boundaries.main();self.assertEqual(q['GNU_links'],12);self.assertEqual(q['effective_guard_rejections'],4);self.assertEqual(q['effective_output_comparisons'],2)
 def test_03_native_SDK32_recursive_and_source_controls(self):
  q=native.main();self.assertEqual(len(q['effective_source_controls']),20);self.assertEqual(q['recursive_parent_cases'],36);self.assertTrue(all(v['cases']==1352 for v in q['profiles'].values()));self.assertEqual(len(q['profiles']),3)
 def test_04_all_callers_and_actual_range_helper(self):
  q=callers.main();self.assertEqual(q['complete_caller_functions'],6);self.assertEqual(q['complete_caller_words'],622);self.assertEqual(q['cases_per_parent_stream'],203);self.assertTrue(q['all_14_actual_JAL_sites_executed']);self.assertEqual(q['complete_actual_range_helper_words'],47);self.assertFalse(q['range_helper_unexecuted']);self.assertEqual(len(q['effective_controls']),2)
 def test_05_all_complete_parent_leaf_combinations(self):
  q=guest.main();self.assertEqual(q['complete_parent_leaf_combinations'],9);self.assertEqual(q['cases_per_combination'],116);self.assertTrue(all(v==224 for v in q['leaf_invocations'].values()))
 def test_06_normalized_fault_prefixes_and_raw_public_boundaries(self):
  q=faults.main();self.assertEqual(q['normalized_full_access_prefix_pairs'],3425);self.assertEqual(q['raw_padded_retail_public_provider_boundary_triples'],37)
if __name__=='__main__':unittest.main(verbosity=2)
