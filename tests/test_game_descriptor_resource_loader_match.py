"""Qualify the complete direct descriptor-loader match and connected helpers."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_descriptor_resource_loader_candidates as screen
from tools.experiments import game_group_publication_propagation_candidates as propagation
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_main_resource_loader as main
from tools.tests import test_game_record_pair_copy_match as pairs
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, BLOCK, ALTERNATE = guest.STACK, 0x70000, 0x72000
COUNTS, GROUP_POINTERS, GROUP_DATA = 0x80098888, 0x80084410, 0x74000
LOOKUP, LOAD, ASSET = 0x1502AC88, 0x1502B350, 0xAB1950
GROUPS = ((0x21,7),(0x24,36),(2,3,4),(),(0xBB,186))
ROLES = dict(remap='func_1503D5F0', request='func_1502B5C8',
    first='func_1503D45C', count='func_1503D484', finish='func_1503D510')
ARITIES = dict(remap=1, request=4, first=2, count=2, finish=1)
LINKS = [(entry, dict(zip(screen.SYMBOLS,(
    0x80107FFC+carry,0x80118004-carry,0x150A7FFC+carry,0x150B8004+carry,
    0x150C7FF0+carry,0x150D8004+carry,0x150E7FF0+carry))))
    for entry,carry in itertools.product((screen.ENTRY,0x15207FFC,0x15318004),(0,8,0x10000))]
LINKS[0] = (screen.ENTRY,screen.SYMBOLS)


def slot(symbols, name, identity):
    return (symbols[name]+(identity&0xFFFFFFFF)*(2 if name=='D_800C5A90' else 4))&0xFFFFFFFF


def fixture(identity=7, present=False, mask=7, symbols=screen.SYMBOLS, loaded=BLOCK, value=0x40):
    memory = {STACK+i:0xA5 for i in range(-0x600,0xC0)}
    for base in (BLOCK,ALTERNATE,loaded,(loaded*2)&0xFFFFFFFF):
        for i in range(256): memory[(base+i)&0xFFFFFFFF]=0xA5
        for index in range(3): put(memory,base+index*4,value+index*8 if mask&(1<<index) else 0)
    for name in ('D_800D1588','D_800C5A90'):
        address = slot(symbols,name,identity)
        for i in range(8): memory[(address+i)&0xFFFFFFFF]=0xA5
    put(memory,slot(symbols,'D_800D1588',identity),ALTERNATE if present else 0)
    put(memory,slot(symbols,'D_800C5A90',identity),0xA180,2)
    for group,values in enumerate(GROUPS):
        memory[COUNTS+group]=len(values)
        put(memory,GROUP_POINTERS+group*4,GROUP_DATA+group*32)
        for index,value in enumerate(values): memory[GROUP_DATA+group*32+index]=value
    return memory


class DescriptorOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,identity=7,unused=0,phase=0,entry=screen.ENTRY,
            symbols=screen.SYMBOLS,result=BLOCK,actions=None,size=0xFFFFFFFF,helpers=False,
            mode=0,connected=None):
        super().__init__(words,memory,arguments=(identity&0xFFFFFFFF,unused&0xFFFFFFFF),
            phase=phase,entry=entry,connected=connected)
        self.descriptor_symbols = symbols
        self.result,self.actions,self.size,self.helpers,self.mode = result,actions or {},size,helpers,mode
        self.lookup_count,self.request_size = 0,None
    def record_call(self,target):
        if target in (LOOKUP,LOAD):
            if target==LOOKUP:
                assert STACK-0x600<=self.r[6]<STACK+0xC0
                args=(*self.r[4:6],('private-descriptor',))
            else:
                assert self.r[6]==self.request_size
                args=(*self.r[4:6],('private-size',))
        elif target==0x1503D438:
            args=tuple(self.r[4:6])
        else:
            role=next(role for role,name in ROLES.items() if self.descriptor_symbols[name]==target)
            args=tuple(self.r[4:4+ARITIES[role]])
            if role=='request':
                assert self.r[4]==self.r[29]+0x34
                self.request_size=self.r[4];self.lookup_count=0
                args=(('private-size',),*args[1:])
        self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==LOOKUP:
            index=self.lookup_count;self.lookup_count+=1
            self.put(self.r[6],0xF0000000 if self.mode==index+1 else 0xF0000020+index*0x20,4)
            result=8*(index+1)
        elif target==LOAD:
            self.put(self.r[6],self.size,4)
            result=0 if self.mode==3 else self.result
        else:
            role=next(role for role,name in ROLES.items() if self.descriptor_symbols[name]==target)
            for address,value,size in self.actions.get(role,()): self.put(address,value,size)
            if role=='request':
                self.put(self.r[4],self.size,4);result=self.result
            elif role=='remap': result=(self.r[4]+5)&0xFFFFFFFF
            elif role=='count':
                self.put(slot(self.descriptor_symbols,'D_800C5A90',self.r[5]),0x8001,2)
                result=0xDEADBEEF
            else: result=0xDEADBEEF
        main.extras_module.clobber(self,result)


class Reference:
    def __init__(self,memory,symbols=screen.SYMBOLS,result=BLOCK,actions=None,helpers=False,mode=0):
        self.memory,self.events,self.calls=memory.copy(),[],[]
        self.symbols,self.result,self.actions,self.helpers,self.mode=symbols,result,actions or {},helpers,mode
    def get(self,address,size=4):
        address&=0xFFFFFFFF
        assert all(address+i in self.memory for i in range(size))
        value=read(self.memory,address,size);self.events.append(('R',address,size,value));return value
    def put(self,address,value,size=4):
        address&=0xFFFFFFFF
        assert all(address+i in self.memory for i in range(size))
        put(self.memory,address,value,size);self.events.append(('W',address,size,value&((1<<(size*8))-1)))
    def record(self,target,args):
        self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def call(self,role,*args):
        target=self.symbols[ROLES[role]]
        self.record(target,args)
        if self.helpers:
            if role=='remap':
                for group in range(5):
                    count=self.get(COUNTS+group,1)
                    if count:
                        base=self.get(GROUP_POINTERS+group*4)
                        for index in range(count):
                            if args[0]==self.get(base+index,1): return self.get(base,1)
                return args[0]
            if role=='request':
                base,descriptor,index=ASSET,0,0
                for component in args[2:]:
                    if descriptor&0x0FFFFFFF or index==0:
                        self.record(LOOKUP,(base,component,('private-descriptor',)))
                        descriptor=0xF0000000 if self.mode==index+1 else 0xF0000020+index*0x20
                        base=(base+8*(index+1))&0xFFFFFFFF;index+=1
                if descriptor&0x0FFFFFFF:
                    self.record(LOAD,(base,descriptor,('private-size',)))
                    return 0 if self.mode==3 else self.result
                return 0
            if role=='first':
                cursor,base=args;value=self.get(cursor)
                while value:
                    following=self.get(cursor+8)
                    self.put(cursor,value+base)
                    cursor+=8;value=following
                return 0
            if role=='count':
                start,identity=args;cursor=start
                value=self.get(cursor,2)
                while value!=999:
                    word=self.get(cursor+4)
                    if word:
                        self.record(0x1503D438,(cursor+4,start))
                        current=self.get(cursor+4)
                        if current and not current&0x0F000000: self.put(cursor+4,current+start)
                    value=self.get(cursor+8,2);cursor+=8
                self.put(slot(self.symbols,'D_800C5A90',identity),(cursor-start)>>3,2)
                return 0
        for address,value,size in self.actions.get(role,()): self.put(address,value,size)
        if role=='remap': return (args[0]+5)&0xFFFFFFFF
        if role=='request': return self.result
        if role=='count': self.put(slot(self.symbols,'D_800C5A90',args[1]),0x8001,2)
        return 0xDEADBEEF
    def run(self,identity=7):
        identity&=0xFFFFFFFF
        published=slot(self.symbols,'D_800D1588',identity)
        if self.get(published): return 0
        mapped=self.call('remap',identity)
        loaded=self.call('request',('private-size',),2,15,mapped)
        if not loaded:
            self.put(published,0);self.put(slot(self.symbols,'D_800C5A90',identity),0,2)
            self.call('finish',identity);return 4
        self.put(published,loaded)
        if self.get(loaded):
            self.put(loaded,self.get(loaded)+loaded)
            base=self.get(published)
            self.call('first',self.get(base),(base+16)&0xFFFFFFFF)
        base=self.get(published)
        for offset in (4,8):
            value=self.get(base+offset)
            if value:
                self.put(base+offset,value+base);base=self.get(published)
        self.put(published,base+16)
        self.call('count',(base+16)&0xFFFFFFFF,identity)
        self.call('finish',identity)
        return 0


def helper_fixture(identity=7,present=False,mask=7,count=3):
    memory=fixture(identity,present,mask,value=0x90)
    for index in range(3): put(memory,BLOCK+index*4,0x90 if index==0 and mask&1 else 0x30+index*8 if mask&(1<<index) else 0)
    for index in range(5): put(memory,BLOCK+0x90+index*8,index+1 if index<count else 0)
    for index in range(5):
        put(memory,BLOCK+16+index*8,999 if index==count else index+1,2)
        put(memory,BLOCK+20+index*8,(0,1,0x0F000004,0x80000000)[index%4])
    return memory


class GameDescriptorResourceLoaderMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-descriptor-resource-loader-match-test'
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
        assert cls.baseline['source']==screen.PAIR_SOURCE_SHA
        assert cls.baseline['elf']=='68ba892ee6637eaf7c043fbebf0466037570fdd86b58d587d0265f3060acfe55'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>69I',cls.rom,screen.ROM))
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
    def compare(self,memory,identity=7,symbols=screen.SYMBOLS,forms=None,**settings):
        reference=Reference(memory,symbols,**{k:v for k,v in settings.items() if k in ('result','actions','helpers','mode')})
        status=reference.run(identity)
        expected=(preparation.public(reference.memory),preparation.events(reference.events),reference.calls,status)
        models=[DescriptorOracle(words,memory,identity=identity,symbols=symbols,**settings).run()
            for words in (forms or (self.retail,self.raw,self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls,model.r[2]),expected)
        return models

    def test_01_complete_direct_shape_and_original_saved_lifetimes(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(69,56,0))
        self.assertEqual((self.meta['diagnostics'],self.meta['pool_bytes']),('',0))
        self.assertEqual(self.raw,self.retail);self.assertEqual(self.padded,self.retail)
        self.assertEqual(self.link('original'),self.retail)
        _,alternate=screen.compile_candidate(self.root,self.out,'retail-profile',profile='retail')
        self.assertEqual(alternate,self.retail)
        self.receipt('shape',words=69,frame=56,S0_spill=24,RA_spill=28,
            unused_A1_home=60,size_output=52,slot_spill=40,direct_words=69,new_guards=0,
            no_profile_or_Makefile_changes=True)

    def test_02_full_identity_presence_failure_fields_and_ignored_argument_matrix(self):
        cases,reached=0,set()
        for identity,present,failed,mask,unused,phase in itertools.product(
                (0,1,7,36,186,187,255,-1,256,0x80000000,0x7FFFFFFF),
                (False,True),(False,True),range(8),(0,0xDEADBEEF),(0,8)):
            models=self.compare(fixture(identity,present,mask),identity,result=0 if failed else BLOCK,unused=unused,phase=phase)
            for model in models:
                reached.update(model.visits)
                if present: self.assertEqual(model.calls,[])
            cases+=1
        self.assertEqual(len(reached&set(range(screen.ENTRY,screen.ENTRY+276,4))),69)
        self.receipt('guest',cases=cases,forms=3,reached_words=69,
            full_word_identity_no_added_gate=True,invalid_identities_mapped_guest_only=True,
            full_memory_public_access_call_order_and_status_reference=True)

    def test_03_live_callback_publication_header_count_aliases_and_size_independence(self):
        cases=0
        for failed,phase,size in itertools.product((False,True),(0,8),(0,1,0x80000000,0xFFFFFFFF)):
            published=slot(screen.SYMBOLS,'D_800D1588',7)
            plans=({}, {'remap':((published,ALTERNATE,4),)},
                {'request':((published,ALTERNATE,4),)},
                {'first':((published,ALTERNATE,4),)},
                {'first':((BLOCK+4,0,4),(BLOCK+8,0xFFFFFFFF,4))},
                {'count':((published,ALTERNATE,4),)},
                {'finish':((published,ALTERNATE,4),(slot(screen.SYMBOLS,'D_800C5A90',7),0xFFFF,2))})
            for actions in plans:
                self.compare(fixture(),result=0 if failed else BLOCK,actions=actions,phase=phase,size=size);cases+=1
        for offset,phase,mask in itertools.product((0,4,8),(0,8),(0,7)):
            base=(slot(screen.SYMBOLS,'D_800D1588',7)-offset)&0xFFFFFFFF
            self.compare(fixture(loaded=base,mask=mask),result=base,phase=phase);cases+=1
        for value in (0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x0F000004):
            self.compare(fixture(value=value));cases+=1
        self.receipt('aliases',cases=cases,live_slot_reloads_and_callback_order=True,
            returned_pointer_not_private_size=True,full_word_wrap_and_publication_header_aliases=True,
            deeper_helper_pointer_validity_not_claimed_for_opaque_cases=True)

    def test_04_independent_global_HI_LO_and_five_helper_JAL_rebases(self):
        cases=0
        for entry,symbols in LINKS:
            forms=[self.link(name,entry,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms[0],forms[1]);self.assertEqual(forms[0],forms[2])
            for identity,failed,present,unused,phase in itertools.product((7,-1),(False,True),
                    (False,True),(0,0xFFFFFFFF),(0,8)):
                self.compare(fixture(identity,present,symbols=symbols),identity,symbols,forms,
                    result=0 if failed else BLOCK,entry=entry,unused=unused,phase=phase);cases+=1
        self.receipt('rebases',links=len(LINKS),cases=cases,two_global_HI_LO_carries_and_five_JAL_rebases=True)

    def test_05_every_private_and_public_fault_prefix_for_all_three_exact_forms(self):
        triples=0
        for present,result,mask,phase in ((True,BLOCK,7,0),(False,0,7,8),(False,BLOCK,0,0),
                (False,BLOCK,7,8),(False,BLOCK,5,0)):
            memory=fixture(present=present,mask=mask)
            complete=DescriptorOracle(self.retail,memory,result=result,phase=phase).run()
            for ordinal in range(complete.accesses):
                models=[DescriptorOracle(words,memory,result=result,phase=phase) for words in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                for model in models[1:]:
                    self.assertEqual((model.memory,model.events,model.calls,model.r),
                        (models[0].memory,models[0].events,models[0].calls,models[0].r))
                triples+=1
        self.receipt('faults',fired_original_raw_padded_triples=triples,
            all_private_and_public_access_partial_memory_events_calls_registers_exact=True,guest_not_hardware=True)

    def test_06_effective_compiled_semantic_and_stale_interface_controls(self):
        controls=(('depth',', 2, 15,',', 1, 15,',False),('path',', 2, 15,',', 2, 14,',False),
            ('mapping','func_1503D5F0(identity)','identity',False),
            ('count-clear','D_800C5A90[identity] = 0','D_800C5A90[identity] = 1',True),
            ('status','return 4;','return 2;',True),
            ('first-base','(s32)(*slot + 0x10)','(s32)(*slot + 0x14)',False),
            ('second','*(u32 *)(*slot + 4) +=','*(u32 *)(*slot + 4) =',False),
            ('publish','*slot += 0x10;','*slot += 0x14;',False))
        for name,before,after,failed in controls:
            body=screen.QUALIFIED.replace(before,after);self.assertNotEqual(body,screen.QUALIFIED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(fixture(),forms=(words,),result=0 if failed else BLOCK)
        before=(self.out/'before-source').read_text()
        for wrong in (before.replace(screen.ORIGINAL,''),before+screen.ORIGINAL,
                before.replace('s32 func_1503D660();','s32 func_1503D660(s32, s32);')):
            with self.assertRaises(ValueError): screen.install(wrong)
        self.receipt('controls',effective_compiled_mutations=len(controls),stale_install_rejections=3)

    def test_07_both_mixed_profile_padded_owners_preserve_all_fourteen_neighbors(self):
        before=(self.out/'before-source').read_text();run=subprocess.run;objects={}
        def compact_run(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for profile in ('owner','unrolled'):
            for stage,source in (('before',before),('after',screen.install(before))):
                with patch('subprocess.run',side_effect=compact_run if profile=='owner' else run):
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
                args+=['--word-patches',str(self.out/'before-guards'),'--function-object',
                    'func_1503D804='+str(objects['unrolled',stage])]
                subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value'];expected=bytearray(parsed[0][0])
            expected[start:start+276]=parsed[1][0][start:start+276];self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start<=o<start+276},
                {o:v for o,v in parsed[1][2].items() if not start<=o<start+276})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors=len(names)-1,actual_padders=2,owner_diagnostics=0,
            all_other_body_bytes_extents_relocations_pools_and_parent_exact=True,
            existing_96_word_function_object_selection_unchanged=True)

    def test_08_immutable_actual_whole_ELF_and_all_assignment_inputs(self):
        from tools.experiments import game_third_resource_loader_lifetime_candidates as third
        for name in self.paths: self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source=(self.out/'before-source').read_text();source=propagation.descriptor_source(self.root)
        installed_now=source!=before_source
        self.assertEqual(source,screen.install(before_source) if installed_now else before_source)
        actual=propagation.descriptor_elf(self.root,self.before);expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,276);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if installed_now:
            struct.pack_into('>69I',expected,start,*self.retail);struct.pack_into('>I',expected,extent,276)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'):
                data=third.historical_guards(self.root) if name=='guards' else (self.root/path).read_bytes()
                self.assertEqual(data,(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=installed_now,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[start:start+276],actual[start:start+276])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            all_other_ELF_bytes_metadata_data_guard_view_Makefile_and_conversion_inputs_exact_after_propagation_projection=True,
            exact_third_lifetime_guard_projection=third.historical_guards(self.root)!=(self.root/third.GUARDS).read_bytes(),protected_data=audit)

    def test_09_native32_complete_C_callbacks_all_halfword_payloads_and_ignored_argument(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace('return 4;','return 2;')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=77824,
            all_65536_low_halfword_payloads_and_256_fixture_identities=True,
            full_arrays_public_slots_callback_trace_return_and_private_size_independence=True,
            effective_failure_control=True,native32_no_strict_aliasing_not_portable_64_bit_or_real_tables=True)

    def test_10_actual_six_body_helper_chain_request_mapping_relocations_and_sentinel_count(self):
        cases,reached=0,set()
        for identity,present,mask,count,mode,phase in itertools.product((7,36,3,186,255,-1),
                (False,True),range(8),range(5),range(4),(0,8)):
            models=self.compare(helper_fixture(identity,present,mask,count),identity,helpers=True,mode=mode,
                connected=self.helpers,phase=phase)
            reached.update(models[0].visits);cases+=1
        self.assertEqual(len(reached&set(range(screen.ENTRY,screen.ENTRY+276,4))),69)
        self.receipt('helpers',cases=cases,actual_69_28_61_10_35_9_word_bodies=True,reached_target_words=69,
            real_optional_size_variadic_depth_two_request_and_live_record_relocations=True,
            lookup_block_loader_and_unrecovered_finish_still_bounded=True)

    def test_11_exact_successor_projection_rejects_source_words_extents_and_preserves_other_bytes(self):
        before_source=(self.out/'before-source').read_text();qualified=screen.install(before_source)
        source_path,elf_path=self.root/screen.SOURCE,self.root/self.paths['elf']
        read_text,read_bytes=Path.read_text,Path.read_bytes
        start=elf_slot_offset(self.before,screen.ENTRY,276);extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        current=bytearray(self.before);struct.pack_into('>69I',current,start,*self.retail);struct.pack_into('>I',current,extent,276)
        def source_patch(body):
            return patch.object(Path,'read_text',lambda path,*a,**kw:body if path==source_path else read_text(path,*a,**kw))
        def elf_patch(data):
            return patch.object(Path,'read_bytes',lambda path:bytes(data) if path==elf_path else read_bytes(path))
        with source_patch(qualified),elf_patch(current):
            self.assertEqual(screen.pair_source(self.root),before_source);self.assertEqual(screen.pair_elf(self.root,self.before),self.before)
        for wrong in (qualified.replace('return 4;','return 2;',1),
                qualified.replace('s32 func_1503D660(s32, s32);','s32 func_1503D660();'),
                qualified.replace('extern u8 *D_800D1588[];','extern u32 D_800D1588[];'),
                qualified.replace('void *func_1502B5C8(s32 *, u32, ...);','void *func_1502B5C8();'),qualified+'\n'):
            with source_patch(wrong),self.assertRaises(AssertionError): screen.pair_source(self.root)
        for offset in (start+4,extent+3):
            wrong=current.copy();wrong[offset]^=1
            with source_patch(qualified),elf_patch(wrong),self.assertRaises(AssertionError): screen.pair_elf(self.root,self.before)
        wrong=current.copy();wrong[start+276]^=1;expected=bytearray(self.before);expected[start+276]^=1
        with source_patch(qualified),elf_patch(wrong): self.assertEqual(screen.pair_elf(self.root,self.before),bytes(expected))
        self.receipt('historical',source_rejections=5,word_extent_rejections=2,
            exact_body_prototype_two_declarations_full_slot_and_extent_only=True,
            immutable_inputs_not_refreshed_and_unrelated_ELF_bytes_preserved=True)

    def test_12_actual_parent_pair_and_descriptor_helper_chain_with_real_failure_four(self):
        original_oracle,original_reference,original_fixture=main.MainOracle,main.Reference,main.fixture
        target_words,reached=self.raw.copy(),set()
        plan=dict(present=False,mask=7)
        executions=0
        original_product=itertools.product
        def descriptor_matrix(*axes,**kwargs):
            extended=any(axis==(None,'request','secondary','third') for axis in axes)
            if not extended:
                return original_product(*axes,**kwargs)
            axes=tuple((None,'request','secondary','third','fourth')
                if axis==(None,'request','secondary','third') else axis for axis in axes)
            def cases():
                for case in original_product(*axes,**kwargs):
                    plan.update(present=case[0]==3,mask=0 if case[0]==1 else 7)
                    yield case
            return cases()
        helper_words={**self.helpers,**{screen.ENTRY+i*4:w for i,w in enumerate(target_words)}}
        class WithDescriptor(original_oracle):
            def __init__(model,*args,**kwargs):
                nonlocal executions
                executions+=1
                connected=dict(kwargs.get('connected') or {});connected.update(helper_words);kwargs['connected']=connected
                super().__init__(*args,**kwargs)
                model.descriptor_active=False;model.descriptor_symbols=screen.SYMBOLS
                model.actions={**model.actions};model.size=0xFFFFFFFF;model.result=BLOCK
                model.lookup_count=0;model.request_size=None;model.helpers=True
                model.mode=3 if model.results.get('fourth') else 0
            def run(model):
                result=super().run();reached.update(model.visits&set(range(screen.ENTRY,screen.ENTRY+276,4)));return result
            def record_call(model,target):
                if target==screen.ENTRY:
                    model.descriptor_active=True
                    return super().record_call(target)
                if model.descriptor_active and target in (*screen.SYMBOLS.values(),LOOKUP,LOAD,0x1503D438):
                    return DescriptorOracle.record_call(model,target)
                return super().record_call(target)
            def hook(model,target):
                if model.descriptor_active and target in (LOOKUP,LOAD,screen.SYMBOLS['func_1503D510']):
                    result=DescriptorOracle.hook(model,target)
                    if target==screen.SYMBOLS['func_1503D510']: model.descriptor_active=False
                    return result
                return super().hook(target)
        class WithReference(original_reference):
            def call(model,role,*args):
                if role!='fourth': return super().call(role,*args)
                target=main.S[main.ROLES[role]];model.calls.append((target,*args));model.events.append(('CALL',target,args))
                child=Reference(model.memory,helpers=True,mode=3 if model.results.get('fourth') else 0)
                value=child.run(args[0]);model.memory=child.memory;model.events.extend(child.events);model.calls.extend(child.calls)
                return value
        def with_descriptor(*args,**kwargs):
            memory=original_fixture(*args,**kwargs)
            identity=kwargs.get('identity',args[0] if args else 7)
            memory.update(helper_fixture(identity,present=plan['present'],mask=plan['mask']));return memory
        pair_words=list(struct.unpack_from('>96I',self.rom,pairs.screen.ROM))
        saved=self.retail,self.raw
        try:
            with patch.object(main,'MainOracle',WithDescriptor),patch.object(main,'Reference',WithReference), \
                    patch.object(main,'fixture',with_descriptor),patch.object(type(self),'padded',property(lambda _:pair_words)), \
                    patch.object(itertools,'product',descriptor_matrix):
                pairs.GameRecordPairCopyMatchTests.test_12_actual_eight_body_loader_chain_noop_copy_and_failure(self)
        finally: self.retail,self.raw=saved
        self.assertEqual(executions,3840)
        self.assertEqual(len(reached),69)
        self.receipt('descriptor-chain',cases=executions//2,executions=executions,reached_descriptor_words=len(reached),
            actual_parent_main_command_counter_pair_descriptor_remap_request_first_count_relocator_extras_buffer_bodies=True,
            former_fourth_flag_drives_real_request_null_and_status_four=True,
            inherited_nested_receipt_counts_not_reused_for_extended_matrix=True,
            deeper_lookup_block_loader_finish_heap_hardware_runtime_still_bounded=True)


NATIVE = r'''#define NULL ((void *)0)
typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;
u8 *D_800D1588[256];s16 D_800C5A90[256];
static u32 block[32],alternate[32],eb[32],ea[32];
static int identity,mode,failed,present,mask,calls[5],error;static u32 payload;
static u8 *returned,*expectedSlot;static u32 expectedCount;
s32 func_1503D660(s32,s32);
s32 func_1503D5F0(s32 id) {calls[0]++;if(id!=identity)error=1;return id+5;}
void *func_1502B5C8(s32 *size,u32 depth,...) {
    __builtin_va_list ap;int path,id;__builtin_va_start(ap,depth);path=__builtin_va_arg(ap,int);
    id=__builtin_va_arg(ap,int);__builtin_va_end(ap);calls[1]++;
    if(depth!=2 || path!=15 || id!=identity+5)error=1;
    *size=(s32)payload;
    if(mode==1)D_800D1588[identity]=(u8 *)alternate;
    return failed?NULL:returned;
}
void func_1503D45C(s32 *first,s32 base) {
    calls[2]++;if((u32)first!=block[0] || (u32)base!=(u32)block+16)error=1;
    if(mode==2)D_800D1588[identity]=(u8 *)alternate;
    if(mode==3){block[1]=0;block[2]=0xFFFFFFF0U;}
}
void func_1503D484(u8 *records,s32 id) {
    calls[3]++;if(records!=expectedSlot || id!=identity)error=1;
    D_800C5A90[id]=(s16)0x8001;
    if(mode==4)D_800D1588[id]=(u8 *)alternate;
}
s32 func_1503D510(s32 id) {
    calls[4]++;if(id!=identity)error=1;
    if(mode==5){D_800D1588[id]=(u8 *)alternate;D_800C5A90[id]=-1;}
    return (s32)0xDEADBEEFU;
}
static int check(int id,int cached,int failure,int action,u32 value,int unused) {
    int i,active;u32 result,*header;
    identity=id;mode=action;failed=failure;present=cached;mask=id&7;payload=value;error=0;
    for(i=0;i<5;i++)calls[i]=0;
    for(i=0;i<32;i++){block[i]=eb[i]=0xA5000000U+(u32)i;alternate[i]=ea[i]=0xC1000000U+(u32)i;}
    for(i=0;i<3;i++){block[i]=eb[i]=mask&(1<<i)?value+(u32)i*8U:0;alternate[i]=ea[i]=0x20U+(u32)i*8U;}
    for(i=0;i<256;i++){D_800D1588[i]=(u8 *)block;D_800C5A90[i]=(s16)0xA180;}
    D_800D1588[id]=cached?(u8 *)alternate:NULL;returned=(u8 *)block;active=!cached;
    expectedSlot=cached?(u8 *)alternate:failure?NULL:(u8 *)(mode==2 && eb[0]?alternate:block)+16;
    result=(u32)func_1503D660(id,unused);
    if(active && !failure) {
        header=eb;
        if(header[0]) {
            header[0]+=(u32)block;
            if(mode==2)header=ea;
            if(mode==3){eb[1]=0;eb[2]=0xFFFFFFF0U;}
        }
        if(header[1])header[1]+=(u32)(header==eb?block:alternate);
        if(header[2])header[2]+=(u32)(header==eb?block:alternate);
    }
    expectedCount=active?(failure?0U:0x8001U):0xA180U;
    if(active && (mode==5 || (!failure && mode==4)))expectedSlot=(u8 *)alternate;
    if(active && mode==5)expectedCount=0xFFFFU;
    if(result!=(active && failure?4U:0U) || error || calls[0]!=active || calls[1]!=active ||
        calls[2]!=(active && !failure && (mask&1) && value!=0) || calls[3]!=(active && !failure) || calls[4]!=active)return 1;
    for(i=0;i<256;i++) {
        if(D_800D1588[i]!=(i==id?expectedSlot:(u8 *)block) ||
            (u32)(unsigned short)D_800C5A90[i]!=(i==id?expectedCount:0xA180U))return 2;
    }
    for(i=0;i<32;i++)if(block[i]!=eb[i] || alternate[i]!=ea[i])return 3;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void) {
    int id,p,f,m,u,r;u32 value;
    for(value=0;value<65536U;value++){r=check(7,0,0,0,value,0);if(r)return r;}
    for(id=0;id<256;id++)for(p=0;p<2;p++)for(f=0;f<2;f++)for(m=0;m<6;m++)for(u=0;u<2;u++){
        r=check(id,p,f,m,0xFFFF0000U+(u32)id,u?(int)0xDEADBEEFU:0);if(r)return r;
    }
    return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
