"""Connected original matrix helpers, callback ABI, aliases and image gates."""

from dataclasses import dataclass
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_linked_matrix_point_update_candidates as candidate
from tools.experiments import game_linked_matrix_point_update_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_actor_direction_point_oracle import add, sub, mul
from tools.tests.test_game_point_transform_match import (
    put, read, STATUS, DIAGNOSTIC, FLAG, CONVERT, TRANSFORM, TRANSLATE)
from tools.tests.test_game_matrix_point_interpolation_match import InterpolationOracle


ROOT = candidate.ROOT
OWNER, LINK, ACTOR, CHANGED, MATRICES = 0x22000, 0x24000, 0x26000, 0x28000, 0x50000
WRAPPER, POINT_HELPER, FRACTION, FRACTIONS = 0x15107F54, 0x15143134, 0x15107AE0, 0x800A2420
WINDOW_START, WINDOW_END = 0x151060BC, 0x151060D0


@dataclass(frozen=True)
class Case:
    route: str = "changed"
    axis: int = 0
    index: int = 0
    fixed: int = 0
    zero: bool = False
    phase: int = 0
    alias: int = 0
    identity: int = 0xA7
    nan: bool = False


def changed_address(case):
    return (CHANGED, LINK+0x14, OWNER+0x14, ACTOR+0x1D7)[case.alias]


def vector(memory, at):
    return tuple(read(memory, at+4*i) for i in range(3))


def transformed(memory, matrix, source):
    if memory[FLAG]:
        values = []
        for i in range(16):
            integer = read(memory,matrix+i*2,2)<<16 | read(memory,matrix+32+i*2,2)
            integer = integer-0x100000000 if integer&0x80000000 else integer
            values.append(bits(float(integer)/65536.0))
    else:
        values = [read(memory,matrix+4*i) for i in range(16)]
    if not any(floating(value)!=0.0 for value in source):
        return tuple(values[12:15])
    return tuple(add(add(mul(values[i],source[0]),mul(values[i+4],source[1])),
                     add(mul(values[i+8],source[2]),values[i+12])) for i in range(3))


def fixture(case):
    memory = {STACK+case.phase+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,size in ((OWNER,0x100),(LINK,0x40),(ACTOR,0x220),(CHANGED,4),(STATUS-4,32)):
        memory.update({base+i:(i*13+(base>>8))&255 for i in range(size)})
    put(memory,OWNER+0x60,LINK)
    put(memory,LINK,ACTOR)
    put(memory,ACTOR,0 if case.route=="inactive" else 1)
    memory[ACTOR+0x3B] = case.identity
    memory[LINK+4] = (case.identity^1) if case.route=="stale" else case.identity
    put(memory,ACTOR+0x1D4,0 if case.route=="no-matrix" else MATRICES+0x40)
    memory[LINK+0x14] = case.index
    for i,value in enumerate((0,0x80000000,0) if case.zero else (bits(1),bits(-2),bits(.5))):
        put(memory,LINK+8+4*i,value)
    if case.nan: put(memory,LINK+8,0x7FC12345)
    memory[FLAG] = case.fixed
    values = [.5,0,0,0, 0,1,0,0, 0,0,2,0, 3,-4,5,1]
    for matrix in {MATRICES+case.index*64, MATRICES+(case.index+1)*64, MATRICES, MATRICES+64}:
        if case.fixed:
            integers = [int(value*65536)&0xFFFFFFFF for value in values]
            payload = struct.pack('>32H',*[v>>16 for v in integers],*[v&65535 for v in integers])
        else: payload = struct.pack('>16I',*[bits(value) for value in values])
        memory.update({matrix+i:value for i,value in enumerate(payload)})
    point = transformed(memory,MATRICES+(case.index+1)*64,vector(memory,LINK+8))
    for i,value in enumerate(point):
        put(memory,OWNER+0x14+4*i,add(value,bits(1)) if case.route=="changed" and i==case.axis else value)
    for i,value in enumerate((bits(50),bits(-60),bits(70))): put(memory,OWNER+0x38+i*4,value)
    put(memory,FRACTIONS,bits(.333))
    put(memory,FRACTIONS+4,bits(.6667))
    memory[CHANGED] = 0xA5
    return memory


def public(memory):
    return {at:value for at,value in memory.items() if not STACK-2048<=at<STACK+512}


def reference(initial, changed):
    memory = dict(initial)
    link = read(memory,OWNER+0x60)
    actor = read(memory,link)
    if not read(memory,actor) or memory[link+4]!=memory[actor+0x3B] or not read(memory,actor+0x1D4):
        return memory,0,False,None
    memory[changed] = 0
    original = vector(memory,OWNER+0x14)
    matrix = read(memory,actor+0x1D4)+memory[link+0x14]*64
    arguments = (actor,memory[link+0x14],link+8,OWNER+0x14)
    source = vector(memory,link+8)
    point = transformed(memory,matrix,source)
    put(memory,STATUS,0)
    if any(floating(value)!=0.0 for value in source):
        put(memory,DIAGNOSTIC,matrix)
        for i,value in enumerate(source): put(memory,STATUS+8+4*i,value)
    for i,value in enumerate(point): put(memory,OWNER+0x14+4*i,value)
    moved = any(floating(a)!=floating(b) for a,b in zip(original,point))
    if moved:
        memory[changed] = 1
        start,end = vector(memory,OWNER+0x14),vector(memory,OWNER+0x38)
        delta = tuple(sub(b,a) for a,b in zip(start,end))
        for destination,fraction in ((OWNER+0x20,read(memory,FRACTIONS)),(OWNER+0x2C,read(memory,FRACTIONS+4))):
            for i in range(3): put(memory,destination+4*i,add(start[i],mul(delta[i],fraction)))
    return memory,1,moved,arguments


class CallbackOracle(InterpolationOracle):
    def __init__(self,words,memory,case,connected,changed=None,entry=match.ENTRY):
        marker = changed_address(case) if changed is None else changed
        TimingOracle.__init__(self,words,memory,phase=case.phase,entry=entry,
                              arguments=(OWNER,marker),connected=connected)
        self.input_args = (LINK+8,OWNER+0x14,MATRICES+(case.index+1)*64)
        self.mutate = False
        self.condition = True
        self.hi,self.lo = 0x89ABCDEF,0x76543210
        self.root_calls = []

    def record_call(self,target):
        counts = {match.ENTRY:2,WRAPPER:4,POINT_HELPER:3,FRACTION:4,
                  CONVERT:2,TRANSFORM:7,TRANSLATE:3}
        if target not in counts: raise AssertionError("Unexpected matrix callback helper %08X"%target)
        args = tuple(self.arguments(counts[target]))
        self.calls.append((target,args))
        self.events.append(("CALL",target,args))
        if target in (WRAPPER,FRACTION): self.root_calls.append((target,args))
        if target==POINT_HELPER: self.input_args = args

    def hook(self,target):
        raise AssertionError("An original helper was not connected: %08X"%target)


class WindowDone(Exception): pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==WINDOW_END: raise WindowDone
        return super().__getitem__(pc)


def controls():
    replacements = {
        "wrong-link":("owner + 0x60","owner + 0x64"),
        "wrong-identity":("actor[0x3B]","actor[0x3A]"),
        "wrong-matrix-field":("actor + 0x1D4","actor + 0x1D0"),
        "missing-matrix-gate":("*(s32 *)(actor + 0x1D4) == 0","0"),
        "wrong-index":("link[0x14]","link[0x15]"),
        "signed-index":("link[0x14]","link[0x14] & 0x7F"),
        "wrong-source":("link + 8","link + 12"),
        "wrong-point":("owner + 0x14","owner + 0x18"),
        "missing-clear":("    *changed = 0;\n",""),
        "wrong-failure":("        return 0;","        return 1;"),
        "wrong-success":("    return 1;","    return 0;"),
        "wrong-endpoint":("owner + 0x38","owner + 0x34"),
        "wrong-first-output":("owner + 0x20","owner + 0x24"),
        "wrong-second-output":("owner + 0x2C","owner + 0x30"),
    }
    result = {name:candidate.SELECTED.replace(old,new,1) for name,(old,new) in replacements.items()}
    if any(body==candidate.SELECTED for body in result.values()): raise AssertionError("Ineffective callback control")
    return result


def native_source(body):
    return r'''typedef unsigned char u8; typedef signed int s32; typedef unsigned int u32;
typedef float f32; typedef struct { f32 unk0,unk4,unk8; } struct17;
void func_15107F54(u8 *,u8,u8 *,u8 *);
void func_15107AE0(const f32 *,const f32 *,f32 *,f32 *);
''' + body + r'''
static u8 *wantedOwner,*wantedLink,*wantedActor;
static u8 wantedIndex;
static u32 calls,error,mode;
void func_15107F54(u8 *actor,u8 index,u8 *source,u8 *output) {
    calls++;
    if(calls!=1 || actor!=wantedActor || index!=wantedIndex ||
       source!=wantedLink+8 || output!=wantedOwner+0x14) error=1;
    if(mode&1) ((f32 *)output)[0]+=1.0f;
    if(mode&2) ((f32 *)output)[1]-=2.0f;
    if(mode&4) ((f32 *)output)[2]+=4.0f;
}
void func_15107AE0(const f32 *start,const f32 *end,f32 *first,f32 *second) {
    calls++;
    if(calls!=2 || (const u8 *)start!=wantedOwner+0x14 ||
       (const u8 *)end!=wantedOwner+0x38 || (u8 *)first!=wantedOwner+0x20 ||
       (u8 *)second!=wantedOwner+0x2C) error=2;
    first[0]=10.0f; first[1]=11.0f; first[2]=12.0f;
    second[0]=20.0f; second[1]=21.0f; second[2]=22.0f;
}
static s32 run(void) {
    union {u32 alignment; u8 bytes[0x220];} ownerStore,linkStore,actorStore;
    u8 *owner=ownerStore.bytes,*link=linkStore.bytes,*actor=actorStore.bytes;
    u8 marker,*changed;
    u32 seed,i,active,stale,present,valid,alias;
    for(seed=0;seed<4096;seed++) {
        for(i=0;i<0x220;i++) {owner[i]=(u8)(seed+i*3u);link[i]=(u8)(seed+i*5u);actor[i]=(u8)(seed+i*7u);}
        active=seed&1;stale=(seed>>1)&1;present=(seed>>2)&1;mode=(seed>>3)&7;
        alias=(seed>>6)&1;
        *(u8 **)(owner+0x60)=link;*(u8 **)link=actor;
        *(s32 *)actor=active?1:0;*(u32 *)(actor+0x1D4)=present?0x50000:0;
        actor[0x3B]=0xA7;link[4]=stale?0xA6:0xA7;
        link[0x14]=(u8)(seed*37u);link[0x15]=link[0x14]^0xFF;
        for(i=0;i<3;i++) ((f32 *)(owner+0x14))[i]=(f32)seed+(f32)i+0.25f;
        marker=0xA5;changed=alias?link+0x14:&marker;
        wantedIndex=(alias && active && !stale && present)?0:link[0x14];
        wantedOwner=owner;wantedLink=link;wantedActor=actor;
        calls=error=0;valid=active && !stale && present;
        {u8 before=*changed;
         if(func_15107E48(owner,changed)!=(s32)valid) return 10;
         if(error) return 11;
         if(!valid) {if(calls || *changed!=before) return 12;}
         else if(mode==0) {if(calls!=1 || *changed!=0) return 13;}
         else {if(calls!=2 || *changed!=1) return 14;
               if(((f32 *)(owner+0x20))[0]!=10.0f || ((f32 *)(owner+0x2C))[2]!=22.0f) return 15;}}
    }
    return 0;
}
void _start(void) {s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label,body,optimization,should_pass):
    out = ROOT/match.BUILD/"native"
    out.mkdir(parents=True,exist_ok=True)
    source,binary = out/(label+".c"),out/(label+".elf")
    source.write_text(native_source(body))
    result = subprocess.run(["gcc","-m32","-std=gnu89",optimization,"-fno-pie","-no-pie",
        "-ffreestanding","-fno-strict-aliasing","-fno-stack-protector",
        "-fsanitize=undefined","-fsanitize-undefined-trap-on-error","-Wall","-Wextra","-Werror",
        "-nostdlib",str(source),"-o",str(binary)],capture_output=True,text=True)
    if result.returncode: raise AssertionError(result.stdout+result.stderr)
    executed = subprocess.run([str(binary)],timeout=30)
    if should_pass!=(executed.returncode==0): raise AssertionError((label,executed.returncode))


class LinkedMatrixPointUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = match.prepare(ROOT)
        cls.out = ROOT/match.BUILD
        cls.rom = (ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail = list(struct.unpack_from('>67I',cls.rom,match.ROM))
        linked,functions = link_owner(ROOT,cls.out,cls.prepared["qualified_compact"],candidate.OWNER)
        cls.natural = list(struct.unpack_from('>67I',linked,functions[match.FUNCTION]["value"]))
        cls.connected = {}
        for entry,rom,words in ((WRAPPER,0x135404,17),(POINT_HELPER,0x1705E4,98),
             (FRACTION,0x134F90,38),(CONVERT,0x21D368,46),(TRANSFORM,0xD4E10,40),(TRANSLATE,0x16F7C4,49)):
            cls.connected.update({entry+i*4:word for i,word in enumerate(struct.unpack_from('>%dI'%words,cls.rom,rom))})

    def receipt(self,name,data):
        (self.out/(name+".json")).write_text(json.dumps(data,indent=2)+"\n")

    def compare(self,case,marker=None):
        initial = fixture(case)
        marker = changed_address(case) if marker is None else marker
        expected,result,moved,arguments = reference(initial,marker)
        models = []
        for words in (self.retail,self.natural):
            model = CallbackOracle(words,initial,case,self.connected,marker).run()
            self.assertEqual(public(model.memory),public(expected),case)
            self.assertEqual(model.r[2],result,case)
            if result:
                self.assertEqual(model.root_calls[0],(WRAPPER,arguments),case)
                self.assertEqual(len(model.root_calls),1+int(moved),case)
            else: self.assertEqual(model.calls,[],case)
            models.append(model)
        return models

    def test_01_owner_frame_guards_and_literal_image(self):
        report = self.prepared["report"]
        self.assertEqual((report["words"],report["guards"],report["neighbors"]),(67,9,36))
        self.assertEqual(report["changed_bodies"],[match.FUNCTION])
        self.assertTrue(report["literal_full_image_prediction"])
        for offset,expected,replacement in match.GUARD_WORDS:
            self.assertEqual(self.natural[offset//4],expected)
            self.assertEqual(self.retail[offset//4],replacement)
        self.assertEqual(report["strict_changed_bytes"],187)
        before,after = self.prepared["predecessor_elf"].read_bytes(),self.prepared["qualified_elf"].read_bytes()
        for position in (0x80,elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad = bytearray(after);bad[position]^=1
            with self.assertRaises(ValueError): match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+match.SIZE])

    def test_02_connected_original_helpers_and_all_public_routes(self):
        coverage=[set(),set()]
        count=0
        for route,axis,index,fixed,zero,phase in itertools.product(
                ("inactive","stale","no-matrix","same","changed"),range(3),(0,128,255),(0,1),(False,True),(0,8)):
            case=Case(route,axis,index,fixed,zero,phase,identity=(0 if count&1 else 255))
            for i,model in enumerate(self.compare(case)):
                coverage[i].update(pc for pc in model.visits if match.ENTRY<=pc<match.ENTRY+match.SIZE)
            count+=1
        for axis in range(3):
            for model in self.compare(Case(axis=axis,nan=True)):
                self.assertEqual(model.memory[CHANGED],1)
        expected=set(range(match.ENTRY,match.ENTRY+match.SIZE,4))-{match.ENTRY+0x44,match.ENTRY+0x60}
        self.assertEqual(coverage,[expected,expected])
        self.receipt("connected-guest",{"cases_per_body":count+3,"reachable_words":65,
            "unreachable_words":["+0x44","+0x60"],"original_helpers":6,
            "matrix_indices":[0,128,255],"float_fixed_and_zero_point_routes":True})

    def test_03_aliases_live_matrix_index_and_fault_boundaries(self):
        count=0
        for alias,route,fixed,phase in itertools.product(range(4),("no-matrix","same","changed"),(0,1),(0,8)):
            self.compare(Case(route=route,index=255,fixed=fixed,phase=phase,alias=alias));count+=1
        observations=[]
        for case in (Case(route="inactive"),Case(route="stale"),Case(route="no-matrix"),Case(route="same"),Case()):
            initial=fixture(case)
            for words in (self.retail,self.natural):
                baseline=CallbackOracle(words,initial,case,self.connected).run()
                for cut in range(baseline.root_accesses):
                    model=CallbackOracle(words,initial,case,self.connected);model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary): model.run()
                    self.assertEqual(model.root_accesses,cut)
                    observations.append((model.current_pc,model.delay_of,cut))
        self.receipt("aliases-and-faults",{"alias_cases_per_body":count,
            "fault_observations":len(observations),"unique_boundaries":len(set(observations))})

    def test_04_native32_and_effective_controls(self):
        for optimization in ("-O0","-O2","-O3"):
            run_native("positive"+optimization[1:],candidate.SELECTED,optimization,True)
        for name,body in controls().items(): run_native("control-"+name,body,"-O2",False)
        self.receipt("native-contract",{"profiles":["O0","O2","O3"],"cases_per_profile":4096,"controls":sorted(controls())})

    def test_05_original_dispatcher_window_and_callback_slot(self):
        evidence=match.registry_evidence(ROOT)
        self.assertEqual(evidence["registry"],"D_80088C10[1]")
        window=list(struct.unpack_from('>5I',self.rom,WINDOW_START-0x15000000+0x2D4B0))
        count=0
        target={match.ENTRY+i*4:word for i,word in enumerate(self.retail)}
        target[WINDOW_END]=0
        for route,phase in itertools.product(("inactive","stale","no-matrix","same","changed"),(0,8)):
            case=Case(route=route,index=255,phase=phase)
            initial=fixture(case)
            caller_sp=STACK+phase-0x30
            marker=caller_sp+0x2B
            initial[marker]=0
            expected,result,_,_=reference(initial,marker)
            model=CallbackOracle(window,initial,case,self.connected|target,marker,WINDOW_START)
            model.r[16],model.r[3],model.r[29]=OWNER,match.ENTRY,caller_sp
            model.before=model.r.copy()
            model.code=WindowCode(model.code,model)
            with self.assertRaises(WindowDone): model.run()
            self.assertEqual(model.r[2],result)
            self.assertEqual(model.r[29],caller_sp)
            self.assertEqual(model.r[16],OWNER)
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.memory[marker],expected[marker])
            self.assertEqual(model.calls[0],(match.ENTRY,(OWNER,marker)))
            count+=1
        self.receipt("caller-window",{"cases":count,"original_jalr":hex(0x151060C8),"callback_slot":"D_80088C10[1]"})


if __name__ == "__main__": unittest.main()
