"""Qualify the complete 36-word loader with only its final scheduling pair."""
import csv
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_third_resource_loader_status_candidates as screen
from tools.experiments import game_third_resource_loader_lifetime_candidates as lifetime
from tools.tests import test_game_third_resource_loader_match as base
from tools.tests import test_game_third_resource_loader_lifetime_match as previous
from tools.pad_generated_object import emit_padded_assembly


class GameThirdResourceLoaderStatusMatchTests(base.GameThirdResourceLoaderMatchTests):
    @classmethod
    def setUpClass(cls):
        base.GameThirdResourceLoaderMatchTests.setUpClass.__func__(cls)
        old=cls.out;cls.out=cls.root/'conker/build/game-third-resource-loader-status-match-test'
        cls.out.mkdir(exist_ok=True);manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert hashlib.sha256((cls.root/screen.SOURCE).read_bytes()).hexdigest()==screen.SOURCE_SHA
            assert hashlib.sha256((cls.root/screen.GUARDS).read_bytes()).hexdigest()==screen.GUARDS_SHA
            values={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                values[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(values,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']==screen.SOURCE_SHA and cls.baseline['guards']==screen.GUARDS_SHA
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.slot=cls.out/'slot.s';cls.slot.write_bytes((old/'slot.s').read_bytes())
        cls.assemble('original',(old/'original.s').read_text())
        cls.after_guards=cls.out/'after-guards.csv'
        cls.after_guards.write_bytes(screen.install_guards((cls.out/'before-guards').read_bytes()))
        with cls.after_guards.open(newline='') as stream:
            reader=csv.DictReader(stream);cls.fields=reader.fieldnames;cls.all_rows=list(reader)
        cls.rows=screen.target_rows(cls.after_guards.read_bytes());cls.target_guards=cls.out/'target-guards.csv'
        with cls.target_guards.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=cls.fields);writer.writeheader();writer.writerows(cls.rows)
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot,
            word_patches_path=cls.target_guards,filename='generated_6A3D0'))

    def test_01_banked_raw_and_complete_existing_guarded_slot(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(36,48,2))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.padded,self.retail);self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(self.raw[:30],self.retail[:30]);self.assertEqual(self.raw[32:],self.retail[32:])
        self.assertEqual(self.raw[30:32],self.retail[30:32][::-1])
        self.assertEqual([int(row['offset'],0) for row in self.rows],[0x78,0x7C])
        self.assertFalse(any(row['omit']=='true' for row in self.rows))
        for profile in ('owner','retail'):
            meta,words=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile)
            self.assertEqual((meta['body_words'],meta['frame'],meta['differences']),(36,48,2));self.assertEqual(words,self.raw)
        self.receipt('shape',raw_words=36,raw_differences=2,linked_words=36,linked_bytes=144,
            normalizations_before=3,normalizations_after=2,instruction_drops_before=1,instruction_drops_after=0,
            direct_retail_words=34,only_final_independent_schedule_swapped=True,direct_match=False)

    def test_06_effective_compiled_semantic_controls(self):
        with patch.object(previous,'screen',screen):
            previous.GameThirdResourceLoaderLifetimeMatchTests.test_06_effective_compiled_semantic_controls(self)

    def test_07_whole_owner_both_profiles_padders_and_existing_neighbors(self):
        with patch.object(previous,'screen',screen):
            previous.GameThirdResourceLoaderLifetimeMatchTests.test_07_whole_owner_both_profiles_padders_and_existing_neighbors(self)

    def test_08_literal_frozen_all_inputs_whole_ELF_guards_and_data(self):
        before_source=(self.out/'before-source').read_bytes();actual=(self.root/screen.SOURCE).read_bytes()
        installed=actual!=before_source
        self.assertEqual(actual,screen.install(before_source.decode('ascii')).encode('ascii') if installed else before_source)
        before_guards=(self.out/'before-guards').read_bytes();guards=(self.root/screen.GUARDS).read_bytes()
        self.assertEqual(guards,screen.install_guards(before_guards) if installed else before_guards)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
            if name not in ('source','guards'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=base.audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=installed,ELF_changes=0,guard_rows_removed=2 if installed else 0,
            exact_complete_source_and_two_scheduling_rows_only=True,all_other_seven_inputs_metadata_data_exact=True,
            source_SHA256=hashlib.sha256(actual).hexdigest(),guards_SHA256=hashlib.sha256(guards).hexdigest(),
            matching_credit=0,protected_data=audit,no_projection_in_actual_delta_audit=True)

    def test_09_native32_all_low_halfword_payloads_keys_unused_and_callbacks(self):
        with patch.object(previous,'screen',screen):
            previous.GameThirdResourceLoaderLifetimeMatchTests.test_09_native32_all_low_halfword_payloads_keys_unused_and_callbacks(self)

    def test_10_each_existing_guard_expected_word_and_relocation_rejects(self):
        cases=0
        for row in self.rows:
            for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_26:func_1502B6BC')):
                rows=[dict(item) for item in self.rows];rows[self.rows.index(row)][field]=value
                target=self.out/'wrong-guards.csv'
                with target.open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=self.fields);writer.writeheader();writer.writerows(rows)
                with self.assertRaises(ValueError): emit_padded_assembly(self.out/'selected.o',self.slot,
                    word_patches_path=target,filename='generated_6A3D0')
                cases+=1
        self.receipt('guards',effective_expected_word_relocation_rejections=cases,remaining_rows=2,instruction_drops=0)

    def test_11_fresh_discriminating_direct_match_probes_are_not_qualified(self):
        variants=dict(screen.candidates());measured=[]
        self.assertEqual(len(variants),len(list(screen.candidates())))
        for name in ('installed','assigned-failure-return','schedule-explicit-goto','tail-volatile-header'):
            for profile in ('owner','retail'):
                meta,words=screen.compile_candidate(self.root,self.out,'probe-'+name+'-'+profile,variants[name],profile)
                self.assertGreater(meta['differences'],0);measured.append(meta)
        self.receipt('diagnostics',measurements=measured,no_direct_match=True,two_scheduling_guards_still_required=True)

    def test_13_exact_successor_projections_and_effective_corruption_rejections(self):
        before=(self.out/'before-source').read_text();after=screen.install(before)
        guards=(self.out/'before-guards').read_bytes();selected=screen.install_guards(guards)
        source_path,guard_path,elf_path=(self.root/path for path in (screen.SOURCE,screen.GUARDS,'conker/build/conker.us.elf'))
        rt,rb=Path.read_text,Path.read_bytes
        def source(value): return patch.object(Path,'read_text',lambda p,*a,**kw:value if p==source_path else rt(p,*a,**kw))
        def files(value=selected,elf=self.before):
            return patch.object(Path,'read_bytes',lambda p:value if p==guard_path else elf if p==elf_path else rb(p))
        with source(after),files():
            self.assertEqual(screen.historical_source(self.root),before);self.assertEqual(screen.historical_guards(self.root),guards)
        for wrong in (after.replace('loaded = 2;','loaded = 4;'),after.replace('    loaded = 0;','    loaded = 1;'),
                after+screen.QUALIFIED,after+'\n'):
            with source(wrong),files(),self.assertRaises(AssertionError):
                screen.historical_source(self.root)
        for wrong in (selected.replace(screen.NEW_BLOCK,screen.NEW_BLOCK.replace(b'0xAC6A0000',b'0xAC6A0001',1)),
                selected+b'\n',selected.replace(b'0x27BDFFC0',b'0x27BDFFC1',1)):
            self.assertNotEqual(wrong,selected)
            with source(after),files(wrong),self.assertRaises(AssertionError):
                screen.historical_guards(self.root)
        start=base.elf_slot_offset(self.before,screen.ENTRY,144)
        extent=base.installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,extent+3):
            wrong=bytearray(self.before);wrong[offset]^=1
            with source(after),files(elf=bytes(wrong)),self.assertRaises(AssertionError): screen.historical_source(self.root)
        with self.assertRaises(ValueError): screen.install(before+'\n')
        with self.assertRaises(ValueError): screen.install_guards(guards+b'\n')
        self.receipt('historical',source_rejections=4,guard_rejections=3,word_extent_rejections=2,stale_install_rejections=2,
            exact_complete_body_guard_block_slot_extent_only=True,baselines_not_refreshed=True)

    def test_14_both_frozen_loader_predecessor_views_remain_exact(self):
        source_path,guard_path=(self.root/path for path in (screen.SOURCE,screen.GUARDS))
        before=(self.out/'before-source').read_text();guards=(self.out/'before-guards').read_bytes()
        rt,rb=Path.read_text,Path.read_bytes
        with patch.object(Path,'read_text',lambda p,*a,**kw:screen.install(before) if p==source_path else rt(p,*a,**kw)),patch.object(
                Path,'read_bytes',lambda p:screen.install_guards(guards) if p==guard_path else rb(p)):
            self.assertEqual(lifetime.historical_source(self.root),(self.root/'conker/build/game-third-resource-loader-match-test/before-source').read_text())
            self.assertEqual(lifetime.historical_guards(self.root),(self.root/'conker/build/game-third-resource-loader-match-test/before-guards').read_bytes())
        self.receipt('predecessors',both_exact_complete_source_guard_predecessor_views=True,seven_actual_other_inputs_not_projected=True)


if __name__=='__main__':unittest.main()
