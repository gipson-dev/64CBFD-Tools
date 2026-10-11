"""Complete resource-buffer modes, live helper mutations and failure rollback."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_resource_buffers_candidates as screen
from tools.experiments import game_resource_buffers_matching as matching
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_owner_state_match import metadata

S, STACK = screen.SYMBOLS, guest.STACK
ACTOR, IDS, CONFIG, SOURCE, PRIVATE, ALTERNATE = 0x20000, 0x21000, 0x22000, 0x23000, 0x24000, 0x25000
ALLOCATE, COPY, FREE = S['allocate_memory'], S['bcopy'], S['func_10004074']
SLOTS = ((0,0),(SOURCE,0),(0,SOURCE),(PRIVATE,0),(0,PRIVATE),
    (PRIVATE,PRIVATE),(SOURCE,SOURCE),(PRIVATE,ALTERNATE),(SOURCE,PRIVATE))


def fixture(mode=0, identity=7, refs=1, slots=(0,0), parent=0, channel=0, units=2,
        config=CONFIG, source=SOURCE, symbols=S, actor=ACTOR):
    memory = {STACK+i:0xA5 for i in range(-0x400,0x100)}
    for base,length in ((actor,0x340),(IDS,8),(CONFIG,32),(SOURCE,256),
            (PRIVATE,256),(ALTERNATE,256),(symbols['D_800D19A0'],1024),
            (symbols['D_800D1F80'],256),(symbols['D_800C57A0'],512)):
        for i in range(length): memory[(base+i)&0xFFFFFFFF]=(i*137+19)&255
    pointer = (symbols['D_800CC0E8']+parent*812)&0xFFFFFFFF
    for i in range(4): memory[pointer+i]=0xA5
    put(memory,pointer,config)
    put(memory,actor+0x65,parent,1); put(memory,actor+0x144,config)
    put(memory,actor+0x2C4,IDS); put(memory,IDS+channel,identity,1)
    put(memory,CONFIG+0x10,mode,1)
    for i,value in enumerate(slots): put(memory,actor+channel*8+0x28C+i*4,value)
    put(memory,symbols['D_800D19A0']+identity*4,source)
    put(memory,symbols['D_800D1F80']+identity,refs,1)
    put(memory,symbols['D_800C57A0']+identity*2,units,2)
    return memory


def external_memory(memory):
    return {a:v for a,v in memory.items() if not STACK-0x400 <= a < STACK+0x100}


def external_events(events):
    return [e for e in events if e[0]=='CALL' or not STACK-0x400 <= e[1] < STACK+0x100]


def helper(model, target, args):
    if target == ALLOCATE:
        index = model.allocations
        model.allocations += 1
        for address,value,size in model.actions.get(('alloc',index),()): model.put(address,value,size)
        return model.results[index] if index < len(model.results) else PRIVATE
    if target == COPY:
        source,destination,length = args
        if length <= 64:
            snapshot = [model.get((source+i)&0xFFFFFFFF,1) for i in range(length)]
            for i,value in enumerate(snapshot): model.put((destination+i)&0xFFFFFFFF,value,1)
        else:
            assert model.record_only, 'large copy requires an explicitly bounded receipt'
        index = model.copies; model.copies += 1
        for address,value,size in model.actions.get(('copy',index),()): model.put(address,value,size)
        return 0
    assert target == FREE, hex(target)
    model.frees += 1
    for address,value,size in model.actions.get(('free',model.frees-1),()): model.put(address,value,size)
    return 0


class BufferOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,actor=ACTOR,channel=0,phase=0,results=(PRIVATE,ALTERNATE),
            actions=None,record_only=False,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,arguments=(actor,channel),phase=phase,entry=entry,connected=connected)
        self.results,self.actions,self.record_only=results,actions or {},record_only
        self.allocations,self.copies,self.frees=0,0,0
    def execute(self,word):
        if word >> 26 == 32: CopyOracle.execute(self,word)
        else: super().execute(word)
    def record_call(self,target):
        assert target in (ALLOCATE,COPY,FREE),hex(target)
        args = tuple(self.r[4:4+{ALLOCATE:4,COPY:3,FREE:1}[target]])
        self.calls.append((target,*args)); self.events.append(('CALL',target,args))
    def hook(self,target):
        args = self.calls[-1][1:]
        result = helper(self,target,args)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class Reference:
    def __init__(self,memory,results,actions,record_only=False):
        self.memory,self.events,self.calls=memory.copy(),[],[]
        self.results,self.actions,self.record_only=results,actions or {},record_only
        self.allocations,self.copies,self.frees=0,0,0
    def get(self,address,size=4):
        assert all(address+i in self.memory for i in range(size))
        value=read(self.memory,address,size); self.events.append(('R',address,size,value)); return value
    def put(self,address,value,size=4):
        assert all(address+i in self.memory for i in range(size))
        put(self.memory,address,value,size); self.events.append(('W',address,size,value&((1<<(size*8))-1)))
    def call(self,target,*args):
        self.calls.append((target,*args)); self.events.append(('CALL',target,args))
        return helper(self,target,args)
    def run(self,actor=ACTOR,channel=0,symbols=S):
        parent=self.get(actor+0x65,1)
        config=self.get(symbols['D_800CC0E8']+parent*812 if parent else actor+0x144)
        identity=self.get(self.get(actor+0x2C4)+channel,1)
        mode=self.get(config+16,1)&3 if config else 0
        if identity==0: mode=2
        pair=actor+channel*8+0x28C
        first=self.get(pair)
        if first and self.get(pair+4): return 0
        resource=symbols['D_800D19A0']+identity*4
        source=self.get(resource)
        if not source: return 0
        count=symbols['D_800D1F80']+identity
        size_address=symbols['D_800C57A0']+identity*2
        if mode==0:
            self.put(pair+4,source); self.put(pair,source)
            self.put(count,self.get(count,1)+2,1); return 0
        if mode==1:
            failed=0
            if not first or first==source:
                if self.get(count,1):
                    size=self.get(size_address,2)*16
                    allocated=self.call(ALLOCATE,size,1,2,2); self.put(pair,allocated)
                    if not allocated: failed=1
                    else:
                        target=self.get(pair)
                        if target: self.call(COPY,self.get(resource),target,size)
                        else: self.put(pair,self.get(resource))
                else:
                    self.put(pair+4,source); self.put(pair,source)
                    self.put(count,self.get(count,1)+2,1)
                first=self.get(pair)
            self.put(pair+4,first); return failed
        if mode!=2: return 0
        for index in range(2):
            slot=pair+index*4; value=self.get(slot)
            eligible=not value or value==self.get(resource)
            if not eligible and index==1:
                eligible=self.get(pair)==self.get(pair+4)
            if not eligible: continue
            if self.get(count,1):
                size=self.get(size_address,2)*16
                allocated=self.call(ALLOCATE,size,1,2,2); self.put(slot,allocated)
                if not allocated:
                    if index==1:
                        first=self.get(pair)
                        if first!=self.get(resource): self.call(FREE,first)
                        else: self.put(count,self.get(count,1)-1,1)
                        self.put(pair,0)
                    return 1
                target=self.get(slot)
                if target: self.call(COPY,self.get(resource),target,size)
                else: self.put(slot,self.get(resource))
            else:
                self.put(slot,self.get(resource)); self.put(count,self.get(count,1)+1,1)
        return 0


class GameResourceBuffersTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-resource-buffers-test'; cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        if not (cls.out/'matching-baseline.json').exists():
            assert (cls.root/screen.SOURCE).read_text()==screen.install(
                (cls.out/'before-source').read_text(),screen.QUALIFIED)
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes(); (cls.out/('matching-before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'matching-baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.matching_baseline=json.loads((cls.out/'matching-baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('matching-before-'+name)).read_bytes()).hexdigest()==cls.matching_baseline[name]
        cls.body=matching.QUALIFIED
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected',cls.body)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>194I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes()
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot=cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_AEB40'))
        cls.historical_meta,_=screen.compile_candidate(cls.root,cls.out,'historical',screen.QUALIFIED)
        cls.assemble('historical-padded',emit_padded_assembly(cls.out/'historical.o',slot,filename='generated_AEB40'))
    def receipt(self,name,**values):
        assert name!='baseline'
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,symbols=S,**settings):
        reference=Reference(memory,settings.get('results',(PRIVATE,ALTERNATE)),
            settings.get('actions'),settings.get('record_only',False))
        result=reference.run(settings.get('actor',ACTOR),settings.get('channel',0),symbols)
        expected=(external_memory(reference.memory),external_events(reference.events),reference.calls,result)
        models=[BufferOracle(words,memory,**settings).run() for words in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((external_memory(model.memory),external_events(model.events),model.calls,model.r[2]),expected)
        self.assertEqual(models[0].memory,models[1].memory)
        self.assertEqual(models[0].events,models[1].events)
        return models
    def test_01_complete_candidate_shape(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['diagnostics']),
            (194,0x60,0,''))
        self.assertEqual(self.meta['differences'],39)
        self.assertEqual((self.historical_meta['body_words'],self.historical_meta['differences']),(192,130))
        self.receipt('shape',words=194,retail_words=194,frame=96,real_word_differences=39,
            historical_words=192,historical_differences=130,
            matching=False,new_guards=0)
    def test_02_all_modes_boundaries_pairs_failures(self):
        coverage=set(); cases=0
        for mode,identity,refs,slots,results,phase in itertools.product(range(4),(0,1,128,255),
                (0,1,127,128,254,255),SLOTS,((PRIVATE,ALTERNATE),(0,ALTERNATE),(PRIVATE,0),(0,0)),(0,8)):
            models=self.compare(fixture(mode,identity,refs,slots),results=results,phase=phase)
            coverage.update(models[0].visits); cases+=1
        for value in range(256):
            self.compare(fixture(0,value,0)); self.compare(fixture(0,7,value)); cases+=2
        self.assertEqual(len(coverage),172)
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=len(coverage),
            saved_registers_GP_FPR_lifetimes_checked=True,full_memory_and_access_order_equal=True,
            all_ids_all_counts_and_mode_slot_failure_boundary_product=True)
    def test_03_parent_channel_size_and_helper_mutations(self):
        cases=0
        for parent,channel,mode,units in itertools.product((0,1,26,128,255),(0,1,3),
                (0,1,2,3,0xFC,0xFD,0xFE,0xFF),(0,1,2,4,0x7FFF,0x8000,0xFFFF)):
            self.compare(fixture(mode,parent=parent,channel=channel,units=units),
                channel=channel,record_only=units>4); cases+=1
        for mode in range(4):
            self.compare(fixture(mode,config=0)); self.compare(fixture(mode,source=0)); cases+=2
        for mode,results,actions in itertools.product((1,2),((PRIVATE,ALTERNATE),(PRIVATE,0),(0,0)),(
                {('alloc',0):((S['D_800D19A0']+28,ALTERNATE,4),)},
                {('alloc',0):((S['D_800C57A0']+14,3,2),)},
                {('alloc',0):((S['D_800D1F80']+7,0,1),)},
                {('copy',0):((ACTOR+0x28C,SOURCE,4),)},
                {('copy',0):((ACTOR+0x290,PRIVATE,4),)},
                {('copy',0):((S['D_800D19A0']+28,PRIVATE,4),)},
                {('free',0):((ACTOR+0x28C,ALTERNATE,4),)},
                {('alloc',1):((S['D_800D19A0']+28,PRIVATE,4),(S['D_800D1F80']+7,0,1))})):
            self.compare(fixture(mode),results=results,actions=actions); cases+=1
        self.receipt('mutations',cases=cases,executions=cases*2,full_unsigned_parent_and_size_extremes=True,
            large_copy_callbacks_record_only=True,live_resource_size_count_slot_and_free_mutations=True)
    def test_04_fired_all_access_fault_prefixes(self):
        pairs=0
        for mode,slots,results,phase in itertools.product(range(4),((0,0),(PRIVATE,0),(SOURCE,0)),
                ((PRIVATE,ALTERNATE),(0,ALTERNATE),(PRIVATE,0)),(0,8)):
            memory=fixture(mode,slots=slots)
            complete=self.compare(memory,results=results,phase=phase)[0]
            for ordinal in range(complete.accesses):
                models=[BufferOracle(w,memory,results=results,phase=phase) for w in (self.retail,self.raw)]
                for model in models:
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                    (models[1].memory,models[1].events,models[1].calls)); pairs+=1
        self.receipt('faults',all_access_pairs=pairs,all_gates_fired=True,
            complete_partial_memory_accesses_and_call_receipts_equal=True,guest_only=True)
    def test_05_copied_owner_and_padding_routes(self):
        before=(self.out/'before-source').read_text(); objects=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before,self.body))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name)
            self.assertEqual(diagnostics,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        parsed=[parse_object(o) for o in objects]
        def fingerprint(data,name):
            text,functions,relocs=data; f=functions[name]; start,end=f['value'],f['value']+f['size']
            return f['size'],text[start:end],{o-start:v for o,v in relocs.items() if start<=o<end}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION: self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for route in ('layout','generated'):
            padded=[]
            for i,obj in enumerate(objects):
                asm=self.out/('owner-%s-%d.s'%(route,i))
                args=['pad_c_object.py',str(obj),str(self.out/'before-layout'),'generated_AEB40',str(asm)] if route=='layout' else [
                    'pad_generated_object.py',str(obj),str(self.root/'conker/asm/AEB40.s'),str(asm),
                    '--filename','generated_AEB40','--rodata-symbol','jtbl_8009CC40_game']
                subprocess.run(['python3',str(self.root/'tools'/args[0]),*args[1:],
                    '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True); padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value']; end=start+776
            expected=bytearray(padded[0][0]); expected[start:end]=padded[1][0][start:end]
            self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<end},
                {o:v for o,v in padded[1][2].items() if not start<=o<end})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_and_guards_unchanged=True)
    @classmethod
    def link(cls,name,symbols=S,entry=screen.ENTRY):
        script=cls.out/('%s-%X.ld'%(name,entry)); elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        length=cls.meta['body_words'] if name=='selected' else 194
        return list(struct.unpack_from('>%dI'%length,sections(elf)['.text'][1]))
    def test_06_relocations_aliases_and_short_circuit_reads(self):
        links=cases=0
        for entry,delta in ((screen.ENTRY,0),(0x15207FF0,0x47FFC),(0x15308004,0x88004)):
            symbols={name:value+delta if name.startswith('D_') else value for name,value in S.items()}
            forms=[self.link(name,symbols,entry) for name in ('original','selected','padded')]; links+=3
            for mode,results in itertools.product(range(4),((PRIVATE,ALTERNATE),(PRIVATE,0),(SOURCE,0))):
                self.compare(fixture(mode,symbols=symbols),forms=forms,symbols=symbols,results=results,entry=entry); cases+=1
        for mode in (0,1,2):
            symbols=dict(S); symbols['D_800D1F80']=ACTOR+0x28C-7
            forms=[self.link(name,symbols) for name in ('original','selected','padded')]; links+=3
            self.compare(fixture(mode,symbols=symbols),forms=forms,symbols=symbols); cases+=1
            symbols=dict(S); symbols['D_800D19A0']=ACTOR+0x28C-28
            forms=[self.link(name,symbols) for name in ('original','selected','padded')]; links+=3
            self.compare(fixture(mode,symbols=symbols,slots=(SOURCE,0)),forms=forms,symbols=symbols); cases+=1
        memory=fixture(slots=(PRIVATE,PRIVATE))
        for start,length in ((S['D_800D19A0'],1024),(S['D_800D1F80'],256),(S['D_800C57A0'],512)):
            for i in range(length): del memory[start+i]
        self.compare(memory); cases+=1
        self.receipt('links',symbol_sets=3,links=links,cases=cases,
            independently_linked_original_candidate_padded_forms=True,
            count_and_resource_slot_aliases_and_complete_pair_no_global_read=True)
    def test_07_effective_fresh_semantic_controls(self):
        controls=(
            ('zero-identity','if (identity == 0)', 'if (0)', fixture(0,identity=0),{}),
            ('share-count','D_800D1F80[identity] += 2', 'D_800D1F80[identity] += 1',fixture(0),{}),
            ('allocate-flags','allocate_memory(size, 1, 2, 2)', 'allocate_memory(size, 1, 1, 2)',fixture(1),{}),
            ('byte-size','D_800C57A0[identity] * 16', 'D_800C57A0[identity] * 8',fixture(1),{}),
            ('failure-result','failed = 1', 'failed = 0',fixture(2),dict(results=(PRIVATE,0))),
            ('skip-free','func_10004074(first)', '(void)first',fixture(2),dict(results=(PRIVATE,0))),
            ('skip-clear','*(u8 **)(pair + 0x28C) = NULL', '(void)pair',fixture(2),dict(results=(PRIVATE,0))),
            ('cached-source','bcopy(D_800D19A0[identity],', 'bcopy(SOURCE_POINTER,',fixture(1),
                dict(actions={('alloc',0):((S['D_800D19A0']+28,ALTERNATE,4),)})))
        for name,old,new,memory,settings in controls:
            body=self.body.replace(old,new)
            if name=='cached-source':
                body=body.replace('    s32 failed;', '    u8 *SOURCE_POINTER;\n    s32 failed;').replace(
                    '    failed = 0;', '    SOURCE_POINTER = D_800D19A0[identity];\n    failed = 0;')
            self.assertNotEqual(body,self.body,name)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            correct=BufferOracle(self.raw,memory,**settings).run(); wrong=BufferOracle(words,memory,**settings).run()
            self.assertNotEqual((external_memory(correct.memory),correct.calls,correct.r[2]),
                (external_memory(wrong.memory),wrong.calls,wrong.r[2]),name)
        self.receipt('negative',fresh_IDO_controls=len(controls),all_effective=True)
    def test_08_native32_actual_complete_C_and_independent_reference(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.RECORD+
                screen.DECLARATIONS+NATIVE_HELPERS+self.body+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,[12288,0,0]))
        wrong=self.body.replace('D_800D1F80[identity] += 2','D_800D1F80[identity] += 1')
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.RECORD+
            screen.DECLARATIONS+NATIVE_HELPERS+wrong+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=12288,profiles=['O2','O0'],
            actual_complete_C_and_independent_state_reference=True,
            all_id_and_count_values_canaries_call_arguments_failure_modes_and_widths=True,
            effective_negative=1)
    def test_09_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
            self.receipt('linked',installed=False); return
        original_source=(self.out/'before-source').read_text()
        historical=source==screen.install(original_source,screen.QUALIFIED)
        self.assertEqual(source,screen.install(original_source,screen.QUALIFIED if historical else self.body))
        selected_words=self.historical_meta['body_words'] if historical else self.meta['body_words']
        selected_size=selected_words*4
        padded=self.link('historical-padded' if historical else 'padded'); expected=bytearray(self.before)
        struct.pack_into('>194I',expected,elf_slot_offset(self.before,screen.ENTRY,776),*padded)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        struct.pack_into('>I',expected,extent,selected_size)
        actual=(self.root/self.paths['elf']).read_bytes()
        before_meta,after_meta=metadata(self.before),metadata(actual)
        self.assertEqual(before_meta[:2],after_meta[:2])
        symbols=before_meta[2].copy()
        target=next(s for s in symbols if s[0]==screen.FUNCTION.encode() and s[1]==screen.ENTRY)
        self.assertEqual(target[2],12)
        symbols[target]-=1
        symbols[(target[0],target[1],selected_size,*target[3:])]+=1
        self.assertEqual(+symbols,after_meta[2]); self.assertEqual(before_meta[3],after_meta[3])
        metadata_bytes=0
        # Newly referenced globals reorder existing symbols and strings, not their values.
        for table in after_meta[4:]:
            start,end=table[4],table[4]+table[5]
            metadata_bytes+=sum(a!=b for a,b in zip(self.before[start:end],actual[start:end]))
            expected[start:end]=actual[start:end]
        self.assertEqual(bytes(expected),actual)
        for name in self.paths:
            if name not in ('source','elf'):
                self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=not historical,historical_recovery_installed=historical,
            target_words=selected_words,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            only_target_slot_extent_and_existing_metadata_order_change=True,
            changed_metadata_bytes=metadata_bytes,
            all_other_ELF_bytes_exact=True,all_other_symbol_values_and_names_exact=True,
            data_guards_census_layout_symbols_and_auto_assignments_unchanged=True,protected_data=audit)
    def test_10_real_allocator_wrapper_and_sdk_copy(self):
        functions=load_elf_functions(str(self.root/self.paths['elf']),'mips-linux-gnu-objdump')[0]
        connected={}
        for name,address in (('allocate_memory',ALLOCATE),('bcopy',COPY)):
            connected.update({address+i*4:w for i,w in enumerate(functions[name])})
        core=0x10003C6C
        wrapper=functions['allocate_memory']
        wrapper_frame=(-wrapper[0])&65535
        wrapper_ra=next(w&65535 for w in wrapper if w>>16==0xAFBF)
        class Connected(BufferOracle):
            def __init__(model,*args,**kwargs):
                super().__init__(*args,**kwargs); model.return_slots={}
            def execute(model,word):
                if word>>26==32 or (word>>26==0 and word&63==32): CopyOracle.execute(model,word)
                else: super().execute(word)
            def record_call(model,target):
                if target==ALLOCATE:
                    address=model.r[29]-wrapper_frame+wrapper_ra
                    model.return_slots.setdefault(address,set()).add(model.r[31])
                if target==core:
                    args=tuple(model.r[4:8])+(read(model.memory,model.r[29]+16,4),)
                    model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                else: super().record_call(target)
            def hook(model,target):
                if target==core:
                    result=helper(model,ALLOCATE,model.calls[-1][1:])
                    for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                    model.f[:20]=[0xA5000000+i for i in range(20)]; model.r[2]=result
                else: super().hook(target)
        cases=0; reached=set()
        for mode,refs,results,units,phase in itertools.product((1,2),(0,1,255),
                ((PRIVATE,ALTERNATE),(PRIVATE,0),(0,0)),(0,1,2,4),(0,8)):
            memory=fixture(mode,refs=refs,units=units)
            models=[Connected(w,memory,results=results,phase=phase,connected=connected).run()
                for w in (self.retail,self.raw)]
            # The wrapper saves the caller continuation, whose PC differs in nonmatching C.
            def normalized(model):
                memory=model.memory.copy(); events=[]
                for address,values in model.return_slots.items():
                    self.assertIn(read(memory,address,4),values); put(memory,address,0)
                for e in model.events:
                    if e[0] in ('R','W') and e[1] in model.return_slots and e[2]==4 and e[3] in model.return_slots[e[1]]:
                        e=(*e[:3],0)
                    events.append(e)
                return memory,events,model.calls,model.r[2]
            self.assertEqual(normalized(models[0]),normalized(models[1]))
            expected=Reference(memory,results,None); result=expected.run()
            self.assertEqual((external_memory(models[0].memory),models[0].r[2]),
                (external_memory(expected.memory),result))
            for call in models[0].calls:
                if call[0]==core: self.assertEqual(call[1:],(units*16,1,2,0,2))
            reached.update(models[0].visits & set(connected)); cases+=1
        self.receipt('sdk',cases=cases,executions=cases*2,connected_words=len(connected),reached_words=len(reached),
            actual_linked_Init_allocate_memory_and_bcopy=True,
            only_actual_wrapper_saved_continuation_PCs_normalized=True,
            allocation_core_and_free_bounded_callbacks=True,hardware_heap_acceptance=False)
    def test_11_complete_original_caller_forwarding(self):
        entry,rom,length=0x1503DA9C,0x6AF4C,104
        outer=list(struct.unpack_from('>104I',self.rom,rom))
        self.assertNotEqual(list(struct.unpack_from('>104I',self.before,elf_slot_offset(self.before,entry,length*4))),outer)
        loader=0x1503CF20
        class Connected(BufferOracle):
            def __init__(model,memory,inner,channel,extras,missing,results,phase):
                super().__init__(outer,memory,channel=7,entry=entry,results=results,phase=phase)
                model.r[6],model.r[7]=channel,extras
                model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
            def record_call(model,target):
                if target==screen.ENTRY:
                    args=tuple(model.r[4:6])
                elif target==loader:
                    args=tuple(model.r[4:8])+(read(model.memory,model.r[29]+16,4),)
                else:
                    return super().record_call(target)
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
            def hook(model,target):
                if target==loader:
                    self.assertEqual(model.calls[-1][1:3],(7,0))
                    model.put(S['D_800D19A0']+28,SOURCE,4)
                    for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                    model.f[:20]=[0xA5000000+i for i in range(20)]; model.r[2]=0
                else: super().hook(target)
        cases=0; invocations=0; reached=set()
        for mode,channel,refs,results,extras,missing,phase in itertools.product(range(4),(0,1,3),(0,1),
                ((PRIVATE,ALTERNATE),(PRIVATE,0),(0,0)),(0,1),(0,1),(0,8)):
            memory=fixture(mode,refs=refs,channel=channel,source=0 if missing else SOURCE)
            put(memory,CONFIG+24,0); put(memory,ACTOR+0xAC,0,1)
            for i in range(2): memory[0x800C5628+14+i]=0
            models=[Connected(memory,w,channel,extras,missing,results,phase).run() for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].r[2]))
            calls=[call for call in models[0].calls if call[0]==screen.ENTRY]
            self.assertEqual(calls,[(screen.ENTRY,ACTOR,channel)])
            reached.update(models[0].visits & set(range(entry,entry+length*4,4)))
            invocations+=len(calls); cases+=1
        self.receipt('caller',cases=cases,executions=cases*2,callee_invocations=invocations,
            complete_original_caller_words=104,reached_caller_words=len(reached),
            actual_actor_channel_forwarding_and_failure_return_propagation=True,
            resource_loader_bounded_callback_extras_zero_count_only=True,
            current_C_caller_still_placeholder_full_resource_loading_not_claimed=True)

    def test_12_committed_recovery_delta(self):
        before_source=(self.out/'matching-before-source').read_text()
        before=(self.out/'matching-before-elf').read_bytes()
        self.assertEqual(hashlib.sha256(before).hexdigest(),
            'e8a9504c87c628ce552d6f752fe26c27f4fcaaf1651612a37f998c80ba8bf690')
        source=(self.root/screen.SOURCE).read_text()
        if source==before_source:
            for name,path in self.paths.items():
                self.assertEqual((self.root/path).read_bytes(),(self.out/('matching-before-'+name)).read_bytes())
            self.receipt('matching-linked',installed=False,baseline_verified=True); return
        self.assertEqual(before_source.count(screen.QUALIFIED),1)
        self.assertEqual(source,before_source.replace(screen.QUALIFIED,self.body))
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(before)
        slot=elf_slot_offset(before,screen.ENTRY,screen.WORDS*4)
        struct.pack_into('>194I',expected,slot,*self.link('padded'))
        extent=installed.symbol_size_offset(before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',before,extent)[0],768)
        struct.pack_into('>I',expected,extent,self.meta['body_words']*4)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'):
                self.assertEqual((self.root/path).read_bytes(),(self.out/('matching-before-'+name)).read_bytes())
        self.receipt('matching-linked',installed=True,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),
            changed_slot_bytes=sum(a!=b for a,b in zip(before[slot:slot+776],actual[slot:slot+776])),
            changed_extent_bytes=sum(a!=b for a,b in zip(before[extent:extent+4],actual[extent:extent+4])),
            every_other_ELF_byte_exact=True,source_only_selected_body_change=True,
            protected_inputs_unchanged=True)


NATIVE_PREFIX='''typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef int s32;
#define NULL ((void *)0)
void bcopy(const void *, void *, int);
'''
NATIVE_HELPERS=r'''
ResourceParent15084044 D_800CC0E8[256];
u8 *D_800D19A0[256];u8 D_800D1F80[256];u16 D_800C57A0[256];
static u8 actor[0x340] __attribute__((aligned(8))), ids[8], cfg[32], banks[3][256];
static u32 calls[8][5];static int callCount,allocations,fail,recordOnly;
s32 func_15084044(u8 *,s32);
static void note(u32 a,u32 b,u32 c,u32 d,u32 e) {
    calls[callCount][0]=a;calls[callCount][1]=b;calls[callCount][2]=c;
    calls[callCount][3]=d;calls[callCount++][4]=e;
}
void *allocate_memory(s32 size,s32 a,s32 b,s32 c) {
    note(1,size,a,b,c);allocations++;
    return (fail&(1<<(allocations-1)))?NULL:banks[allocations];
}
void func_10004074(void *p) {note(3,(u32)p,0,0,0);}
void bcopy(const void *s,void *d,int n) {
    int i;u8 bytes[64];note(2,(u32)s,(u32)d,n,0);
    if(recordOnly) return;
    for(i=0;i<n;i++) bytes[i]=((const u8 *)s)[i];
    for(i=0;i<n;i++) ((u8 *)d)[i]=bytes[i];
}
static void reset(int mode,int id,int refs,int slots,int failure,int units,int parent,int channel) {
    int i,j;u8 **p=(u8 **)(actor+channel*8+0x28C);
    for(i=0;i<0x340;i++) actor[i]=0xA5;
    for(i=0;i<256;i++) {D_800D19A0[i]=banks[0];D_800D1F80[i]=0xA5;D_800C57A0[i]=0xA5A5;}
    for(i=0;i<3;i++) for(j=0;j<256;j++) banks[i][j]=(u8)(j*137+19+i);
    for(i=0;i<40;i++) ((u32 *)calls)[i]=0;
    for(i=0;i<8;i++) ids[i]=(u8)id;
    for(i=0;i<32;i++) cfg[i]=0xA5;
    cfg[16]=(u8)mode;actor[0x65]=(u8)parent;
    *(u8 **)(actor+0x144)=cfg;*(u8 **)(actor+0x2C4)=ids;
    D_800CC0E8[parent].config=cfg;
    p[0]=slots==1?banks[0]:slots==3?banks[1]:NULL;
    p[1]=slots==2?banks[0]:NULL;
    D_800D1F80[id]=(u8)refs;D_800C57A0[id]=(u16)units;
    callCount=allocations=0;fail=failure;recordOnly=units>4;
}
static int reference(int channel) {
    int id=ids[channel],mode=cfg[16]&3,index,size;u8 **p=(u8 **)(actor+channel*8+0x28C),*v;
    if(id==0) mode=2;
    if(p[0] && p[1]) return 0;
    if(!D_800D19A0[id]) return 0;
    if(mode==0) {p[1]=p[0]=D_800D19A0[id];D_800D1F80[id]+=2;return 0;}
    if(mode==3) return 0;
    for(index=0;index<(mode==1?1:2);index++) {
        if(p[index] && p[index]!=D_800D19A0[id] && !(index==1 && p[0]==p[1])) continue;
        if(D_800D1F80[id]==0) {
            p[index]=D_800D19A0[id];D_800D1F80[id]++;
            if(mode==1) {p[1]=p[0];D_800D1F80[id]++;}
        } else {
            size=D_800C57A0[id]*16;v=allocate_memory(size,1,2,2);p[index]=v;
            if(!v) {
                if(mode==1) p[1]=p[0];
                if(index==1) {if(p[0]!=D_800D19A0[id]) func_10004074(p[0]);else D_800D1F80[id]--;p[0]=NULL;}
                return 1;
            }
            bcopy(D_800D19A0[id],v,size);
        }
    }
    if(mode==1) p[1]=p[0];
    return 0;
}
'''
NATIVE_RUNNER=r'''
static u8 wantedActor[0x340],wantedBanks[3][256],wantedRefs[256];
static u32 wantedCalls[8][5];static int wantedReturn,wantedCount,cases,error;
static void check(int mode,int id,int refs,int slots,int failure,int units,int parent,int channel) {
    int i,j,result;
    reset(mode,id,refs,slots,failure,units,parent,channel);wantedReturn=reference(channel);wantedCount=callCount;
    for(i=0;i<0x340;i++) wantedActor[i]=actor[i];
    for(i=0;i<256;i++) wantedRefs[i]=D_800D1F80[i];
    for(i=0;i<3;i++) for(j=0;j<256;j++) wantedBanks[i][j]=banks[i][j];
    for(i=0;i<40;i++) ((u32 *)wantedCalls)[i]=((u32 *)calls)[i];
    reset(mode,id,refs,slots,failure,units,parent,channel);result=func_15084044(actor,channel);cases++;
    if(result!=wantedReturn || callCount!=wantedCount) error=1;
    for(i=0;i<0x340;i++) if(wantedActor[i]!=actor[i]) error=2;
    for(i=0;i<256;i++) if(wantedRefs[i]!=D_800D1F80[i] || D_800C57A0[i]!=(i==id?units:0xA5A5) || D_800D19A0[i]!=banks[0]) error=3;
    for(i=0;i<3;i++) for(j=0;j<256;j++) if(wantedBanks[i][j]!=banks[i][j]) error=4;
    for(i=0;i<40;i++) if(((u32 *)wantedCalls)[i]!=((u32 *)calls)[i]) error=5;
}
void _start(void) {
    int m,v,s,f;u32 report[3];
    if(sizeof(void *)!=4 || sizeof(ResourceParent15084044)!=812) error=6;
    for(m=0;m<4;m++) for(v=0;v<256;v++) for(s=0;s<4;s++) {
        check(m,v,1,s,0,2,v,1);
        check(m,7,v,s,0,2,0,0);
        check(m,7,v,s,2,2,255,3);
    }
    report[0]=cases;report[1]=error;report[2]=0;
    __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(report),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(error):"memory");
    __builtin_unreachable();
}
'''


if __name__=='__main__': unittest.main()
