"""Screen the paired constructors without claiming an unresolved C match."""
import struct,unittest
from tools.experiments import game_random_paired_constructor_screen as packet
from tools.tests import game_random_paired_constructor_oracle as guest
class RandomPairedConstructorScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_ordinary(self):self.assertEqual(guest.ordinary(self.state),{n:20 for n in self.state})
 def test_stack_overlap_boundary(self):
  self.assertEqual(guest.aliases(self.state),{n:{'equal':148,'different':78,'payload_differences':2} for n in self.state})
 def test_dispatch_and_factory_contract(self):
  rom=(packet.ROOT/'conker/conker.us.bin').read_bytes()
  word=lambda off:struct.unpack_from('>I',rom,off)[0]
  self.assertEqual((word(0x22e540),word(0x22e544)),(0x150c60d8,0x150c6a08))
  self.assertEqual((word(0x1619dc),word(0x1619e0)),(0x3c118009,0x26319a70))
  self.assertEqual((word(0x161a48),word(0x161aac)),(0xafb00018,0x0320f809))
  self.assertEqual((word(0x15d7bc),word(0x15d7c0)),(0x24060070,0x0c008bb0))
if __name__=='__main__':unittest.main()
