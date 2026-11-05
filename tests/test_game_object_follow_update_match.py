"""Timer wrap, tracking, live scale aliases, dispatcher and full-image tests."""

from dataclasses import dataclass
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_object_follow_update_candidates as candidate
from tools.experiments import game_object_follow_update_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT=candidate.ROOT
RECORD,OBJECT,SLOT=0x22000,0x24000,0x26000
TICKS,SCALE,RELEASE=0x800BE9E4,0x800BE9A8,0x1516972C
WINDOW_START,WINDOW_END=0x15167168,0x15167178
PATTERNS=(0,0x80000000,1,0x80000001,0x3F800000,0xC0000000,
          0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)


def sign(value,width=16):
    value &= (1<<width)-1
    return value-(1<<width) if value&(1<<(width-1)) else value


@dataclass(frozen=True)
class Case:
    flags:int=0
    timer:int=1
    ticks:int=1
    active:bool=True
    matching:bool=True
    phase:int=0
    seed:int=0
    layout:int=0


def addresses(case):
    record=(RECORD,SCALE-0x38,SCALE-0x3C,SCALE-0x40,RECORD,RECORD)[case.layout]
    obj=(record+0xC if case.layout==4 else record+0x10 if case.layout==5 else OBJECT)
    return record,obj


def fixture(case):
    record,obj=addresses(case)
    memory={STACK+case.phase+i:(i*17+0xA5)&255 for i in range(-0x200,0x180)}
    for base,size in ((record,0x90),(obj,0x80),(SLOT,4)):
        memory.update({base+i:(i*13+case.seed*7+0x59)&255 for i in range(size)})
    put(memory,record+8,0x12345678)
    put(memory,record+0x18,obj)
    memory[record+0x1C]=0xFF if case.seed&1 else 0
    memory[record+0x1D]=case.flags
    put(memory,record+0x1E,case.timer&65535,2)
    put(memory,obj,1 if case.active else 0)
    memory[obj+0x3B]=memory[record+0x1C]^(0 if case.matching else 1)
    for i in range(3):
        put(memory,record+0x20+4*i,PATTERNS[(case.seed+i)%len(PATTERNS)])
        put(memory,obj+0x14+4*i,PATTERNS[(case.seed+i+4)%len(PATTERNS)])
    put(memory,TICKS,case.ticks&0xFFFFFFFF)
    put(memory,SCALE,(0x3F000000,0x40000000,0xBF800000,0x80000000)[case.seed&3])
    return memory


def public(memory):
    return {at:value for at,value in memory.items() if not STACK-0x200<=at<STACK+0x180}


def reference(initial,record):
    memory=dict(initial)
    remove=False
    if memory[record+0x1D]&1:
        timer=sign((read(memory,record+0x1E,2)-read(memory,TICKS))&65535)
        put(memory,record+0x1E,timer&65535,2)
        remove=timer<0
    obj=read(memory,record+0x18)
    if read(memory,obj)==0 or memory[record+0x1C]!=memory[obj+0x3B]: remove=True
    if not remove:
        previous=tuple(read(memory,record+0x20+4*i) for i in range(3))
        for i,value in enumerate(previous): put(memory,record+0x2C+4*i,value)
        obj=read(memory,record+0x18)
        for i in range(3): put(memory,record+0x20+4*i,read(memory,obj+0x14+4*i))
        for i in range(3):
            difference=bits(floating(read(memory,record+0x2C+4*i))-floating(read(memory,record+0x20+4*i)))
            value=bits(floating(difference)*floating(read(memory,SCALE)))
            put(memory,record+0x38+4*i,value)
    return memory,[(RELEASE,(record,))] if remove else []


class FollowOracle(TimingOracle):
    def __init__(self,words,memory,case,entry=match.ENTRY,connected=None):
        super().__init__(words,memory,phase=case.phase,entry=entry,
                         arguments=(addresses(case)[0],),connected=connected)
        self.retire_snapshots=[]

    def record_call(self,target):
        if target not in (RELEASE,match.ENTRY): raise AssertionError("Unexpected follow helper %08X"%target)
        args=tuple(self.arguments(1))
        self.calls.append((target,args));self.events.append(("CALL",target,args))
        if target==RELEASE:
            self.retire_snapshots.append(bytes(self.memory[args[0]+i] for i in range(0x44)))

    def hook(self,target):
        if target!=RELEASE: raise AssertionError("Missing connected follow callback")
        for i in range(4): self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA6000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


class WindowDone(Exception): pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==WINDOW_END: raise WindowDone
        return super().__getitem__(pc)


def controls():
    replacements={
        "wrong-timer-flag":("flags & 1","flags & 2"),
        "wrong-timer-delta":("(u32)record->timer - (u32)D_800BE9E4","(u32)record->timer + (u32)D_800BE9E4"),
        "zero-timer-expiry":("record->timer < 0","record->timer <= 0"),
        "invert-timer-expiry":("record->timer < 0","record->timer > 0"),
        "wrong-active-field":("*(s32 *)object == 0","*(s32 *)(object + 4) == 0"),
        "wrong-identity":("object[0x3B]","object[0x3A]"),
        "missing-identity-gate":(" || record->objectId != object[0x3B]",""),
        "wrong-current-x":("object + 0x14","object + 0x18"),
        "wrong-current-y":("object + 0x18","object + 0x1C"),
        "wrong-current-z":("object + 0x1C","object + 0x14"),
        "missing-previous-copy":("        record->previous = record->current;\n",""),
        "forward-displacement":("record->previous.unk0 - record->current.unk0","record->current.unk0 - record->previous.unk0"),
        "wrong-scale":("* D_800BE9A8","* 1.0f"),
        "missing-retirement":("func_1516972C(record);","(void)record;"),
        "wrong-retired-pointer":("func_1516972C(record);","func_1516972C(record->object);"),
    }
    result={name:candidate.SELECTED.replace(old,new,1) for name,(old,new) in replacements.items()}
    if any(body==candidate.SELECTED for body in result.values()): raise AssertionError("Ineffective follow control")
    return result


def native_source(body):
    return r'''typedef unsigned char u8; typedef signed short s16; typedef signed int s32;
typedef unsigned int u32; typedef float f32; typedef struct {f32 unk0,unk4,unk8;} struct17;
extern s32 D_800BE9E4;
void func_1516972C(void *);
''' + candidate.DECLARATIONS + body + r'''
s32 D_800BE9E4;
f32 D_800BE9A8;
static ObjectFollowUpdate1515BFA8 *wanted;
static u32 retired,error;
void func_1516972C(void *record) {retired++;if(record!=wanted)error=1;}
static s32 run(void) {
    static const u32 ticks[8]={0,1,2,0xFFFFFFFF,32768,0x7FFFFFFF,0x80000000,65535};
    static const s16 timers[6]={0,1,32767,-1,-32768,32766};
    static const u8 flags[6]={0,1,2,3,0x80,0xFF};
    union {u32 alignment;u8 bytes[0x90];} actual,expected,object;
    u32 seed,i,active,matching,remove;
    ObjectFollowUpdate1515BFA8 *record=(ObjectFollowUpdate1515BFA8 *)actual.bytes;
    ObjectFollowUpdate1515BFA8 *want=(ObjectFollowUpdate1515BFA8 *)expected.bytes;
    if(sizeof(void *)!=4 || sizeof(*record)!=0x44) return 9;
    for(seed=0;seed<4096;seed++) {
        for(i=0;i<0x90;i++) {actual.bytes[i]=(u8)(seed+i*13u);object.bytes[i]=(u8)(seed+i*7u);}
        record->object=object.bytes;record->objectId=0xA7;
        record->flags=flags[seed%6];record->timer=timers[(seed/6)%6];
        active=(seed>>4)&1;matching=(seed>>5)&1;
        *(s32 *)object.bytes=active?1:0;object.bytes[0x3B]=matching?0xA7:0xA6;
        record->current.unk0=(f32)(seed%31)+0.25f;
        record->current.unk4=-(f32)(seed%23)-0.5f;
        record->current.unk8=(f32)(seed%17)+0.75f;
        ((f32 *)(object.bytes+0x14))[0]=-(f32)(seed%11)-0.25f;
        ((f32 *)(object.bytes+0x14))[1]=(f32)(seed%13)+0.5f;
        ((f32 *)(object.bytes+0x14))[2]=-(f32)(seed%19)-0.75f;
        D_800BE9E4=(s32)ticks[(seed>>6)&7];
        D_800BE9A8=(seed&1)?0.5f:-2.0f;
        for(i=0;i<0x90;i++) expected.bytes[i]=actual.bytes[i];
        remove=0;
        if(want->flags&1) {want->timer=(s16)((u32)want->timer-(u32)D_800BE9E4);if(want->timer<0)remove=1;}
        if(!active || !matching) remove=1;
        if(!remove) {
            f32 *cur=&want->current.unk0,*prev=&want->previous.unk0,*vel=&want->velocity.unk0;
            for(i=0;i<3;i++) prev[i]=cur[i];
            for(i=0;i<3;i++) cur[i]=((f32 *)(object.bytes+0x14))[i];
            for(i=0;i<3;i++) vel[i]=(prev[i]-cur[i])*D_800BE9A8;
        }
        wanted=record;retired=error=0;
        func_1515BFA8(record);
        if(retired!=remove || error) return 10;
        for(i=0;i<0x90;i++) if(actual.bytes[i]!=expected.bytes[i]) return 11;
    }
    return 0;
}
void _start(void) {s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label,body,optimization,should_pass):
    output=ROOT/match.BUILD/"native";output.mkdir(parents=True,exist_ok=True)
    source,binary=output/(label+".c"),output/(label+".elf")
    source.write_text(native_source(body))
    result=subprocess.run(["gcc","-m32","-std=gnu89",optimization,"-fno-pie","-no-pie",
        "-ffreestanding","-fno-strict-aliasing","-fno-stack-protector","-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error","-Wall","-Wextra","-Werror","-nostdlib",
        str(source),"-o",str(binary)],capture_output=True,text=True)
    if result.returncode: raise AssertionError(result.stdout+result.stderr)
    executed=subprocess.run([str(binary)],timeout=30)
    if should_pass!=(executed.returncode==0): raise AssertionError((label,executed.returncode))


class ObjectFollowUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=match.prepare(ROOT);cls.out=ROOT/match.BUILD
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM))
        selected=candidate.compare()
        if selected["differences"] or selected["words"]!=68: raise AssertionError(selected)
        cls.natural=cls.retail.copy()

    def receipt(self,name,value):
        (self.out/(name+".json")).write_text(json.dumps(value,indent=2)+"\n")

    def compare(self,case):
        initial=fixture(case);record,_=addresses(case)
        expected,calls=reference(initial,record)
        models=[]
        for words in (self.retail,self.natural):
            model=FollowOracle(words,initial,case).run()
            self.assertEqual(public(model.memory),public(expected),case)
            self.assertEqual(model.calls,calls,case)
            if calls:self.assertEqual(model.retire_snapshots,[bytes(expected[record+i] for i in range(0x44))])
            models.append(model)
        return models

    def test_01_natural_owner_registry_and_literal_image(self):
        report=self.prepared["report"]
        self.assertEqual((report["words"],report["guards"],report["neighbors"],report["relocations"]),(68,0,10,5))
        self.assertEqual(report["changed_bodies"],[match.FUNCTION])
        self.assertTrue(report["literal_full_image_prediction"])
        self.assertEqual(report["strict_changed_bytes"],202)
        self.assertEqual(report["registry"]["registry"],"D_8008B4A8[0x32].unk0")
        before,after=self.prepared["predecessor_elf"].read_bytes(),self.prepared["qualified_elf"].read_bytes()
        for at in (0x80,elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+match.SIZE])

    def test_02_timer_wrap_liveness_identity_floats_and_all_words(self):
        coverage=[set(),set()];count=0
        for flags,timer,ticks,active,matching,phase in itertools.product(
            (0,1,2,3,0x80,255),(0,1,32767,-1,-32768,32766),
            (0,1,2,-1,32768,0x7FFFFFFF,-0x80000000),(False,True),(False,True),(0,8)):
            case=Case(flags,timer,ticks,active,matching,phase,count)
            for i,model in enumerate(self.compare(case)):coverage[i].update(model.visits)
            count+=1
        full=set(range(match.ENTRY,match.ENTRY+match.SIZE,4))
        self.assertEqual(coverage,[full,full])
        self.receipt("guest-contract",{"cases_per_body":count,"covered_words":68,
            "timer_wrap_bits":16,"ticks_cover_signed_word_extremes":True,
            "float_patterns":"signed zero, subnormal, finite extrema, infinities and quiet NaN"})

    def test_03_aliases_live_scale_reads_and_cached_control(self):
        count=0
        for layout,phase,seed in itertools.product(range(6),(0,8),range(4)):
            self.compare(Case(phase=phase,seed=seed,layout=layout));count+=1
        # Exact original words reload SCALE between stores; a cached scalar is observably different.
        body=candidate.SELECTED.replace("    u8 *object;", "    u8 *object;\n    f32 scale;",1).replace(
            "        record->velocity.unk0 =",
            "        scale = D_800BE9A8;\n        record->velocity.unk0 =",1).replace("* D_800BE9A8","* scale")
        output=ROOT/candidate.BUILD
        obj,_=compile_owner(ROOT,output,candidate.source_with(body),"cached-scale-control")
        linked,functions=link_owner(ROOT,output,obj,candidate.OWNER)
        info=functions[match.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info["size"]//4),linked,info["value"]))
        case=Case(layout=1);initial=fixture(case);record,_=addresses(case)
        for i,value in enumerate((10.0,-20.0,30.0)):put(initial,record+0x20+4*i,bits(value))
        for i,value in enumerate((1.0,2.0,3.0)):put(initial,OBJECT+0x14+4*i,bits(value))
        put(initial,SCALE,bits(.5))
        wanted,_=reference(initial,record)
        control=FollowOracle(words,initial,case).run()
        self.assertNotEqual(public(control.memory),public(wanted))
        self.receipt("aliases",{"cases_per_body":count,"record_scale_and_object_overlap_layouts":6,
            "compiled_cached_scale_control_rejected":True})

    def test_04_native32_and_effective_controls(self):
        for optimization in ("-O0","-O2","-O3"):
            run_native("positive"+optimization[1:],candidate.SELECTED,optimization,True)
        for name,body in controls().items():run_native("control-"+name,body,"-O2",False)
        self.receipt("native-contract",{"profiles":["O0","O2","O3"],"cases_per_profile":4096,"controls":sorted(controls())})

    def test_05_fault_boundaries_and_original_dispatch_window(self):
        observations=[]
        for case in (Case(),Case(flags=1,timer=0),Case(active=False),Case(matching=False),Case(flags=1,timer=32767,ticks=-1)):
            initial=fixture(case)
            for words in (self.retail,self.natural):
                baseline=FollowOracle(words,initial,case).run()
                for cut in range(baseline.root_accesses):
                    model=FollowOracle(words,initial,case);model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(model.root_accesses,cut)
                    observations.append((model.current_pc,model.delay_of,cut))
        window=list(struct.unpack_from('>4I',self.rom,WINDOW_START-0x15000000+0x2D4B0))
        target={match.ENTRY+i*4:word for i,word in enumerate(self.retail)}|{WINDOW_END:0}
        count=0
        for active,matching,expired,phase in itertools.product((False,True),(False,True),(False,True),(0,8)):
            case=Case(flags=1 if expired else 0,timer=0,active=active,matching=matching,phase=phase)
            initial=fixture(case);expected,calls=reference(initial,RECORD)
            put(expected,SLOT,read(initial,RECORD+8))
            model=FollowOracle(window,initial,case,WINDOW_START,target)
            model.r[16],model.r[17],model.r[25]=RECORD,SLOT,match.ENTRY
            model.before=model.r.copy();model.code=WindowCode(model.code,model)
            with self.assertRaises(WindowDone):model.run()
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.calls,[(match.ENTRY,(RECORD,))]+calls)
            self.assertEqual(model.r[16],RECORD);self.assertEqual(model.r[17],SLOT)
            count+=1
        self.receipt("faults-and-caller",{"fault_observations":len(observations),
            "unique_boundaries":len(set(observations)),"caller_cases":count,"original_jalr":"0x15167170"})


if __name__=="__main__":unittest.main()
