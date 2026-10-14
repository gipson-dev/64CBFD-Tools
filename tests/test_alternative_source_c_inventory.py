"""Lexical discovery must not grant compilation or matching credit."""
from pathlib import Path
import tempfile
import unittest

from tools.experiments.alternative_source_c_inventory import definitions, inventory


class AlternativeSourceCInventoryTests(unittest.TestCase):
    def test_comments_strings_prototypes_and_balanced_bodies(self):
        source = '''// s32 func_15000000(void) { return 0; }
/* void fake(void) { } */
s32 prototype(void);
void real(void) { const char *text = "} void fake2(void) {"; if (text) { call(); } }
void *pointer(s32 arg) { return (void *)arg; }
'''
        self.assertEqual([row['function'] for row in definitions(source)], ['real', 'pointer'])
        self.assertFalse(any(row['trivial_body'] for row in definitions(source)))

    def test_conditional_regions_do_not_leak_past_endif(self):
        rows = definitions('#if 0\nvoid draft(void) { }\n#endif\nvoid active(void) { return; }\n')
        self.assertEqual([row['conditional_region'] for row in rows], [True, False])
        self.assertTrue(all(row['trivial_body'] for row in rows))

    def test_uncompiled_and_trivial_definitions_are_discovery_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference, snapshot = root / 'reference', root / 'snapshot'
            reference.mkdir()
            (snapshot / 'src').mkdir(parents=True)
            (reference / 'progress.csv').write_text('version,section,filename,function,offset,length,language\n'
                'us,game,target,func_15000000,1,12,c\n')
            for project in (reference, snapshot):
                (project / 'symbol_addrs.us.txt').write_text('')
            (snapshot / 'src/draft.c').write_text('s32 func_15000000(void) { return 0; }\n')
            result = inventory(reference, snapshot)
            self.assertEqual((result['source_files'], result['uncompiled_source_files'], result['trivial_definitions']), (1, 1, 1))
            self.assertEqual(result['function_definitions'][0]['canonical_address'], 0x15000000)
            self.assertTrue(result['lexical_inventory_is_not_a_compile_or_matching_result'])


if __name__ == '__main__':
    unittest.main()
