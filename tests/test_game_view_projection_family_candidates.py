"""Standalone type/sequence and byte-preserving structured guard-edit controls."""
import csv
import hashlib
import io
import unittest
from unittest.mock import patch

from tools.experiments import game_view_projection_family as family
from tools.tests import game_view_projection_family_native as native


class ViewProjectionFamilyCandidateTests(unittest.TestCase):
    def test_actual_sequences_types_and_native_case_roots(self):
        self.assertEqual(set(family.PATHS), set(family.BASELINE))
        self.assertEqual(len(family.PATHS), 17)
        self.assertEqual(family.PARENT_BODY.count('    focalExtent = sinf(halfAngle);'), 2)
        self.assertIn('void func_1510B5F8(', family.SELECTED_CHILD)
        self.assertNotIn('return 0;', family.SELECTED_CHILD)
        self.assertEqual(family.SELECTED_CHILD.count('guPerspectiveF('), 1)
        self.assertEqual(family.SELECTED_CHILD.count('guMtxF2L('), 1)
        records = native.vectors()
        self.assertEqual((len(records), {r['kind'] for r in records}), (216, {0, 1, 2}))

    def test_manifest_keeps_unrelated_CRLF_and_multiline_records_verbatim(self):
        fields = ['filename', 'function', 'offset', 'expected', 'replacement', 'expected_relocations',
            'replacement_relocations', 'note', 'insert_after', 'insert_after_relocations', 'omit']
        make = lambda owner, name, note: dict(zip(fields, [owner, name, '0x0', '0', '0', '-', '-', note, '', '', 'false']))
        wrapper = make(family.source.OWNER, 'func_1510B32C', 'obsolete')
        kept = [make('other', 'func_1510B32C', 'Keep, commas\nand lines'), make('other', 'retained', 'fixed')]
        old = io.StringIO(newline='')
        writer = csv.DictWriter(old, fieldnames=fields, lineterminator='\r\n')
        writer.writeheader()
        writer.writerow(kept[0])
        for _ in range(8):
            writer.writerow(wrapper)
        writer.writerow(kept[1])
        before = old.getvalue().encode()
        reference = io.StringIO(newline='')
        writer = csv.DictWriter(reference, fieldnames=fields, lineterminator='\r\n')
        writer.writeheader()
        writer.writerows(kept)
        with patch.dict(family.BASELINE, guards=hashlib.sha256(before).hexdigest()):
            self.assertEqual(family.guard_manifest(before, []), reference.getvalue().encode())
            with self.assertRaisesRegex(ValueError, 'guard baseline'):
                family.guard_manifest(before + b'\n', [])


if __name__ == '__main__':
    unittest.main()
