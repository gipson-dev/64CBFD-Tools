"""Argument homes, copied payload bytes, result lifetime and bounded caller."""
from dataclasses import dataclass, replace
from pathlib import Path
import itertools, json, struct, subprocess, unittest
from unittest.mock import patch
from tools.experiments import game_parameterized_selector_payload as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_command_stream_relocator import StopCode, WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER, RECORD=0x28000, 0x30020
SYMBOLS={'func_151491F4':0x151491F4,'memcpy':0x10022EC0}
KINDS=(0,1,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF,0x12348765)
FLAGS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)


def half(word): return ((word&65535)^32768)-32768


@dataclass(frozen=True)
class Case:
    kind:int=0x12348765
    selector:int=255
    flags:int=0x87654321
    byte:int=0xA7
    null:bool=False
    allocated:bool=True
    effects:int=0
    alias:int=0
    destination:int=0
    seed:int=0xA5


def actor(case,phase=0):
    return 0 if case.null else (OWNER if not case.alias else
        STACK+phase+(-16 if case.alias==1 else 11)-0x3B)


def result(case): return (RECORD if not case.destination else OWNER) if case.allocated else 0


def fixture(case,phase=0):
    m={STACK+phase+i:(i*17+case.seed)&255 for i in range(-0x600,0x900)}
    for base in (OWNER,RECORD-32):
        m.update({base+i:(i*13+case.seed)&255 for i in range(256)})
    if not case.null and not case.alias:m[OWNER+0x3B]=case.byte
    return m


def public(m): return {a:v for a,v in m.items() if not STACK-0x600<=a<STACK+0x908}


def reference(case,phase,m):
    m=dict(m);owner=actor(case,phase);payload=STACK+phase-16
    if not owner:return public(m),[],0,None
    for i,v in enumerate((owner,case.kind,case.selector,case.flags)):put(m,STACK+phase+i*4,v)
    put(m,payload,owner);byte=m[owner+0x3B];m[payload+4]=byte;put(m,payload+8,0)
    args=(half(case.kind)&0xFFFFFFFF,0xFFFFFFFF,24,1,22,12,case.selector&255,case.flags)
    if case.effects&1:m[owner+0x3B]=0x5A
    if case.effects&2:
        for i in range(3):m[payload+5+i]=0x11+i*0x11
    value=result(case)
    calls=[(SYMBOLS['func_151491F4'],args)]
    captured=bytes(m[payload+i] for i in range(12))
    if value:
        calls.append((SYMBOLS['memcpy'],(value+40,payload,12)))
        for i,v in enumerate(captured):m[value+40+i]=v
    return public(m),calls,value,captured


class PayloadOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,symbols=None,entry=source.ENTRY,connected=None):
        self.case,self.payload_symbols,self.phase=case,SYMBOLS if symbols is None else symbols,phase
        self.payload_owner=actor(case,phase);self.trace=[]
        super().__init__(words,memory,phase=phase,entry=entry,
            arguments=(self.payload_owner,case.kind,case.selector,case.flags),connected=connected)
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        count=4 if target==source.ENTRY else 8 if target==self.payload_symbols['func_151491F4'] else 3
        assert target in (source.ENTRY,*self.payload_symbols.values()),hex(target)
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==self.payload_symbols['func_151491F4']:
            if self.case.effects&1:self.put(self.payload_owner+0x3B,0x5A,1)
            if self.case.effects&2:
                for i in range(3):self.put(self.r[29]+0x2D+i,0x11+i*0x11,1)
            value=result(self.case)
        else:
            assert target==self.payload_symbols['memcpy']
            dst,src,n=self.arguments(3)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        self.r[2]=value


def controls():
    b=source.SELECTED
    return {'selected':b,'wrongKind':b.replace('func_151491F4(lifetime,','func_151491F4(lifetime & 255,'),
        'wrongByte':b.replace('[0x3B]','[0x3A]'),'wrongFloat':b.replace('= 0.0f','= 1.0f'),
        'shortCopy':b.replace('sizeof(payload)','8'),'wrongCommand':b.replace('0x18, 1','0x19, 1'),
        'wrongSelector':b.replace('0xC, selector,','0xC, selector ^ 1,'),
        'wrongReturn':b.replace('return record;','return record == NULL ? NULL : record + 1;'),
        'wrongDestination':b.replace('record + 0x28','record + 0x2C')}


def native_harness():
    bodies='\n'.join(b.replace(source.FUNCTION,name)for name,b in controls().items())
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
static union{u32 align[64];u8 bytes[256];}ownerBlock,recordBlock;
static u8 expectedOwner[256],expectedRecord[256];
static u32 error,calls,copies,nullOwner,allocated,expectKind,expectSelector,expectFlags,expectByte;
__attribute__((noinline,noclone)) void *func_151491F4(s16 kind,s8 a,s8 b,u8 c,u8 d,s32 e,u8 selector,s32 flags){
 calls++;if(nullOwner||calls!=1||(u32)(s32)kind!=expectKind||a!=-1||b!=24||c!=1||d!=22||e!=12||selector!=expectSelector||(u32)flags!=expectFlags)error=1;
 ownerBlock.bytes[0x3B]=expectedOwner[0x3B]=0x5A;
 return allocated?recordBlock.bytes+32:NULL;
}
__attribute__((noinline,noclone)) void *memcpy(void *dst,const void *src,size_t n){
 u32 i;const u8 *s=src;u8 *d=dst;copies++;
 if(n!=12||dst!=recordBlock.bytes+72||*(const u32*)src!=(u32)ownerBlock.bytes||s[4]!=expectByte||*(const f32*)(s+8)!=0.0f)error=2;
 for(i=0;i<n;i++){d[i]=s[i];if(72+i<256)expectedRecord[72+i]=s[i];}
 return dst;
}
'''+bodies+r'''
static int variant(void *(*fn)(u8*,s16,u8,s32)){
 const u32 kinds[]={0,1,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF,0x12348765};
 const u32 sels[]={0,127,128,255},flags[]={0,0x7FFFFFFF,0x80000000,0x87654321};
 u32 k,s,n,a,i,count=0;void *answer;
 for(k=0;k<8;k++)for(s=0;s<4;s++)for(n=0;n<2;n++)for(a=0;a<2;a++){
  for(i=0;i<256;i++){ownerBlock.bytes[i]=expectedOwner[i]=(u8)(i*13+k*31+0xA5);recordBlock.bytes[i]=expectedRecord[i]=0xA5;}
  expectKind=(u32)(s32)(s16)kinds[k];expectSelector=sels[s];expectFlags=flags[s];expectByte=ownerBlock.bytes[0x3B];
  error=calls=copies=0;nullOwner=n;allocated=a;
  answer=fn(n?NULL:ownerBlock.bytes,(s16)kinds[k],(u8)sels[s],(s32)flags[s]);
  if(error||calls!=!n||copies!=(!n&&a))return 20;
  if(answer!=(!n&&a?recordBlock.bytes+32:NULL))return 21;
  for(i=0;i<256;i++)if(ownerBlock.bytes[i]!=expectedOwner[i]||recordBlock.bytes[i]!=expectedRecord[i])return 22;
  count++;
 }
 return count==128?0:23;
}
static int run(void){
 if(variant(selected))return 30;
 if(!variant(wrongKind))return 31;if(!variant(wrongByte))return 32;
 if(!variant(wrongFloat))return 33;if(!variant(shortCopy))return 34;
 if(!variant(wrongCommand))return 35;if(!variant(wrongSelector))return 36;
 if(!variant(wrongReturn))return 37;if(!variant(wrongDestination))return 38;
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class ParameterizedSelectorPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        raw,bindings=source.payload(cls.obj);source.normalized(raw,bindings)
        linked,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        raw=linked[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+168]
        cls.raw=list(struct.unpack('>42I',raw));cls.words=list(struct.unpack('>42I',source.patch_schedule(raw)))
        cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,case=Case(),phase=0,symbols=None,images=None,entry=source.ENTRY):
        m=fixture(case,phase);expected,calls,value,captured=reference(case,phase,m)
        if symbols is not None:calls=[(symbols[next(n for n,v in SYMBOLS.items()if v==t)],args)for t,args in calls]
        models=[PayloadOracle(code,m,case,phase,symbols,entry).run()for code in images or(self.truth,self.words)]
        for a in models:
            self.assertEqual(public(a.memory),expected);self.assertEqual(a.calls,calls);self.assertEqual(a.r[2],value)
            if value and not case.null:self.assertEqual(bytes(a.memory[value+40+i]for i in range(12)),captured)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models
    def test_01_owner_Make_guarded_schedule_and_effective_stub(self):
        self.assertEqual(self.words,self.truth)
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(42,56,2,17,5))
        raw,bindings=source.payload(self.obj)
        self.assertEqual(source.normalized(raw,bindings),source.payload(source.original(ROOT,self.out)))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,168)
        stub=PayloadOracle(struct.unpack_from('>42I',old,at),fixture(Case())).run()
        self.assertFalse(stub.calls);self.assertEqual(stub.r[2],0);self.assertNotEqual(stub.r[2],self.compare()[0].r[2])
        self.receipt.update(words=42,frame=56,bindings=2,new_guards=17,neighbors=5,old_stub_effectively_rejected=True)
    def test_02_arguments_null_failure_padding_aliases_and_raw_public_contract(self):
        count=raw_count=0;seen=set()
        cases=itertools.chain(
            (Case(kind=k,selector=s,flags=FLAGS[i%6],byte=i*73&255,null=n,allocated=a,effects=e)
             for i,(k,s,n,a,e)in enumerate(itertools.product(KINDS,(0,127,128,255,256,0xFFFFFFFF),(False,True),(False,True),(0,3)))),
            (Case(selector=s,byte=255-s,flags=FLAGS[s%6],effects=3)for s in range(256)),
            (Case(alias=a,destination=d,allocated=b,effects=e)for a,d,b,e in itertools.product((1,2),(0,1),(False,True),(0,3))))
        for c in cases:
            for phase in(0,8):
                a=self.compare(c,phase)[0];seen.update(a.visits);count+=1
                raw=PayloadOracle(self.raw,fixture(c,phase),c,phase).run()
                self.assertEqual((public(raw.memory),raw.calls,raw.r[2]),(public(a.memory),a.calls,a.r[2]));raw_count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+168,4)))
        self.receipt.update(guest_phases=count,raw_public_phases=raw_count,all_words_visited=42,
            all_selector_bytes=True,padding_copied_not_zeroed=True,full_guarded_private_state=True,
            raw_private_and_fault_identity_claimed=False)
    def test_03_native32_and_effective_defined_wrong_C(self):
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness())
            built=subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(built.stdout+built.stderr)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_selected_cases_per_optimization=128,native_optimizations=['O0','O2','O3'],
            effective_defined_wrong_C_controls=8,trap_UBSan=True,native_unspecified_padding_observed_not_predicted=True)
    def link_words(self,obj,entry,symbols,label,guarded=False):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+''.join('%s = 0x%X;\n'%x for x in symbols.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(op)],capture_output=True,check=True)
        raw=sections(elf)['.text'][1][:168]
        return list(struct.unpack('>42I',source.patch_schedule(raw)if guarded else raw))
    def test_04_independent_links_and_fired_fault_prefixes(self):
        count=cuts=0;original=source.original(ROOT,self.out)
        for i,entry in enumerate((0x17001000,0x17108000,0x1720FFFC)):
            s={'func_151491F4':0x17300000+i*0x100,'memcpy':0x17400000+i*0x100}
            a=self.link_words(original,entry,s,'original-rebase'+str(i));b=self.link_words(self.obj,entry,s,'C-rebase'+str(i),True)
            self.assertEqual(a,b)
            for null,allocated,phase in itertools.product((False,True),(False,True),(0,8)):
                self.compare(Case(null=null,allocated=allocated,effects=3),phase,s,(a,b),entry);count+=1
        for null,allocated,phase in itertools.product((False,True),(False,True),(0,8)):
            case=Case(null=null,allocated=allocated,effects=3);m=fixture(case,phase)
            good=PayloadOracle(self.truth,m,case,phase).run()
            for cut in range(good.root_accesses):
                models=[PayloadOracle(w,m,case,phase)for w in(self.truth,self.words)]
                for a in models:
                    a.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):a.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,fired_guarded_root_fault_prefixes=cuts,
            portable_C_fault_MMU_or_hardware_claimed=False)
    def test_05_actual_caller_window_and_static_references(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x55310])
        start,stop=0x15027E48,0x15029BA4;window=list(struct.unpack_from('>10I',self.rom,0x552F8));count=0
        for k,s,phase,allocated in itertools.product((0,0x7FFF,0x8000,0xFFFF),(0,128,255),(0,8),(False,True)):
            case=Case(kind=k,selector=s,flags=0,allocated=allocated,effects=3);m=fixture(case,phase)
            put(m,STACK+phase+0x75C,0x20000);put(m,STACK+phase+0x764,OWNER);m[STACK+phase+0x773]=s;models=[]
            for leaf in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(leaf)}
                a=PayloadOracle(window,m,case,phase,entry=start,connected=connected);a.r[2]=0x20000+k
                a.code=StopCode(a.code,a,stop)
                with self.assertRaises(WindowEnd):a.run()
                models.append(a)
            self.assertEqual(complete(models[0]),complete(models[1]));a=models[0]
            self.assertEqual(a.calls[0],(source.ENTRY,(OWNER,half(k)&0xFFFFFFFF,s,0)));self.assertEqual(a.r[2],1);count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x150265CC,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_caller_window_phases=count,actual_difference_sign_extension_byte_selector_zero_flags_and_ignored_return=True,
            parent_150265CC_still_stub=True,full_dispatcher_or_gameplay_claimed=False)
    def test_06_guard_corruptions_closed_permutation_and_no_null_dereference(self):
        raw,bindings=source.payload(self.obj);patches=source.schedule_patches()
        self.assertEqual(len(patches),17);self.assertEqual(sorted(a for a,b in patches.values()),sorted(b for a,b in patches.values()))
        for offset in patches:
            wrong=bytearray(raw);wrong[offset]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(wrong),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        malformed=dict(source.SCHEDULE_LAYOUT);malformed[7]=7
        with patch.object(source,'SCHEDULE_LAYOUT',malformed):
            with self.assertRaises(ValueError):source.schedule_patches()
        for code in(self.truth,self.words,self.raw):
            m=fixture(Case(null=True));m={a:v for a,v in m.items()if a<OWNER or a>=OWNER+256}
            a=PayloadOracle(code,m,Case(null=True)).run();self.assertFalse(a.calls);self.assertEqual(a.r[2],0)
        self.receipt.update(guard_corruption_controls=19,closed_unchanged_word_permutation=True,null_owner_unbacked_read_suppressed=True)
    def test_07_return_survives_real_memcpy_caller_clobbers(self):
        for destination,effects,phase in itertools.product((0,1),range(4),(0,8)):
            case=Case(destination=destination,effects=effects);a=self.compare(case,phase)[0]
            self.assertEqual(a.r[2],result(case));self.assertNotEqual(a.r[2],a.calls[-1][1][0])
            self.assertEqual(read(a.memory,STACK+phase-4),result(case))
        self.receipt.update(return_lifetime_and_copy_destination_phases=16,callee_homes_and_all_call_clobbered_classes=True)
    def test_08_pins_installed_identity_and_whole_image_controls(self):
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom[source.ROM:source.ROM+168])if self.installed and name=='conker/build/conker.us.elf'else source.guard_bytes(old)if self.installed and name=='conker/retail_word_patches.us.csv'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+168];pred=source.predicted_image(before,truth)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,168),source.elf_slot_offset(pred,0x15192920,4),source.elf_slot_offset(pred,0x80082B20,4)):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        self.receipt.update(pinned_inputs=len(self.values),whole_image_corruption_controls=5,old_guard_prefix_and_conversion_rows_preserved=True,metadata_exclusions=0)


if __name__=='__main__':unittest.main()
