"""The complete first unguarded view-overlay image and unchanged live inputs."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_view_overlay_pass as source
from tools.tests import view_overlay_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class ViewOverlayInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.expected=source.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),107)
        for key,path in source.PATHS.items():self.assertTrue((self.root/path).read_bytes()==self.wanted[key],key)

    def test_01_complete_image_extent_unchanged_guards_and_protected_layout(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),324)
        at=elf_slot_offset(data,source.ENTRY,408)
        self.assertEqual(data[at:at+408],(self.out/'predicted-slot.bin').read_bytes())
        rows={r[1]:r for r in symbol_rows(data)};old={r[1]:r for r in symbol_rows(before)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted=list(old[name][2][1:])
            if name==source.FUNCTION:wanted[1]=392
            self.assertEqual(row[2][1:],tuple(wanted),name)
        self.assertEqual((self.root/source.PATHS['guards']).read_bytes(),(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=324,body_bytes=392,slot_bytes=408,extent=[12,392],new_guards=0,
            metadata_serialization_bytes=0,metadata_exclusions=0,unchanged_other_inputs=105,
            guard_history_byte_identical=True,protected_layout=layout),indent=2)+'\n')

    def test_02_all107_live_input_and_target_caller_data_metadata_controls(self):
        self.check_live();read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,address,4) for address in (source.ENTRY,source.ENTRY+0x6C,
            source.ENTRY+0xDC,source.ENTRY+0x164,source.ENTRY+388,source.ENTRY+404,0x15018B98,0x150198FC)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_1501878C','D_800BE628','D_800DC2A0'):
            row=rows[name];offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_only_exact_successor_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root);read=Path.read_bytes
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
