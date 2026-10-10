"""Full renderer private layout proofs; callbacks remain explicit bounded models."""
import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_renderer_candidates as recovery
from tools.experiments import game_actor_renderer_layout as layout
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_renderer_recovery as proof


class GameActorRendererLayoutTests(unittest.TestCase):
    assemble = classmethod(proof.GameActorRendererRecoveryTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-layout-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=recovery.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.retail = list(struct.unpack_from('>532I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), recovery.ROM))
        cls.meta, cls.raw = recovery.compile_candidate(cls.root, cls.out, 'selected', layout.SELECTED)
        cls.coverage, cls.cases = set(), 0

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, slot=0, view=0, mode=0, extra=0, alpha=255, phase=0, plan=None):
        args = (proof.OUTPUT, slot, view, 0x27000, alpha, proof.PARAMETERS, mode, extra)
        returned, result, calls = proof.reference(memory, args, plan)
        expected = returned, {a: v for a, v in result.items() if proof.public(a)}, calls
        models = [proof.RendererOracle(words, memory, args, phase, plan).run()
            for words in (self.retail, self.raw)]
        for model in models:
            self.assertEqual(proof.projection(model), expected)
        self.assertEqual(models[0].memory, models[1].memory)
        self.assertEqual(models[0].events, models[1].events)
        self.assertEqual(models[0].accesses, models[1].accesses)
        self.coverage.update(models[0].visits)
        type(self).cases += 1
        return models

    def test_01_full_behavior_and_private_accesses(self):
        for name in ('test_01_complete_graphics_modes_colors_and_lighting',
                'test_02_early_returns_live_masks_and_shift_boundaries',
                'test_03_callback_mutations_and_captured_lifetimes',
                'test_03b_lighting_force_flag_and_identity_boundaries'):
            getattr(proof.GameActorRendererRecoveryTests, name)(self)
        self.assertEqual(self.cases, 273)
        self.assertEqual(len(self.coverage), 532)
        self.receipt('complete-private', cases=self.cases, executions=self.cases * 2,
            original_words_covered=532, complete_memory_and_access_order_exact=True,
            independent_public_reference=True, bounded_callbacks=True,
            connected_helpers_native32_or_hardware_claim=False)

    def test_02_exact_frame_homes_and_saved_map(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (531, 0x150, 0, ''))
        original = layout.physical_metadata(self.retail, dict(frame=0x150))
        candidate = layout.physical_metadata(self.raw, self.meta)
        self.assertEqual(candidate, original)
        self.assertEqual(candidate['color_offsets'], list(range(0x128, 0x100, -4)))
        self.assertEqual(candidate['saved_registers'],
            {str(r): 0x40 + (r - 16) * 4 for r in range(16, 23)} | {'31': 0x5C})
        self.assertEqual(candidate['color_deltas'], [0] * 10)
        self.assertIn('(part & 31)', layout.SELECTED)
        self.receipt('physical-shape', raw=self.meta, homes=candidate,
            original_frame_and_all_color_homes_exact=True,
            production_installation_or_word_match=False)

    def test_03_incoming_private_and_public_aliases(self):
        cases = 0
        for phase in (0, 8):
            for parameters in (proof.PARAMETERS, proof.OUTPUT, proof.STACK + phase + 16,
                    proof.STACK + phase - 0x28, proof.STACK + phase - 0x4C):
                args = (proof.OUTPUT, 0, 0, 0x27000, 255, parameters, 0, 1)
                models = [proof.RendererOracle(words, proof.fixture(), args, phase).run()
                    for words in (self.retail, self.raw)]
                self.assertEqual(models[0].memory, models[1].memory)
                self.assertEqual(models[0].events, models[1].events)
                self.assertEqual(models[0].r[2], models[1].r[2])
                cases += 1
            for before, after, callback in ((4, 3, 'func_150849CC'),
                    (0, 3, 'func_1503DA9C'), (3, 0, 'func_1502CC34')):
                args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, before, 0)
                plan = proof.Plan(actions={(callback, 0):
                    ((proof.STACK + phase + 24, after, 4),)})
                models = [proof.RendererOracle(words, proof.fixture(), args, phase, plan).run()
                    for words in (self.retail, self.raw)]
                self.assertEqual(models[0].memory, models[1].memory)
                self.assertEqual(models[0].events, models[1].events)
                self.assertEqual(models[0].r[2], models[1].r[2])
                cases += 1
        self.receipt('aliases', cases=cases, parameter_array_public_and_private_aliases=True,
            incoming_mode_callback_mutations=True, full_memory_and_events_exact=True)

    def test_04_every_requested_full_fault_prefix_fires(self):
        prefixes, cases = 0, 0
        for mode, count, special, phase in ((0, 4, True, 0), (0, 4, True, 8),
                (3, 3, True, 0), (3, 3, False, 8), (5, 0, True, 0), (4, 33, True, 8)):
            args = (proof.OUTPUT, 0, 0, 0x27000, -1, proof.PARAMETERS, mode, 1)
            memory = proof.fixture(count=count, special=special, skip=2, override=5)
            original = proof.RendererOracle(self.retail, memory, args, phase).run()
            for fault in range(original.accesses):
                models = []
                for words in (self.retail, self.raw):
                    model = proof.RendererOracle(words, memory, args, phase)
                    model.fault = fault
                    with self.assertRaises(proof.guest.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                    models.append(model)
                self.assertEqual(models[0].memory, models[1].memory, (mode, phase, fault))
                self.assertEqual(models[0].events, models[1].events, (mode, phase, fault))
                self.assertEqual(models[0].calls, models[1].calls, (mode, phase, fault))
                prefixes += 1
            cases += 1
        self.receipt('faults', complete_cases=cases, fired_prefix_pairs=prefixes,
            complete_private_and_public_memory_events_and_calls_exact=True,
            absence_of_exception_is_failure=True, portable_C_fault_claim=False)

    def test_05_old_public_only_layout_is_an_effective_negative(self):
        meta, old = recovery.compile_candidate(self.root, self.out, 'old-layout')
        args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, 0, 0)
        models = [proof.RendererOracle(words, proof.fixture(), args).run()
            for words in (self.retail, old)]
        self.assertEqual(proof.projection(models[0]), proof.projection(models[1]))
        self.assertNotEqual(models[0].memory, models[1].memory)
        self.assertNotEqual(models[0].events, models[1].events)
        self.receipt('private-negative', compiled_words=meta['body_words'], frame=meta['frame'],
            public_reference_passes_but_full_memory_and_events_fail=True)

    def test_06_copied_owner_neighbors_relocations_and_pools(self):
        before = (self.out / 'before-source').read_text()
        objects = []
        for name, source in (('owner-before', before),
                ('owner-after', recovery.copied_owner(before, layout.SELECTED))):
            obj, diagnostics = compile_owner(self.root, self.out, source, name)
            self.assertFalse(diagnostics)
            objects.append(parse_object(obj))
        def body(parsed, name):
            text, functions, relocations = parsed
            start, size = functions[name]['value'], functions[name]['size']
            return text[start:start + size], {offset - start: entries
                for offset, entries in relocations.items() if start <= offset < start + size}
        neighbors = 0
        for name in objects[0][1]:
            if name == recovery.FUNCTION: continue
            self.assertEqual(body(objects[0], name), body(objects[1], name), name)
            neighbors += 1
        self.assertEqual(body(objects[1], recovery.FUNCTION),
            body(parse_object(self.out / 'selected.o'), recovery.FUNCTION))
        self.assertEqual(normalized_pools(self.out / 'owner-before.o'),
            normalized_pools(self.out / 'owner-after.o'))
        self.receipt('owner', neighbors=neighbors, exact_bodies_relative_relocations_and_pools=True,
            target_equals_isolated=True, compiler_diagnostics=0, consumer_not_installed=True)

    def test_07_independent_rebases_preserve_full_private_proof(self):
        assembly = (self.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + recovery.FUNCTION, 1)[1].split('endlabel ' + recovery.FUNCTION, 1)[0]
        self.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + recovery.FUNCTION +
            '\n.type ' + recovery.FUNCTION + ',@function\n' + recovery.FUNCTION + ':\n' + assembly +
            '\n.size ' + recovery.FUNCTION + ',.-' + recovery.FUNCTION + '\n')
        cases = 0
        for delta in (0, 0x47FFC, 0x58004):
            symbols = {name: (value + (0 if name.startswith('func_') else delta)) & 0xFFFFFFFF
                for name, value in proof.S.items()}
            script = self.out / ('rebase-%X.ld' % delta)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % recovery.ENTRY)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e',
                recovery.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                '-o', str(elf), str(self.out / 'original.o')], check=True, capture_output=True)
            original = list(struct.unpack_from('>532I', sections(elf)['.text'][1]))
            if delta == 0: self.assertEqual(original, self.retail)
            with patch.dict(proof.S, symbols, clear=True):
                _, raw = recovery.compile_candidate(self.root, self.out, 'rebase-C-%X' % delta,
                    layout.SELECTED)
                for mode in (0, 3, 5):
                    args = (proof.OUTPUT, 0, 0, 0x27000, -1, proof.PARAMETERS, mode, 1)
                    memory = proof.fixture(skip=2, override=5)
                    models = [proof.RendererOracle(words, memory, args).run() for words in (original, raw)]
                    self.assertEqual(proof.projection(models[0]), proof.projection(models[1]))
                    self.assertEqual(models[0].memory, models[1].memory)
                    self.assertEqual(models[0].events, models[1].events)
                    cases += 1
        self.receipt('rebases', independent_links=6, cases=cases, signed_LO16_carries=True,
            retained_virtual_and_physical_aliases=True, full_private_memory_and_events_exact=True)

    def test_08_production_and_immutable_baselines_unchanged(self):
        hashes = json.loads((self.out / 'baseline.json').read_text())
        previous = self.root / 'conker/build/game-actor-renderer-test'
        self.assertEqual(hashes, json.loads((previous / 'baseline.json').read_text()))
        for name, path in self.paths.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), hashes[name])
            self.assertEqual(data, (self.out / ('before-' + name)).read_bytes())
            self.assertEqual(data, (previous / ('before-' + name)).read_bytes())
        self.assertIn(recovery.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        self.receipt('unchanged', baseline=hashes, production_target_still_placeholder=True,
            guards_source_ELF_progress_and_rodata_unchanged=True, previous_baseline_not_modified=True)


if __name__ == '__main__':
    unittest.main()
