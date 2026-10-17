"""Guarded 97-word fit, raw C semantics, native-independent rebases and fault cuts."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_microcode_loader_lifetimes as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_microcode_loader_oracle as model
from tools.tests import test_game_microcode_loader as previous
from tools.tests import test_game_actor_burst_consumer_match as faults


def state(m):
    return (m.memory, m.r, m.f, m.lo, m.events, m.calls, m.current_pc, m.delay_of,
        m.all_accesses, m.root_accesses, m.observations, m.fired)


class Connected(model.LoaderOracle):
    def __init__(self, words, memory, args, helpers, phase, mode):
        model.submit.machine.InitializeOracle.__init__(self, words, memory, args, helpers, phase,
            entry=model.submit.source.ENTRY)
        self.variant, self.paired = model.selectors(memory[model.read(memory, model.STATE) + 43], model.read(memory, model.FLAG))
        self.loader_mode, self.dma_count = mode, 0

    def record_call(self, target):
        if target == model.DMA:
            self.dma_count += 1
            return model.LoaderOracle.record_call(self, target)
        return model.submit.SubmitOracle.record_call(self, target)

    def hook(self, target):
        if target == model.DMA:
            model.transfer(self.memory, self.calls[-1][1])
            if model.effects(self.memory, self.dma_count, self.variant, self.paired, self.loader_mode):
                self.fired.append(self.dma_count)
        elif target not in (model.submit.CACHE, model.submit.SEND):
            raise ValueError('Unconnected provider: %X' % target)
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344


class MicrocodeLoaderLifetimesTests(unittest.TestCase):
    compare = previous.MicrocodeLoaderTests.compare

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>97I', cls.rom, source.source.ROM))
        data, functions = source.source.build.link_owner(cls.root, cls.out, cls.padded, source.source.OWNER)
        cls.normalized = list(struct.unpack_from('>97I', data, functions[source.source.FUNCTION]['value']))
        cls.original = cls.out / 'original-loader.o'

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def test_01_guarded97_original_frame_homes_and_56_raw_neighbors(self):
        self.assertEqual((self.row['words'], self.row['frame']), (96, 48))
        self.assertTrue(self.row['byte_exact']); self.assertFalse(self.row['direct']); self.assertFalse(self.row['installed'])
        self.assertEqual(self.row['new_guards'], 23); self.assertEqual(self.row['unchanged_raw_neighbors'], 56)
        self.assertEqual((self.row['caller_words'], self.row['caller_differences']), (239, 0))
        self.assertEqual(self.normalized, self.truth); self.assertEqual(len(source.RELOCATIONS), 34)
        self.assertEqual(len(source.SCHEDULE), 5); self.assertEqual(len(source.PUBLICATION), 11); self.assertEqual(len(source.REGISTERS), 7)
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before)); self.assertEqual(after.count(b'\n') - before.count(b'\n'), 23)
        self.assertEqual(after.count(b'\r\n'), before.count(b'\r\n'))
        for key, relative in source.source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), source.source.BASELINE[key], key)
        self.receipt('emission', raw_words=96, normalized_words=97, original_frame=48,
            new_guards=23, existing_guard_prefix_unchanged=True, added_instructions=1,
            no_frame_or_home_or_saved_lifetime_repairs=True, unchanged_raw_neighbors=56,
            unchanged_production_inputs=len(source.source.PATHS), installed=False)

    def test_02_all_raw_and_original_words_bindings_pools_and_guard_fields_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.source.FUNCTION]
        for index in range(96):
            bad = bytearray(text); bad[f['value'] + index * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.data':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_object(self.obj)
        original = parse_object(self.original); g = original[1][source.source.FUNCTION]; real_parse = source.parse_object
        for index in range(97):
            bad = bytearray(original[0]); bad[g['value'] + index * 4] ^= 1
            def parse(path):
                return (bytes(bad), original[1], original[2]) if path == self.original else real_parse(path)
            with patch.object(source, 'parse_object', side_effect=parse):
                with self.assertRaises(ValueError): source.normalization(self.obj, self.original)
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        reader = csv.DictReader(io.StringIO(after[len(before):].decode()), fieldnames=next(csv.reader(io.StringIO(before.decode()))))
        rows = list(reader); count = 0
        for row in rows:
            for field in reader.fieldnames:
                old = row[field]; row[field] = 'bad'; stream = io.StringIO(newline='')
                writer = csv.DictWriter(stream, fieldnames=reader.fieldnames, lineterminator='\n'); writer.writerows(rows)
                with self.assertRaises(ValueError): source.checked_guards(before, before + stream.getvalue().encode(), self.obj, self.original)
                row[field] = old; count += 1
        self.assertEqual(count, 253)
        self.receipt('fail-closed', raw_words=96, original_words=97, raw_bindings=34, extra_binding=1,
            private_pool=1, guard_field_corruptions=253, pinned_original_binding_map=True)

    def test_03_reference_raw_C_and_guarded97_all_instruction_positions(self):
        cases = 0; visits = [set(), set(), set()]
        for memory in model.corpus():
            for phase in (0, 8):
                machines = []
                for index, words in enumerate((self.truth, self.words, self.normalized)):
                    m = self.compare(memory, phase, words=words); visits[index].update(m.visits); machines.append(m)
                self.assertEqual(state(machines[0]), state(machines[2])); cases += 1
        for seen, length in zip(visits, (97, 96, 97)):
            wanted = set(range(source.source.ENTRY, source.source.ENTRY + length * 4, 4))
            self.assertEqual(seen & wanted, wanted)
        self.receipt('guest', three_way_cases=cases, all_raw96_and_normalized97_words_visited=True,
            raw_C_public_memory_calls_and_publication_snapshots=True,
            guarded97_literal_private_memory_GPR_FPR_access_and_delay_state=True,
            extended_table_is_synthetic=True, DMA_hardware_bounded=True)

    def test_04_positive_callbacks_real_table_and_literal_fault_prefixes(self):
        cases = 0
        for value, flag, phase, mode in itertools.product(range(4), (0, 1), (0, 8), (1, 2, 4, 8, 15)):
            memory = model.fixture(value, flag); wanted = [i + 1 for i in range(4) if mode & (1 << i)]; machines = []
            for words in (self.truth, self.words, self.normalized):
                m = self.compare(memory, phase, mode, words); self.assertEqual(m.fired, wanted); machines.append(m)
            self.assertEqual(state(machines[0]), state(machines[2])); cases += 1
        retail_cases = 0
        for value, flag, cache in itertools.product(range(6), (0, 1), (0, 1)):
            memory = model.fixture(value, flag, cache, retail=True)
            for words in (self.truth, self.words, self.normalized): self.compare(memory, words=words)
            retail_cases += 1
        fault_count = 0
        for value, flag, cache, phase, mode in ((0, 0, 0, 0, 15), (1, 1, 0, 8, 0), (2, 0, 1, 0, 0), (3, 1, 0, 8, 15)):
            memory = model.fixture(value, flag, cache); full = self.compare(memory, phase, mode, self.truth)
            for fault in range(full.all_accesses):
                partial = []
                for words in (self.truth, self.normalized):
                    m = model.LoaderOracle(words, memory, phase, mode); m.access_fault = fault
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    self.assertEqual(m.all_accesses, fault); partial.append(m)
                self.assertEqual(state(partial[0]), state(partial[1])); fault_count += 1
        self.receipt('callbacks-faults', positive_callback_cases=cases, real_table_cases=retail_cases,
            fired_original_guarded_fault_prefixes=fault_count, raw_C_fault_equivalence_not_claimed=True,
            provider_payload_and_hardware_contracts_bounded=True)

    def test_05_three_independent_original_and_guarded_C_rebases(self):
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in source.RELOCATIONS.values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:(entry + 0x10000 if name.startswith('func_') else
                0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index]) for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.source.FUNCTION], relocations, source.source.FUNCTION, symbols)
            self.assertFalse(unresolved)
            asm = self.out / ('rebase-C-%d.s' % index); asm.write_text(emitted); obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', self.original), ('C', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index)); elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:388])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', independent_original_links=3, independent_guarded_C_links=3,
            all97_words=True, HI_LO_carries=True, raw_C_not_represented_as_direct_match=True)

    def test_06_real239_word_parent_61_word_setup_and_connected_fault_prefixes(self):
        parent = list(struct.unpack_from('>239I', self.rom, model.submit.source.ROM))
        helper = dict(zip(range(model.submit.INIT, model.submit.INIT + 244, 4), struct.unpack_from('>61I', self.rom, 0x4784C)))
        cases = fault_count = 0; visits = set()
        for used, page, value, program, mode, phase, cache in itertools.product((-1, 20, 1001), (0, 1),
                (0, 3), (0, 1), (0, 15), (0, 8), (0, 1)):
            memory, args = model.submit.fixture(used=used, page=page, program=program)
            memory.update(model.fixture(value, 1 if value else 0, cache)); results = []
            def effect(mem, target, unused):
                if target == model.submit.UCODE:
                    result = model.reference(mem, mode); mem.clear(); mem.update(result[0]); results.append(result)
                return False
            with patch.object(model.submit, 'effects', side_effect=effect):
                expected, calls, _ = model.submit.reference(memory, args)
            self.assertEqual(len(results), 1); load = results[0]
            ordered = []
            for call in calls:
                ordered.append(call)
                if call[0] == model.submit.UCODE: ordered.extend(load[1])
            machines = []
            for words in (self.truth, self.words, self.normalized):
                connected = dict(helper); connected.update(zip(range(source.source.ENTRY, source.source.ENTRY + len(words) * 4, 4), words))
                m = Connected(parent, memory, args, connected, phase, mode).run()
                self.assertEqual(model.submit.public(m.memory), model.submit.public(expected))
                self.assertEqual(m.calls, ordered); self.assertEqual(m.observations, load[2]); self.assertEqual(m.fired, load[3])
                visits.update(m.visits); machines.append(m)
            self.assertEqual(state(machines[0]), state(machines[2])); cases += 1
            if (used, page, value, program, mode, phase, cache) not in ((-1, 0, 0, 0, 15, 0, 0), (20, 0, 0, 0, 0, 8, 1)):
                continue
            for fault in range(machines[0].all_accesses):
                partial = []
                for words in (self.truth, self.normalized):
                    connected = dict(helper); connected.update(zip(range(source.source.ENTRY, source.source.ENTRY + 388, 4), words))
                    m = Connected(parent, memory, args, connected, phase, mode); m.access_fault = fault
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    self.assertEqual(m.all_accesses, fault); partial.append(m)
                self.assertEqual(state(partial[0]), state(partial[1])); fault_count += 1
        self.assertEqual(visits & set(helper), set(helper))
        self.receipt('connected', three_way_cases=cases, real_parent_words=239, real_setup_words=61,
            all61_setup_words_visited=True, fired_original_guarded_memory_fault_prefixes=fault_count,
            real_loader_executed_instead_of_previous_ucode_hook=True,
            actual_PI_cache_and_queue_hardware_not_emulated=True, full_startup_or_gameplay_not_claimed=True)


if __name__ == '__main__': unittest.main()
