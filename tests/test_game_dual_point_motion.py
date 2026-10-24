"""Twin-point integration: float order, step aliases, callback window and guards."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import json
import re
import struct
import subprocess
import unittest

from tools.experiments import game_dual_point_motion as source
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests import test_game_effect_owner_ray as ray
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ACTOR,STEP,TABLE=0x30000,0x800BE9A4,0x80089CB8
WRITTEN=(0x34,0x38,0x3C,0x40,0x44,0x48,0x140,0x144,0x148)
ALIAS_FIELDS=(*WRITTEN,0x14C,0x150)
STEPS=(0,0x80000000,1,bits(.25),bits(.5),bits(1),bits(-1),bits(2.5))
DAMPINGS=tuple(map(bits,(0,-0.0,.5,1,-.75,1.25)))
VELOCITIES=((0,0x80000000,1),(bits(1.25),bits(-2.5),bits(3.75)),
    (bits(-19),bits(23),bits(-29)),(1,0x80000001,0x00800000),
    (bits(1e12),bits(-1e12),bits(.25)),(bits(-.125),bits(.375),bits(-.625)))
POINTS=(tuple(map(bits,(1,2,3,11,-13,17))),tuple(map(bits,(1e-25,-1e-25,1e12,-1e12,1e12,-1e-25))))


@dataclass(frozen=True)
class Case:
    step:int=0x3F000000
    damping:int=0x3F000000
    acceleration:int=0xBF800000
    pattern:int=1
    points:int=0
    layout:int=0


def owner_at(c,step=STEP):return ACTOR if not c.layout else step-ALIAS_FIELDS[c.layout-1]
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}


def fixture(c,step=STEP):
    owner=owner_at(c,step);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    m.update({owner+i:(i*13+0xA5)&255 for i in range(0x154)});put(m,step,c.step)
    for at,value in zip((0x34,0x38,0x3C,0x40,0x44,0x48),POINTS[c.points]):put(m,owner+at,value)
    for at,value in zip((0x140,0x144,0x148),VELOCITIES[c.pattern]):put(m,owner+at,value)
    put(m,owner+0x14C,c.acceleration);put(m,owner+0x150,c.damping)
    return m


def reference(initial,c,step=STEP):
    m=dict(initial);owner=owner_at(c,step);damping=read(m,owner+0x150)
    acceleration=read(m,owner+0x14C);old_y=read(m,owner+0x144)
    put(m,owner+0x140,mul(read(m,owner+0x140),damping))
    increment=mul(acceleration,read(m,step));old_z=read(m,owner+0x148)
    put(m,owner+0x148,mul(old_z,damping));put(m,owner+0x144,add(old_y,increment))
    late_step=read(m,step);change=[mul(read(m,owner+0x140+4*i),late_step)for i in range(3)]
    for base in(0x34,0x40):
        for i,value in enumerate(change):put(m,owner+base+4*i,add(read(m,owner+base+4*i),value))
    return m


def observable(m):
    return m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,tuple(m.r[i]for i in(*range(16,24),28,29,30,31))


class MotionOracle(ray.RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,step=STEP,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(owner_at(c,step),),connected=connected)

    def record_call(self,target):
        assert target==source.ENTRY,('unbounded motion service',hex(target))
        args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):raise AssertionError(('unowned motion service',hex(target)))


def corpus():
    for step,damping,pattern,acceleration,points in itertools.product(STEPS,DAMPINGS,range(6),map(bits,(0,-0.0,-9.8,.25)),range(2)):
        yield Case(step,damping,acceleration,pattern,points)


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,wrong_return=b.replace('return 1;','return 0;'),
        damp_y=b.replace('    motion->velocity[1] +=','    motion->velocity[1] *= damping;\n    motion->velocity[1] +='),
        missing_x=b.replace('    motion->velocity[0] *= damping;',''),missing_z=b.replace('    motion->velocity[2] *= damping;',''),
        inverted_acceleration=b.replace('motion->velocity[1] +=','motion->velocity[1] -='),
        unscaled_acceleration=b.replace('motion->verticalAcceleration * D_800BE9A4','motion->verticalAcceleration'),
        missing_endpoint=b.replace('    motion->endPoint[1] += dy;',''),
        wrong_axis=b.replace('motion->endPoint[2] += dz;','motion->endPoint[2] += dy;'),
        position_as_displacement=b.replace('motion->endPoint[0] += dx;','motion->endPoint[0] += motion->position[0];'),
        double_damp=b.replace('motion->velocity[0] *= damping;','motion->velocity[0] *= damping * damping;'))


def guest_controls():
    b=source.SELECTED[source.FUNCTION]
    early=b.replace('    motion->velocity[0] *= damping;','    step = D_800BE9A4;\n    motion->velocity[0] *= damping;')
    early=early.replace('    step = D_800BE9A4;\n    dx =','    dx =')
    extra='    step = D_800BE9A4;\n    dx = motion->velocity[0] * step;\n    dy = motion->velocity[1] * step;\n    dz = motion->velocity[2] * step;\n'
    return dict(early_step=early,reload_after_position=b.replace('    motion->endPoint[0] += dx;',extra+'    motion->endPoint[0] += dx;'))


def native_harness():
    rows=[]
    for c in corpus():
        m=reference(fixture(c),c)
        values=(c.step,c.damping,c.acceleration,*VELOCITIES[c.pattern],*POINTS[c.points],*(read(m,ACTOR+at)for at in WRITTEN))
        rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    text=source.HEADERS+source.DECLARATIONS+'''
f32 D_800BE9A4;
typedef union {u32 u;f32 f;} Float;
typedef char size_check[sizeof(DualPointMotion1BA1D0)==0x154?1:-1];
typedef char position_check[__builtin_offsetof(DualPointMotion1BA1D0,position)==0x34?1:-1];
typedef char endpoint_check[__builtin_offsetof(DualPointMotion1BA1D0,endPoint)==0x40?1:-1];
typedef char velocity_check[__builtin_offsetof(DualPointMotion1BA1D0,velocity)==0x140?1:-1];
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError(name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef struct {u32 step,damping,acceleration,vx,vy,vz,x,y,z,ex,ey,ez,ox,oy,oz,oex,oey,oez,ovx,ovy,ovz;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef s32(*Update)(DualPointMotion1BA1D0*);
__attribute__((noinline,noclone)) static s32 caller(Update fn,DualPointMotion1BA1D0*p){Update table[42];table[8]=fn;return table[8](p);}
static int variant(Update fn,u32 wrapped){
 u32 i,j;Float f;DualPointMotion1BA1D0 m;const Row*r;s32 result;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  r=rows+i;for(j=0;j<sizeof(m);j++)((u8*)&m)[j]=(u8)(j*13+0xA5);
  f.u=r->step;D_800BE9A4=f.f;f.u=r->damping;m.damping=f.f;f.u=r->acceleration;m.verticalAcceleration=f.f;
  f.u=r->vx;m.velocity[0]=f.f;f.u=r->vy;m.velocity[1]=f.f;f.u=r->vz;m.velocity[2]=f.f;
  f.u=r->x;m.position[0]=f.f;f.u=r->y;m.position[1]=f.f;f.u=r->z;m.position[2]=f.f;
  f.u=r->ex;m.endPoint[0]=f.f;f.u=r->ey;m.endPoint[1]=f.f;f.u=r->ez;m.endPoint[2]=f.f;
  result=wrapped?caller(fn,&m):fn(&m);if(result!=1)return 23;
  f.f=m.position[0];if(f.u!=r->ox)return 23;f.f=m.position[1];if(f.u!=r->oy)return 23;f.f=m.position[2];if(f.u!=r->oz)return 23;
  f.f=m.endPoint[0];if(f.u!=r->oex)return 23;f.f=m.endPoint[1];if(f.u!=r->oey)return 23;f.f=m.endPoint[2];if(f.u!=r->oez)return 23;
  f.f=m.velocity[0];if(f.u!=r->ovx)return 23;f.f=m.velocity[1];if(f.u!=r->ovy)return 23;f.f=m.velocity[2];if(f.u!=r->ovz)return 23;
  f.f=m.verticalAcceleration;if(f.u!=r->acceleration)return 23;f.f=m.damping;if(f.u!=r->damping)return 23;f.f=D_800BE9A4;if(f.u!=r->step)return 23;
  for(j=0;j<sizeof(m);j++)if(!((j>=0x34&&j<0x4C)||(j>=0x140&&j<0x154)))
   if(((u8*)&m)[j]!=(u8)(j*13+0xA5))return 23;
 }return 0;
}
int run(void){
'''
    for i,label in enumerate(controls()):text+='if(variant(%s,0)!=%d)return %d;\n'%(label,0 if label=='selected'else 23,i+1)
    return text+'if(variant(selected,1))return 70;\nreturn 0;}\n'+START,len(rows)


class DualPointMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.old=cls.values['conker/build/conker.us.elf']
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER);cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM));data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))

    def compare(self,c,phase=0):
        initial=fixture(c);expected=reference(initial,c)
        models=[MotionOracle(w,initial,c,phase).run()for w in(self.truth,self.raw,self.words)]
        for m in models:self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.r[2],1);self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));return models[0]

    def test_01_derived_schedule_and_all_float_operations_bindings_neighbors(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(source.normalized(raw,rs),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION));self.assertEqual(self.words,self.truth)
        def stream(words):return [w&~(31<<21)if w>>26 in(49,57)else w for w in words if w>>26 in(17,49,57)]
        self.assertEqual(stream(self.raw),stream(self.words));self.assertEqual(self.raw[22],0x24020001);self.assertEqual(self.words[5],0x24020001)
        for i in range(44):
            bad=bytearray(raw);bad[4*i]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],60)
        self.receipt.update(words=44,frame=0,bindings=2,new_guards=20,compiler_only=False,preserved_neighbors=60,
            unchanged_float_stream=True,normalizer_negative_controls=46,return_initializer_move_22_to5=True)

    def test_02_float_rounding_and_twelve_live_timestep_alias_layouts(self):
        count=0;visits=set()
        for c in corpus():
            for phase in(0,8):m=self.compare(c,phase);visits.update(m.visits);count+=1
        for layout,pattern,step,phase in itertools.product(range(12),range(6),STEPS[:4],(0,8)):
            self.compare(Case(step,bits(.5),bits(-.25),pattern,1,layout),phase);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+176,4))-visits,set())
        for value in(0x7FC00000,0x7F800000,0xFF800000):self.compare(Case(value,bits(.5),0,pattern=1))
        self.receipt.update(guest_root_phases=count,all_44_words_visited=True,guest_alias_layouts=12,
            additional_nonfinite_model_cases=3,FCSR_or_hardware_claimed=False,raw_volatile_GPRs_or_PC_not_equated=True)

    def test_03_actual_registration_and_original_return_sensitive_call_window(self):
        table=self.values['conker/asm/data/22E730.rodata.s'].decode().split('dlabel D_80089CB8\n',1)[1].split('enddlabel D_80089CB8',1)[0]
        names=re.findall(r'\.word\s+(\w+)',table);self.assertEqual(len(names),42);self.assertEqual(names[8],source.FUNCTION)
        ptr=struct.pack('>I',source.ENTRY);self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22E798])
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        at=source.elf_slot_offset(self.old,TABLE+32,4);self.assertEqual(self.old[at:at+4],ptr)
        original=list(struct.unpack_from('>16I',self.rom,ray.WINDOW_ROM));count=0;visits=set()
        for slot,expired,phase,zero_return,pattern in itertools.product((0,8),(0,1,128,255),(0,8),(False,True),range(6)):
            c=Case(pattern=pattern);initial=fixture(c);initial[ACTOR+0x70]=slot;initial[ACTOR+0x71]=7
            for i in range(42):put(initial,TABLE+4*i,source.ENTRY if i==8 else 0xABCD0000+4*i)
            expected=dict(initial);sp=STACK+phase-32
            if slot:put(expected,sp+32,ACTOR);put(expected,sp+27,expired,1);expected=reference(expected,c)
            models=[]
            for words in(self.truth,self.raw,self.words):
                callback=list(words)
                if zero_return:callback[callback.index(0x24020001)]=0x24020000
                m=MotionOracle(original,initial,c,phase,entry=ray.WINDOW,connected={source.ENTRY+4*i:w for i,w in enumerate(callback)})
                m.r[29]=sp;m.r[7]=expired;m.code=ray.WindowCode(m.code,m)
                with self.assertRaises(ray.WindowBoundary):m.run()
                wanted=(1 if zero_return else((expired^128)-128))if slot else expired
                self.assertEqual(m.memory,expected);self.assertEqual(m.r[7],wanted&0xFFFFFFFF);self.assertEqual(m.r[4],ACTOR);self.assertEqual(m.r[29],sp)
                self.assertEqual(m.calls,[(source.ENTRY,(ACTOR,))]if slot else[]);models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        self.assertTrue(set(range(ray.WINDOW,ray.WINDOW_END,4))<=visits)
        caller=self.values['conker/src/game_169510.c'].decode();lo,hi=source.function_span(caller,'func_1513CFE4')
        self.assertEqual(caller[lo:hi],'s32 func_1513CFE4() {\n    return 0;\n}')
        self.receipt.update(actual_original_window_words=16,actual_window_phases=count,registered_slot=8,table_entries=42,
            zero_return_control_fired=True,pointer_only_callback=True,full_parent_C_or_behavior_claimed=False)

    def test_04_native32_full_typed_storage_callback_return_and_controls(self):
        text,count=native_harness();unit=self.out/'native32.c';unit.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=count,native_typed_wrapper_cases_per_optimization=count,
            native_optimizations=['O0','O2','O3'],effective_wrong_C_controls=10,trap_UBSan=True,
            full_typed_storage=True,native_alias_or_full_parent_claimed=False)

    def test_05_literal_fault_prefixes_preserve_float_memory_and_saved_state(self):
        count=0
        for c in(Case(),Case(layout=7),Case(layout=9),Case(layout=1)):
            initial=fixture(c);done=MotionOracle(self.words,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.truth,self.raw,self.words):
                    m=MotionOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        self.receipt.update(fired_root_access_prefixes=count,complete_fitted_private_state_equal=True,
            raw_float_memory_trace_saved_state_equal=True,raw_fault_PC_or_volatile_result_not_equated=True)

    def test_06_independent_GNU_constant_carries_and_alias_rebases(self):
        from tools.experiments.game_actor_classifier_candidates import sections
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_1BA1D0.c.o');links=count=0
        for index,(entry,step)in enumerate(((source.ENTRY,STEP),(0x18017FFC,0x800A7FFC),(0x1A028000,0x800A8000))):
            images=[]
            for k,obj in enumerate(objects):
                data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,{'D_800BE9A4':step});self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    '--defsym=D_800BE9A4=0x%X'%step,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for layout,value,phase in itertools.product((0,1,7,9),STEPS[3:7],(0,8)):
                c=Case(value,layout=layout);initial=fixture(c,step);expected=reference(initial,c,step);models=[]
                for words in images:
                    m=MotionOracle(words,initial,c,phase,entry=entry,step=step).run();models.append(m);self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],1)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,HI_LO_carry_boundaries=True)

    def test_07_compiled_wrong_step_capture_controls_have_guest_counterexamples(self):
        results={}
        for name,body in guest_controls().items():
            self.assertNotEqual(body,source.SELECTED[source.FUNCTION]);obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+body,'wrong-'+name)
            self.assertFalse(diag);raw,rs=source.payload(obj,source.FUNCTION);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
            words=list(struct.unpack_from('>%dI'%(len(raw)//4),data,fs[source.FUNCTION]['value']));found=False
            for layout,pattern in itertools.product((1,2,3,4,5,6,7,8,9),range(1,6)):
                c=Case(bits(.5),bits(.5),bits(-.25),pattern,layout=layout);initial=fixture(c);expected=reference(initial,c)
                m=MotionOracle(words,initial,c).run()
                if public(m.memory)!=public(expected):found=True;break
            self.assertTrue(found,name);results[name]=dict(layout=layout,pattern=pattern)
        self.receipt.update(compiled_step_capture_negative_controls=results,disjoint_native_tests_not_used_to_claim_step_alias_sensitivity=True)

    def test_08_strict_image_guard_history_symbolic_and_real_padder_negatives(self):
        bodies=source.truths(self.values);expected=source.predicted_image(self.old,bodies);self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        for at in(0,len(expected)-1,source.elf_slot_offset(expected,source.ENTRY,176)):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.old,bytes(bad),bodies)
        old=self.values['conker/retail_word_patches.us.csv'];wanted=source.guard_bytes(old,*source.payload(self.out/'after-owner.o',source.FUNCTION))
        self.assertTrue(wanted.startswith(old));rows=list(csv.DictReader(io.StringIO(wanted.decode())));prior=list(csv.DictReader(io.StringIO(old.decode())))
        self.assertEqual(rows[:-20],prior);self.assertTrue(all(r['function']==source.FUNCTION for r in rows[-20:]))
        self.assertEqual([(int(r['offset'],0),r['expected_relocations'],r['replacement_relocations'])for r in rows[-20:]if r['expected_relocations']!='-'],
            [(0,'R_MIPS_HI16:D_800BE9A4','R_MIPS_HI16:D_800BE9A4'),(4,'R_MIPS_LO16:D_800BE9A4','R_MIPS_LO16:D_800BE9A4')])
        self.assertTrue(all(not r['insert_after']and r['omit']=='false'for r in rows[-20:]))
        from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
        obj=self.out/'after-owner.o';blob=bytearray(obj.read_bytes());header=ELF_HEADER.unpack_from(blob)
        sections=[SECTION_HEADER.unpack_from(blob,header[6]+i*header[11])for i in range(header[12])];strings=sections[header[13]];names=blob[strings[4]:strings[4]+strings[5]]
        text=next(s for s in sections if read_c_string(names,s[0])=='.text');_,fs,_=source.parse_object(obj);blob[text[4]+fs[source.FUNCTION]['value']+1]^=1
        wrong=self.out/'wrong-expected.o';wrong.write_bytes(blob)
        with self.assertRaises(ValueError):source.emit_padded_assembly(wrong,ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        rows[-20]['expected_relocations']='-';stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[-1]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
        bad=self.out/'wrong-relocations.csv';bad.write_text(stream.getvalue())
        with self.assertRaises(ValueError):source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n',*source.payload(obj,source.FUNCTION))
        self.receipt.update(strict_image_negative_controls=3,actual_padder_corruptions=2,old_guard_prefix_identical=True,
            symbolic_HI_LO_guard_checks=True,guard_prefix_corruption_control=True,new_guard_rows=20,metadata_exclusions=0)
