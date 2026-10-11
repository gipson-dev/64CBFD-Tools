"""Freeze the guarded lazy loader and replace its parent-chain model."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_third_resource_loader_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string,parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_resource_extras_match as extras
from tools.tests import test_game_record_resource_cleanup_match as cleanup
from tools.tests import test_game_main_resource_loader as main
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK,BLOCK,OTHER=guest.STACK,0xA0000,0xA1000
REQUEST=screen.SYMBOLS['func_1502B6BC']
RELOCATIONS=[(entry,dict(D_800D1C90=table,func_1502B6BC=request))
    for entry,table,request in ((screen.ENTRY,0x800D1C90,REQUEST),
        (0x15207FFC,0x80107FFC,0x15118004),(0x15318004,0x80118004,0x15207FFC),
        (0x15408000,0x80218000,0x15308004))]


def slot(identity,symbols=screen.SYMBOLS):
    return (symbols['D_800D1C90']+(identity&0xFFFFFFFF)*4)&0xFFFFFFFF


def fixture(identity=7,present=0,value=0x90010000,symbols=screen.SYMBOLS):
    memory={STACK+i:0xA5 for i in range(-0x600,0xC0)}
    address=slot(identity,symbols)
    memory.update({address+i:0xA5 for i in range(8)})
    for base in (BLOCK,OTHER):
        memory.update({base+i:(i*137+19)&255 for i in range(64)})
        put(memory,base,value)
    put(memory,address,present)
    return memory


class Reference:
    def __init__(self,memory,symbols=screen.SYMBOLS,result=BLOCK,actions=(),output=0xDEADBEEF):
        self.memory=memory.copy();self.symbols=symbols;self.result=result;self.actions=actions;self.output=output
        self.events=[];self.calls=[]
    def get(self,location,size=4):
        assert all(location+i in self.memory for i in range(size))
        value=read(self.memory,location,size);self.events.append(('R',location,size,value));return value
    def put(self,location,value,size=4):
        assert all(location+i in self.memory for i in range(size))
        put(self.memory,location,value,size);self.events.append(('W',location,size,value&((1<<(size*8))-1)))
    def run(self,identity=7,unused=0):
        address=slot(identity,self.symbols)
        if self.get(address): return 0
        args=(('private-output',),2,0,2,0x11,identity&0xFFFFFFFF)
        target=self.symbols['func_1502B6BC'];self.calls.append((target,*args));self.events.append(('CALL',target,args))
        for location,value,size in self.actions: self.put(location,value,size)
        if not self.result: self.put(address,0);return 2
        self.put(address,self.result);value=self.get(self.result);self.put(address,value);return 0


class ThirdOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,identity=7,unused=0,phase=0,entry=screen.ENTRY,
            symbols=screen.SYMBOLS,result=BLOCK,actions=(),output=0xDEADBEEF):
        super().__init__(words,memory,arguments=(identity&0xFFFFFFFF,unused&0xFFFFFFFF),phase=phase,entry=entry)
        self.symbols=symbols;self.result=result;self.actions=actions;self.output=output
    def record_call(self,target):
        assert target==self.symbols['func_1502B6BC']
        args=(('private-output',),*self.r[5:8],read(self.memory,self.r[29]+16),read(self.memory,self.r[29]+20))
        self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.symbols['func_1502B6BC']
        self.put(self.r[4],self.output,4)
        for location,value,size in self.actions: self.put(location,value,size)
        extras.clobber(self,self.result)


class GameThirdResourceLoaderMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-third-resource-loader-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',makefile='conker/Makefile')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            values={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                values[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(values,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='f580435626504c2fda5ecf8b7fa7a87feaf4d1f2a1332be1118923a6492e5dcb'
        assert cls.baseline['elf']=='9f2c45ce2994dafadbaa9bce9c640e61852b6f2ebf4d2a34a41d1d1438bbcb25'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>36I',cls.rom,screen.ROM));cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        assembly=(cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+assembly+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream);cls.fields=reader.fieldnames;cls.all_rows=list(reader)
        cls.rows=[row for row in cls.all_rows if row['filename']=='generated_6A3D0' and row['function']==screen.FUNCTION]
        cls.target_guards=cls.out/'target-guards.csv'
        with cls.target_guards.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=cls.fields);writer.writeheader();writer.writerows(cls.rows)
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot,
            word_patches_path=cls.target_guards,filename='generated_6A3D0'))
        cls.helpers={}
        for entry,rom,count in ((0x1503D5F0,0x6AAA0,28),(0x1502B5C8,0x58A78,61),(0x1503D45C,0x6A90C,10),
                (0x1503D484,0x6A934,35),(0x1503D438,0x6A8E8,9),(0x1503D510,0x6A9C0,56),
                (cleanup.screen.ENTRY,cleanup.screen.ROM,43),(cleanup.RELEASE,0x13AC5C,46),(screen.ENTRY,screen.ROM,36)):
            actual=list(struct.unpack_from('>%dI'%count,cls.before,elf_slot_offset(cls.before,entry,count*4)))
            assert actual==list(struct.unpack_from('>%dI'%count,cls.rom,rom))
            cls.helpers.update({entry+i*4:w for i,w in enumerate(actual)})
        cls.release_words={address:word for address,word in cls.helpers.items()
            if cleanup.RELEASE<=address<cleanup.RELEASE+46*4}
    def receipt(self,name,**values): (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def link(self,name,entry=screen.ENTRY,symbols=screen.SYMBOLS):
        script=self.out/'link.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        count=parse_object(self.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))
    @property
    def padded(self): return self.link('padded')
    def compare(self,memory,identity=7,unused=0,result=BLOCK,actions=(),output=0xDEADBEEF,phase=0,
            forms=None,entry=screen.ENTRY,symbols=screen.SYMBOLS):
        reference=Reference(memory,symbols,result,actions,output);status=reference.run(identity,unused)
        models=[ThirdOracle(words,memory,identity,unused,phase,entry,symbols,result,actions,output).run()
            for words in (forms or (self.retail,self.raw,self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls,model.r[2]),
                (preparation.public(reference.memory),reference.events,reference.calls,status))
        if forms is None:
            self.assertEqual((models[0].memory,models[0].events,models[0].r),(models[2].memory,models[2].events,models[2].r))
        return models
    def test_01_banked_raw_and_complete_existing_guarded_slot(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(37,48,15))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.padded,self.retail);self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(len(self.rows),7);self.assertEqual(sum(row['omit']=='true' for row in self.rows),1)
        self.assertEqual([int(row['offset'],0) for row in self.rows],[0x38,0x50,0x5C,0x60,0x64,0x74,0x78])
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],144)
        self.receipt('shape',raw_words=37,raw_differences=15,linked_words=36,frame=48,
            existing_normalizations=6,existing_drops=1,new_guards=0,direct_match=False)
    def test_02_presence_full_identity_result_payload_unused_and_phase_matrix(self):
        cases=0;reached=set();forms=(self.retail,self.raw,self.padded)
        for identity,present,result,value,unused,phase in itertools.product((0,7,36,186,255,256,-1,0x80000000),
                (0,1,0xFFFFFFFF),(0,BLOCK),(0,1,0x80000000,0xFFFFFFFF),(0,0xDEADBEEF),(0,8)):
            models=self.compare(fixture(identity,present,value),identity,unused,result,phase=phase,forms=forms)
            reached.update(models[0].visits);cases+=1
        self.assertEqual(len(reached&set(range(screen.ENTRY,screen.ENTRY+144,4))),36)
        self.receipt('guest',cases=cases,forms=3,reached_words=36,raw_public_semantics_only=True,
            present_skips_request_without_header_read=True,invalid_keys_mapped_guest_only=True)
    def test_03_cached_slot_callback_header_and_publication_aliases(self):
        cases=0
        for identity,result,phase in itertools.product((7,36),(0,BLOCK),(0,8)):
            for actions in (((slot(identity),OTHER,4),),((BLOCK,0xFFFFFFFF,4),),
                    ((slot(identity)+4,0x80000000,4),(BLOCK,0,4))):
                self.compare(fixture(identity),identity,result=result,actions=actions,phase=phase);cases+=1
        for result,phase in itertools.product((slot(7),slot(7)+4),(0,8)):
            self.compare(fixture(),result=result,phase=phase);cases+=1
        self.receipt('aliases',cases=cases,cached_destination_slot_and_live_returned_header=True,
            first_publication_precedes_aliased_header_read=True,guest_aliases_not_portable_object_layout=True)
    def test_04_independent_global_and_request_rebases(self):
        cases=0
        for entry,symbols in RELOCATIONS:
            forms=[self.link(name,entry,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms[0],forms[2])
            for identity,present,result,phase in itertools.product((7,256),(0,1),(0,BLOCK),(0,8)):
                self.compare(fixture(identity,present,symbols=symbols),identity,result=result,phase=phase,
                    forms=forms,entry=entry,symbols=symbols);cases+=1
        self.receipt('rebases',links=4,cases=cases,global_HI_LO_and_request_JAL=True)
    def test_05_all_original_fitted_fault_prefixes_including_private_stack(self):
        pairs=0;fitted=self.padded
        for present,result,phase in itertools.product((0,1),(0,BLOCK),(0,8)):
            memory=fixture(present=present);complete=ThirdOracle(self.retail,memory,result=result,phase=phase).run()
            for ordinal in range(complete.accesses):
                models=[ThirdOracle(words,memory,result=result,phase=phase) for words in (self.retail,fitted)]
                for model in models:
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r),
                    (models[1].memory,models[1].events,models[1].calls,models[1].r));pairs+=1
        self.receipt('faults',fired_original_fitted_pairs=pairs,full_private_public_prefixes_exact=True,
            raw_private_layout_deliberately_not_called_exact=True)
    def test_06_effective_compiled_semantic_controls(self):
        controls=(('gate','*slot != NULL','*slot == NULL',dict(present=1),dict()),
            ('status','return 2;','return 4;',dict(),dict(result=0)),
            ('path','2, 0x11, arg0','2, 0x10, arg0',dict(),dict()),
            ('header','*(struct124 **)loaded','(struct124 *)loaded',dict(),dict()),
            ('publication','    *slot = (struct124 *)loaded;\n','',dict(),dict(result=slot(7))))
        for name,before,after,inputs,args in controls:
            body=screen.ORIGINAL.replace(before,after);self.assertNotEqual(body,screen.ORIGINAL)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(fixture(**inputs),forms=(words,),**args)
        self.receipt('controls',fresh_effective_semantic_mutations=5)
    def test_07_whole_owner_both_profiles_padders_and_existing_neighbors(self):
        run=subprocess.run;objects={}
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        source=(self.out/'before-source').read_text()
        for profile in ('owner','unrolled'):
            with patch('subprocess.run',side_effect=compact if profile=='owner' else run):
                objects[profile],diagnostics=compile_owner(self.root,self.out,source,profile)
            self.assertEqual(diagnostics,[])
            text,functions,relocations=parse_object(objects[profile]);target=functions[screen.FUNCTION];start=target['value']
            selected=parse_object(self.out/'selected.o')
            self.assertEqual((target['size'],text[start:start+target['size']],
                {o-start:v for o,v in relocations.items() if start<=o<start+target['size']}),
                (selected[1][screen.FUNCTION]['size'],selected[0][:target['size']],selected[2]))
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
        for route in ('pad_c_object.py','pad_generated_object.py'):
            asm=self.out/(route+'.s')
            args=[str(objects['owner']),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                str(objects['owner']),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
            args+=['--word-patches',str(self.out/'before-guards'),'--function-object','func_1503D804='+str(objects['unrolled'])]
            subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            parsed=parse_object(asm.with_suffix('.o'));routes.append(parsed)
            definitions={name:symbols[name] for values in parsed[2].values() for kind,name in values
                if name not in parsed[1]}
            script=self.out/(route+'.ld');script.write_text('SECTIONS { .text 0x1503CF20 : SUBALIGN(4) { *(.text) } }\n')
            elf=script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1503CF20',
                *['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(asm.with_suffix('.o'))],
                check=True,capture_output=True)
            resolved.append(sections(elf)['.text'][1])
        self.assertEqual(routes[0],routes[1]);text,functions,relocations=routes[0]
        owner_entry=0x1503CF20;linked=elf_slot_offset(self.before,owner_entry,len(text))
        self.assertEqual(resolved[0],resolved[1])
        self.assertEqual(resolved[0],self.before[linked:linked+len(text)])
        for name,info in functions.items():
            address=owner_entry+info['value'];extent=installed.symbol_size_offset(self.before,name,address)
            self.assertEqual(info['size'],struct.unpack_from('>I',self.before,extent)[0],name)
        self.assertEqual(len(text),0x1503DDD0-owner_entry);self.assertEqual(len(functions),15)
        self.receipt('owner',functions=15,neighbors=14,actual_padders=2,diagnostics=0,
            complete_owner_paths_equal_existing_D804_selection=True,all_linked_extents_preserved=True,
            complete_resolved_owner_bytes_equal_current_ELF=True)
    def test_08_literal_frozen_all_inputs_whole_ELF_guards_and_data(self):
        from tools.experiments import game_third_resource_loader_lifetime_candidates as third
        views=dict(source=third.historical_source(self.root).encode('ascii'),guards=third.historical_guards(self.root))
        for name,path in self.paths.items():
            actual=views[name] if name in views else (self.root/path).read_bytes()
            self.assertEqual(actual,(self.out/('before-'+name)).read_bytes(),path)
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',ELF_changes=0,recipe_changes=0,matching_credit=0,protected_data=audit,
            historical_source_guard_view_exact=True,all_other_seven_inputs_literal_exact=True,
            successor_projection_used=views['source']!=(self.root/screen.SOURCE).read_bytes())
    def test_09_native32_all_low_halfword_payloads_keys_unused_and_callbacks(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.ORIGINAL+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',NATIVE+screen.ORIGINAL.replace('return 2;','return 4;')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',profiles=['O2','O0'],low_halfword_payload_cases=65536,upper_halfword=65535,matrix_cases=6144,
            valid_native_fixture_identities_only=True,callback_alias_and_status_reference=True,effective_status_control=True)
    def test_10_each_existing_guard_expected_word_and_relocation_rejects(self):
        cases=0
        for row in self.rows:
            for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_26:func_1502B6BC')):
                rows=[dict(item) for item in self.rows];index=self.rows.index(row);rows[index][field]=value
                target=self.out/'wrong-guards.csv'
                with target.open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=self.fields);writer.writeheader();writer.writerows(rows)
                with self.assertRaises(ValueError): emit_padded_assembly(self.out/'selected.o',self.slot,
                    word_patches_path=target,filename='generated_6A3D0')
                cases+=1
        self.receipt('guards',effective_expected_word_relocation_rejections=cases,all_seven_rows_retained=True)
    def test_11_fresh_discriminating_direct_match_probes_are_not_qualified(self):
        variants=dict(screen.candidates());measured=[]
        for name in ('banked','success-first','publish-request','labelled-success-void','outer-null'):
            meta,words=screen.compile_candidate(self.root,self.out,'probe-'+name,variants[name])
            self.assertGreater(meta['differences'],0);measured.append(meta)
        self.receipt('diagnostics',measurements=measured,no_direct_source_selected=True,no_guard_or_profile_changes=True)
    def test_12_actual_seventeen_body_parent_chain_with_third_hook_removed(self):
        old_oracle,old_reference,old_fixture=main.MainOracle,main.Reference,main.fixture
        reached=set();requests=dict(success=0,failure=0)
        words=self.retail.copy();mapping={screen.ENTRY+i*4:w for i,w in enumerate(words)}
        third_block=0xA2000
        class WithThird(old_oracle):
            def __init__(model,*args,**kwargs):
                connected=dict(kwargs.get('connected') or {});connected.update(mapping);kwargs['connected']=connected
                super().__init__(*args,**kwargs)
            def hook(model,target):
                if target==REQUEST and model.r[5]==2 and model.r[7]==2 and read(model.memory,model.r[29]+16)==0x11:
                    model.put(model.r[4],0xDEADBEEF,4)
                    failed=main.helper(model,'third');requests['failure' if failed else 'success']+=1
                    extras.clobber(model,0 if failed else third_block);return
                return super().hook(target)
            def run(model):
                result=super().run();reached.update(model.visits&set(mapping));return result
        class WithReference(old_reference):
            def call(model,role,*args):
                if role!='third': return super().call(role,*args)
                target=main.S[main.ROLES[role]];model.calls.append((target,*args));model.events.append(('CALL',target,args))
                child=Reference(model.memory,result=0 if model.results.get('third') else third_block,
                    actions=model.actions.get(('third',model.numbers.get('third',0)),()))
                model.numbers['third']=model.numbers.get('third',0)+1
                status=child.run(*args);model.memory=child.memory;model.events.extend(child.events);model.calls.extend(child.calls);return status
        def mapped(*args,**kwargs):
            memory=old_fixture(*args,**kwargs);memory.update({third_block+i:0xA5 for i in range(64)})
            identity=kwargs.get('identity',args[0] if args else 7)
            address=slot(identity);memory.update({address+i:0 for i in range(4)})
            put(memory,third_block,0xA3000)
            return memory
        saved=self.retail,self.raw
        self.retail=self.raw=list(struct.unpack_from('>43I',self.rom,cleanup.screen.ROM))
        try:
            with patch.object(main,'MainOracle',WithThird),patch.object(main,'Reference',WithReference),patch.object(main,'fixture',mapped):
                cleanup.GameRecordResourceCleanupMatchTests.test_12_actual_sixteen_body_parent_failure_chain_cleanup_hook_removed(self)
        finally:self.retail,self.raw=saved
        nested=json.loads((self.out/'parent-cleanup-chain.json').read_text())
        self.assertEqual((nested['cases'],nested['executions']),(1920,3840))
        self.assertGreater(len(reached),30)
        self.assertGreater(requests['success'],0);self.assertGreater(requests['failure'],0)
        self.receipt('parent-third-chain',cases=1920,executions=3840,reached_third_words=len(reached),
            actual_third_request_outcomes=requests,
            actual_seventeen_body_chain_including_guarded_third36=True,third_hook_removed=True,
            former_generic_third_failure_now_drives_real_request_null_status_two=True,
            cached_slot_and_success_first_word_publications_real=True,
            deeper_request_lookup_allocator_heap_hardware_runtime_bounded=True)


NATIVE=r'''#define NULL ((void *)0)
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef struct struct124 {u32 first;} struct124;
struct124 *D_800D1C90[256];static u32 block[4],other[4];static int id,mode,failure,calls,error;static u32 payload;
void *func_1502B6BC(s32 *size,s32 depth,s32 *out,s32 kind,...){__builtin_va_list ap;int path,key;
    __builtin_va_start(ap,kind);path=__builtin_va_arg(ap,int);key=__builtin_va_arg(ap,int);__builtin_va_end(ap);
    calls++;if(depth!=2 || out!=NULL || kind!=2 || path!=0x11 || key!=id)error=1;*size=(s32)0xDEADBEEFU;
    if(mode==1)D_800D1C90[id]=(struct124 *)other;
    if(mode==2)block[0]=payload^0x80000000U;
    return failure?NULL:mode==3?(void *)&D_800D1C90[id]:(void *)block;
}
s32 func_1503D774(s32,s32);
static int check(int key,int present,int fail,int action,u32 value,int unused){int i;u32 expected;int active=!present;
    id=key;mode=action;failure=fail;payload=value;calls=error=0;
    for(i=0;i<256;i++)D_800D1C90[i]=(struct124 *)(0x80010000U+(u32)i);
    D_800D1C90[id]=present?(struct124 *)other:NULL;block[0]=value;
    for(i=1;i<4;i++){block[i]=other[i]=0xA5000000U+(u32)i;}other[0]=0xC1000000U;
    if(func_1503D774(key,unused)!=(active && fail?2:0) || error || calls!=active)return 1;
    expected=present?(u32)other:fail?0U:action==3?(u32)&D_800D1C90[id]:action==2?value^0x80000000U:value;
    for(i=0;i<256;i++)if((u32)D_800D1C90[i]!=(i==id?expected:0x80010000U+(u32)i))return 2;
    if(block[0]!=(active && action==2?value^0x80000000U:value) || other[0]!=0xC1000000U)return 3;
    for(i=1;i<4;i++)if(block[i]!=0xA5000000U+(u32)i || other[i]!=0xA5000000U+(u32)i)return 4;
    return 0;
}
'''
NATIVE_MAIN=r'''
static int run(void){int key,p,f,m,u,r;u32 value;
    for(value=0;value<65536U;value++){r=check(7,0,0,0,0xFFFF0000U+value,0);if(r)return r;}
    for(key=0;key<256;key++)for(p=0;p<2;p++)for(f=0;f<2;f++)for(m=0;m<3;m++)for(u=0;u<2;u++){
        r=check(key,p,f,m,0x80000000U+(u32)key,u?(int)0xDEADBEEFU:0);if(r)return r;}
    for(p=0;p<2;p++)for(f=0;f<2;f++){r=check(7,p,f,3,0xFFFFFFFFU,123);if(r)return r;}
    return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
