"""Standalone finite rounding and exact ownership-row controls."""
import unittest

from tools.experiments import game_fixed_matrix_restoration as source
from tools.tests import game_fixed_matrix_oracle as model


class FixedMatrixRoundingTests(unittest.TestCase):
    def test_signed_halfway_modes_and_bounded_domain(self):
        expected = ((2, -2), (1, -1), (2, -1), (1, -2))
        for mode, values in enumerate(expected):
            self.assertEqual(tuple(model.integer(model.bits(x), mode) for x in (1.5, -1.5)), tuple(x & 0xFFFFFFFF for x in values))
        self.assertEqual(model.integer(model.bits(2.5), 0), 2)
        self.assertEqual(model.integer(model.bits(-2.5), 0), 0xFFFFFFFE)
        for value in (float('nan'), float('inf'), 2147483648.0):
            with self.assertRaises(AssertionError):
                model.integer(model.bits(value), 0)

    def test_progress_changes_only_the_unique_owner_row(self):
        row = b'us,game,guMtxF2L,guMtxF2L,353007504,464,c'
        before = b'unchanged,quoted\r\n' + row + b'\r\nother\n'
        self.assertEqual(source.expected_progress(before), b'unchanged,quoted\r\n' + row[:-1] + b'asm\r\nother\n')
        for bad in (b'', row + row):
            with self.assertRaises(ValueError):
                source.expected_progress(bad)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))


if __name__ == '__main__':
    unittest.main()
