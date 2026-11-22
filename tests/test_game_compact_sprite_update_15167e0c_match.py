"""Six bounded source, ABI, caller, role, padder and complete-image gates."""
import unittest
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
from tools.tests import game_compact_sprite_update_15167e0c_guest as guest
from tools.tests import game_compact_sprite_update_15167e0c_native as native
from tools.tests import game_compact_sprite_update_15167e0c_callers as callers
from tools.tests import game_compact_sprite_update_15167e0c_faults as faults
from tools.tests import game_compact_sprite_update_15167e0c_boundaries as boundaries
from tools.tests import game_compact_sprite_update_15167e0c_roles as roles
class CompactSpriteUpdater(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owner_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['changed_bytes'],553)
 def test_02_independent_guest_and_rebases(self):
  r=guest.main();self.assertEqual(r['guest_rebase_runs'],36);self.assertTrue(all(v['cases']==3477 and v['unexecuted']==[122,128,158,164,175]for v in r['streams'].values()))
 def test_03_native_SDK32_aliases_and_source_controls(self):
  r=native.main();self.assertEqual(len(r['effective_source_controls']),24);self.assertTrue(all(v['cases']==2710 for v in r['profiles'].values()));self.assertTrue(r['all_19_field_offsets_asserted'])
 def test_04_complete_registered_dispatcher(self):
  r=callers.main();self.assertEqual(r['cases_per_stream'],324);self.assertEqual(r['registration_columns'],[5,59,66])
 def test_05_normalized_fault_prefixes_and_raw_public_stores(self):
  r=faults.main();self.assertEqual(r['normalized_full_access_prefix_pairs'],229);self.assertEqual(r['raw_padded_retail_public_store_boundary_triples'],48)
 def test_06_symbolic_roles_both_padders_and_controls(self):
  self.assertTrue(roles.main()['symbolic_motion_stores_and_low32_products_equal']);r=boundaries.main();self.assertEqual(r['GNU_links'],12);self.assertEqual(r['effective_guard_rejections'],6);self.assertEqual(r['effective_output_comparisons'],2)
if __name__=='__main__':unittest.main(verbosity=2)
