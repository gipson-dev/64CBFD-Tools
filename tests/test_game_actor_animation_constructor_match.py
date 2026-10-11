"""Complete constructor, live descriptor loop, stacked ABI and linked-only audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_actor_animation_constructor_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_animation_request_match as request
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout
from tools.patch_generated_slice_ld import load_game_data_layout

STACK,ACTOR,MASK=request.STACK,request.ACTOR,0xFFFFFFFF
TABLE,TYPE0,OTHER=screen.recovery.SYMBOLS.values()
RECORDS,ALTERNATE=0x2B000,0x2D000
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,0x7F800000,0xFF800000,
    0x7FC12345,0x7F812345,1,0x807FFFFF,0x7F7FFFFF,0xFFFFFFFF)
RESULTS=(0x31000,0,0xF1238004,0x80000000)
TYPED_STUB=(0xAFA40000,0xAFA50004,0xAFA60008,0xAFA7000C,0x00001025,0x03E00008,0)


def descriptor_address(animation=5,table=TABLE):return (table+((animation-1)&MASK)*8)&MASK


def fixture(animation=5,count=3,kind=0,pattern=0,table=TABLE,records=RECORDS,phase=0):
    memory={STACK+i:0xA5 for i in range(-0x300,0x100)}
    for start,length in ((ACTOR,812),(RECORDS,4096),(ALTERNATE,4096)):
        memory.update({start+i:(i*17+35)&255 for i in range(length)})
    descriptor=descriptor_address(animation,table)
    memory.update({descriptor+i:0xA5 for i in range(8)})
    if records not in (RECORDS,ALTERNATE):memory.update({records+i:0xA5 for i in range(16)})
    for i in range(256 if records in (RECORDS,ALTERNATE) else 1):
        for j in range(16):memory[records+i*16+j]=(j*37+pattern*67+i*19)&255
        memory[records+i*16+3]=(kind if i==0 else (0,2,1,255)[i%4])&255
    put(memory,descriptor,records,4);put(memory,descriptor+4,count,1)
    return memory


def changes(plan,ordinal,descriptor,records,stack):
    if ordinal:return ()
    if plan==1:return ((descriptor+4,0,1),)
    if plan==2:return ((descriptor+4,3,1),)
    if plan==3:return ((descriptor,ALTERNATE,4),(records+16+3,2,1),(records+16+6,255,1))
    if plan==4:return ((stack+8,0x7FC12345,4),(stack+12,0xFFFFFFFF,4),(ACTOR+0x6F,129,1))
    return ()


def reference(memory,actor=ACTOR,animation=5,scale=0x3F800000,mode=0,phase=0,table=TABLE,
        type0=TYPE0,other=OTHER,plan=0,results=RESULTS,stack=None,return_address=0xDEAD0000,stubs=False):
    state,events,calls=memory.copy(),[],[];stack=STACK+phase if stack is None else stack;frame=stack-0x68
    def get(where,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=4):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(target,registers,count,ordinal):
        args=tuple(registers)+tuple(read(state,frame+i*4,4) for i in range(4,count))
        events.append(('CALL',target,args));calls.append((target,*args))
        if stubs:
            if target==type0:
                for i,value in enumerate(registers):store(frame+i*4,value)
            return 0
        for where,value,size in changes(plan,ordinal,descriptor,records,stack):store(where,value,size)
        return results[ordinal%len(results)]&MASK
    store(frame+0x40,0x3F8000153F800014,8)
    for offset,register in ((0x60,22),(0x58,20),(0x50,18)):store(frame+offset,0x5A000000+register)
    store(frame+0x64,return_address)
    for offset,register in ((0x5C,21),(0x54,19),(0x4C,17),(0x48,16)):store(frame+offset,0x5A000000+register)
    descriptor=descriptor_address(animation,table);count=get(descriptor+4,1);records=get(descriptor,4)
    i=0;record=records;result=0
    if count:
        kind=get(record+3,1)
        while True:
            if kind==0:
                third=get(record+2,1);first=get(record+1,1);second=get(record,1);store(frame+0x10,third)
                value=get(record+4,1);store(frame+0x14,value)
                value=get(record+5,1);store(frame+0x18,value)
                value=get(record+6,1);store(frame+0x20,scale);store(frame+0x1C,value)
                result=call(type0,(actor,first,second,0),9,i)
            else:
                selector=get(record+6,1) if kind==2 else MASK
                value=get(record+4,1);first=get(record,1);second=get(record+1,1);third=get(record+7,1)
                store(frame+0x10,value);value=get(record+5,1)
                store(frame+0x1C,animation);store(frame+0x18,mode);store(frame+0x14,value)
                value=get(record+2,1);store(frame+0x28,selector);store(frame+0x24,record+8);store(frame+0x20,value)
                value=get(record+14,1);store(frame+0x2C,value);value=get(record+15,1);store(frame+0x30,value)
                result=call(other,(actor,first,second,third),13,i)
            count=get(descriptor+4,1);i+=1;record=(record+16)&MASK
            if i>=count:break
            assert i<256,'unbounded reference fixture';kind=get(record+3,1)
    get(frame+0x64,4);get(frame+0x40,8)
    for offset in (0x48,0x4C,0x50,0x54,0x58,0x5C,0x60):get(frame+offset,4)
    return state,events,calls,result


class ConstructorOracle(reset.ResetOracle):
    def __init__(self,words,memory,actor=ACTOR,animation=5,scale=0x3F800000,mode=0,phase=0,
            table=TABLE,type0=TYPE0,other=OTHER,plan=0,results=RESULTS,entry=screen.ENTRY,
            connected=None,arguments=None):
        guest.AttachmentOracle.__init__(self,words,memory,
            arguments=(actor,animation&MASK,scale,mode&MASK) if arguments is None else arguments,
            phase=phase,entry=entry,connected=connected)
        self.counts={type0:9,other:13,screen.ENTRY:4,request.screen.ENTRY:3,
            request.LIST:2,request.CLASSIFIER:1,request.lookup.screen.ENTRY:2}
        self.deep=(type0,other);self.table,self.plan,self.results=table,plan,results
        self.descriptor=descriptor_address(animation,table);self.records=read(memory,self.descriptor,4)
        self.ordinal=0
    def hook(self,target):
        assert target in self.deep,('unbounded callback',target)
        for where,value,size in changes(self.plan,self.ordinal,self.descriptor,self.records,self.r[29]+0x68):
            self.put(where,value,size)
        result=self.results[self.ordinal%len(self.results)]&MASK;self.ordinal+=1
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result


def request_reference(memory,actor=ACTOR,index=5,amount=1000,phase=0,stack=None,
        return_address=0xDEAD0000,**unused):
    state,events,calls=memory.copy(),[],[];frame=(STACK+phase if stack is None else stack)-0x18
    def get(where,size):
        assert all(where+i in state for i in range(size));v=read(state,where,size);events.append(('R',where,size,v));return v
    for offset,value in ((0x14,return_address),(0x18,actor),(0x1C,index),(0x20,amount)):
        put(state,frame+offset,value,4);events.append(('W',frame+offset,4,value&MASK))
    index=get(frame+0x1C,4);actor=get(frame+0x18,4)
    if index:
        events.append(('CALL',request.LIST,(actor,0)));calls.append((request.LIST,actor,0))
        state,inner,inner_calls,listing=request.list_reference(state,actor,frame,request.screen.ENTRY+0x2C)
        events.extend(inner);calls.extend(inner_calls);amount=get(frame+0x20,4)
        if listing:
            factor=get(request.FACTOR,4);index=get(frame+0x1C,4);actor=get(frame+0x18,4)
            animation=get((listing+index-1)&MASK,1)
            scaled=request.bits(request.floating(request.bits(request.signed(amount)))*request.floating(factor))
            args=(actor,animation,scaled,0);events.append(('CALL',screen.ENTRY,args));calls.append((screen.ENTRY,*args))
            state,inner,inner_calls,_=reference(state,actor=actor,animation=animation,scale=scaled,stack=frame,
                return_address=request.screen.ENTRY+0x68)
            events.extend(inner);calls.extend(inner_calls)
    get(frame+0x14,4);return state,events,calls


class GameActorAnimationConstructorMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-actor-animation-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream);cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rows=screen.guard_rows(cls.out/'selected.o');cls.guards=cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.old_rows+cls.rows);cls.write_rows(cls.out/'isolated.csv',cls.rows)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>89I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_AEB40'))
        cls.fitted=cls.link('fitted',screen.ENTRY,screen.recovery.SYMBOLS);assert cls.fitted==cls.original
        before=(cls.out/'before-elf').read_bytes();cls.helpers={}
        assert audit_layout(cls.out/'before-elf',cls.root/'conker')['exact']
        for address,words,rom in ((request.screen.ENTRY,30,request.screen.ROM),(request.LIST,19,0xABEA8),
                (request.CLASSIFIER,11,0xB1E50),(request.lookup.screen.ENTRY,24,request.lookup.screen.ROM),
                (request.CALLER,60,0xABA78)):
            code=list(struct.unpack_from('>%dI'%words,before,elf_slot_offset(before,address,words*4)))
            assert code==list(struct.unpack_from('>%dI'%words,cls.rom,rom));cls.helpers[address]=code
        cls.old_other=list(struct.unpack_from('>3I',before,elf_slot_offset(before,OTHER,12)))
        assert cls.old_other==[0x00001025,0x03E00008,0]
        rom_start,vram,rom_end,_=load_game_data_layout(cls.root/'conker');cls.assets={}
        for animation in (5,6,7,10,11,0x17,0x23,0x44):
            address=descriptor_address(animation);offset=elf_slot_offset(before,address,8)
            descriptor=before[offset:offset+8];records=struct.unpack_from('>I',descriptor)[0];count=descriptor[4]
            assert descriptor==cls.rom[rom_start+address-vram:rom_start+address-vram+8]
            offset=elf_slot_offset(before,records,count*16);data=before[offset:offset+count*16]
            assert vram<=records and rom_start+records-vram+len(data)<=rom_end
            assert data==cls.rom[rom_start+records-vram:rom_start+records-vram+len(data)]
            cls.assets[animation]=(descriptor,records,data)

    @classmethod
    def link(cls,name,entry,symbols):
        script=cls.out/('link-%s-%X-%X.ld'%(name,entry,symbols['D_80086CC4']));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>89I',sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings)
        models=[ConstructorOracle(words,memory,**settings).run() for words in
            (forms or (self.original,self.raw,self.fitted))]
        for model in models:self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected)
        return models

    def test_01_complete_shape_closed_recipe_and_stale_rejection(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(89,104,0,17,''))
        self.assertEqual(self.meta['relocations'],screen.RELOCATIONS)
        self.assertEqual({int(r['offset'],0)//4 for r in self.rows},
            {21,24,27,34,37,38,39,40,43,47,51,55,56,59,60,62,63})
        self.assertTrue(all(r['omit']=='false' and not r['insert_after'] and
            r['expected_relocations']==r['replacement_relocations']=='-' for r in self.rows))
        for index in range(89):
            stale=list(screen.RAW);stale[index]^=1
            with self.assertRaises(ValueError):screen.recipe(stale)
        publisher=self.out/'publish-test.csv';before=(self.out/'before-guards').read_bytes();publisher.write_bytes(before)
        screen.append_guards(publisher,before,self.out/'selected.o');published=publisher.read_bytes()
        self.assertTrue(published.startswith(before))
        with publisher.open(newline='') as stream:self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        with self.assertRaises(ValueError):screen.append_guards(publisher,before,self.out/'selected.o')
        with self.assertRaises(ValueError):screen.append_guards(publisher,published,self.out/'selected.o')
        self.receipt('shape',words=89,frame=104,guards=17,insertions=0,omissions=0,pool_bytes=0,
            complete_semantic_O2_g3=True,closed_register_and_independent_expression_only=True,stale_word_rejects=89)

    def test_02_all_record_types_widths_live_count_pointer_and_float_bits(self):
        cases=0;coverage=set()
        for kind,pattern,mode,phase,plan in itertools.product(range(256),range(2),
                (0,0xFFFFFFFF,0xABCDEF11),(0,8),range(5)):
            count=(0,1,3)[pattern+kind%2 if pattern+kind%2<3 else 2]
            scale=FLOATS[(kind+pattern+plan)%len(FLOATS)];animation=(1,5,256)[kind%3]
            models=self.compare(fixture(animation,count,kind,pattern),animation=animation,scale=scale,
                mode=mode,phase=phase,plan=plan);coverage.update(models[0].visits);cases+=1
        for count in range(256):
            models=self.compare(fixture(count=count,kind=count&255),scale=FLOATS[count%len(FLOATS)],mode=MASK)
            coverage.update(models[0].visits);cases+=1
        for scale in FLOATS:self.compare(fixture(count=1),scale=scale);cases+=1
        self.compare(fixture(count=0),actor=0);cases+=1
        memory=fixture(count=0);put(memory,descriptor_address(),0,4);self.compare(memory,actor=0);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+356,4)))
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=89,
            independent_full_private_order=True,all_type_and_count_bytes=True,full_word_mode=True,
            ninth_float_bit_carrier=True,live_count_shrink_growth_and_cached_record_pointer=True,
            null_intermediate_and_last_callback_results=True,caller_GP_FPR_clobbered=True,F20_pair_preserved=True,
            nonfinite_bits_transferred_no_FCSR_arithmetic_claim=True,actual_deeper_helpers_bounded=True)

    def test_03_private_aliases_strict_fault_prefixes_and_null_record_boundary(self):
        cases=prefixes=0
        for phase,kind,alias in itertools.product((0,8),(0,2,255),range(4)):
            frame=STACK+phase-0x68
            table=frame+0x20 if alias==1 else TABLE
            records=frame+0x10 if alias==2 else frame+0x64 if alias==3 else RECORDS
            memory=fixture(animation=1,count=1 if alias>=2 else 3,kind=kind,table=table,records=records)
            symbols=dict(screen.recovery.SYMBOLS,D_80086CC4=table)
            forms=tuple(self.link(name,screen.ENTRY,symbols) for name in ('original','selected','fitted'))
            models=self.compare(memory,forms=forms,animation=1,table=table,phase=phase,scale=0x7F812345);cases+=1
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in forms:
                    model=ConstructorOracle(words,memory,animation=1,table=table,phase=phase,scale=0x7F812345);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                for name in ('memory','events','calls','f'):
                    self.assertEqual(getattr(failed[0],name),getattr(failed[1],name));self.assertEqual(getattr(failed[0],name),getattr(failed[2],name))
                prefixes+=1
        missing=[];memory=fixture(count=1);put(memory,descriptor_address(),0,4)
        for words in (self.original,self.raw,self.fitted):
            model=ConstructorOracle(words,memory)
            with self.assertRaises(AssertionError) as caught:model.run()
            self.assertEqual(caught.exception.args,(('unmapped read',3,1),));missing.append(model)
        for name in ('memory','events','calls','accesses'):
            self.assertEqual(getattr(missing[0],name),getattr(missing[1],name));self.assertEqual(getattr(missing[0],name),getattr(missing[2],name))
        self.receipt('aliases',cases=cases,executions=cases*3,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            outgoing_stack_descriptor_record_and_saved_RA_aliases=True,FP_fault_prefixes_compared=True,
            nonzero_count_null_records_failed_executions=3,guest_fault_not_portable_C=True)

    def test_04_independent_table_and_both_callback_relocations(self):
        cases=0
        for entry,table,first,second in ((screen.ENTRY,TABLE,TYPE0,OTHER),
                (0x15207FFC,0x80117FFC,0x15218004,0x15227FFC),
                (0x15308004,0x80118004,0x15317FFC,0x15328004)):
            symbols=dict(zip(screen.recovery.SYMBOLS,(table,first,second)))
            forms=tuple(self.link(name,entry,symbols) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            for animation,count,kind,phase in itertools.product((0,1,256,0x7FFFFFFF,0x80000000,MASK),
                    (0,1,3),(0,2,255),(0,8)):
                self.compare(fixture(animation,count,kind,table=table),forms=forms,
                    animation=animation,table=table,type0=first,other=second,phase=phase);cases+=1
        self.receipt('rebases',independent_links=9,cases=cases,executions=cases*3,signed_LO_carries=True,
            both_JALs_independent=True,wrapping_table_indices_guest_only=True)

    def test_05_complete_copied_owner_padding_neighbor_extents_and_typed_stub(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True);objects.append(obj)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]),self.rows);padded=[]
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AEB40',str(assembly),
                '--word-patches',str(self.out/('before-guards' if index==0 else 'qualified-guards.csv'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True);padded.append(parse_object(assembly.with_suffix('.o')))
        old,new=padded;start=new[1][screen.FUNCTION]['value'];expected=bytearray(old[0])
        expected[start:start+356]=struct.pack('>89I',*screen.recipe(screen.RAW))
        stub_start=new[1]['func_15083AC8']['value'];expected[stub_start:stub_start+28]=struct.pack('>7I',*TYPED_STUB)
        self.assertEqual(bytes(expected),new[0])
        expected_functions={name:dict(f) for name,f in old[1].items()};expected_functions[screen.FUNCTION]['size']=356
        expected_functions['func_15083AC8']['size']=28
        self.assertEqual(expected_functions,new[1])
        old_relocs={offset:uses for offset,uses in old[2].items() if not start<=offset<start+356}
        new_relocs={offset:uses for offset,uses in new[2].items() if not start<=offset<start+356};self.assertEqual(old_relocs,new_relocs)
        self.assertEqual({offset-start:uses for offset,uses in new[2].items() if start<=offset<start+356},screen.RELOCATIONS)
        cases=0;code={TYPE0+i*4:w for i,w in enumerate(TYPED_STUB)}
        code.update({OTHER+i*4:w for i,w in enumerate(self.old_other)})
        for count,kind,mode,scale,phase in itertools.product((0,1,3),(0,2,255),(0,MASK),FLOATS,(0,8)):
            memory=fixture(count=count,kind=kind);expected_state=reference(memory,mode=mode,scale=scale,phase=phase,stubs=True)
            for words in (self.original,self.raw,self.fitted):
                model=ConstructorOracle(words,memory,mode=mode,scale=scale,phase=phase,connected=code).run()
                self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected_state)
            cases+=1
        self.receipt('owner',unchanged_neighbors=len(new[1])-2,diagnostics=warnings[1],pools_equal=True,
            only_constructor_and_explicit_typed_stub_bodies_and_extents_change=True,
            typed_ninth_float_stub_still_zero=True,typed_stub_added_home_stores=4,
            actual_linked_placeholder_cases=cases,actual_linked_placeholder_executions=cases*3)

    def test_06_effective_IDO_semantic_and_live_callback_negatives(self):
        controls=(('wrong-stride','record += 16','record += 8',{}),
            ('wrong-type2','record[3] == 2','record[3] == 1',dict(kind=2)),
            ('narrow-mode','s32 mode','u8 mode',dict(kind=2,mode=0xABCDEF11)),
            ('zero-scale',', scale);',', 0.0f);',dict(scale=0x3F800000)),
            ('first-result','            i++;','            return created;\n            i++;',{}),
            ('cached-count','    i = 0;','    i = 0;',dict(plan=2,count=1)),
            ('reload-pointer','        do {','        do {\n            record = descriptor->records + (u32)i * 16;',dict(plan=3)))
        controls+= (('signed-byte','record[4]','(s8)record[4]',{}),
            ('signed-count','    s32 i;','    s32 i;',dict(count=128)))
        for name,old,new,case in controls:
            body=screen.SELECTED.replace(old,new)
            if name=='cached-count':body=body.replace('    s32 i;','    s32 i;\n    s32 limit;').replace(
                '    i = 0;','    i = 0;\n    limit = descriptor->count;').replace(
                'if (descriptor->count > 0)','if (limit > 0)').replace('while (i < descriptor->count)','while (i < limit)')
            settings={k:v for k,v in case.items() if k not in ('kind','count')}
            memory=fixture(count=case.get('count',3),kind=case.get('kind',0))
            if name=='signed-count':
                with patch.object(screen.recovery,'RECORD',screen.recovery.RECORD.replace('u8 count','s8 count')):
                    _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            else:_,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            wrong=ConstructorOracle(words,memory,**settings).run();expected=reference(memory,**settings)
            self.assertNotEqual((wrong.calls,wrong.r[2]),(expected[2],expected[3]),name)
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls))

    def test_07_native32_complete_C_both_typed_stack_packets_and_live_callbacks(self):
        source=NATIVE+screen.recovery.RECORD+NATIVE_CALLBACKS+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-stride','record += 16','record += 8'),
                ('native-type2','record[3] == 2','record[3] == 1'),('native-mode','s32 mode','u8 mode')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=256*256*4+256,
            all_type_and_parameter_byte_pairs=True,both_typed_stack_packets=True,live_count_and_cursor_qualify=True,
            full_word_mode_last_result_and_float_bits=True,effective_native_negatives=3,real_assets_hardware_not_claimed=True)

    def test_08_actual_record_caller_request_lookup_list_classifier_constructor_chain(self):
        cases=prefixes=0;connected={a+i*4:w for a,words in self.helpers.items() for i,w in enumerate(words)}
        for identity,index,count,kind,amount,phase in itertools.product((0,3),(0,1,5),
                (0,1,3),(0,2,255),(0,1,MASK),(0,8)):
            memory=request.count.fixture(identity=identity,record_base=request.reset.RESOURCE-7*10)
            selected_animation=(5,6,7,10,11)[max(index-1,0)]
            data=fixture(selected_animation,count,kind)
            memory.update({a:v for a,v in data.items() if not ACTOR<=a<ACTOR+812 and not STACK-0x300<=a<STACK+0x100})
            for i,value in enumerate((5,6,7,10,11)):put(memory,request.DEFAULT+i,value,1)
            put(memory,request.FACTOR,request.FACTOR_BITS,4);put(memory,ACTOR+0x6F,7,1)
            for offset,value,size in ((0,249,1),(1,248,1),(2,7,1),(3,253,1),(4,index,1),(6,1000,2),(8,0,1),(9,0,1)):
                put(memory,request.reset.RESOURCE+offset,value,size)
            put(memory,ACTOR+0x134,2,1);put(memory,request.count.ARCHIVE+0x3B,129,1);put(memory,request.count.ARCHIVE+0x3C,254,1)
            with patch.object(request,'reference',request_reference):expected=request.caller_reference(memory,amount=amount,phase=phase)
            models=[]
            for words in (self.original,self.raw,self.fitted):
                code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                model=ConstructorOracle(self.helpers[request.CALLER],memory,animation=selected_animation,
                    arguments=(ACTOR,amount),entry=request.CALLER,phase=phase,connected=code).run()
                self.assertEqual((model.memory,model.events,model.calls),expected);models.append(model)
            if identity==0 and index==5 and count==3 and kind==2 and amount==1:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.raw,self.fitted):
                        code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                        model=ConstructorOracle(self.helpers[request.CALLER],memory,animation=selected_animation,
                            arguments=(ACTOR,amount),entry=request.CALLER,phase=phase,connected=code);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    for name in ('memory','events','calls','f'):
                        self.assertEqual(getattr(failed[0],name),getattr(failed[1],name));self.assertEqual(getattr(failed[0],name),getattr(failed[2],name))
                    prefixes+=1
            cases+=1
        self.receipt('caller',cases=cases,executions=cases*3,actual_constructor_and_five_caller_helpers=True,
            fired_fault_triples=prefixes,failed_executions=prefixes*3,
            actual_deeper_9_and_13_argument_callbacks_still_bounded=True,hardware_gameplay_not_claimed=True)
        cases=0
        for animation,(descriptor,records,data) in self.assets.items():
            for scale,mode,phase in itertools.product(FLOATS,(0,MASK),(0,8)):
                memory=fixture(animation=animation)
                memory.update({descriptor_address(animation)+i:v for i,v in enumerate(descriptor)})
                memory.update({records+i:v for i,v in enumerate(data)})
                self.compare(memory,animation=animation,scale=scale,mode=mode,phase=phase);cases+=1
        self.receipt('retail-assets',entries=list(self.assets),cases=cases,executions=cases*3,
            descriptor_and_every_record_byte_verified_against_checksum_verified_ROM=True,
            deeper_callbacks_bounded_not_gameplay_acceptance=True)

    def test_09_whole_linked_audit_single_slot_extent_guard_prefix_no_conversion_credit(self):
        for name in self.paths:assert hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest()==self.baseline[name]
        source=(self.root/screen.SOURCE).read_text();before_source=(self.out/'before-source').read_text()
        if screen.recovery.ORIGINAL in source:
            for name,path in self.paths.items():self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('installation',installed=False);return
        self.assertEqual(source,screen.install(before_source))
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        with (self.root/self.paths['guards']).open(newline='') as stream:
            reader=csv.DictReader(stream);self.assertEqual(reader.fieldnames,self.fields);self.assertEqual(list(reader),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        before=(self.out/'before-elf').read_bytes();expected=bytearray(before)
        struct.pack_into('>89I',expected,elf_slot_offset(before,screen.ENTRY,356),*self.original)
        struct.pack_into('>I',expected,installed.symbol_size_offset(before,screen.FUNCTION,screen.ENTRY),356)
        struct.pack_into('>7I',expected,elf_slot_offset(before,TYPE0,28),*TYPED_STUB)
        struct.pack_into('>I',expected,installed.symbol_size_offset(before,'func_15083AC8',TYPE0),28)
        actual=(self.root/self.paths['elf']).read_bytes();self.assertEqual(metadata(bytes(expected))[:4],metadata(actual)[:4])
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_constructor_and_explicit_typed_stub_slots_and_extents_change=True,bytes=384,
            all_other_bytes_addresses_extents_exact=True,guard_prefix_exact=True,guards_added=17,
            conversion_rows_byte_identical=True,converted_functions_added=0,converted_bytes_added=0,protected_data=audit)


NATIVE=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actor[812],records[256][16],alternate[256][16],created[3][4];
static int animationValue,modeValue,planValue,ordinal,errors;static u32 scaleBits;static u8 *last;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static void report(u32 slot,u32 expected,u32 actual){u32 detail[3]={slot,expected,actual};
    __asm__ volatile("int $0x80" : : "a"(4),"b"(2),"c"(detail),"d"(12) : "memory");}
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(f32)==4)?1:-1];
'''
NATIVE_CALLBACKS=r'''
AnimationDescriptor15083568 D_80086CC4[256];
static u8 *callback(int type,const u32 *packet,int count){
    int i;u8 *r=records[ordinal];u32 expected[13];u8 *result;
    if(type==0){expected[0]=(u32)actor;expected[1]=r[1];expected[2]=r[0];expected[3]=0;
        expected[4]=r[2];expected[5]=r[4];expected[6]=r[5];expected[7]=r[6];expected[8]=scaleBits;
    }else{expected[0]=(u32)actor;expected[1]=r[0];expected[2]=r[1];expected[3]=r[7];expected[4]=r[4];
        expected[5]=r[5];expected[6]=(u32)modeValue;expected[7]=animationValue;expected[8]=r[2];
        expected[9]=(u32)(r+8);expected[10]=r[3]==2?r[6]:0xFFFFFFFFu;expected[11]=r[14];expected[12]=r[15];}
    if(type!=!!r[3])errors=1;
    for(i=0;i<count;i++)if(packet[i]!=expected[i]){if(!errors)report(i,expected[i],packet[i]);errors=2;}
    if(!ordinal){if(planValue==1)D_80086CC4[animationValue-1].count=0;
        if(planValue==2)D_80086CC4[animationValue-1].count=3;
        if(planValue==3){D_80086CC4[animationValue-1].records=(u8 *)alternate;records[1][3]=2;records[1][6]=255;}}
    result=((ordinal+modeValue)&3)==0?0:created[ordinal%3];ordinal++;last=result;return result;
}
u8 *func_15083AC8(u8 *a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,f32 scale){
    const u32 packet[9]={(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f,(u32)g,(u32)h,word(scale)};
    return callback(0,packet,9);}
u8 *func_15030AF4(u8 *a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,s32 i,u8 *j,s32 k,s32 l,s32 m){
    const u32 packet[13]={(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f,(u32)g,(u32)h,(u32)i,(u32)j,(u32)k,(u32)l,(u32)m};
    return callback(1,packet,13);}
'''
NATIVE_RUNNER=r'''
static int qualify(int kind,int pattern,int count,int plan,int animation){
    static const u32 floats[12]={0,0x80000000u,0x3F800000u,0xC0200000u,0x7F800000u,0xFF800000u,
        0x7FC12345u,0x7F812345u,1,0x807FFFFFu,0x7F7FFFFFu,0xFFFFFFFFu};
    int i,j,expectedCalls;u8 *result;union{u32 u;f32 f;}input;
    animationValue=animation;modeValue=(s32)(0xABCDEF00u+(u32)pattern);
    planValue=plan;ordinal=errors=0;last=0;scaleBits=floats[(kind+pattern)%12];
    for(i=0;i<256;i++)for(j=0;j<16;j++){records[i][j]=(u8)(j*37+pattern*67+i*19);alternate[i][j]=(u8)(i+j);}
    for(i=0;i<256;i++)records[i][3]=(u8)(i==0?kind:i%4==0?0:i%4==1?2:i%4==2?1:255);
    D_80086CC4[animation-1].records=(u8 *)records;D_80086CC4[animation-1].count=(u8)count;
    input.u=scaleBits;result=func_15083568(actor,animation,input.f,modeValue);
    expectedCalls=count?(plan==1?1:plan==2?3:count):0;
    if(errors || ordinal!=expectedCalls || result!=last)return 1;
    if(D_80086CC4[animation-1].records!=(plan==3 && count?(u8 *)alternate:(u8 *)records))return 2;
    if(D_80086CC4[animation-1].count!=(u8)(count && plan==1?0:count && plan==2?3:count))return 3;
    for(i=0;i<812;i++)if(actor[i])return 5;
    for(i=0;i<256;i++)for(j=0;j<16;j++){
        u8 expected=(u8)(j==3?(i==0?kind:i%4==0?0:i%4==1?2:i%4==2?1:255):j*37+pattern*67+i*19);
        if(count && plan==3 && i==1 && j==3)expected=2;
        if(count && plan==3 && i==1 && j==6)expected=255;
        if(records[i][j]!=expected || alternate[i][j]!=(u8)(i+j))return 4;}
    return 0;
}
int run(void){int kind,pattern,plan,r,count;
    for(kind=0;kind<256;kind++)for(pattern=0;pattern<256;pattern++)for(plan=0;plan<4;plan++){
        r=qualify(kind,pattern,pattern%3==0?0:pattern%3==1?1:3,plan,(kind%3==0?1:kind%3==1?5:256));if(r)return r;}
    for(count=0;count<256;count++){r=qualify(count,count,count,0,1);if(r)return r;}
    return 0;}
'''


if __name__=='__main__':unittest.main()
