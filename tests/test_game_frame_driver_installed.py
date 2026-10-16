"""Require the complete frame-driver prediction, guard append and protected image."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_driver as source
from tools.tests import frame_driver_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class FrameDriverInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def check_live(self):
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),104)
        for key,path in source.PATHS.items():
            actual=(self.root/path).read_bytes()
            wanted=expected.get(key,(self.out/('before-'+key)).read_bytes())
            self.assertTrue(actual==wanted,key)
        return expected

    def test_01_complete_image_guard_prefix_neighbors_and_protected_layout(self):
        expected=self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),1301)
        at=elf_slot_offset(data,source.ENTRY,1648)
        self.assertEqual(data[at:at+1648],(self.out/'predicted-slot.bin').read_bytes())
        rows={r[1]:r for r in symbol_rows(data)};old={r[1]:r for r in symbol_rows(before)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted=list(old[name][2][1:])
            if name==source.FUNCTION:wanted[1]=1648
            self.assertEqual(row[2][1:],tuple(wanted),name)
        self.assertTrue(expected['guards'].startswith((self.out/'before-guards').read_bytes()))
        source.checked_manifest(expected['guards'],self.out,self.out/'qualified.o')
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=1301,body_bytes=1644,slot_bytes=1648,extent=[12,1648],new_guards=55,
            inserted_delay_nops=1,metadata_serialization_bytes=111,metadata_exclusions=0,
            unchanged_other_inputs=101,guard_history_exact_prefix=True,protected_layout=layout),indent=2)+'\n')

    def test_02_every_live_input_code_helpers_caller_and_metadata_controls(self):
        read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises((AssertionError,ValueError)):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,address,4) for address in (source.ENTRY,source.ENTRY+0x234,
            source.ENTRY+0x4DC,source.ENTRY+0x5B0,source.ENTRY+1644,0x150186D0,0x15019130,0x15019BB8,
            0x15019E60,0x15094EA0,0x151EFEB8,0x150A7A48)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_15019BB8','func_15019E60','D_800BE9D0','D_800D9B90',
                'D_800D9F60','D_800D1890','D_80088B60','osPiGetCmdQueue','D_800AA98C','D_80089970',
                'D_800BEB9C','func_1501A680'):
            row=rows[name];offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_exact_three_input_successor_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root)
        read=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            for stage in ('before','after'):
                path=self.out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                    with self.assertRaisesRegex(AssertionError,'fixture'):
                        if stage=='before':checkpoint.previous_input(current,relative,self.root)
                        else:checkpoint.freeze_after(self.root)


if __name__=='__main__':unittest.main()
