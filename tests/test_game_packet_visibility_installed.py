"""Whole installed image, all inputs, protected data and strict successor fixtures."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_visibility as source
from tools.tests import packet_visibility_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols
from tools.check_game_data_layout import audit_layout


class PacketVisibilityInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def test_01_complete_image_every_input_and_protected_layout(self):
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        for key,relative in source.PATHS.items():
            self.assertEqual((self.root/relative).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),expected['elf']
        structural=source.slot_expected_image(before,(self.out/'before-retail_rom').read_bytes())
        self.assertEqual(len(before),len(data))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),551)
        self.assertEqual(sum(a!=b for a,b in zip(structural,data)),157)
        self.assertEqual(canonical_symbols(structural),canonical_symbols(data))
        at=elf_slot_offset(data,source.ENTRY,516)
        self.assertEqual(data[at:at+516],(self.out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+516])
        rows={r[1]:r for r in symbol_rows(data)}
        self.assertEqual(rows[source.FUNCTION][2][1:3],(source.ENTRY,516))
        self.assertEqual(expected['guards'],source.proposed_guards((self.out/'before-guards').read_bytes()))
        self.assertTrue(expected['guards'].startswith((self.out/'before-guards').read_bytes()))
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=551,slot_bytes=516,
            extent=[28,516],guards=7,prior_guard_history_fixed=True,other_ELF_bytes_and_95_inputs_fixed=True,
            metadata_serialization_bytes=157,metadata_exclusions=0,protected_layout=layout,after=checkpoint.AFTER),indent=2)+'\n')

    def test_02_live_input_code_callee_and_metadata_corruptions(self):
        rb=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_every_input_and_protected_layout()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        positions=[elf_slot_offset(data,a,4) for a in (source.ENTRY,source.ENTRY+0x48,source.ENTRY+512,
            source.ENTRY+516,0x150958B0,0x15095A90,0x15095D34)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'D_800D2C80','.L1514EAE8_game_data','D_800D2C70'):
            row=rows[name]
            positions.extend((row[0],row[0]+4,row[0]+8,row[3]))
        for at in positions:
            bad=bytearray(data)
            bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_every_input_and_protected_layout()

    def test_03_strict_successor_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root)
        rb=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            self.assertEqual(checkpoint.previous_input(current,'unowned',self.root),current)
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
