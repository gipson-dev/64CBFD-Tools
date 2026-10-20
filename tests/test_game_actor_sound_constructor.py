"""Word-to-short coordinates, returned handle, original registration and caller."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_actor_sound_constructor as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
ACTOR, TABLE, COUNT = 0x28000, 0x80041FE0, 0x80042760
RATIO, FINALIZE = 0x10019AB0, 0x10011624
COORDINATES = (0.0, -0.0, 1.75, -2.75, 32767.75, 32768.25, -32768.75,
               65535.75, -65536.25, 2147483520.0, -2147483648.0, 16777216.0)
SIGNATURES = {0x151D0F60:4,0x151BC074:1,0x151BD2F8:3,0x151B9F00:3,0x15160A58:16,0x1514EC1C:3}


@dataclass(frozen=True)
class Case:
    point: tuple = (bits(1.75),bits(-2.75),bits(32768.25))
    handle: int = 0x8001
    mutation: bool = False
    home: bool = False
    count: int = 0
    failure: bool = False
    gate: int = 0
    allocated: bool = False


def corpus():
    for i in range(256):
        yield Case(tuple(bits(v) for v in (32768.0+i/4,-32768.0-i/4,i-127.75)),
                   (i*257)&65535,bool(i&1))
    for i,handle,mutation in itertools.product(range(len(COORDINATES)),(0,1,0x7FFF,0x8000,0xFFFF),(False,True)):
        yield Case(tuple(bits(COORDINATES[(i+j)%len(COORDINATES)]) for j in range(3)),handle,mutation)
    for home in (False,True):
        yield Case(home=home,mutation=True)


def short(word):
    value = math.trunc(floating(word))
    assert math.isfinite(floating(word)) and -2147483648 <= value < 2147483648
    value &= 65535
    return value if value < 32768 else value-65536


def packet(case, delta=0):
    return (0x4A7,*(short(w)&0xFFFFFFFF for w in case.point),
            8192,800,200,source.CALLBACK+delta,ACTOR+delta,0,8,0)


def fixture(case, delta=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x500,0x100)}
    memory.update({ACTOR+delta+i:0xA5 for i in range(0x32C)})
    memory.update({TABLE+i:(i*13+0x35)&255 for i in range(32*0x30)})
    put(memory,COUNT,case.count)
    put(memory,0x800BE616,case.gate,1)
    for i,word in enumerate(case.point):
        put(memory,ACTOR+delta+0x14+i*4,word)
    return memory


class SoundOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None):
        self.case,self.delta,self.packets=case,delta,[]
        self.target_sp=STACK+phase
        self.allocations=0
        super().__init__(words,fixture(case,delta),phase=phase,entry=entry,
                         arguments=(ACTOR+delta,),connected=connected)

    def execute(self,word):
        op,rs,rd,fd,fn=word>>26,word>>21&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn==13:
            value=floating(self.f[rd])
            assert math.isfinite(value) and -2147483648 <= math.trunc(value) < 2147483648
            self.f[fd]=math.trunc(value)&0xFFFFFFFF
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            self.target_sp=self.r[29]
            self.calls.append(('ENTER',self.arguments(1)))
            return
        if target==source.REGISTER+self.delta:
            args=self.arguments(12);self.packets.append(args)
        elif target==RATIO:
            args=self.arguments(1);assert args==(0,)
        elif target==FINALIZE:
            args=self.arguments(4)
        else:
            args=self.arguments(SIGNATURES[target])
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678

    def hook(self,target):
        args=self.calls[-1][1]
        if target==source.REGISTER+self.delta:
            if self.case.mutation:
                for i in range(3):
                    self.put(ACTOR+self.delta+0x14+i*4,bits(100+i),4)
            if self.case.home:
                self.put(self.target_sp,0x12345678,4)
            self.clobber();self.r[2]=self.case.handle
        elif target==RATIO:
            self.clobber();self.f[0]=bits(1.0)
        elif target==FINALIZE:
            assert args==(TABLE,COUNT,self.case.count,self.case.count+1)
            self.put(TABLE+self.case.count*0x30+0x24,self.case.handle,2)
            if self.case.failure:
                self.put(COUNT,self.case.count+2,4)
            self.clobber();self.r[2]=0
        else:
            self.clobber();self.r[2]=0
            if target==0x15160A58:
                self.allocations+=1
                if self.case.allocated:
                    self.r[2]=0x30000


def native_harness(body,cases):
    rows=['{'+','.join('0x%Xu'%v for v in (*c.point,c.handle,int(c.mutation)))+'}' for c in cases]
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned short u16;typedef short s16;typedef unsigned char u8;typedef float f32;
typedef struct{u8 p0[20];f32 x_position,y_position,z_position;u8 tail[0x30C];}struct127;
''' + source.DECLARATIONS.replace('#include "structs.h"','') + body + '''
typedef struct{u32 x,y,z,handle,mutation;}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct127 actor;static int calls,error;
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static s16 coord(u32 u){s32 word=(s32)real(u);u32 low=(u32)word&65535;return (s16)(low<32768?(s32)low:(s32)low-65536);}
s32 func_151BB0E0(void){return 0;}
u16 func_1000FA64(u16 sound,s16 x,s16 y,s16 z,s32 amount,u16 rate,s16 limit,s32 callback,void *context,s32 a,s32 flags,s32 b){
    if(calls++ || sound!=0x4A7 || x!=coord(item->x) || y!=coord(item->y) || z!=coord(item->z) ||
       amount!=8192 || rate!=800 || limit!=200 || callback!=(s32)func_151BB0E0 ||
       context!=&actor || a!=0 || flags!=8 || b!=0)error=1;
    if(item->mutation){actor.x_position=100.0f;actor.y_position=101.0f;actor.z_position=102.0f;}
    return (u16)item->handle;
}
static int test_all(void){
    u32 n,i;
    if(sizeof(struct127)!=0x32C || __builtin_offsetof(struct127,x_position)!=0x14)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        u16 result;item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(actor);i++)((u8 *)&actor)[i]=0xA5;
        actor.x_position=real(item->x);actor.y_position=real(item->y);actor.z_position=real(item->z);
        result=func_151BB044(&actor);
        if(error || calls!=1 || result!=item->handle)return 23;
        for(i=0;i<sizeof(actor);i++){
            if(i>=0x14 && i<0x20)continue;
            if(((u8 *)&actor)[i]!=0xA5)return 24;
        }
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ActorSoundConstructorTests(unittest.TestCase):
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
        cls.obj,diagnostic=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diagnostic:raise ValueError(diagnostic)
        data,funcs=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>39I',data,funcs[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>39I',cls.rom,source.ROM))
        cls.registration=list(struct.unpack_from('>109I',cls.rom,0xFA64))
        cls.cases=list(corpus())
        cls.native_cases=[c for c in cls.cases if not c.home]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=0,
                         matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('actor sound constructor qualification:',cls.receipt)

    def test_01_exact_independent_original_callback_binding_and_canonical_fields(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.output)))
        self.assertEqual(sum(map(len,source.payload(self.obj)[1].values())),3)
        check=source.DECLARATIONS+'''
typedef char actor_size[sizeof(struct127)==0x32C?1:-1];
typedef char x_offset[(u32)&((struct127 *)0)->x_position==0x14?1:-1];
typedef char y_offset[(u32)&((struct127 *)0)->y_position==0x18?1:-1];
typedef char z_offset[(u32)&((struct127 *)0)->z_position==0x1C?1:-1];
'''+source.SELECTED
        obj,diagnostic=source.compile_owner(ROOT,self.output,'#include <ultra64.h>\n'+check,'canonical-layout')
        self.assertEqual(diagnostic,'');self.assertEqual(source.payload(obj),source.payload(self.obj))
        elf=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(elf,source.REGISTER,436)
        self.assertEqual(elf[at:at+436],self.rom[0xFA64:0xFC18])
        self.assertEqual(self.registration[-10:-7],[0x96020024,0x354B1000,0x10000002])
        self.assertIn('u16 func_151BB044',source.SELECTED)

    def test_02_complete_models_signed_narrowing_return_lifetime_and_all_words(self):
        visits=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            a=SoundOracle(self.truth,case,phase).run();b=SoundOracle(self.words,case,phase).run()
            self.assertEqual(complete(a),complete(b))
            self.assertEqual(b.packets,[packet(case)]);self.assertEqual(b.r[2],case.handle)
            initial=fixture(case)
            reads=[e for e in b.events if e[0]=='R' and ACTOR<=e[1]<ACTOR+0x32C]
            self.assertEqual(reads,[('R',ACTOR+0x14+i*4,4,w)for i,w in enumerate(case.point)])
            for i in range(0x32C):
                expected=(bits(100+(i-0x14)//4)>>((3-(i-0x14)%4)*8))&255 if case.mutation and 0x14<=i<0x20 else initial[ACTOR+i]
                self.assertEqual(b.memory[ACTOR+i],expected)
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg],b.before[reg])
            visits.update(b.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=visits)
        self.receipt.update(full_model_phases=len(self.cases)*2,all39_words_visited=True,
                            finite_signed_word_conversion_domain=True,explicit_word_before_short=True,
                            return_range=[0,65535],finished_home_probes_guest_only=True)

    def native(self,body,label,optimization='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+optimization)
        args=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
              '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
              '-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
              str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_three_optimizations_and_semantic_negatives(self):
        for optimization in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',optimization),0)
        negatives={
            'wrong-sound':source.SELECTED.replace('0x4A7','0x4A8'),
            'wrong-x':source.SELECTED.replace('(s16)(s32)actor->x_position','(s16)(s32)actor->y_position'),
            'wrong-y':source.SELECTED.replace('(s16)(s32)actor->y_position','(s16)(s32)actor->z_position'),
            'wrong-z':source.SELECTED.replace('(s16)(s32)actor->z_position','(s16)(s32)actor->x_position'),
            'wrong-amount':source.SELECTED.replace('0x2000, 800','0x2001, 800'),
            'wrong-rate':source.SELECTED.replace('0x2000, 800','0x2000, 801'),
            'wrong-callback':source.SELECTED.replace('(s32)func_151BB0E0','0'),
            'wrong-context':source.SELECTED.replace('func_151BB0E0, actor','func_151BB0E0, 0'),
            'wrong-flags':source.SELECTED.replace('actor, 0, 8, 0','actor, 0, 0, 0'),
            'discard-result':source.SELECTED.replace('return func_1000FA64','func_1000FA64').replace('\n}','\n    return 0;\n}'),
        }
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED);self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(negatives))

    def test_04_original_registration_body_capacity_record_fields_and_return(self):
        connected=dict(zip(range(source.REGISTER,source.REGISTER+436,4),self.registration))
        visits=set();calls=0;phases=0
        for count,handle,failure,phase in itertools.product((0,1,31,32,33),(0,0x7FFF,0x8000,0xFFFF),(False,True),(0,8)):
            case=Case(count=count,handle=handle,failure=failure)
            a=SoundOracle(self.truth,case,phase,connected=connected).run()
            b=SoundOracle(self.words,case,phase,connected=connected).run()
            self.assertEqual(complete(a),complete(b));self.assertEqual(b.packets,[packet(case)])
            expected=fixture(case)
            if count<32:
                p=TABLE+count*0x30
                put(expected,COUNT,count+2 if failure else count+1)
                for off,value,size in ((0,0x4A7,2),(2,short(case.point[0]),2),(4,short(case.point[1]),2),(6,short(case.point[2]),2),
                    (8,800,2),(10,200,2),(12,8192,4),(16,0x1A if failure else 0x101A,4),
                    (20,source.CALLBACK,4),(24,ACTOR,4),(28,0,4),(32,0,2),(34,0,1),(35,0,1),
                    (36,handle,2),(38,0,2),(40,0,2),(44,bits(1.0),4)):
                    put(expected,p+off,value&((1<<(size*8))-1),size)
                self.assertEqual(b.r[2],0 if failure else handle)
                self.assertIn(FINALIZE,[c[0]for c in b.calls]);calls+=1
            else:
                self.assertEqual(b.r[2],0)
                self.assertNotIn(FINALIZE,[c[0]for c in b.calls])
            for start,size in ((TABLE,32*0x30),(COUNT,4)):
                self.assertEqual(bytes(b.memory[start+i]for i in range(size)),bytes(expected[start+i]for i in range(size)))
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(b.r[reg],b.before[reg])
            visits.update(b.visits);phases+=1
        self.receipt.update(original_registration_phases=phases,fired_finalizer_calls=calls,
                            original_registration_words_visited=len(visits&set(range(source.REGISTER,source.REGISTER+436,4))),
                            ratio_and_table_finalizer_bounded=True,callback_execution_claimed=False)

    def test_05_direct_caller_inventory_and_complete_original_caller(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(words)if w==opcode)
        self.assertEqual(found,[('func_1514F194',0x1514F1CC)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        caller=list(struct.unpack_from('>93I',self.rom,source.CALLER_ROM))
        self.assertEqual(caller[16:19],[0x3C0E800C,0x91CEE616,0x55C00004])
        visits=set();phases=0
        for gate,allocated,phase in itertools.product((0,1),(False,True),(0,8)):
            case=Case(gate=gate,allocated=allocated)
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+156,4),code))
                models.append(SoundOracle(caller,case,phase,entry=source.CALLER_ENTRY,connected=connected).run())
            self.assertEqual(complete(models[0]),complete(models[1]))
            self.assertEqual(models[1].packets,[packet(case)])
            for reg in (*range(16,24),28,29,30,31):
                self.assertEqual(models[1].r[reg],models[1].before[reg])
            visits.update(models[1].visits);phases+=1
        self.assertTrue(set(range(source.CALLER_ENTRY,source.CALLER_ENTRY+372,4))<=visits)
        self.receipt.update(all_direct_retail_call_sites=found,full_original_caller_phases=phases,
                            original_caller_words_visited=93,other_caller_providers_bounded=True)

    def test_06_independent_callback_HI_LO_and_call_rebases(self):
        count=0
        for delta in (0x10000,0xCF20,0x18000):
            images=[]
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf,script=self.output/('rebase-%d-%d.elf'%(delta,i)),self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=func_151BB0E0=0x%X'%(source.CALLBACK+delta),
                    '--defsym=func_1000FA64=0x%X'%(source.REGISTER+delta),
                    '-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>39I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::29]:
                model=SoundOracle(images[0],case,delta=delta).run()
                self.assertEqual(model.packets,[packet(case,delta)]);self.assertEqual(model.r[2],case.handle);count+=1
        self.receipt.update(independent_rebase_phases=count,rebase_sets=3)

    def test_07_strict_image_header_code_data_metadata_and_length_negatives(self):
        before=self.values['conker/build/conker.us.elf']
        truth=self.rom[source.ROM:source.ROM+156]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,156),
                 source.elf_slot_offset(predicted,0x15001000,4),
                 source.elf_slot_offset(predicted,0x80082B20,4),
                 next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        self.receipt['strict_image_negative_controls']=7
