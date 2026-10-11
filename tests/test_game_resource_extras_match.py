"""Full extras descriptors, live publication aliases and actual caller chain."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_resource_extras_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_resource_buffers as buffers
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools

S, STACK = screen.SYMBOLS, guest.STACK
OLD, NEW, THIRD = 0x30000, 0x31000, 0x32000
LOAD = S['func_1510D0EC']
RESULTS = (0,1,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFF)


def address(symbols, table, identity, stride):
    return (symbols[table]+identity*stride)&0xFFFFFFFF


def fixture(count=3, identity=7, symbols=S):
    memory = {STACK+i:0xA5 for i in range(-0x600,0xC0)}
    for base in (OLD,NEW,THIRD):
        for i in range(16):
            for offset,value in ((0,0xA5A50000+i),(4,base+0xF0000000+i*17),(8,0x800F0000+i)):
                for j in range(4): memory[base+i*12+offset+j]=0
                put(memory,base+i*12+offset,value)
    slot = address(symbols,'D_800C5338',identity,4)
    memory.update({slot+i:0xA5 for i in range(4)})
    put(memory,slot,OLD)
    count_address = address(symbols,'D_800C5628',identity,2)
    memory.update({count_address+i:0xA5 for i in range(2)})
    put(memory,count_address,count,2)
    return memory


def public(memory):
    return preparation.public(memory)


def events(values):
    return preparation.events(values)


def helper(model, symbols):
    number = model.loads
    model.loads += 1
    for location,value,size in model.actions.get(number,()):
        model.put(location,value,size)
    return model.results[min(number,len(model.results)-1)]&0xFFFFFFFF


def clobber(model, result):
    for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
    model.f[:20]=[0xA5000000+i for i in range(20)]
    model.r[2]=result


class ExtrasOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,identity=7,phase=0,symbols=S,entry=screen.ENTRY,
            results=(0x90000000,),actions=None):
        super().__init__(words,memory,arguments=(identity&0xFFFFFFFF,),phase=phase,entry=entry)
        self.symbols,self.results,self.actions = symbols,results,actions or {}
        self.loads = 0
    def record_call(self,target):
        assert target==self.symbols['func_1510D0EC'],hex(target)
        args = tuple(self.r[4:8])
        self.calls.append((target,*args)); self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.symbols['func_1510D0EC']
        clobber(self,helper(self,self.symbols))


class Reference:
    def __init__(self,memory,symbols=S,results=(0x90000000,),actions=None):
        self.memory,self.symbols = memory.copy(),symbols
        self.results,self.actions,self.loads = results,actions or {},0
        self.events,self.calls = [],[]
    def get(self,location,size=4):
        assert all(location+i in self.memory for i in range(size)),('reference read',hex(location),size)
        value = read(self.memory,location,size)
        self.events.append(('R',location,size,value)); return value
    def put(self,location,value,size=4):
        assert all(location+i in self.memory for i in range(size)),('reference write',hex(location),size)
        put(self.memory,location,value,size)
        self.events.append(('W',location,size,value&((1<<(size*8))-1)))
    def run(self,identity=7):
        count = address(self.symbols,'D_800C5628',identity,2)
        errors,index,offset = 0,0,0
        if not self.get(count,2): return 0
        slot = address(self.symbols,'D_800C5338',identity,4)
        cursor = self.get(slot)
        while True:
            args = self.get(cursor+4),0,0x3E,1
            target = self.symbols['func_1510D0EC']
            self.calls.append((target,*args)); self.events.append(('CALL',target,args))
            value = helper(self,self.symbols)
            self.put(self.get(slot)+offset,value)
            cursor = self.get(slot)+offset
            if self.get(cursor)==0x80000000: errors |= 0x10
            current = self.get(count,2)
            index += 1; offset += 12; cursor += 12
            if index>=current: return errors
            assert index<16,'unbounded reference fixture'


class GameResourceExtrasMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-resource-extras-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw = screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>56I',cls.rom,screen.ROM))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot = cls.out/'slot.s'; cls.slot.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+assembly+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot,filename='generated_6A3D0'))
        cls.before = (cls.out/'before-elf').read_bytes()
    def receipt(self,name,**values):
        assert name!='baseline'
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    @classmethod
    def link(cls,name,symbols=S,entry=screen.ENTRY):
        script = cls.out/('%s-%X.ld'%(name,entry)); elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>56I',sections(elf)['.text'][1]))
    def compare(self,memory,forms=None,**settings):
        reference = Reference(memory,settings.get('symbols',S),settings.get('results',(0x90000000,)),settings.get('actions'))
        result = reference.run(settings.get('identity',7))
        expected = public(reference.memory),events(reference.events),reference.calls,result
        models = [ExtrasOracle(words,memory,**settings).run() for words in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((public(model.memory),events(model.events),model.calls,model.r[2]),expected)
        self.assertEqual(models[0].memory,models[1].memory); self.assertEqual(models[0].events,models[1].events)
        return models
    def test_01_complete_direct_shape(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(56,0x38,0,0,''))
        self.assertEqual(self.raw,self.retail)
        self.assertEqual(self.link('original'),self.retail); self.assertEqual(self.link('padded'),self.retail)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse(any(r['function']==screen.FUNCTION for r in csv.DictReader(stream)))
        self.receipt('shape',words=56,frame=56,raw_differences=0,guards=0,direct_match=True)
    def test_02_all_words_boundaries_and_sentinel_sequences(self):
        cases = 0; reached = set()
        for count,identity,results,phase in itertools.product(range(16),(0,1,7,128,186,255),
                tuple((r,) for r in RESULTS)+((0x80000000,0x90000000),(0,0x80000000),(1,0x80000001,0x80000000)),(0,8)):
            models = self.compare(fixture(count,identity),identity=identity,results=results,phase=phase)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+224,4)))
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=len(reached),
            independent_complete_memory_access_order_calls_and_error_reference=True)
    def test_03_live_mutations_wrapping_word_ABI_and_unsigned_counts(self):
        cases = 0
        for identity,count,phase in itertools.product((-1,0,7,128,186,255,0x40000007,0x80000001),
                (0,1,2,0x7FFF,0x8000,0xFFFF),(0,8)):
            count_address = address(S,'D_800C5628',identity,2)
            self.compare(fixture(count,identity),identity=identity,phase=phase,
                actions={0:((count_address,1,2),)},results=(0x80000000,)); cases += 1
        slot = address(S,'D_800C5338',7,4); count_address = address(S,'D_800C5628',7,2)
        for count,results,phase in itertools.product((1,2,3),
                ((0x80000000,0x90000000),(0x80000001,0xFFFFFFFF),(0,1)),(0,8)):
            actions = {0:((slot,NEW,4),(count_address,5,2),(NEW+16,0xF0123456,4)),
                1:((slot,THIRD,4),(count_address,3,2),(THIRD+28,0x81234567,4)),
                2:((slot,OLD,4),(count_address,1,2),)}
            self.compare(fixture(count),results=results,phase=phase,actions=actions); cases += 1
        memory = fixture(0)
        for i in range(4): del memory[slot+i]
        self.compare(memory); cases += 1
        self.receipt('mutations',cases=cases,executions=cases*2,
            live_growth_shrink_new_base_publication_and_following_input_reloads=True,
            high_count_bit_unsigned_and_word_ABI_wrap_guest_only=True,zero_count_no_descriptor_read=True)
    def test_04_publication_changes_table_base_and_count_aliases(self):
        cases = 0
        for offset,phase in itertools.product((0,12,24),(0,8)):
            symbols = dict(S); symbols['D_800C5338']=OLD+offset-7*4
            forms = [self.link(name,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms,[forms[0]]*3)
            memory = fixture(offset//12+1,symbols=symbols)
            put(memory,NEW+offset,0x80000000)
            results = (0x90000000,)*(offset//12)+(NEW,)
            self.compare(memory,forms=forms,symbols=symbols,phase=phase,results=results); cases += 1
        for result,phase in itertools.product((0,1,3,0x80000000,0x80000001),(0,8)):
            symbols = dict(S); symbols['D_800C5628']=OLD+2-7*2
            forms = [self.link(name,symbols) for name in ('original','selected','padded')]
            memory = fixture(2,symbols=symbols)
            self.compare(memory,forms=forms,symbols=symbols,phase=phase,results=(result,)); cases += 1
        self.receipt('aliases',cases=cases,executions=cases*3,
            publication_can_rebind_its_own_descriptor_slot_and_live_count=True,
            failure_test_uses_reloaded_word_not_helper_return=True)
    def test_05_relocations_and_fired_all_access_faults(self):
        links = cases = faults = 0
        for entry,delta in ((screen.ENTRY,0),(0x15207FF0,0x47FFC),(0x15308004,0x88004)):
            symbols = {n:v+delta if n.startswith('D_') else v for n,v in S.items()}
            forms = [self.link(name,symbols,entry) for name in ('original','selected','padded')]; links += 3
            self.assertEqual(forms,[forms[0]]*3)
            for count,results,phase in itertools.product((0,1,3),((0x80000000,),(0xFFFFFFFF,),(0,0x80000000)),(0,8)):
                self.compare(fixture(count,symbols=symbols),forms=forms,symbols=symbols,entry=entry,
                    results=results,phase=phase); cases += 1
        for count,results,phase,mutate in itertools.product((0,1,3),
                ((0x80000000,),(0xFFFFFFFF,),(0,0x80000000)),(0,8),(False,True)):
            actions = {0:((address(S,'D_800C5338',7,4),NEW,4),)} if mutate else {}
            memory = fixture(count); settings = dict(results=results,phase=phase,actions=actions)
            complete = ExtrasOracle(self.retail,memory,**settings).run()
            for index in range(complete.accesses):
                models = []
                for words in (self.retail,self.raw):
                    model = ExtrasOracle(words,memory,**settings); model.fault=index
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,index); models.append(model)
                self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                    (models[1].memory,models[1].events,models[1].calls)); faults += 1
        self.receipt('links-faults',links=links,rebase_cases=cases,fired_fault_pairs=faults,
            complete_partial_memory_accesses_and_calls_equal=True)
    def test_06_effective_fresh_semantic_controls(self):
        alias_symbols = dict(S); alias_symbols['D_800C5338']=OLD-28
        memory = fixture(1,symbols=alias_symbols); put(memory,NEW,0x80000000)
        controls = (
            ('stride',screen.SELECTED.replace('offset += 12','offset += 8').replace('cursor += 3','cursor += 2'),fixture(),{}),
            ('sentinel',screen.SELECTED.replace('0x80000000U','0x80000001U'),fixture(),dict(results=(0x80000000,))),
            ('any-negative',screen.SELECTED.replace('*cursor == 0x80000000U','(s32)*cursor < 0'),fixture(),dict(results=(0x80000001,))),
            ('any-nonzero',screen.SELECTED.replace('*cursor == 0x80000000U','*cursor != 0'),fixture(),dict(results=(1,))),
            ('helper-return',screen.SELECTED.replace('*cursor == 0x80000000U','loaded == 0x80000000U'),memory,
                dict(symbols=alias_symbols,results=(NEW,))),
            ('cached-publication',screen.SELECTED.replace('*(u32 *)((u8 *)*slot + offset) = loaded','*cursor = loaded'),fixture(),
                dict(actions={0:((address(S,'D_800C5338',7,4),NEW,4),)})),
            ('missing-reload',screen.SELECTED.replace('            cursor = (u32 *)((u8 *)*slot + offset);\n',''),fixture(),
                dict(actions={0:((address(S,'D_800C5338',7,4),NEW,4),)},results=(0x80000000,))),
            ('snapshot-count',screen.SELECTED.replace('    u32 loaded;','    u32 loaded;\n    s32 limit;').replace(
                '        do {','        limit = *count;\n        do {').replace('index < *count','index < limit'),fixture(),
                dict(actions={0:((address(S,'D_800C5628',7,2),1,2),)})),
            ('zero-count',screen.SELECTED.replace('if (*count > 0)','if (1)'),fixture(0),{}),
            ('resource-word',screen.SELECTED.replace('cursor[1], 0, 0x3E, 1','cursor[0], 0, 0x3E, 1'),fixture(),{}),
            ('request-flag',screen.SELECTED.replace('cursor[1], 0, 0x3E, 1','cursor[1], 0, 0x3E, 0'),fixture(),{}),
        )
        for name,body,memory,settings in controls:
            with self.subTest(control=name):
                with patch.object(screen,'ENTRY',0x15400000),patch.object(screen,'SYMBOLS',settings.get('symbols',S)):
                    meta,words = screen.compile_candidate(self.root,self.out,'negative-'+name,body)
                self.assertGreater(meta['differences'],0)
                original = self.link('original',settings.get('symbols',S))
                correct = ExtrasOracle(original,memory,**settings).run()
                wrong = ExtrasOracle(words,memory,entry=0x15400000,**settings).run()
                self.assertNotEqual((public(correct.memory),events(correct.events),correct.calls,correct.r[2]),
                    (public(wrong.memory),events(wrong.events),wrong.calls,wrong.r[2]))
        self.receipt('controls',freshly_compiled_effective_controls=len(controls))
    def test_07_complete_owner_both_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        real_run = subprocess.run
        def run(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return real_run(command,*args,**kwargs)
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            with patch('subprocess.run',side_effect=run): obj,diagnostics=compile_owner(self.root,self.out,source,name)
            self.assertEqual(diagnostics,[]); objects.append(obj)
        parsed = [parse_object(obj) for obj in objects]
        def fingerprint(data,name):
            text,functions,relocations=data; info=functions[name]; start=info['value']
            return info['size'],text[start:start+info['size']],{
                o-start:v for o,v in relocations.items() if start<=o<start+info['size']}
        self.assertEqual(set(parsed[0][1]),set(parsed[1][1]))
        for name in parsed[0][1]:
            if name!=screen.FUNCTION: self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        for route in ('pad_c_object.py','pad_generated_object.py'):
            padded = []
            for i,obj in enumerate(objects):
                asm=self.out/('owner-%s-%d.s'%(route,i))
                args=[str(obj),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards')],
                    check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True); padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value']; end=start+224
            expected=bytearray(padded[0][0]); expected[start:end]=padded[1][0][start:end]
            self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<end},
                {o:v for o,v in padded[1][2].items() if not start<=o<end})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_and_typed_caller_body_exact=True)
    def test_08_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text()
        if source==(self.out/'before-source').read_text():
            for name,path in self.paths.items(): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
            self.receipt('linked',installed=False,immutable_baseline_verified=True); return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(self.before)
        off=elf_slot_offset(self.before,screen.ENTRY,224)
        struct.pack_into('>56I',expected,off,*self.retail)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        struct.pack_into('>I',expected,extent,224)
        previous,current=metadata(self.before),metadata(actual)
        self.assertEqual(previous[:2],current[:2]); self.assertEqual(previous[3],current[3])
        symbols=previous[2].copy()
        target=next(s for s in symbols if s[0]==screen.FUNCTION.encode() and s[1]==screen.ENTRY)
        self.assertEqual(target[2],12); symbols[target]-=1; symbols[(target[0],target[1],224,*target[3:])]+=1
        self.assertEqual(+symbols,current[2])
        changed_metadata=0
        for table in current[4:]:
            start,end=table[4],table[4]+table[5]
            changed_metadata+=sum(a!=b for a,b in zip(self.before[start:end],actual[start:end]))
            expected[start:end]=actual[start:end]
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,target_all_56_words_direct_exact=True,
            ELF_sha256=hashlib.sha256(actual).hexdigest(),changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[off:off+224],actual[off:off+224])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            changed_metadata_bytes_including_extent=changed_metadata,
            only_target_slot_extent_and_verified_existing_metadata_order_change=True,
            all_other_ELF_bytes_names_values_data_layout_guards_conversion_rows_exact=True,protected_data=audit)
    def test_09_native32_complete_C_and_publication_aliases(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code,_=self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace(
            '*cursor == 0x80000000U','loaded == 0x80000000U')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',cases_per_profile=2016,profiles=['O2','O0'],
            actual_complete_C_byte_memory_call_trace_reference_and_live_aliases=True,
            effective_helper_return_instead_of_reloaded_word_control=True)
    def test_10_complete_actual_preparation_extras_buffer_chain(self):
        outer_entry,outer_rom=preparation.screen.ENTRY,preparation.screen.ROM
        outer=list(struct.unpack_from('>104I',self.before,elf_slot_offset(self.before,outer_entry,416)))
        inner=list(struct.unpack_from('>194I',self.before,elf_slot_offset(self.before,buffers.screen.ENTRY,776)))
        self.assertEqual(outer,list(struct.unpack_from('>104I',self.rom,outer_rom)))
        self.assertEqual(inner,list(struct.unpack_from('>194I',self.rom,buffers.screen.ROM)))
        class Connected(preparation.PreparationOracle):
            def __init__(model,memory,extra,extra_results,extra_actions,allocation_results,**settings):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(extra)}
                connected.update({buffers.screen.ENTRY+i*4:w for i,w in enumerate(inner)})
                super().__init__(outer,memory,entry=outer_entry,connected=connected,**settings)
                model.extra_results,model.extra_actions,model.extra_loads=extra_results,extra_actions,0
                model.buffer_results=allocation_results
            def record_call(model,target):
                if target!=LOAD: return super().record_call(target)
                args=tuple(model.r[4:8]); model.calls.append((target,*args)); model.events.append(('CALL',target,args))
            def hook(model,target):
                if target!=LOAD: return super().hook(target)
                number=model.extra_loads; model.extra_loads+=1
                for location,value,size in model.extra_actions.get(number,()): model.put(location,value,size)
                clobber(model,model.extra_results[min(number,len(model.extra_results)-1)])
        class OuterReference(preparation.Reference):
            def call(model,role,*args):
                if role not in ('extras','buffers'): return super().call(role,*args)
                target=model.symbols[preparation.ROLES[role]]
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                child=Reference(model.memory,results=model.extra_results,actions=model.extra_actions) if role=='extras' else \
                    buffers.Reference(model.memory,model.allocation_results,model.actions)
                result=child.run(args[0]) if role=='extras' else child.run(channel=args[1])
                model.memory=child.memory; model.events.extend(child.events); model.calls.extend(child.calls)
                return result
        cases=0; reached=[set(),set(),set()]
        for mode,channel,present,extras,flags,count,bounds,load_result,extra_results,phase in itertools.product(
                range(4),(0,3),(False,True),(0,1),(0,0x4000),(0,2),
                ((0,0),(1,0),(3,0),(3,0x10000000)),(0,0x10),
                ((0x90000000,),(0x80000000,0x90000000),(0x80000001,)),(0,8)):
            extra_count,threshold=bounds
            memory=preparation.fixture(present=present,flags=flags,count=count)
            memory.update(buffers.fixture(mode,channel=channel,source=buffers.SOURCE if present else 0))
            memory.update(fixture(extra_count))
            put(memory,preparation.ACTOR+0xAC,0,1); put(memory,preparation.CONFIG+24,flags); put(memory,OLD,threshold)
            actions={('load',0):((preparation.address(preparation.S,'D_800D19A0',7),buffers.SOURCE,4),),
                ('entry',0):((preparation.address(preparation.S,'D_800C4488',7),preparation.OTHER_LIST,4),)}
            extra_actions={0:((address(S,'D_800C5338',7,4),NEW,4),(address(S,'D_800C5628',7,2),3,2)),
                1:((address(S,'D_800C5338',7,4),THIRD,4),(address(S,'D_800C5628',7,2),2,2))}
            allocation_results=(buffers.PRIVATE,0) if phase else (buffers.PRIVATE,buffers.ALTERNATE)
            settings=dict(channel=channel,extras=extras,phase=phase,actions=actions,results=dict(load=load_result))
            models=[Connected(memory,w,extra_results,extra_actions,allocation_results,**settings).run()
                for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].r[2]))
            reference=OuterReference(memory,actions=actions,results=settings['results'])
            reference.extra_results,reference.extra_actions=extra_results,extra_actions
            reference.allocation_results=allocation_results
            result=reference.run(channel=channel,extras=extras)
            self.assertEqual((public(models[0].memory),events(models[0].events),models[0].calls,models[0].r[2]),
                (public(reference.memory),events(reference.events),reference.calls,result))
            for i,(entry,words) in enumerate(((outer_entry,104),(screen.ENTRY,56),(buffers.screen.ENTRY,194))):
                reached[i].update(models[0].visits & set(range(entry,entry+words*4,4)))
            cases+=1
        self.assertEqual([len(reached[0]),len(reached[1])],[104,56])
        self.receipt('connected',cases=cases,executions=cases*2,
            actual_caller_words=104,actual_extras_words=56,actual_buffer_words=194,
            reached_words=[len(v) for v in reached],independent_complete_chain_memory_access_call_and_failure_reference=True,
            main_loader_auxiliary_event_resource_request_allocator_copy_free_callbacks_remain_bounded=True)


NATIVE=r'''
#define NULL ((void *)0)
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u16 D_800C5628[256];u32 *D_800C5338[256];
static u32 old[16][3],fresh[16][3],third[16][3],calls[16][4],savedCalls[16][4];
static s32 identity,loads,mutation,alias,pattern;
static u32 values[]={0,1,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFF};
u32 func_1510D0EC(u32 input,s32 zero,s32 command,s32 active) {
    u32 result; s32 n=loads++;
    calls[n][0]=input;calls[n][1]=zero;calls[n][2]=command;calls[n][3]=active;
    if(mutation==1) {
        if(n==0) { D_800C5338[identity]=(u32 *)fresh;D_800C5628[identity]=5;fresh[1][1]=0xF0123456; }
        if(n==1) { D_800C5338[identity]=(u32 *)third;D_800C5628[identity]=3;third[2][1]=0x81234567; }
        if(n==2) { D_800C5338[identity]=(u32 *)old;D_800C5628[identity]=1; }
    } else if(mutation==2) D_800C5628[identity]=1;
    else if(mutation==3 && n==0) { D_800C5338[identity]=(u32 *)fresh;fresh[1][1]=0xF1234567; }
    result=pattern<6?values[pattern]:(pattern==6?(n?0x90000000:0x80000000):(n?0x80000000:0));
    if(alias==1 && n==0) result=(u32)fresh;
    if(alias==2) result=0x80000000;
    return result;
}
static s32 reference(s32 id) {
    u32 *cursor;u32 value,*destination,errors=0; s32 i=0,offset=0;
    if(!D_800C5628[id]) return 0;
    cursor=D_800C5338[id];
    for(;;) {
        value=func_1510D0EC(cursor[1],0,0x3E,1);
        destination=(u32 *)((u8 *)D_800C5338[id]+offset);*destination=value;
        cursor=(u32 *)((u8 *)D_800C5338[id]+offset);
        if(cursor[0]==0x80000000) errors|=0x10;
        i++;if(i>=D_800C5628[id]) return errors;
        offset+=12;cursor+=3;
    }
}
static void reset(s32 id,s32 count,s32 pat,s32 mut,s32 kind) {
    s32 i,j;identity=id;loads=0;pattern=pat;mutation=mut;alias=kind;
    for(i=0;i<256;i++) { D_800C5338[i]=NULL;D_800C5628[i]=0; }
    for(i=0;i<16;i++) for(j=0;j<3;j++) {
        old[i][j]=0xA5000000U+i*17+j;fresh[i][j]=0xB6000000U+i*17+j;third[i][j]=0xC7000000U+i*17+j;
    }
    fresh[0][0]=0x80000000;
    D_800C5338[id]=(u32 *)old;
    if(kind==1) {
        D_800C5338[id]=(u32 *)&D_800C5338[id];
        D_800C5338[id+1]=(u32 *)0xF1234567U;
    }
    if(kind==2) D_800C5338[id]=(u32 *)&D_800C5628[id];
    D_800C5628[id]=(u16)count;
}
static u8 savedMemory[sizeof(old)+sizeof(fresh)+sizeof(third)+sizeof(D_800C5628)+sizeof(D_800C5338)];
static s32 bytes(const void *data,s32 size,s32 *offset,s32 save) {
    const u8 *p=data;s32 i;
    for(i=0;i<size;i++) {
        if(save) savedMemory[*offset+i]=p[i];else if(savedMemory[*offset+i]!=p[i]) return 0;
    }
    *offset+=size;return 1;
}
static s32 memory(s32 save) {
    s32 offset=0;
#define CHECK(x) if(!bytes(x,sizeof(x),&offset,save)) return 0
    CHECK(old);CHECK(fresh);CHECK(third);CHECK(D_800C5628);CHECK(D_800C5338);
#undef CHECK
    return offset==(s32)sizeof(savedMemory);
}
'''
NATIVE_MAIN=r'''
static s32 check(s32 id,s32 count,s32 pat,s32 mut,s32 kind) {
    s32 result,n,i,j;
    reset(id,count,pat,mut,kind);result=reference(id);n=loads;if(!memory(1)) return 5;
    for(i=0;i<n;i++) for(j=0;j<4;j++) savedCalls[i][j]=calls[i][j];
    reset(id,count,pat,mut,kind);
    if(func_1503DC3C(id)!=result || loads!=n || !memory(0)) return 1;
    for(i=0;i<n;i++) for(j=0;j<4;j++) if(savedCalls[i][j]!=calls[i][j]) return 2;
    return 0;
}
static s32 main(void) {
    static s32 ids[]={0,8,128,186},counts[]={0,1,2,8,15},large[]={0x7FFF,0x8000,0xFFFF};
    s32 id,k,p,m,a,result,cases=0;
    if(sizeof(void *)!=4 || sizeof(s32)!=4) return 9;
    for(id=0;id<4;id++) for(k=0;k<5;k++) for(p=0;p<8;p++) for(m=0;m<4;m++) for(a=0;a<3;a++) {
        result=check(ids[id],counts[k],p,m,a);if(result) return result;cases++;
    }
    for(id=0;id<4;id++) for(k=0;k<3;k++) for(p=0;p<8;p++) {
        result=check(ids[id],large[k],p,2,0);if(result) return result;cases++;
    }
    return cases==2016?0:3;
}
void _start(void) {
    s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();
}
'''


if __name__=='__main__':
    unittest.main()
