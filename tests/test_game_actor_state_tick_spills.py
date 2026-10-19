"""Bounded spill ownership checks; register/private/fault closure remains open."""

import copy
import hashlib
import itertools
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_spills as source
from tools.tests import test_game_actor_state_tick_candidates as guest
from tools.tests import test_game_actor_state_tick_homes as homes


ROOT = Path(__file__).resolve().parents[2]
CURSORS = dict(reset=(0x84, 0x1C), status=(0x60, 0x39C), band=(0x5C, 0x9C),
    timerRow=(0x7C, 0x29C), cooldownRow=(0x74, 0x25C), stateRow=(0x6C, 0x19C),
    eventRow=(0x68, 0x3DC), actionRow=(0x54, 0x31C))
CALL_SAVES = dict(eventByte=(0x64, guest.SIGNAL, guest.EVENT_BYTES + 8),
    actorAction=(0x104, guest.ACTION, 5), drawActor=(0x8C, guest.TEXT, guest.ACTORS + 0x32C))


def alias_case(name, phase):
    if name in source.prior.MATCHED_HOMES:
        memory, actions = homes.alias_case(name, phase)
        return memory, dict(actions=actions), guest.STATUS
    memory = guest.fixture(seed=0, category=0xB9, action=5)
    if name in CURSORS:
        slot, offset = CURSORS[name]
        guest.put(memory, guest.STATE + 0x35C, 0)
        value, target = guest.ALT_STATE + offset, guest.STATUS
        options = dict(status=0)
    else:
        slot, target, value = CALL_SAVES[name]
        guest.put(memory, guest.STATE + 0x19C, 3)
        guest.put(memory, guest.STATE + 0x25C, 30)
        guest.put(memory, guest.EVENT_BYTES + 8, 0x82, 1)
        options = {}
    options['actions'] = {(target, 0): ((guest.STACK + phase - 288 + slot, value, 4),)}
    return memory, options, target


class ActorStateTickSpillTests(unittest.TestCase):
    maxDiff = 1200
    test_empty_inactive_first_seen_and_all_sixteen_slots = guest.ActorStateTickCandidateTests.test_empty_inactive_first_seen_and_all_sixteen_slots
    test_categories_timer_signs_states_actions_and_probability = guest.ActorStateTickCandidateTests.test_categories_timer_signs_states_actions_and_probability
    test_opaque_helpers_can_replace_global_and_mutate_captured_inputs = guest.ActorStateTickCandidateTests.test_opaque_helpers_can_replace_global_and_mutate_captured_inputs

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.report, cls.before, cls.words = source.qualify(cls.root, cls.output)
        cls.raw, cls.bindings = source.prior.prior.prior.payload(cls.output / 'source.o')
        cls.retail = struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(),
                                       source.prior.prior.prior.ROM)
        cls.completed, cls.alias_pairs, cls.old_spill_negatives = 0, 0, 0
        cls.timer_cache_pairs, cls.draw_index_negatives, cls.coverage = 0, 0, set()

    @classmethod
    def tearDownClass(cls):
        receipt = dict(cls.report, completed_three_way_fixtures=cls.completed,
            effective_alias_pairs=cls.alias_pairs, effective_old_spill_negatives=cls.old_spill_negatives,
            cached_timer_pairs=cls.timer_cache_pairs, known_draw_index_negatives=cls.draw_index_negatives,
            retail_words_visited=len(cls.coverage), complete_register_or_fault_equivalence=False)
        (cls.output / 'test-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('actor-state experimental spills:', receipt)

    def compare(self, memory, phase=0, **providers):
        expected, calls, stores, result = guest.reference(memory, **providers)
        for target, occurrence in providers.get('actions', {}):
            self.assertGreater(sum(c[0] == target for c in calls), occurrence, 'Mutation did not fire')
        models = [guest.TickOracle(w, memory, phase, **providers).run()
                  for w in (self.retail, self.before, self.words)]
        for model in models:
            self.assertEqual(model.calls, calls)
            self.assertEqual([s for s in model.stores if not guest.private(s[0])], stores)
            self.assertEqual({a: b for a, b in model.memory.items() if not guest.private(a)},
                             {a: b for a, b in expected.items() if not guest.private(a)})
            self.assertEqual(model.r[2], result)
            self.assertEqual(homes.public_reads(model), homes.public_reads(models[0]))
        type(self).completed += 1
        type(self).coverage.update(models[0].visits)

    def rejects_after_mutation(self, words, memory, phase, options, target, retail):
        model = guest.TickOracle(words, memory, phase, **options)
        try:
            model.run()
        except AssertionError as error:
            self.assertIn('unmapped', str(error))
        else:
            self.assertTrue(homes.observation(model) != homes.observation(retail),
                            'Ineffective wrong-spill control')
        self.assertGreater(model.provider.occurrences.get(target, 0), 0,
                           'Control failed before requested mutation')

    def test_origins_bindings_shape_and_no_production_change(self):
        normalized, bindings = source.normalize(self.raw, self.bindings)
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), source.NORMALIZED_SHA)
        self.assertEqual((len(normalized), len(source.SLOTS), sum(map(len, bindings.values()))),
                         (2712, 11, 62))
        self.assertEqual((self.report['words'], self.report['frame'], self.report['real_word_differences']),
                         (678, 288, 600))
        self.assertFalse(self.report['installed'])
        self.assertFalse(self.report['complete_private_equivalence'])
        self.assertNotEqual(self.words, self.retail)
        order = source.origins()
        self.assertEqual([item for item in order if not isinstance(item, int)], [('actor-bias', 363)])
        self.assertEqual(set(range(678)) - {item for item in order if isinstance(item, int)}, {399})
        original = struct.unpack('>678I', self.raw)
        # Every source memory operation survives; only a private pointer source changes role.
        memory_origins = [i for i, w in enumerate(original) if w >> 26 in source.MEMORY]
        self.assertTrue(all(order.count(i) == 1 for i in memory_origins))
        for at, item in enumerate(order):
            if isinstance(item, int) and item * 4 in self.bindings:
                self.assertEqual(bindings[at * 4], self.bindings[item * 4])
        for name, digest in source.prior.prior.prior.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)

    def test_all_twenty_eight_aliases_fire_and_new_spills_reject_raw_layout(self):
        names = (*source.prior.MATCHED_HOMES, *CURSORS, *CALL_SAVES)
        self.assertEqual(len(names), 28)
        for name, phase in itertools.product(names, (0, 8)):
            with self.subTest(home=name, phase=phase):
                memory, options, target = alias_case(name, phase)
                plain = {k: v for k, v in options.items() if k != 'actions'}
                baseline = guest.TickOracle(self.retail, memory, phase, **plain).run()
                retail = guest.TickOracle(self.retail, memory, phase, **options).run()
                candidate = guest.TickOracle(self.words, memory, phase, **options).run()
                for model in (retail, candidate):
                    self.assertGreater(model.provider.occurrences.get(target, 0), 0)
                self.assertTrue(homes.observation(retail) != homes.observation(baseline),
                                'Ineffective retail alias')
                self.assertTrue(homes.observation(candidate) == homes.observation(retail),
                                'Spill alias changed public observations')
                type(self).alias_pairs += 1
                if name not in source.prior.MATCHED_HOMES:
                    self.rejects_after_mutation(self.before, memory, phase, options, target, retail)
                    type(self).old_spill_negatives += 1

    def test_timer_reset_keeps_cached_row_after_table_home_alias(self):
        for phase in (0, 8):
            memory = guest.fixture(seed=0, category=0xB9, action=5)
            guest.put(memory, guest.STATE + 0x29C, 5)
            guest.put(memory, guest.ALT_STATE + 0x29C, 19)
            options = dict(actions={(guest.STATUS, 0):
                ((guest.STACK + phase - 288 + 0xC4, guest.ALT_STATE + 0x29C, 4),)})
            retail = guest.TickOracle(self.retail, memory, phase, **options).run()
            candidate = guest.TickOracle(self.words, memory, phase, **options).run()
            self.assertGreater(retail.provider.occurrences.get(guest.STATUS, 0), 0)
            self.assertGreater(candidate.provider.occurrences.get(guest.STATUS, 0), 0)
            self.assertIn((guest.STATE + 0x29C, 4, 0), retail.stores,
                          'Fixture did not enter the timer-reset path')
            self.assertTrue(homes.observation(candidate) == homes.observation(retail),
                            'Cached timer changed public observations')
            self.rejects_after_mutation(self.before, memory, phase, options, guest.STATUS, retail)
            type(self).timer_cache_pairs += 1

    def test_missing_draw_index_and_empty_count_stores_stay_explicitly_open(self):
        for phase in (0, 8):
            memory = guest.fixture(seed=0, category=0xB9, action=5)
            options = dict(actions={(guest.TEXT, 0): ((guest.STACK + phase - 288 + 0xA0, 2, 4),)})
            retail = guest.TickOracle(self.retail, memory, phase, **options).run()
            self.rejects_after_mutation(self.words, memory, phase, options, guest.TEXT, retail)
            type(self).draw_index_negatives += 1
            memory = guest.fixture(count=0, category=0xB7)
            a, b = (guest.TickOracle(w, memory, phase).run() for w in (self.retail, self.words))
            self.assertTrue(homes.observation(a) == homes.observation(b))
            for slot in (0x84, 0x60, 0x5C):
                address = guest.STACK + phase - 288 + slot
                self.assertFalse(any(s[0] == address for s in a.stores))
                self.assertTrue(any(s[0] == address for s in b.stores))

    def test_changed_words_bindings_linked_fields_and_recipe_are_rejected(self):
        bad = bytearray(self.raw)
        bad[0] ^= 1
        with self.assertRaisesRegex(ValueError, 'source words'):
            source.normalize(bytes(bad), self.bindings)
        bad_bindings = copy.deepcopy(self.bindings)
        at = next(iter(bad_bindings))
        bad_bindings[at] = [(bad_bindings[at][0][0], 'wrong_symbol')]
        with self.assertRaisesRegex(ValueError, 'source bindings'):
            source.normalize(self.raw, bad_bindings)
        bad_words = list(self.before)
        bad_words[1] ^= 1
        with self.assertRaisesRegex(ValueError, 'outside its binding fields'):
            source.apply_linked(bad_words, self.raw, self.bindings)
        bad_slots = dict(source.SLOTS)
        bad_slots[0xA4] = 0x88
        with patch.object(source, 'SLOTS', bad_slots):
            with self.assertRaisesRegex(ValueError, 'recipe/output'):
                source.normalize(self.raw, self.bindings)
        order = source.origins()
        original = struct.unpack('>678I', self.raw)
        branch = next(i for i, w in enumerate(original) if source.is_branch(w))
        at = order.index(branch + 1)
        order[at], order[at + 1] = order[at + 1], order[at]
        with patch.object(source, 'origins', return_value=order):
            with self.assertRaisesRegex(ValueError, 'separates a delay slot'):
                source.normalize(self.raw, self.bindings)

    def test_resolved_relocation_fields_follow_their_source_origins(self):
        positions = {item: i for i, item in enumerate(source.origins()) if isinstance(item, int)}
        original = struct.unpack('>678I', self.raw)
        unresolved = struct.unpack('>678I', source.normalize(self.raw, self.bindings)[0])
        for pattern in (0, 0x13579BDF, 0xFFFFFFFF):
            linked, expected = list(original), list(unresolved)
            for offset, entries in self.bindings.items():
                mask = 0
                for kind, _ in entries:
                    self.assertIn(kind, ('R_MIPS_26', 'R_MIPS_HI16', 'R_MIPS_LO16'))
                    mask |= 0x3FFFFFF if kind == 'R_MIPS_26' else 0xFFFF
                i = offset // 4
                linked[i] = linked[i] & ~mask | (pattern ^ offset) & mask
                at = positions[i]
                expected[at] = expected[at] & ~mask | linked[i] & mask
            self.assertEqual(source.apply_linked(linked, self.raw, self.bindings), expected)


if __name__ == '__main__':
    unittest.main()
