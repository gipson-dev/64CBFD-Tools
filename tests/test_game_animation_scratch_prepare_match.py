"""Full retail scratch-preparation match with checked normalization and private order."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_animation_scratch_prepare_matching as matching
from tools import pad_generated_object as padder
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_animation_scratch_prepare as previous

screen = previous.screen


class AnimationScratchMatchTests(previous.GameAnimationScratchPrepareTests):
    assemble = classmethod(previous.guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows = classmethod(previous.guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-animation-scratch-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, caller='conker/src/game/generated_6C960.c',
            elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s',
            symbols='conker/symbol_addrs.us.txt', undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out / 'baseline.json').exists():
            assert matching.SELECTED in (cls.root / screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.meta, cls.raw = matching.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>191I', cls.rom, screen.ROM))
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
        cls.fields = next(csv.reader((cls.out / 'before-guards').read_text().splitlines()))
        cls.write_rows(cls.out / 'target-guards.csv', cls.rows)
        cls.full_guards = cls.out / 'qualified-guards.csv'
        cls.full_guards.write_bytes((cls.out / 'before-guards').read_bytes())
        matching.append_guards(cls.full_guards, cls.full_guards.read_bytes(), cls.out / 'selected.o')
        cls.guard_bytes = cls.full_guards.read_bytes()
        body = (cls.root / 'conker/asm/58F80.s').read_text().split('glabel ' + screen.FUNCTION, 1)[1].split(
            'endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot = cls.out / 'slot.s'
        cls.slot.write_text('glabel ' + screen.FUNCTION + body + 'endlabel ' + screen.FUNCTION + '\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + screen.FUNCTION +
            '\n.type ' + screen.FUNCTION + ',@function\n' + screen.FUNCTION + ':\n' + body +
            '\n.size ' + screen.FUNCTION + ',.-' + screen.FUNCTION + '\n')
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot,
            filename='generated_58F80', word_patches_path=cls.out / 'target-guards.csv'))
        cls.fitted = cls.link('fitted', 191)
        assert cls.fitted == cls.retail
        cls.refresh = list(struct.unpack_from('>33I', cls.rom, 0x8B48C))
        assert cls.refresh == list(struct.unpack_from('>33I', cls.before,
            previous.elf_slot_offset(cls.before, previous.REFRESH, 132)))
        cls.selected_patch = patch.object(screen, 'SELECTED', matching.SELECTED)
        cls.selected_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.selected_patch.stop()

    @classmethod
    def link(cls, name, words, entry=screen.ENTRY, symbols=None):
        script = cls.out / (name + '-link.ld')
        elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
            '-e', screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in (symbols or screen.SYMBOLS).items()],
            '-o', str(elf), str(cls.out / (name + '.o'))], check=True, capture_output=True)
        return list(struct.unpack_from('>%dI' % words, previous.sections(elf)['.text'][1]))

    def compare(self, memory, args, forms=None, **settings):
        return super().compare(memory, args, forms=forms or (self.retail, self.raw, self.fitted), **settings)

    def test_01_full_semantic_body_not_claimed_byte_exact(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['diagnostics'], self.meta['pool_bytes']), (187, 80, 102, '', 0))
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual((len(self.fitted), -self.fitted[0] & 65535), (191, 104))
        for i in range(187):
            words = list(matching.RAW)
            words[i] ^= 1
            with self.assertRaisesRegex(ValueError, 'stale complete'):
                matching.recipe(words)
        text, functions, relocations = previous.parse_object(self.out / 'selected.o')
        start = functions[screen.FUNCTION]['value']
        for offset in matching.RELOCATIONS:
            broken = {o: list(v) for o, v in relocations.items()}
            broken[start + offset] = [('R_MIPS_26', 'wrong_helper')]
            with patch.object(matching, 'parse_object', return_value=(text, functions, broken)):
                with self.assertRaisesRegex(ValueError, 'stale complete.*relocations'):
                    matching.guard_rows(self.out / 'selected.o')
        with self.assertRaisesRegex(ValueError, 'stale animation.*manifest'):
            matching.append_guards(self.full_guards, b'wrong\n', self.out / 'selected.o')
        with self.assertRaisesRegex(ValueError, 'already published'):
            matching.append_guards(self.full_guards, self.guard_bytes, self.out / 'selected.o')
        self.assertEqual(len(self.rows), 187)
        self.assertEqual(sum(r['expected'] != r['replacement'] for r in self.rows), 46)
        self.assertEqual(sum(bool(r['insert_after']) for r in self.rows), 4)
        self.assertTrue(all(r['omit'] == 'false' for r in self.rows))
        self.receipt('shape', raw_words=187, raw_frame=80, raw_differences=102,
            fitted_words=191, fitted_frame=104, fitted_differences=0, expectation_rows=187,
            changed_words=46, insertions=4, omissions=0, stale_word_controls=187,
            stale_relocation_controls=5, diagnostics=0, pool_bytes=0)

    def test_02_byte_domains_frame_boundaries_alignments_and_NULL_gates(self):
        super().test_02_byte_domains_frame_boundaries_alignments_and_NULL_gates()
        path = self.out / 'guest.json'
        receipt = json.loads(path.read_text())
        receipt['executions'] = receipt['cases'] * 3
        receipt['raw_private_frame_equivalence_not_claimed'] = receipt.pop('private_frame_equivalence_not_claimed')
        receipt['fitted_retail_private_layout_exact'] = True
        self.receipt('guest', **receipt)

    def test_03_mutations_aliases_and_fired_public_fault_pairs(self):
        cases = pairs = 0
        for plan in range(5):
            memory, args = previous.fixture(length=7, flag=1, frame=7.5, actor=True, sentinel=65535)
            models = self.compare(memory, args, plan=plan)
            cases += 1
            for cut in range(models[0].public_accesses):
                failed = []
                for code in (self.retail, self.raw, self.fitted):
                    model = previous.PrepareOracle(code, memory, args, plan=plan)
                    model.public_fault = cut
                    with self.assertRaises(previous.guest.AccessFault) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args, (cut,))
                    self.assertEqual(model.public_accesses, cut)
                    failed.append((previous.public(model.memory), previous.events_public(model.events), model.calls))
                self.assertEqual(failed[0], failed[1])
                self.assertEqual(failed[0], failed[2])
                pairs += 1
        for alias in (previous.NODE + 0x40, previous.NODE + 0x30):
            memory, args = previous.fixture(length=3, frame=7.5, flag=1)
            self.compare(memory, (args[0], args[1], alias))
            cases += 1
        self.receipt('aliases', cases=cases, fired_public_fault_triples=pairs,
            failed_executions=pairs * 3, raw_private_fault_order_not_claimed=True)

    def test_04_independently_rebased_five_JAL_sites(self):
        cases = 0
        for i in range(3):
            entry = 0x15217FFC + i * 0x10004
            symbols = {name: 0x15417FFC + i * 0x10004 + j * 0x100
                for j, name in enumerate(screen.SYMBOLS)}
            original = self.link('original', 191, entry, symbols)
            raw = self.link('selected', 187, entry, symbols)
            fitted = self.link('fitted', 191, entry, symbols)
            self.assertEqual(fitted, original)
            for length, frame, plan in itertools.product((0, 7, 255), (2.25, 7.5), (0, 2, 3)):
                memory, args = previous.fixture(length=length, frame=frame, flag=1)
                self.compare(memory, args, forms=(original, raw, fitted), entry=entry, symbols=symbols, plan=plan)
                cases += 1
        self.receipt('rebases', links=9, symbol_sets=3, cases=cases, executions=cases * 3,
            all_five_JAL_sites=True, independently_assembled_retail=True)

    def test_05_actual_33_word_actor_refresh_connection(self):
        connected = {previous.REFRESH + i * 4: w for i, w in enumerate(self.refresh)}
        cases = 0
        for flag, node in itertools.product((0, 1), (0, previous.NODE)):
            memory, args = previous.fixture(flag=flag, actor=True, sentinel=65535)
            previous.put(memory, previous.ACTOR + 4, 3, 1)
            previous.put(memory, previous.ACTOR + 0x2D0, node)
            for i in range(8):
                memory[0x800C4ED0 + i] = 0
            previous.put(memory, 0x800C4ED0 + 6, 5, 2)
            models = [previous.PrepareOracle(code, memory, args, connected=connected).run()
                for code in (self.retail, self.raw, self.fitted)]
            for model in models[1:]:
                self.assertEqual((previous.public(model.memory), previous.events_public(model.events), model.calls),
                    (previous.public(models[0].memory), previous.events_public(models[0].events), models[0].calls))
            self.assertFalse(any(call[0] in (previous.SMALL, previous.DMA) for call in models[0].calls))
            cases += 1
        self.receipt('refresh', cases=cases, executions=cases * 3, actual_33_word_helper=True, bzero_bounded=True)

    def test_06_effective_IDO_negative_controls(self):
        super().test_06_effective_IDO_negative_controls()
        controls = ('wrong-length', 'wrong-bank-sign', 'wrong-alignment', 'wrong-threshold',
            'wrong-stride', 'wrong-wrap-mask', 'wrong-offset')
        for name in controls:
            with self.assertRaisesRegex(ValueError, 'stale complete|unexpected complete'):
                matching.guard_rows(self.out / (name + '.o'))
        self.receipt('negative', effective_fresh_IDO_controls=7, normalization_rejects_all_7=True)

    def test_07_copied_owner_and_submit_contract_requalification(self):
        source = (self.out / 'before-source').read_text()
        obj, diagnostics = previous.compile_owner(self.root, self.out, source, 'owner')
        self.assertEqual(diagnostics, [])
        subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'),
            '-O2', '-g3', str((self.out / 'owner.c').relative_to(self.root / 'conker')), '--post-process',
            str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
            '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
        padded = []
        for name, guards in (('before', self.out / 'before-guards'), ('after', self.full_guards)):
            asm = self.out / ('owner-' + name + '.s')
            subprocess.run(['python3', str(self.root / 'tools/pad_c_object.py'), str(obj),
                str(self.root / 'conker/retail_layout.us.txt'), 'generated_58F80', str(asm),
                '--word-patches', str(guards)], check=True, capture_output=True)
            self.assemble('owner-' + name, asm.read_text())
            padded.append(previous.parse_object(self.out / ('owner-' + name + '.o')))
        a, b = padded
        start = a[1][screen.FUNCTION]['value']
        end = start + 764
        self.assertEqual(a[0][:start] + a[0][end:], b[0][:start] + b[0][end:])
        for name in a[1]:
            if name != screen.FUNCTION:
                self.assertEqual(a[1][name], b[1][name])
        self.assertEqual({o: v for o, v in a[2].items() if not start <= o < end},
            {o: v for o, v in b[2].items() if not start <= o < end})
        self.assertEqual(b[1][screen.FUNCTION]['size'], 764)
        self.assertEqual((self.root / self.paths['caller']).read_bytes(), (self.out / 'before-caller').read_bytes())
        previous.submit.GameNodeTransformSubmitMatchTests.setUpClass()
        self.assertEqual(previous.submit.GameNodeTransformSubmitMatchTests.fitted,
            previous.submit.GameNodeTransformSubmitMatchTests.original)
        self.receipt('owner', untouched_neighbors=len(a[1]) - 1, bytes_extents_relocations_exact=True,
            source_and_compiler_pools_unchanged=True, diagnostics=0, current_66_word_submit_stays_exact=True)

    def test_08_whole_ELF_only_preparation_slot_and_size_change(self):
        actual = (self.root / self.paths['elf']).read_bytes()
        manifest = (self.root / self.paths['guards']).read_bytes()
        if manifest == (self.out / 'before-guards').read_bytes():
            self.receipt('linked', installed=False)
            return
        self.assertEqual(manifest, self.guard_bytes)
        expected = bytearray(self.before)
        offset = previous.elf_slot_offset(self.before, screen.ENTRY, 764)
        struct.pack_into('>191I', expected, offset, *self.retail)
        old, new = previous.metadata(self.before), previous.metadata(actual)
        self.assertEqual(old[:2], new[:2])
        self.assertEqual(old[3:], new[3:])
        section, changed = old[4], 0
        for position in range(section[4], section[4] + section[5], section[9]):
            a = previous.SYMBOL.unpack_from(self.before, position)
            b = previous.SYMBOL.unpack_from(actual, position)
            if a != b:
                self.assertEqual(a[1], screen.ENTRY)
                self.assertEqual(a[:2] + a[3:], b[:2] + b[3:])
                self.assertEqual((a[2], b[2]), (748, 764))
                struct.pack_into('>I', expected, position + 8, b[2])
                changed += 1
        self.assertEqual(changed, 1)
        self.assertEqual(bytes(expected), actual)
        for name in self.paths:
            if name not in ('elf', 'guards'):
                self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        audit = previous.audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'])
        self.assertTrue(manifest.startswith((self.out / 'before-guards').read_bytes()))
        self.receipt('linked', installed=True, ELF_bytes=len(actual), ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a, b in zip(self.before, actual)), all_other_ELF_bytes_exact=True,
            data_audit=audit, source_conversion_rows_unchanged=True, matching_credit_added=1,
            expectation_rows_added=187, changed_replacements=46, insertions=4, old_manifest_prefix_exact=True)

    def test_09_complete_66_word_transform_caller_connection(self):
        super().test_09_complete_66_word_transform_caller_connection()
        with patch.object(self, 'raw', self.fitted):
            super().test_09_complete_66_word_transform_caller_connection()
        self.receipt('caller', cases=40, executions=160, actual_complete_66_word_caller=True,
            full_retail_raw_and_fitted_preparers=True, retail_repeated_for_independent_pairs=True,
            gate_and_safe_NULL_temporary_paths=True, other_callbacks_bounded=True)

    def test_11_private_frame_contract_aliases_and_all_access_fault_pairs(self):
        pairs = cases = 0
        for phase, flag, length, frame in itertools.product((0, 8), (0, 1), (0, 7), (2.25, 7.5)):
            memory, args = previous.fixture(flag=flag, length=length, frame=frame)
            models = [previous.PrepareOracle(code, memory, args, phase=phase).run()
                for code in (self.retail, self.fitted)]
            self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].calls, models[1].r, models[1].f))
            for cut in range(models[0].accesses):
                failed = []
                for code in (self.retail, self.fitted):
                    model = previous.PrepareOracle(code, memory, args, phase=phase)
                    model.fault = cut
                    with self.assertRaises(previous.guest.AccessFault) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args, (cut,))
                    self.assertEqual(model.accesses, cut)
                    failed.append(model)
                self.assertEqual((failed[0].memory, failed[0].events, failed[0].calls, failed[0].r, failed[0].f),
                    (failed[1].memory, failed[1].events, failed[1].calls, failed[1].r, failed[1].f))
                pairs += 1
            cases += 1
        for phase, flag in itertools.product((0, 8), (0, 1)):
            memory, args = previous.fixture(flag=flag, length=0, second=0)
            model = previous.PrepareOracle(self.fitted, memory, args, phase=phase).run()
            base = previous.STACK + phase - 104
            saved = model.before
            stores = [(offset, saved[reg], 4) for offset, reg in
                ((0x40, 30), (0x24, 17), (0x20, 16), (0x44, 31), (0x3C, 23),
                 (0x38, 22), (0x34, 21), (0x30, 20), (0x2C, 19), (0x28, 18))]
            stores += [(0x18, model.saved_f[1] << 32 | model.saved_f[0], 8), (0x48, 1, 4)]
            expected = [('W', base + off, size, value) for off, value, size in stores]
            banks = 2 if flag else 1
            if flag:
                expected.append(('W', base + 0x48, 4, 2))
            expected += [('R', base + 0x48, 4, banks)] * (banks + 1)
            expected += [('R', base + off, size, value) for off, value, size in
                [(0x44, saved[31], 4), (0x18, model.saved_f[1] << 32 | model.saved_f[0], 8)] +
                [(0x20 + i * 4, saved[16 + i], 4) for i in range(8)] + [(0x40, saved[30], 4)]]
            private_events = [e for e in model.events if e[0] != 'CALL' and previous.private(e[1])]
            self.assertEqual(private_events, expected)
            self.assertEqual({a: model.memory[a] for a in range(base + 0x4C, base + 104)},
                {a: memory[a] for a in range(base + 0x4C, base + 104)})
            cases += 1
        for phase in (0, 8):
            base = previous.STACK + phase - 104
            for node, scratch in ((previous.NODE, base + 0x4C), (base + 0x4C, previous.SCRATCH)):
                memory, args = previous.fixture(node=node, length=3, flag=0, frame=2.25)
                models = [previous.PrepareOracle(code, memory, (node, 0, scratch), phase=phase).run()
                    for code in (self.retail, self.fitted)]
                self.assertEqual((models[0].memory, models[0].events, models[0].calls),
                    (models[1].memory, models[1].events, models[1].calls))
                cases += 1
        self.receipt('private', cases=cases, fired_all_access_fault_pairs=pairs, failed_executions=pairs * 2,
            fitted_retail_complete_GP_FPR_memory_events_calls=True, independent_frame_save_home_restore_contract=True,
            unwritten_28_byte_capacity_retained=True, scratch_node_private_alias_cases=4,
            raw_0x50_private_fault_alias_equivalence_not_claimed=True)

    def test_12_actual_padder_rejects_every_stale_word_and_relocation(self):
        text, functions, relocations = previous.parse_object(self.out / 'selected.o')
        start = functions[screen.FUNCTION]['value']
        for i in range(187):
            changed = bytearray(text)
            changed[start + i * 4 + 3] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(changed), functions, relocations)):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    emit_padded_assembly(self.out / 'selected.o', self.slot, filename='generated_58F80',
                        word_patches_path=self.out / 'target-guards.csv')
        for offset in matching.RELOCATIONS:
            changed = {o: list(v) for o, v in relocations.items()}
            changed[start + offset] = [('R_MIPS_26', 'wrong_helper')]
            with patch.object(padder, 'parse_object', return_value=(text, functions, changed)):
                with self.assertRaisesRegex(ValueError, 'stale relocations'):
                    emit_padded_assembly(self.out / 'selected.o', self.slot, filename='generated_58F80',
                        word_patches_path=self.out / 'target-guards.csv')
        self.receipt('padder', effective_stale_word_controls=187, effective_stale_relocation_controls=5,
            production_padder_used=True, complete_identity_expectations_enforced=True)

    def test_13_callback_private_bank_home_is_live_and_bounded(self):
        class HomeOracle(previous.PrepareOracle):
            def hook(self, target):
                super().hook(target)
                if self.roles[target] in (previous.SMALL, previous.DMA) and self.copies == 1:
                    self.put(self.r[29] + 0x48, 2, 4)
        cases = 0
        for phase in (0, 8):
            memory, args = previous.fixture(flag=0, length=7, frame=2.25)
            models = [HomeOracle(code, memory, args, phase=phase).run() for code in (self.retail, self.fitted)]
            self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].calls, models[1].r, models[1].f))
            self.assertEqual(len(models[0].calls), 2)
            first = (args[2] + 15) & ~15
            first_skip = (previous.read(memory, args[0] + 0x28) + 7 * 2) & 3
            second = (first + 7 * 2 + first_skip + 15) & ~15
            second_skip = (previous.read(memory, args[0] + 0x2C) + 11 * 2) & 3
            self.assertEqual(previous.read(models[0].memory, args[0] + 0x34), second + second_skip)
            cases += 1
        self.receipt('private-home', cases=cases, executions=cases * 2,
            bank_count_home_reloaded_after_callback=True, one_to_two_bank_extension=True,
            raw_different_frame_not_compared=True)


if __name__ == '__main__':
    unittest.main()
