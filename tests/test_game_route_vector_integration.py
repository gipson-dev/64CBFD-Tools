"""Real caller interfaces, actual Make commands and installed route-vector audit."""
import csv
import itertools
import json
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_vector_integration as source
from tools.tests import test_game_route_vector_saved_roles as previous
from tools.tests import test_game_actor_route_snap as parent

vector = previous.vector
SITES = (0x150874B4, 0x15087744, 0x15087954, 0x1508799C, 0x15088E58)
WINDOWS = ((0x150874A4, 0x150874F0), (0x15087738, 0x1508775C),
           (0x15087940, 0x1508796C), (0x15087980, 0x150879B4))


class WindowStop(Exception):
    pass


class WindowOracle(previous.FullTraceOracle):
    def __init__(self, words, memory, entry, stop, site, helpers, phase, poison):
        self.stop, self.site, self.poison = stop, site, poison
        self.vector_returned = self.stopped = False
        self.sqrt_count = 0
        self.saved_call_state = None
        super().__init__(words, memory, (), phase, entry, connected=helpers)

    def record_call(self, target):
        if target == source.ENTRY:
            self.calls.append((target, self.arguments(4)))
            self.saved_call_state = ([self.r[i] for i in (*range(16, 24), 28, 29, 30, 31)], self.f[20:])
        elif target == parent.CUBIC:
            self.calls.append((target, self.arguments(3)))
        else:
            raise AssertionError('Unknown window helper: ' + hex(target))

    def execute(self, word):
        if self.current_pc == self.site + 8 and not self.vector_returned:
            if self.saved_call_state != ([self.r[i] for i in (*range(16, 24), 28, 29, 30, 31)], self.f[20:]):
                raise AssertionError('Vector changed its caller saved state')
            self.vector_returned = True
            self.r[2] = self.poison
        if self.current_pc == self.stop:
            self.stopped = True
            raise WindowStop
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 4:
            value = vector.base.floating(self.f[word >> 11 & 31])
            if not math.isfinite(value) or value < 0:
                raise ValueError('Retail window sqrt is qualified only for finite nonnegative inputs')
            self.f[word >> 6 & 31] = vector.base.bits(math.sqrt(value))
            self.sqrt_count += 1
            return
        return super().execute(word)


class RouteVectorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.installed = source.verify(cls.root, cls.out) == 'after'
        with source.historical_view(cls.root, cls.out):
            cls.prediction = source.predict(cls.root, cls.out)
            cls.values = source.freeze(cls.root, cls.out)
            cls.obj = cls.out / 'primary-no-unroll.o'
            cls.raw, cls.bindings = source.source.checked(cls.obj)
            cls.normalized, cls.moved = source.layout.normalize(cls.raw, cls.bindings)
            data, functions = source.prior.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
            cls.words = list(struct.unpack_from('>83I', data, functions[source.FUNCTION]['value']))
            cls.row = json.loads((cls.out / 'qualification.json').read_text())
            cls.row['saved'] = list(map(tuple, cls.row['saved']))
        cls.image = source.raw_read(cls.root / 'conker/build/conker.us.elf') if cls.installed else source.raw_read(cls.out / 'after-elf')
        cls.rom = source.raw_read(cls.root / 'conker/conker.us.bin')
        cls.normal = list(struct.unpack_from('>83I', cls.image, source.prior.elf_slot_offset(cls.image, source.ENTRY, 332)))
        cls.truth = list(struct.unpack_from('>83I', cls.rom, source.ROM))
        cls.helpers = {}
        for entry, count in parent.HELPERS.items():
            if entry == source.ENTRY:
                continue
            at = source.prior.elf_slot_offset(cls.image, entry, count * 4)
            body = list(struct.unpack_from('>%dI' % count, cls.image, at))
            if body != list(struct.unpack_from('>%dI' % count, cls.rom, entry - 0x14FD2B50)):
                raise ValueError('Changed linked vector caller helper: ' + hex(entry))
            cls.helpers.update(zip(range(entry, entry + count * 4, 4), body))

    def run(self, result=None):
        with source.historical_view(self.root, self.out):
            return super().run(result)

    def receipt(self, name, **values):
        values['production_installed'] = self.installed
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_01_words_and_bindings = previous.RouteVectorSavedRoleTests.test_01_all_words_bindings_origins_and_file_free_layout
    test_02_full_memory_and_access_order = previous.RouteVectorSavedRoleTests.test_02_full_memory_access_order_private_homes_and_ABI
    test_03_fired_memory_prefixes = previous.RouteVectorSavedRoleTests.test_03_fired_memory_prefixes_and_invariant_roles
    test_04_native32_and_controls = previous.RouteVectorSavedRoleTests.test_04_native32_and_effective_semantic_controls
    test_05_private_padder = previous.RouteVectorSavedRoleTests.test_05_actual_private_mixed_profile_padder
    test_06_raw_and_recipe_controls = previous.RouteVectorSavedRoleTests.test_06_raw_words_bindings_and_recipe_fail_closed
    test_07_frozen_inputs = previous.RouteVectorSavedRoleTests.test_07_inputs_and_production_remain_frozen
    test_08_independent_rebases = previous.RouteVectorSavedRoleTests.test_08_independent_GNU_rebases_and_guest_aliases

    def test_09_actual_Make_first_prediction_and_installed_audit(self):
        self.assertEqual(self.prediction['after'], source.AFTER)
        self.assertEqual(self.prediction['changed_ELF_bytes'], 243)
        self.assertEqual(source.SYMBOL_ORDERS, ())
        plan = json.loads((self.out / 'make-shadow.json').read_text())
        self.assertEqual(plan['actual_expanded_Make_commands'], 7)
        self.assertEqual((plan['primary_owner_flag_count'], plan['normal_override_flag_count']), (1, 0))
        self.assertTrue(plan['all73_primary_functions_equal'])
        self.assertTrue(plan['original_four_GLOBAL_ASM_bodies_preserved'])
        if self.installed:
            self.assertEqual(source.audit(self.root, self.out)['changed_ELF_bytes'], 243)
        else:
            self.assertEqual(source.verify(self.root, self.out), 'before')
        before = self.values['conker/build/conker.us.elf']
        span = bytearray(self.rom[source.ROM:source.ROM + 332])
        span[0] ^= 1
        with self.assertRaises(ValueError):
            source.predicted_image(before, span)
        corrupted = bytearray(before)
        corrupted[-1] ^= 1
        with self.assertRaises(ValueError):
            source.predicted_image(bytes(corrupted), self.rom[source.ROM:source.ROM + 332])

    def test_10_whole_Game_direct_sites_and_current_caller_boundary(self):
        opcode = (3 << 26) | ((source.ENTRY >> 2) & 0x3FFFFFF)
        found = []
        with (self.root / 'conker/retail_layout.us.txt').open() as stream:
            for row in csv.DictReader(stream):
                if row['section'] != 'game':
                    continue
                for at in range(int(row['address'], 0), int(row['end'], 0), 4):
                    if struct.unpack_from('>I', self.rom, at - 0x14FD2B50)[0] == opcode:
                        found.append((row['function'], at))
        self.assertEqual(found, [('func_15087350', at) for at in SITES[:4]] + [('func_15088D58', SITES[4])])
        rows = {row[1]: row[2] for row in source.prior.symbol_rows(self.image)}
        self.assertEqual(rows['func_15087350'][1:3], (0x15087350, 12))
        self.assertEqual(rows['func_15088D58'][1:3], (0x15088D58, 472))
        self.assertEqual(rows[source.FUNCTION][1:3], (source.ENTRY, 332))
        self.receipt('call-sites', whole_Game_scan=True, retail_direct_calls=found,
                     live_C_caller_words=118, other_caller_production_stub_words=3,
                     unknown_indirect_interfaces_and_whole_other_caller_not_claimed=True)

    def test_11_complete_live_C_caller_with_real_linked_helpers(self):
        caller_entry = 0x15088D58
        caller = list(struct.unpack_from('>118I', self.image, source.prior.elf_slot_offset(self.image, caller_entry, 472)))
        self.assertEqual(caller, list(struct.unpack_from('>118I', self.rom, caller_entry - 0x14FD2B50)))
        count = 0
        for actor, steps, mode, angle, alias, phase in itertools.product(
                (0, 3), (0, 2, 7), (0, 128), (0, 0x8000, 0xFFFF), (0, 1), (0, 8)):
            p = (actor, steps, -1, mode, angle, 0x43360B61, 0)
            memory, args = parent.fixture(p, alias)
            expected, calls = parent.reference(memory, args, angle)
            results = []
            for body in (self.words, self.normal):
                helpers = dict(self.helpers)
                helpers.update(zip(range(source.ENTRY, source.ENTRY + 332, 4), body))
                m = parent.RouteOracle(caller, memory, args, angle, helpers, phase).run()
                self.assertEqual((parent.public(m.memory), m.calls), (parent.public(expected), calls))
                self.assertEqual(m.f[20:], m.saved_f)
                for register in (*range(16, 24), 28, 29, 30, 31):
                    self.assertEqual(m.r[register], m.before[register])
                results.append(m)
            self.assertEqual(results[0].memory, results[1].memory)
            count += 1
        self.assertEqual(count, 144)
        self.receipt('connected-C-caller', cases=count, actual_C_caller_words=118, vector_words=83,
                     other_real_linked_helper_words=472, only_atan_is_bounded_provider=True,
                     complete_ordinary_memory_and_saved_ABI_equal=True)

    def test_12_four_retail_only_windows_real_delay_slots_and_consumers(self):
        memory, _ = vector.fixture()
        probe = WindowOracle([0x46000004], memory, 0x16001000, 0x16001008,
                             0x16002000, {}, 0, 0)
        probe.f[0] = 0x41C80000
        probe.execute(0x46000004)
        self.assertEqual((probe.f[0], probe.sqrt_count), (0x40A00000, 1))
        for invalid in (0xBF800000, 0x7FC12345, 0x7F800000):
            probe.f[0], probe.sqrt_count = invalid, 0
            with self.assertRaises(ValueError):
                probe.execute(0x46000004)
            self.assertEqual((probe.f[0], probe.sqrt_count), (invalid, 0))
        count = 0
        for index, (entry, stop) in enumerate(WINDOWS):
            window = list(struct.unpack_from('>%dI' % ((stop - entry) // 4 + 1), self.rom, entry - 0x14FD2B50))
            for mask, pattern, speed, alias, phase, poison in itertools.product(
                    (0, 5, 15), (0, 2, 242), (0x3F000000, 0xBF000000), (0, 1), (0, 8), (0, 0xDEADBEEF)):
                memory, args = vector.fixture(mask, pattern, speed=speed)
                sp = vector.STACK + phase
                record = sp + 0x184 if alias else args[0]
                if alias:
                    memory.update({record + i: memory[args[0] + i] for i in range(132)})
                x, y, z = sp + 0x184, sp + 0x174, sp + 0x164
                vector.put(memory, sp + 0xDC, vector.base.bits(.25))
                initial = dict(memory)
                if index in (2, 3):
                    vector.put(initial, record, vector.base.bits(float(index - 2)))
                expected, _ = vector.reference(initial, (record, x, y, z))
                results = []
                for body in (self.words, self.normal):
                    helpers = dict(self.helpers)
                    helpers.update(zip(range(source.ENTRY, source.ENTRY + 332, 4), body))
                    m = WindowOracle(window, memory, entry, stop, SITES[index], helpers, phase, poison)
                    m.r[16] = m.r[17] = record
                    m.r[19], m.r[20], m.r[24] = x, z, 1
                    m.f[0] = vector.base.bits(.25)
                    with self.assertRaises(WindowStop):
                        m.run()
                    self.assertTrue(m.stopped and m.vector_returned)
                    self.assertEqual(m.sqrt_count, 1 if index == 0 else 0)
                    self.assertEqual([call for call in m.calls if call[0] == source.ENTRY],
                                     [(source.ENTRY, (record, x, y, z))])
                    for output in (x, y, z):
                        self.assertEqual([vector.read(m.memory, output + i * 4) for i in range(4)],
                                         [vector.read(expected, output + i * 4) for i in range(4)])
                    if index == 0:
                        dx = vector.base.sub(vector.read(expected, x + 8), vector.read(expected, x + 4))
                        dz = vector.base.sub(vector.read(expected, z + 8), vector.read(expected, z + 4))
                        magnitude = vector.base.add(vector.base.mul(dx, dx), vector.base.mul(dz, dz))
                        self.assertEqual(vector.read(m.memory, sp + 0x19C),
                                         vector.base.bits(math.sqrt(vector.base.floating(magnitude))))
                    else:
                        fraction = vector.read(expected, sp + 0xDC if index == 1 else record + 8)
                        wanted = parent.spline(tuple(vector.read(expected, x + i * 4) for i in range(4)), fraction)
                        self.assertEqual(m.f[0], wanted)
                    results.append(m)
                self.assertEqual((results[0].memory, results[0].calls), (results[1].memory, results[1].calls))
                count += 1
        self.assertEqual(count, 576)
        self.receipt('retail-only-windows', fired_windows=count, all_four_sites=True,
                     actual_argument_and_delay_slot_instructions=True, real_cubic_consumer_words=49,
                     V0_poison_values=[0, 0xDEADBEEF], stack_output_record_alias=True,
                     fired_finite_nonnegative_sqrt_s_model=True,
                     sqrt_model_domain_rejections=3,
                     bounded_windows_not_full_unrecovered_caller_or_production_gameplay=True)

    def test_13_mixed_installation_stages_fail_closed(self):
        checkpoint = source.source.checkpoint
        read = checkpoint.raw_read
        after = source.expected_inputs(self.root, self.out)
        for path in source.AFTER:
            mapped = {str((self.root / name).resolve()): data for name, data in after.items()}
            mapped[str((self.root / path).resolve())] = source.raw_read(self.out / ('before-%02d' % list(source.INPUTS).index(path)))
            with patch.object(checkpoint, 'raw_read', side_effect=lambda p: mapped.get(str(p.resolve()), read(p))), \
                    self.assertRaises(ValueError):
                source.verify(self.root, self.out)
        self.receipt('stage-controls', mixed_stage_rejections=3, first_prediction_pins_unchanged=True)


if __name__ == '__main__':
    unittest.main()
