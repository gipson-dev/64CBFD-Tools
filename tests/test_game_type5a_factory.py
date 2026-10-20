"""Type-0x5A color factory: eight-input ABI, wrapping sizes and exact partial stores."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_type5a_factory as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary

ROOT=Path(__file__).resolve().parents[2]
OUTPUT,PREVIOUS,ACTOR=0x30000,0x31000,0x32000
OLD,STATUS,TIME,DISABLED=0x800D9894,0x800D9890,0x800BE9E8,0x800BE616
HEAD=source.LIST_BASE+0x5A*4
REMOVE,COPY=0x1516972C,0x10022EC0
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678,0xFF00FF00,0xAABBCCDD)
SIZES=(0,1,4,255,0x1000,0xFFFFFFDF,0xFFFFFFE0,0xFFFFFFFF)


@dataclass(frozen=True)
class Case:
    words:tuple=(0x1234,0x87654321,0xFFFF0080,0xAABB00FF,0x8000007F,0xFFFFFFFF,0xCD,4)
    fail:bool=False
    seed:int=0xA5
    home:object=None


def corpus():
    for byte,fail in itertools.product(range(256),(False,True)):
        args=(0xAABB0000|byte,(byte*1664525+1013904223)&0xFFFFFFFF,
              0x80000000|byte,0x12340000|((byte*5+3)&255),
              0x7FFFFF00|(255-byte),0xFFFF0000|(byte^128),byte,SIZES[byte%8])
        yield Case(args,fail,byte)
    for word,size,fail in itertools.product(WORDS,SIZES,(False,True)):
        yield Case((word,word,word,word,word,word,word&255,size),fail,word&255)
    for home,word,fail in itertools.product((0,-16),WORDS,(False,True)):
        yield Case((word,word,word,word,word,word,0xAABBCCDD,0xFFFFFFE0),fail,0xA5,home)


def destination(case,sp):
    return OUTPUT if case.home is None else (sp+case.home)&0xFFFFFFFF


def packet(args):
    return (0x5A,0,(args[7]+0x20)&0xFFFFFFFF,0,255,1)


def fixture(case,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x400)}
    for base,size in ((OUTPUT,0x100),(PREVIOUS,0x40),(ACTOR,0x340),(STATUS,0x40)):
        memory.update({base+i:(case.seed+i*13)&255 for i in range(-16,size+16)})
    put(memory,OLD,0);put(memory,TIME,case.words[5])
    put(memory,HEAD,0);memory[DISABLED]=0
    memory[ACTOR+0x23D]=case.words[5]&255
    for i,w in enumerate(case.words[4:]):put(memory,STACK+phase+0x10+4*i,w)
    return memory


def reference(case,phase=0,memory=None,sp=None,initialize=False):
    sp=STACK+phase if sp is None else sp
    result=dict(fixture(case,phase)if memory is None else memory)
    for i,w in enumerate(case.words):put(result,sp+4*i,w)
    out=destination(case,sp)
    if case.fail:return result,0
    if initialize:
        result[out+1]=0
        old=read(result,HEAD)
        put(result,out+8,old)
        if old:put(result,old+4,out)
        result[out]=0x5A;put(result,out+4,0);put(result,HEAD,out);result[out+0xC]=255
    # Model retail's interleaved parameter-home reads for guest-only aliases.
    for index,offset,width in ((0,0x14,1),(1,0x10,4),(2,0x15,1),(3,0x16,1),(4,0x17,1)):
        put(result,out+offset,read(result,sp+4*index),width)
    callback=result[sp+0x1B]
    result[out+0x18]=0;result[out+0x19]=callback
    result[out+0x1A]=read(result,sp+0x14)&255
    return result,out


def public(memory):
    return {a:b for a,b in memory.items()if not STACK-0x800<=a<STACK+0x400}


class FactoryOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None,
            memory=None,arguments=None,boundary=None,drop_failed_arguments=False):
        self.case,self.delta=case,delta
        self.entry_sp=STACK+phase
        self.factory_packets,self.heap_packets,self.init_packets,self.entries,self.removals,self.copies=[],[],[],[],[],[]
        self.visits=set();self.drop_failed_arguments=drop_failed_arguments
        super().__init__(words,fixture(case,phase)if memory is None else memory,phase=phase,
            entry=entry,arguments=case.words if arguments is None else arguments,connected=connected)
        if boundary is not None:self.code=ReturnBoundaryCode(self.code,boundary,self)

    def execute(self,word):
        self.visits.add(self.current_pc)
        super().execute(word)

    def record_call(self,target):
        if target==source.FACTORY+self.delta:
            args=self.arguments(6);self.factory_packets.append(args)
        elif target==source.ENTRY:
            args=self.arguments(8);self.entries.append(args);self.entry_sp=self.r[29]
        elif target==source.ALLOCATOR:
            args=self.arguments(5);self.heap_packets.append(args)
        elif target==source.INITIALIZER:
            args=self.arguments(2);self.init_packets.append(args)
        elif target==REMOVE:
            args=self.arguments(1);self.removals.append(args)
        elif target==COPY:
            args=self.arguments(3);self.copies.append(args)
        else:raise AssertionError(('Unbounded type-0x5A call',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        result=0x87654321
        if target in (source.FACTORY+self.delta,source.ALLOCATOR):
            result=0 if self.case.fail else destination(self.case,self.entry_sp)
            if self.case.fail and self.drop_failed_arguments:
                for i in range(32):self.memory.pop(self.entry_sp+i,None)
        elif target==COPY:
            dst,src,size=self.copies[-1]
            assert size==4
            values=[self.memory[src+i]for i in range(size)]
            for i,v in enumerate(values):self.put(dst+i,v,1)
            result=dst
        elif target!=REMOVE:raise AssertionError(('Unbounded type-0x5A provider',hex(target)))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=result


def native_harness(body,cases):
    rows=['{{%s},%du,%du}'%(','.join('0x%Xu'%v for v in c.words),int(c.fail),c.seed)for c in cases]
    return """typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
#define NULL ((void *)0)
""" + source.TYPES + source.DECLARATIONS + body + """
typedef struct{u32 args[8],fail,seed;}Case;
static const Case cases[]={""" + ',\n'.join(rows) + """};
static struct{u32 before[4];Type5AColorRecord record;u8 payload[0x100];u32 after[4];}storage;
static const Case *item;
static int calls,error;
static Type5AColorRecord *record;
__attribute__((noinline))void *func_15167A68(s32 type,s32 subtype,s32 size,s32 mode,u8 flag,u8 active){
    if(calls++!=0 || type!=0x5A || subtype!=0 || (u32)size!=item->args[7]+0x20u ||
        mode!=0 || flag!=255 || active!=1)error=1;
    return item->fail?NULL:record;
}
static int test_all(void){
    u32 n,i;Type5AColorRecord *result;
    if(sizeof(void *)!=4 || sizeof(Type5AColorRecord)!=0x20 ||
       __builtin_offsetof(Type5AColorRecord,value)!=0x10 ||
       __builtin_offsetof(Type5AColorRecord,selector)!=0x14 ||
       __builtin_offsetof(Type5AColorRecord,red)!=0x15 ||
       __builtin_offsetof(Type5AColorRecord,green)!=0x16 ||
       __builtin_offsetof(Type5AColorRecord,blue)!=0x17 ||
       __builtin_offsetof(Type5AColorRecord,state)!=0x18 ||
       __builtin_offsetof(Type5AColorRecord,callback)!=0x19 ||
       __builtin_offsetof(Type5AColorRecord,view)!=0x1A ||
       __builtin_offsetof(Type5AColorRecord,reserved)!=0x1B)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(storage);i++)((u8 *)&storage)[i]=(u8)(item->seed+i*13u);
        record=&storage.record;
        result=func_151A4FD0((s32)item->args[0],item->args[1],(s32)item->args[2],(s32)item->args[3],
            (s32)item->args[4],(s32)item->args[5],(u8)item->args[6],item->args[7]);
        if(error || calls!=1 || result!=(item->fail?NULL:record))return 23;
        if(!item->fail && (record->selector!=(u8)item->args[0] || record->value!=item->args[1] ||
            record->red!=(u8)item->args[2] || record->green!=(u8)item->args[3] ||
            record->blue!=(u8)item->args[4] || record->view!=(u8)item->args[5] ||
            record->callback!=(u8)item->args[6] || record->state!=0))return 23;
        for(i=0;i<sizeof(storage);i++){
            if(!item->fail && i>=32 && i<=42)continue;
            if(((u8 *)&storage)[i]!=(u8)(item->seed+i*13u))return 23;
        }
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class Type5AFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.TYPES+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if c.home is None]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('type-0x5A factory qualification:',cls.receipt)

    def test_01_direct_words_frame_binding_and_old_stub(self):
        self.assertEqual(self.words,self.truth)
        raw,bindings=source.payload(self.obj)
        self.assertEqual(len(raw),160)
        self.assertEqual(bindings,{0x38:[('R_MIPS_26','func_15167A68')]})
        self.assertEqual(self.words[0],0x27BDFFE0)
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(raw,bindings))
        self.assertEqual(source.payload(self.output/'qualified-padded.o'),(raw,bindings))
        before=self.values['conker/build/conker.us.elf']
        old=list(struct.unpack_from('>40I',before,source.elf_slot_offset(before,source.ENTRY,160)))
        stale=FactoryOracle(old,Case()).run()
        self.assertNotEqual(stale.r[2],OUTPUT);self.assertFalse(stale.factory_packets)
        q=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual(q['preserved_neighbors'],22)
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],5)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(words=40,frame=32,bindings=1,compiler_only=True,actual_old_stub_rejected=True,
            preserved_neighbors=22,actual_Make_commands=5,guard_manifest_unchanged=True)

    def test_02_complete_state_wrapping_partial_stores_and_guest_aliases(self):
        visits=set();aliases=0
        for case,phase in itertools.product(self.cases,(0,8)):
            expected,result=reference(case,phase);models=[]
            for code in (self.truth,self.words):
                m=FactoryOracle(code,case,phase).run()
                self.assertEqual(m.factory_packets,[packet(case.words)])
                self.assertEqual(m.r[2],result);self.assertEqual(m.r[29],STACK+phase)
                self.assertEqual(public(m.memory),public(expected))
                if case.home is not None:
                    p=destination(case,STACK+phase)
                    self.assertEqual(bytes(m.memory[p+i]for i in range(0x10,0x20)),
                                     bytes(expected[p+i]for i in range(0x10,0x20)))
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]))
            aliases+=int(case.home is not None)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=visits)
        self.receipt.update(modeled_phases=len(self.cases)*2,all40_words_executed=True,
            guest_stack_alias_phases=aliases,native_stack_alias_claimed=False,
            unsigned_size_wrap=True,late_word_and_byte_homes=True,unwritten_padding_and_payload_preserved=True)

    def native(self,body,name,opt='-O2'):
        path=self.output/(name+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.native_cases))
        subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Werror=implicit-function-declaration',
            '-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,check=True)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_defined_size_math_and_effective_semantic_negatives(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'wrong-type':source.SELECTED.replace('func_15167A68(0x5A','func_15167A68(0x59'),
            'wrong-size':source.SELECTED.replace('extraBytes + 0x20U','extraBytes + 0x1FU'),
            'wrong-flag':source.SELECTED.replace('0, 0xFF, 1);','0, 0xFE, 1);'),
            'truncated-value':source.SELECTED.replace('record->value = value','record->value = (u8)value'),
            'wrong-selector':source.SELECTED.replace('record->selector = selector','record->selector = 0'),
            'swapped-color':source.SELECTED.replace('record->red = red','record->red = green'),
            'wrong-state':source.SELECTED.replace('record->state = 0','record->state = 1'),
            'wrong-callback':source.SELECTED.replace('record->callback = callback','record->callback = callback + 1'),
            'wrong-view':source.SELECTED.replace('record->view = view','record->view = callback'),
            'wrong-pointer-return':source.SELECTED.replace('return record;','return record + 1;'),
            'lost-success':source.SELECTED.replace('return record;','return NULL;'),
            'cleared-reserved-byte':source.SELECTED.replace('return record;','record->reserved[0] = 0;\n    return record;'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls),
            sizeof_record=32,word_value_not_assumed_pointer=True,seventh_argument_is_byte=True)

    def test_04_all_direct_sites_two_full_callers_and_large_caller_window(self):
        syms=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],syms)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);sites=[]
        for row in rows:
            if row['version']!='us' or row['section']not in DEFAULT_SEGMENTS['us']:continue
            base,off=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,syms)
            code=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+off)
            sites.extend((row['function'],entry+i*4)for i,w in enumerate(code)if w==opcode)
        self.assertEqual(sites,[('func_1502460C',0x15025AF0),('func_150B6C90',0x150B6CD4),('func_151CCE94',0x151CCEDC)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        count=0;visits=[set(),set()]
        for which,(entry,start,n)in enumerate(((0x150B6C90,0xE4140,41),(0x151CCE94,0x1FA344,29))):
            caller=list(struct.unpack_from('>%dI'%n,self.rom,start))
            for index,fail,gate,phase in itertools.product((0,1,128,255),(False,True),(0,1),(0,8)):
                args=(0,0,255,0,0,index,0,0)if which==0 else (0,0,0,255,0,index,1,4)
                case=Case(args,fail,index);memory=fixture(case,phase)
                put(memory,OLD,PREVIOUS if gate else 0);memory[DISABLED]=gate
                models=[]
                for code in (self.truth,self.words):
                    connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                    m=FactoryOracle(caller,case,phase,entry=entry,connected=connected,memory=memory,arguments=(ACTOR,)).run()
                    reached=which==0 or bool(gate)
                    self.assertEqual(m.entries,[args]if reached else [])
                    self.assertEqual(m.factory_packets,[packet(args)]if reached else [])
                    self.assertEqual(m.r[29],STACK+phase)
                    if which==0:
                        self.assertEqual(m.removals,[(PREVIOUS,)]if gate else [])
                        self.assertEqual(read(m.memory,OLD),0 if fail else OUTPUT)
                        self.assertEqual(m.memory[STATUS],3)
                        self.assertEqual(bytes(m.memory[0x800D9898+i]for i in range(0x28)),bytes(0x28))
                    elif gate:
                        self.assertEqual(m.copies,[]if fail else[(OUTPUT+0x20,STACK+phase-0x30+0x28,4)])
                        if not fail:self.assertEqual(read(m.memory,OUTPUT+0x20),ACTOR)
                    else:self.assertEqual(m.copies,[])
                    if reached:
                        expected,result=reference(case)
                        for i in range(0x10,0x20):self.assertEqual(m.memory[OUTPUT+i],expected[OUTPUT+i])
                    models.append(m);visits[which].update(m.visits)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for v,(entry,n)in zip(visits,((0x150B6C90,41),(0x151CCE94,29))):
            self.assertTrue(set(range(entry,entry+n*4,4))<=v)
        window=list(struct.unpack_from('>14I',self.rom,0x52F78));joins=window_count=0
        for value,fail,phase in itertools.product(WORDS,(False,True),(0,8)):
            args=(0,value,255,0,0,0x800000FF,0,0);case=Case(args,fail)
            memory=fixture(case,phase);base=0x87654000
            put(memory,STACK+phase+0x164,base);models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                m=FactoryOracle(window,case,phase,entry=0x15025AC8,connected=connected,memory=memory,
                    arguments=(0,),boundary=0x150265B4)
                m.r[2]=(base+value)&0xFFFFFFFF
                with self.assertRaises(CallerBoundary):m.run()
                self.assertEqual(m.boundary_hit,0x150265B4);self.assertEqual(m.entries,[args])
                self.assertEqual(m.r[2],1);self.assertEqual(m.r[29],STACK+phase)
                models.append(m);joins+=1
            self.assertEqual(complete(models[0]),complete(models[1]));window_count+=1
        self.receipt.update(all_direct_sites=sites,full_caller_words=[41,29],full_caller_phases=count,
            large_caller_window_words=14,large_caller_window_phases=window_count,fired_join_boundaries=joins,
            full2032_word_parent_executed=False,remove_and_memcpy_providers_bounded=True)

    def test_05_independent_GNU_call_rebases(self):
        count=0
        for delta in (0x10000,0x18000,0xCF20):
            images=[]
            for index,obj in enumerate((self.obj,source.original(ROOT,self.output))):
                script=self.output/'rebase.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                elf=self.output/('rebase-%d-%d.elf'%(delta,index))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=func_15167A68=0x%X'%(source.FACTORY+delta),'-o',str(elf),str(obj)],capture_output=True,check=True)
                _,data=sections(elf)['.text'];_,functions,_=source.parse_object(obj)
                images.append(list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value'])))
            self.assertEqual(images[0],images[1])
            for case in self.native_cases[::37]:
                m=FactoryOracle(images[0],case,delta=delta).run()
                self.assertEqual(m.factory_packets,[packet(case.words)])
                self.assertEqual(m.r[2],0 if case.fail else OUTPUT);count+=1
        self.receipt.update(independent_GNU_rebase_sets=3,rebase_phases=count)

    def test_06_complete_original_wrapper_and_list_insertion(self):
        connected={}
        for entry,start,n in ((source.FACTORY,0x194F18,28),(source.INITIALIZER,0x195EFC,20)):
            connected.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,self.rom,start)))
        count=0;visits=set()
        for old,extra,fail,phase in itertools.product((0,PREVIOUS),SIZES,(False,True),(0,8)):
            args=(0x1234,0x87654321,0x80000080,0xFFFFFFFF,0x1234007F,0x800000FF,0xCD,extra)
            case=Case(args,fail);memory=fixture(case,phase);put(memory,HEAD,old)
            expected,result=reference(case,phase,memory,initialize=True);models=[]
            for code in (self.truth,self.words):
                m=FactoryOracle(code,case,phase,connected=connected,memory=memory).run()
                self.assertEqual(m.factory_packets,[packet(args)])
                self.assertEqual(m.heap_packets,[((extra+32)&0xFFFFFFFF,1,0,0,1)])
                self.assertEqual(m.init_packets,[]if fail else[(OUTPUT,0x5A)])
                self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result)
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(original_chain_phases=count,all28_factory_wrapper_words=True,
            all20_list_initializer_words=True,lower258_word_heap_bounded=True,old_and_empty_list_heads=True)

    def test_07_strict_image_negatives(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+160]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        self.receipt['strict_image_negatives']=7

    def test_08_null_path_lazy_arguments_and_width_match_control(self):
        for code in (self.truth,self.words):
            m=FactoryOracle(code,Case(fail=True),drop_failed_arguments=True).run()
            self.assertEqual(m.r[2],0);self.assertEqual(len(m.factory_packets),1)
        bad=source.SELECTED.replace('u8 callback, u32 extraBytes','s32 callback, u32 extraBytes')
        self.assertNotEqual(bad,source.SELECTED)
        obj,diag=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.TYPES+bad,'wrong-word-callback')
        self.assertFalse(diag);self.assertNotEqual(source.payload(obj),source.payload(self.obj))
        self.receipt.update(failed_allocation_never_reloads_argument_homes=True,lazy_argument_checks_guest_only=True,
            word_callback_ABI_match_negative=True,signed_overflow_not_assumed=True)
