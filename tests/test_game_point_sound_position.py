"""Point sound positions: signed indexing, float conversion and the real audio setter."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_point_sound_position as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_actor_input_movement_oracle import trunc
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,AUDIO,POINT,SELECTOR=0x20000,0x30000,0x50000,0x60000
HELPER,CALCULATE,PARAMETER=0x1000F91C,0x1000F6B8,0x1000F85C
FINITE=(0,0x80000000,0x3FE00000,0xBFE00000,0x46FFFF80,0x470000C0,0xC70000C0,
        0x477FFF80,0x47800060,0x4EFFFFFF,0xCF000000,1,0x80000001)
GUEST_ONLY=(0x7FC12345,0x7F800000,0xFF800000,0x4F000000,0xCF000001)


def signed(value,n=16):
    return ((value&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))


@dataclass(frozen=True)
class Case:
    active:int=1
    index:int=0
    handle:int=0x8001
    pattern:int=0
    alias:int=0
    mutate:bool=False
    scale:int=32767
    pan:int=231
    invalid:bool=False


def coordinates(case):
    pool=GUEST_ONLY if case.invalid else FINITE
    return tuple(pool[(case.pattern+i*5)%len(pool)]for i in range(3))


def point_address(case,entered):
    return (POINT,entered-32,entered-36,entered-24)[case.alias]


def fixture(t,case,phase=0):
    entered=STACK+phase;point=point_address(case,entered)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base,size in((OWNER,0xA0),(AUDIO,0x140),(POINT,0x40),(SELECTOR,0x80)):
        m.update({base+i:0xA5 for i in range(-16,size+16)})
    m[OWNER+0x2C]=case.active;m[OWNER+0x2D]=case.index
    put(m,OWNER+0x94,(point-signed(case.index,8)*t['stride'])&0xFFFFFFFF);put(m,OWNER+0x98,AUDIO)
    put(m,AUDIO+t['handle'],case.handle,2)
    for i,word in enumerate(coordinates(case)):put(m,point+4*i,word)
    return m


def effects(memory,t,case):
    if case.mutate:
        memory[OWNER+0x2C]=0;memory[OWNER+0x2D]=(case.index+1)&255
        put(memory,AUDIO+t['handle'],0,2)


def reference(initial,t,case,entered=STACK,helper=HELPER,chain=False):
    m=dict(initial);calls=[]
    if case.active and case.handle:
        put(m,entered-32,0)
        point=point_address(case,entered);values=[]
        for i in range(3):
            value=trunc(floating(read(m,point+4*i)));values.append(value)
            if i<2:put(m,entered-28+4*i,value)
        put(m,entered-12,5000);put(m,entered-16,500);put(m,entered-20,values[2])
        args=(case.handle,32767,0,0,0,*values,500,5000);calls.append((helper,args))
        if chain:
            for i,value in enumerate(args[:4]):put(m,entered-48+4*i,value)
            calls.append((CALCULATE,(0,*(signed(v)&0xFFFFFFFF for v in values),'pan-out',500,5000)))
            calls.extend((PARAMETER,(case.handle,command,value))for command,value in
                ((8,((case.scale*32767)&0xFFFFFFFF)>>15),(4,case.pan&127),(256,case.pan&128),(16,0)))
        else:
            for i in range(4):put(m,entered-48+4*i,0xB5000000+i)
        effects(m,t,case)
    return m,calls


def public(memory,case,entered):
    point=point_address(case,entered)
    return {a:b for a,b in memory.items()if not STACK-1024<=a<STACK+1024 or point<=a<point+12}


class SoundOracle(RayOracle):
    def __init__(self,words,memory,t,case=Case(),phase=0,entry=None,helper=HELPER,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=t['entry']if entry is None else entry,
                             arguments=(OWNER,),connected=connected)
        self.t=t;self.case=case;self.entered=STACK+phase;self.helper=helper;self.root_args=None

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            self.f[word>>6&31]=trunc(floating(self.f[word>>11&31]));self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        if target==self.t['entry']:self.entered=self.r[29];args=self.arguments(1)
        elif target==self.helper:self.root_args=self.arguments(10);args=self.root_args
        elif target==CALCULATE:
            raw=self.arguments(7);self.pan_out=raw[4]
            assert self.pan_out==self.r[29]+44,('Unexpected original helper output home',raw)
            args=(*raw[:4],'pan-out',*raw[5:])
        elif target==PARAMETER:args=self.arguments(3)
        else:raise AssertionError(('Unbounded point-sound service',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target==CALCULATE:
            self.put(self.pan_out,self.case.pan,4);value=self.case.scale&0xFFFFFFFF
            effects(self.memory,self.t,self.case)
        else:
            assert target in(self.helper,PARAMETER)
            if target==self.helper:effects(self.memory,self.t,self.case)
            value=0xA5000002
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.end:raise WindowBoundary
        return super().__getitem__(pc)


def controls(name):
    b=source.SELECTED[name];t=source.TARGETS[name]
    return dict(selected=b,
        unsigned_index=b.replace('points[state->index]','points[(u8)state->index]'),
        next_index=b.replace('points[state->index]','points[(s8)(state->index + 1)]'),
        positive_only=b.replace('state->active != 0','state->active > 0'),
        inverted_handle=b.replace('handle != 0','handle == 0'),
        wrong_handle=b.replace('audio + 0x%X'%t['handle'],'audio + 0x%X'%(t['handle']+2)),
        wrong_volume=b.replace('handle, 0x7FFF','handle, 0x7FFE'),
        wrong_x=b.replace('(s32)points[state->index].x','(s32)points[state->index].y'),
        zero_z=b.replace('(s32)points[state->index].z','0'),
        low_byte_x=b.replace('(s32)points[state->index].x','(u8)(s32)points[state->index].x'),
        wrong_near=b.replace(', 500, 5000',', 501, 5000'),
        wrong_far=b.replace(', 500, 5000',', 500, 4999'),
        wrong_context=b.replace('handle, 0x7FFF, 0, 0, 0','handle, 0x7FFF, 0, 0, 1'))


def native_harness(values):
    init=values['conker/src/init_EB00.c'].decode();helper=init[slice(*source.function_span(init,'func_1000F91C'))]
    text=source.HEADERS+source.DECLARATIONS+r'''
typedef char stride36[sizeof(SoundPoint36)==36?1:-1];typedef char stride40[sizeof(SoundPoint40)==40?1:-1];
typedef char owner_size[sizeof(PointSoundOwner)==0x9C?1:-1];
typedef char points_offset[__builtin_offsetof(PointSoundOwner,points)==0x94?1:-1];
typedef char audio_offset[__builtin_offsetof(PointSoundOwner,audio)==0x98?1:-1];
static SoundPoint36 p36[512];static SoundPoint40 p40[512];static PointSoundOwner state;
static u8 *audio;static u32 error,calculateCalls,messages,wantCall,wantedHandle,handleOffset,mutate,attenuation,pan;
static s32 wanted[3];
static f32 real(u32 word){union {u32 u;f32 f;}v;v.u=word;return v.f;}
static s32 narrowed(f32 f){return(s16)(s32)f;}
__attribute__((noinline,noclone)) s32 func_1000F6B8(s32 context,s16 x,s16 y,s16 z,void *out,s16 nearValue,s16 farValue){
 if(!wantCall||calculateCalls++||context||x!=wanted[0]||y!=wanted[1]||z!=wanted[2]||nearValue!=500||farValue!=5000)error=1;
 *(s32*)out=(s32)pan;
 if(mutate){state.active=0;state.index=(s8)(state.index+1);*(u16*)(audio+handleOffset)=0;}
 return(s32)attenuation;
}
__attribute__((noinline,noclone)) void func_1000F85C(u16 handle,s16 command,s32 value){
 static const s16 commands[]={8,4,256,16};u32 expected[4];
 expected[0]=(attenuation*32767u)>>15;expected[1]=pan&127;expected[2]=pan&128;expected[3]=0;
 if(messages>=4||handle!=wantedHandle||command!=commands[messages]||(u32)value!=expected[messages])error=1;
 messages++;
}
'''+helper+'\n'
    for name in source.FUNCTIONS:
        for label,body in controls(name).items():
            if label!='selected'and body==source.SELECTED[name]:raise ValueError('Ineffective control '+label)
            text+=body.replace(name,name+'_'+label)+'\n'
    text+=r'''
static const u32 floats[]={FLOATS};
typedef void(*Refresh)(PointSoundOwner *);
static int one(Refresh fn,u32 stride,u32 offset,u32 active,u32 index,u32 handle,u32 mutation){
 u32 i;u8 before[sizeof(state)],beforeAudio[0x140];u32 slot=128+(u32)(s32)(s8)index;
 for(i=0;i<sizeof(state);i++)((u8*)&state)[i]=0xA5;
 for(i=0;i<0x140;i++)audio[i]=0xA5;
 state.active=(s8)active;state.index=(s8)index;state.audio=audio;
 state.points=stride==36?(void*)(p36+128):(void*)(p40+128);
 *(u16*)(audio+offset)=(u16)handle;*(u16*)(audio+offset+2)=0x41A7;
 wanted[0]=narrowed(stride==36?p36[slot].x:p40[slot].x);
 wanted[1]=narrowed(stride==36?p36[slot].y:p40[slot].y);
 wanted[2]=narrowed(stride==36?p36[slot].z:p40[slot].z);
 for(i=0;i<sizeof(state);i++)before[i]=((u8*)&state)[i];
 for(i=0;i<0x140;i++)beforeAudio[i]=audio[i];
 error=calculateCalls=messages=0;wantCall=active!=0&&handle!=0;wantedHandle=handle;handleOffset=offset;mutate=mutation;
 attenuation=(u32[]){0,1,16384,32767}[index&3];pan=(u32[]){0,127,128,231}[active&3];
 fn(&state);
 if(error||calculateCalls!=wantCall||messages!=(wantCall?4u:0u))return 23;
 if(wantCall&&mutate){before[0x2C]=0;before[0x2D]=(u8)(index+1);beforeAudio[offset]=beforeAudio[offset+1]=0;}
 for(i=0;i<sizeof(state);i++)if(((u8*)&state)[i]!=before[i])return 23;
 for(i=0;i<0x140;i++)if(audio[i]!=beforeAudio[i])return 23;
 return 0;
}
static int variant(Refresh fn,u32 stride,u32 offset,u32 full){
 u32 a,i,h,m;static const u16 handles[]={0,1,32768,65535};static const u8 active[]={0,1,128,255};
 for(a=0;a<(full?256u:4u);a++)for(i=0;i<256;i++)for(h=0;h<4;h++)for(m=0;m<2;m++)
  if(one(fn,stride,offset,full?a:active[a],i,handles[h],m))return 23;
 return 0;
}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 i;audio=allocate(0x140);if(!audio)return 97;
 for(i=0;i<512;i++){
  u32 j;for(j=0;j<24;j++)p36[i].opaque[j]=0xA5;for(j=0;j<28;j++)p40[i].opaque[j]=0xA5;
  p36[i].x=p40[i].x=real(floats[i%13]);p36[i].y=p40[i].y=real(floats[(i+5)%13]);p36[i].z=p40[i].z=real(floats[(i+10)%13]);
 }
'''.replace('FLOATS',','.join('0x%Xu'%x for x in FINITE))
    for name,t in source.TARGETS.items():
        for control_index,label in enumerate(controls(name)):
            text+='if(variant(%s_%s,%d,%d,%d)!=%d)return %d;\n'%(name,label,t['stride'],t['handle'],int(label=='selected'),0 if label=='selected'else 23,11 if label=='selected'else 40+control_index)
        text+='''state.active=0;state.index=-128;state.audio=0;state.points=0;calculateCalls=messages=0;NAME_selected(&state);if(calculateCalls||messages)return 21;
 state.active=1;state.audio=audio;*(u16*)(audio+OFFSET)=0;NAME_selected(&state);if(calculateCalls||messages)return 22;
'''.replace('NAME',name).replace('OFFSET',str(t['handle']))
    return text+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')


class PointSoundPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.words={n:list(struct.unpack_from('>44I',data,fs[n]['value']))for n in source.FUNCTIONS}
        cls.truth={n:list(struct.unpack_from('>44I',cls.rom,t['rom']))for n,t in source.TARGETS.items()}
        cls.helper=list(struct.unpack_from('>46I',cls.rom,0xF91C));cls.receipt={}

    def compare(self,name,case,phase=0,chain=False,images=None,entry=None,helper=HELPER):
        t=source.TARGETS[name];memory=fixture(t,case,phase);expected,calls=reference(memory,t,case,STACK+phase,helper,chain)
        connected=dict(zip(range(HELPER,HELPER+184,4),self.helper))if chain else None
        models=[SoundOracle(words,memory,t,case,phase,entry,helper,connected).run()for words in(images or(self.truth[name],self.words[name]))]
        for m in models:self.assertEqual(public(m.memory,case,STACK+phase),public(expected,case,STACK+phase));self.assertEqual(m.calls,calls)
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
        return models[0]

    def test_01_direct_words_bindings_owner_and_actual_Make(self):
        for name in source.FUNCTIONS:
            self.assertEqual(self.words[name],self.truth[name]);self.assertEqual(self.words[name][0],0x27BDFFD0)
            self.assertEqual(source.payload(self.out/'after-owner.o',name),source.payload(source.original(ROOT,self.out,name),name))
            self.assertEqual(source.payload(self.out/'after-owner.o',name)[1],{152:[('R_MIPS_26','func_1000F91C')]})
            old,fs=source.link_owner(ROOT,self.out,self.out/'before-owner.o',source.OWNER)
            self.assertNotEqual(list(struct.unpack_from('>44I',old,fs[name]['value'])),self.truth[name])
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],67)
        self.assertTrue(json.loads((self.out/'make-shadow.json').read_text())[0]['complete_padded_object_equal'])
        self.receipt.update(functions=2,total_words=88,frame_each=48,bindings_each=1,new_guards=0,compiler_only=True,preserved_neighbors=67)

    def test_02_guest_bytes_float_domain_ordered_aliases_and_ignored_pointees(self):
        phases=alias_phases=invalid=0
        for name,t in source.TARGETS.items():
            visits=set()
            for active,index,handle,phase in itertools.product((0,1,128,255),range(256),(0,1,65535),(0,8)):
                c=Case(active,index,handle,index%13,mutate=bool(index&1));m=self.compare(name,c,phase);visits.update(m.visits);phases+=1
            for active,phase in itertools.product(range(256),(0,8)):
                self.compare(name,Case(active,255,32768,5),phase);phases+=1
            for pattern,alias,mutate,phase in itertools.product(range(13),range(4),(False,True),(0,8)):
                self.compare(name,Case(255,128,65535,pattern,alias,mutate),phase);alias_phases+=1
            for pattern,phase in itertools.product(range(5),(0,8)):
                self.compare(name,Case(1,0,1,pattern,invalid=True),phase);invalid+=1
            for active,handle in((0,1),(1,0)):
                c=Case(active,0,handle);memory=fixture(t,c);put(memory,OWNER+0x94,0)
                if not active:put(memory,OWNER+0x98,0)
                models=[SoundOracle(w,memory,t,c).run()for w in(self.truth[name],self.words[name])]
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertFalse(models[0].calls)
            self.assertTrue(set(range(t['entry'],t['entry']+176,4))<=visits)
        self.receipt.update(guest_phases=phases,guest_alias_phases=alias_phases,guest_invalid_FP_model_phases=invalid,
            all_88_root_words_visited=True,ignored_unmapped_pointees=True,portable_C_alias_or_invalid_conversion_claimed=False)

    def test_03_native_real_helper_C_and_twelve_defined_controls_each(self):
        c=self.out/'native.c';c.write_text(native_harness(self.values))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(c),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),p.stdout+p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),opt)
        self.receipt.update(native_selected_cases_per_optimization=2*256*256*4*2,native_optimizations=3,
            trap_UBSan=True,defined_wrong_C_controls_each=12,real_audio_helper_C=True,native_complete_typed_points_and_owner=True,
            native_finite_representable_conversions_only=True)

    def test_04_actual_registration_and_original_selector_windows(self):
        phases=0
        for name,t in source.TARGETS.items():
            ptr=struct.pack('>I',t['entry']);jal=struct.pack('>I',0x0C000000|(t['entry']>>2&0x3FFFFFF))
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[t['table_rom']])
            self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],t['table'],4)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+4],ptr)
            n=(t['end']-t['window'])//4;code=list(struct.unpack_from('>%dI'%n,self.rom,t['window']-0x15000000+0x2D4B0))
            for selector,active,handle,phase in itertools.product((0,255),(0,1,255),(0,65535),(0,8)):
                c=Case(active,128,handle,9);memory=fixture(t,c,phase);put(memory,t['table'],t['entry'])
                memory[AUDIO+0x64]=selector;memory[SELECTOR+0x38]=selector;models=[]
                for words in(self.truth[name],self.words[name]):
                    connected=dict(zip(range(t['entry'],t['entry']+176,4),words))
                    m=SoundOracle(code,memory,t,c,phase,t['window'],connected=connected)
                    m.r[16]=OWNER;m.r[19]=OWNER;m.r[20]=SELECTOR;m.r[7]=AUDIO;m.r[10]=0x12345678
                    m.code[t['end']]=0;m.code=WindowCode(m.code,m);m.code.end=t['end']
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual([a for target,a in m.calls if target==t['entry']],[(OWNER,)]if selector==0 else[]);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(original_caller_windows=2,caller_window_phases=phases,registered_index_zero_and_signed_disable=True,
            full_parent_or_unproven_table_extent_claimed=False)

    def test_05_connected_original_and_live_audio_setter(self):
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,HELPER,184)
        self.assertEqual(old[at:at+184],self.rom[0xF91C:0xF9D4]);visits=set();phases=0
        for name in source.FUNCTIONS:
            for index,pattern,scale,pan,mutate,phase in itertools.product((0,128,255),(0,5,9),(0,1,16384,32767,0x7FFFFFFF),(0,127,128,0xABCD00E7),(False,True),(0,8)):
                m=self.compare(name,Case(1,index,65535,pattern,mutate=mutate,scale=scale,pan=pan),phase,True);visits.update(m.visits);phases+=1
        self.assertTrue(set(range(HELPER,HELPER+184,4))<=visits)
        self.receipt.update(retained_helper_words=46,helper_phases=phases,all_46_helper_words_visited=True,
            attenuation_and_parameter_backends_bounded=True,full_audio_or_hardware_acceptance_claimed=False)

    def linked(self,name,obj,entry,helper,label):
        text,functions,bindings=source.parse_object(obj);asm,unknown=emit_function(text,functions[name],bindings,name,{'func_1000F91C':helper});self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',name,
            '--defsym=func_1000F91C=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_06_independent_GNU_rebases_and_root_fault_prefixes(self):
        links=phases=cuts=0
        for name,t in source.TARGETS.items():
            objects=(source.original(ROOT,self.out,name),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_1C2C60.c.o')
            for i,(entry,helper)in enumerate(((t['entry'],HELPER),(0x18017FFC,0x18208000),(0x1A028000,0x1B04FFFC))):
                images=[self.linked(name,obj,entry,helper,'rebase-'+name+'-%d-%d'%(i,j))for j,obj in enumerate(objects)]
                self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);links+=3
                for index,alias,phase in itertools.product((0,128,255),range(4),(0,8)):
                    self.compare(name,Case(1,index,32768,9,alias),phase,images=images,entry=entry,helper=helper);phases+=1
            for active,handle,alias,phase in itertools.product((0,1),(0,65535),range(4),(0,8)):
                c=Case(active,128,handle,5,alias);memory=fixture(t,c,phase);done=SoundOracle(self.truth[name],memory,t,c,phase).run()
                for cut in range(done.root_accesses):
                    models=[SoundOracle(w,memory,t,c,phase)for w in(self.truth[name],self.words[name])]
                    for m in models:
                        m.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_claimed=False)

    def test_07_strict_image_and_body_corruptions(self):
        old=self.values['conker/build/conker.us.elf'];truths=source.truths(self.values);wanted=source.predicted_image(old,truths)
        positions=[0,len(wanted)-1,source.elf_slot_offset(old,HELPER,4),source.elf_slot_offset(old,0x80082B20,4)]
        positions.extend(source.elf_slot_offset(old,t['entry'],176)for t in source.TARGETS.values())
        positions.extend(at+8 for at,name,_,_ in source.symbol_rows(old)if name in source.FUNCTIONS)
        for pos in positions:
            wrong=bytearray(wanted);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(wrong),truths)
        with self.assertRaises(ValueError):source.check_image(old,wanted[:-1],truths)
        bad=dict(truths);bad[source.FUNCTIONS[0]]=bytes(176)
        with self.assertRaises(ValueError):source.predicted_image(old,bad)
        self.receipt.update(strict_image_negatives=len(positions)+2,metadata_exclusions=0)

    def test_08_frozen_inputs_guard_history_and_installed_identity(self):
        source.check_inputs(ROOT,self.out,self.installed)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(focused_inputs=28,guard_manifest_byte_identical=True,installed=self.installed)


if __name__=='__main__':unittest.main()
