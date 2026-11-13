"""Script-query list callback: guest, caller, native and padding checks."""
import runpy,unittest
from tools.experiments import game_query_list_1509dbbc_match as packet
from tools.tests import game_query_list_1509dbbc_guards as guards

class QueryListMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.before,cls.after=packet.prepare()
 def test_guest(self):runpy.run_path(str(packet.OUT/'guest.py'))
 def test_connected_dispatcher(self):runpy.run_path(str(packet.OUT/'connected.py'))
 def test_faults_and_aliases(self):runpy.run_path(str(packet.OUT/'faults.py'))
 def test_native(self):runpy.run_path(str(packet.OUT/'native.py'))
 def test_relocations(self):runpy.run_path(str(packet.OUT/'rebase.py'))
 def test_guard_preimages(self):guards.run()
 def test_historical_reconstruction(self):
  self.assertEqual(packet.historical_source(self.after),self.before)
  guards_before=packet.historical_guards((packet.ROOT/'conker/retail_word_patches.us.csv').read_text())
  guards_after=packet.apply(guards_before,packet.MANIFEST['guard_changes'])
  self.assertEqual(packet.historical_guards(guards_after),guards_before)

if __name__=='__main__':unittest.main(verbosity=2)
