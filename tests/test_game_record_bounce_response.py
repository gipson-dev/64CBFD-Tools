"""Literal collision response, float thresholds, original dispatcher and closed image."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_record_bounce_response as source
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
RECORD,SURFACE,POINT,RESPONSE=0x30000,0x32000,0x34000,0x36000
SCALE,THRESHOLD,TABLE,PARENT,QUERY,MOVE=0x800A3848,0x800A384C,0x80089874,0x151319C4,0x1514672C,0x15046C80
SCALE_BITS,THRESHOLD_BITS=0x3D75C290,0x3FFF9DB3


@dataclass(frozen=True)
class Case:
    vy:int=0x40800000
    damping:int=0x3F000000
    flags:int=0x80000007
    response_flags:int=0xFF
    layout:int=0
    extent:int=0x42A00000
    height:int=0xC1200000


def locations(c,scale=SCALE,threshold=THRESHOLD):
    return ((RECORD,RESPONSE,POINT),(RECORD,RECORD+0x54,POINT),
        (RECORD,RECORD+0x58,POINT),(RECORD,RECORD+0x5C,POINT),
        (RECORD,RECORD+0x68,POINT),(RECORD,RESPONSE,RECORD+0x40),
        (scale-0x58,RESPONSE,POINT),(threshold-0x60,RESPONSE,POINT))[c.layout]


def fixture(c,scale=SCALE,threshold=THRESHOLD):
    owner,response,point=locations(c,scale,threshold)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,size in((owner,0x100),(response,8),(point,12),(SURFACE,12)):
        m.update({base+i:(i*13+0xA5)&255 for i in range(size)})
    put(m,scale,SCALE_BITS);put(m,threshold,THRESHOLD_BITS)
    for at,value in((0x3C,c.extent),(0x40,bits(17)),(0x44,bits(-20)),(0x48,bits(23)),
                    (0x58,bits(13)),(0x5C,c.vy),(0x60,bits(-29)),(0x64,bits(71)),(0x68,c.flags),(0x80,bits(3))):put(m,owner+at,value)
    for i,value in enumerate((bits(19),c.height,bits(-37))):put(m,point+4*i,value)
    m[response]=c.response_flags;m[response+1]=0;put(m,response+4,c.damping)
    put(m,SURFACE+4,bits(100))
    return m


def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def vector(m,p):return tuple(read(m,p+4*i)for i in range(3))
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}


def reference(initial,c,scale=SCALE,threshold=THRESHOLD,point=None):
    m=dict(initial);owner,response,default=locations(c,scale,threshold);point=default if point is None else point
    height=add(read(m,point+4),mul(read(m,owner+0x3C),read(m,scale)))
    vx,vy=read(m,owner+0x58),read(m,owner+0x5C);put(m,owner+0x44,height)
    first=read(m,response+4);vz=read(m,owner+0x60);put(m,owner+0x58,mul(vx,first))
    put(m,owner+0x5C,mul(vy,read(m,response+4)^0x80000000))
    third=read(m,response+4);vertical=read(m,owner+0x5C);put(m,owner+0x60,mul(vz,third))
    if floating(vertical&0x7FFFFFFF)<floating(read(m,threshold)):
        for at in(0x58,0x5C,0x60,0x64):put(m,owner+at,0)
        m[response]&=0xFE;put(m,owner+0x68,read(m,owner+0x68)&0xFFFFFFF9)
    return m


class BounceOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None):
        owner,response,point=locations(c)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(owner,SURFACE,point,response),connected=connected)
        self.case=c;self.query_result=self.move_result=1;self.provider_mutation=False

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63 in(5,7):
            self.dispatched_word=word;self.own_instruction=True
            try:
                value=self.f[word>>11&31]
                self.f[word>>6&31]=value&0x7FFFFFFF if word&63==5 else value^0x80000000
            finally:self.own_instruction=False
        else:super().execute(word)

    def record_call(self,target):
        if target==QUERY:args=(vector(self.memory,self.r[4]),)
        elif target==MOVE:args=(vector(self.memory,self.r[4]),*self.arguments(4)[1:])
        else:
            assert target==source.ENTRY,('unbounded bounce provider',hex(target))
            args=(self.r[4],self.r[5],vector(self.memory,self.r[6]),self.r[7])
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target in(QUERY,MOVE)
        point=self.r[4]
        if target==QUERY:
            value=self.query_result
            if self.provider_mutation:
                put(self.memory,point,add(read(self.memory,point),bits(3)))
                put(self.memory,point+8,add(read(self.memory,point+8),bits(-7)))
                put(self.memory,RECORD+0x3C,bits(40));put(self.memory,RESPONSE+4,bits(.25))
        else:
            value=self.move_result;put(self.memory,self.r[7],add(self.r[6],bits(2 if self.provider_mutation else 0)))
            if self.provider_mutation:put(self.memory,point+8,bits(91))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value
        self.hi,self.lo=0x87654321,0x12345678


def corpus():
    t=THRESHOLD_BITS
    vertical=(0,0x80000000,1,0x80000001,bits(-10),bits(10),t-1,t,t+1,(t-1)^0x80000000,t^0x80000000,(t+1)^0x80000000,bits(-3.994),bits(3.994))
    for vy,damping,flags,byte in itertools.product(vertical,map(bits,(0,-0.0,.25,.5,1,-1,2,-2)),(0,6,0x80000007,0xFFFFFFFF),(0,1,0xFE,0xFF)):
        yield Case(vy,damping,flags,byte)


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,wrong_extent=b.replace('D_800A3848','0.6f'),wrong_point=b.replace('point[1]','point[0]'),
        no_reflection=b.replace('-response->damping','response->damping'),wrong_comparison=b.replace('< D_800A384C','<= D_800A384C'),
        no_absolute=b.replace('fabsf(record->velocity[1])','record->velocity[1]'),wrong_threshold=b.replace('D_800A384C','2.0f'),
        no_acceleration_clear=b.replace('        record->verticalAcceleration = 0.0f;',''),wrong_response_mask=b.replace('~1','~2'),
        wrong_motion_mask=b.replace('~6','~4'),wrong_return=b.replace('return 1;','return 0;'))


def native_harness():
    rows=[]
    for c in corpus():
        m=reference(fixture(c),c)
        values=(c.vy,c.damping,c.flags,c.response_flags,c.extent,c.height,
                *(read(m,RECORD+x)for x in(0x44,0x58,0x5C,0x60,0x64,0x68)),m[RESPONSE])
        rows.append('{'+','.join('0x%Xu'%x for x in values)+'}')
    text=source.HEADERS+source.DECLARATIONS+'''
typedef union {u32 u;f32 f;} Float;
f32 D_800A3848,D_800A384C;
f32 fabsf(f32 x){return __builtin_fabsf(x);}
typedef char height_offset[__builtin_offsetof(BounceRecord15D730,position[1])==0x44?1:-1];
typedef char velocity_offset[__builtin_offsetof(BounceRecord15D730,velocity)==0x58?1:-1];
typedef char flags_offset[__builtin_offsetof(BounceRecord15D730,flags)==0x68?1:-1];
typedef char response_offset[__builtin_offsetof(BounceResponse15D730,damping)==4?1:-1];
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError(name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef struct {u32 vy,damping,flags,byte,extent,height,y,vx,outVy,vz,acceleration,outFlags,outByte;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef s32(*Callback)(BounceRecord15D730*,void*,f32*,BounceResponse15D730*);
__attribute__((noinline,noclone)) static s32 caller(Callback fn,BounceRecord15D730*r,void*s,f32*p,BounceResponse15D730*b){return fn(r,s,p,b);}
static int variant(Callback fn,u32 wrapped){
 u32 i,j;Float f;BounceRecord15D730 r;BounceResponse15D730 b;f32 p[3],s[3];const Row*v;s32 result;
 f.u=0x3D75C290;D_800A3848=f.f;f.u=0x3FFF9DB3;D_800A384C=f.f;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  v=rows+i;for(j=0;j<sizeof(r);j++)((u8*)&r)[j]=(u8)(j*13+0xA5);
  for(j=0;j<sizeof(b);j++)((u8*)&b)[j]=(u8)(j*13+0xA5);
  f.u=v->extent;r.extent=f.f;r.velocity[0]=13;r.velocity[2]=-29;r.verticalAcceleration=71;
  f.u=v->vy;r.velocity[1]=f.f;r.flags=v->flags;f.u=v->damping;b.damping=f.f;b.flags=v->byte;b.kind=0;
  p[0]=19;f.u=v->height;p[1]=f.f;p[2]=-37;s[0]=31;s[1]=100;s[2]=-47;
  result=wrapped?caller(fn,&r,s,p,&b):fn(&r,s,p,&b);if(result!=1)return 23;
  f.f=r.position[1];if(f.u!=v->y)return 23;f.f=r.velocity[0];if(f.u!=v->vx)return 23;
  f.f=r.velocity[1];if(f.u!=v->outVy)return 23;f.f=r.velocity[2];if(f.u!=v->vz)return 23;
  f.f=r.verticalAcceleration;if(f.u!=v->acceleration||r.flags!=v->outFlags||b.flags!=v->outByte)return 23;
  f.f=r.extent;if(f.u!=v->extent)return 23;
  f.f=b.damping;if(f.u!=v->damping||b.kind||b.reserved[0]!=(u8)(2*13+0xA5)||b.reserved[1]!=(u8)(3*13+0xA5))return 23;
  f.f=p[1];if(p[0]!=19||f.u!=v->height||p[2]!=-37||s[0]!=31||s[1]!=100||s[2]!=-47)return 23;
  for(j=0;j<sizeof(r);j++)if(!((j>=0x3C&&j<0x40)||(j>=0x44&&j<0x48)||(j>=0x58&&j<0x6C)))
   if(((u8*)&r)[j]!=(u8)(j*13+0xA5))return 23;
 }return 0;
}
int run(void){
'''
    for index,label in enumerate(controls()):text+='if(variant(%s,0)!=%d)return %d;\n'%(label,0 if label=='selected'else 23,index+1)
    return text+'if(variant(selected,1))return 70;\nreturn 0;}\n'+START,len(rows)


class BounceResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.parent=list(struct.unpack_from('>78I',cls.rom,0x15EE74))

    def compare(self,c,phase=0):
        initial=fixture(c);expected=reference(initial,c)
        models=[BounceOracle(w,initial,c,phase).run()for w in(self.truth,self.words)]
        for m in models:self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.r[2],1);self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_direct_body_binding_owner_and_real_make(self):
        self.assertEqual(self.words,self.truth);raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(rs,source.BINDINGS);self.assertEqual(source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION),(raw,rs))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],30)
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())[0]['actual_Make_commands'],5)
        self.receipt.update(words=44,frame=0,bindings=4,new_guards=0,compiler_only=True,preserved_neighbors=30,actual_Make_commands=5)

    def test_02_float_boundaries_ordered_aliases_and_all_flag_bytes(self):
        count=0;visits=set()
        for c in corpus():
            for phase in(0,8):m=self.compare(c,phase);visits.update(m.visits);count+=1
        for layout,byte,vy,damping in itertools.product(range(8),range(256),(bits(1),bits(4)),(bits(.5),bits(1))):
            self.compare(Case(vy,damping,response_flags=byte,layout=layout));count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+176,4))-visits,set())
        for c in(Case(0x7FC00000),Case(0x7F800000),Case(0xFF800000)):self.compare(c)
        self.receipt.update(guest_root_phases=count,root_words_visited=44,guest_alias_layouts=8,
            all_response_flag_bytes=True,ordered_nonfinite_model_cases=3,FCSR_or_hardware_claimed=False)

    def test_03_original_dispatcher_table_gates_and_provider_mutations(self):
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)],[0x22E334])
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        count=0;visits=set()
        for kind,active,present,below,query,move,mutate,phase in itertools.product((-128,-1,0,1,127),(False,True),(False,True),(False,True),(0,1),(0,1),(False,True),(0,8)):
            c=Case();initial=fixture(c);initial[RESPONSE]=int(active);initial[RESPONSE+1]=kind&255
            for i in range(-128,128):put(initial,TABLE+4*i,source.ENTRY if present else 0)
            put(initial,0x800A3844,SCALE_BITS);put(initial,SURFACE+4,bits(100 if below else -100))
            expected=dict(initial);calls=[];result=1
            if active and kind!=-1 and present and below:
                v=[read(expected,RECORD+0x40),read(expected,SURFACE+4),read(expected,RECORD+0x48)]
                calls.append((QUERY,(tuple(v),)))
                if mutate:
                    v[0]=add(v[0],bits(3));v[2]=add(v[2],bits(-7));put(expected,RECORD+0x3C,bits(40));put(expected,RESPONSE+4,bits(.25))
                if not query:result=0
                else:
                    y=bits(floating(read(expected,RECORD+0x44))-floating(mul(read(expected,RECORD+0x3C),SCALE_BITS)))
                    calls.append((MOVE,(tuple(v),0,y,RECORD+0x80)))
                    put(expected,RECORD+0x80,add(y,bits(2 if mutate else 0)))
                    if mutate:v[2]=bits(91)
                    if move:
                        point=(v[0],read(expected,RECORD+0x80),v[2]);calls.append((source.ENTRY,(RECORD,SURFACE,point,RESPONSE)))
                        for i,x in enumerate(point):put(expected,POINT+4*i,x)
                        expected=reference(expected,c)
                        for i in range(12):expected[POINT+i]=initial[POINT+i]
            models=[]
            for words in(self.truth,self.words):
                code={source.ENTRY+4*i:w for i,w in enumerate(words)}
                m=BounceOracle(self.parent,initial,c,phase,entry=PARENT,connected=code,arguments=(RECORD,SURFACE,RESPONSE))
                m.query_result=query;m.move_result=move;m.provider_mutation=mutate;m.run();models.append(m);visits.update(m.visits)
                self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertEqual(set(range(PARENT,PARENT+312,4))-visits,set())
        self.receipt.update(original_parent_words=78,original_parent_phases=count,
            original_parent_words_visited=len(set(range(PARENT,PARENT+312,4))&visits),query_and_move_bounded=True,
            actual_callback_slot_zero_verified=True,other_signed_selector_entries_controlled=True,current_parent_stub_uncredited=True)

    def test_04_native_actual_C_typed_callback_and_negative_controls(self):
        text,count=native_harness();unit=self.out/'native32.c';unit.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=count,native_typed_callback_cases_per_optimization=count,
            native_optimizations=['O0','O2','O3'],effective_wrong_C_controls=10,trap_UBSan=True,
            full_typed_storage=True,native_alias_or_full_parent_claimed=False)

    def test_05_fired_literal_fault_prefixes_and_unused_surface(self):
        count=0
        for c in(Case(),Case(bits(1)),Case(bits(4),layout=1),Case(bits(1),layout=4)):
            initial=fixture(c);done=BounceOracle(self.words,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.truth,self.words):
                    m=BounceOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for arg in(0,0xFFFFFFFF,0x80000000):
            c=Case();owner,response,point=locations(c)
            a=BounceOracle(self.truth,fixture(c),arguments=(owner,arg,point,response)).run()
            b=BounceOracle(self.words,fixture(c),arguments=(owner,arg,point,response)).run()
            self.assertEqual(complete(a),complete(b));self.assertEqual(a.r[2],1)
        self.receipt.update(fired_root_access_prefixes=count,unused_surface_words_qualified=3,complete_private_state_equal=True)

    def test_06_independent_GNU_constant_carries_and_code_rebases(self):
        from tools.experiments.game_actor_classifier_candidates import sections
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_15D730.c.o')
        links=count=0
        for index,(entry,scale,threshold)in enumerate(((source.ENTRY,SCALE,THRESHOLD),(0x18017FFC,0x800A7FFC,0x800A8000),(0x1A028000,0x800AFFFC,0x800B0000))):
            values=[]
            for k,obj in enumerate(objects):
                text,fs,rs=source.parse_object(obj)
                anchors=dict(D_800A3848=scale,D_800A384C=threshold)
                assembly=self.out/('rebase-%d-%d.s'%(index,k))
                asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,anchors)
                self.assertFalse(unknown);assembly.write_text(asm)
                out=assembly.with_suffix('.o');elf=assembly.with_suffix('.elf');script=assembly.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(out),str(assembly)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800A3848=0x%X'%scale,'--defsym=D_800A384C=0x%X'%threshold,'-o',str(elf),str(out)],capture_output=True,check=True)
                values.append(list(struct.unpack('>44I',sections(elf)['.text'][1][:176])));links+=1
            self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for vy,phase in itertools.product((bits(1),bits(4),THRESHOLD_BITS,bits(-4)),(0,8)):
                c=Case(vy,bits(1));initial=fixture(c,scale,threshold);expected=reference(initial,c,scale,threshold)
                models=[BounceOracle(w,initial,c,phase,entry=entry).run()for w in values]
                for m in models:self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],1)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,HI_LO_carry_boundaries=True)

    def test_07_strict_whole_image_and_closed_serialization_negatives(self):
        before=self.values['conker/build/conker.us.elf'];bodies=source.truths(self.values);expected=source.predicted_image(before,bodies)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),bodies)
        positions=[0,len(expected)-1,source.elf_slot_offset(before,source.ENTRY,176)]
        for at,name,fields,location in source.symbol_rows(before):
            if name in('D_800A3848','D_80095B48','D_800A0BD0','D_8009E810'):positions.extend((at+4,location))
        for at in positions:
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),bodies)
        self.receipt.update(strict_image_negative_controls=len(positions),serialized_names_reordered=4,
            named_definitions_preserved_except_target_size=True,metadata_exclusions=0)

    def test_08_original_constants_guard_and_callback_table_unchanged(self):
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x248308),(SCALE_BITS,THRESHOLD_BITS))
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,TABLE,4)
        self.assertEqual(before[at:at+4],self.rom[0x22E334:0x22E338])
        guard='conker/retail_word_patches.us.csv';self.assertEqual((ROOT/guard).read_bytes(),self.values[guard])
        self.assertEqual(source.digest(self.values[guard]),'6d19dfd5806dedfc839f6c7e33f8fb2d1123d826021b93505bd7a265e516f427')
        self.receipt.update(original_constant_bits_preserved=True,whole_guard_CSV_unchanged=True)
