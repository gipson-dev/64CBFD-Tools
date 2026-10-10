"""Complete raw-C and guarded initializer qualification before/after installation."""
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

from tools.experiments import game_owner_points_initializer_candidates as base
from tools.experiments import game_owner_points_initializer_matching as matching
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_points_initializer_recovery as recovery
from tools.tests import test_game_owner_points_initializer_induction as prior


def target_symbol_size_offset(data):
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
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == base.FUNCTION:
                assert symbol[1] == base.ENTRY and symbol[3] & 15 == 2
                matches.append(offset + 8)
    assert len(matches) == 1
    return matches[0]


class GameOwnerPointsInitializerMatchTests(prior.GameOwnerPointsInitializerInductionTests):
    @classmethod
    def setUpClass(cls):
        for name, value in (('RECOVERED', matching.SELECTED), ('TYPES', matching.TYPES)):
            handle = patch.object(base, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-initializer-match-test'
        cls.meta, cls.words = matching.compile_candidate(cls.root, cls.out, 'recovered')
        _, cls.raw_words = matching.control.source.compile_candidate(cls.root, cls.out, 'raw-source')
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
        old = cls.root / 'conker/build/game-owner-points-initializer-induction-test/baseline.json'
        if old.exists():
            assert cls.baseline == json.loads(old.read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.rows = matching.guard_rows(cls.out / 'recovered.o')
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.header, cls.old_rows = reader.fieldnames, list(reader)
        assert not any(r['function'] == base.FUNCTION for r in cls.old_rows)
        cls.guards = cls.out / 'qualified-guards.csv'
        with cls.guards.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.header, lineterminator='\n')
            writer.writeheader()
            writer.writerows(cls.old_rows + cls.rows)

    def compare(self, memory, actor=recovery.ACTOR, phase=0, symbols=None, entry=base.ENTRY, bodies=None):
        return recovery.GameOwnerPointsInitializerRecoveryTests.compare(self, memory, actor, phase,
            symbols, entry, bodies or (self.retail, self.raw_words, self.words))

    def receipt(self, name, result):
        if name in ('mutations', 'private', 'public-reads'):
            result['executions'] = result['cases'] * 3
        recovery.GameOwnerPointsInitializerRecoveryTests.receipt(self, name, result)

    def test_01_full_shape_forms_profiles_and_slot_rejection(self):
        self.assertEqual((self.meta['raw_body_words'], self.meta['body_words'], self.meta['frame'],
            self.meta['differences'], self.meta['pool_bytes']), (158, 157, 96, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.words, self.retail)
        self.assertEqual(matching.normalize(self.raw_words), self.words)
        certificate = matching.certify(self.raw_words)
        self.assertEqual(certificate['complete_symbolic_actor_views'], 61)
        self.assertEqual(sum(r['omit'] == 'true' for r in self.rows), 1)
        self.assertEqual(sum(bool(r['insert_after']) for r in self.rows), 0)
        self.assertEqual(len({r['offset'] for r in self.rows}), len(self.rows))
        self.receipt('shape', dict(meta=self.meta, certificate=certificate, guard_rows=len(self.rows),
            all_157_retail_words_equal=True, no_padding_or_inserted_words=True,
            semantic_raw_C_retained=True, frame_and_private_homes_unchanged=True))

    def test_02_flags_geometry_all_words_and_saved_registers(self):
        coverage = [set(), set(), set()]
        for flags, pattern, phase in itertools.product(range(256), range(4), (0, 8)):
            for index, model in enumerate(self.compare(recovery.fixture(pattern, flags), phase=phase)):
                coverage[index].update(model.visits)
        for reached, length in zip(coverage, (157, 158, 157)):
            self.assertEqual(reached, set(range(base.ENTRY, base.ENTRY + length * 4, 4)))
        self.receipt('guest', dict(cases=2048, executions=6144, all_flag_bytes=True,
            original_raw_normalized_all_words_reached=[157, 158, 157], saved_GPR_and_FP_restored=True,
            no_hardware_FCSR_claim=True))

    def test_05_actual_registered_update_dispatch_and_return(self):
        update = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345B8)[0], base.ENTRY)
        for pattern, flags, phase in itertools.product(range(4), (0, 2, 0x80, 0x83), (0, 8)):
            memory = recovery.fixture(pattern, flags)
            memory[recovery.ACTOR + 0x2C] = memory[recovery.ACTOR + 0x2D] = 255
            memory[recovery.ACTOR + 0x34] = 0
            recovery.put(memory, recovery.ACTOR + 0x12, 300, 2)
            recovery.put(memory, 0x800BE9E4, 1)
            recovery.put(memory, 0x8008FAF8, base.ENTRY)
            expected = recovery.reference(memory)
            if flags & 1:
                recovery.put(expected, recovery.ACTOR + 0x12, 299, 2)
            for words in (self.retail, self.raw_words, self.words):
                connected = dict(zip(range(base.ENTRY, base.ENTRY + len(words) * 4, 4), words))
                model = recovery.PointOracle(update, memory, phase=phase, entry=recovery.UPDATE, connected=connected).run()
                self.assertEqual(recovery.public(model.memory), recovery.public(expected))
                self.assertEqual(model.calls, [(base.ENTRY, recovery.ACTOR)])
        self.receipt('dispatch', dict(cases=32, executions=96, actual_complete_update_words=81,
            actual_registered_one_argument_ABI=True, original_raw_normalized=True))

    def original_fragment(self):
        owner = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + base.FUNCTION, 'endlabel ' + base.FUNCTION
        return begin + owner.split(begin, 1)[1].split(end, 1)[0] + end + '\n'

    def normalized_object(self):
        retail = self.out / 'retail-target.s'
        retail.write_text(self.original_fragment())
        padded = self.out / 'normalized-target.s'
        guards = self.out / 'target-guards.csv'
        with guards.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.header, lineterminator='\n')
            writer.writeheader()
            writer.writerows(self.rows)
        padded.write_text(emit_padded_assembly(self.out / 'recovered.o', retail,
            word_patches_path=guards, filename='generated_1E0560'))
        obj = self.out / 'normalized-target.o'
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(padded)],
            check=True, capture_output=True)
        return obj

    def test_06_original_relocations_and_independent_rebases(self):
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + self.original_fragment())
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
            cwd=self.root, check=True, capture_output=True)
        normalized = self.normalized_object()
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'recovered.o'))
        self.assertEqual(uses(obj), uses(normalized))
        for index, entry in enumerate((base.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = base.SYMBOLS if index == 0 else {name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(base.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, path, length in (('original', obj, 157), ('raw', self.out / 'recovered.o', 158),
                    ('normalized', normalized, 157)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', base.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[2])
            self.assertEqual(matching.normalize(bodies[1]), bodies[2])
            if index == 0:
                self.assertEqual(bodies, [self.retail, self.raw_words, self.words])
            for pattern, phase in itertools.product(range(4), (0, 8)):
                self.compare(recovery.fixture(pattern, symbols=symbols), symbols=symbols,
                    phase=phase, entry=entry, bodies=bodies)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=12, cases=32, executions=96,
            relocation_uses=sum(uses(obj).values()), all_157_linked_original_normalized_words_equal=True,
            original_raw_normalized_semantics=True, actual_padder_guard_recipe=True))

    def test_07_actual_owner_neighbors_and_padder_overflow_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', matching.TYPES.split('\n', 1)[1] +
            base.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(base.ORIGINAL, matching.SELECTED)
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
        self.assertEqual(matching.guard_rows(objects[1]), self.rows)
        padded_objects = []
        for label, obj, guards in (('before', objects[0], self.out / 'before-guards'),
                ('after', objects[1], self.guards)):
            assembly = emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=guards, filename='generated_1E0560')
            path = self.out / ('padded-' + label + '.s')
            path.write_text(assembly)
            output = path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(output), str(path)],
                check=True, capture_output=True)
            padded_objects.append(output)
        a, af, _ = parse_object(padded_objects[0])
        b, bf, _ = parse_object(padded_objects[1])
        target = bf[base.FUNCTION]
        self.assertEqual(target['size'], 628)
        start = target['value']
        self.assertEqual(a[:start], b[:start])
        self.assertEqual(a[start + 628:], b[start + 628:])
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_preserved=True,
            zero_diagnostics=True, actual_owner_guard_rows_equal_isolated=True,
            actual_padder_emits_628_bytes=True, all_other_padded_bytes_equal=True))

    def test_08_production_baseline_data_and_registration_unchanged(self):
        if base.ORIGINAL in (self.root / base.SOURCE).read_text():
            recovery.GameOwnerPointsInitializerRecoveryTests.test_08_production_baseline_data_and_registration_unchanged(self)
            return
        self.assertIn(matching.SELECTED, (self.root / base.SOURCE).read_text())
        with (self.root / self.paths['guards']).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows, self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith(
            (self.out / 'before-guards').read_bytes()))
        self.assertEqual((self.root / self.paths['progress']).read_bytes(),
            (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>157I', expected, elf_slot_offset(before, base.ENTRY, 628), *self.retail)
        struct.pack_into('>I', expected, target_symbol_size_offset(before), 628)
        actual = (self.root / self.paths['elf']).read_bytes()
        expected_metadata, actual_metadata = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(expected_metadata[:4], actual_metadata[:4])
        # Linker symbol/string ordering may change; compare decoded tables first.
        for section in expected_metadata[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        after_elf = sections(self.root / self.paths['elf'])
        start, data = after_elf['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008FAF8 - start)[0], base.ENTRY)
        self.receipt('installation', dict(installed=True, old_guard_history_unchanged=True,
            entire_ELF_only_target_slot_and_symbol_size_semantically_change=True,
            symbol_string_tables_compared_structurally_all_other_bytes_exact=True,
            protected_data=audit, conversion_rows_byte_identical=True,
            complete_body_and_recipe_present=True))

    def test_13_effective_certificate_and_source_negatives(self):
        mutations = ((0x6C, 0x24050003), (0x4C, 0x24030009), (0x120, 0x24A50008),
            (0x238, 0x00C3082A), (0x254, 0x1420FFB2), (0x258, 0xE7A40048),
            (0xB0, 0x24860034), (0x23C, 0x0020C025))
        for offset, word in mutations:
            changed = self.raw_words.copy()
            self.assertNotEqual(changed[offset // 4], word)
            changed[offset // 4] = word
            with self.assertRaises(ValueError):
                matching.normalize(changed)
        self.receipt('proof-negatives', dict(effective_mutations=len(mutations),
            induction_dead_AT_delay_and_pointer_folds_fail_closed=True))

    def test_14_actual_stale_word_and_relocation_guard_rejection(self):
        target = self.out / 'retail-target-negative.s'
        target.write_text(self.original_fragment())
        word_row = next(i for i, row in enumerate(self.rows) if row['expected_relocations'] == '-')
        relocation_row = next(i for i, row in enumerate(self.rows) if row['expected_relocations'] != '-')
        for label, index, field, value in (('word', word_row, 'expected',
                '0x%08X' % (int(self.rows[word_row]['expected'], 0) ^ 1)),
                ('relocation', relocation_row, 'expected_relocations', '-')):
            rows = [dict(row) for row in self.rows]
            rows[index][field] = value
            guards = self.out / ('stale-' + label + '.csv')
            with guards.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=self.header, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, 'stale'):
                emit_padded_assembly(self.out / 'recovered.o', target, word_patches_path=guards,
                    filename='generated_1E0560')
        self.receipt('guard-negatives', dict(effective_stale_word_and_relocation_mutations=2,
            actual_padder_fails_closed=True))
