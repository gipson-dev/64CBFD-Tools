"""Object screening preserves every word and rejects invented bindings."""
import struct
import unittest

from tools.experiments.alternative_source_draft_word_screen import emit_function


class AlternativeDraftWordScreenTests(unittest.TestCase):
    def test_raw_words_and_named_relocations_are_not_normalized(self):
        text = struct.pack('>3I', 0x3C080000, 0x25080000, 0x03E00008)
        info = dict(value=0, size=len(text))
        reloc = {0: [('R_MIPS_HI16', 'D_80001234')], 4: [('R_MIPS_LO16', 'D_80001234')]}
        output, unresolved = emit_function(text, info, reloc, 'func_15000000', {'D_80001234': 0x80001234})
        self.assertFalse(unresolved)
        self.assertEqual(output.count('.word '), 3)
        self.assertIn('.word 0x3C080000', output)
        self.assertIn('.reloc ., R_MIPS_LO16, D_80001234', output)

    def test_unknown_pool_and_local_text_are_rejected(self):
        output, unresolved = emit_function(struct.pack('>2I', 0x08000010, 0x3C010000),
            dict(value=0, size=8), {0: [('R_MIPS_26', '.text')], 4: [('R_MIPS_HI16', '.rodata')]},
            'func_15000000', {'.text': 0, '.rodata': 0})
        self.assertEqual(unresolved, ['.rodata', '.text'])
        self.assertIn('.word 0x08000010', output)


if __name__ == '__main__':
    unittest.main()
