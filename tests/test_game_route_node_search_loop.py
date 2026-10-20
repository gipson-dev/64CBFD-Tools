"""Sentinel/coordinate recovery with complete native, owner and read footprints."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_node_search_loop as source
from tools.tests import test_game_route_node_search_candidates as previous
from tools.tests import game_route_node_search_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


class RouteNodeSearchLoopTests(unittest.TestCase):
    compare = previous.RouteNodeSearchCandidateTests.compare
    test_complete_graphs_boundaries_and_mutable_helpers = previous.RouteNodeSearchCandidateTests.test_complete_graphs_boundaries_and_mutable_helpers
    test_independent_reference_discriminates_retail_quirks = previous.RouteNodeSearchCandidateTests.test_independent_reference_discriminates_retail_quirks
    test_added_guest_sqrt_and_xor_instructions = previous.RouteNodeSearchCandidateTests.test_added_guest_sqrt_and_xor_instructions

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.values = source.prior.freeze(cls.root, cls.output)
        cls.corpus, cls.rows, cls.code = list(guest.cases()), {}, {}
        for normal in (False, True):
            _, cls.code[normal], cls.rows[normal] = source.compile_candidate(
                cls.root, cls.output, 'selected-' + str(normal), normal=normal)
        cls.retail = list(struct.unpack_from('>539I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.completed, cls.native_count, cls.alias_pairs, cls.alias_negatives = 0, 0, 0, 0
        cls.footprints, cls.native_loop_negatives, cls.coverage = 0, 0, set()
        cls.open_capture_aliases = 0

    @classmethod
    def tearDownClass(cls):
        report = dict(candidates=cls.rows, fixture_phases=cls.completed, native_fixtures=cls.native_count,
            live_home_alias_pairs=cls.alias_pairs, old_save_negatives=cls.alias_negatives,
            public_read_footprint_cases=cls.footprints, native_loop_negatives=cls.native_loop_negatives,
            demonstrated_open_capture_aliases=cls.open_capture_aliases,
            retail_words_visited=len(cls.coverage),
            unvisited_retail_offsets=[hex(i * 4) for i in sorted(set(range(539)) - cls.coverage)],
            ordered_reads_exact=False, literal_private_state_exact=False, installed=False, matching_credit=0)
        (cls.output / 'test-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
        print('route-search loop qualification:', report)

    def test_complete_native32_source_ubsan_and_loop_negatives(self):
        with patch.object(previous.source, 'SELECTED', source.SELECTED):
            previous.RouteNodeSearchCandidateTests.test_native32_complete_source_and_effective_compiled_negatives(self)
        unit = guest.native_harness(source.SELECTED, self.corpus)
        controls = {
            'wrong-loop-sentinel': source.SELECTED.replace(
                '    } while (selected != 0xFF);', '    } while (selected == 0xFF);'),
            'lost-frontier-append': source.SELECTED.replace(
                'if (selected == frontierCount)', 'if (0 == frontierCount)'),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            path = self.output / ('native-negative-' + name + '.c')
            path.write_text(unit.replace(source.SELECTED, body))
            exe = path.with_suffix('')
            built = subprocess.run([*previous.native_command('-O2'), '-fno-strict-aliasing',
                                    str(path), '-o', str(exe)], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertIn(subprocess.run([str(exe)], capture_output=True, timeout=15).returncode,
                          (21, 22, 23, 24, 25), name)
            type(self).native_loop_negatives += 1

    def test_complete_owner_profiles_and_predecessor_pins(self):
        before = self.values[source.prior.SOURCE].decode()
        after = source.prior.recovered_owner(before, source.SELECTED)
        reports = []
        for normal in (False, True):
            a, da = source.prior.compile_profile(self.root, self.output, before, 'before-' + str(normal), normal)
            b, db = source.prior.compile_profile(self.root, self.output, after, 'after-' + str(normal), normal)
            self.assertEqual((da, db), ('', ''))
            self.assertEqual(previous.same_functions(a, b, (source.FUNCTION,)), 72)
            self.assertEqual(previous.normalized_pools(a), previous.normalized_pools(b))
            self.assertEqual(source.prior.payload(b), source.prior.payload(
                self.output / ('selected-' + str(normal) + '.o')))
            reports.append(dict(normal=normal, preserved_neighbors=72, pools_unchanged=True,
                                isolated_words_and_bindings_equal=True))
        for name, value in self.values.items():
            self.assertEqual((self.root / name).read_bytes(), value, name)
        (self.output / 'owner-receipt.json').write_text(json.dumps(reports, indent=2) + '\n')

    def test_same_public_read_footprints_but_known_schedule_boundary(self):
        first = None
        for case in self.corpus:
            models = [guest.SearchOracle(code, guest.fixture(case), case, 0, entry).run()
                      for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000))]
            reads = [[x for x in m.reads if not guest.private(x[0])] for m in models]
            self.assertEqual(Counter(reads[0]), Counter(reads[1]), case)
            if first is None and reads[0] != reads[1]:
                i = next(i for i, (a, b) in enumerate(zip(*reads)) if a != b)
                first = dict(case=repr(case), index=i, retail=reads[0][i], source=reads[1][i])
            type(self).footprints += 1
        self.assertIsNotNone(first, 'Expected independent initial-coordinate schedule boundary disappeared')
        (self.output / 'read-order-boundary.json').write_text(json.dumps(first, indent=2) + '\n')

    def test_extent_homes_and_fired_aliases_with_old_save_negatives(self):
        row = self.rows[True]
        self.assertEqual((row['words'], row['frame'], row['raw_SHA256']),
                         (535, 1536, source.NORMAL_SHA))
        raw, _ = source.prior.payload(self.output / 'selected-True.o')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), source.NORMAL_SHA)
        words = struct.unpack('>535I', raw)
        homes = {w & 65535 for w in words if w >> 26 == 9 and w >> 21 & 31 == 29}
        self.assertTrue({0x7C, 0xBC, 0xFC, 0x1C4, 0x28C} <= homes)
        self.assertEqual([w & 65535 for w in words if w >> 26 == 57 and w >> 21 & 31 == 29
                          and w >> 16 & 31 == 2], [0x5D0])
        old_body = source.SELECTED.replace('    f32 distance;', '    s32 proposed;', 1).replace(
            '    f32 dz;\n    s32 proposed;', '    f32 dz;\n    f32 distance;', 1)
        self.assertNotEqual(old_body, source.SELECTED)
        _, old_words, _ = source.compile_candidate(self.root, self.output, 'old-distance-home', old_body)
        result = lambda m: (m.r[2], m.calls, [x for x in m.stores if not guest.private(x[0])], guest.public(m.memory))
        for phase in (0, 8):
            ordinary = guest.Case()
            baseline = guest.SearchOracle(self.retail, guest.fixture(ordinary), ordinary, phase).run()
            for target, offset, value, size in ((guest.LOOKUP, 0xBD, 4, 1),
                    (guest.LENGTH, 0x7E, 1, 1), (guest.LENGTH, 0x5D0, guest.bits(10.5), 4)):
                address = guest.STACK + phase - 1536 + offset
                case = guest.Case(actions=((target, 0, address, value, size),))
                a = guest.SearchOracle(self.retail, guest.fixture(case), case, phase).run()
                b = guest.SearchOracle(self.code[True], guest.fixture(case), case, phase, 0x18000000).run()
                for model in (a, b):
                    self.assertIn((address, size, value), model.stores, 'Alias mutation did not fire')
                self.assertEqual(result(a), result(b))
                self.assertNotEqual(result(a), result(baseline))
                type(self).alias_pairs += 1
                if offset == 0x5D0:
                    old = guest.SearchOracle(old_words, guest.fixture(case), case, phase, 0x18000000).run()
                    self.assertIn((address, size, value), old.stores, 'Negative mutation did not fire')
                    self.assertNotEqual(result(a), result(old))
                    type(self).alias_negatives += 1

    def test_table_home_and_avoid_argument_captures_remain_demonstrably_open(self):
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
                a = CaptureAlias(self.retail, memory, case, phase).run()
                b = CaptureAlias(self.code[True], memory, case, phase, 0x18000000).run()
                for model in (a, b):
                    self.assertTrue(model.fired, 'Requested capture alias did not fire')
                    self.assertIn((home, 4, value), model.stores)
                self.assertNotEqual(signature(a), signature(baseline), 'Retail alias has no effect')
                self.assertEqual(signature(b), signature(baseline), 'Source capture boundary changed')
                self.assertNotEqual(signature(a), signature(b), 'Expected open capture boundary disappeared')
                reports.append(dict(kind=kind, phase=phase, home=hex(home), fired=True,
                    retail_calls=a.calls, source_calls=b.calls, still_open=True))
                type(self).open_capture_aliases += 1
        (self.output / 'open-capture-aliases.json').write_text(json.dumps(reports, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
