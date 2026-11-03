"""Semantic, callback, and strict-image gates for func_151AB1C4."""

import itertools
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_ground_effect_callback_candidates as candidate
from tools.experiments import game_actor_ground_effect_callback_match as match
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
OWNER = 0x220000
ACTOR = 0x230000
OTHER = 0x240000
THRESHOLD = 0x800A8FEC
QUERY = 0x15045800
EFFECT = 0x151ABE40
SOUND = 0x10010FFC
FINALIZE = 0x151AA264


def f32(value):
    return floating(bits(value))


def cases():
    for seed in range(128):
        threshold = f32((seed % 9 - 4) * 25.0)
        top = f32(threshold + (50.0 if seed & 1 else -50.0))
        yield {
            "seed": seed,
            "threshold": threshold,
            "top": top,
            "x": f32((seed - 60) * 1.25),
            "y": f32((40 - seed) * 0.75),
            "z": f32((seed % 17 - 8) * -2.5),
            "height": f32((seed % 13 - 6) * 3.25),
            "outcome": seed % 3 != 0,
            "mode": seed & 15,
            "identity": (seed * 17 + 3) & 0xFF,
            "category": (seed * 29 + 0x41) & 0xFF,
        }


def position_address(phase):
    return STACK + phase - 0x10


def fixture(case, phase):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    for pointer, size in ((OWNER - 32, 0x180), (ACTOR - 32, 0x180),
                          (OTHER - 32, 0x180)):
        memory.update({pointer + index: (index * 13 + case["seed"] * 19 + 0x59) & 0xFF
                       for index in range(size)})
    put(memory, OWNER + 0x18, ACTOR)
    memory[OWNER + 1] = case["identity"]
    memory[OWNER + 0xC] = case["category"]
    put(memory, ACTOR + 0x14, bits(case["x"]))
    put(memory, ACTOR + 0x18, bits(case["y"]))
    put(memory, ACTOR + 0x1C, bits(case["z"]))
    put(memory, ACTOR + 0x118, bits(case["top"]))
    put(memory, THRESHOLD, bits(case["threshold"]))
    return memory


def call_event(target, args, memory, position=None):
    payload = () if position is None else tuple(
        read(memory, position + index * 4) for index in range(3))
    return target, args, payload


def helper_effect(memory, case, target, position):
    if target == QUERY:
        put(memory, OWNER + 0x34, bits(case["height"]))
        memory[OWNER + 0x50] ^= 0x40
        if case["mode"] & 1:
            memory[OWNER + 1] ^= 0xFF
            memory[OWNER + 0xC] ^= 0x55
        if case["mode"] & 2:
            put(memory, position, bits(-77.25))
            put(memory, position + 4, bits(-999.0))
            put(memory, position + 8, bits(99.5))
        if case["mode"] & 4:
            put(memory, OWNER + 0x18, OTHER)
    elif target == EFFECT:
        memory[OWNER + 0x51] ^= 0x20
        if case["mode"] & 8:
            put(memory, OWNER + 0x18, OTHER)
    elif target == SOUND:
        memory[OWNER + 0x52] ^= 0x10
    else:
        memory[OWNER + 0x53] ^= 0x08


def reference(initial, case, phase):
    memory = dict(initial)
    position = position_address(phase)
    actor = read(memory, OWNER + 0x18)
    top = floating(read(memory, actor + 0x118))
    threshold = floating(read(memory, THRESHOLD))
    y = f32(top + f32(100.0)) if threshold < top else f32(
        floating(read(memory, actor + 0x18)) + f32(150.0))
    values = (read(memory, actor + 0x14), bits(y), read(memory, actor + 0x1C))
    for index, value in enumerate(values):
        put(memory, position + index * 4, value)
    depth = bits(f32(y - f32(300.0)))
    query_args = (position, 0, depth, OWNER + 0x34)
    calls = [call_event(QUERY, query_args, memory, position)]
    helper_effect(memory, case, QUERY, position)
    if case["outcome"]:
        put(memory, position + 4, read(memory, OWNER + 0x34))
        effect_args = (position, OWNER + 0x34, 3,
                       memory[OWNER + 0xC], memory[OWNER + 1])
        calls.append(call_event(EFFECT, effect_args, memory, position))
        helper_effect(memory, case, EFFECT, position)
        sound_args = (0, 0x11, 0x5208, 0, 0, actor)
        calls.append(call_event(SOUND, sound_args, memory))
        helper_effect(memory, case, SOUND, position)
    final_args = (actor, OWNER + 0x34)
    calls.append(call_event(FINALIZE, final_args, memory))
    helper_effect(memory, case, FINALIZE, position)
    return memory, calls


def public(memory, phase):
    return (
        bytes(memory[OWNER + index] for index in range(0x90)),
        bytes(memory[ACTOR + index] for index in range(0x120)),
        bytes(memory[OTHER + index] for index in range(0x120)),
        bytes(memory[position_address(phase) + index] for index in range(12)),
    )


class GroundEffectOracle(TimingOracle):
    def __init__(self, words, memory, case, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OWNER,))
        self.case = case
        self.phase_value = phase
        self.raw_calls = []

    def arguments(self, count):
        return tuple(self.r[4 + index] if index < 4 else
                     read(self.memory, self.r[29] + index * 4)
                     for index in range(count))

    def record_call(self, target):
        counts = {QUERY: 4, EFFECT: 5, SOUND: 6, FINALIZE: 2}
        if target not in counts:
            raise AssertionError("Unexpected ground-effect helper %08X" % target)
        args = self.arguments(counts[target])
        position = args[0] if target in (QUERY, EFFECT) else None
        event = call_event(target, args, self.memory, position)
        self.raw_calls.append((target, args))
        self.calls.append(event)
        self.events.append(("CALL",) + event)

    def hook(self, target):
        recorded, _ = self.raw_calls[-1]
        if recorded != target:
            raise AssertionError((recorded, target))
        position = position_address(self.phase_value)
        helper_effect(self.memory, self.case, target, position)
        if target == QUERY:
            result = 1 if self.case["outcome"] else 0
        elif target == FINALIZE:
            result = 0x76543210
        else:
            result = 0x65432100 | (target & 0xFF)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = result


def controls():
    body = candidate.MATCHED
    variants = {
        "wrong-x": body.replace("actor + 0x14", "actor + 0x18", 1),
        "wrong-top": body.replace("actor + 0x118", "actor + 0x18", 1),
        "wrong-high-offset": body.replace("100.0f", "90.0f", 1),
        "wrong-low-offset": body.replace("150.0f", "140.0f", 1),
        "wrong-z": body.replace("actor + 0x1C", "actor + 0x18", 1),
        "wrong-depth": body.replace("300.0f", "250.0f", 1),
        "wrong-kind": body.replace("owner + 0x34, 3,", "owner + 0x34, 4,", 1),
        "stale-category": body.replace("owner[0xC]", "0", 1),
        "skip-sound": body.replace(
            "        func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);",
            "        (void)0;", 1),
        "skip-finalizer": body.replace(
            "    func_151AA264(actor, (f32 *)(owner + 0x34));", "    (void)0;", 1),
        "wrong-final-pointer": body.replace(
            "func_151AA264(actor, (f32 *)(owner + 0x34))",
            "func_151AA264(actor, (f32 *)(owner + 0x38))", 1),
    }
    if len(variants) != 11 or any(value == body for value in variants.values()):
        raise AssertionError("A ground-effect semantic control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef float f32;
typedef union {u64 align;u8 bytes[0x180];} Store;
static Store ownerStore,actorStore,otherStore;
static f32 D_800A8FEC;
static u32 modeValue,outcomeValue,calls,failed;
static f32 heightValue;
static u32 fbits(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static u8 *owner(void){return ownerStore.bytes;}
static u8 *actor(void){return actorStore.bytes;}
static u8 *other(void){return otherStore.bytes;}
static void setf(u8 *base,u32 offset,f32 value){*(f32 *)(base+offset)=value;}
static void setp(u8 *base,u32 offset,u8 *value){*(u8 **)(base+offset)=value;}
s32 func_15045800(f32 *position,u16 mode,f32 depth,void *result){
    f32 top=*(f32 *)(actor()+0x118);f32 y=D_800A8FEC<top?top+100.0f:*(f32 *)(actor()+0x18)+150.0f;
    if(calls++!=0u||mode!=0||result!=owner()+0x34||fbits(position[0])!=fbits(*(f32 *)(actor()+0x14))||
       fbits(position[1])!=fbits(y)||fbits(position[2])!=fbits(*(f32 *)(actor()+0x1C))||fbits(depth)!=fbits(y-300.0f))failed=1;
    *(f32 *)result=heightValue;owner()[0x50]^=0x40;
    if(modeValue&1u){owner()[1]^=0xFF;owner()[0xC]^=0x55;}
    if(modeValue&2u){position[0]=-77.25f;position[1]=-999.0f;position[2]=99.5f;}
    if(modeValue&4u)setp(owner(),0x18,other());
    return (s32)outcomeValue;
}
void func_151ABE40(f32 *position,void *result,s32 kind,u8 category,s32 identity){
    if(calls++!=1u||!outcomeValue||result!=owner()+0x34||kind!=3||category!=owner()[0xC]||
       (u8)identity!=owner()[1]||fbits(position[1])!=fbits(heightValue))failed=1;
    owner()[0x51]^=0x20;if(modeValue&8u)setp(owner(),0x18,other());
}
u16 func_10010FFC(s32 a,s32 b,u16 c,s16 d,u8 e,void *who){
    if(calls++!=2u||!outcomeValue||a||b!=0x11||c!=0x5208||d||e||who!=actor())failed=1;
    owner()[0x52]^=0x10;return 0x1234;
}
void func_151AA264(u8 *who,f32 *result){
    u32 wanted=outcomeValue?3u:1u;
    if(calls++!=wanted||who!=actor()||result!=(f32 *)(owner()+0x34))failed=1;
    owner()[0x53]^=0x08;
}
''' + body + r'''
static void initialize(u32 seed){
    u32 i;for(i=0;i<sizeof(Store);i++){owner()[i]=(u8)(i*13u+seed*19u+0x59u);actor()[i]=(u8)(i*17u+seed*7u+0x31u);other()[i]=(u8)(i*23u+seed*11u+0x47u);}
    D_800A8FEC=((s32)(seed%9u)-4)*25.0f;
    setf(actor(),0x118,D_800A8FEC+((seed&1u)?50.0f:-50.0f));
    setf(actor(),0x14,((s32)seed-60)*1.25f);setf(actor(),0x18,(40-(s32)seed)*0.75f);
    setf(actor(),0x1C,((s32)(seed%17u)-8)*-2.5f);setp(owner(),0x18,actor());
    owner()[1]=(u8)(seed*17u+3u);owner()[0xC]=(u8)(seed*29u+0x41u);
    heightValue=((s32)(seed%13u)-6)*3.25f;
}
static int one(u32 seed){modeValue=seed&15u;outcomeValue=seed%3u!=0u;calls=failed=0;initialize(seed);
    func_151AB1C4(owner());return failed||calls!=(outcomeValue?4u:2u);}
int main(void){u32 seed;for(seed=0;seed<256u;seed++)if(one(seed))return 1;return 0;}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".exe")
    source.write_text(native_source(body))
    command = [
        "gcc", "-msse2", "-mfpmath=sse", optimization, "-std=c99",
        "-fno-strict-aliasing", "-ffp-contract=off",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class ActorGroundEffectCallbackTest(unittest.TestCase):
    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for case, phase in itertools.product(cases(), (0, 8)):
            initial = fixture(case, phase)
            wanted, calls = reference(initial, case, phase)
            model = GroundEffectOracle(words, initial, case, phase).run()
            self.assertEqual(public(model.memory, phase), public(wanted, phase))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], 0x76543210)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 256)
        # The branch-likely false path executes the load in its delay slot at
        # +0x3C and targets +0x5C.  Retail retains a duplicate copy at +0x58,
        # between the true path's unconditional branch and that target, so no
        # control-flow edge can execute it.
        unreachable = 0x58
        self.assertEqual(words[unreachable // 4], 0xC6100018)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)) - {unreachable})

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.MATCHED,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_owner_callback_and_full_image(self):
        candidate_report = candidate.compare("test-guarded-owner", candidate.MATCHED)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["frame"], match.RETAIL_FRAME)
        self.assertEqual(candidate_report["differences"], len(match.PATCH_ROWS))
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.MATCHED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], len(match.PATCH_ROWS))
        self.assertEqual(report["natural_positional_differences"], len(match.PATCH_ROWS))
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
