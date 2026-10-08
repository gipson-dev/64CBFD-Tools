"""One-argument callback transport, embedded pointer and real indirect dispatch."""

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

from tools.experiments import game_record_embedded_callback_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_point_transform_match import put, read

HELPER = screen.SYMBOLS['func_151D8C00']
ACTOR, TABLE = 0x20000, 0x8008FCC0
CALLER, CALLER_ROM, TABLE_ROM = 0x151D8A74, 0x205F24, 0x234780
RESULTS = (0,1,255,256,0x7FFFFFFF,0x80000000,0xFFFFFF80,0xFFFFFFFF)
OWNER = 'conker/src/game/generated_205C90.c'


def fixture(actor=None, phase=0):
    memory = {prior.STACK+i:0xA5 for i in range(-0x60,0x100)}
    if actor is not None:
        memory.update({actor+i:0xA5 for i in range(0x40)})
    return memory


def effects(actor, embedded, stack, mode, result):
    if mode == 1:
        return ((actor+0x12,result,1),(embedded,0x12345678,4),(embedded+0x14,result^255,1))
    if mode == 2:
        return ((stack+0x18,0x87654321,4),(stack+0x1C,0,4),(stack,0xCAFEBABE,4),(stack+4,result,4))
    return ()


class CallbackOracle(TriangleOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, result=0, mode=0,
                 entry=screen.ENTRY, helper=HELPER, connected=None, tail=False):
        super().__init__(words,memory,entry=entry,arguments=(actor,),phase=phase,connected=connected,tail=tail)
        self.result,self.mode,self.helper = result,mode,helper

    def execute(self,word):
        if word >> 26 == 32:
            CopyOracle.execute(self,word)
        else:
            super().execute(word)

    def record_call(self,target):
        if target in self.code and target != self.helper:
            self.calls.append((target,self.r[4]))
        else:
            assert target == self.helper, ('unexpected helper',hex(target))
            self.calls.append((target,self.r[4],self.r[5]))

    def hook(self,target):
        assert target == self.helper
        actor,embedded,stack=self.r[4],self.r[5],self.r[29]
        for address,value,size in effects(actor,embedded,stack,self.mode,self.result):
            self.put(address&0xFFFFFFFF,value,size)
        if self.mode == 3:
            del self.memory[stack+0x14]
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.r[2]=self.result
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameRecordEmbeddedCallbackTests(unittest.TestCase):
    run_host = prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-embedded-callback-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>8I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,actor=ACTOR,phase=0,result=0,mode=0,mapped=False):
        memory=fixture(actor if mapped else None,phase)
        expected=memory.copy()
        put(expected,prior.STACK+phase-4,0xDEAD0000)
        for address,value,size in effects(actor,(actor+0x18)&0xFFFFFFFF,prior.STACK+phase-0x18,mode,result):
            put(expected,address&0xFFFFFFFF,value,size)
        models=[CallbackOracle(w,memory,actor,phase,result,mode).run() for w in (self.words,self.retail)]
        for model in models:
            self.assertEqual(model.calls,[(HELPER,actor,(actor+0x18)&0xFFFFFFFF)])
            self.assertEqual((model.memory,model.r[2]),(expected,result))
        self.assertEqual((models[0].r,models[0].f,models[0].events),(models[1].r,models[1].f,models[1].events))
        return models

    def test_01_complete_direct_slot_void_contract_and_call_relocation(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(8,0x18,0))
        self.assertEqual(self.words,self.retail)
        self.assertEqual(self.record['relocations'],{8:[('R_MIPS_26','func_151D8C00')]})
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.assertTrue(screen.SELECTED.startswith('void func_151D8BE0(u8 *record)'))
        self.receipt('slot',dict(words=8,bytes=32,frame=0x18,differences=0,guards_added=0,
            void_C_return_contract=True,forwarded_guest_V0_is_instruction_evidence_only=True))

    def test_02_pointer_patterns_results_and_saved_register_lifetime(self):
        seen,cases=set(),0
        upper=(0,0x7FFF0000,0x80000000,0xFFFF0000)
        for low,phase in itertools.product(range(65536),(0,8)):
            actor=upper[(low>>12)&3]|low
            for model in self.compare(actor,phase,RESULTS[low&7]):
                seen.update(model.visits)
            cases+=1
        patterns=(0,1,3,0x7FFFFFE8,0x7FFFFFFF,0x80000000,0xFFFF7FFC,0xFFFFFFE7,0xFFFFFFE8,0xFFFFFFFC,0xFFFFFFFF)
        for actor,result,phase in itertools.product(patterns,RESULTS,(0,8)):
            for model in self.compare(actor,phase,result):
                seen.update(model.visits)
            cases+=1
        self.assertEqual(seen,set(range(screen.ENTRY,screen.ENTRY+32,4)))
        self.receipt('guest',dict(cases=cases,exhaustive_low16_patterns=65536,upper_patterns=4,results=8,
            SP_phases=2,all_8_words_reached=True,complete_selected_retail_GP_FP_trace_memory_equal=True,
            raw_null_wrap_and_unaligned_pointer_transport_not_portable_C_pointer_promises=True,
            helper_is_controlled_interface_not_complete_callee=True))

    def test_03_callback_mutations_stack_home_aliases_and_required_stack_faults(self):
        cases=0
        for actor,phase,mode,result in itertools.product((ACTOR,prior.STACK+8,prior.STACK+0x10),
                (0,8),(1,2),RESULTS):
            self.compare(actor,phase,result,mode,mapped=True)
            cases+=1
        faults=0
        for phase,index in itertools.product((0,8),range(4)):
            memory=fixture()
            del memory[prior.STACK+phase-4+index]
            models=[CallbackOracle(w,memory,phase=phase) for w in (self.words,self.retail)]
            for model in models:
                with self.assertRaises(AssertionError):
                    model.run()
                self.assertEqual(model.calls,[])
            self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
            faults+=1
        for phase in (0,8):
            models=[CallbackOracle(w,fixture(),phase=phase,mode=3) for w in (self.words,self.retail)]
            for model in models:
                with self.assertRaises(AssertionError):
                    model.run()
                self.assertEqual(model.calls,[(HELPER,ACTOR,ACTOR+0x18)])
            self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
            faults+=1
        self.receipt('gates',dict(callback_alias_cases=cases,required_stack_fault_prefixes=faults,
            incoming_home_mutations_do_not_change_captured_arguments=True,
            arbitrary_private_saved_RA_aliases_and_hardware_not_claimed=True))

    def test_04_actual_native32_C_pointer_transport_and_canaries(self):
        source=(self.root/OWNER).read_text()
        selected=screen.SELECTED
        typed='void func_151D8C00(u8 *owner, RecordDistanceLevel *parameters);' in source
        if typed:
            selected=selected.replace('record + 0x18','(RecordDistanceLevel *)(record + 0x18)')
        self.fixture=r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef char widths[sizeof(void *)==4&&sizeof(s32)==4?1:-1];
typedef struct {float x,y,z,inner,width,inverseWidth;u8 player;} RecordDistanceLevel;
static u8 arena[0x10080] __attribute__((aligned(16)));static u8 *wanted;
static u32 result,mode,calls,error;
static s32 func_151D8C00(u8 *record,void *address){
    u8 *embedded=address;
    calls++;if(record!=wanted||embedded!=wanted+0x18)error=1;
    if(mode){record[0x12]=result;embedded[0]=0x5A;embedded[0x14]=result^255;}
    return (s32)result;
}
''' + selected + r'''
static void (*volatile invoke)(u8 *)=func_151D8BE0;
'''
        self.run_host('static const u32 stride=%d;\n'%(4 if typed else 1)+r'''u32 offset,p,i,count=0;
static const u32 results[8]={0,1,255,256,0x7FFFFFFF,0x80000000,0xFFFFFF80,0xFFFFFFFF};
for(offset=0;offset<65536;offset+=stride)for(p=0;p<8;p++)for(mode=0;mode<2;mode++){
    wanted=arena+16+offset;result=results[p];calls=error=0;
    for(i=0;i<96;i++)wanted[(s32)i-16]=0xA5;
    invoke(wanted);if(error||calls!=1)return 1;
    for(i=0;i<96;i++){
        u8 expected=0xA5;
        if(mode){if(i==16+0x12)expected=result;if(i==16+0x18)expected=0x5A;if(i==16+0x2C)expected=result^255;}
        if(wanted[(s32)i-16]!=expected)return 2;
    }
    count++;
}
if(count!=1048576/stride)return 3;
''')
        self.receipt('native',dict(cases=262144 if typed else 1048576,offsets=16384 if typed else 65536,result_patterns=8,mutation_modes=2,
            pointer_bytes=4,int_bytes=4,actual_complete_C_through_volatile_function_pointer=True,
            all_96_window_bytes_checked=True,valid_private_array_pointers_only=True,
            typed_embedded_parameter_cast=typed,required_parameter_alignment=4 if typed else None))

    def test_05_profiles_and_effective_compiled_controls(self):
        records,ordinary,negatives=[],0,0
        cases=((0,0,0xFFFFFFFF),(ACTOR,0,0),(ACTOR,8,0x80000000),(0xFFFFFFE8,0,0x12345678))
        forms=[(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            # Oversized controls must not overlap the retail helper address.
            helper=HELPER+0x10000
            elf=self.out/(name+'-control.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(self.out/'record-callback.ld'),
                '-e',screen.FUNCTION,'--defsym=func_151D8C00=0x%X'%helper,
                '-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
            words=list(struct.unpack_from('>%dI'%record['body_words'],sections(elf)['.text'][1]))
            outcomes=[]
            for actor,phase,result in cases:
                try:
                    model=CallbackOracle(words,fixture(),actor,phase,result,helper=helper).run()
                    equal=model.calls==[(helper,actor,(actor+0x18)&0xFFFFFFFF)] and model.r[2]==result
                except (AssertionError,KeyError):
                    equal=False
                outcomes.append(equal)
                ordinary += not name.startswith('negative-')
            if name.startswith('negative-'):
                self.assertFalse(all(outcomes),name)
                negatives+=1
            else:
                self.assertTrue(all(outcomes),name)
        self.assertEqual(negatives,7)
        self.receipt('controls',dict(forms=len(records),ordinary_executions=ordinary,
            effective_negatives=negatives,measurements=records,
            controls_executed_with_symbolically_rebound_nonoverlapping_helper=helper,
            forced_zero_control_rejected_for_emitted_V0_not_portable_void_return_contract=True))

    def test_06_copied_owner_padder_and_independent_entry_helper_links(self):
        source=(self.root/OWNER).read_text()
        selected=screen.SELECTED
        if 'void func_151D8C00(u8 *owner, RecordDistanceLevel *parameters);' in source:
            selected=selected.replace('record + 0x18','(RecordDistanceLevel *)(record + 0x18)')
        if selected in source:
            source=source.replace(selected,screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        objects=[]
        for name,body in (('baseline',source),('selected',source.replace(screen.ORIGINAL,selected))):
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
        self.assertEqual(text[target['value']:target['value']+32],isolated[:32])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+32},isolated_rel)
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
        self.assertEqual(functions[screen.FUNCTION]['size'],32)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        bindings=[(screen.ENTRY,HELPER),(screen.ENTRY+0x01000004,HELPER)]
        bindings += [(screen.ENTRY,h) for h in (HELPER+4,0x15FFFFFC,0x10000000,0x1FFFFFFC)]
        cases=0
        for index,(entry,helper) in enumerate(bindings):
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                '--defsym=func_151D8C00=0x%X'%helper,'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>8I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            expected[2]=expected[2]&0xFC000000|helper>>2&0x3FFFFFF
            self.assertEqual(words,expected)
            for actor,result in ((0,0),(ACTOR,0x80000000),(0xFFFFFFE8,0xFFFFFFFF)):
                model=CallbackOracle(words,fixture(),actor,result=result,entry=entry,helper=helper).run()
                self.assertEqual((model.calls,model.r[2]),([(helper,actor,(actor+0x18)&0xFFFFFFFF)],result))
                cases+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,strict_diagnostics=0,
            relative_relocations_and_pools_unchanged=True,padding_and_generated_data=0,
            independent_links=len(bindings),rebased_executions=cases))

    def test_07_actual_callback_table_dispatch_and_skip_path(self):
        caller=list(struct.unpack_from('>10I',self.rom,CALLER_ROM))
        table=list(struct.unpack_from('>4I',self.rom,TABLE_ROM))
        self.assertEqual(table,[screen.ENTRY,0,0,0])
        self.assertEqual((caller[0],caller[8]),(0x82220014,0x0320F809))
        cases=0
        for selector,result,phase,mode in itertools.product((0,255),RESULTS,(0,8),range(3)):
            memory=fixture(ACTOR,phase)
            put(memory,ACTOR+0x14,selector,1)
            for i,value in enumerate(table):
                put(memory,TABLE+i*4,value)
            models=[]
            for body in (self.words,self.retail):
                code={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                model=CallbackOracle(caller+[0x03400008,0],memory,ACTOR,phase,result,mode,
                    entry=CALLER,connected=code,tail=True)
                model.r[16]=model.before[16]=ACTOR
                model.r[17]=model.before[17]=ACTOR
                model.r[26]=0xDEAD0000
                model.run()
                expected=[] if selector==255 else [(screen.ENTRY,ACTOR),(HELPER,ACTOR,ACTOR+0x18)]
                self.assertEqual(model.calls,expected)
                if selector==255:
                    self.assertFalse(any(e[0]=='R' and TABLE<=e[1]<TABLE+16 for e in model.events))
                models.append(model)
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                (models[1].r,models[1].f,models[1].events,models[1].memory))
            cases+=1
        self.receipt('caller-transport',dict(cases=cases,actual_prefix_words=10,actual_table_words=4,
            selector_zero_dispatch_and_minus_one_skip=True,actual_jalr_and_complete_wrapper_executed=True,
            callee_is_controlled_interface=True,synthetic_exit_boundary=True,complete_caller_workflow_not_claimed=True))

    def test_08_installed_or_original_assembly_and_guard_history(self):
        source=(self.root/OWNER).read_text()
        selected=screen.SELECTED
        if 'void func_151D8C00(u8 *owner, RecordDistanceLevel *parameters);' in source:
            selected=selected.replace('record + 0x18','(RecordDistanceLevel *)(record + 0x18)')
        installed=selected in source
        self.assertEqual(source.count(selected if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertFalse(any(row['function']==screen.FUNCTION for row in guards))
        functions,_,addresses=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION],functions[screen.FUNCTION]),(screen.ENTRY,self.retail))


if __name__ == '__main__':
    unittest.main()
