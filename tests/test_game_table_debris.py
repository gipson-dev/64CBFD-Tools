"""Qualify table-debris semantics while rejecting the unresolved retail frame/lifetimes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_table_debris as source
from tools.tests import game_table_debris_oracle as guest
from tools.tests import game_table_debris_native as native
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def controls():
    return {
        'narrow-lookup': source.SELECTED.replace('func_1518C900(entry->kind)', 'func_1518C900((u8)entry->kind)'),
        'signed-lookup': source.SELECTED.replace('func_1518C900(entry->kind)', 'func_1518C900((s16)entry->kind)'),
        'cached-kind': source.SELECTED.replace('    s32 asset;', '    s32 kind;\n    s32 asset;').replace(
            '        asset = func_1518C900(entry->kind);\n        packet.kind = entry->kind;',
            '        kind = entry->kind;\n        asset = func_1518C900(kind);\n        packet.kind = kind;'),
        'wrong-position-type': source.SELECTED.replace('entry->offset[0] + originX', '*(s32 *)&entry->offset[0] + originX'),
        'missing-absolute': source.SELECTED.replace('fabsf(entry->offset[1])', 'entry->offset[1]'),
        'wrong-horizontal': source.SELECTED.replace('entry->offset[2] * horizontal', 'entry->offset[2] * vertical'),
        'wrong-rotation': source.SELECTED.replace('packet.rotation[0] * rotationScale', 'packet.rotation[1] * rotationScale'),
        'wrong-second-range': source.SELECTED.replace('* 10.0f - 5.0f', '* 9.0f - 5.0f'),
        'reset-fixed-packet': source.SELECTED.replace('        asset = func_1518C900(entry->kind);',
            '        packet.lifetime = 60;\n        asset = func_1518C900(entry->kind);'),
        'reset-reserved-byte': source.SELECTED.replace('        packet.asset = asset;',
            '        packet.reserved44[0] = 0;\n        packet.asset = asset;'),
        'wide-actor-store': source.SELECTED.replace('actor[0x6E] = 1;', '*(s32 *)(actor + 0x6C) = 1;'),
    }


class TableDebrisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>158I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, mode=0, rotation=0, phase=0, streams=None):
        models = []
        for words in streams or (self.truth, self.words):
            model = guest.TableDebrisOracle(words, memory, args, phase, mode, rotation).run()
            frame = (-words[0]) & 65535
            home = model.packet_pointer - (guest.STACK + phase - frame)
            expected = guest.reference(memory, args, mode, rotation, phase, frame, home)
            self.assertEqual((model.calls, model.full_packets, guest.public(model.memory)), expected)
            models.append(model)
        for model in models[1:]:
            self.assertEqual((model.calls, model.packets, guest.public(model.memory)),
                (models[0].calls, models[0].packets, guest.public(models[0].memory)))
        return models

    def test_01_shape_neighbors_actual_padder_and_rejected_installation(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['diagnostics'], self.row['pool_bytes']), (158, 248, 121, '', 0))
        self.assertEqual(self.row['raw_sha256'], '7c11a8d372b5d02912bf3e11053e88e2223aba5746f8f446e0cb33e2788f1436')
        with self.assertRaisesRegex(ValueError, 'installation rejected'):
            source.qualify(self.root, self.out)
        obj, diagnostics = source.build.compile_owner(self.root, self.out, (self.out / 'before-edge_wrapper_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: {at - f['value']: rows for at, rows in o[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        padded = self.out / 'unqualified-padded.s'
        padded.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER, word_patches_path=self.out / 'before-guards'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded.with_suffix('.o')), str(padded)], check=True, capture_output=True)
        data, functions = source.build.link_owner(self.root, self.out, padded.with_suffix('.o'), source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(f['size'], 632)
        self.assertEqual(list(struct.unpack_from('>158I', data, f['value'])), self.words)
        self.receipt('shape', words=158, frame=248, retail_frame=232, real_differences=121,
            packet_home=152, retail_packet_home=132, neighbors_unchanged=8, pools_fixed=True,
            padder_does_not_fix_differences=True, installation_rejected=True)

    def test_02_complete_sequences_all_packet_bytes_and_provider_lifetimes(self):
        visits, cases = set(), 0
        for pattern, flags, context, mode, rotation, phase in itertools.product(range(3), (0, 0xABCDEF81, 0xFFFFFFFF),
                (0, 0x87654321), range(6), (0, 2, 5), (0, 8)):
            memory, args = guest.fixture(self.rom, pattern, flags, context)
            models = self.compare(memory, args, mode, rotation, phase)
            visits |= models[0].visits
            cases += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 632, 4)))
        self.receipt('semantics', cases=cases, runs=cases * 2, all_158_original_instructions_visited=True,
            initialized_bytes=90, full_96_bytes_per_stream_home=True, private_frames_not_equal=True,
            unsigned_halfword_then_late_byte_kind=True, live_tables_and_snapshot_coefficients=True)

    def test_03_effective_compiled_semantic_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            failed = False
            for mode in (0, 1, 2, 3, 5):
                memory, args = guest.fixture(self.rom, 1)
                try:
                    self.compare(memory, args, mode, 2, streams=(self.truth, words))
                except AssertionError:
                    failed = True
                    break
            self.assertTrue(failed, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence)

    def test_04_native32_framed_initialized_and_provider_seeded_bytes(self):
        harness = self.out / 'native-harness.c'
        harness.write_text(native.fixtures(self.rom))
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.TYPES + native.declarations() + body)
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error'] if valid else ['-Wno-unused-but-set-variable']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            (self.out / ('native-' + name + '-diagnostics.txt')).write_text(result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 29)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1024, separate_translation_units=True, selected_UBSan=True,
            initialized_90_and_provider_seeded_holes=True, effective_negatives=len(controls()), exits=exits,
            no_native_initial_indeterminate_byte_or_guest_private_home_claim=True)

    def test_05_all_live_frozen_input_and_manifest_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        target = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        self.receipt('scope', inputs=len(source.PATHS), all_live_frozen=True, all_capture_corruptions_effective=True,
            production_source_guards_ELF_and_reference_unchanged=True)

    def test_06_original_three_input_caller_and_missing_current_window(self):
        entry, rom, size = 0x1511C76C, 0x149C1C, 44
        original = self.rom[rom:rom + size]
        image = (self.out / 'before-elf').read_bytes()
        current = image[elf_slot_offset(image, entry, size):][:size]
        self.assertEqual(current, b'\0' * size)
        self.assertNotEqual(current, original)
        class StopCaller(guest.TableDebrisOracle):
            def record_call(model, target):
                if target == source.ENTRY:
                    model.entry_args = model.arguments(3)
                    raise guest.edge.CallBoundary
                return super().record_call(target)
        cases = 0
        for data, phase, actor in itertools.product((original,), (0, 8), (guest.ACTOR, guest.ACTOR + 64)):
            memory, _ = guest.fixture(self.rom)
            guest.put(memory, guest.STACK + phase + 0x48, actor)
            model = StopCaller(list(struct.unpack('>11I', data)), memory, (0, 0x12345678, 0x87654321), phase=phase, entry=entry)
            model.r[1] = model.r[2] = 1
            with self.assertRaises(guest.edge.CallBoundary):
                model.run()
            self.assertEqual(model.entry_args, (actor, 255, 0))
            cases += 1
        self.receipt('caller', original_captures=cases, current_window_zero_filled_bytes=size,
            actor_from_home_flags_255_context_zero=True, no_current_caller_or_gameplay_claim=True)

    def test_07_actual_consumer_allocator_and_full_packet_copies(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for address, rom, size in ((source.SUBMIT, 0x196094, 104), (guest.prior.ALLOCATOR, 0x194F18, 112)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        cases = 0
        for pattern, phase, mode, fail in itertools.product(range(3), (0, 8), (0, 4), (False, True)):
            memory, args = guest.fixture(self.rom, pattern)
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(6 * 0x100)})
            for words in (self.truth, self.words):
                model = guest.TableDebrisOracle(words, memory, args, phase, mode, connected=connected, fail=fail).run()
                frame = (-words[0]) & 65535
                home = model.packet_pointer - (guest.STACK + phase - frame)
                calls, packets, expected = guest.reference(memory, args, mode, phase=phase, frame=frame, home=home)
                copies = []
                for i, packet in enumerate(packets):
                    if not struct.unpack_from('>I', packet, 0x40)[0] or fail and (i + 1) % 3 == 0:
                        continue
                    record = 0x30000 + i * 0x100
                    guest.put(expected, record, 0x10, 1)
                    guest.put(expected, record + 1, args[2], 1)
                    guest.put(expected, record + 12, args[1], 1)
                    for j, byte in enumerate(packet):
                        expected[record + 0x90 + j] = byte
                    copies.append((record + 0x90, packet))
                self.assertEqual((model.calls, model.full_packets, model.copies, guest.public(model.memory)), (calls, packets, copies, expected))
                cases += 1
        self.receipt('connected', runs=cases, actual_consumer_allocator_words=54, full_96_byte_copies=True,
            zero_asset_and_every_third_allocation_failure=True, first_residue_per_stream_home=True,
            RNG_lookup_heap_registration_and_bcopy_bounded_or_opaque=True)


if __name__ == '__main__':
    unittest.main()
