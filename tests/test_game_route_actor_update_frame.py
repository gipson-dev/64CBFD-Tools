"""Owned compiler evidence and full-body frame recovery, without matching credit."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_fit as fit
from tools.experiments import game_route_actor_update_frame as capture
from tools.tests import test_game_route_actor_update as old


class RouteActorUpdateFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.RouteActorUpdateTests.setUpClass.__func__(cls)
        cls.out = cls.root / fit.BUILD
        cls.obj, cls.candidate, cls.row = fit.qualify(cls.root, cls.out)
        cls.capture_out = cls.root / capture.BUILD
        cls.evidence = capture.audit(cls.root, cls.capture_out)

    compare = old.RouteActorUpdateTests.compare

    def receipt(self, name, **values):
        values.update(raw_model_SHA256=fit.RAW_SHA, model_name=fit.SELECTED_NAME)
        (self.out / ('bound-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_completed_owned_capture_and_upstream_frame(self):
        with patch.object(capture, 'capture', side_effect=AssertionError('Do not relaunch GDB')):
            result = capture.audit(self.root, self.capture_out)
        self.assertTrue(result['code_unchanged'])
        self.assertEqual(result['qualified']['raw_SHA256'], old.source.RAW_SHA)
        self.assertEqual(result['qualified']['bindings'], 70)
        self.assertEqual(result['lifecycle']['child_and_driver_exit_codes'], [0] * 5)
        self.assertTrue(result['lifecycle']['final_inferior_null'])
        facts = result['facts']
        self.assertEqual((facts['frontend_local_bytes'], facts['optimized_local_bytes'],
            facts['saved_bytes'], facts['outgoing_bytes'], facts['frame_bytes']), (396, 416, 48, 16, 480))
        self.assertEqual(facts['optimized_lower_home_dtype'], 'J')
        self.assertTrue(facts['extra_local_bytes_exist_before_UGEN'])
        self.assertFalse(result['installed'])
        self.receipt('compiler-frame', facts=facts, reused_completed_capture=True,
            normal_words_bindings_definitions_and_pools_equal=True, debugger_launches_in_suite=0)

    def test_02_effective_frame_and_wire_fact_controls(self):
        original = self.evidence['observations']
        controls = []
        for key, value in (('frame', 479), ('locals', 400), ('saved', 56), ('outgoing', 8),
                           ('temporary', 4), ('temp_base', 1), ('pool', [{'pointer': 1}])):
            damaged = copy.deepcopy(original)
            damaged['events'][-1][key] = value
            controls.append(damaged)
        damaged = copy.deepcopy(original)
        damaged['events'].pop(0)
        controls.append(damaged)
        for stage in ('frontend', 'optimizer'):
            for storage in ('M', 'P'):
                damaged = copy.deepcopy(original)
                next(r for r in damaged['records'][stage] if r['name'] == 'def' and r['storage'] == storage)['length'] += 4
                controls.append(damaged)
            damaged = copy.deepcopy(original)
            next(r for r in damaged['records'][stage] if r['name'] == 'ent')['block'] += 1
            controls.append(damaged)
        for offset in (-56, -72, -88, -228, -260, -328):
            damaged = copy.deepcopy(original)
            for r in damaged['records']['frontend']:
                if r['name'] == 'lda' and r['storage'] == 'M' and r['offset'] == offset:
                    r['length'] += 1
            controls.append(damaged)
        for key, value in (('dtype', 'L'), ('length', 8), ('block', 770), ('offset', -408)):
            damaged = copy.deepcopy(original)
            next(r for r in damaged['records']['optimizer'] if r['storage'] == 'M' and r['offset'] == -404)[key] = value
            controls.append(damaged)
        for damaged in controls:
            with self.assertRaises(ValueError):
                capture.frame_facts(damaged)
        self.receipt('frame-fact-controls', effective_controls=len(controls))

    def test_03_lifecycle_and_retained_input_payload_controls(self):
        work = self.capture_out / 'selected'
        log = (work / 'debugger.txt').read_text()
        controls = [re.sub(r'(?m)^TRACE_EXIT inferior=%d code=0\n' % i, '', log) for i in (2, 3, 4, 5, 1)]
        for name in ('cfe', 'uopt', 'ugen', 'as1'):
            controls.append(log.replace('executing new program: ' + str(self.root / 'ido/ido5.3_recomp' / name),
                                        'executing new program: /wrong/' + name))
        controls += [log + '\nTRACE_EXIT inferior=1 code=0\n', log.replace('<null>', '<running>')]
        for damaged in controls:
            with self.assertRaises(ValueError):
                capture.lifecycle(self.root, damaged)
        files = ('frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json')
        with tempfile.TemporaryDirectory(prefix='cbfd-route-frame-') as directory:
            target = Path(directory)
            for name in files:
                shutil.copyfile(work / name, target / name)
            self.assertEqual(capture.frame_facts(capture.frame.validate_observations(target, log)), self.evidence['facts'])
            for name in files:
                before = (target / name).read_bytes()
                if name.endswith('.ucode'):
                    damaged = bytearray(before)
                    damaged[0] ^= 1
                    (target / name).write_bytes(damaged)
                elif name == 'ucode-table.json':
                    table = json.loads(before)
                    next(row for row in table if row['name'] == 'lda')['name'] = 'bad'
                    (target / name).write_text(json.dumps(table))
                else:
                    types = json.loads(before)
                    types['dtypes'] = types['dtypes'].replace('J', 'L')
                    (target / name).write_text(json.dumps(types))
                with self.assertRaises(ValueError):
                    capture.frame_facts(capture.frame.validate_observations(target, log))
                (target / name).write_bytes(before)
        self.receipt('capture-controls', lifecycle_controls=len(controls), payload_controls=4,
            originals_preserved=True, new_debugger_launches=0)

    def test_04_frame_point_words_bindings_and_saved_layout(self):
        raw, bindings = fit.checked(self.obj)
        words = list(struct.unpack('>589I', raw))
        self.assertEqual(self.candidate[:15], self.retail[:15])
        self.assertEqual(self.candidate[-11:], self.retail[-11:])
        self.assertEqual((self.retail[15], self.candidate[15]), (0x8FB801C8, 0x8FAE01C8))
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (589, 456, 481))
        prologue = words[:next(i for i, w in enumerate(words) if w >> 26 == 15)]
        gp = [(w >> 16 & 31, w & 65535) for w in prologue if w >> 26 == 43 and w >> 16 & 31 >= 16]
        fp = [(w >> 16 & 31, w & 65535) for w in prologue if w >> 26 == 61]
        self.assertEqual(gp, [(31, 68), (20, 64), (19, 60), (18, 56), (17, 52), (16, 48)])
        self.assertEqual(fp, [(24, 40), (22, 32), (20, 24)])
        for i in range(589):
            damaged = bytearray(raw)
            damaged[i * 4] ^= 1
            with self.assertRaises(ValueError):
                fit.check_payload(damaged, bindings)
        for at in bindings:
            damaged = dict(bindings)
            damaged[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                fit.check_payload(raw, damaged)
        self.receipt('frame-point', words=589, frame=456, missing_words=15, differences=481,
            saved_GPRs=gp, saved_FP_pairs=fp, raw_word_controls=589, binding_controls=len(bindings),
            first15_words_exact=True, last11_words_exact=True, saved_layout_exact=True, installed=False)

    test_05_complete_caller_real_helpers = old.RouteActorUpdateTests.test_02_complete_caller_with_494_real_helper_words
    test_06_effectful_providers = old.RouteActorUpdateTests.test_03_effectful_selection_event_and_signed_tick_refresh
    test_07_ranking_and_ties = old.RouteActorUpdateTests.test_05_signed_lap_scores_stable_ties_and_all_17_slots
    test_08_widths_and_actor_sign = old.RouteActorUpdateTests.test_06_null_table_modular_index_and_signed_actor
    test_09_active_and_signed_ticks = old.RouteActorUpdateTests.test_07_full_width_active_and_signed_tick_divisor
    test_10_error_limits = old.RouteActorUpdateTests.test_08_exact_error_limits_and_eleven_iteration_stop
    test_11_actual_caller_windows = old.RouteActorUpdateTests.test_11_whole_Game_direct_scan_and_both_actual_caller_windows

    def test_12_effective_frame_point_semantic_negatives(self):
        b = fit.selected()
        forms = {
            'upper-inclusive': b.replace('50.0f < error', '50.0f <= error'),
            'ten-iterations': b.replace('iterations >= 11', 'iterations >= 10'),
            'unsigned-old-tick': b.replace('(f32)(s8)record[0x32]', '(f32)record[0x32]'),
            'byte-active-test': b.replace('if (active == 0)', 'if ((u8)active == 0)'),
            'half-lookahead': b.replace('lookAhead + lookAhead', 'lookAhead'),
            'unsigned-lap': b.replace('(f32)(s8)cursor[0x2A]', '(f32)cursor[0x2A]'),
            'ascending-rank': b.replace('scores[i] < scores[i + 1]', 'scores[i] > scores[i + 1]'),
        }
        for name, body in forms.items():
            self.assertNotEqual(body, b)
            _, wrong, row = old.source.measure(self.root, self.out, 'negative-frame-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            if name in ('upper-inclusive', 'ten-iterations'):
                memory, args = old.fixture(index=1, mode=1, position=(-34. if name == 'upper-inclusive' else -4096., 0.))
                old.put(memory, old.RECORDS + 132 + 8, old.bits(.25))
                pair = [old.UpdateOracle(w, memory, args, steps=(64., 10., 0.)).run() for w in (self.retail, wrong)]
            else:
                memory, args = old.fixture(mode=1, active=256 if name == 'byte-active-test' else 1, real=True)
                old.put(memory, old.RECORDS + 0x33, 255, 1)
                old.put(memory, old.RECORDS + 132 + 0x2A, 255, 1)
                pair = [old.UpdateOracle(w, memory, args, helpers=self.helpers).run() for w in (self.retail, wrong)]
            self.assertNotEqual((old.public(pair[0].memory), pair[0].provider_calls),
                                (old.public(pair[1].memory), pair[1].provider_calls), name)
        self.receipt('frame-semantic-controls', effective_ordinary_wrong_results=len(forms))

    def test_13_fired_opening_prefixes_and_argument_register_rejection(self):
        states = []
        for phase, cut in itertools.product((0, 8), range(17)):
            memory, args = old.fixture(real=True)
            pair = [old.UpdateOracle(w, memory, args, phase, self.helpers) for w in (self.retail, self.candidate)]
            observed = []
            for model in pair:
                model.access_fault = cut
                with self.assertRaises(old.base.faults.AccessBoundary):
                    model.run()
                self.assertEqual(model.all_accesses, cut)
                observed.append((model.memory, model.r, model.f, model.events, model.calls,
                    model.current_pc, model.delay_of, model.lo, model.condition))
            if cut < 14:
                self.assertEqual(observed[0], observed[1])
            else:
                self.assertNotEqual(observed[0], observed[1])
                if cut == 14:
                    self.assertEqual(pair[0].memory, pair[1].memory)
                    self.assertEqual(pair[0].f, pair[1].f)
                    self.assertEqual(pair[0].events, pair[1].events)
                    self.assertEqual(pair[0].current_pc, pair[1].current_pc)
                    self.assertNotEqual(pair[0].r, pair[1].r)
                    self.assertEqual([r for r in range(32) if pair[0].r[r] != pair[1].r[r]], [14, 24])
            states.append(dict(phase=phase, cut=cut, equal=cut < 14,
                retail_PC=pair[0].current_pc, raw_PC=pair[1].current_pc,
                differing_GPRs=[r for r in range(32) if pair[0].r[r] != pair[1].r[r]]))
        self.receipt('opening-boundary', fired=34, equal=28, rejected=6, states=states,
            RAM_GPR_FPR_accesses_calls_PC_delay_compared=True,
            differing_instruction_words_and_hardware_traps_not_equated=True,
            original_save_and_argument_homes_restored=True, first_argument_temporary_registers_still_wrong=True)

    def test_14_all_25_source_screens_and_finite_semantics(self):
        rows = sum((json.loads((self.out / name).read_text()) for name in
                    ('screens.json', 'role-screens.json', 'local-screens.json')), [])
        forms = dict((*fit.forms(), *fit.role_forms(), *fit.local_forms()))
        self.assertEqual((len(rows), len(forms)), (25, 25))
        cases = 0
        for row in rows:
            name = row['name']
            self.assertEqual((row['neighbors'], row['diagnostics']), (72, ''))
            self.assertEqual((self.out / (name + '.c')).read_text(), old.source.recovered_owner(
                self.values['conker/src/game/generated_B3020.c'].decode(), forms[name]))
            image, functions = old.source.prior.link_owner(self.root, self.out, self.out / (name + '.o'), old.source.OWNER)
            text, definitions, _ = old.source.parse_object(self.out / (name + '.o'))
            d = definitions[old.source.FUNCTION]
            self.assertEqual(hashlib.sha256(text[d['value']:d['value'] + d['size']]).hexdigest(), row['raw_sha256'])
            f = functions[old.source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size'] // 4), image, f['value']))
            for index, mode, phase in itertools.product((0, 1), (0, 1, 128), (0, 8)):
                memory, args = old.fixture(index=index, mode=mode, real=True)
                self.compare(memory, args, phase, bodies=(self.retail, words))
                cases += 1
        self.receipt('scalar-screens', screens=25, additional_guest_cases=cases,
            all72_owner_neighbors_and_pools_preserved=True, production_installable_screens=0,
            register_keyword_forms_emit_unchanged_words=True)

    def test_15_production_and_prior_evidence_remain_frozen(self):
        old.source.freeze(self.root, self.out)
        old.source.freeze(self.root, self.capture_out)
        self.assertEqual(self.row['neighbors'], 72)
        self.assertFalse(self.row['installed'])
        self.assertEqual(self.row['matching_credit'], 0)
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        lo, hi = old.source.function_span(owner, old.source.FUNCTION)
        self.assertEqual(owner[lo:hi], 's32 func_15087350() {\n    return 0;\n}')

    def test_16_bound_phase_screens_keep_complete_semantics(self):
        rows = json.loads((self.out / 'bound-screens.json').read_text())
        forms = dict(fit.bound_forms())
        self.assertEqual((len(rows), len(forms)), (6, 6))
        cases = 0
        for row in rows:
            name = row['name']
            self.assertEqual((row['neighbors'], row['diagnostics']), (72, ''))
            self.assertEqual((self.out / (name + '.c')).read_text(), old.source.recovered_owner(
                self.values['conker/src/game/generated_B3020.c'].decode(), forms[name]))
            image, functions = old.source.prior.link_owner(self.root, self.out, self.out / (name + '.o'), old.source.OWNER)
            f = functions[old.source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size'] // 4), image, f['value']))
            for index, mode, phase in itertools.product((0, 1), (0, 1, 128), (0, 8)):
                memory, args = old.fixture(index=index, mode=mode, real=True)
                self.compare(memory, args, phase, bodies=(self.retail, words))
                cases += 1
        self.receipt('bound-screens', screens=6, additional_guest_cases=cases,
            full_width_modular_offset_kept_until_gate=True, signed_bound_cast_after_phase_change=True)

    def test_17_normal_profile_neighbors_and_projection_override(self):
        before = self.values['conker/src/game/generated_B3020.c'].decode()
        baseline, first = old.source.prior.compile_profile(self.root, self.out, before, 'normal-before', True)
        candidate, second = old.source.prior.compile_profile(self.root, self.out,
            old.source.recovered_owner(before, fit.selected()), 'normal-bound', True)
        self.assertEqual((first, second), ('', ''))
        model = old.source.previous.source.installed.source.model
        self.assertEqual(model.same_functions(baseline, candidate, (old.source.FUNCTION,)), 72)
        self.assertEqual(old.source.normalized_pools(baseline), old.source.normalized_pools(candidate))
        old.source.prior.candidate.checked(candidate)
        for label in ('normal-before', 'normal-bound'):
            command = json.loads((self.out / (label + '-command.json')).read_text())
            self.assertNotIn('-Wo,-loopunroll,0', command)
        self.receipt('normal-profile', neighbors=72, pools_unchanged=True,
            original_projection_override_raw_words_and_bindings_exact=True,
            primary_and_normal_profiles_keep_their_existing_flags=True,
            production_Make_padder_or_installation_not_claimed=True)

    def test_18_existing_capture_is_rejected_before_baseline_rewrite(self):
        paths = [self.capture_out / n for n in ('isolated.c', 'isolated.o', 'isolated.json')]
        before = [p.read_bytes() for p in paths]
        with patch.object(capture, 'qualify', side_effect=AssertionError('Baseline rewrite')), \
                patch.object(capture.frame, 'fingerprints', side_effect=AssertionError('Capture setup')):
            with self.assertRaisesRegex(ValueError, 'Capture directory already exists'):
                capture.capture(self.root, self.capture_out)
        self.assertEqual([p.read_bytes() for p in paths], before)
        self.receipt('recapture-guard', existing_capture_rejected_before_any_setup_or_rewrite=True,
            evidence_source_object_and_metadata_preserved=True, new_debugger_launches=0)


if __name__ == '__main__':
    unittest.main()
