"""Four-entry loader: variadic ABI, unsigned counts, late writes and literal frames."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_four_entry_loader as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
POINTERS,COUNTS,BASE,CLEAR,INIT=0x800DC280,0x800DC290,0xAB1950,0x800894B0,0x1512ABF8
SYMBOLS={'D_800DC280':POINTERS,'D_800DC290':COUNTS,'func_1502B5C8':source.LOAD}
VALUES=tuple(range(24))+(24,25,47,48,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xFFFFFFFE)
RETURNS=(0x30000,0x80000000,0xFFFFFFFF,1)


@dataclass(frozen=True)
class Case:
    pattern:int=0
    nulls:int=0
    mode:int=0
    missing_stage:int=0
    missing:int=0
    seed:int=0xA5


def size(case,index):
    return VALUES[(case.pattern+index*7)%32]


def result(case,index):
    return 0 if case.nulls>>index&1 else RETURNS[(case.pattern+index)%4]


def fixture(case,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    memory={STACK+i:(i*17+case.seed)&255 for i in range(-1024,256)}
    for base in(s['D_800DC280'],s['D_800DC290'],CLEAR):
        for i in range(-16,32):
            if not STACK-1024<=base+i<STACK+256:memory[base+i]=(i*13+case.seed)&255
    return memory


def mutate(memory,index,mode,symbols):
    if mode&1:
        slot=(index+3)%4;put(memory,symbols['D_800DC280']+slot*4,0x87654321)
        put(memory,symbols['D_800DC290']+slot*4,0x80000000|index)
    if mode&2:
        slot=(index+1)%4;put(memory,symbols['D_800DC280']+slot*4,0)
        put(memory,symbols['D_800DC290']+slot*4,0xFFFFFFFF-index)


def reference(initial,case,entered=STACK,symbols=None,chain=False):
    s=SYMBOLS if symbols is None else symbols
    memory=dict(initial);calls=[];home=entered-4
    for index in range(4):
        calls.append((s['func_1502B5C8'],(home,2,27,index)))
        mutate(memory,index,case.mode,s)
        missing=chain and case.missing_stage and case.missing>>index&1
        value=0 if missing else size(case,index);answer=0 if missing else result(case,index)
        put(memory,home,value)
        # Retail captures size before its first output store, even for guest aliases.
        quotient=value//24
        put(memory,s['D_800DC280']+index*4,answer)
        put(memory,s['D_800DC290']+index*4,quotient)
    return memory,calls


def view(memory,symbols):
    outputs={base+i for base in(symbols['D_800DC280'],symbols['D_800DC290'])for i in range(16)}
    return {a:b for a,b in memory.items()if not STACK-1024<=a<STACK+256 or a in outputs}


class LoaderOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,symbols=None,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,
            arguments=(0xFFFFFFFF,0x80000000,0x87654321,0xABCDEF01),connected=connected)
        self.case=case;self.loader_symbols=SYMBOLS if symbols is None else symbols
        self.entered=STACK+phase;self.loads=0;self.stage=0;self.slot=-1

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered=self.r[29];args=()
        elif target==INIT:args=()
        elif target==self.loader_symbols['func_1502B5C8']:
            args=self.arguments(4);assert args==(self.entered-4,2,27,self.loads)
            self.slot=self.loads;self.loads+=1;self.stage=0
        elif target==source.LOOKUP:
            args=self.arguments(3);index=self.slot
            assert args[:2]==((BASE,27)if self.stage==0 else(BASE+0x20+index*4,index))
            assert args[2]==self.entered-64-80+0x38
        elif target==source.FETCH:
            args=self.arguments(3)
            assert args==(BASE+0x20+self.slot*4+0x40+self.slot*8,0xC0000040,self.entered-4)
        else:raise AssertionError(('unbounded four-entry helper',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target==INIT:
            put(self.memory,self.loader_symbols['D_800DC280'],0xDEADBEEF)
            put(self.memory,self.loader_symbols['D_800DC290']+12,0xABCD1234)
            put(self.memory,CLEAR,0xFFFFFFFF);value=0xA5000002
        elif target==self.loader_symbols['func_1502B5C8']:
            mutate(self.memory,self.slot,self.case.mode,self.loader_symbols)
            self.put(self.entered-4,size(self.case,self.slot),4);value=result(self.case,self.slot)
        elif target==source.LOOKUP:
            _,_,out=self.arguments(3);index=self.slot
            if self.stage==0:
                mutate(self.memory,index,self.case.mode,self.loader_symbols)
                descriptor=0 if self.case.missing_stage==1 and self.case.missing>>index&1 else 0xB0000040
                value=0x20+index*4;self.stage=1
            else:
                descriptor=0 if self.case.missing_stage==2 and self.case.missing>>index&1 else 0xC0000040
                value=0x40+index*8;self.stage=2
            self.put(out,descriptor,4)
        else:
            assert target==source.FETCH
            self.put(self.arguments(3)[2],size(self.case,self.slot),4);value=result(self.case,self.slot)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==0x15005458:raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    b=source.SELECTED
    return dict(selected=b,three=b.replace('index < 4','index < 3'),five=b.replace('index < 4','index < 5'),
        signed_division=b.replace('(u32)size / 24','size / 24'),
        wrong_divisor=b.replace('/ 24','/ 12'),wrong_depth=b.replace('&size, 2,','&size, 1,'),
        wrong_path=b.replace('2, 27, index','2, 26, index'),wrong_index=b.replace('27, index','27, 0'),
        first_slot=b.replace('D_800DC280[index]','D_800DC280[0]'),
        keep_count=b.replace('        D_800DC290[index] = (u32)size / 24;',''),
        null_return=b.replace('D_800DC280[index] = func_1502B5C8(&size, 2, 27, index);',
                              'func_1502B5C8(&size, 2, 27, index); D_800DC280[index] = 0;'),
        gate_count=b.replace('        D_800DC290[index] = (u32)size / 24;',
                            '        if (D_800DC280[index] != 0) D_800DC290[index] = (u32)size / 24;'))


def native_harness(helper):
    text='#include <ultra64.h>\n#include <stdarg.h>\n#include <stddef.h>\n'+source.ISOLATED_DECLARATIONS+'''
static struct {u32 left[4];void *pointers[5];s32 counts[5];u32 right[4];} actual,expected;
#define D_800DC280 actual.pointers
#define D_800DC290 actual.counts
static u8 D_AB1950[2048],blocks[5][4];
static u32 values[5],nulls,mode,missingStage,missingMask,error,calls,stage,slot,fetches;
static s32 *sizeHome;
s32 func_1502AC88(u32 base,s32 component,u32 *descriptor){
 u32 value;
 if(stage==0){
  slot=calls++;if(slot>4){error=1;slot=4;}
  if(base!=(u32)D_AB1950||component!=27)error=2;
  if(mode&1){u32 j=(slot+3)%4;actual.pointers[j]=blocks[4];actual.counts[j]=(s32)(0x80000000u|slot);}
  if(mode&2){u32 j=(slot+1)%4;actual.pointers[j]=0;actual.counts[j]=(s32)(0xFFFFFFFFu-slot);}
  *descriptor=(missingStage==1&&(missingMask>>slot&1))?0:0xB0000040u;
  stage=*descriptor?1:0;value=0x20+slot*4;
 }else{
  if(component!=(s32)slot||base!=(u32)D_AB1950+0x20+slot*4)error=3;
  *descriptor=(missingStage==2&&(missingMask>>slot&1))?0:0xC0000040u;
  stage=0;value=0x40+slot*8;
 }
 return(s32)value;
}
void *func_1502B350(u32 base,u32 descriptor,s32 *size){
 fetches++;if(base!=(u32)D_AB1950+0x60+slot*12||descriptor!=0xC0000040u)error=4;
 if(sizeHome&&sizeHome!=size)error=5;sizeHome=size;*size=(s32)values[slot];
 return nulls>>slot&1?0:blocks[slot];
}
'''+helper+'\n'
    for name,body in controls().items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef void (*Initialize)(void);
static const u32 words[]={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,47,48,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0xFFFFFFFEu};
static int variant(Initialize fn){
 u32 seed,pattern,n,m,missing,i,j,wantedFetches;u8 *p=(u8*)&actual,*q=(u8*)&expected;
 for(seed=0;seed<16;seed++)for(pattern=0;pattern<32;pattern++)for(n=0;n<16;n++)for(m=0;m<4;m++)for(missing=0;missing<3;missing++){
  for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*17+seed);
  for(i=0;i<5;i++)values[i]=words[(pattern+i*7+seed)%32];
  nulls=n;mode=m;missingStage=missing;missingMask=(seed^n)&15;error=calls=stage=fetches=0;sizeHome=0;wantedFetches=0;
  for(i=0;i<4;i++){
   if(m&1){j=(i+3)%4;expected.pointers[j]=blocks[4];expected.counts[j]=(s32)(0x80000000u|i);}
   if(m&2){j=(i+1)%4;expected.pointers[j]=0;expected.counts[j]=(s32)(0xFFFFFFFFu-i);}
   if(missing&&(missingMask>>i&1)){expected.pointers[i]=0;expected.counts[i]=0;}
   else{wantedFetches++;expected.pointers[i]=n>>i&1?0:blocks[i];expected.counts[i]=(s32)(values[i]/24);}
  }
  fn();if(error||calls!=4||stage||fetches!=wantedFetches)return 23;
  for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,i+1)
    return text+' return 0;\n}\n'+START


class FourEntryLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        cls.raw,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.ISOLATED_DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.out,cls.raw,source.OWNER)
        cls.words=list(struct.unpack_from('>43I',data,functions[source.FUNCTION]['value']))
        cls.loader=list(struct.unpack_from('>61I',cls.rom,0x58A78));cls.receipt={}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')

    def compare(self,case,phase=0,chain=False,images=None,symbols=None,entry=source.ENTRY):
        s=SYMBOLS if symbols is None else symbols;memory=fixture(case,s)
        expected,calls=reference(memory,case,STACK+phase,s,chain)
        connected={source.LOAD+i*4:w for i,w in enumerate(self.loader)}if chain else None
        models=[LoaderOracle(w,memory,case,phase,s,entry,connected).run()for w in(images or(self.truth,self.words))]
        for model in models:
            self.assertEqual(view(model.memory,s),view(expected,s),case)
            self.assertEqual([x for x in model.calls if x[0]==s['func_1502B5C8']],calls)
            self.assertEqual(model.r[29],STACK+phase);self.assertEqual(model.loads,4)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_words_bindings_owner_make_and_history(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFC0)
        self.assertEqual(source.payload(self.raw),source.payload(source.original(ROOT,self.out)))
        self.assertEqual(sum(map(len,source.payload(self.raw)[1].values())),5)
        source.check_inputs(ROOT,self.out,installed=self.installed)
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],5)
        self.receipt.update(exact_words=43,frame=64,bindings=5,new_guards=0,compiler_only=True,preserved_neighbors=5)

    def test_02_guest_variadic_helper_mutations_and_unsigned_counts(self):
        visits=set();ordinary=connected=0
        for pattern,nulls,mode,phase in itertools.product(range(32),range(16),range(4),(0,8)):
            model=self.compare(Case(pattern,nulls,mode),phase);visits.update(model.visits);ordinary+=1
        for pattern,stage,missing,nulls,mode,phase in itertools.product(range(32),range(3),(0,5,15),(0,15),(0,3),(0,8)):
            model=self.compare(Case(pattern,nulls,mode,stage,missing),phase,True);visits.update(model.visits);connected+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+172,4))-{0x1512D2B0}<=visits)
        self.assertNotIn(0x1512D2B0,visits)
        self.assertTrue(set(range(source.LOAD,source.LOAD+244,4))<=visits)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.LOAD,244)
        self.assertEqual(before[at:at+244],self.rom[0x58A78:0x58A78+244])
        self.receipt.update(ordinary_guest_phases=ordinary,connected_helper_phases=connected,retained_helper_words=61,
            loader_frame=80,visited_helper_words=61,root_visited_words=42,unreachable_divisor_break_retained=True,
            lookup_and_fetch_providers_bounded=True,full_asset_pipeline_claimed=False)

    def linked(self,obj,entry,symbols,label):
        data,functions,bindings=source.parse_object(obj)
        asm,unknown=emit_function(data,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
        self.assertFalse(unknown);p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_03_independent_rebases_output_private_aliases_and_fault_prefixes(self):
        profiles=[(source.ENTRY,SYMBOLS,0),(0x18017FFC,dict(zip(SYMBOLS,(0x80347FFC,0x80458000,0x18207FFC))),8),
                  (0x1A028000,dict(zip(SYMBOLS,(0x80568000,0x80677FFC,0x1B047FF0))),0)]
        for phase in(0,8):
            profiles.extend((0x19000000,dict(zip(SYMBOLS,(a,b,source.LOAD))),phase)for a,b in
                ((POINTERS,POINTERS),(POINTERS,POINTERS+4),(STACK+phase-4,COUNTS),(POINTERS,STACK+phase-4)))
        objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_159940.c.o')
        count=cuts=0
        for i,(entry,symbols,phase)in enumerate(profiles):
            images=[self.linked(obj,entry,symbols,'rebased-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for pattern,nulls,mode in itertools.product((0,23,28,31),(0,15),(0,3)):
                self.compare(Case(pattern,nulls,mode),phase,images=images[:2],symbols=symbols,entry=entry);count+=1
        for pattern,nulls,mode,phase in itertools.product((0,23,28,31),(0,15),(0,3),(0,8)):
            case=Case(pattern,nulls,mode);memory=fixture(case)
            done=LoaderOracle(self.truth,memory,case,phase).run();self.assertEqual(done.root_accesses,26)
            for cut in range(done.root_accesses):
                models=[LoaderOracle(w,memory,case,phase)for w in(self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=len(profiles)*3,rebase_and_alias_phases=count,fired_root_access_prefixes=cuts,
            guest_output_and_private_size_aliases=True,portable_C_alias_or_fault_claimed=False)

    def test_04_native32_actual_variadic_C_helper_and_effective_controls(self):
        text=self.values['conker/src/game_57FA0.c'].decode();lo,hi=source.function_span(text,'func_1502B5C8')
        unit=self.out/'native32.c';unit.write_text(native_harness(text[lo:hi]))
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            p=subprocess.run([*native_command(opt),str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_calls_per_optimization=98304,native_optimizations=['O0','O2','O3'],
            actual_variadic_helper_C_body=True,depth_two_only=True,effective_wrong_C_controls=11,trap_UBSan=True,
            native_disjoint_typed_storage=True)

    def test_05_actual_caller_window_and_no_argument_interface(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));literal=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x328F8])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==literal],[])
        window=list(struct.unpack_from('>6I',self.rom,0x328F0))
        self.assertEqual(window,[0x0D44AAFE,0,struct.unpack('>I',jal)[0],0,0x3C018009,0xAC2094B0])
        count=0
        for pattern,nulls,mode,phase in itertools.product((0,23,28,31),(0,15),(0,3),(0,8)):
            case=Case(pattern,nulls,mode);initial=fixture(case);sp=STACK+phase-0x70;before=dict(initial)
            put(before,POINTERS,0xDEADBEEF);put(before,COUNTS+12,0xABCD1234);put(before,CLEAR,0xFFFFFFFF)
            expected,calls=reference(before,case,sp);put(expected,CLEAR,0);models=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                model=LoaderOracle(window,initial,case,phase,entry=0x15005440,connected=connected)
                model.r[29]=sp;model.code=WindowCode(model.code,model)
                with self.assertRaises(WindowBoundary):model.run()
                self.assertEqual(model.r[29],sp);self.assertEqual(view(model.memory,SYMBOLS),view(expected,SYMBOLS))
                self.assertEqual(model.calls,[(INIT,()),(source.ENTRY,()),*calls]);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        old=self.values['conker/src/game_32740.c'].decode();lo,hi=source.function_span(old,'func_15005290')
        self.assertEqual(old[lo:hi],'s32 func_15005290() {\n    return 0;\n}')
        self.receipt.update(original_caller_window_words=6,caller_phases=count,no_argument_void_interface=True,
            prior_initializer_bounded=True,full_parent_C_or_other_paths_claimed=False)

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
