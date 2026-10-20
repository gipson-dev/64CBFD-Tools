"""Camera heading gate, late vector reads, store order and linked image isolation."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_camera_heading as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete

ROOT = Path(__file__).resolve().parents[2]
CAMERA, DESC = 0x28000, 0x2A000
CALLER, CALLER_ROM = 0x151283B8, 0x155868
PARENT, PARENT_ROM, ACTOR = 0x15126138, 0x1535E8, 0x30000
COORDS = (0.0, -0.0, 1.75, -2.75, 16777216.0, 1e20, -1e20, floating(1))
ANGLES = (0, 0x80000000, bits(45.0), bits(90.0), bits(180.0), bits(359.75), bits(-90.0))


@dataclass(frozen=True)
class Case:
    flags: int = 0
    points: tuple = tuple(bits(x) for x in (1.0, 2.0, 3.0, 5.0, 6.0, 7.0, 9.0, 10.0, 11.0))
    angle: int = bits(45.0)
    factor: int = source.CONSTANT
    mutation: int = 0
    alias: bool = False


def corpus():
    for i in range(256):
        for flags in (i, i << 8):
            yield Case(flags, tuple(bits(COORDS[(i+j) % len(COORDS)]) for j in range(9)),
                       ANGLES[i % len(ANGLES)], source.CONSTANT, i % 4)
    for flags, mutation, angle in itertools.product((0,4,0x400,0x8000,0xFFFF), range(4), ANGLES):
        yield Case(flags=flags, mutation=mutation, angle=angle)
    for mutation, angle in itertools.product(range(4), ANGLES):
        yield Case(mutation=mutation, angle=angle, alias=True)


def camera_address(case, factor=source.FACTOR):
    return factor - 0x37C if case.alias else CAMERA


def changed_points(points):
    result = list(points)
    result[0], result[2], result[3], result[5] = map(bits, (101.0, -103.0, 211.0, -223.0))
    return result


def vector(case):
    p = list(case.points)
    initial = [bits(floating(p[i])-floating(p[6+i])) for i in range(3)]
    if case.mutation & 1:
        p = changed_points(p)
    initial[0] = bits(floating(initial[0])+floating(bits(floating(p[3])-floating(p[0]))))
    initial[2] = bits(floating(initial[2])+floating(bits(floating(p[5])-floating(p[2]))))
    return tuple(initial)


def result(case):
    if case.flags & 4:
        return (case.factor if case.alias else bits(-17.0)), bits(-19.0)
    factor = case.angle if case.alias else bits(0.25) if case.mutation & 2 else case.factor
    return case.angle, bits(floating(case.angle)*floating(factor))


def fixture(case, factor=source.FACTOR, mode=2):
    camera = camera_address(case, factor)
    memory = {STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x200)}
    memory.update({camera+i:0xA5 for i in range(-16,0x9B0)})
    memory.update({DESC+i:0xA5 for i in range(-16,32)})
    for off, value in ((0x2C,mode),(0xDC,4),(0x36C,DESC),(0x37C,bits(-17.0)),(0x39C,bits(-19.0))):
        put(memory,camera+off,value)
    for i,value in enumerate(case.points):
        put(memory,camera+(0x2BC if i<6 else 0x2F8)+(i if i<6 else i-6)*4,value)
    put(memory,DESC,case.flags,2)
    put(memory,factor,case.factor)
    # The alias fixture's old degree field is the constant itself.
    if case.alias:
        put(memory,camera+0x37C,case.factor)
    for at in (0x80099070,0x80099074):
        put(memory,at,bits(57.2957763671875))
    return memory


class HeadingOracle(TimingOracle):
    def __init__(self, words, case, phase=0, delta=0, factor=source.FACTOR, entry=source.ENTRY,
                 connected=None, mode=2, parent=None):
        self.case,self.delta,self.factor = case,delta,factor
        self.camera = camera_address(case,factor)
        self.vector_packets,self.final_packets,self.asin_inputs = [],[],[]
        self.target_sp = STACK+phase-(24 if entry in (CALLER,PARENT) else 0)
        super().__init__(words,fixture(case,factor,mode),phase=phase,entry=entry,
                         arguments=(self.camera,),connected=connected)
        if parent is not None:
            axis,enabled,state,flag=parent
            self.memory.update({ACTOR+i:0xA5 for i in range(-16,0x33C)})
            put(self.memory,self.camera+0x3D0,ACTOR)
            put(self.memory,self.camera+0x84,0x200000 if enabled else 0)
            put(self.memory,ACTOR,state);put(self.memory,ACTOR+0x102,flag,1)
            for i in range(3):
                put(self.memory,self.camera+0x2B0+i*4,bits(float(i)))
                put(self.memory,ACTOR+0x14+i*4,bits(float(i+1 if axis==i else i)))

    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn in (4,7):
            self.f[fd] = bits(math.sqrt(floating(self.f[rd]))) if fn==4 else self.f[rd]^0x80000000
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.DIFFERENCE+self.delta:
            args=self.arguments(3)
            self.assert_difference(args)
        elif target==source.ANGLE+self.delta:
            args=self.arguments(1)
            self.vector_packets.append(tuple(read(self.memory,args[0]+i*4) for i in range(3)))
            assert read(self.memory,self.target_sp)==self.camera
        elif target==source.FINAL+self.delta:
            args=self.arguments(1)
            self.final_packets.append((args[0],read(self.memory,args[0]+0x37C),read(self.memory,args[0]+0x39C)))
        elif target==0x15048C30:
            args=(self.f[12],);self.asin_inputs.append(self.f[12])
        elif target==0x15124C38:
            args=self.arguments(2)
            assert args==(self.camera,0)
        elif target==0x151247C0:
            args=self.arguments(1)
            assert args==(self.camera,)
        elif target==source.ENTRY or target in (0x15123A54,0x1512E140,0x1512A390,
                0x15122440,0x15129934,0x15121C80,0x15122170,0x15120158,0x1512DEA4):
            args=self.arguments(1)
        else:
            raise AssertionError(('Unbounded heading call',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def assert_difference(self,args):
        assert args==(self.camera+0x2F8,self.camera+0x2BC,self.target_sp-0x28+0x1C)
        assert read(self.memory,self.target_sp)==self.camera

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678

    def hook(self,target):
        value=None
        if target==source.DIFFERENCE+self.delta:
            a,b,out=self.arguments(3)
            for i in range(3):
                self.put(out+i*4,bits(floating(read(self.memory,b+i*4))-floating(read(self.memory,a+i*4))),4)
            if self.case.mutation&1:
                for i,v in enumerate(changed_points(self.case.points)[:6]):
                    self.put(self.camera+0x2BC+i*4,v,4)
        elif target==source.ANGLE+self.delta:
            value=self.case.angle
            if self.case.mutation&2:
                self.put(self.factor,bits(0.25),4)
                self.put(self.camera+0x37C,bits(777.0),4)
        elif target==0x15048C30:
            x=floating(self.f[12])
            assert -1.000001<=x<=1.000001
            value=bits(math.asin(min(1.0,max(-1.0,x))))
        self.clobber()
        self.r[2]=0x87654321
        if value is not None:
            self.f[0]=value


def native_harness(body,cases):
    rows=[]
    for c in cases:
        rows.append('{%s,{%s},{%s},{%s}}'%(
            ','.join('0x%Xu'%v for v in (c.flags,c.angle,c.factor,c.mutation,*result(c))),
            ','.join('0x%Xu'%v for v in c.points),
            ','.join('0x%Xu'%v for v in vector(c)),
            ','.join('0x%Xu'%v for v in (changed_points(c.points) if c.mutation&1 and not c.flags&4 else c.points))))
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned short u16;typedef unsigned char u8;typedef float f32;
typedef struct{f32 unk0,unk4,unk8;}struct17;
typedef struct{u8 pad0[0x2BC];f32 unk2BC,unk2C0,unk2C4;s32 unk2C8,unk2CC,unk2D0;
u8 pad2D4[0x24];f32 unk2F8,unk2FC,unk300;u8 pad304[0x68];u16 *unk36C;
u8 pad370[0xC];f32 unk37C;u8 pad380[0x1C];f32 unk39C;}struct108;
''' + source.DECLARATIONS.replace('#include "structs.h"','') + body + '''
f32 D_800A3460;
typedef struct{u32 flags,angle,factor,mutation,degrees,radians,points[9],vector[3],last[9];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct{u32 before[4];struct108 camera;u32 after[4];}storage;
static u16 descriptor[2];static int calls,error;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void setpoints(const u32 *p){u32 i;for(i=0;i<9;i++){f32 *v=(f32 *)((u8 *)&storage.camera+(i<6?0x2BC+i*4:0x2F8+(i-6)*4));*v=real(p[i]);}}
__attribute__((noinline))void func_15048F90(struct17 *a,struct17 *b,struct17 *out){
    if(calls++!=0 || a!=(struct17 *)&storage.camera.unk2F8 || b!=(struct17 *)&storage.camera.unk2BC)error=1;
    out->unk0=b->unk0-a->unk0;out->unk4=b->unk4-a->unk4;out->unk8=b->unk8-a->unk8;
    if(item->mutation&1)setpoints(item->last);
}
__attribute__((noinline))f32 func_15048FC8(struct17 *v){
    if(calls++!=1 || word(v->unk0)!=item->vector[0] || word(v->unk4)!=item->vector[1] || word(v->unk8)!=item->vector[2])error=1;
    if(item->mutation&2){D_800A3460=0.25f;storage.camera.unk37C=777.0f;}
    return real(item->angle);
}
__attribute__((noinline))void func_15122980(struct108 *p){
    if(calls++!=(item->flags&4?0:2) || p!=&storage.camera || word(p->unk37C)!=item->degrees || word(p->unk39C)!=item->radians)error=1;
}
static int test_all(void){
    u32 n,i;
    if(sizeof(void *)!=4 || __builtin_offsetof(struct108,unk2C8)!=0x2C8 ||
       __builtin_offsetof(struct108,unk2F8)!=0x2F8 || __builtin_offsetof(struct108,unk36C)!=0x36C ||
       __builtin_offsetof(struct108,unk37C)!=0x37C || __builtin_offsetof(struct108,unk39C)!=0x39C)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(storage);i++)((u8 *)&storage)[i]=0xA5;
        descriptor[0]=(u16)item->flags;descriptor[1]=0xA5A5;storage.camera.unk36C=descriptor;
        setpoints(item->points);storage.camera.unk37C=-17.0f;storage.camera.unk39C=-19.0f;D_800A3460=real(item->factor);
        func_151220D0(&storage.camera);
        if(error || calls!=(item->flags&4?1:3))return 23;
        for(i=0;i<4;i++)if(storage.before[i]!=0xA5A5A5A5u || storage.after[i]!=0xA5A5A5A5u)return 24;
        if(descriptor[0]!=item->flags || descriptor[1]!=0xA5A5 || storage.camera.unk36C!=descriptor)return 25;
        for(i=0;i<9;i++)if(word(*(f32 *)((u8 *)&storage.camera+(i<6?0x2BC+i*4:0x2F8+(i-6)*4)))!=item->last[i])return 26;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class CameraHeadingTests(unittest.TestCase):
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
        cls.obj,diag=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:
            raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.alias]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('camera heading qualification:',cls.receipt)

    def test_01_direct_words_bindings_and_existing_layout(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.output)))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),5)
        self.assertEqual(self.words[0],0x27BDFFD8)
        self.assertEqual(self.words[6],0x95CF0000)
        self.assertEqual(self.words[12],0xAFA70028)
        self.assertEqual(self.words[30:34],[0xE4E0037C,0xC4303460,0x46100482,0xE4F2039C])
        self.assertEqual(struct.unpack_from('>I',self.rom,0x247F20)[0],source.CONSTANT)

    def test_02_complete_models_late_reads_gate_clobbers_and_store_alias(self):
        visits=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            a=HeadingOracle(self.truth,case,phase).run();b=HeadingOracle(self.words,case,phase).run()
            self.assertEqual(complete(a),complete(b))
            self.assertEqual(b.vector_packets,[] if case.flags&4 else [vector(case)])
            self.assertEqual(b.final_packets,[(camera_address(case),*result(case))])
            self.assertEqual([x[0]for x in b.calls],
                [source.FINAL] if case.flags&4 else [source.DIFFERENCE,source.ANGLE,source.FINAL])
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg],b.before[reg])
            self.assertEqual(b.f[20:],b.saved_f);visits.update(b.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=visits)
        self.receipt.update(full_model_phases=len(self.cases)*2,all40_target_words_visited=True,
            aliased_factor_store_phases=sum(c.alias for c in self.cases)*2)
        bad=self.words.copy()
        bad[30],bad[31]=bad[31],bad[30]
        witness=Case(alias=True)
        self.assertNotEqual(HeadingOracle(bad,witness).run().final_packets,
                            [(camera_address(witness),*result(witness))])
        self.receipt['effective_store_order_guest_negative']=True

    def native(self,body,label,opt='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+opt)
        args=['gcc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True)
        (self.output/(label+opt+'-compiler.log')).write_text(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,p.stderr[:3000])
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_and_effective_compiled_negatives(self):
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'wrong-mask':source.SELECTED.replace('unk36C[0] & 4','unk36C[0] & 0x400'),
            'inverted-gate':source.SELECTED.replace('if (!(','if (('),
            'integer-field-conversion':source.SELECTED.replace('*(f32 *)&camera->unk2C8','(f32)camera->unk2C8'),
            'wrong-x-subtract':source.SELECTED.replace('unk2C8 - camera->unk2BC','unk2C8 + camera->unk2BC'),
            'wrong-z-field':source.SELECTED.replace('unk2D0 - camera->unk2C4','unk2CC - camera->unk2C4'),
            'wrong-helper-order':source.SELECTED.replace('(struct17 *)&camera->unk2F8,\n            (struct17 *)&camera->unk2BC','(struct17 *)&camera->unk2BC,\n            (struct17 *)&camera->unk2F8'),
            'wrong-radian-factor':source.SELECTED.replace('camera->unk37C * D_800A3460','camera->unk37C * 0.01745329238f'),
            'skipped-final':source.SELECTED.replace('    func_15122980(camera);','    if (!(camera->unk36C[0] & 4)) func_15122980(camera);'),
            'degree-to-wrong-field':source.SELECTED.replace('camera->unk37C =','*(f32 *)&camera->pad380[0] ='),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls),
            native_layout='independent 32-bit subset of existing struct108; emitted IDO offsets separately pinned')

    def test_04_complete_retail_caller_dispatch(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:
                continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(words)if w==opcode)
        self.assertEqual(found,[('func_15126138',0x15126218),('func_151283B8',0x1512846C)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        caller=list(struct.unpack_from('>67I',self.rom,CALLER_ROM))
        count=0
        modes=(-1,0,1,2,8,0x40,0x80,0x100,0x400,0x800,0x2000,0x800000,0x7FFFFFFF)
        for mode,flags,phase in itertools.product(modes,(0,4),(0,8)):
            case=Case(flags=flags)
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                m=HeadingOracle(caller,case,phase,entry=CALLER,connected=connected,mode=mode&0xFFFFFFFF).run()
                self.assertEqual(m.vector_packets,[vector(case)] if mode==2 and not flags&4 else [])
                if mode==2:
                    self.assertEqual(m.final_packets,[(CAMERA,*result(case))])
                self.assertEqual(m.r[29],STACK+phase);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(all_direct_sites=found,complete_caller_phases=count,
            caller_words=67,other_dispatch_targets_bounded=True)
        parent=list(struct.unpack_from('>65I',self.rom,PARENT_ROM))
        gates=((2,1,0,0,1),(2,0,0,0,1),(2,1,30,0,1),(2,1,0,1,1),
               (2,1,0,0,0),(0x40,1,0,0,1),(2,1,0,0,4),(2,1,0,0,8),
               (2,1,0,0,0x8000),(0,1,0,0,1),(0x100,1,0,0,1))
        count=active=0;visits=set()
        for axis,(mode,enabled,state,flag,flags),phase in itertools.product((-1,0,1,2),gates,(0,8)):
            case=Case(flags=flags);models=[]
            reached=bool(enabled and state!=30 and not flag and flags&15 and not mode&0x40)
            moving=axis>=0 and bool(mode&~0x100)
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                m=HeadingOracle(parent,case,phase,entry=PARENT,connected=connected,mode=mode,
                                parent=(axis,enabled,state,flag)).run()
                self.assertEqual(m.vector_packets,[vector(case)] if reached and not flags&4 else [])
                self.assertEqual(m.final_packets,[(CAMERA,*result(case))] if reached else [])
                self.assertEqual(m.calls[0][0],0x151247C0)
                self.assertEqual(m.calls[-1],(0x15124C38,(CAMERA,0)))
                self.assertEqual(read(m.memory,CAMERA+0x298,2),int(moving))
                self.assertEqual(read(m.memory,CAMERA+0x7E6,2),60 if moving else 0xA5A5)
                self.assertEqual(read(m.memory,CAMERA+0x8ED,1),0 if moving else 0xA5)
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1;active+=reached
        self.assertTrue(set(range(PARENT,PARENT+260,4))<=visits)
        self.receipt.update(complete_camera_parent_phases=count,active_camera_parent_phases=active,
            all65_camera_parent_words=True,preparation_and_finalizer_bounded=True)

    def test_05_independent_GNU_call_and_HILO_rebases(self):
        count=0
        for delta,factor in ((0x10000,0x800A7FFC),(0xCF20,0x800A8000),(0x18000,0x800AFFF0)):
            images=[]
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf=self.output/('rebase-%d-%d.elf'%(delta,i));script=self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                definitions=['--defsym=%s=0x%X'%(name,address+delta)for name,address in (
                    ('func_15048F90',source.DIFFERENCE),('func_15048FC8',source.ANGLE),('func_15122980',source.FINAL))]
                definitions+=['--defsym=D_800A3460=0x%X'%factor]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *definitions,'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::41]:
                m=HeadingOracle(images[0],case,delta=delta,factor=factor).run()
                self.assertEqual(m.final_packets,[(camera_address(case,factor),*result(case))]);count+=1
        self.receipt.update(rebase_sets=3,independent_rebase_phases=count,signed_LO16_carries=True)

    def test_06_actual_difference_and_angle_helpers(self):
        difference=list(struct.unpack_from('>14I',self.rom,0x76440))
        angle=list(struct.unpack_from('>56I',self.rom,0x76478))
        connected=dict(zip(range(source.DIFFERENCE,source.ANGLE+224,4),difference+angle))
        visits=set();count=0
        for x,z,phase in itertools.product((-5.0,0.0,5.0),(-7.0,0.0,7.0),(0,8)):
            case=Case(points=tuple(map(bits,(0.0,4.0,0.0,x,2.0,z,0.0,1.0,0.0))))
            models=[]
            for code in (self.truth,self.words):
                m=HeadingOracle(code,case,phase,connected=connected).run()
                self.assertEqual(m.vector_packets,[vector(case)])
                degrees=m.final_packets[0][1]
                self.assertEqual(m.final_packets[0][2],bits(floating(degrees)*floating(source.CONSTANT)))
                if not x and not z:
                    self.assertEqual(degrees,0);self.assertEqual(m.asin_inputs,[])
                else:
                    expected=math.degrees(math.atan2(-x,-z))%360.0
                    self.assertAlmostEqual(floating(degrees),expected,places=4)
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(actual_vector_angle_phases=count,all14_difference_words=True,all56_angle_words=True,
            asin_provider='bounded host asin after guest ratio; not original polynomial or FCSR hardware')

    def test_07_actual_final_helper_gated_continuation(self):
        helper=list(struct.unpack_from('>87I',self.rom,0x14FE30))
        connected=dict(zip(range(source.FINAL,source.FINAL+348,4),helper))
        count=0;visits=set()
        for flags,phase in itertools.product((0,4,0x8000,0xFFFF),(0,8)):
            case=Case(flags=flags);models=[]
            for code in (self.truth,self.words):
                m=HeadingOracle(code,case,phase,connected=connected).run()
                self.assertEqual(m.final_packets,[(CAMERA,*result(case))])
                self.assertEqual([c[0]for c in m.calls[-4:]],[source.FINAL,0x15123A54,0x1512E140,0x1512A390])
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        covered=len(visits&set(connected));self.assertEqual(covered,20)
        self.receipt.update(original_final_DC4_phases=count,original_final_gate_words=covered,
            nonDC4_final_and_lower_updates_executed=False)

    def test_08_strict_image_negatives(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+160]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION),
            next(at+4 for at,name,_,_ in source.symbol_rows(predicted)if name=='D_800A3460'),
            next(string for _,name,_,string in source.symbol_rows(predicted)if name=='D_80091710'))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_negatives']=9
