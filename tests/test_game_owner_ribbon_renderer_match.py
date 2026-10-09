"""Complete renderer guarded matching, scheduling proof and whole-ELF audit."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_ribbon_renderer_candidates as screen
from tools.experiments import game_owner_ribbon_renderer_registers as registers
from tools.experiments import game_owner_ribbon_renderer_scheduling as matching
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_ribbon_renderer_registers as register_tests
from tools.tests import test_game_owner_ribbon_renderer_recovery as recovery


def elf_symbol_size_offset(data, name):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    matches = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == name:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                matches.append(offset + 8)
    assert len(matches) == 1
    return matches[0]


def guard_text(rows):
    stream = io.StringIO()
    csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n').writerows(rows)
    return stream.getvalue()


class GameOwnerRibbonRendererMatchTests(register_tests.GameOwnerRibbonRendererRegistersTests):
    @classmethod
    def setUpClass(cls):
        original_compile = screen.compile_candidate

        def compile_selected(root, out, name, body=None, profile='o2g3'):
            return original_compile(root, out, name, matching.SELECTED if body is None else body, profile)

        for name, value in (('SELECTED', matching.SELECTED), ('compile_candidate', compile_selected)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-ribbon-renderer-match-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.normalized = matching.normalize(cls.words)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>475I', cls.rom, screen.ROM))
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        cls.installed = matching.SELECTED in (cls.root / screen.SOURCE).read_text()
        if not cls.installed and not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        manifest = (cls.root / cls.paths['guards']).read_bytes()
        cls.guards = cls.out / 'guards.csv'
        cls.guards.write_bytes(manifest if cls.installed else manifest + guard_text(cls.rows).encode())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def compare(self, *args, **kwargs):
        if getattr(self, 'rebasing', False):
            bodies = kwargs['bodies']
            kwargs['bodies'] = (*bodies, matching.normalize(bodies[-1]))
            return recovery.GameOwnerRibbonRendererRecoveryTests.compare(self, *args, **kwargs)
        return super().compare(*args, **kwargs)

    def test_01_complete_profiles_and_reject_installation(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
                         (475, 328, 161, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.normalized, self.retail)
        self.assertEqual(len(self.rows), 161)
        self.assertEqual(sum(map(len, self.meta['relocations'].values())), 17)
        self.assertTrue(all(r['expected_relocations'] == r['replacement_relocations'] for r in self.rows))
        profiles, forms = [], []
        for profile in screen.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            if profile == 'o2g3':
                self.assertEqual(matching.normalize(words), self.retail)
                matching.certify(words)
            else:
                with self.assertRaises(ValueError):
                    matching.certify(words)
            profiles.append(meta)
        for name, body in matching.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            failures = []
            for pattern, success, material, alias in itertools.product(range(4), (False, True),
                    (False, True), (False, True)):
                memory, vertex = recovery.fixture(pattern=pattern, alias=alias)
                try:
                    self.compare(memory, success=success, material=material, vertex=vertex, bodies=(words,))
                except AssertionError as error:
                    failures.append(str(error).splitlines()[0])
            forms.append(dict(meta, contract_cases=32, contract_failures=failures))
        self.receipt('shape', dict(meta=self.meta, profiles=profiles, forms=forms,
            normalized_exact=True, guarded_words=161, no_literal_retail_lookup=True))

    def test_05_actual_owner_neighbors_and_padder_rejection(self):
        before = (self.out / 'before-source').read_text()
        self.assertEqual(before.count(screen.ORIGINAL), 1)
        after = before.replace('/* Non-matching placeholders', screen.TYPES + screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, matching.SELECTED)
        objects, warnings = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings, [[], []])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, f in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rs, ff: {o - ff['value']: r for o, r in rs.items()
                if ff['value'] <= o < ff['value'] + ff['size']}
            self.assertEqual(relative(nrels, f), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        target = nf[screen.FUNCTION]
        self.assertEqual(target['size'], 1900)
        owner_words = list(struct.unpack_from('>475I', new, target['value']))
        isolated, fs, _ = parse_object(self.out / 'selected.o')
        self.assertEqual(owner_words, list(struct.unpack_from('>475I', isolated, fs[screen.FUNCTION]['value'])))
        matching.certify(owner_words)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.guards, filename='generated_1E0560')
        emitted = assembly.split(screen.FUNCTION + ':\n', 1)[1].split('.size ' + screen.FUNCTION, 1)[0]
        emitted_words = [int(line.split()[1], 16) for line in emitted.splitlines() if line.startswith('.word')]
        self.assertEqual(emitted_words, matching.normalize(owner_words))
        self.assertNotIn('.space', emitted)
        (self.out / 'padded.s').write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(self.out / 'padded.o'),
            str(self.out / 'padded.s')], check=True, capture_output=True)
        for field, value in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_HI16:wrong')):
            bad = [dict(r) for r in self.rows]
            bad[0][field] = value
            path = self.out / ('bad-' + field + '.csv')
            path.write_bytes((self.out / 'before-guards').read_bytes() + guard_text(bad).encode())
            with self.assertRaises(ValueError):
                emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                    word_patches_path=path, filename='generated_1E0560')
        self.receipt('owner', dict(neighbors=len(nf) - 1, new_warnings=0, existing_warnings=0,
            pools_relative_relocations_and_isolated_body_preserved=True, guarded_padder_passes=True,
            stale_expected_word_and_relocation_rejected=True, guarded_words=161))

    def test_06_production_unchanged_protected_data_and_registered_pointer(self):
        current = {name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                   for name, path in self.paths.items()}
        elf = sections(self.root / self.paths['elf'])
        start, data = elf['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008BF0C - start)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2309CC)[0], screen.ENTRY)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        if self.installed:
            source = (self.root / screen.SOURCE).read_text()
            self.assertEqual(source.count(matching.SELECTED), 1)
            self.assertNotIn(screen.ORIGINAL, source)
            with (self.root / self.paths['guards']).open(newline='') as stream:
                rows = [r for r in csv.DictReader(stream) if r['function'] == screen.FUNCTION]
            self.assertEqual(rows, self.rows)
            self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith(
                (self.out / 'before-guards').read_bytes()))
            self.assertEqual((self.root / self.paths['progress']).read_bytes(),
                             (self.out / 'before-progress').read_bytes())
            old = (self.out / 'before-elf').read_bytes()
            expected = bytearray(old)
            struct.pack_into('>475I', expected, elf_slot_offset(old, screen.ENTRY, 1900), *self.retail)
            struct.pack_into('>I', expected, elf_symbol_size_offset(old, screen.FUNCTION), 1900)
            self.assertEqual(bytes(expected), (self.root / self.paths['elf']).read_bytes())
            old_symbols = metadata(old)[2]
            new_symbols = metadata(bytes(expected))[2]
            old_target = [s for s in old_symbols if s[0] == screen.FUNCTION.encode()]
            new_target = [s for s in new_symbols if s[0] == screen.FUNCTION.encode()]
            self.assertEqual(len(old_target), 1)
            self.assertEqual(new_target[0][1:3], (screen.ENTRY, 1900))
            old_symbols.pop(old_target[0])
            new_symbols.pop(new_target[0])
            self.assertEqual(old_symbols, new_symbols)
        else:
            self.assertEqual(current, self.baseline)
        self.receipt('installation', dict(installed=self.installed, hashes=current, protected_data=audit,
            registered_pointer='0x8008BF0C', exact_words=475 if self.installed else 0,
            entire_ELF_only_target_slot_and_target_size_change=self.installed,
            all_other_symbol_metadata_old_guard_bytes_and_conversion_rows_preserved=self.installed))

    def test_15_closed_GPR_paths_effective_collision_and_composition(self):
        full = self.normalized
        self.normalized = registers.normalize(self.words)
        try:
            super().test_15_closed_GPR_paths_effective_collision_and_composition()
        finally:
            self.normalized = full

    def test_16_scheduling_windows_effective_dependency_memory_and_FP_controls(self):
        certificate = matching.certify(self.words)
        self.assertEqual(certificate['changed_words'], 161)
        self.assertEqual(len(certificate['scheduling_windows']), 4)
        first = list(matching.PERMUTATIONS[0][1])
        first[1], first[2] = first[2], first[1]
        with patch.object(matching, 'PERMUTATIONS', ((0xCC, tuple(first)), *matching.PERMUTATIONS[1:])):
            with self.assertRaisesRegex(ValueError, 'closed-window state/read/ABI mismatch'):
                matching.certify(self.words)
        for offset, value in ((0xE4, 0xAFB80010), (0xE0, 0xAE2F0010), (0x2B8, 0xC7A60138)):
            bad = list(self.words)
            bad[offset // 4] = value
            with self.assertRaises(ValueError):
                matching.certify(bad)
        edits = dict(matching.GPR_EDITS)
        edits[0x234] = ((11, 5, 23),)
        with patch.object(matching, 'GPR_EDITS', edits):
            with self.assertRaisesRegex(ValueError, 'closed-window state/read/ABI mismatch'):
                matching.certify(self.words)
        self.receipt('scheduling-certificate', dict(certificate, effective_unsafe_controls=5,
            full_normalized_exact=True, closed_private_windows_and_live_call_arguments=True))

    def test_17_read_only_table_pair_fault_prefixes(self):
        for offset in (40, 44):
            memory, vertex = recovery.fixture()
            del memory[screen.SYMBOLS['D_800A4AC8'] + offset]
            reference = recovery.RibbonReference(memory)
            with self.assertRaises(KeyError):
                reference.run()
            for body in (self.retail, self.words, self.normalized):
                model = recovery.RibbonOracle(body, memory)
                with self.assertRaises(KeyError):
                    model.run()
                self.assertEqual(model.calls, reference.calls)
                self.assertEqual(recovery.external(model.memory), recovery.external(reference.memory))
                self.assertEqual(recovery.writes(model), reference.events)
        self.receipt('table-faults', dict(cases=2, executions=6, public_call_write_prefixes_equal=True,
            read_order_itself_changes=True, hardware_exception_or_volatile_read_claim=False))

    def test_18_independent_guarded_object_links_all_symbol_words(self):
        original = self.out / 'original.o'
        if not original.exists():
            self.test_07_independent_original_relocations_and_semantic_rebases()
        data = bytearray((self.out / 'selected.o').read_bytes())
        h = ELF_HEADER.unpack_from(data)
        records = [SECTION_HEADER.unpack_from(data, h[6] + i * h[11]) for i in range(h[12])]
        names = records[h[13]]
        strings = data[names[4]:names[4] + names[5]]
        text = next(s for s in records if strings[s[0]:].split(b'\0', 1)[0] == b'.text')
        _, functions, _ = parse_object(self.out / 'selected.o')
        begin = text[4] + functions[screen.FUNCTION]['value']
        raw = list(struct.unpack_from('>475I', data, begin))
        matching.certify(raw)
        struct.pack_into('>475I', data, begin, *matching.normalize(raw))
        fitted = self.out / 'normalized.o'
        fitted.write_bytes(data)
        self.assertEqual(parse_object(fitted)[2], parse_object(self.out / 'selected.o')[2])
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('normalized-rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, obj in (('original', original), ('normalized', fitted)):
                path = self.out / ('normalized-rebase-%d-%s.elf' % (index, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(path), str(obj)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>475I', sections(path)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
        self.receipt('normalized-rebases', dict(symbol_sets=4, independent_links=8,
            byte_exact_words_per_set=475, relocation_sites_and_uses_unchanged=True))


if __name__ == '__main__':
    unittest.main()
