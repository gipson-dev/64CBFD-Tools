"""Complete count helper, actual count/lookup/classifier chain and linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_actor_definition_count_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_definition_lookup_match as lookup
from tools.tests import test_game_actor_channel_transition_match as transition
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,MASK=lookup.STACK,lookup.ACTOR,lookup.MASK
CLASSIFIER,TABLE=screen.SYMBOLS.values()
ARCHIVE,ALTERNATE=0x2C008,0x2D008
SIZES=(0,1,8,9,10,11,19,20,79,80,89,90,970,65535,65536,0x7FFFFFFF,
    0x80000000,0x80000001,0xFFFFFFF0,0xFFFFFFFE,0xFFFFFFFF)


def fixture(kind=0,identity=3,size=970,present=True,selector=0,actor=ACTOR,
        table=TABLE,archive=ARCHIVE,record_base=lookup.RECORDS):
    memory=lookup.fixture(identity,present,True,selector,actor,table,record_base,archive)
    for base in (ARCHIVE-8,ALTERNATE-8):
        for i in range(64):memory.setdefault(base+i,0xA5)
    put(memory,archive-4,size,4);put(memory,ALTERNATE-4,1110,4)
    put(memory,table+150*4,archive if present else 0,4)
    put(memory,actor+4,kind,1)
    return memory


def reference(memory,actor=ACTOR,identity=3,phase=0,table=TABLE,classifier=CLASSIFIER,
        actual_classifier=False,mutations=None,stack=None,return_address=0xDEAD0000,entry=screen.ENTRY):
    state,events,calls=memory.copy(),[],[];frame=(STACK+phase if stack is None else stack)-0x18
    def get(where,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    store(frame+0x14,return_address,4);kind=get(actor+4,1)
    if kind==150:identity=150
    else:
        events.append(('CALL',classifier,(actor,)));calls.append((classifier,actor))
        if actual_classifier:
            selector=get(actor+0x1C9,1);classes=get(actor+0x2C4,4)
            identity=get(classes+(selector-1 if selector else 0),1)
        else:
            for where,value,size in mutations or ():store(where,value,size)
    get(frame+0x14,4);result=0
    if identity!=255:
        archive=get(table+((identity*4)&MASK),4)
        if archive:result=get(archive-4,4)//10
    return state,events,calls,result


class CountOracle(lookup.DefinitionOracle):
    def __init__(self,words,memory,actor=ACTOR,identity=3,phase=0,table=TABLE,
            classifier=CLASSIFIER,actual_classifier=False,mutations=None,entry=screen.ENTRY,connected=None):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(actor,),phase=phase,entry=entry,connected=connected)
        self.classifier=classifier;self.identity=identity;self.mutations=mutations or ()
    def execute(self,word):
        if word>>26==0 and word&63==27:
            numerator=self.r[word>>21&31]&MASK;denominator=self.r[word>>16&31]&MASK
            assert denominator,'zero divisor outside this helper contract'
            self.lo=numerator//denominator
        else:super().execute(word)


class GameActorDefinitionCountMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-actor-definition-count-test'
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
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>32I',cls.rom,screen.ROM))
        assert cls.original==cls.selected
        body=(cls.root/'conker/asm/AB760.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        before=(cls.out/'before-elf').read_bytes()
        cls.classifier=list(struct.unpack_from('>11I',before,elf_slot_offset(before,CLASSIFIER,44)))
        assert cls.classifier==list(struct.unpack_from('>11I',cls.rom,0xB1E50))
        cls.caller=list(struct.unpack_from('>73I',before,elf_slot_offset(before,transition.screen.ENTRY,292)))
        assert cls.caller==list(struct.unpack_from('>73I',cls.rom,transition.screen.ROM))
        cls.definition=list(struct.unpack_from('>24I',before,elf_slot_offset(before,lookup.screen.ENTRY,96)))
        assert cls.definition==list(struct.unpack_from('>24I',cls.rom,lookup.screen.ROM))

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings)
        connected={CLASSIFIER+i*4:w for i,w in enumerate(self.classifier)} if settings.get('actual_classifier') else None
        models=[CountOracle(words,memory,connected=connected,**settings).run() for words in
            (forms or (self.original,self.selected))]
        for model in models:self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected)
        return models

    def test_01_complete_direct_shape_profile_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(32,24,0,0,''))
        self.assertEqual(self.meta['relocations'],{24:[('R_MIPS_26','func_150849A0')],
            68:[('R_MIPS_HI16','D_800D1C90')],76:[('R_MIPS_LO16','D_800D1C90')]})
        self.receipt('shape',words=32,frame=24,guards=0,insertions=0,omissions=0,
            all_words_from_complete_C=True,normal_O2_g3=True,diagnostics=0,pool_bytes=0)

    def test_02_unsigned_boundaries_all_actor_and_class_bytes_live_callbacks(self):
        cases=0;coverage=set()
        settings=[]
        settings.extend(itertools.product(range(256),(3,150,255),(10,0xFFFFFFFF),(False,True),(0,8),(0,)))
        settings.extend(itertools.product((0,150),range(256),(970,0xFFFFFFFF),(False,True),(0,8),(0,1)))
        settings.extend(itertools.product((0,150),(0,255,0x40000001,0xFFFFFFFF),SIZES,
            (False,True),(0,8),(0,1,2)))
        for kind,identity,size,present,phase,plan in settings:
            memory=fixture(kind,identity,size,present);slot=(TABLE+((identity*4)&MASK))&MASK
            mutations=()
            if plan==1:mutations=((slot,ALTERNATE,4),(ACTOR+4,150,1))
            if plan==2:mutations=((ARCHIVE-4,0xFFFFFFFF,4),(ACTOR+0x1C9,255,1))
            models=self.compare(memory,identity=identity,phase=phase,mutations=mutations)
            coverage.update(models[0].visits);cases+=1
        self.assertEqual(coverage,{screen.ENTRY+i*4 for i in range(32) if i!=10})
        self.receipt('guest',cases=cases,executions=cases*2,retail_words=32,reachable_words=31,
            original_dead_move_not_falsely_counted=True,all_actor_and_classifier_bytes=True,
            full_word_classifier_carriers_and_unsigned_division=True,independent_full_private_order=True,
            special_case_skips_callback=True,live_table_and_header_after_callback=True,
            caller_GP_FPR_clobbered=True,scalar_return_compared=True)

    @classmethod
    def link(cls,name,entry,classifier,table):
        script=cls.out/('link-%s-%X-%X-%X.ld'%(name,entry,classifier,table));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=func_150849A0=0x%X'%classifier,'--defsym=D_800D1C90=0x%X'%table,
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>32I',sections(elf)['.text'][1]))

    def test_03_actual_classifier_private_aliases_and_strict_fault_prefixes(self):
        cases=prefixes=0;coverage=set()
        for selector,identity,kind,size,present,phase in itertools.product((0,1,2,128,255),
                (0,150,255),(0,150),(9,10,0xFFFFFFFF),(False,True),(0,8)):
            models=self.compare(fixture(kind,identity,size,present,selector),identity=identity,
                phase=phase,actual_classifier=True);cases+=1;coverage.update(models[0].visits)
        self.assertEqual(coverage&set(range(CLASSIFIER,CLASSIFIER+44,4)),
            {CLASSIFIER+i*4 for i in range(11) if i!=7})
        for phase,mode,kind in itertools.product((0,8),range(5),(0,150)):
            actor=STACK+phase-8 if mode==4 else ACTOR
            archive=STACK+phase if mode==1 else actor+8 if mode==3 else ARCHIVE
            table=STACK+phase-4 if mode==2 else TABLE
            memory=fixture(kind,0,970,True,actor=actor,table=table,archive=archive)
            put(memory,0xDEAD0000-4,1110,4)
            forms=tuple(self.link(name,screen.ENTRY,CLASSIFIER,table) for name in ('original','selected'))
            settings=dict(actor=actor,identity=0,phase=phase,table=table)
            models=self.compare(memory,forms=forms,**settings);cases+=1
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in forms:
                    model=CountOracle(words,memory,**settings);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                prefixes+=1
        self.receipt('aliases-classifier',cases=cases,executions=cases*2,fired_fault_pairs=prefixes,
            failed_executions=prefixes*2,actual_classifier_words=11,reachable_classifier_words=10,
            actor_header_saved_RA_and_table_aliases=True,strict_fault_prefixes=True,
            not_portable_C_fault_semantics=True)

    def test_04_independent_JAL_HI_LO_carry_and_division_rebases(self):
        cases=0
        for entry,classifier,table in ((screen.ENTRY,CLASSIFIER,TABLE),
                (0x15207FFC,0x15218004,0x80117FFC),(0x15308004,0x15327FFC,0x80118004),
                (0x15417FFC,0x15428004,0x80227FF0)):
            forms=tuple(self.link(name,entry,classifier,table) for name in ('selected','original'))
            self.assertEqual(forms[0],forms[1])
            for kind,identity,size,present,phase in itertools.product((0,150),(0,255),
                    (9,10,0x80000000,0xFFFFFFFF),(False,True),(0,8)):
                self.compare(fixture(kind,identity,size,present,table=table),forms=forms,entry=entry,
                    classifier=classifier,table=table,identity=identity,phase=phase);cases+=1
        self.receipt('rebases',independent_links=8,cases=cases,executions=cases*2,
            entry_JAL_and_table_independent=True,signed_LO_carry_boundaries=True,guards=0)

    def test_05_copied_owner_actual_padding_and_all_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True);objects.append(obj)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        padded=[]
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AB760',str(assembly),
                '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True);padded.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(padded[0],padded[1]);self.assertEqual(warnings[0],[])
        self.receipt('owner',neighbors=len(padded[0][1])-1,diagnostics=0,
            all_actual_padded_bytes_extents_relocations_equal=True,pools_equal=True,no_new_guards=True)

    def test_06_effective_complete_IDO_negative_controls(self):
        controls=(('special','!= 150','!= 149',dict(kind=150,identity=7)),
            ('sentinel','== 255','== 254',dict(identity=255)),
            ('signed-size','*(u32 *)','*(s32 *)',dict(size=0xFFFFFFFF)),
            ('stride','/ 10','/ 8',{}),('header','archive + 4','archive + 0',{}),
            ('byte-classifier','s32 identity','u8 identity',dict(identity=256)))
        for name,old,new,case in controls:
            memory=fixture(**case);put(memory,TABLE+7*4,ALTERNATE,4);put(memory,TABLE,ALTERNATE,4)
            # Wrong special handling and narrowing must observe a different live slot.
            if not case:put(memory,TABLE+3*4,ARCHIVE,4)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            settings=dict(identity=case.get('identity',3))
            wrong=CountOracle(words,memory,**settings).run();expected=reference(memory,**settings)
            self.assertNotEqual(wrong.r[2],expected[3],name)
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls))

    def test_07_native32_complete_C_full_domains_unsigned_sizes_and_live_table(self):
        source=NATIVE+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-signed','*(u32 *)','*(s32 *)'),('native-special','!= 150','!= 149')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=256*256*4*2*3+65536*2*2,
            all_actor_classifier_byte_pairs=True,all_low_halfword_sizes_and_unsigned_high_boundaries=True,
            live_table_and_header_mutations=True,full_actor_table_header_compared=True,
            typed_single_argument_ABI=True,effective_native_negatives=2,synthetic_assets_only=True)

    def test_08_actual_channel_count_definition_classifier_and_fault_prefixes(self):
        entry=transition.screen.ENTRY;cases=prefixes=0
        class Caller(transition.TransitionOracle):
            def execute(model,word):
                if word>>26==0 and word&63==27:
                    numerator=model.r[word>>21&31]&MASK;denominator=model.r[word>>16&31]&MASK
                    assert denominator,'zero divisor outside this helper contract'
                    model.lo=numerator//denominator
                else:super().execute(word)
            def record_call(model,target):
                if target==CLASSIFIER:
                    args=model.arguments(1);model.calls.append((target,*args));model.events.append(('CALL',target,args))
                else:super().record_call(target)
        for channel,size,kind,identity,priority,present,descriptor,phase in itertools.product((0,8,255),
                (0,79,80,89,90,2560,0xFFFFFFFF),(0,150),(3,255),(0,3),(False,True),(0,7),(0,8)):
            memory=transition.fixture(descriptor=descriptor)
            selector=255 if phase else 0
            extra=fixture(kind,identity,size,present,selector,record_base=transition.RESOURCE-7*10)
            for where,value in extra.items():
                if TABLE-16<=where<TABLE+1040 or lookup.CLASS_LIST<=where<lookup.CLASS_LIST+256 or ARCHIVE-8<=where<ARCHIVE+56:
                    memory[where]=value
            put(memory,ACTOR+4,kind,1);put(memory,ACTOR+0x1C9,selector,1);put(memory,ACTOR+0x2C4,lookup.CLASS_LIST,4)
            count=size//10 if present and (kind==150 or identity!=255) else 0
            expected=transition.reference(memory,channel=channel,priority=priority,count=count,phase=phase)
            state=memory.copy();put(state,STACK+phase+0x10,10,4);events=[];calls=[]
            for event in expected[1]:
                events.append(event)
                if event[0]=='W':put(state,event[1],event[3],event[2])
                elif event[0]=='R':self.assertEqual(read(state,event[1],event[2]),event[3])
                else:
                    target,args=event[1:];calls.append((target,*args))
                    if target==screen.ENTRY:
                        state,inner,inner_calls,result=reference(state,actor=args[0],actual_classifier=True,
                            stack=STACK+phase-0x30,return_address=entry+0x98)
                        self.assertEqual(result,count);events.extend(inner);calls.extend(inner_calls)
                    if target==lookup.screen.ENTRY:
                        state,inner,inner_calls,result=lookup.reference(state,actor=args[0],index=args[1],
                            actual_classifier=True,stack=STACK+phase-0x30,return_address=entry+0xB4)
                        self.assertEqual(result,transition.RESOURCE);events.extend(inner);calls.extend(inner_calls)
            for words in (self.original,self.selected):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({CLASSIFIER+i*4:w for i,w in enumerate(self.classifier)})
                connected.update({lookup.screen.ENTRY+i*4:w for i,w in enumerate(self.definition)})
                model=Caller(self.caller,memory,channel=channel,priority=priority,count=count,phase=phase,connected=connected).run()
                self.assertEqual((model.memory,model.events,model.calls),(state,events,calls))
                if words is self.original and channel==8 and size==90 and priority==3 and present and descriptor==7:
                    for ordinal in range(model.accesses):
                        failed=[]
                        for body in (self.original,self.selected):
                            code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(body)})
                            fault=Caller(self.caller,memory,channel=channel,priority=priority,count=count,phase=phase,connected=code)
                            fault.fault=ordinal
                            with self.assertRaises(guest.AccessFault) as caught:fault.run()
                            self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(fault.accesses,ordinal);failed.append(fault)
                        for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                        prefixes+=1
            cases+=1
        self.receipt('caller',cases=cases,executions=cases*2,caller_words=73,count_words=32,definition_words=24,classifier_words=11,
            independent_replayed_full_private_reference=True,fired_connected_fault_pairs=prefixes,
            failed_executions=prefixes*2,actual_strict_count_gate=True,deeper_list_animation_finish_bounded=True,
            other_complete_callers_not_executed=True)

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
        index=indices[0];self.assertEqual(old[index][5:],['128','asm']);new=[row.copy() for row in old];new[index][6]='c'
        self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),new)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,whole_ELF_byte_identical=True,all_addresses_extents_symbols_exact=True,
            only_conversion_row=screen.FUNCTION,converted_bytes_added=128,guards_and_symbol_files_byte_identical=True,protected_data=audit)

    def test_10_actual_list_and_default_animation_bytes_in_complete_caller(self):
        list_entry,default=0x1507E9F8,0x8009D910;entry=transition.screen.ENTRY;cases=prefixes=0
        before=(self.out/'before-elf').read_bytes()
        listing=list(struct.unpack_from('>19I',before,elf_slot_offset(before,list_entry,76)))
        self.assertEqual(listing,list(struct.unpack_from('>19I',self.rom,0xABEA8)))
        data=before[elf_slot_offset(before,default,5):][:5];self.assertEqual(data,bytes((5,6,7,10,11)))
        class Caller(transition.TransitionOracle):
            def execute(model,word):
                if word>>26==0 and word&63==27:
                    numerator=model.r[word>>21&31]&MASK;denominator=model.r[word>>16&31]&MASK
                    assert denominator;model.lo=numerator//denominator
                else:super().execute(word)
            def record_call(model,target):
                if target==CLASSIFIER:
                    args=model.arguments(1);model.calls.append((target,*args));model.events.append(('CALL',target,args))
                else:super().record_call(target)
        def list_reference(memory,actor,stack,return_address):
            state,events,calls=memory.copy(),[],[];frame=stack-0x18
            def get(where,size):
                self.assertTrue(all(where+i in state for i in range(size)))
                value=read(state,where,size);events.append(('R',where,size,value));return value
            for where,value in ((frame+0x14,return_address),(frame+0x1C,0)):
                self.assertTrue(all(where+i in state for i in range(4)));put(state,where,value,4)
                events.append(('W',where,4,value))
            events.append(('CALL',CLASSIFIER,(actor,)));calls.append((CLASSIFIER,actor))
            selector=get(actor+0x1C9,1);classes=get(actor+0x2C4,4)
            identity=get(classes+(selector-1 if selector else 0),1)
            self.assertEqual(get(frame+0x1C,4),0)
            result=default if identity==0 else 0;get(frame+0x14,4)
            return state,events,calls,result
        # Only this sequential reference invocation changes its animation base.
        with patch.object(transition,'ANIMATIONS',default):
            for channel,size,kind,identity,descriptor,present,phase in itertools.product((0,8,255),
                    (0,90,2560),(0,150),(0,3),(0,1,5),(False,True),(0,8)):
                memory=transition.fixture(descriptor=descriptor)
                extra=fixture(kind,identity,size,present,record_base=transition.RESOURCE-7*10)
                for where,value in extra.items():
                    if TABLE-16<=where<TABLE+1040 or lookup.CLASS_LIST<=where<lookup.CLASS_LIST+256 or ARCHIVE-8<=where<ARCHIVE+56:
                        memory[where]=value
                put(memory,ACTOR+4,kind,1);put(memory,ACTOR+0x1C9,0,1);put(memory,ACTOR+0x2C4,lookup.CLASS_LIST,4)
                for i,value in enumerate(data):put(memory,default+i,value,1)
                count=size//10 if present else 0
                expected=transition.reference(memory,channel=channel,priority=3,count=count,phase=phase,list_present=identity==0)
                state=memory.copy();put(state,STACK+phase+0x10,10,4);events=[];calls=[]
                for event in expected[1]:
                    events.append(event)
                    if event[0]=='W':put(state,event[1],event[3],event[2])
                    elif event[0]=='R':self.assertEqual(read(state,event[1],event[2]),event[3])
                    else:
                        target,args=event[1:];calls.append((target,*args))
                        if target==screen.ENTRY:
                            state,inner,inner_calls,result=reference(state,actor=args[0],actual_classifier=True,
                                stack=STACK+phase-0x30,return_address=entry+0x98)
                            self.assertEqual(result,count);events.extend(inner);calls.extend(inner_calls)
                        elif target==lookup.screen.ENTRY:
                            state,inner,inner_calls,result=lookup.reference(state,actor=args[0],index=args[1],
                                actual_classifier=True,stack=STACK+phase-0x30,return_address=entry+0xB4)
                            self.assertEqual(result,transition.RESOURCE);events.extend(inner);calls.extend(inner_calls)
                        elif target==list_entry:
                            self.assertEqual(args,(ACTOR,0))
                            state,inner,inner_calls,result=list_reference(state,ACTOR,STACK+phase-0x30,entry+0xD0)
                            self.assertEqual(result,default if identity==0 else 0);events.extend(inner);calls.extend(inner_calls)
                models=[]
                for words in (self.original,self.selected):
                    connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                    for address,body in ((CLASSIFIER,self.classifier),(lookup.screen.ENTRY,self.definition),(list_entry,listing)):
                        connected.update({address+i*4:w for i,w in enumerate(body)})
                    model=Caller(self.caller,memory,channel=channel,priority=3,count=count,phase=phase,
                        list_present=identity==0,connected=connected).run()
                    self.assertEqual((model.memory,model.events,model.calls),(state,events,calls));models.append(model)
                if channel==8 and size==90 and descriptor==5 and present:
                    for ordinal in range(models[0].accesses):
                        failed=[]
                        for words in (self.original,self.selected):
                            code=connected.copy();code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                            model=Caller(self.caller,memory,channel=channel,priority=3,count=count,phase=phase,
                                list_present=identity==0,connected=code);model.fault=ordinal
                            with self.assertRaises(guest.AccessFault) as caught:model.run()
                            self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                        for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                        prefixes+=1
                cases+=1
        self.receipt('actual-list-chain',cases=cases,executions=cases*2,list_words=19,default_data_hex=data.hex(),
            actual_count_lookup_classifier_list_and_default_bytes=True,fired_fault_pairs=prefixes,failed_executions=prefixes*2,
            list_output_NULL_context_only=True,animation_and_finish_bodies_still_bounded=True,gameplay_not_claimed=True)


NATIVE=r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
static u8 actor[812] __attribute__((aligned(16))),savedActor[812],archive[16] __attribute__((aligned(16)));
u8 *D_800D1C90[256];static int identity,plan,error,calls,present;static u32 size;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(u32)==4)?1:-1];
s32 func_150849A0(u8 *a){if(a!=actor)error=1;calls++;
    if(plan==1)D_800D1C90[identity]=present?0:archive+8;
    if(plan==2)*(u32 *)(archive+4)=0xFFFFFFFFU;
    return identity;}
'''
NATIVE_RUNNER=r'''
static int qualify(int kind,int id,u32 bytes,int available,int mutation){
    int i,special=kind==150;u8 *wantArchive;u32 wantSize,expected,result;
    identity=id;plan=mutation;error=calls=0;present=available;size=bytes;
    for(i=0;i<812;i++)actor[i]=savedActor[i]=(u8)(i*17+35);
    actor[4]=savedActor[4]=(u8)kind;
    for(i=0;i<256;i++)D_800D1C90[i]=present?archive+8:0;
    *(u32 *)(archive+4)=bytes;*(u32 *)archive=1230;
    wantArchive=(plan==1 && !special?!present:present)?archive+8:0;
    wantSize=plan==2 && !special?0xFFFFFFFFU:bytes;
    expected=(special || id!=255) && wantArchive?wantSize/10:0;
    result=(u32)func_1507E968(actor);
    if(error || calls!=!special || result!=expected)return 1;
    for(i=0;i<812;i++)if(actor[i]!=savedActor[i])return 2;
    for(i=0;i<256;i++)if(D_800D1C90[i]!=(i==id?wantArchive:(present?archive+8:0)))return 3;
    if(*(u32 *)(archive+4)!=wantSize || *(u32 *)archive!=1230)return 4;
    return 0;
}
int run(void){int kind,id,n,p,plan,r;u32 i;const u32 sizes[4]={9,10,0x80000000U,0xFFFFFFFFU};
    for(kind=0;kind<256;kind++)for(id=0;id<256;id++)for(n=0;n<4;n++)for(p=0;p<2;p++)for(plan=0;plan<3;plan++){
        r=qualify(kind,id,sizes[n],p,plan);if(r)return r;}
    for(i=0;i<65536;i++)for(kind=0;kind<2;kind++)for(p=0;p<2;p++){
        r=qualify(kind?150:0,127,i,p,0);if(r)return r;}
    return 0;}
'''


if __name__=='__main__':unittest.main()
