"""Private full-word fit, derived schedule recipe and its remaining install boundary."""
from collections import Counter
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_view_projection_command_matching as matching
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import test_game_view_projection_command as recovery
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections


class ViewProjectionCommandFittingTests(unittest.TestCase):
    function_words = classmethod(recovery.ViewProjectionCommandTests.function_words.__func__)
    receipt = recovery.ViewProjectionCommandTests.receipt
    trig_fixture = recovery.ViewProjectionCommandTests.trig_fixture

    @classmethod
    def assemble(cls, text, label):
        path = cls.out / (label + '.s')
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        return obj

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        source.freeze(cls.root, cls.root / source.BUILD)
        cls.out = cls.root / source.BUILD / 'lifetime-fit' / 'matching'
        cls.out.mkdir(exist_ok=True)
        cls.before = (cls.root / source.BUILD / 'before-owner').read_text()
        cls.body = matching.SELECTED
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.recover(cls.before, cls.body), 'qualified-fit')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
        cls.raw = cls.function_words(source.FUNCTION)
        cls.rows = matching.guard_rows(cls.obj)
        with (cls.root / source.PATHS['guards']).open() as stream:
            before = list(csv.DictReader(stream))
        cls.fields = list(before[0])
        cls.guards = cls.out / 'private-guards.csv'
        cls.write_rows(cls.guards, [r for r in before if r['function'] != 'func_1510B32C'] + cls.rows)
        primary = pad_c_object.emit_padded_assembly(cls.obj, cls.root / source.PATHS['layout'], source.OWNER, word_patches_path=cls.guards)
        cls.primary = cls.assemble(primary, 'primary-padded')
        data, functions = build.link_owner(cls.root, cls.out, cls.primary, source.OWNER)
        at = functions[source.FUNCTION]['value']
        cls.words = list(struct.unpack_from('>129I', data, at))
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>129I', cls.rom, source.ROM))
        original = (cls.root / source.PATHS['original']).read_text()
        cls.original_text = 'glabel ' + source.FUNCTION + original.split('glabel ' + source.FUNCTION, 1)[1].split('endlabel ' + source.FUNCTION, 1)[0]
        cls.original_text += 'endlabel ' + source.FUNCTION + '\n'
        cls.original_path = cls.out / 'retail-target.s'
        cls.original_path.write_text(cls.original_text)
        raw, functions, relocations = parse_object(cls.obj)
        info = functions[source.FUNCTION]
        emitted, unresolved = emit_function(raw, info, relocations, source.FUNCTION, nm_anchors(cls.root / source.PATHS['elf']))
        if unresolved:
            raise ValueError(unresolved)
        isolated = cls.assemble(emitted, 'isolated')
        selected = cls.out / 'selected-guards.csv'
        cls.write_rows(selected, cls.rows)
        padded = emit_padded_assembly(isolated, cls.original_path, filename=source.OWNER, word_patches_path=selected)
        cls.generated = cls.assemble(padded, 'generated-padded')

    @classmethod
    def write_rows(cls, path, rows):
        with path.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    def models(self, args, near=0, far=0, seed=0, mode=0, phase=0, bodies=None, connected=None, memory=None):
        models = recovery.ViewProjectionCommandTests.models(self, args, near, far, seed, mode, phase,
            bodies or (self.retail, self.raw, self.words), connected, memory)
        for model in models[1:]:
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(model))
        return models

    def test_01_complete_owner_both_padders_and_derived_word_fit(self):
        self.assertEqual((self.diagnostics, len(self.raw), self.raw[0]), ('', 129, 0x27BDFFB0))
        self.assertEqual(sum(a != b for a, b in zip(self.raw, self.retail)), 19)
        raw, functions, relocations = parse_object(self.obj)
        info = functions[source.FUNCTION]
        relative = {at - info['value']: uses for at, uses in relocations.items() if info['value'] <= at < info['value'] + info['size']}
        unlinked = list(struct.unpack_from('>129I', raw, info['value']))
        self.assertEqual(relative, matching.RELOCATIONS)
        partial = matching.recipe(unlinked, scheduling_only=True)
        indices = [*range(21, 34), 71, 77]
        atoms = lambda words, uses: Counter((words[i], tuple(uses.get(i * 4, []))) for i in indices)
        self.assertEqual(atoms(unlinked, relative), atoms(partial, matching.OUTPUT_RELOCATIONS))
        self.assertEqual(len(self.rows), 19)
        self.assertEqual(self.words, self.retail)
        old, diagnostics = build.compile_owner(self.root, self.out, self.before, 'before-fit-owner')
        a, af, ar = parse_object(old)
        retained = set(af) - {source.FUNCTION, 'func_1510B32C', 'func_1510B5F8'}
        for name in retained:
            x, y = af[name], functions[name]
            self.assertEqual(x['size'], y['size'], name)
            self.assertEqual(a[x['value']:x['value'] + x['size']], raw[y['value']:y['value'] + y['size']], name)
            rel = lambda table, item: {at - item['value']: uses for at, uses in table.items() if item['value'] <= at < item['value'] + item['size']}
            self.assertEqual(rel(ar, x), rel(relocations, y), name)
        self.assertEqual((diagnostics, normalized_pools(old)), ('', normalized_pools(self.obj)))
        data, symbols = build.link_owner(self.root, self.out, self.generated, source.OWNER)
        self.assertEqual(data[symbols[source.FUNCTION]['value']:symbols[source.FUNCTION]['value'] + 516], struct.pack('>129I', *self.retail))
        self.receipt('owner', code_words=129, frame=80, raw_differences=19, guards=19,
            independent_schedule_atoms=15, commutative_comparisons=2, branch_delay_words=2,
            both_padders=True, untouched_neighbors=len(retained), pools_fixed=True,
            matrix_child_stub_still_unrecovered=True, no_production_install=True)

    def test_02_raw_public_and_guarded_complete_state(self):
        cases, coverage = 0, [set(), set(), set()]
        for index, clip, seed, mode, phase in itertools.product((0, 1, 3), range(5), range(6), range(6), (0, 8)):
            args = (index, bits(1.25), bits(-2.5), bits((1.0, -1.25, 0.0)[index % 3]), recovery.CLIPS[(clip + 2) % 5])
            models = self.models(args, recovery.CLIPS[clip], recovery.CLIPS[(clip + 1) % 5], seed, mode, phase)
            for i, model in enumerate(models):
                coverage[i].update(model.visits)
            cases += 1
        self.receipt('public', cases=cases, raw_source_public_and_guarded_complete_state=True,
            reached_root_words=[len(s & set(range(source.ENTRY, source.ENTRY + 516, 4))) for s in coverage],
            signed_zero_and_qNaN_clip_transport=True, finite_arithmetic_no_native_FCSR_or_gameplay_claim=True)

    def test_03_independent_original_and_rebased_links(self):
        assembly = self.original_text + '.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',516\n'
        original = self.assemble(assembly, 'original')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        used = {name for uses in matching.OUTPUT_RELOCATIONS.values() for _, name in uses}
        for delta in (0, 0x9000):
            outputs = []
            for label, obj in (('original', original), ('generated', self.out / 'generated-padded.o')):
                script = self.out / ('rebase-' + label + '-' + str(delta) + '.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, anchors[name] + delta) for name in sorted(used)],
                    '-o', str(elf), str(obj)], capture_output=True, check=True)
                self.assertEqual(nm_anchors(elf)[source.FUNCTION], source.ENTRY + delta)
                outputs.append(sections(elf)['.text'][1][:516])
            self.assertEqual(outputs[0], outputs[1])
            if not delta:
                self.assertEqual(outputs[0], self.rom[source.ROM:source.ROM + 516])

    def test_04_fired_prefixes_and_independent_schedule_boundary(self):
        partial = list(self.raw)
        partial[21:34] = [*self.raw[22:34], self.raw[21]]
        partial[71], partial[77] = self.raw[77], self.raw[71]
        self.assertEqual([i for i, (a, b) in enumerate(zip(partial, self.retail)) if a != b], [88, 90, 91, 104])
        cases = 0
        for near, fallback, phase in itertools.product((0, bits(7.0), 0x7FC12345), (0, bits(2.0)), (0, 8)):
            args = (0, bits(1.25), bits(-2.5), bits(1.0), fallback)
            memory = recovery.fixture(near=near)
            full = recovery.CommandOracle(self.retail, memory, args, phase=phase).run()
            for cut in range(full.root_accesses):
                models = [recovery.CommandOracle(words, memory, args, phase=phase, fault=cut) for words in (self.retail, partial, self.words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                for model in models[1:]:
                    self.assertEqual(machine.complete_state(models[0]), machine.complete_state(model))
                    self.assertEqual((models[0].current_pc, models[0].delay_of), (model.current_pc, model.delay_of))
                cases += 1
        self.receipt('faults', fired_paired_prefixes=cases,
            literal_retail_guarded_and_schedule_only_four_difference_bodies=True,
            full_modeled_state_PC_and_delay_identity=True, helpers_atomic_bounded_no_FCSR_or_native_fault_claim=True)

    def test_05_expected_word_relocation_and_unknown_recipe_controls(self):
        for index in range(len(self.rows)):
            rows = [dict(row) for row in self.rows]
            rows[index]['expected'] = '0x%08X' % (int(rows[index]['expected'], 16) ^ 1)
            bad = self.out / 'bad-expected.csv'
            self.write_rows(bad, rows)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'], source.OWNER, word_patches_path=bad)
        rows = [dict(row) for row in self.rows]
        rows[0]['expected_relocations'] = 'R_MIPS_LO16:D_800A2C24'
        self.write_rows(bad, rows)
        with self.assertRaises(ValueError):
            pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'], source.OWNER, word_patches_path=bad)
        data, functions, _ = parse_object(self.obj)
        info = functions[source.FUNCTION]
        words = list(struct.unpack_from('>129I', data, info['value']))
        words[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'complete view-command words'):
            matching.recipe(words)
        with patch.object(matching, 'RELOCATIONS', {}):
            with self.assertRaisesRegex(ValueError, 'complete view-command relocations'):
                matching.guard_rows(self.obj)

    def test_06_connected_trig_wrapper_and_effective_semantic_controls(self):
        recovery.ViewProjectionCommandTests.test_03_connected_actual_recovered_trig(self)
        recovery.ViewProjectionCommandTests.test_04_actual_typed_wrapper_to_private_command(self)
        recovery.ViewProjectionCommandTests.test_05_effective_compiled_semantic_controls(self)

    def test_07_frozen_production_no_installation(self):
        source.freeze(self.root, self.root / source.BUILD)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        self.assertEqual((self.body.count('cosineX'), self.body.count('cosineY')), (3, 5))

    def test_08_completed_source_screens_without_raw_match(self):
        rows = json.loads((self.root / source.BUILD / 'lifetime-fit/screens.json').read_text())
        self.assertEqual(len(rows), 141)
        self.assertTrue(all(not row['diagnostics'] for row in rows))
        self.assertFalse(any(row['bytes'] == 516 and not row['differences'] for row in rows))


if __name__ == '__main__':
    unittest.main()
