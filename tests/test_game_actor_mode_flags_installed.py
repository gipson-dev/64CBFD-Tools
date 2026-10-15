"""Closed actor-dispatch image delta and exact-input predecessor validation."""
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_mode_flags as source
from tools.tests import actor_mode_flags_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before,rom):
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:
        raise ValueError('Unexpected actor mode predecessor ELF')
    expected=bytearray(before)
    offset=elf_slot_offset(before,source.ENTRY,source.WORDS*4)
    expected[offset:offset+source.WORDS*4]=rom[source.ROM:source.ROM+source.WORDS*4]
    row=next(row for row in symbol_rows(before) if row[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):
        raise ValueError('Unexpected actor mode predecessor symbol')
    struct.pack_into('>I',expected,row[0]+8,source.WORDS*4)
    return bytes(expected)


class ActorModeInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_current_source_binding_and_every_ELF_byte(self):
        before=(self.out/'before-elf').read_bytes()
        rom=(self.root/'conker/conker.us.bin').read_bytes()
        expected={'elf':expected_image(before,rom),
            'actor_owner':source.recover((self.out/'before-actor_owner').read_text()).encode(),
            'makefile':source.recovered_makefile((self.out/'before-makefile').read_text()).encode()}
        for key,path in source.PATHS.items():
            actual=(self.root/path).read_bytes()
            self.assertEqual(actual,expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest,key)
        for key in ('actor_owner','makefile'):
            self.assertEqual((self.root/source.PATHS[key]).read_text(),expected[key].decode())
        data=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image',ELF_sha256=checkpoint.AFTER['elf'],
            changed_bytes=sum(a!=b for a,b in zip(before,expected['elf'])),code_slot=[source.ENTRY,212],
            symbol_extent=[12,212],metadata_allowances=0,every_other_ELF_byte_fixed=True,
            original_table_and_all_protected_data=data,guards_profiles_headers_progress_fixed=True,
            source_and_single_makefile_binding_exact=True)

    def test_02_effective_current_and_frozen_corruption_controls(self):
        rb,rt=Path.read_bytes,Path.read_text
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_current_source_binding_and_every_ELF_byte()
        for key in ('actor_owner','makefile'):
            path=self.root/source.PATHS[key]
            with patch.object(Path,'read_text',lambda p,*a,**kw:rt(p,*a,**kw)+'\n' if p==path else rt(p,*a,**kw)):
                with self.assertRaises(AssertionError):
                    self.test_01_current_source_binding_and_every_ELF_byte()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        definition=next(row for row in symbol_rows(data) if row[1]==source.FUNCTION)
        offsets=(elf_slot_offset(data,source.ENTRY,4),elf_slot_offset(data,source.TABLE,4),
            definition[0]+8,elf_slot_offset(data,0x15081E0C,4),elf_slot_offset(data,0x1510BF60,4))
        for offset in offsets:
            bad=bytearray(data)
            bad[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_current_source_binding_and_every_ELF_byte()
        baseline=bytearray((self.out/'before-elf').read_bytes())
        baseline[elf_slot_offset(baseline,source.ENTRY,4)]^=1
        with self.assertRaisesRegex(ValueError,'predecessor ELF'):
            expected_image(bytes(baseline),(self.root/'conker/conker.us.bin').read_bytes())
        self.receipt('installed-controls',current_inputs=len(source.PATHS),text_controls=2,
            in_file_code_table_symbol_caller_and_scanner_flips=len(offsets),unknown_predecessor_rejected=True)

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
                    with self.assertRaisesRegex(AssertionError,'actor mode fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse',known_paths=3,absolute_relative_unknown_and_all_before_after_controls=True)

    def test_04_predecessor_matrix_gates_through_only_the_exact_inverse(self):
        selectors=[
            'tools.tests.test_game_view_matrix_pass.ViewMatrixPassTests.test_14_installed_sources_progress_guards_and_independent_closed_image',
            'tools.tests.test_game_view_matrix_pass.ViewMatrixPassTests.test_15_effective_current_image_source_and_capture_controls',
            'tools.tests.test_game_view_matrix_pass.ViewMatrixPassTests.test_16_exact_inverse_unknown_input_and_capture_controls']
        rb=Path.read_bytes
        def predecessor(path):
            return checkpoint.previous_input(rb(path),path,self.root)
        output=io.StringIO()
        with patch.object(Path,'read_bytes',predecessor):
            suite=unittest.defaultTestLoader.loadTestsFromNames(selectors)
            result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
        self.assertEqual(result.testsRun,3,output.getvalue())
        self.assertTrue(result.wasSuccessful(),output.getvalue())
        self.receipt('history',predecessor_tests=3,exact_input_inverse_only=True,
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
