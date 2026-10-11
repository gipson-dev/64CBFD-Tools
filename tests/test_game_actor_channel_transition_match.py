"""Channel arbitration, strict five-word normalization and whole-linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_actor_channel_transition_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,RESOURCE,ANIMATIONS=reset.STACK,reset.ACTOR,reset.RESOURCE,reset.ANIMATIONS
COUNT,DEFINITION,LIST,APPLY,FINISH=tuple(screen.SYMBOLS.values())
COUNTS={COUNT:1,DEFINITION:2,LIST:2,APPLY:2,FINISH:2,0x1507EABC:1,screen.ENTRY:5}


def fixture(current=7,default=9,previous=1,remaining=8,descriptor=1,actor=ACTOR):
    memory=reset.fixture(actor=actor,descriptor=descriptor)
    for offset,value,size in ((0x6F,current,1),(0x70,default,1),(0x71,previous,1),(0x72,remaining,2)):
        put(memory,actor+offset,value,size)
    put(memory,ANIMATIONS-1,0xEF,1)
    return memory


def reference(memory,actor=ACTOR,channel=8,priority=2,duration=9,amount=10,
        phase=0,count=256,list_present=True,mutations=None):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x30
    put(state,STACK+phase+0x10,amount,4)
    def get(where,size=1):
        assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=1):
        assert all(where+i in state for i in range(size)),('unmapped reference',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(target,args):
        events.append(('CALL',target,args));calls.append((target,*args))
        for where,value,size in (mutations or {}).get(target,()):store(where,value,size)
    store(frame+0x18,0x5A000010,4);store(frame+0x38,priority,4)
    priority&=255
    store(frame+0x1C,0xDEAD0000,4);store(frame+0x34,channel,4);store(frame+0x3C,duration,4)
    old=get(actor+0x6F);captured=get(frame+0x37);early=False
    if old==captured:
        previous=get(actor+0x71);wanted=get(frame+0x3E,2)
        if previous==priority:early=get(actor+0x72,2)==wanted
    accepted=not early
    if accepted and priority!=3:
        accepted=get(actor+0x70)==old or captured==old or get(actor+0x72,2)==0 or get(actor+0x71)<priority
    if accepted:
        store(frame+0x3B,priority);store(frame+0x20,captured,4)
        call(COUNT,(actor,));captured=get(frame+0x20,4)
        if signed(captured)<signed(count&0xFFFFFFFF):
            call(DEFINITION,(actor,get(actor+0x6F)))
            descriptor=get(RESOURCE+4)
            if descriptor:
                store(frame+0x2C,RESOURCE,4);call(LIST,(actor,0));definition=get(frame+0x2C,4)
                if list_present:
                    descriptor=get(definition+4)
                    call(APPLY,(actor,get(ANIMATIONS+descriptor-1)))
            captured=get(frame+0x37);store(actor+0x6F,captured)
            store(actor+0x72,get(frame+0x3E,2),2);store(actor+0x71,get(frame+0x3B))
            call(FINISH,(actor,get(frame+0x40,4)))
    get(frame+0x1C,4);get(frame+0x18,4)
    return state,events,calls


class TransitionOracle(reset.ResetOracle):
    def __init__(self,words,memory,actor=ACTOR,channel=8,priority=2,duration=9,amount=10,
            phase=0,count=256,list_present=True,mutations=None,entry=screen.ENTRY,connected=None):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(actor,channel,priority,duration,amount),
            phase=phase,entry=entry,connected=connected)
        self.counts=COUNTS;self.mutations=mutations or {}
        self.returns={COUNT:count&0xFFFFFFFF,DEFINITION:RESOURCE,LIST:ANIMATIONS if list_present else 0}


class GameActorChannelTransitionMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-actor-channel-transition-test'
        cls.out.mkdir(exist_ok=True)
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
        if not (cls.out/'before-undefined').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            data=(cls.root/'conker/undefined_funcs_auto.txt').read_bytes()
            assert data.count(b'func_1507E7E4 = 0x1507E7E4;')==1
            (cls.out/'before-undefined').write_bytes(data)
            (cls.out/'linker-baseline.json').write_text(json.dumps({'sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
        cls.linker_hash=json.loads((cls.out/'linker-baseline.json').read_text())['sha256']
        assert hashlib.sha256((cls.out/'before-undefined').read_bytes()).hexdigest()==cls.linker_hash
        with (cls.out/'before-guards').open(newline='') as stream:
            cls.fields=csv.DictReader(stream).fieldnames
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>73I',cls.rom,screen.ROM))
        cls.fitted=screen.normalize(cls.raw);assert cls.fitted==cls.original
        body=(cls.root/'conker/asm/AB760.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.write_rows(cls.out/'isolated.csv',screen.guard_rows())
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_AB760'))
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings)
        models=[TransitionOracle(words,memory,**settings).run() for words in
            (forms or (self.original,self.raw,self.fitted))]
        for model in models:
            self.assertEqual(model.memory,expected[0]);self.assertEqual(model.events,expected[1])
            self.assertEqual(model.calls,expected[2])
        return models

    def test_01_complete_shape_and_strict_guard_closure(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(73,48,0,5,''))
        self.assertEqual(self.meta['relocations'],{offset:[('R_MIPS_26',name)] for offset,name in
            zip((144,172,200,228,264),screen.SYMBOLS)})
        for index,_,_ in screen.PATCHES:
            wrong=self.raw.copy();wrong[index]^=1
            with self.assertRaises(ValueError):screen.normalize(wrong)
        with self.assertRaises(ValueError):screen.normalize(self.raw[:-1])
        self.receipt('shape',retail_words=73,frame=48,guard_words=5,insertions=0,omissions=0,
            complete_C=True,closed_t8_t9_swap=True,symmetric_equality_operands=True,
            diagnostics=0,pool_bytes=0,normal_O2_g3=True,stale_guard_controls=6)

    def test_02_priority_duration_count_and_ordered_callbacks(self):
        cases=0;coverage=set();paths=set()
        inputs=[(i,(i+1)&255,(i*17)&255,(i*19)&255,(i*7)&255) for i in range(256)]
        inputs+=list(itertools.product((0,3,128,255),(0,3,255),(0,3,255),(0,3,255),(0,3,255)))
        for current,default,previous,channel,priority in inputs:
            for remaining,duration in ((0,0),(8,8),(8,9),(65535,65535)):
                memory=fixture(current,default,previous,remaining,descriptor=current&1)
                for count in (0,channel,channel+1,256,0xFFFFFFFF,0x80000000):
                    models=self.compare(memory,channel=channel,priority=priority,duration=duration,
                        amount=0x81234567,count=count)
                    coverage.update(models[0].visits);paths.add(tuple(c[0] for c in models[0].calls));cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+292,4)))
        self.assertGreaterEqual(len(paths),3)
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=73,
            independent_full_private_order=True,all_priority_bytes=True,unsigned_fields=True,
            signed_full_word_count=True,all_caller_GP_FPR_clobbered=True)

    def test_03_live_rereads_private_aliases_and_fired_fault_prefixes(self):
        cases=prefixes=0
        for phase,actor,descriptor,present,plan in itertools.product((0,8),
                (ACTOR,STACK-0x60,STACK-0x90),(0,1,7,255),(False,True),range(3)):
            actor=actor+phase if actor!=ACTOR else actor;frame=STACK+phase-0x30
            memory=fixture(actor=actor,descriptor=descriptor)
            mutations={}
            if plan==1:mutations={COUNT:((actor+0x6F,21,1),),LIST:((RESOURCE+4,0,1),),
                APPLY:((actor+0x71,99,1),(actor+0x72,0,2))}
            if plan==2:mutations={COUNT:((frame+0x34,0x123456FE,4),(frame+0x3C,0x1234FF80,4),
                (frame+0x3B,128,1),(frame+0x40,0x80000001,4)),LIST:((frame+0x2C,RESOURCE+8,4),
                (RESOURCE+12,7,1))}
            models=self.compare(memory,actor=actor,priority=3,phase=phase,
                list_present=present,mutations=mutations);cases+=1
            if descriptor==7:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.raw,self.fitted):
                        model=TransitionOracle(words,memory,actor=actor,priority=3,phase=phase,
                            list_present=present,mutations=mutations);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                        failed.append(model)
                    for model in failed[1:]:
                        for name in ('memory','events','calls'):self.assertEqual(getattr(model,name),getattr(failed[0],name))
                    prefixes+=1
        self.receipt('aliases-faults',cases=cases,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            definition_count_live_reread_and_zero_minus_one=True,retained_pointer_reload=True,
            incoming_argument_homes_live=True,strict_fault_prefixes=True,not_portable_C_fault_semantics=True)
        carriers=0
        for channel,priority,duration,amount,phase in itertools.product((0x100,0x123456FF),
                (0x100,0x103,0x12345680,0xFFFFFFFF),(0x10000,0x1234FFFF),
                (0,0x80000001),(0,8)):
            self.compare(fixture(),channel=channel,priority=priority,duration=duration,amount=amount,phase=phase)
            carriers+=1
        self.receipt('carriers',cases=carriers,executions=carriers*3,raw_high_O32_words_narrowed=True)

    def test_04_independent_links_and_actual_banked_caller(self):
        links=cases=caller_cases=0
        for entry,shift in ((screen.ENTRY,0),(0x15207FFC,0x200000),(0x15308004,0x300000)):
            symbols={name:address+shift for name,address in screen.SYMBOLS.items()};forms=[]
            for name in ('selected','fitted','original'):
                script=self.out/('link-%s-%X.ld'%(name,entry));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],
                    check=True,capture_output=True)
                forms.append(list(struct.unpack_from('>73I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(screen.normalize(forms[0]),forms[1]);self.assertEqual(forms[1],forms[2])
            for priority,channel,count in itertools.product((0,2,3,128,255),(0,8,255),(0,256,-1)):
                models=[]
                for words in forms:
                    model=TransitionOracle(words,fixture(),priority=priority,channel=channel,count=count,entry=entry)
                    model.counts={target+shift:n for target,n in COUNTS.items()}
                    model.returns={target+shift:value for target,value in model.returns.items()}
                    model.run();models.append(model)
                for model in models[1:]:
                    for name in ('memory','events','calls'):self.assertEqual(getattr(model,name),getattr(models[0],name))
                cases+=1
        before=(self.out/'before-elf').read_bytes();entry=0x1507EABC
        caller=list(struct.unpack_from('>28I',before,elf_slot_offset(before,entry,112)))
        for channel,same,count,descriptor,present in itertools.product((0,8,255),(False,True),
                (0,9,256,0xFFFFFFFF),(0,1,7),(False,True)):
            memory=reset.fixture(255,10,channel,same=same,descriptor=descriptor)
            models=[]
            for words in (self.original,self.raw,self.fitted):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(words)}
                model=reset.ResetOracle(caller,memory,entry=entry,connected=connected,count=count,list_present=present).run()
                expected=reset.reference(memory,entry=entry,connected_helper=True,count=count,list_present=present)
                self.assertEqual((model.memory,model.events,model.calls),expected);models.append(model)
            caller_cases+=1
        self.receipt('links-caller',independent_links=links,rebase_cases=cases,rebase_executions=cases*3,
            actual_caller_words=28,actual_target_words=73,caller_cases=caller_cases,caller_executions=caller_cases*3,
            other_two_callers_interface_only=True)

    def test_05_copied_owner_and_actual_padding_all_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True);objects.append(obj)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        old_guards=(self.out/'before-guards').read_bytes()
        guards=self.out/'owner-guards.csv';self.write_rows(guards,screen.guard_rows())
        added=guards.read_bytes().split(b'\n',1)[1];guards.write_bytes(old_guards+added)
        parsed=[]
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AB760',str(assembly),
                '--word-patches',str(guards if index else self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True);parsed.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(parsed[0],parsed[1])
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=len(warnings[0]),
            all_padded_bytes_functions_extents_relocations_exact=True,pools_exact=True)

    def test_06_effective_semantic_negative_controls(self):
        controls=(('priority','priority == 3','priority == 2',dict(priority=3,previous=255)),
            ('exclusive-count','channel < func_1507E968','channel <= func_1507E968',dict(count=8)),
            ('unsigned-count','channel < func_1507E968','channel < (u32)func_1507E968',dict(count=-1)),
            ('priority-signed','actor[0x71] < priority','((s8 *)actor)[0x71] < priority',dict(previous=255)),
            ('duration-byte','*(u16 *)(actor + 0x72) = duration','*(u8 *)(actor + 0x72) = duration',{}),
            ('animation-index','definition[4] - 1','definition[4]',{}),
            ('wrong-channel','actor[0x6F] = channel','actor[0x70] = channel',{}),
            ('cached-old','func_1507E908(actor, actor[0x6F])','func_1507E908(actor, oldChannel)',
                dict(mutations={COUNT:((ACTOR+0x6F,21,1),)})))
        public=lambda m:{a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}
        trace=lambda es:[e for e in es if e[0]=='CALL' or not STACK-0x500<=e[1]<STACK+0x100]
        for name,old,new,case in controls:
            inputs=case.copy();previous=inputs.pop('previous',1)
            memory=fixture(previous=previous);expected=reference(memory,**inputs)
            # Wrong longer bodies can overlap the retail callee VA; isolate their entry.
            with patch.object(screen,'ENTRY',0x1547E7E4):
                _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            wrong=TransitionOracle(words,memory,entry=0x1547E7E4,**inputs).run()
            self.assertNotEqual((public(wrong.memory),trace(wrong.events),wrong.calls),
                (public(expected[0]),trace(expected[1]),expected[2]),name)
        self.receipt('negatives',fresh_effective_IDO_controls=len(controls))

    def test_07_native32_actual_C_arbitration_and_callbacks(self):
        source=NATIVE+screen.SELECTED+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-count','channel < func_1507E968','channel <= func_1507E968'),
                ('native-index','definition[4] - 1','definition[4]')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=256*256*8*4,all_priority_byte_pairs=True,
            full_812_byte_actor_compared=True,typed_fifth_argument_ABI=True,effective_native_negatives=2)

    def test_08_whole_linked_ELF_target_symbol_and_recovered_progress_boundary(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text();before_source=(self.out/'before-source').read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('installation',installed=False);return
        self.assertEqual(source,screen.install(before_source))
        before_linker=(self.out/'before-undefined').read_bytes()
        self.assertEqual(hashlib.sha256(before_linker).hexdigest(),self.linker_hash)
        lines=before_linker.splitlines(keepends=True);assignment=b'func_1507E7E4 = 0x1507E7E4;'
        self.assertEqual(sum(line.strip()==assignment for line in lines),1)
        self.assertEqual((self.root/'conker/undefined_funcs_auto.txt').read_bytes(),
            b''.join(line for line in lines if line.strip()!=assignment))
        self.assertEqual((self.root/self.paths['rodata']).read_bytes(),(self.out/'before-rodata').read_bytes())
        guards=(self.root/self.paths['guards']).read_bytes();old_guards=(self.out/'before-guards').read_bytes()
        self.assertTrue(guards.startswith(old_guards))
        old_rows=list(csv.DictReader(old_guards.decode().splitlines()))
        new_rows=list(csv.DictReader(guards.decode().splitlines()))
        self.assertEqual(new_rows,old_rows+screen.guard_rows())
        before=(self.out/'before-elf').read_bytes();actual=(self.root/self.paths['elf']).read_bytes()
        expected=bytearray(before)
        before_symbol=installed.symbol_size_offset(before,screen.FUNCTION,screen.ENTRY)
        after_symbol=installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',before,before_symbol)[0],292)
        self.assertEqual(struct.unpack_from('>I',actual,after_symbol)[0],292)
        self.assertEqual(struct.unpack_from('>H',before,before_symbol+6)[0],0xFFF1)
        self.assertEqual(struct.unpack_from('>H',actual,after_symbol+6)[0],5)
        struct.pack_into('>H',expected,before_symbol+6,5)
        em,am=metadata(bytes(expected)),metadata(actual);self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5];expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        old=list(csv.reader((self.out/'before-progress').read_text().splitlines()))
        self.assertFalse(any(row[3]==screen.FUNCTION for row in old))
        indices=[i for i,row in enumerate(old) if row[3]=='func_1507E73C'];self.assertEqual(len(indices),1)
        index=indices[0];self.assertEqual(old[index][5:],['460','asm'])
        new=[row.copy() for row in old];new[index][5]='168'
        new.insert(index+1,['us','game','generated_AB760',screen.FUNCTION,str(screen.ENTRY),'292','c'])
        self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),new)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,all_linked_instruction_bytes_addresses_extents_exact=True,
            only_new_conversion_row=screen.FUNCTION,previous_assembly_extent_split='460 -> 168 + 292',
            newly_counted_function=1,converted_bytes_added=292,target_symbol_ABS_to_game_only=True,
            guards_prefix_byte_identical=True,
            only_five_guard_rows_added=True,protected_data=audit)


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
static u8 actor[812] __attribute__((aligned(16))),expected[812],definition[64],list[256];
static int plan,error,calls[5],count,descriptor,present,wantOld,wantAnimation,wantAmount;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(u16)==2)?1:-1];
s32 func_1507E968(u8 *a){if(a!=actor)error=1;calls[0]++;if(plan==1)a[0x6F]=21;return count;}
u8 *func_1507E908(u8 *a,s32 old){if(a!=actor || old!=wantOld)error=2;calls[1]++;return definition;}
u8 *func_1507E9F8(u8 *a,s32 *out){if(a!=actor || out)error=3;calls[2]++;if(plan==2)definition[4]=7;return present?list:0;}
void func_150302F0(s32 address,s32 animation){u8 *a=(u8 *)address;if(a!=actor || animation!=wantAnimation)error=4;calls[3]++;if(plan==3){a[0x71]=99;*(u16 *)(a+0x72)=0;}}
void func_1507E5C8(u8 *a,s32 amount){if(a!=actor || amount!=wantAmount)error=5;calls[4]++;}
'''
NATIVE_RUNNER=r'''
static int qualify(int oldPriority,int priority,int scenario,int mutation){
    int i,channel,current,def,remaining,duration,accepted,changed,counts[5]={0,0,0,0,0};
    plan=mutation;error=0;channel=(scenario*37)&255;current=(scenario&1)?channel:7;
    def=(scenario&2)?current:9;remaining=(scenario&4)?0:8;duration=(scenario&1)?remaining:9;
    count=(scenario&2)?channel:256;descriptor=(scenario&4)?0:1;present=(scenario&1)?0:1;
    wantAmount=(s32)0x81234567;wantOld=plan==1?21:current;wantAnimation=list[plan==2?6:0];
    for(i=0;i<812;i++)actor[i]=0xA5;
    actor[0x6F]=(u8)current;actor[0x70]=(u8)def;actor[0x71]=(u8)oldPriority;*(u16 *)(actor+0x72)=(u16)remaining;
    definition[4]=(u8)descriptor;for(i=0;i<5;i++)calls[i]=0;
    for(i=0;i<812;i++)expected[i]=actor[i];
    accepted=!(current==channel && oldPriority==priority && remaining==duration) &&
        (priority==3 || def==current || channel==current || remaining==0 || oldPriority<priority);
    changed=accepted && channel<count;
    if(accepted){counts[0]++;if(plan==1)expected[0x6F]=21;}
    if(changed){counts[1]++;if(descriptor){counts[2]++;if(present)counts[3]++;}
        expected[0x6F]=(u8)channel;*(u16 *)(expected+0x72)=(u16)duration;expected[0x71]=(u8)priority;counts[4]++;}
    func_1507E7E4(actor,(u8)channel,(u8)priority,(u16)duration,wantAmount);
    if(error)return error;
    for(i=0;i<5;i++)if(calls[i]!=counts[i])return 6;
    for(i=0;i<812;i++)if(actor[i]!=expected[i])return 7;
    return 0;
}
int run(void){int i,p,s,m,r;for(i=0;i<256;i++)list[i]=(u8)(i*17+35);
    for(i=0;i<256;i++)for(p=0;p<256;p++)for(s=0;s<8;s++)for(m=0;m<4;m++){
        r=qualify(i,p,s,m);if(r)return r;}return 0;}
'''


if __name__=='__main__':unittest.main()
