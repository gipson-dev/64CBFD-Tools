"""Damped motion, blend extrapolation, live timestep aliases and return-sensitive caller."""

from dataclasses import dataclass
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_blended_dual_point_motion_candidates as candidate
from tools.experiments import game_blended_dual_point_motion_match as match
from tools.experiments.game_linear_float_dataflow import derive
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_effect_owner_ray as ray
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT=candidate.ROOT
ACTOR,STEP,TABLE=0x30000,0x800BE9A4,0x80089CB8
WRITTEN=(0x34,0x38,0x3C,0x40,0x44,0x48,0x140,0x144,0x148)
INPUTS=(*WRITTEN,0x14C,0x150,0x15C)
STEPS=(0,0x80000000,1,bits(.5),bits(-1),bits(2.5))
DAMPINGS=tuple(map(bits,(0,-0.0,.5,-.75,1.25)))
BLENDS=tuple(map(bits,(-1,-0.0,0,.25,.5,1,1.5)))
VELOCITIES=((0,0x80000000,1),tuple(map(bits,(1.25,-2.5,3.75))),
    tuple(map(bits,(-19,23,-29))),(1,0x80000001,0x00800000),
    tuple(map(bits,(1e12,-1e12,.25))),tuple(map(bits,(-.125,.375,-.625))))
POINTS=(tuple(map(bits,(1,2,3,11,-13,17))),tuple(map(bits,(1e-25,-1e-25,1e12,-1e12,1e12,-1e-25))))


@dataclass(frozen=True)
class Case:
    step:int=0x3F000000
    damping:int=0x3F000000
    acceleration:int=0xBE800000
    blend:int=0x3E800000
    pattern:int=1
    points:int=0
    layout:int=-1


def owner_at(case,step=STEP):return ACTOR if case.layout<0 else step-case.layout
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def public(memory):return {at:v for at,v in memory.items() if not STACK-2048<=at<STACK+512}


def fixture(case,step=STEP):
    owner=owner_at(case,step)
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    memory.update({owner+i:(i*13+0x59)&255 for i in range(0x160)})
    for offset,value in zip(WRITTEN[:6],POINTS[case.points]):put(memory,owner+offset,value)
    for offset,value in zip(WRITTEN[6:],VELOCITIES[case.pattern]):put(memory,owner+offset,value)
    for offset,value in ((0x14C,case.acceleration),(0x150,case.damping),(0x15C,case.blend)):
        put(memory,owner+offset,value)
    put(memory,step,case.step)
    return memory


def reference(initial,case,step=STEP):
    memory=dict(initial);owner=owner_at(case,step)
    damping=read(memory,owner+0x150);acceleration=read(memory,owner+0x14C)
    put(memory,owner+0x140,mul(read(memory,owner+0x140),damping))
    y=add(read(memory,owner+0x144),mul(acceleration,read(memory,step)))
    z=mul(read(memory,owner+0x148),damping)
    put(memory,owner+0x144,y);put(memory,owner+0x148,z)
    late_step=read(memory,step)
    changes=[mul(read(memory,owner+0x140+4*i),late_step) for i in range(3)]
    for base in (0x34,0x40):
        for axis,change in enumerate(changes):
            at=owner+base+axis*4;put(memory,at,add(read(memory,at),change))
    for axis in range(3):
        pos=read(memory,owner+0x34+axis*4);at=owner+0x40+axis*4
        put(memory,at,add(pos,mul(sub(read(memory,at),pos),read(memory,owner+0x15C))))
    return memory


def nan_equivalent(actual,expected,owner):
    # C does not specify which NaN payload an exchanged add/multiply selects.
    # Preserve full byte equality everywhere except NaN-valued output words.
    actual,expected=public(actual),public(expected)
    for offset in WRITTEN:
        at=owner+offset
        if math.isnan(floating(read(expected,at))) and math.isnan(floating(read(actual,at))):
            put(actual,at,0x7FC00000);put(expected,at,0x7FC00000)
    return actual==expected


class MotionOracle(ray.RayOracle):
    def __init__(self,words,memory,case=Case(),phase=0,entry=match.ENTRY,step=STEP,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=(owner_at(case,step),),connected=connected)

    def record_call(self,target):
        if target!=match.ENTRY:raise AssertionError('Unbounded blended-motion helper %08X'%target)
        args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):raise AssertionError('Unowned blended-motion helper')


def corpus():
    for args in itertools.product(STEPS,DAMPINGS,map(bits,(0,-9.8,.25)),BLENDS,range(6),range(2)):
        yield Case(*args)


def controls():
    body=candidate.SELECTED
    replacements={
        'wrong_return':('return 1;','return 0;'),
        'missing_x_damping':('    motion->velocity[0] *= damping;\n',''),
        'missing_z_damping':('    motion->velocity[2] *= damping;\n',''),
        'damp_y':('    motion->velocity[1] +=','    motion->velocity[1] *= damping;\n    motion->velocity[1] +='),
        'inverted_acceleration':('motion->velocity[1] +=','motion->velocity[1] -='),
        'unscaled_acceleration':('motion->verticalAcceleration * D_800BE9A4','motion->verticalAcceleration'),
        'wrong_x_step':('motion->velocity[0] * step','motion->velocity[1] * step'),
        'wrong_end_z_step':('motion->endPoint[2] += dz','motion->endPoint[2] += dy'),
        'missing_end_y_step':('    motion->endPoint[1] += dy;\n',''),
        'wrong_position_x':('motion->position[0] += dx','motion->position[0] += dy'),
        'inverse_blend':('* motion->blend;','* (1.0f - motion->blend);'),
        'wrong_blend_field':('* payload->blend;','* motion->damping;'),
        'wrong_blend_sign':('(motion->endPoint[0] - motion->position[0])','(motion->position[0] - motion->endPoint[0])'),
        'wrong_blend_base':('motion->position[0] + (motion->endPoint[0]','motion->endPoint[0] + (motion->endPoint[0]'),
        'missing_x_blend':('    motion->endPoint[0] = motion->position[0] + (motion->endPoint[0] - motion->position[0]) * motion->blend;\n',''),
        'wrong_y_blend_axis':('(motion->endPoint[1] - motion->position[1])','(motion->endPoint[2] - motion->position[1])'),
    }
    result={name:body.replace(old,new,1) for name,(old,new) in replacements.items()}
    if any(value==body for value in result.values()):raise AssertionError('Ineffective blended-motion control')
    return result


def guest_controls():
    body=candidate.SELECTED
    early=body.replace('    motion->velocity[0] *= damping;',
        '    step = D_800BE9A4;\n    motion->velocity[0] *= damping;',1)
    early=early.replace('    step = D_800BE9A4;\n    dx =','    dx =',1)
    extra='    step = D_800BE9A4;\n    dx = motion->velocity[0] * step;\n    dy = motion->velocity[1] * step;\n    dz = motion->velocity[2] * step;\n'
    return {'early_step':early,'reload_after_position':body.replace('    motion->endPoint[0] += dx;',extra+'    motion->endPoint[0] += dx;',1)}


def native_source():
    cases=list(corpus());rows=[]
    for index in range(4096):
        case=cases[index*97%len(cases)];initial=fixture(case);expected=reference(initial,case)
        values=(read(initial,STEP),*(read(initial,ACTOR+at) for at in INPUTS),
                *(read(expected,ACTOR+at) for at in WRITTEN))
        rows.append('{{'+','.join('0x%08Xu'%v for v in values[:13])+'},{'+','.join('0x%08Xu'%v for v in values[13:])+'}}')
    text='typedef unsigned char u8;typedef unsigned int u32;typedef signed int s32;typedef float f32;\nextern f32 D_800BE9A4;\n'+candidate.DECLARATIONS
    variants={'selected':candidate.SELECTED,**controls()}
    for name,body in variants.items():text+=body.replace(candidate.FUNCTION,name)+'\n'
    text+='''
f32 D_800BE9A4;
typedef union {u32 u;f32 f;} Float;
typedef char size_check[sizeof(BlendedDualPointMotion1518EF54)==0x160?1:-1];
typedef char point_check[__builtin_offsetof(BlendedDualPointMotion1518EF54,position)==0x34?1:-1];
typedef char end_check[__builtin_offsetof(BlendedDualPointMotion1518EF54,endPoint)==0x40?1:-1];
typedef char velocity_check[__builtin_offsetof(BlendedDualPointMotion1518EF54,velocity)==0x140?1:-1];
typedef char blend_check[__builtin_offsetof(BlendedDualPointMotion1518EF54,blend)==0x15C?1:-1];
typedef struct {u32 input[13],output[9];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef s32(*Update)(BlendedDualPointMotion1518EF54 *);
__attribute__((noinline,noclone)) static s32 caller(Update fn,BlendedDualPointMotion1518EF54 *m){Update table[42];table[7]=fn;return table[7](m);}
static s32 variant(Update fn,u32 wrapped){
 static const u32 inputs[12]={0x34,0x38,0x3C,0x40,0x44,0x48,0x140,0x144,0x148,0x14C,0x150,0x15C};
 static const u32 outputs[9]={0x34,0x38,0x3C,0x40,0x44,0x48,0x140,0x144,0x148};
 union {BlendedDualPointMotion1518EF54 m;u32 words[0x160/4];u8 bytes[0x160];} actual,wanted;
 u32 i,j;Float f;s32 result;
 for(i=0;i<4096;i++){
  for(j=0;j<0x160;j++)actual.bytes[j]=(u8)(j*13+0x59);
  for(j=0;j<12;j++)actual.words[inputs[j]/4]=rows[i].input[j+1];
  f.u=rows[i].input[0];D_800BE9A4=f.f;
  for(j=0;j<0x160;j++)wanted.bytes[j]=actual.bytes[j];
  for(j=0;j<9;j++)wanted.words[outputs[j]/4]=rows[i].output[j];
  result=wrapped?caller(fn,&actual.m):fn(&actual.m);
  if(result!=1)return 23;
  for(j=0;j<0x160;j++)if(actual.bytes[j]!=wanted.bytes[j])return 23;
  f.f=D_800BE9A4;if(f.u!=rows[i].input[0])return 23;
 }return 0;
}
int run(void){
 if(variant(selected,0)||variant(selected,1))return 1;
'''
    for index,name in enumerate(controls()):text+=' if(variant(%s,0)!=23)return %d;\n'%(name,index+2)
    return text+' return 0;\n}\n'+START


class BlendedDualPointMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=match.prepare(ROOT);cls.out=ROOT/match.BUILD;cls.nan_payload_cases=0
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>65I',cls.rom,match.ROM))
        text,functions,bindings=parse_object(cls.prepared['qualified_compact']);info=functions[match.FUNCTION]
        raw=text[info['value']:info['value']+match.SIZE]
        cls.raw=list(struct.unpack('>65I',raw));cls.raw[:2]=cls.retail[:2]
        fitted,_=match.normalized(raw,match.BINDINGS,cls.rom[match.ROM:match.ROM+match.SIZE])
        cls.fitted=list(struct.unpack('>65I',fitted));cls.fitted[:2]=cls.retail[:2]

    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,case,phase=0,step=STEP,entry=match.ENTRY,words=None):
        initial=fixture(case,step);expected=reference(initial,case,step)
        images=(self.retail,self.raw,self.fitted) if words is None else words
        models=[MotionOracle(image,initial,case,phase,entry,step).run() for image in images]
        for index,model in enumerate(models):
            if index==1:
                self.assertTrue(nan_equivalent(model.memory,expected,owner_at(case,step)),case)
                if public(model.memory)!=public(expected):self.nan_payload_cases+=1
            else:self.assertEqual(public(model.memory),public(expected),case)
            self.assertEqual(model.r[2],1);self.assertFalse(model.calls)
        self.assertEqual(complete(models[0]),complete(models[2]))
        return models

    def test_01_bijective_dataflow_normalizer_owner_guards_and_literal_image(self):
        report=self.prepared['report'];proof=report['dataflow']
        self.assertEqual((report['words'],report['guards'],report['neighbors'],report['relocations']),(65,51,60,2))
        self.assertEqual((proof['alias_layouts'],proof['loads'],proof['stores'],proof['float_operations']),(89,25,12,22))
        self.assertEqual(sorted(proof['permutation']),list(range(65)));self.assertFalse(proof['reassociation'])
        raw,functions,_=parse_object(self.prepared['qualified_compact']);info=functions[match.FUNCTION]
        body=raw[info['value']:info['value']+match.SIZE];truth=self.rom[match.ROM:match.ROM+match.SIZE]
        for index in range(match.SIZE):
            bad=bytearray(body);bad[index]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),match.BINDINGS,truth)
        for bindings in ({},{0:match.BINDINGS[0]},{**match.BINDINGS,4:[('R_MIPS_LO16','D_800BE9A8')]}):
            with self.assertRaises(ValueError):match.normalized(body,bindings,truth)
        bad=self.raw.copy();at=next(i for i,w in enumerate(bad) if w>>26==17 and w&63==2);bad[at]^=2
        with self.assertRaises(ValueError):derive(bad,self.retail,[ACTOR])
        with self.assertRaises(ValueError):derive(self.raw[:-1],self.retail,[ACTOR])
        for index in (0,len(match.PATCH_ROWS)//2,len(match.PATCH_ROWS)-1):
            rows=[dict(r) for r in self.prepared['predecessor_rows']]+[match.complete_row(r) for r in match.PATCH_ROWS]
            rows[len(self.prepared['predecessor_rows'])+index]['expected']='0x%08X'%(match.GUARD_WORDS[index][1]^1)
            path=self.out/('bad-guard-%d.csv'%index);harness.write_patches(path,self.prepared['fields'],rows)
            with self.assertRaises(ValueError):emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,word_patches_path=path,filename=match.FILENAME)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for at in (0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)

    def test_02_float_order_blend_endpoints_extrapolation_and_all_words(self):
        visits=set();count=0
        for case in corpus():
            for model in self.compare(case):visits.update(model.visits)
            count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+match.SIZE,4)))
        for word in (0x7FC12345,0x7F800000,0xFF800000,0x7F7FFFFF):
            self.compare(Case(step=word));self.compare(Case(blend=word));count+=2
        self.receipt('guest-contract',{'cases_per_body':count,'covered_words':65,'blend_values':list(BLENDS),
            'raw_nan_payload_comparison':'NaN value classification; all other bytes exact',
            'raw_nan_payload_cases':self.nan_payload_cases,'FCSR_or_hardware_claimed':False})

    def test_03_every_aligned_timestep_overlap_in_record(self):
        count=0
        for layout,pattern,blend,phase in itertools.product(range(0,0x160,4),(0,1,4),map(bits,(0,.5,1.5)),(0,8)):
            self.compare(Case(layout=layout,pattern=pattern,blend=blend),phase);count+=1
        self.receipt('aliases',{'cases_per_body':count,'aligned_overlapping_layouts':88,
            'disjoint_layout_also_qualified':True,'raw_nan_payload_cases':self.nan_payload_cases})

    def test_04_native32_typed_storage_direct_and_callback_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_source())
        for opt in ('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            result=subprocess.run([*native_command(opt),'-fno-strict-aliasing','-mstackrealign',str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            executed=subprocess.run([str(binary)],capture_output=True,timeout=60)
            self.assertEqual(executed.returncode,0,(opt,executed.returncode,executed.stdout,executed.stderr))
        self.receipt('native-contract',{'profiles':['O0','O2','O3'],'direct_cases_per_profile':4096,
            'typed_callback_cases_per_profile':4096,'semantic_controls':sorted(controls()),'trap_UBSan':True})

    def test_05_original_registered_return_sensitive_callback_window(self):
        original=list(struct.unpack_from('>16I',self.rom,ray.WINDOW_ROM));count=0;visits=set()
        for slot,expired,phase,zero_return,pattern,blend in itertools.product((0,7),(0,1,128,255),(0,8),(False,True),(0,1,4),map(bits,(0,.5,1.5))):
            case=Case(pattern=pattern,blend=blend);initial=fixture(case);initial[ACTOR+0x70]=slot;initial[ACTOR+0x71]=7
            for i in range(42):put(initial,TABLE+4*i,match.ENTRY if i==7 else 0xABCD0000+4*i)
            expected=dict(initial);sp=STACK+phase-32
            if slot:
                put(expected,sp+32,ACTOR);put(expected,sp+27,expired,1);expected=reference(expected,case)
            models=[]
            for image in (self.retail,self.raw,self.fitted):
                callback=list(image)
                if zero_return:callback[callback.index(0x24020001)]=0x24020000
                connected={match.ENTRY+4*i:w for i,w in enumerate(callback)}
                model=MotionOracle(original,initial,case,phase,entry=ray.WINDOW,connected=connected)
                model.r[29]=sp;model.r[7]=expired;model.code=ray.WindowCode(model.code,model)
                with self.assertRaises(ray.WindowBoundary):model.run()
                self.assertEqual(model.memory,expected);self.assertEqual(model.r[29],sp)
                wanted=(1 if zero_return else ((expired^128)-128)) if slot else expired
                self.assertEqual(model.r[7],wanted&0xFFFFFFFF)
                self.assertEqual(model.calls,[(match.ENTRY,(ACTOR,))] if slot else [])
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.assertTrue(set(range(ray.WINDOW,ray.WINDOW_END,4))<=visits)
        self.receipt('caller-window',{'phases':count,'words':16,'slot':7,'table_entries':42,
            'controlled_zero_return_fired':True,'full_parent_claimed':False})

    def test_06_normalized_literal_fault_prefixes(self):
        count=0
        for case in (Case(),Case(layout=0x140),Case(layout=0x144),Case(layout=0x34),Case(layout=0x15C)):
            initial=fixture(case);done=MotionOracle(self.fitted,initial,case).run()
            for cut in range(done.root_accesses):
                models=[]
                for image in (self.retail,self.fitted):
                    model=MotionOracle(image,initial,case);model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                    models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt('fault-prefixes',{'fired_prefixes':count,'complete_fitted_private_state_equal':True,
            'raw_fault_access_order_or_PC_not_equated':True})

    def test_07_independent_GNU_links_step_carries_and_rebased_aliases(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('BlendedOriginal',(),dict(root=ROOT,out=self.out))
        original=ViewListSetupTests.original.__func__(context,'original-blended', (ROOT/match.ASM).read_text(),match.FUNCTION)
        objects=(original,self.prepared['qualified_compact'],self.prepared['qualified_owner']);count=links=0
        for index,(entry,step) in enumerate(((match.ENTRY,STEP),(0x18017FFC,0x800A7FFC),(0x1A028000,0x800A8000))):
            images=[]
            for ordinal,obj in enumerate(objects):
                data,functions,relocations=parse_object(obj)
                assembly,unknown=emit_function(data,functions[match.FUNCTION],relocations,match.FUNCTION,{'D_800BE9A4':step})
                self.assertFalse(unknown);path=self.out/('rebase-%d-%d'%(index,ordinal))
                path.with_suffix('.s').write_text(assembly);path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path.with_suffix('.ld')),'-e',match.FUNCTION,
                    '--defsym=D_800BE9A4=0x%X'%step,'-o',str(path.with_suffix('.elf')),str(path.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>65I',sections(path.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);derive(images[1],images[0],[ACTOR]+[step-at for at in range(0,0x160,4)])
            for layout,blend in itertools.product((-1,0x34,0x140,0x144,0x15C),map(bits,(0,.5,1.5))):
                self.compare(Case(layout=layout,blend=blend),step=step,entry=entry,words=images);count+=1
        self.receipt('rebases',{'GNU_links':links,'phases':count,'HI_LO_carry_edges':True})

    def test_08_compiled_early_and_late_step_controls_have_guest_counterexamples(self):
        result={}
        for label,body in guest_controls().items():
            obj,_=compile_owner(ROOT,self.out,candidate.source_with(body),'control-'+label)
            text,functions=link_owner(ROOT,self.out,obj,candidate.OWNER);info=functions[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),text,info['value']))
            case=Case(layout=0x140 if label=='early_step' else 0x34)
            initial=fixture(case);wanted=reference(initial,case);model=MotionOracle(words,initial,case).run()
            self.assertNotEqual(public(model.memory),public(wanted),label)
            result[label]={'layout':'0x%X'%case.layout,'words':len(words),'counterexample':True}
        self.receipt('compiled-step-controls',result)


if __name__=='__main__':unittest.main()
