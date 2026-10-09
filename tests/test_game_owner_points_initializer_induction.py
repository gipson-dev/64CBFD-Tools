"""Qualify complete initializer zero-read removal; reject the 158-word overflow."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_initializer_candidates as base
from tools.experiments import game_owner_points_initializer_fitting as fitting
from tools.experiments import game_owner_points_initializer_induction as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_owner_points_initializer_recovery as recovery
from tools.tests import test_game_owner_points_initializer_fitting as prior


class GameOwnerPointsInitializerInductionTests(unittest.TestCase):
    run_host = recovery.GameOwnerPointsInitializerRecoveryTests.run_host
    compare = recovery.GameOwnerPointsInitializerRecoveryTests.compare
    receipt = recovery.GameOwnerPointsInitializerRecoveryTests.receipt
    test_02_flags_geometry_all_words_and_saved_registers = recovery.GameOwnerPointsInitializerRecoveryTests.test_02_flags_geometry_all_words_and_saved_registers
    test_04_actual_native32_source_and_complete_actor_bytes = recovery.GameOwnerPointsInitializerRecoveryTests.test_04_actual_native32_source_and_complete_actor_bytes
    test_05_actual_registered_update_dispatch_and_return = recovery.GameOwnerPointsInitializerRecoveryTests.test_05_actual_registered_update_dispatch_and_return
    test_08_production_baseline_data_and_registration_unchanged = recovery.GameOwnerPointsInitializerRecoveryTests.test_08_production_baseline_data_and_registration_unchanged
    test_09_missing_byte_public_prefixes_and_unused_bytes = recovery.GameOwnerPointsInitializerRecoveryTests.test_09_missing_byte_public_prefixes_and_unused_bytes
    test_10_actual_private_frame_bytes_and_home_addresses = prior.GameOwnerPointsInitializerFittingTests.test_10_actual_private_frame_bytes_and_home_addresses
    test_11_native_actor_layout_and_complete_static_offsets = prior.GameOwnerPointsInitializerFittingTests.test_11_native_actor_layout_and_complete_static_offsets

    @classmethod
    def setUpClass(cls):
        for module, name, value in ((base, 'RECOVERED', screen.SELECTED), (base, 'TYPES', screen.TYPES),
                (fitting, 'SELECTED', screen.SELECTED)):
            handle = patch.object(module, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-initializer-induction-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'recovered')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>157I', cls.rom, base.ROM))
        cls.paths = dict(source=base.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        older = cls.root / 'conker/build/game-owner-points-initializer-fitting-test/baseline.json'
        if older.exists():
            assert cls.baseline == json.loads(older.read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def test_01_full_shape_forms_profiles_and_slot_rejection(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
                         (158, 96, 110, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertNotEqual(self.words, self.retail)
        forms = []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            failures = []
            for pattern, phase in itertools.product(range(4), (0, 8)):
                try:
                    self.compare(recovery.fixture(pattern), phase=phase, bodies=(self.retail, words))
                except AssertionError as error:
                    failures.append(str(error).splitlines()[0])
            forms.append(dict(meta, contract_cases=8, contract_failures=failures))
        self.assertTrue(all(not row['contract_failures'] for row in forms), forms)
        profiles = []
        for profile in base.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.compare(recovery.fixture(), bodies=(self.retail, words))
            profiles.append(meta)
        self.receipt('shape', dict(selected=self.meta, forms=forms, profiles=profiles,
            full_source=True, frame_and_private_homes_fit=True,
            installation_rejected_one_word_overflow=True, installed=False, guards=0))

    def test_06_original_relocations_and_independent_rebases(self):
        owner = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + base.FUNCTION, 'endlabel ' + base.FUNCTION
        original = begin + owner.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + original)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        cases = 0
        for index, entry in enumerate((base.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = base.SYMBOLS if index == 0 else {name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(base.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 157), ('candidate', self.out / 'recovered.o', 158)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', base.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            if index == 0:
                self.assertEqual(bodies, [self.retail, self.words])
            for pattern, phase in itertools.product(range(4), (0, 8)):
                self.compare(recovery.fixture(pattern, symbols=symbols), symbols=symbols,
                    phase=phase, entry=entry, bodies=bodies)
                cases += 1
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=cases, executions=cases * 2,
            relocation_uses=sum(uses(obj).values()), complete_157_and_158_word_bodies=True,
            semantic_not_byte_exact=True))

    def test_03_independent_scales_aliases_and_effective_negatives(self):
        cases = 0
        for scales, pattern, phase in itertools.product(
                ((recovery.SCALE,) * 3, (recovery.bits(1.), recovery.bits(-1.), 0),
                 (1, 0x80000001, recovery.bits(2.)),
                 (recovery.bits(.25), recovery.bits(-.5), recovery.bits(4.))), range(4), (0, 8)):
            self.compare(recovery.fixture(pattern, scales=scales), phase=phase)
            cases += 1
        for actor, pattern in itertools.product(
                (0x800AA394 - 0x48, 0x800AA394 - 0x54, 0x800AA394 - 0x50), range(4)):
            self.compare(recovery.fixture(pattern, actor=actor), actor=actor)
            cases += 1
        replacements = (
            ('owner->flags &= ~2;', 'owner->flags |= 2;'), ('return 1;', 'return 0;'),
            ('count = 10;', 'count = 6;'), ('position.x += step.x;', 'position.x -= step.x;'),
            ('step.z = delta.z * D_800AA39C;', 'step.z = delta.z * D_800AA394;'),
            ('*(f32 *)(actor + 0x5C + (0) * 24) = 0.0f;',
             '*(f32 *)(actor + 0x5C + (0) * 24) = 1.0f;'))
        for index, (old, new) in enumerate(replacements):
            self.assertIn(old, screen.SELECTED)
            body = screen.SELECTED.replace(old, new)
            self.assertNotEqual(body, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-%d' % index, body)
            with self.assertRaises(AssertionError):
                self.compare(recovery.fixture(scales=(recovery.bits(.25), recovery.bits(-.5), recovery.bits(2.))),
                    bodies=(words,))
        self.receipt('mutations', dict(cases=cases, executions=cases * 2,
            first_record_constant_aliases=True, effective_compiled_negatives=len(replacements)))

    def test_07_actual_owner_neighbors_and_padder_overflow_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.TYPES.split('\n', 1)[1] +
            base.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(base.ORIGINAL, screen.SELECTED)
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
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == base.FUNCTION:
                continue
            previous = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (previous['size'], old[previous['value']:previous['value'] + previous['size']]), name)
            relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                if f['value'] <= o < f['value'] + f['size']}
            self.assertEqual(relative(nrels, function), relative(orels, previous), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, fs, _ = parse_object(self.out / 'recovered.o')
        target = nf[base.FUNCTION]
        self.assertEqual(target['size'], 632)
        self.assertEqual(new[target['value']:target['value'] + 632],
            isolated[fs[base.FUNCTION]['value']:fs[base.FUNCTION]['value'] + 632])
        with self.assertRaisesRegex(ValueError, 'func_151B3A7C'):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_preserved=True,
            zero_diagnostics=True, raw_target_equals_isolated=True,
            actual_padder_rejects_one_word_overflow=True, installed=False))

    def test_12_removed_zero_reload_and_complete_public_read_footprint(self):
        original_read_sets = set()
        cases = 0
        for pattern, phase in itertools.product(range(4), (0, 8)):
            models = self.compare(recovery.fixture(pattern), phase=phase)
            reads = []
            for model in models:
                public_reads = [(address, size) for operation, address, size, _ in model.events
                    if operation == 'R' and not recovery.STACK - 0x600 <= address < recovery.STACK + 0x140]
                self.assertEqual(len(public_reads), 13)
                self.assertFalse(any(recovery.ACTOR + 0x48 <= a < recovery.ACTOR + 0x138 for a, _ in public_reads))
                reads.append(Counter(public_reads))
            self.assertEqual(reads[0], reads[1])
            original_read_sets.add(tuple(sorted(reads[0].items())))
            self.assertEqual(models[0].memory, models[1].memory)
            cases += 1
        self.assertEqual(len(original_read_sets), 1)
        # The prior full-slot body really does issue the extra read; the gate is effective.
        _, prior_words = screen.compile_candidate(self.root, self.out, 'prior-full-slot', screen.SEED)
        model = recovery.PointOracle(prior_words, recovery.fixture()).run()
        extra = [(a, n) for op, a, n, _ in model.events if op == 'R'
            and recovery.ACTOR + 0x48 <= a < recovery.ACTOR + 0x138]
        self.assertEqual(extra, [(recovery.ACTOR + 0xA4, 4), (recovery.ACTOR + 0x104, 4)])
        self.receipt('public-reads', dict(cases=cases, executions=cases * 2, reads_per_call=13,
            footprint_and_multiplicity_match=True, zero_vector_reload_removed=True,
            prior_extra_reads_detected=2, read_order_and_hardware_not_matching=True))


if __name__ == '__main__':
    unittest.main()
