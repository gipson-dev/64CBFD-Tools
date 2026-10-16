"""Complete installed ELF, guard history, protected layout and exact successor."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_projected_packet_draw as source
from tools.tests import projected_packet_draw_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class ProjectedPairInstalledTests(unittest.TestCase):
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
        self.assertEqual(len(before),len(data))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),490)
        rows={r[1]:r for r in symbol_rows(data)}
        for name,entry,rom,size in ((source.FUNCTION,source.ENTRY,source.ROM,336),('func_1509563C',source.PROJECT,0xC2AEC,292)):
            at=elf_slot_offset(data,entry,size)
            self.assertEqual(data[at:at+size],(self.out/'before-retail_rom').read_bytes()[rom:rom+size])
            self.assertEqual(rows[name][2][1:3],(entry,size))
        self.assertEqual(expected['guards'],source.proposed_guards((self.out/'before-guards').read_bytes()))
        self.assertTrue(expected['guards'].startswith((self.out/'before-guards').read_bytes()))
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=490,slot_bytes=628,
            draw_extent=[12,336],project_extent=[12,292],draw_guards=0,project_guards=10,
            prior_guard_history_fixed=True,every_other_ELF_byte_and_93_inputs_fixed=True,
            metadata_exclusions=0,protected_layout=layout,after=checkpoint.AFTER),indent=2)+'\n')

    def test_02_all_live_input_and_code_callee_metadata_corruptions(self):
        rb=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_every_input_and_protected_layout()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        positions=[elf_slot_offset(data,a,4) for a in (source.ENTRY,source.ENTRY+332,source.ENTRY+336,
            source.PROJECT,source.PROJECT+0xD8,source.PROJECT+288,source.DRAW,0x15095060,0x1516D980)]
        rows={r[1]:r for r in symbol_rows(data)}
        for name in (source.FUNCTION,'func_1509563C'):
            row=rows[name]
            positions.extend((row[0],row[0]+4,row[0]+8,row[3]))
        for at in positions:
            bad=bytearray(data)
            bad[at]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_every_input_and_protected_layout()

    def test_03_exact_checkpoint_mapping_and_both_fixture_stages(self):
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
