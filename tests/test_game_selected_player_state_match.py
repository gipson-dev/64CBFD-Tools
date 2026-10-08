"""Ordered selected-player predicate, lazy byte reads and bounded caller flow."""

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

from tools.experiments import game_selected_player_state_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_attachment_progress_match import ProgressReference
from tools.tests.test_game_point_transform_match import put, read

MAP, FLAGS = screen.SYMBOLS.values()
OWNER, DISABLE = 0x20000, 0x800E0B94
CALLER, CALLER_ROM, POSITIVE, EPILOGUE = 0x151D8868, 0x205D18, 0x151D88C0, 0x151D8A08
SOURCE = 'conker/src/game/generated_205C90.c'
UPPER = (0,0x7F000000,0x80000000,0xFFFF0000)
MAPPINGS = ((0,1,2,3),(3,2,1,0),(0,0,0,0),(3,3,3,3),
            (4,0,1,2),(0,4,1,2),(0,1,4,2),(0,1,2,4),(255,)*4,(128,0,255,3))


def flags_for(mask):
    return tuple((1,127,128,255)[(mask+i)&3] if mask&(1<<i) else 0 for i in range(4))


def public(memory):
    return {a:v for a,v in memory.items() if not prior.STACK-0x600<=a<prior.STACK+0x140}


def public_events(model):
    return [e for e in model.events if not prior.STACK-0x600<=e[1]<prior.STACK+0x140]


def fixture(mapping=(0,1,2,3),flags=(0,0,0,0),map_address=MAP,flag_address=FLAGS,full=False):
    memory={prior.STACK+i:0xA5 for i in range(12)}
    if full:
        for base in (map_address,flag_address):
            memory.update({(base+i)&0xFFFFFFFF:0xA5 for i in range(256)})
    for base,values in ((map_address,mapping),(flag_address,flags)):
        for i,value in enumerate(values):
            put(memory,(base+i)&0xFFFFFFFF,value,1)
    return memory


class PredicateReference(ProgressReference):
    def run(self,mask,map_address=MAP,flag_address=FLAGS):
        self.put(self.stack,mask)
        mask &= 255
        for player in range(4):
            if mask&(1<<player):
                index=self.get(map_address+player,1)
                if index>=4:
                    return 0
                if self.get(flag_address+index,1):
                    return 1
        return 0


class PredicateOracle(TriangleOracle):
    def __init__(self,words,memory,mask=0,phase=0,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(mask,),connected=connected)

    def record_call(self,target):
        assert target==screen.ENTRY,hex(target)
        self.calls.append((target,self.r[4]))


class GameSelectedPlayerStateTests(unittest.TestCase):
    run_host=prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-selected-player-state-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>34I',cls.rom,screen.ROM))
        cls.functions,_,cls.addresses=load_elf_functions(str(cls.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,mask=0,mapping=(0,1,2,3),flags=(0,0,0,0),phase=0,memory=None,
                map_address=MAP,flag_address=FLAGS,words=None,entry=screen.ENTRY):
        memory=fixture(mapping,flags,map_address,flag_address) if memory is None else memory
        reference=PredicateReference(memory,phase)
        result=reference.run(mask,map_address,flag_address)
        models=[PredicateOracle(w,memory,mask,phase,entry).run() for w in
                ((self.words,self.retail) if words is None else (words,))]
        for model in models:
            self.assertEqual((model.r[2],model.calls,model.events,model.memory),
                             (result,[],reference.events,reference.memory))
        if len(models)==2:
            self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models

    def test_01_complete_direct_slot_byte_contract_and_global_relocations(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(34,0,0))
        self.assertEqual(self.words,self.retail)
        self.assertEqual(self.record['relocations'],{
            12:[('R_MIPS_HI16','D_800BE944')],16:[('R_MIPS_HI16','D_80084060')],
            20:[('R_MIPS_LO16','D_80084060')],24:[('R_MIPS_LO16','D_800BE944')]})
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.receipt('slot',dict(words=34,bytes=136,frame=0,differences=0,guards_added=0,
            byte_argument_and_incoming_word_home=True,normalized_integer_returns=(0,1),global_relocations=4))

    def test_02_masks_mapping_bytes_flag_bytes_and_all_word_coverage(self):
        seen,counts=set(),[0,0,0,0]
        for mask,value,slot,pattern in itertools.product(range(16),range(256),range(4),range(4)):
            mapping=list((0,1,2,3))
            mapping[slot]=value
            raw=UPPER[(value+slot)&3]|mask|(value&0xF0)
            flags=((0,0,0,0),(1,0,0,0),(0,128,0,255),(255,255,255,255))[pattern]
            for model in self.compare(raw,mapping,flags,phase=(pattern&1)*8):
                seen.update(model.visits)
            counts[0]+=1
        for mask,mapping,state in itertools.product(range(256),MAPPINGS,range(16)):
            for model in self.compare(UPPER[state&3]|mask,mapping,flags_for(state),phase=(state&1)*8):
                seen.update(model.visits)
            counts[1]+=1
        for mask,slot,index,value in itertools.product(range(16),range(4),range(4),range(256)):
            mapping=list((0,1,2,3))
            mapping[slot]=index
            flags=[0]*4
            flags[index]=value
            for model in self.compare(UPPER[(value+slot)&3]|mask,mapping,flags,phase=(value&1)*8):
                seen.update(model.visits)
            counts[2]+=1
        raw_masks=(0,1,15,255,256,257,511,0x7FFFFFFF,0x80000000,0x800000F0,0xFFFFFF80,0xFFFFFFFF)
        for mask,mapping,state,phase in itertools.product(raw_masks,MAPPINGS[:3],range(16),(0,8)):
            for model in self.compare(mask,mapping,flags_for(state),phase):
                seen.update(model.visits)
            counts[3]+=1
        self.assertEqual(seen,set(range(screen.ENTRY,screen.ENTRY+136,4)))
        self.receipt('guest',dict(cases=sum(counts),mapping_byte_cases=counts[0],
            full_byte_mask_cases=counts[1],flag_byte_cases=counts[2],explicit_raw_argument_cases=counts[3],
            all_34_words_reached=True,SP_phases=2,upper_argument_patterns=4,
            independent_return_order_trace_memory_reference=True,complete_GP_FP_equality=True,
            raw_upper_register_patterns_are_instruction_evidence_not_extra_C_parameter_range=True))

    def test_03_lazy_reads_fault_prefixes_and_argument_home_aliases(self):
        for phase in (0,8):
            self.compare(0,memory={prior.STACK+phase+i:0xA5 for i in range(4)},phase=phase)
            memory={prior.STACK+phase+i:0xA5 for i in range(4)}
            put(memory,MAP,255,1)
            self.compare(15,memory=memory,phase=phase)
            memory={prior.STACK+phase+i:0xA5 for i in range(4)}
            put(memory,MAP,0,1)
            put(memory,FLAGS,255,1)
            self.compare(15,memory=memory,phase=phase)
        faults=0
        for phase in (0,8):
            for address in (*[prior.STACK+phase+i for i in range(4)],
                            *[MAP+i for i in range(4)],*[FLAGS+i for i in range(4)]):
                memory=fixture()
                del memory[address]
                reference=PredicateReference(memory,phase)
                with self.assertRaises(AssertionError):
                    reference.run(15)
                for words in (self.words,self.retail):
                    model=PredicateOracle(words,memory,15,phase)
                    with self.assertRaises(AssertionError):
                        model.run()
                    self.assertEqual((model.events,model.memory),(reference.events,reference.memory),hex(address))
                faults+=1
        self.receipt('gates',dict(lazy_empty_invalid_ready_cases=6,required_fault_prefixes=faults,
            skipped_players_and_future_entries_not_read=True,invalid_before_ready_and_ready_before_invalid=True,
            private_argument_home_aliases_are_qualified_in_rebased_tests_not_portable_C=True))

    def test_04_complete_native32_C_all_masks_and_readonly_canaries(self):
        self.fixture=r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef char widths[sizeof(void *)==4&&sizeof(int)==4?1:-1];
u8 D_80084060[256],D_800BE944[256];
''' + screen.SELECTED + r'''
static s32 (*volatile invoke)(u8)=func_151D87E0;
static int verify(u32 mask){
    u32 i;int wanted=0,result;u8 maps[4],flags[4];
    for(i=0;i<4;i++){maps[i]=D_80084060[i];flags[i]=D_800BE944[i];}
    for(i=0;i<4;i++)if((mask&255)&(1<<i)){
        if(maps[i]>=4)break;
        if(flags[maps[i]]){wanted=1;break;}
    }
    result=invoke((u8)mask);
    if(result!=wanted)return 1;
    for(i=0;i<4;i++)if(D_80084060[i]!=maps[i]||D_800BE944[i]!=flags[i])return 2;
    return 0;
}
static int canaries(void){
    u32 i;for(i=4;i<256;i++)if(D_80084060[i]!=0xA5||D_800BE944[i]!=0xA5)return 3;
    return 0;
}
'''
        self.run_host(r'''u32 mapping,mask,state,i,n,slot,index,value,cases=0;int error;
static const u8 choices[]={0,1,2,3,255},active[]={1,127,128,255};
for(i=0;i<256;i++)D_80084060[i]=D_800BE944[i]=0xA5;
for(mapping=0;mapping<625;mapping++)for(state=0;state<16;state++){
    n=mapping;
    for(i=0;i<4;i++){D_80084060[i]=choices[n%5];n/=5;D_800BE944[i]=state&(1<<i)?active[(state+i)&3]:0;}
    for(mask=0;mask<256;mask++){
        if((error=verify(mask|((mapping&3)*0x40000000u))))return error;
        cases++;
    }
    if((error=canaries()))return error;
}
for(slot=0;slot<4;slot++)for(index=0;index<4;index++)for(value=0;value<256;value++){
    for(i=0;i<4;i++){D_80084060[i]=i;D_800BE944[i]=0;}
    D_80084060[slot]=index;D_800BE944[index]=value;
    for(mask=0;mask<256;mask++){
        if((error=verify(mask)))return error;
        cases++;
    }
    if((error=canaries()))return error;
}
if(cases!=3608576)return 4;
''')
        self.receipt('native',dict(cases=3608576,all_byte_masks=True,all_625_mapping_combinations=True,
            all_16_state_bitsets=True,all_flag_bytes=True,pointer_int_bytes=4,
            complete_C_through_volatile_pointer=True,first_4_global_bytes_checked_every_call=True,
            remaining_504_global_canary_bytes_checked_every_configuration=True,defined_byte_conversions_only=True))

    def test_05_source_profile_controls_and_effective_compiled_negatives(self):
        cases=((0,(0,1,2,3),(0,0,0,0)),(1,(0,1,2,3),(1,0,0,0)),
               (2,(0,1,2,3),(0,128,0,0)),(3,(255,0,1,2),(1,1,1,1)),
               (3,(0,255,1,2),(1,0,0,0)),(1,(4,0,1,2),(0,0,0,0)),
               (8,(3,2,1,0),(255,0,0,0)),(255,(0,1,2,3),(0,0,255,0)))
        forms=[(name,body,'o2g3') for name,body in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        records,ordinary,negatives=[],0,0
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            outcomes=[]
            for mask,mapping,flags in cases:
                memory=fixture(mapping,flags,full=True)
                memory.update({prior.STACK+i:0xA5 for i in range(-0x100,0x100)})
                reference=PredicateReference(memory)
                wanted=reference.run(mask)
                model=PredicateOracle(words,memory,mask).run()
                outcomes.append((model.r[2],public(model.memory))==(wanted,public(reference.memory)))
                ordinary+=not name.startswith('negative-')
            if name.startswith('negative-'):
                self.assertFalse(all(outcomes),name)
                negatives+=1
            else:
                self.assertTrue(all(outcomes),name)
        self.assertEqual(negatives,7)
        self.receipt('controls',dict(forms=len(forms),ordinary_executions=ordinary,
                                    effective_negatives=negatives,measurements=records))

    def test_06_copied_owner_padder_independent_globals_and_aliases(self):
        source=(self.root/SOURCE).read_text()
        if screen.SELECTED in source:
            source=source.replace(screen.SELECTED,screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        candidate=source.replace(screen.ORIGINAL,screen.SELECTED)
        if screen.DECLARATIONS not in candidate:
            candidate=candidate.replace('void func_1501C17C',screen.DECLARATIONS+'void func_1501C17C')
        objects=[]
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
        self.assertEqual(text[target['value']:target['value']+136],isolated[:136])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+136},isolated_rel)
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
        self.assertEqual(functions[screen.FUNCTION]['size'],136)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        bindings=[(screen.ENTRY,MAP,FLAGS),(screen.ENTRY+0x1000004,MAP,FLAGS),
                  (screen.ENTRY,0x80007FFF,FLAGS),(screen.ENTRY,MAP,0x80008000),
                  (screen.ENTRY,0xFFFF7FFC,0x7FFF8000),(screen.ENTRY,MAP,MAP),
                  (screen.ENTRY,prior.STACK,FLAGS),(screen.ENTRY,MAP,prior.STACK)]
        executions=0
        for n,(entry,map_address,flag_address) in enumerate(bindings):
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%n)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            symbols={'D_80084060':map_address,'D_800BE944':flag_address}
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>34I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            for i,value in ((3,(flag_address+0x8000)>>16),(4,(map_address+0x8000)>>16),
                            (5,map_address),(6,flag_address)):
                expected[i]=expected[i]&0xFFFF0000|value&65535
            self.assertEqual(words,expected)
            for mask,mapping,flags in ((0,(0,1,2,3),(0,0,0,0)),(15,(0,1,2,3),(0,0,128,0)),
                                       (15,(255,0,1,2),(1,1,1,1)),(0xFFFFFF03,(0,255,1,2),(255,0,0,0))):
                self.compare(mask,mapping,flags,map_address=map_address,flag_address=flag_address,
                             words=words,entry=entry)
                executions+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,strict_diagnostics=0,
            pools_and_relative_relocations_unchanged=True,generated_padding_data=0,
            independent_links=len(bindings),rebased_executions=executions,
            global_global_and_private_home_aliases_are_emitted_instruction_evidence=True))

    def test_07_actual_caller_prefix_gate_and_real_epilogue(self):
        prefix=list(struct.unpack_from('>22I',self.rom,CALLER_ROM))
        epilogue=list(struct.unpack_from('>7I',self.rom,0x205EB8))
        self.assertEqual(self.functions['func_151D8868'][:22],prefix)
        self.assertEqual(self.functions['func_151D8868'][-7:],epilogue)
        cases=0
        for mask,mapping,state,disabled,phase in itertools.product(range(256),
                ((0,1,2,3),(255,0,1,2),(0,255,1,2),(255,)*4),(0,1,5,15),(0,1,255),(0,8)):
            memory=fixture(mapping,flags_for(state))
            memory.update({prior.STACK+i:0xA5 for i in range(-0x100,0x100)})
            memory.update({OWNER+i:0xA5 for i in range(64)})
            put(memory,OWNER+5,mask,1)
            put(memory,DISABLE,disabled,1)
            if disabled:
                del memory[OWNER+5]
                wanted=0
                events=[('R',DISABLE,1,disabled)]
                calls=[]
            else:
                ref=PredicateReference(memory,phase-0x30)
                wanted=ref.run(mask)
                events=[('R',DISABLE,1,0),('R',OWNER+5,1,mask),
                        *[e for e in ref.events if not prior.STACK-0x600<=e[1]<prior.STACK+0x140]]
                calls=[(screen.ENTRY,mask)]
            models=[]
            for body in (self.words,self.retail):
                code=dict(zip(range(screen.ENTRY,screen.ENTRY+136,4),body))
                code.update(zip(range(EPILOGUE,EPILOGUE+28,4),epilogue))
                # Only the positive continuation is replaced; both exits use the real epilogue.
                code[POSITIVE]=0x08000000|(EPILOGUE>>2&0x3FFFFFF)
                code[POSITIVE+4]=0
                model=PredicateOracle(prefix,memory,OWNER,phase,entry=CALLER,connected=code).run()
                self.assertEqual((model.r[2],model.calls,public_events(model),public(model.memory)),
                                 (wanted,calls,events,public(memory)))
                models.append(model)
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                             (models[1].r,models[1].f,models[1].events,models[1].memory))
            cases+=1
        self.receipt('caller',dict(cases=cases,actual_prefix_words=22,actual_epilogue_words=7,
            complete_predicate_words=34,disable_skip_with_unmapped_owner_byte=True,
            actual_linked_prefix_epilogue_equal_retail=True,positive_continuation_synthetic_jump=True,
            complete_caller_gameplay_hardware_not_claimed=True))

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
