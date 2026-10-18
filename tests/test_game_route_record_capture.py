"""Qualify the recovered S7 call lifetime while retaining the next rejection."""
import json
from unittest.mock import patch
import unittest

from tools.experiments import game_route_record_capture as source
from tools.tests import test_game_route_record_setup as previous


class CaptureOracle(previous.FullTraceOracle):
    def __init__(self, *args, **kwargs):
        self.captures = []
        self.post_reload_roles = []
        super().__init__(*args, **kwargs)

    def record_call(self, target):
        if target == previous.SELECTOR and sum(c[0] == target for c in self.calls) == 1:
            parent_sp = self.before[29] - 96
            self.captures.append((self.r[23], previous.read(self.memory, parent_sp + 0x48, 1),
                                  previous.read(self.memory, parent_sp + 0x49, 1)))
        elif target == previous.INITIALIZE:
            self.post_reload_roles.append((self.r[23], self.r[30]))
        super().record_call(target)


class RouteRecordCaptureTests(previous.RouteRecordSetupTests):
    @classmethod
    def setUpClass(cls):
        with patch.object(previous, 'source', source):
            super().setUpClass()

    def run(self, result=None):
        with patch.object(previous, 'source', source):
            return super().run(result)

    def test_03_fired_private_prefix_boundary_still_rejects_matching(self):
        super().test_03_fired_private_prefix_boundary_still_rejects_matching()
        receipt = json.loads((self.out / 'private-boundary.json').read_text())
        self.assertGreater(receipt['first']['cut'], 43)
        self.assertGreater(receipt['equal_memory_prefixes'], 140)
        memory, args, allocation = previous.fixture()
        results = []
        for words in (self.words, self.truth):
            m = CaptureOracle(words, memory, args, self.helpers, allocation)
            m.access_fault = 43
            with self.assertRaises(previous.base.base.faults.AccessBoundary):
                m.run()
            results.append(m)
        self.assertEqual((results[0].memory, results[0].complete_trace),
                         (results[1].memory, results[1].complete_trace))
        receipt.update(previous_first_cut_43_closed=True, previous_equal_memory_prefixes=140,
                       installation_permitted=False)
        (self.out / 'private-boundary.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def test_07_actual_S7_capture_private_seed_lifetime_and_effective_old_control(self):
        self.assertEqual(self.words[61:70], self.truth[61:70])
        count = 0
        for index, parameters in enumerate(previous.corpus()):
            memory, args, allocation = previous.fixture(*parameters)
            _, calls, _ = previous.reference(memory, args, allocation)
            selectors = [c for c in calls if c[0] == previous.SELECTOR]
            if len(selectors) < 2:
                continue
            first = previous.neighbor.reference(memory, selectors[0][1], previous.ROUTE_TABLE)[0] & 255
            observations = []
            for body in (self.words, self.truth):
                m = CaptureOracle(body, memory, args, self.helpers, allocation, (index & 1) * 8).run()
                parent_sp = m.before[29] - 96
                expected = [(first, previous.read(memory, parent_sp + 0x48, 1),
                             previous.read(memory, parent_sp + 0x49, 1))]
                self.assertEqual(m.captures, expected, parameters)
                observations.append(m.captures)
            self.assertEqual(*observations)
            count += 1
        obj, old, row = source.source.measure(self.root, self.out, 'previous-recovery', source.source.selected())
        source.source.checked(obj)
        self.assertEqual((row['words'], row['frame'], row['differences']), (160, 96, 43))
        memory, args, allocation = previous.fixture()
        old_machine = CaptureOracle(old, memory, args, self.helpers, allocation).run()
        new_machine = CaptureOracle(self.words, memory, args, self.helpers, allocation).run()
        self.assertNotEqual(old_machine.captures, new_machine.captures)
        self.assertNotEqual(old[61:70], self.truth[61:70])
        self.receipt('capture', cases=count, actual_S7_and_unwritten_seeds_before_second_call=True,
                     nine_literal_retail_words_equal=True, previous_recovery_effectively_rejected=True,
                     complete_later_saved_roles_and_private_order_not_claimed=True)

    def test_08_four_node_later_role_witness_remains_rejected(self):
        memory, args, allocation = previous.fixture(length=4)
        machines = [CaptureOracle(words, memory, args, self.helpers, allocation).run()
                    for words in (self.words, self.truth)]
        self.assertEqual(machines[0].captures, machines[1].captures)
        self.assertEqual(machines[0].post_reload_roles, [(3, 2)] * 3)
        self.assertEqual(machines[1].post_reload_roles, [(2, 3)] * 3)
        self.assertEqual((machines[0].memory, machines[0].trace, machines[0].calls),
                         (machines[1].memory, machines[1].trace, machines[1].calls))
        self.receipt('later-roles', raw_S7_FP=machines[0].post_reload_roles,
                     retail_S7_FP=machines[1].post_reload_roles,
                     initial_S7_capture_equal=True, later_roles_equal=False,
                     ordinary_memory_and_public_accesses_and_calls_equal=True,
                     installation_permitted=False)


if __name__ == '__main__':
    unittest.main()
