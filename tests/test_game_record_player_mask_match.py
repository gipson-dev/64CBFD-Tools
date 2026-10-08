"""Four-player live-mask dispatch, callback mutations and connected retail paths."""

import csv
import itertools
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_player_mask_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_attachment_progress_match import ProgressReference
from tools.tests.test_game_point_transform_match import put, read

HELPER = screen.SYMBOLS['func_1501C17C']
OWNER, MAP, STATE = 0x20000, 0x80084060, 0x800BE93C
SOURCE = 'conker/src/game/generated_205C90.c'
CALLERS = ((0x151D8B88,0x206038,0x15169804),(0x151D8BB4,0x206064,0x15169824))
MAPPINGS = tuple((n,)*4 for n in (0,1,2,3,4,127,128,255)) + ((0,1,2,3),(3,2,1,0))


def public(memory):
    return {a:v for a,v in memory.items() if not prior.STACK-0x600<=a<prior.STACK+0x140}


def public_events(model):
    return [e for e in model.events if e[0]=='CALL' or not prior.STACK-0x600<=e[1]<prior.STACK+0x140]


def fixture(mask=15,owner=OWNER,mapping=(0,1,2,3)):
    memory={prior.STACK+i:0xA5 for i in range(-0x100,0x100)}
    for base,length in ((MAP,256),(STATE-32,96),(owner,64)):
        memory.update({base+i:0xA5 for i in range(length)})
    for i,value in enumerate(mapping):
        put(memory,MAP+i,value,1)
    for i in range(4):
        put(memory,STATE+i,0x5A+i,1)
    put(memory,owner+0x12,mask^255,1)
    put(memory,owner+0x13,mask,1)
    return memory


def effects(owner,player,call,mode,schedule):
    if mode==1 and call==1:
        mask=schedule&255
    elif mode==2:
        mask=(schedule>>(player*4)&15)|(schedule>>8&0xF0)
    else:
        return ()
    return ((owner+0x12,player^0x5A,1),(owner+0x13,mask,1))


class MaskReference(ProgressReference):
    def put(self,address,value,size=1):
        value &= (1<<(size*8))-1
        self.events.append(('W',address,size,value))
        assert all(address+i in self.memory for i in range(size)),('unmapped store',address,size)
        put(self.memory,address,value,size)

    def run(self,owner=OWNER,mode=0,schedule=0,real=False):
        calls=[]
        for player in range(4):
            mask=self.get(owner+0x13,1)
            if mask&(1<<player):
                calls.append((HELPER,player))
                self.events.append(('CALL',HELPER,(player,)))
                if real:
                    index=self.get(MAP+player,1)
                    if index<4:
                        self.put(STATE+index,0)
                else:
                    for address,value,size in effects(owner,player,len(calls),mode,schedule):
                        self.put(address,value,size)
        return calls


class MaskOracle(TriangleOracle):
    def __init__(self,words,memory,owner=OWNER,phase=0,mode=0,schedule=0,
                 entry=screen.ENTRY,helper=HELPER,connected=None,second=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(owner,),connected=connected)
        self.owner,self.mode,self.schedule=owner,mode,schedule
        self.helper,self.second=helper,second
        self.helper_calls=0

    def record_call(self,target):
        if target==self.helper:
            self.helper_calls+=1
            self.calls.append((HELPER,self.r[4]))
            self.events.append(('CALL',HELPER,(self.r[4],)))
        elif target==screen.ENTRY:
            self.calls.append((target,self.r[4]))
        else:
            assert target==self.second,hex(target)
            self.calls.append((target,self.r[4]))

    def hook(self,target):
        if target==self.helper:
            player=self.r[4]
            assert 0<=player<=255
            for address,value,size in effects(self.owner,player,self.helper_calls,self.mode,self.schedule):
                self.put(address,value,size)
            if self.mode==3:
                del self.memory[self.owner+0x13]
            if self.mode==4 and self.helper_calls==1:
                del self.memory[self.r[29]+0x1C]
            if self.mode==5:
                self.put(prior.STACK,OWNER+0x100,4)
        else:
            assert target==self.second
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.r[2]=0x11223344
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameRecordPlayerMaskTests(unittest.TestCase):
    run_host=prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-player-mask-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>25I',cls.rom,screen.ROM))
        cls.callee=list(struct.unpack_from('>13I',cls.rom,0x4962C))
        cls.functions,_,cls.addresses=load_elf_functions(str(cls.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,mask=15,schedule=0,mode=0,phase=0,owner=OWNER,mapping=(0,1,2,3),real=False):
        memory=fixture(mask,owner,mapping)
        ref=MaskReference(memory,phase)
        expected=ref.run(owner,mode,schedule,real)
        connected=dict(zip(range(HELPER,HELPER+52,4),self.callee)) if real else None
        models=[MaskOracle(words,memory,owner,phase,mode,schedule,connected=connected).run()
                for words in (self.words,self.retail)]
        for model in models:
            self.assertEqual((model.calls,public_events(model),public(model.memory)),
                             (expected,ref.events,public(ref.memory)))
            self.assertEqual(model.r[2],4)
        self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                         (models[1].r,models[1].f,models[1].events,models[1].memory))
        return models

    def test_01_complete_direct_slot_void_contract_and_relocation(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(25,0x20,0))
        self.assertEqual(self.words,self.retail)
        self.assertEqual(self.record['relocations'],{0x34:[('R_MIPS_26','func_1501C17C')]})
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.assertTrue(screen.SELECTED.startswith('void func_151D8B24(u8 *owner)'))
        self.receipt('slot',dict(words=25,bytes=100,frame=0x20,differences=0,guards_added=0,
            void_C_contract=True,retail_V0_four_is_instruction_evidence_only=True))

    def test_02_byte_masks_mutation_pairs_schedules_and_coverage(self):
        seen,cases=set(),0
        for mask,new_mask,phase in itertools.product(range(256),range(256),(0,8)):
            for model in self.compare(mask,new_mask,mode=1,phase=phase):
                seen.update(model.visits)
            cases+=1
        for schedule in range(65536):
            mask=15|(schedule>>8&0xF0)
            for model in self.compare(mask,schedule,mode=2,phase=(schedule&1)*8):
                seen.update(model.visits)
            cases+=1
        for mask,phase in itertools.product(range(256),(0,8)):
            for model in self.compare(mask,phase=phase):
                seen.update(model.visits)
            cases+=1
        self.assertEqual(seen,set(range(screen.ENTRY,screen.ENTRY+100,4)))
        self.receipt('guest',dict(cases=cases,all_initial_updated_byte_mask_pairs=65536,
            all_post_callback_nibble_schedules=65536,static_cases=512,SP_phases=2,
            complete_25_words_reached=True,independent_ordered_public_reference=True,
            complete_selected_retail_GP_FP_trace_memory_equal=True,
            owner_captured_and_mask_reloaded_after_callbacks=True))

    def test_03_required_reads_saves_and_post_callback_fault_prefixes(self):
        faults=0
        for phase in (0,8):
            for address in (OWNER+0x13,prior.STACK+phase-4,prior.STACK+phase-8,prior.STACK+phase-12):
                memory=fixture()
                del memory[address]
                models=[MaskOracle(w,memory,phase=phase) for w in (self.words,self.retail)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                    self.assertEqual(model.calls,[])
                self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
                faults+=1
            for mode in (3,4):
                models=[MaskOracle(w,fixture(),phase=phase,mode=mode) for w in (self.words,self.retail)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                self.assertEqual((models[0].calls,models[0].events,models[0].memory),
                                 (models[1].calls,models[1].events,models[1].memory))
                faults+=1
        self.receipt('gates',dict(required_fault_prefixes=faults,SP_phases=2,
            second_mask_read_and_saved_RA_reload_after_callbacks_checked=True,
            arbitrary_saved_register_aliases_and_hardware_fault_behavior_not_claimed=True))

    def test_04_actual_native32_C_dynamic_masks_and_canaries(self):
        self.fixture=r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef char widths[sizeof(void *)==4&&sizeof(int)==4?1:-1];
static u8 arena[64],expected[64],calls[4],wanted[4];static u32 count,mode,schedule;
void func_1501C17C(u8 player){
    u8 *owner=arena+16;u32 mask;
    if(count<4)calls[count]=player;
    count++;
    if(mode==1&&count==1)mask=schedule&255;
    else if(mode==2)mask=(schedule>>(player*4)&15)|(schedule>>8&0xF0);
    else return;
    owner[0x12]=player^0x5A;owner[0x13]=mask;
}
''' + screen.SELECTED + r'''
static void (*volatile invoke)(u8 *)=func_151D8B24;
static int check(u32 initial){
    u32 i,n=0;u8 mask=initial;
    for(i=0;i<64;i++)arena[i]=expected[i]=0xA5;
    arena[16+0x12]=expected[16+0x12]=initial^255;
    arena[16+0x13]=expected[16+0x13]=initial;
    count=0;
    for(i=0;i<4;i++)if(mask&(1<<i)){
        wanted[n++]=i;
        if(mode==1&&n==1)mask=schedule;
        else if(mode==2)mask=(schedule>>(i*4)&15)|(schedule>>8&0xF0);
        else continue;
        expected[16+0x12]=i^0x5A;expected[16+0x13]=mask;
    }
    invoke(arena+16);if(count!=n)return 1;
    for(i=0;i<n;i++)if(calls[i]!=wanted[i])return 2;
    for(i=0;i<64;i++)if(arena[i]!=expected[i])return 3;
    return 0;
}
'''
        self.run_host(r'''u32 mask,cases=0;int error;
mode=0;for(mask=0;mask<256;mask++){if((error=check(mask)))return error;cases++;}
mode=1;for(mask=0;mask<256;mask++)for(schedule=0;schedule<256;schedule++){
    if((error=check(mask)))return error;
    cases++;
}
mode=2;for(mask=0;mask<16;mask++)for(schedule=0;schedule<65536;schedule++){
    if((error=check(mask|(schedule>>8&0xF0))))return error;
    cases++;
}
if(cases!=1114368)return 4;
''')
        self.receipt('native',dict(cases=1114368,static_masks=256,byte_mutation_pairs=65536,
            initial_low_nibbles=16,all_post_callback_nibble_schedules=65536,pointer_int_bytes=4,
            actual_complete_C_through_volatile_pointer=True,all_64_canary_bytes_checked=True,
            valid_byte_array_pointers_only=True))

    def test_05_compiled_source_profile_controls_and_effective_negatives(self):
        forms=[(name,body,'o2g3') for name,body in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        cases=((0,0,0),(1,0,0),(8,0,0),(15,0,0),(128,0,0),(255,0,0),(15,1,0),(1,1,8))
        records,ordinary,negatives=[],0,0
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            outcomes=[]
            for mask,mode,schedule in cases:
                memory=fixture(mask)
                reference=MaskReference(memory)
                calls=reference.run(mode=mode,schedule=schedule)
                model=MaskOracle(words,memory,mode=mode,schedule=schedule).run()
                outcomes.append((model.calls,public(model.memory))==(calls,public(reference.memory)))
                ordinary+=not name.startswith('negative-')
            if name.startswith('negative-'):
                self.assertFalse(all(outcomes),name)
                negatives+=1
            else:
                self.assertTrue(all(outcomes),name)
        self.assertEqual(negatives,7)
        self.receipt('controls',dict(forms=len(forms),ordinary_executions=ordinary,
                                    effective_negatives=negatives,measurements=records))

    def test_06_copied_owner_padder_and_independent_links(self):
        source=(self.root/SOURCE).read_text()
        if screen.SELECTED in source:
            source=source.replace(screen.SELECTED,screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        objects=[]
        candidate=source.replace(screen.ORIGINAL,screen.SELECTED).replace(
            'func_151D8B24(arg0);','func_151D8B24((u8 *)arg0);')
        if screen.DECLARATIONS not in candidate:
            candidate=candidate.replace('void func_15169260',screen.DECLARATIONS+'void func_15169260')
        for name,body in (('baseline',source),('selected',candidate)):
            obj,warnings=compile_owner(self.root,self.out,body,'owner-'+name)
            self.assertEqual(warnings,[])
            processed=self.out/('owner-'+name+'-postprocessed.o')
            shutil.copyfile(obj,processed)
            subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(processed.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(processed)
        old,previous,old_rel=parse_object(objects[0])
        text,current,rel=parse_object(objects[1])
        self.assertEqual(current.keys(),previous.keys())
        for name,function in current.items():
            if name==screen.FUNCTION:
                continue
            before=previous[name]
            self.assertEqual(text[function['value']:function['value']+function['size']],
                             old[before['value']:before['value']+before['size']],name)
            self.assertEqual({o-function['value']:r for o,r in rel.items() if function['value']<=o<function['value']+function['size']},
                             {o-before['value']:r for o,r in old_rel.items() if before['value']<=o<before['value']+before['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        target=current[screen.FUNCTION]
        isolated,_,isolated_rel=parse_object(self.out/'selected.o')
        self.assertEqual(text[target['value']:target['value']+100],isolated[:100])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+100},isolated_rel)
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/205C90.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_205C90')
        start=assembly.index('.type %s, @function'%screen.FUNCTION)
        end=assembly.index('.size %s, . - %s'%(screen.FUNCTION,screen.FUNCTION),start)
        end=assembly.index('\n',end)+1
        self.assertNotIn('.space',assembly[end:assembly.find('.type ',end)])
        asm,obj=self.out/'padded.s',self.out/'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n'%screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        _,functions,relocations=parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'],100)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        bindings=[(screen.ENTRY,HELPER),(screen.ENTRY+0x1000004,HELPER),
                  (screen.ENTRY,HELPER+4),(screen.ENTRY,0x10000000),(screen.ENTRY,0x1FFFFFFC)]
        cases=0
        for index,(entry,helper) in enumerate(bindings):
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                '--defsym=func_1501C17C=0x%X'%helper,'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>25I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            expected[13]=expected[13]&0xFC000000|helper>>2&0x3FFFFFF
            self.assertEqual(words,expected)
            for mask,mode,schedule in ((0,0,0),(255,0,0),(15,1,8),(1,2,0xFFFF)):
                memory=fixture(mask)
                reference=MaskReference(memory)
                calls=reference.run(mode=mode,schedule=schedule)
                model=MaskOracle(words,memory,mode=mode,schedule=schedule,entry=entry,helper=helper).run()
                self.assertEqual((model.calls,public_events(model),public(model.memory)),
                                 (calls,reference.events,public(reference.memory)))
                cases+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,strict_diagnostics=0,
            pools_and_relative_relocations_unchanged=True,generated_padding_data=0,
            independent_links=len(bindings),rebased_executions=cases))

    def test_07_actual_clearer_aliases_and_complete_direct_callers(self):
        self.assertEqual(self.functions['func_1501C17C'],self.callee)
        cases=0
        for mask,mapping,owner,phase in itertools.product(range(256),MAPPINGS,
                (OWNER,*[STATE-0x13+i for i in range(4)]),(0,8)):
            self.compare(mask,phase=phase,owner=owner,mapping=mapping,real=True)
            cases+=1
        caller_cases=0
        for (entry,rom,second),mask,mapping,phase in itertools.product(CALLERS,range(256),
                ((0,1,2,3),(3,3,3,3),(255,4,128,0)),(0,8)):
            caller=list(struct.unpack_from('>11I',self.rom,rom))
            self.assertEqual(self.functions['func_%08X'%entry],caller)
            memory=fixture(mask,mapping=mapping)
            ref=MaskReference(memory,phase)
            calls=ref.run(real=True)
            models=[]
            for body in (self.words,self.retail):
                code=dict(zip(range(screen.ENTRY,screen.ENTRY+100,4),body))
                code.update(zip(range(HELPER,HELPER+52,4),self.callee))
                model=MaskOracle(caller,memory,phase=phase,entry=entry,connected=code,second=second).run()
                self.assertEqual(model.calls,[(screen.ENTRY,OWNER),*calls,(second,OWNER)])
                self.assertEqual((public_events(model),public(model.memory)),(ref.events,public(ref.memory)))
                self.assertEqual(model.r[2],0x11223344)
                models.append(model)
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                             (models[1].r,models[1].f,models[1].events,models[1].memory))
            caller_cases+=1
        # The dispatcher keeps its captured owner while its caller reloads a changed home.
        memory=fixture(15)
        for body in (self.words,self.retail):
            code=dict(zip(range(screen.ENTRY,screen.ENTRY+100,4),body))
            model=MaskOracle(list(struct.unpack_from('>11I',self.rom,CALLERS[0][1])),memory,
                mode=5,entry=CALLERS[0][0],connected=code,second=CALLERS[0][2]).run()
            self.assertEqual(model.calls,[(screen.ENTRY,OWNER),*[(HELPER,i) for i in range(4)],
                                          (CALLERS[0][2],OWNER+0x100)])
        self.receipt('connected',dict(actual_clearer_words=13,actual_clearer_alias_cases=cases,
            actual_complete_callers=2,caller_words_each=11,complete_caller_cases=caller_cases,
            captured_owner_and_caller_home_reload_cases=2,actual_linked_caller_clearer_equal_retail=True,
            second_helpers_controlled_interfaces=True,full_gameplay_hardware_not_claimed=True))

    def test_08_installed_or_original_and_guard_history(self):
        source=(self.root/SOURCE).read_text()
        installed=screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertFalse(any(row['function']==screen.FUNCTION for row in guards))
        self.assertEqual((self.addresses[screen.FUNCTION],self.functions[screen.FUNCTION]),
                         (screen.ENTRY,self.retail))


if __name__=='__main__':
    unittest.main()
