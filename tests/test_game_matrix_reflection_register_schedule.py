"""Qualify the recovered prologue while retaining all unresolved boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_register_schedule as screen
from tools.tests import test_game_matrix_reflection_saved_index as previous
from tools.tests import test_game_matrix_reflection_recovery as oracle
from tools.tests.test_game_matrix_reflection_roles import state


class GameMatrixReflectionRegisterScheduleTests(previous.GameMatrixReflectionSavedIndexTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-register-schedule-test'
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
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        _, cls.banked_words = screen.compile_candidate(cls.root, cls.out, 'banked259', screen.BASE)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.compiler.ROM))

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 240, 0, ''))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual(self.words[:22], self.retail[:22])
        self.assertNotEqual(self.words[22], self.retail[22])
        self.assertEqual(self.words[22:], self.banked_words[22:])
        self.assertEqual(sum(a != b for a, b in zip(self.words, self.banked_words)), 19)
        self.assertEqual(self.words[1:4], [0xAFB60058, 0x00E0B025, 0xAFBF0064])
        self.assertNotIn('saved', self.body)
        self.assertIn('guMtxIdentF(reflection);', self.body)
        self.assertFalse(any(w & 0xFFE0FFFF in (0xAFA0019C, 0xAFA001D8) for w in self.words))
        self.receipt('shape', words=486, frame=400, differences=240, changed_words=19,
            exact_opening_words=22, all_later_words_equal_banked259=True,
            early_s6_save_and_argument_move_recovered=True, temporary_input_assignment_removed=True,
            source_body_direct_no_guards=True, installed=False)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        """Compare all 23 real source forms and the complete eligible arrays."""
        forms = list(screen.candidates())
        self.assertEqual(len(forms), 23)
        self.assertEqual(len({name for name, _ in forms}), 23)
        arrays, records, by_name = set(), [], {}
        for name, body in forms:
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            by_name[name] = words
            if meta['body_words'] == 486 and meta['frame'] == 400:
                arrays.add(tuple(words))
                self.assertNotEqual(words, self.retail, name)
            if name == screen.SELECTED_NAME:
                self.assertEqual(words, self.words)
        for name in ('identity-direct-cast', 'identity-direct-address'):
            self.assertEqual(by_name[name], self.words)
        self.receipt('screens', forms=23, extent_frame_valid_literal_arrays=len(arrays), records=records,
            direct_identity_casts_same_full_words=True, wrong_extent_or_frame_not_installed=True)

    def test_13_owned_frame_capture_keeps_original_extent_and_object_identity(self):
        adapter = SimpleNamespace(SELECTED=self.body, compile_candidate=screen.compiler.compile_candidate)
        with patch.object(oracle.observer, 'screen', adapter):
            record = oracle.observer.trace(self.root, self.out, 'frame-selected', self.body)
        self.assertTrue(record['code_unchanged'])
        events = [e for e in record['events'] if e['event'] == 'frame-write']
        self.assertEqual([e['frame'] for e in events], [88, 104, 400])
        self.assertEqual((events[-1]['locals'], events[-1]['saved'], events[-1]['outgoing']), (296, 88, 16))
        stages = {}
        for stage, local_bytes in (('frontend', 284), ('optimizer', 292)):
            records = record['records'][stage]
            definitions = {r['storage']: r['length'] for r in records if r['name'] == 'def'}
            self.assertEqual(definitions, dict(M=local_bytes, P=76))
            output = [r for r in records if r['name'] == 'lod' and r['storage'] == 'P' and r['offset'] == 16]
            modes = [r for r in records if r['name'] == 'lod' and r['storage'] == 'P' and r['offset'] == 8]
            self.assertEqual((len(output), len(modes)), (5, 3))
            self.assertFalse(any(r['name'] in ('lda', 'rlda') and r['storage'] == 'P' and r['offset'] == 16
                for r in records))
            self.assertFalse(any(r['name'] == 'str' and r['storage'] == 'P' and r['offset'] == 12 for r in records))
            stages[stage] = dict(definitions=definitions,
                output_loads=[dict(byte_offset=r['byte_offset'], words=r['words']) for r in output],
                mode_loads=[dict(byte_offset=r['byte_offset'], words=r['words']) for r in modes])
        offsets = {r['offset'] for r in record['records']['optimizer'] if r['storage'] == 'M'}
        self.assertTrue({-268, -192, -128, -64}.issubset(offsets))
        caches = [(r['offset'], r['words'][2]) for r in record['records']['optimizer']
            if r['name'] == 'rlda' and r['storage'] == 'M']
        self.assertEqual(caches, [(-268, 20), (-268, 20)])
        self.receipt('direct-home-lowering', stages=stages, physical_frame=400, physical_locals=296,
            saved=88, outgoing=16, frontend_M=284, optimizer_M=292, parameter_bytes=76,
            no_input_parameter_assignment_in_either_stream=True, no_output_address_materialization=True,
            original_matrix_addresses_retained=True, conversion_cache_s4_still_unrecovered=caches,
            normal_traced_object_identity=True, flag_bits_not_inferred=True)

    def test_15_literal_fired_fault_prefix_retains_saved_role_boundary(self):
        memory, args = oracle.fixture(0, 1, 0)
        cases = []
        for phase in (0, 8):
            for cut in range(20):
                states = []
                for words in (self.retail, self.words):
                    model = oracle.FaultOracle(words, memory, args, phase=phase, fault=cut)
                    with self.assertRaises(oracle.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    states.append(state(model))
                self.assertEqual(states[0] == states[1], cut < 19)
                cases.append(dict(phase=phase, cut=cut, states_equal=states[0] == states[1]))
            old = oracle.FaultOracle(self.banked_words, memory, args, phase=phase, fault=1)
            with self.assertRaises(oracle.AccessFault):
                old.run()
            original = oracle.FaultOracle(self.retail, memory, args, phase=phase, fault=1)
            with self.assertRaises(oracle.AccessFault):
                original.run()
            self.assertNotEqual(state(old), state(original))
        self.receipt('fault-boundary', cases=cases, fired_pairs=40,
            first_memory_state_difference=19, previous_cut1_negative_remains_effective=True,
            first19_modeled_prefix_states_equal_both_phases=True, hardware_PC_BD_FCSR_HI_not_claimed=True)

    def test_20_cold_and_home_forms_retain_effective_lower_score_rejection(self):
        older = screen.previous.previous.previous
        forms = [*older.cold_loop_candidates(), *older.home_candidates(),
            *older.typedef_candidates(), *older.direct_home_candidates()]
        self.assertEqual(len(forms), 21)
        arrays, records = {}, []
        for name, body in forms:
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            arrays[name] = words
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            if name == older.HOME_SELECTED_NAME:
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 407))
        diagnostic = arrays[older.HOME_SELECTED_NAME]
        self.assertNotEqual(diagnostic, self.words)
        meta, rejected = screen.compile_candidate(self.root, self.out, 'tail329-count-negative', older.tail_body())
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 329))
        meta, legacy = screen.compile_candidate(self.root, self.out, 'legacy333-control', older.BASE)
        self.assertEqual(meta['differences'], 333)
        meta, prior = screen.compile_candidate(self.root, self.out, 'prior331-control', screen.previous.BASE)
        self.assertEqual(meta['differences'], 331)
        self.assertEqual(arrays['direct-home-dereference-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-parenthesized-address'], arrays['cold-c1-o1'])
        self.assertEqual(arrays['direct-home-zero-subscript'], diagnostic)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o0'])), 11)
        self.assertEqual(sum(a != b for a, b in zip(rejected, arrays['cold-c1-o1'])), 15)
        failures = [[], [], []]
        for mode, count, fixed, phase, enabled in itertools.product(
                (0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256)):
            memory, args = oracle.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            models = [oracle.FaultOracle(w, memory, args, phase=phase).run()
                for w in (self.retail, legacy, prior, self.banked_words, rejected, self.words)]
            counts = [m.accesses for m in models]
            self.assertLessEqual(abs(counts[0] - counts[5]), abs(counts[0] - counts[3]))
            for index in range(3):
                if abs(counts[0] - counts[4]) > abs(counts[0] - counts[index + 1]):
                    failures[index].append((mode, count, fixed, phase, enabled))
        self.assertEqual(list(map(len, failures)), [8, 48, 48])
        self.assertTrue(all((m, c, enabled) == (1, 0, 0) for m, c, _, _, enabled in failures[0]))
        self.assertTrue(set(failures[0]).issubset(failures[1]))
        self.assertEqual(failures[1], failures[2])
        self.assertEqual((diagnostic[36], diagnostic[40]), (0x27B801A0, 0x8F110000))
        self.receipt('home-controls', forms=21, records=records, rejection_domains=failures,
            reference_scores=[333, 331, 259], rejection_counts=[8, 48, 48],
            historical_and_current_rejections_retained=True, all192_selected_count_distances_never_worse=True,
            equal329_scores_hide_11_or_15_word_changes=True, previous407_diagnostic_distinct=True)

    def test_23_retail_profile_is_required_for_the_recovered_opening(self):
        records = []
        memory, args = oracle.fixture(0, 1, 0)
        for profile, expected in (('o2', (486, 400, 257)), ('o1g3', (556, 312, 539)), ('o1', (556, 312, 539))):
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, self.body, profile)
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected)
            self.assertNotEqual(words[:22], self.retail[:22])
            records.append(dict(profile=profile, words=meta['body_words'], frame=meta['frame'], differences=meta['differences']))
            if profile == 'o2':
                states = []
                for w in (self.retail, words):
                    model = oracle.FaultOracle(w, memory, args, fault=1)
                    with self.assertRaises(oracle.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, 1)
                    states.append(state(model))
                self.assertNotEqual(states[0], states[1])
        self.receipt('profiles', selected='o2g3', records=records,
            bare_o2_same_extent_frame_but_opening_fault_negative=True,
            o1_variants_wrong_extent_and_frame_not_installed=True, production_profile_unchanged=True)


if __name__ == '__main__':
    unittest.main()
