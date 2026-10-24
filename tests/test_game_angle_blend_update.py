"""Angle blend: float32 boundaries, helper ABI, original parent and closed image."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_angle_blend_update as source
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ACTOR,ALT=0x30000,0x34000
STEP,FINAL,HELPER,PARENT,ORIENT=0x800A3694,0x800A3698,0x15048A70,0x1512C068,0x15123A54
STEP_BITS,FINAL_BITS=0x3BC49BA6,0x4479C000


@dataclass(frozen=True)
class Case:
    phase:int=0
    current:int=0
    target:int=0
    flags:int=3
    mode:int=0
    alias:int=0


def owner_at(c,step=STEP,final=FINAL):
    return (ACTOR,step-0x5CC,final-0x384,final-0x240)[c.alias]


def fixture(c,step=STEP,final=FINAL):
    owner=owner_at(c,step,final)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base in (owner,ALT):
        m.update({base+i:(i*13+0xA5)&255 for i in range(0x600)})
    put(m,step,STEP_BITS);put(m,final,FINAL_BITS)
    for at,value in ((0x5CC,c.phase),(0x384,c.current),(0x37C,c.target),(0x240,c.flags)):
        put(m,owner+at,value)
    for at,value in ((0x5CC,bits(.25)),(0x384,bits(-123.25)),(0x37C,bits(720)),(0x240,0x80000002)):
        put(m,ALT+at,value)
    return m


def angle_delta(current,target):
    a,b=floating(current),floating(target);difference=floating(bits(a-b))
    if difference>180:a=floating(bits(a-360))
    elif difference<=-180:b=floating(bits(b-360))
    return bits(b-a)


def mutation(m,c,owner):
    if c.mode==1:
        put(m,owner+0x384,bits(-123.25));put(m,owner+0x5CC,bits(.25));put(m,owner+0x37C,bits(720))
    elif c.mode==2:
        put(m,owner+0x384,bits(77));put(m,owner+0x5CC,bits(-.5));put(m,owner+0x240,0xA5A50003)


def reference(initial,c,step=STEP,final=FINAL,helper=HELPER,owner=None):
    m=dict(initial);owner=owner_at(c,step,final)if owner is None else owner;calls=[]
    phase=bits(floating(read(m,owner+0x5CC))+floating(read(m,step)))
    if floating(phase)>1:phase=bits(1)
    put(m,owner+0x5CC,phase)
    if floating(phase)==1:
        sentinel=read(m,final);put(m,owner+0x240,read(m,owner+0x240)&0xFFFFFFFD);put(m,owner+0x384,sentinel)
    else:
        args=(read(m,owner+0x384),read(m,owner+0x37C));calls.append((helper,args))
        delta=angle_delta(*args);mutation(m,c,owner)
        if c.mode==3:owner=ALT
        product=bits(floating(delta)*floating(read(m,owner+0x5CC)))
        put(m,owner+0x384,bits(floating(read(m,owner+0x384))+floating(product)))
    return m,calls


def public(m):
    return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}


class AngleOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,helper=HELPER,arguments=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(owner_at(c),),connected=connected)
        self.case,self.helper,self.entered=c,helper,STACK+phase
        self.parent_mutation=False

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==4:
            self.dispatched_word=word;self.own_instruction=True
            try:self.f[word>>6&31]=bits(math.sqrt(floating(self.f[word>>11&31])))
            finally:self.own_instruction=False
            return
        return super().execute(word)

    def record_call(self,target):
        if target==self.helper:args=(self.f[12],self.f[14])
        else:
            assert target in(source.ENTRY,ORIENT),('unbounded angle provider',hex(target))
            args=self.arguments(1)
            if target==source.ENTRY:self.entered=self.r[29]
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target==self.helper:
            value=angle_delta(self.f[12],self.f[14]);mutation(self.memory,self.case,owner_at(self.case))
            if self.case.mode==3:put(self.memory,self.entered,ALT)
        else:
            assert target==ORIENT;value=0xA5000000
            if self.parent_mutation:
                owner=self.arguments(1)[0]
                put(self.memory,owner+0x5CC,bits(.995));put(self.memory,owner+0x384,bits(123));put(self.memory,owner+0x240,0xA5A50001)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value
        self.hi,self.lo=0x87654321,0x12345678


def corpus():
    boundary=bits(1-floating(STEP_BITS))
    phases=(0,0x80000000,1,bits(-2),bits(-.006),bits(.5),bits(.993),boundary-1,boundary,boundary+1,bits(1),bits(1)+1,bits(2))
    pairs=((0,0),(0x80000000,0),(bits(1e-40),0),(bits(179),bits(-179)),(bits(-179),bits(179)),
        (bits(180),0),(bits(180)-1,0),(bits(180)+1,0),(0,bits(180)),(0,bits(180)-1),(0,bits(180)+1),
        (bits(-540),bits(540)),(bits(1080),bits(-1080)),(bits(35.25),bits(-172.5)))
    for phase,(current,target),flags,mode in itertools.product(phases,pairs,(0,2,0x80000002,0xFFFFFFFF),(0,1,2)):
        yield Case(phase,current,target,flags,mode)


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,wrong_step=b.replace('D_800A3694','0.00625f'),
        missing_clamp=b.replace('actor->unk5CC = actor->unk5CC > 1.0f ? 1.0f : actor->unk5CC;',''),
        lower_clamp=b.replace('    if (actor->unk5CC == 1.0f)', '    if (actor->unk5CC < 0) actor->unk5CC = 0;\n    if (actor->unk5CC == 1.0f)'),
        wrong_completion=b.replace('== 1.0f','> 0.99f'),wrong_sentinel=b.replace('D_800A3698','0.0f'),
        wrong_flag=b.replace('~2','~1'),reversed_delta=b.replace('actor->unk384, actor->unk37C','actor->unk37C, actor->unk384'),
        missing_factor=b.replace('delta * actor->unk5CC','delta'),
        early_angle=b.replace('    f32 delta;','    f32 delta;\n    f32 previous = actor->unk384;').replace('actor->unk384 += delta * actor->unk5CC;','actor->unk384 = previous + delta * actor->unk5CC;'),
        early_phase=b.replace('    f32 delta;','    f32 delta;\n    f32 phase;').replace('        delta = func_15048A70','        phase = actor->unk5CC;\n        delta = func_15048A70').replace('delta * actor->unk5CC','delta * phase'))


def native_harness(helper):
    rows=[]
    for c in corpus():
        initial=fixture(c);expected,calls=reference(initial,c)
        row=(c.phase,c.current,c.target,c.flags,c.mode,read(expected,ACTOR+0x5CC),read(expected,ACTOR+0x384),read(expected,ACTOR+0x37C),read(expected,ACTOR+0x240),len(calls))
        rows.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=source.HEADERS+source.DECLARATIONS+'''
static struct108 actual;static u32 calls,error,mode;
f32 D_800A3694,D_800A3698;
typedef union {u32 u;f32 f;} Float;
typedef char phase_offset[__builtin_offsetof(struct108,unk5CC)==0x5CC?1:-1];
typedef char flag_offset[__builtin_offsetof(struct108,unk240)==0x240?1:-1];
typedef char angle_offset[__builtin_offsetof(struct108,unk384)==0x384?1:-1];
typedef char target_offset[__builtin_offsetof(struct108,unk37C)==0x37C?1:-1];
'''+helper.replace('func_15048A70','retained_angle')+'''
__attribute__((noinline,noclone)) f32 func_15048A70(f32 a,f32 b){
 f32 result=retained_angle(a,b);calls++;
 if(mode==1){actual.unk384=-123.25f;actual.unk5CC=.25f;actual.unk37C=720.0f;}
 if(mode==2){actual.unk384=77.0f;actual.unk5CC=-.5f;actual.unk240=(s32)0xA5A50003;}
 return result;
}
'''
    for label,body in controls().items():
        if label!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError('Ineffective control '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    text+='''typedef struct {u32 phase,current,target,flags,mode,outPhase,outAngle,outTarget,outFlags,calls;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef void(*Update)(struct108*);
__attribute__((noinline,noclone)) static void caller(Update fn,struct108*p){fn(p);}
static int variant(Update fn,u32 wrapped){
 u32 i,j;Float f;const Row*r;
 f.u=0x3BC49BA6;D_800A3694=f.f;f.u=0x4479C000;D_800A3698=f.f;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  r=rows+i;for(j=0;j<sizeof(actual);j++)((u8*)&actual)[j]=(u8)(j*13+0xA5);
  f.u=r->phase;actual.unk5CC=f.f;f.u=r->current;actual.unk384=f.f;f.u=r->target;actual.unk37C=f.f;
  actual.unk240=(s32)r->flags;mode=r->mode;calls=error=0;
  if(wrapped)caller(fn,&actual);else fn(&actual);
  f.f=actual.unk5CC;if(f.u!=r->outPhase)return 23;f.f=actual.unk384;if(f.u!=r->outAngle)return 23;
  f.f=actual.unk37C;if(f.u!=r->outTarget)return 23;
  if((u32)actual.unk240!=r->outFlags||calls!=r->calls||error)return 23;
  for(j=0;j<sizeof(actual);j++)if(!((j>=0x240&&j<0x244)||(j>=0x37C&&j<0x380)||(j>=0x384&&j<0x388)||(j>=0x5CC&&j<0x5D0)))
   if(((u8*)&actual)[j]!=(u8)(j*13+0xA5))return 23;
 }return 0;
}
int run(void){
'''
    for index,label in enumerate(controls()):text+='if(variant(%s,0)!=%d)return %d;\n'%(label,0 if label=='selected'else 23,index+1)
    return text+'if(variant(selected,1))return 70;\nreturn 0;}\n'+START,len(rows)


class AngleBlendUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.helper=list(struct.unpack_from('>24I',cls.rom,HELPER-0x15000000+0x2D4B0));cls.parent=list(struct.unpack_from('>58I',cls.rom,PARENT-0x15000000+0x2D4B0))

    def compare(self,c,phase=0,connected=False):
        initial=fixture(c);expected,calls=reference(initial,c)
        code={HELPER+4*i:w for i,w in enumerate(self.helper)}if connected else None
        models=[AngleOracle(w,initial,c,phase,connected=code).run()for w in(self.truth,self.words)]
        for m in models:self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_direct_body_binding_owner_and_real_make(self):
        self.assertEqual(self.words,self.truth);raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(rs,source.BINDINGS);self.assertEqual(source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION),(raw,rs))
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],14)
        self.receipt.update(words=44,frame=24,bindings=5,new_guards=0,compiler_only=True,preserved_neighbors=14)

    def test_02_float32_boundaries_late_reloads_aliases_and_private_home(self):
        count=0;visits=set()
        for c in corpus():
            for phase in(0,8):
                m=self.compare(c,phase);visits.update(m.visits);count+=1
        for alias,mode,phase,progress in itertools.product(range(4),range(4),(0,8),(bits(-.5),bits(.5),bits(1))):
            self.compare(Case(progress,bits(179),bits(-179),0x80000002,mode,alias),phase);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+176,4))-visits,{source.ENTRY+0x44,source.ENTRY+0x78})
        for c in(Case(0x7FC00000,bits(5),bits(2)),Case(0x7F800000,bits(5),bits(2)),Case(0xFF800000,bits(5),bits(2))):
            self.compare(c)
        self.receipt.update(guest_root_phases=count,executable_root_words_visited=42,unreachable_duplicate_words=2,
            guest_alias_layouts=4,private_home_redirection_qualified=True,ordered_nonfinite_model_cases=3,FCSR_or_hardware_claimed=False)

    def test_03_actual_angle_helper_and_one_fold_boundaries(self):
        count=0;visits=set()
        for phase,(current,target)in itertools.product((bits(-1),0,bits(.5),bits(.993),bits(1)),((bits(a),bits(b))for a,b in itertools.product((-1080,-540,-180,-179,0,179,180,540,1080),repeat=2))):
            c=Case(phase,current,target);m=self.compare(c,connected=True);visits.update(m.visits);count+=1
        self.assertEqual(set(range(HELPER,HELPER+96,4))-visits,{HELPER+0x30})
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,HELPER,96)
        self.assertEqual(old[at:at+96],struct.pack('>24I',*self.helper))
        self.receipt.update(retained_helper_words=24,helper_phases=count,helper_reachable_words_visited=23,helper_unreachable_duplicate_words=1)

    def test_04_complete_original_caller_and_provider_mutation(self):
        pointer=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertFalse(any(self.rom[i:i+4]==pointer for i in range(0,len(self.rom),4)))
        sites=(0x1504FC,0x156FD8,0x1595E8)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],list(sites))
        for site,delay,following in ((sites[0],0x02002025,0x0D44A131),
                                    (sites[1],0x02002025,0x920B023C),
                                    (sites[2],0,0x8FBF0014)):
            self.assertEqual(struct.unpack_from('>2I',self.rom,site+4),(delay,following))
        count=0;visits=set()
        for kind,distance,heading,mutate in itertools.product((0,0x40,0x80,0x80000000),(0,41,42,43),(0,180,270),(False,True)):
            c=Case(bits(.5),bits(35),bits(-172),0x80000001);m=fixture(c)
            for at,value in((0x2C,kind),(0x390,bits(heading)),(0x2F8,bits(distance)),(0x2BC,0),(0x300,0),(0x2C4,0)):put(m,ACTOR+at,value)
            expected=dict(m);calls=[]
            if kind not in(0x40,0x80):
                d=bits(math.sqrt(floating(bits(float(distance)*float(distance)))));put(expected,ACTOR+0x370,d)
                if floating(d)<42:
                    put(expected,ACTOR+0x5CC,0);put(expected,ACTOR+0x384,bits(floating(read(expected,ACTOR+0x37C))-(90 if heading<180 else -90)))
                    calls.append((ORIENT,(ACTOR,)))
                    if mutate:
                        put(expected,ACTOR+0x5CC,bits(.995));put(expected,ACTOR+0x384,bits(123));put(expected,ACTOR+0x240,0xA5A50001)
                    put(expected,ACTOR+0x240,read(expected,ACTOR+0x240)|2)
            calls.append((source.ENTRY,(ACTOR,)));expected,more=reference(expected,c);calls+=more;models=[]
            for words in(self.truth,self.words):
                code={source.ENTRY+4*i:w for i,w in enumerate(words)}
                model=AngleOracle(self.parent,m,c,entry=PARENT,connected=code);model.parent_mutation=mutate;model.run()
                self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls);visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertEqual(set(range(PARENT,PARENT+232,4))-visits,{PARENT+0x38})
        self.receipt.update(original_parent_words=58,original_parent_phases=count,
            original_parent_words_visited=len(set(range(PARENT,PARENT+232,4))&visits),orientation_provider_bounded=True,current_parent_stub_uncredited=True,
            direct_call_sites_audited=len(sites),other_two_callers_window_only=True)

    def test_05_native_actual_C_helper_root_typed_caller_and_controls(self):
        text=self.values['conker/src/game_75E60.c'].decode();lo,hi=source.function_span(text,'func_15048A70')
        unit=self.out/'native32.c';harness,count=native_harness(text[lo:hi]);unit.write_text(harness)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=count,native_typed_wrapper_cases_per_optimization=count,
            native_optimizations=['O0','O2','O3'],effective_wrong_C_controls=10,trap_UBSan=True,
            full_typed_struct108_storage=True,actual_angle_helper_C_compiled=True,native_private_alias_or_full_parent_claimed=False)

    def test_06_fired_literal_fault_prefixes(self):
        count=0
        for c in(Case(bits(.5),bits(179),bits(-179),mode=2),Case(bits(1)),Case(bits(.5),bits(179),bits(-179),mode=3)):
            initial=fixture(c);done=AngleOracle(self.words,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for w in(self.truth,self.words):
                    m=AngleOracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(fired_root_access_prefixes=count,complete_private_guest_state_equal=True)

    def test_07_independent_GNU_HI_LO_carries_and_call_rebases(self):
        from tools.experiments.game_actor_classifier_candidates import sections
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_157840.c.o')
        links=count=0
        for index,(entry,step,final,helper)in enumerate(((source.ENTRY,STEP,FINAL,HELPER),(0x18017FFC,0x800A7FFC,0x800A8000,0x18208000),(0x1A028000,0x800AFFFC,0x800B0000,0x1B04FFFC))):
            anchors={'D_800A3694':step,'D_800A3698':final,'func_15048A70':helper};images=[]
            for j,obj in enumerate(objects):
                text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,anchors);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(n,v)for n,v in anchors.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for progress,phase in itertools.product((bits(-1),bits(.5),bits(1)),(0,8)):
                c=Case(progress,bits(179),bits(-179));initial=fixture(c,step,final);expected,calls=reference(initial,c,step,final,helper)
                models=[AngleOracle(w,initial,c,phase,entry=entry,helper=helper).run()for w in images]
                for m in models:self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(complete(m),complete(models[0]))
                count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,independent_HI_LO_carry_boundaries=True)

    def test_08_strict_image_closed_serialization_and_constants(self):
        before=self.values['conker/build/conker.us.elf'];bodies=source.truths(self.values);wanted=source.predicted_image(before,bodies)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),bodies)
        positions=[0,len(wanted)-1,source.elf_slot_offset(before,source.ENTRY,176)]
        rows={name:(at,loc)for at,name,_,loc in source.symbol_rows(before)}
        for name in('D_800A3698','D_8009ED98'):
            at,loc=rows[name];positions.extend((at+4,loc))
        for pos in positions:
            bad=bytearray(wanted);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),bodies)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x248154),(STEP_BITS,FINAL_BITS))
        self.receipt.update(strict_image_negative_controls=len(positions),metadata_exclusions=0,
            serialized_names_reordered=2,named_definitions_preserved_except_target_size=True,guard_file_unchanged=True)
