"""Route-search guard history, actual Make/padding and strict image gates."""

import csv
import hashlib
import io
import json
from pathlib import Path
import unittest

from tools.experiments import game_route_node_search_integration as source


ROOT = Path(__file__).resolve().parents[2]


class RouteNodeSearchIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD
        cls.values = source.snapshot(cls.output)
        cls.installed = hashlib.sha256((ROOT / source.SOURCE).read_bytes()).hexdigest() != source.core.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)

    def test_all_guard_words_and_old_manifest_bytes_are_preserved(self):
        before = self.values['conker/retail_word_patches.us.csv']
        guards = source.guard_bytes(before, *source.core.payload(self.output / 'after-normal.o'))
        self.assertTrue(guards.startswith(before))
        self.assertEqual(guards, (self.output / 'qualified-guards.csv').read_bytes())
        rows = [r for r in csv.DictReader(io.StringIO(guards.decode()))
                if r['filename'] == source.OWNER and r['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 535)
        self.assertEqual(sum(bool(r['insert_after']) for r in rows), 4)
        self.assertTrue(all(r['omit'] == 'false' for r in rows))
        raw, bindings = source.core.payload(self.output / 'after-normal.o')
        with self.assertRaises(ValueError):
            source.guard_bytes(guards, raw, bindings)
        for i in range(535):
            bad = bytearray(raw)
            bad[i * 4 + 3] ^= 1
            with self.assertRaises(ValueError):
                source.guard_bytes(before, bytes(bad), bindings)

    def test_actual_Make_padded_neighbors_and_function_profile(self):
        before, after = self.output / 'before-padded.o', self.output / 'qualified-padded.o'
        self.assertEqual(source.same_functions(before, after, (source.FUNCTION,)), 72)
        a, fa = source.core.link_owner(self.root, self.output, before, source.OWNER)
        b, fb = source.core.link_owner(self.root, self.output, after, source.OWNER)
        self.assertEqual((fa[source.FUNCTION]['size'], fb[source.FUNCTION]['size']), (12, 2156))
        self.assertEqual({n: f['value'] for n, f in fa.items()}, {n: f['value'] for n, f in fb.items()})
        at = fb[source.FUNCTION]['value']
        self.assertEqual(a[:at], b[:at])
        self.assertEqual(a[at + 2156:], b[at + 2156:])
        self.assertEqual(b[at:at + 2156], self.values['conker/conker.us.bin'][source.ROM:source.ROM + 2156])
        report = json.loads((self.output / 'make-shadow.json').read_text())
        self.assertEqual((report['actual_expanded_Make_commands'], report['profile_flags']), (7, [1, 0]))
        self.assertTrue(report['padded_code_and_metadata_equal'])
        old = self.values['conker/Makefile'].decode()
        wanted = source.recovered_makefile(old)
        self.assertEqual(wanted.replace(' --function-object func_15086364=$@.normal.compact', ''), old)
        self.assertEqual((self.output / 'proposed-Makefile').read_text(), wanted)
        with self.assertRaises(ValueError):
            source.emit_padded_assembly(self.output / 'after-primary.o', self.root / 'conker/asm/B3020.s',
                function_objects={name: self.output / 'after-normal.o' for name in
                    ('func_150891E8', 'func_1508BC20', 'func_15089BC0')},
                word_patches_path=self.output / 'qualified-guards.csv', filename=source.OWNER)

    def test_strict_first_image_and_effective_scope_negatives(self):
        before = self.values['conker/build/conker.us.elf']
        truth = self.values['conker/conker.us.bin'][source.ROM:source.ROM + 2156]
        expected = source.predicted_image(before, truth)
        actual = (self.output / 'first-linked.elf').read_bytes()
        source.check_image(before, actual, truth)
        at = source.elf_slot_offset(before, source.ENTRY, source.SIZE)
        size = source.symbol_size_offset(before)
        for offset in (0, at - 1, at, at + 2155, at + 2156, size):
            wrong = bytearray(actual)
            wrong[offset] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(wrong), truth)
        self.assertEqual(json.loads((self.output / 'first-link.json').read_text())['changed_bytes'], 1632)

    def test_current_installed_or_predecessor_source_and_input_boundaries(self):
        proposed = source.core.recovered_owner(self.values[source.SOURCE].decode(), source.layout.SELECTED)
        self.assertEqual((self.output / 'proposed-owner.c').read_text(), proposed)
        if self.installed:
            report = source.audit(self.root, self.output)
            self.assertTrue(report['exact_first_link_reproduced'])
            self.assertEqual(report['other_bodies_fixed'], report['functions'] - 1)
        else:
            for name, old in self.values.items():
                self.assertEqual((self.root / name).read_bytes(), old, name)


if __name__ == '__main__':
    unittest.main()
