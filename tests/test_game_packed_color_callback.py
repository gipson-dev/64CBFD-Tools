"""Uninstalled packed RGB recovery: bounded semantics are not a byte-match claim."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_color_callback as source
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_actor_mask_scan_match import MaskOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle, rounded, converted_angle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_packed_record_updater_installed as previous

RECORD, DELTA, TIMES, COLORS = 0x20000, 0x800BE9E4, 0x800A6E00, 0x800A6E0C
TABLE = bytes.fromhex('ff28231e19140f00ff280000 ffff00ffff00ff8000ff8000ff0000ff0000c000008000005a5a5a5a5a5a000000000000')


def fixture(intensity=127, countdown=1, delta=1, width=-32768, ramp=1, record=RECORD):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 512)}
    memory.update({record + i: (i * 13 + 0xC5) & 255 for i in range(0x34)})
    memory.update({TIMES + i: value for i, value in enumerate(TABLE)})
    put(memory, record + 0x1F, intensity, 1)
    put(memory, record + 0x24, countdown, 1)
    put(memory, record + 0x26, ramp, 1)
    put(memory, record + 0x14, width, 2)
    put(memory, DELTA, delta)
    return memory


def reference(original, record=RECORD):
    memory = dict(original)
    value = read(memory, record + 0x1F, 1)
    if read(memory, record + 0x24, 1):
        if value != 255:
            value = min(signed((value + (read(memory, DELTA) << 5)) & 0xFFFFFFFF), 255)
            put(memory, record + 0x1F, value, 1)
    elif value:
        value = max(signed((value - (read(memory, DELTA) << 4)) & 0xFFFFFFFF), 0)
        put(memory, record + 0x1F, value, 1)
    if not read(memory, record + 0x24, 1) and value == 0:
        return memory, 1
    extent = read(memory, record + 0x14, 2) + read(memory, DELTA) * 10
    put(memory, record + 0x16, extent, 2)
    put(memory, record + 0x14, extent, 2)
    countdown = read(memory, record + 0x24, 1)
    phase = countdown + 8 if countdown else read(memory, record + 0x1F, 1) // 32
    start = read(memory, record + 0x26, 1)
    for index in range(start, start + 8):
        current = read(memory, TIMES + index, 1)
        if phase < current:
            continue
        denominator = read(memory, TIMES + index - 1, 1) - current
        assert denominator != 0, 'finite ramp fixture required'
        weight = rounded(float(phase - current) / denominator)
        complement = rounded(1.0 - weight)
        for channel in range(3):
            previous = float(read(memory, COLORS + index * 3 - 3 + channel, 1))
            current_color = float(read(memory, COLORS + index * 3 + channel, 1))
            color = rounded(rounded(previous * weight) + rounded(current_color * complement))
            put(memory, record + 0x1C + channel, converted_angle(color), 1)
        break
    return memory, 0


class ColorOracle(MaskOracle):
    def __init__(self, words, memory, record=RECORD, fcsr=0):
        super().__init__(words, memory, entry=source.ENTRY, arguments=(record,))
        self.fcsr = self.initial_fcsr = fcsr

    def execute(self, word):
        op, rs, fn = word >> 26, word >> 21 & 31, word & 63
        if op == 17 and (rs in (2, 6) or (rs == 16 and fn == 36)):
            return AreaOracle.execute(self, word)
        return super().execute(word)

    def record_call(self, target):
        raise AssertionError(('unexpected leaf call', target))

    def run(self):
        result = super().run()
        assert self.fcsr == self.initial_fcsr, 'conversion control state leaked'
        return result


class PackedColorCandidateTests(unittest.TestCase):
    def test_scope_recipes_fingerprints_and_fail_closed_match_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(len(set(source.PATHS.values())), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        before = 'extern s32 D_800BE9E4;\ns32 func_1516E8CC() {\n    return 0;\n}\nvoid other(void) { }\n'
        for body in source.candidates().values():
            self.assertNotIn('volatile', body)
            result = source.recovered_owner(before, body)
            self.assertIn('extern u8 D_800A6E00[];', result)
            self.assertTrue(result.endswith('void other(void) { }\n'))
            with self.assertRaises(ValueError):
                source.recovered_owner(result)
        for words, differences, diagnostics in ((247, 0, ''), (248, 1, ''), (248, 0, 'warning')):
            with self.assertRaisesRegex(ValueError, 'not a direct match'):
                source.require_direct_match(dict(words=words, differences=differences, diagnostics=diagnostics))


class PackedColorRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out, 'semantics')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>248I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_06_all_original_801_archive_fingerprints = previous.PackedRecordUpdaterInstalledTests.test_04_all_original_801_archive_fingerprints

    def test_01_raw_nonmatch_rejected_all_neighbors_and_tables_fixed(self):
        self.assertEqual((self.row['words'], self.row['differences'], self.row['diagnostics']), (241, 234, ''))
        with self.assertRaises(ValueError):
            source.require_direct_match(self.row)
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
        self.assertEqual(self.rom[0x24B8C0:0x24B8F0], TABLE)
        elf = (self.out / 'before-elf').read_bytes()
        at = elf_slot_offset(elf, TIMES, 48)
        self.assertEqual(elf[at:at + 48], TABLE)
        self.receipt('owner', words=241, retail_words=248, differences=234, installed=False,
            unchanged_neighbors=len(new[1]) - 1, pools_and_relative_relocations_fixed=True,
            table_bytes=48, table_ROM=0x24B8C0, FCSR_model='bounded conversions, not hardware emulation')

    def test_02_all_intensity_bytes_live_wrap_aliases_and_finite_ramps(self):
        count = 0
        deltas = (0, 1, 2, 255, 256, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000000, 0x7FFFFFFF, 0x01000000, 0x87654321)
        for i in range(1024):
            for record in (RECORD, DELTA - 0x1C, DELTA - 0x14):
                memory = fixture(i & 255, (i // 256) * 85, deltas[(i // 7) % len(deltas)],
                    (i * 65521) & 65535, 1 if i & 1 else 9, record)
                expected = reference(memory, record)
                for words in (self.words, self.truth):
                    model = ColorOracle(words, memory, record).run()
                    self.assertEqual((model.memory, model.r[2]), expected)
                count += 1
        for intensity, countdown in ((0, 0), (255, 1)):
            model = ColorOracle(self.truth, fixture(intensity, countdown)).run()
            reads = [e for e in model.events if e[0] == 'R' and e[1] == DELTA]
            self.assertEqual(len(reads), 0 if countdown == 0 else 1)
        # Full live 256 becomes a stored zero byte but must not finish early.
        model = ColorOracle(self.words, fixture(240, 0, 0xFFFFFFFF)).run()
        self.assertEqual((model.r[2], model.memory[RECORD + 0x1F]), (0, 0))
        self.receipt('semantics', paired_finite_cases=count, all_intensity_bytes=True,
            counter_values=[0, 85, 170, 255], signed_wrap_and_extent_truncation=True,
            delta_RGB_and_extent_aliases=True, bounded_table_starts=[1, 9],
            raw_and_retail_memory_return_equal=True, raw_fault_order_not_qualified=True,
            arbitrary_table_indices_and_full_hardware_FCSR_not_claimed=True)

    def test_03_effective_compiled_negatives(self):
        controls = {
            'early-byte': source.SELECTED.replace('value = (s32)((u32)value -', 'value = (u8)((u32)value -'),
            'wrong-fade': source.SELECTED.replace('D_800BE9E4 << 4', 'D_800BE9E4 << 3'),
            'lost-height': source.SELECTED.replace('    *(s16 *)(record + 0x16) = value;\n', ''),
            'wrong-phase': source.SELECTED.replace('record[0x24] + 8', 'record[0x24] + 9'),
            'swapped-weights': source.SELECTED.replace('color[-3] * weight', 'color[-3] * complement').replace('color[0] * complement', 'color[0] * weight'),
        }
        counts = {}
        for name, body in controls.items():
            words = source.measure(self.root, self.out, 'negative-' + name, body)[1]
            failures = 0
            for i in range(256):
                memory = fixture(i, (i // 32) * 5, 0xFFFFFFFF if i & 1 else 1, i * 257, 1)
                model = ColorOracle(words, memory).run()
                failures += (model.memory, model.r[2]) != reference(memory)
            self.assertGreater(failures, 0, name)
            counts[name] = failures
        self.receipt('negative-controls', effective_compiled_controls=counts)

    def test_04_all_52_live_inputs_and_capture_corruptions(self):
        for key, relative in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), source.BASELINE[key], key)
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('unchanged-inputs', frozen_and_live_inputs=52, capture_flips_rejected=52,
            production_source_ELF_guards_progress_and_data_fixed=True)

    def test_05_native32_finite_conversion_cases_against_guest_results(self):
        rows = []
        for i in range(1024):
            args = (i & 255, (i // 256) * 85,
                (0, 1, 2, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000)[(i // 5) % 6],
                (i * 65521) & 65535, 1 if i & 1 else 9)
            expected, result = reference(fixture(*args))
            guest = ColorOracle(self.truth, fixture(*args)).run()
            self.assertEqual((guest.memory, guest.r[2]), (expected, result))
            fields = (result, expected[RECORD + 0x1F], read(expected, RECORD + 0x14, 2),
                read(expected, RECORD + 0x16, 2), *(expected[RECORD + 0x1C + c] for c in range(3)))
            rows.append('{' + ','.join('0x%XU' % (x & 0xFFFFFFFF) for x in (*args, *fields)) + '}')
        tables = ('u8 D_800A6E00[] = {' + ','.join(map(str, TABLE[:12])) + '};\n' +
            'u8 D_800A6E0C[] = {' + ','.join(map(str, TABLE[12:])) + '};\n')
        harness = '''typedef unsigned char u8; typedef signed short s16;
typedef unsigned int u32; typedef signed int s32; typedef float f32;
s32 D_800BE9E4;
''' + tables + source.SELECTED + '''
static u32 cases[][12] = {''' + ',\n'.join(rows) + '''};
static int check(void) {
    unsigned int i, j; u8 record[0x34] __attribute__((aligned(4))); u32 *row;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        row = cases[i];
        for (j = 0; j < sizeof(record); j++) record[j] = j * 13 + 0xC5;
        record[0x1F] = row[0]; record[0x24] = row[1]; record[0x26] = row[4];
        D_800BE9E4 = (s32)row[2];
        *(s16 *)(record + 0x14) = row[3]; *(s16 *)(record + 0x16) = (s16)0xE3F0;
        if ((u32)func_1516E8CC(record) != row[5] || record[0x1F] != row[6] ||
            (unsigned short)*(s16 *)(record + 0x14) != row[7] ||
            (unsigned short)*(s16 *)(record + 0x16) != row[8] ||
            record[0x1C] != row[9] || record[0x1D] != row[10] || record[0x1E] != row[11]) return 1;
    }
    return 0;
}
void _start(void) { int result = check(); __asm__ volatile("int $0x80" : : "a"(1), "b"(result)); __builtin_unreachable(); }
'''
        path = self.out / 'native-finite.c'
        path.write_text(harness)
        for optimization in ('-O2', '-O0'):
            binary = self.out / ('native-' + optimization[1:])
            command = ['cc', '-m32', optimization, '-std=c11', '-fno-strict-aliasing',
                '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-o', str(binary), str(path)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        self.receipt('native', cases_per_profile=1024, profiles=['-O2', '-O0'],
            original_guest_results_checked=True, finite_table_domain_only=True,
            arbitrary_float_to_unsigned_casts_and_host_gameplay_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
