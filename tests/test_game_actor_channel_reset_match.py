"""Direct channel reset conversion, ordered ABI proof and unchanged linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_channel_reset_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,ALTERNATE,RESOURCE,ANIMATIONS=guest.STACK,0x20000,0x21000,0x28000,0x29000
HELPER=screen.SYMBOLS['func_1507E7E4']
COUNTS={HELPER:5,0x1507E968:1,0x1507E908:2,0x1507E9F8:2,0x150302F0:2,0x1507E5C8:2}
LIMITS=(0,1,9,10,11,127,128,255)


def fixture(first=9,second=10,channel=255,actor=ACTOR,same=False,descriptor=1):
    memory={}
    for start,length in ((STACK-0x500,0x600),(actor,812),(ALTERNATE,812),(RESOURCE,64),(ANIMATIONS,256)):
        memory.update({start+i:0xA5 for i in range(length)})
    for where in (actor,ALTERNATE):
        for offset,value,size in ((0x6C,first,1),(0x6D,second,1),(0x70,channel,1),
                (0x6F,channel if same else (channel+1)&255,1),(0x71,3 if same else 0xA5,1),
                (0x72,65535 if same else 0xA5A5,2)):
            put(memory,where+offset,value,size)
    put(memory,RESOURCE+4,descriptor,1)
    for i in range(256):put(memory,ANIMATIONS+i,(i*17+35)&255,1)
    return memory


def reference(memory,actor=ACTOR,phase=0,helper=HELPER,mutations=None,
        connected_helper=False,count=256,list_present=True,entry=screen.ENTRY):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x20
    def get(where,size=1):
        assert all(where+i in state for i in range(size)),('reference unmapped read',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=1):
        assert all(where+i in state for i in range(size)),('reference unmapped write',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(target,args):
        events.append(('CALL',target,args));calls.append((target,*args))
        for where,value,size in (mutations or {}).get(target,()):store(where,value,size)
    def actual_helper(channel):
        child=frame-0x30
        store(child+0x18,0x5A000010,4);store(child+0x38,3,4)
        store(child+0x1C,entry+0x24,4);store(child+0x34,channel,4);store(child+0x3C,65535,4)
        old=get(actor+0x6F);captured=get(child+0x37)
        early=False
        if old==captured:
            priority=get(actor+0x71);duration=get(child+0x3E,2)
            if priority==3:early=get(actor+0x72,2)==duration
        if not early:
            store(child+0x3B,3);store(child+0x20,captured,4)
            call(0x1507E968,(actor,));captured=get(child+0x20,4)
            if signed(captured)<signed(count&0xFFFFFFFF):
                call(0x1507E908,(actor,get(actor+0x6F)))
                descriptor=get(RESOURCE+4)
                if descriptor:
                    store(child+0x2C,RESOURCE,4);call(0x1507E9F8,(actor,0))
                    resource=get(child+0x2C,4)
                    if list_present:
                        descriptor=get(resource+4)
                        call(0x150302F0,(actor,get(ANIMATIONS+descriptor-1)))
                captured=get(child+0x37);store(actor+0x6F,captured)
                store(actor+0x72,get(child+0x3E,2),2)
                store(actor+0x71,get(child+0x3B))
                call(0x1507E5C8,(actor,get(child+0x40,4)))
        get(child+0x1C,4);get(child+0x18,4)
    store(frame+0x1C,0xDEAD0000,4)
    channel=get(actor+0x70);store(frame+0x10,10,4);store(frame+0x20,actor,4)
    call(helper,(actor,channel,3,65535,10))
    if connected_helper:actual_helper(channel)
    actor=get(frame+0x20,4);first=get(actor+0x6C)
    store(actor+0x71,0);store(actor+0x72,0,2)
    if first>=10:store(actor+0x6C,0);store(actor+0x6A,0)
    if get(actor+0x6D)>=10:store(actor+0x6D,0);store(actor+0x6B,0)
    get(frame+0x1C,4)
    return state,events,calls


class ResetOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,actor=ACTOR,phase=0,helper=HELPER,mutations=None,
            connected=None,count=256,list_present=True,entry=screen.ENTRY):
        super().__init__(words,memory,arguments=(actor,),phase=phase,entry=entry,connected=connected)
        self.counts={**COUNTS,helper:5};self.mutations=mutations or {}
        self.returns={0x1507E968:count&0xFFFFFFFF,0x1507E908:RESOURCE,
            0x1507E9F8:ANIMATIONS if list_present else 0}
    def execute(self,word):
        if word>>26==32:
            rs,rt,imm=word>>21&31,word>>16&31,word&65535
            address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
            value=self.get(address,1)
            self.r[rt]=(value if value<128 else value-256)&0xFFFFFFFF
            self.r[0]=0
        else:super().execute(word)
    def record_call(self,target):
        args=self.arguments(self.counts[target]);self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in self.counts
        for where,value,size in self.mutations.get(target,()):self.put(where,value,size)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.returns.get(target,0xA5000002)


class GameActorChannelResetMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-channel-reset-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s')
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
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>28I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/AB760.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        before=(cls.out/'before-elf').read_bytes()
        cls.helper=list(struct.unpack_from('>73I',before,elf_slot_offset(before,HELPER,292)))
        assert cls.helper==list(struct.unpack_from('>73I',cls.rom,0xABC94))
        assert cls.original==cls.selected

    @classmethod
    def link(cls,name,entry,helper):
        script=cls.out/('link-%s-%X.ld'%(name,entry));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=func_1507E7E4=0x%X'%helper,'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>28I',sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,actual_helper=False,**settings):
        expected=reference(memory,connected_helper=actual_helper,**settings)
        connected={HELPER+i*4:word for i,word in enumerate(self.helper)} if actual_helper else None
        models=[ResetOracle(words,memory,connected=connected,**settings).run()
            for words in (forms or (self.original,self.selected))]
        for index,model in enumerate(models):
            self.assertEqual(model.memory,expected[0],('memory',index))
            self.assertEqual(model.events,expected[1],('events',index));self.assertEqual(model.calls,expected[2],('calls',index))
        return models

    def test_01_direct_complete_shape_and_production_profile(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(28,32,0,0,''))
        self.assertEqual(self.meta['relocations'],{28:[('R_MIPS_26','func_1507E7E4')]})
        self.receipt('shape',retail_words=28,frame=32,guards=0,inserted_omitted_words=0,
            every_word_emits_from_complete_C=True,normal_O2_g3=True,diagnostics=0,pool_bytes=0)

    def test_02_independent_ordered_byte_domains_and_mutating_callbacks(self):
        cases=0;coverage=set()
        inputs=[(i,255-i,(i*17)&255) for i in range(256)]
        inputs+=list(itertools.product(LIMITS,LIMITS,(0,127,128,255)))
        for (first,second,channel),phase,plan in itertools.product(inputs,(0,8),range(3)):
            memory=fixture(first,second,channel)
            mutations={HELPER:((ACTOR+0x6C,255-first,1),(ACTOR+0x6D,255-second,1),
                (ACTOR+0x70,0,1),(ACTOR+0x71,17,1),(ACTOR+0x72,0x7F00,2))} if plan==1 else {}
            if plan==2:mutations={HELPER:((STACK+phase,ALTERNATE,4),)}
            models=self.compare(memory,phase=phase,mutations=mutations)
            coverage.update(models[0].visits);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+112,4)))
        self.receipt('guest',cases=cases,executions=cases*2,retail_words_reached=28,
            independent_full_private_public_order=True,unsigned_field_domains_and_thresholds=True,
            five_argument_O32_ABI=True,live_callback_reads_and_saved_actor_home_reload=True,
            all_caller_GP_FPR_clobbered=True,void_return_not_compared=True)

    def test_03_private_aliases_and_every_fired_fault_prefix(self):
        cases=prefixes=0
        for phase,actor,plan in itertools.product((0,8),(ACTOR,STACK-0x6C,STACK-0x80),range(2)):
            actor=actor+phase if actor!=ACTOR else actor
            memory=fixture(9,10,255,actor=actor)
            mutations={HELPER:((STACK+phase,ALTERNATE,4),)} if plan else {}
            models=self.compare(memory,actor=actor,phase=phase,mutations=mutations)
            for ordinal in range(models[0].accesses):
                failed=[]
                for body in (self.original,self.selected):
                    model=ResetOracle(body,memory,actor=actor,phase=phase,mutations=mutations);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                    failed.append(model)
                for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                prefixes+=1
            cases+=1
        self.receipt('aliases-faults',cases=cases,fired_fault_pairs=prefixes,failed_executions=prefixes*2,
            incoming_actor_and_outgoing_fifth_home_aliases=True,absent_fault_is_failure=True,
            full_private_prefix_memory_events_calls=True,not_portable_C_fault_acceptance=True)

    def test_04_independent_JAL_rebases(self):
        cases=0
        for entry,helper in ((screen.ENTRY,HELPER),(0x15207FFC,0x15218004),(0x15308004,0x15327FFC)):
            forms=tuple(self.link(name,entry,helper) for name in ('original','selected'))
            self.assertEqual(forms[0],forms[1])
            for first,second,channel,phase in itertools.product((0,10,255),(9,10,128),(0,255),(0,8)):
                self.compare(fixture(first,second,channel),forms=forms,entry=entry,helper=helper,phase=phase);cases+=1
        self.receipt('rebases',independent_links=6,cases=cases,executions=cases*2,
            distinct_entries_and_JAL_targets=True,no_guards_or_pools=True)

    def test_05_complete_actual_73_word_helper_and_fault_order(self):
        cases=prefixes=0;coverage=set()
        for channel,same,count,descriptor,present,plan in itertools.product((0,8,255),(False,True),
                (0,9,256,0xFFFFFFFF),(0,1,7),(False,True),range(3)):
            memory=fixture(255,10,channel,same=same,descriptor=descriptor)
            mutations={}
            if plan==1:mutations={0x1507E9F8:((RESOURCE+4,7,1),),
                0x150302F0:((ACTOR+0x6C,9,1),(ACTOR+0x6D,255,1))}
            if plan==2:
                child=STACK-0x20-0x30
                mutations={0x1507E968:((child+0x34,257,4),(child+0x3C,12,4),
                    (child+0x3B,5,1),(STACK,ALTERNATE,4)),0x1507E5C8:((ACTOR+0x6D,0,1),)}
            models=self.compare(memory,actual_helper=True,count=count,list_present=present,mutations=mutations)
            coverage.update(models[0].visits);cases+=1
            if (channel,same,count,descriptor,present,plan)==(8,False,256,7,True,1):
                connected={HELPER+i*4:word for i,word in enumerate(self.helper)}
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.selected):
                        model=ResetOracle(words,memory,connected=connected,count=count,list_present=present,
                            mutations=mutations);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                        failed.append(model)
                    for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                    prefixes+=1
        self.assertIn(HELPER,coverage);self.assertIn(HELPER+0x11C,coverage)
        self.receipt('actual-helper',cases=cases,executions=cases*2,actual_banked_helper_words=73,
            independent_full_private_reference=True,fired_fault_pairs=prefixes,
            nested_fifth_argument_consumed_from_real_home=True,captured_and_live_nested_callback_reads=True,
            deeper_callbacks_bounded=True,not_complete_helper_branch_coverage=True)

    def test_06_copied_owner_and_actual_padding_all_unchanged(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        self.assertEqual(warnings[0],warnings[1])
        parsed=[parse_object(obj) for obj in objects]
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        padded=[]
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AB760',str(assembly),
                '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True)
            padded.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(padded[0],padded[1])
        self.receipt('owner',neighbors=len(parsed[0][1])-1,preexisting_warning_count=len(warnings[0]),
            no_new_diagnostics=True,all_padded_owner_bytes_functions_extents_relocations_exact=True,
            pools_and_caller_code_exact=True,target_full_112_bytes_not_padding_credit=True)

    def test_07_fresh_complete_semantic_negative_controls(self):
        controls=(('first-threshold','actor[0x6C] >= 10','actor[0x6C] > 10',dict(first=10)),
            ('signed-byte','actor[0x6C] >= 10','((s8 *)actor)[0x6C] >= 10',dict(first=255)),
            ('channel','actor[0x70], 3','actor[0x6F], 3',{}),
            ('duration','3, 0xFFFF, 10','3, 0x7FFF, 10',{}),
            ('fifth-argument','3, 0xFFFF, 10','3, 0xFFFF, 9',{}),
            ('halfword','*(u16 *)(actor + 0x72)','*(u8 *)(actor + 0x72)',{}),
            ('reset-pair','actor[0x6A] = 0','actor[0x6B] = 0',dict(first=10,second=0)))
        for name,old,new,case in controls:
            self.assertIn(old,screen.SELECTED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            memory=fixture(**case);wrong=ResetOracle(words,memory).run()
            expected=reference(memory)
            public=lambda m:{a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}
            trace=lambda es:[e for e in es if e[0]=='CALL' or not STACK-0x500<=e[1]<STACK+0x100]
            self.assertNotEqual((public(wrong.memory),trace(wrong.events),wrong.calls),
                (public(expected[0]),trace(expected[1]),expected[2]),name)
        cached=screen.SELECTED.replace('    func_1507E7E4',
            '    u8 first = actor[0x6C];\n    func_1507E7E4').replace('actor[0x6C] >= 10','first >= 10')
        _,words=screen.compile_candidate(self.root,self.out,'negative-precallback-read',cached)
        memory=fixture(first=9);mutation={HELPER:((ACTOR+0x6C,255,1),)}
        wrong=ResetOracle(words,memory,mutations=mutation).run();expected=reference(memory,mutations=mutation)
        self.assertNotEqual(read(wrong.memory,ACTOR+0x6C,1),read(expected[0],ACTOR+0x6C,1))
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls)+1)

    def test_08_native32_complete_C_and_all_threshold_pairs(self):
        source=NATIVE+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-threshold','actor[0x6C] >= 10','actor[0x6C] > 10'),
                ('native-fifth','3, 0xFFFF, 10','3, 0xFFFF, 9'),
                ('native-halfword','*(u16 *)(actor + 0x72)','*(u8 *)(actor + 0x72)')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=2*256*256*3,all_threshold_byte_pairs=True,
            all_channel_bytes_and_live_callback_mutations=True,full_812_byte_actor_compared=True,
            actual_five_argument_typed_ABI=True,native_effective_negatives=3)

    def test_09_whole_linked_ELF_and_only_one_conversion_row(self):
        with self.assertRaisesRegex(ValueError,'immutable'):self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text();before_source=(self.out/'before-source').read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('installation',installed=False,five_current_baselines_unchanged=True);return
        self.assertEqual(source,screen.install(before_source))
        for name in ('guards','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes();actual=(self.root/self.paths['elf']).read_bytes()
        expected=bytearray(before);em,am=metadata(before),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5];expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        old=list(csv.reader((self.out/'before-progress').read_text().splitlines()))
        positions=[i for i,row in enumerate(old) if row[3]==screen.FUNCTION];self.assertEqual(len(positions),1)
        index=positions[0];self.assertEqual(old[index][6],'asm')
        new=[row.copy() for row in old];new[index][6]='c'
        self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),new)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,all_linked_instruction_bytes_addresses_extents_exact=True,
            only_conversion_row=screen.FUNCTION,converted_bytes_added=112,guard_file_byte_identical=True,
            protected_data=audit)

    def test_10_actual_banked_direct_caller_and_full_word_gate(self):
        before=(self.out/'before-elf').read_bytes();entry=0x1507EB4C
        caller=list(struct.unpack_from('>13I',before,elf_slot_offset(before,entry,52)))
        class Caller(ResetOracle):
            def record_call(model,target):
                if target==screen.ENTRY:
                    args=model.arguments(1);model.calls.append((target,*args));model.events.append(('CALL',target,args))
                else:super().record_call(target)
            def hook(model,target):
                assert target!=screen.ENTRY,'channel reset must execute actual instructions'
                super().hook(target)
        cases=0
        for channel,value,phase,plan in itertools.product((0,9,255),(0,9,255,256,511,0xFFFFFFFF),(0,8),(0,1)):
            memory=fixture(9,10,channel)
            mutation={HELPER:((ACTOR+0x6C,255,1),(ACTOR+0x6D,9,1))} if plan else {}
            models=[]
            for body in (self.original,self.selected):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                model=Caller(caller,memory,phase=phase,entry=entry,connected=connected,mutations=mutation)
                model.r[5]=model.before[5]=value;model.run();models.append(model)
                called=value!=channel
                self.assertEqual(screen.ENTRY in model.visits,called)
                if called:
                    self.assertEqual(model.calls,[(screen.ENTRY,ACTOR),(HELPER,ACTOR,value&255,3,65535,10)])
                    self.assertEqual(read(model.memory,ACTOR+0x70,1),value&255)
                else:
                    public=lambda m:{a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}
                    self.assertEqual(public(model.memory),public(memory))
            for name in ('memory','events','calls','accesses'):self.assertEqual(getattr(models[0],name),getattr(models[1],name))
            cases+=1
        self.receipt('caller',cases=cases,executions=cases*2,actual_banked_caller_slot_words=13,
            actual_target_words=28,full_word_change_gate_and_byte_store=True,
            full_private_traces_and_ABI_exact=True,helper_bounded_in_this_caller_matrix=True)


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
static u8 actors[2][812] __attribute__((aligned(16))),expected[812],*currentActor;
static int plan,error,calls,wantChannel;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(u16)==2)?1:-1];
void func_1507E7E4(u8 *actor,u8 channel,u8 priority,u16 duration,s32 amount) {
    if(actor!=currentActor || channel!=wantChannel || priority!=3 || duration!=65535 || amount!=10)error=1;
    if(actor[0x71]!=0xA5 || *(u16 *)(actor+0x72)!=0xA5A5)error=2;
    calls++;
    if(plan==1){actor[0x6C]=255-actor[0x6C];actor[0x6D]=255-actor[0x6D];actor[0x70]=0;}
    if(plan==2){actor[0x6C]=9;actor[0x6D]=10;actor[0x70]=5;}
    actor[0x71]=17;*(u16 *)(actor+0x72)=0x7F00;
}
'''
NATIVE_RUNNER=r'''
static int qualify(int slot,int first,int second,int mutation) {
    int i;u8 *actor=actors[slot];currentActor=actor;plan=mutation;error=calls=0;
    wantChannel=(first*3+second*7)&255;
    for(i=0;i<812;i++)actor[i]=0xA5;
    actor[0x6C]=(u8)first;actor[0x6D]=(u8)second;actor[0x70]=(u8)wantChannel;
    for(i=0;i<812;i++)expected[i]=actor[i];
    if(plan==1){expected[0x6C]=(u8)(255-first);expected[0x6D]=(u8)(255-second);expected[0x70]=0;}
    if(plan==2){expected[0x6C]=9;expected[0x6D]=10;expected[0x70]=5;}
    expected[0x71]=0;*(u16 *)(expected+0x72)=0;
    if(expected[0x6C]>=10){expected[0x6C]=0;expected[0x6A]=0;}
    if(expected[0x6D]>=10){expected[0x6D]=0;expected[0x6B]=0;}
    func_1507EABC(actor);
    if(error || calls!=1)return 1;
    for(i=0;i<812;i++)if(actor[i]!=expected[i])return 2;
    return 0;
}
int run(void) {
    int slot,first,second,p,r;
    for(slot=0;slot<2;slot++)for(first=0;first<256;first++)for(second=0;second<256;second++)for(p=0;p<3;p++) {
        r=qualify(slot,first,second,p);if(r)return r;
    }
    return 0;
}
'''


if __name__=='__main__':unittest.main()
