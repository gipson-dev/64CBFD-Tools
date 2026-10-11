"""Complete main loading, live relocation, rollback and unchanged-owner audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_resource_extras_match as extras_module
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

S, STACK = screen.SYMBOLS, guest.STACK
BLOCK, CONFIG, PRIMARY, SECONDARY, NEW_PRIMARY, NEW_SECONDARY = (
    0x50000,0x42000,0x44000,0x46000,0x48000,0x4A000)
EXTRAS, AUX, OTHER, LAST = 0x4C000,0x4D000,0x4E000,0x4F000
ROLES = dict(request='func_1502B6BC',relocate='func_1503D438',
    child='func_1503D368',extras='func_1503DC3C',event='func_1510CE60',
    prepare='func_1503D984',secondary='func_1503D804',auxiliary='func_150028BC',
    third='func_1503D774',fourth='func_1503D660',cleanup='func_1503DD1C',
    free='func_10004074')
ARITIES = dict(request=6,relocate=2,child=2,extras=1,event=5,prepare=1,
    secondary=1,auxiliary=1,third=2,fourth=2,cleanup=1,free=1)
HALVES = {'D_800C4310','D_800C57A0','D_800C4778','D_800C5628','D_800C4ED0'}


def address(table,identity=7,symbols=S):
    return (symbols[table]+identity*(2 if table in HALVES else 4))&0xFFFFFFFF


def fixture(identity=7,first_count=2,second_count=2,extra_count=2,
        present=False,boundary=True,flags=0,optional=7,symbols=S):
    memory={STACK+i:0xA5 for i in range(-0x600,0xC0)}
    for base,size in ((BLOCK,0x300),(CONFIG,0x40),(PRIMARY,0x100),(SECONDARY,0x100),
            (NEW_PRIMARY,0x100),(NEW_SECONDARY,0x100),(EXTRAS,0x100)):
        memory.update({base+i:(i*17+0x35)&255 for i in range(size)})
    for name in symbols:
        if not name.startswith('D_'): continue
        location=address(name,identity,symbols); size=2 if name in HALVES else 4
        memory.update({location+i:0xA5 for i in range(size)})
        put(memory,location,0,size)
    put(memory,address('D_800D19A0',identity,symbols),BLOCK+0x38 if present else 0)
    for table,value,mask in (('D_800C6360',LAST,1),('D_800C5C08',AUX,2),('D_800C6070',OTHER,4)):
        put(memory,address(table,identity,symbols),value if optional&mask else 0)
    header=(BLOCK+0xB8 if boundary else 0,0x1B,PRIMARY,first_count*4,
        0x80000100,0xA7,EXTRAS,extra_count*12,0xFFFFFFFF,0xDEADBEEF,
        SECONDARY,second_count*4,0x12345678,0xF1234567)
    for i,value in enumerate(header): put(memory,BLOCK+i*4,value)
    for base in (PRIMARY,SECONDARY,NEW_PRIMARY,NEW_SECONDARY):
        for i in range(16): put(memory,base+i*4,0x90000000+(base>>4)+i)
    for i in range(16):
        put(memory,EXTRAS+i*12,0x100+i)
        put(memory,EXTRAS+i*12+4,0x81000000+i)
        put(memory,EXTRAS+i*12+8,0xA5000000+i)
    put(memory,CONFIG+24,flags)
    return memory


def helper(model,role):
    number=model.numbers.get(role,0); model.numbers[role]=number+1
    for location,value,size in model.actions.get((role,number),()):
        model.put(location,value,size)
    result=model.results.get(role,BLOCK if role=='request' else 0)
    return (result[min(number,len(result)-1)] if isinstance(result,tuple) else result)&0xFFFFFFFF


class MainOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,identity=7,unused=0,config=CONFIG,extras=1,
            flags=0,phase=0,entry=screen.ENTRY,symbols=S,results=None,actions=None,connected=None):
        super().__init__(words,memory,arguments=(identity&0xFFFFFFFF,unused&0xFFFFFFFF,
            config,extras&0xFFFFFFFF,flags&0xFFFFFFFF),phase=phase,entry=entry,connected=connected)
        self.symbols,self.results,self.actions=symbols,results or {},actions or {}
        self.numbers={}; self.publicFault=None; self.publicAccesses=0
        self.hi=0
    def public_gate(self,location):
        if not STACK-0x600<=location<STACK+0xC0:
            if self.publicAccesses==self.publicFault: raise guest.AccessFault(self.publicAccesses)
            self.publicAccesses+=1
    def get(self,location,size):
        self.public_gate(location)
        return super().get(location,size)
    def put(self,location,value,size):
        if self.recording and hasattr(self,'publicAccesses'): self.public_gate(location)
        super().put(location,value,size)
    def execute(self,word):
        if word>>26==0 and word&63==27:
            numerator,denominator=self.r[word>>21&31],self.r[word>>16&31]
            assert denominator!=0,'fixture must not divide by zero'
            self.lo,self.hi=divmod(numerator,denominator)
        else:
            super().execute(word)
    def record_call(self,target):
        role=next((r for r,n in ROLES.items() if self.symbols[n]==target),None)
        if role is None:
            assert target==extras_module.LOAD,hex(target)
            args=tuple(self.r[4:8])
        else:
            arity=ARITIES[role]; args=tuple(self.r[4:4+min(arity,4)])
            args+=tuple(read(self.memory,self.r[29]+16+(i-4)*4) for i in range(4,arity))
            if role=='request': args=(('private-output',),*args[1:])
        self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        role=next((r for r,n in ROLES.items() if self.symbols[n]==target),None)
        if role is None:
            assert target==extras_module.LOAD
            result=helper(self,'extra-request')
        else:
            if role=='request': self.put(self.r[4],0x12345678,4)
            result=helper(self,role)
        extras_module.clobber(self,result)


class Reference(preparation.Reference):
    def call(self,role,*args):
        target=self.symbols[ROLES[role]]
        self.calls.append((target,*args)); self.events.append(('CALL',target,args))
        return helper(self,role)
    def run(self,identity=7,unused=0,config=CONFIG,extras=1,flags=0):
        identity_word=identity&0xFFFFFFFF
        if identity_word==255 or signed(identity_word)>=187: return 0
        slot=lambda table:address(table,identity_word,self.symbols)
        main=slot('D_800D19A0')
        if self.get(main): return 0
        block=self.call('request',('private-output',),7,0,2,1,identity_word)
        if not block: return 1
        self.put(main,(block+0x38)&0xFFFFFFFF)
        for table,offset in (('D_800C4020',0),('D_800C4488',8),('D_800C48F0',40),
                ('D_800C4BE0',16),('D_800C5338',24),('D_800C5048',32)):
            self.put(slot(table),self.get(block+offset))
        self.put(slot('D_800C4310'),self.get(block+4)>>2,2)
        boundary=self.get(slot('D_800C4020'))
        if not boundary: boundary=self.get(slot('D_800C4488'))
        self.put(slot('D_800C57A0'),((boundary-block-0x38)&0xFFFFFFFF)>>4,2)
        count=(self.get(block+12)>>2)&0xFFFF
        self.put(slot('D_800C4778'),count,2)
        index=0
        if count:
            while True:
                base=self.get(slot('D_800C4488')); self.call('relocate',base+index*4,block)
                base=self.get(slot('D_800C4488')); self.call('child',self.get(base+index*4),block)
                count=self.get(slot('D_800C4778'),2); index+=1
                if index>=count: break
                assert index<16,'unbounded first reference loop'
        cached=self.get(block+44)>>2
        for index in range(cached):
            assert index<16,'unbounded cached reference loop'
            base=self.get(slot('D_800C48F0')); self.call('relocate',base+index*4,block)
            base=self.get(slot('D_800C48F0')); self.call('child',self.get(base+index*4),block)
        self.put(slot('D_800C5628'),self.get(block+28)//12,2)
        self.put(slot('D_800C4ED0'),self.get(block+20)>>4,2)
        failed=0
        if extras:
            failed=self.call('extras',identity_word)
            if not failed:
                index=0
                while index<self.get(slot('D_800C4778'),2):
                    base=self.get(slot('D_800C4488'))
                    self.call('event',self.get(base+index*4),0,0,0x3E,0); index+=1
                    assert index<16,'unbounded event reference loop'
        if not failed:
            self.call('prepare',identity_word)
            failed=self.call('secondary',identity_word)
        if not failed and ((config and self.get(config+24)&0x4000) or flags&1):
            if self.call('auxiliary',identity_word): failed|=8
        if not failed:
            failed=self.call('third',identity_word,0)
            if not failed: failed=self.call('fourth',identity_word,0)
        if failed:
            value=self.get(slot('D_800C6360'))
            if value: self.call('free',value)
            self.call('cleanup',identity_word)
            for name in ('D_800C5C08','D_800C6070'):
                location=slot(name); value=self.get(location)
                if value: self.call('free',value); self.put(location,0)
            value=self.get(main)
            if value: self.call('free',(value-0x38)&0xFFFFFFFF); self.put(main,0)
        return failed


class GameMainResourceLoaderTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-main-resource-loader-test'; cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>274I',cls.rom,screen.ROM))
        assembly=(cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s'; cls.slot.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+assembly+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',cls.slot,filename='generated_6A3D0'))
    def receipt(self,name,**values):
        assert name!='baseline'
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    @classmethod
    def link(cls,name,symbols=S,entry=screen.ENTRY):
        script=cls.out/('%s-%X.ld'%(name,entry)); elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        size=274 if name in ('original','padded') else cls.meta['body_words']
        return list(struct.unpack_from('>%dI'%size,sections(elf)['.text'][1]))
    def compare(self,memory,forms=None,**settings):
        reference=Reference(memory,symbols=settings.get('symbols',S),
            actions=settings.get('actions'),results=settings.get('results'))
        result=reference.run(**{k:v for k,v in settings.items() if k in ('identity','unused','config','extras','flags')})
        expected=preparation.public(reference.memory),preparation.events(reference.events),reference.calls,result
        models=[MainOracle(words,memory,**settings).run() for words in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls,model.r[2]),expected)
        return models
    def test_01_complete_slot_fitting_shape(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences']),(272,0x88,273))
        self.assertEqual((self.meta['pool_bytes'],self.meta['diagnostics']),(0,''))
        self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(self.link('padded')[:272],self.raw)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse(any(row['function']==screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('shape',words=272,slot_words=274,frame=0x88,raw_differences=273,
            matching_not_achieved=True,new_guards=0)
    def test_02_full_reference_and_all_retail_words(self):
        cases=0; reached=set()
        for first,second,extra,boundary,phase in itertools.product((0,1,3),(0,1,3),(0,2),(False,True),(0,8)):
            settings=dict(phase=phase)
            for failure in (None,'request','extras','secondary','auxiliary','third','fourth'):
                results={} if failure is None else {failure:0 if failure=='request' else 0x80000010}
                for optional in (0,7):
                    models=self.compare(fixture(first_count=first,second_count=second,extra_count=extra,
                        boundary=boundary,flags=0x4000,optional=optional),results=results,**settings)
                    reached.update(models[0].visits);cases+=1
        for identity,present in itertools.product((0,186,187,255,256,0x7FFFFFFF),(False,True)):
            models=self.compare(fixture(identity=identity,present=present),identity=identity)
            reached.update(models[0].visits);cases+=1
        models=self.compare(fixture(),results=dict(secondary=4),
            actions={('cleanup',0):((address('D_800D19A0'),0,4),)})
        reached.update(models[0].visits);cases+=1
        unreachable={0x1503CF68}
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+274*4,4))-unreachable)
        self.receipt('guest',cases=cases,executions=cases*2,reached_retail_words=len(reached),
            unreachable_duplicate_compare=sorted(unreachable),
            independent_complete_public_memory_access_call_and_error_reference=True)
    def test_03_live_loops_and_cleanup_callbacks(self):
        cases=0
        for phase in (0,8):
            count=address('D_800C4778')
            actions={('relocate',0):((address('D_800C4488'),NEW_PRIMARY,4),(count,3,2)),
                ('child',0):((NEW_PRIMARY+4,0x81234567,4),),
                ('child',1):((count,2,2),(address('D_800C48F0'),NEW_SECONDARY,4)),
                ('relocate',2):((BLOCK+44,0,4),(NEW_SECONDARY,0xF1234567,4)),
                ('event',0):((address('D_800C4488'),PRIMARY,4),(count,3,2)),
                ('event',1):((count,2,2),)}
            self.compare(fixture(),phase=phase,actions=actions);cases+=1
            for optional in range(8):
                actions={('cleanup',0):((address('D_800C5C08'),OTHER,4),(address('D_800C6070'),AUX,4)),
                    ('free',1):((address('D_800D19A0'),BLOCK+0x78,4),)}
                self.compare(fixture(optional=optional),phase=phase,actions=actions,results=dict(secondary=4));cases+=1
            for value in (0,1,0xFFFF,0x80000000,0xFFFFFFFF):
                self.compare(fixture(),phase=phase,extras=value,unused=value,flags=value,
                    results=dict(extras=0,prepare=value,secondary=0,auxiliary=value,third=value,fourth=value));cases+=1
        memory=fixture(first_count=0,second_count=0)
        put(memory,BLOCK+8,0);put(memory,BLOCK+40,0)
        self.compare(memory,extras=0);cases+=1
        memory=fixture(present=True)
        del memory[CONFIG+24]
        self.compare(memory,config=0xDEAD0000);cases+=1
        self.receipt('mutations',cases=cases,executions=cases*2,
            live_primary_count_and_bases_cached_secondary_count_and_cleanup_reloads=True)
    def test_04_argument_gates_unsigned_sizes_and_aliases(self):
        cases=0
        for identity,config,flags,extras,phase in itertools.product(
                (-1,0,7,186,0x80000001),(0,CONFIG),(0,1,2,0x80000001),(0,1),(0,8)):
            self.compare(fixture(identity=identity,flags=0),identity=identity,
                config=config,flags=flags,extras=extras,phase=phase);cases+=1
        for count in (0x7FFF,0x8000,0xFFFF,0x10000,0x10001):
            memory=fixture(first_count=0)
            put(memory,BLOCK+12,count*4)
            self.compare(memory,extras=0,
                actions={('child',0):((address('D_800C4778'),1,2),)});cases+=1
        for word in (0,1,0xFFFF,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
            memory=fixture(first_count=0,second_count=0)
            put(memory,BLOCK+4,word);put(memory,BLOCK+20,word);put(memory,BLOCK+28,word)
            self.compare(memory,extras=0);cases+=1
        for name,offset in (('D_800D19A0',0),('D_800C4488',40),('D_800C4778',28)):
            symbols=dict(S);symbols[name]=BLOCK+offset-7*(2 if name in HALVES else 4)
            memory=fixture(symbols=symbols,first_count=1,second_count=1)
            if name=='D_800D19A0': put(memory,BLOCK,0)
            forms=[self.link(n,symbols) for n in ('original','selected','padded')]
            self.compare(memory,forms=forms,symbols=symbols,extras=0);cases+=1
        memory=fixture();del memory[CONFIG+24]
        self.compare(memory,results=dict(extras=0x10));cases+=1
        self.receipt('gates',cases=cases,executions=cases*2,
            signed_identity_word_arguments_shift_division_truncation_and_cross_table_aliases=True,
            high_counts_callback_shrink_only=True)
    def test_05_independent_links_and_public_access_faults(self):
        links=cases=faults=0
        for entry,delta in ((screen.ENTRY,0),(0x15207FF0,0x47FFC),(0x15308004,0x88004)):
            symbols={n:v+delta if n.startswith('D_') else v for n,v in S.items()}
            forms=[self.link(n,symbols,entry) for n in ('original','selected','padded')];links+=3
            for first,extras,result in itertools.product((0,2),(0,1),(0,4)):
                self.compare(fixture(first_count=first,symbols=symbols),forms=forms,
                    entry=entry,symbols=symbols,extras=extras,results=dict(secondary=result));cases+=1
        for first,failure,optional,phase in itertools.product((0,2),
                ('request','extras','secondary','auxiliary','third','fourth'),(0,7),(0,8)):
            memory=fixture(first_count=first,flags=0x4000,optional=optional)
            settings=dict(phase=phase,results={failure:0 if failure=='request' else 4})
            complete=MainOracle(self.retail,memory,**settings).run()
            for index in range(complete.publicAccesses):
                models=[]
                for words in (self.retail,self.raw):
                    model=MainOracle(words,memory,**settings);model.publicFault=index
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.publicAccesses,index);models.append(model)
                self.assertEqual((preparation.public(models[0].memory),preparation.events(models[0].events),models[0].calls),
                    (preparation.public(models[1].memory),preparation.events(models[1].events),models[1].calls));faults+=1
        self.receipt('links-faults',links=links,cases=cases,fired_public_access_fault_pairs=faults,
            private_frame_faults_not_compared=True,full_public_partial_memory_access_call_prefix=True)
    def test_06_effective_compiled_semantic_controls(self):
        controls=(
            ('identity-signed','identity >= 0xBB','(u32)identity >= 0xBB',fixture(identity=-1),dict(identity=-1)),
            ('cached-presence','*mainSlot != NULL','*mainSlot == NULL',fixture(present=True),{}),
            ('request-kind','&output, 7, 0, 2, 1, identity','&output, 6, 0, 2, 1, identity',fixture(),{}),
            ('publication-offset','(u8 *)block + 0x38','(u8 *)block + 0x30',fixture(),{}),
            ('cached-count','index < *count','index < 2',fixture(first_count=2,second_count=0),
                dict(actions={('child',0):((address('D_800C4778'),1,2),)})),
            ('extras-flag','if (extras != 0)','if (extras == 0)',fixture(),dict(extras=1)),
            ('config-mask','& 0x4000','& 0x2000',fixture(flags=0x4000),dict(results=dict(auxiliary=1))),
            ('auxiliary-error','failed |= 8','failed |= 4',fixture(flags=0x4000),dict(results=dict(auxiliary=1))),
            ('skip-free','func_10004074(*mainSlot - 0x38)','(void)(*mainSlot - 0x38)',fixture(),dict(results=dict(secondary=4))),
            ('clear-before-free','func_10004074(*cleanupSlot);\n            *cleanupSlot = NULL;',
                '*cleanupSlot = NULL;\n            func_10004074(*cleanupSlot);',fixture(),dict(results=dict(secondary=4))),
        )
        for name,before,after,memory,settings in controls:
            body=screen.QUALIFIED.replace(before,after);self.assertNotEqual(body,screen.QUALIFIED)
            with patch.object(screen,'ENTRY',0x15400000):
                meta,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            correct=MainOracle(self.retail,memory,**settings).run()
            wrong=MainOracle(words,memory,entry=0x15400000,**settings).run()
            self.assertNotEqual((preparation.public(correct.memory),preparation.events(correct.events),correct.calls,correct.r[2]),
                (preparation.public(wrong.memory),preparation.events(wrong.events),wrong.calls,wrong.r[2]))
        self.receipt('controls',freshly_compiled_effective_controls=len(controls))
    def test_07_complete_owner_and_both_real_padders(self):
        before=(self.out/'before-source').read_text();objects=[]
        run=subprocess.run
        def compile_run(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            with patch('subprocess.run',side_effect=compile_run):
                obj,diagnostics=compile_owner(self.root,self.out,body,name)
            self.assertEqual(diagnostics,[]);objects.append(obj)
        parsed=[parse_object(obj) for obj in objects]
        def fingerprint(data,name):
            text,functions,relocations=data;info=functions[name];start=info['value']
            return info['size'],text[start:start+info['size']],{
                o-start:v for o,v in relocations.items() if start<=o<start+info['size']}
        self.assertEqual(set(parsed[0][1]),set(parsed[1][1]))
        for name in parsed[0][1]:
            if name!=screen.FUNCTION: self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        for route in ('pad_c_object.py','pad_generated_object.py'):
            padded=[]
            for i,obj in enumerate(objects):
                asm=self.out/('owner-%s-%d.s'%(route,i))
                args=[str(obj),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards')],
                    check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True);padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value'];end=start+274*4
            expected=bytearray(padded[0][0]);expected[start:end]=padded[1][0][start:end]
            self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<end},
                {o:v for o,v in padded[1][2].items() if not start<=o<end})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_and_caller_contract_exact=True)
    def test_08_immutable_baseline_and_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text()
        if source==(self.out/'before-source').read_text():
            for name,path in self.paths.items():self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
            self.receipt('linked',installed=False,immutable_baseline_verified=True);return
        recovery_source=screen.install((self.out/'before-source').read_text())
        words=self.link('padded');emitted_words=self.meta['body_words']
        if source!=recovery_source:
            from tools.experiments import game_main_resource_loader_lifetimes as lifetime
            lifetime_source=lifetime.install(recovery_source)
            if source==lifetime_source:
                latest,words=screen.compile_candidate(self.root,self.out,'latest-lifetime',lifetime.SELECTED)
                self.assertEqual((latest['body_words'],latest['frame'],latest['differences']), (274,0x80,271))
            else:
                from tools.experiments import game_main_resource_loader_count_lifetimes as count
                count_source=count.install(lifetime_source)
                if source==count_source:
                    latest,words=screen.compile_candidate(self.root,self.out,'latest-count-lifetime',count.SELECTED)
                    self.assertEqual((latest['body_words'],latest['frame'],latest['differences']), (274,0x78,98))
                else:
                    from tools.experiments import game_main_resource_loader_private_layout as layout
                    self.assertEqual(source,layout.install(count_source))
                    latest,words=screen.compile_candidate(self.root,self.out,'latest-private-layout',layout.SELECTED)
                    self.assertEqual((latest['body_words'],latest['frame'],latest['differences']), (274,0x78,24))
            self.assertEqual((latest['diagnostics'],latest['pool_bytes']),('',0))
            emitted_words=latest['body_words']
        else:
            self.assertEqual(source,recovery_source)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        offset=elf_slot_offset(self.before,screen.ENTRY,274*4)
        struct.pack_into('>274I',expected,offset,*words)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        struct.pack_into('>I',expected,extent,emitted_words*4)
        previous,current=metadata(self.before),metadata(actual)
        self.assertEqual(previous[:2],current[:2]);self.assertEqual(previous[3],current[3])
        symbols=previous[2].copy()
        target=next(s for s in symbols if s[0]==screen.FUNCTION.encode() and s[1]==screen.ENTRY)
        self.assertEqual(target[2],12);symbols[target]-=1;symbols[(target[0],target[1],emitted_words*4,*target[3:])]+=1
        self.assertEqual(+symbols,current[2])
        changed_metadata=0
        for table in current[4:]:
            start,end=table[4],table[4]+table[5]
            changed_metadata+=sum(a!=b for a,b in zip(self.before[start:end],actual[start:end]))
            expected[start:end]=actual[start:end]
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[offset:offset+1096],actual[offset:offset+1096])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            changed_metadata_bytes_including_extent=changed_metadata,
            all_other_ELF_bytes_names_values_data_layout_guards_conversion_rows_exact=True,protected_data=audit)
    def test_09_actual_native32_complete_loader(self):
        for profile in ('-O2','-O0'):
            code,detail=self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_REFERENCE+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        body=screen.QUALIFIED.replace('func_10004074(*mainSlot - 0x38);','(void)(*mainSlot - 0x38);')
        code,_=self.run_native('native-negative',NATIVE+body+NATIVE_REFERENCE+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',cases_per_profile=6048,profiles=['O2','O0'],
            complete_C_every_modeled_memory_byte_and_helper_trace_reference=True,
            effective_missing_main_free_control=True)
    def test_10_actual_parent_main_extras_relocator_buffer_chain(self):
        buffers=extras_module.buffers
        outer_entry=preparation.screen.ENTRY
        banked={}
        for name,entry,rom,count in (
                ('outer',outer_entry,preparation.screen.ROM,104),
                ('extras',extras_module.screen.ENTRY,extras_module.screen.ROM,56),
                ('relocate',S['func_1503D438'],0x6A8E8,9),
                ('buffers',buffers.screen.ENTRY,buffers.screen.ROM,194)):
            words=list(struct.unpack_from('>%dI'%count,self.before,elf_slot_offset(self.before,entry,count*4)))
            self.assertEqual(words,list(struct.unpack_from('>%dI'%count,self.rom,rom)))
            banked[name]=(entry,words)
        symbols={**S,**preparation.S,**buffers.S}
        class Connected(MainOracle):
            def __init__(model,memory,main,channel,extra,results,extra_results,buffer_results,phase):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(main)}
                for name in ('extras','relocate','buffers'):
                    entry,words=banked[name];connected.update({entry+i*4:w for i,w in enumerate(words)})
                super().__init__(banked['outer'][1],memory,entry=outer_entry,
                    connected=connected,symbols=symbols,results=results,phase=phase)
                model.r[4:8]=[buffers.ACTOR,7,channel,extra]
                model.extra_results,model.extra_loads=extra_results,0
                model.buffer_results=buffer_results
                model.allocations=model.copies=model.frees=0;model.record_only=False
            def execute(model,word):
                if word>>26==32: buffers.CopyOracle.execute(model,word)
                else: super().execute(word)
            def record_call(model,target):
                if target in (screen.ENTRY,buffers.screen.ENTRY):
                    arity=5 if target==screen.ENTRY else 2
                    args=tuple(model.r[4:4+min(arity,4)])
                    if arity==5:args+=(read(model.memory,model.r[29]+16),)
                    model.calls.append((target,*args));model.events.append(('CALL',target,args));return
                if target in (buffers.ALLOCATE,buffers.COPY):
                    return buffers.BufferOracle.record_call(model,target)
                super().record_call(target)
            def hook(model,target):
                if target==extras_module.LOAD:
                    value=model.extra_results[min(model.extra_loads,len(model.extra_results)-1)]
                    model.extra_loads+=1;extras_module.clobber(model,value);return
                if target in (buffers.ALLOCATE,buffers.COPY):
                    saved=model.results
                    try:
                        model.results=model.buffer_results
                        value=buffers.helper(model,target,model.calls[-1][1:])
                    finally:model.results=saved
                    extras_module.clobber(model,value);return
                super().hook(target)
        class MainReference(Reference):
            def call(model,role,*args):
                if role=='extras':
                    target=S[ROLES[role]];model.calls.append((target,*args));model.events.append(('CALL',target,args))
                    child=extras_module.Reference(model.memory,results=model.extra_results)
                    value=child.run(args[0]);model.memory=child.memory
                    model.events.extend(child.events);model.calls.extend(child.calls);return value
                value=super().call(role,*args)
                if role=='relocate':
                    word=model.get(args[0])
                    if word and not word&0x0F000000:model.put(args[0],(word+args[1])&0xFFFFFFFF)
                return value
        class OuterReference(preparation.Reference):
            def call(model,role,*args):
                target=preparation.S[preparation.ROLES[role]]
                model.calls.append((target,*args));model.events.append(('CALL',target,args))
                if role=='load':
                    child=MainReference(model.memory,symbols=S,results=model.main_results)
                    child.extra_results=model.extra_results
                    value=child.run(identity=args[0],unused=args[1],config=args[2],extras=args[3],flags=args[4])
                elif role=='buffers':
                    child=buffers.Reference(model.memory,model.buffer_results,{})
                    value=child.run(actor=args[0],channel=args[1])
                else:raise AssertionError(('unexpected outer callback',role))
                model.memory=child.memory;model.events.extend(child.events);model.calls.extend(child.calls)
                return value
        cases=0;reached={name:set() for name in ('outer','main','extras','relocate','buffers')}
        for mode,channel,extra,failure,extra_results,buffer_results,phase in itertools.product(
                range(4),(0,3),(0,1),(None,'request','secondary','third'),
                ((0x90000000,),(0x80000000,0x90000000)),
                ((buffers.PRIVATE,buffers.ALTERNATE),(0,),(buffers.PRIVATE,0)),(0,8)):
            memory=buffers.fixture(mode,channel=channel,source=0)
            memory.update(fixture(first_count=2,second_count=2,extra_count=2,optional=7))
            put(memory,buffers.ACTOR+0xAC,0,1)
            put(memory,buffers.CONFIG+24,0)
            put(memory,BLOCK,BLOCK+0x78)
            results={} if failure is None else {failure:0 if failure=='request' else 4}
            models=[Connected(memory,words,channel,extra,results,extra_results,buffer_results,phase).run()
                for words in (self.retail,self.raw)]
            for name in ('outer','extras','relocate','buffers'):
                entry,words=banked[name]
                reached[name].update(models[0].visits&set(range(entry,entry+len(words)*4,4)))
            reached['main'].update(models[0].visits&set(range(screen.ENTRY,screen.ENTRY+1096,4)))
            reference=OuterReference(memory)
            reference.main_results,reference.extra_results,reference.buffer_results=results,extra_results,buffer_results
            result=reference.run(channel=channel,extras=extra)
            expected=preparation.public(reference.memory),preparation.events(reference.events),reference.calls,result
            for model in models:
                self.assertEqual((preparation.public(model.memory),preparation.events(model.events),model.calls,model.r[2]),expected)
            cases+=1
        self.receipt('connected',cases=cases,executions=cases*2,
            actual_words_mapped=dict(outer=104,main=274,extras=56,relocate=9,buffers=194),
            reached_words={name:len(words) for name,words in reached.items()},
            independent_complete_main_extras_relocator_buffer_parent_memory_access_call_reference=True,
            request_child_auxiliary_cleanup_allocator_copy_free_internals_remain_bounded=True)


NATIVE=r'''
#define NULL ((void *)0)
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u8 *D_800D19A0[256],*D_800C6360[256],*D_800C5C08[256],*D_800C6070[256];
u32 D_800C4020[256],D_800C4BE0[256],D_800C5048[256];
u32 *D_800C4488[256],*D_800C48F0[256],*D_800C5338[256];
u16 D_800C4310[256],D_800C57A0[256],D_800C4778[256],D_800C5628[256],D_800C4ED0[256];
static u32 header[80],primary[16],secondary[16],freshPrimary[16],freshSecondary[16],configWords[8];
static u32 trace[128][7],wantedTrace[128][7];
static s32 id,mode,failedRole,numbers[13],callCount,bad;
static u32 record(s32 role,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f) {
    s32 n=numbers[role]++;u32 *t=trace[callCount++];
    t[0]=role;t[1]=a;t[2]=b;t[3]=c;t[4]=d;t[5]=e;t[6]=f;
    if(callCount>127) bad=1;
    if(mode==1) {
        if(role==2 && n==0) {D_800C4488[id]=freshPrimary;D_800C4778[id]=3;}
        if(role==3 && n==1) {D_800C4778[id]=2;D_800C48F0[id]=freshSecondary;}
        if(role==2 && n==2) header[11]=0;
        if(role==5 && n==0) {D_800C4488[id]=primary;D_800C4778[id]=3;}
        if(role==5 && n==1) D_800C4778[id]=2;
    }
    if(mode==2) {
        if(role==6) configWords[6]=0x4000;
        if(role==11) {D_800C5C08[id]=(u8 *)0x11223344;D_800C6070[id]=(u8 *)0x55667788;}
        if(role==12 && n==1) D_800D19A0[id]=(u8 *)header+0x78;
    }
    if(role==6) return 0x80000010;
    if(role==failedRole) return role==1?0:(role==10?0x80000001:role==4?0x10:4);
    return role==1?(u32)header:0;
}
void *func_1502B6BC(s32 *out,s32 kind,s32 *zero,s32 channel,...) {
    __builtin_va_list ap;s32 active,identity;
    __builtin_va_start(ap,channel);active=__builtin_va_arg(ap,s32);identity=__builtin_va_arg(ap,s32);__builtin_va_end(ap);
    *out=0x12345678;return (void *)record(1,0,kind,(u32)zero,channel,active,identity);
}
void func_1503D438(u32 *p,u32 base) {record(2,(u32)p,base,0,0,0,0);}
s32 func_1503D368(u32 value,u32 base) {return record(3,value,base,0,0,0,0);}
s32 func_1503DC3C(s32 identity) {return record(4,identity,0,0,0,0,0);}
void func_1510CE60(u32 value,s32 a,s32 b,s32 c,s32 d) {record(5,value,a,b,c,d,0);}
s32 func_1503D984(s32 identity) {return record(6,identity,0,0,0,0,0);}
s32 func_1503D804(s32 identity) {return record(7,identity,0,0,0,0,0);}
s32 func_150028BC(s32 identity) {return record(8,identity,0,0,0,0,0);}
s32 func_1503D774(s32 identity,s32 zero) {return record(9,identity,zero,0,0,0,0);}
s32 func_1503D660(s32 identity,s32 zero) {return record(10,identity,zero,0,0,0,0);}
s32 func_1503DD1C(s32 identity) {return record(11,identity,0,0,0,0,0);}
void func_10004074(void *p) {record(12,(u32)p,0,0,0,0,0);}
static void reset(s32 identity,s32 first,s32 second,s32 extras,s32 cfg,s32 flags,s32 failure,s32 optional,s32 mutation) {
    s32 i;id=identity;mode=mutation;failedRole=failure;callCount=bad=0;
    for(i=0;i<13;i++) numbers[i]=0;
    for(i=0;i<256;i++) {
        D_800D19A0[i]=(u8 *)0xA5A5A5A5;D_800C6360[i]=(u8 *)0xA5A5A5A5;
        D_800C5C08[i]=(u8 *)0xA5A5A5A5;D_800C6070[i]=(u8 *)0xA5A5A5A5;
        D_800C4020[i]=D_800C4BE0[i]=D_800C5048[i]=0xA5A5A5A5;
        D_800C4488[i]=D_800C48F0[i]=D_800C5338[i]=(u32 *)0xA5A5A5A5;
        D_800C4310[i]=D_800C57A0[i]=D_800C4778[i]=D_800C5628[i]=D_800C4ED0[i]=0xA5A5;
    }
    D_800D19A0[id]=NULL;D_800C6360[id]=optional&1?(u8 *)0x12345678:NULL;
    D_800C5C08[id]=optional&2?(u8 *)0x23456789:NULL;D_800C6070[id]=optional&4?(u8 *)0x3456789A:NULL;
    for(i=0;i<80;i++) header[i]=0xA5000000+i;
    for(i=0;i<16;i++) {primary[i]=0x90000000+i;secondary[i]=0xA0000000+i;freshPrimary[i]=0xB0000000+i;freshSecondary[i]=0xC0000000+i;}
    for(i=0;i<8;i++) configWords[i]=0;
    configWords[6]=cfg?0x4000:0;
    header[0]=cfg?(u32)header+0xB8:0;header[1]=0x1B;header[2]=(u32)primary;
    header[3]=first*4;header[4]=0x80000100;header[5]=0xA7;header[6]=0x81000000;
    header[7]=extras*12;header[8]=0xFFFFFFFF;header[10]=(u32)secondary;header[11]=second*4;
}
static u8 wantedMemory[16000];
static s32 bytes(const void *p,s32 length,s32 *offset,s32 save) {
    const u8 *v=p;s32 i;
    if(*offset+length>16000) return 0;
    for(i=0;i<length;i++) {if(save) wantedMemory[*offset+i]=v[i];else if(wantedMemory[*offset+i]!=v[i]) return 0;}
    *offset+=length;return 1;
}
static s32 memory(s32 save) {
    s32 offset=0;
#define CHECK(x) if(!bytes(x,sizeof(x),&offset,save)) return 0
    CHECK(header);CHECK(primary);CHECK(secondary);CHECK(freshPrimary);CHECK(freshSecondary);CHECK(configWords);
    CHECK(D_800D19A0);CHECK(D_800C6360);CHECK(D_800C5C08);CHECK(D_800C6070);
    CHECK(D_800C4020);CHECK(D_800C4BE0);CHECK(D_800C5048);CHECK(D_800C4488);CHECK(D_800C48F0);CHECK(D_800C5338);
    CHECK(D_800C4310);CHECK(D_800C57A0);CHECK(D_800C4778);CHECK(D_800C5628);CHECK(D_800C4ED0);
#undef CHECK
    return 1;
}
'''
NATIVE_REFERENCE=r'''
static s32 reference(s32 identity,s32 unused,u8 *cfg,s32 extras,s32 flags) {
    s32 i;u32 cached,error,base=(u32)header,boundary;
    if(identity==255 || identity>=187 || D_800D19A0[identity]) return 0;
    if(!record(1,0,7,0,2,1,identity)) return 1;
    D_800D19A0[identity]=(u8 *)header+0x38;
    D_800C4020[identity]=header[0];D_800C4488[identity]=(u32 *)header[2];D_800C48F0[identity]=(u32 *)header[10];
    D_800C4BE0[identity]=header[4];D_800C5338[identity]=(u32 *)header[6];D_800C5048[identity]=header[8];
    D_800C4310[identity]=(u16)(header[1]/4);
    boundary=D_800C4020[identity];if(!boundary) boundary=(u32)D_800C4488[identity];
    D_800C57A0[identity]=(u16)((boundary-base-56)/16);
    D_800C4778[identity]=(u16)(header[3]/4);i=0;
    while(i<D_800C4778[identity]) {
        record(2,(u32)(D_800C4488[identity]+i),base,0,0,0,0);
        record(3,D_800C4488[identity][i],base,0,0,0,0);i++;
    }
    cached=header[11]/4;
    for(i=0;(u32)i<cached;i++) {
        record(2,(u32)(D_800C48F0[identity]+i),base,0,0,0,0);
        record(3,D_800C48F0[identity][i],base,0,0,0,0);
    }
    D_800C5628[identity]=(u16)(header[7]/12);D_800C4ED0[identity]=(u16)(header[5]/16);
    error=extras?record(4,identity,0,0,0,0,0):0;
    if(extras && !error) for(i=0;i<D_800C4778[identity];i++) record(5,D_800C4488[identity][i],0,0,0x3E,0,0);
    if(!error) {record(6,identity,0,0,0,0,0);error=record(7,identity,0,0,0,0,0);}
    if(!error && ((cfg && *(u32 *)(cfg+24)&0x4000) || flags&1)) if(record(8,identity,0,0,0,0,0)) error=8;
    if(!error) {error=record(9,identity,0,0,0,0,0);if(!error) error=record(10,identity,0,0,0,0,0);}
    if(error) {
        if(D_800C6360[identity]) record(12,(u32)D_800C6360[identity],0,0,0,0,0);
        record(11,identity,0,0,0,0,0);
        if(D_800C5C08[identity]) {record(12,(u32)D_800C5C08[identity],0,0,0,0,0);D_800C5C08[identity]=NULL;}
        if(D_800C6070[identity]) {record(12,(u32)D_800C6070[identity],0,0,0,0,0);D_800C6070[identity]=NULL;}
        if(D_800D19A0[identity]) {record(12,(u32)D_800D19A0[identity]-56,0,0,0,0,0);D_800D19A0[identity]=NULL;}
    }
    return error;
}
'''
NATIVE_MAIN=r'''
static s32 check(s32 identity,s32 first,s32 second,s32 extras,s32 cfg,s32 flags,s32 failure,s32 optional,s32 mutation) {
    s32 result,count,i,j;
    reset(identity,first,second,extras,cfg,flags,failure,optional,mutation);
    result=reference(identity,0,cfg?(u8 *)configWords:NULL,extras,flags);count=callCount;
    if(!memory(1) || bad) return 4;
    for(i=0;i<count;i++) for(j=0;j<7;j++) wantedTrace[i][j]=trace[i][j];
    reset(identity,first,second,extras,cfg,flags,failure,optional,mutation);
    if(func_1503CF20(identity,0,cfg?(u8 *)configWords:NULL,extras,flags)!=result || callCount!=count || bad || !memory(0)) return 1;
    for(i=0;i<count;i++) for(j=0;j<7;j++) if(wantedTrace[i][j]!=trace[i][j]) return 2;
    return 0;
}
static s32 main(void) {
    static s32 ids[]={0,7,186},counts[]={0,1,3},failures[]={0,1,4,7,8,9,10};
    s32 id,c,s,e,f,g,h,o,m,result,cases=0;
    if(sizeof(void *)!=4 || sizeof(s32)!=4) return 9;
    for(id=0;id<3;id++) for(c=0;c<3;c++) for(s=0;s<2;s++) for(e=0;e<2;e++) for(f=0;f<2;f++)
    for(g=0;g<2;g++) for(h=0;h<7;h++) for(o=0;o<2;o++) for(m=0;m<3;m++) {
        result=check(ids[id],counts[c],s*2,e,f,g,failures[h],o*7,m);if(result) return result;cases++;
    }
    return cases==6048?0:3;
}
void _start(void) {
    s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();
}
'''


if __name__=='__main__':
    unittest.main()
