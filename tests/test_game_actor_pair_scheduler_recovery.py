"""Qualify scheduler semantics without claiming unresolved retail/private layout."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_pair_scheduler_candidates as source
from tools.experiments import game_actor_pair_visibility_integration as integration
from tools.tests import game_actor_pair_scheduler_oracle as guest
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command


def public_stores(model):
    return [row for row in model.stores if not guest.STACK - 0x600 <= row[0] < guest.STACK + 0x100]


class ActorPairSchedulerRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / (source.BUILD + '/recovery')
        cls.values = source.freeze(cls.root, cls.out)
        cls.obj, cls.words, cls.row = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>261I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_complete_shape_and_retained_nonfinite_subtraction(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (256, 208, 241))
        self.assertEqual(self.row['raw_SHA256'], '0486ad7b141288c0bdc1068efb466f4d89f75230388726c11b44d7922af0f9e1')
        self.assertFalse(self.row['diagnostics'])
        self.assertEqual((-self.retail[0]) & 65535, 192)
        self.assertNotEqual(self.words, self.retail)
        subtractions = [w for w in self.words if w >> 26 == 17 and (w >> 21 & 31, w & 63) == (16, 1)]
        self.assertTrue(any(w >> 16 & 31 == w >> 11 & 31 for w in subtractions))
        _, folded, row = source.compile_candidate(self.root, self.out, 'folded-control', source.INITIAL)
        folded_subtractions = [w for w in folded if w >> 26 == 17 and (w >> 21 & 31, w & 63) == (16, 1)]
        self.assertFalse(any(w >> 16 & 31 == w >> 11 & 31 for w in folded_subtractions))
        self.assertEqual((row['words'], row['frame']), (257, 200))
        self.receipts.update(raw_words=256, raw_frame=208, raw_differences=241,
            retail_words=261, retail_frame=192, retained_self_subtraction=True,
            direct_C_self_subtraction_folded_control=True, installed=False)

    def test_02_ordered_public_buffers_calls_and_provider_effects(self):
        completed, coverage, attempts64 = 0, set(), 0
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            result, wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                with self.subTest(case=n, phase=phase):
                    for words in (self.retail, self.words):
                        model = guest.SchedulerModel(words, memory, case, phase).run()
                        self.assertEqual(model.r[2], result)
                        self.assertEqual(model.calls, calls)
                        self.assertEqual(public_stores(model), stores)
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        if words is self.retail:
                            coverage.update(model.visits)
                            attempts64 += 0x1508C950 in model.visits and case.kinds == (0,)
                completed += 1
        self.assertGreater(attempts64, 0)
        self.receipts.update(fixtures=len(self.corpus), completed_retail_raw_pairs=completed,
            retail_words_visited=len(coverage), unvisited_retail_words=[hex(a) for a in sorted(
                set(range(source.ENTRY, source.ENTRY + 1044, 4)) - coverage)],
            full_public_buffers_and_ordered_stores=True, opaque_call_snapshots_and_effects=True)

    def native(self, body, name, opt='-O2'):
        path = self.out / (name + '.c')
        if not hasattr(self, 'native_template'):
            self.native_template = guest.native_harness('SCHEDULER_SOURCE_BODY',
                tuple(case for case in self.corpus if case.count <= 16))
        path.write_text(self.native_template.replace('SCHEDULER_SOURCE_BODY', body))
        exe = path.with_suffix('.elf')
        result = subprocess.run(native_command(opt) + ['-mstackrealign', '-fno-strict-aliasing',
            str(path), '-o', str(exe)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return subprocess.run([str(exe)], capture_output=True, timeout=30).returncode

    def test_03_native32_profiles_and_effective_semantic_negatives(self):
        for opt in ('-O0', '-O2', '-O3'):
            self.assertEqual(self.native(source.SELECTED, 'native' + opt[1:], opt), 0)
        body = source.SELECTED
        controls = {
            'signed-cursors': body.replace('    u8 first;', '    s8 first;').replace('    u8 second;', '    s8 second;'),
            'short-attempt-cap': body.replace('attempts >= 64', 'attempts >= 63'),
            'inclusive-rank-tie': body.replace('cost < costs[2]', 'cost <= costs[2]').replace('cost < displacedCost', 'cost <= displacedCost'),
            'two-ranked-pairs': body.replace('for (i = 0; i < 3; i++) {\n                    candidate', 'for (i = 0; i < 2; i++) {\n                    candidate'),
            'lost-high-mask': body.replace('0x10001u', '1u'),
            'reloaded-group-bank': body.replace('groups[primary] != groups[candidate]',
                '((s32 *)((u8 *)D_800D23B0 + 0xE64))[primary] != ((s32 *)((u8 *)D_800D23B0 + 0xE64))[candidate]').replace(
                    'groups = (s32 *)((u8 *)D_800D23B0 + 0xE64);', 'groups = (s32 *)((u8 *)D_800D23B0 + 0xE64); (void)groups;'),
            'reloaded-sentinel': body.replace('costs[i] = sentinel;', 'costs[i] = D_8009DA68;').replace(
                'sentinel = D_8009DA68;', 'sentinel = D_8009DA68; (void)sentinel;'),
            'wrong-rank-position': body.replace('dz = sameZ - *(f32 *)(actor + 0x1C);',
                'dz = sameZ - *(f32 *)(D_800CC2D0 + candidate * 0x32C + 0x1C);'),
        }
        results = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            code = self.native(changed, 'negative-' + name)
            self.assertNotEqual(code, 0, name)
            results[name] = code
        self.receipts.update(native32_profiles=['O0', 'O2', 'O3'], UBSan=True,
            native_fixtures=sum(case.count <= 16 for case in self.corpus), effective_negatives=results)

    def test_03b_NOR_width_zero_and_fired_private_boundary(self):
        case = guest.Case()
        memory = guest.fixture(case)
        for left, right in ((0, 0), (0xFFFFFFFF, 0), (0x80000000, 1), (0x12345678, 0x87654321)):
            model = guest.SchedulerModel(self.retail, memory, case)
            model.r[8], model.r[9] = left, right
            model.execute(8 << 21 | 9 << 16 | 10 << 11 | 39)
            self.assertEqual(model.r[10], ~(left | right) & 0xFFFFFFFF)
            model.execute(8 << 21 | 9 << 16 | 39)
            self.assertEqual(model.r[0], 0)
        models = []
        for words, frame in ((self.retail, 192), (self.words, 208)):
            model = guest.SchedulerModel(words, memory, case)
            model.fault = 0
            with self.assertRaises(guest.core.AccessFault):
                model.run()
            self.assertEqual(model.accesses, 0)
            self.assertEqual(model.r[29], guest.STACK - frame)
            self.assertEqual(model.requested, ('W', guest.STACK - frame + 0x40, 4))
            models.append(model)
        self.assertNotEqual(models[0].r, models[1].r)
        self.receipts.update(NOR_vectors=4, first_access_cut_fired_for_both=True,
            private_frame_boundary='Retail SP-192 versus raw SP-208 before first S6 save')

    def test_04_both_complete_owner_profiles_preserve_neighbors_and_pools(self):
        same = integration.mixed.candidate.source.neighbor.same_functions
        for name, normal in (('primary', False), ('normal', True)):
            before, diagnostics = source.compile_profile(self.root, self.out,
                self.values[source.SOURCE].decode(), 'before-' + name, normal)
            after, _, row = source.compile_candidate(self.root, self.out, 'after-' + name, normal=normal, whole=True)
            self.assertFalse(diagnostics or row['diagnostics'])
            self.assertEqual(same(before, after, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(before), normalized_pools(after))
            self.assertEqual(source.payload(after), source.payload(self.obj))
        self.receipts.update(unchanged_raw_neighbors_per_profile=72, owner_profiles=2,
            owner_pools_unchanged=True, typed_caller_prototype_preserves_caller=True)

    def test_05_negative_budgets_fire_bounded_call_gates(self):
        count = 0
        for budget in (-1, -2147483648):
            case = guest.Case(primary=0, budget=budget)
            memory = guest.fixture(case)
            models = []
            for words in (self.retail, self.words):
                model = guest.SchedulerModel(words, memory, case, stop_calls=3)
                with self.assertRaises(guest.CallStop):
                    model.run()
                self.assertEqual(len(model.calls), 3)
                models.append(model)
            self.assertEqual(models[0].calls, models[1].calls)
            self.assertEqual(public_stores(models[0]), public_stores(models[1]))
            self.assertEqual(guest.public(models[0].memory), guest.public(models[1].memory))
            count += 1
        self.receipts.update(negative_budget_fired_prefix_pairs=count, negative_budgets_not_claimed_complete=True)

    def test_06_actual_restored_null_actor_child_returns(self):
        rom = self.values['conker/conker.us.bin']
        child = list(struct.unpack_from('>261I', rom, 0xB9654))
        connected = dict(zip(range(guest.PAIR, guest.PAIR + 1044, 4), child))
        runs = 0
        for case in (guest.Case(no_pair_writes=True), guest.Case(primary=0, no_pair_writes=True, budget=4),
                guest.Case(primary=0, kinds=(0,), no_pair_writes=True)):
            memory = guest.fixture(case)
            result, wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                for words in (self.retail, self.words):
                    model = guest.SchedulerModel(words, memory, case, phase, connected=connected).run()
                    self.assertEqual(model.r[2], result)
                    self.assertEqual(model.calls, calls)
                    self.assertEqual(public_stores(model), stores)
                    self.assertEqual(guest.public(model.memory), guest.public(wanted))
                    runs += 1
        self.receipts.update(actual_null_actor_child_runs=runs, geometry_providers_still_opaque=True)

    def test_07_production_inputs_unchanged(self):
        for name, digest in source.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn(source.ORIGINAL, (self.root / source.SOURCE).read_text())
        self.receipts.update(frozen_production_inputs_unchanged=True, production_stub_retained=True)


if __name__ == '__main__':
    unittest.main()
