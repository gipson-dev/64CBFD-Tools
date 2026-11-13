"""Retail actor extent callback: owner, guest, caller, native and relocation checks."""
import unittest
import itertools
from tools.experiments import game_extent_15149a94_match as packet
from tools.tests import game_extent_15149a94_oracle as oracle
from tools.tests import game_extent_15149a94_connected as connected
from tools.tests import game_extent_15149a94_native as native
from tools.tests import game_extent_15149a94_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class ExtentCallbackMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.prepared=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_dispatch_window(self):connected.run()
 def test_native_negative_controls(self):native.run()
 def test_relocations(self):rebase.run()
 def test_stack_alias_and_access_prefixes(self):
  programs=[oracle.bound_blob(*oracle.payload(self.prepared[x],oracle.NAME),oracle.SYMS) for x in ('retail','after','generated','generic')]
  def state(m):return (m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
  for delta,flags,timer in itertools.product(range(-0x180,0x21,16),(0,10),(4,5)):
   case=oracle.Case(flags,timer,3.,6.,0.5,0);initial=oracle.fixture(case);actor=oracle.STACK+delta
   for i in range(0x160):initial[actor+i]=initial[oracle.ACTOR+i]
   results=[]
   for p in programs:
    machine=oracle.Machine(p,case,initial.copy());machine.r[4]=actor
    try:machine.run();outcome='ok'
    except (AssertionError,KeyError) as e:outcome=(type(e).__name__,str(e))
    results.append((outcome,state(machine)))
   self.assertTrue(all(r==results[0] for r in results),(delta,flags,timer))
  for flags,timer in itertools.product((0,2,8,10),(4,5)):
   case=oracle.Case(flags,timer,3.,6.,0.5,0);initial=oracle.fixture(case)
   complete=oracle.Machine(programs[0],case,initial.copy()).run()
   for cut in range(complete.all_accesses):
    states=[]
    for p in programs:
     machine=oracle.Machine(p,case,initial.copy());machine.cut=cut
     with self.assertRaises(AccessBoundary):machine.run()
     states.append(state(machine))
    self.assertTrue(all(s==states[0] for s in states),(flags,timer,cut))
if __name__=='__main__':unittest.main(verbosity=2)
