"""Full finite-case FP ordering and prior symbolic/caller/native boundaries."""
from types import SimpleNamespace
from unittest.mock import patch
import json
import struct
import unittest
from tools.experiments import game_strip_update_151ad174_ordered as m
from tools.tests import game_strip_update_151ad174_private_oracle as guest
from tools.tests import game_strip_update_151ad174_private_native as native
from tools.tests import game_strip_update_151ad174_private_caller as caller
from tools.tests import game_strip_update_151ad174_lifetime_relation as relation
from tools.tests import game_strip_update_151ad174_ordered_trace as trace


class StripUpdateOrderedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = m.compile_and_check()
        raw, refs = guest.payload(m.OUT / 'owner.o', m.NAME)
        cls.raw = guest.bound_blob(raw, refs, guest.SYMS)
        cls.truth = list(struct.unpack('>494I', (m.OUT / 'retail.bin').read_bytes()))

    @classmethod
    def tearDownClass(cls):
        m.check_inputs()

    def test_01_complete_finite_public_and_ordered_FP(self):
        coverage = {'retail': set(), 'raw': set()}
        operations = 0
        private_words = set()
        count = 0
        for case in guest.cases():
            left, right = trace.compare(self.truth, self.raw, case)
            coverage['retail'].update(left.visits)
            coverage['raw'].update(right.visits)
            operations += len(left.fp)
            frame_top = left.r[29]
            self.assertEqual(frame_top, right.r[29])
            self.assertEqual(frame_top, guest.STACK + case.phase)
            private_words.update(offset & ~3 for offset in range(-776, 16)
                                 if left.memory[frame_top + offset] != right.memory[frame_top + offset])
            count += 1
        self.assertEqual(count, 544)
        report = dict(cases=count, words_visited={k: len(v) for k, v in coverage.items()},
                      ordered_FP_operations_compared=operations, ordered_FP_operands_equal=True,
                      coefficient_loads_equal=True, remaining_private_words=sorted(private_words),
                      private_frame_offsets=sorted(offset + 776 for offset in private_words),
                      both_incoming_stack_phases_checked=True,
                      public_bytes_and_calls_equal=True, full_preserved_registers=True,
                      source_installed=False, c_match_credit=0,
                      domain='Finite disjoint 544-case matrix with existing opaque providers. No FCSR, NaN, fault-state or whole-loop symbolic proof.')
        (m.OUT / 'guest-report.json').write_text(json.dumps(report, indent=2) + '\n')

    def test_02_symbolic_entry_and_inductive_snapshot(self):
        prefix = relation.prefix_controls(self.truth, self.raw)
        snapshot = relation.snapshot_controls(self.truth, self.raw)
        self.assertEqual((prefix['paths'], prefix['visited_words'], prefix['call_boundaries']), (18, 142, 30))
        self.assertTrue(snapshot['loop_live_relation_reestablished'])
        for name, report in [('prefix-relation.json', prefix), ('snapshot-relation.json', snapshot)]:
            (m.OUT / name).write_text(json.dumps(report, indent=2) + '\n')

    def test_03_native_three_profiles_and_four_effective_controls(self):
        adapter = SimpleNamespace(ROOT=m.ROOT, PACKET=m.PACKET, OUT=m.OUT,
                                  FROZEN=m.source.FROZEN, SOURCE=m.source.SOURCE,
                                  PIN=dict(m.source.PIN, body=m.PIN['body']), check_inputs=m.check_inputs)
        with patch.object(native, 'source', adapter):
            native.main()
        report = json.loads((m.OUT / 'native/native-report.json').read_text())
        self.assertTrue(report['passes'])
        self.assertEqual((report['cases'], len(report['runs'])), (544, 7))

    def test_04_complete_registered_caller(self):
        with patch.object(caller, 'p', m.OUT):
            caller.main()
        report = json.loads((m.OUT / 'caller-report.json').read_text())
        self.assertEqual(report['cases_per_stream'], 64)
        self.assertTrue(report['effective_controls'])

    def test_05_operand_swap_controls(self):
        report = trace.controls(self.truth, self.raw)
        self.assertEqual(len(report), 2)
        (m.OUT / 'ordered-controls.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
