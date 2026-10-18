"""Source-derived local homes and error lifetime, with prior point kept separate."""
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_actor_update_storage as source
from tools.experiments import game_route_actor_update_native as native
from tools.tests import test_game_route_actor_update_native as previous
from tools.tests import test_game_route_actor_update as guest


class RouteActorUpdateRolesTests(previous.RouteActorUpdateNativeTests):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        source.qualify(root, root / source.BUILD)
        for target, attribute, value in ((native, 'source', source),
                                          (native, 'BUILD', source.BUILD + '/native')):
            context = patch.object(target, attribute, value)
            context.start()
            cls.addClassCleanup(context.stop)
        previous.RouteActorUpdateNativeTests.setUpClass.__func__(cls)

    def test_07_selected_words_bindings_and_block_lengths(self):
        raw, bindings = source.checked(self.root / source.BUILD / 'qualified-cursor.o')
        row = json.loads((self.root / source.BUILD / 'qualified-cursor.json').read_text())
        self.assertEqual((row['words'], row['frame'], row['differences'], row['neighbors']), (594, 456, 450, 72))
        self.assertEqual(self.candidate[:15], self.retail[:15])
        self.assertEqual(self.candidate[-11:], self.retail[-11:])
        self.assertEqual([(r['block'], r['missing_words']) for r in row['call_anchored_blocks'] if r['missing_words']],
            [(13, 7), (19, 2), (20, 1)])
        for i in range(594):
            damaged = bytearray(raw)
            damaged[4 * i] ^= 1
            with self.assertRaises(ValueError):
                source.check_payload(damaged, bindings)
        for at in bindings:
            damaged = dict(bindings)
            damaged[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                source.check_payload(raw, damaged)
        self.receipt('selected-roles', words=594, frame=456, differences=450, missing_words=10,
            raw_word_controls=594, binding_controls=len(bindings), early_advance_and_event_block_extents_restored=True,
            no_guards_normalizer_padding_or_installation=True)

    def test_08_recovered_private_arrays_and_core_home_payloads(self):
        cases = 0
        for index, mode, phase, position, effect in itertools.product((0, 1), (0, 1, 2, 128), (0, 8),
                ((20., 10.), (-300., 100.)), (0, 5)):
            memory, args = native.fixture(dict(index=index, mode=mode, position=position), native.static_constants(self.root))
            pair = self.compare(memory, args, phase, effect=effect)
            frame = pair[0].r[29] - 456
            self.assertEqual(pair[1].r[29] - 456, frame)
            for model in pair:
                for target, values in model.calls:
                    if target == guest.VECTOR:
                        self.assertEqual(values[1:], (frame + 0x184, frame + 0x174, frame + 0x164))
                    elif target == guest.DERIVATIVE:
                        self.assertIn((values[0] - frame, values[3] - frame), ((0x184, 0x1B4), (0x164, 0x1B0)))
                    elif target == guest.COPY:
                        self.assertEqual(values[1:], (frame + 0xD4, 132))
                for offset in (0x15C, 0x19C, 0x1A0, 0x1AC, 0x1B0, 0x1B4, 0x1B8, 0x1BC):
                    self.assertEqual(guest.read(model.memory, frame + offset), guest.read(pair[0].memory, frame + offset))
                self.assertEqual(guest.read(model.memory, frame + 0x15A, 1), guest.read(pair[0].memory, frame + 0x15A, 1))
                for start, length in ((0x164, 48), (0xD4, 132), (0xB4, 32), (0x70, 68)):
                    self.assertEqual([model.memory[frame + start + j] for j in range(length)],
                        [pair[0].memory[frame + start + j] for j in range(length)])
            cases += 1
        self.assertEqual(cases, 64)
        self.receipt('recovered-homes', guest_cases=cases, both_stack_phases=True,
            arrays=dict(x=0x184, y=0x174, z=0x164, copy=0xD4, order=0xB4, scores=0x70),
            scalar_homes=[0x15C, 0x15A, 0x19C, 0x1A0, 0x1AC, 0x1B0, 0x1B4, 0x1B8, 0x1BC],
            physical_helper_arguments_and_complete_array_payloads_equal=True,
            error_and_offset_and_conversion_homes_or_full_private_state_not_claimed=True)

    def test_09_opening_private_state_still_rejects(self):
        states = []
        for phase, cut in itertools.product((0, 8), range(17)):
            memory, args = native.fixture({}, native.static_constants(self.root))
            pair = [guest.UpdateOracle(w, memory, args, phase, self.helpers) for w in (self.retail, self.candidate)]
            observed = []
            for model in pair:
                model.access_fault = cut
                with self.assertRaises(guest.base.faults.AccessBoundary):
                    model.run()
                self.assertEqual(model.all_accesses, cut)
                observed.append((model.memory, model.r, model.f, model.events, model.calls,
                    model.current_pc, model.delay_of, model.lo, model.condition))
            if cut < 14:
                self.assertEqual(observed[0], observed[1])
            else:
                self.assertNotEqual(observed[0], observed[1])
            states.append(dict(phase=phase, cut=cut, equal=cut < 14))
        self.receipt('remaining-opening-boundary', fired=34, equal=28, rejected=6, states=states,
            first_argument_temporary_registers_still_differ=True, hardware_trap_equivalence_not_claimed=True)

    def test_10_normal_profile_neighbors_and_alternate_flag_controls(self):
        out = self.root / source.BUILD
        before = self.values['conker/src/game/generated_B3020.c'].decode()
        a, first = source.source.prior.compile_profile(self.root, out, before, 'normal-before', True)
        b, second = source.source.prior.compile_profile(self.root, out,
            source.source.recovered_owner(before, source.selected()), 'normal-roles', True)
        self.assertEqual((first, second), ('', ''))
        model = source.source.previous.source.installed.source.model
        self.assertEqual(model.same_functions(a, b, (source.source.FUNCTION,)), 72)
        self.assertEqual(source.source.normalized_pools(a), source.source.normalized_pools(b))
        source.source.prior.candidate.checked(b)
        rows = json.loads((out / 'profile-screens.json').read_text())
        self.assertEqual([(r['words'], r['frame'], r['differences']) for r in rows], [(593, 456, 596), (691, 400, 684)])
        for row in rows:
            command = json.loads((out / (row['name'] + '-command.json')).read_text())
            self.assertIn(row['optimization'], command)
            self.assertIn('-g0', command)
            self.assertNotIn('-g3', command)
            self.assertTrue(row['diagnostic_profile_not_original_flag_claim'])
        self.receipt('profiles', normal_neighbors=72, pools_and_projection_override_preserved=True,
            alternate_profiles_diagnostic_only=True, production_profile_unchanged=True)

    test_11_exact_error_limits = guest.RouteActorUpdateTests.test_08_exact_error_limits_and_eleven_iteration_stop
    test_12_actual_caller_windows = guest.RouteActorUpdateTests.test_11_whole_Game_direct_scan_and_both_actual_caller_windows

    def test_13_previous_source_point_and_native_receipts_are_retained(self):
        old = source.prior
        old.checked(self.root / old.BUILD / 'qualified-cursor.o')
        result = json.loads((self.root / 'conker/build/game-route-actor-update-native/native32.json').read_text())
        self.assertEqual(result['raw_target_SHA256'], old.RAW_SHA)
        self.assertNotEqual(result['raw_target_SHA256'], source.RAW_SHA)
        with patch.object(native, 'source', old):
            for body in native.controls().values():
                self.assertNotEqual(body, old.selected())
        self.receipt('prior-point-retained', original594_point_and_native_receipts_preserved=True,
            legacy_comparison_controls_still_effective_as_source_edits=True, old_native_builds_not_reclaimed_as_fresh=True)


if __name__ == '__main__':
    import unittest
    unittest.main()
