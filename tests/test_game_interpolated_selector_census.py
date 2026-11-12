"""Static selector extent and negative controls for the US linked image."""
import struct
import unittest
import os
from pathlib import Path

from tools.experiments import game_interpolated_selector_census as census


class SelectorCensusTests(unittest.TestCase):
    def test_pair_bounds_and_signed_counts(self):
        data = bytearray(census.ROWS * census.COLUMNS * census.PAIR_SIZE)
        struct.pack_into('>hh', data, 0, 2, 7)
        struct.pack_into('>hh', data, (127*8+7)*4, 5, -1)
        hits = census.scan_pairs(data)
        self.assertEqual([(x['row'], x['column'], x['index'], x['count'], x['declared'])
                          for x in hits], [(0, 0, 2, 7, True), (127, 7, 5, -1, False)])
        with self.assertRaises(ValueError):
            census.scan_pairs(data[:-1])

    def test_real_image_and_changed_retail_table(self):
        root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2]))
        elf = (root/'conker/build/conker.us.elf').read_bytes()
        rom = (root/'conker/conker.us.bin').read_bytes()
        result = census.census(elf, rom)
        self.assertEqual((result['selected_hits'], result['declared_hits'],
                          len(result['outside_hits']), len(result['zero_count_hits'])),
                         (34, 20, 14, 14))
        self.assertEqual({h['index'] for h in result['zero_count_hits']}, {2, 3, 5})
        altered = bytearray(rom)
        altered[census.TABLE_ROM] ^= 1
        with self.assertRaises(ValueError):
            census.census(elf, altered)


if __name__ == '__main__':
    unittest.main()
