"""Qualify the SDK-typed index without crediting unresolved saved scheduling."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_matrix_reflection_saved_index as screen
from tools.tests import test_game_matrix_reflection_dispatch_homes as previous
from tools.tests import test_game_matrix_reflection_recovery as oracle


class GameMatrixReflectionSavedIndexTests(previous.GameMatrixReflectionDispatchHomesTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-saved-index-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.compiler.SOURCE, elf='conker/build/conker.us.elf',
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
        cls.meta, cls.words = screen.compiler.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        _, cls.banked_words = screen.compiler.compile_candidate(cls.root, cls.out, 'banked331', screen.BASE)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.compiler.ROM))

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 259, 0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual(self.words[:23], self.banked_words[:23])
        self.assertEqual(self.words[19:22], [0x00E0B025, 0x0D429EF0, 0x27A40150])
        self.assertIn(0x8FB701D4, self.words)
        self.assertIn(0x8FBE01D8, self.words)
        self.assertNotIn('&output', self.body)
        self.assertFalse(any(w & 0xFFE0FFFF in (0xAFA0019C, 0xAFA001D8) for w in self.words))
        self.receipt('shape', words=486, frame=400, differences=259,
            changed_words=sum(a != b for a, b in zip(self.words, self.banked_words)),
            SDK_typed_matrix_index=True, saved_shift_index_recovered=True,
            saved_store_schedule_still_different=True, installed=False)

    def native_source(self, body):
        source = super().native_source(body)
        marker = 'v->mode,(u8 *)input,(u8 *)output'
        self.assertEqual(source.count(marker), 1)
        return source.replace(marker, 'v->mode,(Mtx *)input,(u8 *)output')

    def test_07_native32_actual_body_and_effective_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(self.body), profile)[0], 0)
        marker = '*(u8 **)(actor + 0x1D4) = cursor;'
        self.assertEqual(self.body.count(marker), 1)
        controls = {
            'wrong-ramp': self.body.replace('nearDistance = 10.0f;', 'nearDistance = 9.0f;'),
            'byte-gate': self.body.replace('*(u32 *)(actor + 0x9C)', 'actor[0x9F]'),
            'wrong-restore': self.body.replace(marker, '*(u8 **)(actor + 0x1D4) = cursor + 4;'),
            'wrong-distance-slots': self.body.replace('(s32)pointX, (s32)pointZ', '(s32)pointZ, (s32)pointX'),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, self.body)
            self.assertNotEqual(self.run_native(name, self.native_source(body))[0], 0, name)
        self.receipt('native', cases_per_profile=256, profiles=['O2', 'O0'], effective_negatives=4,
            original_four_contracts_retained=True, typed_input_runner_cast_not_a_body_rewrite=True,
            restoration_control_targets_actual_callback_pointer_store=True)

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
        self.assertEqual([i for i in range(32) if pair[0].r[i] != banked.r[i]], [9, 14])
        _, old_words = screen.compiler.compile_candidate(self.root, self.out, 'old-private-control',
            dict(screen.compiler.candidates())['do-count-o1-a0'])
        old = self.compare(memory, args, words=old_words)[1]
        old_calls = next(args for name, args in old.raw_calls if name == 'guMtxL2F')
        self.assertEqual(old_calls[0] - calls[0][0], 12)
        self.assertNotEqual(old.memory, pair[0].memory)
        self.receipt('private-boundary', conversion_destinations=[hex(a[0]) for a in calls],
            exact_sampled_RAM_and_FPRs=True, changed_return_GPRs=changed,
            banked_and_selected_same_unresolved_register_boundary=True,
            full_state_identity=False, old12_byte_layout_negative_effective=True, installed=False)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        """Measure every current source form and compare full eligible arrays."""
        forms = list(screen.candidates())
        self.assertEqual(len(forms), 75)
        self.assertEqual(len({name for name, _ in forms}), len(forms))
        arrays, records, by_name = set(), [], {}
        for name, body in forms:
            meta, words = screen.compiler.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            by_name[name] = words
            if meta['body_words'] == 486 and meta['frame'] == 400:
                arrays.add(tuple(words))
                self.assertNotEqual(words[:23], self.retail[:23], name)
            if name == screen.SELECTED_NAME:
                self.assertEqual(words, self.words)
        self.assertEqual(by_name['incoming-register-baseline'], by_name['baseline331'])
        self.assertEqual(by_name['typed-base-array'], by_name['typed-shared-array'])
        self.assertEqual(by_name['typed-base-array'], by_name['typed-shared-shift'])
        self.assertEqual(by_name['actor-flags-s32-owner-cursor'], self.words)
        self.receipt('screens', forms=len(forms), extent_frame_valid_literal_arrays=len(arrays), records=records,
            ordinary_register_hint_has_no_effect=True, independent_typed_and_shift_forms_same_words=True,
            shorter_or_spilling_forms_not_installed=True, no_opening_match=True)

    def test_18_named_cross_call_index_still_rematerializes(self):
        shifts = [i for i, w in enumerate(self.words)
            if w >> 26 == 0 and w & 63 == 0 and w >> 6 & 31 == 6]
        self.assertEqual(shifts, [45, 52, 290, 297])
        self.assertEqual([self.words[i] for i in shifts], [0x00139180] * 4)
        self.assertEqual([self.words[i] for i in shifts], [self.retail[i] for i in shifts])
        self.assertNotIn(0x02C09025, self.words)
        self.assertNotIn(0x26520040, self.words)
        self.assertNotIn(0x27BE0150, self.words)
        self.assertEqual(sum(w >> 26 == 35 and w >> 21 & 31 == 29 and w & 65535 == 0x1A0
            for w in self.words), 5)
        self.receipt('register-boundary', original_saved_shift_indices=shifts,
            original_s2_shift_words_recovered=True, extra_input_cursor_removed=True,
            direct_output_home_reads=5, reflection_cache_still_removed=True,
            original_saved_store_schedule_and_conversion_cache_role_unrecovered=True)

    def test_20_cold_and_home_forms_retain_effective_lower_score_rejection(self):
        older = screen.previous.previous
        forms = [*older.cold_loop_candidates(), *older.home_candidates(),
            *older.typedef_candidates(), *older.direct_home_candidates()]
        self.assertEqual(len(forms), 21)
        arrays, records = {}, []
        for name, body in forms:
            meta, words = screen.compiler.compile_candidate(self.root, self.out, name, body)
            arrays[name] = words
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            if name == older.HOME_SELECTED_NAME:
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 407))
        diagnostic = arrays[older.HOME_SELECTED_NAME]
        self.assertNotEqual(diagnostic, self.words)
        meta, rejected = screen.compiler.compile_candidate(self.root, self.out, 'tail329-count-negative', older.tail_body())
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 329))
        legacy_meta, legacy = screen.compiler.compile_candidate(self.root, self.out, 'legacy333-control', older.BASE)
        self.assertEqual((legacy_meta['body_words'], legacy_meta['frame'], legacy_meta['differences']), (486, 400, 333))
        self.assertEqual(arrays['direct-home-dereference-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-parenthesized-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-zero-subscript'], diagnostic)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o0'])), 11)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o1'])), 15)
        legacy_failures, current_failures = [], []
        for mode, count, fixed, phase, enabled in itertools.product(
                (0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256)):
            memory, args = oracle.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            models = [oracle.FaultOracle(w, memory, args, phase=phase).run()
                for w in (self.retail, legacy, self.banked_words, rejected, self.words)]
            counts = [m.accesses for m in models]
            self.assertLessEqual(abs(counts[0] - counts[4]), abs(counts[0] - counts[2]))
            case = (mode, count, fixed, phase, enabled, counts)
            if abs(counts[0] - counts[3]) > abs(counts[0] - counts[1]):
                legacy_failures.append(case)
            if abs(counts[0] - counts[3]) > abs(counts[0] - counts[2]):
                current_failures.append(case)
        self.assertEqual(len(legacy_failures), 8)
        self.assertTrue(all((m, c, enabled) == (1, 0, 0) for m, c, _, _, enabled, _ in legacy_failures))
        self.assertEqual(len(current_failures), 48)
        self.assertTrue({c[:5] for c in legacy_failures}.issubset({c[:5] for c in current_failures}))
        self.assertEqual(diagnostic[36], 0x27B801A0)
        self.assertEqual(diagnostic[40], 0x8F110000)
        self.receipt('home-controls', forms=len(forms), records=records,
            legacy333_rejects_original_eight_domains=legacy_failures,
            current331_rejects_48_domains=current_failures,
            every_earlier_rejection_retained=True, all192_selected_count_distances_never_worse=True,
            equal329_scores_hide_11_or_15_word_changes=True,
            previous407_diagnostic_remains_distinct=True, gate_not_relaxed=True)

    def test_22_typed_input_bank_stride_has_effective_wrong_index_control(self):
        self.assertEqual(self.body.count('&input[i]'), 4)
        body = self.body.replace('&input[i]', '&input[i + 1]', 1)
        meta, bad_words = screen.compiler.compile_candidate(self.root, self.out, 'wrong-input-index', body)
        self.assertEqual(meta['diagnostics'], '')
        memory, args = oracle.fixture(0, 1, 1)
        models = [oracle.ReflectionOracle(w, memory, args).run() for w in (self.retail, self.words, bad_words)]
        calls = [next(a for name, a in m.raw_calls if name == 'guMtxL2F') for m in models]
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(calls[2][1] - calls[0][1], 64)
        self.assertEqual(models[0].memory, models[1].memory)
        self.assertNotEqual(oracle.public(models[0].memory), oracle.public(models[2].memory))
        self.receipt('typed-index-control', real_bank_stride=64,
            wrong_index_compiles_and_changes_actual_conversion_source=True,
            wrong_index_public_negative_effective=True, production_unchanged=True)


if __name__ == '__main__':
    unittest.main()
