"""Whole first aggregate prediction, unchanged data/guards and exact successors."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_color_channel_aggregate as source
from tools.experiments import game_color_channel_aggregate_installation as installation
from tools.tests import color_channel_aggregate_checkpoint as checkpoint
from tools.tests import color_overlay_draw_checkpoint as successor
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
from tools.check_game_data_layout import audit_layout


class ColorChannelAggregateInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/installation.BUILD
        source.freeze(cls.root,cls.out);cls.expected=installation.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),148)
        for key,path in source.PATHS.items():
            self.assertTrue(successor.previous_input((self.root/path).read_bytes(),path,self.root)==self.wanted[key],key)

    def test_01_whole_first_prediction_only_44word_body_extent_and_exact_data(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(installation.digest(self.expected[key]),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual((self.out/'prelink-prediction.elf').read_bytes(),data)
        at=elf_slot_offset(data,source.ENTRY,176)
        self.assertEqual(data[at:at+176],(self.out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+176])
        code=sum(a!=b for a,b in zip(before[at:at+176],data[at:at+176]));self.assertGreater(code,0)
        changed=sum(a!=b for a,b in zip(before,data));self.assertEqual(changed,code+1)
        old=canonical_symbols(before);wanted=old.copy();original=next(k for k in old if k[0]==source.FUNCTION)
        self.assertEqual(original[2],12);successor=list(original);successor[2]=176
        wanted[original]-=1;wanted[tuple(successor)]+=1;self.assertEqual(+wanted,canonical_symbols(data))
        for entry,length in ((0x1517EE40,192),(0x1517EF00,172),(0x151E8214,164)):
            position=elf_slot_offset(data,entry,length);self.assertEqual(before[position:position+length],data[position:position+length])
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=changed,code_bytes=code,extent_bytes=1,metadata_reordering_bytes=0,
            metadata_exclusions=0,raw_words=44,direct=True,guards=0,extent=[12,176],
            guard_manifest_byte_identical=True,unchanged_other_inputs=146,protected_layout=layout),indent=2)+'\n')

    def test_02_all148_inputs_and_metadata_definitions_fail_closed(self):
        self.check_live();read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()
        path=self.root/source.PATHS['elf'];data=read(path)
        offsets=[elf_slot_offset(data,va,4) for va in (source.ENTRY,source.ENTRY+0x20,source.ENTRY+0x40,source.ENTRY+172,0x1517EF00,0x151E8214)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION,'func_1517EF00','D_80082FA0','D_800DDDC8'):
                offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad=bytearray(data);bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else read(p)):
                with self.assertRaises(AssertionError):self.check_live()

    def test_03_only_exact_successor_and_both_before_after_fixture_pairs(self):
        with patch.object(inverse,'checkpoint',checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__=='__main__':unittest.main()
