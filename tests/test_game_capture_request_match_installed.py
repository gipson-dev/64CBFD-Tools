"""Independent whole-image closure and fail-closed successor/history checks."""
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_capture_request_match as match
from tools.experiments import game_capture_request_slot as source
from tools.tests import capture_request_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before,rom):
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:
        raise ValueError('Unexpected capture request predecessor ELF')
    row=next(row for row in symbol_rows(before) if row[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):
        raise ValueError('Unexpected capture request predecessor symbol')
    output=bytearray(before)
    offset=elf_slot_offset(before,source.ENTRY,160)
    output[offset:offset+160]=rom[source.ROM:source.ROM+160]
    struct.pack_into('>I',output,row[0]+8,156)
    return bytes(output)


class CaptureRequestInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/match.BUILD
        source.freeze(cls.root,cls.root/source.BUILD)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_literal_source_guard_prefix_and_every_ELF_byte(self):
        before=(self.root/source.BUILD/'before-elf').read_bytes()
        expected={'elf':expected_image(before,(self.root/'conker/conker.us.bin').read_bytes()),
            'request_owner':source.recover((self.root/source.BUILD/'before-request_owner').read_text(),source.SELECTED).encode(),
            'guards':match.guard_manifest((self.root/source.BUILD/'before-guards').read_bytes())}
        for key,path in source.PATHS.items():
            actual=(self.root/path).read_bytes()
            self.assertEqual(actual,expected.get(key,(self.root/source.BUILD/('before-'+key)).read_bytes()),key)
        for key,digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(),digest,key)
        self.assertEqual((self.root/source.PATHS['request_owner']).read_text(),expected['request_owner'].decode())
        data=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.assertEqual(sum(a!=b for a,b in zip(before,expected['elf'])),121)
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image',ELF_sha256=checkpoint.AFTER['elf'],ELF_bytes=len(before),
            changed_bytes=121,code_slot=[source.ENTRY,160],symbol_extent=[12,156],
            every_other_ELF_byte_fixed=True,metadata_allowances=0,protected_data=data,
            guard_prefix_fixed_and_exactly_22_rows_appended=True,unchanged_other_inputs=len(source.PATHS)-3)

    def test_02_effective_current_and_frozen_corruption_controls(self):
        rb,rt=Path.read_bytes,Path.read_text
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_literal_source_guard_prefix_and_every_ELF_byte()
        path=self.root/source.PATHS['request_owner']
        with patch.object(Path,'read_text',lambda p,*a,**kw:rt(p,*a,**kw)+'\n' if p==path else rt(p,*a,**kw)):
            with self.assertRaises(AssertionError):
                self.test_01_literal_source_guard_prefix_and_every_ELF_byte()
        path=self.root/source.PATHS['elf']
        data=rb(path)
        row=next(row for row in symbol_rows(data) if row[1]==source.FUNCTION)
        offsets=(elf_slot_offset(data,source.ENTRY,4),row[0]+8,elf_slot_offset(data,0x151742EC,4),
            elf_slot_offset(data,0x15019464,4),elf_slot_offset(data,0x1510BF60,4),elf_slot_offset(data,0x8009B884,4))
        for offset in offsets:
            bad=bytearray(data)
            bad[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_literal_source_guard_prefix_and_every_ELF_byte()
        before=bytearray((self.root/source.BUILD/'before-elf').read_bytes())
        before[elf_slot_offset(before,source.ENTRY,4)]^=1
        with self.assertRaisesRegex(ValueError,'predecessor ELF'):
            expected_image(bytes(before),(self.root/'conker/conker.us.bin').read_bytes())
        self.receipt('installed-controls',all_current_input_flips=len(source.PATHS),source_text_flip=True,
            in_file_target_symbol_caller_previous_match_scanner_table_flips=len(offsets),unknown_predecessor_rejected=True)

    def test_03_exact_inverse_unknown_inputs_and_all_capture_guards(self):
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
                directory=source.BUILD if stage=='before' else checkpoint.BUILD
                path=self.root/directory/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                    with self.assertRaisesRegex(AssertionError,'capture request match fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse',known_paths=3,absolute_relative_unknown_and_all_capture_controls=True)

    def test_04_previous_view_gates_through_only_the_exact_inverse(self):
        rb=Path.read_bytes
        def predecessor(path):
            return checkpoint.previous_input(rb(path),path,self.root)
        output=io.StringIO()
        with patch.object(Path,'read_bytes',predecessor):
            suite=unittest.defaultTestLoader.loadTestsFromName('tools.tests.test_game_view_pass_dispatch_installed')
            result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
        self.assertEqual(result.testsRun,5,output.getvalue())
        self.assertTrue(result.wasSuccessful(),output.getvalue())
        self.receipt('history',previous_view_tests=5,embedded_earlier_actor_and_matrix_tests=8,
            exact_input_inverse_only=True,current_image_independent_without_normalization=True)

    def test_05_all_original_archive_fingerprints(self):
        manifest=self.root/'conker/build/alternative-source-byte-audit-20261014/source-before.json'
        self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1')
        files=json.loads(manifest.read_text(encoding='utf-8-sig'))['files']
        self.assertEqual(len(files),801)
        archive=self.root/'../Another Source/CBFD-Recompiled/conker'
        for path,digest in files.items():
            self.assertEqual(hashlib.sha256((archive/path).read_bytes()).hexdigest().upper(),digest,path)
        self.receipt('archive',all_original_fingerprints=801,original_manifest_fixed=True)


if __name__=='__main__':
    unittest.main()
