"""Research gates only: this candidate still has 44 retail word differences."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_microcode_loader as source
from tools.pad_generated_object import parse_object
from tools.tests import game_microcode_loader_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class MicrocodeLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>97I', cls.rom, source.ROM))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.emitted = list(struct.unpack_from('>97I', data, functions[source.FUNCTION]['value']))

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def compare(self, memory, phase=0, mode=0, words=None):
        expected, calls, observations, fired = model.reference(memory, mode)
        m = model.LoaderOracle(self.words if words is None else words, memory, phase, mode).run()
        self.assertEqual(model.submit.public(m.memory), model.submit.public(expected))
        self.assertEqual(m.calls, calls); self.assertEqual(m.observations, observations); self.assertEqual(m.fired, fired)
        return m

    def test_01_emission_is_explicitly_not_installable(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (97, 48, 44))
        self.assertFalse(self.row['byte_exact']); self.assertFalse(self.row['installed'])
        self.assertEqual(self.row['new_guards'], 0); self.assertEqual(self.row['unchanged_raw_neighbors'], 56)
        self.assertEqual((self.row['caller_words'], self.row['caller_differences']), (239, 0))
        self.assertEqual(self.words, self.emitted); self.assertEqual(len(source.RELOCATIONS), 34)
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-loader',
            (self.out / 'before-view_list_caller_original').read_text(), source.FUNCTION)
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(f['size'], 388); self.assertEqual(data[f['value']:f['value'] + 388], self.rom[source.ROM:source.ROM + 388])
        self.receipt('emission', words=97, frame=48, remaining_word_differences=44, new_guards=0,
            raw_neighbors_preserved=56, parent_direct_words_preserved=239, installed=False)

    def test_02_all_words_bindings_pools_and_input_anchors_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for index in range(97):
            bad = bytearray(text); bad[f['value'] + index * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.rodata':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_object(self.obj)
        before = (self.out / 'before-view_list_caller_owner').read_text()
        with self.assertRaises(ValueError): source.recovered_owner(source.recovered_owner(before))
        for key, relative in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), source.BASELINE[key], key)
        self.receipt('fail-closed', words=97, bindings=34, extra_binding=1, pool=1, immutable_live_inputs=len(source.PATHS))

    def test_03_independent_reference_unsigned_input_signed_cache_full_word_flag(self):
        cases = 0; visits = [set(), set()]
        for memory in model.corpus():
            for phase in (0, 8):
                for index, words in enumerate((self.truth, self.words)):
                    visits[index].update(self.compare(memory, phase, words=words).visits)
                cases += 1
        for seen in visits:
            self.assertEqual(seen & set(range(source.ENTRY, source.ENTRY + 388, 4)), set(range(source.ENTRY, source.ENTRY + 388, 4)))
        self.receipt('guest', original_and_candidate_cases=cases, all97_words_visited_in_both=True,
            final_public_memory_and_ordered_DMA_packets_and_publication_snapshots=True,
            literal_register_instruction_trace_and_fault_order_equivalence_not_claimed=True,
            extended_260_row_table_is_synthetic=True, hardware_PI_cache_queue_not_emulated=True)

    def test_04_four_positive_DMA_callbacks_and_live_table_reload(self):
        cases = 0
        for value, flag, phase, mode in itertools.product((0, 1, 2, 3), (0, 1), (0, 8), (1, 2, 4, 8, 15)):
            memory = model.fixture(value, flag)
            wanted = [i + 1 for i in range(4) if mode & (1 << i)]
            self.assertEqual(model.reference(memory, mode)[3], wanted)
            for words in (self.truth, self.words):
                self.assertEqual(self.compare(memory, phase, mode, words).fired, wanted)
            cases += 1
        self.receipt('callbacks', original_and_candidate_cases=cases, all_positive_DMA_gates_fired=True,
            state_and_flag_local_lifetimes_cache_publication_and_post_DMA_table_reloads=True,
            synthetic_mutations_not_gameplay=True)

    def test_05_retail_table_bytes_and_actual_eight_row_domain(self):
        expected = b''.join(struct.pack('>4I', *row) for row in model.RETAIL_TABLE)
        self.assertEqual(self.rom[0x228B38:0x228BB8], expected)
        before = (self.out / 'before-elf').read_bytes(); at = elf_slot_offset(before, model.TABLE, 128)
        self.assertEqual(before[at:at + 128], expected)
        cases = 0
        for value, flag, cache_mode in itertools.product(range(6), (0, 1), (0, 1)):
            memory = model.fixture(value, flag, cache_mode, retail=True)
            for words in (self.truth, self.words): self.compare(memory, words=words)
            cases += 1
        self.receipt('retail-table', table_records=8, table_bytes=128, original_and_candidate_cases=cases,
            actual_text_and_data_transfer_lengths=True, payload_bytes_are_synthetic_not_original_microcode=True)

    def test_06_effective_signed_cache_and_exact_flag_negative_controls(self):
        controls = (
            ('unsigned-cache', source.SELECTED.replace('variant != D_80084070', 'variant != (u8)D_80084070'), model.fixture(130, 0, 1)),
            ('nonzero-flag', source.SELECTED.replace('D_800BEB98 == 1', 'D_800BEB98 != 0'), model.fixture(0, 2)))
        for label, body, memory in controls:
            self.compare(memory)
            words = source.measure(self.root, self.out, 'negative-' + label, body)[1]
            expected = model.reference(memory)
            m = model.LoaderOracle(words, memory).run()
            self.assertTrue(m.calls != expected[1] or model.submit.public(m.memory) != model.submit.public(expected[0]), label)
        self.receipt('negative-controls', functional_controls=2, compiled_and_executed=True,
            unsigned_cache_and_nonzero_flag_rejected=True, no_compile_failures_or_signals_counted=True)

    def test_07_local_signed_byte_instruction_vectors(self):
        for byte, destination in itertools.product((0, 127, 128, 255), (0, 2)):
            memory = model.fixture(); memory[model.STATE_OBJECT + 43] = byte
            word = (32 << 26) | (4 << 21) | (destination << 16) | 65535
            m = model.LoaderOracle([word, 0x03E00008, 0], memory)
            m.r[4] = model.STATE_OBJECT + 44; m.run()
            self.assertEqual(m.r[destination], (((byte ^ 128) - 128) & 0xFFFFFFFF) if destination else 0)
            self.assertEqual(m.all_accesses, 1)
        self.receipt('signed-byte-vectors', vectors=8, signed_address_offset=True, zero_register_preserved=True)


if __name__ == '__main__': unittest.main()
