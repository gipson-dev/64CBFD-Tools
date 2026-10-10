"""Qualify six endpoint reads and full private homes; reject slot overflow."""
import hashlib
import itertools
import json
import struct
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_endpoint_reads as fitting
from tools.tests import test_game_owner_points_arc_delta_y as previous_tests
from tools.tests import test_game_owner_points_arc_recovery as recovery
from tools.tests.test_game_owner_points_arc_fitting import saved_signature


class GameOwnerPointsArcEndpointReadTests(previous_tests.GameOwnerPointsArcDeltaYTests):
    @classmethod
    def setUpClass(cls):
        module = patch.object(previous_tests, 'fitting', fitting)
        module.start()
        cls.addClassCleanup(module.stop)
        for name, value in (('COMPACT', fitting.SELECTED), ('TYPES', fitting.TYPES)):
            handle = patch.object(recovery.screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-endpoint-reads-test'
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

    @staticmethod
    def endpoint_reads(model):
        return Counter(event[1] - recovery.ACTOR for event in model.events if event[0] == 'R'
            and recovery.ACTOR + 0x14 <= event[1] < recovery.ACTOR + 0x2C)

    def private_homes(self, models, phase):
        super().private_homes(models, phase)
        expected = Counter(dict.fromkeys(range(0x14, 0x2C, 4), 1))
        for model in models:
            self.assertEqual(self.endpoint_reads(model), expected)

    def test_01_complete_source_profile_and_form_discriminators(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (144, 136, 138, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        self.assertNotEqual(self.words, self.retail)
        forms, cases = list(fitting.candidates()), 0
        self.assertEqual(len(forms), len(dict(forms)))
        rows = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['pool_bytes'], meta['diagnostics']), (0, ''))
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
        self.receipt('shape', dict(selected=self.meta, forms=rows, profiles=profiles,
            form_cases=cases, form_executions=cases * 2, original_frame_and_saved_homes=True,
            original_private_memory_and_six_read_multiplicity=True, private_order_not_claimed=True,
            two_word_overflow=True, installed=False, guards=0))

    def test_02_complete_guest_flags_geometry_and_saved_registers(self):
        coverage, cases = [set(), set()], 0
        for flags, index, phase in itertools.product(range(256), (0, 2, 3, 4, 5), (0, 8)):
            models = self.compare(recovery.fixture(index, flags), phase=phase, seed=flags % 4)
            self.private_homes(models, phase)
            for i, model in enumerate(models):
                coverage[i].update(model.visits)
            cases += 1
        for visited, length in zip(coverage, (142, 144)):
            self.assertEqual(visited, set(range(fitting.base.ENTRY, fitting.base.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=cases, executions=cases * 2, all_words_reached=[142, 144],
            all_flags_saved_GPR_FP_actor_canaries_preserved=True,
            entire_final_memory_and_private_write_multisets_equal=True,
            six_endpoint_reads_each_once_in_every_case=True, Z_only_active_branch_covered=True,
            helper_contract_only=True, private_write_and_full_read_order_not_claimed=True))

    def test_11_effective_private_home_controls_and_endpoint_reads(self):
        body = fitting.previous.SELECTED
        meta, words = fitting.compile_candidate(self.root, self.out, 'negative-retained-ten-reads', body)
        models = self.compare(recovery.fixture(), bodies=(self.retail, words))
        super().private_homes(models, 0)
        self.assertEqual([sum(self.endpoint_reads(model).values()) for model in models], [6, 10])
        with self.assertRaises(AssertionError):
            self.private_homes(models, 0)
        reload = fitting.SELECTED.replace('        first.x = along - midpoint.x;',
            '        (void)*(volatile f32 *)(actor + 0x14);\n        first.x = along - midpoint.x;')
        self.assertNotEqual(reload, fitting.SELECTED)
        meta2, words2 = fitting.compile_candidate(self.root, self.out, 'negative-one-reload', reload)
        models2 = self.compare(recovery.fixture(), bodies=(self.retail, words2))
        self.assertEqual([sum(self.endpoint_reads(model).values()) for model in models2], [6, 7])
        with self.assertRaises(AssertionError):
            super().private_homes(models2, 0)
        with self.assertRaises(AssertionError):
            self.assertEqual(self.endpoint_reads(models2[1]), self.endpoint_reads(models2[0]))
        with self.assertRaises(AssertionError):
            self.private_homes(models2, 0)
        swapped = fitting.SELECTED.replace(
            '    OwnerArcDeltaY delta;\n    OwnerRibbonPosition32C8 midpoint;',
            '    OwnerRibbonPosition32C8 midpoint;\n    OwnerArcDeltaY delta;')
        self.assertNotEqual(swapped, fitting.SELECTED)
        meta3, words3 = fitting.compile_candidate(self.root, self.out, 'negative-private-order', swapped)
        self.assertEqual(meta3['frame'], 136)
        self.assertEqual(saved_signature(words3), saved_signature(self.retail))
        models3 = self.compare(recovery.fixture(), bodies=(self.retail, words3))
        with self.assertRaises(AssertionError):
            self.private_homes(models3, 0)
        self.receipt('read-controls', dict(effective_compiled_read_negatives=2,
            effective_compiled_private_home_negative=1, public_contracts_pass_all_controls=True,
            full_private_memory_still_equal_in_ten_read_negative=True,
            seventh_read_control_also_changes_private_memory=True,
            ten_read_control=meta, one_reload_control=meta2, private_order_control=meta3,
            original_candidate_endpoint_reads=[6, 6], full_input_order_not_claimed=True))

    def test_12_all_endpoint_missing_byte_fault_prefixes(self):
        cases = 0
        for offset, phase in itertools.product(range(0x14, 0x2C, 4), (0, 8)):
            memory = recovery.fixture()
            del memory[recovery.ACTOR + offset]
            models = []
            for words in (self.retail, self.words):
                model = recovery.ArcOracle(words, memory, phase=phase)
                with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                    model.run()
                models.append(model)
            self.assertEqual(recovery.public(models[0].memory), recovery.public(models[1].memory))
            self.assertEqual(models[0].calls, models[1].calls)
            writes = lambda model: [event for event in model.events if event[0] == 'W' and
                not recovery.STACK - 0x600 <= event[1] < recovery.STACK + 0x140]
            self.assertEqual(writes(models[0]), writes(models[1]))
            cases += 1
        self.receipt('endpoint-faults', dict(cases=cases, executions=cases * 2,
            all_six_endpoint_faults_both_phases=True, public_write_call_prefixes_equal=True,
            full_private_fault_prefix_input_order_and_portable_C_faults_not_claimed=True))


if __name__ == '__main__':
    import unittest
    unittest.main()
