"""Zero-health callback ABI, lazy byte gates and direct C image isolation."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_zero_health_callback as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary

ROOT = Path(__file__).resolve().parents[2]
ACTOR, OTHER, FLAG, DESC, FALLBACK, STATE = 0x28000, 0x29000, 0x30000, 0x31000, 0x32000, 0x33000
LOWER, LEVEL, DISABLED = 0x15053694, 0x800BE9F0, 0x800BE616
SIGNATURES = {source.FIRST:8, source.SECOND:1, source.THIRD:2}
BINDINGS = {0x58:[('R_MIPS_26','func_15136C3C')],
    0x60:[('R_MIPS_26','func_15145A50')],0x6C:[('R_MIPS_26','func_1507CD64')]}


@dataclass(frozen=True)
class Case:
    health:int=0
    selector:int=0
    kind:int=0x47
    mutation:int=0
    alias:bool=False


def corpus():
    for value in range(256):
        yield Case(value,0,value,value%32)
        yield Case(0,value,0x47,value%32)
        yield Case(0,0,value)
    for health,selector,kind,mode in itertools.product((0,255),(0,255),(0x46,0x47),range(16)):
        yield Case(health,selector,kind,mode,True)


def other(case):
    return ACTOR if case.alias else OTHER


def fixture(case):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x200)}
    for base,size in ((ACTOR,0x32C),(OTHER,0x32C),(FLAG,4),(DESC,16),(FALLBACK,16),(STATE,0xA0)):
        memory.update({base+i:0xA5 for i in range(-16,size+16)})
    memory[ACTOR+4]=0x42
    memory[ACTOR+0x127]=case.selector
    memory[ACTOR+0x1CA]=case.health
    memory[OTHER+0x1CA]=0x7B
    memory[other(case)+4]=case.kind
    put(memory,ACTOR+0x31C,0)
    put(memory,LEVEL,0);memory[DISABLED]=0
    put(memory,source.TABLE+34*4,source.ENTRY)
    return memory


def effects(memory,case,index):
    p=other(case)
    if index==0:
        if case.mutation&1:memory[p+4]=0x47
        if case.mutation&8:
            memory[ACTOR+0x1CA]=0xFE
            memory[ACTOR+0x127]=0xFF
    if index==1:
        if case.mutation&2:memory[p+4]=0x46
        if case.mutation&16:memory[p+0x1CA]=0x77
    if index==2 and case.mutation&4:memory[p+4]=0x47


def reference(case,initial=None):
    memory=dict(fixture(case) if initial is None else initial);calls=[]
    if memory[ACTOR+0x1CA]==0 and memory[ACTOR+0x127]!=255:
        calls=[(source.FIRST,(ACTOR,1,1,1,1,0,255,1)),
               (source.SECOND,(ACTOR,)),(source.THIRD,(ACTOR,6))]
        for index in range(3):effects(memory,case,index)
    if memory[other(case)+4]==0x47:memory[other(case)+0x1CA]=0
    return memory,calls


def public(memory):
    return {k:v for k,v in memory.items() if not STACK-0x800<=k<STACK+0x200}


class HealthOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None,
            boundary=None,memory=None):
        self.case,self.delta=case,delta
        self.packets,self.callback_packets,self.low_packets,self.visits=[],[],[],set()
        super().__init__(words,fixture(case) if memory is None else memory,phase=phase,
            entry=entry,arguments=(other(case),ACTOR,FLAG),connected=connected)
        self.r[2]=0x87654321
        if boundary is not None:self.code=ReturnBoundaryCode(self.code,boundary,self)

    def execute(self,word):
        self.visits.add(self.current_pc)
        super().execute(word)

    def record_call(self,target):
        canonical=target-self.delta
        if canonical in SIGNATURES:
            args=self.arguments(SIGNATURES[canonical])
            self.packets.append((canonical,args))
        elif target==source.ENTRY:
            args=self.arguments(3);self.callback_packets.append(args)
        elif target==LOWER:
            args=self.arguments(1);self.low_packets.append((target,args))
        else:raise AssertionError(('Unbounded zero-health call',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        canonical=target-self.delta
        if canonical in SIGNATURES:effects(self.memory,self.case,(source.FIRST,source.SECOND,source.THIRD).index(canonical))
        elif target!=LOWER:raise AssertionError(('Unbounded zero-health provider',hex(target)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0x87654321
        self.hi,self.lo=0x87654321,0x12345678


def native_harness(body,cases):
    rows=[]
    for case in cases:
        expected,calls=reference(case)
        rows.append('{%s}'%','.join(str(x)+'u' for x in
            (case.health,case.selector,case.kind,case.mutation,int(case.alias),len(calls),
             expected[ACTOR+4],expected[ACTOR+0x127],expected[ACTOR+0x1CA],
             expected[OTHER+4],expected[OTHER+0x1CA])))
    return """typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
typedef struct{u8 pad0[4];u8 id;u8 pad5[0x122];u8 unk127;
u8 pad128[0xA2];u8 health;u8 pad1CB[0x161];}struct127;
""" + source.DECLARATIONS.replace('#include "structs.h"','') + body + """
typedef struct{u32 health,selector,kind,mode,alias,calls,actorId,actorSelector,actorHealth,otherId,otherHealth;}Case;
static const Case cases[]={""" + ',\n'.join(rows) + """};
static struct{u32 before[4];struct127 value;u32 after[4];}a,b;
static u8 flag[3];
static const Case *item;
static struct127 *partner;
static int calls,error;
static void change(int step){
    if(step==0){
        if(item->mode&1)partner->id=0x47;
        if(item->mode&8){a.value.health=0xFE;a.value.unk127=0xFF;}
    }
    if(step==1){
        if(item->mode&2)partner->id=0x46;
        if(item->mode&16)partner->health=0x77;
    }
    if(step==2 && (item->mode&4))partner->id=0x47;
}
__attribute__((noinline))s32 func_15136C3C(void *p,s32 v1,s32 v2,s32 v3,s32 v4,s32 v5,s32 v6,s32 v7){
    if(calls++!=0 || p!=&a.value || v1!=1 || v2!=1 || v3!=1 ||
       v4!=1 || v5!=0 || v6!=255 || v7!=1)error=1;
    change(0);return (s32)0x87654321u;
}
__attribute__((noinline))void func_15145A50(struct127 *p){
    if(calls++!=1 || p!=&a.value)error=1;change(1);
}
__attribute__((noinline))s32 func_1507CD64(struct127 *p,s32 mode){
    if(calls++!=2 || p!=&a.value || mode!=6)error=1;
    change(2);return (s32)0x87654321u;
}
static void (*callbacks[39])(struct127 *,struct127 *,u8 *)={[34]=func_15195698};
static int test_all(void){
    u32 n,i;
    if(sizeof(void *)!=4 || sizeof(struct127)!=0x32C ||
       __builtin_offsetof(struct127,id)!=4 || __builtin_offsetof(struct127,unk127)!=0x127 ||
       __builtin_offsetof(struct127,health)!=0x1CA)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(a);i++)((u8 *)&a)[i]=0xA5;
        for(i=0;i<sizeof(b);i++)((u8 *)&b)[i]=0xA5;
        a.value.id=0x42;a.value.health=(u8)item->health;a.value.unk127=(u8)item->selector;
        b.value.health=0x7B;partner=item->alias?&a.value:&b.value;partner->id=(u8)item->kind;
        flag[0]=0xA5;flag[1]=0x87;flag[2]=0xA5;
        callbacks[34](partner,&a.value,&flag[1]);
        if(error || calls!=(int)item->calls || a.value.id!=item->actorId ||
           a.value.unk127!=item->actorSelector || a.value.health!=item->actorHealth ||
           b.value.id!=item->otherId || b.value.health!=item->otherHealth)return 23;
        if(flag[0]!=0xA5 || flag[1]!=0x87 || flag[2]!=0xA5)return 23;
        for(i=0;i<4;i++)if(a.before[i]!=0xA5A5A5A5u || a.after[i]!=0xA5A5A5A5u ||
            b.before[i]!=0xA5A5A5A5u || b.after[i]!=0xA5A5A5A5u)return 24;
        for(i=0;i<sizeof(struct127);i++){
            if(i!=4 && i!=0x127 && i!=0x1CA && ((u8 *)&a.value)[i]!=0xA5)return 25;
            if(i!=4 && i!=0x1CA && ((u8 *)&b.value)[i]!=0xA5)return 25;
        }
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ZeroHealthCallbackTests(unittest.TestCase):
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
        obj,diag=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        cls.obj=obj;cls.raw,cls.bindings=source.payload(obj)
        data,functions=source.link_owner(ROOT,cls.output,obj,source.OWNER)
        cls.words=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        cls.cases=list(corpus())
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('zero-health callback qualification:',cls.receipt)

    def test_01_direct_words_bindings_frame_and_owner(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(len(self.raw),160);self.assertEqual(self.bindings,BINDINGS)
        self.assertEqual(self.truth[0],0x27BDFFD0)
        before=self.values['conker/build/conker.us.elf']
        old=list(struct.unpack_from('>40I',before,source.elf_slot_offset(before,source.ENTRY,160)))
        old_model=HealthOracle(old,Case()).run()
        self.assertNotEqual(old_model.packets,reference(Case())[1])
        self.assertNotEqual(public(old_model.memory),public(reference(Case())[0]))
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(self.raw,self.bindings))
        self.assertEqual(source.payload(self.output/'qualified-padded.o'),(self.raw,self.bindings))
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),
                         self.values['conker/retail_word_patches.us.csv'])
        q=json.loads((self.output/'qualification.json').read_text())
        make=json.loads((self.output/'make-shadow.json').read_text())
        self.assertTrue(q['owner_diagnostics_unchanged']);self.assertTrue(q['all_owner_addresses_fixed'])
        self.assertEqual(make['actual_Make_commands'],5)
        self.receipt.update(words=40,frame=48,bindings=3,compiler_only=True,
            preserved_neighbors=q['preserved_neighbors'],actual_Make_commands=5,guard_manifest_unchanged=True,
            actual_old_compiled_stub_rejected=True)

    def test_02_all_bytes_late_reads_aliases_and_complete_modeled_state(self):
        visits=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            expected,packets=reference(case);models=[]
            for code in (self.truth,self.words):
                m=HealthOracle(code,case,phase).run()
                self.assertEqual(m.packets,packets);self.assertEqual(public(m.memory),public(expected))
                self.assertEqual(m.r[29],STACK+phase)
                self.assertEqual(m.r[2],0x87654321)
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]))
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=visits)
        self.receipt.update(modeled_phases=len(self.cases)*2,all40_target_words_executed=True,
            all256_gate_bytes=True,legal_same_actor_aliases=True,late_type_reads=True,ignored_return_values=True)

    def native(self,body,name,opt='-O2'):
        path=self.output/(name+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.cases))
        subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib',
            '-fno-stack-protector','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],
            capture_output=True,check=True)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_typed_callback_and_effective_negatives(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'wrong-health':source.SELECTED.replace('actor->health == 0','actor->health != 0'),
            'wrong-selector':source.SELECTED.replace('actor->unk127 != 0xFF','actor->unk127 == 0xFF'),
            'signed-selector-range':source.SELECTED.replace('actor->unk127 != 0xFF','actor->unk127 < 0x80'),
            'wrong-zero-argument':source.SELECTED.replace('1, 0, 0xFF, 1','1, 1, 0xFF, 1'),
            'wrong-ff-argument':source.SELECTED.replace('1, 0, 0xFF, 1','1, 0, 0x7F, 1'),
            'wrong-call-order':source.SELECTED.replace('func_15145A50(actor);\n        func_1507CD64(actor, 6);','func_1507CD64(actor, 6);\n        func_15145A50(actor);'),
            'wrong-command':source.SELECTED.replace('func_1507CD64(actor, 6)','func_1507CD64(actor, 5)'),
            'skipped-third':source.SELECTED.replace('        func_1507CD64(actor, 6);',''),
            'wrong-other-type':source.SELECTED.replace('other->id == 0x47','other->id == 0x46'),
            'wrong-clear-destination':source.SELECTED.replace('other->health = 0','actor->health = 0'),
            'cached-type':source.SELECTED.replace('    if ((actor->health','    u8 kind = other->id;\n    if ((actor->health').replace('other->id == 0x47','kind == 0x47'),
            'unexpected-event-write':source.SELECTED.replace('    if (other->id','    if (arg2) *arg2 = 0;\n    if (other->id'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED);self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_cases=len(self.cases),native_optimizations=3,trap_UBSan=True,
            compiled_semantic_negatives=len(controls),typed_third_argument='unused byte pointer',
            native_layout='independent 32-bit struct127 subset; IDO field offsets pinned separately')

    def test_04_callback_inventory_and_two_real_dispatch_windows(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);direct=[]
        for row in rows:
            if row['version']!='us' or row['section']not in DEFAULT_SEGMENTS['us']:continue
            base,off=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            code=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+off)
            direct.extend((row['function'],entry+4*i)for i,w in enumerate(code)if w==opcode)
        self.assertFalse(direct)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)],[0x22B1DC])
        table=struct.unpack_from('>39I',self.rom,0x22B154)
        self.assertEqual(table[34],source.ENTRY);self.assertEqual(table[-2:],(0,0))
        count=joins=callbacks=0
        for slot,(entry,rom,n,boundary,eventoff)in enumerate((
                (0x1505BD5C,0x8920C,17,0x1505BDA0,0x67),
                (0x1505C6DC,0x89B8C,8,0x1505C6FC,0x54))):
            window=list(struct.unpack_from('>%dI'%n,self.rom,rom))
            for case,phase,fallback,skip in itertools.product(self.cases[::113],(0,8),(False,True),(False,True)):
                if slot==1 and (fallback or skip):continue
                models=[]
                for code in (self.truth,self.words):
                    memory=fixture(case);memory[DESC+8]=0 if fallback else 34;memory[FALLBACK+8]=34
                    memory[STACK+phase+0x67]=0x27 if skip else 0
                    put(memory,STACK+phase+0x68,other(case))
                    connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                    m=HealthOracle(window,case,phase,entry=entry,connected=connected,boundary=boundary,memory=memory)
                    m.r[16]=ACTOR;m.r[17]=other(case);m.r[25]=DESC;m.r[9]=FALLBACK;m.r[2]=34
                    with self.assertRaises(CallerBoundary):m.run()
                    self.assertEqual(m.boundary_hit,boundary);self.assertEqual(m.r[29],STACK+phase)
                    reached=slot==1 or not skip
                    expected_packets=reference(case)[1]if reached else []
                    self.assertEqual(m.packets,expected_packets)
                    self.assertEqual(m.callback_packets,[(other(case),ACTOR,STACK+phase+eventoff)]if reached else [])
                    self.assertEqual(m.r[16],ACTOR);self.assertEqual(m.r[17],other(case))
                    models.append(m);joins+=1
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
                callbacks+=int(slot==1 or not skip)
        self.receipt.update(direct_sites=direct,literal_pointer_ROM=0x22B1DC,callback_table_index=34,
            dispatcher_window_words=[17,8],dispatcher_phases=count,fired_join_boundaries=joins,
            reached_callback_phases=callbacks,full_dispatcher_parents_executed=False)

    def test_05_independent_GNU_call_rebases(self):
        count=0
        for delta in (0x10000,0x18000,0xCF20):
            images=[]
            for index,obj in enumerate((self.obj,source.original(ROOT,self.output))):
                script=self.output/'rebase.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                elf=self.output/('rebase-%d-%d.elf'%(delta,index))
                defs=['--defsym=%s=0x%X'%(name,address+delta)for name,address in
                    (('func_15136C3C',source.FIRST),('func_15145A50',source.SECOND),('func_1507CD64',source.THIRD))]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *defs,'-o',str(elf),str(obj)],capture_output=True,check=True)
                _,data=sections(elf)['.text'];_,functions,_=source.parse_object(obj)
                images.append(list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value'])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::47]:
                m=HealthOracle(images[0],case,delta=delta).run()
                self.assertEqual(m.packets,reference(case)[1]);count+=1
        self.receipt.update(independent_GNU_rebase_sets=3,rebase_phases=count,all_three_call_bindings=True)

    def test_06_original_state_helper_and_final_null_path(self):
        second=dict(zip(range(source.SECOND,source.SECOND+34*4,4),struct.unpack_from('>34I',self.rom,0x172F00)))
        count=0;visits=set()
        for level,disabled,state,pointer,phase in itertools.product((0,51),(0,1),(0,1,5,21,8),(0,STATE),(0,8)):
            case=Case();memory=fixture(case)
            put(memory,LEVEL,level);memory[DISABLED]=disabled;put(memory,ACTOR,state);put(memory,ACTOR+0x31C,pointer)
            expected,packets=reference(case,memory);expected[ACTOR+5]=3
            lower=False
            if level!=51:
                if disabled or state in (1,5,21):
                    put(expected,ACTOR,5)
                    if pointer:put(expected,pointer+0x78,0,1)
                else:lower=True
            models=[]
            for code in (self.truth,self.words):
                m=HealthOracle(code,case,phase,connected=second,memory=memory).run()
                self.assertEqual(m.packets,packets);self.assertEqual(public(m.memory),public(expected))
                self.assertEqual(m.low_packets,[(LOWER,(ACTOR,))]if lower else [])
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        third=dict(zip(range(source.THIRD,source.THIRD+253*4,4),struct.unpack_from('>253I',self.rom,0xAA214)))
        final_visits=set()
        for case,phase in itertools.product((Case(),Case(kind=0),Case(alias=True)),(0,8)):
            models=[]
            for code in (self.truth,self.words):
                m=HealthOracle(code,case,phase,connected=third).run()
                self.assertEqual(m.packets,reference(case)[1]);self.assertEqual(public(m.memory),public(reference(case)[0]))
                self.assertEqual(m.r[2],0)
                models.append(m);final_visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]))
        covered=sorted(a for a in visits if a in second)
        self.assertTrue(set(second)<=visits)
        self.assertIn(source.THIRD,final_visits)
        self.receipt.update(original_state_helper_phases=count,original_state_helper_words_visited=len(covered),
            original_state_helper_slot_words=34,original_final_null_phases=6,
            original_final_null_words_visited=len(set(third)&final_visits),
            original_final_slot_words=253,first197_word_helper_and_lower_state_provider_bounded=True)

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

    def test_08_lazy_gate_and_unused_event_pointer(self):
        count=0
        for code in (self.truth,self.words):
            case=Case(health=128);m=HealthOracle(code,case)
            del m.memory[ACTOR+0x127]
            for i in range(4):del m.memory[FLAG+i]
            m.r[6]=0xFFFFFFFF;m.run()
            self.assertEqual(m.packets,[]);self.assertEqual(m.r[2],0x87654321)
            self.assertEqual(m.memory[OTHER+0x1CA],0);count+=1
            m=HealthOracle(code,Case(health=1));m.r[4]=0
            with self.assertRaisesRegex(AssertionError,'unmapped read'):m.run()
            m=HealthOracle(code,Case());m.r[5]=0
            with self.assertRaisesRegex(AssertionError,'unmapped read'):m.run()
        self.receipt.update(lazy_selector_cases=count,event_pointer_never_dereferenced=True,
            NULL_fault_checks_guest_only=True,defensive_NULL_behavior_added=False)
