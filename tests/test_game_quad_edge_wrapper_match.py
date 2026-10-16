"""Framed C proof plus literal normalized private/fault/alias and chain checks."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_wrapper_match as source
from tools.experiments.game_quad_wrapper_proof import prove
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_quad_edge_path_recovery as prior
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class QuadWrapperMatchTests(unittest.TestCase):
    test_09_all_801_archive_fingerprints = prior.QuadEdgePathRecoveryTests.test_09_all_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>61I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_raw_shape_actual_padder_neighbors_and_closed_guards(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['guards_added'], self.row['identity_guards']), (63, 9))
        raw, rel = source.raw_target(self.obj)
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest(), rel), (252, source.RAW_SHA256, source.RELOCATIONS))
        before, diagnostic = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-edge_wrapper_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'])
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']])
            relative = lambda o, f: [(at - f['value'], entries) for at, entries in o[2].items()
                if f['value'] <= at < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g))
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        rows = list(csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())))
        rows = [r for r in rows if r['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 63)
        self.assertEqual([r['offset'] for r in rows if r['omit'] == 'true'], ['0x8', '0x18'])
        self.assertTrue(all(not r['insert_after'] for r in rows))
        self.receipt('shape', raw_words=63, normalized_retail_words=61, guards=63, identity_guards=9, omitted_nonescaping_homes=2,
            neighbors_unchanged=len(old[1]) - 1, minimal_callee_declaration=True)

    def test_02_symbolic_value_graph_proof_and_effective_controls(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        result = prove(raw, rel, normalized, moved)
        a, b = list(struct.unpack('>63I', raw)), list(struct.unpack('>61I', normalized))
        self.assertEqual(sorted(i for i, _ in source.PLAN), [i for i in range(63) if i not in (2, 6)])
        for i, (old, _) in enumerate(source.PLAN):
            mask = sum(31 << shift for shift in source.register_fields(a[old]))
            self.assertEqual(b[i] & ~mask, a[old] & ~mask)
        effective = []
        for name, change in (
                ('actor-base', lambda w: w.__setitem__(5, w[5] & ~(31 << 21) | 5 << 21)),
                ('ordered-float-operands', lambda w: w.__setitem__(21, w[21] & ~((31 << 16) | (31 << 11))
                    | (w[21] >> 11 & 31) << 16 | (w[21] >> 16 & 31) << 11)),
                ('narrow-preset', lambda w: w.__setitem__(19, w[19] & 0x03FF0000 | 36 << 26 | 0x9F)),
                ('return-home', lambda w: w.__setitem__(57, w[57] & 0xFFFF0000 | 0x28))):
            bad = list(b)
            change(bad)
            with self.assertRaises(ValueError, msg=name):
                prove(raw, rel, struct.pack('>61I', *bad), moved)
            effective.append(name)
        bad = list(b)
        bad[53], bad[55] = bad[55], bad[53]
        with self.assertRaises(ValueError):
            prove(raw, rel, struct.pack('>61I', *bad), {212: moved[220]})
        effective.append('call-before-quad-and-scale')
        legal = list(b)
        legal[12], legal[13] = legal[13], legal[12]
        prove(raw, rel, struct.pack('>61I', *legal), moved)
        self.receipt('symbolic-proof', **result, same_opcode_immediate_operation_identity=True,
            effective_dependency_mutants=effective, independent_legal_load_schedule_accepted=True,
            not_a_raw_private_or_FCSR_equivalence_proof=True)

    def test_03_complete_literal_state_and_independent_packets(self):
        cases = 0
        for coords in itertools.product((-32768, -1, 0, 1, 32767), repeat=3):
            for values in ((10., 20., .5, -1.25, 3.5), (-100., -40., -17.5, 0., 123.25)):
                for pattern in range(4):
                    for phase in (0, 8):
                        memory, args = prior.fixture(coords, values, pattern)
                        packet, quad = prior.packet_reference(memory, args, phase)
                        models = [prior.WrapperOracle(w, memory, args, phase).run() for w in (self.words, self.truth, self.raw_words)]
                        self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                        for model in models:
                            self.assertEqual(model.calls, [(source.CALLEE, *packet)])
                            self.assertEqual(model.quads, [quad])
                        cases += 1
        self.receipt('private', normalized_original_pairs=cases, raw_public_pairs=cases,
            complete_literal_register_memory_events_equal=True, framed_source_contract_kept_explicit=True)

    def test_04_every_fired_original_fault_and_bounded_stack_aliases(self):
        faults, aliases = 0, 0
        for phase in (0, 8):
            for pattern in range(4):
                memory, args = prior.fixture(pattern=pattern)
                whole = prior.WrapperOracle(self.truth, memory, args, phase).run()
                for fault in range(whole.accesses):
                    models = [prior.WrapperOracle(w, memory, args, phase, fault=fault) for w in (self.words, self.truth)]
                    for model in models:
                        with self.assertRaises(edge.AccessFault):
                            model.run()
                    self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                    faults += 1
            for offset in (-0x90, -0x80, -0x70, -0x60, -0x50, -0x40, -0x30, -0x20, -0x10, 0, 0x10, 0x20):
                memory, args = prior.fixture(pattern=1)
                args = (edge.STACK + phase + offset, *args[1:])
                models = [prior.WrapperOracle(w, memory, args, phase).run() for w in (self.words, self.truth)]
                self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                aliases += 1
        self.receipt('faults-aliases', fired_prefix_pairs=faults, bounded_guest_aliases=aliases,
            exact_private_state_and_fault_prefix=True, aliases_are_not_claimed_valid_native_C=True)

    def test_05_all_raw_and_guard_relocation_corruptions_fail_closed(self):
        raw, rel = source.raw_target(self.obj)
        for i in range(63):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown wrapper compiler'):
                source.normalize(bytes(bad), rel)
        for bad in ({}, {228: [('R_MIPS_26', 'wrong')]}, {224: rel[228]}):
            with self.assertRaisesRegex(ValueError, 'Unknown wrapper compiler'):
                source.normalize(raw, bad)
        before = (self.out / 'before-guards').read_bytes()
        with self.assertRaisesRegex(ValueError, 'guard predecessor'):
            source.guard_manifest(before + b'\n', raw, rel)
        self.receipt('corruptions', all_63_instruction_flips_rejected=True, changed_call_bindings_rejected=3,
            guard_predecessor_closed=True)

    def test_06_native32_selected_C_and_effective_controls(self):
        with patch.object(prior.source, 'SELECTED', source.SELECTED), patch.object(prior.source, 'DECLARATIONS', source.DECLARATIONS):
            prior.QuadEdgePathRecoveryTests.test_08_native32_O2_O0_all_signed_coordinate_patterns(self)

    def test_07_staged_original_emitter_with_current_factory_allocator(self):
        connected = {}
        connected.update(zip(range(source.CALLEE, source.CALLEE + 1064, 4), struct.unpack_from('>266I', self.rom, 0x19D588)))
        image = (self.root / source.PATHS['elf']).read_bytes()
        for address, rom, count in ((edge.source.FACTORY, 0x19A998, 100), (0x15167A68, 0x194F18, 28)):
            data = image[elf_slot_offset(image, address, count * 4):][:count * 4]
            self.assertEqual(data, self.rom[rom:rom + count * 4])
            connected.update(zip(range(address, address + count * 4, 4), struct.unpack('>%dI' % count, data)))

        class Chain(edge.EdgeOracle):
            def __init__(model, words, memory, args, phase, mode, fail):
                super().__init__(words, memory, args, edge.SAMPLES[2], phase, mode,
                    connected=connected, entry=source.ENTRY, allocation_fail=fail)
                model.wrapper_capture = []

            def record_call(model, target):
                if target == source.CALLEE:
                    args = model.arguments(10)
                    quad = tuple(edge.read(model.memory, args[0] + i * 4) for i in range(12))
                    model.wrapper_capture.append((args, quad))
                super().record_call(target)

        pairs = 0
        table = self.rom[0x2316B4:0x2316B4 + 33]
        for kind in range(3):
            for counts in ((0, 0), (2, 3), (4, 2)):
                for phase in (0, 8):
                    for mode in range(4):
                        for fail in (False, True):
                            memory, args = prior.fixture(pattern=1)
                            args = (*args[:6], kind, args[7], *counts, edge.bits(1.0), *args[11:])
                            memory.update({edge.TABLE + i: value for i, value in enumerate(table)})
                            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(4096)})
                            packet, quad = prior.packet_reference(memory, args, phase)
                            models = [Chain(w, memory, args, phase, mode, fail).run() for w in (self.words, self.truth)]
                            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                            self.assertEqual(models[0].wrapper_capture, [(packet, quad)])
                            pairs += 1
        self.receipt('chain', pairs=pairs, original_emitter_words=266, actual_current_factory_allocator_words=128,
            complete_literal_state_equal=True, providers_and_allocation_failures=True,
            emitter_is_staged_original_not_production_C=True, lower_heap_and_registration_opaque=True)

    def test_08_all_frozen_inputs_and_reference_manifest(self):
        source.freeze(self.root, self.out)
        for key, path in source.PATHS.items():
            current = (self.root / path).read_bytes()
            if key not in ('elf', 'guards', 'edge_wrapper_owner'):
                self.assertEqual(hashlib.sha256(current).hexdigest(), source.BASELINE[key], key)
        self.receipt('inputs', frozen_inputs=len(source.PATHS), unaffected_current_inputs=60,
            installed_image_checked_separately=True)

    def test_10_actual_padder_rejects_all_stale_words_and_bindings(self):
        original = parse_object(self.obj)
        start = original[1][source.FUNCTION]['value']
        manifest = self.out / 'qualified-guards.csv'
        for i in range(63):
            bad = bytearray(original[0])
            bad[start + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(bad), original[1], original[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'],
                        filename=source.OWNER, word_patches_path=manifest)
            rel = dict(original[2])
            rel[start + i * 4] = [('R_MIPS_32', 'wrong')]
            with patch.object(padder, 'parse_object', return_value=(original[0], original[1], rel)):
                with self.assertRaisesRegex(ValueError, 'stale relocations'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'],
                        filename=source.OWNER, word_patches_path=manifest)
        self.receipt('actual-guard-controls', every_source_word_closed=63, every_instruction_binding_closed=63)

    def test_11_independent_original_normalized_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        from tools.experiments.game_actor_classifier_candidates import sections
        import subprocess
        text, functions, rel = parse_object(self.padded)
        emitted, missing = emit_function(text, functions[source.FUNCTION], rel, source.FUNCTION,
            dict(func_151700D8=source.CALLEE))
        self.assertEqual(missing, [])
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('normalized', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        pairs = 0
        for number, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % number)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name in ('original', 'normalized'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, number))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_151700D8=0x%X' % callee, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>61I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            if number == 0:
                self.assertEqual(bodies[0], self.truth)
            with patch.object(prior.source, 'CALLEE', callee):
                for pattern in range(4):
                    for phase in (0, 8):
                        memory, args = prior.fixture(pattern=pattern)
                        models = [prior.WrapperOracle(w, memory, args, phase, entry=entry).run() for w in bodies]
                        self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                        pairs += 1
        self.receipt('rebases', independent_original_normalized_links=3, exact_word_and_private_pairs=pairs)


if __name__ == '__main__':
    unittest.main()
