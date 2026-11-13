import unittest
from tools.experiments import game_checksum_record_spawn_match as packet
from tools.tests import game_checksum_record_spawn_oracle as guest
from tools.tests import game_checksum_record_spawn_native as native
from tools.tests import game_checksum_record_spawn_connected as connected
from tools.tests import game_checksum_record_spawn_faults as faults
from tools.tests import game_checksum_record_spawn_rebase as rebase
class ChecksumRecordSpawnMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_ordinary(self):guest.run()
 def test_aliases(self):guest.aliases()
 def test_native(self):native.run()
 def test_factory_wrapper(self):connected.run()
 def test_access_cuts(self):faults.run()
 def test_rebases(self):rebase.run()
if __name__=='__main__':unittest.main()
