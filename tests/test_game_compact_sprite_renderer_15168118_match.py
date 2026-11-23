"""Seven bounded complete-source, caller, role, native and strict-image gates."""
import unittest
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
from tools.tests import game_compact_sprite_renderer_15168118_qualification_guest as guest
from tools.tests import game_compact_sprite_renderer_15168118_native as native
from tools.tests import game_compact_sprite_renderer_15168118_callers as callers
from tools.tests import game_compact_sprite_renderer_15168118_indirect_parent as parent
from tools.tests import game_compact_sprite_renderer_15168118_faults as faults
from tools.tests import game_compact_sprite_renderer_15168118_boundaries as boundaries
from tools.tests import game_compact_sprite_renderer_15168118_origin_trace as origins
class CompactSpriteRenderer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owners_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['changed_bytes'],1111);self.assertEqual(self.report['metadata_symbol_records'],7)
 def test_02_independent_guest_and_rebases(self):
  q=guest.main();self.assertEqual(q['guest_rebase_runs'],36);self.assertTrue(all(v['cases']==2970 for v in q['streams'].values()))
 def test_03_native_SDK32_aliases_and_source_controls(self):
  q=native.main();self.assertEqual(len(q['effective_source_controls']),17);self.assertTrue(all(v['cases']==1890 for v in q['profiles'].values()));self.assertTrue(q['all_17_used_record_offsets_and_packet_camera_layouts_asserted'])
 def test_04_complete_direct_caller(self):
  q=callers.main();self.assertTrue(q['positive_caller_all_21_words_direct_from_C']);self.assertTrue(all(v['cases']==448 and v['renderer_invocations']==112 for v in q['streams'].values()))
 def test_05_complete_registered_indirect_parent(self):
  q=parent.main();self.assertEqual(q['cases_per_stream'],116);self.assertEqual(q['actual_descriptor_columns'],[5,66]);self.assertEqual(len(q['effective_controls']),3)
 def test_06_normalized_fault_prefixes_and_raw_public_boundaries(self):
  q=faults.main();self.assertEqual(q['normalized_full_access_prefix_pairs'],323);self.assertEqual(q['raw_padded_retail_public_provider_boundary_triples'],37)
 def test_07_source_origins_both_padders_and_controls(self):
  q=origins.main();self.assertEqual(q['cases'],2970);self.assertFalse(q['different_origins']);self.assertEqual(q['private_dead_load_instances'],2790)
  q=boundaries.main();self.assertEqual(q['GNU_links'],12);self.assertEqual(q['effective_guard_rejections'],6);self.assertEqual(q['effective_output_comparisons'],2)
if __name__=='__main__':unittest.main(verbosity=2)
