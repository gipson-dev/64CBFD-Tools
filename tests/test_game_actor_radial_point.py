"""Actor gates, late matrix selection, exact locals, native32 and original caller."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_actor_radial_point as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
ACTOR, ALTERNATE, MODEL, OTHER = 0x28000, 0x2C000, 0x30000, 0x31000
CURRENT, LOOKUP, TABLE = 0x800D154C, 0x151423D8, 0x8009A220


@dataclass(frozen=True)
class Case:
    tag: int = 1
    matrix: bool = True
    rng: int = 0x876543FF
    kind: int = 0x123400FF
    flags: int = 0x87654321
    mutation: int = 0
    home: bool = False

    @property
    def active(self):
        return self.matrix and self.tag & 15 != 15


def corpus():
    for tag, matrix in itertools.product(range(256), (False, True)):
        yield Case(tag, matrix, (tag*1664525+1013904223)&0xFFFFFFFF,
                   0xABCD0000|tag, (tag*0x01010101)&0xFFFFFFFF, tag%4)
    for angle in range(256):
        yield Case(rng=0x87654300|angle, kind=angle, mutation=angle%4)
    for rng, kind, flags, mutation in itertools.product(
            (0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,128,255),(0,0x80000000,0xFFFFFFFF),(0,3)):
        yield Case(rng=rng,kind=kind,flags=flags,mutation=mutation)
    yield Case(home=True)
    yield Case(home=True,mutation=3)


def offset(case, table=None):
    angle = case.rng & 255
    if table is None:
        return (bits(angle*0.25),0,bits(-float(angle)*0.5))
    def lookup(value):
        value &= 255
        index = 64-(value&63) if value&64 else value&63
        word = struct.unpack_from('>I',table,index*4)[0]
        return word if value&192 in (0,192) else word^0x80000000
    return (bits(floating(lookup(angle-64))*100.0),0,bits(floating(lookup(angle))*100.0))


def selected_matrix(case):
    return OTHER if case.home or case.mutation else MODEL


def output(case, table=None):
    vector = offset(case,table)
    translation = 20.0 if selected_matrix(case)==OTHER else 10.0
    return tuple(bits(floating(word)+translation+i) for i,word in enumerate(vector))


def submitted(case, table=None):
    if not case.active:
        return []
    return [(output(case,table),0x5A if case.home else case.kind&255,
             0x76543210 if case.home else case.flags)]


def fixture(case, table=b''):
    memory = {STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x160)}
    for base in (ACTOR,ALTERNATE):
        memory.update({base+i:0xA5 for i in range(-16,0x33C)})
    for base in (MODEL,OTHER):
        memory.update({base+i:0xA5 for i in range(0x500)})
    put(memory,ACTOR+0x1D4,MODEL if case.matrix else 0)
    put(memory,ACTOR+0x74,case.tag,1)
    put(memory,ALTERNATE+0x1D4,OTHER)
    put(memory,ALTERNATE+0x74,1,1)
    put(memory,CURRENT,ACTOR)
    memory.update({TABLE+i:b for i,b in enumerate(table)})
    return memory


class RadialOracle(TimingOracle):
    def __init__(self, words, case, phase=0, delta=0, entry=source.ENTRY,
                 connected=None, table=None):
        self.case,self.delta,self.table = case,delta,table
        self.target_sp = STACK+phase
        self.submissions = []
        arguments = (0x12345678,) if entry==source.CALLER_ENTRY else (ACTOR,case.kind,case.flags)
        super().__init__(words,fixture(case,table or b''),phase=phase,entry=entry,
                         arguments=arguments,connected=connected)

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            self.f[word>>6&31] = self.f[word>>11&31]^0x80000000
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            assert self.arguments(3)==(ACTOR,255,1)
            self.target_sp=self.r[29]
            args=self.arguments(3)
        elif target==source.INTEGER_RNG+self.delta:
            args=()
        elif target==source.DIRECTION+self.delta:
            args=self.arguments(4)
            assert args==(self.case.rng&255,bits(100.0),self.target_sp-12,self.target_sp-4),args
            assert tuple(self.get(args[2]+i*4,4) for i in range(3))==(0,0,0)
        elif target==source.TRANSFORM+self.delta:
            args=self.arguments(3)
            assert args==(self.target_sp-12,self.target_sp-24,selected_matrix(self.case)+0x4C0),args
            assert tuple(self.get(args[0]+i*4,4) for i in range(3))==offset(self.case,self.table)
        elif target==source.SUBMIT+self.delta:
            args=self.arguments(3)
            assert args[0]==self.target_sp-24
            point=tuple(self.get(args[0]+i*4,4) for i in range(3))
            self.submissions.append((point,*args[1:]))
        elif target==LOOKUP:
            args=self.arguments(1)
        else:
            raise AssertionError(('Unknown radial provider',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678

    def hook(self,target):
        if target==source.INTEGER_RNG+self.delta:
            if self.case.mutation&1:
                self.put(ACTOR+0x1D4,OTHER,4);self.put(ACTOR+0x74,15,1)
            if self.case.home:
                self.put(self.target_sp,ALTERNATE,4)
                self.put(self.target_sp+4,0x1234005A,4)
                self.put(self.target_sp+8,0x76543210,4)
        elif target==source.DIRECTION+self.delta:
            args=self.arguments(4)
            vector=offset(self.case)
            self.put(args[2],vector[0],4);self.put(args[3],vector[2],4)
            if self.case.mutation&2:
                self.put(ACTOR+0x1D4,OTHER,4);self.put(ACTOR+0x74,15,1)
        elif target==source.TRANSFORM+self.delta:
            destination=self.r[5]
            for i,word in enumerate(output(self.case,self.table)):
                self.put(destination+i*4,word,4)
        elif target!=source.SUBMIT+self.delta:
            raise AssertionError(('Unbounded radial helper',target))
        self.clobber()
        self.r[2]=self.case.rng if target==source.INTEGER_RNG+self.delta else 0x76543210


def native_harness(body,cases):
    rows=['{'+','.join('0x%Xu'%v for v in
          (c.tag,int(c.matrix),c.rng,c.kind,c.flags,c.mutation,int(c.active)))+
          ',{'+','.join('0x%Xu'%v for v in offset(c))+'},{'+
          ','.join('0x%Xu'%v for v in output(c))+'}}' for c in cases]
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef float f32;
typedef struct{u8 prefix[0x244];}struct255;
typedef struct{u8 p0[0x74];u8 unk74;u8 p75[0x15F];struct255 *unk1D4;u8 tail[0x154];}struct127;
typedef struct{f32 unk0,unk4,unk8;}struct17;
''' + source.DECLARATIONS.replace('#include "structs.h"','') + body + '''
typedef struct{u32 tag,matrix,rng,kind,flags,mode,active,offset[3],point[3];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct127 actor;static union{u32 align;u8 bytes[0x500];}models[2];
static int calls,error;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void mutate(void){actor.unk1D4=(struct255 *)models[1].bytes;actor.unk74=15;}
__attribute__((noinline))s32 func_150ADA20(void){
    union{u32 u;s32 s;}v;
    if(calls++!=0 || !item->active)error=1;
    if(item->mode&1)mutate();
    v.u=item->rng;return v.s;
}
__attribute__((noinline))void func_15143874(s16 angle,f32 radius,f32 *x,f32 *z){
    if(calls++!=1 || angle!=(s16)(item->rng&255) || word(radius)!=0x42C80000u ||
       z!=x+2 || word(x[0])!=0 || word(x[1])!=0 || word(x[2])!=0)error=1;
    *x=real(item->offset[0]);*z=real(item->offset[2]);
    if(item->mode&2)mutate();
}
__attribute__((noinline))void func_15143134(f32 *input,f32 *out,u8 *matrix){
    u32 i,wanted=(u32)models[item->mode?1:0].bytes+0x4C0;
    if(calls++!=2 || (u32)matrix!=wanted || input==out)error=1;
    for(i=0;i<3;i++){if(word(input[i])!=item->offset[i])error=1;out[i]=real(item->point[i]);}
}
__attribute__((noinline))void func_151C329C(struct17 *point,s32 kind,s32 flags){
    if(calls++!=3 || (u32)kind!=(item->kind&255) || (u32)flags!=item->flags ||
       word(point->unk0)!=item->point[0] || word(point->unk4)!=item->point[1] ||
       word(point->unk8)!=item->point[2])error=1;
}
static int test_all(void){
    u32 n,i,expected;
    if(sizeof(struct127)!=0x32C || __builtin_offsetof(struct127,unk74)!=0x74 ||
       __builtin_offsetof(struct127,unk1D4)!=0x1D4 || sizeof(struct17)!=12)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(actor);i++)((u8 *)&actor)[i]=0xA5;
        actor.unk74=(u8)item->tag;actor.unk1D4=item->matrix?(struct255 *)models[0].bytes:0;
        func_150F2230(&actor,(u8)item->kind,(s32)item->flags);
        expected=item->active?4:0;
        if(error || (u32)calls!=expected)return 23;
        for(i=0;i<sizeof(actor);i++){
            if(i==0x74 || (i>=0x1D4 && i<0x1D8))continue;
            if(((u8 *)&actor)[i]!=0xA5)return 24;
        }
        if(actor.unk74!=(item->active && item->mode?15:(u8)item->tag) ||
           (u32)actor.unk1D4!=(item->active && item->mode?(u32)models[1].bytes:
                             item->matrix?(u32)models[0].bytes:0))return 25;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ActorRadialPointTests(unittest.TestCase):
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
        cls.words=list(struct.unpack_from('>39I',data,funcs[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>39I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.home]
        at=source.elf_slot_offset(cls.values['conker/build/conker.us.elf'],TABLE,260)
        cls.table=cls.values['conker/build/conker.us.elf'][at:at+260]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),
                         guards=0,matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('actor radial point qualification:',cls.receipt)

    def test_01_direct_body_alignment_bindings_and_canonical_layout(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.output)))
        self.assertEqual(len(sections(self.obj)['.text'][1]),160)
        self.assertEqual(sections(self.obj)['.text'][1][-4:],bytes(4))
        self.assertEqual(self.rom[source.ROM+156:source.ROM+160],bytes(4))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),4)
        check=source.DECLARATIONS+'''
typedef char actor_size[sizeof(struct127)==0x32C?1:-1];
typedef char actor_tag[(u32)&((struct127 *)0)->unk74==0x74?1:-1];
typedef char actor_matrix[(u32)&((struct127 *)0)->unk1D4==0x1D4?1:-1];
typedef char point_size[sizeof(struct17)==12?1:-1];
'''+source.SELECTED
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+check,'canonical-layout')
        self.assertEqual(diagnostic,'');self.assertEqual(source.payload(obj),source.payload(self.obj))
        self.assertIn(source.CALLER_DECLARATION,(self.output/'proposed-caller.c').read_text())
        report=json.loads((self.output/'caller-qualification.json').read_text())
        self.assertEqual(report['functions_fixed'],328)

    def test_02_complete_state_gates_reference_calls_read_order_and_all_words(self):
        visits=set();active=0
        for case,phase in itertools.product(self.cases,(0,8)):
            a=RadialOracle(self.truth,case,phase).run();b=RadialOracle(self.words,case,phase).run()
            self.assertEqual(complete(a),complete(b));self.assertEqual(b.submissions,submitted(case))
            addresses={base+off for base in (ACTOR,ALTERNATE) for off in (0x74,0x1D4)}
            reads=[e for e in b.events if e[0]=='R' and e[1] in addresses]
            wanted=[('R',ACTOR+0x1D4,4,MODEL if case.matrix else 0)]
            if case.matrix:
                wanted.append(('R',ACTOR+0x74,1,case.tag))
            if case.active:
                owner=ALTERNATE if case.home else ACTOR
                wanted.append(('R',owner+0x1D4,4,selected_matrix(case)))
                self.assertEqual([c[0]for c in b.calls],[source.INTEGER_RNG,source.DIRECTION,source.TRANSFORM,source.SUBMIT])
                active+=1
            else:
                self.assertEqual(b.calls,[])
            self.assertEqual(reads,wanted)
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg],b.before[reg])
            self.assertEqual(b.f[20:],b.saved_f);visits.update(b.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=visits)
        self.receipt.update(full_model_phases=len(self.cases)*2,active_phases=active,all39_body_words_visited=True,
            all256_gate_bytes=True,late_matrix_reload=True,home_redirect_cases_guest_only=2)

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

    def test_03_native32_optimizations_and_effective_semantic_controls(self):
        for optimization in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',optimization),0)
        controls={
            'missing-null-gate':source.SELECTED.replace('actor->unk1D4 != 0 && ',''),
            'wrong-nibble':source.SELECTED.replace('unk74 & 0xF','unk74 & 0x1F'),
            'wrong-zero-y':source.SELECTED.replace('offset.unk4 = 0.0f','offset.unk4 = 1.0f'),
            'wide-angle':source.SELECTED.replace('(u8)func_150ADA20()','(s16)func_150ADA20()'),
            'wrong-radius':source.SELECTED.replace('100.0f','101.0f'),
            'swapped-outputs':source.SELECTED.replace('&offset.unk0, &offset.unk8','&offset.unk8, &offset.unk0'),
            'wrong-matrix':source.SELECTED.replace('0x4C0','0x480'),
            'signed-kind':source.SELECTED.replace('&point, kind, flags','&point, (s8)kind, flags'),
            'narrow-flags':source.SELECTED.replace('&point, kind, flags','&point, kind, (u8)flags'),
            'early-matrix':source.SELECTED.replace('    struct17 offset;','    u8 *matrix = (u8 *)actor->unk1D4;\n    struct17 offset;').replace('(u32)actor->unk1D4 +','(u32)matrix +'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls),
            prepared_flat_32bit_ABI_not_arbitrary_host_pointer_claim=True)

    def test_04_caller_inventory_and_complete_original_wrapper(self):
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
        self.assertEqual(found,[('func_15071D08',0x15071D20)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        caller=list(struct.unpack_from('>12I',self.rom,source.CALLER_ROM))
        self.assertEqual(caller[3:8],[0x3C04800D,0x8C84154C,0x240500FF,opcode,0x24060001])
        at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.CALLER_ENTRY,48)
        self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+48],self.rom[source.CALLER_ROM:source.CALLER_ROM+48])
        visits=set();count=0
        for tag,matrix,mutation,phase in itertools.product((0,15,16,255),(False,True),range(4),(0,8)):
            case=Case(tag,matrix,kind=255,flags=1,mutation=mutation)
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+156,4),code))
                model=RadialOracle(caller,case,phase,entry=source.CALLER_ENTRY,connected=connected).run()
                self.assertEqual(model.submissions,submitted(case));models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(source.CALLER_ENTRY,source.CALLER_ENTRY+48,4))<=visits)
        self.receipt.update(all_direct_retail_call_sites=found,full_original_caller_phases=count,
                            all12_caller_words_visited=True,caller_owner_functions_preserved=328)

    def test_05_independent_GNU_four_call_rebases(self):
        count=0
        for delta in (0x10000,0xCF20,0x18000):
            images=[]
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf,script=self.output/('rebase-%d-%d.elf'%(delta,i)),self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                definitions=['--defsym=%s=0x%X'%(name,address+delta)for name,address in (
                    ('func_150ADA20',source.INTEGER_RNG),('func_15143874',source.DIRECTION),
                    ('func_15143134',source.TRANSFORM),('func_151C329C',source.SUBMIT))]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *definitions,'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>39I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::43]:
                model=RadialOracle(images[0],case,delta=delta).run()
                self.assertEqual(model.submissions,submitted(case));count+=1
        self.receipt.update(independent_rebase_phases=count,rebase_sets=3)

    def test_06_strict_image_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+156]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,156),
            source.elf_slot_offset(predicted,source.CALLER_ENTRY,48),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_negative_controls']=7

    def test_07_full_downstream_original_interfaces_are_static_not_execution_claims(self):
        direction=struct.unpack_from('>25I',self.rom,0x170D24)
        transform=struct.unpack_from('>98I',self.rom,0x1705E4)
        submit=struct.unpack_from('>271I',self.rom,0x1F074C)
        self.assertEqual(direction[:6],(0x27BDFFE0,0xAFBF0014,0xAFA40020,0xAFA50024,0xAFA60028,0xAFA7002C))
        self.assertIn(0xE5E40000,direction);self.assertIn(0xE7080000,direction)
        self.assertIn(0x00808025,transform);self.assertIn(0x00A08825,transform);self.assertIn(0x00C09025,transform)
        self.assertEqual(submit[:6],(0x27BDFEC0,0xAFB00038,0x00808025,0xAFBF003C,0xAFA50144,0xAFA60148))
        self.assertIn(0x93A50147,submit);self.assertIn(0x8FA60148,submit)
        self.receipt.update(transform_and_submission_interfaces_inspected=True,
                            full_transform_submission_execution_claimed=False)

    def test_08_complete_original_direction_and_lookup_with_frozen_table(self):
        connected={}
        for address,rom,words in ((source.DIRECTION,0x170D24,25),(LOOKUP,0x16F888,27)):
            connected.update(zip(range(address,address+words*4,4),struct.unpack_from('>%dI'%words,self.rom,rom)))
        visits=set();count=0
        for angle,phase in itertools.product(range(256),(0,8)):
            case=Case(rng=0x87654300|angle,kind=angle)
            models=[]
            for code in (self.truth,self.words):
                model=RadialOracle(code,case,phase,connected=connected,table=self.table).run()
                self.assertEqual(model.submissions,submitted(case,self.table))
                lookups=[args[0]for target,args in model.calls if target==LOOKUP]
                self.assertEqual(lookups,[angle,(angle-64)&255])
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(original_direction_lookup_phases=count,actual_helper_words_visited=len(connected),
                            frozen_table_entries=65,float_FCSR_hardware_claimed=False)
