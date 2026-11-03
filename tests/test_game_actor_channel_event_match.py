"""Direct C, semantics, ABI, caller, owner and image gates for func_15172E7C."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_channel_event_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


ACTOR, STATE = 0x220000, 0x230000
EFFECT, FALLBACK = 0x1517EE40, 0x15172D28
CHANNELS, PAYLOADS, MODE = 0x800DD2B0, 0x800DD2C0, 0x800BE9F0


def signed8(value):
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


def fixture(health, channel, state_value, camera, current, selector, payload,
            mode, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x180, 0x100)}
    memory.update({ACTOR + i: (i * 13 + 0x59) & 0xFF for i in range(0x340)})
    memory.update({STATE + i: (i * 29 + 0x71) & 0xFF for i in range(0x40)})
    memory.update({CHANNELS + i: 0x55 for i in range(16)})
    memory.update({PAYLOADS + i: 0x66 for i in range(16)})
    memory[ACTOR + 0x127] = channel & 0xFF
    memory[ACTOR + 0x1CA] = health & 0xFF
    put(memory, ACTOR + 0x2F8, 0xA520, 2)
    put(memory, ACTOR + 0x318, 0x240000 if camera else 0)
    put(memory, ACTOR + 0x31C, 0 if state_value is None else STATE)
    if state_value is not None:
        memory[STATE + 0x23] = state_value & 0xFF
    memory[CHANNELS + channel] = current & 0xFF
    memory[PAYLOADS + channel] = 0x6D
    put(memory, MODE, mode)
    return memory


def external(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x180 <= address < STACK + 0x100}


def reference(initial, health, channel, state_value, camera, current,
              selector, payload, mode):
    memory, calls = dict(initial), []
    state_open = state_value is None or signed8(state_value) <= 0
    if health != 0 and state_open:
        if camera:
            if signed8(current) == -1:
                calls.append((EFFECT, (0, 0, 0, 10, 1, channel)))
                flags = read(memory, ACTOR + 0x2F8, 2)
                put(memory, ACTOR + 0x2F8, flags | 0x10, 2)
                memory[CHANNELS + channel] = selector & 0xFF
                memory[PAYLOADS + channel] = payload & 0xFF
        elif selector & 0xFFFFFFFF == mode & 0xFFFFFFFF:
            calls.append((FALLBACK, (ACTOR, payload & 0xFFFFFFFF)))
    return memory, calls


class ChannelOracle(TimingOracle):
    def __init__(self, words, memory, selector, payload, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(ACTOR, selector, payload))

    def execute(self, word):
        op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
        if op == 32:  # LB
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            address = (self.r[rs] + immediate) & 0xFFFFFFFF
            self.r[rt] = signed8(self.get(address, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        if target == EFFECT:
            args = self.arguments(6)
        elif target == FALLBACK:
            args = self.arguments(2)
        else:
            raise AssertionError("Unexpected actor-channel call %08X" % target)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target not in (EFFECT, FALLBACK):
            raise AssertionError("Unexpected actor-channel hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return """typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;
#define NULL ((void *)0)
typedef struct {
    u8 pad0[0x127];
    u8 unk127;
    u8 pad128[0xA2];
    u8 health;
    u8 pad1CB[0x12D];
    u16 unk2F8;
    u8 pad2FA[0x1E];
    void *camera;
    void *unk31C;
} struct127;
s32 D_800BE9F0;
signed char D_800DD2B0[16];
u8 D_800DD2C0[16];
void func_15172D28(u8 *, s32);
void func_1517EE40(s32, s32, s32, s32, signed char, s32);
%s
static struct127 actor;
static signed char state[64];
static s32 callKind, badArgs;
void func_1517EE40(s32 a0, s32 a1, s32 a2, s32 a3,
                   signed char a4, s32 a5) {
    callKind = 1;
    if (a0 || a1 || a2 || a3 != 10 || a4 != 1 || a5 != actor.unk127)
        badArgs = 1;
}
void func_15172D28(u8 *owner, s32 payload) {
    callKind = 2;
    if (owner != (u8 *)&actor || payload != 0x76543210) badArgs = 1;
}
static int one(s32 health, s32 stateKind, s32 camera, s32 current,
               s32 selector, s32 mode) {
    s32 expectedKind = 0;
    s32 open;
    actor.unk127 = 5;
    actor.health = (u8)health;
    actor.unk2F8 = 0xA520;
    actor.camera = camera ? (void *)1 : 0;
    actor.unk31C = stateKind ? state : 0;
    state[0x23] = stateKind == 1 ? -1 : 1;
    D_800DD2B0[5] = (signed char)current;
    D_800DD2C0[5] = 0x6D;
    D_800BE9F0 = mode;
    callKind = badArgs = 0;
    open = stateKind == 0 || stateKind == 1;
    if (health && open) {
        if (camera && (signed char)current == -1) expectedKind = 1;
        else if (!camera && selector == mode) expectedKind = 2;
    }
    func_15172E7C(&actor, selector, 0x76543210);
    if (badArgs || callKind != expectedKind) return 10;
    if (actor.unk2F8 != (expectedKind == 1 ? 0xA530 : 0xA520)) return 11;
    if ((u8)D_800DD2B0[5] != (expectedKind == 1 ? (u8)selector : (u8)current)) return 12;
    if (D_800DD2C0[5] != (expectedKind == 1 ? 0x10 : 0x6D)) return 13;
    return 0;
}
static int run(void) {
    static const s32 selectors[] = {0, 0x35, 0x135, -1};
    static const s32 modes[] = {0, 0x35, 0x135, -1};
    s32 h, s, c, q, i, j;
    for (h = 0; h < 2; h++)
        for (s = 0; s < 3; s++)
            for (c = 0; c < 2; c++)
                for (q = 0; q < 2; q++)
                    for (i = 0; i < 4; i++)
                        for (j = 0; j < 4; j++)
                            if (one(h, s, c, q ? 0 : -1,
                                    selectors[i], modes[j])) return 20;
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class ActorChannelEventMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, rom, match.ROM))

    def test_01_direct_C_owner_dependent_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["slot_words"],
                          self.report["frame"], self.report["natural_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (59, 61, 48, 0, 0, 8))
        self.assertEqual(self.report["neighbors"], 4)
        self.assertEqual(self.report["dependent_functions_fixed"], 28)
        self.assertTrue(self.report["dependent_identical"])
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_paths_aliases_stack_phases_and_all_words(self):
        visits, cases = set(), 0
        selector_modes = (
            (0, 0), (0x35, 0x35), (0x135, 0x35),
            (0x135, 0x135), (0xFFFFFFFF, 0xFFFFFFFF))
        for health, state_value, camera, current, pair, payload, phase in itertools.product(
                (0, 1), (None, -1, 0, 1), (0, 1), (-1, 0),
                selector_modes, (0, 0x76543210, 0xFFFFFFFF), (0, 8)):
            selector, mode = pair
            channel = (health * 7 + camera * 3 + phase) & 0xF
            initial = fixture(health, channel, state_value, camera, current,
                              selector, payload, mode, phase)
            wanted, calls = reference(
                initial, health, channel, state_value, camera, current,
                selector, payload, mode)
            model = ChannelOracle(
                self.words, initial, selector, payload, phase).run()
            self.assertEqual(external(model.memory), external(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 960)

    def compile_native(self, body, label, optimization):
        source = self.output / (label + optimization + ".c")
        binary = self.output / (label + optimization)
        source.write_text(native_harness(body))
        result = subprocess.run([
            "gcc", "-m32", optimization, "-std=gnu89", "-ffreestanding",
            "-nostdlib", "-static", "-fno-pie", "-no-pie",
            "-fno-stack-protector", "-fno-strict-aliasing",
            "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
            "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
            capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_03_native32_profiles_and_effective_controls(self):
        body = match.SELECTED
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
        controls = {
            "ignore-health": body.replace("actor->health != 0", "actor->health == 0"),
            "wrong-state": body.replace("[0x23] <= 0", "[0x23] > 0"),
            "wrong-camera": body.replace("actor->camera != NULL", "actor->camera == NULL"),
            "wrong-slot": body.replace("D_800DD2B0[channel] == -1", "D_800DD2B0[channel] != -1"),
            "wrong-duration": body.replace("0xA, 1, channel", "9, 1, channel"),
            "no-flag": body.replace("actor->unk2F8 |= 0x10;", "actor->unk2F8 |= 0;"),
            "wrong-selector": body.replace("D_800DD2B0[channel] = selector;", "D_800DD2B0[channel] = payload;"),
            "wrong-payload": body.replace("D_800DD2C0[channel] = payload;", "D_800DD2C0[channel] = selector;"),
            "wrong-fallback": body.replace("selector == D_800BE9F0", "selector != D_800BE9F0"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)

    def test_04_retail_callers_and_live_installed_state(self):
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        opcode = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        found = [offset for offset in range(0, len(rom) - 3, 4)
                 if struct.unpack_from(">I", rom, offset)[0] == opcode]
        self.assertEqual(found, [0xCCF48, 0xCF070, 0xCFCD0])
        predecessor, qualified, installed = match.source_states(
            (self.root / match.SOURCE).read_text())
        old_dependent, new_dependent, dependent_installed = match.dependent_states(
            (self.root / match.DEPENDENT_SOURCE).read_text())
        self.assertEqual((installed, dependent_installed),
                         (self.report["installed"], self.report["installed"]))
        expected_owner = self.qualified_owner if installed else self.predecessor_owner
        expected_elf = self.qualified_elf if installed else self.predecessor_elf
        self.assertEqual((self.root / match.OBJECT).read_bytes(),
                         expected_owner.read_bytes())
        self.assertEqual((self.root / match.ELF).read_bytes(),
                         expected_elf.read_bytes())
        self.assertNotEqual(predecessor, qualified)
        self.assertNotEqual(old_dependent, new_dependent)
        self.assertIn(match.NEW_DECLARATION, new_dependent)
        self.assertIn("func_15172E7C(actor, D_800D3098[index].field17,",
                      new_dependent)


if __name__ == "__main__":
    unittest.main()
