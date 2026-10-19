"""Qualify direct-C draw spills and count-gated cursor stores, not a match."""

import hashlib
import itertools
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_draw as source
from tools.tests import test_game_actor_state_tick_candidates as guest
from tools.tests import test_game_actor_state_tick_homes as homes
from tools.tests import test_game_actor_state_tick_lifetimes as lifetime


ROOT = Path(__file__).resolve().parents[2]


def alias_case(name, phase):
    if name in source.prior.MATCHED_HOMES:
        memory, actions = homes.alias_case(name, phase)
        return memory, dict(actions=actions), guest.STATUS
    memory = guest.fixture(category=0xB9, action=5, seed=0)
    target, value = (guest.TEXT, 2) if name == 'index' else (guest.ACTION, 5)
    mutation = guest.STACK + phase - 288 + source.MATCHED_HOMES[name], value, 4
    return memory, dict(actions={(target, 0): (mutation,)}), target


class ActorStateTickDrawTests(unittest.TestCase):
    maxDiff = 1200
    compare = homes.ActorStateTickHomeTests.compare
    test_empty_inactive_first_seen_and_all_sixteen_slots = guest.ActorStateTickCandidateTests.test_empty_inactive_first_seen_and_all_sixteen_slots
    test_categories_timer_signs_states_actions_and_probability = guest.ActorStateTickCandidateTests.test_categories_timer_signs_states_actions_and_probability
    test_opaque_helpers_can_replace_global_and_mutate_captured_inputs = guest.ActorStateTickCandidateTests.test_opaque_helpers_can_replace_global_and_mutate_captured_inputs
    test_timer_reload_has_effective_literal_public_read_control = lifetime.ActorStateTickLifetimeTests.test_timer_reload_has_effective_literal_public_read_control

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        source.prior.prior.prior.freeze(cls.root, cls.output)
        cls.record, cls.words = source.compile_candidate(cls.root, cls.output, 'selected', source.SELECTED)
        cls.before_record, cls.before = source.prior.compile_candidate(cls.root, cls.output,
                                                                        'before', source.prior.SELECTED)
        cls.retail = struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(),
                                       source.prior.prior.prior.ROM)
        cls.coverage, cls.completed, cls.ordered_pairs, cls.public_reads = set(), 0, 0, 0
        cls.alias_pairs, cls.old_draw_negatives, cls.empty_private_pairs, cls.native_count = 0, 0, 0, 0
        cls.action_word_pairs, cls.timer_cache_negatives = 0, 0

    @classmethod
    def tearDownClass(cls):
        receipt = dict(words=cls.record['body_words'], frame=cls.record['frame'],
            raw_sha256=cls.record['raw_sha256'], raw_differences=cls.record['aligned_differences'],
            completed_fixtures=cls.completed, ordered_public_read_pairs=cls.ordered_pairs,
            public_read_footprint_pairs=cls.public_reads, retail_words_visited=len(cls.coverage),
            matched_named_homes=len(cls.record['matched_homes']), alias_pairs=cls.alias_pairs,
            effective_predecessor_draw_negatives=cls.old_draw_negatives,
            empty_count_private_store_pairs=cls.empty_private_pairs, native_fixtures=cls.native_count,
            action_word_alias_pairs=cls.action_word_pairs, known_timer_cache_negatives=cls.timer_cache_negatives,
            installed=False, matching_credit=0, complete_private_fault_or_register_equivalence=False)
        (cls.output / 'qualification.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('actor-state direct draw qualification:', receipt)

    def test_real_declarations_nineteen_homes_and_complete_source_fingerprint(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['aligned_differences']),
                         (678, 288, 344))
        self.assertEqual(self.record['raw_sha256'], source.RAW_SHA256)
        self.assertEqual(self.record['diagnostics'], '')
        self.assertFalse(self.record['installed'])
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual({n: self.record['homes'][n] for n in source.MATCHED_HOMES}, source.MATCHED_HOMES)
        self.assertEqual(len(self.record['matched_homes']), 19)
        _, _, old = source.prior.declarations(source.prior.SELECTED)
        _, _, new = source.prior.declarations(source.SELECTED)
        self.assertEqual(set(new), set(old) - {'selector', 'otherActor'} | {'index', 'address'})
        self.assertEqual(len(old), len(new))
        self.assertEqual(new['actorAction'], '    s32 actorAction;\n')
        raw, bindings = source.prior.prior.prior.payload(self.output / 'selected.o')
        words = struct.unpack('>678I', raw)
        self.assertEqual(sum(map(len, bindings.values())), 62)
        self.assertEqual([(i, w >> 26) for i, w in enumerate(words)
                          if w >> 21 & 31 == 29 and w & 65535 == 0x104 and w >> 26 in (35, 43)],
                         [(303, 43), (304, 35)])
        self.assertEqual([(i, w >> 26) for i, w in enumerate(words)
                          if w >> 21 & 31 == 29 and w & 65535 == 0xA0 and w >> 26 in (35, 43)],
                         [(638, 43), (658, 35)])

    def test_nineteen_effective_aliases_and_old_draw_home_controls(self):
        for name, phase in itertools.product(source.MATCHED_HOMES, (0, 8)):
            with self.subTest(home=name, phase=phase):
                memory, options, target = alias_case(name, phase)
                retail = guest.TickOracle(self.retail, memory, phase, **options).run()
                candidate = guest.TickOracle(self.words, memory, phase, **options).run()
                baseline = guest.TickOracle(self.retail, memory, phase).run()
                for model in (retail, candidate):
                    self.assertGreater(model.provider.occurrences.get(target, 0), 0)
                self.assertTrue(homes.observation(retail) != homes.observation(baseline),
                                'Ineffective retail home alias')
                self.assertTrue(homes.observation(candidate) == homes.observation(retail),
                                'Recovered home alias changed public observations')
                type(self).alias_pairs += 1
                if name in ('index', 'actorAction'):
                    old = guest.TickOracle(self.before, memory, phase, **options).run()
                    self.assertGreater(old.provider.occurrences.get(target, 0), 0)
                    self.assertTrue(homes.observation(old) != homes.observation(retail),
                                    'Ineffective predecessor draw control')
                    type(self).old_draw_negatives += 1

    def test_nonpositive_count_skips_cursor_homes_and_preserves_eager_table_reads(self):
        for count, phase in itertools.product((-1, 0), (0, 8)):
            memory = guest.fixture(count=count, category=0xB7)
            retail, candidate, old = (guest.TickOracle(w, memory, phase).run()
                                      for w in (self.retail, self.words, self.before))
            self.assertTrue(homes.observation(retail) == homes.observation(candidate))
            for model, slots in ((retail, (0x84, 0x60, 0x5C)),
                                 (candidate, (0xA4, 0xFC, 0x9C))):
                for slot in slots:
                    self.assertFalse(any(s[0] == guest.STACK + phase - 288 + slot for s in model.stores))
            for slot in (0xA4, 0xA0, 0x9C):
                self.assertTrue(any(s[0] == guest.STACK + phase - 288 + slot for s in old.stores))
            for slot in (0xDC, 0xD8, 0xD4, 0xCC, 0xC8, 0xC4, 0xC0, 0xBC, 0xB8, 0xB0, 0xAC):
                address = guest.STACK + phase - 288 + slot
                self.assertEqual([s for s in candidate.stores if s[0] == address],
                                 [s for s in retail.stores if s[0] == address])
            type(self).empty_private_pairs += 1

    def test_actor_action_call_save_is_a_full_word_not_a_byte(self):
        for value, phase in itertools.product((0, 4, 5, 0x105, 0x80000005, 0xFFFFFFFF), (0, 8)):
            with self.subTest(value=hex(value), phase=phase):
                memory = guest.fixture(category=0xB9, action=5, seed=0)
                options = dict(actions={(guest.ACTION, 0):
                    ((guest.STACK + phase - 288 + 0x104, value, 4),)})
                retail, candidate = (guest.TickOracle(w, memory, phase, **options).run()
                                      for w in (self.retail, self.words))
                for model in (retail, candidate):
                    self.assertGreater(model.provider.occurrences.get(guest.ACTION, 0), 0)
                self.assertTrue(homes.observation(retail) == homes.observation(candidate))
                type(self).action_word_pairs += 1

    def test_cached_timer_alias_is_still_an_open_source_boundary(self):
        for phase in (0, 8):
            memory = guest.fixture(category=0xB9, action=5, seed=0)
            guest.put(memory, guest.STATE + 0x29C, 5)
            guest.put(memory, guest.ALT_STATE + 0x29C, 19)
            options = dict(actions={(guest.STATUS, 0):
                ((guest.STACK + phase - 288 + 0xC4, guest.ALT_STATE + 0x29C, 4),)})
            retail, candidate = (guest.TickOracle(w, memory, phase, **options).run()
                                  for w in (self.retail, self.words))
            for model in (retail, candidate):
                self.assertGreater(model.provider.occurrences.get(guest.STATUS, 0), 0)
            self.assertIn((guest.STATE + 0x29C, 4, 0), retail.stores)
            self.assertTrue(homes.observation(retail) != homes.observation(candidate),
                            'Unexpectedly closed the unqualified timer-cache boundary')
            type(self).timer_cache_negatives += 1

    def test_complete_native32_source_at_three_optimizations_with_sanitizer(self):
        with patch.object(lifetime.source, 'SELECTED', source.SELECTED):
            lifetime.ActorStateTickLifetimeTests.test_complete_native32_source_at_three_optimizations_with_ubsan(self)

    def test_complete_owner_profiles_preserve_other_functions_and_pools(self):
        rows = source.qualify_owner(self.root, self.output / 'owner')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['preserved_neighbors'] == 72 and r['words'] == 678 and r['frame'] == 288
                            for r in rows))

    def test_saved_main_roles_match_at_the_measured_status_boundary(self):
        class Capture(guest.TickOracle):
            def record_call(self, target):
                super().record_call(target)
                if target == guest.STATUS and self.r[4] == 1:
                    self.capture = self.r[16:24] + [self.r[30]]

        memory = guest.fixture(count=16, category=0xB9, action=5, seed=1)
        retail, candidate, old = (Capture(w, memory).run() for w in (self.retail, self.words, self.before))
        self.assertEqual(retail.capture, [4, guest.GLOBAL, 1, guest.ACTORS + 0x32C, 0, 1,
                                          guest.STATE + 0x360, guest.STATE + 0x220, 2])
        self.assertEqual(candidate.capture, retail.capture)
        self.assertNotEqual(old.capture[:4], retail.capture[:4])
        (self.output / 'remaining-register-boundary.json').write_text(json.dumps(dict(
            retail=retail.capture, selected=candidate.capture, predecessor=old.capture,
            measured_status_slot1_roles_equal=True, complete_register_equivalence=False), indent=2) + '\n')

    def test_pinned_production_inputs_stay_unchanged(self):
        for name, digest in source.prior.prior.prior.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
