"""Whole first projection image/source/pool-binding prediction and exact data."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_overlay_projection as source
from tools.experiments import game_overlay_projection_installation as installation
from tools.tests import overlay_projection_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
from tools.check_game_data_layout import audit_layout


class OverlayProjectionInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/installation.BUILD
        source.freeze(cls.root,cls.out);cls.expected=installation.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),156)
        for key,path in source.PATHS.items():self.assertTrue((self.root/path).read_bytes()==self.wanted[key],key)

    def test_01_first_whole371byte_prediction_120_words_pool_binding_and_exact_data(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(installation.digest(self.expected[key]),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual((self.out/'prelink-prediction.elf').read_bytes(),data)
        at=elf_slot_offset(data,source.ENTRY,480)
        self.assertEqual(data[at:at+480],(self.out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+480])
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+480],data[at:at+480])),369)
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),371)
        self.assertEqual(installation.SERIALIZATION,())
        old=canonical_symbols(before);wanted=old.copy();original=next(k for k in old if k[0]==source.FUNCTION)
        self.assertEqual(original[2],12);successor=list(original);successor[2]=480
        wanted[original]-=1;wanted[tuple(successor)]+=1;self.assertEqual(+wanted,canonical_symbols(data))
        at=elf_slot_offset(data,0x800A7280,12);self.assertEqual(data[at:at+12],source.POOL[:12])
        for address,length in ((0x1517F08C,788),(0x1517F564,444),(0x150A7960,232)):
            at=elf_slot_offset(data,address,length);self.assertEqual(before[at:at+length],data[at:at+length])
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,changed_ELF_bytes=371,
            code_bytes=369,extent_bytes=2,metadata_exclusions=0,symbol_reordering=0,words=120,new_guards=0,
            pool_bytes_reused=12,new_runtime_data_bytes=0,unchanged_input_entries=153,protected_layout=layout),indent=2)+'\n')

    def test_02_all156_inputs_extent_metadata_pool_words_and_binding_fail_closed(self):
        self.check_live();read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(AssertionError):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,va,4) for va in (source.ENTRY,source.ENTRY+0x190,source.ENTRY+476,0x800A7280,0x800A7284,0x800A7288)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION,source.POOL_SYMBOL):offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_only_exact_successor_and_all_three_before_after_fixture_pairs(self):
        with patch.object(inverse,'checkpoint',checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__=='__main__':unittest.main()
