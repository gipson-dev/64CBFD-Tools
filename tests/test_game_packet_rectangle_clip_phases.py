"""Qualify the twelve directly recovered flip words, not the six stack homes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_clip_phases as source
from tools.tests import test_game_packet_rectangle_recovery as prior
from tools.tests import game_packet_rectangle_oracle as guest


def controls():
    with patch.object(prior.source, 'SELECTED', source.SELECTED):
        rows = prior.controls()
    rows['wrong-inset'] = source.replace_once(source.SELECTED,
        '(width + width) / D_800D2C80', 'width / D_800D2C80')
    rows['wrong-animation-modulo'] = source.replace_once(source.SELECTED,
        'packet->animationFrame -= packet->descriptor->unkA << 3;',
        'packet->animationFrame %= packet->descriptor->unkA << 3;')
    if any(body == source.SELECTED for body in rows.values()):
        raise ValueError('Ineffective rectangle source control')
    return rows


class RectangleClipPhaseTests(unittest.TestCase):
    receipt = prior.PacketRectangleRecoveryTests.receipt
    test_01_public = prior.PacketRectangleRecoveryTests.test_01_original_and_C_geometry_globals_and_animation
    test_04_aliases = prior.PacketRectangleRecoveryTests.test_04_guest_aliases_preserve_live_descriptor_and_color_reads
    test_05_traps = prior.PacketRectangleRecoveryTests.test_05_guest_division_traps_and_nonfinite_conversion_scope
    test_07_animation = prior.PacketRectangleRecoveryTests.test_07_original_animation_loop_and_both_pingpong_directions
    test_09_rebases = prior.PacketRectangleRecoveryTests.test_09_original_and_C_independent_symbol_rebases
    test_10_connected_caller = prior.PacketRectangleRecoveryTests.test_10_connected_real_visibility_caller_and_renderer

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.installed = hashlib.sha256((cls.root / 'conker/build/conker.us.elf').read_bytes()).hexdigest() != (
            source.INPUTS['conker/build/conker.us.elf'])
        cls.values = source.freeze(cls.root, cls.out, cls.installed)
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out, cls.installed)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>346I', cls.rom, source.ROM))
        (cls.out / 'before-packet_original').write_bytes(cls.values['conker/asm/C1D70.s'])

    def test_02_native32(self):
        with patch.object(prior.source, 'SELECTED', source.SELECTED), patch.object(prior, 'controls', return_value=controls()):
            prior.PacketRectangleRecoveryTests.test_02_native32_O2_O0_UBSan_and_effective_controls(self)

    def test_03_complete_source_shape_and_saved_screen(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['different']),
            (346, 136, [205, 210, 211, 224, 242, 254]))
        self.assertEqual(self.words[:205], self.truth[:205])
        self.assertEqual(self.words[-91:], self.truth[-91:])
        rows = json.loads((self.out / 'screen.json').read_text())
        self.assertEqual(len(rows), 19)
        self.assertEqual(len({body for _, body in source.forms()}), 19)
        best = min(rows, key=lambda row: row['differences'])
        self.assertEqual(best['label'], 'flip-origin-first-ST')
        self.assertEqual((best['differences'], best['old_exact_losses']), (6, []))
        baseline = self.out / 'predecessor.o'
        pools = source.normalized_pools(baseline)
        for row, (label, body) in zip(rows, source.forms()):
            self.assertEqual(row['label'], label)
            self.assertEqual(row['source_sha256'], hashlib.sha256(body.encode()).hexdigest())
            self.assertEqual((self.out / (label + '.c')).read_text(),
                source.recovered_owner(self.values['conker/src/game/generated_C1D70.c'].decode(), body))
            obj = self.out / (label + '.o')
            data, functions = source.previous.build.link_owner(self.root, self.out, obj, source.OWNER)
            _, _, actual = source.facts(obj, data, functions, self.truth)
            for key, value in actual.items():
                self.assertEqual(row[key], value, (label, key))
            self.assertEqual(source.same_functions(baseline, obj, (source.FUNCTION,)), 18)
            self.assertEqual(source.normalized_pools(obj), pools)

    def test_06_compiled_controls(self):
        rejected = []
        for label, body in controls().items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + label, body, self.installed)
            self.assertFalse(row['diagnostics'])
            for memory, args in prior.cases():
                expected, cursor, trap = guest.reference(memory, args)
                self.assertIsNone(trap)
                model = guest.RectangleOracle(words, memory, args).run()
                if (guest.base.public(model.memory), model.r[2]) != (guest.base.public(expected), cursor):
                    rejected.append(label)
                    break
            else:
                self.fail('Ineffective compiled rectangle control: ' + label)
        self.assertEqual(len(rejected), 8)
        self.receipt('negatives',compiled_observable_rejections=rejected)

    def test_08_live_and_frozen_input_corruption_controls(self):
        read = Path.read_bytes
        for index, relative in enumerate(source.INPUTS):
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: read(p) + b'\n' if p == path else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root, self.out, self.installed)
            fixture = self.out / ('before-%02d' % index)
            with patch.object(Path, 'read_bytes', lambda p: read(p) + b'\n' if p == fixture else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root, self.out, self.installed)

    def test_08b_object_word_binding_pool_and_first_slot_controls(self):
        source.checked_object(self.obj)
        text, functions, relocations = source.parse_object(self.obj)
        f = functions[source.FUNCTION]
        for i in range(346):
            bad = bytearray(text)
            bad[f['value'] + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad = dict(relocations)
            bad[f['value'] + at] = [('R_MIPS_LO16', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.rodata': (0, b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        slot = (self.out / 'selected-slot.bin').read_bytes()
        for i in range(346):
            bad = bytearray(slot)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.expected_inputs(self.values, bytes(bad))

    def test_11_literal_prefix_full_state_and_effective_control(self):
        class Boundary(Exception):
            pass
        class Prefix(guest.RectangleOracle):
            def execute(model, instruction):
                if any(pc >= source.ENTRY + 205 * 4 for pc in model.visits):
                    raise Boundary()
                super().execute(instruction)
        count = 0
        for flip, inset, tint, phase in itertools.product(range(4), (0, 1), (0, 1), (0, 8)):
            memory, args = guest.fixture(flip=flip, tint=tint, offsets=(17, inset, -5),
                animation=129, frame=127, speed=255, timestep=255)
            states = []
            for words in (self.truth, self.words):
                model = Prefix(words, memory, args, phase=phase)
                with self.assertRaises(Boundary):
                    model.run()
                states.append((guest.base.edge.state(model), model.fcsr, model.condition))
            self.assertEqual(*states)
            bad = list(self.words)
            bad[2] ^= 1 << 16
            model = Prefix(bad, memory, args, phase=phase)
            with self.assertRaises(Boundary):
                model.run()
            self.assertNotEqual(states[0], (guest.base.edge.state(model), model.fcsr, model.condition))
            count += 1
        self.receipt('prefix', paired_states=count, literal_words=205,
            boundary='0x15096068', six_later_private_stack_home_accesses_unresolved=True)

    def test_12_first_prediction_and_installed_scope(self):
        expected = source.expected_inputs(self.values, (self.out / 'selected-slot.bin').read_bytes())
        actual = expected['conker/build/conker.us.elf']
        before = self.values['conker/build/conker.us.elf']
        self.assertEqual(len(actual), len(before))
        self.assertEqual(sum(a != b for a, b in zip(before, actual)), 21)
        if self.installed:
            audit = source.audit(self.root, self.out)
            self.assertEqual(audit['functions'], 6057)
            self.assertEqual(audit['changed'], [source.FUNCTION])
        else:
            source.freeze(self.root, self.out)


if __name__ == '__main__':
    unittest.main()
