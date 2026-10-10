"""Qualify the fitting curve's original frame and full-path delta-Y home/read."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_threshold_curve_vectors as fitting
from tools.tests import test_game_owner_points_threshold_curve_recovery as recovery
from tools.tests.test_game_owner_points_arc_fitting import saved_signature

screen = fitting.base


class GameOwnerPointsThresholdCurveVectorTests(recovery.GameOwnerPointsThresholdCurveRecoveryTests):
    @classmethod
    def setUpClass(cls):
        for name, value in (('SELECTED', fitting.SELECTED), ('TYPES', fitting.TYPES + fitting.PROJECTED_TYPE)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-threshold-vectors-test'
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

    def test_01_complete_source_shape_and_positive_forms(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (170, 280, 173, 0))
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        forms = list(itertools.chain(fitting.candidates(), fitting.home_candidates(), fitting.cached_candidates()))
        self.assertEqual(len(forms), 72)
        self.assertEqual(len(dict(forms)), 72)
        self.assertNotIn('OwnerArcDeltaY delta;', fitting.previous.SEED)
        rows = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['diagnostics'], meta['pool_bytes']), ('', 0))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                with self.subTest(form=name, geometry=index, threshold=threshold, phase=phase):
                    self.compare(recovery.fixture(index, threshold), phase=phase, bodies=(self.retail, words))
            self.assertNotEqual(words, self.retail)
            rows.append(meta)
        selected = next(row for row in rows if row['name'] == 'form-' + fitting.SELECTED_NAME)
        self.assertEqual((selected['body_words'], selected['frame'], selected['differences']), (170, 280, 173))
        self.receipt('shape', dict(selected=self.meta, forms=rows, cases=864, executions=1728,
            source_seed_isolated=True, original_frame_and_saved_homes=True,
            fits_slot_not_byte_exact=True, installed=False, guards=0))

    def delta_home(self, models, phase):
        address = recovery.STACK + phase - 8
        writes = [[e for e in m.events if e[0] == 'W' and e[1] == address] for m in models]
        self.assertEqual(writes[0], writes[1])
        self.assertEqual(len(writes[0]), 1)
        for model in models:
            self.assertEqual(sum(e[0] == 'R' and e[1] == address for e in model.events), 1)
            self.assertEqual(recovery.read(model.memory, address), recovery.read(models[0].memory, address))

    def test_02_complete_geometry_threshold_flags_and_ABI(self):
        start = self.cases
        for flags, index, threshold, phase in itertools.product((0, 2, 0x80, 255), range(len(recovery.GEOMETRIES)),
                recovery.THRESHOLDS, (0, 8)):
            models = self.compare(recovery.fixture(index, threshold, flags), phase=phase, seed=flags % 4)
            self.delta_home(models, phase)
        for visits, count in zip(self.coverage, (178, 170)):
            self.assertEqual(visits, set(range(screen.ENTRY, screen.ENTRY + count * 4, 4)))
        self.receipt('guest', dict(cases=self.cases - start, executions=(self.cases - start) * 2,
            all_words_reached=[178, 170], saved_GP_FP_SP_preserved=True,
            delta_y_home_store_read_and_final_value_equal_all_paths=True,
            bounded_trig_not_real_math_bodies=True, other_private_memory_not_matched=True))

    def test_03_fresh_step_snapshots_and_effective_negatives(self):
        count = 0
        for index, threshold, phase, result in itertools.product((0, 3, 4, 6), (-1, 6.25, 10000),
                (0, 8), (0, 1, 2, 0xFFFFFFFF)):
            models = self.compare(recovery.fixture(index, threshold), phase=phase,
                actions=recovery.actions_for(), fallback_result=result)
            self.delta_home(models, phase)
            count += 1
        controls = []
        for name, body in fitting.negative_candidates():
            self.assertNotEqual(body, fitting.SELECTED)
            _, words = fitting.compile_candidate(self.root, self.out, name, body)
            self.assertNotEqual(words, self.words, name)
            if name == 'negative-private-no-work-y-read':
                models = self.compare(recovery.fixture(0), bodies=(self.retail, words))
                with self.assertRaises(AssertionError):
                    self.delta_home(models, 0)
                controls.append(dict(name=name, public_contract_passes_private_read_rejected=True))
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
            endpoint_threshold_snapshot=True, fresh_angle_step_after_every_point=True,
            fallback_return_not_assumed_one=True, real_private_read_gate_rejects_public_only_control=True))

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
            for label, path, length in (('original', obj, 178), ('candidate', self.out / 'selected.o', 170)):
                elf = self.out / ('rebase-%d-%s.elf' % (i, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, recovery.sections(elf)['.text'][1])))
            for index, threshold, phase in itertools.product((0, 3, 6), (-1, 10), (0, 8)):
                models = self.compare(recovery.fixture(index, threshold, symbols=symbols), phase=phase, symbols=symbols,
                    entry=entry, bodies=bodies, actions=recovery.actions_for(symbols))
                self.delta_home(models, phase)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=48, executions=96,
            relocation_uses=sum(uses(obj).values()), semantic_and_delta_home_not_byte_exact=True))

    def test_07_actual_copied_owner_and_unmatched_private_layout(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.OWNER_INSERT +
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
        assembly = self.out / 'padded.s'
        assembly.write_text(recovery.emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(assembly.with_suffix('.o')), str(assembly)],
            check=True, capture_output=True)
        _, padded, _ = recovery.parse_object(assembly.with_suffix('.o'))
        self.assertEqual((padded[screen.FUNCTION]['size'], padded['func_151B42A4']['value'] - padded[screen.FUNCTION]['value']),
            (680, 712))
        self.receipt('owner', dict(neighbors=len(nf) - 1, raw_neighbors_pools_relative_relocations_unchanged=True,
            target_isolated_bytes_equal=True, actual_padded_slot_bytes=712, candidate_symbol_bytes=680,
            padding_bytes=32, private_memory_and_words_not_matched=True, installed=False))

    def test_09_public_read_contract_and_private_home_handoff(self):
        rows = []
        for index, threshold, phase in itertools.product((0, 6), (-1, 10), (0, 8)):
            models = self.compare(recovery.fixture(index, threshold), phase=phase)
            self.delta_home(models, phase)
            frame = recovery.STACK + phase - 280
            public_reads = lambda m: [e for e in m.events if e[0] == 'R' and not
                recovery.STACK - 0x600 <= e[1] < recovery.STACK + 0x140]
            self.assertEqual(Counter((e[1], e[2]) for e in public_reads(models[0])),
                Counter((e[1], e[2]) for e in public_reads(models[1])))
            homes = [sorted({(e[1] - frame, e[2]) for e in m.events if e[0] == 'W' and frame <= e[1] < frame + 280})
                for m in models]
            self.assertNotEqual(models[0].memory, models[1].memory)
            self.assertNotEqual(public_reads(models[0]), public_reads(models[1]))
            for model in models:
                helpers, steps, last_write = 0, 0, None
                for event in model.events:
                    if event[0] == 'CALL':
                        helpers += 1
                    elif event[0] == 'W' and recovery.ACTOR <= event[1] < recovery.ACTOR + 0x190:
                        last_write = event[1]
                    elif event[0] == 'R' and event[1] == screen.SYMBOLS['D_800AA3B4']:
                        self.assertEqual(helpers, (steps + 1) * 2)
                        self.assertEqual(last_write, recovery.ACTOR + 0x50 + steps * 24)
                        steps += 1
                self.assertEqual(steps, 10 if index == 6 and threshold == 10 else 0)
            rows.append(dict(geometry=index, threshold=threshold, phase=phase, homes=homes))
        self.receipt('reads-homes', dict(cases=8, rows=rows, frame_and_saved_homes_equal=True,
            delta_y_store_read_and_final_value_equal_all_paths=True,
            other_private_homes_memory_and_input_read_order_not_matched=True))
