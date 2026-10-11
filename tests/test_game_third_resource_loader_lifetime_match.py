"""Qualify the complete incoming-result loader and literal guard-only delta."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
from pathlib import Path
from unittest.mock import patch
import unittest

from tools.experiments import game_third_resource_loader_lifetime_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string,parse_object,emit_padded_assembly
from tools.tests import test_game_third_resource_loader_match as base
from tools.tests.game_owner_pool import normalized_pools


class GameThirdResourceLoaderLifetimeMatchTests(base.GameThirdResourceLoaderMatchTests):
    @classmethod
    def setUpClass(cls):
        base.GameThirdResourceLoaderMatchTests.setUpClass.__func__(cls)
        old=cls.out;cls.out=cls.root/'conker/build/game-third-resource-loader-lifetime-match-test'
        cls.out.mkdir(exist_ok=True)
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert (cls.root/screen.SOURCE).read_bytes()==(old/'before-source').read_bytes()
            assert (cls.root/screen.GUARDS).read_bytes()==(old/'before-guards').read_bytes()
            for name in cls.paths: (cls.out/('before-'+name)).write_bytes((old/('before-'+name)).read_bytes())
            manifest.write_bytes((old/'baseline.json').read_bytes())
        cls.baseline=json.loads(manifest.read_text())
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
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(37,48,7))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.padded,self.retail);self.assertEqual(self.link('original'),self.retail)
        self.assertEqual((self.raw[20],self.raw[23],self.raw[24]),(0xAFA30024,0x14400004,0x8FA30024))
        self.assertEqual(self.raw[28:32],[0xAC620000,0x8C4A0000,0x00002025,0xAC6A0000])
        self.assertEqual([int(row['offset'],0) for row in self.rows],[0x38,0x6C,0x78,0x80])
        self.assertEqual(sum(row['omit']=='true' for row in self.rows),1)
        for profile in ('owner','retail'):
            meta,words=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile)
            self.assertEqual((meta['body_words'],meta['frame'],meta['differences']),(37,48,7));self.assertEqual(words,self.raw)
        self.receipt('shape',raw_words=37,raw_differences=7,linked_words=36,linked_bytes=144,
            original_frame=48,normalizations_before=6,normalizations_after=3,instruction_drops_before=1,
            instruction_drops_after=1,direct_retail_words=33,direct_match=False)

    def test_06_effective_compiled_semantic_controls(self):
        controls=(('gate','*slot != NULL','*slot == NULL',dict(present=1),dict()),
            ('status','loaded = 2;','loaded = 4;',dict(),dict(result=0)),
            ('path','2, 0x11, identity','2, 0x10, identity',dict(),dict()),
            ('header','*(struct124 **)loaded','(struct124 *)loaded',dict(),dict()),
            ('publication','    *slot = (struct124 *)loaded;\n','',dict(),dict(result=base.slot(7))))
        for name,before,after,inputs,args in controls:
            body=screen.QUALIFIED.replace(before,after);self.assertNotEqual(body,screen.QUALIFIED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(base.fixture(**inputs),forms=(words,),**args)
        self.receipt('controls',fresh_effective_selected_semantic_mutations=5)

    def test_07_whole_owner_both_profiles_padders_and_existing_neighbors(self):
        run=subprocess.run;objects={};before=(self.out/'before-source').read_text();after=screen.install(before)
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        def fingerprint(obj,name):
            text,functions,relocations=parse_object(obj);info=functions[name];start=info['value'];end=start+info['size']
            return info['size'],text[start:end],{o-start:v for o,v in relocations.items() if start<=o<end}
        for profile in ('owner','unrolled'):
            for stage,source in (('before',before),('after',after)):
                with patch('subprocess.run',side_effect=compact if profile=='owner' else run):
                    objects[profile,stage],diagnostics=compile_owner(self.root,self.out,source,profile+'-'+stage)
                self.assertEqual(diagnostics,[])
            names=set(parse_object(objects[profile,'before'])[1])
            for name in names-{screen.FUNCTION}:
                self.assertEqual(fingerprint(objects[profile,'before'],name),fingerprint(objects[profile,'after'],name),name)
            self.assertEqual(normalized_pools(objects[profile,'before']),normalized_pools(objects[profile,'after']))
            self.assertEqual(fingerprint(objects[profile,'after'],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        header=ELF_HEADER.unpack_from(self.before)
        headers=[SECTION_HEADER.unpack_from(self.before,header[6]+index*header[11]) for index in range(header[12])]
        symbols={}
        for table in headers:
            if table[1]!=2: continue
            strings=headers[table[6]];names=self.before[strings[4]:strings[4]+strings[5]]
            for offset in range(table[4],table[4]+table[5],table[9]):
                name,value,size,info,other,section=SYMBOL.unpack_from(self.before,offset)
                if section: symbols[read_c_string(names,name)]=value
        routes=[];resolved=[]
        for route,stage in itertools.product(('pad_c_object.py','pad_generated_object.py'),('before','after')):
            asm=self.out/(route+'-'+stage+'.s');guards=self.out/'before-guards' if stage=='before' else self.after_guards
            args=[str(objects['owner',stage]),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                str(objects['owner',stage]),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
            args+=['--word-patches',str(guards),'--function-object','func_1503D804='+str(objects['unrolled',stage])]
            subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            parsed=parse_object(asm.with_suffix('.o'));routes.append(parsed)
            definitions={name:symbols[name] for values in parsed[2].values() for kind,name in values if name not in parsed[1]}
            script=asm.with_suffix('.ld');script.write_text('SECTIONS { .text 0x1503CF20 : SUBALIGN(4) { *(.text) } }\n')
            elf=script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1503CF20',
                *['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(asm.with_suffix('.o'))],
                check=True,capture_output=True)
            resolved.append(sections(elf)['.text'][1])
        self.assertTrue(all(item==routes[0] for item in routes));self.assertTrue(all(item==resolved[0] for item in resolved))
        start=base.elf_slot_offset(self.before,0x1503CF20,len(resolved[0]))
        self.assertEqual(resolved[0],self.before[start:start+len(resolved[0])])
        self.assertEqual(len(routes[0][1]),15)
        for name,info in routes[0][1].items():
            extent=base.installed.symbol_size_offset(self.before,name,0x1503CF20+info['value'])
            self.assertEqual(info['size'],struct.unpack_from('>I',self.before,extent)[0],name)
        self.receipt('owner',functions=15,neighbors=14,profiles=2,actual_padders=2,
            all_four_complete_resolved_owner_bytes_extents_relocations_pools_exact=True,D804_selection_unchanged=True)

    def test_08_literal_frozen_all_inputs_whole_ELF_guards_and_data(self):
        from tools.experiments import game_third_resource_loader_status_candidates as status
        before_source=(self.out/'before-source').read_bytes();source=status.historical_source(self.root).encode('ascii')
        installed=source!=before_source
        expected_source=screen.install(before_source.decode('ascii')).encode('ascii') if installed else before_source
        self.assertEqual(source,expected_source)
        before_guards=(self.out/'before-guards').read_bytes();actual_guards=status.historical_guards(self.root)
        self.assertEqual(actual_guards,screen.install_guards(before_guards) if installed else before_guards)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
            if name not in ('source','guards'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes(),path)
        audit=base.audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=installed,ELF_changes=0,guard_rows_removed=3 if installed else 0,
            source_guard_view_and_exact_four_row_successor_only=True,all_other_ELF_bytes_metadata_data_inputs_exact=True,
            source_SHA256=hashlib.sha256(source).hexdigest(),guards_SHA256=hashlib.sha256(actual_guards).hexdigest(),
            matching_credit=0,protected_data=audit,no_projection_in_actual_ELF_delta_audit=True,
            exact_status_source_guard_projection=source!=(self.root/screen.SOURCE).read_bytes())

    def test_09_native32_all_low_halfword_payloads_keys_unused_and_callbacks(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],base.NATIVE+screen.QUALIFIED+base.NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',base.NATIVE+screen.QUALIFIED.replace('loaded = 2;','loaded = 4;')+base.NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',profiles=['O2','O0'],low_halfword_payload_cases=65536,upper_halfword=65535,
            matrix_cases=6144,publication_alias_cases=4,valid_native_ids_only=True,effective_status_control=True)

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
        self.receipt('guards',effective_expected_word_relocation_rejections=cases,remaining_rows=4,retired_normalizations=3)

    def test_11_fresh_discriminating_direct_match_probes_are_not_qualified(self):
        measured=[]
        for name,body in screen.candidates():
            for profile in ('owner','retail'):
                meta,words=screen.compile_candidate(self.root,self.out,'probe-'+name+'-'+profile,body,profile)
                self.assertGreater(meta['differences'],0);measured.append(meta)
        self.receipt('diagnostics',measurements=measured,no_direct_match=True,three_normalizations_and_drop_still_required=True)

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
            with source(wrong),files(),self.assertRaises(AssertionError): screen.historical_source(self.root)
        for wrong in (selected.replace(b'0x24040002',b'0x24040003',1),selected+b'\n',selected.replace(b'0x27BDFFC0',b'0x27BDFFC1',1)):
            self.assertNotEqual(wrong,selected)
            with source(after),files(wrong),self.assertRaises(AssertionError): screen.historical_guards(self.root)
        start=base.elf_slot_offset(self.before,screen.ENTRY,144)
        extent=base.installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,extent+3):
            wrong=bytearray(self.before);wrong[offset]^=1
            with source(after),files(elf=bytes(wrong)),self.assertRaises(AssertionError): screen.historical_source(self.root)
        with self.assertRaises(ValueError): screen.install(before+'\n')
        with self.assertRaises(ValueError): screen.install_guards(guards+b'\n')
        self.receipt('historical',source_rejections=4,guard_rejections=3,word_extent_rejections=2,stale_install_rejections=2,
            complete_body_exact_guard_block_and_retail_slot_extent_only=True,baselines_not_refreshed=True)


if __name__=='__main__':unittest.main()
