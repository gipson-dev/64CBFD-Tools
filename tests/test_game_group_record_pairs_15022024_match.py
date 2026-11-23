"""Focused source, normalization, semantic, ABI and full-image adoption gates."""
import unittest
from tools.experiments import game_group_record_pairs_15022024_match as p
class PairLookupMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):p.inspect_source()
 def test_01_guards_and_independent_rebases(self):
  from tools.experiments.game_group_record_pairs_15022024_qualification import main
  main()
 def test_02_guest_symbolic_reference_and_callers(self):
  from tools.tests import game_group_record_pairs_15022024_guest as g
  g.main();g.callers();g.faults()
 def test_03_native_sdk32(self):
  from tools.tests.game_group_record_pairs_15022024_native import main
  main()
 def test_04_actual_make_and_independent_complete_image(self):p.qualify()
if __name__=='__main__':unittest.main()
