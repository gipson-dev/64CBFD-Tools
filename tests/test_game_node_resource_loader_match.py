"""Full default loader: direct retail fit, live outputs, ordered faults and initializer."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_node_resource_loader_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_node_resource_initializer_match as initializer
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout

STACK,MASK=initializer.STACK,0xFFFFFFFF
REFS,DEPS,CACHE,LOAD,RETAIN,RELOCATE=screen.SYMBOLS.values()
HEADER,HEADER2,ARRAY,ARRAY2,OUTPUT=0x50000,0x52000,0x50028,0x54000,0x56000
COUNTS=(0,1,2,3,4,127,128,255)
MODES=(0,1,2,127,128,255)


def arguments(kind=133,mask=7):
    return (kind,OUTPUT,OUTPUT+4,OUTPUT+8,
        OUTPUT+12 if mask&1 else 0,OUTPUT+16 if mask&2 else 0,OUTPUT+20 if mask&4 else 0)


def homes(memory,args,phase=0):
    for i,arg in enumerate(args[4:]):put(memory,STACK+phase+16+i*4,arg)
    return memory


def fixture(kind=133,refs=0,count=2,phase=0,symbols=None,packed=0xA5800003):
    ref,dep,cache,*_= (symbols or screen.SYMBOLS).values();memory={}
    for start,size in ((STACK-0x500,0x600),(HEADER,0x500),(HEADER2,0x500),(ARRAY2,0x500),(OUTPUT,64)):
        memory.update({start+i:(i*17+35)&255 for i in range(size)})
    for base,value,size in ((ref+kind,refs,1),(dep+(kind<<2),0xF1238004,4),(cache+(kind<<2),HEADER,4)):
        for i in range(size):memory[(base+i)&MASK]=0xA5
        put(memory,base&MASK,value,size)
    for h in (HEADER,HEADER2):
        for offset,value in ((0,ARRAY),(4,(packed&~0x3FC)|(count<<2)),(8,0x81238004),
                (12,0xFEDCBA98),(16,0x81548004)):
            put(memory,h+offset,value)
    for a in (ARRAY,ARRAY2):
        for i in range(256):put(memory,a+i*4,0x80+i*4)
    return homes(memory,arguments(kind),phase)


def mutations(role,ordinal,plan,args,frame,symbols):
    kind,records,count,*_=args;ref,dep,cache,*_ =symbols.values()
    if role=='load' and plan==1:return (((ref+kind)&MASK,254,1),)
    if role=='retain' and ordinal==0 and plan in (2,3):
        return ((count,0 if plan==2 else 4,1),(records,ARRAY2,4),(HEADER+16,0x81550004,4))
    if role=='relocate' and ordinal==0 and plan==4:return (
        ((ref+kind)&MASK,255,1),(count,1,1),(frame+0x5C,OUTPUT+24,4),
        (frame+0x60,OUTPUT+28,4),(frame+0x64,0,4))
    if role=='relocate' and ordinal==0 and plan==5:return (
        (HEADER+8,0x81668004,4),(HEADER+12,0x80000000,4),(HEADER+16,0,4),
        ((cache+(kind<<2))&MASK,HEADER2,4))
    return ()


def reference(memory,args=None,phase=0,result=HEADER,plan=0,symbols=None,
        saved=None,return_address=0xDEAD0000):
    args=args or arguments();symbols=symbols or screen.SYMBOLS
    ref,dep,cache,load,retain,relocate=symbols.values();state=memory.copy();events=[];calls=[]
    frame=STACK+phase-0x50;kind,records,count,source,*_=args
    def get(address,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(target,packet,role,ordinal=0):
        calls.append((target,*packet));events.append(('CALL',target,packet))
        if role=='retain':store(packet[4],0x60000+ordinal*4)
        for address,value,size in mutations(role,ordinal,plan,args,frame,symbols):store(address,value,size)
    saved=saved or {i:0x5A000000+i for i in range(16,23)}
    for reg,offset in ((22,0x38),(21,0x34),(18,0x28)) :store(frame+offset,saved[reg])
    store(frame+0x3C,return_address)
    for reg,offset in ((20,0x30),(19,0x2C),(17,0x24),(16,0x20)):store(frame+offset,saved[reg])
    store(frame+0x5C,source);reference_address=(ref+kind)&MASK
    cached=get(reference_address,1)
    def finish(status):
        get(frame+0x3C)
        for offset in (0x20,0x24,0x28,0x2C,0x30,0x34,0x38):get(frame+offset)
        return state,events,calls,status
    if cached:
        header=get(cache+(kind<<2));store(records,get(header));store(count,get(header+4)>>2,1)
    else:
        store(frame+0x10,9);store(frame+0x14,kind);store(frame+0x44,reference_address)
        call(load,(0,0,0,2,9,kind&MASK),'load')
        header=result
        if not header:return finish(1)
        store(records,get(header));word=get(header+4);store(count,word>>2,1)
        if (word>>2)&255:
            base=get(records);i=0
            while True:
                element=(base+i*4)&MASK;store(element,get(element)+header)
                record=get(get(records)+i*4);store(frame+0x10,(dep+(kind<<2))&MASK)
                call(retain,(record,0,1,0x3E,(dep+(kind<<2))&MASK),'retain',i)
                record=get(get(records)+i*4);call(relocate,(record,header),'relocate',i)
                live_count=get(count,1);i+=1
                assert i<=256,'unbounded live-count fixture'
                if i>=live_count:break
                base=get(records)
        store(cache+(kind<<2),header);reference_address=get(frame+0x44)
    value=get(reference_address,1);transform=get(frame+0x60);source=get(frame+0x5C)
    store(reference_address,value+1,1);store(source,header+0x18)
    if transform:store(transform,get(header+16))
    extra=get(frame+0x64);extra_count=get(frame+0x68)
    if extra:
        store(extra,get(header+8))
        if extra_count:store(extra_count,get(header+12)>>4)
    return finish(0)


class LoaderOracle(reset.ResetOracle):
    def __init__(self,words,memory,args=None,phase=0,result=HEADER,plan=0,symbols=None,
            entry=screen.ENTRY,connected=None):
        args=args or arguments()
        guest.AttachmentOracle.__init__(self,words,memory,arguments=args,phase=phase,entry=entry,connected=connected)
        self.symbols=symbols or screen.SYMBOLS;_,_,_,load,retain,relocate=self.symbols.values()
        self.roles={load:'load',retain:'retain',relocate:'relocate'};self.counts={load:6,retain:5,relocate:2}
        self.result,self.plan,self.args,self.frame=result,plan,args,STACK+phase-0x50;self.ordinals={}
    def hook(self,target):
        role=self.roles[target];ordinal=self.ordinals.get(role,0);self.ordinals[role]=ordinal+1
        if role=='retain':self.put(self.calls[-1][5],0x60000+ordinal*4,4)
        for address,value,size in mutations(role,ordinal,self.plan,self.args,self.frame,self.symbols):self.put(address,value,size)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.result if role=='load' else 0xBEEF0000+ordinal


class InitializerOracle(initializer.ResourceOracle):
    def __init__(self,*args,loader_result=HEADER,**kwargs):
        super().__init__(*args,**kwargs);self.loader_result=loader_result;self.loader_args=None
        self.loader_snapshots=[];self.loader_calls=0;self.counts.update({LOAD:6,RETAIN:5,RELOCATE:2})
    def record_call(self,target):
        if target==screen.ENTRY:
            self.loader_args=tuple(self.arguments(7));self.loader_frame=self.r[29]-0x50
            self.loader_snapshots.append((self.memory.copy(),self.r[29],self.loader_args,
                len(self.calls),{i:self.r[i] for i in range(16,23)},self.r[31]))
        super().record_call(target)
    def hook(self,target):
        if target in (LOAD,RETAIN,RELOCATE):
            if target==RETAIN:self.put(self.calls[-1][5],0x60000+self.loader_calls*4,4);self.loader_calls+=1
            for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)]
            self.r[2]=self.loader_result if target==LOAD else 0xBEEF1234
        else:super().hook(target)


class GameNodeResourceLoaderMatchTests(unittest.TestCase):
    maxDiff=1800
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-node-resource-loader-test'
        cls.out.mkdir(exist_ok=True);cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>114I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes()
        body=(cls.root/'conker/asm/5D2C0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_5D2C0'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original==cls.raw
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in (symbols or screen.SYMBOLS).items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>114I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,args=None,forms=None,**settings):
        args=args or arguments();memory=homes(memory.copy(),args,settings.get('phase',0))
        expected=reference(memory,args,**{k:v for k,v in settings.items() if k!='entry'});models=[]
        for code in forms or (self.original,self.raw,self.fitted):
            model=LoaderOracle(code,memory,args=args,**settings).run();models.append(model)
            self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected)
        return models
    def test_01_direct_complete_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes'],
            self.meta['diagnostics']),(114,80,0,0,''))
        self.assertEqual(self.raw,self.original);self.assertEqual(len(self.meta['relocations']),11)
        self.receipt('shape',words=114,frame=80,direct=True,guards=0,relocation_sites=11,pools=0,diagnostics='')
    def test_02_all_kind_reference_count_bytes_optional_outputs_and_coverage(self):
        cases=0;coverage=set()
        for value,axis,phase in itertools.product(range(256),('kind','refs','count'),(0,8)):
            inputs={axis:value,'phase':phase};models=self.compare(fixture(**inputs),arguments(value if axis=='kind' else 133),phase=phase)
            cases+=1;coverage.update(models[0].visits)
        for refs,count,mask,phase,result in itertools.product(MODES,COUNTS,range(8),(0,8),(0,HEADER)):
            models=self.compare(fixture(refs=refs,count=count,phase=phase),arguments(mask=mask),phase=phase,result=result)
            cases+=1;coverage.update(models[0].visits)
        self.assertEqual(set(range(screen.ENTRY,screen.ENTRY+456,4))-coverage,set())
        self.receipt('guest',cases=cases,executions=cases*3,all_kind_reference_count_bytes=True,
            nullable_output_masks=True,cached_miss_allocation_failure_reference_rollover=True,
            all_114_words_reached=True,independent_complete_ordered_reference=True,caller_GP_FPR_clobbered=True)
    def test_03_live_mutations_aliases_required_outputs_and_fired_faults(self):
        cases=prefixes=0
        for plan,refs,count,phase in itertools.product(range(6),(0,1),(0,1,3),(0,8)):
            memory=fixture(refs=refs,count=count,phase=phase);models=self.compare(memory,plan=plan,phase=phase);cases+=1
            if phase==0 and refs==0 and count==3:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for code in (self.original,self.raw,self.fitted):
                        model=LoaderOracle(code,homes(memory.copy(),arguments()),plan=plan);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    for model in failed[1:]:self.assertEqual((model.memory,model.events,model.calls,model.f),
                        (failed[0].memory,failed[0].events,failed[0].calls,failed[0].f))
                    prefixes+=1
        for refs in (0,1):
            for which,address in ((1,HEADER),(2,HEADER+4),(3,HEADER+16),(3,OUTPUT),
                    (4,OUTPUT),(5,OUTPUT+8),(6,OUTPUT+12),(3,STACK-0xC0)):
                args=list(arguments());args[which]=address;self.compare(fixture(refs=refs,count=0),tuple(args));cases+=1
        for refs,result in ((0,0),(0,HEADER),(1,HEADER)):
            for which in (1,2,3):
                args=list(arguments());args[which]=0;memory=homes(fixture(refs=refs),args)
                if not refs and not result:self.compare(memory,tuple(args),result=0)
                else:
                    for code in (self.original,self.raw,self.fitted):
                        with self.assertRaises(AssertionError):LoaderOracle(code,memory,args=tuple(args),result=result).run()
                cases+=1
        self.receipt('aliases',cases=cases,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            live_records_count_header_fields_reference_cache_and_private_output_homes=True,
            required_NULL_outputs_error_gate_and_public_private_aliases=True,guest_faults_not_portable_C=True)
    def test_04_independent_globals_callbacks_signed_carries_and_full_word_kind(self):
        cases=0
        for j in range(3):
            symbols=dict(screen.SYMBOLS)
            for i,name in enumerate(symbols):symbols[name]=(0x80107FFC+j*0x10004+i*0x8008 if i<3
                else 0x15410004+j*0x10004+i*0x100)&MASK
            entry=0x15217FFC+j*0x10004;forms=tuple(self.link(n,entry,symbols) for n in ('original','selected','fitted'))
            for kind,refs,count,mask in itertools.product((0,255,0x1E3),MODES,(0,3),(0,7)):
                self.compare(fixture(kind=kind,refs=refs,count=count,symbols=symbols),arguments(kind,mask),
                    forms=forms,entry=entry,symbols=symbols);cases+=1
        for kind in (0x10000,0x80000000,MASK):
            self.compare(fixture(kind=kind),arguments(kind));cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,three_independent_globals_callbacks=True,
            HI_LO_signed_carries_and_repeated_cache_HI_LO_sites=True,full_word_kind_guest_wrapping_only=True)
    def test_05_copied_owner_real_padder_pools_and_unchanged_neighbors(self):
        objects=[];padded=[];diagnostics=[];before=(self.out/'before-source').read_text()
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,detail=compile_owner(self.root,self.out,source,name);objects.append(obj);diagnostics.append(detail)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_5D2C0',str(asm),'--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        a,b=padded;start=b[1][screen.FUNCTION]['value'];expected=bytearray(a[0])
        # Owner text carries relocatable JAL/HI/LO words until the final link.
        raw,functions,_=parse_object(objects[1]);slot=functions[screen.FUNCTION]['value']
        expected[start:start+456]=raw[slot:slot+456];self.assertEqual(bytes(expected),b[0])
        for name in a[1]:
            if name!=screen.FUNCTION:self.assertEqual(a[1][name],b[1][name])
        self.assertEqual(a[2],{k:v for k,v in b[2].items() if not start<=k<start+456})
        self.receipt('owner',untouched_neighbors=len(a[1])-1,neighbor_bytes_extents_relocations_exact=True,
            diagnostics_equal=True,diagnostic_bytes=0,pools_exact=True,actual_padder=True,seven_argument_caller_unchanged=True)
    def test_06_effective_fresh_IDO_negative_controls(self):
        controls=(('narrow-kind',screen.SELECTED.replace('s32 kind','u8 kind'),dict(kind=0x10000),arguments(0x10000),{}),
            ('wrong-cache-gate',screen.SELECTED.replace('D_800DF7D0[kind] == 0','D_800DF7D0[kind] == 1'),{},arguments(),{}),
            ('wrong-kind-tag',screen.SELECTED.replace('0, 2, 9, kind','0, 2, 8, kind'),{},arguments(),{}),
            ('wrong-count-shift',screen.SELECTED.replace('header + 4) >> 2','header + 4) >> 3'),dict(count=2),arguments(),{}),
            ('wrong-rebase',screen.SELECTED.replace('+= (u32)header','+= (u32)header + 4'),{},arguments(),{}),
            ('wrong-retain-mode',screen.SELECTED.replace(', 0, 1, 0x3E',', 0, 0, 0x3E'),{},arguments(),{}),
            ('missing-ref',screen.SELECTED.replace('    D_800DF7D0[kind]++;\n',''),{},arguments(),{}),
            ('wrong-source',screen.SELECTED.replace('header + 0x18','header + 0x1C'),{},arguments(),{}),
            ('wrong-extra-shift',screen.SELECTED.replace('header + 0xC) >> 4','header + 0xC) >> 3'),{},arguments(),{}),
            ('cached-count',screen.SELECTED.replace('    s32 index;','    s32 index;\n    s32 limit;').replace(
                '        if (*count > 0) {','        limit = *count;\n        if (limit > 0) {').replace(
                'index < *count','index < limit'),dict(count=3),arguments(),dict(plan=2)))
        for name,body,inputs,args,settings in controls:
            _,words=screen.compile_candidate(self.root,self.out,name,body);memory=fixture(**inputs)
            if name=='narrow-kind':memory={**fixture(kind=0),**memory}
            homes(memory,args)
            expected=LoaderOracle(self.original,memory,args=args,**settings).run();actual=LoaderOracle(words,memory,args=args,**settings).run()
            self.assertNotEqual((initializer.public(actual.memory),actual.calls),
                (initializer.public(expected.memory),expected.calls),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))
    def test_07_native32_optimized_unoptimized_complete_cache_output_contract(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        for name,body in (('native-wrong-rebase',screen.SELECTED.replace('+= (u32)header','+= (u32)header + 4')),
                ('native-missing-ref',screen.SELECTED.replace('    D_800DF7D0[kind]++;\n',''))):
            result,_=self.run_native(name,NATIVE_PREFIX+body+NATIVE_RUNNER);self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=6912,executions=13824,profiles=['O2','O0'],
            effective_native_negative_controls=2,complete_header_arrays_outputs_cache_reference_dependency_and_calls=True,
            live_callback_mutations=True,bounded_resource_record_callbacks=True)
    def test_08_actual_initializer_consumes_real_loader_outputs(self):
        entry=initializer.screen.ENTRY;words=list(struct.unpack_from('>96I',self.before,elf_slot_offset(self.before,entry,384)))
        self.assertEqual(words,list(struct.unpack_from('>96I',self.rom,initializer.screen.ROM)))
        cases=prefixes=0
        for refs,flags,actor_flags,transform,result,first,second,phase in itertools.product(
                (0,1,255),(0,16),(0,8,12),(0,0x81548004),(0,HEADER),(0,initializer.DEST1),(0,initializer.DEST2),(0,8)):
            memory=initializer.fixture(actor_flags=actor_flags,flags=flags,phase=phase)
            loader_memory=fixture(refs=refs,count=2,phase=phase)
            memory.update({a:v for a,v in loader_memory.items() if not STACK-0x500<=a<STACK+0x100})
            put(memory,HEADER+16,transform)
            connected={screen.ENTRY+i*4:w for i,w in enumerate(self.raw)}
            model=InitializerOracle(words,memory,phase=phase,connected=connected,loader_result=result,
                first=first,second=second,source=HEADER+0x18,length=16).run()
            expected_header=HEADER if refs else result
            copied=not flags&16 and actor_flags&12==8 and transform!=0
            status=not expected_header or copied and (not first or not second)
            self.assertEqual(model.r[2],int(status));self.assertEqual(len(model.loader_snapshots),1)
            if expected_header:
                self.assertEqual(read(model.memory,initializer.NODE+0x24),ARRAY)
                self.assertEqual(read(model.memory,REFS+133,1),(refs+1)&255)
                self.assertEqual(read(model.memory,initializer.NODE+0x14,1),2)
                self.assertEqual(read(model.memory,initializer.NODE+0x30),transform)
                if not status:
                    self.assertEqual(read(model.memory,initializer.NODE+9,1),1)
                    self.assertEqual(read(model.memory,initializer.NODE+0x28),first if copied else HEADER+0x18)
                    self.assertEqual(read(model.memory,initializer.NODE+0x2C),second if copied else HEADER+0x18)
                    if copied:
                        self.assertEqual(bytes(model.memory[first+i] for i in range(16)),bytes(model.memory[HEADER+0x18+i] for i in range(16)))
                        self.assertEqual(bytes(model.memory[second+i] for i in range(16)),bytes(model.memory[HEADER+0x18+i] for i in range(16)))
            snapshot,stack,args,_,saved,ra=model.loader_snapshots[0]
            expected=reference(snapshot,args,phase=stack-STACK,result=result,saved=saved,return_address=ra)
            loader_end=next(i for i,event in enumerate(model.events) if event==('R',stack-0x50+0x38,4,saved[22]))
            loader_start=next(i for i,event in enumerate(model.events) if event==('W',stack-0x50+0x38,4,saved[22]))
            self.assertEqual(model.events[loader_start:loader_end+1],expected[1])
            if phase==0 and refs==0 and flags==0 and actor_flags==8 and transform and first and second:
                for ordinal in range(model.accesses):
                    fault=InitializerOracle(words,memory,connected=connected,loader_result=result,
                        first=first,second=second,source=HEADER+0x18,length=16);fault.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:fault.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(fault.accesses,ordinal);prefixes+=1
            cases+=1
        self.receipt('initializer',cases=cases,actual_96_word_initializer_full_114_word_loader=True,
            real_source_output_and_buffers_consumed=True,cached_reference_rollover_and_loader_allocation_buffer_failures=True,
            independent_ordered_loader_reference_inside_actual_caller=True,fired_faults=prefixes,
            deeper_resource_load_retain_relocate_allocator_copy_callbacks_bounded=True)
    def test_10_repeated_cache_hits_rollover_and_fresh_header(self):
        memory=fixture(count=3);args=arguments();cases=0
        for expected_ref in (1,2,3):
            models=self.compare(memory,args);memory=models[0].memory;cases+=1
            self.assertEqual(read(memory,REFS+133,1),expected_ref)
            self.assertEqual(sum(call[0]==LOAD for call in models[0].calls),int(expected_ref==1))
            self.assertEqual(read(memory,ARRAY),HEADER+0x80)
        put(memory,REFS+133,255,1);models=self.compare(memory,args);memory=models[0].memory;cases+=1
        self.assertEqual(read(memory,REFS+133,1),0);self.assertFalse(models[0].calls)
        put(memory,HEADER2,ARRAY2);put(memory,HEADER2+4,3<<2)
        models=self.compare(memory,args,result=HEADER2);cases+=1
        self.assertEqual(read(models[0].memory,REFS+133,1),1)
        self.assertEqual(read(models[0].memory,CACHE+133*4),HEADER2)
        self.assertEqual(read(models[0].memory,ARRAY2),HEADER2+0x80)
        self.assertEqual(read(models[0].memory,OUTPUT+8),HEADER2+0x18)
        self.receipt('repeated',cases=cases,executions=cases*3,cached_records_not_relocated_twice=True,
            reference_255_rolls_to_zero_then_loads_fresh_header=True)
    def test_09_whole_ELF_single_slot_extent_protected_inputs_and_no_guards(self):
        source=(self.root/screen.SOURCE).read_text();before=self.before
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>114I',expected,elf_slot_offset(before,screen.ENTRY,456),*self.raw)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbols=old[4];changed=0
        for offset in range(symbols[4],symbols[4]+symbols[5],symbols[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:]);self.assertEqual((a[2],b[2]),(12,456))
                struct.pack_into('>I',expected,offset+8,b[2]);changed+=1
        self.assertEqual(changed,1);self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        for name in ('guards','progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,
            all_other_ELF_bytes_exact=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),guard_manifest_exact=True,appended_rows=0,
            data_audit=audit,conversion_rows_unchanged=True)


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
static u8 D_800DF7D0[484];static s32 *D_800DF9B8[484];static u8 *D_800E0148[484];
static u32 header[320],alternate[320],outputs[8];
struct Call {u32 target,args[6];};static struct Call calls[520],expectedCalls[520];
static u32 expectedHeader[320],expectedAlternate[320],expectedOutputs[8],expectedDependency,expectedCache;
static u8 expectedRef;static s32 callCount,expectedCount,currentKind,plan,ordinal;
static u8 *currentHeader;static u8 **recordOutput;static u8 *countOutput;
static void record(s32 target,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){
    struct Call *call=&calls[callCount++];call->target=(u32)target;
    call->args[0]=a;call->args[1]=b;call->args[2]=c;call->args[3]=d;call->args[4]=e;call->args[5]=f;
    if(target==1&&plan==1)D_800DF7D0[currentKind]=254;
    if(target==2){
        *(s32 *)e=0x60000+ordinal*4;
        if(ordinal==0&&(plan==2||plan==3)){
            *countOutput=plan==2?0:4;*recordOutput=(u8 *)alternate;header[4]=0x81550004u;
        }
    }
    if(target==3){
        if(ordinal==0&&plan==5){header[2]=0x81668004u;header[3]=0x80000000u;header[4]=0;
            D_800E0148[currentKind]=(u8 *)alternate;}
        ordinal++;
    }
}
static void *func_1502B6BC(s32 *a,s32 b,s32 *c,s32 d,...){
    __builtin_va_list args;s32 tag,kind;__builtin_va_start(args,d);
    tag=__builtin_va_arg(args,s32);kind=__builtin_va_arg(args,s32);__builtin_va_end(args);
    record(1,(u32)a,(u32)b,(u32)c,(u32)d,(u32)tag,(u32)kind);return currentHeader;
}
static s32 func_1510CE60(void *a,s32 b,s32 c,s32 d,s32 *e){record(2,(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,0);return -1;}
static void func_15168E54(void *a,void *b){record(3,(u32)a,(u32)b,0,0,0,0);}
'''
NATIVE_RUNNER=r'''
static s32 independent(s32 kind,u8 **out,u8 *count,u8 **source,u8 **matrix,u8 **extra,u32 *amount){
    u32 *h;s32 index=0;
    if(D_800DF7D0[kind])h=(u32 *)D_800E0148[kind];
    else{
        h=func_1502B6BC(0,0,0,2,9,kind);if(!h)return 1;
        *out=(u8 *)h[0];*count=(u8)(h[1]>>2);
        while(index<*count){
            u32 *element=(u32 *)(*out+index*4);*element+=(u32)h;
            func_1510CE60((void *)*element,0,1,62,(s32 *)&D_800DF9B8[kind]);
            func_15168E54((void *)((u32 *)*out)[index],h);index++;
        }
        D_800E0148[kind]=(u8 *)h;
        goto output;
    }
    *out=(u8 *)h[0];*count=(u8)(h[1]>>2);
output:
    D_800DF7D0[kind]=(u8)(D_800DF7D0[kind]+1);*source=(u8 *)h+24;
    if(matrix)*matrix=(u8 *)h[4];
    if(extra){*extra=(u8 *)h[2];if(amount)*amount=h[3]>>4;}
    return 0;
}
static void setup(s32 kind,s32 refs,s32 count,s32 mask,s32 scenario,s32 missing){
    s32 i;currentKind=kind;plan=scenario;callCount=ordinal=0;
    D_800DF7D0[kind]=(u8)refs;D_800DF9B8[kind]=(s32 *)0xF1238004u;D_800E0148[kind]=(u8 *)header;
    for(i=0;i<320;i++){header[i]=0x80u+(u32)i*4;alternate[i]=0x180u+(u32)i*4;}
    for(i=0;i<8;i++)outputs[i]=0xA5A5A5A5u;
    header[0]=(u32)&header[10];header[1]=0xA5800003u|((u32)count<<2);
    header[2]=0x81238004u;header[3]=0xFEDCBA98u;header[4]=0x81548004u;
    currentHeader=missing?0:(u8 *)header;recordOutput=(u8 **)&outputs[0];countOutput=(u8 *)&outputs[1];
    (void)mask;
}
static s32 qualify(s32 kind,s32 refs,s32 count,s32 mask,s32 scenario,s32 missing){
    s32 i,j,a,b;setup(kind,refs,count,mask,scenario,missing);
    a=independent(kind,(u8 **)&outputs[0],(u8 *)&outputs[1],(u8 **)&outputs[2],
        mask&1?(u8 **)&outputs[3]:0,mask&2?(u8 **)&outputs[4]:0,mask&4?&outputs[5]:0);
    expectedRef=D_800DF7D0[kind];expectedDependency=(u32)D_800DF9B8[kind];expectedCache=(u32)D_800E0148[kind];
    expectedCount=callCount;for(i=0;i<callCount;i++)expectedCalls[i]=calls[i];
    for(i=0;i<320;i++){expectedHeader[i]=header[i];expectedAlternate[i]=alternate[i];}
    for(i=0;i<8;i++)expectedOutputs[i]=outputs[i];
    setup(kind,refs,count,mask,scenario,missing);
    b=func_1502FE10(kind,(u8 **)&outputs[0],(u8 *)&outputs[1],(u8 **)&outputs[2],
        mask&1?(u8 **)&outputs[3]:0,mask&2?(u8 **)&outputs[4]:0,mask&4?&outputs[5]:0);
    if(a!=b||expectedRef!=D_800DF7D0[kind]||expectedDependency!=(u32)D_800DF9B8[kind]||
        expectedCache!=(u32)D_800E0148[kind]||expectedCount!=callCount)return 1;
    for(i=0;i<callCount;i++){
        if(expectedCalls[i].target!=calls[i].target)return 2;
        for(j=0;j<6;j++)if(expectedCalls[i].args[j]!=calls[i].args[j])return 3;
    }
    for(i=0;i<320;i++)if(expectedHeader[i]!=header[i]||expectedAlternate[i]!=alternate[i])return 4;
    for(i=0;i<8;i++)if(expectedOutputs[i]!=outputs[i])return 5;
    return 0;
}
int run(void){
    s32 axis,value,mask,missing,scenario,r,refs,count,kind;
    for(axis=0;axis<3;axis++)for(value=0;value<256;value++)for(mask=0;mask<8;mask++){
        kind=axis==0?value:133;refs=axis==1?value:0;count=axis==2?value:3;
        r=qualify(kind,refs,count,mask,0,0);if(r)return r;
    }
    for(refs=0;refs<2;refs++)for(count=0;count<4;count++)for(mask=0;mask<8;mask++)
        for(missing=0;missing<2;missing++)for(scenario=0;scenario<6;scenario++){
            r=qualify(133,refs,count,mask,scenario,missing);if(r)return r;
        }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
