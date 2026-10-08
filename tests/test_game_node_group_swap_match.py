"""Direct full-word group-key swapping, mutable list lifetime and caller transport."""

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

from tools.experiments import game_node_group_swap_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_attachment_progress_match import ProgressReference
from tools.tests.test_game_point_transform_match import put, read

HEAD = screen.SYMBOLS['D_800C3EE0']
NODES = tuple(0x10000+i*0x100 for i in range(8))
KEYS = (0,1,127,128,255,256,257,0x10080,0x100FF,0x7FFFFFFF,0x80000000,0xFFFFFF80,0xFFFFFFFF)
ARGS = (1,2)
CALLER, CALLER_ROM, ACTORS = 0x1506293C, 0x8FDEC, (0x20000,0x21000)


def fixture(groups=(1,2,3), order=None, full=False):
    memory = {prior.STACK+i:0xA5 for i in range(-0x40,0x40)}
    order = tuple(range(len(groups))) if order is None else order
    if full:
        for base,size in ((HEAD,0x60), *((node,0x60) for node in NODES[:len(groups)])):
            memory.update({base+i:0xA5 for i in range(size)})
    put(memory,HEAD,NODES[order[0]] if order else 0)
    for i,group in enumerate(groups):
        put(memory,NODES[i],group,1)
        put(memory,NODES[i]+1,group^255,1)
        put(memory,NODES[i]+2,0xA5A5,2)
        put(memory,NODES[i]+0x50,0)
    for i,index in enumerate(order):
        put(memory,NODES[index]+0x54,NODES[order[i+1]] if i+1<len(order) else 0)
    return memory


class SwapReference(ProgressReference):
    def put(self,address,value,size=1):
        value &= (1 << (size*8))-1
        self.events.append(('W',address,size,value))
        assert all(address+i in self.memory for i in range(size)), ('unmapped store',address,size)
        put(self.memory,address,value,size)

    def run(self,first=1,second=2,head=HEAD):
        first,second = first&0xFFFFFFFF,second&0xFFFFFFFF
        current = self.get(head)
        for _ in range(64):
            if not current:
                return 0
            group = self.get(current,1)
            following = self.get(current+0x54)
            if group == first:
                self.put(current,second)
            elif group == second:
                self.put(current,first)
            current = following
        raise AssertionError('finite fixture bound, not a production list limit')


class SwapOracle(TriangleOracle):
    def __init__(self,words,memory,args=ARGS,phase=0,entry=screen.ENTRY):
        super().__init__(words,memory,entry=entry,arguments=args,phase=phase)

    def record_call(self,target):
        raise AssertionError(('unexpected call',target))


def aliases():
    memory=fixture((),full=True)
    put(memory,HEAD,HEAD)
    put(memory,HEAD+0x54,NODES[0])
    memory.update({NODES[0]+i:0xA5 for i in range(0x60)})
    put(memory,NODES[0],255,1)
    put(memory,NODES[0]+0x54,0)
    result=[('head-owner',memory,(128,255))]
    memory=fixture((),full=True)
    memory.update({NODES[0]+i:0xA5 for i in range(0x60)})
    put(memory,HEAD,NODES[0])
    put(memory,NODES[0],1,1)
    put(memory,NODES[0]+4,2,1)
    put(memory,NODES[0]+0x54,NODES[0]+4)
    put(memory,NODES[0]+0x58,0)
    result.append(('overlapping-records',memory,(1,2)))
    parent=NODES[0]-0x54
    target=0xFF010300
    memory=fixture((),full=True)
    for base,size in ((parent,0xB4),(target,0x60),(0x10300,0x60)):
        memory.update({base+i:0xA5 for i in range(size)})
    put(memory,HEAD,NODES[0])
    put(memory,NODES[0],0x00010300)
    put(memory,NODES[0]+0x54,parent)
    put(memory,parent,3,1)
    put(memory,target,255,1)
    put(memory,target+0x54,0)
    result.append(('live-future-link',memory,(0,255)))
    return result


class GameNodeGroupSwapMatchTests(unittest.TestCase):
    run_host = prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        assert not any(prior.STACK-0x600 <= a < prior.STACK+0x140 for a in (*NODES,HEAD,*ACTORS))
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-node-group-swap-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>18I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,memory,args=ARGS,phase=0):
        reference=SwapReference(memory,phase)
        expected=reference.run(*args)
        models=[SwapOracle(w,memory,args,phase).run() for w in (self.words,self.retail)]
        for model in models:
            self.assertEqual((model.r[2],model.calls,model.events,model.memory),(expected,[],reference.events,reference.memory))
        self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models

    def test_01_direct_slot_void_contract_and_symbolic_global(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(18,0,0))
        self.assertEqual(self.words,self.retail)
        self.assertTrue(screen.SELECTED.startswith('void func_15033EC4(s32 first, s32 second)'))
        self.assertEqual(self.record['relocations'],{4:[('R_MIPS_HI16','D_800C3EE0')],8:[('R_MIPS_LO16','D_800C3EE0')]})
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.receipt('slot',dict(words=18,bytes=72,frame=0,raw_differences=0,guards_added=0,
            original_assembly_already_exact=True,void_C_contract=True,retail_V0_zero_is_instruction_evidence_only=True))

    def test_02_all_byte_keys_full_width_keys_masks_topologies_and_coverage(self):
        seen,counts=set(),[0,0,0]
        for first,second in itertools.product(range(256),repeat=2):
            for model in self.compare(fixture((first,second,first^255,second^255)),(first,second)):
                seen.update(model.visits)
            counts[0]+=1
        for first,second,group in itertools.product(KEYS,KEYS,range(256)):
            for model in self.compare(fixture((group,)),(first,second)):
                seen.update(model.visits)
            counts[1]+=1
        pairs=((0,255),(127,128),(128,128),(255,0),(256,1),(1,0x100FF))
        for pair,mask,order,phase in itertools.product(pairs,range(256),
                (tuple(range(8)),(3,0,7,2,5,1,6,4)),(0,8)):
            groups=tuple((pair[0] if mask&(1<<i) else pair[1])&255 for i in range(8))
            for model in self.compare(fixture(groups,order),pair,phase):
                seen.update(model.visits)
            counts[2]+=1
        for model in self.compare(fixture(()),(0xFFFFFFFF,0x80000000)):
            seen.update(model.visits)
        missing=sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY,screen.ENTRY+72,4))-seen)
        self.assertEqual(missing,[])
        self.receipt('guest',dict(cases=sum(counts)+1,byte_key_pairs=counts[0],full_word_cases=counts[1],
            mask_topology_cases=counts[2],key_patterns=len(KEYS),masks=256,topologies=2,SP_phases=2,
            missing_word_indices=missing,independent_access_order_and_full_GP_FP_trace_memory_equal=True,no_hooks=True))

    def test_03_lazy_head_required_read_faults_and_mutable_aliases(self):
        self.compare({HEAD+i:0 for i in range(4)},(0xFFFFFFFF,0x80000000))
        probes=[HEAD,NODES[0],*range(NODES[0]+0x54,NODES[0]+0x58),NODES[1],NODES[1]+0x54,NODES[2],NODES[2]+0x54]
        for address in probes:
            memory=fixture((1,2,3),full=True)
            del memory[address]
            reference=SwapReference(memory)
            with self.assertRaises(AssertionError):
                reference.run()
            for words in (self.words,self.retail):
                model=SwapOracle(words,memory)
                with self.assertRaises(AssertionError):
                    model.run()
                self.assertEqual((model.events,model.memory),(reference.events,reference.memory),hex(address))
        for _,memory,args in aliases():
            for phase in (0,8):
                self.compare(memory,args,phase)
        self.receipt('gates',dict(lazy_cases=1,fault_prefixes=len(probes),alias_layouts=len(aliases()),
            alias_executions=2*len(aliases()),head_captured_once_and_future_links_live=True,
            next_read_before_store_and_partial_writes_checked=True,read_only_hardware_mapping_and_arbitrary_private_aliases_not_claimed=True))

    def test_04_source_profiles_and_effective_compiled_negatives(self):
        records,negatives,ordinary=[],0,0
        cases=[(fixture(()),(0xFFFFFFFF,0x80000000)),(fixture((1,2,3),full=True),(1,2)),
            (fixture((128,128,3),full=True),(128,128)),(fixture((0,1,128),full=True),(256,1)),
            (fixture((128,255,0),full=True),(0xFFFFFF80,255)),*[(m,a) for _,m,a in aliases()]]
        forms=[(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            outcomes=[]
            for memory,args in cases:
                reference=SwapReference(memory)
                reference.run(*args)
                try:
                    model=SwapOracle(words,memory,args).run()
                    writes=[e for e in prior.public(model.events) if e[0]=='W']
                    expected=[e for e in prior.public(reference.events) if e[0]=='W']
                    equal=(model.calls,writes,prior.external_memory(model.memory)) == ([],expected,prior.external_memory(reference.memory))
                    if name=='selected':
                        self.assertEqual(model.events,reference.events)
                        self.assertEqual(model.r[2],0)
                except (AssertionError,KeyError):
                    equal=False
                outcomes.append(equal)
                ordinary += 'negative-' not in name
            if 'negative-' in name:
                self.assertFalse(all(outcomes),name)
                negatives+=1
            else:
                self.assertTrue(all(outcomes),name)
        self.assertEqual(negatives,7)
        self.receipt('controls',dict(forms=len(records),ordinary_executions=ordinary,effective_negatives=negatives,
            measurements=records,alternate_private_register_read_schedule_and_void_V0_not_claimed=True,
            selected_full_order_and_GP_FP_still_checked=True))

    def test_05_native32_exhaustive_byte_triples_full_keys_and_alias_canaries(self):
        self.fixture=r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef union {u8 b[0x60];u8 *pointer;} Node;
typedef struct {u8 b[0x300];} Block;
typedef char pointer_width[sizeof(void *)==4&&sizeof(s32)==4?1:-1];
static Node nodes[8],saved[8],expected[8],header,saved_header,expected_header;
static Block block __attribute__((aligned(256))),saved_block,expected_block;
#define D_800C3EE0 header.pointer
static u32 cases;
static const u32 keys[13]={0,1,127,128,255,256,257,0x10080,0x100FF,0x7FFFFFFF,0x80000000,0xFFFFFF80,0xFFFFFFFF};
static void copy(u8 *a,const u8 *b,u32 n){u32 i;for(i=0;i<n;i++)a[i]=b[i];}
static int equal(const u8 *a,const u8 *b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void fill(u8 *a,u32 n){u32 i;for(i=0;i<n;i++)a[i]=0xA5;}
static void setup(void){fill((u8 *)nodes,sizeof(nodes));fill(header.b,sizeof(header));fill(block.b,sizeof(block));}
''' + screen.SELECTED + r'''
static void (*volatile invoke)(s32,s32)=func_15033EC4;
static int single(u32 a,u32 b,u32 group){
    u32 wanted=group==a?(b&255):group==b?(a&255):group;
    nodes[0].b[0]=group;expected[0].b[0]=wanted;
    invoke((s32)a,(s32)b);cases++;
    return !equal(nodes[0].b,expected[0].b,sizeof(Node))||!equal(header.b,expected_header.b,sizeof(Node));
}
static void reference(u32 a,u32 b){
    u8 *cursor=D_800C3EE0,*next;u32 group;
    while(cursor){group=cursor[0];next=*(u8 **)(cursor+0x54);
        if(group==a)cursor[0]=b;else if(group==b)cursor[0]=a;cursor=next;}
}
static int general(u32 a,u32 b){
    copy((u8 *)saved,(u8 *)nodes,sizeof(nodes));copy(saved_header.b,header.b,sizeof(header));copy(saved_block.b,block.b,sizeof(block));
    reference(a,b);
    copy((u8 *)expected,(u8 *)nodes,sizeof(nodes));copy(expected_header.b,header.b,sizeof(header));copy(expected_block.b,block.b,sizeof(block));
    copy((u8 *)nodes,(u8 *)saved,sizeof(nodes));copy(header.b,saved_header.b,sizeof(header));copy(block.b,saved_block.b,sizeof(block));
    invoke((s32)a,(s32)b);cases++;
    return !equal((u8 *)nodes,(u8 *)expected,sizeof(nodes))||!equal(header.b,expected_header.b,sizeof(header))
        ||!equal(block.b,expected_block.b,sizeof(block));
}
'''
        for lower in range(0,256,32):
            extra=r'''
for(a=0;a<13;a++)for(b=0;b<13;b++)for(g=0;g<256;g++)if(single(keys[a],keys[b],g))return 2;
for(a=0;a<256;a++)for(mask=0;mask<256;mask++)for(order=0;order<2;order++){
    setup();
    for(i=0;i<8;i++){j=order?permutation[i]:i;k=i==7?8:(order?permutation[i+1]:i+1);
        nodes[j].b[0]=mask&(1u<<j)?a:a^255;*(u8 **)(nodes[j].b+0x54)=k==8?0:nodes[k].b;}
    D_800C3EE0=nodes[order?permutation[0]:0].b;if(general(a,a^255))return 3;
}
setup();D_800C3EE0=0;if(general(0xFFFFFFFF,0x80000000))return 4;
setup();D_800C3EE0=0;if(general(1,1))return 5;
setup();D_800C3EE0=header.b;*(u8 **)(header.b+0x54)=nodes[0].b;*(u8 **)(nodes[0].b+0x54)=0;
a=header.b[0];nodes[0].b[0]=a^255;if(general(a,a^255))return 6;
setup();D_800C3EE0=block.b;block.b[0]=1;block.b[4]=2;*(u8 **)(block.b+0x54)=block.b+4;*(u8 **)(block.b+0x58)=0;
if(general(1,2))return 7;
setup();D_800C3EE0=block.b+0x100;*(u8 **)(block.b+0x100)=block.b+0x180;*(u8 **)(block.b+0x154)=block.b+0xAC;
block.b[0xAC]=3;block.b[0x1C0]=0xC0;*(u8 **)(block.b+0x214)=0;
if(block.b[0x100]!=0x80)return 8;
if(general(0x80,0xC0))return 9;
''' if lower==0 else ''
            wanted=2097152+(174341 if lower==0 else 0)
            self.run_host('''u32 a,b,g,mask,order,i,j,k;
static const u32 permutation[8]={3,0,7,2,5,1,6,4};
setup();D_800C3EE0=nodes[0].b;*(u8 **)(nodes[0].b+0x54)=0;
copy(expected[0].b,nodes[0].b,sizeof(Node));copy(expected_header.b,header.b,sizeof(Node));
for(a=%d;a<%d;a++)for(b=0;b<256;b++)for(g=0;g<256;g++)if(single(a,b,g))return 1;
'''%(lower,lower+32)+extra+'if(cases!=%d)return 10;\n'%wanted)
        self.receipt('native',dict(cases=16951557,byte_triples=16777216,full_word_cases=43264,mask_topology_cases=131072,
            lazy_and_alias_cases=5,batches=8,pointer_bytes=4,int_bytes=4,actual_complete_C_via_volatile_function_pointer=True,
            every_byte_in_node_header_and_alias_buffers_checked=True,native_pointer_byte_endianness_used=True))

    def test_06_copied_owner_padder_and_independent_global_rebases(self):
        source = (self.root / 'conker/src/game/generated_5D2C0.c').read_text()
        if screen.SELECTED in source:
            source = source.replace(screen.SELECTED, screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        selected = source.replace(screen.ORIGINAL, screen.SELECTED)
        objects = []
        for name, body in (('baseline',source),('selected',selected)):
            obj, warnings = compile_owner(self.root,self.out,body,'owner-'+name)
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
        self.assertEqual(text[target['value']:target['value']+72],isolated[:72])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+72},isolated_rel)
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/5D2C0.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_5D2C0',rodata_symbol='jtbl_80096F40_game')
        start=assembly.index('.type %s, @function'%screen.FUNCTION)
        end=assembly.index('.size %s, . - %s'%(screen.FUNCTION,screen.FUNCTION),start)
        end=assembly.index('\n',end)+1
        self.assertNotIn('.space',assembly[end:assembly.find('.type ',end)])
        asm,obj=self.out/'padded.s',self.out/'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n'%screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        _,functions,relocations=parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'],72)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        bindings=[(screen.ENTRY,HEAD),(screen.ENTRY+0x01000004,HEAD)]
        bindings += [(screen.ENTRY,h) for h in (HEAD+4,HEAD+0x8004,0x7FFF7FFC,0xFFFF8000)]
        executions=0
        for index,(entry,head) in enumerate(bindings):
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                '--defsym=D_800C3EE0=0x%X'%head,'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>18I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            expected[1]=expected[1]&0xFFFF0000|((head+0x8000)>>16)&65535
            expected[2]=expected[2]&0xFFFF0000|head&65535
            self.assertEqual(words,expected)
            for groups in ((),(1,),(1,2,3)):
                memory=fixture(groups)
                value=read(memory,HEAD)
                for i in range(4):
                    del memory[HEAD+i]
                put(memory,head,value)
                reference=SwapReference(memory)
                result=reference.run(head=head)
                model=SwapOracle(words,memory,entry=entry).run()
                self.assertEqual((model.r[2],model.events,model.memory),(result,reference.events,reference.memory))
                executions+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,relative_relocations_and_pools_unchanged=True,
            strict_diagnostics=0,padding_and_generated_data=0,independent_links=len(bindings),rebased_executions=executions))


    def test_07_installed_or_original_assembly_and_guard_history(self):
        source=(self.root/'conker/src/game/generated_5D2C0.c').read_text()
        installed=screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertFalse(any(row['function']==screen.FUNCTION for row in guards))
        functions,_,addresses=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION],functions[screen.FUNCTION]),(screen.ENTRY,self.retail))

    def test_08_actual_caller_unsigned_key_loads_saves_and_jal_transport(self):
        caller=list(struct.unpack_from('>7I',self.rom,CALLER_ROM))
        self.assertEqual(caller[:2],[0x9205003B,0x9224003B])
        self.assertEqual(caller[5],0x0D40CFB1)
        cases=0
        for pair,groups,phase in itertools.product(((0,0),(0,255),(128,255),(255,128),(128,128)),
                ((),(0,),(128,),(255,),(128,255,7)),(0,8)):
            memory=fixture(groups,full=True)
            for base,key in zip(ACTORS,(pair[1],pair[0])):
                memory.update({base+i:0xA5 for i in range(0x40)})
                put(memory,base+0x3B,key,1)
            models=[]
            for body in (self.words,self.retail):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                model=TriangleOracle(caller+[0x03400008,0],memory,entry=CALLER,arguments=(),phase=phase,connected=connected,tail=True)
                model.r[16]=model.before[16]=ACTORS[0]
                model.r[17]=model.before[17]=ACTORS[1]
                model.r[26]=0xDEAD0000
                model.r[10],model.r[9],model.r[7],model.r[6]=(0x12345678,0xABCDEF01,0x7FFFFFFF,0x80000000)
                model.record_call=lambda target,m=model: m.calls.append((target,m.r[4],m.r[5]))
                reference=SwapReference(memory,phase)
                second=reference.get(ACTORS[0]+0x3B,1)
                first=reference.get(ACTORS[1]+0x3B,1)
                for offset,value in ((0x20,model.r[10]),(0x24,model.r[9]),(0x2C,model.r[7]),(0x30,model.r[6])):
                    reference.put(prior.STACK+phase+offset,value,4)
                reference.run(first,second)
                model.run()
                self.assertEqual((model.r[2],model.calls,model.events,model.memory),(0,[(screen.ENTRY,*pair)],reference.events,reference.memory))
                self.assertEqual(model.r[31],CALLER+28)
                models.append(model)
            self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
            cases+=1
        self.receipt('caller-transport',dict(cases=cases,actual_caller_words=7,unsigned_key_loads=2,private_argument_saves=4,
            SP_phases=2,actual_jal_and_complete_callee_executed=True,synthetic_exit_boundary=True,full_caller_workflow_not_claimed=True))


if __name__ == '__main__':
    unittest.main()
