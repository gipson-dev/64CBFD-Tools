"""One-shot payload: allocation failure, live aliases, original helpers and callers."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_one_shot_link as source
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
FLAG,GLOBAL,OWNER,OTHER,EFFECT=0x80088B60,0x800D3098,0x28000,0x29000,0x30000
SYMBOLS={'D_80088B60':FLAG,'D_800D3098':GLOBAL,'func_15149130':source.SPAWN,'memcpy':source.COPY}
PARAMETERS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)


@dataclass(frozen=True)
class Case:
    flag:int=0
    code:int=255
    value:int=1
    allocated:bool=True
    mode:int=0
    destination:int=0
    private:bool=False
    seed:int=0xA5


def corpus():
    for code,allocated,mode in itertools.product(range(256),(False,True),range(4)):
        yield Case(code=code|0xA5B60000,value=PARAMETERS[code%6],allocated=allocated,mode=mode,seed=code)
    for flag,allocated in itertools.product(range(256),(False,True)):
        yield Case(flag=flag,code=0xFFFFFFFF,value=0x80000000,allocated=allocated)
    for allocated,mode,destination,private in itertools.product((False,True),range(4),range(7),(False,True)):
        yield Case(code=0x87654380,value=0xFFFFFFFF,allocated=allocated,mode=mode,destination=destination,private=private)


def fixture(case,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    m={STACK+i:(i*17+case.seed)&255 for i in range(-1024,256)}
    for base,length in((s['D_80088B60']-64,128),(s['D_800D3098']-64,128),(OWNER,0x800),(OTHER,0x800),(EFFECT-16,128)):
        m.update({base+i:(i*13+case.seed)&255 for i in range(length)})
    m[s['D_80088B60']]=case.flag;put(m,s['D_800D3098'],OWNER)
    return m


def destination(case,payload,symbols):
    return (EFFECT+0x28,symbols['D_80088B60'],payload+1,payload-1,
            symbols['D_800D3098'],payload+12,OWNER+0x71C)[case.destination]


def effects(memory,case,payload,symbols):
    if case.mode&1:put(memory,symbols['D_800D3098'],OTHER)
    if case.mode&2:memory[symbols['D_80088B60']]=0x5A
    if case.private:
        put(memory,payload+4,0x12345678);put(memory,payload+8,0x80000000)


def header(memory,base):
    put(memory,base+0xE,300,2)
    for at,value in((0x10,255),(0x11,0x57),(0x12,255),(0xD,0),(0x13,0x46)):
        memory[base+at]=value
    for i in range(16):memory[base+0x14+i]=0


def reference(initial,case,entered=STACK,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    m=dict(initial);calls=[];payload=entered-72+0x3C;captured=None
    put(m,entered-28,0xDEAD0000)
    if not m[s['D_80088B60']]:
        owner=read(m,s['D_800D3098']);put(m,payload,(owner+0x71C)&0xFFFFFFFF)
        put(m,payload+4,(owner+0x6E8)&0xFFFFFFFF);put(m,payload+8,0)
        args=(300,0xFFFFFFFF,0x57,0xFFFFFFFF,0,0x46,12,case.code&255,case.value)
        calls.append((s['func_15149130'],args));effects(m,case,payload,s)
        if case.allocated:
            target=destination(case,payload,s);header(m,target-0x28)
            m[s['D_80088B60']]=1
            captured=bytes(m[payload+i]for i in range(12))
            calls.append((s['memcpy'],(target,payload,12)))
            for i in range(12):m[target+i]=m[payload+i]
    return m,calls,captured


def public(memory):
    return {a:b for a,b in memory.items()if not STACK-1024<=a<STACK+256}


class OneShotOracle(RayOracle):
    """Reuse the qualified signed-LB engine for the retained factory."""
    def __init__(self,words,memory,case=Case(),phase=0,symbols=None,entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=(case.code,case.value),connected=connected)
        self.case=case;self.link_symbols=SYMBOLS if symbols is None else symbols
        self.entered=STACK+phase;self.captured=None;self.fired=set();self.escape_target=None

    def run(self):
        try:
            return super().run()
        except AssertionError as error:
            # Malformed allocation aliases may destroy the literal saved RA.
            if (self.case.flag or not self.case.allocated or self.case.destination not in(2,3,5)
                    or error.args!=(('unowned jump',self.r[31]),)
                    or (self.current_pc,self.delay_of)!=(self.root_entry+168,self.root_entry+164)):
                raise
            self.escape_target=self.r[31]
            return self

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered=self.r[29]
            args=self.arguments(2);assert args==(255,1)
        elif target==self.link_symbols['func_15149130']:
            args=self.arguments(9)
            assert args==(300,0xFFFFFFFF,0x57,0xFFFFFFFF,0,0x46,12,self.case.code&255,self.case.value)
        elif target==self.link_symbols['memcpy']:
            args=self.arguments(3);assert args[1]==self.entered-72+0x3C and args[2]==12
            assert args[0]==destination(self.case,args[1],self.link_symbols)
            self.captured=bytes(self.memory[args[1]+i]for i in range(12))
            assert self.memory[self.link_symbols['D_80088B60']]==1
        elif target==source.ALLOCATE:
            args=self.arguments(6);assert args==(35,self.case.value,52,1,self.case.code&255,1)
        elif target==source.BZERO:
            args=self.arguments(2);assert args==(destination(self.case,self.entered-72+0x3C,self.link_symbols)-0x14,16)
        else:raise AssertionError(('unbounded one-shot helper',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target in(self.link_symbols['func_15149130'],source.ALLOCATE):
            effects(self.memory,self.case,self.entered-72+0x3C,self.link_symbols)
            if self.case.mode&1:self.fired.add('late-global-change')
            if self.case.mode&2:self.fired.add('helper-latch-change')
            if self.case.private:self.fired.add('private-payload-change')
            value=(destination(self.case,self.entered-72+0x3C,self.link_symbols)-0x28)&0xFFFFFFFF if self.case.allocated else 0
            if value and target==self.link_symbols['func_15149130']:header(self.memory,value)
        elif target==self.link_symbols['memcpy']:
            dst,src,n=self.arguments(3)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        else:
            assert target==source.BZERO
            dst,n=self.arguments(2)
            for i in range(n):self.put(dst+i,0,1)
            value=0xB5000002
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc in(0x150265B4,0x1509D76C):raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    b=source.SELECTED
    capture='''        payload.first = D_800D3098 + 0x71C;
        payload.second = D_800D3098 + 0x6E8;
'''
    latch='''        if (effect != 0) {
            D_80088B60 = 1;
        }
'''
    return dict(selected=b,wrong_gate=b.replace('D_80088B60 == 0','D_80088B60 != 0'),
        wrong_first=b.replace('0x71C','0x720'),wrong_second=b.replace('0x6E8','0x6EC'),
        wrong_zero=b.replace('payload.zero = 0.0f','payload.zero = 1.0f'),
        short_copy=b.replace('&payload, 12','&payload, 8'),
        wrong_command=b.replace('0x57, -1','0x56, -1'),
        wrong_code=b.replace('12, code, value','12, 0, value'),
        wrong_value=b.replace('12, code, value','12, code, 0'),
        missing_latch=b.replace('D_80088B60 = 1','D_80088B60 = 0'),
        latch_on_failure=b.replace(latch,'        D_80088B60 = 1;\n'),
        late_capture=b.replace(capture,'').replace('        if (effect != 0) {',capture+'        if (effect != 0) {',1))


def native_harness():
    text='#include <ultra64.h>\n'+source.ISOLATED_DECLARATIONS+'''
typedef char payload_size[sizeof(OneShotLinkPayload)==12?1:-1];
typedef char second_offset[__builtin_offsetof(OneShotLinkPayload,second)==4?1:-1];
typedef char zero_offset[__builtin_offsetof(OneShotLinkPayload,zero)==8?1:-1];
static union {u32 align[512];u8 bytes[2048];} owner,other;
static union {u32 align[32];u8 bytes[128];} actual,expected;
u8 D_80088B60;u8 *D_800D3098;
static OneShotLinkPayload wanted;
static u32 allocation,mode,error,calls,copies,wantedCode,wantedValue;
__attribute__((noinline,noclone)) void *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,s32 n,u8 code,s32 value){
 u32 i;calls++;
 if(a!=300||b!=-1||c!=0x57||d!=-1||e!=0||f!=0x46||n!=12||code!=wantedCode||(u32)value!=wantedValue||D_80088B60!=0)error=1;
 if(mode&1)D_800D3098=other.bytes;
 if(mode&2)D_80088B60=0x5A;
 if(!allocation)return 0;
 *(s16*)(actual.bytes+14)=300;
 actual.bytes[16]=255;actual.bytes[17]=0x57;actual.bytes[18]=255;actual.bytes[13]=0;actual.bytes[19]=0x46;
 for(i=20;i<36;i++)actual.bytes[i]=0;
 return actual.bytes;
}
__attribute__((noinline,noclone)) void *memcpy(void *dst,const void *src,u32 n){
 u32 i;u8*d=dst;const u8*s=src,*w=(const u8*)&wanted;copies++;
 if(dst!=actual.bytes+40||n!=12||D_80088B60!=1){error=2;return dst;}
 for(i=0;i<12;i++){if(s[i]!=w[i])error=3;d[i]=s[i];}
 return dst;
}
'''
    for name,body in controls().items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef void (*Create)(u8,s32);
static const u32 parameters[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x87654321u};
static const u8 flags[]={0,1,2,127,128,255,85,170};
static int variant(Create fn){
 u32 code,flag,param,a,m,i,repeat,attempt;u8 expectedFlag,*expectedGlobal;
 for(code=0;code<256;code++)for(flag=0;flag<8;flag++)for(param=0;param<6;param++)for(a=0;a<2;a++)for(m=0;m<4;m++){
  for(i=0;i<128;i++)actual.bytes[i]=expected.bytes[i]=(u8)(i*13+code+flag*17);
  D_80088B60=flags[flag];D_800D3098=owner.bytes;allocation=a;mode=m;wantedCode=code;wantedValue=parameters[param];
  for(repeat=0;repeat<2;repeat++){
   attempt=D_80088B60==0;expectedFlag=D_80088B60;expectedGlobal=D_800D3098;
   if(attempt){
    wanted.first=D_800D3098+0x71C;wanted.second=D_800D3098+0x6E8;wanted.zero=0.0f;
    if(m&1)expectedGlobal=other.bytes;if(m&2)expectedFlag=0x5A;
    if(a){
     expectedFlag=1;*(s16*)(expected.bytes+14)=300;
     expected.bytes[16]=255;expected.bytes[17]=0x57;expected.bytes[18]=255;expected.bytes[13]=0;expected.bytes[19]=0x46;
     for(i=20;i<36;i++)expected.bytes[i]=0;
     for(i=0;i<12;i++)expected.bytes[40+i]=((const u8*)&wanted)[i];
    }
   }
   error=calls=copies=0;fn((u8)code,(s32)parameters[param]);
   if(error||calls!=attempt||copies!=(attempt&&a)||D_80088B60!=expectedFlag||D_800D3098!=expectedGlobal)return 23;
   for(i=0;i<128;i++)if(actual.bytes[i]!=expected.bytes[i])return 23;
  }
 }
 return 0;
}
int run(void){
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,i+1)
    return text+' return 0;\n}\n'+START


class OneShotLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        cls.raw,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.ISOLATED_DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        linked,functions=source.link_owner(ROOT,cls.out,cls.raw,source.OWNER)
        cls.words=list(struct.unpack_from('>43I',linked,functions[source.FUNCTION]['value']))
        cls.factory=list(struct.unpack_from('>49I',cls.rom,0x1765E0));cls.copy=list(struct.unpack_from('>11I',cls.rom,0x22EC0))
        cls.cases=list(corpus());cls.receipt={}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')

    def model(self,words,case,phase=0,chain=False,symbols=None,entry=source.ENTRY):
        s=SYMBOLS if symbols is None else symbols;connected={}
        if chain:
            self.assertEqual(s,SYMBOLS)
            connected.update({source.SPAWN+i*4:w for i,w in enumerate(self.factory)})
            connected.update({source.COPY+i*4:w for i,w in enumerate(self.copy)})
        return OneShotOracle(words,fixture(case,s),case,phase,s,entry,connected)

    def compare(self,case,phase=0,chain=False,words=None,symbols=None,entry=source.ENTRY):
        memory=fixture(case,symbols);expected,calls,captured=reference(memory,case,STACK+phase,symbols)
        models=[self.model(w,case,phase,chain,symbols,entry).run()for w in(words or(self.truth,self.words))]
        for model in models:
            self.assertEqual(public(model.memory),public(expected),case)
            observed=[x for x in model.calls if x[0]in((symbols or SYMBOLS)['func_15149130'],(symbols or SYMBOLS)['memcpy'])]
            self.assertEqual(observed,calls);self.assertEqual(model.captured,captured)
            payload=STACK+phase-72+0x3C
            if not case.flag:
                self.assertEqual(bytes(model.memory[payload+i]for i in range(12)),bytes(expected[payload+i]for i in range(12)))
            self.assertEqual(model.r[29],STACK+phase)
            wanted_return=read(expected,STACK+phase-28)
            self.assertEqual(model.escape_target,None if wanted_return==0xDEAD0000 else wanted_return)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_direct_words_bindings_owner_make_and_history(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFB8)
        self.assertEqual(source.payload(self.raw),source.payload(source.original(ROOT,self.out)))
        self.assertEqual(sum(map(len,source.payload(self.raw)[1].values())),8)
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],17)
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        self.receipt.update(exact_words=43,frame=72,bindings=8,new_guards=0,compiler_only=True,preserved_neighbors=17)

    def test_02_guest_all_bytes_failures_aliases_and_retained_helpers(self):
        visits=set();fired=set();count=connected=escaped=0
        for case in self.cases:
            for phase in(0,8):
                for chain in(False,True):
                    model=self.compare(case,phase,chain);visits.update(model.visits);fired.update(model.fired);count+=1
                    connected+=source.COPY in model.visits
                    escaped+=model.escape_target is not None
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+172,4))<=visits)
        self.assertEqual(fired,{'late-global-change','helper-latch-change','private-payload-change'})
        expected=set(range(source.SPAWN,source.SPAWN+196,4))-{0x15149164,0x15149168}
        self.assertTrue(expected<=visits);self.assertTrue(set(range(source.COPY,source.COPY+44,4))<=visits)
        for entry,offset,size in((source.SPAWN,0x1765E0,196),(source.COPY,0x22EC0,44)):
            old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,entry,size)
            self.assertEqual(old[at:at+size],self.rom[offset:offset+size])
        self.receipt.update(guest_phases=count,connected_original_memcpy_phases=connected,retained_helper_words=60,
            visited_factory_words=47,visited_memcpy_words=11,guest_overlap_layouts=6,
            malformed_allocation_return_boundaries=escaped,
            all_target_words_visited=True,allocator_and_bzero_bounded=True,full_allocator_or_hardware_claimed=False)

    def linked(self,obj,entry,symbols,label):
        data,functions,bindings=source.parse_object(obj)
        asm,unknown=emit_function(data,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
        self.assertFalse(unknown);p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%pair for pair in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_03_relocations_and_literal_fault_prefixes(self):
        count=cuts=0
        profiles=((source.ENTRY,SYMBOLS),(0x18017FFC,dict(zip(SYMBOLS,(0x80347FFC,0x80458000,0x18207FFC,0x10318000)))),
                  (0x1A028000,dict(zip(SYMBOLS,(0x80568000,0x80677FFC,0x1B047FF0,0x10128000)))))
        objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_126F60.c.o')
        for i,(entry,symbols)in enumerate(profiles):
            images=[self.linked(obj,entry,symbols,'rebased-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for flag,allocated,mode in itertools.product((0,128),(False,True),range(4)):
                self.compare(Case(flag,0x87654380,0xFFFFFFFF,allocated,mode),8,words=images[:2],symbols=symbols,entry=entry);count+=1
        for flag,allocated,mode,dest in itertools.product((0,255),(False,True),(0,3),(0,2,4)):
            case=Case(flag,0x87654380,0x80000000,allocated,mode,dest,True)
            done=self.model(self.truth,case,8).run()
            for cut in range(done.root_accesses):
                models=[self.model(w,case,8)for w in(self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=count,fired_root_access_prefixes=cuts,
            literal_PC_delay_GPR_FPR_RAM_events=True,portable_C_fault_or_alias_claimed=False)

    def test_04_native32_repeats_and_effective_wrong_C_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_harness())
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            p=subprocess.run([*native_command(opt),str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=196608,native_optimizations=['O0','O2','O3'],
            repeated_latch_and_failure_attempts=True,trap_UBSan=True,effective_wrong_C_controls=11,native_disjoint_typed_storage=True)

    def test_05_both_original_caller_windows_and_void_return(self):
        opcode=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==opcode],[0x528B0,0xCA68C])
        windows=((0x150253FC,0x528AC,0x158,1),(0x1509D1D8,0xCA688,0xC8,0x87654321))
        count=0
        for entry,offset,frame,answer in windows:
            original=list(struct.unpack_from('>5I',self.rom,offset))
            self.assertEqual(original[:3],[0x240400FF,struct.unpack('>I',opcode)[0],0x24050001])
            for flag,allocated,mode,phase in itertools.product((0,255),(False,True),(0,3),(0,8)):
                case=Case(flag,255,1,allocated,mode);initial=fixture(case);sp=STACK+phase-frame;put(initial,sp+0xC4,answer)
                expected,calls,captured=reference(initial,case,sp);models=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                    model=OneShotOracle(original,initial,case,phase,entry=entry,connected=connected)
                    model.r[29]=sp;model.code=WindowCode(model.code,model)
                    with self.assertRaises(WindowBoundary):model.run()
                    self.assertEqual(model.r[2],answer);self.assertEqual(model.r[29],sp)
                    self.assertEqual(public(model.memory),public(expected))
                    self.assertEqual(model.calls,[(source.ENTRY,(255,1)),*calls]);self.assertEqual(model.captured,captured);models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for path,name in(('conker/src/game/generated_50D80.c','func_1502460C'),('conker/src/game/generated_C9EC0.c','func_1509D180')):
            old=self.values[path].decode();lo,hi=source.function_span(old,name)
            self.assertEqual(old[lo:hi],'s32 '+name+'() {\n    return 0;\n}')
        self.receipt.update(original_caller_windows=2,caller_window_words=10,caller_window_phases=count,
            byte_word_arguments_and_void_return=True,full_parent_C_or_other_paths_claimed=False)

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
