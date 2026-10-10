"""Complete tile scheduling qualification; production and special-helper gate stay unchanged."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_tile_updater_matching as matching
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, emit_padded_assembly, parse_object
from tools.tests import test_game_actor_tile_updater_recovery as proof
from tools.tests.game_owner_pool import normalized_pools


class GameActorTileUpdaterMatchTests(unittest.TestCase):
    assemble = classmethod(proof.GameActorTileUpdaterRecoveryTests.assemble.__func__)
    run_native = proof.GameActorTileUpdaterRecoveryTests.run_native
    receipt = proof.GameActorTileUpdaterRecoveryTests.receipt

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-tile-updater-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.snapshot = cls.root / 'conker/build/game-actor-tile-updater-test'
        cls.paths = dict(source=matching.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        cls.baseline = json.loads((cls.snapshot / 'baseline.json').read_text())
        assert set(cls.baseline) == set(cls.paths)
        cls.meta, cls.raw = matching.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>123I', cls.rom, matching.ROM))
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + matching.FUNCTION, 1)[1].split('endlabel ' + matching.FUNCTION, 1)[0]
        cls.slot_asm = cls.out / 'slot.s'
        cls.slot_asm.write_text('glabel ' + matching.FUNCTION + assembly +
            'endlabel ' + matching.FUNCTION + '\n')
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
        cls.write_rows(cls.out / 'isolated.csv', cls.rows)
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+matching.FUNCTION+
            '\n.type '+matching.FUNCTION+',@function\n'+matching.FUNCTION+':\n'+assembly+
            '\n.size '+matching.FUNCTION+',.-'+matching.FUNCTION+'\n')
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot_asm,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80'))
        cls.fitted = cls.link('fitted', matching.ENTRY, matching.recovery.SYMBOLS)
        cls.forms = (cls.retail, cls.raw, cls.fitted)

    @staticmethod
    def write_rows(path, rows):
        with path.open('w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    @classmethod
    def link(cls, name, entry, symbols):
        script = cls.out / ('link-%s-%X-%X.ld' % (name, entry, symbols['D_800CC2D0']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
            '-e', matching.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
            '-o', str(elf), str(cls.out / (name + '.o'))], check=True, capture_output=True)
        size = parse_object(cls.out / (name + '.o'))[1][matching.FUNCTION]['size']
        return list(struct.unpack_from('>%dI' % (size // 4), sections(elf)['.text'][1]))

    def compare(self, memory, slot=0, commands=proof.OUTPUT, phase=0, delta=16, actions=()):
        expected, state, events, calls = proof.reference(memory, commands, slot, delta, actions)
        models = [proof.TileOracle(words, memory, slot, commands, phase, delta, actions).run()
            for words in self.forms]
        for model in models:
            self.assertEqual(model.r[2], expected)
            self.assertEqual({a:v for a,v in model.memory.items() if proof.public(a)},
                {a:v for a,v in state.items() if proof.public(a)})
            self.assertEqual([e for e in model.events if e[0]=='CALL' or proof.public(e[1])],
                [e for e in events if e[0]=='CALL' or proof.public(e[1])])
            self.assertEqual(bytes(model.memory[commands+i] for i in range(16)),
                bytes(state[commands+i] for i in range(16)))
            self.assertEqual(model.calls, calls)
        for model in models[1:]:
            for name in ('memory', 'events', 'calls', 'accesses'):
                self.assertEqual(getattr(models[0], name), getattr(model, name), name)
        return models

    def test_01_complete_three_forms_all_words_and_producer_dependencies(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['pool_bytes'],
            self.meta['differences'], self.meta['diagnostics']), (120, 32, 0, 120, ''))
        self.assertEqual(self.fitted, self.retail)
        coverage = [set(), set(), set()]
        for kind, present, phase in itertools.product(range(256), (False, True), (0, 8)):
            for index, model in enumerate(self.compare(proof.fixture(kind, present), phase=phase)):
                coverage[index].update(model.visits)
        self.assertEqual(coverage, [set(range(matching.ENTRY, matching.ENTRY+size*4, 4))
            for size in (123, 120, 123)])
        certificate = matching.certify(matching.RAW)
        self.assertEqual(certificate['omitted_producers'], 0)
        self.assertEqual(parse_object(self.out/'fitted.o')[2],
            parse_object(self.out/'original.o')[2])
        self.receipt('guest', cases=1024, executions=3072, all_words=[123,120,123],
            full_private_public_memory_order_calls=True, independent_public_reference=True,
            fitted_all_123_words_exact=True, producer_certificate=certificate)

    def test_02_boundary_and_callback_corpus_three_forms(self):
        proof.GameActorTileUpdaterRecoveryTests.test_02_signed_wrapped_slots_coordinate_dimensions_and_callback_results(self)
        self.receipt('boundary-three-forms', cases=548, executions=1644,
            wrapped_slots_coordinates_dimensions_and_bounded_callback_mutations=True)

    def test_03_alias_and_every_fired_fault_prefix_three_forms(self):
        # Reuse the same published corpus, once for each complete source/scheduled pair.
        raw = self.raw
        for name, words in (('raw', raw), ('fitted', self.fitted)):
            self.raw = words
            proof.GameActorTileUpdaterRecoveryTests.test_03_live_output_aliases_and_private_fired_fault_prefixes(self)
            receipt = json.loads((self.out/'aliases.json').read_text())
            self.assertEqual(receipt['full_fired_fault_prefix_pairs'], 518)
            self.receipt('aliases-'+name, **receipt)
        self.raw = raw
        self.receipt('alias-three-forms', cases=85, positive_executions=255,
            fault_prefix_cases=518, pair_comparison_failed_executions=2072,
            every_fault_fired=True, full_private_public_prefix_bytes_events_calls_exact=True,
            no_saved_PC_or_stack_normalization=True)

    def test_04_actual_copied_owner_padding_and_neighbors(self):
        before = (self.snapshot/'before-source').read_text()
        objects = []
        for name, source in (('owner-before', before), ('owner-after',
                matching.recovery.copied_owner(before, matching.SELECTED))):
            obj, warnings = compile_owner(self.root, self.out, source, name)
            self.assertEqual(warnings, [])
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.out/(name+'.c')).relative_to(self.root/'conker')),
                '--post-process', str(obj.relative_to(self.root/'conker')), '--assembler',
                'mips-linux-gnu-as -EB -march=vr4300', '--asm-prelude',
                'include/asm_processor_prelude.inc'], cwd=self.root/'conker',
                check=True, capture_output=True)
            objects.append(obj)
        parsed = [parse_object(obj) for obj in objects]
        def body(data, name):
            text, functions, relocations = data
            target = functions[name]
            base, size = target['value'], target['size']
            return size, text[base:base+size], {a-base:v for a,v in relocations.items()
                if base<=a<base+size}
        self.assertEqual(parsed[0][1].keys(), parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=matching.FUNCTION:
                self.assertEqual(body(parsed[0], name), body(parsed[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(body(parsed[1], matching.FUNCTION),
            body(parse_object(self.out/'selected.o'), matching.FUNCTION))
        self.assertEqual(matching.guard_rows(objects[1]), self.rows)
        with (self.snapshot/'before-guards').open(newline='') as source:
            existing = list(csv.DictReader(source))
        self.assertFalse(any(row['function']==matching.FUNCTION for row in existing))
        self.write_rows(self.out/'owner-guards.csv', existing+self.rows)
        padded = []
        for index, obj in enumerate(objects):
            name = 'padded-owner-%d' % index
            self.assemble(name, emit_padded_assembly(obj, self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'owner-guards.csv' if index else self.snapshot/'before-guards',
                filename='generated_58F80', rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out/(name+'.o')))
        base = padded[1][1][matching.FUNCTION]['value']
        self.assertEqual(padded[1][1][matching.FUNCTION]['size'], 492)
        self.assertEqual(padded[1][1]['func_1502FBE8']['value']-base, 492)
        self.assertEqual(padded[1][0][base:base+492], struct.pack('>123I', *matching.recipe(matching.RAW)))
        expected = bytearray(padded[0][0])
        expected[base:base+492] = padded[1][0][base:base+492]
        self.assertEqual(bytes(expected), padded[1][0])
        self.assertEqual({a:v for a,v in padded[0][2].items() if not base<=a<base+492},
            {a:v for a,v in padded[1][2].items() if not base<=a<base+492})
        self.assertEqual({a-base:v for a,v in padded[1][2].items() if base<=a<base+492},
            matching.OUTPUT_RELOCATIONS)
        self.receipt('owner', neighbors=len(parsed[0][1])-1, diagnostics=0,
            other_bodies_extents_relative_relocations_pools_exact=True,
            isolated_owner_equal=True, fitted_symbol_and_window_bytes=492,
            only_copied_target_changes=True, zero_missing_body_padding=True)

    def test_05_independently_linked_signed_carry_rebases(self):
        settings = ((matching.ENTRY, proof.ACTORS, proof.TABLE, proof.SPECIAL),
            (0x15207FF0,0x80107FFC,0x80218004,0x15218004),
            (0x15308004,0x80118004,0x80227FFC,0x15327FFC),
            (0x15417FFC,0x80207FF0,0x80318004,0x15407FF0))
        cases = 0
        for entry, actors, table, special in settings:
            symbols = dict(D_800CC2D0=actors, D_800C5338=table, func_150C3160=special)
            forms = tuple(self.link(name, entry, symbols) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0], forms[2])
            with patch.object(proof.screen, 'ENTRY', entry), patch.object(proof, 'ACTORS', actors),\
                    patch.object(proof, 'TABLE', table), patch.object(proof, 'SPECIAL', special):
                old = self.forms
                self.forms = forms
                try:
                    for slot, kind, pattern, phase in itertools.product((0,25,-1),
                            proof.KINDS, range(4), (0,8)):
                        self.compare(proof.fixture(kind,slot=slot,pattern=pattern),slot=slot,phase=phase)
                        cases += 1
                finally:
                    self.forms = old
        self.receipt('rebases', independent_links=12, symbol_sets=4, cases=cases,
            executions=cases*3, fitted_original_exact=True,
            signed_HI_LO_carries_JAL_entry_and_full_private_events_exact=True)

    def test_06_actual_stale_words_and_relative_relocation_rejections(self):
        data = (self.out/'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
        names_header = headers[header[13]]
        names = data[names_header[4]:names_header[4]+names_header[5]]
        text = next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(120):
            words = [word^0x10000 if i==index else word for i,word in enumerate(matching.RAW)]
            with self.assertRaisesRegex(ValueError, 'stale complete'):
                matching.recipe(words)
            stale = bytearray(data)
            struct.pack_into('>I', stale, text[4]+index*4, words[index])
            path = self.out/'stale.o'
            path.write_bytes(stale)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',
                    filename='generated_58F80')
        for offset in matching.RELOCATIONS:
            rows = [dict(row) for row in self.rows]
            rows[offset//4]['expected_relocations'] = '-'
            path = self.out/'stale-relocations.csv'
            self.write_rows(path, rows)
            with self.assertRaisesRegex(ValueError, 'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,
                    filename='generated_58F80')
        relocation_section = next(s for s in headers
            if names[s[0]:].split(b'\0',1)[0]==b'.rel.text')
        actual_rejections = 0
        for offset in range(relocation_section[4], relocation_section[4]+relocation_section[5], 8):
            address, info = struct.unpack_from('>II', data, offset)
            if address not in matching.RELOCATIONS:
                continue
            stale = bytearray(data)
            struct.pack_into('>II', stale, offset, address, info & ~255 | 2)
            path = self.out/'stale-relocation.o'
            path.write_bytes(stale)
            with self.assertRaisesRegex(ValueError, 'stale complete actor tile relocations'):
                matching.guard_rows(path)
            with self.assertRaisesRegex(ValueError, 'stale relocations'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',
                    filename='generated_58F80')
            actual_rejections += 1
        self.assertEqual(actual_rejections, 5)
        self.receipt('stale', producer_rejections=120, actual_padder_word_rejections=120,
            CSV_relocation_rejections=5, actual_object_relocation_rejections=5,
            no_unchecked_words=True)

    def test_07_complete_native32_C_and_effective_fresh_controls(self):
        with patch.object(proof.screen, 'SELECTED', matching.SELECTED):
            proof.GameActorTileUpdaterRecoveryTests.test_06_actual_native32_C_sdk_all_types_boundaries_aliases_and_negatives(self)
            proof.GameActorTileUpdaterRecoveryTests.test_04_fresh_effective_complete_C_negatives(self)
        for name in ('wrong-row','wrong-type','wrong-inset','wrong-width','wrong-tile',
                'wrong-count','wrong-null-gate'):
            with self.assertRaises(ValueError):
                matching.guard_rows(self.out/(name+'.o'))
        self.receipt('negative-recipe', fresh_complete_C_bodies=7,
            semantically_effective_and_rejected_by_recipe=True)

    def test_08_full_actual_banked_dispatcher_renderer_boundaries(self):
        for name, words in (('raw', self.raw), ('fitted', self.fitted)):
            old = self.raw
            self.raw = words
            try:
                proof.GameActorTileUpdaterRecoveryTests.test_09_complete_banked_renderer_actual_helper_and_tile_call_boundaries(self)
                receipt = json.loads((self.out/'connected.json').read_text())
                self.receipt('connected-'+name, **receipt)
            finally:
                self.raw = old

    def test_09_immutable_production_and_snapshot_hashes(self):
        with self.assertRaisesRegex(ValueError, 'immutable baseline'):
            self.receipt('baseline', replacement=True)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(), self.baseline[name])
            self.assertEqual(hashlib.sha256((self.snapshot/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        before = (self.snapshot/'before-source').read_text()
        with self.assertRaisesRegex(ValueError, 'stale'):
            matching.recovery.copied_owner(matching.recovery.copied_owner(before,matching.SELECTED))
        self.receipt('unchanged-production', five_artifacts_and_original_snapshots_exact=True,
            no_installation_or_matching_credit=True, actual_special_helper_still_open=True)


if __name__ == '__main__':
    unittest.main()
