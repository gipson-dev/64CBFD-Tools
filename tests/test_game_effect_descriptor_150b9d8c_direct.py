"""Check the direct C descriptor against retail, including frame overlaps."""
import itertools
import unittest

from tools.experiments import game_effect_descriptor_150b9d8c_direct as packet
from tools.tests import game_effect_descriptor_150b9d8c_oracle as guest
from tools.tests import game_effect_descriptor_150b9d8c_connected as connected
from tools.tests import game_effect_descriptor_150b9d8c_direct_native as native
from tools.tests import game_effect_descriptor_150b9d8c_direct_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary


class EffectDescriptorDirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = packet.prepare()
        cls.compat = dict(cls.state, four=cls.state['after'])

    def test_ordinary_and_original_random_generator(self):
        result = guest.ordinary(self.compat)
        self.assertEqual(result['cases'], 72)
        result = connected.actual_rng(self.compat)
        self.assertEqual(result['visited_rng_words'], result['rng_words'])

    def test_stack_overlaps_and_exception_state(self):
        programs = guest.programs(self.compat)
        self.assertTrue(all(p == programs[0] for p in programs))
        count = 0
        for delta, phase, selector, mutation in itertools.product(range(-0x120, 0x41, 4), (0, 8), (-1, 0), (0, 1)):
            case = guest.Case(guest.STACK + phase + delta, phase, selector,
                              (0x76543210, 0x12345678, 0x80000001), mutation)
            initial = guest.fixture(case)
            observed = []
            for program in programs:
                machine = guest.Machine(program, case, initial.copy())
                machine.r[16] = machine.before[16] = 0xffff0000
                try:
                    machine.run()
                    outcome = ('ok',)
                except Exception as exc:
                    outcome = ('error', type(exc).__name__, str(exc))
                observed.append((outcome, machine.calls, machine.packets, machine.memory, machine.r))
            self.assertTrue(all(v == observed[0] for v in observed), case)
            count += 1
        self.assertEqual(count, 712)

    def test_native_behavior_and_controls(self):
        native.run()

    def test_access_boundary_prefixes(self):
        programs = guest.programs(self.compat)
        cases = (guest.Case(), guest.Case(selector=0),
                 guest.Case(actor=guest.STACK-0xd0),
                 guest.Case(actor=guest.STACK-0xd8, mutation=1))
        cuts = 0
        for case in cases:
            initial = guest.fixture(case)
            complete = guest.Machine(programs[0], case, initial.copy()).run()
            for cut in range(complete.all_accesses):
                observations = []
                for program in programs:
                    machine = guest.Machine(program, case, initial.copy())
                    machine.cut = cut
                    with self.assertRaises(AccessBoundary):
                        machine.run()
                    observations.append((machine.memory, machine.r, machine.f, machine.hi,
                                         machine.lo, machine.condition, machine.trace, machine.calls))
                self.assertTrue(all(v == observations[0] for v in observations), (case, cut))
                cuts += 1
        self.assertGreater(cuts, 0)

    def test_relocated_link(self):
        rebase.run()

    def test_reference_census(self):
        result = connected.caller_census()
        self.assertFalse(any(result['aligned_code_image_hits'].values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
