"""Direct matching and bounded semantic checks for the resource callback."""
import csv
import itertools
import struct
import subprocess
import unittest

from tools.experiments import game_resource_callback_151572d0_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests import game_resource_callback_151572d0_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put


class ResourceCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=match.prepare()

    def test_01_direct_words_and_relocations(self):
        self.assertEqual(len(self.state['words']),84)
        data,refs=match.payload(self.state['after'])
        self.assertEqual(len(data),336)
        self.assertEqual(len(refs),8)
        self.assertEqual((data,refs),match.payload(self.state['retail']))
        with (match.ROOT/'conker/retail_word_patches.us.csv').open(newline='') as f:
            self.assertFalse(any(row['function']==match.NAME for row in csv.DictReader(f)))

    def test_02_guest_reference_and_mutations(self):
        seen=set(); count=0
        for flags,first,second,results,timer,delta,mutation,phase in itertools.product(
                (0,1,0x20,0x21),(-1,0,1,2,3),(-1,0,1),((0,0),(0,1),(1,0),(1,1)),
                (-32768,-1,0,1,32767),(0,1,0xffff),(0,1),(0,8)):
            case=g.Case(flags,first,second,*results,timer,delta,mutation,phase)
            expected,calls=g.reference(case)
            model=g.Oracle(self.state['words'],case);model.run()
            self.assertEqual((g.public(model.memory),model.calls),(expected,calls),case)
            seen.update(model.visits);count+=1
        self.assertEqual(count,14400)
        self.assertEqual(sum(g.ENTRY+4*i in seen for i in range(84)),84)

    def test_03_sdk_native_reference_and_controls(self):
        from tools.tests import game_resource_callback_151572d0_native as native
        self.assertEqual(set(native.profiles),{'-O0','-O2','-O3'})
        for result in native.profiles.values():
            self.assertEqual((result['cases'],result['negative_controls'],result['UBSan']),(4320,4,True))

    def test_04_both_padders_and_independent_rebases(self):
        a,b=match.pad_both(self.state)
        self.assertEqual(same_functions(a,b),26)
        data,refs=match.payload(a)
        # Isolate just the target while preserving named relocations.
        source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
        for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
            for typ,symbol in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+symbol+'\n'
            source+='.word 0x%08X\n'%word
        source+='.size '+match.NAME+',.-'+match.NAME+'\n'
        isolated=match.assemble(source,'isolated')
        self.assertEqual(match.payload(isolated),(data,refs))
        names=sorted({name for entries in refs.values() for _,name in entries})
        for low in (0,0x7ffc,0x8000,0xfffc):
            symbols={name:(0x15010000+i*0x10000+low if name.startswith('func_') else
                           0x80010000+i*0x10000+low) for i,name in enumerate(names)}
            expected=bound_blob(data,refs,symbols)
            script=match.OUT/('rebase-%04x.ld'%low)
            script.write_text('SECTIONS { .text 0x151572D0 : SUBALIGN(4) { *(.text) } }\n')
            elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
            cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,
                 *['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(isolated)]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>84I',binary.read_bytes())),expected)

    def test_05_original_registered_walker(self):
        walker_entry,table,lists,depth,slots=0x151670C0,0x8008B4A8,0x800DCE50,0x800DD190,0x800DD198
        rom=self.state['rom'];walker=struct.unpack_from('>74I',rom,0x194570)
        live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual(tuple(live['func_151670C0']),walker)
        descriptors=rom[0x22ff68:0x22ff68+101*52]
        columns=[i for i in range(101) if struct.unpack_from('>I',descriptors,i*52)[0]==g.ENTRY]
        self.assertEqual(columns,[54,76,91])
        connected=dict(zip(range(g.ENTRY,g.ENTRY+84*4,4),self.state['words']))
        class Walker(FactoryOracle):
            def __init__(self,case,memory):
                super().__init__(walker,memory,case,entry=walker_entry,arguments=(),connected=connected)
                self.recorded=[]
            def record_call(self,target):
                self.recorded.append((target,(self.r[4],)))
            def hook(self,target):
                self.assert_target(target)
                g.effect(self.memory,target,self.case)
                answer=(self.case.ret_first if target in g.FIRST_FNS else
                        self.case.ret_second if target in g.SECOND_FNS else 0)
                for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
                for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
                self.f[:20]=[0xa5000000+i for i in range(20)]
                self.hi=self.lo=0xa5000000;self.r[2]=answer
            def assert_target(self,target):
                assert target in (*g.FIRST_FNS,*g.SECOND_FNS,g.UPDATE,g.RELEASE),hex(target)
        count=0
        for col,row,(flag,results,mutation,phase) in itertools.product(columns,(0,1),
                ((0,(1,1),0,0),(1,(0,1),1,8),(0x20,(1,0),0,0),(0x21,(1,1),1,8))):
            case=g.Case(flag,0,0,*results,5,1,mutation,phase)
            memory=g.fixture(case)
            for base,length in ((table,101*52),(lists,0x340),(depth,1),(slots,24)):
                memory.update({base+i:0 for i in range(length)})
            memory.update({table+i:b for i,b in enumerate(descriptors)})
            put(memory,lists+row*0x1a0+col*4,g.OBJ);put(memory,g.OBJ+8,0)
            expected,calls=g.reference(case)
            for address,value in g.public(memory).items():
                if address not in expected:expected[address]=value
            put(expected,g.OBJ+8,0);put(expected,slots+4,0)
            machine=Walker(case,memory);machine.run()
            self.assertEqual(g.public(machine.memory),expected)
            self.assertEqual(machine.recorded,[(g.ENTRY,(g.OBJ,))]+calls)
            self.assertEqual(machine.memory[depth],0);count+=1
        self.assertEqual(count,24)
