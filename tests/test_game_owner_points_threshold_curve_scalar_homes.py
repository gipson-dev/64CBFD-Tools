"""Qualify original limit copies/reads while refusing the overflowing diagnostic."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_scalar_homes as fitting
from tools.tests import test_game_owner_points_threshold_curve_recovery as recovery
from tools.tests import test_game_owner_points_threshold_curve_member_homes as member_tests
from tools.tests.test_game_owner_points_arc_fitting import saved_signature

screen = fitting.base


class GameOwnerPointsThresholdCurveScalarHomeTests(member_tests.GameOwnerPointsThresholdCurveMemberHomeTests):
    @classmethod
    def setUpClass(cls):
        for name, value in (('SELECTED', fitting.SELECTED),
                ('TYPES', fitting.TYPES + fitting.previous.previous.PROJECTED_TYPE)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-threshold-scalar-homes-test'
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

    def scalar_homes(self, models, phase):
        frame = recovery.STACK + phase - 280
        for offset, reads in ((0x68, 2), (0x6C, 2), (0xD0, 1)):
            address = frame + offset
            writes = [[e for e in m.events if e[0] == 'W' and e[1] == address] for m in models]
            self.assertEqual(writes[0], writes[1])
            self.assertIn(len(writes[0]), (0, 1))
            expected = reads if writes[0] else 0
            read_events = [[e for e in m.events if e[0] == 'R' and e[1] == address] for m in models]
            self.assertEqual(Counter(read_events[0]), Counter(read_events[1]))
            for model in models:
                self.assertEqual(sum(e[0] == 'R' and e[1] == address for e in model.events), expected)
                self.assertEqual(recovery.read(model.memory, address), recovery.read(models[0].memory, address))
            self.assertTrue(all(e[2] == 4 for events in read_events for e in events))

    def vector_homes(self, models, phase):
        super().vector_homes(models, phase)
        self.scalar_homes(models, phase)

    def test_01_complete_source_shape_and_positive_forms(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (186, 280, 185, 0))
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        meta, words = fitting.compile_candidate(self.root, self.out, 'prior-slot-form', fitting.previous.SELECTED)
        self.assertEqual(tuple(meta[k] for k in ('body_words', 'frame', 'differences')), (178, 280, 154))
        previous_object = self.root / 'conker/build/game-owner-points-threshold-member-homes-test/selected.o'
        self.assertEqual(recovery.parse_object(previous_object), recovery.parse_object(self.out / 'prior-slot-form.o'))
        forms = list(itertools.chain(fitting.candidates(), fitting.direct_member_candidates(), fitting.limit_candidates(),
            fitting.lifetime_candidates(), fitting.gate_candidates()))
        self.assertEqual((len(forms), len(dict(forms))), (67, 67))
        rows = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['diagnostics'], meta['pool_bytes']), ('', 0))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                with self.subTest(form=name, geometry=index, threshold=threshold, phase=phase):
                    self.compare(recovery.fixture(index, threshold), phase=phase, bodies=(self.retail, words))
            self.assertNotEqual(words, self.retail)
            rows.append(meta)
        profiles = []
        for name, body in (('slot-vector', fitting.previous.SELECTED), ('scalar-homes', fitting.SELECTED)):
            for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
                meta, words = fitting.compile_candidate(self.root, self.out, name + '-' + profile, body, profile)
                for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                    self.compare(recovery.fixture(index, threshold), phase=phase, bodies=(self.retail, words))
                profiles.append(meta)
        self.receipt('shape', dict(selected=self.meta, forms=rows, cases=804, executions=1608,
            profile_forms=profiles, profile_cases=96, profile_executions=192,
            prior178_word_slot_form_object_unchanged=True, overflow_bytes=32, installed=False, guards=0))

    def test_02_complete_geometry_threshold_flags_and_ABI(self):
        start = self.cases
        for flags, index, threshold, phase in itertools.product((0, 2, 0x80, 255), range(len(recovery.GEOMETRIES)),
                recovery.THRESHOLDS, (0, 8)):
            models = self.compare(recovery.fixture(index, threshold, flags), phase=phase, seed=flags % 4)
            self.vector_homes(models, phase)
        for visits, length in zip(self.coverage, (178, 186)):
            self.assertEqual(visits, set(range(screen.ENTRY, screen.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=self.cases - start, executions=(self.cases - start) * 2,
            all_words_reached=[178, 186], saved_GP_FP_SP_preserved=True,
            vector_delta_and_limit_projection_store_read_final_values_qualified=True,
            other_private_memory_not_matched=True, bounded_trig_not_real_math_bodies=True))

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
                    self.assertEqual(meta['frame'], 280)
                    self.delta_home(models, 0)
                if 'limit' in name:
                    self.assertEqual(meta['frame'], 280)
                    member_tests.GameOwnerPointsThresholdCurveMemberHomeTests.vector_homes(self, models, 0)
                    with self.assertRaises(AssertionError):
                        self.scalar_homes(models, 0)
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
            qualified_homes_retained=True, fresh_step_and_endpoint_threshold_snapshots=True,
            fallback_return_not_assumed_one=True))

    def test_06_original_relocations_and_independent_rebases(self):
        asm = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        fragment = begin + asm.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + fragment)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(u for group in recovery.parse_object(path)[2].values() for u in group)
        self.assertEqual(uses(obj), uses(self.out / 'selected.o'))
        for i, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if i == 0 else {name: (entry & 0xF0000000) + 0x108008 + n * 0x100
                for n, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 178), ('candidate', self.out / 'selected.o', 186)):
                elf = self.out / ('rebase-%d-%s.elf' % (i, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, recovery.sections(elf)['.text'][1])))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                models = self.compare(recovery.fixture(index, threshold, symbols=symbols), phase=phase, symbols=symbols,
                    entry=entry, bodies=bodies, actions=recovery.actions_for(symbols))
                self.vector_homes(models, phase)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=48, executions=96,
            relocation_uses=sum(uses(obj).values()), public_and_qualified_homes_not_byte_exact=True))

    def test_07_actual_copied_owner_and_unmatched_private_layout(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', fitting.PAIR_TYPE + screen.OWNER_INSERT +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, fitting.SELECTED)
        objects = []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = recovery.compile_owner(self.root, self.out, body, name)
            self.assertEqual(diagnostics, [])
            objects.append(obj)
        old, of, old_rels = recovery.parse_object(objects[0])
        new, nf, new_rels = recovery.parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        relative = lambda rels, f: {o - f['value']: uses for o, uses in rels.items()
            if f['value'] <= o < f['value'] + f['size']}
        isolated, functions, relocations = recovery.parse_object(self.out / 'selected.o')
        for name, f in nf.items():
            previous = functions[name] if name == screen.FUNCTION else of[name]
            raw, rels = (isolated, relocations) if name == screen.FUNCTION else (old, old_rels)
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_rels, f)),
                (previous['size'], raw[previous['value']:previous['value'] + previous['size']], relative(rels, previous)), name)
        self.assertEqual(recovery.normalized_pools(objects[0]), recovery.normalized_pools(objects[1]))
        with self.assertRaisesRegex(ValueError, 'patched func_151B3FDC is 0x2E8 bytes but its retail span is only 0x2C8'):
            recovery.emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        self.receipt('owner', dict(neighbors=len(nf) - 1, raw_neighbors_pools_relative_relocations_unchanged=True,
            target_isolated_bytes_equal=True, candidate_symbol_bytes=744, retail_slot_bytes=712,
            actual_padder_rejects_overflow_bytes=32, installed=False))

    def test_10_limit_reads_before_fallback_and_native_layout(self):
        rows = []
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
            rows.append(dict(geometry=index, threshold=threshold, phase=phase,
                private_different_bytes=sum(v != models[1].memory.get(k) for k, v in models[0].memory.items())))
        self.fixture = 'typedef float f32;\n' + fitting.PAIR_TYPE
        self.run_host('''
if(sizeof(OwnerCurveLimits)!=8 || __builtin_offsetof(OwnerCurveLimits,threshold)!=0 ||
   __builtin_offsetof(OwnerCurveLimits,quarter)!=4)return 1;
''')
        self.receipt('scalar-homes', dict(cases=8, rows=rows, native32_pair_size=8, offsets=[0, 4],
            both_limit_reads_before_fallback_or_trig=True, private_homes_qualified=[0x68, 0x6C, 0xD0],
            access_order_scalar_spills_and_full_private_memory_open=True))
