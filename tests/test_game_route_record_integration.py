"""Pre/installed route setup qualification with actual Make and strict image gates."""
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_record_integration as source
from tools.tests import test_game_route_record_reload as core

previous = core.previous


class RouteRecordIntegrationTests(core.RouteRecordReloadTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.installed = source.verify(cls.root, cls.out) == 'after'
        with source.historical_view(cls.root, cls.out):
            cls.prediction = source.predict(cls.root, cls.out)
            cls.values = source.freeze(cls.root, cls.out)
            cls.obj = cls.out / 'qualified.o'
            cls.raw, cls.bindings = source.source.checked(cls.obj)
            cls.normalized, cls.moved = source.layout.normalize(cls.raw, cls.bindings)
            data, functions = source.prior.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
            cls.words = list(struct.unpack_from('>160I', data, functions[source.FUNCTION]['value']))
            cls.row = json.loads((cls.out / 'qualification.json').read_text())
        cls.image = source.raw_read(cls.root / 'conker/build/conker.us.elf') if cls.installed else source.raw_read(cls.out / 'after-elf')
        cls.truth = list(struct.unpack_from('>160I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.anchors = {row[1]: row[2][1] for row in source.prior.symbol_rows(cls.image)}
        cls.normal = source.layout.relocate(cls.normalized, cls.moved, cls.anchors)
        cls.helpers = {}
        for entry, count in previous.HELPERS.items():
            at = source.prior.elf_slot_offset(cls.image, entry, count * 4)
            body = cls.image[at:at + count * 4]
            if body != cls.values['conker/conker.us.bin'][entry - 0x14FD2B50:entry - 0x14FD2B50 + count * 4]:
                raise ValueError('Changed actual linked setup helper')
            cls.helpers.update(zip(range(entry, entry + count * 4, 4), struct.unpack('>%dI' % count, body)))

    def run(self, result=None):
        with source.historical_view(self.root, self.out):
            return super().run(result)

    def receipt(self, name, **values):
        raw = {'guest', 'five-neighbors', 'capture', 'private-boundary', 'later-roles',
               'native32', 'caller', 'corruptions', 'wire-controls'}
        values.update(production_installed=self.installed,
                      proof_model='raw C diagnostic' if name in raw else 'normalized C or integration',
                      matching_credit=1 if self.installed and name == 'integration' else 0)
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_15_actual_Make_first_prediction_and_target_extent(self):
        self.assertEqual(self.prediction['after'], source.AFTER)
        self.assertEqual(self.prediction['metadata_order_groups'], 0)
        plan = json.loads((self.out / 'make-shadow.json').read_text())
        self.assertEqual(plan['actual_expanded_Make_commands'], 7)
        self.assertEqual((plan['primary_owner_flag_count'], plan['normal_override_flag_count']), (1, 0))
        self.assertTrue(plan['all73_primary_functions_equal'])
        self.assertTrue(plan['original_four_GLOBAL_ASM_bodies_preserved'])
        self.assertEqual(self.image[source.prior.elf_slot_offset(self.image, source.ENTRY, 640):
                                    source.prior.elf_slot_offset(self.image, source.ENTRY, 640) + 640],
                         self.values['conker/conker.us.bin'][source.ROM:source.ROM + 640])
        rows = {row[1]: row[2] for row in source.prior.symbol_rows(self.image)}
        self.assertEqual(rows[source.FUNCTION][1:3], (source.ENTRY, 640))
        before = self.values['conker/build/conker.us.elf']
        span = bytearray(self.values['conker/conker.us.bin'][source.ROM:source.ROM + 640])
        span[0] ^= 1
        with self.assertRaises(ValueError):
            source.predicted_image(before, span)
        bad = bytearray(before)
        bad[-1] ^= 1
        with self.assertRaises(ValueError):
            source.predicted_image(bytes(bad), self.values['conker/conker.us.bin'][source.ROM:source.ROM + 640])
        self.receipt('integration', actual_make_commands=7, source_target_bytes=640,
            first_prediction_reproduced=True, changed_ELF_bytes=self.prediction['changed_ELF_bytes'],
            only_target_code_and_symbol_extent_changed=True, metadata_order_groups=0)

    def test_16_installed_whole_image_addresses_other_bodies_and_game_data(self):
        if self.installed:
            result = source.audit(self.root, self.out)
            self.assertEqual(result['changed_ELF_bytes'], self.prediction['changed_ELF_bytes'])
            self.assertEqual((result['functions'], result['other_bodies_fixed']), (6057, 6056))
            self.assertEqual((result['game_data']['bytes'], result['game_data']['owner_count'],
                              result['game_data']['different_bytes']), (189088, 720, 0))
        else:
            self.assertEqual(source.verify(self.root, self.out), 'before')

    def test_17_mixed_source_guard_image_stages_fail_closed(self):
        checkpoint = source.checkpoint
        read = checkpoint.raw_read
        after = source.expected_inputs(self.root, self.out)
        for name in source.AFTER:
            mapped = {str((self.root / path).resolve()): data for path, data in after.items()}
            mapped[str((self.root / name).resolve())] = source.raw_read(
                self.out / ('before-%02d' % list(source.INPUTS).index(name)))
            with patch.object(checkpoint, 'raw_read', side_effect=lambda p: mapped.get(str(p.resolve()), read(p))), \
                    self.assertRaises(ValueError):
                source.verify(self.root, self.out)
        self.receipt('stage-controls', mixed_stages_rejected=3, immutable_prediction_pins_preserved=True)


if __name__ == '__main__':
    unittest.main()
