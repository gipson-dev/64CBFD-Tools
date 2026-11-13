"""Coordinate-table initializer: caller, guest, native and fault checks."""
import unittest
from tools.experiments import game_coordinate_table_1512abf8_match as packet
from tools.tests import game_coordinate_table_1512abf8_guest as guest
from tools.tests import game_coordinate_table_1512abf8_connected as connected
from tools.tests import game_coordinate_table_1512abf8_native as native
from tools.tests import game_coordinate_table_1512abf8_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class CoordinateTableMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.prepared=packet.prepare()
 def test_guest_model(self):guest.run()
 def test_caller_window(self):connected.run()
 def test_native_controls(self):native.run()
 def test_relocations(self):rebase.run()
 def test_access_prefixes_and_read_order(self):
  programs=guest.words();self.assertEqual(programs[0],programs[2]);self.assertEqual(programs[0],programs[3])
  for c in (guest.Case(-1,0,0),guest.Case(1,27,1),guest.Case(3,30,0)):
   initial=guest.fixture(c);original=guest.Machine(programs[0],c,initial.copy()).run();raw=guest.Machine(programs[1],c,initial.copy()).run()
   reads=lambda m:[row[1] for row in m.trace if row[0]=='R']
   self.assertEqual(reads(original)[:2],[guest.MODE,guest.PLAYERS]);self.assertEqual(reads(raw)[:2],[guest.PLAYERS,guest.MODE])
   cuts=set(range(min(8,original.all_accesses)))|set(range(0,original.all_accesses,32))|{original.all_accesses-1}
   for cut in cuts:
    states=[]
    for p in (programs[0],programs[2],programs[3]):
     m=guest.Machine(p,c,initial.copy());m.cut=cut
     with self.assertRaises(AccessBoundary):m.run()
     states.append((m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of))
    self.assertTrue(all(s==states[0] for s in states),(c,cut))
if __name__=='__main__':unittest.main(verbosity=2)
