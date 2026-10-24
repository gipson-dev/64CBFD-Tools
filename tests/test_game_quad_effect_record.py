"""Quad-effect record: o32 arguments, SDK vertices, allocator lifetime and caller windows."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_quad_effect_record as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
EFFECT,ALLOC,REGISTER=0x30000,0x10003C6C,0x15168A4C
SYMBOLS={'func_15167A68':source.ALLOCATE}
VALUES=(0,1,127,128,255,256,32767,32768,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)
MUTATED=(0xA5B68000,0xA5B6FFFF,0xA5B60080,0x876543FF,0x87650001,0xFFFFFFFF,0xA5B600FF,0x87654321)


@dataclass(frozen=True)
class Case:
    pattern:int=0
    allocated:bool=True
    mutate:bool=False
    alias:int=0
    seed:int=0xA5


def arguments(case):
    return tuple(VALUES[(case.pattern+i*3)%len(VALUES)] for i in range(8))


def address(case,entered):
    return (EFFECT,entered-0x50,entered-0x40)[case.alias]


def fixture(case,phase=0,args=None):
    m={STACK+i:(i*17+case.seed)&255 for i in range(-1024,512)}
    m.update({EFFECT+i:(i*13+case.seed)&255 for i in range(-16,112)})
    a=arguments(case) if args is None else args
    for i,v in enumerate(a):put(m,STACK+phase+i*4,v)
    return m


def effects(m,case,entered):
    if case.mutate:
        for i,v in enumerate(MUTATED):put(m,entered+i*4,v)


def reference(initial,case,entered=STACK,args=None,connected=False):
    m=dict(initial);a=arguments(case) if args is None else args
    for i,value in enumerate(a):put(m,entered+i*4,value)
    kind=15 if a[5]==0 else 67
    calls=[(source.ALLOCATE,(kind,a[7],96,1,a[6]&255,1))]
    effects(m,case,entered)
    dst=address(case,entered) if case.allocated else 0
    if dst:
        if connected:
            m[dst+1]=a[7]&255;m[dst+12]=a[6]&255
        # The first halfword is captured before frame zeroing can alias its home.
        first=read(m,entered+2,2);put(m,dst+0x52,0,2);put(m,dst+0x50,first,2)
        put(m,dst+0x54,read(m,entered+16),2)
        put(m,dst+0x56,read(m,entered+6,2),2)
        put(m,dst+0x58,m[entered+11],1)
        flags=read(m,entered+12)
        for offset in(0x16,0x26,0x36,0x46):put(m,dst+offset,0,2)
        put(m,dst+0x59,flags,1)
    return m,calls,dst


def view(m,case,entered):
    dst=address(case,entered)
    visible=set(range(dst,dst+96))
    stores=({dst+offset+i for offset in(0x16,0x26,0x36,0x46,0x50,0x52,0x54,0x56,0x58)for i in range(2)}
            if case.allocated else set())
    return {a:b for a,b in m.items()if not STACK-1024<=a<STACK+512 or a in stores or a in visible and a>=entered}


class QuadOracle(RayOracle):
    def __init__(self,words,memory,case=Case(),phase=0,entry=source.ENTRY,connected=None,symbols=None,args=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments(case) if args is None else args,connected=connected)
        self.case=case;self.entered=STACK+phase;self.quad_symbols=SYMBOLS if symbols is None else symbols
        self.root_arguments=arguments(case) if args is None else args

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered=self.r[29];args=self.arguments(8);self.root_arguments=args
        elif target==self.quad_symbols['func_15167A68']:
            a=self.root_arguments;args=self.arguments(6)
            assert args==(15 if a[5]==0 else 67,a[7],96,1,a[6]&255,1),args
        elif target==ALLOC:
            args=self.arguments(5);assert args==(96,1,1,0,1),args
        elif target==REGISTER:
            args=self.arguments(2)
            assert args==(address(self.case,self.entered),15 if self.root_arguments[5]==0 else 67),args
        else:raise AssertionError(('unbounded quad-effect helper',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target in(self.quad_symbols['func_15167A68'],ALLOC):
            effects(self.memory,self.case,self.entered)
            value=address(self.case,self.entered) if self.case.allocated else 0
        else:
            assert target==REGISTER;value=0xB5000002
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc in(0x15171DAC,0x15171EF4,0x15171F58,0x15171FB0):
            raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    b=source.SELECTED
    return dict(selected=b,
        narrow_mode=b.replace('alternate == 0','(u8)alternate == 0'),
        inverted_mode=b.replace('alternate == 0','alternate != 0'),
        wrong_kind=b.replace('0x43','0x42'),
        wrong_context=b.replace('0x43, context','0x43, 0'),
        wrong_size=b.replace('sizeof(QuadEffect19F150)','sizeof(QuadEffect19F150) - 8'),
        wrong_slot=b.replace('1, slot, 1','1, 0, 1'),
        wrong_lifetime=b.replace('record->lifetime = lifetime','record->lifetime = 0'),
        wrong_frame=b.replace('record->frame = 0','record->frame = 1'),
        wrong_step=b.replace('record->frameStep = frameStep','record->frameStep = (u8)frameStep'),
        wrong_color=b.replace('record->color = color','record->color = 0'),
        wrong_image=b.replace('record->imageIndex = imageIndex','record->imageIndex = 0'),
        wrong_flags=b.replace('record->flags = flags','record->flags = 0'),
        missing_vertex=b.replace('record->vertices[3].v.flag = 0;',''),
        zero_position=b.replace('record->vertices[0].v.flag = 0;','record->vertices[0].v.flag = 0;\n    record->vertices[0].v.ob[0] = 0;'))


def native_harness(helper):
    text='#include <ultra64.h>\n'+source.DECLARATIONS+'''
typedef char record_size[sizeof(QuadEffect19F150)==96?1:-1];
typedef char vertex_size[sizeof(Vtx)==16?1:-1];
typedef char vertex_offset[__builtin_offsetof(QuadEffect19F150,vertices)==16?1:-1];
typedef char lifetime_offset[__builtin_offsetof(QuadEffect19F150,lifetime)==80?1:-1];
typedef char flags_offset[__builtin_offsetof(QuadEffect19F150,flags)==89?1:-1];
static struct {u8 pre[16];QuadEffect19F150 record;u8 post[16];} actual,expected;
static u32 error,allocated,allocations,registrations,wantedKind,wantedContext,wantedSlot;
void *func_10003C6C(s32 n,s32 a,s32 b,s32 c,u8 pool);
void func_15168A4C(void *p,s32 kind);
__attribute__((noinline,noclone)) void *func_10003C6C(s32 n,s32 a,s32 b,s32 c,u8 pool){
 allocations++;if(n!=96||a!=1||b!=1||c!=0||pool!=1)error=1;
 return allocated?&actual.record:0;
}
__attribute__((noinline,noclone)) void func_15168A4C(void *p,s32 kind){
 registrations++;if(p!=&actual.record||(u32)kind!=wantedKind||((u8*)p)[1]!=(u8)wantedContext)error=2;
}
'''+helper+'\n'
    # A second boundary checks the six-argument interface before entering actual helper C.
    text=text.replace('void *func_15167A68(s32 arg0','void *actual_allocator(s32 arg0',1)
    text+='''
__attribute__((noinline,noclone)) void *func_15167A68(s32 kind,s32 context,s32 n,s32 flag,u8 slot,u8 pool){
 if((u32)kind!=wantedKind||(u32)context!=wantedContext||n!=96||flag!=1||slot!=wantedSlot||pool!=1)error=3;
 return actual_allocator(kind,context,n,flag,slot,pool);
}
'''
    for name,body in controls().items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef void *(*Create)(s16,u16,u8,s32,s32,s32,u8,s32);
static const u32 values[]={0,1,127,128,255,256,32767,32768,65535,65536,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x87654321u};
static int variant(Create fn){
 u32 i,p,byte,a,j;u32 v[8];void *result;
 for(p=0;p<14;p++)for(byte=0;byte<256;byte++)for(a=0;a<2;a++){
  for(i=0;i<8;i++)v[i]=values[(p+i*3)%14];
  v[2]=(v[2]&0xFFFFFF00u)|byte;v[6]=(v[6]&0xFFFFFF00u)|((byte*37)&255);
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=(u8)(i*13+p+byte);
  allocated=a;error=allocations=registrations=0;wantedKind=v[5]==0?15:67;wantedContext=v[7];wantedSlot=(u8)v[6];
  if(a){
   ((u8*)&expected.record)[1]=(u8)v[7];((u8*)&expected.record)[12]=(u8)v[6];
   expected.record.lifetime=(s16)v[0];expected.record.frame=0;expected.record.frameStep=(s16)v[4];
   expected.record.color=(u16)v[1];expected.record.imageIndex=(u8)v[2];expected.record.flags=(u8)v[3];
   for(j=0;j<4;j++)expected.record.vertices[j].v.flag=0;
  }
  result=fn((s16)v[0],(u16)v[1],(u8)v[2],(s32)v[3],(s32)v[4],(s32)v[5],(u8)v[6],(s32)v[7]);
  if(error||allocations!=1||registrations!=a||result!=(a?&actual.record:0))return 23;
  for(i=0;i<sizeof(actual);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,i+1)
    return text+' return 0;\n}\n'+START


class QuadEffectRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        cls.raw,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.out,cls.raw,source.OWNER)
        cls.words=list(struct.unpack_from('>43I',data,functions[source.FUNCTION]['value']))
        cls.allocator=list(struct.unpack_from('>28I',cls.rom,0x194F18));cls.receipt={}

    def compare(self,case,phase=0,chain=False,images=None,symbols=None,entry=source.ENTRY):
        s=SYMBOLS if symbols is None else symbols;memory=fixture(case,phase)
        expected,calls,dst=reference(memory,case,STACK+phase,connected=chain)
        calls=[(s['func_15167A68'],calls[0][1])]
        connected={source.ALLOCATE+i*4:w for i,w in enumerate(self.allocator)}if chain else None
        models=[QuadOracle(w,memory,case,phase,entry,connected,s).run()for w in(images or(self.truth,self.words))]
        for model in models:
            self.assertEqual(view(model.memory,case,STACK+phase),view(expected,case,STACK+phase),case)
            self.assertEqual([x for x in model.calls if x[0]==s['func_15167A68']],calls)
            self.assertEqual(model.r[29],STACK+phase);self.assertEqual(model.r[2],dst)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_words_bindings_owner_make_and_history(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFE0)
        self.assertEqual(source.payload(self.raw),source.payload(source.original(ROOT,self.out)))
        self.assertEqual(sum(map(len,source.payload(self.raw)[1].values())),1)
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],6)
        self.receipt.update(exact_words=43,frame=32,bindings=1,new_guards=0,compiler_only=True,preserved_neighbors=6)

    def test_02_guest_widths_live_homes_and_original_allocator(self):
        visits=set();ordinary=connected=0
        for pattern,allocated,mutate,alias,phase in itertools.product(range(14),(False,True),(False,True),range(3),(0,8)):
            model=self.compare(Case(pattern,allocated,mutate,alias),phase);visits.update(model.visits);ordinary+=1
        for pattern,allocated,mutate,phase in itertools.product(range(14),(False,True),(False,True),(0,8)):
            model=self.compare(Case(pattern,allocated,mutate),phase,True);visits.update(model.visits);connected+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+172,4))<=visits)
        self.assertTrue(set(range(source.ALLOCATE,source.ALLOCATE+112,4))<=visits)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.ALLOCATE,112)
        self.assertEqual(before[at:at+112],self.rom[0x194F18:0x194F18+112])
        self.receipt.update(ordinary_guest_phases=ordinary,connected_helper_phases=connected,retained_helper_words=28,
            root_visited_words=43,visited_helper_words=28,allocator_and_registration_providers_bounded=True,
            full_allocation_pipeline_claimed=False,live_argument_homes_and_output_aliases=True)

    def linked(self,obj,entry,symbols,label):
        data,functions,bindings=source.parse_object(obj)
        asm,unknown=emit_function(data,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
        self.assertFalse(unknown);p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_03_independent_rebases_and_fault_prefixes(self):
        profiles=[(source.ENTRY,SYMBOLS),(0x18017FFC,{'func_15167A68':0x18207FFC}),(0x1A028000,{'func_15167A68':0x1B047FF0})]
        objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_19F150.c.o')
        count=cuts=0
        for i,(entry,symbols)in enumerate(profiles):
            images=[self.linked(obj,entry,symbols,'rebased-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for pattern,allocated,mutate,alias,phase in itertools.product((0,5,9,12),(False,True),(False,True),range(3),(0,8)):
                self.compare(Case(pattern,allocated,mutate,alias),phase,images=images[:2],symbols=symbols,entry=entry);count+=1
        for allocated,mutate,alias,phase in itertools.product((False,True),(False,True),range(3),(0,8)):
            case=Case(12,allocated,mutate,alias);memory=fixture(case,phase)
            done=QuadOracle(self.truth,memory,case,phase).run()
            for cut in range(done.root_accesses):
                models=[QuadOracle(w,memory,case,phase)for w in(self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_and_alias_phases=count,fired_root_access_prefixes=cuts,
            portable_C_alias_or_fault_claimed=False)

    def test_04_native32_actual_allocator_C_and_effective_controls(self):
        text=self.values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(text,'func_15167A68')
        unit=self.out/'native32.c';unit.write_text(native_harness(text[lo:hi]))
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            p=subprocess.run([*native_command(opt),str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_calls_per_optimization=7168,native_optimizations=['O0','O2','O3'],
            actual_allocator_C_body=True,effective_wrong_C_controls=14,trap_UBSan=True,native_disjoint_typed_storage=True)

    def test_05_both_actual_caller_argument_windows(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));literal=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x19F240,0x19F3F8])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==literal],[])
        count=0
        for caller,rom,size in((0x15171D4C,0x19F1FC,24),(0x15171F04,0x19F3B4,21)):
            window=list(struct.unpack_from('>%dI'%size,self.rom,rom))
            for pattern,allocated,phase in itertools.product(range(14),(False,True),(0,8)):
                case=Case(pattern,allocated);args=arguments(case);initial=fixture(case,phase)
                # Parent's stack arguments are raw words. SDK float homes are preserved, not interpreted.
                parent_args=(0x3F800000,0xBF800000,args[0],args[1])
                if caller==0x15171D4C:
                    offsets=(12,16,20,36,40,44,48,52)
                else:offsets=(16,20,24,32,36,40,44,48)
                parent_sp=STACK+phase
                for i,offset in enumerate(offsets):put(initial,parent_sp+offset,args[i])
                # Saved a3 overwrites +12 in caller 1; make it the lifetime's complete home word.
                if caller==0x15171D4C:parent_args=(0x3F800000,0xBF800000,0x40000000,args[0])
                entered=parent_sp-48
                a=list(args);a[0]=((args[0]&65535)^32768)-32768;a[0]&=0xFFFFFFFF
                a[1]&=65535;a[2]&=255;a[6]&=255;a=tuple(a)
                expected,calls,dst=reference(initial,case,entered,a)
                models=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                    model=QuadOracle(window,initial,case,phase,caller,connected,args=parent_args)
                    model.code=WindowCode(model.code,model)
                    with self.assertRaises(WindowBoundary):model.run()
                    self.assertEqual(model.calls,[(source.ENTRY,a),*calls])
                    self.assertEqual(model.r[2],dst);self.assertEqual(model.r[29],entered)
                    for i in range(-16,112):
                        self.assertEqual(model.memory[EFFECT+i],expected[EFFECT+i],(hex(caller),case,i))
                    models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(actual_caller_windows=2,caller_window_words=[24,21],caller_phases=count,
            eight_argument_o32_interface=True,full_parent_C_or_geometry_claimed=False)

    def test_06_strict_image_and_input_negative_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172]
        expected=source.predicted_image(before,truth);source.check_image(before,expected,truth)
        at=source.elf_slot_offset(before,source.ENTRY,172)
        sym=[offset for offset,name,_,_ in source.symbol_rows(before)if name==source.FUNCTION][0]
        for position in(0,at-1,at,at+168,at+172,sym+4,sym+8,len(before)-1):
            bad=bytearray(expected);bad[position]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.receipt.update(strict_image_negatives=9,guard_manifest_byte_identical=True,metadata_exclusions=0)
