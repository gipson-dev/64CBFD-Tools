"""Complete installed-image prediction and readonly input/layout gates."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_sequence as source
from tools.tests import frame_sequence_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class FrameSequenceInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def check_live(self):
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),103)
        for key,relative in source.PATHS.items():
            self.assertEqual((self.root/relative).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        return expected

    def test_01_whole_image_all_inputs_readonly_guards_and_protected_layout(self):
        expected=self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),516)
        at=elf_slot_offset(data,source.ENTRY,740)
        self.assertEqual(data[at:at+740],(self.out/'predicted-slot.bin').read_bytes())
        rows={r[1]:r for r in symbol_rows(data)}
        old={r[1]:r for r in symbol_rows(before)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted=list(old[name][2][1:])
            if name==source.FUNCTION:wanted[1]=740
            self.assertEqual(row[2][1:],tuple(wanted),name)
        self.assertEqual(rows['func_1501878C'][2][1:3],(0x1501878C,12))
        self.assertEqual((self.root/source.PATHS['guards']).read_bytes(),(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=516,slot_bytes=740,extent=[12,740],
            new_guards=0,guard_manifest_readonly=True,metadata_serialization_bytes=16,metadata_exclusions=0,
            unchanged_other_inputs=101,protected_layout=layout,installed_upstream_still_stubbed=True,after=checkpoint.AFTER),indent=2)+'\n')

    def test_02_every_live_input_and_code_callee_upstream_metadata_control(self):
        read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises((AssertionError,ValueError)):self.check_live()
        path=self.root/source.PATHS['elf']
        data=read(path)
        offsets=[elf_slot_offset(data,address,4) for address in
            (source.ENTRY,source.ENTRY+44,source.ENTRY+328,source.ENTRY+736,0x1501878C,0x15094EA0,0x151EFEB8,0x150A7A48)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_1501878C','D_80043B40','D_80088894','D_800884D4','D_80084190','D_80084930'):
            row=rows[name]
            offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_exact_successor_and_both_fixture_stages(self):
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
