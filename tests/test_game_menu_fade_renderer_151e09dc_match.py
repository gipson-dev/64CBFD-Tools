"""Five fresh direct fade, ABI-only stub and literal complete-image gates."""
import unittest
from tools.experiments import game_menu_fade_renderer_151e09dc_match as p
from tools.experiments import game_menu_fade_renderer_151e09dc_qualification as q
from tools.tests import game_menu_fade_renderer_151e09dc_guest as g
from tools.tests import game_menu_fade_renderer_151e09dc_native as n
class MenuFadeRenderer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  v=self.report;self.assertTrue(v['strict_predicted_ELF_equal']);self.assertEqual(v['changed_bytes'],486);self.assertEqual(v['exclusions'],0);self.assertTrue(v['protected_data_audit']['exact']);self.assertEqual(v['protected_data_audit']['bytes'],189088);self.assertEqual(v['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(v['all_58_reference_neighbors_fixed']);self.assertTrue(v['all_helper_jump_table_anchors_retained']);self.assertEqual(v['ABI_only_helper_matching_credit'],0)
 def test_02_complete_guest_and_independent_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],303);self.assertEqual(v['unexecuted_original_words'],[]);self.assertTrue(v['direct_complete_identity']);self.assertTrue(v['independent_public_semantics_equal']);self.assertTrue(v['signed_wrap_and_full_value_vs_byte']);self.assertTrue(v['live_provider_mutations']);self.assertTrue(v['post_draw_alias_reread']);self.assertTrue(v['effective_stale_halfword_instruction_control']);self.assertFalse(v['void_result_compared'])
 def test_03_fault_prefixes_caller_and_changed_ABI_stub(self):
  v=g.faults();self.assertEqual(v['four_stream_full_state_and_dispatched_access_prefixes'],97);self.assertFalse(v['portable_C_fault_claim']);v=g.callers();self.assertEqual((v['original_bounded_caller_words'],v['cases_per_stream']),(4,4));self.assertTrue(v['enclosing_RA_restored']);self.assertFalse(v['complete_dispatcher_claim']);v=g.abi_stub();self.assertEqual((v['cases'],v['old_words'],v['new_words']),(4,3,7));self.assertTrue(v['only_first_four_o32_homes_written']);self.assertTrue(v['SP_RA_saved_registers_and_fifth_argument_preserved']);self.assertTrue(v['zero_result_preserved']);self.assertFalse(v['retail_helper_implementation_claim']);self.assertEqual(v['helper_matching_credit'],0)
 def test_04_native_SDK32_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==300 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['single_intentional_variadic_word']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),16);self.assertTrue(all(x['comparison_exit']in range(10,19)for x in v['effective_source_controls']));self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(v['format_address_codec_verified'])
 def test_05_direct_corruption_visibility_and_GNU_relocations(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['effective_wrong_word_or_binding_controls'],268);self.assertEqual((v['source_words_covered'],v['source_binding_sites_covered']),(101,33));self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertTrue(v['raw_is_exact_retail_words_and_bindings'])
if __name__=='__main__':unittest.main(verbosity=2)
