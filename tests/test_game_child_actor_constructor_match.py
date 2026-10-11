"""Full retail constructor match, closed relocation recipe and private frame."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_child_actor_constructor_matching as matching
from tools import pad_generated_object as padder
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_child_actor_constructor as previous

screen = previous.screen


class ChildActorConstructorMatchTests(previous.GameChildActorConstructorTests):
    write_rows = classmethod(previous.guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-child-actor-constructor-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert matching.SELECTED in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=matching.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.retail=list(struct.unpack_from('>182I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes();cls.rows=matching.guard_rows(cls.out/'selected.o')
        cls.fields=next(csv.reader((cls.out/'before-guards').read_text().splitlines()))
        cls.write_rows(cls.out/'target-guards.csv',cls.rows)
        cls.full_guards=cls.out/'qualified-guards.csv';cls.full_guards.write_bytes((cls.out/'before-guards').read_bytes())
        matching.append_guards(cls.full_guards,cls.full_guards.read_bytes(),cls.out/'selected.o')
        cls.guard_bytes=cls.full_guards.read_bytes()
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot,
            filename='generated_AEB40',word_patches_path=cls.out/'target-guards.csv'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.retail
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in (symbols or screen.SYMBOLS).items()],'-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>182I',previous.sections(elf)['.text'][1]))
    def compare(self,memory,arguments,created,forms=None,**settings):
        return super().compare(memory,arguments,created,forms=forms or (self.retail,self.raw,self.fitted),**settings)
    def test_01_full_shape_and_not_byte_exact(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(182,80,125,0,''))
        self.assertEqual(self.fitted,self.retail);self.assertEqual(-self.fitted[0]&65535,56)
        for i in range(182):
            words=list(matching.RAW);words[i]^=1
            with self.assertRaisesRegex(ValueError,'stale complete'):matching.recipe(words)
        text,functions,relocations=previous.parse_object(self.out/'selected.o');start=functions[screen.FUNCTION]['value']
        for offset in matching.RELOCATIONS:
            broken={o:list(v) for o,v in relocations.items()};broken[start+offset]=[('R_MIPS_26','wrong_helper')]
            with patch.object(matching,'parse_object',return_value=(text,functions,broken)):
                with self.assertRaisesRegex(ValueError,'stale complete.*relocations'):matching.guard_rows(self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'stale child.*manifest'):matching.append_guards(self.full_guards,b'wrong\n',self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'already published'):matching.append_guards(self.full_guards,self.guard_bytes,self.out/'selected.o')
        self.assertEqual(len(self.rows),182)
        self.assertTrue(all(r['omit']=='false' and not r['insert_after'] for r in self.rows))
        self.receipt('shape',raw_words=182,raw_frame=80,raw_differences=125,fitted_words=182,fitted_frame=56,
            fitted_differences=0,expectation_rows=182,changed_words=sum(r['expected']!=r['replacement'] for r in self.rows),
            relocation_changed_rows=sum(r['expected_relocations']!=r['replacement_relocations'] for r in self.rows),
            insertions=0,omissions=0,stale_word_controls=182,stale_relocation_controls=len(matching.RELOCATIONS))
    def test_02_domains_boundaries_live_arguments_and_aliases(self):
        super().test_02_domains_boundaries_live_arguments_and_aliases()
        receipt=json.loads((self.out/'guest.json').read_text());receipt['executions']=receipt['cases']*3
        receipt['raw_private_frame_equivalence_not_claimed']=receipt.pop('private_frame_equivalence_not_claimed')
        receipt['fitted_retail_original_private_layout']=True;self.receipt('guest',**receipt)
    def test_03_fired_public_faults_and_unconditional_NULL_access(self):
        triples=0
        for plan in range(7):
            memory,args,created=previous.fixture();models=self.compare(memory,args,created,plan=plan)
            for cut in range(models[0].public_accesses):
                failed=[]
                for code in (self.retail,self.raw,self.fitted):
                    model=previous.ChildOracle(code,memory,args,created,plan=plan);model.public_fault=cut
                    with self.assertRaises(previous.guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(cut,));self.assertEqual(model.public_accesses,cut)
                    failed.append((previous.public(model.memory),previous.public_events(model.events),model.calls))
                self.assertEqual(failed[0],failed[1]);self.assertEqual(failed[0],failed[2]);triples+=1
        memory,args,_=previous.fixture();failed=[]
        for code in (self.retail,self.raw,self.fitted):
            model=previous.ChildOracle(code,memory,args,0)
            with self.assertRaisesRegex(AssertionError,'unmapped write'):model.run()
            self.assertEqual(len(model.calls),3);failed.append(previous.public_events(model.events))
        self.assertEqual(failed[0],failed[1]);self.assertEqual(failed[0],failed[2])
        self.receipt('faults',fired_public_fault_triples=triples,executions=triples*3,NULL_fault_executions=3,
            raw_private_frame_fault_order_not_claimed=True)
    def test_04_effective_fresh_IDO_controls(self):
        super().test_04_effective_fresh_IDO_controls()
        names=('wrong-parent-index','wrong-mask','wrong-copy','wrong-scale-gate','wrong-limit','wrong-toggle','wrong-float-word')
        for name in names:
            with self.assertRaisesRegex(ValueError,'(stale|unexpected) complete'):matching.guard_rows(self.out/(name+'.o'))
        receipt=json.loads((self.out/'negative.json').read_text());receipt['also_rejected_by_normalization']=len(names)
        self.receipt('negative',**receipt)
    def test_05_independent_relocations(self):
        cases=0
        for ordinal in range(3):
            entry=0x15217FFC+ordinal*0x10004
            symbols={n:(0x80117FFC+ordinal*0x20004+i*0x1000 if n.startswith('D_') else
                0x15407FFC+ordinal*0x10004+i*0x100) for i,n in enumerate(previous.S)}
            forms=[self.link(name,entry,symbols) for name in ('original','selected','fitted')]
            self.assertEqual(forms[0],forms[2])
            for plan in range(7):
                memory,args,created=previous.fixture(symbols=symbols);self.compare(memory,args,created,forms=forms,
                    symbols=symbols,entry=entry,plan=plan);cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,
            ten_JAL_sites_and_five_globals_independent=True,all_rematerialized_base_relocations=True)
    def test_06_copied_owner_and_all_unchanged_neighbors(self):
        source=(self.out/'before-source').read_text();obj,warnings=previous.compile_owner(self.root,self.out,source,'owner')
        self.assertEqual(warnings,[])
        subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
            str((self.out/'owner.c').relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
            '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
        self.assertEqual(matching.guard_rows(obj),self.rows);padded=[]
        for name,guards in (('before',self.out/'before-guards'),('after',self.full_guards)):
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_AEB40',str(asm),'--word-patches',str(guards)],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(previous.parse_object(asm.with_suffix('.o')))
        a,b=padded;start=a[1][screen.FUNCTION]['value'];end=start+728
        self.assertEqual(a[0][:start]+a[0][end:],b[0][:start]+b[0][end:]);self.assertEqual(a[1],b[1])
        self.assertEqual({o:v for o,v in a[2].items() if not start<=o<end},{o:v for o,v in b[2].items() if not start<=o<end})
        self.receipt('owner',untouched_neighbors=len(a[1])-1,all_bytes_extents_relocations_exact=True,
            source_unchanged=True,adjacent_helper_placeholders_unchanged=True,diagnostics=0)
    def test_07_whole_linked_installation(self):
        old=(self.out/'before-guards').read_bytes();actual_guards=(self.root/self.paths['guards']).read_bytes()
        if actual_guards==old:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        struct.pack_into('>182I',expected,previous.elf_slot_offset(self.before,screen.ENTRY,728),*self.retail)
        self.assertEqual(bytes(expected),actual);self.assertEqual(previous.metadata(self.before),previous.metadata(actual))
        self.assertEqual(actual_guards,self.guard_bytes);self.assertTrue(actual_guards.startswith(old))
        for name in ('source','progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=previous.audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),all_other_ELF_bytes_and_metadata_exact=True,
            source_and_conversion_rows_unchanged=True,matching_credit_added=1,appended_guard_rows=182,data_audit=audit)
    def test_08_actual_descriptor_caller_and_resource_transition(self):
        original_raw=self.raw
        try:
            super().test_08_actual_descriptor_caller_and_resource_transition();self.raw=self.fitted
            super().test_08_actual_descriptor_caller_and_resource_transition()
        finally:self.raw=original_raw
        receipt=json.loads((self.out/'connected.json').read_text())
        receipt['cases']*=2;receipt['executions']*=2
        receipt['original_raw_and_original_fitted_pairs']=True;receipt['type0_calls_per_pair_form']=receipt.pop('type0_calls_per_form')
        self.receipt('connected',**receipt)
    def test_10_independent_original_private_frame_contract(self):
        cases=0
        for flags,count,active,inherit,phase in itertools.product((0,1,2,3),(-1,0,2),(0,1),(0,1),(0,8)):
            memory,args,created=previous.fixture(flags=flags,count=count,active=active,inherit=inherit)
            for code in (self.retail,self.fitted):
                model=previous.ChildOracle(code,memory,args,created,phase=phase)
                initial=model.memory.copy();frame=previous.STACK+phase-56;expected=[]
                def store(offset,value):
                    previous.put(initial,frame+offset,value);expected.append(('W',frame+offset,4,value&previous.MASK))
                def get(offset):
                    value=previous.read(initial,frame+offset);expected.append(('R',frame+offset,4,value));return value
                for offset,register in ((0x20,19),(0x18,17),(0x14,16),(0x24,31),(0x1C,18)):
                    store(offset,model.r[register])
                store(0x40,args[2]);get(0x40);get(0x40);get(0x48);get(0x40);get(0x50);get(0x4C)
                if flags&1:get(0x40)
                store(0x2C,0)
                if flags&2:store(0x2C,1)
                get(0x40);get(0x40);get(0x54);get(0x2C);get(0x58)
                for offset in (0x24,0x14,0x18,0x1C,0x20):get(offset)
                model.run();events=[e for e in model.events if e[0]!='CALL' and previous.private(e[1])]
                self.assertEqual(events,expected)
                self.assertEqual({a:v for a,v in model.memory.items() if previous.private(a)},
                    {a:v for a,v in initial.items() if previous.private(a)})
                self.assertEqual(model.r[29],previous.STACK+phase)
            cases+=1
        self.receipt('private',cases=cases,executions=cases*2,independent_save_home_mode_restore_contract=True,
            original_0x38_frame_and_untouched_capacity=True,GP_FPR_lifetimes_preserved=True)
    def test_11_fired_complete_access_fault_prefixes_and_private_aliases(self):
        pairs=cases=0
        for plan,phase,count in itertools.product(range(7),(0,8),(-1,2)):
            memory,args,created=previous.fixture(count=count);models=[]
            for code in (self.retail,self.fitted):models.append(previous.ChildOracle(code,memory,args,created,plan=plan,phase=phase).run())
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            for cut in range(models[0].accesses):
                failed=[]
                for code in (self.retail,self.fitted):
                    model=previous.ChildOracle(code,memory,args,created,plan=plan,phase=phase);model.fault=cut
                    with self.assertRaises(previous.guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(cut,));self.assertEqual(model.accesses,cut)
                    failed.append((model.memory,model.events,model.calls,model.r,model.f))
                self.assertEqual(failed[0],failed[1]);pairs+=1
            cases+=1
        aliases=0
        for phase,kind,offset in itertools.product((0,8),('parent','created'),(0x14C,0x270,0x2D0)):
            memory,args,created=previous.fixture();address=previous.STACK+phase-56-offset
            memory.update({address+i:memory.get(address+i,(i*17+35)&255) for i in range(0x400)})
            if kind=='parent':args=(address,*args[1:])
            else:created=address
            models=[previous.ChildOracle(code,memory,args,created,phase=phase).run() for code in (self.retail,self.fitted)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f));aliases+=1
        self.receipt('private-faults',cases=cases,paired_executions=cases*2,fired_full_access_fault_pairs=pairs,
            failed_executions=pairs*2,private_alias_cases=aliases,original_fitted_full_memory_events_GP_FPR_exact=True,
            raw_different_frame_private_equivalence_not_claimed=True)
    def test_12_live_original_private_mode_home(self):
        class Mutated(previous.ChildOracle):
            def hook(self,target):
                super().hook(target)
                if target==previous.S['func_1515D440']:
                    self.put(self.top_stack-56+0x2C,0xFEDCBA98,4)
        cases=0
        for phase,flags in itertools.product((0,8),(0,3)):
            memory,args,created=previous.fixture(flags=flags)
            models=[Mutated(code,memory,args,created,phase=phase).run() for code in (self.retail,self.fitted)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            packet=next(c for c in models[0].calls if c[0]==previous.S['func_150838EC'])
            self.assertEqual(packet[3],0xFEDCBA98);cases+=1
        self.receipt('mode-home',cases=cases,executions=cases*2,live_original_SP_0x2C_callback_mutation=True)
    def test_13_actual_padder_rejects_all_stale_words_and_relocations(self):
        text,functions,relocations=previous.parse_object(self.out/'selected.o');start=functions[screen.FUNCTION]['value']
        for i in range(182):
            broken=bytearray(text);word=struct.unpack_from('>I',broken,start+i*4)[0]
            struct.pack_into('>I',broken,start+i*4,word^1)
            with patch.object(padder,'parse_object',return_value=(bytes(broken),functions,relocations)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):
                    emit_padded_assembly(self.out/'selected.o',self.slot,filename='generated_AEB40',word_patches_path=self.out/'target-guards.csv')
        for offset in matching.RELOCATIONS:
            broken={o:list(v) for o,v in relocations.items()};broken[start+offset]=[('R_MIPS_26','wrong_helper')]
            with patch.object(padder,'parse_object',return_value=(text,functions,broken)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):
                    emit_padded_assembly(self.out/'selected.o',self.slot,filename='generated_AEB40',word_patches_path=self.out/'target-guards.csv')
        self.receipt('production-rejection',stale_words=182,stale_relocations=len(matching.RELOCATIONS),
            identity_rows_checked=True,actual_production_padder=True)


if __name__=='__main__':unittest.main()
