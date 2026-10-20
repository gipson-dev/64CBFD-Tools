"""Complete route-search behavioral qualification; installation stays gated."""

import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_route_node_search_candidates as source
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests import game_route_node_search_oracle as guest
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command


ROOT = Path(__file__).resolve().parents[2]


class RouteNodeSearchCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.values = source.freeze(cls.root, cls.output)
        cls.corpus = list(guest.cases())
        cls.code, cls.rows = {}, {}
        for normal in (False, True):
            _, cls.code[normal], cls.rows[normal] = source.compile_candidate(
                cls.root, cls.output, 'selected-' + str(normal), normal=normal)
        cls.retail = list(struct.unpack_from('>539I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.completed, cls.native_count, cls.alias_pairs, cls.alias_negatives, cls.coverage = 0, 0, 0, 0, set()

    @classmethod
    def tearDownClass(cls):
        row = dict(candidates=cls.rows, completed_fixture_phases=cls.completed,
                   native_fixtures=cls.native_count, retail_words_visited=len(cls.coverage),
                   unvisited_retail_offsets=[hex(i * 4) for i in sorted(set(range(539)) - cls.coverage)],
                   effective_live_home_alias_pairs=cls.alias_pairs,
                   effective_old_distance_home_negatives=cls.alias_negatives,
                   retail_words=539, installed=False, matching_credit=0)
        (cls.output / 'test-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        print('route-search qualification:', row)

    def compare(self, case, phase):
        memory = guest.fixture(case)
        answer, final, calls, stores, _ = guest.reference(memory, case)
        for target, occurrence, *_ in case.actions:
            self.assertGreater(sum(c[0] == target for c in calls), occurrence, 'Mutation gate did not fire')
        # The oversized normal candidate overlaps LENGTH at its retail address.
        # A disjoint same-JAL-region base preserves branches and external calls.
        for words in (self.retail, self.code[False], self.code[True]):
            entry = source.ENTRY if words is self.retail else 0x18000000
            self.assertFalse(any(w >> 26 == 2 for w in words), 'Absolute internal jump needs rebasing')
            model = guest.SearchOracle(words, memory, case, phase, entry).run()
            self.assertEqual(model.r[2], answer, (case, phase, 'answer'))
            self.assertEqual(model.calls, calls, (case, phase, 'calls'))
            public_stores = [s for s in model.stores if not guest.private(s[0])]
            self.assertEqual(public_stores, stores, (case, phase, 'stores'))
            self.assertEqual(guest.public(model.memory), guest.public(final), (case, phase, 'memory'))
            if words is self.retail:
                self.coverage.update((pc - source.ENTRY) // 4 for pc in model.visits
                                     if source.ENTRY <= pc < source.ENTRY + 539 * 4)
        type(self).completed += 1

    def test_complete_graphs_boundaries_and_mutable_helpers(self):
        for case in self.corpus:
            for phase in (0, 8):
                with self.subTest(case=case, phase=phase):
                    self.compare(case, phase)

    def test_independent_reference_discriminates_retail_quirks(self):
        half_case = next(c for c in self.corpus if len(c.coords) == 3 and c.coords[1] == (32000, 32000, 0))
        self.assertEqual(guest.reference(guest.fixture(half_case), half_case)[0], 1)
        tie_case = next(c for c in self.corpus if len(c.coords) == 3 and c.coords[1] == (100, 0, 0))
        self.assertEqual(guest.reference(guest.fixture(tie_case), tie_case)[0], 1)
        for alias, expected in ((1, 255), (2, 0)):
            case = next(c for c in self.corpus if c.alias == alias)
            self.assertEqual(guest.reference(guest.fixture(case), case)[0], expected)

    def test_added_guest_sqrt_and_xor_instructions(self):
        case = guest.Case()
        model = guest.SearchOracle(self.retail, guest.fixture(case), case)
        for value, expected in ((0.0, 0.0), (4.0, 2.0), (2.25, 1.5)):
            model.f[4] = guest.bits(value)
            model.execute(0x46002004)
            self.assertEqual(model.f[0], guest.bits(expected))
        model.r[4], model.r[5] = 0xA5A50000, 0x00005A5A
        model.execute(0x00851026)
        self.assertEqual(model.r[2], 0xA5A55A5A)
        model.execute(0x00850026)
        self.assertEqual(model.r[0], 0)

    def test_selected_frame_array_homes_and_effective_live_aliases(self):
        row = self.rows[True]
        self.assertEqual((row['words'], row['frame'], row['raw_SHA256']),
                         (545, 1536, source.SELECTED_NORMAL_SHA))
        raw, _ = source.payload(self.output / 'selected-True.o')
        words = struct.unpack('>%dI' % (len(raw) // 4), raw)
        addresses = {w & 65535 for w in words if w >> 26 == 9 and w >> 21 & 31 == 29}
        self.assertTrue({0x7C, 0xBC, 0xFC, 0x1C4, 0x28C} <= addresses)
        f2_stores = [(i, w & 65535) for i, w in enumerate(words)
                     if w >> 26 == 57 and w >> 21 & 31 == 29 and w >> 16 & 31 == 2]
        self.assertEqual(f2_stores, [(515, 0x5D0)])
        old_body = source.SELECTED.replace('    f32 distance;', '    s32 proposed;', 1).replace(
            '    f32 dz;\n    s32 proposed;', '    f32 dz;\n    f32 distance;', 1)
        self.assertNotEqual(old_body, source.SELECTED)
        _, old_words, _ = source.compile_candidate(self.root, self.output, 'old-distance-home', old_body, normal=True)
        for phase in (0, 8):
            for target, offset, value, size in ((guest.LOOKUP, 0xBC + 1, 4, 1),
                    (guest.LENGTH, 0x7C + 2, 1, 1), (guest.LENGTH, 0x5D0, guest.bits(10.5), 4)):
                at = guest.STACK + phase - 1536 + offset
                case = guest.Case(actions=((target, 0, at, value, size),))
                models = [guest.SearchOracle(code, guest.fixture(case), case, phase, entry).run()
                          for code, entry in ((self.retail, source.ENTRY), (self.code[True], 0x18000000))]
                for model in models:
                    self.assertGreater(model.occurrences.get(target, 0), 0, 'Alias mutation did not fire')
                    self.assertIn((at, size, value), model.stores)
                result = lambda m: (m.r[2], m.calls,
                    [s for s in m.stores if not guest.private(s[0])], guest.public(m.memory))
                self.assertEqual(result(models[0]), result(models[1]))
                ordinary = guest.Case()
                baseline = guest.SearchOracle(self.retail, guest.fixture(ordinary), ordinary, phase).run()
                self.assertNotEqual(result(models[0]), result(baseline), 'Alias has no observable effect')
                type(self).alias_pairs += 1
                if offset == 0x5D0:
                    old_model = guest.SearchOracle(old_words, guest.fixture(case), case, phase, 0x18000000).run()
                    self.assertIn((at, size, value), old_model.stores, 'Negative mutation did not fire')
                    self.assertNotEqual(result(old_model), result(models[0]))
                    type(self).alias_negatives += 1

    def test_native32_complete_source_and_effective_compiled_negatives(self):
        unit = guest.native_harness(source.SELECTED, self.corpus)
        path = self.output / 'native.c'
        path.write_text(unit)
        for opt in ('-O0', '-O2', '-O3'):
            exe = self.output / ('native' + opt)
            build = subprocess.run([*native_command(opt), '-fno-strict-aliasing', str(path), '-o', str(exe)],
                                   cwd=self.root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, (opt, run.stdout, run.stderr))
        type(self).native_count = len(self.corpus)
        controls = {
            'lost-opening-halfword': source.SELECTED.replace('(s16)(s32)sqrtf', '(s32)sqrtf'),
            'last-entry-tie': source.SELECTED.replace('costs[frontier[i]] < minimum', 'costs[frontier[i]] <= minimum'),
            'signed-goal-id': source.SELECTED.replace('start == goals[i]', 'start == (s8)goals[i]'),
        }
        for name, bad in controls.items():
            self.assertNotEqual(bad, source.SELECTED)
            path = self.output / ('negative-' + name + '.c')
            path.write_text(unit.replace(source.SELECTED, bad))
            exe = path.with_suffix('')
            build = subprocess.run([*native_command('-O2'), '-fno-strict-aliasing', str(path), '-o', str(exe)],
                                   cwd=self.root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            self.assertIn(subprocess.run([str(exe)], capture_output=True, timeout=15).returncode,
                          (21, 22, 23, 24, 25), name)
        overflow = self.output / 'overflow.c'
        overflow.write_text('int run(void){volatile int v=0x7FFFFFFF;return v+1;}\n'
            '__attribute__((force_align_arg_pointer)) void _start(void){int v=run();'
            '__asm__ volatile("int $0x80"::"a"(1),"b"(v));__builtin_unreachable();}\n')
        exe = overflow.with_suffix('')
        build = subprocess.run([*native_command('-O2'), str(overflow), '-o', str(exe)],
                               cwd=self.root, capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(subprocess.run([str(exe)], capture_output=True, timeout=5).returncode, -4)

    def test_both_owner_profiles_preserve_other_bodies_and_pools(self):
        before = self.values[source.SOURCE].decode()
        after = source.recovered_owner(before)
        reports = []
        for normal in (False, True):
            a, da = source.compile_profile(self.root, self.output, before, 'before-' + str(normal), normal)
            b, db = source.compile_profile(self.root, self.output, after, 'after-' + str(normal), normal)
            self.assertEqual((da, db), ('', ''))
            self.assertEqual(same_functions(a, b, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(a), normalized_pools(b))
            self.assertEqual(source.payload(b), source.payload(self.output / ('selected-' + str(normal) + '.o')))
            reports.append(dict(normal=normal, preserved_neighbors=72, pools_unchanged=True,
                                isolated_words_and_bindings_equal=True))
        (self.output / 'owner-receipt.json').write_text(json.dumps(reports, indent=2) + '\n')

    def test_production_pins_and_recovery_extent(self):
        self.assertEqual(len(self.retail), 539)
        self.assertEqual((-self.retail[0]) & 65535, 1536)
        for name, before in self.values.items():
            self.assertEqual((self.root / name).read_bytes(), before, name)
        for row in self.rows.values():
            self.assertFalse(row['installed'])
            self.assertEqual(row['matching_credit'], 0)
            self.assertEqual(row['diagnostics'], '')
        self.assertEqual(source.INPUTS[source.SOURCE], hashlib.sha256(self.values[source.SOURCE]).hexdigest())


if __name__ == '__main__':
    unittest.main()
