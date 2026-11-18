"""Complete callback recovery through source, callers, padders and linked image."""
import unittest
from tools.experiments import game_menu_radial_150b879c_match as s
from tools.tests import game_menu_radial_150b879c_oracle as guest
from tools.tests import game_menu_radial_150b879c_native as native
from tools.tests import game_menu_radial_150b879c_callers as callers
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

def state():
 lookup={v[1]:v[2][1]for v in symbol_rows((s.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 return dict(raw_words=bound_blob(*payload(s.OUT/'owner.o',s.NAME),lookup),retail_words=bound_blob(*payload(s.OUT/'original.o',s.NAME),lookup),rom=(s.FROZEN/'conker/conker.us.bin').read_bytes())

class MenuRadialMatch(unittest.TestCase):
 def test_01_complete_source_relation(self):self.assertEqual(s.qualify_source()['raw_words'],142)
 def test_02_padders_guards_and_rebases(self):
  self.assertEqual(s.padders()['gnu_links'],12);self.assertEqual(s.guard_controls(),336)
 def test_03_guest_descriptor_and_capture(self):self.assertEqual(guest.run(state())['cases'],3072)
 def test_04_native_optimization_and_controls(self):
  report=native.run()
  for result in report['profiles'].values():self.assertEqual((result['cases'],result['negative_controls']),(8192,17))
 def test_05_complete_retail_dispatcher(self):
  result=callers.run(state());self.assertEqual((result['cases'],result['table_index']),(195,25))
 def test_06_connected_factory_and_memcpy(self):
  result=callers.factory(state());self.assertEqual(result['words'],{'func_15130374':18,'func_15130280':41,'memcpy':11})
 def test_07_actual_Make_and_whole_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
