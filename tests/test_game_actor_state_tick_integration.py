"""Actual actor-tick source, guard, padding, Make and strict image contracts."""

import csv
import hashlib
import io
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_integration as integration
from tools.tests import test_game_actor_state_tick_lifetimes as native


ROOT = Path(__file__).resolve().parents[2]


class ActorStateTickIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / integration.BUILD
        cls.values = integration.snapshot(cls.root, cls.output)
        cls.installed = hashlib.sha256((cls.root / integration.SOURCE).read_bytes()).hexdigest() != integration.core.INPUTS[integration.SOURCE]
        cls.native_count = 0
        if cls.installed:
            integration.audit(cls.root, cls.output)

    @classmethod
    def tearDownClass(cls):
        row = dict(installed=cls.installed, native_fixtures=cls.native_count,
                   strict_closed_metadata_groups=2, target_words=678)
        (cls.output / ('installed-tests.json' if cls.installed else 'preinstall-tests.json')).write_text(
            json.dumps(row, indent=2) + '\n')

    def test_owner_guard_payload_and_history_are_exact(self):
        raw, bindings = integration.core.payload(self.output / 'after-primary.o')
        normalized, moved = integration.layout.normalize(raw, bindings)
        before = self.values['conker/retail_word_patches.us.csv']
        guards = integration.guard_bytes(self.values, self.output)
        self.assertTrue(guards.startswith(before))
        self.assertEqual((self.output / 'qualified-guards.csv').read_bytes(), guards)
        rows = [r for r in csv.DictReader(io.StringIO(guards.decode()))
                if r['filename'] == integration.OWNER and r['function'] == integration.FUNCTION]
        self.assertEqual(len(rows), 344)
        self.assertTrue(all(r['omit'] == 'false' and not r['insert_after'] for r in rows))
        self.assertEqual(len(normalized), 2712)
        self.assertEqual(sum(map(len, moved.values())), 62)
        with self.assertRaises(ValueError):
            integration.layout.private_guards(guards, raw, bindings)
        wrong = bytearray(raw)
        wrong[0] ^= 1
        with self.assertRaises(ValueError):
            integration.layout.private_guards(before, bytes(wrong), bindings)

    def test_padded_neighbors_addresses_and_expanded_Make_recipe(self):
        before, after = self.output / 'before-padded.o', self.output / 'qualified-padded.o'
        self.assertEqual(integration.same_functions(before, after, (integration.FUNCTION,)), 72)
        a, fa = integration.core.link_owner(self.root, self.output, before, integration.OWNER)
        b, fb = integration.core.link_owner(self.root, self.output, after, integration.OWNER)
        self.assertEqual(fa[integration.FUNCTION]['size'], 12)
        self.assertEqual(fb[integration.FUNCTION]['size'], 2712)
        self.assertEqual({name: f['value'] for name, f in fa.items()},
                         {name: f['value'] for name, f in fb.items()})
        at = fb[integration.FUNCTION]['value']
        self.assertEqual(a[:at], b[:at])
        self.assertEqual(a[at + 2712:], b[at + 2712:])
        self.assertEqual(b[at:at + 2712], self.values['conker/conker.us.bin'][integration.ROM:integration.ROM + 2712])
        make = json.loads((self.output / 'make-shadow.json').read_text())
        self.assertEqual((make['actual_expanded_Make_commands'], make['profile_flags']), (7, [1, 0]))
        self.assertTrue(make['padded_code_and_metadata_equal'])
        self.assertEqual((self.root / 'conker/Makefile').read_bytes(), self.values['conker/Makefile'])

    def test_first_image_and_all_scope_metadata_negatives_are_strict(self):
        before = self.values['conker/build/conker.us.elf']
        truth = self.values['conker/conker.us.bin'][integration.ROM:integration.ROM + 2712]
        actual = (self.output / 'first-linked.elf').read_bytes()
        integration.check_image(before, actual, truth)
        row = json.loads((self.output / 'first-link.json').read_text())
        self.assertEqual((row['changed_bytes'], row['target_code_bytes_changed'], row['metadata_bytes_changed']),
                         (2183, 2124, 59))
        at = integration.elf_slot_offset(before, integration.ENTRY, 2712)
        sizes = integration.symbol_size_offset(before)
        groups = [r for r in integration.symbol_rows(before) if r[1] in sum(integration.SYMBOL_ORDER, ())]
        for byte in (0, at - 1, at + 2712, at + 40, sizes, groups[0][0] + 4, groups[0][3]):
            wrong = bytearray(actual)
            wrong[byte] ^= 1
            with self.assertRaises(ValueError):
                integration.check_image(before, bytes(wrong), truth)
        with patch.object(integration, 'SYMBOL_ORDER', ()):
            with self.assertRaises(ValueError):
                integration.check_image(before, actual, truth)
        canonical = lambda data: sorted((name, fields[1:]) for _, name, fields, _ in integration.symbol_rows(data))
        sized = bytearray(before)
        struct.pack_into('>I', sized, sizes, 2712)
        self.assertEqual(canonical(sized), canonical(actual))

    def test_native32_extracted_actual_or_proposed_source_with_sanitizer(self):
        path = self.root / integration.SOURCE if self.installed else self.output / 'proposed-owner.c'
        text = path.read_text()
        lo, hi = integration.core.function_span(text, integration.FUNCTION)
        body = text[lo:hi]
        self.assertEqual(body, integration.layout.source.SELECTED.split('*/\n', 1)[1])
        with patch.object(native.source, 'SELECTED', body):
            native.ActorStateTickLifetimeTests.test_complete_native32_source_at_three_optimizations_with_ubsan(self)

    def test_live_source_manifest_and_predecessor_boundaries(self):
        if self.installed:
            row = integration.audit(self.root, self.output)
            self.assertTrue(row['exact_first_link_reproduced'])
            self.assertEqual(row['other_bodies_fixed'], row['functions'] - 1)
        else:
            for name, before in self.values.items():
                self.assertEqual((self.root / name).read_bytes(), before)
        self.assertEqual((self.output / 'proposed-owner.c').read_text(),
                         integration.recovered_owner(self.values[integration.SOURCE].decode()))


if __name__ == '__main__':
    unittest.main()
