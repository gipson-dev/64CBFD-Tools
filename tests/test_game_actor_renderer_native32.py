"""Full portable renderer, real SDK macros and explicit native callback/reference models."""
import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_actor_renderer_native32 as native
from tools.tests.test_game_row_destination_fill import START


class GameActorRendererNative32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-renderer-native32-test'
        cls.out.mkdir(exist_ok=True)
        cls.records = native.vectors()
        cls.paths = dict(source=native.matching.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')

    def execute(self, name, body=native.matching.SELECTED, optimize='-O2', records=None):
        source = self.out / (name + '.c')
        binary = source.with_suffix('')
        source.write_text(native.source(self.root, body, self.records if records is None else records) + START)
        result = subprocess.run(['cc', '-m32', optimize, '-std=c99', '-fno-strict-aliasing',
            '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffreestanding', '-nostdlib', '-static',
            '-fno-pie', '-no-pie', '-fno-stack-protector', '-ffp-contract=off', '-Wall', '-Wextra',
            '-Werror', '-Wno-unused-parameter', '-Wno-unused-function', str(source), '-o', str(binary)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        result = subprocess.run([str(binary)], capture_output=True, timeout=30)
        detail = list(struct.unpack('<7I', result.stderr)) if len(result.stderr) == 28 else result.stderr.hex()
        return result.returncode, detail

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_native32_actual_SDK_two_profiles(self):
        self.assertEqual(len(self.records), 330)
        for name, profile in (('selected-o2', '-O2'), ('selected-o0', '-O0')):
            result, detail = self.execute(name, optimize=profile)
            self.assertEqual(result, 0, (name, detail))
        self.receipt('native', cases_per_profile=330, profiles=2, executions=660,
            real_SDK_macros=True, full_commands_cursor_callback_ABI_and_actor_config_footprint=True,
            live_table_mask_page_and_history_mutations=True, independent_endian_explicit_reference=True,
            full_width_view_fixture_privately_mapped=True, real_helpers_or_N64_private_stack_claim=False)

    def test_02_every_shift_boundary_and_unsigned_maximum_count(self):
        counts = [native.little_read(memory, native.proof.S['D_800C4778'] + 14, 2)
            for memory, _, _, _ in self.records if native.proof.S['D_800C4778'] + 14 in memory]
        for count in (0, 1, 4, 31, 32, 33, 63, 64, 65535):
            self.assertIn(count, counts)
        extremes = [record for record in self.records if record[3]]
        self.assertEqual(len(extremes), 3)
        result, detail = self.execute('maximum-count', records=extremes)
        self.assertEqual(result, 0, detail)
        self.receipt('boundaries', native_reexecuted_max_count_cases=3,
            unsigned_count=65535, wrapped_parts_through_65534=True,
            all_skip_zero_count_command_call_equivalence=True,
            no_guest_fault_or_order_claim_from_metamorphic_case=True)

    def test_03_fresh_effective_complete_native_controls(self):
        controls = (
            ('wrong-fog', '0x400000', 'G_FOG'),
            ('wrong-primitive', '0xF2, 0, primitiveR', '0, 0xF2, primitiveR'),
            ('wrong-tail', 'actor[0x2FE] = 1;', 'actor[0x2FE] = 0;'),
            ('wrong-light-argument', 'actor + 0x1DD, flags', 'actor + 0x1DC, flags'))
        results = []
        for name, old, new in controls:
            self.assertIn(old, native.matching.SELECTED)
            result, detail = self.execute(name, native.matching.SELECTED.replace(old, new))
            self.assertIn(result, (10, 12, 15), (name, result, detail))
            results.append(dict(name=name, result=result, detail=detail))
        self.receipt('negatives', effective_complete_native_controls=len(results), results=results)

    def test_04_pointer_provenance_preserves_scalar_collisions(self):
        self.assertEqual(native.proof.OUTPUT, 0x20000)
        self.assertEqual(native.expression(0x20000), '0x00020000U')
        self.assertIn('output + 1', native.expression(0x20000, pointer=True))
        for value in (native.proof.LIGHTS, 0x27000, 0x27800):
            self.assertEqual(native.expression(value), '0x%08XU' % value)
            self.assertNotEqual(native.expression(value, pointer=True), native.expression(value))
        self.assertIn('matrixInput', native.expression(0x26FC8, pointer=True))
        self.assertIn('+ 0x38', native.expression(0x27000, pointer=True))

    def test_05_production_and_prior_baselines_unchanged(self):
        hashes = json.loads((self.out / 'baseline.json').read_text())
        previous = self.root / 'conker/build/game-actor-renderer-schedule-test'
        self.assertEqual(hashes, json.loads((previous / 'baseline.json').read_text()))
        for name, path in self.paths.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), hashes[name])
            self.assertEqual(data, (self.out / ('before-' + name)).read_bytes())
            self.assertEqual(data, (previous / ('before-' + name)).read_bytes())
        self.assertIn(native.matching.recovery.ORIGINAL, (self.root / native.matching.SOURCE).read_text())
        self.receipt('unchanged', baseline=hashes, source_ELF_guards_progress_rodata_unchanged=True,
            consumer_target_not_installed=True)


if __name__ == '__main__':
    unittest.main()
