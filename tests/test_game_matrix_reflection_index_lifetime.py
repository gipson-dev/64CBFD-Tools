"""Qualify economical index lifetimes without crediting unresolved register roles."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_matrix_reflection_index_lifetime as screen
from tools.tests import test_game_matrix_reflection_recovery as oracle
from tools.tests import test_game_matrix_reflection_roles as previous


class GameMatrixReflectionIndexLifetimeTests(previous.GameMatrixReflectionRolesTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-index-lifetime-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.previous.previous.SOURCE, elf='conker/build/conker.us.elf',
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
        cls.body = screen.qualified_body()
        cls.meta, cls.words = screen.previous.previous.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        _, cls.banked_words = screen.previous.previous.compile_candidate(cls.root, cls.out, 'banked333', screen.BASE)
        cls.retail = list(struct.unpack_from('>486I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), screen.previous.previous.ROM))

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 407, 0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertNotEqual(self.words, self.banked_words)
        self.assertEqual(self.words[:23], self.banked_words[:23])
        self.assertFalse(any(word & 0xFFE0FFFF == 0xAFA0019C for word in self.words))
        self.assertFalse(any(word & 0xFFE0FFFF == 0xAFA001D8 for word in self.words))
        self.assertEqual(sum(a != b for a, b in zip(self.words, self.banked_words)), 309)
        self.receipt('shape', words=486, frame=400, differences=407, banked_differences=333,
            changed_words=sum(a != b for a, b in zip(self.words, self.banked_words)),
            first23_banked_words_unchanged=True, input_home_not_written=True,
            best_literal_candidate332_retained_separately=True,
            no_padding_register_bindings_or_guards=True, installed=False)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        """Replace the inherited screen with all 51 economical lifetime forms."""
        forms = list(screen.candidates())
        self.assertEqual(len(forms), 51)
        self.assertEqual(len({name for name, _ in forms}), len(forms))
        records, arrays = [], set()
        for name, body in forms:
            meta, words = screen.previous.previous.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'],
                differences=meta['differences']))
            if meta['body_words'] == 486 and meta['frame'] == 400:
                arrays.add(tuple(words))
                self.assertNotEqual(words[:23], self.retail[:23], name)
            if name == screen.SELECTED_NAME:
                self.assertNotEqual(words, self.words)
        self.receipt('screens', forms=len(forms), extent_frame_valid_literal_arrays=len(arrays),
            no_opening_match=True, records=records)
        memory, args = oracle.fixture(2, 0, 0, enabled=0)
        _, bad_words = screen.previous.previous.compile_candidate(self.root, self.out, 'lost-home-control',
            dict(forms)['shared-float-index-s32-arms-setup-both'])
        models = [oracle.FaultOracle(w, memory, args).run()
            for w in (self.retail, self.banked_words, self.words, bad_words)]
        loads = lambda model: sum(e[0] == 'R' and e[1] == oracle.STACK + 16 for e in model.events)
        self.assertEqual([loads(m) for m in models], [2, 1, 2, 0])
        self.assertEqual([m.accesses for m in models], [54, 53, 54, 52])
        self.receipt('rejected-load', differences325_rejected=True,
            original_banked_selected_rejected_accesses=[m.accesses for m in models],
            output_home_reads=[loads(m) for m in models], real_removed_read=True)

    def test_09_public_agreement_is_not_literal_private_frame_identity(self):
        memory, args = oracle.fixture(0, 1, 1)
        pair = self.compare(memory, args)
        calls = [next(args for name, args in model.raw_calls if name == 'guMtxL2F') for model in pair]
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(pair[0].memory, pair[1].memory)
        self.assertEqual(pair[0].f, pair[1].f)
        changed = [i for i in range(32) if pair[0].r[i] != pair[1].r[i]]
        banked = oracle.ReflectionOracle(self.banked_words, memory, args).run()
        self.assertEqual([i for i in range(32) if pair[0].r[i] != banked.r[i]], [9, 13])
        self.assertEqual(changed, [9, 12])
        self.assertEqual(pair[0].r[13], pair[1].r[13])
        self.assertNotEqual(pair[0].r[12], pair[1].r[12])
        _, old_words = screen.previous.previous.compile_candidate(self.root, self.out, 'old-private-control',
            dict(screen.previous.previous.candidates())['do-count-o1-a0'])
        old = self.compare(memory, args, words=old_words)[1]
        old_calls = next(args for name, args in old.raw_calls if name == 'guMtxL2F')
        self.assertEqual(old_calls[0] - calls[0][0], 12)
        self.assertNotEqual(old.memory, pair[0].memory)
        self.receipt('private-boundary', conversion_destinations=[hex(args[0]) for args in calls],
            old_conversion_destination=hex(old_calls[0]), exact_sampled_RAM_and_FPRs=True,
            banked_changed_return_GPRs=[9, 13], changed_return_GPRs=changed,
            GPR13_recovers_but_GPR12_loses_prior_component_agreement=True,
            full_state_identity=False, candidate_installed=False, matching_credit=0)

    def test_16_all_common_fired_fault_cuts_preserve_previous_agreements(self):
        pairs = old_equal = new_equal = 0
        cases = []
        for mode, count, fixed, phase, enabled in itertools.product(
                (0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256)):
            memory, args = oracle.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            completed = [oracle.FaultOracle(w, memory, args, phase=phase).run()
                for w in (self.retail, self.banked_words, self.words)]
            old, new = completed[1].accesses, completed[2].accesses
            self.assertLessEqual(abs(completed[0].accesses - new), abs(completed[0].accesses - old))
            home_loads = lambda model: sum(e[0] == 'R' and e[1] == oracle.STACK + phase + 16
                for e in model.events)
            self.assertEqual(home_loads(completed[0]), home_loads(completed[2]))
            old_cuts, new_cuts = [], []
            for cut in range(min(model.accesses for model in completed)):
                snapshots = []
                for words in (self.retail, self.banked_words, self.words):
                    model = oracle.FaultOracle(words, memory, args, phase=phase, fault=cut)
                    with self.assertRaises(oracle.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    snapshots.append(previous.state(model))
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
                accesses=[m.accesses for m in completed], old_equal_cuts=old_cuts, new_equal_cuts=new_cuts))
        self.receipt('full-fault-sweep', cases=cases, domains=len(cases), fired_triplets=pairs,
            banked_equal_states=old_equal, candidate_equal_states=new_equal,
            no_previously_equal_states_lost=True, output_home_read_counts_match_retail=True,
            access_count_distance_to_retail_never_worse=True, hardware_PC_BD_FCSR_HI_not_claimed=True)

    def test_13_owned_frame_capture_keeps_original_extent_and_object_identity(self):
        super().test_13_owned_frame_capture_keeps_original_extent_and_object_identity()
        record = json.loads((self.out / 'frame-selected/receipt.json').read_text())
        pairs = {}
        for stage in ('frontend', 'optimizer'):
            records = record['records'][stage]
            at = next(i for i, r in enumerate(records)
                if r['name'] == 'lda' and r['storage'] == 'P' and r['offset'] == 16)
            pair = records[at:at + 2]
            self.assertEqual((pair[1]['name'], pair[1]['dtype'], pair[1]['offset']), ('ilod', 'A', 0))
            pairs[stage] = [dict(byte_offset=r['byte_offset'], opcode=r['name'], words=r['words']) for r in pair]
        self.assertEqual([r['byte_offset'] for r in pairs['frontend']], [1144, 1168])
        self.assertEqual([r['byte_offset'] for r in pairs['optimizer']], [1320, 1344])
        self.receipt('output-home-address-work', pairs=pairs, parameter_offset=16,
            extra_address_work_exists_in_frontend_and_survives_optimizer=True,
            volatile_flag_bit_meaning_not_inferred=True, not_only_ugen_scheduling=True)

    def test_18_named_cross_call_index_still_rematerializes(self):
        self.assertEqual(self.body.count('matrixOffset = i * 64;'), 4)
        self.assertEqual(self.words[47], 0x0012C980)
        self.assertEqual(self.words[60], 0x0D429E92)
        self.assertEqual(self.words[63], 0x00124980)
        self.receipt('rematerialized-index', source_assignments=4,
            primary_pre_call_shift='0012C980', concat_call='0D429E92',
            primary_post_call_shift='00124980', reflection_cache_still_fp=True,
            retail_saved_s2_index_not_recovered=True)

    def test_19_tail_restores_live_read_and_null_actor_boundary(self):
        forms = list(screen.tail_candidates())
        self.assertEqual(len(forms), 13)
        arrays, records = set(), []
        for name, body in forms:
            meta, words = screen.previous.previous.compile_candidate(self.root, self.out, name, body)
            self.assertEqual((meta['body_words'], meta['frame'], meta['diagnostics']), (486, 400, ''))
            records.append(dict(name=name, differences=meta['differences']))
            arrays.add(tuple(words))
            if name == screen.TAIL_SELECTED_NAME:
                self.assertNotEqual(words, self.words)
        cases = 0
        for mode, count, fixed, phase, enabled in itertools.product(
                (0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256, 0x80000000, 0xFFFFFFFF)):
            memory, args = oracle.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            self.compare(memory, args, phase)
            for words in (self.retail, self.words):
                model = oracle.FaultOracle(words, memory, args, phase=phase).run()
                at = next((i for i, e in enumerate(model.events)
                    if e[0] == 'R' and e[1] == oracle.STACK + phase), None)
                if mode == 3:
                    self.assertIsNone(at)
                elif enabled is None:
                    self.assertIsNotNone(at)
                    self.assertFalse(any(e[0] == 'R' and e[1] == oracle.STACK + phase + 16
                        for e in model.events[at:]))
                else:
                    self.assertIsNotNone(at)
                    self.assertEqual([(e[0], e[1]) for e in model.events[at:at + 3]],
                        [('R', oracle.STACK + phase), ('R', args[0] + 0x9C),
                         ('R', oracle.STACK + phase + 16)])
            cases += 1
        self.receipt('tail', cases=cases, forms=len(forms), literal_arrays=len(arrays), records=records,
            full32_state_gate=True, null_actor_skips_output_read=True,
            nonnull_zero_gate_still_reads_output_home=True, complete_sampled_RAM_and_helper_packets=True)

    def test_20_cold_and_home_forms_retain_effective_lower_score_rejection(self):
        forms = [*screen.cold_loop_candidates(), *screen.home_candidates(),
            *screen.typedef_candidates(), *screen.direct_home_candidates()]
        self.assertEqual(len(forms), 21)
        records, arrays = [], {}
        for name, body in forms:
            meta, words = screen.previous.previous.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            arrays[name] = words
            if name == screen.HOME_SELECTED_NAME:
                self.assertEqual(words, self.words)
        meta, rejected = screen.previous.previous.compile_candidate(self.root, self.out, 'tail329-count-negative', screen.tail_body())
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 329))
        self.assertEqual(arrays['direct-home-dereference-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-parenthesized-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-zero-subscript'], self.words)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o0'])), 11)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o1'])), 15)
        failures = []
        for mode, count, fixed, phase, enabled in itertools.product(
                (0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256)):
            memory, args = oracle.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            models = [oracle.FaultOracle(w, memory, args, phase=phase).run()
                for w in (self.retail, self.banked_words, rejected, self.words)]
            counts = [m.accesses for m in models]
            if abs(counts[0] - counts[2]) > abs(counts[0] - counts[1]):
                failures.append((mode, count, fixed, phase, enabled, counts))
                self.assertLessEqual(abs(counts[0] - counts[3]), abs(counts[0] - counts[1]))
        self.assertEqual(len(failures), 8)
        self.assertTrue(all((m, c, enabled) == (1, 0, 0) for m, c, _, _, enabled, _ in failures))
        self.assertEqual(self.words[36], 0x27B801A0)
        self.assertEqual(self.words[40], 0x8F110000)
        self.receipt('home-controls', forms=len(forms), records=records,
            lower329_regressing_domains=failures, direct_count_gate_not_relaxed=True,
            equal329_scores_hide_11_or_15_word_changes=True,
            direct_address_dereference_folds_to_cold_body_but_subscript_preserves_indirection=True,
            guarded_indirect_address_and_load_words=['27B801A0', '8F110000'],
            highest_score_not_claimed_matching_improvement=True)


if __name__ == '__main__':
    unittest.main()
