"""Direct list collection, ordered alias reads, lazy storage and exact ownership."""

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

from tools.experiments import game_node_group_collector_candidates as screen
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
ACTOR, OUTPUT = 0x20000, 0x30000
NODES = tuple(0x10000 + i * 0x100 for i in range(8))


def fixture(group=1, groups=(1,), order=None, full=False):
    memory = {prior.STACK+i:0xA5 for i in range(-0x40, 0x40)}
    order = tuple(range(len(groups))) if order is None else order
    if full:
        for base, size in ((ACTOR, 0x40), (OUTPUT-4, 44), (HEAD, 36),
                *((node, 0x60) for node in NODES[:len(groups)])):
            memory.update({base+i: 0xA5 for i in range(size)})
    else:
        memory.update({OUTPUT+i: 0xA5 for i in range(36)})
    put(memory, ACTOR+0x3A, group^255, 1)
    put(memory, ACTOR+0x3B, group, 1)
    put(memory, HEAD, NODES[order[0]] if order else 0)
    for i, kind in enumerate(groups):
        put(memory, NODES[i], kind, 1)
        put(memory, NODES[i]+0x50, 0)
    for i, index in enumerate(order):
        put(memory, NODES[index]+0x54, NODES[order[i+1]] if i+1 < len(order) else 0)
    return memory


class CollectorReference(ProgressReference):
    def put(self, address, value):
        self.events.append(('W', address, 4, value & 0xFFFFFFFF))
        assert all(address+i in self.memory for i in range(4)), ('unmapped store', address, 4)
        put(self.memory, address, value)

    def run(self, actor=ACTOR, output=OUTPUT, head=HEAD):
        current, count = self.get(head), 0
        for _ in range(64):
            if not current:
                return count
            group = self.get(actor+0x3B, 1)
            kind = self.get(current, 1)
            next_node = self.get(current+0x54)
            if group == kind:
                self.put(output+4*count, current)
                count += 1
            current = next_node
        raise AssertionError('finite test-fixture bound, not a production list limit')


class CollectorOracle(TriangleOracle):
    def __init__(self, words, memory, args=(ACTOR, OUTPUT), phase=0, entry=screen.ENTRY):
        super().__init__(words, memory, entry=entry, arguments=args, phase=phase)

    def record_call(self, target):
        raise AssertionError(('unexpected call', target))


def alias_cases():
    result = []
    memory = fixture(255, (255, 0, 0), full=True)
    put(memory, OUTPUT+3, 255, 1)
    result.append(('live-actor-group', memory, (OUTPUT-0x38, OUTPUT)))
    for name, output in (('captured-next', NODES[0]+0x54), ('later-node-group', NODES[1]),
            ('head-write', HEAD), ('current-node-group', NODES[0])):
        result.append((name, fixture(255, (255, 255, 255), full=True), (ACTOR, output)))
    return result


class GameNodeGroupCollectorMatchTests(unittest.TestCase):
    run_host = prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        assert not any(prior.STACK-0x600 <= address < prior.STACK+0x140 for address in (*NODES, ACTOR, OUTPUT, HEAD))
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-node-group-collector-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>23I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, value):
        (self.out / (name+'.json')).write_text(json.dumps(value, indent=2)+'\n')

    def compare(self, memory, args=(ACTOR, OUTPUT), phase=0, words=None, entry=screen.ENTRY, head=HEAD):
        reference = CollectorReference(memory, phase)
        expected = reference.run(*args, head)
        models = [CollectorOracle(body, memory, args, phase, entry).run() for body in (words or self.words, self.retail)]
        for model in models:
            self.assertEqual((model.r[2], model.calls, model.events, model.memory),
                (expected, [], reference.events, reference.memory))
        self.assertEqual((models[0].r, models[0].f, models[0].events), (models[1].r, models[1].f, models[1].events))
        return models

    def test_01_direct_slot_frame_and_symbolic_global(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (23, 0, 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.record['relocations'], {4:[('R_MIPS_HI16', 'D_800C3EE0')], 8:[('R_MIPS_LO16', 'D_800C3EE0')]})
        self.assertEqual((self.record['pool_bytes'], self.record['diagnostics']), (0, ''))
        self.receipt('slot', dict(words=23, bytes=92, frame=0, raw_differences=0, guards_added=0,
            original_assembly_already_exact=True, padding_and_generated_data=0))

    def test_02_all_byte_pairs_masks_topologies_and_word_coverage(self):
        seen, counts = set(), [0, 0]
        for group, kind in itertools.product(range(256), repeat=2):
            for model in self.compare(fixture(group, (kind,))):
                seen.update(model.visits)
            counts[0] += 1
        for group, mask, order, phase in itertools.product((0, 127, 128, 255), range(256),
                (tuple(range(8)), (3, 0, 7, 2, 5, 1, 6, 4)), (0, 8)):
            groups = tuple(group if mask & (1 << i) else group^255 for i in range(8))
            for model in self.compare(fixture(group, groups, order), phase=phase):
                seen.update(model.visits)
            counts[1] += 1
        for model in self.compare(fixture(groups=()), (0, 0)):
            seen.update(model.visits)
        missing = sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY, screen.ENTRY+92, 4))-seen)
        self.assertEqual(missing, [])
        self.receipt('guest', dict(cases=sum(counts)+1, byte_pair_cases=counts[0], mask_topology_cases=counts[1],
            all_actor_and_node_group_bytes=256, masks=256, topologies=2, SP_phases=2, missing_word_indices=missing,
            independent_access_order_and_full_GP_FP_trace_memory_equal=True, no_hooks=True))

    def test_03_lazy_storage_fault_prefixes_and_aliases(self):
        lazy = [({HEAD+i:0 for i in range(4)}, (0, 0)),
            ({HEAD+i:0 for i in range(4)}, (0xFFFFFFFF, 0xFFFFFFFF)),
            (fixture(127, (128, 128, 128)), (ACTOR, 0))]
        for memory, args in lazy:
            self.compare(memory, args)
        probes = [HEAD, ACTOR+0x3B, NODES[0], *range(NODES[0]+0x54, NODES[0]+0x58),
            OUTPUT, NODES[1], NODES[1]+0x54, OUTPUT+4, NODES[2], NODES[2]+0x54]
        for address in probes:
            memory = fixture(255, (255, 255, 255), full=True)
            del memory[address]
            reference = CollectorReference(memory)
            with self.assertRaises(AssertionError):
                reference.run()
            for words in (self.words, self.retail):
                model = CollectorOracle(words, memory)
                with self.assertRaises(AssertionError):
                    model.run()
                self.assertEqual((model.events, model.memory), (reference.events, reference.memory), hex(address))
        for name, memory, args in alias_cases():
            for phase in (0, 8):
                self.compare(memory, args, phase)
        self.receipt('gates', dict(lazy_cases=len(lazy), fault_prefixes=len(probes), alias_layouts=len(alias_cases()),
            alias_executions=2*len(alias_cases()), output_canaries_and_partial_stores_checked=True,
            group_reread_and_next_capture_before_store=True, arbitrary_private_aliases_not_claimed=True))

    def test_04_profiles_and_effective_semantic_negatives(self):
        records, negatives, ordinary = [], 0, 0
        cases = [(fixture(groups=()), (0, 0)), (fixture(128, (128, 127, 128), full=True), (ACTOR, OUTPUT)),
            (fixture(127, (128, 128, 128)), (ACTOR, 0)), *[(m,a) for _,m,a in alias_cases()]]
        forms = [(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p != 'o2g3']
        for name, body, profile in forms:
            record, words = screen.compile_candidate(self.root, self.out, name, body, profile)
            records.append(record)
            outcomes = []
            for memory, args in cases:
                reference = CollectorReference(memory)
                expected = reference.run(*args)
                try:
                    model = CollectorOracle(words, memory, args).run()
                    writes = [event for event in prior.public(model.events) if event[0] == 'W']
                    expected_writes = [event for event in prior.public(reference.events) if event[0] == 'W']
                    equal = (model.r[2],model.calls,writes,prior.external_memory(model.memory)) == (
                        expected,[],expected_writes,prior.external_memory(reference.memory))
                    if name == 'selected':
                        self.assertEqual(model.events, reference.events)
                except (AssertionError, KeyError):
                    equal = False
                outcomes.append(equal)
                ordinary += 'negative-' not in name
            if 'negative-' in name:
                self.assertFalse(all(outcomes), name)
                negatives += 1
            else:
                self.assertTrue(all(outcomes), name)
        self.assertEqual(negatives, 7)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary, effective_negatives=negatives,
            measurements=records, alternate_private_register_and_read_schedule_not_claimed=True,
            selected_complete_read_write_order_still_checked=True))

    def test_05_actual_native32_complete_C_bytes_masks_aliases_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef union {u8 b[0x60];u8 *alignment;} Node;
typedef union {u8 b[0x40];u8 *alignment;} Actor;
typedef union {u8 b[0xA0];u8 *alignment;} Arena;
typedef char pointer_width[sizeof(void *)==4?1:-1];
static Node nodes[8],old_nodes[8],expected_nodes[8];
static Actor actor,old_actor,expected_actor;
static Arena arena,old_arena,expected_arena;
static u8 *D_800C3EE0;
static u32 cases;
static void copy(u8 *to,const u8 *from,u32 n){u32 i;for(i=0;i<n;i++)to[i]=from[i];}
static int equal(const u8 *a,const u8 *b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void setup(u32 group,u32 other,u32 order,u32 mask,u32 use_mask){
    u32 i,j,k;static const u32 permutation[8]={3,0,7,2,5,1,6,4};
    for(i=0;i<sizeof(nodes);i++)((u8 *)nodes)[i]=0xA5;
    for(i=0;i<sizeof(actor);i++)actor.b[i]=0xA5;
    for(i=0;i<sizeof(arena);i++)arena.b[i]=0xA5;
    actor.b[0x3A]=group^255;actor.b[0x3B]=group;
    for(i=0;i<8;i++){
        j=order?permutation[i]:i;k=i==7?8:(order?permutation[i+1]:i+1);
        nodes[j].b[0]=use_mask?(mask&(1u<<j)?group:group^255):(j==0?other:(j&1?group:group^255));
        *(u8 **)(nodes[j].b+0x50)=0;
        *(u8 **)(nodes[j].b+0x54)=k==8?0:nodes[k].b;
    }
    D_800C3EE0=nodes[order?permutation[0]:0].b;
}
static s32 reference(u8 *a,u8 **out){
    u8 *cursor=D_800C3EE0;u8 *following;s32 used=0;u8 group,kind;
    while(cursor){
        group=a[0x3B];kind=cursor[0];following=*(u8 **)(cursor+0x54);
        if(group==kind){out[used]=cursor;used++;}
        cursor=following;
    }
    return used;
}
''' + screen.SELECTED + r'''
static int check(u8 *a,u8 **out){
    u8 *head=D_800C3EE0;u8 *expected_head;s32 wanted,actual;
    copy((u8 *)old_nodes,(u8 *)nodes,sizeof(nodes));
    copy(old_actor.b,actor.b,sizeof(actor));copy(old_arena.b,arena.b,sizeof(arena));
    wanted=reference(a,out);expected_head=D_800C3EE0;
    copy((u8 *)expected_nodes,(u8 *)nodes,sizeof(nodes));
    copy(expected_actor.b,actor.b,sizeof(actor));copy(expected_arena.b,arena.b,sizeof(arena));
    copy((u8 *)nodes,(u8 *)old_nodes,sizeof(nodes));
    copy(actor.b,old_actor.b,sizeof(actor));copy(arena.b,old_arena.b,sizeof(arena));D_800C3EE0=head;
    actual=func_15033E28(a,out);cases++;
    return wanted!=actual||D_800C3EE0!=expected_head||!equal((u8 *)nodes,(u8 *)expected_nodes,sizeof(nodes))
        ||!equal(actor.b,expected_actor.b,sizeof(actor))||!equal(arena.b,expected_arena.b,sizeof(arena));
}
'''
        self.run_host(r'''
u32 g,h,order,alias;u8 *a;u8 **out;u8 later;
for(g=0;g<256;g++)for(h=0;h<256;h++)for(order=0;order<2;order++){
    setup(g,h,order,0,0);if(check(actor.b,(u8 **)(arena.b+64)))return 1;
    setup(g,0,order,h,1);if(check(actor.b,(u8 **)(arena.b+64)))return 2;
}
setup(1,1,0,0,0);D_800C3EE0=0;if(check(0,0))return 3;
setup(1,1,0,0,0);D_800C3EE0=0;if(check((u8 *)1,(u8 **)1))return 4;
setup(127,0,0,0,1);if(check(actor.b,0))return 5;
for(alias=0;alias<5;alias++){
    setup(255,0,0,255,1);a=actor.b;out=(u8 **)(arena.b+64);
    *(u8 **)(nodes[2].b+0x54)=0;
    if(alias==0){
        later=((u8 *)&D_800C3EE0)[3];a=arena.b+8;a[0x3B]=later^255;
        nodes[0].b[0]=a[0x3B];nodes[1].b[0]=nodes[2].b[0]=later;
    }else if(alias==1)out=(u8 **)(nodes[0].b+0x54);
    else if(alias==2)out=(u8 **)nodes[1].b;
    else if(alias==3){out=&D_800C3EE0;nodes[0].b[0]=nodes[2].b[0]=0;}
    else out=(u8 **)nodes[0].b;
    if(check(a,out))return 6;
}
if(cases!=262152)return 7;
''')
        self.receipt('native',dict(cases=262152,pointer_bytes=4,actual_complete_C=True,
            all_group_byte_pairs=65536,all_8_node_match_masks=256,topologies=2,alias_layouts=5,
            all_input_output_bytes_and_global_head_checked=True,native_alias_bytes_use_native_endianness=True))

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
        self.assertEqual(text[target['value']:target['value']+92],isolated[:92])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+92},isolated_rel)
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
        self.assertEqual(functions[screen.FUNCTION]['size'],92)
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
            words=list(struct.unpack_from('>23I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            expected[1]=expected[1]&0xFFFF0000|((head+0x8000)>>16)&65535
            expected[2]=expected[2]&0xFFFF0000|head&65535
            self.assertEqual(words,expected)
            for groups in ((),(255,),(255,0,255)):
                memory=fixture(255,groups)
                value=read(memory,HEAD)
                for i in range(4):
                    del memory[HEAD+i]
                put(memory,head,value)
                reference=CollectorReference(memory)
                result=reference.run(head=head)
                model=CollectorOracle(words,memory,entry=entry).run()
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

    def test_08_retail_caller_stack_output_interface(self):
        cases = 0
        for groups, phase in itertools.product(((), (128,)*8, (128,127,128)), (0,8)):
            output = prior.STACK+phase+0x80
            memory = fixture(128, groups)
            memory.update({output+i:0xA5 for i in range(-4,40)})
            for model in self.compare(memory, (ACTOR,output), phase):
                pointers = [NODES[i] for i,group in enumerate(groups) if group == 128]
                self.assertEqual(model.r[2], len(pointers))
                self.assertEqual([read(model.memory,output+4*i) for i in range(len(pointers))],pointers)
                self.assertEqual(read(model.memory,output+4*len(pointers)),0xA5A5A5A5)
            cases += 1
        self.receipt('caller-interface',dict(cases=cases,SP_phases=2,output_offset=0x80,
            complete_output_and_stack_canaries_checked=True,full_caller_workflow_not_claimed=True))


if __name__ == '__main__':
    unittest.main()
