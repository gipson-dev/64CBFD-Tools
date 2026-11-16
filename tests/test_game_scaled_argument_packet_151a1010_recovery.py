"""Focused frame, semantic C, independent proof and exact object gates."""
import unittest
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
from tools.tests import game_scaled_argument_packet_151a1010_oracle as g
from tools.tests import game_scaled_argument_packet_151a1010_native as n
from tools.tests import game_scaled_argument_packet_151a1010_proof as p
from tools.tests import game_scaled_argument_packet_151a1010_frame_proof as f
from tools.experiments import game_scaled_argument_packet_151a1010_match as match
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
class ScaledPacketRecovery(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check()
 def test_01_complete_guest_packet(self):g.main()
 def test_02_ordered_transfer(self):
  p.main();f.main()
  raw,refs=payload(m.OUT.parent/'candidate.o',m.NAME)
  self.assertEqual(__import__('hashlib').sha256(raw).hexdigest(),m.PIN['raw_sha256']['original-frame'])
  words=bound_blob(raw,refs,{'D_800A8D28':m.CONST,'func_151A11CC':m.CALLEE})
  with self.assertRaisesRegex(AssertionError,'ordered transfer mismatch'):p.prove(words,m.retail())
 def test_03_defined_native32(self):n.main()
 def test_04_static_reference_scope(self):
  self.assertFalse(any(m.caller_census().values()));self.assertEqual(m.check_inputs(),887)
 def test_05_exact_object_and_rebases(self):match.main()
if __name__=='__main__':unittest.main()
