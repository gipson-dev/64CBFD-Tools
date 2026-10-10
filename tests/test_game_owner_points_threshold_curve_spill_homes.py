"""Separate a real squared-copy boundary from incorrect frame/save locations."""
import hashlib
import itertools
import json
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_spill_homes as fitting
from tools.tests import test_game_owner_points_threshold_curve_scalar_homes as scalar_tests
from tools.tests import test_game_owner_points_threshold_curve_member_homes as member_tests
from tools.tests import test_game_owner_points_threshold_curve_recovery as recovery
from tools.tests.test_game_owner_points_arc_fitting import saved_signature

screen = fitting.base


class GameOwnerPointsThresholdCurveSpillHomeTests(scalar_tests.GameOwnerPointsThresholdCurveScalarHomeTests):
    @classmethod
    def setUpClass(cls):
        for module, name, value in ((screen, 'SELECTED', fitting.SELECTED),
                (screen, 'TYPES', fitting.TYPES + fitting.previous.previous.previous.PROJECTED_TYPE),
                (scalar_tests, 'fitting', fitting)):
            handle = patch.object(module, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-threshold-spill-homes-test'
        cls.meta, cls.words = fitting.compile_candidate(cls.root, cls.out, 'selected', fitting.SELECTED)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>178I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        cls.baseline = json.loads((cls.root / 'conker/build/game-owner-points-threshold-curve-test/baseline.json').read_text())
        for name, relative in cls.paths.items():
            data = (cls.root / relative).read_bytes()
            assert hashlib.sha256(data).hexdigest() == cls.baseline[name], name
            (cls.out / ('before-' + name)).write_bytes(data)
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.coverage, cls.cases = [set(), set()], 0

    def square_home(self, models, phase):
        address = recovery.STACK + phase - 280 + 0x64
        writes = [[e for e in m.events if e[0] == 'W' and e[1] == address] for m in models]
        self.assertEqual(writes[0], writes[1])
        self.assertIn(len(writes[0]), (0, 1))
        for model in models:
            self.assertEqual(sum(e[0] == 'R' and e[1] == address for e in model.events), 0)
            self.assertEqual(recovery.read(model.memory, address), recovery.read(models[0].memory, address))

    def vector_homes(self, models, phase):
        super().vector_homes(models, phase)
        self.square_home(models, phase)

    def frame_saved_homes(self, words):
        self.assertEqual((-words[0]) & 65535, 280)
        self.assertEqual(saved_signature(words), saved_signature(self.retail))

    def test_01_complete_source_shape_and_positive_forms(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (186, 288, 186, 0))
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        with self.assertRaises(AssertionError):
            self.frame_saved_homes(self.words)
        forms = list(itertools.chain(fitting.candidates(), fitting.record_candidates(), fitting.lifetime_candidates(),
            fitting.midpoint_candidates()))
        self.assertEqual((len(forms), len(dict(forms))), (40, 40))
        rows = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['diagnostics'], meta['pool_bytes']), ('', 0))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                with self.subTest(form=name, geometry=index, threshold=threshold, phase=phase):
                    self.compare(recovery.fixture(index, threshold), phase=phase, bodies=(self.retail, words))
            self.assertNotEqual(words, self.retail)
            rows.append(meta)
        for name, body, directory in (
                ('prior-scalar', fitting.previous.SELECTED, 'scalar'),
                ('prior-slot', fitting.previous.previous.SELECTED, 'member')):
            _, _words = fitting.compile_candidate(self.root, self.out, name, body)
            old = self.root / ('conker/build/game-owner-points-threshold-' + directory + '-homes-test/selected.o')
            self.assertEqual(recovery.parse_object(old), recovery.parse_object(self.out / (name + '.o')))
        self.receipt('shape', dict(selected=self.meta, forms=rows, cases=480, executions=960,
            prior_slot_and_scalar_objects_unchanged=True, physical_saved_homes_not_original=True,
            frame_gate_rejects=True, installed=False, guards=0))

    def test_03_fresh_step_snapshots_and_effective_negatives(self):
        count = 0
        for index, threshold, phase, result in itertools.product((0, 3, 4, 6), (-1, 6.25, 10000),
                (0, 8), (0, 1, 2, 0xFFFFFFFF)):
            models = self.compare(recovery.fixture(index, threshold), phase=phase,
                actions=recovery.actions_for(), fallback_result=result)
            self.vector_homes(models, phase)
            count += 1
        controls = []
        for name, body in fitting.negative_candidates():
            self.assertNotEqual(body, fitting.SELECTED)
            meta, words = fitting.compile_candidate(self.root, self.out, name, body)
            self.assertNotEqual(words, self.words)
            if name.startswith('negative-private-'):
                index = 0 if name.endswith('y-read') else 6
                models = self.compare(recovery.fixture(index), bodies=(self.retail, words))
                if name.endswith('home-swap'):
                    self.assertEqual(meta['frame'], 288)
                    self.delta_home(models, 0)
                if 'limit' in name:
                    self.assertEqual(meta['frame'], 288)
                    member_tests.GameOwnerPointsThresholdCurveMemberHomeTests.vector_homes(self, models, 0)
                    with self.assertRaises(AssertionError):
                        self.scalar_homes(models, 0)
                if 'square-copy' in name:
                    scalar_tests.GameOwnerPointsThresholdCurveScalarHomeTests.vector_homes(self, models, 0)
                    with self.assertRaises(AssertionError):
                        self.square_home(models, 0)
                with self.assertRaises(AssertionError):
                    self.vector_homes(models, 0)
                controls.append(dict(name=name, public_passes_private_gate_rejected=True))
                continue
            rejected = False
            for index, threshold in ((6, 10), (6, -1), (4, 10000), (3, 6.25)):
                try:
                    self.compare(recovery.fixture(index, threshold), actions=recovery.actions_for(),
                        fallback_result=0xFFFFFFFF, bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
            controls.append(dict(name=name, public_semantic_rejected=True))
        self.receipt('mutations', dict(cases=count, executions=count * 2, effective_compiled_negatives=controls,
            qualified_float_homes_retained=True, frame_and_other_private_memory_not_matched=True))

    def test_10_limit_reads_before_fallback_and_native_layout(self):
        for index, threshold, phase in itertools.product((0, 6), (-1, 10), (0, 8)):
            models = self.compare(recovery.fixture(index, threshold), phase=phase)
            self.vector_homes(models, phase)
            frame = recovery.STACK + phase - 280
            for model in models:
                if index == 6:
                    reads = [i for i, e in enumerate(model.events) if e[0] == 'R' and e[1] in (frame + 0x68, frame + 0x6C)]
                    calls = [i for i, e in enumerate(model.events) if e[0] == 'CALL']
                    self.assertEqual(len(reads), 4)
                    self.assertLess(max(reads), min(calls))
        self.fixture = 'typedef float f32;\n' + fitting.LATE_ENDPOINT_TYPE
        self.run_host('''
if(sizeof(OwnerCurveLateEndpointMeasures)!=16 ||
   __builtin_offsetof(OwnerCurveLateEndpointMeasures,squared)!=0 ||
   __builtin_offsetof(OwnerCurveLateEndpointMeasures,threshold)!=4 ||
   __builtin_offsetof(OwnerCurveLateEndpointMeasures,quarter)!=8 ||
   __builtin_offsetof(OwnerCurveLateEndpointMeasures,endpointZ)!=12)return 1;
''')
        self.receipt('scalar-homes', dict(cases=8, original_frame_relative_offsets=[0x64, 0x68, 0x6C, 0xD0],
            candidate_frame=288, original_frame=280, native32_record_size=16, offsets=[0, 4, 8, 12],
            both_limit_reads_before_fallback_or_trig=True, frame_and_other_private_memory_open=True))

    def test_11_orthogonal_square_and_physical_saved_home_gates(self):
        _, prior = fitting.compile_candidate(self.root, self.out, 'prior-frame-control', fitting.previous.SELECTED)
        rows = []
        for threshold, phase in itertools.product((-1, 10), (0, 8)):
            models = self.compare(recovery.fixture(6, threshold), phase=phase, bodies=(self.retail, prior))
            scalar_tests.GameOwnerPointsThresholdCurveScalarHomeTests.vector_homes(self, models, phase)
            self.frame_saved_homes(prior)
            with self.assertRaises(AssertionError):
                self.square_home(models, phase)
            selected = self.compare(recovery.fixture(6, threshold), phase=phase)
            self.vector_homes(selected, phase)
            frame = recovery.STACK + phase - 280
            saves = lambda m: [e for e in m.events if e[0] == 'W' and frame + 0x10 <= e[1] < frame + 0x58]
            self.assertNotEqual(saves(selected[0]), saves(selected[1]))
            actual = [e for e in selected[1].events if e[0] == 'W' and frame + 8 <= e[1] < frame + 0x50]
            self.assertEqual([(e[0], e[1] - 8, *e[2:]) for e in saves(selected[0])], actual)
            rows.append(dict(threshold=threshold, phase=phase,
                private_different_bytes=sum(v != selected[1].memory.get(k) for k, v in selected[0].memory.items())))
        self.receipt('orthogonal-gates', dict(cases=4, rows=rows,
            prior_frame_passes_square_fails=True, selected_square_passes_frame_fails=True,
            original_square_home_from_incoming_SP='-0xB4', actual_saved_write_locations_differ=True))
