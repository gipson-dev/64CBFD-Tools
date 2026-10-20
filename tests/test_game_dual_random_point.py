"""Two independent RNG floats, fixed homes, point identity and both caller windows."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_dual_random_point as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary


ROOT = Path(__file__).resolve().parents[2]
POINT, ALT1, ALT2, NODE, STATE = 0x28000,0x29000,0x2A000,0x30000,0x31000
COORDS = (0.0,-0.0,1.75,-2.75,32768.25,-32768.75,65535.75,16777216.0,2147483520.0,-2147483648.0)
RANDOMS = (0,0x80000000,1,0x007FFFFF,0x00800000,0x3EAAAAAB,0x3F000000,0x3F7FFFFF,0x3F800000,
           bits(-1.0),bits(-3.0),bits(-4.0),bits(1e20),bits(-1e20))
WINDOWS = ((0x150F7A40,0x124EF0,0x150F7A64),(0x150F7ADC,0x124F8C,0x150F7B00))


@dataclass(frozen=True)
class Case:
    first: int = bits(0.25)
    second: int = bits(0.75)
    selector: int = 0x123400FF
    parameter: int = 0x87654321
    point: tuple = (bits(1.75),bits(-2.75),bits(32768.25))
    mutation: int = 0
    handle: int = 0
    home: int = 0
    integers: tuple = (0xFFFFFFFF,0x80000000)


def corpus():
    for i in range(256):
        yield Case(bits((i%65)/64),bits(((i*7)%65)/64),0xABCD0000|i,(i*0x01010101)&0xFFFFFFFF,
                   tuple(bits(COORDS[(i+j)%len(COORDS)])for j in range(3)),i%4,0x87650000 if i&1 else 0)
    for first,second in itertools.product(RANDOMS,repeat=2):
        yield Case(first,second,mutation=(first^second)&3,handle=0x80000000 if second&1 else 0)
    for selector,parameter,mutation in itertools.product((0,127,128,255,0xABCDEF80),(0,0x80000000,0xFFFFFFFF),range(4)):
        yield Case(selector=selector,parameter=parameter,mutation=mutation,handle=mutation&1)
    for home in (1,2,3):
        yield Case(home=home,mutation=3)


def first_pointer(case,point):
    return ALT1 if case.home&1 else point


def last_pointer(case,point):
    return ALT2 if case.home&2 else first_pointer(case,point)


def first_point(case):
    if case.mutation&1:
        return tuple(bits(100.0+i)for i in range(3))
    if case.home&1:
        return tuple(bits(400.0+i)for i in range(3))
    return case.point


def last_point(case):
    if case.home&2:
        return tuple(bits(700.0+i)for i in range(3))
    if case.mutation&2:
        return tuple(bits(200.0+i)for i in range(3))
    return first_point(case)


def widths(case):
    a=bits(floating(bits(floating(case.first)*3.0))+9.0)
    b=bits(floating(bits(floating(case.second)*70.0))+70.0)
    return a,b


def parameters(case,stage):
    if stage==2 and case.home&2:
        return 0xA5,0x76543210
    if case.home&1:
        return 0x5A,0x12345678
    return case.selector&255,case.parameter


def packets(case,point=POINT):
    a,b=widths(case);selector,word=parameters(case,1)
    first=(first_pointer(case,point),a,source.CONSTANT,b,0,selector,word)
    selector,word=parameters(case,2)
    last=(last_pointer(case,point),selector,word)
    return [('FIRST',first,first_point(case)),('SECOND',last,last_point(case))]


def fixture(case,point=POINT,gate=1):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x200)}
    for base,size in ((POINT-16,44),(ALT1-16,44),(ALT2-16,44),(NODE-16,0xA0),(STATE-16,0xA0)):
        memory.update({base+i:0xA5 for i in range(size)})
    for i,word in enumerate(case.point):
        put(memory,point+i*4,word)
    for base,start in ((ALT1,400.0),(ALT2,700.0)):
        for i in range(3):
            put(memory,base+i*4,bits(start+i))
    put(memory,NODE+12,case.selector&255,1);put(memory,NODE+1,case.parameter&255,1)
    put(memory,STATE+0x70,gate,1)
    return memory


class DualOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None,gate=1):
        self.case,self.delta=case,delta
        self.point=NODE+0x38 if entry==WINDOWS[1][0] else POINT
        self.target_sp=STACK+phase
        self.packets,self.emissions=[],[]
        self.float_calls,self.integer_calls,self.checked_first_home=0,0,0
        self.before_second_return=None;self.boundary_hit=None
        super().__init__(words,fixture(case,self.point,gate),phase=phase,entry=entry,
                         arguments=(self.point,case.selector,case.parameter),connected=connected)
        if entry in (w[0]for w in WINDOWS):
            self.r[16],self.r[17],self.r[20]=STATE,NODE,POINT
            self.code=ReturnBoundaryCode(self.code,next(w[2]for w in WINDOWS if w[0]==entry),self)

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            value=floating(self.f[word>>11&31])
            assert math.isfinite(value) and -2147483648<=math.trunc(value)<2147483648
            self.f[word>>6&31]=math.trunc(value)&0xFFFFFFFF
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            assert self.arguments(3)==(self.point,self.case.selector&255,self.case.parameter&255)
            self.target_sp=self.r[29];args=self.arguments(3)
        elif target==source.FLOAT_RNG+self.delta:
            assert self.float_calls<2,'Positive first-provider RNG is outside this fixture'
            args=()
            if self.float_calls==1:
                assert read(self.memory,self.r[29]+0x28)==self.case.first
                self.checked_first_home+=1
        elif target==source.FIRST+self.delta:
            args=self.arguments(7)
            self.packets.append(('FIRST',args,tuple(read(self.memory,args[0]+i*4)for i in range(3))))
        elif target==source.SECOND+self.delta:
            args=self.arguments(3)
            self.before_second_return=self.r[2]
            self.packets.append(('SECOND',args,tuple(read(self.memory,args[0]+i*4)for i in range(3))))
        elif target==source.INTEGER_RNG:
            assert self.integer_calls<2;args=()
        elif target==source.EMIT:
            args=self.arguments(11);descriptor,coords=args[:2]
            fields=(read(self.memory,descriptor,1),read(self.memory,descriptor+1,1),
                    read(self.memory,descriptor+2,2),read(self.memory,descriptor+4,1))
            self.emissions.append((fields,tuple(read(self.memory,coords+i*4)for i in range(3)),args[2:]))
        else:
            raise AssertionError(('Unknown dual-point provider',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678

    def hook(self,target):
        result=0x76543210
        if target==source.FLOAT_RNG+self.delta:
            self.float_calls+=1
            value=self.case.first if self.float_calls==1 else self.case.second
            if self.float_calls==2:
                if self.case.home&1:
                    for off,word in ((0,ALT1),(4,0x1234005A),(8,0x12345678)):
                        self.put(self.target_sp+off,word,4)
                if self.case.mutation&1:
                    p=first_pointer(self.case,self.point)
                    for i in range(3):
                        self.put(p+i*4,bits(100.0+i),4)
        elif target==source.FIRST+self.delta:
            if self.case.mutation&2:
                p=self.r[4]
                for i in range(3):
                    self.put(p+i*4,bits(200.0+i),4)
            if self.case.home&2:
                for off,word in ((0,ALT2),(4,0x123400A5),(8,0x76543210)):
                    self.put(self.target_sp+off,word,4)
            result=self.case.handle
        elif target==source.INTEGER_RNG:
            result=self.case.integers[self.integer_calls];self.integer_calls+=1
        elif target not in (source.SECOND+self.delta,source.EMIT):
            raise AssertionError(('Unbounded dual-point provider',target))
        self.clobber();self.r[2]=result
        if target==source.FLOAT_RNG+self.delta:
            self.f[0]=value


def native_harness(body,cases):
    rows=['{'+','.join('0x%Xu'%v for v in
          (c.first,c.second,c.selector,c.parameter,c.mutation,c.handle,*widths(c)))+
          ',{'+','.join('0x%Xu'%v for v in c.point)+'},{'+
          ','.join('0x%Xu'%v for v in first_point(c))+'},{'+
          ','.join('0x%Xu'%v for v in last_point(c))+'}}'for c in cases]
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef short s16;typedef float f32;
typedef struct{f32 unk0,unk4,unk8;}struct17;
''' + source.DECLARATIONS.replace('#include "structs.h"','') + body + '''
typedef struct{u32 first,second,selector,parameter,mutation,handle,a,b,point[3],firstPoint[3],lastPoint[3];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct{u32 before[4];struct17 point;u32 after[4];}storage;
static int calls,error;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
__attribute__((noinline))f32 func_150ADA68(void){
    int ordinal=calls++;
    if(ordinal>1){error=1;return 0.0f;}
    if(ordinal==1 && item->mutation&1){storage.point.unk0=100.0f;storage.point.unk4=101.0f;storage.point.unk8=102.0f;}
    return real(ordinal?item->second:item->first);
}
__attribute__((noinline))void *func_151541B8(struct17 *point,f32 a,f32 constant,f32 b,f32 extra,u8 selector,s32 parameter){
    if(calls++!=2 || point!=&storage.point || word(a)!=item->a || word(b)!=item->b ||
       word(constant)!=0x3F030C35u || word(extra)!=0 || selector!=(item->selector&255) ||
       (u32)parameter!=item->parameter){error=1;return (void *)item->handle;}
    if(word(point->unk0)!=item->firstPoint[0] || word(point->unk4)!=item->firstPoint[1] ||
       word(point->unk8)!=item->firstPoint[2])error=1;
    if(item->mutation&2){point->unk0=200.0f;point->unk4=201.0f;point->unk8=202.0f;}
    return (void *)item->handle;
}
__attribute__((noinline))void func_151D3F14(struct17 *point,u8 selector,s32 parameter){
    if(calls++!=3 || point!=&storage.point || selector!=(item->selector&255) ||
       (u32)parameter!=item->parameter){error=1;return;}
    if(word(point->unk0)!=item->lastPoint[0] || word(point->unk4)!=item->lastPoint[1] ||
       word(point->unk8)!=item->lastPoint[2])error=1;
}
static int test_all(void){
    u32 n,i;
    if(sizeof(struct17)!=12 || __builtin_offsetof(struct17,unk4)!=4 || __builtin_offsetof(struct17,unk8)!=8)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<4;i++){storage.before[i]=0xA5A5A5A5u;storage.after[i]=0xA5A5A5A5u;}
        storage.point.unk0=real(item->point[0]);storage.point.unk4=real(item->point[1]);storage.point.unk8=real(item->point[2]);
        func_150F7F8C(&storage.point,(u8)item->selector,(s32)item->parameter);
        if(error || calls!=4)return 23;
        for(i=0;i<4;i++)if(storage.before[i]!=0xA5A5A5A5u || storage.after[i]!=0xA5A5A5A5u)return 24;
        if(word(storage.point.unk0)!=item->lastPoint[0] || word(storage.point.unk4)!=item->lastPoint[1] ||
           word(storage.point.unk8)!=item->lastPoint[2])return 25;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class DualRandomPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output)
        cls.obj,diagnostic=source.compile_owner(ROOT,cls.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diagnostic:
            raise ValueError(diagnostic)
        data,funcs=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>40I',data,funcs[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.home]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),
                         guards=0,matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('dual random point qualification:',cls.receipt)

    def test_01_direct_words_bindings_first_home_and_exact_constant(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.output)))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),4)
        self.assertEqual(self.words[8:10],[0xE7A00028,0xC7B20028])
        self.assertEqual(self.words[21],0x3C063F03);self.assertEqual(self.words[24],0x34C60C35)
        self.assertEqual(bits(0.5119050145149231),source.CONSTANT)
        first=struct.unpack_from('>221I',self.rom,0x181668)
        second=struct.unpack_from('>56I',self.rom,0x2013C4)
        self.assertEqual(first[:7],(0x27BDFF40,0x44856000,0x44801000,0xAFBF001C,0xAFA400C0,0xAFA600C8,0xAFA700CC))
        self.assertIn(0x93A800D7,first);self.assertIn(0x8FA900D8,first);self.assertIn(0x00601025,first)
        self.assertEqual(second[2:4],(0xAFA50054,0xAFA60058))
        self.receipt.update(complete_helper_interfaces_inspected=True,first_provider_pointer_return=True)

    def test_02_complete_state_independent_math_calls_clobbers_and_home_redirects(self):
        visits=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            a=DualOracle(self.truth,case,phase).run();b=DualOracle(self.words,case,phase).run()
            self.assertEqual(complete(a),complete(b));self.assertEqual(b.packets,packets(case))
            self.assertEqual([c[0]for c in b.calls],[source.FLOAT_RNG,source.FLOAT_RNG,source.FIRST,source.SECOND])
            self.assertEqual(b.checked_first_home,1)
            self.assertEqual(b.before_second_return,case.handle)
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg],b.before[reg])
            self.assertEqual(b.f[20:],b.saved_f);visits.update(b.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=visits)
        self.receipt.update(full_model_phases=len(self.cases)*2,all40_words_visited=True,
            separate_float32_rounding=True,first_home_checked_before_second_RNG=True,
            first_result_NULL_does_not_skip_second=True,home_redirect_cases_guest_only=3)

    def native(self,body,label,optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+optimization)
        args=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True)
        (self.output/(label+optimization+'-compiler.log')).write_text(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,p.stderr[:6000])
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_three_optimizations_and_effective_semantic_negatives(self):
        for optimization in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',optimization),0)
        conditional=source.SELECTED.replace('    func_151541B8(','    if (func_151541B8(').replace(
            '0.0f, selector, parameter);','0.0f, selector, parameter)) {').replace(
            '    func_151D3F14(point, selector, parameter);','        func_151D3F14(point, selector, parameter);\n    }')
        controls={
            'one-RNG':source.SELECTED.replace('second = func_150ADA68();','second = first;'),
            'mixed-first':source.SELECTED.replace('first * 3.0f','(first + second) * 3.0f'),
            'wrong-first-offset':source.SELECTED.replace('+ 9.0f','+ 8.0f'),
            'mixed-second':source.SELECTED.replace('second * 70.0f','(second + first) * 70.0f'),
            'wrong-second-offset':source.SELECTED.replace('+ 70.0f','+ 71.0f'),
            'wrong-constant-ULP':source.SELECTED.replace('0.5119050145149231f','0.5119050741195679f'),
            'wrong-extra':source.SELECTED.replace('0.0f, selector','1.0f, selector'),
            'wrong-selector':source.SELECTED.replace('selector, parameter','selector ^ 0x80, parameter'),
            'narrow-word':source.SELECTED.replace('selector, parameter','selector, (s16)parameter'),
            'conditional-second':conditional,
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls))

    def test_04_direct_caller_inventory_and_both_actual_gate_windows(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()));add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:
                continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(words)if w==opcode)
        self.assertEqual(found,[('func_150F78B4',0x150F7A58),('func_150F78B4',0x150F7AF4)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        count,active=0,0
        for (entry,rom,boundary),original,gate,phase in itertools.product(WINDOWS,self.native_cases[::47],(0,1),(0,8)):
            case=replace(original,selector=original.selector&255,parameter=original.parameter&255)
            window=list(struct.unpack_from('>9I',self.rom,rom))
            self.assertEqual(window[6:8],[opcode,0x92260001])
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                model=DualOracle(window,case,phase,entry=entry,connected=connected,gate=gate)
                with self.assertRaises(CallerBoundary):
                    model.run()
                self.assertEqual(model.boundary_hit,boundary);self.assertEqual(model.r[29],STACK+phase)
                self.assertEqual(model.packets,packets(case,model.point)if gate else [])
                self.assertEqual(model.float_calls,2 if gate else 0);models.append(model)
                if entry==WINDOWS[0][0]:
                    self.assertEqual(read(model.memory,STACK+phase+0x1AF,1),0)
                else:
                    self.assertEqual(model.r[1],0x3F800000)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1;active+=bool(gate)
        self.receipt.update(all_direct_retail_call_sites=found,actual_caller_window_phases=count,
            active_caller_window_phases=active,actual_join_boundaries=count*2,full_parent_execution_claimed=False)

    def test_05_independent_GNU_four_call_rebases(self):
        count=0
        for delta in (0x10000,0xCF20,0x18000):
            images=[]
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf,script=self.output/('rebase-%d-%d.elf'%(delta,i)),self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                definitions=['--defsym=%s=0x%X'%(name,address+delta)for name,address in (
                    ('func_150ADA68',source.FLOAT_RNG),('func_151541B8',source.FIRST),('func_151D3F14',source.SECOND))]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *definitions,'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::29]:
                model=DualOracle(images[0],case,delta=delta).run()
                self.assertEqual(model.packets,packets(case));count+=1
        self.receipt.update(independent_rebase_phases=count,rebase_sets=3)

    def test_06_strict_image_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+160]
        predicted=source.predicted_image(before,truth);self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_negative_controls']=7

    def test_07_actual_first_helper_early_NULL_return_still_reaches_second(self):
        helper=list(struct.unpack_from('>221I',self.rom,0x181668))
        connected=dict(zip(range(source.FIRST,source.FIRST+884,4),helper))
        visits=set();count=0
        for first,second,phase in itertools.product((-3.0,-4.0,-100.0),(0.0,0.5,1.0),(0,8)):
            case=Case(first=bits(first),second=bits(second))
            models=[]
            for code in (self.truth,self.words):
                model=DualOracle(code,case,phase,connected=connected).run()
                self.assertEqual(model.packets,packets(case));self.assertEqual(model.before_second_return,0)
                self.assertEqual(model.float_calls,2);models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        covered=len(visits&set(connected));self.assertEqual(covered,18)
        self.receipt.update(original_first_NULL_phases=count,first_helper_reachable_gate_words=covered,
                            positive_first_factory_and_FCSR_execution_claimed=False)

    def test_08_complete_original_second_helper_unsigned_counts_coordinates_and_emission(self):
        helper=list(struct.unpack_from('>56I',self.rom,0x2013C4))
        connected=dict(zip(range(source.SECOND,source.SECOND+224,4),helper))
        visits=set();count=0;counts=set();modes=set()
        for i,phase in itertools.product(range(39),(0,8)):
            case=Case(first=bits(i/38),second=bits(((i*7)%39)/38),selector=(i*73)&255,
                parameter=0x80000000^i,point=tuple(bits(COORDS[(i+j)%len(COORDS)])for j in range(3)),
                mutation=i%4,integers=(0xFFFFFFFF if i&1 else i,0x80000000 if i%3==0 else i))
            models=[]
            descriptor=(3,255,case.integers[0]%3+4,0)
            coords=tuple(math.trunc(floating(w))&0xFFFFFFFF for w in last_point(case))
            tail=(case.integers[1]%13+20,255,232,171,255,0,0,*parameters(case,2))
            for code in (self.truth,self.words):
                model=DualOracle(code,case,phase,connected=connected).run()
                self.assertEqual(model.packets,packets(case));self.assertEqual(model.integer_calls,2)
                self.assertEqual(model.emissions,[(descriptor,coords,tail)])
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1;counts.add(descriptor[2]);modes.add(tail[0])
        self.assertTrue(set(connected)<=visits);self.assertEqual(counts,{4,5,6});self.assertEqual(modes,set(range(20,33)))
        self.receipt.update(original_second_helper_phases=count,all56_second_helper_words_visited=True,
                            second_integer_count_range=[4,6],second_mode_range=[20,32],lower_emitter_bounded=True)
