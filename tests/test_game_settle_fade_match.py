"""Wrapped motion, signed spin, landing, word-wrap fade and callback checks."""

from dataclasses import dataclass
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_settle_fade_candidates as candidate
from tools.experiments import game_settle_fade_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_object_follow_update_match import WindowCode, WindowDone


ROOT=candidate.ROOT
RECORD,SLOT,TICKS,RELEASE=0x22000,0x26000,0x800BE9E4,0x1516972C
WINDOW_START,WINDOW_END=0x15167168,0x15167178
VALUES=(-32768,-32767,-1,0,1,32766,32767)
SPINS=(-128,-127,-1,0,1,126,127)
MOTION=((10,0,0),(10,1,0),(10,2,0),(1,-1,0),(1,-3,0),
        (-32768,-1,-32768),(32767,1,32767),(32767,-32768,0))


def sign(value,width=16):
    value &= (1<<width)-1
    return value-(1<<width) if value&(1<<(width-1)) else value


@dataclass(frozen=True)
class Case:
    timer:int=0
    ticks:int=1
    mode:int=0
    seed:int=0
    phase:int=0
    layout:int=0


def address(case):
    return (RECORD,TICKS-0x90,TICKS-0xA4,TICKS-0xA6)[case.layout]


def fixture(case):
    record=address(case)
    memory={STACK+case.phase+i:(i*17+0xA5)&255 for i in range(-0x200,0x180)}
    memory.update({record+i:(i*13+case.seed*7+0x59)&255 for i in range(0xB8)})
    memory.update({SLOT+i:0xA5 for i in range(4)})
    put(memory,record+8,0x12345678)
    for i,offset in enumerate((0x90,0x94,0x96,0x98,0x9A,0xA0,0xA4)):
        put(memory,record+offset,VALUES[(case.seed+i)%len(VALUES)]&65535,2)
    y,vy,floor=MOTION[case.mode]
    for offset,value in ((0x92,y),(0xA2,vy),(0xB0,floor),(0xA6,case.timer)):
        put(memory,record+offset,value&65535,2)
    for i in range(3):memory[record+0x9C+i]=SPINS[(case.seed+i)%len(SPINS)]&255
    put(memory,TICKS,case.ticks&0xFFFFFFFF)
    return memory


def public(memory):
    return {at:value for at,value in memory.items() if not STACK-0x200<=at<STACK+0x180}


def reference(initial,record):
    memory=dict(initial);calls=[]
    remaining=read(memory,record+0xA6,2)
    def half(offset):return sign(read(memory,record+offset,2))
    def store(offset,value):put(memory,record+offset,value&65535,2)
    if remaining==0:
        for offset in (0x90,0x92,0x94):store(offset,half(offset)+half(offset+0x10))
        if half(0xA2)>0:
            store(0xA2,half(0xA2)-1)
            if half(0xA2)<=0:store(0xA2,-3)
        if half(0x92)-half(0xB0)<=0:
            store(0x96,90);store(0x9A,0);store(0xA6,60);store(0x92,half(0xB0))
        else:
            for i in range(3):store(0x96+2*i,half(0x96+2*i)+sign(memory[record+0x9C+i],8))
    else:
        remaining=sign(remaining-read(memory,TICKS),32)
        if remaining>0:
            store(0xA6,remaining)
            shifted=sign(remaining<<8,32)
            opacity=(abs(shifted)//60)*(-1 if shifted<0 else 1)
            memory[record+0xB3]=opacity&255
        else:calls=[(RELEASE,(record,))]
    return memory,calls


class SettleOracle(TimingOracle):
    def __init__(self,words,memory,case,entry=match.ENTRY,connected=None):
        super().__init__(words,memory,phase=case.phase,entry=entry,
                         arguments=(address(case),),connected=connected)
        self.retire_snapshots=[]

    def execute(self,word):
        if word>>26==32:
            rs,rt=(word>>21)&31,(word>>16)&31
            at=(self.r[rs]+sign(word&65535))&0xFFFFFFFF
            self.r[rt]=sign(self.get(at,1),8)&0xFFFFFFFF
            self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        if target not in (RELEASE,match.ENTRY):raise AssertionError("Unexpected settle helper %08X"%target)
        args=tuple(self.arguments(1))
        self.calls.append((target,args));self.events.append(("CALL",target,args))
        if target==RELEASE:self.retire_snapshots.append(bytes(self.memory[args[0]+i] for i in range(0xB8)))

    def hook(self,target):
        if target!=RELEASE:raise AssertionError("Missing connected settle callback")
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA6000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def controls():
    replacements={
        "signed-timer":("s32 remaining = record->timer;","s32 remaining = (s16)record->timer;"),
        "wrong-moving-gate":("if (remaining == 0)","if (remaining == 1)"),
        "wrong-x-speed":("record->x += record->speedX","record->x += record->speedZ"),
        "wrong-y-direction":("record->y += record->speedY","record->y -= record->speedY"),
        "wrong-z-speed":("record->z += record->speedZ","record->z += record->speedX"),
        "zero-speed-deceleration":("record->speedY > 0","record->speedY >= 0"),
        "wrong-deceleration":("record->speedY--;","record->speedY++;"),
        "missing-negative-speed":("record->speedY = -3;","record->speedY = 0;"),
        "floor-equality-rejection":("if (remaining <= 0)","if (remaining < 0)"),
        "wrong-landing-angle":("record->angleX = 90","record->angleX = 89"),
        "missing-landing-z-clear":("record->angleZ = 0","record->angleZ = 1"),
        "wrong-landing-lifetime":("record->timer = 60","record->timer = 59"),
        "missing-floor-clamp":("record->y = record->floorY","record->y = record->floorY + 1"),
        "unsigned-spin":("record->angleX += record->spinX","record->angleX += (u8)record->spinX"),
        "wrong-y-spin":("record->angleY += record->spinY","record->angleY += record->spinZ"),
        "wrong-z-spin":("record->angleZ += record->spinZ","record->angleZ += record->spinX"),
        "wrong-tick-direction":("(u32)remaining - (u32)D_800BE9E4","(u32)remaining + (u32)D_800BE9E4"),
        "zero-fade-survives":("if (remaining > 0)","if (remaining >= 0)"),
        "wrong-fade-denominator":("<< 8) / 60","<< 8) / 59"),
        "wrong-fade-shift":("remaining << 8","remaining << 7"),
        "unsigned-fade-division":("(s32)((u32)remaining << 8) / 60","((u32)remaining << 8) / 60"),
        "missing-retirement":("func_1516972C(record);","(void)record;"),
        "wrong-retired-pointer":("func_1516972C(record);","func_1516972C((u8 *)record + 4);"),
    }
    result={name:candidate.SELECTED.replace(old,new,1) for name,(old,new) in replacements.items()}
    if any(body==candidate.SELECTED for body in result.values()):raise AssertionError("Ineffective settle control")
    return result


def native_source(body):
    return r'''typedef unsigned char u8;typedef signed char s8;typedef signed short s16;
typedef unsigned short u16;typedef signed int s32;typedef unsigned int u32;
''' + candidate.DECLARATIONS + body + r'''
s32 D_800BE9E4;
static SettleFade1517A84C *wanted;
static u32 retired,error;
void func_1516972C(void *record){retired++;if(record!=wanted)error=1;}
static s32 run(void) {
    static const u16 timers[11]={0,1,2,59,60,61,255,256,32767,32768,65535};
    static const u32 ticks[15]={0,1,2,59,60,61,0xFFFFFFFF,0x7FFFFFFF,0x80000000,65535,
        0xFF800001,0xFF800000,0xFF000001,0xFF000000,0x80010000};
    static const s16 values[7]={-32768,-32767,-1,0,1,32766,32767};
    static const s8 spins[7]={-128,-127,-1,0,1,126,127};
    static const s16 motion[8][3]={{10,0,0},{10,1,0},{10,2,0},{1,-1,0},{1,-3,0},
        {-32768,-1,-32768},{32767,1,32767},{32767,-32768,0}};
    union {u32 alignment;u8 bytes[0xB8];} actual,expected;
    SettleFade1517A84C *r=(SettleFade1517A84C *)actual.bytes;
    SettleFade1517A84C *w=(SettleFade1517A84C *)expected.bytes;
    u32 seed,i,remove; s32 remaining,mode;
    if(sizeof(void *)!=4 || sizeof(*r)!=0xB4)return 9;
    for(seed=0;seed<4096;seed++) {
        for(i=0;i<0xB8;i++)actual.bytes[i]=(u8)(seed+i*13u);
        r->timer=timers[seed%11];D_800BE9E4=(s32)ticks[(seed/11)%15];mode=(seed/165)%8;
        r->x=values[seed%7];r->z=values[(seed+1)%7];
        r->angleX=values[(seed+2)%7];r->angleY=values[(seed+3)%7];r->angleZ=values[(seed+4)%7];
        r->speedX=values[(seed+5)%7];r->speedZ=values[(seed+6)%7];
        r->y=motion[mode][0];r->speedY=motion[mode][1];r->floorY=motion[mode][2];
        r->spinX=spins[seed%7];r->spinY=spins[(seed+1)%7];r->spinZ=spins[(seed+2)%7];
        for(i=0;i<0xB8;i++)expected.bytes[i]=actual.bytes[i];
        remove=0;
        if(!w->timer) {
            w->x=(s16)(w->x+w->speedX);w->y=(s16)(w->y+w->speedY);w->z=(s16)(w->z+w->speedZ);
            if(w->speedY>0){w->speedY--;if(w->speedY<=0)w->speedY=-3;}
            if((s32)w->y-w->floorY<=0){w->angleX=90;w->angleZ=0;w->timer=60;w->y=w->floorY;}
            else {w->angleX=(s16)(w->angleX+w->spinX);w->angleY=(s16)(w->angleY+w->spinY);w->angleZ=(s16)(w->angleZ+w->spinZ);}
        } else {
            remaining=(s32)((u32)w->timer-(u32)D_800BE9E4);
            if(remaining>0){w->timer=(u16)remaining;w->opacity=(u8)((s32)((u32)remaining<<8)/60);}
            else remove=1;
        }
        wanted=r;retired=error=0;func_1517A84C(r);
        if(retired!=remove || error)return 10;
        for(i=0;i<0xB8;i++)if(actual.bytes[i]!=expected.bytes[i])return 11;
    }
    return 0;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label,body,optimization,should_pass):
    output=ROOT/match.BUILD/"native";output.mkdir(parents=True,exist_ok=True)
    source,binary=output/(label+".c"),output/(label+".elf")
    source.write_text(native_source(body))
    result=subprocess.run(["gcc","-m32","-std=gnu89",optimization,"-fno-pie","-no-pie",
        "-ffreestanding","-fno-strict-aliasing","-fno-stack-protector","-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error","-Wall","-Wextra","-Werror","-nostdlib",
        str(source),"-o",str(binary)],capture_output=True,text=True)
    if result.returncode:raise AssertionError(result.stdout+result.stderr)
    executed=subprocess.run([str(binary)],timeout=30)
    if should_pass!=(executed.returncode==0):raise AssertionError((label,executed.returncode))


class SettleFadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=match.prepare(ROOT);cls.out=ROOT/match.BUILD
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>67I',cls.rom,match.ROM))
        selected=candidate.compare()
        if selected["differences"] or selected["words"]!=67:raise AssertionError(selected)
        cls.natural=cls.retail.copy()

    def receipt(self,name,value):
        (self.out/(name+".json")).write_text(json.dumps(value,indent=2)+"\n")

    def compare(self,case):
        initial=fixture(case);record=address(case)
        expected,calls=reference(initial,record);models=[]
        for words in (self.retail,self.natural):
            model=SettleOracle(words,initial,case).run()
            self.assertEqual(public(model.memory),public(expected),case)
            self.assertEqual(model.calls,calls,case)
            if calls:self.assertEqual(model.retire_snapshots,[bytes(expected[record+i] for i in range(0xB8))])
            models.append(model)
        return models

    def test_01_direct_owner_bindings_registry_and_literal_image(self):
        report=self.prepared["report"]
        self.assertEqual((report["words"],report["guards"],report["relocations"]),(67,0,3))
        self.assertEqual(report["changed_bodies"],[match.FUNCTION])
        self.assertEqual(report["registry"]["registry"],"D_8008B4A8[9].unk0")
        self.assertTrue(report["literal_full_image_prediction"])
        before,after=self.prepared["predecessor_elf"].read_bytes(),self.prepared["qualified_elf"].read_bytes()
        for at in (0x80,elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+match.SIZE])

    def test_02_wrapped_motion_landing_signed_spin_and_word_fade(self):
        coverage=[set(),set()];count=0;negative_shift_cases=0
        for timer,ticks,mode,phase in itertools.product((0,1,2,59,60,61,255,256,32767,32768,65535),
                (0,1,2,59,60,61,-1,0x7FFFFFFF,-0x80000000,65535,
                 -0x7FFFFF,-0x800000,-0xFFFFFF,-0x1000000,-0x7FFF0000),range(8),(0,8)):
            for i,model in enumerate(self.compare(Case(timer,ticks,mode,count,phase))):coverage[i].update(model.visits)
            count+=1
            remaining=sign(timer-ticks,32)
            negative_shift_cases+=bool(timer and remaining>0 and sign(remaining<<8,32)<0)
        full=set(range(match.ENTRY,match.ENTRY+match.SIZE,4));unreachable={match.ENTRY+0x98}
        self.assertEqual(coverage,[full-unreachable,full-unreachable])
        self.assertGreater(negative_shift_cases,0)
        self.receipt("guest-contract",{"cases_per_body":count,"covered_words":66,
            "statically_exact_unreachable_offsets":["0x98"],"signed_spins":list(SPINS),
            "word_wrap_before_signed_fade_division":True,"stored_timer_unsigned_bits":16,
            "negative_shifted_fade_cases_per_body":negative_shift_cases})

    def test_03_tick_aliases_and_whole_backing_preservation(self):
        count=0
        for layout,timer,ticks,phase in itertools.product(range(4),(0,1,60,65535),
                (0,1,-1,-0x80000000),(0,8)):
            self.compare(Case(timer,ticks,seed=count,phase=phase,layout=layout));count+=1
        self.receipt("aliases",{"cases_per_body":count,"tick_overlap_layouts":4,"record_backing_bytes":0xB8})

    def test_04_native32_and_effective_controls(self):
        for optimization in ("-O0","-O2","-O3"):run_native("positive"+optimization[1:],candidate.SELECTED,optimization,True)
        for name,body in controls().items():run_native("control-"+name,body,"-O2",False)
        self.receipt("native-contract",{"profiles":["O0","O2","O3"],"cases_per_profile":4096,"controls":sorted(controls())})

    def test_05_fault_boundaries_and_original_dispatch_window(self):
        observations=[]
        cases=(Case(mode=0),Case(mode=1),Case(mode=3),Case(timer=60),Case(timer=1),
               Case(timer=65535,ticks=-0x80000000))
        for case in cases:
            initial=fixture(case)
            for words in (self.retail,self.natural):
                baseline=SettleOracle(words,initial,case).run()
                for cut in range(baseline.root_accesses):
                    model=SettleOracle(words,initial,case);model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(model.root_accesses,cut)
                    observations.append((model.current_pc,model.delay_of,cut))
        window=list(struct.unpack_from('>4I',self.rom,WINDOW_START-0x15000000+0x2D4B0))
        target={match.ENTRY+i*4:word for i,word in enumerate(self.retail)}|{WINDOW_END:0}
        count=0
        for timer,ticks,mode,phase in itertools.product((0,1,60,65535),(1,-1),range(8),(0,8)):
            case=Case(timer,ticks,mode,count,phase);initial=fixture(case)
            expected,calls=reference(initial,RECORD);put(expected,SLOT,read(initial,RECORD+8))
            model=SettleOracle(window,initial,case,WINDOW_START,target)
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
