"""Complete renderer with actual color/fog and both matrix chains, not hardware."""
import csv
import hashlib
import itertools
import json
import struct
import unittest
from pathlib import Path

from tools.experiments import game_actor_renderer_matching as screen
from tools.experiments import game_actor_renderer_connected as chain
from tools.tests import test_game_actor_renderer_schedule as schedule
from tools.tests import test_game_actor_renderer_recovery as proof
from tools.pad_generated_object import emit_padded_assembly


class GameActorRendererConnectedTests(unittest.TestCase):
    assemble = classmethod(schedule.GameActorRendererScheduleTests.assemble.__func__)
    write_rows = classmethod(schedule.GameActorRendererScheduleTests.write_rows.__func__)
    link = classmethod(schedule.GameActorRendererScheduleTests.link.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-connected-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.bodies, cls.data = chain.load_helpers(cls.root)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>532I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        with (cls.out / 'before-guards').open(newline='') as stream:
            cls.fields = csv.DictReader(stream).fieldnames
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split('glabel ' + screen.FUNCTION, 1)[1].split(
            'endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot = cls.out / 'slot.s'
        cls.slot.write_text('glabel ' + screen.FUNCTION + assembly + 'endlabel ' + screen.FUNCTION + '\n')
        cls.write_rows(cls.out / 'isolated.csv', screen.guard_rows(cls.out / 'selected.o'))
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80'))
        cls.fitted = cls.link('fitted', proof.S)
        cls.coverage = set()

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def models(self, memory, arguments, phase=0, plan=None, cosine=0.5, caller=False, dispatch_plan=None):
        models = [chain.ConnectedOracle(words, memory, arguments, self.bodies, self.data,
            phase, plan, dispatch_plan, cosine, caller, chain.return_map() if index == 1 else None).run()
            for index, words in enumerate((self.retail, self.raw, self.fitted))]
        for model in models[1:]:
            self.assertEqual(chain.canonical(model), chain.canonical(models[0]))
        self.coverage.update(models[0].visits)
        return models

    def compare(self, memory, args, phase=0, plan=None, cosine=0.5):
        memory = {**memory, **self.data}
        expected, state, calls = chain.reference(memory, args, plan, cosine)
        models = self.models(memory, args, phase, plan, cosine)
        names = set(proof.COUNTS)
        for model in models:
            actual = (model.r[2], {a: value for a, value in model.memory.items() if proof.public(a)},
                [call for call in model.calls if call[1] in names])
            self.assertEqual(actual, (expected, {a: value for a, value in state.items() if proof.public(a)}, calls))
            self.assertIn(chain.COLOR, model.visits)
            self.check_colors(model, cosine)
        return models

    def check_colors(self, model, cosine=0.5):
        self.assertEqual(len(model.color_inputs), 1)
        captured, color_args = model.color_inputs[0]
        parameters = tuple(proof.guest.read(captured, color_args[3] + i * 4, 4) for i in range(4))
        expected = tuple(value & 0xFFFFFFFF for value in
            chain.colors(captured, color_args[0], chain.signed(color_args[1]), parameters, cosine))
        actual = tuple(proof.guest.read(model.memory, address, 4) for address in color_args[4:])
        self.assertEqual(actual, expected)

    def test_01_complete_candidate_and_banked_helper_shapes(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['diagnostics']), (531, 0x150, ''))
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(len(self.bodies[chain.COLOR]), 50)
        self.assertEqual(sum(len(body) for body in self.bodies.values()), 726)
        self.receipt('shape', renderer_words=532, raw_words=531, frame=0x150,
            actual_helpers={hex(entry): len(body) for entry, body in self.bodies.items()},
            color_from_full_retail_not_production_placeholder=True,
            ten_other_complete_helpers_banked_byte_exact=True, helper_rodata_exact=True)

    def test_02_actual_color_fog_and_identity_with_independent_public_reference(self):
        cases = 0
        for kind in range(256):
            view = (-1, 0, 3, 0x12340002)[kind % 4]
            slot, mode = (25 if kind & 1 else 0), (3 if kind & 1 else 0)
            memory = chain.fixture(slot, view, kind=kind, direct=83)
            args = (proof.OUTPUT, slot, view, 0x27000, -1, proof.PARAMETERS, mode, kind & 1)
            self.compare(memory, args, phase=8 if kind & 2 else 0, cosine=(-1.0, 0.5, 1.0)[kind % 3])
            cases += 1
        for direct in (0, 1, 254, 255, chain.FLOAT):
            for amount in (-100.0, -0.0, 0.0, 0.25, 10.25, 254.9, 255.0, 300.0):
                args = (proof.OUTPUT, 0, 3, 0x27000, 255, proof.PARAMETERS, 4, 1)
                self.compare(chain.fixture(view=3, kind=1, direct=direct, amount=amount), args)
                cases += 1
        for mode, page, count in itertools.product((0, 3, 4, 5, 6), (0, 1), (0, 1, 33)):
            args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, mode, 1)
            self.compare(chain.fixture(kind=6, count=count, page=page), args)
            cases += 1
        self.receipt('renderer', cases=cases, executions=cases * 3,
            independent_palette_fog_commands_cursor_public_state=True, original_fitted_full_private_memory_order_exact=True,
            raw_private_comparison_adjusts_only_proven_saved_return_PCs=True,
            full_50word_color_and_150word_fog_helpers_execute=True,
            full_110word_identity_chain_executes=True, all_256_fog_modes=True,
            finite_clamps_and_signed_fullwidth_views=True, cosine_explicitly_bounded=True)

    def test_03_complete_dispatch_RGB_shading_renderer_and_both_matrix_chains(self):
        cases = 0
        for slot, view, mode, enabled, w in itertools.product((0, 25), (0, 3), range(7), (0, 1), (0.0, 2.0, 10.0)):
            memory = chain.fixture(slot, view, kind=cases % 8, enabled=enabled,
                flags=4 if cases & 1 else 12, w=w)
            args = (proof.OUTPUT, slot, view, mode, cases & 1)
            models = self.models(memory, args, phase=8 if cases & 2 else 0,
                caller=True, dispatch_plan=chain.dispatch.Plan(second=254))
            actor = proof.S['D_800CC2D0'] + slot * 0x32C
            expected_rgb = tuple(255 - (memory[actor + 0x1DD + i] + memory[actor + 0x1E0 + i]) // 2
                for i in range(3)) if cases & 1 else (255, 255, 255)
            expected_alpha = chain.shading.semantic_alpha(memory, actor, view)[0] if enabled else 255
            for model in models:
                self.assertEqual(len(model.render_inputs), 1)
                captured, render_args = model.render_inputs[0]
                parameters = tuple(proof.guest.read(captured, render_args[5] + i * 4, 4) for i in range(4))
                self.assertEqual(parameters, (*expected_rgb, expected_alpha))
                self.assertIn(chain.RGB, model.visits)
                if enabled:
                    self.assertIn(chain.SHADING, model.visits)
                    self.assertTrue(set(range(chain.POINT, chain.POINT + 160, 4)).issubset(model.visits))
                expected, state, _ = chain.reference(captured, render_args, cosine=0.5)
                base = proof.guest.read(state, chain.dispatch.S['D_800BE9C8'] + memory[proof.S['D_800BE9C0']] * 4, 4)
                limit = proof.guest.read(state, chain.dispatch.S['D_800BEBA4'], 4)
                self.assertEqual(model.r[2], proof.OUTPUT if chain.signed(limit) < (chain.signed(expected - base) >> 3) else expected)
                self.assertEqual({a: value for a, value in model.memory.items() if proof.public(a)},
                    {a: value for a, value in state.items() if proof.public(a)})
                self.assertIn(chain.COLOR, model.visits)
                self.check_colors(model)
            cases += 1
        self.receipt('caller', cases=cases, executions=cases * 3, actual_dispatch_RGB_shading_renderer=True,
            caller_parameters_independently_checked=True, independent_renderer_public_reference=True,
            real_color_fog_point_and_identity_bodies=True, other_callbacks_and_cosine_bounded=True,
            whole_game_or_hardware_acceptance=False)

    def test_04_private_parameter_aliases_and_live_bounded_callback_mutations(self):
        cases = 0
        for phase in (0, 8):
            for parameters in (proof.PARAMETERS, proof.OUTPUT, proof.STACK + phase + 16,
                    proof.STACK + phase - 0x28, proof.STACK + phase - 0x4C):
                args = (proof.OUTPUT, 0, 0, 0x27000, 255, parameters, 0, 1)
                self.models(chain.fixture(kind=6), args, phase)
                cases += 1
            actor = proof.S['D_800CC2D0']
            for address, value, size in ((actor + 0xA4, 3, 1), (chain.PRIMITIVE, 254, 1),
                    (actor + 0x94, 0xFFFFFFFF, 4), (proof.CONFIG + 0x3E, 1, 2)):
                plan = proof.Plan(actions={('func_1502F01C', 0): ((address, value, size),)})
                args = (proof.OUTPUT, 0, 0, 0x27000, -1, proof.PARAMETERS, 0, 1)
                self.compare(chain.fixture(kind=1), args, phase, plan)
                cases += 1
        self.receipt('aliases', cases=cases, original_fitted_complete_memory_order_exact=True,
            raw_private_comparison_adjusts_only_proven_saved_return_PCs=True,
            actual_color_outputs_not_hooked=True, live_callback_mutations_independently_checked=True)

    def test_05_every_selected_full_connected_fault_prefix_fires(self):
        prefixes = 0
        for kind, mode, caller, phase in ((1, 0, False, 0), (4, 3, False, 8), (6, 0, True, 8)):
            memory = chain.fixture(kind=kind, direct=chain.FLOAT, enabled=1, count=1)
            args = (proof.OUTPUT, 0, 0, mode, 1) if caller else (
                proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, mode, 1)
            original = self.models(memory, args, phase=phase, caller=caller)[0]
            for fault in range(original.accesses):
                failed = []
                for index, body in enumerate((self.retail, self.raw, self.fitted)):
                    model = chain.ConnectedOracle(body, memory, args, self.bodies, self.data, phase, caller=caller,
                        returns=chain.return_map() if index == 1 else None)
                    model.fault = fault
                    with self.assertRaises(proof.guest.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args, (fault,))
                    self.assertEqual(model.accesses, fault)
                    failed.append(model)
                for model in failed[1:]:
                    self.assertEqual(chain.canonical(model)[1:4], chain.canonical(failed[0])[1:4])
                prefixes += 1
        self.receipt('faults', cases=3, full_fired_prefix_triples=prefixes,
            executions=prefixes * 3, original_fitted_complete_private_public_memory_events_calls_exact=True,
            raw_private_comparison_adjusts_only_proven_saved_return_PCs=True,
            no_portable_C_fault_or_FCSR_claim=True)

    def test_06_actual_helper_hooks_and_compiled_renderer_negatives_are_rejected(self):
        args = (proof.OUTPUT, 0, 3, 0x27000, 255, proof.PARAMETERS, 0, 1)
        memory = {**chain.fixture(view=3, kind=6), **self.data}
        expected, state, _ = chain.reference(memory, args)
        self.compare(memory, args)
        for name, old, new in (
                ('wrong-color-view', 'actor, view, alpha, parameters', 'actor, 0, alpha, parameters'),
                ('wrong-primitive', '0xF2, 0, primitiveR', '0, 0xF2, primitiveR'),
                ('wrong-tail', 'actor[0x2FE] = 1;', 'actor[0x2FE] = 0;')):
            self.assertIn(old, screen.SELECTED)
            _, body = screen.compile_candidate(self.root, self.out, name, screen.SELECTED.replace(old, new))
            wrong = chain.ConnectedOracle(body, memory, args, self.bodies, self.data).run()
            self.assertNotEqual((wrong.r[2], {a: value for a, value in wrong.memory.items() if proof.public(a)}),
                (expected, {a: value for a, value in state.items() if proof.public(a)}), name)
        for entry in (chain.COLOR, chain.FOG, chain.IDENTITY, chain.FLOAT_IDENTITY, chain.PACK):
            bodies = {a: body for a, body in self.bodies.items() if a != entry}
            with self.assertRaisesRegex(AssertionError, 'actual helper cannot be modeled'):
                chain.ConnectedOracle(self.fitted, memory, args, bodies, self.data).run()
        self.receipt('negatives', effective_fresh_complete_compiled_renderer_controls=3,
            missing_actual_helper_body_rejections=5, modeled_substitute_rejected=True)

    def test_07_raw_return_PC_provenance_does_not_hide_other_differences(self):
        args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, 0, 1)
        original, raw, fitted = self.models(chain.fixture(kind=6), args)
        self.assertEqual((original.memory, original.events, original.calls),
            (fitted.memory, fitted.events, fitted.calls))
        self.assertNotEqual(raw.memory, original.memory)
        changed = [index for index, value in raw.return_events.items() if raw.events[index][3] != value]
        self.assertTrue(changed)
        self.assertTrue(all(raw.events[index][0] in ('R', 'W') and
            raw.events[index][2] == 4 and not proof.public(raw.events[index][1]) for index in changed))
        old_pc, canonical_pc = next((old, new) for old, new in chain.return_map().items() if old != new)
        raw.put(proof.OUTPUT, old_pc, 4)
        self.assertEqual(proof.guest.read(chain.canonical(raw)[1], proof.OUTPUT, 4), old_pc)
        self.assertNotEqual(old_pc, canonical_pc)
        self.assertNotEqual(chain.canonical(raw), chain.canonical(original))
        self.receipt('return-provenance', changed_saved_return_accesses=len(changed),
            original_fitted_bytes_events_exact_without_adjustment=True,
            raw_execution_unmodified=True, adjustments_only_proven_private_RA_accesses=True,
            identical_scalar_bits_not_adjusted=True, unrelated_public_change_rejected=True)

    def test_08_production_and_original_baselines_unchanged(self):
        hashes = json.loads((self.out / 'baseline.json').read_text())
        previous = self.root / 'conker/build/game-actor-renderer-native32-test'
        self.assertEqual(hashes, json.loads((previous / 'baseline.json').read_text()))
        for name, path in self.paths.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), hashes[name])
            self.assertEqual(data, (self.out / ('before-' + name)).read_bytes())
            self.assertEqual(data, (previous / ('before-' + name)).read_bytes())
        self.assertIn(screen.recovery.ORIGINAL, (self.root / screen.SOURCE).read_text())
        self.receipt('unchanged', source_ELF_guards_progress_rodata_unchanged=True,
            renderer_and_color_helper_not_installed=True, original_baselines_preserved=True)


if __name__ == '__main__':
    unittest.main()
