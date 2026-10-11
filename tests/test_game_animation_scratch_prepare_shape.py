"""Qualify the retail-shaped loop without claiming full byte or frame matching."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_animation_scratch_prepare_shape as shape
from tools.tests import test_game_animation_scratch_prepare as previous

screen = previous.screen


class AnimationScratchShapeTests(previous.GameAnimationScratchPrepareTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-animation-scratch-shape-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, caller='conker/src/game/generated_6C960.c',
            elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s',
            symbols='conker/symbol_addrs.us.txt', undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out / 'baseline.json').exists():
            assert screen.BASE in (cls.root / screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected', shape.SELECTED)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>191I', cls.rom, screen.ROM))
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.guard_bytes = (cls.out / 'before-guards').read_bytes()
        (cls.out / 'qualified-guards.csv').write_bytes(cls.guard_bytes)
        cls.refresh = list(struct.unpack_from('>33I', cls.rom, 0x8B48C))
        assert cls.refresh == list(struct.unpack_from('>33I', cls.before,
            previous.elf_slot_offset(cls.before, previous.REFRESH, 132)))
        cls.selected_patch = patch.object(screen, 'SELECTED', shape.SELECTED)
        cls.selected_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.selected_patch.stop()

    def test_01_full_semantic_body_not_claimed_byte_exact(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['diagnostics'], self.meta['pool_bytes']), (187, 80, 102, '', 0))
        self.assertEqual(len(self.meta['relocations']), 5)
        self.assertNotEqual(self.raw, self.retail)
        for bad in (shape.SELECTED, screen.BASE + '\n' + screen.BASE,
                screen.BASE.replace('length * 2', 'length * 3')):
            with self.assertRaisesRegex(ValueError, 'stale complete'):
                shape.install(bad)
        self.receipt('shape', raw_words=187, retail_words=191, raw_frame=80, retail_frame=104,
            isolated_word_differences=102, previous_differences=162, word_guards=0,
            matching_not_achieved=True, compiler_diagnostics=0, pool_bytes=0)

    def test_04_independently_rebased_five_JAL_sites(self):
        cases = 0
        for i in range(3):
            entry = 0x15217FFC + i * 0x10004
            symbols = {name: 0x15417FFC + i * 0x10004 + j * 0x100
                for j, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % i)
            elf = script.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                '-e', screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                '-o', str(elf), str(self.out / 'selected.o')], check=True, capture_output=True)
            raw = list(struct.unpack_from('>187I', previous.sections(elf)['.text'][1]))
            retail = list(self.retail)
            for n, word in enumerate(retail):
                if word >> 26 == 3:
                    target = ((screen.ENTRY + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
                    name = next(name for name, va in screen.SYMBOLS.items() if va == target)
                    retail[n] = 0x0C000000 | ((symbols[name] >> 2) & 0x3FFFFFF)
            for length, frame, plan in itertools.product((0, 7, 255), (2.25, 7.5), (0, 2, 3)):
                memory, args = previous.fixture(length=length, frame=frame, flag=1)
                self.compare(memory, args, forms=(retail, raw), entry=entry, symbols=symbols, plan=plan)
                cases += 1
        self.receipt('rebases', links=3, cases=cases, executions=cases * 2, all_five_JAL_sites=True)

    def test_07_copied_owner_and_submit_contract_requalification(self):
        objects, padded, diagnostics = [], [], []
        before = (self.out / 'before-source').read_text()
        for name, source in (('owner-before', before), ('owner-after', shape.install(before))):
            obj, detail = previous.compile_owner(self.root, self.out, source, name)
            objects.append(obj)
            diagnostics.append(detail)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.out / (name + '.c')).relative_to(self.root / 'conker')),
                '--post-process', str(obj.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -march=vr4300', '--asm-prelude',
                'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            asm = self.out / (name + '-padded.s')
            subprocess.run(['python3', str(self.root / 'tools/pad_c_object.py'), str(obj),
                str(self.root / 'conker/retail_layout.us.txt'), 'generated_58F80', str(asm),
                '--word-patches', str(self.out / 'qualified-guards.csv')], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o',
                str(asm.with_suffix('.o')), str(asm)], check=True, capture_output=True)
            padded.append(previous.parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics, [[], []])
        self.assertEqual(previous.normalized_pools(objects[0]), previous.normalized_pools(objects[1]))
        a, b = padded
        start = a[1][screen.FUNCTION]['value']
        end = start + 191 * 4
        self.assertEqual(a[0][:start] + a[0][end:], b[0][:start] + b[0][end:])
        for name in a[1]:
            if name != screen.FUNCTION:
                self.assertEqual(a[1][name], b[1][name])
        self.assertEqual({o: v for o, v in a[2].items() if not start <= o < end},
            {o: v for o, v in b[2].items() if not start <= o < end})
        self.assertEqual((self.root / self.paths['caller']).read_bytes(), (self.out / 'before-caller').read_bytes())
        previous.submit.GameNodeTransformSubmitMatchTests.setUpClass()
        self.assertEqual(previous.submit.GameNodeTransformSubmitMatchTests.fitted,
            previous.submit.GameNodeTransformSubmitMatchTests.original)
        self.receipt('owner', untouched_neighbors=len(a[1]) - 1,
            bytes_extents_relocations_pools_exact=True, diagnostics=0, submit_source_unchanged=True,
            current_66_word_submit_stays_exact=True, guard_manifest_unchanged=True)

    def test_08_whole_ELF_only_preparation_slot_and_size_change(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.BASE in source:
            self.receipt('linked', installed=False)
            return
        self.assertEqual(source, shape.install((self.out / 'before-source').read_text()))
        actual = (self.root / self.paths['elf']).read_bytes()
        expected = bytearray(self.before)
        offset = previous.elf_slot_offset(self.before, screen.ENTRY, 764)
        struct.pack_into('>191I', expected, offset, *(self.raw + [0] * (191 - len(self.raw))))
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
                self.assertEqual((a[2], b[2]), (752, 748))
                struct.pack_into('>I', expected, position + 8, b[2])
                changed += 1
        self.assertEqual(changed, 1)
        self.assertEqual(bytes(expected), actual)
        linked = struct.unpack_from('>191I', actual, offset)
        self.assertEqual(sum(a != b for a, b in zip(linked, self.retail)), 102)
        for name in self.paths:
            if name not in ('source', 'elf'):
                self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        audit = previous.audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'])
        self.receipt('linked', installed=True, ELF_bytes=len(actual),
            ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            all_other_ELF_bytes_exact=True, data_audit=audit, conversion_rows_unchanged=True,
            linked_word_differences=102, matching_credit_added=0, new_function_guards=0,
            caller_source_and_guards_unchanged=True)


if __name__ == '__main__':
    unittest.main()
