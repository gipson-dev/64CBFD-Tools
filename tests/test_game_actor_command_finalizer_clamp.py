"""Qualify full-width bounds, clamp and secondary-tail source recovery."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_clamp as screen
from tools.tests import test_game_actor_command_finalizer_secondary as previous
from tools.tests import test_game_actor_command_finalizer_opening as opening
from tools.tests import test_game_actor_command_finalizer_recovery as recovery


class GameActorCommandFinalizerClampTests(opening.GameActorCommandFinalizerOpeningTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-command-finalizer-clamp-test'
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
        assert cls.baseline['source'] == 'b6b23e5b354ee79fb67f67aef212fffc3ca25d04855775f1f1ff7f76f1e2fa6f'
        assert cls.baseline['elf'] == 'c25a2f5ee0e9c056d10f79f83b8d1060a94948740a386e347103f5033b6d06c2'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        compiler = screen.previous.fitting.compile_candidate
        cls.meta, cls.words = compiler(cls.root, cls.out, 'selected', screen.SELECTED)
        _, cls.banked_words = compiler(cls.root, cls.out, 'banked', screen.BASE)
        _, cls.old_words = compiler(cls.root, cls.out, 'old-slot-control', opening.roles.roles.BASE)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), 0x61D10))

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (405, 72, 76, 0, ''))
        self.assertEqual(self.words[:14], self.retail[:14])
        self.assertEqual(self.words[-4:], self.retail[-4:])
        self.assertEqual(self.words[81:83], self.retail[81:83])
        self.assertEqual(self.words[210:214], self.retail[210:214])
        for index in (237, 251, 267, 268, 302):
            self.assertEqual(self.words[index], self.retail[index])
        self.assertEqual(self.words[357], self.retail[357])
        self.assertEqual(self.words[360], self.retail[360])
        self.assertEqual((self.words[362] >> 26, self.words[362] & 63,
            self.words[362] >> 16 & 31), (0, 0x21, 3))
        self.assertNotEqual(self.words[362], self.retail[362])
        self.assertEqual(sum(a != b for a, b in zip(self.banked_words, self.words)), 237)
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function'] == recovery.screen.FUNCTION])
        probes = screen.previous.previous.fault_probes(self.words, self.retail)
        self.assertEqual([r['equal'] for r in probes[:5]], [True, True, False, True, True])
        self.receipt('shape', words=405, frame=72, differences=76, matching_credit=0,
            secondary_block_aligned=True, primary_clamp_words_exact=True,
            secondary_velocity_copy_removed=True, probes=probes)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        with patch.object(previous.screen, 'SELECTED', screen.SELECTED):
            previous.GameActorCommandFinalizerSecondaryTests.test_05_native32_actual_source_and_fresh_effective_negatives(self)

    def test_06_owned_frame_and_temporary_records(self):
        with patch.multiple(opening.opening, BASE=screen.BASE, SELECTED=screen.SELECTED):
            opening.GameActorCommandFinalizerOpeningTests.test_06_owned_frame_and_temporary_records(self)

    def test_09_independent_original_links_and_carry_rebases(self):
        with patch.object(opening.opening, 'SELECTED', screen.SELECTED):
            opening.GameActorCommandFinalizerOpeningTests.test_09_independent_original_links_and_carry_rebases(self)

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        old, new = [screen.previous.previous.previous.fault_sweep(words, self.retail)
            for words in (self.banked_words, self.words)]
        self.assertEqual((len(old['cases']), old['fired_pairs'], old['equal_states']), (52, 2938, 1322))
        self.assertEqual((len(new['cases']), new['fired_pairs'], new['equal_states']), (52, 2938, 1598))
        self.assertEqual(new['first_cuts'], {10: 44, 7: 8})
        for before, after in zip(old['cases'], new['cases']):
            self.assertEqual(before['accesses'], after['accesses'])
            self.assertTrue(set(before['equal_cuts']).issubset(after['equal_cuts']))
        self.receipt('fault-boundary', **new, banked_equal_states=1322,
            no_previously_exact_sampled_states_lost=True, whole_private_fault_match=False,
            hardware_PC_BD_FCSR_not_claimed=True)

    def test_14_source_screens_and_effective_overflow_and_fault_controls(self):
        forms = {}
        for name, body in screen.candidates():
            meta, words = screen.previous.fitting.compile_candidate(self.root, self.out, 'screen-' + name, body)
            forms[name] = (meta, words)
        self.assertEqual(len(forms), 25)
        self.assertEqual(forms[screen.SELECTED_NAME][1], self.words)
        self.assertEqual(forms['lt-arms'][1], self.banked_words)
        for name in ('bounds-explicit-ge1', 'tail-current', 'tail-primaryIndex', 'tail-suppressed'):
            self.assertEqual((forms[name][0]['body_words'], forms[name][0]['differences']), (406, 112), name)
        self.assertFalse(forms['tail-secondaryBias'][1][:14] == self.retail[:14])
        rejected = forms['aligned-early-lower']
        self.assertEqual((rejected[0]['body_words'], rejected[0]['differences']), (405, 70))
        probes = screen.previous.previous.fault_probes(rejected[1], self.retail)
        self.assertEqual((probes[1]['equal'], probes[1]['GPRs'], probes[1]['FPRs']), (False, [7], [16]))
        self.receipt('screens', complete_forms=25, rejected_overflow=True,
            rejected_opening_regression=True, rejected_better_score_with_cut9_loss=True,
            chosen=screen.SELECTED_NAME, production_padding_not_used=True)

    def test_15_signed_velocity_and_bound_controls_are_effective(self):
        controls = {
            'unsigned-tail-velocity': screen.replace_once(screen.SELECTED,
                '*(s16 *)(actor + 0x204) += *(s8 *)(actor + 0x209);',
                '*(s16 *)(actor + 0x204) += actor[0x209];'),
            'wrong-category-upper': screen.replace_once(screen.SELECTED, 'upper = 120;', 'upper = 119;'),
            'wrong-primary-clamp': screen.replace_once(screen.SELECTED, 'value >= 256 ? limit : value',
                'value >= 255 ? 254 : value')}
        for name, body in controls.items():
            self.assertNotEqual(body, screen.SELECTED, name)
            self.assertNotEqual(self.run_native(name, self.native_source(body))[0], 0, name)
        self.receipt('native-tail-controls', fresh_effective_controls=3,
            signed_velocity_category_bounds_and_primary_clamp=True)


if __name__ == '__main__':
    unittest.main()
