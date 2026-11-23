"""Actor preset C, callback return chain, byte ABI and strict full-image gates."""
import unittest
from tools.experiments import game_actor_preset_constructor_15196438_match as p
class ActorPresetConstructor(unittest.TestCase):
 @classmethod
 def setUpClass(cls):p.inspect_source()
 def test_01_symbolic_regions_and_byte_ABI(self):
  from tools.tests.game_actor_preset_constructor_15196438_symbolic import proof
  proof()
 def test_02_guards_and_GNU_rebases(self):
  from tools.experiments.game_actor_preset_constructor_15196438_qualification import main
  main()
 def test_03_guest_callers_and_faults(self):
  from tools.tests import game_actor_preset_constructor_15196438_guest as g
  g.main();g.aliases();g.callers();g.faults();g.connected_sound();g.connected_audio_chain()
 def test_04_native_SDK32(self):
  from tools.tests.game_actor_preset_constructor_15196438_native import main
  main()
 def test_05_actual_Make_and_complete_image(self):p.qualify()
if __name__=='__main__':unittest.main()
