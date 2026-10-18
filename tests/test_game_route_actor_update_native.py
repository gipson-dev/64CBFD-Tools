"""Native32/UBSan, connected guest corpus and rejected storage-lifetime controls."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_native as native
from tools.experiments import game_route_actor_update_storage as storage
from tools.tests import test_game_route_actor_update as guest


class RouteActorUpdateNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / native.BUILD
        cls.values = native.source.source.freeze(cls.root, cls.out)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>604I', cls.rom, guest.ROM))
        obj = cls.root / native.source.BUILD / 'qualified-cursor.o'
        native.source.checked(obj)
        image, functions = native.source.source.prior.link_owner(cls.root, cls.out, obj, native.source.source.OWNER)
        f = functions[native.source.source.FUNCTION]
        cls.candidate = list(struct.unpack_from('>594I', image, f['value']))
        cls.helpers = {}
        image = cls.values['conker/build/conker.us.elf']
        for address, count in guest.HELPERS.items():
            at = native.source.source.prior.elf_slot_offset(image, address, count * 4)
            words = list(struct.unpack_from('>%dI' % count, image, at))
            if words != list(struct.unpack_from('>%dI' % count, cls.rom, address - 0x14FD2B50)):
                raise ValueError('Changed connected real helper: ' + hex(address))
            cls.helpers.update(zip(range(address, address + count * 4, 4), words))
        cls.result = native.qualify(cls.root, cls.out)

    compare = guest.RouteActorUpdateTests.compare

    def receipt(self, name, **values):
        values.update(raw_model_SHA256=native.source.RAW_SHA)
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_three_positive_profiles_and_five_effective_controls(self):
        r = self.result
        self.assertEqual(r['cases_per_positive_build'], 553)
        self.assertFalse(r['smoke_only'])
        self.assertEqual(r['helper_source_SHA256'], native.HELPER_SHA)
        self.assertEqual(r['raw_target_SHA256'], native.source.RAW_SHA)
        self.assertTrue(r['all_five_effect_gates_required'])
        for name in ('O0', 'O2', 'O2-UBSAN'):
            self.assertEqual(r['exits'][name], 0)
        for name in native.controls():
            self.assertIn(r['exits'][name], (21, 22, 23))
        self.assertEqual(r['effective_controls'], 5)
        self.assertEqual(r['outside_cast_domain_sanitizer_control_exit'], -4)
        self.assertTrue(r['float_cast_overflow_checked'])
        for name in r['exits']:
            command = json.loads((self.out / ('native-' + name + '.compile.json')).read_text())
            self.assertEqual((command['exit'], command['diagnostics']), (0, ''))
            for flag in ('-m32', '-mstackrealign', '-fno-strict-aliasing', '-ffp-contract=off', '-fexcess-precision=standard'):
                self.assertIn(flag, command['command'])
            if name != 'O0' and name != 'O2':
                self.assertIn('-fsanitize=undefined', command['command'])
                self.assertIn('-fsanitize=float-cast-overflow', command['command'])
        self.receipt('native', cases_per_build=553, positive_profiles=3, effective_controls=5,
            no_UBSan_traps_or_provider_misses_accepted_in_positive_or_semantic_runs=True,
            separate_outside_domain_control_fires_SIGILL=True)

    def test_02_same_553_inputs_connect_full_retail_and_raw_C(self):
        constants = native.static_constants(self.root)
        for row in native.cases():
            memory, args = native.fixture(row, constants)
            self.compare(memory, args, effect=row.get('effect', 0))
        self.receipt('connected-corpus', guest_cases=553, caller_words=604, raw_words=594,
            real_helper_words=len(self.helpers), independent_ordered_float_reference=True,
            same_inputs_as_native_not_a_new_disjoint_corpus=True)

    def test_03_native_unit_preserves_selected_body_and_actual_constant_bytes(self):
        text = (self.out / 'native-O2.c').read_text()
        a, b = native.function_span(text, native.source.source.FUNCTION)
        body = native.strip_externs(native.source.selected())
        lo, hi = native.function_span(body, native.source.source.FUNCTION)
        self.assertEqual(text[a:b], body[lo:hi])
        values = native.static_constants(self.root)
        self.assertNotEqual(guest.read(values, 0x8009D9E0), guest.bits(.05))
        self.assertEqual(guest.read(values, 0x8009D9E0), guest.bits(.06))
        for at, n in ((0x8009D9E0, 4), (0x8009D9E4, 4), (0x8009D9E8, 4),
                      (0x8009D9F0, 8), (0x8009D9F8, 4), (0x8009D9FC, 4)):
            offset = native.source.source.prior.elf_slot_offset(self.values['conker/build/conker.us.elf'], at, n)
            self.assertEqual(bytes(values[at + i] for i in range(n)),
                self.values['conker/build/conker.us.elf'][offset:offset + n])
        self.assertIn('address(0x800CC310U,0)', text)
        self.assertEqual(len(native.REGIONS), 12)
        self.receipt('unit', source_body_unchanged_except_external_variable_declarations=True,
            actual_frozen_ELF_constants=True, public_aliases_in_one_mapped_arena=True)

    def test_04_fail_closed_memory_and_helper_controls(self):
        memory, _ = native.fixture({}, native.static_constants(self.root))
        with patch.object(native, 'schema', return_value=[(guest.RECORDS, 4, False)] * 2):
            with self.assertRaisesRegex(ValueError, 'Overlapping'):
                native.patches(memory, 0)
        damaged = dict(memory)
        damaged[0x12345] = 0
        with self.assertRaisesRegex(ValueError, 'Unmapped native public address'):
            native.patches(damaged, 0)
        guest.put(memory, guest.TABLE, 0x12345)
        with self.assertRaisesRegex(ValueError, 'Unmapped native pointer'):
            native.patches(memory, 0)
        with patch.dict(native.HELPER_SHA, {'func_15088F30': 'wrong'}):
            with self.assertRaisesRegex(ValueError, 'Changed native real-helper source'):
                native.translation_unit(self.root, rows=[{}])
        self.receipt('wire-controls', overlapping_schema_rejected=True, unmapped_public_byte_rejected=True,
            unmapped_pointer_rejected=True, helper_source_mutation_rejected=True)

    def test_05_ten_storage_screens_keep_ordinary_semantics_only(self):
        out = self.root / storage.BUILD
        count = cases = 0
        for group, factory in storage.GROUPS.items():
            rows = json.loads((out / (group + '-screens.json')).read_text())
            forms = dict(factory())
            self.assertEqual(len(rows), len(forms))
            for row in rows:
                name = row['name']
                self.assertEqual((row['neighbors'], row['diagnostics']), (72, ''))
                self.assertEqual((out / (name + '.c')).read_text(), native.source.source.recovered_owner(
                    self.values['conker/src/game/generated_B3020.c'].decode(), forms[name]))
                obj = out / (name + '.o')
                text, definitions, _ = native.source.source.parse_object(obj)
                d = definitions[native.source.source.FUNCTION]
                self.assertEqual(hashlib.sha256(text[d['value']:d['value'] + d['size']]).hexdigest(), row['raw_sha256'])
                image, functions = native.source.source.prior.link_owner(self.root, out, obj, native.source.source.OWNER)
                f = functions[native.source.source.FUNCTION]
                words = list(struct.unpack_from('>%dI' % (f['size'] // 4), image, f['value']))
                for index, mode, phase in itertools.product((0, 1), (0, 1, 128), (0, 8)):
                    memory, args = native.fixture(dict(index=index, mode=mode), native.static_constants(self.root))
                    self.compare(memory, args, phase, bodies=(self.retail, words))
                    cases += 1
                count += 1
        self.assertEqual((count, cases), (10, 120))
        self.receipt('storage', screens=count, additional_guest_cases=cases, new_selected_points=0,
            no_qualifier_or_narrowed_input_domain_invented=True, full_private_or_argument_home_proof_not_claimed=True)

    def test_06_production_inputs_remain_frozen(self):
        native.source.source.freeze(self.root, self.out)
        native.source.source.freeze(self.root, self.root / storage.BUILD)
        native.source.checked(self.root / native.source.BUILD / 'qualified-cursor.o')
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        a, b = native.function_span(owner, native.source.source.FUNCTION)
        self.assertEqual(owner[a:b], 's32 func_15087350() {\n    return 0;\n}')


if __name__ == '__main__':
    unittest.main()
