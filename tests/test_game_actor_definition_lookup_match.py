"""Direct definition lookup, actual classifier/caller and unchanged linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_definition_lookup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_channel_transition_match as transition
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

STACK,ACTOR=reset.STACK,reset.ACTOR
CLASSIFIER,TABLE=screen.SYMBOLS.values()
CLASS_LIST,ARCHIVE,ALTERNATE,RECORDS=0x26000,0x28008,0x29008,0x30000
MASK=0xFFFFFFFF
INDICES=(0,1,2,127,128,255,256,257,65535,65536,0x7FFFFFFF,0x80000000,
    0xFFFFFFFE,0xFFFFFFFF,0x1999999A,0xCCCCCCCD)


def fixture(identity=3,archive_present=True,records_present=True,selector=0,actor=ACTOR,
        table=TABLE,record_base=RECORDS,archive=ARCHIVE):
    memory=reset.fixture(actor=actor)
    for base,length in ((table-16,1056),(CLASS_LIST,256),(ARCHIVE-8,64),(ALTERNATE-8,64),(RECORDS,4096)):
        memory.update({(base+i)&MASK:0xA5 for i in range(length)})
    for i in range(256):
        put(memory,table+i*4,archive,4);put(memory,CLASS_LIST+i,(i*17+35)&255,1)
    selected=(table+((identity*4)&MASK))&MASK
    put(memory,selected,archive if archive_present else 0,4)
    put(memory,archive-8,record_base if records_present else 0,4)
    put(memory,ALTERNATE-8,RECORDS+128,4)
    put(memory,actor+0x1C9,selector,1);put(memory,actor+0x2C4,CLASS_LIST,4)
    put(memory,CLASS_LIST+(selector-1 if selector else 0),identity,1)
    return memory


def reference(memory,actor=ACTOR,index=7,identity=3,phase=0,table=TABLE,classifier=CLASSIFIER,
        actual_classifier=False,mutations=None,stack=None,return_address=0xDEAD0000,entry=screen.ENTRY):
    state,events,calls=memory.copy(),[],[];frame=(STACK+phase if stack is None else stack)-0x18
    def get(where,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size):
        where&=MASK;assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    store(frame+0x14,return_address,4);store(frame+0x1C,index,4)
    events.append(('CALL',classifier,(actor,)));calls.append((classifier,actor))
    if actual_classifier:
        selector=get(actor+0x1C9,1);classes=get(actor+0x2C4,4)
        identity=get(classes+(selector-1 if selector else 0),1)
    else:
        for where,value,size in mutations or ():store(where,value,size)
    archive=get(table+((identity*4)&MASK),4)
    get(frame+0x14,4)
    result=0
    if archive:
        records=get(archive-8,4);index=get(frame+0x1C,4)
        if records:result=(records+((index*10)&MASK))&MASK
    return state,events,calls,result


class DefinitionOracle(reset.ResetOracle):
    def __init__(self,words,memory,actor=ACTOR,index=7,identity=3,phase=0,table=TABLE,
            classifier=CLASSIFIER,actual_classifier=False,mutations=None,entry=screen.ENTRY,connected=None):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(actor,index),phase=phase,entry=entry,connected=connected)
        self.classifier=classifier;self.identity=identity;self.mutations=mutations or ()
    def record_call(self,target):
        assert target==self.classifier
        args=self.arguments(1);self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.classifier
        for where,value,size in self.mutations:self.put(where,value,size)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.identity&MASK


class GameActorDefinitionLookupMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-actor-definition-lookup-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
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
        cls.meta,cls.selected=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>24I',cls.rom,screen.ROM))
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

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings)
        connected={CLASSIFIER+i*4:w for i,w in enumerate(self.classifier)} if settings.get('actual_classifier') else None
        models=[DefinitionOracle(words,memory,connected=connected,**settings).run() for words in
            (forms or (self.original,self.selected))]
        for model in models:
            self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected)
        return models

    def test_01_complete_direct_shape_profile_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(24,24,0,0,''))
        self.assertEqual(self.meta['relocations'],{12:[('R_MIPS_26','func_150849A0')],
            24:[('R_MIPS_HI16','D_800D1C90')],32:[('R_MIPS_LO16','D_800D1C90')]})
        self.receipt('shape',words=24,frame=24,guards=0,insertions=0,omissions=0,
            all_words_from_complete_C=True,normal_O2_g3=True,diagnostics=0,pool_bytes=0)

    def test_02_full_word_indices_nullable_headers_and_live_callback_order(self):
        cases=0;coverage=set()
        for identity,index,present,records,phase,plan in itertools.product(
                (0,1,127,128,255,0x40000000,0x40000001,0xFFFFFFFF),INDICES,
                (False,True),(False,True),(0,8),range(3)):
            memory=fixture(identity,present,records);home=STACK+phase+4
            slot=(TABLE+((identity*4)&MASK))&MASK
            mutations=()
            if plan==1:mutations=((slot,ALTERNATE,4),(home,0xFFFFFFFF,4))
            if plan==2:mutations=((ARCHIVE-8,0,4),(ACTOR+0x6F,128,1))
            models=self.compare(memory,identity=identity,index=index,phase=phase,mutations=mutations)
            coverage.update(models[0].visits);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+96,4)))
        for index,base in ((16,0xFFFFFF60),(0x80000000,RECORDS),(0x1999999A,0xFFFFFFFC)):
            models=self.compare(fixture(record_base=base),index=index);cases+=1
            self.assertEqual(models[0].r[2],(base+((index*10)&MASK))&MASK)
        self.receipt('guest',cases=cases,executions=cases*2,retail_words_reached=24,
            independent_full_private_order=True,full_O32_index_and_modulo_word_arithmetic=True,
            live_table_after_callback_and_home_reload=True,nullable_archive_and_records=True,
            all_caller_GP_FPR_clobbered=True,pointer_return_compared=True)

    def test_03_aliases_actual_classifier_and_every_selected_fault_prefix(self):
        cases=prefixes=0;classifier_coverage=set()
        for selector,identity,index,present,records,phase in itertools.product(
                (0,1,2,128,255),(0,7,128,255),(0,7,256,0xFFFFFFFF),
                (False,True),(False,True),(0,8)):
            models=self.compare(fixture(identity,present,records,selector),identity=identity,index=index,
                phase=phase,actual_classifier=True);cases+=1;classifier_coverage.update(models[0].visits)
        reachable={CLASSIFIER+i*4 for i in range(11) if i!=7}
        self.assertEqual(classifier_coverage&set(range(CLASSIFIER,CLASSIFIER+44,4)),reachable)
        for phase,mode,index in itertools.product((0,8),range(4),(0,7,0xFFFFFFFF)):
            archive=STACK+phase+12 if mode in (1,3) else ARCHIVE
            table=STACK+phase+4 if mode in (2,3) else TABLE
            if table!=TABLE:index={0:0,7:ARCHIVE,0xFFFFFFFF:ALTERNATE}[index]
            memory=fixture(0,archive=archive,table=table)
            settings=dict(identity=0,index=index,phase=phase,table=table)
            if table!=TABLE:
                # Link the real global table symbol to the incoming index home.
                forms=tuple(self.link(name,screen.ENTRY,CLASSIFIER,table) for name in ('selected','original'))
            else:forms=(self.selected,self.original)
            models=self.compare(memory,forms=forms,**settings);cases+=1
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in forms:
                    model=DefinitionOracle(words,memory,**settings);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                    failed.append(model)
                for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                prefixes+=1
        unmapped=0
        for phase,mode,index in itertools.product((0,8),(2,3),(7,0xFFFFFFFF)):
            table=STACK+phase+4;archive=STACK+phase+12 if mode==3 else ARCHIVE
            memory=fixture(0,archive=archive,table=table);models=[]
            for name in ('selected','original'):
                model=DefinitionOracle(self.link(name,screen.ENTRY,CLASSIFIER,table),memory,
                    identity=0,index=index,phase=phase,table=table)
                with self.assertRaises(AssertionError) as caught:model.run()
                self.assertEqual(caught.exception.args,(('unmapped read',(index-8)&MASK,4),))
                self.assertEqual(model.accesses,5);models.append(model)
            for name in ('memory','events','calls','accesses'):self.assertEqual(getattr(models[0],name),getattr(models[1],name))
            unmapped+=1
        self.receipt('aliases-classifier',cases=cases,executions=cases*2,fired_fault_pairs=prefixes,
            failed_executions=prefixes*2,actual_classifier_words=11,reachable_classifier_words=10,
            unmapped_home_alias_fault_pairs=unmapped,unmapped_failed_executions=unmapped*2,
            retail_dead_word_not_falsely_counted=True,incoming_home_aliases=True,
            strict_fault_prefixes=True,not_portable_C_fault_semantics=True)

    @classmethod
    def link(cls,name,entry,classifier,table):
        script=cls.out/('link-%s-%X-%X-%X.ld'%(name,entry,classifier,table));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=func_150849A0=0x%X'%classifier,'--defsym=D_800D1C90=0x%X'%table,
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>24I',sections(elf)['.text'][1]))

    def test_04_independent_JAL_and_HI_LO_carry_rebases(self):
        cases=0
        for entry,classifier,table in ((screen.ENTRY,CLASSIFIER,TABLE),
                (0x15207FFC,0x15218004,0x80117FFC),(0x15308004,0x15327FFC,0x80118004),
                (0x15417FFC,0x15428004,0x80227FF0)):
            forms=tuple(self.link(name,entry,classifier,table) for name in ('selected','original'))
            self.assertEqual(forms[0],forms[1])
            for identity,index,present,records,phase in itertools.product((0,127,255),
                    (0,256,0xFFFFFFFF),(False,True),(False,True),(0,8)):
                self.compare(fixture(identity,present,records,table=table),forms=forms,entry=entry,
                    classifier=classifier,table=table,identity=identity,index=index,phase=phase);cases+=1
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
        self.assertEqual(padded[0],padded[1])
        self.receipt('owner',neighbors=len(padded[0][1])-1,diagnostics=len(warnings[0]),
            all_actual_padded_bytes_extents_relocations_equal=True,pools_equal=True,no_new_guards=True)

    def test_06_effective_complete_IDO_negative_controls(self):
        controls=(('byte-index','s32 index','u8 index',dict(index=256)),
            ('stride','index * 10','index * 8',{}),
            ('header-offset','archive -= 8','archive -= 4',{}),
            ('fixed-classifier','func_150849A0(actor)','(func_150849A0(actor), 0)',dict(identity=7)),
            ('wrong-table','D_800D1C90[func_150849A0(actor)]','D_800D1C90[func_150849A0(actor) + 1]',dict(identity=7)))
        for name,old,new,case in controls:
            memory=fixture(case.get('identity',3));identity=case.get('identity',3)
            put(memory,TABLE,ALTERNATE,4);put(memory,TABLE+((identity+1)*4),ALTERNATE,4)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            wrong=DefinitionOracle(words,memory,**case).run();expected=reference(memory,**case)
            self.assertNotEqual(wrong.r[2],expected[3],name)
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls))

    def test_07_native32_complete_C_valid_records_and_live_callbacks(self):
        source=NATIVE+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-stride','index * 10','index * 8'),
                ('native-header','archive -= 8','archive -= 4')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=256*256*4*3,
            all_classifier_bytes_and_valid_byte_indices=True,live_table_and_header_mutations=True,
            full_actor_and_table_compared=True,typed_two_argument_ABI=True,effective_native_negatives=2,
            extreme_guest_address_formation_not_claimed_portable_native_C=True)

    def test_08_actual_transition_caller_classifier_and_null_fault_boundary(self):
        entry=transition.screen.ENTRY;cases=failures=0
        class Caller(transition.TransitionOracle):
            def record_call(model,target):
                if target==CLASSIFIER:
                    args=model.arguments(1);model.calls.append((target,*args));model.events.append(('CALL',target,args))
                else:super().record_call(target)
        for channel,priority,count,descriptor,present,selector,phase in itertools.product((0,8,255),
                (0,2,3,255),(0,9,256,0xFFFFFFFF),(0,7),(False,True),(0,2),(0,8)):
            memory=transition.fixture(descriptor=descriptor)
            extra=fixture(3,selector=selector,record_base=reset.RESOURCE-7*10)
            for where,value in extra.items():
                if TABLE-16<=where<TABLE+1040 or CLASS_LIST<=where<CLASS_LIST+256 or ARCHIVE-8<=where<ARCHIVE+56:
                    memory[where]=value
            put(memory,reset.RESOURCE+4,descriptor,1)
            put(memory,ACTOR+0x1C9,selector,1);put(memory,ACTOR+0x2C4,CLASS_LIST,4)
            expected=transition.reference(memory,channel=channel,priority=priority,count=count,
                list_present=present,phase=phase)
            state=memory.copy();put(state,STACK+phase+0x10,10,4);events=[];calls=[]
            for event in expected[1]:
                events.append(event)
                if event[0]=='W':put(state,event[1],event[3],event[2])
                elif event[0]=='R':self.assertEqual(read(state,event[1],event[2]),event[3])
                else:
                    target,args=event[1:];calls.append((target,*args))
                    if target==screen.ENTRY:
                        state,inner,inner_calls,result=reference(state,actor=args[0],index=args[1],
                            actual_classifier=True,stack=STACK+phase-0x30,return_address=entry+0xB4)
                        self.assertEqual(result,reset.RESOURCE);events.extend(inner);calls.extend(inner_calls)
            for words in (self.original,self.selected):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({CLASSIFIER+i*4:w for i,w in enumerate(self.classifier)})
                model=Caller(self.caller,memory,channel=channel,priority=priority,count=count,
                    list_present=present,phase=phase,connected=connected).run()
                self.assertEqual((model.memory,model.events,model.calls),(state,events,calls))
            cases+=1
        for archive_present,records_present in ((False,True),(True,False)):
            memory=transition.fixture();extra=fixture(3,archive_present,records_present)
            for where,value in extra.items():
                if TABLE-16<=where<TABLE+1040 or CLASS_LIST<=where<CLASS_LIST+256 or ARCHIVE-8<=where<ARCHIVE+56:
                    memory[where]=value
            put(memory,ACTOR+0x1C9,0,1);put(memory,ACTOR+0x2C4,CLASS_LIST,4);models=[]
            for words in (self.original,self.selected):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({CLASSIFIER+i*4:w for i,w in enumerate(self.classifier)})
                model=Caller(self.caller,memory,priority=3,connected=connected)
                with self.assertRaises(AssertionError) as caught:model.run()
                self.assertEqual(caught.exception.args,(('unmapped read',4,1),));models.append(model);failures+=1
            for name in ('memory','events','calls','accesses'):self.assertEqual(getattr(models[0],name),getattr(models[1],name))
        self.receipt('caller',cases=cases,executions=cases*2,caller_words=73,target_words=24,classifier_words=11,
            independent_replayed_full_private_reference=True,null_dereference_failed_executions=failures,
            no_invented_compatibility_guard=True,deeper_callbacks_bounded=True,other_callers_not_executed=True)

    def test_09_whole_linked_ELF_only_one_conversion_row_and_no_guard_change(self):
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
        index=indices[0];self.assertEqual(old[index][5:],['96','asm']);new=[row.copy() for row in old];new[index][6]='c'
        self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),new)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,whole_ELF_byte_identical=True,all_addresses_extents_symbols_exact=True,
            only_conversion_row=screen.FUNCTION,converted_bytes_added=96,guards_and_symbol_files_byte_identical=True,
            protected_data=audit)


NATIVE=r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
static u8 actor[812] __attribute__((aligned(16))),savedActor[812],archive[16] __attribute__((aligned(16)));
static u8 records[4096],alternate[4096];u8 *D_800D1C90[256];
static int identity,plan,error,calls,present,haveRecords;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(u32)==4)?1:-1];
s32 func_150849A0(u8 *a){if(a!=actor)error=1;calls++;
    if(plan==1)D_800D1C90[identity]=present?0:archive+8;
    if(plan==2)*(u8 **)archive=haveRecords?0:alternate;
    return identity;}
'''
NATIVE_RUNNER=r'''
static int qualify(int id,int index,int flags,int mutation){
    int i;u8 *wantArchive,*wantRecords,*result,*expected;
    identity=id;plan=mutation;error=calls=0;present=flags&1;haveRecords=flags&2;
    for(i=0;i<812;i++)actor[i]=savedActor[i]=(u8)(i*17+35);
    for(i=0;i<256;i++)D_800D1C90[i]=0;
    D_800D1C90[id]=present?archive+8:0;*(u8 **)archive=haveRecords?records:0;
    *(u8 **)(archive+4)=alternate;
    wantArchive=(plan==1?!present:present)?archive+8:0;
    wantRecords=plan==2?(haveRecords?0:alternate):(haveRecords?records:0);
    expected=wantArchive && wantRecords?wantRecords+index*10:0;
    result=func_1507E908(actor,index);
    if(error || calls!=1 || result!=expected)return 1;
    for(i=0;i<812;i++)if(actor[i]!=savedActor[i])return 2;
    for(i=0;i<256;i++)if(D_800D1C90[i]!=(i==id?wantArchive:0))return 3;
    if(*(u8 **)archive!=wantRecords)return 4;
    return 0;
}
int run(void){int id,index,flags,plan,r;
    for(id=0;id<256;id++)for(index=0;index<256;index++)for(flags=0;flags<4;flags++)for(plan=0;plan<3;plan++){
        r=qualify(id,index,flags,plan);if(r)return r;}return 0;}
'''


if __name__=='__main__':unittest.main()
