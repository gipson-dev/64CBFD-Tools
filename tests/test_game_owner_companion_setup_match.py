"""Certified prefix, full C semantics, relocations and installed companion match."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_companion_setup_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_companion_setup_recovery as recovery
from tools.tests import test_game_owner_link_allocator_match as wrapper

INSERT=recovery.INSERT


def guard_text(rows):
    stream=io.StringIO()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writerows(rows)
    return stream.getvalue()


def normalize_object(source,destination):
    data=bytearray(source.read_bytes())
    h=ELF_HEADER.unpack_from(data)
    parts=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
    names=parts[h[13]]
    pool=data[names[4]:names[4]+names[5]]
    label=lambda p:pool[p[0]:].split(b'\0',1)[0]
    text=next(p for p in parts if label(p)==b'.text')
    _,functions,_=parse_object(source)
    fn=functions[screen.FUNCTION];base=fn['value']
    words=list(struct.unpack_from('>176I',data,text[4]+base))
    screen.certify(words)
    struct.pack_into('>176I',data,text[4]+base,*screen.normalize(words))
    inverse={source:target for target,source in enumerate(screen.PREFIX_MAP)}
    for part in parts:
        if label(part)!=b'.rel.text':continue
        for offset in range(part[4],part[4]+part[5],8):
            address,info=struct.unpack_from('>II',data,offset)
            if base<=address<base+0x11C:
                struct.pack_into('>II',data,offset,base+inverse[(address-base)//4]*4,info)
    destination.write_bytes(data)


class GameOwnerCompanionSetupMatchTests(unittest.TestCase):
    run_host=recovery.GameOwnerCompanionSetupRecoveryTests.run_host
    receipt=recovery.GameOwnerCompanionSetupRecoveryTests.receipt
    compare=recovery.GameOwnerCompanionSetupRecoveryTests.compare
    test_03_native32_actual_body_and_layout=recovery.GameOwnerCompanionSetupRecoveryTests.test_03_native32_actual_body_and_layout
    test_04_compiled_effective_negatives=recovery.GameOwnerCompanionSetupRecoveryTests.test_04_compiled_effective_negatives

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-companion-setup-match-test'
        cls.out.mkdir(exist_ok=True)
        directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)
        changed=patch.object(recovery.screen,'SELECTED',screen.SELECTED)
        changed.start();cls.addClassCleanup(changed.stop)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>176I',cls.rom,screen.ROM))
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.words=screen.normalize(cls.raw)
        cls.rows=screen.guard_rows(cls.out/'selected.o')
        installed=screen.SELECTED in (cls.root/screen.SOURCE).read_text()
        current=(cls.root/'conker/retail_word_patches.us.csv').read_bytes()
        cls.guards=cls.out/'guards.csv'
        cls.guards.write_bytes(current if installed else current+guard_text(cls.rows).encode())
        if not (cls.out/'baseline.json').exists() and not installed:
            hashes={}
            for name,path in dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')

    def test_01_complete_certificate_profiles_and_rejected_controls(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences','pool_bytes')),(176,216,69,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.words,self.retail)
        self.assertEqual(len(self.rows),69)
        self.assertEqual(sum(r['expected_relocations']!='-' for r in self.rows),8)
        self.assertEqual(sum(r['replacement_relocations']!='-' for r in self.rows),8)
        proof=screen.certify(self.raw)
        # These corruptions invalidate the private-memory proof, not a ROM comparison.
        bad=self.raw.copy();bad[5]=(bad[5]&~65535)|0xD4
        with self.assertRaisesRegex(ValueError,'private-home shape'):screen.certify(bad)
        bad=self.raw.copy();bad[0x98//4]=(9<<26)|(17<<21)|(17<<16)|4
        with self.assertRaisesRegex(ValueError,'congruence'):screen.certify(bad)
        bad=self.raw.copy();bad[0x48//4]=(9<<26)|(16<<21)|(25<<16)
        with self.assertRaisesRegex(ValueError,'public write'):screen.certify(bad)
        bad=self.raw.copy();bad[0xA8//4]=3<<26
        with self.assertRaisesRegex(ValueError,'unsupported/control'):screen.certify(bad)
        state=screen.PrefixState()
        for address,size in ((-217,1),(4,1),(1,4)):
            with self.assertRaisesRegex(ValueError,'owned frame/home'):
                state.put(('address','stack',address),screen.constant(1),size)
        profiles=[]
        for profile in recovery.screen.setup.compiler.PROFILES:
            meta,_=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile)
            profiles.append(meta)
        self.receipt('shape',dict(meta=self.meta,profiles=profiles,certificate=proof,normalized_exact=True,
            guards=69,old_relocation_words=8,new_relocation_words=8,rejected_certificate_controls=7,
            raw_private_volatile_home_access_order_not_preserved_or_claimed=True))

    def test_02_guest_original_raw_normalized_and_raw_holes(self):
        count=0;coverage=set()
        for seed,alias,mask,enabled,phase,result_alias in itertools.product(range(3),(False,True),range(8),(False,True),(0,8),(False,True)):
            memory,endpoint=recovery.fixture(seed,alias)
            results=(recovery.ACTOR,endpoint,endpoint) if result_alias else recovery.RESULTS
            models=[self.compare(words,memory,endpoint,mask,enabled,phase,results) for words in (self.retail,self.raw,self.words)]
            coverage.update(models[0].visits)
            self.assertEqual(models[0].memory,models[1].memory)
            self.assertEqual(models[0].memory,models[2].memory)
            self.assertEqual(models[0].events,models[2].events)
            count+=1
        self.assertEqual(len(coverage),176)
        self.receipt('guest',dict(cases=count,executions=count*3,retail_words_reached=176,
            all_memory_and_raw_packet_holes_equal=True,normalized_full_access_trace_equal=True,
            raw_private_access_order_not_claimed=True,valid_public_objects_disjoint_from_private_frame=True))

    def test_05_independent_original_raw_normalized_rebases(self):
        fragment=(self.root/'conker/asm/nonmatchings/generated_1DF510/func_151B2690.s').read_text()
        source=self.out/'original.s';original=self.out/'original.o';normalized=self.out/'normalized.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+fragment)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(original),str(source)],
            cwd=self.root,check=True,capture_output=True)
        normalize_object(self.out/'selected.o',normalized)
        self.assertEqual(parse_object(original)[2],parse_object(normalized)[2])
        self.assertEqual(sum(map(len,parse_object(original)[2].values())),22)
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {n:(entry&0xF0000000)+0x108008+i*0x100 for i,n in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,obj in (('original',original),('raw',self.out/'selected.o'),('normalized',normalized)):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>176I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2])
            for mask,phase in itertools.product(range(8),(0,8)):
                memory,endpoint=recovery.fixture(count%3,bool(count%2))
                for name,address in screen.SYMBOLS.items():
                    if name.startswith('D_'):
                        for i in range(12 if address&255<0x80 else 4):
                            memory[symbols[name]+i]=memory[address+i]
                models=[self.compare(words,memory,endpoint,mask,True,phase,symbols=symbols,entry=entry) for words in bodies]
                self.assertEqual(models[0].memory,models[1].memory)
                self.assertEqual(models[0].memory,models[2].memory)
                self.assertEqual(models[0].events,models[2].events)
                count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=12,cases=count,executions=count*3,
            normalized_byte_exact=True,relocation_uses=22,raw_final_state_and_normalized_access_trace_equal=True))

    def test_06_copied_owner_and_actual_guarded_padder(self):
        current=(self.root/screen.SOURCE).read_text()
        before=current.replace(screen.SELECTED,screen.ORIGINAL).replace(INSERT,'').replace(
            'void func_151B2690(u8 *volatile);','void func_151B2690(u8 *);')
        after=before.replace('/* Non-matching placeholders',INSERT+'/* Non-matching placeholders',1).replace(
            screen.ORIGINAL,screen.SELECTED).replace('void func_151B2690(u8 *);','void func_151B2690(u8 *volatile);')
        objects=[];warnings=[]
        for name,body in (('owner-before',before),('owner-after',after)):
            obj,diagnostics=compile_owner(self.root,self.out,body,name)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj);warnings.append(diagnostics)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(len(warnings[0]),4)
        old,of,orels=parse_object(objects[0]);new,nf,nrels=parse_object(objects[1])
        self.assertEqual(of.keys(),nf.keys())
        for name,f in nf.items():
            if name==screen.FUNCTION:continue
            prior=of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-f['value']:r for o,r in nrels.items() if f['value']<=o<f['value']+f['size']},
                {o-prior['value']:r for o,r in orels.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        old_guards=self.out/'old-guards.csv'
        baseline=self.out/'before-guards'
        if baseline.exists():
            old_guards.write_bytes(baseline.read_bytes())
        else:
            # A fresh installed clone can qualify padding without claiming a historical ELF audit.
            current_guards=self.guards.read_bytes();appended=guard_text(self.rows).encode()
            self.assertTrue(current_guards.endswith(appended))
            old_guards.write_bytes(current_guards[:-len(appended)])
        padded=[]
        for name,obj,guards in (('padded-before',objects[0],old_guards),('padded-after',objects[1],self.guards)):
            assembly=self.out/(name+'.s');target=self.out/(name+'.o')
            assembly.write_text(emit_padded_assembly(obj,self.root/'conker/asm/1DF510.s',
                word_patches_path=guards,filename='generated_1DF510'))
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(assembly)],check=True,capture_output=True)
            padded.append(parse_object(target))
        old,of,orels=padded[0];new,nf,nrels=padded[1]
        for name,f in nf.items():
            prior=of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-f['value']:r for o,r in nrels.items() if f['value']<=o<f['value']+f['size']},
                {o-prior['value']:r for o,r in orels.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.receipt('owner',dict(neighbors=len(nf)-1,existing_diagnostics=4,new_diagnostics=0,
            raw_neighbors_pools_relocations_preserved=True,isolated_owner_guards_identical=True,
            actual_padded_all_functions_and_relative_relocations_identical=True))

    def test_07_real_wrapper_three_setup_forms(self):
        words=list(struct.unpack_from('>53I',self.rom,wrapper.screen.ROM))
        start,data=sections(self.root/'conker/build/conker.us.elf')['.game']
        self.assertEqual(list(struct.unpack_from('>53I',data,wrapper.screen.ENTRY-start)),words)
        count=0
        for alias,mask,enabled,phase in itertools.product((False,True),range(8),(False,True),(0,8)):
            memory,endpoint=recovery.fixture(count%3,alias)
            models=[self.compare(body,memory,endpoint,mask,enabled,phase,connected=words)
                for body in (self.retail,self.raw,self.words)]
            self.assertEqual(models[0].memory,models[1].memory)
            self.assertEqual(models[0].memory,models[2].memory)
            self.assertEqual(models[0].events,models[2].events)
            for model in models:self.assertEqual(model.common_calls,[(0x33,0,0x180,1,255,1)]*2)
            count+=1
        self.receipt('connected',dict(cases=count,executions=count*3,setup_forms=3,actual_setup_words=176,
            actual_wrapper_words=53,installed_wrapper_exact=True,common_allocator_factory_sdk_bounded=True))

    def test_08_missing_byte_raw_public_and_normalized_complete_prefixes(self):
        count=0
        for alias in (False,True):
            memory,endpoint=recovery.fixture(0,alias)
            for address in (recovery.ACTOR+0x28,endpoint+0x3B,endpoint+0x14,0x800AA320,0x800AA368,0x800AA388):
                broken=memory.copy();del broken[address];models=[]
                for words in (self.retail,self.raw,self.words):
                    model=recovery.CompanionOracle(words,broken,endpoint,7,False,0)
                    with self.assertRaises(KeyError):model.run()
                    models.append(model)
                self.assertEqual((recovery.public(models[0].memory),models[0].records),
                    (recovery.public(models[1].memory),models[1].records))
                self.assertEqual((models[0].memory,models[0].events,models[0].records),
                    (models[2].memory,models[2].events,models[2].records))
                count+=1
        self.receipt('faults',dict(cases=count,executions=count*3,raw_public_prefix_equal=True,
            normalized_full_memory_access_prefix_equal=True,no_hardware_or_portable_fault_guarantee=True))

    def test_09_immutable_installed_elf_guard_progress_audit(self):
        if not (self.out/'baseline.json').exists():
            self.skipTest('immutable pre-install baseline absent')
        before=(self.out/'before-elf').read_bytes()
        current=(self.root/'conker/build/conker.us.elf').read_bytes()
        old_meta,new_meta=metadata(before),metadata(current)
        self.assertEqual(old_meta,new_meta)
        expected=bytearray(before)
        for section in old_meta[4:]:
            start,length=section[4],section[5]
            expected[start:start+length]=current[start:start+length]
        self.assertEqual(current,bytes(expected))
        installed=screen.SELECTED in (self.root/screen.SOURCE).read_text()
        old_guards=(self.out/'before-guards').read_bytes()
        guards=(self.root/'conker/retail_word_patches.us.csv').read_bytes()
        self.assertEqual(guards,old_guards+(guard_text(self.rows).encode() if installed else b''))
        old_progress=(self.out/'before-progress').read_bytes()
        progress=(self.root/'conker/progress.csv').read_bytes()
        if installed:
            old=list(csv.DictReader(io.StringIO(old_progress.decode())))
            new=list(csv.DictReader(io.StringIO(progress.decode())))
            self.assertEqual(len(old),len(new))
            changed=[]
            for a,b in zip(old,new):
                if a!=b:
                    self.assertEqual(a['function'],screen.FUNCTION)
                    self.assertEqual(a['language'],'asm');self.assertEqual(b,dict(a,language='c'))
                    changed.append(a['function'])
            self.assertEqual(changed,[screen.FUNCTION])
        else:
            self.assertEqual(progress,old_progress)
            self.assertEqual((self.root/screen.SOURCE).read_bytes(),(self.out/'before-source').read_bytes())
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('audit',dict(installed=installed,all_loadable_bytes_and_symbol_meanings_identical=True,
            symbol_string_order_only_permitted=True,actual_entire_elf_identical=current==before,
            only69_guard_rows_appended=installed,only_target_asm_to_c_row=installed,
            protected_data_layout=audit,source_sha256=hashlib.sha256((self.root/screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest()))


if __name__=='__main__':
    unittest.main()
