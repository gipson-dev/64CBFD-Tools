"""Qualify direct C mode dispatch, retail table, helpers and caller window."""
import itertools
import unittest
from tools.experiments import game_owner_mode_1514ea1c_direct as packet
from tools.tests import game_owner_mode_1514ea1c_direct_oracle as g
from tools.tests import game_owner_mode_1514ea1c_direct_connected as connected
from tools.tests import game_owner_mode_1514ea1c_direct_native as native
from tools.tests import game_owner_mode_1514ea1c_direct_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def state(m):return (m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)

class OwnerModeDirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=packet.prepare();cls.streams=g.programs()
    def test_guest_model(self):g.run()
    def test_original_helpers(self):g.connected()
    def test_original_dispatch_window(self):connected.run()
    def test_stack_and_table_aliases(self):
        count=0
        for owner,mode,statebyte,mutation in itertools.product(
                (g.STACK-0x40,g.STACK-0x20,g.STACK,g.TABLE-0x20,g.TABLE,g.TABLE+0x20),
                (-1,0,3,4,6,9,12,13),(0,2,255),(0,1)):
            c=g.Case(owner=owner,mode=mode,state=statebyte,returned=0x87654321,mutation=mutation)
            initial=g.fixture(c);rows=[]
            for stream in self.streams:
                m=g.Machine(stream,c,initial.copy())
                try:m.run();outcome=('ok',)
                except (AssertionError,KeyError) as exc:outcome=(type(exc).__name__,str(exc))
                rows.append((outcome,state(m)))
            self.assertTrue(all(v==rows[0] for v in rows),(c,[r[0] for r in rows]));count+=1
        self.assertEqual(count,288)
    def test_access_boundaries(self):
        cuts=0
        for c in (g.Case(mode=0),g.Case(mode=3,state=2),g.Case(mode=6,state=1),g.Case(mode=9,state=2),g.Case(mode=12),g.Case(mode=13)):
            initial=g.fixture(c);full=g.Machine(self.streams[0],c,initial.copy()).run()
            for cut in range(full.all_accesses):
                rows=[]
                for stream in self.streams:
                    m=g.Machine(stream,c,initial.copy());m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    rows.append(state(m))
                self.assertTrue(all(x==rows[0] for x in rows),(c,cut));cuts+=1
        self.assertGreater(cuts,0)
    def test_native_controls(self):native.run()
    def test_rebased_link(self):rebase.run()

if __name__=='__main__':unittest.main(verbosity=2)
