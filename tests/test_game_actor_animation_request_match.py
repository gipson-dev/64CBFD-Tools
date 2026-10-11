"""Direct mixed-O32 animation request, actual caller/list and unchanged ELF."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_animation_request_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_definition_lookup_match as lookup
from tools.tests import test_game_actor_definition_count_match as count
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,MASK=lookup.STACK,lookup.ACTOR,lookup.MASK
LIST,CONSTRUCTOR,FACTOR=screen.SYMBOLS.values()
CLASSIFIER,DEFAULT,CALLER=lookup.CLASSIFIER,0x8009D910,0x1507E5C8
BUFFER,ALTERNATE,FACTOR_BITS=0x29000,0x2A000,0x3A83126F
INDICES=(0,1,2,5,127,128,255,256,257,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
AMOUNTS=(0,1,0xFFFFFFFF,9,10,999,1000,65535,65536,0x7FFFFFFF,0x80000000,
    16777215,16777216,16777217,(-16777217)&MASK,0x7F000001)
FACTORS=(FACTOR_BITS,0x3F000000,0xBF800000,0,0x80000000)


def fixture(index=5,factor=FACTOR,factor_bits=FACTOR_BITS,listing=BUFFER):
    memory=reset.fixture()
    for base in (BUFFER,ALTERNATE):
        for i in range(-16,272):memory[base+i]=(i*17+35)&255
    put(memory,factor,factor_bits,4)
    put(memory,(listing+((index-1)&MASK))&MASK,151,1)
    return memory


def list_reference(memory,actor,stack,return_address):
    state,events,calls=memory.copy(),[],[];frame=stack-0x18
    def get(where,size):
        assert all(where+i in state for i in range(size)),('unmapped list reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    for where,value in ((frame+0x14,return_address),(frame+0x1C,0)):
        assert all(where+i in state for i in range(4));put(state,where,value,4);events.append(('W',where,4,value))
    events.append(('CALL',CLASSIFIER,(actor,)));calls.append((CLASSIFIER,actor))
    selector=get(actor+0x1C9,1);classes=get(actor+0x2C4,4)
    identity=get(classes+(selector-1 if selector else 0),1)
    assert get(frame+0x1C,4)==0
    get(frame+0x14,4)
    return state,events,calls,DEFAULT if identity==0 else 0


def reference(memory,actor=ACTOR,index=5,amount=1000,phase=0,listing=BUFFER,
        symbols=None,mutations=None,actual_list=False,stack=None,return_address=0xDEAD0000,entry=screen.ENTRY):
    state,events,calls=memory.copy(),[],[];frame=(STACK+phase if stack is None else stack)-0x18
    helper,constructor,factor=(symbols or screen.SYMBOLS).values()
    def get(where,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(target,args):
        events.append(('CALL',target,args));calls.append((target,*args))
        for where,value,size in (mutations or {}).get(target,()):store(where,value,size)
    for offset,value in ((0x14,return_address),(0x18,actor),(0x1C,index),(0x20,amount)):store(frame+offset,value,4)
    index=get(frame+0x1C,4);actor=get(frame+0x18,4)
    if index:
        call(helper,(actor,0))
        if actual_list:
            assert helper==LIST
            state,inner,inner_calls,listing=list_reference(state,actor,frame,entry+0x2C)
            events.extend(inner);calls.extend(inner_calls)
        amount=get(frame+0x20,4)
        if listing:
            factor_bits=get(factor,4)
            index=get(frame+0x1C,4);actor=get(frame+0x18,4)
            animation=get((listing+index-1)&MASK,1)
            scaled=bits(floating(bits(signed(amount)))*floating(factor_bits))
            call(constructor,(actor,animation,scaled,0))
    get(frame+0x14,4)
    return state,events,calls


class RequestOracle(reset.ResetOracle):
    def __init__(self,words,memory,actor=ACTOR,index=5,amount=1000,phase=0,listing=BUFFER,
            symbols=None,mutations=None,actual_list=False,entry=screen.ENTRY,connected=None,arguments=None):
        args=(actor,index&MASK,amount&MASK) if arguments is None else arguments
        guest.AttachmentOracle.__init__(self,words,memory,arguments=args,phase=phase,entry=entry,connected=connected)
        helper,constructor,_=(symbols or screen.SYMBOLS).values()
        self.counts={helper:2,constructor:4,CLASSIFIER:1,lookup.screen.ENTRY:2,screen.ENTRY:3}
        self.returns={helper:listing,constructor:0x2F000};self.mutations=mutations or {}


def caller_reference(memory,amount=10,phase=0,mutations=None):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x20
    def get(where,size):
        assert all(where+i in state for i in range(size)),('unmapped caller reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size):
        assert all(where+i in state for i in range(size));value&=(1<<(size*8))-1
        put(state,where,value,size);events.append(('W',where,size,value))
    store(frame+0x14,0xDEAD0000,4);store(frame+0x24,amount,4)
    index=get(ACTOR+0x6F,1);store(frame+0x20,ACTOR,4)
    events.append(('CALL',lookup.screen.ENTRY,(ACTOR,index)));calls.append((lookup.screen.ENTRY,ACTOR,index))
    state,inner,inner_calls,definition=lookup.reference(state,actor=ACTOR,index=index,
        actual_classifier=True,stack=frame,return_address=CALLER+0x18)
    events.extend(inner);calls.extend(inner_calls);actor=get(frame+0x20,4)
    if definition:
        animation=get(definition+4,1);duration=get(definition+6,2);store(frame+0x20,actor,4);store(frame+0x1C,definition,4)
        events.append(('CALL',screen.ENTRY,(actor,animation,duration)));calls.append((screen.ENTRY,actor,animation,duration))
        state,inner,inner_calls=reference(state,actor=actor,index=animation,amount=duration,actual_list=True,
            stack=frame,return_address=CALLER+0x34,mutations=mutations)
        events.extend(inner);calls.extend(inner_calls)
        definition=get(frame+0x1C,4);actor=get(frame+0x20,4);amount=get(frame+0x24,4)
        desired=get(definition+2,1);current=get(actor+0x134,1)
        if desired!=current:
            store(actor+0x134,desired,1)
            store(actor+0x135,get(definition+3,1) if amount==0 else amount,1)
        store(actor+0x6C,get(definition,1)+10,1);store(actor+0x6D,get(definition+1,1)+10,1)
        for record_offset,actor_offset,header_offset in ((8,0x68,0x3B),(9,0x69,0x3C)):
            value=get(definition+record_offset,1)
            if not value:
                kind=get(actor+4,1);archive=get(lookup.TABLE+kind*4,4);value=get(archive+header_offset,1)
            store(actor+actor_offset,value,1)
    get(frame+0x14,4)
    return state,events,calls


class GameActorAnimationRequestMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-actor-animation-request-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.selected=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>30I',cls.rom,screen.ROM))
        assert cls.original==cls.selected
        body=(cls.root/'conker/asm/AB760.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        before=(cls.out/'before-elf').read_bytes();cls.helpers={}
        for address,words,rom in ((LIST,19,0xABEA8),(CLASSIFIER,11,0xB1E50),
                (lookup.screen.ENTRY,24,lookup.screen.ROM),(CALLER,60,0xABA78)):
            code=list(struct.unpack_from('>%dI'%words,before,elf_slot_offset(before,address,words*4)))
            assert code==list(struct.unpack_from('>%dI'%words,cls.rom,rom));cls.helpers[address]=code
        cls.default=before[elf_slot_offset(before,DEFAULT,5):][:5];assert cls.default==bytes((5,6,7,10,11))
        assert struct.unpack_from('>I',before,elf_slot_offset(before,FACTOR,4))[0]==FACTOR_BITS

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def helper_code(self,addresses):
        return {address+i*4:w for address in addresses for i,w in enumerate(self.helpers[address])}

    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings)
        connected=self.helper_code((LIST,CLASSIFIER)) if settings.get('actual_list') else None
        models=[RequestOracle(words,memory,connected=connected,**settings).run() for words in
            (forms or (self.original,self.selected))]
        for model in models:self.assertEqual((model.memory,model.events,model.calls),expected)
        return models

    def test_01_complete_direct_shape_profile_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(30,24,0,0,''))
        self.assertEqual(self.meta['relocations'],{36:[('R_MIPS_26','func_1507E9F8')],
            56:[('R_MIPS_HI16','D_8009B8A0')],60:[('R_MIPS_LO16','D_8009B8A0')],
            96:[('R_MIPS_26','func_15083568')]})
        self.receipt('shape',words=30,frame=24,guards=0,insertions=0,omissions=0,
            normal_O2_g3=True,diagnostics=0,pool_bytes=0,all_words_from_complete_C=True)

    def test_02_full_word_index_signed_scale_RNE_bits_and_live_reload_order(self):
        cases=0;coverage=set()
        for index,amount,present,factor_bits,phase,plan in itertools.product(INDICES,AMOUNTS,
                (False,True),FACTORS,(0,8),range(4)):
            memory=fixture(index=index,factor_bits=factor_bits);mutations={}
            if plan==1:mutations={LIST:((STACK+phase+4,1,4),(STACK+phase+8,MASK,4),
                (STACK+phase,reset.ALTERNATE,4),(FACTOR,0x3F000000,4))}
            if plan==2:mutations={LIST:(((BUFFER+index-1)&MASK,254,1),(FACTOR,0xBF800000,4))}
            if plan==3:mutations={CONSTRUCTOR:((FACTOR,0,4),(ACTOR+0x6F,9,1))}
            models=self.compare(memory,index=index,amount=amount,listing=BUFFER if present else 0,
                phase=phase,mutations=mutations);coverage.update(models[0].visits);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+120,4)))
        self.compare(fixture(),actor=0,index=0)
        self.receipt('guest',cases=cases+1,executions=(cases+1)*2,retail_words_reached=30,
            independent_full_private_order=True,full_index_and_amount_word_bits=True,typed_mixed_O32_A2_float_bits=True,
            signed_conversion_then_single_multiply=True,RNE_finite_normal_or_zero_factors_only=True,
            live_actor_index_amount_and_factor_after_callback=True,void_V0_not_compared=True,
            caller_GP_FPR_clobbered=True,extreme_indices_not_portable_native_C=True,FCSR_not_emulated=True)

    @classmethod
    def link(cls,name,entry,symbols):
        script=cls.out/('link-%s-%X-%X.ld'%(name,entry,symbols['D_8009B8A0']));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>30I',sections(elf)['.text'][1]))

    def test_03_actual_list_private_aliases_and_strict_fault_prefixes(self):
        cases=prefixes=0
        for identity,selector,index,amount,phase in itertools.product((0,3),(0,1,2,128,255),
                (0,1,5),(0,65535,0x80000000,0x7FFFFFFF),(0,8)):
            memory=lookup.fixture(identity,selector=selector);put(memory,FACTOR,FACTOR_BITS,4)
            for i,value in enumerate(self.default):put(memory,DEFAULT+i,value,1)
            self.compare(memory,index=index,amount=amount,phase=phase,actual_list=True);cases+=1
        for phase,mode,index in itertools.product((0,8),range(4),(0,1,5)):
            factor=STACK+phase+8 if mode==1 else ACTOR+4 if mode==2 else FACTOR
            listing=STACK+phase-4 if mode==3 else BUFFER
            memory=fixture(index,factor,FACTOR_BITS,listing)
            symbols=dict(screen.SYMBOLS,D_8009B8A0=factor)
            forms=tuple(self.link(name,screen.ENTRY,symbols) for name in ('original','selected'))
            settings=dict(index=index,amount=0x3F000000 if mode==1 else 1000,phase=phase,listing=listing,symbols=symbols)
            models=self.compare(memory,forms=forms,**settings);cases+=1
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in forms:
                    model=RequestOracle(words,memory,**settings);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                for name in ('memory','events','calls','f'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                prefixes+=1
        missing=[];memory=fixture()
        for words in (self.original,self.selected):
            model=RequestOracle(words,memory,actor=0,index=1,connected=self.helper_code((LIST,CLASSIFIER)))
            with self.assertRaises(AssertionError) as caught:model.run()
            self.assertEqual(caught.exception.args,(('unmapped read',0x1C9,1),));missing.append(model)
        for name in ('memory','events','calls','accesses'):self.assertEqual(getattr(missing[0],name),getattr(missing[1],name))
        self.receipt('aliases-list',cases=cases,executions=cases*2,fired_fault_pairs=prefixes,failed_executions=prefixes*2,
            actual_list_words=19,actual_classifier_words=11,actual_default_bytes=self.default.hex(),
            zero_index_null_actor_allowed=True,nonnull_index_null_actor_failed_executions=2,
            private_amount_factor_and_saved_RA_byte_aliases=True,FP_register_fault_prefixes_compared=True,
            list_output_NULL_context_only=True,guest_fault_not_portable_C=True)

    def test_04_independent_JAL_HI_LO_carry_and_mixed_argument_rebases(self):
        cases=0
        for entry,helper,constructor,factor in ((screen.ENTRY,LIST,CONSTRUCTOR,FACTOR),
                (0x15207FFC,0x15217FFC,0x15228004,0x80117FFC),
                (0x15308004,0x15318004,0x15327FFC,0x80118004),
                (0x15417FFC,0x15428004,0x15437FFC,0x80227FF0)):
            symbols=dict(zip(screen.SYMBOLS,(helper,constructor,factor)))
            forms=tuple(self.link(name,entry,symbols) for name in ('selected','original'));self.assertEqual(forms[0],forms[1])
            for index,amount,present,phase in itertools.product((0,1,256),
                    (1,0xFFFFFFFF,0x7FFFFFFF,0x80000000),(False,True),(0,8)):
                self.compare(fixture(index,factor),forms=forms,index=index,amount=amount,phase=phase,
                    listing=BUFFER if present else 0,symbols=symbols,entry=entry);cases+=1
        self.receipt('rebases',independent_links=8,cases=cases,executions=cases*2,
            both_JALs_and_factor_independent=True,signed_LO_carry_boundaries=True,guards=0)

    def test_05_copied_owner_actual_padding_and_all_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True);objects.append(obj)
        self.assertEqual(warnings,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        padded=[]
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AB760',str(assembly),
                '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True);padded.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(padded[0],padded[1])
        self.receipt('owner',neighbors=len(padded[0][1])-1,diagnostics=0,
            all_actual_padded_bytes_extents_relocations_equal=True,pools_equal=True,no_new_guards=True)

    def test_06_effective_complete_IDO_negative_controls(self):
        controls=(('byte-index','s32 index','u8 index',dict(index=256)),
            ('wrong-offset','(u32)index - 1','(u32)index',{}),
            ('unsigned-amount','(f32)amount','(f32)(u32)amount',dict(amount=MASK)),
            ('float-input','s32 amount','f32 amount',{}),
            ('wrong-mode','D_8009B8A0, 0','D_8009B8A0, 1',{}),
            ('truncate-scale','(f32)amount * D_8009B8A0','(f32)(s32)((f32)amount * D_8009B8A0)',dict(amount=1)),
            ('cached-factor','D_8009B8A0','0.001f',dict(factor_bits=0x3F000000)))
        for name,old,new,case in controls:
            settings={k:v for k,v in case.items() if k!='factor_bits'}
            memory=fixture(case.get('index',5),factor_bits=case.get('factor_bits',FACTOR_BITS))
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            for section,(address,data) in sections(self.out/('negative-'+name+'.elf')).items():
                if section in ('.rodata','.data'):
                    for offset,value in enumerate(data):memory[address+offset]=value
            wrong=RequestOracle(words,memory,**settings).run();expected=reference(memory,**settings)
            self.assertNotEqual(wrong.calls,expected[2],name)
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls))

    def test_07_native32_complete_C_signed_integer_float_bridge_and_live_callbacks(self):
        source=NATIVE+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-unsigned','(f32)amount','(f32)(u32)amount'),
                ('native-offset','(u32)index - 1','(u32)index')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=257*16*2*4+131072*3*2,
            all_low_signed_amounts_and_full_word_rounding_boundaries=True,valid_one_based_synthetic_indices=True,
            float_packet_bits_and_typed_callbacks=True,actor_lists_factor_compared=True,live_callback_changes=True,
            effective_native_negatives=2,RNE_no_FCSR_trap_claim=True)

    def test_08_actual_record_caller_lookup_classifier_list_and_live_record_updates(self):
        cases=prefixes=0;coverage=set();presence=((False,True),(True,False),(True,True))
        connected=self.helper_code((LIST,CLASSIFIER,lookup.screen.ENTRY))
        for identity,descriptor,duration,amount,equal,overrides,present,phase,plan in itertools.product(
                (0,3),(0,1,5),(0,65535),(0,1,MASK),(False,True),range(4),presence,(0,8),(0,1)):
            archive_present,records_present=present
            memory=count.fixture(identity=identity,present=archive_present,selector=255 if phase else 0,
                record_base=reset.RESOURCE-7*10)
            if not records_present:put(memory,count.ARCHIVE-8,0,4)
            for offset,value,size in ((0,255 if equal else 249,1),(1,248,1),(2,7,1),(3,253,1),
                    (4,descriptor,1),(6,duration,2),(8,127 if overrides&1 else 0,1),(9,128 if overrides&2 else 0,1)):
                put(memory,reset.RESOURCE+offset,value,size)
            put(memory,ACTOR+0x6F,7,1);put(memory,ACTOR+0x134,7 if equal else 2,1)
            put(memory,FACTOR,FACTOR_BITS,4)
            for i,value in enumerate(self.default):put(memory,DEFAULT+i,value,1)
            put(memory,count.ARCHIVE+0x3B,129,1);put(memory,count.ARCHIVE+0x3C,254,1)
            mutations={}
            if plan:mutations={CONSTRUCTOR:((reset.RESOURCE+2,6,1),(ACTOR+0x134,5,1),
                (reset.RESOURCE,255,1),(reset.RESOURCE+1,248,1),(reset.RESOURCE+8,0,1),(reset.RESOURCE+9,0,1),
                (count.ARCHIVE+0x3B,255,1),(count.ARCHIVE+0x3C,127,1),(STACK+phase+4,0xABCDEF11,4))}
            expected=caller_reference(memory,amount=amount,phase=phase,mutations=mutations);models=[]
            for words in (self.original,self.selected):
                code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                model=RequestOracle(self.helpers[CALLER],memory,arguments=(ACTOR,amount),entry=CALLER,
                    phase=phase,connected=code,mutations=mutations).run()
                self.assertEqual((model.memory,model.events,model.calls),expected);models.append(model);coverage.update(model.visits)
            if descriptor==5 and duration==65535 and amount==1 and not equal and overrides==0 and present==(True,True):
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.selected):
                        code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                        model=RequestOracle(self.helpers[CALLER],memory,arguments=(ACTOR,amount),entry=CALLER,
                            phase=phase,connected=code,mutations=mutations);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    for name in ('memory','events','calls','f'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                    prefixes+=1
            cases+=1
        self.assertEqual(coverage&set(range(CALLER,CALLER+240,4)),{CALLER+i*4 for i in range(60) if i not in (37,49)})
        self.receipt('caller',cases=cases,executions=cases*2,caller_words=60,reachable_caller_words=58,
            actual_request_lookup_list_classifier_and_default_data=True,independent_full_private_reference=True,
            fired_fault_pairs=prefixes,failed_executions=prefixes*2,live_record_and_parent_argument_rereads=True,
            constructor_body_still_placeholder_and_bounded=True,hardware_gameplay_not_claimed=True)

    def test_09_whole_linked_ELF_one_conversion_row_and_no_guard_change(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text();before_source=(self.out/'before-source').read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('installation',installed=False);return
        self.assertEqual(source,screen.install(before_source))
        for name in ('guards','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes();actual=(self.root/self.paths['elf']).read_bytes()
        self.assertEqual(metadata(before)[:4],metadata(actual)[:4]);self.assertEqual(before,actual)
        old=list(csv.reader((self.out/'before-progress').read_text().splitlines()))
        indices=[i for i,row in enumerate(old) if row[3]==screen.FUNCTION];self.assertEqual(len(indices),1)
        index=indices[0];self.assertEqual(old[index][5:],['120','asm']);new=[row.copy() for row in old];new[index][6]='c'
        self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),new)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,whole_ELF_byte_identical=True,all_addresses_extents_symbols_exact=True,
            only_conversion_row=screen.FUNCTION,converted_bytes_added=120,guards_and_symbol_files_byte_identical=True,protected_data=audit)


NATIVE=r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;typedef float f32;
static u8 actor[812],savedActor[812],listing[257],alternate[257];
f32 D_8009B8A0;static int indexValue,plan,present,errors,lists,requests;static u32 packet[4];
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(f32)==4)?1:-1];
static u32 word(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static f32 real(void){union{f32 f;u32 u;}v;v.u=0x3A83126F;return v.f;}
u8 *func_1507E9F8(u8 *a,s32 *out){if(a!=actor || out)errors=1;lists++;
    if(plan==1)actor[0x6F]=129;
    if(plan==2){listing[indexValue-1]=151;D_8009B8A0=0.5f;}
    return present?(plan==1?alternate:listing):0;}
u8 *func_15083568(u8 *a,s32 animation,f32 scale,s32 mode){requests++;
    packet[0]=(u32)a;packet[1]=animation;packet[2]=word(scale);packet[3]=mode;
    if(plan==3){D_8009B8A0=0;actor[0x71]=7;}return actor;}
'''
NATIVE_RUNNER=r'''
static int qualify(int index,s32 amount,int available,int mutation){
    int i,active=index && available;u8 expectedByte;volatile f32 converted,scaled;u32 expectedScale;
    indexValue=index;present=available;plan=mutation;errors=lists=requests=0;D_8009B8A0=real();
    for(i=0;i<812;i++)actor[i]=savedActor[i]=(u8)(i*17+35);
    for(i=0;i<257;i++){listing[i]=(u8)(i*17+35);alternate[i]=(u8)(i*19+51);}
    for(i=0;i<4;i++)packet[i]=0;
    expectedByte=index?(plan==1?alternate[index-1]:plan==2?151:listing[index-1]):0;
    converted=amount;scaled=converted*(index && plan==2?0.5f:real());expectedScale=word(scaled);
    func_1507EA44(actor,index,amount);
    if(errors || lists!=!!index || requests!=active)return 1;
    if(active && (packet[0]!=(u32)actor || packet[1]!=expectedByte || packet[2]!=expectedScale || packet[3]))return 2;
    if(index && plan==1)savedActor[0x6F]=129;
    if(active && plan==3)savedActor[0x71]=7;
    for(i=0;i<812;i++)if(actor[i]!=savedActor[i])return 3;
    for(i=0;i<257;i++)if(listing[i]!=(u8)(index && plan==2 && i==index-1?151:i*17+35) || alternate[i]!=(u8)(i*19+51))return 4;
    if(word(D_8009B8A0)!=word(active && plan==3?0:index && plan==2?0.5f:real()))return 5;
    return 0;
}
int run(void){int index,a,p,plan,r;const s32 amounts[16]={0,1,-1,9,10,999,1000,65535,65536,2147483647,
    (-2147483647-1),16777215,16777216,16777217,-16777217,0x7F000001};
    for(index=0;index<=256;index++)for(a=0;a<16;a++)for(p=0;p<2;p++)for(plan=0;plan<4;plan++){
        r=qualify(index,amounts[a],p,plan);if(r)return r;}
    for(a=-65536;a<65536;a++)for(index=0;index<3;index++)for(p=0;p<2;p++){
        r=qualify(index==0?0:index==1?1:5,a,p,0);if(r)return r;}
    return 0;}
'''


if __name__=='__main__':unittest.main()
