"""Audit bookkeeping filters, padding boundary and effective content controls."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import alternative_source_byte_match_audit as source


class AlternativeSourceByteMatchAuditTests(unittest.TestCase):
    def test_metadata_and_data_do_not_receive_function_credit(self):
        for name in ('D_160036F0', 'func_16000590.NON_MATCHING', '.L10002A98', 'L80001234'):
            self.assertFalse(source.code_name(name), name)
        for name in ('func_1501905C', 'osGetTime', '__osSetHWIntrRoutine'):
            self.assertTrue(source.code_name(name), name)

    def test_full_slot_and_omitted_padding_are_distinguished(self):
        words = [0x24020001, 0x03E00008, 0]
        exact = source.compare(words, words, {}, {})
        self.assertTrue(exact['strict_full_slot'])
        self.assertEqual(exact['classification'], 'exact')
        padded = source.compare(words, words + [0, 0], {}, {})
        self.assertFalse(padded['strict_full_slot'])
        self.assertTrue(padded['content_exact'])
        self.assertEqual(padded['omitted_alignment_nops'], 2)
        bad = source.compare(words, words + [1], {}, {})
        self.assertEqual(bad['classification'], 'diff')

    def test_real_instruction_and_address_only_differences_are_distinguished(self):
        words = [0x24020001, 0x03E00008, 0]
        bad = source.compare([0x24020002, *words[1:]], words, {}, {})
        self.assertEqual(bad['classification'], 'diff')
        self.assertFalse(bad['content_exact'])
        relocated = source.compare([0x0C008000, 0], [0x0C008001, 0], {}, {})
        self.assertEqual(relocated['classification'], 'blocked')
        self.assertFalse(relocated['content_exact'])

    def test_fresh_diagnostic_and_single_instruction_negative_control(self):
        root = Path(__file__).resolve().parents[2]
        reference = root / 'conker'
        candidate = reference / 'build/alternative-source-byte-audit-20261014/snapshot/conker'
        if not (candidate / 'build/conker.us.elf').exists():
            self.skipTest('Disposable diagnostic snapshot unavailable')
        baseline = source.audit(reference, candidate)
        self.assertFalse(baseline['unanchored_C_rows'])
        self.assertTrue(baseline['not_a_runnable_or_normally_linked_build'])
        self.assertTrue(baseline['this_audit_is_read_only'])
        self.assertEqual(baseline['candidate']['total']['functions'], 1478)
        self.assertEqual(baseline['candidate']['total']['strict_full_slot'], 1478)
        load = source.matcher.load_elf_functions

        def changed(path, objdump):
            words, symbols, addresses = load(path, objdump)
            if Path(path) == candidate / 'build/conker.us.elf':
                words['func_1505DFDC'][0] ^= 1
            return words, symbols, addresses

        with patch.object(source.matcher, 'load_elf_functions', changed):
            negative = source.audit(reference, candidate)
        self.assertEqual(negative['candidate']['total']['exact'], 1477)
        self.assertEqual(negative['candidate']['total']['diff'], 1)
        self.assertEqual(negative['main_guarded'], baseline['main_guarded'])


if __name__ == '__main__':
    unittest.main()
