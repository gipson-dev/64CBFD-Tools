import json,unittest
from tools.experiments import game_actor_colored_dispatch_match as p
from tools.tests import game_actor_colored_dispatch_mixed as mixed, game_actor_colored_dispatch_guest as guest, game_actor_colored_dispatch_native as native, game_actor_colored_dispatch_window as window, game_actor_colored_dispatch_window2 as window2, game_actor_colored_dispatch_boundaries as boundaries, game_actor_colored_dispatch_table_controls as table_controls
class ActorColoredDispatchTests(unittest.TestCase):
 report={}
 def test_01_mixed_padders(self):mixed.main()
 def test_02_actual_make_and_image(self):type(self).report=p.prepare()
 def test_03_guest(self):guest.main()
 def test_04_native(self):native.main()
 def test_05_caller_one(self):window.main()
 def test_06_caller_two(self):window2.main()
 def test_07_boundaries(self):boundaries.main()
 def test_08_table_controls(self):table_controls.main()
 def test_09_no_target_override_warning(self):
  result=json.loads((p.out/'actual-Make.json').read_text())
  warnings=[line for line in result['warnings'].splitlines() if 'generated_12DAB0.c.o' in line]
  self.assertEqual(warnings,[])
  commands='\n'.join(result['commands'])
  self.assertIn('-DCBFD_COLORED_PRIMARY',commands)
  self.assertIn('-Wo,-no_const_in_reg',commands)
  self.assertIn('--function-object func_151026BC=',commands)
