"""Standalone fitting invariants; actual instruction acceptance needs consumer tests."""
from collections import Counter
import unittest

from tools.experiments import game_view_projection_command_fitting as fitting
from tools.experiments import game_view_projection_command_matching as matching


class ViewProjectionCommandFittingCandidateTests(unittest.TestCase):
    def test_all_labelled_forms_and_selected_real_lifetimes(self):
        rows = list(fitting.variants())
        self.assertEqual(len(rows), 141)
        self.assertEqual(len({label for label, _ in rows}), 141)
        body = dict(rows)['copy-homes-1-0-2-6']
        self.assertEqual(body, matching.SELECTED)
        self.assertEqual((body.count('cosineX'), body.count('cosineY')), (3, 5))
        self.assertEqual((body.count('cosf('), body.count('sinf('), body.count('func_1510B5F8(')), (2, 2, 1))
        layouts = dict(fitting.layout_variants(body))
        for mode in range(6):
            self.assertEqual(''.join(layouts['layout-%d' % mode].split()), ''.join(body.split()))

    def test_schedule_relocations_only_move_the_two_known_high_halves(self):
        before, after = matching.RELOCATIONS, matching.OUTPUT_RELOCATIONS
        atoms = lambda rows: Counter(value for entries in rows.values() for value in entries)
        self.assertEqual(atoms(before), atoms(after))
        self.assertEqual(after[132], before[84])
        self.assertEqual(after[308], before[284])
        self.assertNotIn(84, after)
        self.assertNotIn(284, after)
        self.assertEqual({k: v for k, v in before.items() if k not in (84, 284)},
            {k: v for k, v in after.items() if k not in (132, 308)})
        with self.assertRaisesRegex(ValueError, 'complete view-command words'):
            matching.recipe([0] * 129)


if __name__ == '__main__':
    unittest.main()
