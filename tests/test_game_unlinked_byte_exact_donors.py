"""Active ABI, unchanged owner neighbors and both real retail padders."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_unlinked_donor_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, parse_retail_slice, emit_padded_assembly
# pad_c_object retains the standalone script's sibling-module import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import unlinked_donor_checkpoint as checkpoint
from tools.match_progress import load_symbol_addrs


class UnlinkedByteExactDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()

    def test_01_complete_owner_neighbors_pools_and_both_production_padders(self):
        records = []
        for owner in sorted({spec['owner'] for spec in source.TARGETS.values()}):
            before = (self.out / ('before-' + owner)).read_text()
            after = source.recover(before, owner)
            old, w0 = build.compile_owner(self.root, self.out, before, owner + '-before')
            new, w1 = build.compile_owner(self.root, self.out, after, owner + '-after')
            text0, functions0, reloc0 = parse_object(old)
            text1, functions1, reloc1 = parse_object(new)
            targets = {name for name, spec in source.TARGETS.items() if spec['owner'] == owner}
            expected_names = set(functions0) - targets if owner == 'generated_10EF60' else set(functions0)
            self.assertEqual(expected_names, set(functions1))
            for name in set(functions0) - targets:
                a, b = functions0[name], functions1[name]
                self.assertEqual(a['size'], b['size'], name)
                self.assertEqual(text0[a['value']:a['value'] + a['size']], text1[b['value']:b['value'] + b['size']], name)
                relative = lambda table, info: {at - info['value']: value for at, value in table.items()
                    if info['value'] <= at < info['value'] + info['size']}
                self.assertEqual(relative(reloc0, a), relative(reloc1, b), name)
            self.assertEqual(normalized_pools(old), normalized_pools(new), owner)
            self.assertLessEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'), owner)
            original = self.root / ('conker/asm/' + owner.removeprefix('generated_') + '.s')
            overrides = None
            if owner == 'generated_10EF60':
                extra, diagnostics = build.compile_owner(self.root, self.out, source.emission_source(), 'wrappers-for-padding')
                self.assertFalse(diagnostics)
                overrides = {name: extra for name in targets}
                self.assertEqual(normalized_pools(extra), {'.rodata': None, '.data': None})
            primary = pad_c_object.emit_padded_assembly(new, self.root / 'conker/retail_layout.us.txt', owner,
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv', function_objects=overrides)
            if overrides:
                combined = self.out / 'combined-10EF60.s'
                combined.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + primary)
                compact = combined.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(compact), str(combined)],
                    capture_output=True, text=True, check=True)
                generated = emit_padded_assembly(compact, original, filename=owner)
            else:
                generated = emit_padded_assembly(new, original, filename=owner,
                    word_patches_path=self.root / 'conker/retail_word_patches.us.csv')
            assemblies = (generated, primary)
            for index, assembly in enumerate(assemblies):
                path = self.out / (owner + '-pad%d.s' % index)
                path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
                obj = path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
                    capture_output=True, text=True, check=True)
                emitted, functions = build.link_owner(self.root, self.out, obj, owner)
                for name in targets:
                    entry, count = int(name[5:], 16), source.TARGETS[name]['words']
                    rom = entry - 0x15000000 + 0x2D4B0
                    info = functions[name]
                    self.assertEqual(emitted[info['value']:info['value'] + count * 4], self.rom[rom:rom + count * 4], name)
            records.append(dict(owner=owner, unchanged_neighbors=len(functions0) - len(targets),
                before_warnings=w0.count('cfe: Warning'), after_warnings=w1.count('cfe: Warning')))
        (self.out / 'owners-and-padders.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_02_effective_compiled_flag_and_color_controls(self):
        for name, old, new in (('func_150B1E20', '0x10000', '0x20000'), ('func_150CCD90', '255.0f', '254.0f')):
            spec = source.TARGETS[name]
            before = (self.out / ('before-' + spec['owner'])).read_text()
            after = source.recover(before, spec['owner'])
            lo, hi = build.function_span(after, name)
            changed = after[lo:hi].replace(old, new)
            self.assertNotEqual(changed, after[lo:hi])
            obj, _ = build.compile_owner(self.root, self.out, after[:lo] + changed + after[hi:], 'negative-' + name)
            emitted, functions = build.link_owner(self.root, self.out, obj, spec['owner'])
            entry, count = int(name[5:], 16), spec['words']
            info = functions[name]
            rom = entry - 0x15000000 + 0x2D4B0
            self.assertNotEqual(emitted[info['value']:info['value'] + min(count * 4, info['size'])],
                self.rom[rom:rom + min(count * 4, info['size'])], name)

    def test_03_installed_sources_slots_and_closed_image(self):
        pins = json.loads((self.out / 'baseline.json').read_text())
        self.assertEqual(pins['elf'], source.BASELINE_ELF)
        self.assertEqual(pins['makefile'], source.BASELINE_MAKEFILE)
        for key, digest in pins.items():
            self.assertEqual(hashlib.sha256((self.out / ('before-' + key)).read_bytes()).hexdigest(), digest, key)
        for owner in {spec['owner'] for spec in source.TARGETS.values()}:
            self.assertEqual((self.root / source.path(owner)).read_text(),
                source.recover((self.out / ('before-' + owner)).read_text(), owner), owner)
        self.assertEqual((self.root / 'conker/src/game/translation_units/10EF60_wrappers.c').read_text(), source.emission_source())
        before = (self.out / 'before-elf').read_bytes()
        after_path = self.root / 'conker/build/conker.us.elf'
        after = after_path.read_bytes()
        expected = bytearray(before)
        expected_symbols = canonical_symbols(before)
        raw_counts = {name: spec['words'] - {'func_150BEEB0': 1, 'func_150C7770': 3, 'func_150CCD90': 1}.get(name, 0)
            for name, spec in source.TARGETS.items()}
        for name, spec in source.TARGETS.items():
            entry, count = int(name[5:], 16), spec['words']
            rom = entry - 0x15000000 + 0x2D4B0
            truth = self.rom[rom:rom + count * 4]
            at = elf_slot_offset(before, entry, count * 4)
            expected[at:at + count * 4] = truth
            self.assertEqual(after[elf_slot_offset(after, entry, count * 4):][:count * 4], truth, name)
            old = next(row for row in expected_symbols if row[0] == name)
            expected_symbols[old] -= 1
            expected_symbols[(name, old[1], raw_counts[name] * 4, *old[3:])] += 1
        self.assertEqual(+expected_symbols, canonical_symbols(after))
        old_sections, new_sections = sections(self.out / 'before-elf'), sections(after_path)
        self.assertEqual(set(old_sections), set(new_sections))
        game = old_sections['.game']
        at = elf_slot_offset(before, game[0], len(game[1]))
        self.assertEqual(new_sections['.game'], (game[0], bytes(expected[at:at + len(game[1])])),
            'Only the nine complete retail slots may change')
        for name in set(old_sections) - {'.game', '.symtab', '.strtab'}:
            self.assertEqual(new_sections[name], old_sections[name], name)
        guards = (self.root / 'conker/retail_word_patches.us.csv').read_bytes()
        self.assertEqual(guards, (self.out / 'before-guards').read_bytes())
        expected_progress = (self.out / 'before-progress').read_bytes()
        for name in ('func_150ED234', 'func_150FFBDC'):
            matching = [line for line in expected_progress.splitlines(keepends=True) if b',' + name.encode() + b',' in line]
            self.assertEqual(len(matching), 1)
            self.assertTrue(matching[0].endswith(b',asm\n'))
            expected_progress = expected_progress.replace(matching[0], matching[0].replace(b',asm\n', b',c\n'))
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), expected_progress)
        data = audit_layout(after_path, self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'image-transition.json').write_text(json.dumps(dict(
            functions=9, retail_words=444, new_C_rows=2, new_guards=0,
            changed_game_bytes=sum(a != b for a, b in zip(game[1], new_sections['.game'][1])),
            ELF_sha256=hashlib.sha256(after).hexdigest(), no_overflow_changes=True,
            all_other_executable_and_data_sections_fixed=True, symbol_definition_changes_closed=True,
            protected_data=data), indent=2) + '\n')

    def test_04_effective_installed_image_and_progress_controls(self):
        read_bytes = Path.read_bytes
        path = self.root / 'conker/build/conker.us.elf'
        for name, spec in source.TARGETS.items():
            changed = bytearray(read_bytes(path))
            changed[elf_slot_offset(changed, int(name[5:], 16), spec['words'] * 4) + 3] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(changed) if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_03_installed_sources_slots_and_closed_image()
        for filename in ('conker/progress.csv', 'conker/retail_word_patches.us.csv'):
            path = self.root / filename
            changed = read_bytes(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p: changed if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_03_installed_sources_slots_and_closed_image()

    def test_05_literal_serialization_and_closed_historical_projection(self):
        self.test_03_installed_sources_slots_and_closed_image()
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            actual = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(actual, path, self.root), checkpoint.fixture(self.root, 'before', key))
            bad = actual[:-1] + bytes([actual[-1] ^ 1])
            self.assertEqual(checkpoint.previous_input(bad, path, self.root), bad)

    def test_06_independent_original_links_and_HI_LO_carries(self):
        anchors = load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt'))
        output = subprocess.run(['mips-linux-gnu-nm', '-n', str(self.root / 'conker/build/conker.us.elf')],
            capture_output=True, text=True, check=True).stdout
        for line in output.splitlines():
            fields = line.split()
            if len(fields) == 3:
                anchors.setdefault(fields[2], int(fields[0], 16))
        comparisons = 0
        for owner in sorted({spec['owner'] for spec in source.TARGETS.values()}):
            original = self.root / ('conker/asm/' + owner.removeprefix('generated_') + '.s')
            obj = self.out / (owner + '-retail.o')
            _, end, labels, _ = parse_retail_slice(original)
            ordered = sorted(labels, key=labels.get)
            typed = self.out / (owner + '-typed-retail.s')
            typed.write_text(original.read_text() + '\n' + '\n'.join(
                '.type %s,@function\n.size %s,0x%X' % (name, name,
                    (labels[ordered[index + 1]] if index + 1 < len(ordered) else end) - labels[name])
                for index, name in enumerate(ordered)) + '\n')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', 'include', '-o', str(obj), str(typed)],
                cwd=self.root / 'conker', capture_output=True, text=True, check=True)
            objects = (obj, *(self.out / (owner + '-pad%d.o' % index) for index in range(2)))
            call_targets = {symbol for artifact in objects for values in parse_object(artifact)[2].values()
                for kind, symbol in values if kind == 'R_MIPS_26'}
            for phase, base in enumerate((0x15004000, 0x16004000)):
                linked = []
                for index, artifact in enumerate(objects):
                    _, functions, relocations = parse_object(artifact)
                    defined = {name for _, name, fields, _ in symbol_rows(artifact.read_bytes()) if fields[5] != 0}
                    referenced = {symbol for values in relocations.values() for _, symbol in values} - defined
                    self.assertFalse({symbol for symbol in referenced if symbol.startswith('.')}, str(artifact))
                    order = {name: offset for offset, name in enumerate(sorted(anchors))}
                    symbols = {symbol: (0x17008000 + order[symbol] * 4 if symbol in call_targets else
                        0x90007FFC + (order[symbol] % 4) * 4 + (order[symbol] // 4) * 0x10000)
                        for symbol in referenced} if phase else {
                            symbol: anchors[symbol] for symbol in referenced}
                    script = self.out / (owner + '-rebase%d-%d.ld' % (phase, index))
                    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                    elf = script.with_suffix('.elf')
                    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                        '-e', min(functions, key=lambda name: functions[name]['value']),
                        *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(artifact)],
                        capture_output=True, text=True, check=True)
                    linked.append((sections(elf)['.text'][1], functions))
                for name, spec in source.TARGETS.items():
                    if spec['owner'] != owner:
                        continue
                    spans = [data[functions[name]['value']:functions[name]['value'] + spec['words'] * 4]
                        for data, functions in linked]
                    self.assertEqual(spans[0], spans[1], name)
                    self.assertEqual(spans[0], spans[2], name)
                    comparisons += 2
        self.assertEqual(comparisons, 36)
        (self.out / 'independent-rebases.json').write_text(json.dumps(dict(
            comparisons=comparisons, target_functions=9, padders=2, link_profiles=2,
            independently_assembled_original_owners=True, external_HI_LO_carry_addresses=True), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
