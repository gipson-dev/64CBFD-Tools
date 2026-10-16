"""Require the complete 208-byte prediction, including the closed metadata pair."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_point_transform as source
from tools.tests import packed_point_transform_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class PackedPointTransformInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def test_01_whole_image_all_inputs_guard_history_and_protected_layout(self):
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        for key,relative in source.PATHS.items():
            self.assertEqual((self.root/relative).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),208)
        at=elf_slot_offset(data,source.ENTRY,220)
        self.assertEqual(data[at:at+220],(self.out/'predicted-slot.bin').read_bytes())
        rows={r[1]:r for r in symbol_rows(data)}
        old={r[1]:r for r in symbol_rows(before)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted=list(old[name][2][1:])
            if name==source.FUNCTION:
                wanted[1]=220
            self.assertEqual(row[2][1:],tuple(wanted),name)
        guards=(self.root/source.PATHS['guards']).read_bytes()
        self.assertTrue(guards.startswith((self.out/'before-guards').read_bytes()))
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=208,slot_bytes=220,
            extent=[12,220],new_guards=2,metadata_serialization_bytes=40,metadata_exclusions=0,
            unchanged_other_inputs=97,protected_layout=layout,after=checkpoint.AFTER),indent=2)+'\n')

    def test_02_every_live_input_code_neighbor_and_metadata_control(self):
        rb=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_image_all_inputs_guard_history_and_protected_layout()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        offsets=[elf_slot_offset(data,address,4) for address in (source.ENTRY,source.ENTRY+48,source.ENTRY+52,
            source.ENTRY+216,0x1509499C,0x15095D34)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_151AF388','D_80089974'):
            row=rows[name]
            offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data)
            bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_image_all_inputs_guard_history_and_protected_layout()

    def test_03_exact_successor_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root)
        rb=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            for stage in ('before','after'):
                path=self.out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                    with self.assertRaisesRegex(AssertionError,'fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__=='__main__':
    unittest.main()
