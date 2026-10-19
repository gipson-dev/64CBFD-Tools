"""Qualify direct C frame/buffer recovery while keeping allocation unresolved."""
from dataclasses import replace
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_pair_scheduler_home_candidates as homes
from tools.tests import test_game_actor_pair_scheduler_recovery as previous

source, guest = homes.source, previous.guest


def literal_state(model):
    return (model.r, model.f, model.memory, model.stores, model.reads, model.requested,
        model.visits, model.accesses, model.condition, model.calls, model.events)


def frame_stores(model, phase):
    base = guest.STACK + phase - 192
    return [row for row in model.stores if base + 0x7C <= row[0] < base + 0x94]


class ActorPairSchedulerHomeTests(unittest.TestCase):
    native = previous.ActorPairSchedulerRecoveryTests.native
    test_02_ordered_public_buffers_calls_and_provider_effects = previous.ActorPairSchedulerRecoveryTests.test_02_ordered_public_buffers_calls_and_provider_effects
    test_05_negative_budgets_fire_bounded_call_gates = previous.ActorPairSchedulerRecoveryTests.test_05_negative_budgets_fire_bounded_call_gates
    test_06_actual_restored_null_actor_child_returns = previous.ActorPairSchedulerRecoveryTests.test_06_actual_restored_null_actor_child_returns
    test_07_production_inputs_unchanged = previous.ActorPairSchedulerRecoveryTests.test_07_production_inputs_unchanged

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / (homes.BUILD + '/qualification')
        cls.values = source.freeze(cls.root, cls.out)
        cls.obj, cls.words, cls.row = source.compile_candidate(cls.root, cls.out, 'selected', homes.SELECTED)
        cls.retail = list(struct.unpack_from('>261I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_frame_homes_saved_actor_and_unchanged_initial_words(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (255, 192, 238))
        self.assertFalse(self.row['diagnostics'])
        self.assertEqual(self.row['raw_SHA256'], 'ad992aec1fad04999e4966bb07af529738e8312aaabcd1815eae3b6ea152d630')
        self.assertEqual(self.words[:17], self.retail[:17])
        self.assertEqual(self.words[0x60 // 4], 0xAFAE007C)
        self.assertEqual(self.words[0xA4 // 4], 0x27B00090)
        self.assertEqual(self.words[0xA8 // 4], 0x27A20080)
        self.assertEqual(self.words[0x14C // 4], 0xC7AA0088)
        self.assertEqual(self.words[0x9C // 4], 0xC7D00014)
        self.assertEqual(self.words[0x230 // 4], 0x27DE032C)
        self.assertEqual(self.words[0x20C // 4] >> 26, 3)
        self.assertEqual(self.words[0x210 // 4], 0xAC5916C0)
        subtractions = [w for w in self.words if w >> 26 == 17 and (w >> 21 & 31, w & 63) == (16, 1)]
        self.assertTrue(any(w >> 16 & 31 == w >> 11 & 31 for w in subtractions))
        self.receipts.update(raw_words=255, frame=192, raw_differences=238,
            initial_exact_words=17, group_home=0x7C, costs_home=0x80, choices_home=0x90,
            saved_actor_register=30, first_call_delay_slot_is_second_mask_clear=True, installed=False)

    def test_03_native32_profiles_and_effective_updated_negatives(self):
        for opt in ('-O0', '-O2', '-O3'):
            self.assertEqual(self.native(homes.SELECTED, 'native' + opt[1:], opt), 0)
        body = homes.SELECTED
        controls = {
            'signed-cursors': body.replace('    u8 first;', '    s8 first;').replace('    u8 second;', '    s8 second;'),
            'short-attempt-cap': body.replace('attempts >= 64', 'attempts >= 63'),
            'inclusive-rank-tie': body.replace('cost < costs[2]', 'cost <= costs[2]').replace('cost < dz', 'cost <= dz'),
            'two-ranked-pairs': body.replace('for (i = 0; i < 3; i++) {\n                    candidate', 'for (i = 0; i < 2; i++) {\n                    candidate'),
            'lost-high-mask': body.replace('0x10001u', '1u'),
            'reloaded-group-bank': body.replace('groups[primary] != groups[candidate]',
                '((s32 *)((u8 *)D_800D23B0 + 0xE64))[primary] != ((s32 *)((u8 *)D_800D23B0 + 0xE64))[candidate]').replace(
                    'groups = (s32 *)((u8 *)D_800D23B0 + 0xE64);', 'groups = (s32 *)((u8 *)D_800D23B0 + 0xE64); (void)groups;'),
            'reloaded-sentinel': body.replace('costs[i] = sentinel;', 'costs[i] = D_8009DA68;').replace(
                'sentinel = D_8009DA68;', 'sentinel = D_8009DA68; (void)sentinel;'),
            'wrong-rank-position': body.replace('dz = x - *(f32 *)(actor + 0x1C);',
                'dz = x - *(f32 *)(D_800CC2D0 + candidate * 0x32C + 0x1C);'),
        }
        results = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            code = self.native(changed, 'negative-' + name)
            self.assertNotEqual(code, 0, name)
            results[name] = code
        self.receipts.update(native32_profiles=['O0', 'O2', 'O3'], native_fixtures=80,
            UBSan=True, effective_negatives=results)

    def test_04_both_complete_owner_profiles_preserve_neighbors_and_pools(self):
        with patch.object(source, 'SELECTED', homes.SELECTED):
            previous.ActorPairSchedulerRecoveryTests.test_04_both_complete_owner_profiles_preserve_neighbors_and_pools(self)

    def test_08_complete_private_RAM_and_ordered_buffer_stores(self):
        pairs = 0
        for case in self.corpus:
            memory = guest.fixture(case)
            for phase in (0, 8):
                a, b = [guest.SchedulerModel(words, memory, case, phase).run() for words in (self.retail, self.words)]
                self.assertEqual(a.memory, b.memory)
                self.assertEqual(frame_stores(a, phase), frame_stores(b, phase))
                pairs += 1
        self.receipts.update(complete_RAM_pairs=pairs, ordered_group_and_rank_stores_equal=True,
            full_GP_FP_literal_state_not_yet_equal=True, opaque_pair_effects_for_complete_RAM=True)

    def test_09_fired_initial_private_prefix_and_remaining_allocation_boundary(self):
        memory, count = guest.fixture(guest.Case()), 0
        for phase in (0, 8):
            for cut in range(15):
                models = []
                for words in (self.retail, self.words):
                    model = guest.SchedulerModel(words, memory, guest.Case(), phase)
                    model.fault = cut
                    with self.assertRaises(guest.core.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    models.append(model)
                self.assertEqual(literal_state(models[0]), literal_state(models[1]))
                count += 1
            models = []
            for words in (self.retail, self.words):
                model = guest.SchedulerModel(words, memory, guest.Case(), phase)
                model.fault = 15
                with self.assertRaises(guest.core.AccessFault):
                    model.run()
                self.assertEqual(model.accesses, 15)
                models.append(model)
            self.assertEqual(models[0].requested, models[1].requested)
            self.assertEqual(models[0].memory, models[1].memory)
            self.assertNotEqual(models[0].r, models[1].r)
        self.receipts.update(initial_fired_literal_cut_pairs=count, remaining_boundary_cut=15,
            remaining_boundary='Context pointer in retail A2 versus raw V1')

    def test_10_guest_group_table_aliases_reject_old_buffer_homes(self):
        _, old, _ = source.compile_candidate(self.root, self.out, 'old-homes-control', source.SELECTED)
        pairs, negatives = 0, 0
        for phase in (0, 8):
            for count in (6, 9):
                case = replace(guest.Case(), count=count, budget=1)
                memory = guest.fixture(case)
                bank = guest.STACK + phase - 192 + 0x80 - 0xE64
                data = bytes(memory[guest.BANKS[0] + i] for i in range(0x1C00))
                memory.update((bank + i, v) for i, v in enumerate(data))
                guest.put(memory, guest.CONTEXT, bank, 4)
                a, b = [guest.SchedulerModel(words, memory, case, phase).run() for words in (self.retail, self.words)]
                self.assertEqual(a.memory, b.memory)
                self.assertEqual(a.calls, b.calls)
                self.assertEqual(a.r[2], b.r[2])
                prior = guest.SchedulerModel(old, memory, case, phase).run()
                self.assertNotEqual((a.calls, previous.public_stores(a)),
                    (prior.calls, previous.public_stores(prior)))
                pairs += 1
                negatives += 1
        self.receipts.update(completed_guest_frame_alias_pairs=pairs, effective_old_home_negatives=negatives,
            alias='Captured group table overlaps live SP80 ranking scratch; guest-only')


if __name__ == '__main__':
    unittest.main()
