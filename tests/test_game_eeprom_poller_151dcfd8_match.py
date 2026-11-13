"""EEPROM poller: modeled providers, both callers, native and fault tests."""
import unittest
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
from tools.tests import game_eeprom_poller_151dcfd8_guest as guest
from tools.tests import game_eeprom_poller_151dcfd8_connected as connected
from tools.tests import game_eeprom_poller_151dcfd8_connected_read as connected_read
from tools.tests import game_eeprom_poller_151dcfd8_native as native
from tools.tests import game_eeprom_poller_151dcfd8_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class EepromPollerMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.prepared=packet.prepare()
 def test_guest_model(self):guest.run()
 def test_request_caller(self):connected.run()
 def test_read_caller(self):connected_read.run()
 def test_native_controls(self):native.run()
 def test_relocations(self):rebase.run()
 def test_access_prefixes(self):
  programs=guest.words()
  for case in (guest.Case(0,0,0,0,1,0,0),guest.Case(1,-1,8,0,0,0xffffffff,0),guest.Case(1,0,8,0,1,0x100000000,3),guest.Case(1,0,9,-1,1,0xffffffffffffffff,2)):
   initial=guest.fixture(case);complete=guest.Machine(programs[0],case,initial.copy()).run()
   for cut in range(complete.all_accesses):
    states=[]
    for program in (programs[0],programs[2],programs[3]):
     machine=guest.Machine(program,case,initial.copy());machine.cut=cut
     with self.assertRaises(AccessBoundary):machine.run()
     states.append((machine.memory,machine.r,machine.f,machine.hi,machine.lo,machine.calls,machine.trace,machine.current_pc,machine.delay_of))
    self.assertTrue(all(state==states[0] for state in states),(case,cut))
if __name__=='__main__':unittest.main(verbosity=2)
