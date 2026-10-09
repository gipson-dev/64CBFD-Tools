"""Endpoint quad complete recovery, GPR proof, actual owner guards and installation."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_endpoint_quad_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_state_match import metadata
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_owner_endpoint_quad_recovery as recovery


def guard_text(rows):
    stream = io.StringIO()
    csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n').writerows(rows)
    return stream.getvalue()


def normalized_object(source, destination):
    data = bytearray(source.read_bytes())
    header = ELF_HEADER.unpack_from(data)
    records = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    names = records[header[13]]
    strings = data[names[4]:names[4] + names[5]]
    text = next(s for s in records if strings[s[0]:].split(b'\0', 1)[0] == b'.text')
    _, functions, _ = parse_object(source)
    begin = text[4] + functions[screen.FUNCTION]['value']
    words = list(struct.unpack_from('>340I', data, begin))
    screen.certify(words)
    struct.pack_into('>340I', data, begin, *screen.normalize(words))
    destination.write_bytes(data)


class GameOwnerEndpointQuadMatchTests(recovery.GameOwnerEndpointQuadRecoveryTests):
    @classmethod
    def setUpClass(cls):
        scope = patch.object(recovery, 'screen', screen)
        scope.start()
        cls.addClassCleanup(scope.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-endpoint-quad-match-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.fitted = screen.normalize(cls.words)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>340I', cls.rom, screen.ROM))
        cls.rows = screen.guard_rows(cls.out / 'selected.o')
        cls.installed = screen.SELECTED in (cls.root / screen.SOURCE).read_text()
        paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        if not cls.installed and not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        manifest = (cls.root / paths['guards']).read_bytes()
        cls.guards = cls.out / 'guards.csv'
        cls.guards.write_bytes(manifest if cls.installed else manifest + guard_text(cls.rows).encode())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, data):
        if name == 'guest':
            data = dict(data, executions=data['cases'] * 3,
                complete_private_memory_and_write_trace_equal=True, normalized_body_included=True)
        super().receipt(name, data)

    def compare(self, memory, view=0, success=True, mode=0, phase=0, vertex=recovery.VERTICES,
            bodies=None, symbols=None, entry=screen.ENTRY):
        default = bodies is None
        ref, models = super().compare(memory, view, success, mode, phase, vertex,
            bodies or (self.retail, self.words, self.fitted), symbols, entry)
        if default:
            for model in models[1:]:
                self.assertEqual(model.memory, models[0].memory)
                self.assertEqual(model.events, models[0].events)
                self.assertEqual(model.arguments_by_call, models[0].arguments_by_call)
        return ref, models

    def test_01_complete_profiles_and_reject_installation(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (340, 184, 84, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.fitted, self.retail)
        proof = screen.certify(self.words)
        self.assertEqual((proof['instruction_words_reached'], proof['paths']), (339, 27))
        self.assertEqual(len(self.rows), 84)
        self.assertTrue(all(r['expected_relocations'] == r['replacement_relocations'] == '-' for r in self.rows))
        self.assertEqual(sum(map(len, self.meta['relocations'].values())), 17)
        rows = []
        for profile in screen.recovery.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.assertEqual(meta['diagnostics'], '')
            if profile == 'o2g3':
                self.assertEqual(screen.normalize(words), self.retail)
            else:
                with self.assertRaises(ValueError):
                    screen.certify(words)
            rows.append(meta)
        bad = self.words.copy()
        bad[0x33C // 4] = (bad[0x33C // 4] & ~(31 << 16)) | (24 << 16)
        with self.assertRaisesRegex(ValueError, 'operand provenance'):
            screen.certify(bad)
        bad = self.words.copy()
        bad[0x534 // 4] = (bad[0x534 // 4] & ~(31 << 16)) | (9 << 16)
        with self.assertRaisesRegex(ValueError, 'operand provenance'):
            screen.certify(bad)
        self.receipt('shape', dict(meta=self.meta, profiles=rows, certificate=proof,
            normalized_exact=True, guarded_words=84, literal_retail_lookup=False))

    def test_04_actual_owner_neighbors_and_scratch_padder(self):
        before = (self.out / 'before-source').read_text()
        self.assertEqual(before.count(screen.ORIGINAL), 1)
        after = before.replace('/* Non-matching placeholders', screen.TYPES + screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
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
        self.assertEqual(warnings[0], warnings[1])
        self.assertEqual(len(warnings[0]), 4)
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            self.assertEqual({o - function['value']: r for o, r in nrels.items()
                if function['value'] <= o < function['value'] + function['size']},
                {o - prior['value']: r for o, r in orels.items()
                if prior['value'] <= o < prior['value'] + prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        function = nf[screen.FUNCTION]
        owner_words = list(struct.unpack_from('>340I', new, function['value']))
        isolated, functions, _ = parse_object(self.out / 'selected.o')
        self.assertEqual(owner_words, list(struct.unpack_from('>340I', isolated, functions[screen.FUNCTION]['value'])))
        screen.certify(owner_words)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1DF510.s',
            word_patches_path=self.guards, filename='generated_1DF510')
        source = self.out / 'padded.s'
        source.write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(self.out / 'padded.o'),
            str(source)], check=True, capture_output=True)
        # A stale expected word must fail in the actual production padder.
        rejected = [dict(row) for row in self.rows]
        rejected[0]['expected'] = '0x00000000'
        bad = self.out / 'bad-guards.csv'
        bad.write_bytes((self.out / 'before-guards').read_bytes() + guard_text(rejected).encode())
        with self.assertRaisesRegex(ValueError, 'expected'):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/1DF510.s',
                word_patches_path=bad, filename='generated_1DF510')
        self.receipt('owner', dict(neighbors=17, existing_warnings=4, new_warnings=0,
            pools_and_relative_relocations_preserved=True, actual_guarded_padder_passes=True,
            owner_target_equals_isolated=True, stale_expected_word_rejected=True))

    def test_05_production_unchanged_protected_data_and_registered_pointer(self):
        paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        current = {name: hashlib.sha256((self.root / path).read_bytes()).hexdigest() for name, path in paths.items()}
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22F130)[0], screen.ENTRY)
        elf = sections(self.root / paths['elf'])
        address, data = elf['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A670 - address)[0], screen.ENTRY)
        audit = audit_layout(self.root / paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        if self.installed:
            self.assertNotIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
            self.assertEqual((self.root / screen.SOURCE).read_text().count(screen.SELECTED), 1)
            with (self.root / paths['guards']).open(newline='') as stream:
                actual = [r for r in csv.DictReader(stream) if r['function'] == screen.FUNCTION]
            self.assertEqual(actual, self.rows)
            self.assertTrue((self.root / paths['guards']).read_bytes().startswith(
                (self.out / 'before-guards').read_bytes()))
            self.assertEqual((self.root / paths['progress']).read_bytes(),
                (self.out / 'before-progress').read_bytes())
            old_symbols = metadata((self.out / 'before-elf').read_bytes())[2]
            new_symbols = metadata((self.root / paths['elf']).read_bytes())[2]
            target = screen.FUNCTION.encode()
            old_target = [s for s in old_symbols if s[0] == target]
            new_target = [s for s in new_symbols if s[0] == target]
            self.assertEqual(len(old_target), 1)
            self.assertEqual(len(new_target), 1)
            self.assertEqual(old_target[0][1], screen.ENTRY)
            self.assertEqual(new_target[0][1:3], (screen.ENTRY, 1360))
            self.assertEqual(old_target[0][3:], new_target[0][3:])
            old_symbols.pop(old_target[0])
            new_symbols.pop(new_target[0])
            self.assertEqual(old_symbols, new_symbols)
            prior = sections(self.out / 'before-elf')
            for name in ('.header', '.boot', '.game_data', '.init', '.init_data', '.debugger', '.game_overflow'):
                self.assertEqual(elf[name], prior[name], name)
            start, game = elf['.game']
            old_start, old_game = prior['.game']
            self.assertEqual(start, old_start)
            begin, end = screen.ENTRY - start, screen.ENTRY - start + 1360
            self.assertEqual(game[:begin], old_game[:begin])
            self.assertEqual(game[end:], old_game[end:])
            self.assertEqual(list(struct.unpack_from('>340I', game, begin)), self.retail)
            expected = bytearray((self.out / 'before-elf').read_bytes())
            header = ELF_HEADER.unpack_from(expected)
            records = [SECTION_HEADER.unpack_from(expected, header[6] + i * header[11])
                for i in range(header[12])]
            game_section = next(s for s in records if s[3] == start and s[1] == 1)
            struct.pack_into('>340I', expected, game_section[4] + begin, *self.retail)
            table = next(s for s in records if s[1] == 2)
            strings = records[table[6]]
            names = expected[strings[4]:strings[4] + strings[5]]
            size_offsets = []
            for offset in range(table[4], table[4] + table[5], table[9]):
                symbol = SYMBOL.unpack_from(expected, offset)
                if names[symbol[0]:].split(b'\0', 1)[0] == target:
                    size_offsets.append(offset + 8)
            self.assertEqual(len(size_offsets), 1)
            struct.pack_into('>I', expected, size_offsets[0], 1360)
            self.assertEqual(bytes(expected), (self.root / paths['elf']).read_bytes())
        else:
            self.assertEqual(current, self.baseline)
            self.assertIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
        self.receipt('installation', dict(installed=self.installed, hashes=current, protected_data=audit,
            registered_pointer='0x8008A670', exact_words=340 if self.installed else 0,
            other_Game_words_and_Init_and_Debugger_unchanged=self.installed,
            all_other_symbol_metadata_unchanged=self.installed,
            entire_ELF_only_target_slot_and_target_size_change=self.installed,
            old_guard_bytes_and_all_conversion_rows_preserved=self.installed))

    def test_10_normalized_object_independent_links_and_all_symbol_words(self):
        original = self.out / 'original.o'
        if not original.exists():
            self.test_07_independent_original_candidate_symbol_rebases()
        fitted = self.out / 'normalized.o'
        normalized_object(self.out / 'selected.o', fitted)
        raw_uses = parse_object(self.out / 'selected.o')[2]
        self.assertEqual(parse_object(fitted)[2], raw_uses)
        count = 0
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('normalized-rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, object_path in (('original', original), ('normalized', fitted)):
                elf = self.out / ('normalized-rebase-%d-%s.elf' % (index, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(object_path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>340I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            count += 1
        self.receipt('normalized-rebases', dict(symbol_sets=count, independent_links=count * 2,
            byte_exact_words_per_set=340, relocation_sites_and_uses_unchanged=True))
