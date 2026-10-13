"""Qualify direct output-home loads and the real dispatch snapshots."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_dispatch_homes as screen
from tools.tests import test_game_matrix_reflection_index_lifetime as previous
from tools.tests import test_game_matrix_reflection_recovery as oracle


class GameMatrixReflectionDispatchHomesTests(previous.GameMatrixReflectionIndexLifetimeTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-dispatch-homes-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.previous.previous.previous.SOURCE, elf='conker/build/conker.us.elf',
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
        cls.meta, cls.words = screen.previous.previous.previous.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        _, cls.banked_words = screen.previous.previous.previous.compile_candidate(cls.root, cls.out, 'banked333',
            screen.previous.BASE)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(),
            screen.previous.previous.previous.ROM))

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 331, 0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertNotEqual(self.words[:23], self.banked_words[:23])
        self.assertEqual(self.words[19:22], [0x00E0B025, 0x0D429EF0, 0x27A40150])
        self.assertIn(0x8FB701D4, self.words)
        self.assertIn(0x8FBE01D8, self.words)
        self.assertNotIn('&output', self.body)
        self.assertFalse(any(word & 0xFFE0FFFF in (0xAFA0019C, 0xAFA001D8) for word in self.words))
        self.receipt('shape', words=486, frame=400, differences=331,
            changed_words=sum(a != b for a, b in zip(self.words, self.banked_words)),
            no_padding_register_bindings_or_guards=True, direct_home_without_address_escape=True,
            input_bank_s6_recovered=True, identity_call_and_direct_address_aligned=True,
            reflection_cache_removed=True, installed=False)

    def test_09_public_agreement_is_not_literal_private_frame_identity(self):
        memory, args = oracle.fixture(0, 1, 1)
        pair = self.compare(memory, args)
        calls = [next(args for name, args in m.raw_calls if name == 'guMtxL2F') for m in pair]
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(pair[0].memory, pair[1].memory)
        self.assertEqual(pair[0].f, pair[1].f)
        changed = [i for i in range(32) if pair[0].r[i] != pair[1].r[i]]
        self.assertEqual(changed, [9, 14])
        banked = oracle.ReflectionOracle(self.banked_words, memory, args).run()
        self.assertEqual([i for i in range(32) if pair[0].r[i] != banked.r[i]], [9, 13])
        _, old_words = screen.previous.previous.previous.compile_candidate(self.root, self.out, 'old-private-control',
            dict(screen.previous.previous.previous.candidates())['do-count-o1-a0'])
        old = self.compare(memory, args, words=old_words)[1]
        old_calls = next(args for name, args in old.raw_calls if name == 'guMtxL2F')
        self.assertEqual(old_calls[0] - calls[0][0], 12)
        self.assertNotEqual(old.memory, pair[0].memory)
        self.receipt('private-boundary', conversion_destinations=[hex(a[0]) for a in calls],
            exact_sampled_RAM_and_FPRs=True, changed_return_GPRs=changed,
            full_state_identity=False, recovered_GPR13_but_lost_GPR14_component=True,
            old12_byte_layout_negative_effective=True, installed=False)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        """Replace the inherited screen with all 30 real dispatch/address forms."""
        forms = list(screen.candidates())
        self.assertEqual(len(forms), 30)
        self.assertEqual(len({name for name, _ in forms}), len(forms))
        arrays, records = set(), []
        for name, body in forms:
            meta, words = screen.previous.previous.previous.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            if meta['body_words'] == 486 and meta['frame'] == 400:
                arrays.add(tuple(words))
                self.assertNotEqual(words[:23], self.retail[:23], name)
            if name == screen.SELECTED_NAME:
                self.assertEqual(words, self.words)
        self.receipt('screens', forms=len(forms), extent_frame_valid_literal_arrays=len(arrays), records=records,
            no_opening_match=True, shorter_or_spilling_forms_not_installed=True)

    def test_13_owned_frame_capture_keeps_original_extent_and_object_identity(self):
        adapter = SimpleNamespace(SELECTED=self.body, compile_candidate=oracle.screen.compile_candidate)
        with patch.object(oracle.observer, 'screen', adapter):
            record = oracle.observer.trace(self.root, self.out, 'frame-selected', self.body)
        self.assertTrue(record['code_unchanged'])
        events = [e for e in record['events'] if e['event'] == 'frame-write']
        self.assertEqual([e['frame'] for e in events], [88, 104, 400])
        self.assertEqual((events[-1]['locals'], events[-1]['saved'], events[-1]['outgoing']), (296, 88, 16))
        definitions = {r['storage']: r['length'] for r in record['records']['optimizer'] if r['name'] == 'def'}
        self.assertEqual(definitions, dict(M=296, P=76))
        frontend = {r['storage']: r['length'] for r in record['records']['frontend'] if r['name'] == 'def'}
        self.assertEqual(frontend, dict(M=288, P=76))
        offsets = {r['offset'] for r in record['records']['optimizer'] if r['storage'] == 'M'}
        self.assertTrue({-268, -192, -128, -64}.issubset(offsets))
        caches = [(r['offset'], r['words'][2]) for r in record['records']['optimizer']
            if r['name'] == 'rlda' and r['storage'] == 'M']
        self.assertEqual(caches, [(-268, 20), (-268, 20)])
        stages = {}
        for stage in ('frontend', 'optimizer'):
            records = record['records'][stage]
            loads = [r for r in records if r['name'] == 'lod' and r['storage'] == 'P' and r['offset'] == 16]
            self.assertEqual(len(loads), 5)
            self.assertFalse(any(r['name'] in ('lda', 'rlda') and r['storage'] == 'P' and r['offset'] == 16
                for r in records))
            modes = [r for r in records if r['name'] == 'lod' and r['storage'] == 'P' and r['offset'] == 8]
            self.assertEqual(len(modes), 3)
            stages[stage] = dict(output_loads=[dict(byte_offset=r['byte_offset'], words=r['words']) for r in loads],
                mode_loads=[dict(byte_offset=r['byte_offset'], words=r['words']) for r in modes])
        self.receipt('direct-home-lowering', stages=stages, direct_P16_loads=5, mode_snapshots=3,
            no_output_address_materialization_in_frontend_or_optimizer=True,
            frontend_M=288, optimizer_M=296, parameter_bytes=76, physical_frame=400,
            physical_locals=296, saved=88, outgoing=16, matrix_offsets=[-268, -192, -128, -64],
            reflection_cache_removed_but_conversion_cache_remains=caches,
            normal_traced_object_identity=True, flag_bits_not_inferred=True)

    def test_18_named_cross_call_index_still_rematerializes(self):
        shifts = [i for i, w in enumerate(self.words)
            if w >> 26 == 0 and w & 63 == 0 and w >> 6 & 31 == 6]
        self.assertFalse(shifts)
        loads = [i for i, w in enumerate(self.words)
            if w >> 26 == 35 and w >> 21 & 31 == 29 and w & 65535 == 0x1A0]
        self.assertEqual(len(loads), 5)
        self.assertNotIn(0x27BE0150, self.words)
        self.assertIn(0x02C09025, self.words)
        self.assertIn(0x26520040, self.words)
        self.receipt('register-boundary', counter_shift_indices=shifts, direct_output_load_indices=loads,
            reflection_cache_removed=True, input_cursor_strength_reduced_to_s2=True,
            input_flag_s7_and_output_flag_fp_recovered=True,
            original_saved_shift_index_not_recovered=True, saved_schedule_still_different=True)

    def test_20_cold_and_home_forms_retain_effective_lower_score_rejection(self):
        forms = [*screen.previous.cold_loop_candidates(), *screen.previous.home_candidates(),
            *screen.previous.typedef_candidates(), *screen.previous.direct_home_candidates()]
        self.assertEqual(len(forms), 21)
        records, arrays = [], {}
        for name, body in forms:
            meta, words = screen.previous.previous.previous.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            arrays[name] = words
            if name == screen.previous.HOME_SELECTED_NAME:
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 407))
        diagnostic = arrays[screen.previous.HOME_SELECTED_NAME]
        self.assertNotEqual(diagnostic, self.words)
        meta, rejected = screen.previous.previous.previous.compile_candidate(self.root, self.out,
            'tail329-count-negative', screen.previous.tail_body())
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 329))
        self.assertEqual(arrays['direct-home-dereference-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-parenthesized-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-zero-subscript'], diagnostic)
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
        self.assertEqual(diagnostic[36], 0x27B801A0)
        self.assertEqual(diagnostic[40], 0x8F110000)
        self.receipt('home-controls', forms=len(forms), records=records,
            lower329_regressing_domains=failures, direct_count_gate_not_relaxed=True,
            equal329_scores_hide_11_or_15_word_changes=True,
            direct_address_dereference_folds_to_cold_body_but_subscript_preserves_indirection=True,
            guarded_indirect_address_and_load_words=['27B801A0', '8F110000'],
            previous407_diagnostic_distinct_from_current331_candidate=True,
            highest_score_not_claimed_matching_improvement=True)

    def test_20_direct_homes_fix_missing_mode_read_without_address_work(self):
        memory, args = oracle.fixture(0, 0, 0, enabled=0)
        args = (0, *args[1:])
        _, cold_words = screen.previous.previous.previous.compile_candidate(self.root, self.out, 'cold-control', screen.BASE)
        models = [oracle.FaultOracle(w, memory, args).run() for w in (self.retail, cold_words, self.words)]
        counts = [sum(e[0] == 'R' and e[1] == oracle.STACK + 8 for e in m.events) for m in models]
        self.assertEqual(counts, [3, 2, 3])
        self.assertEqual([m.accesses for m in models], [51, 50, 51])
        self.assertEqual(models[0].memory, models[2].memory)
        self.receipt('mode-read-control', original_cold_selected_mode_reads=counts,
            original_cold_selected_own_accesses=[m.accesses for m in models],
            missing_mode_not_output_home_was_count_deficit=True)

    def test_21_mode_home_remains_live_after_identity_and_matrix_helpers(self):
        for phase in (0, 8):
            memory, args = oracle.fixture(0, 1, 0, distance=5.0, enabled=0)
            for action in (('guMtxIdentF', 2, 2), ('func_150A7A48', 2, 1)):
                pair = [oracle.ReflectionOracle(w, memory, args, phase=phase, action=action).run()
                    for w in (self.retail, self.words)]
                self.assertTrue(all(m.helpers.applied for m in pair))
                self.assertEqual(pair[0].memory, pair[1].memory)
                self.assertEqual(pair[0].helpers.calls, pair[1].helpers.calls)
        marker = '            firstMode = mode;\n'
        self.assertEqual(self.body.count(marker), 1)
        bad = self.body.replace(marker, '            firstMode = 0;\n')
        meta, bad_words = screen.previous.previous.previous.compile_candidate(self.root, self.out, 'stale-mode-negative', bad)
        self.assertEqual(meta['diagnostics'], '')
        memory, args = oracle.fixture(0, 1, 0, distance=5.0, enabled=0)
        models = [oracle.ReflectionOracle(w, memory, args, action=('func_150A7A48', 2, 1)).run()
            for w in (self.retail, self.words, bad_words)]
        self.assertTrue(all(m.helpers.applied for m in models))
        self.assertEqual([m.memory[oracle.RECORD + 4] for m in models], [200, 200, 100])
        self.assertNotEqual(oracle.public(models[0].memory), oracle.public(models[2].memory))
        self.receipt('live-mode-home', cases=4, both_stack_phases=True,
            identity_routing_and_post_matrix_opacity_modes_remain_live=True,
            stale_snapshot_compiles_and_has_public_negative=True, opacity_bytes=[200, 200, 100],
            opaque_provider_action_not_actual_SDK_behavior=True)


if __name__ == '__main__':
    unittest.main()
