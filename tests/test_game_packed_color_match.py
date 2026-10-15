"""Packed RGB raw/guarded semantics, physical guards, rebases and real lifecycle."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_color_match as source
from tools.experiments import game_packed_color_control_fit as fit
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests import test_game_packed_color_callback as previous
from tools.tests import test_game_packed_record_updater as updater


class ColorOracle(previous.ColorOracle):
    def __init__(self, words, memory, record=previous.RECORD, entry=source.ENTRY, fault=None):
        MaskOracle.__init__(self, words, memory, entry=entry, arguments=(record,), fault=fault)
        self.fcsr = self.initial_fcsr = 0


class ConnectedColorOracle(updater.UpdaterOracle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fcsr = self.initial_fcsr = 0

    def execute(self, word):
        op, rs, fn = word >> 26, word >> 21 & 31, word & 63
        if op == 17 and (rs in (2, 6) or (rs == 16 and fn == 36)):
            return AreaOracle.execute(self, word)
        return super().execute(word)


def state(model):
    return (model.memory, model.r, model.f, model.lo, model.condition, model.events,
        model.calls, model.accesses, model.fcsr)


class PackedColorMatchCandidateTests(unittest.TestCase):
    def test_complete_recipes_scoped_source_and_frozen_input_set(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(len(set(source.PATHS.values())), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(fit.candidates()), 3)
        before = 'extern s32 D_800BE9E4;\ns32 func_1516E8CC() {\n    return 0;\n}\nvoid other(void) { }\n'
        for body in fit.candidates().values():
            self.assertNotIn('volatile', body)
            self.assertNotIn('__asm__', body)
            self.assertEqual(source.build.body(body, source.FUNCTION), body[body.index('s32 func_'):].strip())
            self.assertTrue(source.recovered_owner(before, body).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        self.assertEqual(len(source.GUARDS), 7)
        self.assertEqual([g[0] for g in source.GUARDS[:5]], [0xC0, 0xCC, 0xD0, 0xD8, 0xDC])
        for key in source.BASELINE:
            self.assertRegex(source.BASELINE[key], '^[0-9a-f]{64}$')


class PackedColorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>248I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = previous.PackedColorRecoveryTests.test_06_all_original_801_archive_fingerprints

    def test_01_all_words_neighbors_physical_guards_and_dead_tail(self):
        self.assertEqual(self.words, self.truth)
        before, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        f = new[1][source.FUNCTION]
        raw = new[0][f['value']:f['value'] + f['size']]
        normalized, rel = source.normalize(raw, source.RELOCATIONS)
        self.assertEqual(rel, source.RELOCATIONS)
        for index in range(246):
            bad = bytearray(raw)
            bad[index * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), source.RELOCATIONS)
        for at in source.RELOCATIONS:
            with self.assertRaises(ValueError):
                source.normalize(raw, {p: r for p, r in source.RELOCATIONS.items() if p != at})
        self.assertEqual(struct.unpack_from('>5I', normalized, 0x3CC), (0x00001025, 0x03E00008, 0, 0x03E00008, 0))
        old_guards = (self.out / 'before-guards').read_bytes()
        guards = source.guard_manifest(old_guards)
        self.assertEqual(guards[:len(old_guards)], old_guards)
        self.assertEqual(len(guards[len(old_guards):].splitlines()), 7)
        self.receipt('owner', raw_words=246, raw_instruction_differences=5, missing_dead_tail_words=2,
            guarded_words=248, guarded_differences=0, unchanged_neighbors=len(new[1]) - 1,
            pools_and_relocations_fixed=True, all_word_and_relocation_corruptions_rejected=True,
            first_A3_to_A1_live_range_only=True, reachable_return_delay_slot_preserved=True)

    def test_02_raw_guarded_retail_live_words_aliases_and_private_state(self):
        count = 0
        deltas = (0, 1, 2, 255, 256, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000000, 0x7FFFFFFF, 0x01000000, 0x87654321)
        for i in range(1024):
            for record in (previous.RECORD, previous.DELTA - 0x1C, previous.DELTA - 0x14):
                ramp = (0, 1, 9)[i % 3]
                if i // 256 == 3 and ramp == 0:
                    ramp = 1
                memory = previous.fixture(i & 255, (i // 256) * 85, deltas[(i // 7) % len(deltas)],
                    (i * 65521) & 65535, ramp, record)
                expected = previous.reference(memory, record)
                models = [ColorOracle(words, memory, record).run() for words in (self.raw, self.words, self.truth)]
                self.assertEqual(state(models[1]), state(models[2]))
                for model in models:
                    self.assertEqual((model.memory, model.r[2]), expected)
                self.assertEqual(models[0].events, models[1].events)
                self.assertEqual(models[1].r[29], updater.STACK)
                count += 1
        self.receipt('semantics', cases=count, all_intensity_bytes=True, raw_and_guarded_memory_return_access_trace_equal=True,
            guarded_private_registers_FCSR_and_events_equal_retail=True, frame=0,
            bounded_table_starts=[0, 1, 9], start_zero_phase_below_255=True,
            arbitrary_index_and_hardware_FCSR_not_claimed=True)

    def test_03_every_fired_guest_access_prefix_and_private_state(self):
        count = 0
        for intensity in (0, 1, 127, 255):
            for countdown in (0, 1):
                for ramp in (0, 1, 9):
                    memory = previous.fixture(intensity, countdown, 0xFFFFFFFF, ramp=ramp)
                    whole = ColorOracle(self.words, memory).run()
                    for fault in range(whole.accesses):
                        pair = [ColorOracle(words, memory, fault=fault) for words in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        count += 1
        self.receipt('prefixes', fired_paired_guest_faults=count, private_state_and_FCSR_equal=True,
            emitted_guest_not_portable_C_fault_or_hardware_claim=True)

    def test_04_five_effective_compiled_controls_receive_no_guards(self):
        controls = {
            'early-byte': source.SELECTED.replace('value = (s32)((u32)value -', 'value = (u8)((u32)value -'),
            'wrong-fade': source.SELECTED.replace('D_800BE9E4 << 4', 'D_800BE9E4 << 3'),
            'lost-height': source.SELECTED.replace('    *(s16 *)(record + 0x16) = value;\n', ''),
            'wrong-phase': source.SELECTED.replace('phase += 8;', 'phase += 9;'),
            'swapped-weights': source.SELECTED.replace('color[0] * complement', 'color[0] * weight').replace('color[-3] * weight', 'color[-3] * complement'),
        }
        failures = {}
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            obj, words, _ = source.measure(self.root, self.out, 'negative-' + name, body)
            data, fs, rel = parse_object(obj)
            f = fs[source.FUNCTION]
            with self.assertRaises(ValueError):
                source.normalize(data[f['value']:f['value'] + f['size']], source.RELOCATIONS)
            count = 0
            for i in range(256):
                memory = previous.fixture(i, (i // 32) * 5, 0xFFFFFFFF if i & 1 else 1, i * 257, 1)
                model = ColorOracle(words, memory).run()
                count += (model.memory, model.r[2]) != previous.reference(memory)
            self.assertGreater(count, 0, name)
            failures[name] = count
        self.receipt('controls', effective_compiled_failures=failures, normalization_rejects_every_mutant=True)

    def test_05_native32_actual_C_O2_O0_against_original_guest(self):
        with patch.object(previous, 'source', source):
            previous.PackedColorRecoveryTests.test_05_native32_finite_conversion_cases_against_guest_results(self)

    def test_06_independent_original_rebases_and_signed_low_carries(self):
        data, fs, _ = parse_object(self.obj)
        f = fs[source.FUNCTION]
        normalized, rel = source.normalize(data[f['value']:f['value'] + f['size']], source.RELOCATIONS)
        symbols = dict(D_800BE9E4=previous.DELTA, D_800A6E00=previous.TIMES, D_800A6E0C=previous.COLORS)
        text, missing = emit_function(normalized, dict(value=0, size=992), rel, source.FUNCTION, symbols)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        rebases = ((0, previous.DELTA, previous.TIMES, previous.COLORS),
            (0x10000, 0x80318004, 0x80517FFC, 0x80627FF0), (-0x10000, 0x80407FFC, 0x80728004, 0x80838FF0))
        for index, (delta, step, times, colors) in enumerate(rebases):
            anchors = dict(D_800BE9E4=step, D_800A6E00=times, D_800A6E0C=colors)
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in anchors.items()], '-o', str(elf), str(self.out / (label + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(sections(elf)['.text'][1][:992])
            self.assertEqual(outputs[0], outputs[1])
            with patch.multiple(previous, DELTA=step, TIMES=times, COLORS=colors):
                for ramp in (0, 1, 9):
                    memory = previous.fixture(127, 1, ramp=ramp)
                    memory.update({times + i: value for i, value in enumerate(previous.TABLE[:12])})
                    memory.update({colors + i: value for i, value in enumerate(previous.TABLE[12:])})
                    model = ColorOracle(list(struct.unpack('>248I', outputs[0])), memory, entry=source.ENTRY + delta).run()
                    self.assertEqual((model.memory, model.r[2]), previous.reference(memory))
        self.receipt('rebases', independent_original_text_data_pairs=3, all_three_symbols_rebased=True,
            signed_low_carry_boundaries=True, same_full_248_words=True)

    def test_07_actual_updater_dispatch_callback_and_cleanup(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, rom, count in ((source.ENTRY, source.ROM, 248), (0x1516972C, 0x196BDC, 28)):
            words = self.words if entry == source.ENTRY else list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        update_words = list(struct.unpack_from('>48I', image, elf_slot_offset(image, 0x1516D678, 192)))
        self.assertEqual(update_words, list(struct.unpack_from('>48I', self.rom, 0x19AB28)))
        table = self.rom[0x231660:0x231684]
        self.assertEqual(struct.unpack_from('>I', table)[0], source.ENTRY)
        removed = active = 0
        for i in range(256):
            binding = 0 if i % 3 == 0 else updater.BINDING
            memory = updater.fixture(i, 1, 0, binding=binding)
            memory.update({0x8008CBA0 + j: v for j, v in enumerate(table)})
            memory.update({previous.TIMES + j: v for j, v in enumerate(previous.TABLE)})
            put(memory, updater.RECORD + 0x1F, i, 1)
            put(memory, updater.RECORD + 0x26, 0 if i < 248 else 1 if i & 1 else 9, 1)
            callback_input = dict(memory)
            put(callback_input, updater.RECORD + 0x24, max(i - 1, 0), 1)
            expected, result = previous.reference(callback_input, updater.RECORD)
            model = ConnectedColorOracle(update_words, memory, connected=connected).run()
            calls = [(source.ENTRY, updater.RECORD)]
            if result:
                removed += 1
                self.assertEqual(model.unlink_lifetime, [0 if binding else None])
                if binding:
                    put(expected, binding + 4, 0, 2)
                put(expected, updater.RECORD, 0, 1)
                calls.extend([(0x1516972C, updater.RECORD), (updater.UNLINK, updater.RECORD)])
            else:
                active += 1
                self.assertEqual(model.unlink_lifetime, [])
                y = updater.short(read(expected, updater.RECORD + 16, 2))
                velocity = updater.short(read(expected, updater.RECORD + 24, 2))
                fixed = (y * 256 + read(expected, updater.RECORD + 37, 1) + velocity) & 0xFFFFFFFF
                put(expected, updater.RECORD + 16, signed(fixed) >> 8, 2)
                put(expected, updater.RECORD + 37, fixed, 1)
            for base, length in ((updater.RECORD, 64), (updater.BINDING, 16)):
                for j in range(length):
                    self.assertEqual(model.memory[base + j], expected[base + j])
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.fcsr, 0)
        self.assertGreater(removed, 0)
        self.assertGreater(active, 0)
        self.receipt('connected', actual_updater_callback_cleanup_cases=256, actual_table_index=0,
            removed=removed, active=active, NULL_and_nonNULL_bindings=True,
            callback_and_cleanup_not_opaque=True, lower_unlink_destructor_providers_opaque=True)


if __name__ == '__main__':
    unittest.main()
