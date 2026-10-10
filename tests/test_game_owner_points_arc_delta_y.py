"""Qualify complete delta-Y homes without accepting the two-word overflow."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_delta_y as fitting
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_owner_points_arc_recovery as recovery
from tools.tests.test_game_owner_points_arc_fitting import saved_signature


class GameOwnerPointsArcDeltaYTests(recovery.GameOwnerPointsArcRecoveryTests):
    @classmethod
    def setUpClass(cls):
        handle = patch.object(recovery.screen, 'COMPACT', fitting.SELECTED)
        handle.start()
        cls.addClassCleanup(handle.stop)
        types = patch.object(recovery.screen, 'TYPES', fitting.TYPES)
        types.start()
        cls.addClassCleanup(types.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-delta-y-test'
        cls.meta, cls.words = fitting.compile_candidate(cls.root, cls.out, 'recovered', fitting.SELECTED)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>142I', cls.rom, fitting.base.ROM))
        cls.paths = dict(source=fitting.base.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        prior = cls.root / 'conker/build/game-owner-points-arc-test/baseline.json'
        cls.baseline = json.loads(prior.read_text()) if prior.exists() else {
            name: hashlib.sha256((cls.root / path).read_bytes()).hexdigest() for name, path in cls.paths.items()}
        for name, path in cls.paths.items():
            (cls.out / ('before-' + name)).write_bytes((cls.root / path).read_bytes())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def test_01_complete_source_profile_and_form_discriminators(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (144, 136, 135, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        self.assertNotEqual(self.words, self.retail)
        forms, cases = list(fitting.candidates()), 0
        self.assertEqual(len(forms), len(dict(forms)))
        rows = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['pool_bytes'], meta['diagnostics']), (0, ''))
            if name in ('member-snapshot-all-angle-y-threshold', 'member-snapshot-all-radius-x-threshold'):
                with self.assertRaises(AssertionError):
                    self.compare(recovery.fixture(), bodies=(words,))
                rows.append(dict(meta, execution_qualified=False, effective_snapshot_collision=True))
                continue
            if name.endswith('cast-half'):
                double_ops = [word for word in words if word >> 26 == 17 and word >> 21 & 31 == 17]
                self.assertGreater(meta['body_words'], 142)
                self.assertTrue(double_ops)
                rows.append(dict(meta, execution_qualified=False, double_operations=len(double_ops)))
                continue
            for index, phase in itertools.product((0, 2, 4, 5), (0, 8)):
                with self.subTest(form=name, geometry=index, phase=phase):
                    self.compare(recovery.fixture(index), phase=phase, bodies=(self.retail, words))
                cases += 1
            rows.append(meta)
        profiles = []
        for profile in fitting.base.compiler.PROFILES:
            meta, words = fitting.compile_candidate(self.root, self.out, 'profile-' + profile,
                fitting.SELECTED, profile)
            self.compare(recovery.fixture(), bodies=(self.retail, words))
            profiles.append(meta)
        self.receipt('shape', dict(selected=self.meta, forms=rows, profiles=profiles, form_cases=cases,
            form_executions=cases * 2, original_frame_and_saved_homes=True,
            qualified_forms=sum('execution_qualified' not in row for row in rows),
            effective_snapshot_collision_controls=2, static_rejected_double_forms=2,
            two_word_overflow=True, complete_delta_y_home=True, installed=False, guards=0))

    def private_homes(self, models, phase):
        frame = recovery.STACK + phase - 136
        retail, candidate = models
        self.assertEqual(retail.memory, candidate.memory)
        writes = lambda model: Counter(event for event in model.events if event[0] == 'W' and
            frame + 0x58 <= event[1] < frame + 0x84)
        self.assertEqual(writes(retail), writes(candidate))
        self.assertTrue(any(event[0] == 'W' and event[1] == frame + 0x80
            for event in candidate.events))

    def test_02_complete_guest_flags_geometry_and_saved_registers(self):
        coverage, cases = [set(), set()], 0
        for flags, index, phase in itertools.product(range(256), (0, 2, 4, 5), (0, 8)):
            models = self.compare(recovery.fixture(index, flags), phase=phase, seed=flags % 4)
            self.private_homes(models, phase)
            for i, model in enumerate(models):
                coverage[i].update(model.visits)
            cases += 1
        for visited, length in zip(coverage, (142, 144)):
            self.assertEqual(visited, set(range(fitting.base.ENTRY, fitting.base.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=cases, executions=cases * 2, all_words_reached=[142, 144],
            all_flags_saved_GPR_FP_actor_canaries_preserved=True, all_vector_and_delta_y_homes_and_write_multisets_equal=True,
            entire_final_memory_equal=True,
            helper_contract_only=True, private_write_order_not_claimed=True))

    def test_03_boundaries_mutation_snapshot_and_effective_negatives(self):
        actions = {0: [(recovery.ACTOR + 0x14, recovery.bits(99), 4),
            (fitting.base.SYMBOLS['D_800AA3A4'], recovery.bits(-0.5), 4),
            (fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(0.125), 4)],
            1: [(fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(-3), 4), (recovery.ACTOR + 0x10, 0xA2, 1)]}
        cases = 0
        for index, phase, mutate in itertools.product(range(len(recovery.GEOMETRIES)), (0, 8), (False, True)):
            models = self.compare(recovery.fixture(index), phase=phase, actions=actions if mutate else {})
            self.private_homes(models, phase)
            cases += 1
        negatives = (
            ('return', '    return 1;', '    return 0;'),
            ('count', 'offset != 0xF0', 'offset != 0xD8'),
            ('step', 'angle += angleStep;', 'angle -= angleStep;'),
            ('fresh-step', 'angle += angleStep;', 'angle += D_800AA3A8;'),
            ('arg-order', 'func_150484A0(vertical, angleStep)', 'func_150484A0(angleStep, vertical)'),
            ('threshold', 'D_800AA3A0 < fabsf(delta.x)', 'D_800AA3A0 <= fabsf(delta.x)'),
            ('position', 'along * nx + midpoint.x', 'along * nz + midpoint.x'),
        )
        for name, old, new in negatives:
            self.assertEqual(fitting.SELECTED.count(old), 1)
            _, words = fitting.compile_candidate(self.root, self.out, 'negative-' + name, fitting.SELECTED.replace(old, new))
            rejected = False
            for index in (1, 4, 5):
                try:
                    self.compare(recovery.fixture(index), actions=actions, bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
        self.receipt('mutations', dict(cases=cases, executions=cases * 2, effective_compiled_negatives=len(negatives),
            all_boundaries_and_private_homes=True, late_bias_step_load_and_retained_step=True))

    def test_06_original_relocations_and_independent_symbol_rebases(self):
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + self.original_fragment())
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        for index, entry in enumerate((fitting.base.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = fitting.base.SYMBOLS if index == 0 else {
                name: (entry & 0xF0000000) + 0x108008 + i * 0x100 for i, name in enumerate(fitting.base.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 142), ('candidate', self.out / 'recovered.o', 144)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', fitting.base.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            if index == 0:
                self.assertEqual(bodies, [self.retail, self.words])
            for geometry, phase in itertools.product((0, 2, 4, 5), (0, 8)):
                models = self.compare(recovery.fixture(geometry, symbols=symbols), phase=phase,
                    symbols=symbols, entry=entry, bodies=bodies)
                self.private_homes(models, phase)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=32, executions=64,
            relocation_uses=sum(uses(obj).values()), saved_and_private_vector_homes_preserved=True,
            semantic_not_byte_exact=True))

    def test_07_actual_owner_neighbors_and_padding_frame_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', fitting.base.DECLARATIONS + fitting.DELTA_TYPE +
            '\n/* Non-matching placeholders', 1).replace(fitting.base.ORIGINAL, fitting.SELECTED)
        self.assertNotEqual(before, after)
        objects = []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            self.assertEqual(diagnostics, [])
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        isolated, isolated_functions, isolated_relocations = parse_object(self.out / 'recovered.o')
        target = isolated_functions[fitting.base.FUNCTION]
        relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
            if f['value'] <= o < f['value'] + f['size']}
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == fitting.base.FUNCTION:
                self.assertEqual(new[function['value']:function['value'] + function['size']],
                    isolated[target['value']:target['value'] + target['size']])
                self.assertEqual(relative(nrels, function), relative(isolated_relocations, target))
                continue
            previous = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (previous['size'], old[previous['value']:previous['value'] + previous['size']]), name)
            self.assertEqual(relative(nrels, function), relative(orels, previous), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        with self.assertRaisesRegex(ValueError, fitting.base.FUNCTION):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_relative_relocations_preserved=True,
            isolated_and_actual_owner_target_equal=True, diagnostics=0, words=144, retail_words=142,
            actual_padder_rejects_two_word_overflow=True, original_frame_and_saved_homes=True, installed=False))

    def test_11_effective_private_home_controls_and_endpoint_reads(self):
        changed = fitting.SELECTED.replace(
            '    OwnerArcDeltaY delta;\n    OwnerRibbonPosition32C8 midpoint;',
            '    OwnerRibbonPosition32C8 midpoint;\n    OwnerArcDeltaY delta;')
        self.assertNotEqual(changed, fitting.SELECTED)
        controls = [('private-order', changed), ('missing-delta-y', fitting.previous.SELECTED)]
        rows = []
        for name, body in controls:
            meta, words = fitting.compile_candidate(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(meta['frame'], 136)
            self.assertEqual(saved_signature(words), saved_signature(self.retail))
            models = self.compare(recovery.fixture(), bodies=(self.retail, words))
            with self.assertRaises(AssertionError):
                self.private_homes(models, 0)
            rows.append(meta)
        traces = []
        for index in (0, 4):
            models = self.compare(recovery.fixture(index))
            counts = [Counter(event[1] - recovery.ACTOR for event in model.events if event[0] == 'R'
                and recovery.ACTOR + 0x14 <= event[1] < recovery.ACTOR + 0x2C) for model in models]
            self.assertEqual(counts[0], Counter(dict.fromkeys(range(0x14, 0x2C, 4), 1)))
            expected = {0x14: 2, 0x18: 3, 0x1C: 2, 0x20: 1, 0x24: 1, 0x28: 1} if index else dict.fromkeys(
                range(0x14, 0x2C, 4), 1)
            self.assertEqual(counts[1], Counter(expected))
            traces.append(dict(geometry=index, original=dict(counts[0]), candidate=dict(counts[1])))
        snapshot = dict(fitting.candidates())['member-snapshot-all-angle-y']
        meta, words = fitting.compile_candidate(self.root, self.out, 'six-read-control', snapshot)
        self.assertEqual((meta['body_words'], meta['frame']), (145, 144))
        model = self.compare(recovery.fixture(), bodies=(words,))[0]
        reads = Counter(event[1] - recovery.ACTOR for event in model.events if event[0] == 'R'
            and recovery.ACTOR + 0x14 <= event[1] < recovery.ACTOR + 0x2C)
        self.assertEqual(reads, Counter(dict.fromkeys(range(0x14, 0x2C, 4), 1)))
        self.assertEqual(saved_signature(words), saved_signature(self.retail))
        with self.assertRaises(AssertionError):
            self.private_homes(self.compare(recovery.fixture(), bodies=(self.retail, words)), 0)
        self.receipt('home-controls', dict(effective_compiled_controls=2, public_contracts_still_pass=True,
            same_frame_and_saved_homes_wrong_private_memory_rejected=True, controls=rows,
            endpoint_read_counts=traces, active_reads=[6, 10], early_exit_reads=[6, 6],
            six_read_snapshot_control=meta, six_read_control_wrong_frame_and_private_memory=True,
            six_read_control_relative_saved_offsets_preserved=True,
            full_input_read_order_and_hardware_FCSR_not_claimed=True))


if __name__ == '__main__':
    import unittest
    unittest.main()
