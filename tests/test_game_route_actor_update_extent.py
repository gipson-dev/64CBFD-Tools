"""Complete ranking-cursor recovery; diagnostic alignment earns no matching credit."""
import hashlib
import itertools
import json
import struct
import unittest

from tools.experiments import game_route_actor_update_extent as extent
from tools.tests import test_game_route_actor_update as old


class RouteActorUpdateExtentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.RouteActorUpdateTests.setUpClass.__func__(cls)
        cls.out = cls.root / extent.BUILD
        cls.obj, cls.candidate, cls.row = extent.qualify(cls.root, cls.out)

    compare = old.RouteActorUpdateTests.compare

    def receipt(self, name, **values):
        values.update(raw_model_SHA256=extent.RAW_SHA, model_name=extent.SELECTED_NAME)
        (self.out / ('selected-cursor-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_point_frame_and_binding_controls(self):
        raw, bindings = extent.checked(self.obj)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (594, 456, 481))
        self.assertEqual(self.candidate[:15], self.retail[:15])
        self.assertEqual(self.candidate[-11:], self.retail[-11:])
        self.assertNotIn('volatile', extent.selected())
        self.assertEqual(extent.selected().count('(s32)D_800D23'), 3)
        for i in range(594):
            damaged = bytearray(raw)
            damaged[i * 4] ^= 1
            with self.assertRaises(ValueError):
                extent.check_payload(damaged, bindings)
        for at in bindings:
            damaged = dict(bindings)
            damaged[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                extent.check_payload(raw, damaged)
        self.receipt('point', words=594, missing_words=10, frame=456, differences=481,
            first15_and_last11_words_exact=True, word_controls=594, binding_controls=len(bindings),
            no_volatile_or_narrowed_conversion_in_selected_source=True, installed=False)

    def test_02_call_anchors_localize_but_do_not_normalize(self):
        old_blocks = extent.analyze(self.root, self.out)['blocks']
        blocks = extent.call_blocks(self.retail, self.candidate)
        self.assertEqual(len(blocks), 21)
        self.assertEqual([(r['block'], r['missing_words']) for r in blocks if r['missing_words']],
            [(3, 1), (4, -1), (13, 7), (19, 2), (20, 1)])
        self.assertEqual(old_blocks[:-1], blocks[:-1])
        self.assertEqual((old_blocks[-1]['raw_words'], blocks[-1]['raw_words']), (108, 113))
        self.assertEqual(sum(r['missing_words'] for r in blocks), 10)
        damaged = list(self.candidate)
        call = next(i for i, w in enumerate(damaged) if w >> 26 == 3)
        damaged[call] ^= 1
        with self.assertRaises(ValueError):
            extent.call_blocks(self.retail, damaged)
        # Diagnostic shape equality deliberately omits real physical differences.
        self.assertNotEqual(self.retail[15], self.candidate[15])
        self.assertEqual(extent.shape(self.retail[15]), extent.shape(self.candidate[15]))
        self.receipt('blocks', blocks=blocks, five_words_recovered_only_in_ranking_tail=True,
            alignment_not_matching_or_instruction_rewriting=True, changed_call_control_rejected=True)

    test_03_complete_real_helpers = old.RouteActorUpdateTests.test_02_complete_caller_with_494_real_helper_words
    test_04_effectful_providers = old.RouteActorUpdateTests.test_03_effectful_selection_event_and_signed_tick_refresh
    test_05_ranking_and_ties = old.RouteActorUpdateTests.test_05_signed_lap_scores_stable_ties_and_all_17_slots
    test_06_widths_and_actor_sign = old.RouteActorUpdateTests.test_06_null_table_modular_index_and_signed_actor
    test_07_active_and_ticks = old.RouteActorUpdateTests.test_07_full_width_active_and_signed_tick_divisor
    test_08_error_limits = old.RouteActorUpdateTests.test_08_exact_error_limits_and_eleven_iteration_stop
    test_09_actual_caller_windows = old.RouteActorUpdateTests.test_11_whole_Game_direct_scan_and_both_actual_caller_windows

    def test_10_effective_complete_point_semantic_negatives(self):
        b = extent.selected()
        forms = {
            'upper-inclusive': b.replace('50.0f < error', '50.0f <= error'),
            'ten-iterations': b.replace('iterations >= 11', 'iterations >= 10'),
            'unsigned-old-tick': b.replace('(f32)(s8)record[0x32]', '(f32)record[0x32]'),
            'byte-active-test': b.replace('if (active == 0)', 'if ((u8)active == 0)'),
            'half-lookahead': b.replace('lookAhead + lookAhead', 'lookAhead'),
            'unsigned-lap': b.replace('(f32)(s8)cursor[0x2A]', '(f32)cursor[0x2A]'),
            'ascending-rank': b.replace('valueX < *(f32 *)(cursor + 4)', 'valueX > *(f32 *)(cursor + 4)'),
        }
        for name, body in forms.items():
            self.assertNotEqual(body, b)
            _, wrong, row = old.source.measure(self.root, self.out, 'negative-cursor-' + name, body)
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
        self.receipt('semantic-controls', effective_ordinary_wrong_results=len(forms))

    def test_11_all_19_bounded_source_screens(self):
        cases = 0
        groups = dict(conversions='conversion', spills='spill', ranking='ranking', cursors='cursor', typed='typed')
        banks = {self.out / (name + '-screens.json'): (self.out / (name + '-screens.json')).read_bytes()
                 for name in groups.values()}
        for group, prefix in groups.items():
            rows = json.loads((self.out / (prefix + '-screens.json')).read_text())
            forms = dict(extent.GROUPS[group]())
            self.assertEqual(len(rows), len(forms))
            for row in rows:
                name = row['name']
                self.assertEqual((row['neighbors'], row['diagnostics']), (72, ''))
                self.assertEqual((self.out / (name + '.c')).read_text(), old.source.recovered_owner(
                    self.values['conker/src/game/generated_B3020.c'].decode(), forms[name]))
                obj = self.out / (name + '.o')
                text, definitions, _ = old.source.parse_object(obj)
                d = definitions[old.source.FUNCTION]
                self.assertEqual(hashlib.sha256(text[d['value']:d['value'] + d['size']]).hexdigest(), row['raw_sha256'])
                image, functions = old.source.prior.link_owner(self.root, self.out, obj, old.source.OWNER)
                f = functions[old.source.FUNCTION]
                words = list(struct.unpack_from('>%dI' % (f['size'] // 4), image, f['value']))
                self.assertEqual(len(extent.call_blocks(self.retail, words)), 21)
                for index, mode, phase in itertools.product((0, 1), (0, 1, 128), (0, 8)):
                    memory, args = old.fixture(index=index, mode=mode, real=True)
                    self.compare(memory, args, phase, bodies=(self.retail, words))
                    cases += 1
        self.assertEqual(cases, 228)
        self.receipt('screens', screens=19, additional_guest_cases=cases, all72_neighbors_and_pools_preserved=True,
            volatile_and_narrowed_domain_controls_not_selected=True, production_installable_screens=0)
        self.assertEqual({path: path.read_bytes() for path in banks}, banks)

    def test_12_fired_opening_prefixes_still_reject_argument_roles(self):
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
                    self.assertEqual(pair[0].current_pc, 0x150873A4)
                    self.assertEqual(pair[1].current_pc, 0x150873A4)
                    self.assertEqual([r for r in range(32) if pair[0].r[r] != pair[1].r[r]], [14, 24])
            states.append(dict(phase=phase, cut=cut, equal=cut < 14))
        self.receipt('opening-boundary', fired=34, equal=28, rejected=6, first_reject_PC='150873A4',
            differing_GPRs=[14, 24], states=states, full_private_or_hardware_trap_equivalence_not_claimed=True)

    def test_13_normal_profile_neighbors_and_projection_override(self):
        before = self.values['conker/src/game/generated_B3020.c'].decode()
        baseline, first = old.source.prior.compile_profile(self.root, self.out, before, 'normal-before', True)
        candidate, second = old.source.prior.compile_profile(self.root, self.out,
            old.source.recovered_owner(before, extent.selected()), 'normal-cursor', True)
        self.assertEqual((first, second), ('', ''))
        model = old.source.previous.source.installed.source.model
        self.assertEqual(model.same_functions(baseline, candidate, (old.source.FUNCTION,)), 72)
        self.assertEqual(old.source.normalized_pools(baseline), old.source.normalized_pools(candidate))
        old.source.prior.candidate.checked(candidate)
        for label in ('normal-before', 'normal-cursor'):
            command = json.loads((self.out / (label + '-command.json')).read_text())
            self.assertNotIn('-Wo,-loopunroll,0', command)
        self.receipt('normal-profile', neighbors=72, pools_unchanged=True,
            projection_override_raw_words_and_bindings_preserved=True, production_Make_or_padding_not_claimed=True)

    def test_14_production_and_prior_evidence_are_frozen(self):
        old.source.freeze(self.root, self.out)
        old.source.freeze(self.root, self.root / extent.prior.BUILD)
        self.assertFalse(self.row['installed'])
        self.assertEqual(self.row['matching_credit'], 0)
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        lo, hi = old.source.function_span(owner, old.source.FUNCTION)
        self.assertEqual(owner[lo:hi], 's32 func_15087350() {\n    return 0;\n}')

    def test_15_coordinate_narrowing_retains_the_32_bit_conversion(self):
        cases = 0
        for value, phase in itertools.product((32768., -32769., 65535., -65535., 16777216., -16777216.), (0, 8)):
            memory, args = old.fixture(mode=1, active=0, position=(value, -value), real=True)
            old.put(memory, old.ACTORS + 0x18, old.bits(value))
            self.compare(memory, args, phase)
            cases += 1
        self.receipt('wide-coordinates', cases=cases, coordinates_outside_signed_16_range=True,
            finite_signed_32_float_conversion_domain=True, direct_float_to_short_native_C_domain_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
