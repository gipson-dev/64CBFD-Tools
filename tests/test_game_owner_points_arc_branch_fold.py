"""Qualify certified arc branch-copy folding through the actual padder and links."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_branch_fold as fitting
from tools.experiments import game_owner_points_arc_slot_fitting as source_forms
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_owner_points_arc_recovery as recovery
from tools.tests import test_game_owner_points_arc_endpoint_reads as previous_tests
from tools.tests.test_game_owner_points_arc_fitting import saved_signature


class GameOwnerPointsArcBranchFoldTests(previous_tests.GameOwnerPointsArcEndpointReadTests):
    def private_homes(self, models, phase):
        for candidate in models[1:]:
            super().private_homes((models[0], candidate), phase)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-branch-fold-test'
        for name, value in (('COMPACT', fitting.SELECTED), ('TYPES', fitting.TYPES)):
            handle = patch.object(recovery.screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.meta, cls.words = fitting.compile_candidate(cls.root, cls.out, 'recovered')
        cls.raw_meta, cls.raw = fitting.source.compile_candidate(cls.root, cls.out, 'raw', fitting.SELECTED)
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
        cls.guards = cls.out / 'fold-only.csv'
        rows = fitting.guard_rows(cls.out / 'recovered.o')
        with cls.guards.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        assembly = cls.out / 'folded.s'
        retail = cls.out / 'retail-slot.s'
        retail.write_text(cls.original_fragment(cls))
        assembly.write_text(emit_padded_assembly(cls.out / 'recovered.o', retail,
            word_patches_path=cls.guards, filename='generated_1E0560'))
        cls.folded_obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.folded_obj), str(assembly)],
            check=True, capture_output=True)

    def test_01_complete_source_profile_and_form_discriminators(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (142, 136, 102, 0))
        self.assertEqual((self.raw_meta['body_words'], self.raw_meta['differences']), (144, 138))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(saved_signature(self.words), saved_signature(self.retail))
        self.assertNotEqual(self.words, self.retail)
        certificate = fitting.certify(self.raw)
        rows, cases = [], 0
        for name, body in source_forms.candidates():
            meta, words = source_forms.compile_candidate(self.root, self.out, 'form-' + name, body)
            self.assertEqual((meta['diagnostics'], meta['pool_bytes']), ('', 0))
            for index, phase in itertools.product((0, 2, 3, 4, 5), (0, 8)):
                with self.subTest(form=name, geometry=index, phase=phase):
                    self.compare(recovery.fixture(index), phase=phase, bodies=(self.retail, words))
                cases += 1
            rows.append(meta)
        self.receipt('shape', dict(selected=self.meta, raw=self.raw_meta, source_forms=rows,
            source_cases=cases, source_executions=cases * 2, certificate=certificate,
            guarded_fold_not_plain_C_142_word_claim=True, installed=False))

    def test_02_complete_guest_flags_geometry_and_saved_registers(self):
        coverage, cases = [set(), set(), set()], 0
        for flags, index, phase in itertools.product(range(256), (0, 2, 3, 4, 5), (0, 8)):
            models = self.compare(recovery.fixture(index, flags), phase=phase, seed=flags % 4,
                bodies=(self.retail, self.raw, self.words))
            self.private_homes(models, phase)
            for i, model in enumerate(models):
                coverage[i].update(model.visits)
            cases += 1
        for visited, length in zip(coverage, (142, 144, 142)):
            self.assertEqual(visited, set(range(fitting.base.ENTRY, fitting.base.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=cases, executions=cases * 3, all_words_reached=[142, 144, 142],
            entire_final_memory_and_private_write_multisets_equal=True, six_input_reads_each_once=True,
            all_flags_saved_GP_FP_and_actor_canaries_preserved=True, helper_contract_only=True))

    def test_03_boundaries_mutation_snapshot_and_effective_negatives(self):
        actions = {0: [(recovery.ACTOR + 0x14, recovery.bits(99), 4),
            (fitting.base.SYMBOLS['D_800AA3A4'], recovery.bits(-0.5), 4),
            (fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(0.125), 4)],
            1: [(fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(-3), 4), (recovery.ACTOR + 0x10, 0xA2, 1)]}
        cases = 0
        for index, phase, mutate in itertools.product(range(len(recovery.GEOMETRIES)), (0, 8), (False, True)):
            models = self.compare(recovery.fixture(index), phase=phase, actions=actions if mutate else {},
                bodies=(self.retail, self.raw, self.words))
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
            _, words = fitting.source.compile_candidate(self.root, self.out, 'negative-' + name,
                fitting.SELECTED.replace(old, new))
            rejected = False
            for index in (1, 4, 5):
                try:
                    self.compare(recovery.fixture(index), actions=actions, bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
        self.receipt('mutations', dict(cases=cases, executions=cases * 3,
            effective_compiled_semantic_negatives=len(negatives), all_private_homes_and_six_reads=True))

    def test_06_original_relocations_and_independent_symbol_rebases(self):
        original, obj = self.out / 'original.s', self.out / 'original.o'
        original.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + self.original_fragment())
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(original)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        self.assertEqual(uses(obj), uses(self.folded_obj))
        def offsets(path):
            _, functions, rels = parse_object(path)
            target = functions[fitting.base.FUNCTION]
            return {offset - target['value']: group for offset, group in rels.items()
                if target['value'] <= offset < target['value'] + target['size']}
        self.assertEqual(self.meta['raw_relocations'], offsets(self.out / 'recovered.o'))
        self.assertEqual(self.meta['relocations'], offsets(self.folded_obj))
        for index, entry in enumerate((fitting.base.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = fitting.base.SYMBOLS if index == 0 else {
                name: (entry & 0xF0000000) + 0x108008 + i * 0x100 for i, name in enumerate(fitting.base.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 142), ('raw', self.out / 'recovered.o', 144),
                    ('folded', self.folded_obj, 142)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', fitting.base.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            self.assertEqual(fitting.normalize(bodies[1]), bodies[2])
            if index == 0:
                self.assertEqual(bodies, [self.retail, self.raw, self.words])
            for geometry, phase in itertools.product((0, 2, 3, 4, 5), (0, 8)):
                models = self.compare(recovery.fixture(geometry, symbols=symbols), phase=phase,
                    symbols=symbols, entry=entry, bodies=bodies)
                self.private_homes(models, phase)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=12, cases=40, executions=120,
            relocation_uses=sum(uses(obj).values()), actual_guarded_object_equals_recipe=True))

    def test_07_actual_owner_neighbors_and_padding_frame_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', fitting.base.DECLARATIONS + fitting.DELTA_TYPE +
            '\n/* Non-matching placeholders', 1).replace(fitting.base.ORIGINAL, fitting.SELECTED)
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
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        with self.assertRaisesRegex(ValueError, fitting.base.FUNCTION):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        with (self.root / self.paths['guards']).open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, existing = reader.fieldnames, list(reader)
        rows = fitting.guard_rows(objects[1])
        guarded = self.out / 'owner-guards.csv'
        with guarded.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(existing + rows)
        padded = []
        for index, (obj, guards) in enumerate(((objects[0], self.root / self.paths['guards']), (objects[1], guarded))):
            path = self.out / ('padded-%d.s' % index)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=guards, filename='generated_1E0560'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
                check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        old, of, orels = padded[0]
        new, nf, nrels = padded[1]
        self.assertEqual(of.keys(), nf.keys())
        target, old_target = nf[fitting.base.FUNCTION], of[fitting.base.FUNCTION]
        self.assertEqual((target['value'], target['size']), (old_target['value'], 568))
        self.assertEqual(nf['func_151B3F28']['value'] - target['value'], 568)
        self.assertEqual(old[:target['value']], new[:target['value']])
        self.assertEqual(old[target['value'] + 568:], new[target['value'] + 568:])
        relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
            if f['value'] <= o < f['value'] + f['size']}
        isolated, functions, rels = parse_object(self.folded_obj)
        isolated_target = functions[fitting.base.FUNCTION]
        self.assertEqual(new[target['value']:target['value'] + 568],
            isolated[isolated_target['value']:isolated_target['value'] + 568])
        self.assertEqual(relative(nrels, target), relative(rels, isolated_target))
        for name, function in nf.items():
            if name != fitting.base.FUNCTION:
                self.assertEqual(function, of[name])
                self.assertEqual(relative(nrels, function), relative(orels, of[name]))
        self.receipt('owner', dict(neighbors=len(nf) - 1, actual_guarded_padder_words=142,
            guard_rows=len(rows), certified_omissions=2, insertions=0, frame_patches=0,
            raw_padder_still_rejects=True, all_other_padded_bytes_pools_and_relocations_preserved=True,
            isolated_and_actual_owner_equal=True, installed=False))

    def test_11_effective_private_home_controls_and_endpoint_reads(self):
        previous_tests.GameOwnerPointsArcEndpointReadTests.test_11_effective_private_home_controls_and_endpoint_reads(self)
        target = parse_object(self.out / 'recovered.o')[1][fitting.base.FUNCTION]
        text, functions, rels = parse_object(self.out / 'recovered.o')
        malformed = dict(functions, **{fitting.base.FUNCTION: dict(target, size=148 * 4)})
        with patch.object(fitting, 'parse_object', return_value=(text, malformed, rels)):
            with self.assertRaisesRegex(ValueError, 'object extent'):
                fitting.guard_rows(self.out / 'recovered.o')
        for offset in fitting.WINDOW:
            changed = self.raw.copy()
            changed[offset // 4] ^= 1
            with self.assertRaises(ValueError):
                fitting.normalize(changed)
            text = bytearray(sections(self.out / 'recovered.o')['.text'][1])
            struct.pack_into('>I', text, target['value'] + offset, changed[offset // 4])
            replacement = self.out / 'stale-text.bin'
            replacement.write_bytes(text)
            stale = self.out / 'stale.o'
            subprocess.run(['mips-linux-gnu-objcopy', '--update-section', '.text=' + str(replacement),
                str(self.out / 'recovered.o'), str(stale)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit_padded_assembly(stale, self.out / 'retail-slot.s',
                    word_patches_path=self.guards, filename='generated_1E0560')
        for offset in (0x70, 0x88):
            changed = self.words.copy()
            changed[offset // 4] = 0
            with self.assertRaises(AssertionError):
                self.compare(recovery.fixture(), bodies=(changed,))
        self.receipt('fold-negatives', dict(stale_window_words_rejected=len(fitting.WINDOW),
            actual_padder_stale_words_rejected=len(fitting.WINDOW),
            effective_live_value_negatives=2, removing_Z_delta_or_half_not_accepted=True))

    def test_12_all_endpoint_missing_byte_fault_prefixes(self):
        previous_tests.GameOwnerPointsArcEndpointReadTests.test_12_all_endpoint_missing_byte_fault_prefixes(self)


if __name__ == '__main__':
    import unittest
    unittest.main()
