"""Owner ray callback: direct words, live aliases, faults and original call window."""
from pathlib import Path
import itertools
import json
import re
import struct
import subprocess
import unittest

from tools.experiments import game_effect_owner_ray as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
EFFECT,LINKED,TABLE=0x30000,0x40000,0x80089CB8
WINDOW,WINDOW_END,WINDOW_ROM=0x1513D034,0x1513D074,0x16A4E4
VALUES=(0,0x80000000,0x3FA00000,0xC1900000,0x3F000000,0xBF800000)
FLAGS=(0,2,4,6,0x80000000,0x3F800007)


def fixture(active,flags,layout=0,seed=0,effect=EFFECT):
    owner=(LINKED,effect+8,effect+0x24,effect-0xF4)[layout]
    memory={STACK+i:(i*17+seed)&255 for i in range(-1024,1024)}
    for base in(effect,owner):
        memory.update({base+i:(i*29+seed)&255 for i in range(-16,0x200)})
    put(memory,effect+0x178,owner)
    for i in range(3):
        put(memory,owner+0x34+i*4,VALUES[(seed+i)%6])
        put(memory,owner+0x140+i*4,VALUES[(seed+i+3)%6])
    memory[owner+0x128]=active
    put(memory,effect+0x58,flags)
    return memory,owner


def reference(initial,effect=EFFECT):
    memory=dict(initial);owner=read(memory,effect+0x178)
    if memory[owner+0x128]&1:
        flags=read(memory,effect+0x58)
        for i in range(3):put(memory,effect+0x34+i*4,read(memory,owner+0x34+i*4))
        for i in range(3):
            direction=floating(read(memory,owner+0x140+i*4))
            position=floating(read(memory,owner+0x34+i*4))
            value=bits(position+floating(bits(direction*500.0)))
            if i==2:put(memory,effect+0x58,flags|6)
            put(memory,effect+0x40+i*4,value)
    else:
        flags=read(memory,effect+0x58)&0xFFFFFFFB
        put(memory,effect+0x58,flags);put(memory,effect+0x58,flags&0xFFFFFFFD)
    return memory


class RayOracle(TimingOracle):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY,effect=EFFECT,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(effect,),connected=connected)

    def execute(self,word):
        if word>>26!=32:
            return super().execute(word)
        rs,rt,imm=word>>21&31,word>>16&31,word&65535
        self.dispatched_word=word;self.own_instruction=True
        try:
            value=self.get((self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF,1)
            self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
        finally:
            self.own_instruction=False

    def record_call(self,target):
        assert target==source.ENTRY,('unbounded callback',hex(target))
        self.calls.append((target,self.arguments(1)))
        self.events.append(('CALL',target,self.arguments(1)))

    def hook(self,target):
        raise AssertionError(('unowned ray helper',target))


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==WINDOW_END:raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    body=source.SELECTED
    return dict(selected=body,false_return=body.replace('return 1;','return 0;'),
        wrong_scale=body.replace('500.0f','499.0f'),
        exact_active=body.replace('active & 1','active == 1'),
        missing_flag=body.replace('flags |= 6','flags |= 4'),
        wrong_clear=body.replace('flags &= ~4','flags &= ~8'),
        keep_position=body.replace('effect->position = owner->position;',''),
        wrong_axis=body.replace('motion->direction.z','motion->direction.x'),
        keep_endpoint_y=body.replace('effect->endPoint.y = owner->position.y + motion->direction.y * 500.0f;',''))


def native_harness():
    result='#include <ultra64.h>\n'+source.DECLARATIONS+'''
typedef char effect_size[sizeof(OwnerRayEffect)==0x17C?1:-1];
typedef char owner_size[sizeof(EffectRayOwner)==0x14C?1:-1];
typedef char linked_offset[__builtin_offsetof(OwnerRayEffect,owner)==0x178?1:-1];
typedef char active_offset[__builtin_offsetof(EffectRayOwner,motion.active)==0x128?1:-1];
typedef char direction_offset[__builtin_offsetof(EffectRayOwner,motion.direction)==0x140?1:-1];
typedef char position_offset[__builtin_offsetof(OwnerRayEffect,position)==0x34?1:-1];
typedef char endpoint_offset[__builtin_offsetof(OwnerRayEffect,endPoint)==0x40?1:-1];
typedef char flags_offset[__builtin_offsetof(OwnerRayEffect,flags)==0x58?1:-1];
static struct {u32 left[4];OwnerRayEffect record;u32 right[4];} actual,expected;
static struct {u32 left[4];EffectRayOwner record;u32 right[4];} linked,saved;
'''
    for name,body in controls().items():result+=body.replace(source.FUNCTION,name)+'\n'
    result+='''typedef s32 (*Update)(OwnerRayEffect*);
static f32 real(u32 bits){union{u32 bits;f32 value;}v;v.bits=bits;return v.value;}
static const u32 flags[]={0,1,2,4,6,7,0x80000000u,0xFFFFFFFFu,0xA5A5A5A5u};
static const u32 values[]={0,0x80000000u,0x3FA00000u,0xC1900000u,0x3F000000u,0xBF800000u};
static int variant(Update fn){
 u32 active,flag,value,i;u8*p=(u8*)&actual,*q=(u8*)&expected,*a=(u8*)&linked,*b=(u8*)&saved;
 for(active=0;active<256;active++)for(flag=0;flag<9;flag++)for(value=0;value<6;value++){
  for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*29+active+flag*17);
  for(i=0;i<sizeof(linked);i++)a[i]=(u8)(i*13+value*7);
  actual.record.owner=&linked.record;
  linked.record.position.x=real(values[value]);
  linked.record.position.y=real(values[(value+1)%6]);
  linked.record.position.z=real(values[(value+2)%6]);
  linked.record.motion.direction.x=real(values[(value+3)%6]);
  linked.record.motion.direction.y=real(values[(value+4)%6]);
  linked.record.motion.direction.z=real(values[(value+5)%6]);
  linked.record.motion.active=(u8)active;actual.record.flags=flags[flag];
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];
  for(i=0;i<sizeof(linked);i++)b[i]=a[i];
  if(active&1){
   volatile f32 x=linked.record.motion.direction.x*500.0f;
   volatile f32 y=linked.record.motion.direction.y*500.0f;
   volatile f32 z=linked.record.motion.direction.z*500.0f;
   expected.record.position=linked.record.position;
   expected.record.endPoint.x=linked.record.position.x+x;
   expected.record.endPoint.y=linked.record.position.y+y;
   expected.record.endPoint.z=linked.record.position.z+z;
   expected.record.flags|=6;
  }else{expected.record.flags&=~4;expected.record.flags&=~2;}
  if(fn(&actual.record)!=1)return 23;
  for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 23;
  for(i=0;i<sizeof(linked);i++)if(a[i]!=b[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i,name in enumerate(controls()):result+=' if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,i+1)
    return result+' return 0;\n}\n'+START


class EffectOwnerRayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        raw,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        cls.raw=raw;cls.words=list(struct.unpack('>43I',source.payload(raw)[0]));cls.receipt={}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')

    def test_01_literal_words_owner_make_and_inputs(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(source.payload(self.raw)[1],{})
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],43)
        self.receipt.update(exact_words=43,frame=0,bindings=0,new_guards=0,compiler_only=True,preserved_neighbors=43)

    def test_02_guest_results_aliases_and_literal_state(self):
        visits=set();count=0
        for active,flags,layout in itertools.product(range(256),FLAGS,range(4)):
            memory,_=fixture(active,flags,layout,active%6);expected=reference(memory)
            models=[RayOracle(words,memory,phase=(active&1)*8).run()for words in(self.truth,self.words)]
            for model in models:
                self.assertEqual(model.memory,expected);self.assertEqual(model.r[2],1)
                self.assertEqual(model.r[29],STACK+(active&1)*8);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-{0x150F0170})
        self.receipt.update(guest_phases=count,guest_alias_layouts=3,visited_words=42,
            unreachable_redundant_load_retained=True,literal_full_GPR_FPR_RAM_events=True,
            hardware_FCSR_parity_claimed=False,portable_native_alias_claimed=False)

    def linked(self,obj,entry,label):
        data,functions,bindings=source.parse_object(obj)
        asm,unknown=emit_function(data,functions[source.FUNCTION],bindings,source.FUNCTION,{})
        self.assertFalse(unknown);p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            '-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_03_rebased_code_stack_aliases_and_fired_fault_prefixes(self):
        count=cuts=0
        objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_11C2B0.c.o')
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            images=[self.linked(obj,entry,'rebased-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for active,layout,effect in itertools.product((0,1,128,255),range(4),(EFFECT,STACK-0x180)):
                memory,_=fixture(active,6,layout,2,effect)
                models=[RayOracle(words,memory,entry=entry,effect=effect).run()for words in images[:2]]
                self.assertEqual(models[0].memory,reference(memory,effect));self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for active,layout,phase in itertools.product((0,1,128,255),range(4),(0,8)):
            memory,_=fixture(active,6,layout,2);model=RayOracle(self.truth,memory,phase).run()
            for cut in range(model.root_accesses):
                models=[RayOracle(words,memory,phase)for words in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=count,fired_root_access_prefixes=cuts,
            guest_stack_aliases_checked=True,portable_C_fault_semantics_claimed=False)

    def test_04_native32_semantics_layouts_and_effective_controls(self):
        fixture_path=self.out/'native32.c';fixture_path.write_text(native_harness())
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            p=subprocess.run([*native_command(opt),str(fixture_path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=13824,native_optimizations=['O0','O2','O3'],
            effective_wrong_C_controls=8,trap_UBSan=True,native_disjoint_typed_finite_float_storage=True)

    def test_05_original_registration_call_window_and_return_control(self):
        table_source=self.values['conker/asm/data/22E730.rodata.s'].decode()
        table_source=table_source.split('dlabel D_80089CB8\n',1)[1].split('enddlabel D_80089CB8',1)[0]
        names=re.findall(r'\.word\s+(\w+)',table_source)
        self.assertEqual(len(names),42);self.assertEqual(names[30],source.FUNCTION)
        literal=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==literal],[0x22E7F0])
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[])
        original=list(struct.unpack_from('>16I',self.rom,WINDOW_ROM));self.assertEqual(original[9],0x0320F809)
        count=0;visits=set()
        for slot,expired,active,phase,zero_return in itertools.product((0,30),(0,1,128,255),(0,1),(0,8),(False,True)):
            initial,_=fixture(active,0x80000000,0,2);initial[EFFECT+0x70]=slot;initial[EFFECT+0x71]=7
            for i in range(42):put(initial,TABLE+i*4,source.ENTRY if i==30 else 0xABCD0000+i*4)
            expected=dict(initial);sp=STACK+phase-32
            if slot:
                put(expected,sp+32,EFFECT);put(expected,sp+27,expired,1);expected=reference(expected)
            models=[]
            for words in(self.truth,self.words):
                callback=list(words)
                if zero_return:callback[-3]=0x24020000
                connected={source.ENTRY+i*4:w for i,w in enumerate(callback)}
                model=RayOracle(original,initial,phase,entry=WINDOW,connected=connected)
                model.r[29]=sp;model.r[7]=expired;model.code=WindowCode(model.code,model)
                with self.assertRaises(WindowBoundary):model.run()
                self.assertEqual(model.memory,expected)
                wanted=(1 if zero_return else ((expired^128)-128))if slot else expired
                self.assertEqual(model.r[7],wanted&0xFFFFFFFF)
                self.assertEqual(model.calls,[(source.ENTRY,(EFFECT,))]if slot else [])
                self.assertEqual(model.r[4],EFFECT);self.assertEqual(model.r[29],sp)
                visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(WINDOW,WINDOW_END,4))<=visits)
        caller=self.values['conker/src/game_169510.c'].decode()
        lo,hi=source.function_span(caller,'func_1513CFE4')
        self.assertEqual(caller[lo:hi],'s32 func_1513CFE4() {\n    return 0;\n}')
        self.receipt.update(actual_original_window_words=16,actual_call_window_phases=count,
            table_entries=42,registered_slot=30,pointer_only_callback=True,zero_return_control_fired=True,
            full_parent_C_or_behavior_claimed=False,retail_no_range_check_preserved=True)

    def test_06_strict_image_and_history_negative_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE]
        expected=source.predicted_image(before,truth);source.check_image(before,expected,truth)
        at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
        sym=[offset for offset,name,_,_ in source.symbol_rows(before)if name==source.FUNCTION][0]
        positions=(0,at-1,at,at+168,at+172,sym+4,sym+8,len(before)-1)
        for position in positions:
            bad=bytearray(expected);bad[position]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.assertEqual(json.loads((self.out/'first-link.json').read_text())['metadata_exclusions'],0)
        self.receipt.update(strict_image_negatives=len(positions)+1,guard_manifest_byte_identical=True,
            full_source_input_history_pinned=True,metadata_exclusions=0)
