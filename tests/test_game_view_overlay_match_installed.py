"""Complete first matched overlay image, guard prefix and unchanged inputs."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_view_overlay_match as source
from tools.tests import view_overlay_match_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as previous
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class ViewOverlayMatchInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out);cls.expected=source.expected_inputs(cls.root,cls.out)
        cls.wanted={k:cls.expected.get(k,(cls.out/('before-'+k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual(len(source.PATHS),107)
        for key,path in source.PATHS.items():self.assertTrue((self.root/path).read_bytes()==self.wanted[key],key)

    def test_01_complete_matched_image_extent_guard_prefix_and_protected_layout(self):
        self.check_live()
        for key,digest in checkpoint.AFTER.items():self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(),digest)
        before,data=(self.out/'before-elf').read_bytes(),self.expected['elf']
        self.assertEqual((len(before),len(data)),(3257636,3257636))
        self.assertEqual(sum(a!=b for a,b in zip(before,data)),318)
        at=elf_slot_offset(data,source.ENTRY,408)
        self.assertEqual(data[at:at+408],(self.out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+408])
        rows={r[1]:r for r in symbol_rows(data)};old={r[1]:r for r in symbol_rows(before)}
        self.assertEqual(set(rows),set(old))
        for name,row in rows.items():
            wanted=list(old[name][2][1:])
            if name==source.FUNCTION:wanted[1]=408
            self.assertEqual(row[2][1:],tuple(wanted),name)
        self.assertTrue(self.expected['guards'].startswith((self.out/'before-guards').read_bytes()))
        source.checked_manifest(self.expected['guards'],self.out,self.out/'qualified.o')
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out/'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=318,body_bytes=408,slot_bytes=408,extent=[392,408],new_guards=37,
            metadata_serialization_bytes=0,metadata_exclusions=0,unchanged_other_inputs=104,
            guard_history_exact_prefix=True,protected_layout=layout),indent=2)+'\n')

    def test_02_all107_live_inputs_and_code_caller_data_metadata_controls(self):
        with patch.object(previous,'source',source):
            previous.ViewOverlayInstalledTests.test_02_all107_live_input_and_target_caller_data_metadata_controls(self)

    def test_03_only_exact_successor_and_both_fixture_stages(self):
        with patch.object(previous,'checkpoint',checkpoint):
            previous.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__=='__main__':unittest.main()
