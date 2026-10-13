"""Qualify pointer reuse without confusing lower scores with full matching."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_matrix_reflection_roles as screen
from tools.tests import test_game_matrix_reflection_recovery as previous


def state(model):
    return (model.memory, model.r, model.f, model.fcsr, model.condition,
        model.lo, getattr(model, 'hi', None), model.events, model.raw_calls)


class GameMatrixReflectionRolesTests(previous.GameMatrixReflectionRecoveryTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-roles-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.previous.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', assembly='conker/asm/61D10.s', layout='conker/retail_layout.us.txt')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == '38ac5d5272b5800ff666bb1d284ccfa12409f3a25fa06b38068cd9d337973561'
        cls.body = dict(screen.candidates())[screen.SELECTED_NAME]
        cls.meta, cls.words = screen.previous.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        _, cls.banked_words = screen.previous.compile_candidate(cls.root, cls.out, 'banked', screen.BASE)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.previous.ROM))

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 333, 0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertNotEqual(self.words, self.banked_words)
        self.assertEqual(sum(a != b for a, b in zip(self.words, self.banked_words)), 21)
        self.assertFalse(any(word & 0xFFE0FFFF == 0xAFA0019C for word in self.words))
        self.receipt('shape', words=486, frame=400, differences=333, banked_differences=347,
            changed_words=sum(a != b for a, b in zip(self.words, self.banked_words)),
            input_argument_home_not_written=True, opening_still_different=True,
            no_register_bindings_or_guards=True, installed=False)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        """Replace the historical layout screen with this target's complete role screen."""
        forms = list(screen.candidates())
        self.assertEqual(len({name for name, _ in forms}), len(forms))
        self.assertEqual(len(forms), 100)
        records, arrays = [], set()
        for name, body in forms:
            meta, words = screen.previous.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            if meta['body_words'] == 486 and meta['frame'] == 400:
                arrays.add(tuple(words))
                self.assertNotEqual(words[:23], self.retail[:23], name)
            if name == screen.SELECTED_NAME:
                self.assertEqual(words, self.words)
        self.receipt('screens', forms=len(forms), extent_frame_valid_literal_arrays=len(arrays),
            no_opening_match=True, records=records)
        memory, args = previous.fixture(2, 0, 0, enabled=0)
        good = previous.FaultOracle(self.banked_words, memory, args).run()
        _, rejected = screen.previous.compile_candidate(self.root, self.out, 'better-score-rejected',
            dict(forms)['setup-c1-o0-secondary1'])
        bad = previous.FaultOracle(rejected, memory, args).run()
        output_home = previous.STACK + 16
        loads = lambda model: sum(e[0] == 'R' and e[1] == output_home for e in model.events)
        original = previous.FaultOracle(self.retail, memory, args).run()
        self.assertEqual((loads(original), loads(good), loads(bad)), (2, 1, 0))
        self.assertEqual((original.accesses, good.accesses, bad.accesses), (54, 53, 52))
        self.receipt('rejected-load', lower_score=344, real_output_home_load_removed=True,
            banked_and_rejected_counts=[good.accesses, bad.accesses], original_count=54)

    def test_13_owned_frame_capture_keeps_original_extent_and_object_identity(self):
        super().test_13_owned_frame_capture_keeps_original_extent_and_object_identity()
        record = json.loads((self.out / 'frame-selected/receipt.json').read_text())
        addresses = [r for r in record['records']['optimizer']
            if r['name'] == 'rlda' and r['storage'] == 'M']
        self.assertEqual([(r['offset'], r['words'][2]) for r in addresses],
            [(-64, 30), (-268, 19), (-268, 19)])
        self.assertIn(0x27BE0150, self.words[:23])
        self.receipt('reflection-cache', optimizer_address_records=[
            dict(byte_offset=r['byte_offset'], offset=r['offset'], raw_register_word=r['words'][2])
            for r in addresses], emitted_fp_address_word='27BE0150',
            cache_already_in_optimized_stream=True, not_only_ugen_scheduling=True,
            generic_rlda_length_not_a_matrix_size=True)

    def test_16_all_common_fired_fault_cuts_preserve_previous_agreements(self):
        domains = itertools.product((0, 1, 2, 3), (0, 1), range(4), (0, 8), (0, 256))
        pairs = old_equal = new_equal = 0
        cases = []
        for mode, count, fixed, phase, enabled in domains:
            memory, args = previous.fixture(mode, count, fixed, enabled=enabled)
            completed = [previous.FaultOracle(w, memory, args, phase=phase).run()
                for w in (self.retail, self.banked_words, self.words)]
            self.assertEqual(completed[1].accesses, completed[2].accesses)
            old_cuts, new_cuts = [], []
            for cut in range(min(model.accesses for model in completed)):
                snapshots = []
                for words in (self.retail, self.banked_words, self.words):
                    model = previous.FaultOracle(words, memory, args, phase=phase, fault=cut)
                    with self.assertRaises(previous.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    snapshots.append(state(model))
                before, after = snapshots[0] == snapshots[1], snapshots[0] == snapshots[2]
                if before:
                    self.assertTrue(after, (mode, count, fixed, phase, enabled, cut))
                    old_cuts.append(cut)
                if after:
                    new_cuts.append(cut)
                old_equal += before
                new_equal += after
                pairs += 1
            cases.append(dict(mode=mode, count=count, fixed=fixed, phase=phase, enabled=enabled,
                accesses=[model.accesses for model in completed], old_equal_cuts=old_cuts, new_equal_cuts=new_cuts))
        self.receipt('full-fault-sweep', cases=cases, domains=len(cases), fired_triplets=pairs,
            banked_equal_states=old_equal, candidate_equal_states=new_equal,
            no_previously_equal_states_lost=True, exhaustive_all_inputs_not_claimed=True,
            hardware_PC_BD_FCSR_not_claimed=True)

    def test_17_flag_initializer_sinks_but_forced_early_capture_is_effective(self):
        memory, args = previous.fixture(0, 1, 0, enabled=0)
        action = ('guMtxIdentF', 18, 1)
        body = dict(screen.candidates())['flag-outputFixed-capture1']
        meta, captured_words = screen.previous.compile_candidate(self.root, self.out, 'flag-initializer', body)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 345))
        self.assertEqual(body.count('s32 encoded = outputFixed;'), 1)
        forced = body.replace('s32 encoded = outputFixed;', 'volatile s32 encoded = outputFixed;')
        bad_meta, bad_words = screen.previous.compile_candidate(self.root, self.out, 'forced-early-flag-control', forced)
        self.assertEqual(bad_meta['diagnostics'], '')
        good = [previous.ReflectionOracle(w, memory, args, action=action).run()
            for w in (self.retail, self.banked_words, self.words, captured_words)]
        bad = previous.ReflectionOracle(bad_words, memory, args, action=action).run()
        for model in good[1:]:
            self.assertEqual(good[0].memory, model.memory)
        self.assertNotEqual(previous.public(good[0].memory), previous.public(bad.memory))
        self.assertTrue(all(any(name == 'guMtxF2L2' for name, _ in model.helpers.calls) for model in good))
        self.assertFalse(any(name == 'guMtxF2L2' for name, _ in bad.helpers.calls))
        self.assertTrue(all(model.helpers.applied for model in [*good, bad]))
        self.receipt('early-flag-control', nonvolatile_initializer345_observes_live_home=True,
            forced_volatile_snapshot_compiles_and_has_effective_public_mismatch=True,
            forced_words=bad_meta['body_words'], forced_frame=bad_meta['frame'],
            mutation_fired=all(model.helpers.applied for model in [*good, bad]),
            original_banked_selected_and_initializer_agree=True,
            opaque_provider_action_not_actual_SDK_behavior=True)


if __name__ == '__main__':
    unittest.main()
