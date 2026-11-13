"""Direct C camera callback: model, caller, aliases, faults and links."""
import itertools
import unittest

from tools.experiments import game_camera_state_15125924_direct as packet
from tools.tests import game_camera_state_15125924_direct_oracle as g
from tools.tests import game_camera_state_15125924_direct_connected as connected
from tools.tests import game_camera_state_15125924_direct_native as native
from tools.tests import game_camera_state_15125924_direct_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary


def state(machine):
    return (machine.memory, machine.r, machine.f, machine.hi, machine.lo,
            machine.condition, machine.trace, machine.calls, machine.current_pc, machine.delay_of)


class CameraStateDirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = packet.prepare()
        cls.programs = [g.words(cls.state[key]) for key in ('retail', 'after', 'padded')]
        assert cls.programs[0] == cls.programs[1] == cls.programs[2]

    def test_independent_guest_model(self):
        g.run()

    def test_original_caller_windows(self):
        connected.run()

    def test_camera_stack_aliases(self):
        cases = failures = 0
        for delta, present, status, value, first in itertools.product(
                range(-0x800, 0x31, 16), (0, 1), (0, 1), (0., 1.25), (0, 1)):
            case = g.Case(present=present, status=status, value=value, first=first)
            actor = g.STACK+delta
            initial = g.fixture(case)
            for i in range(0x800):
                initial[actor+i] = (i*29+0x35)&255
            for offset, value in ((0x3d4, g.STATE if present else 0), (0x3d0, g.ACTOR),
                                  (0x2c, 0), (0x84, 0x4000), (0x6c8, 0), (0x5f0, 0x1000),
                                  (0x2fc, g.bits(5.5)), (0x354, g.bits(2.25))):
                g.put(initial, actor+offset, value)
            observations = []
            for words in self.programs:
                machine = g.Machine(words, case, initial.copy())
                machine.r[4] = actor
                try:
                    machine.run()
                    outcome = ('ok',)
                except (AssertionError, KeyError) as exc:
                    outcome = (type(exc).__name__, str(exc))
                observations.append((outcome, state(machine)))
            self.assertTrue(all(value == observations[0] for value in observations), (delta, case))
            failures += observations[0][0] != ('ok',)
            cases += 1
        self.assertEqual(cases, 2112)
        self.assertEqual(failures, 32)

    def test_access_boundary_prefixes(self):
        cases = (g.Case(), g.Case(flags=0x40), g.Case(value=1.25, flags=0x80),
                 g.Case(first=1, second=1, mutate=1), g.Case(present=0, first=0))
        cuts = 0
        for case in cases:
            initial = g.fixture(case)
            complete = g.Machine(self.programs[0], case, initial.copy()).run()
            for cut in range(complete.all_accesses):
                observations = []
                for words in self.programs:
                    machine = g.Machine(words, case, initial.copy())
                    machine.cut = cut
                    with self.assertRaises(AccessBoundary):
                        machine.run()
                    observations.append(state(machine))
                self.assertTrue(all(value == observations[0] for value in observations), (case, cut))
                cuts += 1
        self.assertGreater(cuts, 0)

    def test_native_and_negative_controls(self):
        native.run()

    def test_rebased_links(self):
        rebase.run()


if __name__ == '__main__':
    unittest.main(verbosity=2)
