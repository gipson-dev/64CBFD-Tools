"""Qualify the complete group publication propagation and connected finish helper."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_group_publication_propagation_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_descriptor_resource_loader_match as descriptor
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, MEMBERS = guest.STACK, 0x78000
LINKS = [(entry, dict(zip(screen.SYMBOLS,(
    0x80107FFC+carry,0x80118004-carry,0x80128004+carry,0x80137FFC-carry))))
    for entry,carry in itertools.product((screen.ENTRY,0x15207FFC,0x15318004),(0,8,0x10000))]
LINKS[0] = (screen.ENTRY,screen.SYMBOLS)


def fixture(groups=(),identity=7,value=0x8001,symbols=screen.SYMBOLS):
    memory = {STACK+i:0xA5 for i in range(-0x600,0xC0)}
    for name,size in (('D_80098888',256),('D_80084410',20),('D_800D1588',1024),('D_800C5A90',512)):
        memory.update({symbols[name]+i:0xA5 for i in range(size)})
    for group in range(5):
        values = groups[group] if group<len(groups) else ()
        base = MEMBERS+group*512
        memory.update({base+i:0 for i in range(512)})
        memory[symbols['D_80098888']+group]=len(values)
        put(memory,symbols['D_80084410']+group*4,base)
        for index,member in enumerate(values): memory[base+index]=member
    for index in range(256):
        put(memory,symbols['D_800D1588']+index*4,0x80010000+index)
        put(memory,symbols['D_800C5A90']+index*2,0xA500+index,2)
    for name,size in (('D_800D1588',4),('D_800C5A90',2)):
        address=(symbols[name]+(identity&0xFFFFFFFF)*size)&0xFFFFFFFF
        memory.update({address+i:0xA5 for i in range(size)})
    put(memory,(symbols['D_800C5A90']+(identity&0xFFFFFFFF)*2)&0xFFFFFFFF,value,2)
    return memory


def propagate(memory,identity,symbols=screen.SYMBOLS):
    events=[]
    def get(address,size):
        address&=0xFFFFFFFF
        assert all(address+i in memory for i in range(size)),('unmapped reference read',address,size)
        value=read(memory,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size):
        address&=0xFFFFFFFF
        assert all(address+i in memory for i in range(size)),('unmapped reference write',address,size)
        put(memory,address,value,size);events.append(('W',address,size,value&((1<<(size*8))-1)))
    identity&=0xFFFFFFFF
    for group in range(5):
        count=get(symbols['D_80098888']+group,1)
        if not count: continue
        members=get(symbols['D_80084410']+group*4,4)
        for index in range(count):
            if identity==get(members+index,1):
                for copied in range(count):
                    member=get(members+copied,1)
                    pointer=get(symbols['D_800D1588']+identity*4,4)
                    store(symbols['D_800D1588']+member*4,pointer,4)
                    member=get(members+copied,1)
                    value=get(symbols['D_800C5A90']+identity*2,2)
                    store(symbols['D_800C5A90']+member*2,value,2)
                return events
    return events


def map_publications(memory):
    for name,size in (('D_800D1588',1024),('D_800C5A90',512)):
        base=screen.SYMBOLS[name]
        for index in range(size): memory.setdefault(base+index,0xA5)
    return memory


class WithPropagationReference(descriptor.Reference):
    def call(self,role,*args):
        if role!='finish': return super().call(role,*args)
        target=self.symbols[descriptor.ROLES[role]]
        self.record(target,args)
        self.events.extend(propagate(self.memory,args[0]))
        return 0


class GameGroupPublicationPropagationMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-group-publication-propagation-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',makefile='conker/Makefile')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            values={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                values[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(values,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']==screen.DESCRIPTOR_SOURCE_SHA
        assert cls.baseline['elf']=='08eef58ac95303c6e5dd3169a2daad0725d654bc767a16e5538b8ea8d222a973'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>56I',cls.rom,screen.ROM))
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        body=(cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot))
        cls.helpers={}
        for entry,rom,words in ((0x1503D5F0,0x6AAA0,28),(0x1502B5C8,0x58A78,61),
                (0x1503D45C,0x6A90C,10),(0x1503D484,0x6A934,35),(0x1503D438,0x6A8E8,9)):
            actual=list(struct.unpack_from('>%dI'%words,cls.before,elf_slot_offset(cls.before,entry,words*4)))
            assert actual==list(struct.unpack_from('>%dI'%words,cls.rom,rom))
            cls.helpers.update({entry+i*4:word for i,word in enumerate(actual)})
        cls.helpers.update({screen.ENTRY+i*4:word for i,word in enumerate(cls.raw)})

    def receipt(self,name,**values): (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def link(self,name,entry=screen.ENTRY,symbols=screen.SYMBOLS):
        script=self.out/'link.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],
            check=True,capture_output=True)
        count=parse_object(self.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))
    @property
    def padded(self):
        if not hasattr(type(self),'_padded_words'): type(self)._padded_words=self.link('padded')
        return type(self)._padded_words
    def compare(self,memory,identity=7,forms=None,entry=screen.ENTRY,symbols=screen.SYMBOLS,phase=0):
        expected=memory.copy();events=propagate(expected,identity,symbols)
        models=[guest.AttachmentOracle(words,memory,arguments=(identity&0xFFFFFFFF,0xDEADBEEF,0x12345678,0x80000000),
            entry=entry,phase=phase).run() for words in (forms or (self.retail,self.raw,self.padded))]
        for model in models:
            self.assertEqual((model.memory,model.events,model.calls),(expected,events,[]))
        return models

    def test_01_complete_direct_leaf_both_profiles_and_original_control(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(56,0,0))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.raw,self.retail);self.assertEqual(self.padded,self.retail)
        self.assertEqual(self.link('original'),self.retail)
        meta,words=screen.compile_candidate(self.root,self.out,'retail-profile',profile='retail')
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences']),(56,0,0));self.assertEqual(words,self.retail)
        self.receipt('shape',words=56,direct_words=56,frame=0,new_guards=0,no_profile_recipe_or_global_declaration_changes=True)

    def test_02_all_groups_empty_late_duplicates_full_word_keys_and_maximum_counts(self):
        cases,reached=0,set()
        for identity,winner,length,value,phase in itertools.product((0,7,36,127,255,256,-1,0x80000000,0x7FFFFFFF),
                range(6),(0,1,3,255),(0,0x7FFF,0x8000,0xFFFF),(0,8)):
            groups=[()]*5
            if winner<5:
                groups[winner]=tuple([((identity+1)&255)]*max(0,length-1)+([identity&255] if length else []))
                if winner<4: groups[winner+1]=(identity&255,1,2)
            models=self.compare(fixture(groups,identity,value),identity,phase=phase)
            for model in models: reached.update(model.visits)
            cases+=1
        self.assertEqual(len(reached&set(range(screen.ENTRY,screen.ENTRY+224,4))),56)
        self.receipt('guest',cases=cases,forms=3,reached_words=56,first_matching_group_only=True,
            full_word_identity_no_narrowing_invalid_keys_mapped_guest_only=True,maximum_count=255)

    def test_03_cached_count_list_and_live_source_member_alias_order(self):
        cases=0
        for alias,phase in itertools.product(('pointer','halfword','counts'),(0,8)):
            memory=fixture(((7,12,33),),7)
            base=dict(pointer=screen.SYMBOLS['D_800D1588']+12*4,
                halfword=screen.SYMBOLS['D_800C5A90']+7*2,
                counts=screen.SYMBOLS['D_80098888'])[alias]
            put(memory,screen.SYMBOLS['D_80084410'],base)
            for index,member in enumerate((7,12,33,7,0,0,0)): memory[base+index]=member
            self.compare(memory,7,phase=phase);cases+=1
        for name,phase in itertools.product(('D_80098888','D_80084410'),(0,8)):
            symbols=dict(screen.SYMBOLS)
            symbols[name]=symbols['D_800D1588']+12*4
            memory=fixture(((7,12,33),),7,symbols=symbols)
            put(memory,symbols['D_800D1588']+7*4,0x80010007)
            memory[symbols['D_80098888']]=3
            put(memory,symbols['D_80084410'],MEMBERS)
            forms=[self.link(form,screen.ENTRY,symbols) for form in ('original','selected','padded')]
            models=self.compare(memory,7,forms= forms,symbols=symbols,phase=phase)
            changed=read(models[0].memory,symbols[name],1 if name=='D_80098888' else 4)
            self.assertEqual(changed,0x80 if name=='D_80098888' else 0x80010007)
            cases+=1
        for value in (0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
            memory=fixture(((7,7,12,7,255),),7)
            put(memory,screen.SYMBOLS['D_800D1588']+7*4,value)
            self.compare(memory);cases+=1
        self.receipt('aliases',cases=cases,cached_count_and_group_pointer_live_source_values=True,
            member_reread_between_pointer_and_halfword_stores=True,guest_aliases_not_portable_host_layout=True)

    def test_04_independent_four_global_relocations_identities_and_unused_registers(self):
        cases=0
        for entry,symbols in LINKS:
            forms=[self.link(name,entry,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms[0],forms[1]);self.assertEqual(forms[0],forms[2])
            for identity,winner,phase in itertools.product((7,256),(0,4,5),(0,8)):
                groups=[()]*5
                if winner<5: groups[winner]=(identity&255,12,33)
                self.compare(fixture(groups,identity,symbols=symbols),identity,forms,entry,symbols,phase);cases+=1
        self.receipt('rebases',links=len(LINKS),cases=cases,four_independent_HI_LO_carries=True)

    def test_05_every_leaf_public_access_fault_prefix_fires(self):
        triples=0
        for groups,identity in (((),7),(((7,12,33),),7),(((),(),(),(),(1,2,7)),7),(((1,2),),256)):
            memory=fixture(groups,identity)
            complete=guest.AttachmentOracle(self.retail,memory,arguments=(identity,),entry=screen.ENTRY).run()
            for ordinal in range(complete.accesses):
                models=[guest.AttachmentOracle(words,memory,arguments=(identity,),entry=screen.ENTRY)
                    for words in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                for model in models[1:]:
                    self.assertEqual((model.memory,model.events,model.calls,model.r),(models[0].memory,models[0].events,models[0].calls,models[0].r))
                triples+=1
        self.receipt('faults',fired_original_raw_padded_triples=triples,all_partial_memory_events_calls_and_registers_exact=True)

    def test_06_effective_compiled_semantic_and_stale_install_controls(self):
        controls=(('groups','group < 5','group < 4',(((),(),(),(),(7,12,33))),7),
            ('key','s32 identity','u8 identity',((0,12,33),),256),
            ('pointer','D_800D1588[identity]','D_800D1588[0]',((7,12,33),),7),
            ('count','[identity];','[0];',((7,12,33),),7),
            ('member','[group][copy]','[group][0]',((7,12,33),),7))
        for name,before,after,groups,identity in controls:
            body=screen.QUALIFIED.replace(before,after);self.assertNotEqual(body,screen.QUALIFIED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(fixture(groups,identity),identity,forms=(words,))
        before=(self.out/'before-source').read_text()
        for wrong in (before.replace(screen.ORIGINAL,''),before+screen.ORIGINAL):
            with self.assertRaises(ValueError): screen.install(wrong)
        self.receipt('controls',effective_compiled_mutations=len(controls),stale_install_rejections=2)

    def test_07_complete_mixed_owner_both_padders_and_all_neighbors(self):
        before=(self.out/'before-source').read_text();run=subprocess.run;objects={}
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for profile in ('owner','unrolled'):
            for stage,source in (('before',before),('after',screen.install(before))):
                with patch('subprocess.run',side_effect=compact if profile=='owner' else run):
                    obj,diagnostics=compile_owner(self.root,self.out,source,profile+'-'+stage)
                self.assertEqual(diagnostics,[]);objects[profile,stage]=obj
        def fingerprint(obj,name):
            text,functions,relocations=parse_object(obj);info=functions[name];start=info['value'];end=start+info['size']
            return info['size'],text[start:end],{o-start:v for o,v in relocations.items() if start<=o<end}
        names=set(parse_object(objects['owner','before'])[1])
        for profile in ('owner','unrolled'):
            for name in names-{screen.FUNCTION}:
                self.assertEqual(fingerprint(objects[profile,'before'],name),fingerprint(objects[profile,'after'],name),name)
            self.assertEqual(normalized_pools(objects[profile,'before']),normalized_pools(objects[profile,'after']))
            self.assertEqual(fingerprint(objects[profile,'after'],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage in ('before','after'):
                asm=self.out/(route+'-'+stage+'.s')
                args=[str(objects['owner',stage]),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                    str(objects['owner',stage]),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
                args+=['--word-patches',str(self.out/'before-guards'),'--function-object','func_1503D804='+str(objects['unrolled',stage])]
                subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value'];expected=bytearray(parsed[0][0])
            expected[start:start+224]=parsed[1][0][start:start+224];self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start<=o<start+224},
                {o:v for o,v in parsed[1][2].items() if not start<=o<start+224})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors=len(names)-1,actual_padders=2,owner_diagnostics=0,
            all_other_bytes_extents_relocations_pools_and_69_word_caller_exact=True,existing_D804_selector_unchanged=True)

    def test_08_immutable_actual_whole_ELF_and_every_assignment_input(self):
        for name in self.paths: self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source=(self.out/'before-source').read_text();source=(self.root/screen.SOURCE).read_text();now=source!=before_source
        self.assertEqual(source,screen.install(before_source) if now else before_source)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,224);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if now: struct.pack_into('>56I',expected,start,*self.retail);struct.pack_into('>I',expected,extent,224)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=now,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[start:start+224],actual[start:start+224])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            all_other_ELF_bytes_metadata_data_guards_recipe_conversion_inputs_exact=True,protected_data=audit)

    def test_09_native32_all_halfwords_all_byte_identities_and_maximum_groups(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace('group < 5','group < 4')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=71680,
            all_65536_halfword_payloads_and_256_fixture_identities=True,maximum_255_member_group=True,
            full_pointer_and_halfword_arrays_first_group_only=True,effective_negative_control=True,
            native32_no_strict_aliasing_not_64_bit_or_hardware=True)

    def test_10_exact_successor_projection_and_effective_rejections(self):
        before=(self.out/'before-source').read_text();qualified=screen.install(before)
        source_path,elf_path=self.root/screen.SOURCE,self.root/self.paths['elf'];rt,rb=Path.read_text,Path.read_bytes
        start=elf_slot_offset(self.before,screen.ENTRY,224);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        current=bytearray(self.before);struct.pack_into('>56I',current,start,*self.retail);struct.pack_into('>I',current,extent,224)
        def source(body): return patch.object(Path,'read_text',lambda path,*a,**kw:body if path==source_path else rt(path,*a,**kw))
        def elf(data): return patch.object(Path,'read_bytes',lambda path:bytes(data) if path==elf_path else rb(path))
        with source(qualified),elf(current):
            self.assertEqual(screen.descriptor_source(self.root),before);self.assertEqual(screen.descriptor_elf(self.root,self.before),self.before)
        for wrong in (qualified.replace('group < 5','group < 4',1),qualified.replace('void func_1503D510','s32 func_1503D510'),qualified+'\n'):
            with source(wrong),self.assertRaises(AssertionError): screen.descriptor_source(self.root)
        for offset in (start+4,extent+3):
            wrong=current.copy();wrong[offset]^=1
            with source(qualified),elf(wrong),self.assertRaises(AssertionError): screen.descriptor_elf(self.root,self.before)
        wrong=current.copy();wrong[start+224]^=1;expected=bytearray(self.before);expected[start+224]^=1
        with source(qualified),elf(wrong): self.assertEqual(screen.descriptor_elf(self.root,self.before),bytes(expected))
        self.receipt('historical',source_rejections=3,word_extent_rejections=2,
            exact_body_full_slot_extent_only=True,immutable_baselines_not_refreshed_unrelated_bytes_preserved=True)

    def test_11_actual_seven_body_descriptor_chain_and_real_finish_publications(self):
        cases,reached=0,set()
        words=list(struct.unpack_from('>69I',self.rom,descriptor.screen.ROM))
        for identity,present,mask,count,mode,phase in itertools.product((7,36,3,186,255,256),
                (False,True),(0,1,7),(0,1,3),(0,1,2,3),(0,8)):
            memory=map_publications(descriptor.helper_fixture(identity,present,mask,count))
            reference=WithPropagationReference(memory,helpers=True,mode=mode);status=reference.run(identity)
            for raw in (words,list(struct.unpack_from('>69I',self.before,elf_slot_offset(self.before,descriptor.screen.ENTRY,276)))):
                model=descriptor.DescriptorOracle(raw,memory,identity=identity,result=descriptor.BLOCK,
                    helpers=True,mode=mode,phase=phase,entry=descriptor.screen.ENTRY,connected=self.helpers).run()
                self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls,model.r[2]),
                    (preparation.public(reference.memory),preparation.events(reference.events),reference.calls,status))
                reached.update(model.visits&set(range(screen.ENTRY,screen.ENTRY+224,4)))
            cases+=1
        self.assertEqual(len(reached),56)
        self.receipt('helpers',cases=cases,executions=cases*2,reached_finish_words=len(reached),
            actual_69_28_61_10_35_9_56_word_chain=True,no_finish_hook_real_failure_and_success_group_publications=True,
            deeper_lookup_and_block_loaders_remain_bounded=True)

    def test_12_actual_fourteen_body_parent_chain_with_finish_hook_removed(self):
        original_fixture=descriptor.helper_fixture
        def mapped(*args,**kwargs): return map_publications(original_fixture(*args,**kwargs))
        raw=self.raw;self.raw=list(struct.unpack_from('>69I',self.rom,descriptor.screen.ROM))
        try:
            with patch.object(descriptor,'Reference',WithPropagationReference),patch.object(descriptor,'helper_fixture',mapped):
                descriptor.GameDescriptorResourceLoaderMatchTests.test_12_actual_parent_pair_and_descriptor_helper_chain_with_real_failure_four(self)
        finally: self.raw=raw
        nested=json.loads((self.out/'descriptor-chain.json').read_text())
        self.assertEqual((nested['cases'],nested['executions']),(1920,3840))
        self.receipt('parent-chain',cases=nested['cases'],executions=nested['executions'],
            actual_fourteen_body_chain_including_56_word_finish=True,finish_hook_removed=True,
            original_descriptor_all_69_words_still_reached=True,deeper_third_lookup_heap_hardware_runtime_bounded=True)


NATIVE = r'''#define NULL ((void *)0)
typedef unsigned char u8;typedef short s16;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u8 D_80098888[5],members[5][256];u8 *D_80084410[5],*D_800D1588[256],*expected[256];s16 D_800C5A90[256],counts[256];
void func_1503D510(s32);
static int check(int identity,int winner,int scenario,u32 value){
    int group,index;u32 count;
    for(index=0;index<256;index++){D_800D1588[index]=expected[index]=(u8 *)(0x80010000U+(u32)index);
        D_800C5A90[index]=counts[index]=(s16)(0xA500U+(u32)index);}
    D_800C5A90[identity]=counts[identity]=(s16)value;
    for(group=0;group<5;group++){
        D_80084410[group]=members[group];D_80098888[group]=0;
        for(index=0;index<256;index++)members[group][index]=(u8)(identity+1);
    }
    if(winner<5){
        count=scenario==0?1U:scenario==2?255U:3U;D_80098888[winner]=(u8)count;
        members[winner][count-1]=(u8)identity;
        if(scenario==3){members[winner][0]=(u8)identity;members[winner][1]=(u8)identity;}
        if(winner<4){D_80098888[winner+1]=3;members[winner+1][0]=(u8)identity;}
        for(index=0;index<(int)count;index++){
            expected[members[winner][index]]=expected[identity];counts[members[winner][index]]=counts[identity];
        }
    }
    func_1503D510(identity);
    for(index=0;index<256;index++)if(D_800D1588[index]!=expected[index] || (u16)D_800C5A90[index]!=(u16)counts[index])return 1;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void){int id,w,s,r;u32 v;
    for(v=0;v<65536U;v++){r=check(7,0,1,v);if(r)return r;}
    for(id=0;id<256;id++)for(w=0;w<6;w++)for(s=0;s<4;s++){r=check(id,w,s,0x8000U+(u32)id);if(r)return r;}
    return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
