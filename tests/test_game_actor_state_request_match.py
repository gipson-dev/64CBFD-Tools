"""Actor-state request: direct C, lazy gates, real callers and literal image checks."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_actor_state_request_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
ENTRY=0x1512B100;HELPER=0x1512AD54;ACTOR=0x32000;G1=0x800BEAC0;G2=0x800C3671;POST=(0x1512C20C,0x1512BB10)

TYPES=(0,0x100,0x40,0x140,1,0x80000000,0x80000100,0xFFFFFFFF);FLAGS=(0,8,0x200,0x208,0xFFFFFFFF,0x80000008,0x400,0x408);STATES=(0,0x40,0x80,0xC0,0xFFFFFFFF,0x80000000,0x100,0x800000C0)
def fixture(kind=1,flags=8,byte=0,state=0,g1=0,g2=0,actor=ACTOR):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x100)}
 for i in range(-16,0x630):m[actor+i]=(i*13+0xA5)&255
 m[G1]=g1;m[G2]=g2;put(m,actor+0x2C,kind);put(m,actor+0x84,flags);m[actor+0x23C]=byte;put(m,actor+0x5F0,state);return m
def effect(m,actor,mode):
 if mode:
  put(m,actor+0x5F8,0x1234,2);put(m,actor+0x5FC,0x5678,2);put(m,actor+0x5FE,0x9ABC,2);m[G1]=255;m[G2]=128

def reference(memory,actor,mode=0):
 m=dict(memory);kind=read(m,actor+0x2C);calls=[]
 if kind&0xFFFFFEFF and not m[G1]and not m[G2]:
  if kind!=0x40 and(read(m,actor+0x84)&8)and not(read(m,actor+0x84)&0x200)and not m[actor+0x23C]and not(read(m,actor+0x5F0)&0x80)and not(read(m,actor+0x5F0)&0x40):
   calls=[(HELPER,(actor,))];effect(m,actor,mode)
  else:put(m,actor+0x5F8,1,2);put(m,actor+0x5FC,2,2);put(m,actor+0x5FE,60,2)
 return m,calls

def public(m):return{a:v for a,v in m.items()if not STACK-0x200<=a<STACK+0x100}
class Oracle(TimingOracle):
 def __init__(self,code,memory,actor=ACTOR,phase=0,mode=0):
  self.state_effect_mode,self.trace=mode,[];super().__init__(code,memory,phase=phase,entry=ENTRY,arguments=(actor,))
 def get(self,at,size):
  value=super().get(at,size)
  if self.own_instruction:self.trace.append(('R',at,size,value))
  return value
 def put(self,at,value,size):
  if self.recording and self.own_instruction:assert all(at+i in self.memory for i in range(size))
  super().put(at,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',at,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target==HELPER;args=(self.r[4],);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==HELPER;actor=self.calls[-1][1][0];effect(self.memory,actor,self.state_effect_mode)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]

def compare(m,actor=ACTOR,phase=0,mode=0):
 expected,calls=reference(m,actor,mode);models=[Oracle(code,m,actor,phase,mode).run()for code in(truth,words)]
 for model in models:assert public(model.memory)==public(expected)and model.calls==calls
 assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace;return models

class Caller(Oracle):
 def __init__(self,window,memory,actor,entry,connected,phase=0,mode=0):
  self.state_effect_mode,self.trace,self.incoming_v0=mode,[],[]
  TimingOracle.__init__(self,window,memory,phase=phase,entry=entry,arguments=(0xBAD0BEEF,),connected=connected)
  self.r[16]=self.before[16]=actor;self.r[23]=self.before[23]=self.before[31];self.tail=True
 def record_call(self,target):
  assert target in(ENTRY,HELPER,*POST),hex(target);args=(self.r[4],);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target in POST:self.incoming_v0.append((target,self.r[2]))
 def hook(self,target):
  if target==HELPER:return Oracle.hook(self,target)
  assert target in POST
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=0xD5000000|(target&65535);self.f[:20]=[0xA5000000+i for i in range(20)]

header=r'''typedef int s32;typedef unsigned int u32;typedef unsigned short u16;typedef short s16;typedef unsigned char u8;
static u8 D_800BEAC0,D_800C3671;typedef struct {
 u8 pad0[0x2C];s32 kind;u8 pad30[0x54];s32 flags;
 u8 pad88[0x1B4];u8 status;u8 pad23D[0x3B3];s32 state;
 u8 pad5F4[4];s16 request,keep5FA;u16 mode;s16 timer;u8 pad600[0x20];
} NativeActor;
typedef char Width[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(s16)==2&&sizeof(NativeActor)==0x620&&__builtin_offsetof(NativeActor,kind)==0x2C&&__builtin_offsetof(NativeActor,flags)==0x84&&__builtin_offsetof(NativeActor,status)==0x23C&&__builtin_offsetof(NativeActor,state)==0x5F0&&__builtin_offsetof(NativeActor,request)==0x5F8&&__builtin_offsetof(NativeActor,mode)==0x5FC&&__builtin_offsetof(NativeActor,timer)==0x5FE)?1:-1];
typedef struct{u32 pre[4];NativeActor actor;u32 post[4];}State;static State actual,expected;
static u32 calls,observed,bad;static s32 func_1512AD54(u8 *actor){calls++;if(actor!=(u8*)&actual.actor)bad=1;observed=*(u32*)(actor+0x2C);*(u16*)(actor+0x5F8)=0x1234;*(u16*)(actor+0x5FC)=0x5678;*(u16*)(actor+0x5FE)=0x9ABC;D_800BEAC0=255;D_800C3671=128;return (s32)0xFEDCBA98u;}
'''
tail=r'''
static int run(void){const u32 types[]={0,256,64,320,1,0x80000000u,0x80000100u,0xFFFFFFFFu};const u32 flags[]={0,8,512,520,0xFFFFFFFFu,0x80000008u,1024,1032};const u32 states[]={0,64,128,192,0xFFFFFFFFu,0x80000000u,256,0x800000C0u};u32 k,f,s,gate,byte,i,kind,flag,state,want,w1,w2;u8 *a=(u8*)&actual,*b=(u8*)&expected,*actor=(u8*)&actual.actor,*e=(u8*)&expected.actor;
 for(k=0;k<8;k++)for(f=0;f<8;f++)for(s=0;s<8;s++)for(gate=0;gate<4;gate++)for(byte=0;byte<2;byte++){
  for(i=0;i<sizeof(State);i++)a[i]=(u8)(i*13+0xA5);kind=types[k];flag=flags[f];state=states[s];D_800BEAC0=(gate&1)?255:0;D_800C3671=(gate&2)?255:0;w1=D_800BEAC0;w2=D_800C3671;
  *(u32*)(actor+44)=kind;*(u32*)(actor+132)=flag;actor[572]=byte?255:0;*(u32*)(actor+1520)=state;for(i=0;i<sizeof(State);i++)b[i]=a[i];calls=observed=bad=0;want=0;
  if((kind&0xFFFFFEFFu)!=0&&gate==0){if(kind!=64&&(flag&8)!=0&&(flag&512)==0&&byte==0&&(state&192)==0){want=1;*(u16*)(e+1528)=0x1234;*(u16*)(e+1532)=0x5678;*(u16*)(e+1534)=0x9ABC;w1=255;w2=128;}else{*(u16*)(e+1528)=1;*(u16*)(e+1532)=2;*(u16*)(e+1534)=60;}}
  func_1512B100(actor);if(calls!=want||bad||(want&&observed!=kind)||D_800BEAC0!=w1||D_800C3671!=w2)return 23;for(i=0;i<sizeof(State);i++)if(a[i]!=b[i])return 23;
 }return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
def native(label,unit,opt):
 src=o/(label+opt+'.c');exe=src.with_suffix('.elf');src.write_text(header+unit+tail);p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector','-fno-builtin','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Werror=implicit-function-declaration','-Wl,-e,_start',str(src),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr;return subprocess.run([str(exe)],capture_output=True).returncode


class ActorStateRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global words,truth,rom,body,o
        cls.out=ROOT/source.BUILD;cls.receipt={};cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out)
        cls.obj,diagnostics=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.ISOLATED_DECLARATIONS+'\n'+source.SELECTED,'fresh-selected')
        if diagnostics:raise ValueError(diagnostics)
        source.checked_payload(*source.payload(cls.obj));data,functions=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        words=list(struct.unpack_from('>46I',data,functions[source.FUNCTION]['value']));rom=cls.values['conker/conker.us.bin'];truth=list(struct.unpack_from('>46I',rom,source.ROM))
        body=source.SELECTED;o=cls.out/'native32';o.mkdir(exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def test_01_direct_C_original_full_owner_and_actual_Make(self):
        self.assertEqual(words,truth);raw,bindings=source.checked_payload(*source.payload(self.obj))
        self.assertEqual(source.payload(self.out/'after-owner.o'),(raw,bindings));self.assertEqual(source.payload(self.out/'original-func_1512B100.o'),(raw,bindings))
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),14)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],q['preserved_neighbors']),(46,24,0,14))
        self.assertEqual((self.out/'make-shadow/src/game/generated_157840.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        self.assertEqual((self.out/'qualified-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        if self.installed:source.audit(ROOT,self.out)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,184);m=fixture(kind=0x40)
        model=Oracle(struct.unpack_from('>46I',old,at),m).run();expected,calls=reference(m,ACTOR)
        self.assertNotEqual(public(model.memory),public(expected))
        self.receipt.update(words=46,alignment_words=0,frame=24,guards=0,bindings=5,neighbors=14,provider_stub_unchanged=True,actual_Make_commands=3)
    def test_02_fullword_gates_byte_sweeps_aliases_lazy_reads_and_fired_faults(self):
        visits=set();count=0
        for kind,flags,g1,g2,byte,state,phase in itertools.product(TYPES,FLAGS,(0,255),(0,255),(0,255),STATES,(0,8)):
         models=compare(fixture(kind,flags,byte,state,g1,g2),phase=phase,mode=1);visits.update(models[0].visits);count+=1
        assert set(range(ENTRY,ENTRY+184,4))<=visits
        sweeps=0
        for byte,field in itertools.product(range(256),(G1,G2,ACTOR+0x23C)):
         m=fixture();m[field]=byte;compare(m,mode=1);sweeps+=1
        aliases=0
        for actor in(G1-0x2C,G1-0x84,G1-0x5F8,G2-0x2D,G2-0x85,G2-0x5FD):
         for kind in(1,0x40,0xFFFFFFFF):compare(fixture(kind=kind,actor=actor),actor,mode=1);aliases+=1
        faultcount=0
        for args in((0,8,0,0,0,0),(1,8,0,0,255,0),(1,8,0,0,0,255),(0x40,8,0,0,0,0),(1,8,0,0,0,0),(1,8,255,0,0,0),(1,8,0,0x40,0,0)):
         m=fixture(*args);good=Oracle(truth,m,mode=1).run()
         for cut in range(good.root_accesses):
          models=[Oracle(code,m,mode=1)for code in(truth,words)]
          for model in models:
           model.root_fault=cut
           try:model.run()
           except faults.AccessBoundary:pass
           else:raise AssertionError('fault control did not fire')
          assert complete(models[0])==complete(models[1]);faultcount+=1
        lazy=0
        requests=[(fixture(kind=kind),[G1,G2,*range(ACTOR+0x84,ACTOR+0x88),ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)])for kind in(0,0x100)]
        requests.extend([(fixture(g1=255),[G2,*range(ACTOR+0x84,ACTOR+0x88),ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)]),(fixture(g2=255),[*range(ACTOR+0x84,ACTOR+0x88),ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)]),(fixture(kind=0x40),[*range(ACTOR+0x84,ACTOR+0x88),ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)]),(fixture(flags=0),[ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)]),(fixture(flags=0x208),[ACTOR+0x23C,*range(ACTOR+0x5F0,ACTOR+0x5F4)]),(fixture(byte=255),list(range(ACTOR+0x5F0,ACTOR+0x5F4))),(fixture(),[*range(ACTOR+0x5F8,ACTOR+0x5FA),*range(ACTOR+0x5FC,ACTOR+0x600)])])
        for memory,unused in requests:
            for at in unused:memory.pop(at,None)
            compare(memory,mode=0);lazy+=1
        self.receipt.update(guest_cases=count,byte_sweeps=sweeps,guest_alias_cases=aliases,fired_fault_prefixes=faultcount,lazy_unmapped_cases=lazy,all46_words_visited=True,exact_access_order=True)
    def test_03_native32_typed_fields_canaries_and_effective_negative_controls(self):
        for opt in('-O0','-O2','-O3'):assert native('selected',body,opt)==0
        changes={'type-mask':('~0x100','~0x101'),'masked-type':('type != 0x40','(type & ~0x100) != 0x40'),'global1':('!D_800BEAC0','D_800BEAC0'),'global2':('!D_800C3671','D_800C3671'),'flag8':('& 8)','& 4)'),'flag200':('& 0x200','& 0x400'),'byte23C':('!actor[0x23C]','actor[0x23C]'),'state80':('& 0x80','& 0x100'),'state40':('& 0x40','& 0x20'),'first-halfword':('actor + 0x5F8','actor + 0x5FA'),'constant-one':('= 1;','= 3;'),'constant-two':('= 2;','= 4;'),'constant-sixty':('= 60;','= 59;')}
        for label,(old,new)in changes.items():
         unit=body.replace(old,new);assert unit!=body,label;code=native(label,unit,'-O2');assert code==23,(label,code)
        self.receipt.update(native_optimizations=3,native_cases_per_run=4096,native_effective_controls=len(changes),trap_UBSan=True,native_typed_field_offsets_asserted=True,canaries_and_global_effects_checked=True)
    def test_04_both_actual_caller_windows_and_void_result_boundary(self):
        count=0;v0=set()
        for at in(0x15048C,0x1504B8):
         entry=at-0x2D4B0+0x15000000;actual=list(struct.unpack_from('>6I',rom,at));assert actual==[0x0D44AC40,0x02002025,0x0D44B083,0x02002025,0x0D44AEC4,0x02002025]
         # Only the final two words are a declared return adapter, outside the six retail words.
         window=actual+[0x02E00008,0]
         for kind,flags,byte,state,mode,phase in itertools.product((0,0x100,0x40,0x140,1,0xFFFFFFFF),(0,8,0x208),(0,255),(0,0x40,0x80),(0,1),(0,8)):
          memory=fixture(kind,flags,byte,state);expected,calls=reference(memory,ACTOR,mode);models=[]
          for image in(truth,words):
           connected=dict(zip(range(ENTRY,ENTRY+184,4),image));model=Caller(window,memory,ACTOR,entry,connected,phase,mode).run()
           assert public(model.memory)==public(expected)
           assert model.calls==[(ENTRY,(ACTOR,))]+calls+[(x,(ACTOR,))for x in POST]
           assert model.r[16]==ACTOR and model.r[29]==model.before[29];models.append(model);v0.add(model.incoming_v0[0][1])
          assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace;count+=1
        assert len(v0)>1
        self.receipt.update(actual_caller_sites=['0x15122FDC','0x15123008'],actual_words_per_window=6,adapter_words=2,caller_cases=count,observed_unused_V0_values=len(v0),S0_SP_preserved=True,RA_excluded_only_at_adapter_boundary=True,full_parent_or_post_provider_claimed=False)
    def test_05_independent_GNU_links_and_rebased_semantics(self):
        o=self.out/'GNU-rebases';o.mkdir(exist_ok=True);function=source.FUNCTION
        objects=(('original',self.out/'original-func_1512B100.o'),('C',self.obj));rows=[];cases=0
        ns=globals();saved={k:ns[k]for k in('ENTRY','HELPER','G1','G2','truth','words')};self.addCleanup(lambda:ns.update(saved))
        for i in range(3):
         entry=0x1700FFFC+i*0x10000;anchors=dict(D_800BEAC0=(0x80117FFC,0x80128000,0x8013FFFF)[i],D_800C3671=(0x80228000,0x80237FFF,0x80240000)[i],func_1512AD54=0x17018000+i*0x10000);images=[]
         for label,obj in objects:
          text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[function],bindings,function,anchors);assert not unknown;stem=o/('GNU-'+str(i)+'-'+label);src=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf');src.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
          subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(src)],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',function,*['--defsym=%s=0x%X'%x for x in anchors.items()],'-o',str(elf),str(out)],check=True,capture_output=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
         assert images[0]==images[1]
         ns.update(ENTRY=entry,HELPER=anchors['func_1512AD54'],G1=anchors['D_800BEAC0'],G2=anchors['D_800C3671'],truth=images[0],words=images[1])
         for kind,flags,state,gate,phase in itertools.product((0,0x100,0x40,0x140,1,0xFFFFFFFF),(0,8,0x208),(0,0x40,0x80),((0,0),(255,0),(0,255)),(0,8)):
          compare(fixture(kind,flags,0,state,*gate),phase=phase,mode=1);cases+=1
         rows.append(dict(entry=hex(entry),anchors={k:hex(v)for k,v in anchors.items()},all46_words_equal=True))
        self.receipt.update(independent_GNU_links=6,rebased_semantic_cases=cases,rebase_layouts=rows,all5_bindings_checked=True)
    def test_06_strict_image_current_inputs_guards_and_effective_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out)
        before=values['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+184];expected=source.predicted_image(before,truth_bytes)
        self.assertEqual((self.out/'first-linked.elf').read_bytes(),expected);at=source.elf_slot_offset(before,source.ENTRY,184)
        for offset in(0,at-1,at,at+180,at+184,len(before)-1):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth_bytes)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),values['conker/retail_word_patches.us.csv'])
        self.receipt.update(strict_image_corruptions_rejected=7,metadata_exclusions=0,frozen_and_current_inputs=len(values),entire_guard_manifest_unchanged=True)

if __name__=='__main__':unittest.main()
