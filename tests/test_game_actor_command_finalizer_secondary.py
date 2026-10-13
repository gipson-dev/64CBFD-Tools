"""Qualify recovered secondary value and physical register lifetimes."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_secondary as screen
from tools.tests import test_game_actor_command_finalizer_opening as previous
from tools.tests import test_game_actor_command_finalizer_recovery as recovery


class GameActorCommandFinalizerSecondaryTests(previous.GameActorCommandFinalizerOpeningTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-command-finalizer-secondary-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=recovery.screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile',
            caller='conker/src/game/generated_61490.c', rodata='conker/asm/data/23C630.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '76c0c333b9c1de6e9c9cbd3865dc84ea2742692f1b4add3ef6f3a52ef43da27f'
        assert cls.baseline['elf'] == '9c75bf09dcf23dcfb2266396a565a8ca6196a4d41be59eff9ca1c6d3ae58a52b'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.meta, cls.words = screen.fitting.compile_candidate(cls.root, cls.out, 'selected', screen.SELECTED)
        _, cls.banked_words = screen.fitting.compile_candidate(cls.root, cls.out, 'banked', screen.BASE)
        _, cls.old_words = screen.fitting.compile_candidate(cls.root, cls.out, 'old-slot-control', previous.roles.roles.BASE)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), 0x61D10))

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (405, 72, 266, 0, ''))
        self.assertEqual(self.words[:14], self.retail[:14])
        self.assertEqual(self.words[-4:], self.retail[-4:])
        self.assertEqual(self.words[81:83], self.retail[81:83])
        # The secondary block is still four bytes early; roles are literal, not an address match.
        for source_index, retail_index in ((236, 237), (250, 251), (266, 267), (267, 268), (301, 302)):
            self.assertEqual(self.words[source_index], self.retail[retail_index])
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function'] == recovery.screen.FUNCTION])
        observed = screen.previous.fault_probes(self.words, self.retail)
        self.assertEqual([r['equal'] for r in observed[:5]], [True, True, False, True, True])
        self.receipt('shape', words=405, frame=72, differences=266, matching_credit=0,
            register_roles=dict(sign=6, choose=4, reverse=7, secondary_value=2), observations=observed)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        body = screen.SELECTED
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(body), profile)[0], 0)
        negatives = {
            'narrow-first': body.replace('if (first != limit)', 'if ((u8)first != limit)'),
            'unsigned-jitter': body.replace('actor[0x1FE] * *(s8 *)(actor + 0x202)', 'actor[0x1FE] * actor[0x202]'),
            'wrong-suppression': body.replace('value == 0x70', 'value == 0x71'),
            'wrong-sign': body.replace('sign = -1;', 'sign = 1;'),
            'signed-modulo': body.replace('(u32)func_150ADA20() %', 'func_150ADA20() %'),
            'secondary-low-byte': screen.replace_once(body,
                'value = *(s16 *)(actor + 0x204);\n                if (sign > 0)',
                'value = actor[0x204];\n                if (sign > 0)')}
        for name, negative in negatives.items():
            self.assertNotEqual(negative, body, name)
            self.assertNotEqual(self.run_native(name, self.native_source(negative))[0], 0, name)
        self.receipt('native', cases=8192, profiles=['O2', 'O0'], effective_negatives=len(negatives))

    def test_06_owned_frame_and_temporary_records(self):
        with patch.multiple(previous.opening, BASE=screen.BASE, SELECTED=screen.SELECTED):
            super().test_06_owned_frame_and_temporary_records()

    def test_09_independent_original_links_and_carry_rebases(self):
        with patch.object(previous.opening, 'SELECTED', screen.SELECTED):
            super().test_09_independent_original_links_and_carry_rebases()

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        old, new = [screen.previous.previous.fault_sweep(words, self.retail)
            for words in (self.banked_words, self.words)]
        self.assertEqual((len(old['cases']), old['fired_pairs'], old['equal_states']), (52, 2938, 1086))
        self.assertEqual((len(new['cases']), new['fired_pairs'], new['equal_states']), (52, 2938, 1322))
        self.assertEqual(new['first_cuts'], {10: 44, 7: 8})
        for before, after in zip(old['cases'], new['cases']):
            self.assertEqual(before['accesses'], after['accesses'])
            self.assertTrue(set(before['equal_cuts']).issubset(after['equal_cuts']))
        self.receipt('fault-boundary', **new, banked_equal_states=1086,
            no_previously_exact_sampled_states_lost=True, whole_private_fault_match=False,
            hardware_PC_BD_FCSR_not_claimed=True)

    def test_14_sign_defaults_and_equivalent_surface_forms_are_not_matching_progress(self):
        forms = {}
        for name, body in screen.candidates():
            meta, words = screen.fitting.compile_candidate(self.root, self.out, 'screen-' + name, body)
            forms[name] = (meta, words)
        self.assertEqual(len(forms), 19)
        self.assertEqual(forms['ternary'][1], self.banked_words)
        for name, changed in (('inverted', 3), ('value-suppressed', 19)):
            self.assertEqual(forms[name][0]['differences'], 267, name)
            self.assertEqual(sum(a != b for a, b in zip(forms[name][1], self.banked_words)), changed, name)
            self.assertNotEqual(forms[name][1], self.banked_words, name)
        self.assertEqual(forms['value-primaryIndex'][1], self.words)
        for name in ('before-scale', 'after-scale', 'value-value-default'):
            self.assertEqual(forms[name][0]['body_words'], 404, name)
            self.assertNotEqual(forms[name][1], self.words, name)
        self.assertNotEqual(forms['value-secondaryBias'][1][:14], self.retail[:14])
        self.receipt('screens', complete_forms=19, one_word_short_defaults=True,
            equal_scores_not_word_identity=True, rejected_opening_regression=True, chosen=screen.SELECTED_NAME)


if __name__ == '__main__':
    unittest.main()
