"""Whole-image closure, corruption controls and exact predecessor replay."""
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_view_pass_dispatch as source
from tools.tests import view_pass_dispatch_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before,rom):
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:
        raise ValueError('Unexpected view dispatch predecessor ELF')
    definition=next(row for row in symbol_rows(before) if row[1]==source.FUNCTION)
    if definition[2][1:3]!=(source.ENTRY,source.WORDS*4):
        raise ValueError('Unexpected view dispatch predecessor symbol')
    expected=bytearray(before)
    offset=elf_slot_offset(before,source.ENTRY,source.WORDS*4)
    expected[offset:offset+source.WORDS*4]=rom[source.ROM:source.ROM+source.WORDS*4]
    return bytes(expected)


class ViewPassDispatchInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_current_sources_and_every_ELF_byte(self):
        before=(self.out/'before-elf').read_bytes()
        rom=(self.root/'conker/conker.us.bin').read_bytes()
        expected={'elf':expected_image(before,rom),
            'dispatch_owner':source.recover((self.out/'before-dispatch_owner').read_text()).encode()}
        for key,path in source.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest,key)
        self.assertEqual((self.root/source.PATHS['dispatch_owner']).read_text(),expected['dispatch_owner'].decode())
        data=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        changed=sum(a!=b for a,b in zip(before,expected['elf']))
        self.assertEqual(changed,151)
        self.receipt('installed-image',ELF_sha256=checkpoint.AFTER['elf'],changed_bytes=changed,
            ELF_bytes=len(before),code_slot=[source.ENTRY,316],symbol_extent_unchanged=316,
            every_other_ELF_byte_fixed=True,metadata_allowances=0,protected_data=data,
            unchanged_production_inputs=len(source.PATHS)-2,guards_profiles_headers_progress_fixed=True)

    def test_02_effective_current_and_frozen_corruption_controls(self):
        rb,rt=Path.read_bytes,Path.read_text
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_current_sources_and_every_ELF_byte()
        path=self.root/source.PATHS['dispatch_owner']
        with patch.object(Path,'read_text',lambda p,*a,**kw:rt(p,*a,**kw)+'\n' if p==path else rt(p,*a,**kw)):
            with self.assertRaises(AssertionError):
                self.test_01_current_sources_and_every_ELF_byte()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        definition=next(row for row in symbol_rows(data) if row[1]==source.FUNCTION)
        offsets=(elf_slot_offset(data,source.ENTRY,4),definition[0]+8,
            elf_slot_offset(data,0x1507DF10,4),elf_slot_offset(data,0x1510B958,4),
            elf_slot_offset(data,0x1510BF60,4),elf_slot_offset(data,0x8009B884,4))
        for offset in offsets:
            bad=bytearray(data)
            bad[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_current_sources_and_every_ELF_byte()
        baseline=bytearray((self.out/'before-elf').read_bytes())
        baseline[elf_slot_offset(baseline,source.ENTRY,4)]^=1
        with self.assertRaisesRegex(ValueError,'predecessor ELF'):
            expected_image(bytes(baseline),(self.root/'conker/conker.us.bin').read_bytes())
        self.receipt('installed-controls',current_inputs=len(source.PATHS),text_controls=1,
            in_file_target_symbol_actor_select_scanner_table_flips=len(offsets),unknown_predecessor_rejected=True)

    def test_03_exact_inverse_unknown_inputs_and_capture_guards(self):
        checkpoint.freeze_after(self.root)
        rb=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            before=checkpoint.fixture(self.root,'before',key)
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),before)
            self.assertEqual(checkpoint.previous_input(current,self.root/relative,self.root),before)
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            self.assertEqual(checkpoint.previous_input(current,'unowned-path',self.root),current)
            for stage in ('before','after'):
                path=self.out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                    with self.assertRaisesRegex(AssertionError,'view dispatch fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse',known_paths=2,absolute_relative_unknown_and_all_before_after_controls=True)

    def test_04_predecessor_actor_gates_through_only_the_exact_inverse(self):
        rb=Path.read_bytes
        def predecessor(path):
            return checkpoint.previous_input(rb(path),path,self.root)
        output=io.StringIO()
        with patch.object(Path,'read_bytes',predecessor):
            suite=unittest.defaultTestLoader.loadTestsFromName('tools.tests.test_game_actor_mode_flags_installed')
            result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
        self.assertEqual(result.testsRun,5,output.getvalue())
        self.assertTrue(result.wasSuccessful(),output.getvalue())
        self.receipt('history',predecessor_tests=5,embedded_matrix_tests=3,exact_input_inverse_only=True,
            current_image_independently_qualified_without_normalization=True)

    def test_05_all_original_archive_fingerprints(self):
        manifest=self.root/'conker/build/alternative-source-byte-audit-20261014/source-before.json'
        self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1')
        rows=json.loads(manifest.read_text(encoding='utf-8-sig'))['files']
        self.assertEqual(len(rows),801)
        archive=self.root/'../Another Source/CBFD-Recompiled/conker'
        for path,digest in rows.items():
            self.assertEqual(hashlib.sha256((archive/path).read_bytes()).hexdigest().upper(),digest,path)
        self.receipt('archive',all_original_fingerprints=801,original_manifest_fixed=True)


if __name__=='__main__':
    unittest.main()
