"""Require the complete first point-slot provider image and unchanged neighbors."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_point_slot_provider as source
from tools.tests import point_slot_provider_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class PointSlotProviderInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def test_01_whole_image_all_inputs_guard_history_and_protected_layout(self):
        expected = source.expected_inputs(self.root,self.out)
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        for key,relative in source.PATHS.items():
            self.assertEqual((self.root/relative).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest)
        before,data = (self.out/'before-elf').read_bytes(),expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a != b for a,b in zip(before,data)),220)
        at = elf_slot_offset(data,source.ENTRY,284)
        self.assertEqual(data[at:at+284],(self.out/'predicted-slot.bin').read_bytes())
        old = {r[1]:r for r in symbol_rows(before)}
        rows = {r[1]:r for r in symbol_rows(data)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted = list(old[name][2][1:])
            if name == source.FUNCTION:
                wanted[1] = 284
            self.assertEqual(row[2][1:],tuple(wanted),name)
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        layout = audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=220,slot_bytes=284,
            extent=[12,284],new_guards=33,metadata_serialization_bytes=0,metadata_exclusions=0,
            unchanged_other_inputs=97,protected_layout=layout,after=checkpoint.AFTER),indent=2)+'\n')

    def test_02_every_live_input_code_neighbor_and_metadata_control(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_image_all_inputs_guard_history_and_protected_layout()
        path = self.root/source.PATHS['elf']
        data = rb(path)
        offsets = [elf_slot_offset(data,address,4) for address in
            (source.ENTRY,source.ENTRY+128,source.ENTRY+280,0x150948C0,0x15094AB8,0x15095D34)]
        rows = {r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_150948C0','D_80089974'):
            row = rows[name]
            offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_image_all_inputs_guard_history_and_protected_layout()

    def test_03_exact_successor_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current = (self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            for stage in ('before','after'):
                path = self.out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError,'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
