"""First-match/read-order proof for C origins and the guarded retail search."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import unittest
import subprocess

from tools.experiments import game_context_node_search as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, read_c_string
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_mask_scan_match import CallBoundary


ROOT = Path(__file__).resolve().parents[2]
BASE, END, COLUMNS = 0x800DCE50, 0x800DD190, 0x800A5760
NODES, PAYLOADS, CONTEXTS, REQUEST = 0x20000, 0x24000, 0x28000, 0x30000
STRIDE, PSTRIDE = 0xA0, 0x50
COLUMN_PAIRS = ((77,34),(0,103),(34,77),(77,77))


@dataclass(frozen=True)
class Case:
    columns: tuple = (77,34)
    heads: tuple = (-1,-1,-1,-1)
    nexts: tuple = (1,2,3,4,5,6,7,-1)
    kinds: tuple = (11,)*8
    contexts: tuple = (0,1,2,3,0,1,2,3)
    query: int = 0
    shared: bool = False
    null_non_type: bool = False


def corpus():
    for i in range(256):
        yield Case(COLUMN_PAIRS[i%4],tuple(-1 if (i+j*3)%5==0 else (i+j*3)%8 for j in range(4)),
            tuple(j+1 if j<7 and (i+j)%4 else -1 for j in range(8)),
            tuple((11,0,12,-1,0x8000000B)[(i+j*7)%5] for j in range(8)),
            tuple((i+j*5)%5-1 for j in range(8)),i%5-1,bool(i&8))
    for slot,depth,query in itertools.product(range(4),range(8),(-1,0,1,3)):
        heads=[-1]*4;heads[slot]=0
        contexts=[(query+1)%4]*8;contexts[depth]=query
        yield Case(COLUMN_PAIRS[slot],tuple(heads),contexts=tuple(contexts),query=query)
    for shared,null in itertools.product((False,True),(False,True)):
        yield Case(heads=(0,1,2,3),kinds=(0,12,11,-1,11,11,0,11),shared=shared,null_non_type=null)
    yield Case()
    yield Case(heads=(0,1,2,3),contexts=(0,)*8)
    yield Case(heads=(-1,1,2,-1),contexts=(0,)*8)


def context(index):
    return 0 if index<0 else CONTEXTS+index*4


def fixture(case,delta=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x100)}
    memory.update({BASE+delta+i:0 for i in range(-16,0x350)})
    for i,value in enumerate(case.columns):
        put(memory,COLUMNS+delta+i*4,value)
    for phase,row in itertools.product(range(2),range(2)):
        index=case.heads[phase*2+row]
        put(memory,BASE+delta+row*416+case.columns[phase]*4,0 if index<0 else NODES+index*STRIDE)
    for i in range(8):
        memory.update({NODES+i*STRIDE+j:0xA5 for j in range(STRIDE)})
        memory.update({PAYLOADS+i*PSTRIDE+j:0x5A for j in range(PSTRIDE)})
    for i in range(8):
        node=NODES+i*STRIDE;p=PAYLOADS+(i%2 if case.shared else i)*PSTRIDE
        put(memory,node+4,0)
        put(memory,node+8,0 if case.nexts[i]<0 else NODES+case.nexts[i]*STRIDE)
        put(memory,node+0x20,case.kinds[i]&0xFFFFFFFF)
        put(memory,node+0x98,0 if case.null_non_type and case.kinds[i]!=11 else p)
        put(memory,p+0x44,context((case.contexts[i]+1)%4))
        put(memory,p+0x48,context(case.contexts[i]))
    put(memory,REQUEST+0x18,context(case.query))
    return memory


def reference(memory,case,delta=0):
    events=[]
    def load(address):
        value=read(memory,address);events.append(('R',address,4,value));return value
    for phase in range(2):
        column=load(COLUMNS+delta+phase*4)
        assert 0<=column<104
        for row in range(2):
            node=load(BASE+delta+row*416+column*4)
            seen=set()
            while node:
                assert node not in seen,'Fixture must terminate'
                seen.add(node)
                if load(node+0x20)==11:
                    payload=load(node+0x98)
                    if load(payload+0x48)==context(case.query):
                        return node,events
                node=load(node+8)
    return 0,events


class SearchOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None):
        self.case,self.entered,self.boundary=case,[],None
        args=(context(case.query),) if entry==source.ENTRY else (0x12345678,REQUEST)
        super().__init__(words,fixture(case,delta),phase=phase,entry=entry,arguments=args,connected=connected)

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered.append(self.arguments(1));return
        assert target==0x1515C1A0,hex(target)
        self.boundary=(self.arguments(4),read(self.memory,self.r[29]+0x38),self.r[2])
        raise CallBoundary


def section_headers(data):
    header=ELF_HEADER.unpack_from(data)
    rows=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
    strings=data[rows[header[13]][4]:][:rows[header[13]][5]]
    return {read_c_string(strings,row[0]):row for row in rows}


def native_harness(body,cases):
    rows=[]
    for c in cases:
        found,_=reference(fixture(c),c)
        expected=-1 if not found else (found-NODES)//STRIDE
        parts=['{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
               for values in (c.columns,c.heads,c.nexts,c.kinds,c.contexts)]
        rows.append('{'+','.join(parts+['0x%Xu'%(c.query&0xFFFFFFFF),str(int(c.shared)),
                                        '0x%Xu'%(expected&0xFFFFFFFF)])+'}')
    return '''typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
typedef struct Payload{u8 pad[0x44];void *alternate;void *context;}Payload;
typedef struct Node Node;
struct Node{u32 pad0;Node *alternate;Node *next;u8 padC[0x14];s32 type;u8 pad24[0x74];Payload *payload;};
static Node nodes[8];static Payload payloads[8];static Node *heads[2][104];static s32 D_800A5760[2];static u32 contexts[4];
#define D_800DCE50 ((u8 *)heads)
#define D_800DD190 (*(s8 *)(heads+2))
typedef char node_size[sizeof(Node)==0x9C?1:-1];
typedef char node_next[__builtin_offsetof(Node,next)==8?1:-1];
typedef char node_type[__builtin_offsetof(Node,type)==0x20?1:-1];
typedef char node_payload[__builtin_offsetof(Node,payload)==0x98?1:-1];
typedef char payload_context[__builtin_offsetof(Payload,context)==0x48?1:-1];
''' + body + '''
typedef struct{u32 columns[2],heads[4],nexts[8],types[8],contexts[8],query,shared,expected;}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static u8 before[sizeof(nodes)+sizeof(payloads)+sizeof(heads)+sizeof(D_800A5760)];
static void *ctx(u32 index){return index<4?&contexts[index]:0;}
static void snapshot(int check){
    volatile u8 *blocks[4]={(u8 *)nodes,(u8 *)payloads,(u8 *)heads,(u8 *)D_800A5760};
    u32 sizes[4]={sizeof(nodes),sizeof(payloads),sizeof(heads),sizeof(D_800A5760)},b,i,at=0;
    for(b=0;b<4;b++)for(i=0;i<sizes[b];i++,at++){
        if(check){if(before[at]!=blocks[b][i])__builtin_trap();}
        else before[at]=blocks[b][i];
    }
}
static int test_all(void){
    u32 n,i,j,phase,row;void *result;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        const Case *c=&cases[n];
        for(i=0;i<sizeof(nodes);i++)((u8 *)nodes)[i]=0xA5;
        for(i=0;i<sizeof(payloads);i++)((u8 *)payloads)[i]=0x5A;
        for(row=0;row<2;row++)for(j=0;j<104;j++)heads[row][j]=0;
        for(phase=0;phase<2;phase++){
            D_800A5760[phase]=(s32)c->columns[phase];
            for(row=0;row<2;row++){i=c->heads[phase*2+row];heads[row][c->columns[phase]]=i<8?&nodes[i]:0;}
        }
        for(i=0;i<8;i++){
            j=c->shared?i%2:i;
            nodes[i].alternate=0;nodes[i].next=c->nexts[i]<8?&nodes[c->nexts[i]]:0;
            nodes[i].type=(s32)c->types[i];nodes[i].payload=&payloads[j];
            payloads[j].alternate=ctx(c->contexts[i]==0xFFFFFFFFu?0:(c->contexts[i]+1)%4);
            payloads[j].context=ctx(c->contexts[i]);
        }
        snapshot(0);result=func_151CE634(ctx(c->query));snapshot(1);
        if(result!=(c->expected<8?(void *)&nodes[c->expected]:0))return 23;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ContextNodeSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output)
        cls.obj,d=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if d:raise ValueError(d)
        raw,bindings=source.payload(cls.obj)
        cls.original=source.original(ROOT,cls.output)
        cls.normal=source.normalized(raw,bindings,source.payload(cls.original))
        data,funcs=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.raw_words=list(struct.unpack_from('>41I',data,funcs[source.FUNCTION]['value']))
        image,funcs=source.link_owner(ROOT,cls.output,cls.output/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>39I',image,funcs[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>39I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.null_non_type]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),
                         raw_C_words=41,retail_words=39,compiler_only=False,new_guard_rows=41,
                         matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('context search qualification:',cls.receipt)

    def test_01_closed_origins_bindings_guard_prefix_and_literal_output(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(self.normal,source.payload(self.original))
        self.assertEqual(set(range(41))-set(source.ORIGINS),{5,13,19})
        self.assertEqual(len(set(source.ORIGINS)),38);self.assertEqual(source.ORIGINS.count(17),2)
        guards=(self.output/'qualified-guards.csv').read_bytes()
        prefix=self.values['conker/retail_word_patches.us.csv']
        self.assertTrue(guards.startswith(prefix))
        rows=list(csv.DictReader(io.StringIO(guards.decode())))
        selected=[r for r in rows if r['function']==source.FUNCTION]
        self.assertEqual(len(selected),41)
        self.assertEqual([int(r['offset'],0)for r in selected],list(range(0,164,4)))
        self.assertEqual(sum(r['omit']=='true'for r in selected),3)
        self.assertEqual(sum(bool(r['insert_after'])for r in selected),1)
        self.assertEqual(sum(len(r['replacement_relocations'].split(';'))for r in selected if r['replacement_relocations']!='-'),6)
        elf=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(elf,COLUMNS,8)
        self.assertEqual(struct.unpack_from('>2I',elf,at),(77,34))
        addresses={name:f[1]for _,name,f,_ in source.symbol_rows(elf)}
        self.assertEqual(addresses['D_800DD190']-addresses['D_800DCE50'],0x340)
        self.receipt.update(guard_prefix_byte_identical=True,guarded_input_words=41,folded_origins=[5,13,19],
                            duplicated_row_advance=17,original_frozen_columns=[77,34])

    def test_02_reference_raw_C_and_guarded_full_states_order_and_first_match(self):
        visits=[set(),set(),set()];nonnull=0
        for case,phase in itertools.product(self.cases,(0,8)):
            expected,events=reference(fixture(case),case)
            models=[SearchOracle(w,case,phase).run()for w in (self.truth,self.raw_words,self.words)]
            self.assertEqual(complete(models[0]),complete(models[2]))
            for i,m in enumerate(models):
                self.assertEqual(m.r[2],expected)
                self.assertEqual(m.events,events)
                self.assertEqual(m.memory,fixture(case))
                self.assertFalse(m.calls)
                for reg in (*range(16,24),28,29,30,31):self.assertEqual(m.r[reg],m.before[reg])
                visits[i].update(m.visits)
            nonnull+=bool(expected)
        # Each compiler leaves one unreachable next-link load after the early return.
        for entry,count,dead,v in ((source.ENTRY,39,25,visits[0]),(source.ENTRY,41,29,visits[1]),(source.ENTRY,39,25,visits[2])):
            self.assertEqual(v,set(range(entry,entry+count*4,4))-{entry+dead*4})
        self.receipt.update(three_way_phases=len(self.cases)*2,successful_return_phases=nonnull,
                            original_reachable_words=38,raw_reachable_words=40,
                            preserved_unreachable_retail_word=25,source_ordered_reads_and_return=True,
                            raw_private_GPR_fault_identity_claimed=False,hardware_MMU_claimed=False)

    def native(self,body,label,optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+optimization)
        p=subprocess.run(['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror',str(unit),'-o',str(binary)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_domains_aliases_readonly_bytes_and_semantic_controls(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        negatives={
            'wrong-tag':source.SELECTED.replace('== 11','== 12'),
            'reverse-context':source.SELECTED.replace('+ 0x48) == context','+ 0x48) != context'),
            'wrong-context-field':source.SELECTED.replace('+ 0x48) == context','+ 0x44) == context'),
            'wrong-link':source.SELECTED.replace('node + 8','node + 4'),
            'reverse-phase':source.SELECTED.replace('D_800A5760[phase]','D_800A5760[1-phase]'),
            'one-row':source.SELECTED.replace('row != (u8 *)&D_800DD190','row != D_800DCE50+0x1A0'),
            'one-phase':source.SELECTED.replace('phase < 2','phase < 1'),
            'discard-found':source.SELECTED.replace('return node;','return 0;'),
        }
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED);self.assertEqual(self.native(body,label),23,label)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(negatives),
                            native_typed_node_payload_and_head_objects=True,readonly_byte_fences=True,
                            null_non_type_payloads_guest_only=True)

    def test_04_all_input_word_and_relocation_guards_reject_effective_mutants(self):
        obj=self.output/'after-owner.o';data=obj.read_bytes()
        headers=section_headers(data);info=source.parse_object(obj)[1][source.FUNCTION]
        for i in range(41):
            mutant=bytearray(data);at=headers['.text'][4]+info['value']+i*4;mutant[at+3]^=1
            path=self.output/'negative-word.o';path.write_bytes(mutant)
            with self.assertRaises(ValueError)as error:
                source.emit_padded_assembly(path,ROOT/source.ASM,word_patches_path=self.output/'qualified-guards.csv',filename=source.OWNER)
            self.assertIn(source.FUNCTION,str(error.exception));self.assertIn('expected',str(error.exception))
        symbols=headers['.symtab']
        # Section link indexes refer to ELF order; resolve the raw header array directly.
        eh=ELF_HEADER.unpack_from(data);sh=[SECTION_HEADER.unpack_from(data,eh[6]+i*eh[11])for i in range(eh[12])]
        strings=data[sh[symbols[6]][4]:][:sh[symbols[6]][5]]
        own_index=next(i for i,at in enumerate(range(symbols[4],symbols[4]+symbols[5],16))
                       if read_c_string(strings,SYMBOL.unpack_from(data,at)[0])==source.FUNCTION)
        rel=headers['.rel.text'];checked=0
        for offset in source.RAW_BINDINGS:
            at=next(at for at in range(rel[4],rel[4]+rel[5],8)if struct.unpack_from('>I',data,at)[0]==info['value']+offset)
            mutant=bytearray(data);rinfo=struct.unpack_from('>I',data,at+4)[0]
            struct.pack_into('>I',mutant,at+4,(own_index<<8)|(rinfo&255))
            path=self.output/'negative-binding.o';path.write_bytes(mutant)
            with self.assertRaises(ValueError)as error:
                source.emit_padded_assembly(path,ROOT/source.ASM,word_patches_path=self.output/'qualified-guards.csv',filename=source.OWNER)
            self.assertIn(source.FUNCTION,str(error.exception));self.assertIn('relocation',str(error.exception));checked+=1
        self.receipt.update(fired_input_word_negatives=41,fired_input_binding_negatives=checked)

    def test_05_independent_global_rebases_and_fixed_row_end_contract(self):
        phases=0
        for delta in (0x10000,0x8A0,0x131B0):
            images=[]
            for label,path in (('raw',self.obj),('retail',self.original),('guarded',self.output/'qualified-padded.o')):
                elf,script=self.output/('rebase-%d-%s.elf'%(delta,label)),self.output/'rebase.ld'
                # A full padded owner has unrelated external bindings; isolate its normalized target.
                if label=='guarded':
                    from tools.experiments.alternative_source_draft_word_screen import emit_function
                    raw=self.normal[0];bindings=self.normal[1]
                    assembly,unresolved=emit_function(raw,dict(value=0,size=156),bindings,source.FUNCTION,
                        {'D_800DCE50':BASE+delta,'D_800DD190':END+delta,'D_800A5760':COLUMNS+delta})
                    self.assertFalse(unresolved)
                    asm=self.output/'isolated-guarded.s';asm.write_text(assembly);path=asm.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800DCE50=0x%X'%(BASE+delta),'--defsym=D_800DD190=0x%X'%(END+delta),
                    '--defsym=D_800A5760=0x%X'%(COLUMNS+delta),'-o',str(elf),str(path)],capture_output=True,check=True)
                count=41 if label=='raw' else 39
                images.append(list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1])))
            self.assertEqual(images[1],images[2])
            for case in self.cases[::23]:
                expected,events=reference(fixture(case,delta),case,delta)
                models=[SearchOracle(words,case,delta=delta).run()for words in images]
                self.assertEqual(complete(models[1]),complete(models[2]))
                for m in models:self.assertEqual((m.r[2],m.events),(expected,events))
                phases+=1
        self.receipt.update(independent_rebase_phases=phases,rebase_sets=3,base_end_stride_contract=0x340)

    def test_06_real_caller_forwarding_zero_return_and_saved_pointer_boundary(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section']not in DEFAULT_SEGMENTS['us']:continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(words)if w==opcode)
        self.assertEqual(found,[('func_151CE51C',0x151CE528)])
        caller=list(struct.unpack_from('>70I',self.rom,0x1FB9CC));phases=0;entered=0
        for case,phase in itertools.product(self.cases[::19],(0,8)):
            expected,_=reference(fixture(case),case);models=[]
            for code in (self.truth,self.raw_words,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+len(code)*4,4),code))
                m=SearchOracle(caller,case,phase,entry=0x151CE51C,connected=connected)
                if expected:
                    with self.assertRaises(CallBoundary):m.run()
                    self.assertEqual(m.boundary[0],(0x12345678,STACK+phase-80+0x44,
                                                   STACK+phase-80+0x40,STACK+phase-80+0x3C))
                    self.assertEqual(m.boundary[1:],(expected,expected));entered+=1
                else:
                    m.run();self.assertIsNone(m.boundary);self.assertEqual(m.r[2],0)
                    self.assertEqual(m.r[29],m.before[29]);self.assertEqual(m.r[31],m.before[31])
                self.assertEqual(m.entered,[(context(case.query),)]);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[2]));phases+=1
        self.receipt.update(all_direct_retail_call_sites=found,caller_window_phases=phases,
                            fired_positive_caller_boundaries=entered,full_positive_caller_execution_claimed=False)

    def test_07_strict_header_code_data_size_and_length_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+156]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,156),
                 source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
                 next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        self.receipt['strict_image_negative_controls']=7
