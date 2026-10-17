"""Whole first direct helper prediction, three owners, unchanged guards and data."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_color_state_submit as source
from tools.experiments import game_color_state_submit_installation as installation
from tools.tests import color_state_submit_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
from tools.check_game_data_layout import audit_layout


class ColorStateSubmitInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/installation.BUILD
        source.freeze(cls.root,cls.out);cls.expected=installation.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),144)
        for key,path in source.PATHS.items():self.assertTrue((self.root/path).read_bytes()==self.wanted[key],key)

    def test_01_complete215byte_prediction_all48_words_three_owners_and_data(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(installation.digest(self.expected[key]),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636));self.assertEqual(sum(a!=b for a,b in zip(before,data)),215)
        self.assertEqual((self.out/'prelink-prediction.elf').read_bytes(),data)
        at=elf_slot_offset(data,source.ENTRY,192)
        self.assertEqual(data[at:at+192],(self.out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+192])
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+192],data[at:at+192])),165)
        old=canonical_symbols(before);wanted=old.copy();original=next(k for k in old if k[0]==source.FUNCTION)
        self.assertEqual(original[2],12);successor=list(original);successor[2]=192
        wanted[original]-=1;wanted[tuple(successor)]+=1;self.assertEqual(+wanted,canonical_symbols(data))
        self.assertEqual(len(installation.SERIALIZATION),2)
        for entry,length in ((0x1501DAAC,876),(0x1501D348,1892),(0x15172CA8,128)):
            position=elf_slot_offset(data,entry,length);self.assertEqual(before[position:position+length],data[position:position+length])
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=215,code_bytes=165,extent_bytes=1,metadata_bytes=49,exact_symbol_groups=2,
            metadata_exclusions=0,raw_words=48,direct=True,guards=0,extent=[12,192],
            guard_manifest_byte_identical=True,unchanged_other_inputs=140,
            two_signed_byte_caller_prototypes_only=True,protected_layout=layout),indent=2)+'\n')

    def test_02_all144_inputs_and_every_metadata_definition_fail_closed(self):
        self.check_live();read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,va,4) for va in (source.ENTRY,source.ENTRY+0x30,source.ENTRY+188,0x1501DAAC,0x15172CA8)]
        names={source.FUNCTION}|{name for row in installation.SERIALIZATION for name in row[0]}
        for row in symbol_rows(data):
            if row[1] in names:offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_only_exact_successor_and_all_four_before_after_fixture_pairs(self):
        with patch.object(inverse,'checkpoint',checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__=='__main__':unittest.main()
