"""Capture closures and stale guards; complete literal/integration gates stay open."""

import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_node_search_captures as source
from tools.tests import test_game_route_node_search_loop as previous
from tools.tests import game_route_node_search_oracle as guest
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]


class RouteNodeSearchCaptureTests(previous.RouteNodeSearchLoopTests):
    test_table_home_and_avoid_argument_captures_remain_demonstrably_open = None

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.values = source.core.freeze(cls.root, cls.output)
        cls.corpus, cls.code, cls.rows = list(guest.cases()), {}, {}
        _, cls.code[False], cls.rows[False] = source.core.compile_candidate(
            cls.root, cls.output, 'selected-False', source.SELECTED, False)
        cls.raw_obj, cls.raw_words, cls.normalized_obj, cls.code[True], cls.report = source.qualify(
            cls.root, cls.output)
        cls.rows[True] = json.loads((cls.output / 'selected-True.json').read_text())
        cls.retail = list(struct.unpack_from('>539I', cls.values['conker/conker.us.bin'], source.ROM))
        _, cls.predecessor, _ = source.core.compile_candidate(
            cls.root, cls.output, 'predecessor', source.prior.SELECTED, True)
        cls.completed, cls.native_count, cls.alias_pairs, cls.alias_negatives = 0, 0, 0, 0
        cls.footprints, cls.native_loop_negatives, cls.coverage = 0, 0, set()
        cls.closed_captures, cls.capture_negatives, cls.word_negatives, cls.binding_negatives = 0, 0, 0, 0

    @classmethod
    def tearDownClass(cls):
        row = dict(cls.report, candidates=cls.rows, fixture_phases=cls.completed,
            native_fixtures=cls.native_count, public_read_footprint_cases=cls.footprints,
            existing_live_home_aliases=cls.alias_pairs, old_save_negatives=cls.alias_negatives,
            capture_aliases_closed=cls.closed_captures, effective_old_capture_negatives=cls.capture_negatives,
            native_loop_negatives=cls.native_loop_negatives, stale_word_negatives=cls.word_negatives,
            stale_binding_negatives=cls.binding_negatives, retail_words_visited=len(cls.coverage),
            unvisited_retail_offsets=[hex(i * 4) for i in sorted(set(range(539)) - cls.coverage)],
            ordered_reads_exact=False, literal_private_state_exact=False)
        (cls.output / 'test-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        print('route-search capture qualification:', row)

    def test_complete_native32_source_ubsan_and_loop_negatives(self):
        with patch.object(source.prior, 'SELECTED', source.SELECTED):
            super().test_complete_native32_source_ubsan_and_loop_negatives()

    def test_complete_owner_profiles_and_predecessor_pins(self):
        with patch.object(source.prior, 'SELECTED', source.SELECTED):
            super().test_complete_owner_profiles_and_predecessor_pins()
        before = self.output / 'after-True.o'
        after = source.normalize_object(before, self.output / 'owner-normalized.o')
        self.assertEqual(previous.previous.same_functions(before, after, (source.FUNCTION,)), 72)
        self.assertEqual(previous.previous.normalized_pools(before), previous.previous.normalized_pools(after))
        self.assertEqual(source.core.payload(after), source.core.payload(self.normalized_obj))

    def test_extent_homes_and_fired_aliases_with_old_save_negatives(self):
        raw, bindings = source.core.payload(self.raw_obj)
        normalized, moved = source.normalize(raw, bindings)
        self.assertEqual((len(normalized) // 4, (-self.code[True][0]) & 65535), (535, 1536))
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), source.NORMALIZED_SHA)
        self.assertEqual(moved, bindings)
        words = struct.unpack('>535I', normalized)
        homes = {w & 65535 for w in words if w >> 26 == 9 and w >> 21 & 31 == 29}
        self.assertTrue({0x7C, 0xBC, 0xFC, 0x1C4, 0x28C} <= homes)
        self.assertEqual([w & 65535 for w in words if w >> 26 == 57 and w >> 21 & 31 == 29
                          and w >> 16 & 31 == 2], [0x5D0])
        old_body = source.SELECTED.replace('    f32 distance;', '    s32 proposed;', 1).replace(
            '    f32 dz;\n    s32 proposed;', '    f32 dz;\n    f32 distance;', 1)
        self.assertNotEqual(old_body, source.SELECTED)
        _, old_words, _ = source.core.compile_candidate(
            self.root, self.output, 'old-distance-home', old_body, True)
        result = lambda m: (m.r[2], m.calls, [x for x in m.stores if not guest.private(x[0])], guest.public(m.memory))
        for phase in (0, 8):
            ordinary = guest.Case()
            baseline = guest.SearchOracle(self.retail, guest.fixture(ordinary), ordinary, phase).run()
            for target, offset, value, size in ((guest.LOOKUP, 0xBD, 4, 1),
                    (guest.LENGTH, 0x7E, 1, 1), (guest.LENGTH, 0x5D0, guest.bits(10.5), 4)):
                address = guest.STACK + phase - 1536 + offset
                case = guest.Case(actions=((target, 0, address, value, size),))
                models = [guest.SearchOracle(code, guest.fixture(case), case, phase, entry).run()
                          for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000))]
                for model in models:
                    self.assertIn((address, size, value), model.stores, 'Requested home alias did not fire')
                self.assertEqual(result(models[0]), result(models[1]))
                self.assertNotEqual(result(models[0]), result(baseline))
                type(self).alias_pairs += 1
                if offset == 0x5D0:
                    old = guest.SearchOracle(old_words, guest.fixture(case), case, phase, 0x18000000).run()
                    self.assertIn((address, size, value), old.stores, 'Old-home mutation did not fire')
                    self.assertNotEqual(result(old), result(models[0]))
                    type(self).alias_negatives += 1

    def test_table_home_and_avoid_argument_captures_are_closed(self):
        reports = []
        case = guest.Case(avoid=(255,))
        signature = lambda m: (m.r[2], m.calls,
            [x for x in m.stores if not guest.private(x[0])], guest.public(m.memory))
        for phase in (0, 8):
            for kind in ('table-home', 'avoid-argument'):
                memory = guest.fixture(case)
                if kind == 'table-home':
                    for i, value in enumerate((5, 255, 255, 255, 255)):
                        guest.put(memory, guest.ALT_BANK + 16 + 9 + i, value, 1)
                    home, value = guest.STACK + phase - 1536 + 0x60, guest.ALT_BANK
                else:
                    guest.put(memory, guest.GOALS + 64, 3, 1)
                    home, value = guest.STACK + phase + 0x10, guest.GOALS + 64

                class CaptureAlias(guest.SearchOracle):
                    def __init__(self, *args, **kwargs):
                        self.armed, self.fired, self.goal_reads = False, False, 0
                        super().__init__(*args, **kwargs)
                        self.armed = True

                    def get(self, address, size):
                        result = super().get(address, size)
                        if self.armed and (address, size) == (guest.GOALS, 1):
                            self.goal_reads += 1
                            if self.goal_reads == 2:
                                self.put(home, value, 4)
                                self.fired = True
                        return result

                baseline = guest.SearchOracle(self.retail, memory, case, phase).run()
                models = [CaptureAlias(code, memory, case, phase, entry).run()
                          for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000),
                                             (self.raw_words, 0x18000000), (self.predecessor, 0x18000000))]
                for model in models:
                    self.assertTrue(model.fired, 'Capture alias gate did not fire')
                    self.assertIn((home, 4, value), model.stores)
                self.assertNotEqual(signature(models[0]), signature(baseline), 'Retail alias has no effect')
                self.assertEqual(signature(models[0]), signature(models[1]))
                if kind == 'table-home':
                    self.assertEqual(signature(models[2]), signature(baseline), 'Raw table control changed')
                    self.assertNotEqual(signature(models[0]), signature(models[2]))
                else:
                    self.assertEqual(signature(models[0]), signature(models[2]), 'Typed C does not close avoid capture')
                    self.assertEqual(signature(models[3]), signature(baseline), 'Old avoid control changed')
                    self.assertNotEqual(signature(models[0]), signature(models[3]))
                type(self).closed_captures += 1
                type(self).capture_negatives += 1
                reports.append(dict(kind=kind, phase=phase, fired=True, closed=True,
                    retail_calls=models[0].calls, normalized_calls=models[1].calls,
                    raw_C_closes=(kind == 'avoid-argument')))
        (self.output / 'closed-capture-aliases.json').write_text(json.dumps(reports, indent=2) + '\n')

    def test_pure_guarded_five_field_mapping_and_immutable_object(self):
        raw, bindings = source.core.payload(self.raw_obj)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Normalizer read a file')):
            normalized, moved = source.normalize(raw, bindings)
        self.assertEqual(moved, bindings)
        self.assertEqual(sum(map(len, bindings.values())), 14)
        a, b = struct.unpack('>535I', raw), struct.unpack('>535I', normalized)
        self.assertEqual({i for i, (x, y) in enumerate(zip(a, b)) if x != y}, set(source.SLOT_WORDS))
        for i in source.SLOT_WORDS:
            self.assertEqual((a[i] >> 16, b[i] >> 16, a[i] & 65535, b[i] & 65535),
                             (a[i] >> 16, a[i] >> 16, 0x5FC, 0x60))
        for i in range(535):
            bad = bytearray(raw)
            bad[i * 4 + 3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), bindings)
            type(self).word_negatives += 1
        for at, rows in bindings.items():
            for j in range(len(rows)):
                bad = copy.deepcopy(bindings)
                kind, name = bad[at][j]
                bad[at][j] = kind, name + '_stale'
                with self.assertRaises(ValueError):
                    source.normalize(raw, bad)
                type(self).binding_negatives += 1
        original, changed = self.raw_obj.read_bytes(), self.normalized_obj.read_bytes()
        header = source.ELF_HEADER.unpack_from(original)
        _, functions, _ = parse_object(self.raw_obj)
        section = source.SECTION_HEADER.unpack_from(
            original, header[6] + functions[source.FUNCTION]['section'] * header[11])
        allowed = {section[4] + i * 4 + j for i in source.SLOT_WORDS for j in range(4)}
        self.assertEqual(len(original), len(changed))
        self.assertTrue(all(x == y or i in allowed for i, (x, y) in enumerate(zip(original, changed))))
        self.assertEqual(parse_object(self.raw_obj)[1:], parse_object(self.normalized_obj)[1:])


if __name__ == '__main__':
    unittest.main()
