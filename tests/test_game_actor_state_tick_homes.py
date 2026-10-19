"""Qualify actual homes and ordered public accesses without claiming a match."""

import copy
import itertools
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_homes as source
from tools.tests import test_game_actor_state_tick_candidates as guest
from tools.tests import test_game_actor_state_tick_lifetimes as lifetime


ROOT = Path(__file__).resolve().parents[2]
POINTER_FIELDS = dict(groups=0xE64, latches=0x35C, actions=0x31C, states=0x19C,
    elapsed=0x21C, timers=0x29C, cooldowns=0x25C, timeouts=0x41C, events=0x3DC,
    groupCounts=0xDDC, scores=0x1574)


def public_reads(model):
    return [r for r in model.reads if not guest.private(r[0])]


def observation(model):
    return ([s for s in model.stores if not guest.private(s[0])], model.calls, model.r[2],
            {a: b for a, b in model.memory.items() if not guest.private(a)}, public_reads(model))


def alias_case(name, phase):
    memory = guest.fixture(count=4, category=0xB9, seed=3, active=0xFFFF, seen=0xFFFF,
                           action=0 if name == 'idle' else 5)
    guest.put(memory, guest.STATE + 0x29C, -1)
    if name == 'groups':
        for slot in range(4):
            guest.put(memory, guest.ALT_STATE + 0xE64 + slot * 4, (slot + 1) % 4)
    if name == 'actions':
        for slot in range(4):
            guest.put(memory, guest.ALT_STATE + 0x31C + slot * 4, 0)
    if name == 'groupCounts':
        guest.put(memory, guest.STATE + 0x35C, 0)
    if name in POINTER_FIELDS:
        value, size = guest.ALT_STATE + POINTER_FIELDS[name], 4
    elif name == 'idle':
        value, size = 0, 1
    else:
        value, size = {'changed': 0x40000000, 'previousTimer': 5, 'active': 0,
                       'seen': 0x12345678, 'count': 2}[name], 4
    action = (guest.STACK + phase - 288 + source.MATCHED_HOMES[name], value, size)
    return memory, {(guest.STATUS, 0): (action,)}


class ActorStateTickHomeTests(unittest.TestCase):
    test_empty_inactive_first_seen_and_all_sixteen_slots = guest.ActorStateTickCandidateTests.test_empty_inactive_first_seen_and_all_sixteen_slots
    test_categories_timer_signs_states_actions_and_probability = guest.ActorStateTickCandidateTests.test_categories_timer_signs_states_actions_and_probability
    test_opaque_helpers_can_replace_global_and_mutate_captured_inputs = guest.ActorStateTickCandidateTests.test_opaque_helpers_can_replace_global_and_mutate_captured_inputs
    test_timer_reload_has_effective_literal_public_read_control = lifetime.ActorStateTickLifetimeTests.test_timer_reload_has_effective_literal_public_read_control

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        source.prior.prior.freeze(cls.root, cls.output)
        cls.record, cls.words = source.compile_candidate(cls.root, cls.output, 'selected', source.SELECTED)
        cls.before_record, cls.before = source.prior.compile_candidate(cls.root, cls.output,
                                                                      'before', source.prior.SELECTED)
        cls.retail = struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(),
                                       source.prior.prior.ROM)
        cls.coverage, cls.completed, cls.public_reads, cls.native_count = set(), 0, 0, 0
        cls.ordered_pairs, cls.alias_pairs, cls.old_home_negatives = 0, 0, 0

    @classmethod
    def tearDownClass(cls):
        receipt = dict(completed_fixtures=cls.completed, ordered_public_read_pairs=cls.ordered_pairs,
            retail_words_visited=len(cls.coverage), words=cls.record['body_words'], frame=cls.record['frame'],
            public_read_footprint_pairs=cls.public_reads, native_fixtures=cls.native_count,
            matched_named_homes=len(cls.record['matched_homes']), alias_pairs=cls.alias_pairs,
            effective_old_home_negatives=cls.old_home_negatives, installed=False, matching_credit=0,
            complete_private_fault_or_register_equivalence=False)
        (cls.output / 'qualification.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('actor-state home qualification:', receipt)

    def compare(self, memory, phase=0, **providers):
        expected, calls, stores, result = guest.reference(memory, **providers)
        for target, occurrence in providers.get('actions', {}):
            self.assertGreater(sum(c[0] == target for c in calls), occurrence, 'Mutation did not fire')
        models = [guest.TickOracle(w, memory, phase, **providers).run() for w in (self.retail, self.words)]
        for model in models:
            self.assertEqual(model.calls, calls)
            self.assertEqual([s for s in model.stores if not guest.private(s[0])], stores)
            self.assertEqual({a: b for a, b in model.memory.items() if not guest.private(a)},
                             {a: b for a, b in expected.items() if not guest.private(a)})
            self.assertEqual(model.r[2], result)
        self.assertEqual(public_reads(models[0]), public_reads(models[1]))
        type(self).completed += 1
        type(self).ordered_pairs += 1
        type(self).coverage.update(models[0].visits)

    def test_closed_declarations_seventeen_homes_and_two_word_schedule(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['aligned_differences']),
                         (678, 288, 600))
        self.assertEqual(self.record['raw_sha256'], source.RAW_SHA256)
        self.assertEqual(self.record['diagnostics'], '')
        self.assertFalse(self.record['installed'])
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual({n: self.record['homes'][n] for n in source.MATCHED_HOMES}, source.MATCHED_HOMES)
        self.assertEqual(len(self.record['matched_homes']), 17)
        for name in ('reset', 'status', 'band'):
            self.assertNotEqual(self.record['homes'][name], source.TARGET_HOMES[name])
        _, _, old_names = source.declarations(source.prior.SELECTED)
        _, _, new_names = source.declarations(source.SELECTED)
        self.assertEqual(set(new_names), set(old_names) - {'owner'} | {'selector'})
        self.assertEqual(len(new_names), len(old_names))
        with self.assertRaisesRegex(ValueError, 'added/lost'):
            source.ordered(source.prior.SELECTED, list(old_names)[:-1])

        old, old_bindings = source.prior.prior.payload(self.output / 'before.o')
        new, new_bindings = source.prior.prior.payload(self.output / 'selected.o')
        a, b = list(struct.unpack('>678I', old)), list(struct.unpack('>678I', new))
        self.assertEqual((a[400] >> 26, a[401] >> 26), (35, 32))
        a[400], a[401] = a[401], a[400]
        differences = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(len(differences), 101)
        self.assertTrue(all(x >> 16 == y >> 16 and x >> 21 & 31 == 29 for x, y in differences))
        bindings = copy.deepcopy(old_bindings)
        self.assertNotIn(1600, bindings)
        bindings[1600] = bindings.pop(1604)
        self.assertEqual(bindings[1600], [('R_MIPS_LO16', 'D_800E0BD0')])
        self.assertEqual(new_bindings, bindings)

    def test_all_seventeen_aliases_fire_and_reject_old_homes_in_both_phases(self):
        for name, phase in itertools.product(source.MATCHED_HOMES, (0, 8)):
            with self.subTest(home=name, phase=phase):
                memory, actions = alias_case(name, phase)
                baseline = guest.TickOracle(self.retail, memory, phase).run()
                retail = guest.TickOracle(self.retail, memory, phase, actions=actions).run()
                candidate = guest.TickOracle(self.words, memory, phase, actions=actions).run()
                self.assertGreater(retail.provider.occurrences.get(guest.STATUS, 0), 0)
                self.assertGreater(candidate.provider.occurrences.get(guest.STATUS, 0), 0)
                self.assertNotEqual(observation(retail), observation(baseline), 'Ineffective retail alias')
                self.assertEqual(observation(candidate), observation(retail))
                old = guest.TickOracle(self.before, memory, phase, actions=actions)
                try:
                    old.run()
                    self.assertNotEqual(observation(old), observation(retail), 'Ineffective old-home control')
                except AssertionError as error:
                    self.assertIn('unmapped', str(error))
                self.assertGreater(old.provider.occurrences.get(guest.STATUS, 0), 0,
                                   'Old-home negative failed before its mutation')
                type(self).alias_pairs += 1
                type(self).old_home_negatives += 1

    def test_complete_native32_source_with_sanitizer_and_negative_controls(self):
        with patch.object(source.prior, 'SELECTED', source.SELECTED):
            lifetime.ActorStateTickLifetimeTests.test_complete_native32_source_at_three_optimizations_with_ubsan(self)

    def test_complete_owner_profiles_preserve_other_bodies_and_pools(self):
        rows = source.qualify_owner(self.root, self.output / 'owner')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['preserved_neighbors'] == 72 and r['words'] == 678 and r['frame'] == 288 for r in rows))


if __name__ == '__main__':
    unittest.main()
