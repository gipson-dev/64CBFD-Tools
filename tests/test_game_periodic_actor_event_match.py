"""Semantic, registry, owner and strict-image gates for func_151905BC."""

from dataclasses import dataclass
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_periodic_actor_event_candidates as candidate
from tools.experiments import game_periodic_actor_event_match as match
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x22000
OWNER = 0x24000
ATTACHED = 0x28000
TICKS = 0x800BE9E4
ACTORS = 0x800CC2D0
STRIDE = 0x32C
EVENT = 0x1505D024


def u32(value):
    return value & 0xFFFFFFFF


def s32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


@dataclass(frozen=True)
class Case:
    period: int = 10
    elapsed: int = 0
    ticks: int = 1
    actor_index: int = 0
    attached: bool = True
    attached_state: int = 0
    timer: int = 0x1234
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
              for index in range(-0x400, 0x100)}
    for base, size in ((RECORD - 0x20, 0xE0), (OWNER, 0x360),
                       (ATTACHED, 0xC0), (TICKS, 4)):
        memory.update({base + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
                       for index in range(size)})
    put(memory, RECORD + 0x10, OWNER)
    put(memory, RECORD + 0x90, case.period)
    put(memory, RECORD + 0x94, case.elapsed)
    put(memory, RECORD + 0x98, ACTORS + case.actor_index * STRIDE)
    put(memory, OWNER + 0x31C, ATTACHED if case.attached else 0)
    memory[ATTACHED + 0x84] = case.attached_state & 0xFF
    put(memory, ATTACHED + 0x46, case.timer, 2)
    put(memory, TICKS, case.ticks)
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x100}


def reference(initial):
    memory = dict(initial)
    calls = []
    period = s32(read(memory, RECORD + 0x90))
    elapsed = s32(u32(read(memory, RECORD + 0x94)) +
                  u32(read(memory, TICKS)))
    put(memory, RECORD + 0x94, elapsed)
    while elapsed >= period:
        target = read(memory, RECORD + 0x98)
        numerator = s32(u32(target) - ACTORS)
        actor_index = abs(numerator) // STRIDE
        if numerator < 0:
            actor_index = -actor_index
        calls.append((EVENT, (OWNER, 0x60021, 0, u32(actor_index))))
        elapsed = s32(u32(elapsed) - u32(period))
        put(memory, RECORD + 0x94, elapsed)
    attached = read(memory, OWNER + 0x31C)
    if attached != 0 and memory[attached + 0x84] == 0:
        put(memory, attached + 0x46, 1000, 2)
    return memory, calls, 1


class PeriodicOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=(RECORD,))
        self.root_fault = fault

    def record_call(self, target):
        if target != EVENT:
            raise AssertionError("Unexpected periodic-event helper %08X" % target)
        args = tuple(self.arguments(4))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != EVENT:
            raise AssertionError("Unbounded periodic-event helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = 0x76543210


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-tick": body.replace("(u32)D_800BE9E4", "1U", 1),
        "wrong-loop-edge": body.replace(
            "clock->elapsed >= clock->period", "clock->elapsed > clock->period", 1),
        "wrong-event-code": body.replace("eventCode = 0x60021;",
                                           "eventCode = 0x60020;", 1),
        "wrong-actor-base": body.replace("base = D_800CC2D0;",
                                           "base = D_800CC2D0 + 1;", 1),
        "wrong-period-wrap": body.replace(
            "            clock->elapsed = (s32)((u32)clock->elapsed - (u32)clock->period);\n",
            "            clock->elapsed = (s32)((u32)clock->elapsed - ((u32)clock->period + 1U));\n",
            1),
        "wrong-attached-byte": body.replace("[0x84]", "[0x85]", 1),
        "wrong-attached-gate": body.replace("[0x84] == 0", "[0x84] != 0", 1),
        "wrong-refresh-value": body.replace("= 1000;", "= 999;", 1),
        "wrong-return": body.replace("return 1;", "return 0;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A periodic actor event control did not alter source")
    return variants


def native_source(body):
    return r'''#define NULL ((void *)0)
typedef unsigned char u8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef struct {u8 retained00[0x46];s16 timer;u8 retained48[0x3C];u8 state;} struct126;
typedef struct struct127 struct127;
struct struct127 {u8 retained00[0x31C];struct126 *unk31C;u8 retained320[0xC];};
typedef struct {s32 period;s32 elapsed;struct127 *eventTarget;} PeriodicActorEventClock151905BC;
typedef struct {u8 retained00[0x10];struct127 *owner;u8 retained14[0x7C];PeriodicActorEventClock151905BC clock;} PeriodicActorEventNested151905BC;
s32 D_800BE9E4;
struct127 D_800CC2D0[26];
static s32 calls,lastCode,lastZero,lastIndex;
static struct127 *lastOwner;
s32 func_1505D024(struct127 *owner,s32 code,u16 zero,s32 index) {
    calls++;lastOwner=owner;lastCode=code;lastZero=zero;lastIndex=index;return 0x76543210;
}
''' + body + r'''
static s32 signed32(u32 value) {return (value&0x80000000u)?(s32)(value-0x80000000u)-(s32)0x7FFFFFFF-1:(s32)value;}
static int one(u32 seed) {
    static const s32 periods[]={1,2,3,17,4096,1048576,2147483647};
    static const u32 ticks[]={0,1,2,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
    static const u8 states[]={0,1,255};
    PeriodicActorEventNested151905BC record;struct127 owner;struct126 attached;
    s32 period=periods[seed%7],wantedElapsed,initial,index=(s32)((seed/11)%26),wantedCalls;
    u32 tick=ticks[(seed/5)%6];s32 result;
    u8 *bytes=(u8 *)&record;u32 i;
    for(i=0;i<sizeof(record);i++)bytes[i]=(u8)(i*13u+seed*19u+0x59u);
    bytes=(u8 *)&owner;for(i=0;i<sizeof(owner);i++)bytes[i]=(u8)(i*7u+seed*3u+0x35u);
    bytes=(u8 *)&attached;for(i=0;i<sizeof(attached);i++)bytes[i]=(u8)(i*11u+seed*5u+0x71u);
    if((seed&7u)==0)wantedElapsed=-(s32)((seed%31u)+1u);
    else if(period>1000000)wantedElapsed=(s32)(seed%(u32)period);
    else wantedElapsed=(s32)((seed%5u)*(u32)period+(seed%(u32)period));
    wantedCalls=0;while(wantedElapsed>=period){wantedElapsed-=period;wantedCalls++;}
    if((seed&7u)==0)wantedElapsed=-(s32)((seed%31u)+1u);
    else if(period>1000000)wantedElapsed=(s32)(seed%(u32)period);
    else wantedElapsed=(s32)((seed%5u)*(u32)period+(seed%(u32)period));
    initial=signed32((u32)wantedElapsed-tick);
    record.owner=&owner;record.clock.period=period;record.clock.elapsed=initial;
    record.clock.eventTarget=&D_800CC2D0[index];D_800BE9E4=(s32)tick;
    owner.unk31C=(seed&1u)?&attached:(struct126 *)0;attached.state=states[(seed/13)%3];attached.timer=(s16)0x1234;
    calls=0;lastOwner=(struct127 *)0;lastCode=lastZero=lastIndex=-1;
    result=func_151905BC(&record);
    if(result!=1||calls!=wantedCalls)return 1;
    while(wantedElapsed>=period)wantedElapsed-=period;
    if(record.clock.elapsed!=wantedElapsed)return 2;
    if(calls&&(lastOwner!=&owner||lastCode!=0x60021||lastZero!=0||lastIndex!=index))return 3;
    if(owner.unk31C&&attached.state==0){if(attached.timer!=1000)return 4;}
    else if(attached.timer!=(s16)0x1234)return 5;
    return 0;
}
static int run(void) {
    u32 seed;
    if(sizeof(void *)!=4||sizeof(struct127)!=0x32C||sizeof(PeriodicActorEventNested151905BC)!=0x9C)return 9;
    for(seed=0;seed<4096;seed++)if(one(seed))return 1;
    return 0;
}
void _start(void) {s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class GamePeriodicActorEventMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.retail = list(struct.unpack_from(">66I", (ROOT / match.ROM_IMAGE).read_bytes(),
                                                   match.ROM))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")

    def test_01_direct_profile_owner_neighbors_and_strict_image(self):
        direct = candidate.compare("test-debug", candidate.SELECTED, ("-O2", "-g3"))
        self.assertEqual((direct["words"], direct["frame"], direct["differences"]),
                         (66, 0x30, 0))
        self.assertEqual(direct["bindings"], {
            "0x020": [("R_MIPS_HI16", "D_800BE9E4")],
            "0x024": [("R_MIPS_LO16", "D_800BE9E4")],
            "0x048": [("R_MIPS_HI16", "D_800CC2D0")],
            "0x054": [("R_MIPS_LO16", "D_800CC2D0")],
            "0x09C": [("R_MIPS_26", "func_1505D024")],
        })
        plain = candidate.compare("test-plain", candidate.SELECTED, ("-O2",))
        self.assertEqual((plain["words"], plain["frame"], plain["differences"]),
                         (66, 0x30, 31))
        report = match.prepare(ROOT)["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual((report["guards"], report["neighbors"],
                          report["strict_exclusions"]), (0, 60, 0))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])

    def test_02_guest_period_wrap_callback_target_and_reachable_words(self):
        periods = (1, 2, 3, 17, 4096, 1048576, 0x7FFFFFFF)
        ticks = (0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
        cases = []
        for index in range(4096):
            period = periods[index % len(periods)]
            if index & 7 == 0:
                wanted = -((index % 31) + 1)
            elif period > 1000000:
                wanted = index % period
            else:
                wanted = (index % 5) * period + index % period
            tick = ticks[(index // 5) % len(ticks)]
            initial = s32(u32(wanted) - tick)
            cases.append(Case(period, initial, tick,
                              (-1, 0, 1, 25)[(index // 11) % 4],
                              bool(index & 1), (0, 1, 255)[(index // 13) % 3],
                              0x1234, (index & 1) * 8, index & 0xFF))
        coverage = set()
        calls = 0
        for case in cases:
            initial = fixture(case)
            wanted, expected_calls, result = reference(initial)
            model = PeriodicOracle(self.retail, initial, case).run()
            self.assertEqual((public(model.memory), model.calls, s32(model.r[2])),
                             (public(wanted), expected_calls, result))
            coverage.update(model.visits)
            calls += len(model.calls)
        static_divide_guards = {match.ENTRY + offset
                                for offset in (0x80, 0x90, 0x94, 0x98)}
        self.assertEqual(coverage | static_divide_guards,
                         set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt("guest-contract", {
            "cases": len(cases), "callbacks": calls,
            "reachable_words": len(coverage), "static_divide_guard_words": 4,
            "static_divide_guard_breaks": 2,
            "signed_tick_wrap": True, "multi_period_wrap": True,
            "actor_indices": [-1, 0, 1, 25], "callback_clobber": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_registry_abi_and_active_root_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"], ["0x23213c"])
        case = Case(17, 35, 0, 25, True, 0, 0x1234, 8, 7)
        initial = fixture(case)
        baseline = PeriodicOracle(self.retail, initial, case).run()
        states = []
        for cut in range(baseline.root_accesses):
            model = PeriodicOracle(self.retail, initial, case, fault=cut)
            with self.assertRaises(faults.AccessBoundary):
                model.run()
            states.append((model.current_pc, model.delay_of, model.root_accesses))
        self.assertEqual(len(states), baseline.root_accesses)
        self.assertGreater(len(states), 8)
        self.receipt("registry-and-faults", {
            "registry_pointer_offsets": evidence["aligned_pointer_literals"],
            "root_access_faults": states,
            "no_direct_call_sites_expected": True,
        })


if __name__ == "__main__":
    unittest.main()
