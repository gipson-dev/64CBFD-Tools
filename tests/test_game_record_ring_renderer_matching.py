"""Closed full-renderer normalization, private boundaries and real owner padding."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_ring_renderer_candidates as screen
from tools.experiments import game_record_ring_renderer_normalization as normalization
from tools.experiments import game_record_ring_renderer_proof as proof
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests import test_game_record_ring_renderer_recovery as recovery


class BoundaryStop(RuntimeError):
    pass


class BoundaryOracle(recovery.RibbonAccessOracle):
    def __init__(self, *args, stop=None, **kwargs):
        self.accesses, self.stop = 0, None
        super().__init__(*args, **kwargs)
        self.accesses, self.stop = 0, stop

    def boundary(self):
        current = self.accesses
        self.accesses += 1
        if current == self.stop:
            raise BoundaryStop(current)

    def get(self, address, size):
        self.boundary()
        return super().get(address, size)

    def put(self, address, value, size):
        self.boundary()
        return super().put(address, value, size)


def snapshot(model):
    return (model.r, model.f, model.lo, model.condition, model.fcsr,
        model.memory, model.events, model.calls)


source_shapes = recovery.source_shapes


class GameRecordRingRendererMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-renderer-test/normalization'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', screen.SETUP_FITTED)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.normalized = normalization.normalize(cls.words)
        text, functions, cls.relocations = parse_object(cls.out / 'selected.o')
        cls.unlinked = list(struct.unpack_from('>405I', text, functions[screen.FUNCTION]['value']))
        cls.guards = normalization.owner_guards(cls.unlinked, cls.relocations)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_pure_derivation_and_whole_cfg_certificate(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (405, 208, 185))
        self.assertEqual(self.normalized, self.retail)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('normalizer must not load retail words')):
            self.assertEqual(normalization.normalize(self.words), self.retail)
        certificate = proof.Proof(self.words, self.normalized).run()
        self.assertEqual((certificate['checked_words'], certificate['obligations'], certificate['call_sites']), (404, 560, 6))
        self.assertEqual(len(normalization.GP_REWRITES), 180)
        self.assertEqual(sum(len(fields) for _, fields in normalization.GP_REWRITES), 230)
        self.assertEqual(len(self.guards), 185)
        self.assertTrue(all(r['expected_relocations'] == r['replacement_relocations'] == '-' for r in self.guards))
        for pc in normalization.RELOCATIONS:
            self.assertEqual(self.words[pc // 4], self.normalized[pc // 4])
        self.receipt('closure', dict(certificate=certificate, raw_differences=185, normalized_differences=0,
            GP_instruction_rewrites=180, GP_field_rewrites=230, guards=185, relocated_guard_words=0,
            all_16_relocation_words_unchanged=True, no_retail_word_lookup=True))

    def test_02_all_word_and_relocation_stale_candidates_fail_closed(self):
        for index in range(405):
            bad = list(self.words)
            bad[index] ^= 1 << 31
            with self.assertRaisesRegex(ValueError, 'stale complete ribbon candidate'):
                normalization.normalize(bad)
        for pc in self.relocations:
            bad = dict(self.relocations)
            bad[pc] = []
            with self.assertRaisesRegex(ValueError, 'stale complete ribbon relocations'):
                normalization.owner_guards(self.unlinked, bad)
        with self.assertRaisesRegex(ValueError, 'wrong complete ribbon extent'):
            normalization.normalize(self.words[:-1])
        self.receipt('stale', dict(changed_word_controls=405, changed_relocation_controls=16,
            wrong_extent=True, full_masked_source_fingerprint=True))

    def test_03_effective_partial_transform_negatives(self):
        controls = ((0x18, 'output register move'), (0x2A0, 'seed alpha product'),
            (0x5C4, 'loop index decrement'), (0x610, 'live goal branch'))
        witnesses = []
        memory = recovery.fixture(flags=10)
        accepted = recovery.RibbonOracle(self.normalized, memory).run()
        for pc, name in controls:
            kept = tuple(item for item in normalization.GP_REWRITES if item[0] != pc)
            with patch.object(normalization, 'GP_REWRITES', kept):
                bad = normalization.normalize(self.words)
            model = recovery.RibbonOracle(bad, memory)
            failure = None
            try:
                model.run()
            except AssertionError as error:
                self.assertRegex(str(error), 'unmapped read|unmapped store|saved register')
                failure = str(error)
            if failure is None:
                self.assertNotEqual((recovery.external(model.memory), model.calls, model.r[2]),
                    (recovery.external(accepted.memory), accepted.calls, accepted.r[2]))
            witnesses.append(dict(omitted=pc, name=name, outcome=failure or 'different logical output'))
        with patch.object(normalization, 'SAVE_REWRITES', normalization.SAVE_REWRITES[:-1]):
            bad = normalization.normalize(self.words)
        with self.assertRaisesRegex(AssertionError, 'saved register'):
            recovery.RibbonOracle(bad, memory).run()
        self.receipt('partial-negatives', dict(controls=witnesses, saved_lifetime_control=True,
            all_effective_without_timeout_or_unsupported_opcode=True))

    def test_04_whole_entry_public_and_complete_private_exit_state(self):
        cases = 0
        for flags, pattern, view, phase, mode in itertools.product((0, 2, 8, 10), range(3),
                (0, 3, -1), (0, 8), (0, 1, 6, 7, 8, 11)):
            memory = recovery.fixture(flags=flags, pattern=pattern, view=view)
            models = [recovery.RibbonAccessOracle(body, memory, view, mode=mode, phase=phase).run()
                for body in (self.words, self.normalized, self.retail)]
            self.assertEqual(snapshot(models[1]), snapshot(models[2]))
            self.assertEqual(models[0].memory, models[2].memory)
            self.assertEqual((models[0].calls, models[0].r[2]), (models[2].calls, models[2].r[2]))
            public = lambda m: [e for e in m.events if e[0] == 'CALL' or
                not recovery.STACK - 0x600 <= e[1] < recovery.STACK + 0x140]
            self.assertEqual(public(models[0]), public(models[2]))
            cases += 1
        self.receipt('private-exits', dict(cases=cases, executions=cases * 3,
            derived_retail_all_model_GP_FP_LO_condition_FCSR_memory_events_calls_equal=True,
            raw_retail_public_prefixes_and_exit_memory_equal=True, raw_private_state_identity=False))

    def test_05_every_private_public_access_boundary_and_real_missing_bytes(self):
        stops = missing = 0
        for flags, pattern, phase in itertools.product((0, 2, 8, 10), range(3), (0, 8)):
            memory = recovery.fixture(flags=flags, pattern=pattern)
            complete = BoundaryOracle(self.retail, memory, phase=phase).run()
            for ordinal in range(complete.accesses):
                models = [BoundaryOracle(body, memory, phase=phase, stop=ordinal)
                    for body in (self.normalized, self.retail)]
                for model in models:
                    with self.assertRaises(BoundaryStop):
                        model.run()
                self.assertEqual(snapshot(models[0]), snapshot(models[1]))
                stops += 1
            seen = set()
            first_reads = set()
            for event in complete.events:
                if event[0] not in ('R', 'W'):
                    continue
                for address in range(event[1], event[1] + event[2]):
                    if address not in seen and event[0] == 'R':
                        first_reads.add(address)
                    seen.add(address)
            for address in sorted(first_reads):
                broken = dict(memory)
                del broken[address]
                models = [recovery.RibbonAccessOracle(body, broken, phase=phase)
                    for body in (self.normalized, self.retail)]
                for model in models:
                    with self.assertRaisesRegex(AssertionError, 'unmapped read|unmapped store'):
                        model.run()
                self.assertEqual(snapshot(models[0]), snapshot(models[1]))
                missing += 1
        self.receipt('private-boundaries', dict(fixtures=24, injected_access_boundary_pairs=stops,
            injected_executions=stops * 2, actual_missing_byte_pairs=missing,
            missing_byte_executions=missing * 2, full_derived_retail_model_state_equal=True,
            raw_private_fault_identity=False, hardware_CP0_FCSR_traps=False))

    def test_06_real_copied_owner_padding_guards_and_independent_rebases(self):
        objects, warnings = [], []
        for name, source in zip(('baseline', 'selected'), source_shapes(self.root)):
            obj, diagnostics = compile_owner(self.root, self.out, source, 'owner-' + name)
            processed = self.out / ('owner-' + name + '-post.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
            warnings.append(diagnostics)
        self.assertEqual(warnings[0], warnings[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            before = previous[name]
            if name == screen.FUNCTION:
                continue
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']],
                old[before['value']:before['value'] + before['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - before['value']: r for o, r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        fn = current[screen.FUNCTION]
        copied = list(struct.unpack_from('>405I', text, fn['value']))
        relative = {o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']}
        self.assertEqual(copied, self.unlinked)
        self.assertEqual(relative, self.relocations)
        self.assertEqual(normalization.owner_guards(copied, relative), self.guards)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards[:11275])
        self.assertIn(guards[11275:], ([], self.guards))
        manifest = self.out / 'proposed.csv'

        def emit(rows):
            with manifest.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=guards[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
                word_patches_path=manifest, filename='generated_204660')

        for index in range(185):
            bad = [dict(row) for row in self.guards]
            bad[index]['expected'] = '0x%08X' % (int(bad[index]['expected'], 0) ^ 1)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit(guards[:11275] + bad)
        bad = [dict(row) for row in self.guards]
        bad[0]['expected_relocations'] = bad[0]['replacement_relocations'] = 'R_MIPS_LO16:D_800DD1E8'
        with self.assertRaisesRegex(ValueError, 'stale relocations'):
            emit(guards[:11275] + bad)
        assembly = emit(guards[:11275] + self.guards)
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, padded_fn, padded_rel = parse_object(obj)
        self.assertEqual((padded_fn[screen.FUNCTION]['size'], padded_rel), (1620, self.relocations))
        original_asm, original_obj = self.out / 'original.s', self.out / 'original.o'
        original_asm.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n.type ' + screen.FUNCTION +
            ', @function\n' + (self.root / 'conker/asm/nonmatchings/generated_204660/func_151D80C4.s').read_text() +
            '\n.size ' + screen.FUNCTION + ', . - ' + screen.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(original_obj), str(original_asm)],
            cwd=self.root, check=True, capture_output=True)
        _, _, original_rel = parse_object(original_obj)
        self.assertCountEqual([r for rs in original_rel.values() for r in rs], [r for rs in padded_rel.values() for r in rs])
        executions = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = dict(screen.SYMBOLS)
            if variant:
                for index, name in enumerate(n for n in symbols if n.startswith('D_')):
                    symbols[name] = 0x70000000 + (index + 1) * 0x100000 + (0x7FFC, 0x8000, 0xFFF8)[(index + variant) % 3]
                for index, name in enumerate(recovery.TARGET_NAMES.values()):
                    symbols[name] = (entry & 0xF0000000) + 0x100800 + index * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for kind, object_ in (('original', original_obj), ('padded', obj), ('raw', self.out / 'selected.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (variant, kind))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(object_)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>405I', screen.sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(normalization.normalize(bodies[2]), bodies[0])
            proof.Proof(bodies[2], bodies[1], entry, symbols).run()
            for flags, mode, phase, view in itertools.product((0, 2, 8, 10), (0, 1, 7, 8, 10, 11), (0, 8), (0, 3)):
                memory = recovery.fixture(flags=flags, view=view, symbols=symbols)
                models = [recovery.RibbonAccessOracle(body, memory, view, mode=mode, phase=phase,
                    entry=entry, symbols=symbols).run() for body in bodies]
                self.assertEqual(snapshot(models[0]), snapshot(models[1]))
                ref = recovery.RibbonReference(memory, view, mode=mode, symbols=symbols).run()
                for model in models:
                    self.assertEqual((recovery.external(model.memory), model.calls, model.r[2], recovery.writes(model)),
                        (recovery.external(ref.memory), ref.calls, ref.result, [e for e in ref.events if e[0] == 'W']))
                    executions += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, pools_relative_relocations_unchanged=True,
            copied_isolated_target_identical=True, warnings=len(warnings[0]), actual_padder_1620_bytes=True,
            no_padding_insertions_omissions=True, guards=185, stale_guard_controls=185,
            stale_guard_relocation=True, independent_links=4, relocation_uses=16,
            executions=executions, raw_padded_original_reference_agreement=True))

    def test_07_linked_baseline_or_installation_guard_and_source_closure(self):
        baseline = json.loads((self.root / 'conker/build/game-record-ring-shaping-test/after.json').read_text())
        linked, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        slots = {name: dict(address=addresses[name], words=len(words),
            sha256=hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()) for name, words in linked.items()}
        self.assertEqual(slots, baseline['slots'])
        self.assertEqual(len(slots), 6058)
        self.assertEqual(linked[screen.FUNCTION], self.retail)
        protected = {name: dict(address=address, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, (address, data) in screen.sections(self.root / 'conker/build/conker.us.elf').items()
            if name in baseline['protected']}
        self.assertEqual(protected, baseline['protected'])
        original, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
            '73e090010650f383d2180dc482c3b9c24d28894f59fc3102fd8115c8fc1910e9')
        installed = (self.root / recovery.SOURCE).read_text() == selected
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        self.assertEqual(guards[:11275], baseline['guards'])
        self.assertEqual(guards[11275:], self.guards if installed else [])
        assert_guard_history(self, guards[:11275])
        with (self.root / 'conker/progress.csv').open(newline='') as stream:
            target = [row for row in csv.DictReader(stream) if row['function'] == screen.FUNCTION]
        self.assertEqual([(r['language'], r['length']) for r in target], [('c' if installed else 'asm', '1620')])
        self.receipt('linked', dict(installed=installed, all_6058_bodies_addresses_extents_unchanged=True,
            protected_sections_unchanged=True, guard_count=len(guards), prior_guard_history_unchanged=True,
            source_reverse_reconstruction_exact=True, progress_target_language='c' if installed else 'asm'))


if __name__ == '__main__':
    unittest.main()
