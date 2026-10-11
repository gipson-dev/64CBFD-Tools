"""Full transform submit: live selector, empty adjustment stream and void float ABI."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_node_transform_submit_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_node_alternate_loader_match as alternate
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.check_game_data_layout import audit_layout

STACK,MASK=alternate.STACK,0xFFFFFFFF
SELECTOR,STEP,ALLOCATE,PREPARE,EMIT,SUBMIT,TIMELINE,FREE=screen.recovery.SYMBOLS.values()
NODE,MATRIX,MATRIX2,BUFFER,BUFFER2,TEMP=0x68000,0x70000,0x71000,0x72000,0x73000,0x74000
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,1,0x807FFFFF,0x7F7FFFFF)
BOUNDARIES=(0,1,2,127,128,254,255)


def fixture(selector=0,count=2,gate=True,step=0x3F800000,node=NODE,phase=0,symbols=None):
    selector_address,step_address,*_=(symbols or screen.recovery.SYMBOLS).values();memory={}
    for start,size in ((STACK-0x700,0x800),(node,0x800),(MATRIX,128),(MATRIX2,128),
            (BUFFER,512),(BUFFER2,512),(TEMP,0x320),(selector_address,4),(step_address,4)):
        memory.update({(start+i)&MASK:(i*17+35)&255 for i in range(size)})
    for address,value,size in ((selector_address,selector,1),(step_address,step,4),
            (node+0x3F4,count,1),(node+0x3F0,MATRIX2,4),(node+0x28,0,4)):
        put(memory,address&MASK,value,size)
    for offset,value in ((0x3E0,MATRIX),(0x3E4,MATRIX2),(0x3E8,BUFFER),(0x3EC,BUFFER2)):
        put(memory,(node+offset)&MASK,value)
    put(memory,(node+0x3E0+selector*4)&MASK,MATRIX if gate else 0)
    put(memory,(node+0x3E8+selector*4)&MASK,BUFFER)
    return memory


def changes(role,plan,node,frame,symbols):
    selector,step,*_=symbols.values()
    if role=='allocate' and plan==1:return ((selector,1,1),)
    if role=='prepare' and plan==2:return ((selector,1,1),(node+0x3F4,255,1),(node+0x3F0,MATRIX,4))
    if role=='emit' and plan==3:return ((selector,2,1),(node+0x3F4,0,1),(node+0x3F0,BUFFER2,4))
    if role=='submit' and plan==4:return ((step,0x7F812345,4),(node+0x3F6,0,1))
    if role=='timeline' and plan==5:return ((frame+0x44,BUFFER2,4),(node+0x3F6,77,1))
    if role=='timeline' and plan==6:return ((frame+0x44,0,4),)
    if role=='emit' and plan==7:return ((frame+0x44,BUFFER2,4),)
    if role=='free' and plan==8:return ((node+0x3F6,99,1),)
    return ()


def reference(memory,node=NODE,phase=0,temporary=TEMP,plan=0,symbols=None,marker=0x40,
        return_address=0xDEAD0000,**unused):
    symbols=symbols or screen.recovery.SYMBOLS;selector,step,allocate,prepare,emit,submit,timeline,free=symbols.values()
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x48
    def get(address,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(target,packet,role):
        events.append(('CALL',target,packet));calls.append((target,*packet))
        if role=='emit':
            value=get(packet[0]);self_marker=get(packet[5],2);assert self_marker==0x1000
            store(packet[0],value+64)
        for address,value,size in changes(role,plan,node,frame,symbols):store(address,value,size)
    store(frame+0x28,0x5A000010);store(frame+0x2C,return_address)
    index=get(selector,1);store(frame+0x44,0);matrix=get(node+0x3E0+index*4)
    if matrix:
        call(allocate,(0x320,1,2,2),'allocate');store(frame+0x44,temporary)
        call(prepare,(node,0,temporary),'prepare')
        index=get(selector,1);store(frame+marker,0x1000,2)
        buffer=get(node+0x3E8+index*4);matrix=get(node+0x3E0+index*4);store(frame+0x38,buffer)
        count=get(node+0x3F4,1);source=get(node+0x3F0)
        for offset,value in ((0x1C,0),(0x18,0),(0x14,frame+marker),(0x10,count)):store(frame+offset,value)
        call(emit,(frame+0x38,matrix,node,source,count,frame+marker,0,0),'emit')
        index=get(selector,1);count=get(node+0x3F4,1);buffer=get(node+0x3E8+index*4)
        call(submit,(buffer,count),'submit');store(node+0x3F6,1,1)
    call(timeline,(node,get(step),0,0),'timeline')
    value=get(frame+0x44)
    if value:call(free,(value,),'free')
    get(frame+0x2C);get(frame+0x28)
    return state,events,calls


class SubmitOracle(reset.ResetOracle):
    def __init__(self,words,memory,node=NODE,phase=0,temporary=TEMP,plan=0,symbols=None,
            entry=screen.ENTRY,connected=None,**unused):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(node,),phase=phase,entry=entry,connected=connected)
        self.symbols=symbols or screen.recovery.SYMBOLS;_,_,allocate,prepare,emit,submit,timeline,free=self.symbols.values()
        self.roles=dict(zip((allocate,prepare,emit,submit,timeline,free),('allocate','prepare','emit','submit','timeline','free')))
        self.counts=dict(zip((allocate,prepare,emit,submit,timeline,free),(4,3,8,2,4,1)))
        self.node,self.frame,self.temporary,self.plan=node,STACK+phase-0x48,temporary,plan
    def hook(self,target):
        role=self.roles[target];packet=self.calls[-1][1:]
        if role=='emit':
            value=self.get(packet[0],4);marker=self.get(packet[5],2)
            assert marker==0x1000,('invalid transform terminator',marker)
            self.put(packet[0],value+64,4)
        for address,value,size in changes(role,self.plan,self.node,self.frame,self.symbols):self.put(address,value,size)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.temporary if role=='allocate' else (0xBEEF0000|target&65535)


class WindowOracle(SubmitOracle):
    def record_call(self,target):
        if target==screen.ENTRY:self.snapshot=(self.memory.copy(),self.r[29],self.r[4],len(self.events),self.r[31])
        super().record_call(target)


class GameNodeTransformSubmitMatchTests(unittest.TestCase):
    maxDiff=1800
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-node-transform-submit-test'
        cls.out.mkdir(exist_ok=True);cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>66I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes();cls.rows=screen.guard_rows(cls.out/'selected.o')
        cls.fields=next(csv.reader((cls.out/'before-guards').read_text().splitlines()))
        cls.write_rows(cls.out/'target-guards.csv',cls.rows)
        cls.full_guards=cls.out/'full-guards.csv';cls.full_guards.write_bytes((cls.out/'before-guards').read_bytes())
        screen.append_guards(cls.full_guards,cls.full_guards.read_bytes(),cls.out/'selected.o')
        body=(cls.root/'conker/asm/6C960.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_6C960',
            word_patches_path=cls.out/'target-guards.csv'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%v for v in (symbols or screen.recovery.SYMBOLS).items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>66I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        models=[]
        for index,code in enumerate(forms or (self.original,self.raw,self.fitted)):
            model=SubmitOracle(code,memory,**settings).run();models.append(model)
            expected=reference(memory,marker=0x3E if index==1 else 0x40,**settings)
            self.assertEqual((model.memory,model.events,model.calls),expected)
        return models
    def test_01_shape_stale_body_relocations_and_publication(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes'],
            self.meta['diagnostics']),(66,72,2,0,''))
        text,functions,relocations=parse_object(self.out/'selected.o');start=functions[screen.FUNCTION]['value']
        for i in range(66):
            words=list(screen.RAW);words[i]^=1
            with self.assertRaisesRegex(ValueError,'stale complete'):screen.recipe(words)
        for offset in screen.RELOCATIONS:
            modified={k:list(v) for k,v in relocations.items()};modified[start+offset]=[('R_MIPS_26','wrong_symbol')]
            with patch.object(screen,'parse_object',return_value=(text,functions,modified)):
                with self.assertRaisesRegex(ValueError,'stale transform.*relocations'):screen.guard_rows(self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'stale transform.*manifest'):
            screen.append_guards(self.full_guards,b'wrong\n',self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'already published'):
            screen.append_guards(self.full_guards,self.full_guards.read_bytes(),self.out/'selected.o')
        self.assertEqual(len(self.rows),2)
        self.assertTrue(all(r['insert_after']=='' and r['omit']=='false' for r in self.rows))
        self.receipt('shape',words=66,frame=72,guards=2,private_marker_raw=62,private_marker_retail=64,
            stale_word_controls=66,stale_relocation_controls=14,insertions_omissions=0,diagnostic_bytes=0,pool_bytes=0)
    def test_02_all_selector_count_bytes_gates_NULL_temporary_and_float_bits(self):
        cases=0;coverage=set()
        for axis,value,phase in itertools.product(('selector','count'),range(256),(0,8)):
            inputs={axis:value,'phase':phase};models=self.compare(fixture(**inputs),phase=phase);cases+=1
            coverage.update(models[0].visits)
        for selector,count,gate,step,temporary,phase in itertools.product((0,1),BOUNDARIES,(False,True),FLOATS,(0,TEMP),(0,8)):
            models=self.compare(fixture(selector,count,gate,step,phase=phase),temporary=temporary,phase=phase)
            cases+=1;coverage.update(models[0].visits)
        self.assertEqual(set(range(screen.ENTRY,screen.ENTRY+264,4))-coverage,set())
        self.receipt('guest',cases=cases,executions=cases*3,all_66_words_reached=True,
            all_selector_count_bytes=True,NULL_allocation_still_prepares_and_submits=True,
            full_float_wire_bits_including_signed_zero_infinities_and_NaNs=True,
            independent_raw_private_layout_reference=True,fitted_complete_ordered_reference=True,
            caller_GP_FPR_clobbered=True,void_return_not_status=True)
    def test_03_live_mutations_aliases_and_fired_fault_pairs(self):
        cases=prefixes=0
        for plan,gate,temporary,phase in itertools.product(range(9),(False,True),(0,TEMP),(0,8)):
            memory=fixture(gate=gate,phase=phase);models=self.compare(memory,plan=plan,temporary=temporary,phase=phase);cases+=1
            if phase==0:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for code in (self.original,self.fitted):
                        model=SubmitOracle(code,memory,plan=plan,temporary=temporary);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls,failed[0].f),
                        (failed[1].memory,failed[1].events,failed[1].calls,failed[1].f));prefixes+=1
        for node in ((SELECTOR-0x3F4)&MASK,(STEP-0x3E0)&MASK):
            self.compare(fixture(node=node),node=node);cases+=1
        failed=[]
        for code in (self.original,self.fitted):
            model=SubmitOracle(code,fixture(),node=0)
            with self.assertRaises(AssertionError):model.run()
            failed.append(model)
        self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls),
            (failed[1].memory,failed[1].events,failed[1].calls));cases+=1
        self.receipt('aliases',cases=cases,fired_retail_fitted_fault_pairs=prefixes,failed_executions=prefixes*2,
            live_selector_metadata_step_and_temporary_home=True,private_cursor_update_not_submission_source=True,
            global_public_aliases=True,required_NULL_node_guest_fault=True,raw_private_fault_equivalence_not_claimed=True)
    def test_04_independent_two_globals_six_callbacks_and_signed_carries(self):
        cases=0
        for j in range(3):
            symbols={name:0x80107FFC+j*0x10004+i*0x8008 if i<2 else 0x15410004+j*0x10004+i*0x100
                for i,name in enumerate(screen.recovery.SYMBOLS)}
            entry=0x15217FFC+j*0x10004;forms=tuple(self.link(n,entry,symbols) for n in ('original','selected','fitted'))
            for selector,gate,temporary,plan in itertools.product((0,1,255),(False,True),(0,TEMP),(0,2,3,5)):
                self.compare(fixture(selector=selector,gate=gate,symbols=symbols),forms=forms,
                    entry=entry,symbols=symbols,temporary=temporary,plan=plan);cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,all_14_relocation_sites=True,
            independent_selector_float_globals_and_six_callbacks=True,HI_LO_signed_carries=True)
    def test_05_copied_owner_real_padder_three_unchanged_neighbors(self):
        objects=[];padded=[];diagnostics=[];before=(self.out/'before-source').read_text()
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,detail=compile_owner(self.root,self.out,source,name);objects.append(obj);diagnostics.append(detail)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_6C960',str(asm),'--word-patches',str(self.full_guards if name=='owner-after' else self.out/'before-guards')],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        a,b=padded;start=b[1][screen.FUNCTION]['value'];expected=bytearray(a[0]);raw,funcs,_=parse_object(objects[1])
        words=struct.unpack_from('>66I',raw,funcs[screen.FUNCTION]['value'])
        struct.pack_into('>66I',expected,start,*screen.recipe(words));self.assertEqual(bytes(expected),b[0])
        for name in a[1]:
            if name!=screen.FUNCTION:self.assertEqual(a[1][name],b[1][name])
        self.assertEqual(a[2],{k:v for k,v in b[2].items() if not start<=k<start+264})
        self.receipt('owner',untouched_neighbors=len(a[1])-1,neighbor_bytes_extents_relocations_exact=True,
            normalized_pools_exact=True,diagnostic_bytes=0,actual_padder=True,existing_24_neighbor_guards_unchanged=True)
    def test_06_effective_fresh_IDO_negative_controls(self):
        controls=(('wrong-gate',screen.SELECTED.replace('[D_800BE9C0] != NULL','[D_800BE9C0] == NULL'),{}),
            ('wrong-size',screen.SELECTED.replace('0x320, 1','0x300, 1'),{}),
            ('skip-NULL-prepare',screen.SELECTED.replace('        func_1502D824(node, 0, temporary);',
                '        if (temporary != NULL) func_1502D824(node, 0, temporary);'),dict(temporary=0)),
            ('wrong-marker',screen.SELECTED.replace('scale = 0x1000','scale = 0x1001'),{}),
            ('wrong-count',screen.SELECTED.replace('node[0x3F4]','(s8)node[0x3F4]'),dict(count=255)),
            ('cached-cursor',screen.SELECTED.replace('func_150A9984(((u8 **)(node + 0x3E8))[D_800BE9C0],','func_150A9984(buffer,'),{}),
            ('wrong-flag',screen.SELECTED.replace('[0x3F6] = 1','[0x3F6] = 0'),{}),
            ('wrong-step',screen.SELECTED.replace('(struct197 *)node, D_800BE9A4, NULL, 0',
                '(struct197 *)node, 1.0f, NULL, 0'),dict(step=0xC0200000)))
        for name,body,inputs in controls:
            _,words=screen.compile_candidate(self.root,self.out,name,body);settings={k:v for k,v in inputs.items() if k=='temporary'}
            memory=fixture(**{k:v for k,v in inputs.items() if k!='temporary'});expected=SubmitOracle(self.original,memory,**settings).run()
            if name=='wrong-marker':
                actual=SubmitOracle(words,memory,**settings)
                with self.assertRaises(AssertionError) as caught:actual.run()
                self.assertEqual(caught.exception.args,(('invalid transform terminator',0x1001),))
                self.assertEqual(actual.calls[-1][0],EMIT)
            else:
                actual=SubmitOracle(words,memory,**settings).run()
                self.assertNotEqual((alternate.initializer.public(actual.memory),actual.calls),
                    (alternate.initializer.public(expected.memory),expected.calls),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls),marker_protocol_rejects_bad_terminator=True)
    def test_07_native32_optimized_unoptimized_valid_selector_and_wire_contract(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        for name,body in (('wrong-size',screen.SELECTED.replace('0x320, 1','0x300, 1')),
                ('wrong-flag',screen.SELECTED.replace('[0x3F6] = 1','[0x3F6] = 0'))):
            result,_=self.run_native('native-'+name,NATIVE_PREFIX+body+NATIVE_RUNNER);self.assertNotEqual(result,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=7680,executions=15360,
            effective_negative_controls=2,all_count_bytes_and_full_float_wire_bits=True,valid_selectors=[0,1],
            private_addresses_normalized_but_cursor_and_terminator_values_checked=True,bounded_callbacks=True)
    def test_08_complete_retail_and_current_timeline_connections(self):
        original=list(struct.unpack_from('>287I',self.rom,0xA9260))
        current=list(struct.unpack_from('>287I',self.before,elf_slot_offset(self.before,TIMELINE,1148)))
        difference=sum(a!=b for a,b in zip(current,original));self.assertEqual(difference,237)
        cases=0
        for gate,temporary,sequence,rate,frame,phase in itertools.product((False,True),(0,TEMP),(0,1),
                (1.0,-1.0),(2.0,9.5),(0,8)):
            memory=fixture(gate=gate,phase=phase)
            for address,value,size in ((NODE,0,4),(NODE+4,0,2),(NODE+8,bits(frame),4),(NODE+0x10,bits(rate),4),
                    (NODE+0x18,bits(10.0),4),(NODE+0x20,bits(1.0),4),(NODE+0x28,sequence,4),
                    (NODE+0x3A,1,2),(NODE+0x3C,0,2),(0x800BEA0C,0,1),(0x800BE9E4,1,4),(0x8009B688,bits(1.0),4)):
                for i in range(size):memory[address+i]=0
                put(memory,address,value,size)
            models=[]
            for helper in (original,current):
                connected={TIMELINE+i*4:w for i,w in enumerate(helper)}
                pair=[SubmitOracle(code,memory,connected=connected,temporary=temporary,phase=phase).run()
                    for code in (self.original,self.fitted)]
                a,b=pair;self.assertEqual((a.memory,a.events,a.calls),(b.memory,b.events,b.calls));models.append(a)
            self.assertEqual(alternate.initializer.public(models[0].memory),alternate.initializer.public(models[1].memory))
            expected=frame if not sequence else frame+rate
            if sequence and expected>=10.0:expected=expected-10.0+1.0
            if sequence and expected<1.0:expected=expected-1.0+10.0
            self.assertEqual(read(models[0].memory,NODE+8),bits(expected));cases+=1
        self.receipt('timeline',cases=cases,executions=cases*4,reference_words=287,current_slot_words=287,
            current_helper_word_differences=237,current_helper_not_claimed_matching=True,
            original_and_current_finite_null_actor_timeline_outputs_agree=True,complete_helpers_executed=True)
    def test_09_whole_ELF_single_slot_and_protected_inputs(self):
        source=(self.root/screen.SOURCE).read_text();before=self.before
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.recovery.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.recovery.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>66I',expected,elf_slot_offset(before,screen.ENTRY,264),*self.fitted)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbols=old[4];changed=0
        for offset in range(symbols[4],symbols[4]+symbols[5],symbols[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:]);self.assertEqual((a[2],b[2]),(12,264))
                struct.pack_into('>I',expected,offset+8,b[2]);changed+=1
        self.assertEqual(changed,1);self.assertEqual(bytes(expected),actual)
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.full_guards.read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,all_other_ELF_bytes_exact=True,
            ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),appended_guards=2,old_guard_prefix_exact=True,
            data_audit=audit,conversion_rows_unchanged=True)
    def test_10_three_retail_JAL_delay_slot_windows(self):
        cases=0
        for pc,rom,offset in ((0x150309EC,0x5DE9C,0x48),(0x151573A4,0x184854,None),
                (0x151EDCD8,0x21B188,0x24)):
            call,delay=struct.unpack_from('>2I',self.rom,rom);self.assertEqual(call,0x0D40FD2C)
            self.assertEqual(delay,0xAFA50020 if offset is None else 0x8E240000|offset)
            # Synthetic save/restore brackets only the authentic two-word call window.
            wrapper=[0x27BDFFE0,0xAFBF001C,call,delay,0x8FBF001C,0x03E00008,0x27BD0020]
            for gate,temporary,phase,plan in itertools.product((False,True),(0,TEMP),(0,8),(0,2)):
                memory=fixture(gate=gate,phase=phase);owner=0x76000
                memory.update({owner+i:0xA5 for i in range(0x80)})
                if offset is not None:put(memory,owner+offset,NODE)
                models=[]
                for body in (self.original,self.fitted):
                    connected={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                    model=WindowOracle(wrapper,memory,phase=phase,temporary=temporary,plan=plan,entry=pc-8,connected=connected)
                    model.r[17]=model.before[17]=owner;model.r[5]=owner;model.counts[screen.ENTRY]=1;model.frame-=0x20
                    model.run();models.append(model)
                    snapshot,stack,node,index,ra=model.snapshot
                    expected=reference(snapshot,node=node,phase=stack-STACK,temporary=temporary,plan=plan,return_address=ra)
                    self.assertEqual(model.events[index+1:index+1+len(expected[1])],expected[1])
                    self.assertEqual(model.calls[0],(screen.ENTRY,NODE));self.assertEqual(model.calls[1:],expected[2])
                a,b=models;self.assertEqual((a.memory,a.events,a.calls),(b.memory,b.events,b.calls));cases+=1
        self.receipt('callers',cases=cases,executions=cases*2,authentic_JAL_delay_windows=3,
            independent_complete_target_reference_inside_each_window=True,void_return_register_ignored=True,
            synthetic_wrapper=True,complete_callers_not_claimed_executed=True)


NATIVE_PREFIX=r'''
#define NULL ((void *)0)
typedef unsigned char u8;typedef short s16;typedef signed char s8;typedef int s32;typedef unsigned int u32;typedef float f32;
typedef struct {u8 opaque[64];} struct197;typedef struct struct127 struct127;
static u8 D_800BE9C0;static f32 D_800BE9A4;static u32 nodeWords[256],temporaryWords[200];
static u8 *node=(u8 *)nodeWords;static s32 missing,plan,callCount,error;
struct Call {u32 target,args[10];};static struct Call calls[8],expectedCalls[8];
static u32 expectedNode[256],expectedStep;static u8 expectedSelector;static s32 expectedCount;
static void record(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g,u32 h,u32 i,u32 j){
    struct Call *r=&calls[callCount++];r->target=target;r->args[0]=a;r->args[1]=b;r->args[2]=c;r->args[3]=d;r->args[4]=e;
    r->args[5]=f;r->args[6]=g;r->args[7]=h;r->args[8]=i;r->args[9]=j;
}
static void *allocate_memory(s32 size,s32 a,s32 b,s32 c){
    record(1,(u32)size,(u32)a,(u32)b,(u32)c,0,0,0,0,0,0);
    if(plan==1)D_800BE9C0^=1;
    return missing?0:temporaryWords;
}
static void func_1502D824(u8 *p,u8 *zero,u8 *temp){
    record(2,(u32)p,(u32)zero,(u32)temp,0,0,0,0,0,0,0);
    if(plan==2){D_800BE9C0^=1;p[1012]=255;*(u32 *)(p+1008)=0x81238004u;}
}
static void func_150A81D0(u8 **cursor,void *matrix,u8 *p,u8 *source,s32 count,s16 *marker,s32 a,s32 b){
    record(3,1,(u32)matrix,(u32)p,(u32)source,(u32)count,2,(u32)a,(u32)b,(u32)*cursor,(u32)(unsigned short)*marker);
    if(*marker!=4096)error=1;
    *cursor=(u8 *)((u32)*cursor+64u);
    if(plan==3){D_800BE9C0^=1;p[1012]=0;}
}
static void func_150A9984(u8 *buffer,s32 count){
    record(4,(u32)buffer,(u32)count,0,0,0,0,0,0,0,0);
    if(plan==4){union {u32 u;f32 f;} x;x.u=0x7F812345u;D_800BE9A4=x.f;node[1014]=0;}
}
static void func_1507BDB0(struct197 *input,f32 step,struct127 *actor,s32 mode){
    u8 *p=(u8 *)input;
    union {u32 u;f32 f;} x;x.f=step;record(5,(u32)p,x.u,(u32)actor,(u32)mode,0,0,0,0,0,0);
    if(plan==5)p[1014]=77;
}
static void func_10004074(void *temp){record(6,(u32)temp,0,0,0,0,0,0,0,0,0);if(plan==6)node[1014]=99;}
'''
NATIVE_RUNNER=r'''
static void independent(u8 *p){
    void *temp=0,*matrix;u8 *cursor;s16 marker;
    if(*(u32 *)(p+992+(u32)D_800BE9C0*4)){
        temp=allocate_memory(800,1,2,2);func_1502D824(p,0,temp);marker=4096;
        matrix=(void *)*(u32 *)(p+992+(u32)D_800BE9C0*4);cursor=(u8 *)*(u32 *)(p+1000+(u32)D_800BE9C0*4);
        func_150A81D0(&cursor,matrix,p,(u8 *)*(u32 *)(p+1008),(s32)p[1012],&marker,0,0);
        func_150A9984((u8 *)*(u32 *)(p+1000+(u32)D_800BE9C0*4),(s32)p[1012]);p[1014]=1;
    }
    func_1507BDB0((struct197 *)p,D_800BE9A4,0,0);if(temp)func_10004074(temp);
}
static void setup(s32 selector,s32 count,s32 gate,s32 fail,s32 scenario,u32 step){
    s32 i;union {u32 u;f32 f;} x;D_800BE9C0=(u8)selector;x.u=step;D_800BE9A4=x.f;
    callCount=error=0;missing=fail;plan=scenario;
    for(i=0;i<256;i++)nodeWords[i]=0xA5A5A5A5u;
    nodeWords[248]=0x70000;nodeWords[249]=0x71000;nodeWords[250]=0x72000;nodeWords[251]=0x73000;
    nodeWords[252]=0x81238004u;node[1012]=(u8)count;if(!gate)nodeWords[248+selector]=0;
}
static s32 qualify(s32 selector,s32 count,s32 gate,s32 fail,s32 scenario,u32 step){
    s32 i,j;union {u32 u;f32 f;} x;setup(selector,count,gate,fail,scenario,step);independent(node);
    expectedCount=callCount;for(i=0;i<callCount;i++)expectedCalls[i]=calls[i];
    for(i=0;i<256;i++)expectedNode[i]=nodeWords[i];
    expectedSelector=D_800BE9C0;x.f=D_800BE9A4;expectedStep=x.u;
    setup(selector,count,gate,fail,scenario,step);func_1503F4B0(node);if(error||expectedCount!=callCount)return 1;
    for(i=0;i<callCount;i++){if(expectedCalls[i].target!=calls[i].target)return 2;
        for(j=0;j<10;j++)if(expectedCalls[i].args[j]!=calls[i].args[j])return 3;}
    for(i=0;i<256;i++)if(expectedNode[i]!=nodeWords[i])return 4;
    x.f=D_800BE9A4;if(expectedSelector!=D_800BE9C0||expectedStep!=x.u)return 5;return 0;
}
int run(void){
    static const u32 words[]={0,0x80000000u,0x3F800000u,0xC0200000u,0x7F800000u,0xFF800000u,0x7FC12345u,0x7F812345u,1,0x807FFFFFu,0x7F7FFFFFu};
    static const s32 counts[]={0,1,2,127,128,254,255,256};s32 count,selector,gate,fail,scenario,i,r;
    for(count=0;count<256;count++)for(selector=0;selector<2;selector++)for(gate=0;gate<2;gate++)for(fail=0;fail<2;fail++){
        r=qualify(selector,count,gate,fail,0,0x3F800000u);if(r)return r;}
    for(count=0;count<8;count++)for(selector=0;selector<2;selector++)for(gate=0;gate<2;gate++)for(fail=0;fail<2;fail++)
        for(scenario=0;scenario<8;scenario++)for(i=0;i<11;i++){r=qualify(selector,counts[count],gate,fail,scenario,words[i]);if(r)return r;}
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
