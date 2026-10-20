"""Qualify the real start spill and complete extent, without installing a match."""

import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_node_search_start_home as source
from tools.tests import test_game_route_node_search_captures as previous
from tools.tests import game_route_node_search_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


def signature(model):
    return (model.r[2], model.calls,
        [x for x in model.stores if not guest.private(x[0])], guest.public(model.memory))


class RouteNodeSearchStartHomeTests(previous.RouteNodeSearchCaptureTests):
    test_pure_guarded_five_field_mapping_and_immutable_object = None
    test_selected_cost_closes_but_start_argument_home_remains_open = None
    test_same_public_read_footprints_but_known_schedule_boundary = None

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.values = source.core.freeze(cls.root, cls.output)
        cls.corpus, cls.code, cls.rows = list(guest.cases()), {}, {}
        _, cls.code[False], cls.rows[False] = source.core.compile_candidate(
            cls.root, cls.output, 'selected-False', source.SELECTED, False)
        cls.raw_obj, cls.raw_words, cls.code[True], cls.report = source.qualify(cls.root, cls.output)
        cls.rows[True] = json.loads((cls.output / 'selected-True.json').read_text())
        raw, bindings = source.core.payload(cls.raw_obj)
        cls.old_capture = list(cls.raw_words)
        for i in source.prior.SLOT_WORDS:
            cls.old_capture[i] = cls.old_capture[i] & 0xFFFF0000 | 0x60
        cls.retail = list(struct.unpack_from('>539I', cls.values['conker/conker.us.bin'], source.ROM))
        _, cls.predecessor, _ = source.core.compile_candidate(
            cls.root, cls.output, 'predecessor', source.prior.prior.SELECTED, True)
        cls.completed, cls.native_count, cls.alias_pairs, cls.alias_negatives = 0, 0, 0, 0
        cls.footprints, cls.native_loop_negatives, cls.coverage = 0, 0, set()
        cls.closed_captures, cls.capture_negatives = 0, 0
        cls.word_negatives, cls.binding_negatives, cls.linked_negatives = 0, 0, 0
        cls.start_aliases, cls.start_negatives, cls.cost_aliases, cls.early_aliases = 0, 0, 0, 0
        cls.start_histories = 0

    @classmethod
    def tearDownClass(cls):
        row = dict(cls.report, candidates=cls.rows, fixture_phases=cls.completed,
            native_fixtures=cls.native_count, public_read_footprint_cases=cls.footprints,
            existing_live_home_aliases=cls.alias_pairs, old_save_negatives=cls.alias_negatives,
            capture_aliases_closed=cls.closed_captures, effective_old_capture_negatives=cls.capture_negatives,
            native_loop_negatives=cls.native_loop_negatives, stale_word_negatives=cls.word_negatives,
            stale_binding_negatives=cls.binding_negatives, stale_linked_negatives=cls.linked_negatives,
            start_home_aliases_closed=cls.start_aliases, effective_old_start_negatives=cls.start_negatives,
            selected_cost_aliases_closed=cls.cost_aliases, early_start_overwrite_cases=cls.early_aliases,
            exact_start_home_histories=cls.start_histories,
            exact_complete_final_memory_cases=cls.start_histories,
            retail_words_visited=len(cls.coverage),
            unvisited_retail_offsets=[hex(i * 4) for i in sorted(set(range(539)) - cls.coverage)],
            ordered_reads_exact=True, literal_private_state_exact=False)
        (cls.output / 'test-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        print('route-search start-home qualification:', row)

    def test_complete_owner_profiles_and_predecessor_pins(self):
        loop = previous.previous
        with patch.object(loop.source, 'SELECTED', source.SELECTED):
            loop.RouteNodeSearchLoopTests.test_complete_owner_profiles_and_predecessor_pins(self)
        owner = self.output / 'after-True.o'
        raw, bindings = source.core.payload(owner)
        self.assertEqual((raw, bindings), source.core.payload(self.raw_obj))
        image, functions = source.core.link_owner(self.root, self.output, owner, source.core.OWNER)
        words = struct.unpack_from('>535I', image, functions[source.FUNCTION]['value'])
        self.assertEqual(source.apply_linked(words, raw, bindings), self.code[True])

    def test_pure_source_origins_branch_delay_and_binding_guards(self):
        raw, bindings = source.core.payload(self.raw_obj)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Normalizer read a file')):
            normalized, moved = source.normalize(raw, bindings)
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), source.NORMALIZED_SHA)
        words = struct.unpack('>539I', normalized)
        self.assertEqual((len(words), (-words[0]) & 65535), (539, 1536))
        order = source.origins()
        positions = {item: i for i, item in enumerate(order) if isinstance(item, int)}
        targets = {i: positions[i] - (i in source.INSERT_BEFORE) for i in range(535)}
        targets[535] = 539
        self.assertEqual(sorted(i for i in order if isinstance(i, int)), list(range(535)))
        self.assertEqual(order[152:155], [151, 152, 150])
        self.assertEqual(sum(map(len, moved.values())), 14)
        before = struct.unpack('>535I', raw)
        for i, word in enumerate(before):
            if source.is_branch(word):
                target = i + 1 + struct.unpack('>h', struct.pack('>H', word & 65535))[0]
                actual = positions[i] + 1 + struct.unpack('>h', struct.pack('>H', words[positions[i]] & 65535))[0]
                self.assertEqual(actual, targets[target])
                self.assertEqual(positions[i + 1], positions[i] + 1)
            if i * 4 in bindings:
                self.assertEqual(moved[positions[i] * 4], bindings[i * 4])
        self.assertEqual([(i, w) for i, w in enumerate(words)
            if w >> 26 in source.prior.MEMORY and w >> 21 & 31 == 29 and w & 65535 == 0x600],
            [(95, 0xAFBE0600), (146, 0x8FBE0600), (309, 0x8FBE0600), (337, 0x8FBE0600)])
        for i in range(535):
            stale = bytearray(raw)
            stale[i * 4 + 3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(stale), bindings)
            type(self).word_negatives += 1
            stale = list(self.raw_words)
            stale[i] ^= 0x04000000
            with self.assertRaises(ValueError):
                source.apply_linked(stale, raw, bindings)
            type(self).linked_negatives += 1
        for at, rows in bindings.items():
            for j in range(len(rows)):
                stale = copy.deepcopy(bindings)
                kind, name = stale[at][j]
                stale[at][j] = kind, name + '_stale'
                with self.assertRaises(ValueError):
                    source.normalize(raw, stale)
                type(self).binding_negatives += 1

    def test_complete_memory_and_start_home_read_store_histories(self):
        reports = []
        for case in self.corpus:
            for phase in (0, 8):
                models = [guest.SearchOracle(code, guest.fixture(case), case, phase, entry).run()
                    for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000))]
                home = guest.STACK + phase
                stores = [[x for x in m.stores if x[0] == home] for m in models]
                reads = [[x for x in m.reads if x[0] == home] for m in models]
                self.assertEqual(stores[0], stores[1], (case, phase, 'start stores'))
                self.assertEqual(reads[0], reads[1], (case, phase, 'start reads'))
                self.assertEqual(models[0].memory, models[1].memory, (case, phase, 'complete memory'))
                type(self).start_histories += 1
                reports.append(dict(case=repr(case), phase=phase, stores=stores[0], reads=reads[0]))
        (self.output / 'start-home-histories.json').write_text(json.dumps(reports, indent=2) + '\n')

    def test_ordered_public_reads_close_with_effective_old_schedule(self):
        for case in self.corpus:
            models = [guest.SearchOracle(code, guest.fixture(case), case, 0, entry).run()
                for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000))]
            reads = [[x for x in m.reads if not guest.private(x[0])] for m in models]
            self.assertEqual(reads[0], reads[1], case)
            type(self).footprints += 1
        case = guest.Case()
        models = [guest.SearchOracle(code, guest.fixture(case), case, 0, entry).run()
            for code, entry in ((self.retail, source.ENTRY), (self.old_capture, 0x18000000))]
        reads = [[x for x in m.reads if not guest.private(x[0])] for m in models]
        self.assertNotEqual(reads[0], reads[1], 'Old schedule is not an effective negative')
        self.assertEqual(sorted(reads[0]), sorted(reads[1]))
        at = next(i for i, (a, b) in enumerate(zip(*reads)) if a != b)
        (self.output / 'old-read-schedule-negative.json').write_text(json.dumps(dict(
            effective=True, index=at, retail=reads[0][at], old_source=reads[1][at]), indent=2) + '\n')

    def test_start_and_cost_aliases_close_with_effective_old_start_control(self):
        reports = []
        for phase in (0, 8):
            for kind, occurrence, offset, value in (('early-start', 1, 0x600, 1),
                    ('start-home', 2, 0x600, 1), ('selected-cost', 2, 0x290, 1000000)):
                case = guest.Case()
                memory = guest.fixture(case)
                home = guest.STACK + phase - 1536 + offset

                class ReadAlias(guest.SearchOracle):
                    def __init__(self, *args, **kwargs):
                        self.armed, self.fired, self.seen = False, False, 0
                        super().__init__(*args, **kwargs)
                        self.armed = True

                    def get(self, address, size):
                        result = super().get(address, size)
                        if self.armed and (address, size) == (guest.GOALS, 1):
                            self.seen += 1
                            if self.seen == occurrence:
                                self.put(home, value, 4)
                                self.fired = True
                        return result

                baseline = guest.SearchOracle(self.retail, memory, case, phase).run()
                models = [ReadAlias(code, memory, case, phase, entry).run()
                    for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000),
                                       (self.old_capture, 0x18000000))]
                for model in models:
                    self.assertTrue(model.fired, 'Requested start/cost alias did not fire')
                    self.assertIn((home, 4, value), model.stores)
                self.assertEqual(signature(models[0]), signature(models[1]))
                if kind == 'early-start':
                    self.assertEqual(signature(models[0]), signature(baseline))
                    self.assertEqual([x for x in models[1].stores if x[0] == home],
                                     [(home, 4, 1), (home, 4, 0)])
                    type(self).early_aliases += 1
                else:
                    self.assertNotEqual(signature(models[0]), signature(baseline))
                    if kind == 'start-home':
                        self.assertEqual((models[0].r[2], models[1].r[2], models[2].r[2]), (3, 3, 1))
                        self.assertEqual(signature(models[2]), signature(baseline))
                        type(self).start_aliases += 1
                        type(self).start_negatives += 1
                    else:
                        self.assertEqual((models[0].r[2], models[1].r[2]), (2, 2))
                        type(self).cost_aliases += 1
                reports.append(dict(kind=kind, phase=phase, fired=True,
                    retail_result=models[0].r[2], normalized_result=models[1].r[2],
                    old_result=models[2].r[2], public_signatures_equal=True))
        (self.output / 'closed-start-and-cost-aliases.json').write_text(json.dumps(reports, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
