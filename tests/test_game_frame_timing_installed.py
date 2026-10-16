"""Full timing ELF prediction including six named symbol/string permutations."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_timing_update as source
from tools.tests import frame_timing_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as previous
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
from tools.check_game_data_layout import audit_layout


class FrameTimingInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out);cls.expected=source.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),109)
        for key,path in source.PATHS.items():self.assertTrue((self.root/path).read_bytes()==self.wanted[key],key)

    def test_01_complete_image_extent_metadata_and_protected_layout(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),755)
        at=elf_slot_offset(data,source.ENTRY,768)
        self.assertEqual(data[at:at+768],(self.out/'predicted-slot.bin').read_bytes())
        structural=(self.out/'structural-prediction.elf').read_bytes()
        self.assertEqual(canonical_symbols(structural),canonical_symbols(data))
        old=canonical_symbols(before);wanted=old.copy()
        original=next(k for k in old if k[0]==source.FUNCTION)
        successor=list(original);successor[2]=764
        wanted[original]-=1;wanted[tuple(successor)]+=1
        self.assertEqual(+wanted,canonical_symbols(data))
        self.assertEqual((self.root/source.PATHS['guards']).read_bytes(),(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=755,code_bytes=580,extent_bytes=2,metadata_serialization_bytes=173,
            metadata_groups=6,body_bytes=764,slot_bytes=768,extent=[12,764],new_guards=0,
            metadata_exclusions=0,unchanged_other_inputs=107,guard_history_byte_identical=True,
            protected_layout=layout),indent=2)+'\n')

    def test_02_all109_inputs_and_target_caller_constant_metadata_controls(self):
        self.check_live();read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,a,4) for a in (source.ENTRY,source.ENTRY+0xD0,source.ENTRY+0x174,
            source.ENTRY+0x2E4,source.ENTRY+764,0x1501908C,0x800968D0)]
        names={name for group,_,_ in source.SERIALIZATION for name in group}|{source.FUNCTION,'func_1501905C'}
        for row in symbol_rows(data):
            if row[1] in names:offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_exact_successor_and_both_fixture_stages(self):
        with patch.object(previous,'checkpoint',checkpoint):
            previous.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__=='__main__':unittest.main()
