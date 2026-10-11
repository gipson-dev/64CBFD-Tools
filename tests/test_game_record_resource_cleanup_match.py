"""Complete callback-aware cleanup, literal installation and actual release chain."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_resource_cleanup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_extras_match as extras
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_group_publication_propagation_match as propagation
from tools.tests import test_game_main_resource_loader as main
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, OLD, NEW = guest.STACK, extras.OLD, extras.NEW
RELEASE, FREE = 0x1510D7AC, 0x10004074
STATE, REFS, POINTERS, HEAP = 0x800BC448, 0x800D9F68, 0x800B0E58, 0x90000
LINKS = [(entry,dict(zip(screen.SYMBOLS,(0x80107FFC+carry,0x80118004-carry,0x15118004+carry))))
    for entry,carry in itertools.product((screen.ENTRY,0x15207FFC,0x15318004),(0,8,0x10000))]
LINKS[0]=(screen.ENTRY,screen.SYMBOLS)


def address(symbols,table,identity,stride):
    return (symbols[table]+(identity&0xFFFFFFFF)*stride)&0xFFFFFFFF


def fixture(count=3,identity=7,symbols=screen.SYMBOLS,pattern=0):
    memory=extras.fixture(count,identity,symbols)
    for base in (OLD,NEW):
        for index in range(16):
            current=(0x80000000,7,0x80000001,0,0xFFFFFFFF)[(index+pattern)%5]
            source=current if (index+pattern)%4==1 else 7+index
            put(memory,base+index*12,current);put(memory,base+index*12+4,source)
    return memory


def map_release(memory,state=0x41,refs=1):
    for identity in range(256):
        memory[STATE+identity]=state;memory[REFS+identity]=refs
        for offset in range(4): memory[POINTERS+identity*4+offset]=0
        put(memory,POINTERS+identity*4,HEAP+identity*8)
        for offset in range(8): memory[HEAP+identity*8+offset]=0
        put(memory,HEAP+identity*8,0x91000000+identity*16)
    return memory


class Reference:
    def __init__(self,memory,symbols=screen.SYMBOLS,actions=None,actual_release=False,
            results=None,numbers=None):
        self.memory=memory.copy();self.symbols=symbols;self.actions=actions or {}
        self.events=[];self.calls=[];self.loads=0;self.actual_release=actual_release
        self.results=results or {};self.numbers={} if numbers is None else numbers
    def get(self,location,size=4):
        location&=0xFFFFFFFF
        assert all(location+i in self.memory for i in range(size)),('reference read',hex(location),size)
        value=read(self.memory,location,size);self.events.append(('R',location,size,value));return value
    def put(self,location,value,size=4):
        location&=0xFFFFFFFF
        assert all(location+i in self.memory for i in range(size)),('reference write',hex(location),size)
        put(self.memory,location,value,size);self.events.append(('W',location,size,value&((1<<(size*8))-1)))
    def record(self,target,value):
        self.calls.append((target,value));self.events.append(('CALL',target,(value,)))
    def callback(self,target,value):
        self.record(target,value)
        if self.actual_release:
            return main.helper(self,'free')
        for location,word,size in self.actions.get(self.loads,()): self.put(location,word,size)
        self.loads+=1
    def release(self,identity):
        self.record(self.symbols['func_1510D7AC'],identity)
        if not self.actual_release:
            for location,word,size in self.actions.get(self.loads,()): self.put(location,word,size)
            self.loads+=1;return
        state=self.get(STATE+identity,1)
        if state:
            count=self.get(REFS+identity,1)
            if count:
                count=(count-1)&255;self.put(REFS+identity,count,1)
                if not count:
                    if state&0x40: self.callback(FREE,self.get(self.get(POINTERS+identity*4)))
                    self.callback(FREE,self.get(POINTERS+identity*4))
                    self.put(POINTERS+identity*4,0xFFFFFFFF);self.put(STATE+identity,0,1)
    def run(self,identity=7):
        count_address=address(self.symbols,'D_800C5628',identity,2)
        count=self.get(count_address,2)
        if not count: return
        slot=address(self.symbols,'D_800C5338',identity,4)
        index=0
        while index<count:
            cursor=(self.get(slot)+index*12)&0xFFFFFFFF
            current=self.get(cursor)
            if current!=0x80000000:
                source=self.get(cursor+4)
                if current!=source:
                    self.release(source);count=self.get(count_address,2)
            index+=1
            assert index<=16,'unbounded guest fixture'


class CleanupOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,identity=7,phase=0,entry=screen.ENTRY,
            symbols=screen.SYMBOLS,actions=None,connected=None,actual_release=False):
        super().__init__(words,memory,arguments=(identity&0xFFFFFFFF,0xDEADBEEF,0x12345678,0x80000000),
            phase=phase,entry=entry,connected=connected)
        self.symbols=symbols;self.actions=actions or {};self.loads=0
        self.actual_release=actual_release;self.results={};self.numbers={}
    def execute(self,word):
        if word>>26==32:
            extras.buffers.CopyOracle.execute(self,word)
        else:
            super().execute(word)
    def record_call(self,target):
        assert target==self.symbols['func_1510D7AC'] or self.actual_release and target==FREE,hex(target)
        value=self.r[4];self.calls.append((target,value));self.events.append(('CALL',target,(value,)))
    def hook(self,target):
        if self.actual_release:
            assert target==FREE
            value=main.helper(self,'free')
        else:
            assert target==self.symbols['func_1510D7AC']
            for location,value,size in self.actions.get(self.loads,()): self.put(location,value,size)
            self.loads+=1;value=0xDEADBEEF
        extras.clobber(self,value)


class GameRecordResourceCleanupMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-resource-cleanup-match-test';cls.out.mkdir(exist_ok=True)
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
        assert cls.baseline['source']==screen.PROPAGATION_SOURCE_SHA
        assert cls.baseline['elf']=='e00c6867c8189e07472107ef036ca016267b22fce90e0b32cba5bdc9f410e6e2'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>43I',cls.rom,screen.ROM));cls.slot_words=list(struct.unpack_from('>45I',cls.rom,screen.ROM))
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        body=(cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+body)
        body=body.split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot))
        actual=list(struct.unpack_from('>46I',cls.before,elf_slot_offset(cls.before,RELEASE,184)))
        assert actual==list(struct.unpack_from('>46I',cls.rom,0x13AC5C))
        assert struct.unpack_from('>I',cls.before,installed.symbol_size_offset(cls.before,'func_1510D7AC',RELEASE))[0]==184
        cls.release_words={RELEASE+i*4:w for i,w in enumerate(actual)}
        cls.helpers={}
        for entry,rom,words in ((0x1503D5F0,0x6AAA0,28),(0x1502B5C8,0x58A78,61),
                (0x1503D45C,0x6A90C,10),(0x1503D484,0x6A934,35),(0x1503D438,0x6A8E8,9),(0x1503D510,0x6A9C0,56)):
            words_actual=list(struct.unpack_from('>%dI'%words,cls.before,elf_slot_offset(cls.before,entry,words*4)))
            assert words_actual==list(struct.unpack_from('>%dI'%words,cls.rom,rom))
            cls.helpers.update({entry+i*4:w for i,w in enumerate(words_actual)})
        cls.helpers.update({screen.ENTRY+i*4:w for i,w in enumerate(cls.raw)});cls.helpers.update(cls.release_words)

    def receipt(self,name,**values): (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def link(self,name,entry=screen.ENTRY,symbols=screen.SYMBOLS):
        script=self.out/'link.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        count=parse_object(self.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        if name=='padded':
            self.assertEqual(count,43)
            count=45
        return list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))
    @property
    def padded(self):
        if not hasattr(type(self),'_padded_words'): type(self)._padded_words=self.link('padded')
        return type(self)._padded_words
    def compare(self,memory,identity=7,forms=None,entry=screen.ENTRY,symbols=screen.SYMBOLS,phase=0,actions=None,actual_release=False):
        reference=Reference(memory,symbols,actions,actual_release);reference.run(identity)
        models=[CleanupOracle(words,memory,identity,phase,entry,symbols,actions,
            self.release_words if actual_release else None,actual_release).run() for words in (forms or (self.retail,self.raw,self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls),
                (preparation.public(reference.memory),reference.events,reference.calls))
        for model in models[1:]: self.assertEqual((model.memory,model.events,model.calls,model.r),(models[0].memory,models[0].events,models[0].calls,models[0].r))
        return models

    def test_01_complete_body_slot_frame_delay_updates_and_profiles(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(43,0x30,0))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.raw,self.retail);self.assertEqual(self.padded,self.slot_words)
        self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'],172)
        self.assertEqual(self.raw[:7],[0x27BDFFD0,0xAFBF002C,0xAFB40028,0xAFB30024,0xAFB20020,0xAFB1001C,0xAFB00018])
        self.assertEqual((self.raw[23],self.raw[24],self.raw[26],self.raw[27],self.raw[34]),
            (0x52430008,0x26100001,0x50650005,0x26100001,0x2631000C))
        meta,words=screen.compile_candidate(self.root,self.out,'retail-profile',profile='retail')
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences']),(43,0x30,0));self.assertEqual(words,self.retail)
        self.receipt('shape',direct_words=43,body_bytes=172,slot_words=45,trailing_nops=2,frame=48,new_guards=0,diagnostics=0)

    def test_02_unsigned_counts_sentinel_equal_mixed_and_full_word_identity(self):
        cases=0;reached=set()
        for identity,count,pattern,phase in itertools.product((0,7,36,186,255,256,-1,0x80000000),range(6),range(5),(0,8)):
            models=self.compare(fixture(count,identity,pattern=pattern),identity,phase=phase)
            reached.update(models[0].visits);cases+=1
        for count,phase in itertools.product((0x7FFF,0x8000,0xFFFF),(0,8)):
            memory=fixture(count);put(memory,OLD,1)
            self.compare(memory,phase=phase,actions={0:((address(screen.SYMBOLS,'D_800C5628',7,2),0,2),)});cases+=1
        self.assertEqual(len(reached&set(range(screen.ENTRY,screen.ENTRY+172,4))),43)
        memory=fixture(0);slot=address(screen.SYMBOLS,'D_800C5338',7,4)
        for offset in range(4): del memory[slot+offset]
        self.compare(memory);cases+=1
        self.receipt('guest',cases=cases,forms=3,reached_words=43,zero_count_no_pointer_read=True,
            unsigned_high_counts_early_callback_shrink=True,invalid_identities_mapped_guest_only=True)

    def test_03_live_callback_count_base_and_record_changes(self):
        slot=address(screen.SYMBOLS,'D_800C5338',7,4);count=address(screen.SYMBOLS,'D_800C5628',7,2)
        plans=({0:((count,0,2),)},{0:((count,5,2),)},{0:((slot,NEW,4),)},
            {0:((slot,NEW,4),(count,4,2),(NEW+12,0x80000000,4))},
            {0:((OLD+16,0xFFFFFFFF,4),)}, {0:((count,2,2),),1:((count,5,2),)})
        cases=0
        for actions,phase in itertools.product(plans,(0,8)):
            memory=fixture(3);put(memory,OLD,1);self.compare(memory,phase=phase,actions=actions);cases+=1
        memory=fixture(3);put(memory,OLD,0x80000000)
        for offset in range(4): del memory[OLD+4+offset]
        self.compare(memory);cases+=1
        self.receipt('callbacks',cases=cases,live_table_reload_each_record=True,
            cached_count_on_skips_reload_only_after_release=True,sentinel_short_circuit_no_source_read=True,
            all_caller_saved_integer_and_float_registers_clobbered=True)

    def test_04_independent_globals_and_release_jal_relocations(self):
        cases=0
        for entry,symbols in LINKS:
            forms=[self.link(name,entry,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms[0],forms[1]);self.assertEqual(forms[0],forms[2][:43]);self.assertEqual(forms[2][43:],[0,0])
            for identity,count,phase in itertools.product((7,256),(0,1,5),(0,8)):
                self.compare(fixture(count,identity,symbols=symbols),identity,forms,entry,symbols,phase);cases+=1
        self.receipt('rebases',links=9,cases=cases,two_independent_HI_LO_carries_and_release_JAL=True)

    def test_05_every_private_public_callback_fault_prefix_fires(self):
        triples=0
        actions={0:((address(screen.SYMBOLS,'D_800C5338',7,4),NEW,4),)}
        for count,phase in itertools.product((0,1,3,5),(0,8)):
            memory=fixture(count);complete=CleanupOracle(self.retail,memory,phase=phase,actions=actions).run()
            for ordinal in range(complete.accesses):
                models=[CleanupOracle(words,memory,phase=phase,actions=actions) for words in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                for model in models[1:]: self.assertEqual((model.memory,model.events,model.calls,model.r),
                    (models[0].memory,models[0].events,models[0].calls,models[0].r))
                triples+=1
        self.receipt('faults',fired_original_raw_padded_triples=triples,all_partial_private_public_memory_events_calls_registers_exact=True)

    def test_06_effective_compiled_semantic_and_stale_install_controls(self):
        controls=(('sentinel','0x80000000U','0x80000001U',3,0,None),
            ('equal','record[0] != record[1]','record[0] == record[1]',3,1,None),
            ('stride','index * 12','index * 8',3,1,None),
            ('argument','func_1510D7AC(record[1])','func_1510D7AC(record[0])',3,2,None),
            ('count','D_800C5628[identity]','((s16 *)D_800C5628)[identity]',0xFFFF,2,
                {0:((address(screen.SYMBOLS,'D_800C5628',7,2),0,2),)}))
        for name,before,after,count,pattern,actions in controls:
            body=screen.QUALIFIED.replace(before,after);self.assertNotEqual(body,screen.QUALIFIED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(fixture(count,pattern=pattern),forms=(words,),actions=actions)
        before=(self.out/'before-source').read_text()
        for wrong in (before.replace(screen.ORIGINAL,''),before+screen.ORIGINAL,before.replace(screen.PROTOTYPE,'')):
            with self.assertRaises(ValueError): screen.install(wrong)
        self.receipt('controls',effective_compiled_mutations=5,stale_install_rejections=3)

    def test_07_complete_owner_both_profiles_padders_and_all_neighbors(self):
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
            for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[profile,'before'],name),fingerprint(objects[profile,'after'],name),name)
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
            expected[start:start+180]=parsed[1][0][start:start+180];self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start<=o<start+180},
                {o:v for o,v in parsed[1][2].items() if not start<=o<start+180})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors=len(names)-1,actual_padders=2,diagnostics=0,
            all_other_bytes_extents_relocations_pools_and_274_word_caller_exact=True,D804_selector_unchanged=True)

    def test_08_literal_immutable_whole_ELF_and_every_assignment_input(self):
        for name in self.paths: self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source=(self.out/'before-source').read_text();source=(self.root/screen.SOURCE).read_text();now=source!=before_source
        self.assertEqual(source,screen.install(before_source) if now else before_source)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,180);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if now:
            struct.pack_into('>45I',expected,start,*self.slot_words);struct.pack_into('>I',expected,extent,172)
            expected=bytearray(screen.swap_metadata_pair(expected))
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=now,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[start:start+180],actual[start:start+180])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            changed_metadata_pair_bytes=14 if now else 0,
            literal_no_projection_exact_target_extent_and_two_symbol_name_value_permutation_only=True,
            all_semantic_symbols_and_other_ELF_bytes_data_guards_recipe_conversion_inputs_exact=True,protected_data=audit)

    def test_09_native32_full_unsigned_counts_maximum_scan_and_callbacks(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace('index * 12','index * 8')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',profiles=['O2','O0'],initial_count_cases=65536,callback_matrix_cases=3072,
            full_65535_record_sentinel_scan=True,high_count_cases_early_shrink_not_full_scans=True,
            valid_native_fixture_identities_only=True,effective_stride_control=True,native32_not_hardware_or_portable64=True)

    def test_10_strict_successor_projection_and_corruption_rejections(self):
        before=(self.out/'before-source').read_text();qualified=screen.install(before)
        source_path,elf_path=self.root/screen.SOURCE,self.root/self.paths['elf'];rt,rb=Path.read_text,Path.read_bytes
        start=elf_slot_offset(self.before,screen.ENTRY,180);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        current=bytearray(self.before);struct.pack_into('>45I',current,start,*self.slot_words);struct.pack_into('>I',current,extent,172)
        current=bytearray(screen.swap_metadata_pair(current))
        def source(body): return patch.object(Path,'read_text',lambda path,*a,**kw:body if path==source_path else rt(path,*a,**kw))
        def elf(data): return patch.object(Path,'read_bytes',lambda path:bytes(data) if path==elf_path else rb(path))
        with source(qualified),elf(current):
            self.assertEqual(screen.propagation_source(self.root),before);self.assertEqual(screen.propagation_elf(self.root,self.before),self.before)
        for wrong in (qualified.replace('index * 12','index * 8'),qualified.replace(screen.TYPED_PROTOTYPE,screen.PROTOTYPE),
                qualified.replace(screen.RELEASE_DECLARATION,'void func_1510D7AC();'),qualified+'\n'):
            with source(wrong),self.assertRaises(AssertionError): screen.propagation_source(self.root)
        pair=screen.metadata_pair(current)
        for offset in (start+4,start+176,extent+3,pair[0][0]+7,pair[0][1]+8):
            wrong=current.copy();wrong[offset]^=1
            with source(qualified),elf(wrong),self.assertRaises(AssertionError): screen.propagation_elf(self.root,self.before)
        wrong=current.copy();wrong[start+180]^=1;expected=bytearray(self.before);expected[start+180]^=1
        with source(qualified),elf(wrong): self.assertEqual(screen.propagation_elf(self.root,self.before),bytes(expected))
        self.receipt('historical',source_rejections=4,word_padding_extent_metadata_rejections=5,
            body_prototype_declaration_180_byte_slot_and_172_byte_extent_exact=True,
            exact_two_absolute_symbol_name_value_permutation_only=True,immutable_baselines_unrelated_bytes_preserved=True)

    def test_11_actual_43_and_46_word_release_chain_and_free_callbacks(self):
        cases=0;reached=set()
        for state,refs,count,phase in itertools.product((0,1,0x41,0x80,0xC1),(0,1,2,255),(0,1,3,5),(0,8)):
            models=self.compare(map_release(fixture(count,pattern=2),state,refs),actual_release=True,phase=phase)
            reached.update(models[0].visits);cases+=1
        count=address(screen.SYMBOLS,'D_800C5628',7,2);slot=address(screen.SYMBOLS,'D_800C5338',7,4)
        for actions in ({('free',0):((count,0,2),)}, {('free',0):((slot,NEW,4),)},
                {('free',0):((POINTERS+7*4,HEAP+8*8,4),)}):
            memory=map_release(fixture(3,pattern=2));self.compare(memory,actual_release=True,actions=actions);cases+=1
        self.assertEqual(len(reached&set(self.release_words)),46)
        self.receipt('release-chain',cases=cases,executions=cases*3,actual_cleanup43_release46=True,
            all_release_words_reached=46,signed_state_unsigned_byte_refcount_and_live_outer_pointer=True,
            conditional_two_free_calls_real_table_clear=True,heap_free_hardware_and_runtime_still_bounded=True)

    def test_12_actual_sixteen_body_parent_failure_chain_cleanup_hook_removed(self):
        old_oracle,old_reference,old_fixture=main.MainOracle,main.Reference,main.fixture
        reached=set();release_reached=set();release_words=self.release_words;cleanup_words={screen.ENTRY+i*4:w for i,w in enumerate(self.retail)}
        class WithCleanup(old_oracle):
            def __init__(model,*args,**kwargs):
                connected=dict(kwargs.get('connected') or {});connected.update(cleanup_words);connected.update(release_words)
                kwargs['connected']=connected;super().__init__(*args,**kwargs)
            def record_call(model,target):
                if target==RELEASE:
                    model.calls.append((target,model.r[4]));model.events.append(('CALL',target,(model.r[4],)));return
                return super().record_call(target)
            def run(model):
                result=super().run();reached.update(model.visits&set(cleanup_words));release_reached.update(model.visits&set(release_words));return result
        class WithReference(old_reference):
            def call(model,role,*args):
                if role!='cleanup': return super().call(role,*args)
                target=main.S[main.ROLES[role]];model.calls.append((target,*args));model.events.append(('CALL',target,args))
                child=Reference(model.memory,actual_release=True,actions=model.actions,results=model.results,numbers=model.numbers)
                child.run(args[0]);model.memory=child.memory;model.events.extend(child.events);model.calls.extend(child.calls);return 0
        def mapped(*args,**kwargs):
            memory=map_release(old_fixture(*args,**kwargs))
            for index in range(16): put(memory,main.EXTRAS+index*12+4,7+index)
            return memory
        with patch.object(main,'MainOracle',WithCleanup),patch.object(main,'Reference',WithReference),patch.object(main,'fixture',mapped):
            propagation.GameGroupPublicationPropagationMatchTests.test_12_actual_fourteen_body_parent_chain_with_finish_hook_removed(self)
        nested=json.loads((self.out/'parent-chain.json').read_text())
        self.assertEqual((nested['cases'],nested['executions']),(1920,3840))
        self.assertGreater(len(reached),35)
        self.assertGreater(len(release_reached),40)
        self.receipt('parent-cleanup-chain',cases=1920,executions=3840,reached_cleanup_words=len(reached),
            reached_release_words=len(release_reached),
            actual_sixteen_body_chain_including_cleanup43_and_release46=True,cleanup_and_release_hooks_removed=True,
            failure_rollback_free_trace_and_public_memory_exact=True,
            bounded_safe_resource_ids_in_disposable_fixture=True,deeper_third_lookup_allocator_heap_hardware_runtime_bounded=True)


NATIVE = r'''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u16 D_800C5628[256];u32 *D_800C5338[256];
static u32 records[65536][3],other[16][3];static int identity,mode,calls,error;
void func_1503DD1C(s32);
void func_1510D7AC(s32 value){
    if(value!=7+calls)error=1;
    if(mode==0)D_800C5628[identity]=0;
    if(mode==1 && calls==0)D_800C5338[identity]=other[0];
    if(mode==2 && calls==0)D_800C5628[identity]=5;
    if(mode==3 && calls==0)D_800C5628[identity]=1;
    calls++;
}
static int check(int id,u32 count,int action){int i;identity=id;mode=action;calls=error=0;
    D_800C5628[id]=(u16)count;D_800C5338[id]=records[0];
    for(i=0;i<16;i++){records[i][0]=other[i][0]=1;records[i][1]=other[i][1]=(u32)(7+i);records[i][2]=other[i][2]=0xA5U;}
    func_1503DD1C(id);
    if(error || calls!=(count==0?0:action==0 || action==3?1:action==2?5:(int)count))return 1;
    if(D_800C5338[id]!=(action==1 && count?other[0]:records[0]))return 2;
    for(i=0;i<16;i++)if(records[i][0]!=1 || records[i][1]!=(u32)(7+i) || records[i][2]!=0xA5U ||
        other[i][0]!=1 || other[i][1]!=(u32)(7+i) || other[i][2]!=0xA5U)return 3;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void){u32 count;int id,mode,r,i;
    for(count=0;count<65536U;count++){r=check(7,count,0);if(r)return r;}
    for(id=0;id<256;id++)for(mode=0;mode<4;mode++)for(count=0;count<3;count++){r=check(id,count,mode);if(r)return r;}
    identity=7;calls=error=0;mode=0;D_800C5628[7]=65535;D_800C5338[7]=records[0];
    for(i=0;i<65535;i++){records[i][0]=0x80000000U;records[i][1]=0xFFFFFFFFU;}
    func_1503DD1C(7);if(calls || error || D_800C5628[7]!=65535)return 4;
    for(i=0;i<65535;i++)if(records[i][0]!=0x80000000U || records[i][1]!=0xFFFFFFFFU)return 5;
    return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__=='__main__':
    unittest.main()
