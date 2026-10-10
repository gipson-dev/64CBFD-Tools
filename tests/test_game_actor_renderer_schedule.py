"""Qualify full 532-word renderer padding and private order before installation."""
import csv
import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_renderer_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_renderer_recovery as proof
from tools.tests import test_game_actor_renderer_layout as private


class GameActorRendererScheduleTests(unittest.TestCase):
    assemble = classmethod(private.GameActorRendererLayoutTests.assemble.__func__)
    write_rows = classmethod(proof.guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-schedule-test'
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
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields = reader.fieldnames
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>532I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + screen.FUNCTION, 1)[1].split('endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot_asm = cls.out / 'slot.s'
        cls.slot_asm.write_text('glabel ' + screen.FUNCTION + assembly +
            'endlabel ' + screen.FUNCTION + '\n')
        cls.rows = screen.guard_rows(cls.out / 'selected.o')
        cls.write_rows(cls.out / 'isolated.csv', cls.rows)
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + screen.FUNCTION +
            '\n.type ' + screen.FUNCTION + ',@function\n' + screen.FUNCTION + ':\n' + assembly +
            '\n.size ' + screen.FUNCTION + ',.-' + screen.FUNCTION + '\n')
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot_asm,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80'))
        cls.fitted = cls.link('fitted', proof.S)
        cls.coverage, cls.cases = set(), 0

    @classmethod
    def link(cls, name, symbols):
        script = cls.out / ('link-%s-%X.ld' % (name, symbols['D_800CC2D0']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % screen.ENTRY)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e',
            screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
            '-o', str(elf), str(cls.out / (name + '.o'))], check=True, capture_output=True)
        size = parse_object(cls.out / (name + '.o'))[1][screen.FUNCTION]['size'] // 4
        return list(struct.unpack_from('>%dI' % size, sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, slot=0, view=0, mode=0, extra=0, alpha=255, phase=0, plan=None):
        args = (proof.OUTPUT, slot, view, 0x27000, alpha, proof.PARAMETERS, mode, extra)
        returned, result, calls = proof.reference(memory, args, plan)
        expected = returned, {a: v for a, v in result.items() if proof.public(a)}, calls
        models = [proof.RendererOracle(words, memory, args, phase, plan).run()
            for words in (self.retail, self.raw, self.fitted)]
        for model in models:
            self.assertEqual(proof.projection(model), expected)
            self.assertEqual(model.memory, models[0].memory)
            self.assertEqual(model.events, models[0].events)
            self.assertEqual(model.accesses, models[0].accesses)
        self.coverage.update(models[0].visits)
        type(self).cases += 1
        return models

    def test_01_actual_padder_complete_shape_and_no_missing_body_fill(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (531, 0x150, 0, ''))
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(len(self.rows), 531)
        self.assertEqual(sum(row['expected'] != row['replacement'] for row in self.rows), 122)
        self.assertEqual([i for i, row in enumerate(self.rows) if row['omit'] == 'true'], [327])
        self.assertEqual([i for i, row in enumerate(self.rows) if row['insert_after']], [452, 453])
        self.assertEqual(parse_object(self.out / 'fitted.o')[1][screen.FUNCTION]['size'], 2128)
        original = parse_object(self.out / 'original.o')
        target = original[1][screen.FUNCTION]
        self.assertEqual(screen.OUTPUT_RELOCATIONS,
            {offset - target['value']: uses for offset, uses in original[2].items()
                if target['value'] <= offset < target['value'] + target['size']})
        self.receipt('shape', original_words=532, raw_words=531, fitted_words=532, frame=0x150,
            guards=531, changed_words=sum(row['expected'] != row['replacement'] for row in self.rows),
            insertions=2, omissions=1, padding=0, all_original_relocations_exact=True,
            existing_branch_and_live_count_read_duplicated=True, consumer_not_installed=True)

    def test_02_complete_private_semantics_all_532_words(self):
        private.GameActorRendererLayoutTests.test_01_full_behavior_and_private_accesses(self)
        self.receipt('complete-private', primary_cases=273, complete_executions=819,
            original_words_covered=len(self.coverage), original_raw_and_fitted_memory_order_exact=True,
            independent_public_reference=True, bounded_callbacks=True,
            real_helper_native32_or_hardware_claim=False)

    def test_03_fitted_aliases_and_every_full_fault_prefix(self):
        raw = self.raw
        try:
            self.raw = self.fitted
            private.GameActorRendererLayoutTests.test_03_incoming_private_and_public_aliases(self)
            private.GameActorRendererLayoutTests.test_04_every_requested_full_fault_prefix_fires(self)
        finally:
            self.raw = raw

    def test_04_actual_complete_owner_padding_changes_only_target(self):
        before = (self.out / 'before-source').read_text()
        objects, diagnostics = [], []
        for name, body in (('owner-before', before),
                ('owner-after', screen.recovery.copied_owner(before, screen.SELECTED))):
            obj, warnings = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics, [[], []])
        parsed = [parse_object(obj) for obj in objects]
        def body(data, name):
            text, functions, relocations = data
            start, size = functions[name]['value'], functions[name]['size']
            return text[start:start + size], {offset - start: uses for offset, uses in relocations.items()
                if start <= offset < start + size}
        self.assertEqual(parsed[0][1].keys(), parsed[1][1].keys())
        for name in parsed[0][1]:
            if name != screen.FUNCTION:
                self.assertEqual(body(parsed[0], name), body(parsed[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]), self.rows)
        with (self.out / 'before-guards').open(newline='') as stream:
            old_rows = list(csv.DictReader(stream))
        guards = self.out / 'qualified-owner-guards.csv'
        self.write_rows(guards, old_rows + self.rows)
        padded = []
        for i, obj in enumerate(objects):
            name = 'padded-owner-%d' % i
            self.assemble(name, emit_padded_assembly(obj, self.root / 'conker/asm/58F80.s',
                word_patches_path=self.out / 'before-guards' if i == 0 else guards,
                filename='generated_58F80', rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out / (name + '.o')))
        start = padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'], 2128)
        self.assertEqual(padded[0][0][:start], padded[1][0][:start])
        self.assertEqual(padded[0][0][start + 2128:], padded[1][0][start + 2128:])
        self.assertEqual(struct.unpack_from('>532I', padded[1][0], start), tuple(screen.recipe(screen.RAW)))
        self.receipt('owner', neighbors=len(parsed[0][1]) - 1, compiler_diagnostics=0,
            bodies_relative_relocations_and_pools_exact=True, target_equals_isolated=True,
            actual_padder_only_target_2128_byte_slot_changes=True, consumer_not_installed=True)

    def test_05_independent_rebases_and_complete_private_order(self):
        cases = 0
        for delta in (0, 0x47FFC, 0x58004):
            symbols = {name: (value + (0 if name.startswith('func_') else delta)) & 0xFFFFFFFF
                for name, value in proof.S.items()}
            bodies = [self.link(name, symbols) for name in ('original', 'fitted', 'selected')]
            self.assertEqual(bodies[0], bodies[1])
            with patch.dict(proof.S, symbols, clear=True):
                for mode in (0, 3, 5):
                    args = (proof.OUTPUT, 0, 0, 0x27000, -1, proof.PARAMETERS, mode, 1)
                    memory = proof.fixture(skip=2, override=5)
                    models = [proof.RendererOracle(words, memory, args).run() for words in bodies]
                    for model in models[1:]:
                        self.assertEqual(model.memory, models[0].memory)
                        self.assertEqual(model.events, models[0].events)
                        self.assertEqual(model.r[2], models[0].r[2])
                    cases += 1
        self.receipt('links', independent_links=9, cases=cases, all_532_fitted_words_exact=True,
            signed_LO16_carries_and_physical_aliases=True, complete_private_memory_and_order_exact=True)

    def test_06_every_stale_word_and_relocation_is_rejected(self):
        raw = (self.out / 'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(raw)
        headers = [SECTION_HEADER.unpack_from(raw, header[6] + i * header[11]) for i in range(header[12])]
        text = next(section for section in headers if section[2] & 4)
        for index in range(531):
            words = list(screen.RAW)
            words[index] ^= 0x10000
            with self.assertRaisesRegex(ValueError, 'stale complete actor renderer'):
                screen.recipe(words)
            damaged = bytearray(raw)
            struct.pack_into('>I', damaged, text[4] + index * 4, words[index])
            path = self.out / 'stale.o'
            path.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit_padded_assembly(path, self.slot_asm, word_patches_path=self.out / 'isolated.csv',
                    filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows = [dict(row) for row in self.rows]
            rows[offset // 4]['expected_relocations'] = '-'
            path = self.out / 'stale-relocations.csv'
            self.write_rows(path, rows)
            with self.assertRaisesRegex(ValueError, 'stale relocations'):
                emit_padded_assembly(self.out / 'selected.o', self.slot_asm, word_patches_path=path,
                    filename='generated_58F80')
        self.receipt('stale', recipe_word_rejections=531, actual_padder_word_rejections=531,
            actual_padder_relocation_rejections=len(screen.RELOCATIONS), complete_dependency_gates=True)

    def test_07_complete_compiled_negative_controls(self):
        for name, old, new in (
                ('wrong-fog-bit', '0x400000', 'G_FOG'),
                ('wrong-primitive-control', '0xF2, 0, primitiveR', '0, 0xF2, primitiveR'),
                ('missing-tail-state', 'actor[0x2FE] = 1;', 'actor[0x2FE] = 0;')):
            self.assertIn(old, screen.SELECTED)
            _, damaged = screen.compile_candidate(self.root, self.out, name, screen.SELECTED.replace(old, new))
            with self.assertRaisesRegex(ValueError, 'stale complete actor renderer'):
                text, functions, _ = parse_object(self.out / (name + '.o'))
                target = functions[screen.FUNCTION]
                screen.recipe(struct.unpack_from('>%dI' % (target['size'] // 4), text, target['value']))
            args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, 0, 0)
            memory = proof.fixture(skip=2, override=5)
            models = [proof.RendererOracle(words, memory, args).run() for words in (self.retail, damaged)]
            self.assertNotEqual(proof.projection(models[0]), proof.projection(models[1]))
        self.receipt('negatives', effective_complete_compiled_forms=3, recipe_rejects_each=True)

    def test_08_production_and_prior_baselines_unchanged(self):
        private.GameActorRendererLayoutTests.test_08_production_and_immutable_baselines_unchanged(self)


if __name__ == '__main__':
    unittest.main()
