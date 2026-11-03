"""Direct C, semantics, ABI, owner, and image gates for func_15043BB8."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_ring_message_send_match as match
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


QUEUE, RING, INPUT, HELPER = 0x220000, 0x230000, 0x240000, 0x15043A20


def signed(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def fixture(capacity, read_cursor, write_cursor, length, phase, queue=QUEUE,
            input_pointer=INPUT):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    memory.update({RING + i: (i * 13 + 0x59) & 0xFF for i in range(128)})
    memory.update({INPUT + i: (i * 29 + 0x71) & 0xFF for i in range(64)})
    put(memory, queue, RING)
    put(memory, queue + 4, capacity)
    put(memory, queue + 8, read_cursor)
    put(memory, queue + 12, write_cursor)
    return memory


def visible(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def transfer(memory, ring, capacity, cursor, source, count):
    for index in range(count):
        memory[ring + (cursor + index) % capacity] = memory[source + index]
    return (cursor + count) % capacity if count else cursor


def reference(initial, capacity, read_cursor, write_cursor, length, phase,
              queue=QUEUE, input_pointer=INPUT):
    memory = dict(initial)
    if length == 0 or input_pointer == 0:
        return memory, [], 0
    total = (length + 7) & 0xFFFFFFFC
    if signed(write_cursor) < signed(read_cursor):
        full = not signed(write_cursor + total) < signed(read_cursor)
    else:
        full = not signed(write_cursor + total - capacity) < signed(read_cursor)
    if full:
        return memory, [], 1
    payload = (total - 4) & 0xFFFFFFFF
    header = STACK + phase + 8
    for index, value in enumerate(struct.pack(">I", payload)):
        memory[header + index] = value
    first = transfer(memory, RING, capacity, write_cursor, header, 4)
    final = transfer(memory, RING, capacity, first, input_pointer, payload)
    put(memory, queue + 12, final)
    calls = [
        (HELPER, (RING, capacity, write_cursor, header, 4)),
        (HELPER, (RING, capacity, first, input_pointer, payload)),
    ]
    return memory, calls, 0


class WriterOracle(TimingOracle):
    def __init__(self, words, memory, length, phase=0, entry=match.ENTRY,
                 queue=QUEUE, input_pointer=INPUT, connected=None):
        super().__init__(words, memory, phase=phase, entry=entry,
                         arguments=(queue, input_pointer, length),
                         connected=connected)

    def record_call(self, target):
        if target == HELPER:
            arguments = self.arguments(5)
        elif target == match.ENTRY:
            arguments = self.arguments(3)
        else:
            raise AssertionError("Unexpected ring writer call %08X" % target)
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected hooked call %08X" % target)
        ring, capacity, cursor, source, count = self.calls[-1][1]
        if capacity <= 0 or count > 64:
            raise AssertionError("Unbounded writer helper fixture")
        for index in range(count):
            self.put(ring + (cursor + index) % capacity,
                     self.get(source + index, 1), 1)
        result = (cursor + count) % capacity if count else cursor
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.r[2] = result


def native_harness(body):
    return """typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef struct { s32 unk0, unk4, unk8, unkC; } struct105;
s32 func_15043A20(u8 *, s32, s32, u8 *, s32);
%s
static u8 ring[64], input[64], expected[64];
static unsigned calls;
s32 func_15043A20(u8 *target, s32 capacity, s32 cursor, u8 *source, s32 count) {
    s32 i;
    calls++;
    if (target != ring || capacity <= 0 || count < 0 || count > 32) return -99;
    for (i = 0; i < count; i++) target[(cursor + i) %% capacity] = source[i];
    return count ? (cursor + count) %% capacity : cursor;
}
static int one(s32 capacity, s32 readCursor, s32 writeCursor,
               s32 length, int nullInput) {
    struct105 queue;
    s32 i, total, payload, full, first, final = writeCursor, result;
    u8 *header;
    for (i = 0; i < 64; i++) {
        ring[i] = expected[i] = (u8)(i * 13 + 0x59);
        input[i] = (u8)(i * 29 + 0x71);
    }
    queue.unk0 = (s32)ring;
    queue.unk4 = capacity;
    queue.unk8 = readCursor;
    queue.unkC = writeCursor;
    calls = 0;
    total = (length + 7) & ~3;
    full = writeCursor < readCursor ? writeCursor + total >= readCursor :
           writeCursor + total - capacity >= readCursor;
    if (length == 0 || nullInput) {
        full = 0;
        result = 0;
    } else if (full) {
        result = 1;
    } else {
        payload = total - 4;
        header = (u8 *)&payload;
        for (i = 0; i < 4; i++) expected[(writeCursor + i) %% capacity] = header[i];
        first = (writeCursor + 4) %% capacity;
        for (i = 0; i < payload; i++) expected[(first + i) %% capacity] = input[i];
        final = (first + payload) %% capacity;
        result = 0;
    }
    if (func_15043BB8(&queue, nullInput ? (u8 *)0 : input, length) != result)
        return 20;
    if (calls != ((!length || nullInput || full) ? 0u : 2u)) return 21;
    if (queue.unk0 != (s32)ring || queue.unk4 != capacity ||
        queue.unk8 != readCursor || queue.unkC !=
        ((!length || nullInput || full) ? writeCursor : final)) return 22;
    for (i = 0; i < 64; i++) if (ring[i] != expected[i]) return 23;
    return 0;
}
static int run(void) {
    s32 capacity, readCursor, writeCursor, length, nullInput;
    for (capacity = 8; capacity <= 24; capacity += 8)
        for (readCursor = 0; readCursor < capacity; readCursor++)
            for (writeCursor = 0; writeCursor < capacity; writeCursor++)
                for (length = 0; length <= 9; length++)
                    for (nullInput = 0; nullInput < 2; nullInput++)
                        if (one(capacity, readCursor, writeCursor,
                                length, nullInput)) return 30;
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class RingMessageSendMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, rom, match.ROM))

    def test_01_direct_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (59, 40, 0, 0, 2))
        self.assertEqual(self.report["neighbors"], 15)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_ring_full_wrap_alignment_and_all_words(self):
        visits = set()
        cases = 0
        for capacity, read_cursor, write_cursor, length, phase, null_input in itertools.product(
                (8, 16, 24), range(0, 8), range(0, 8),
                (0, 1, 2, 3, 4, 5, 7, 9), (0, 8), (False, True)):
            read_cursor %= capacity
            write_cursor %= capacity
            input_pointer = 0 if null_input else INPUT
            initial = fixture(capacity, read_cursor, write_cursor, length, phase,
                              input_pointer=input_pointer)
            wanted, calls, answer = reference(
                initial, capacity, read_cursor, write_cursor, length, phase,
                input_pointer=input_pointer)
            model = WriterOracle(self.words, initial, length, phase,
                                 input_pointer=input_pointer).run()
            self.assertEqual(visible(model.memory), visible(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], answer)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        for phase in (0, 8):
            initial = fixture(16, 15, 0, 1, phase)
            wanted, calls, answer = reference(initial, 16, 15, 0, 1, phase)
            model = WriterOracle(self.words, initial, 1, phase).run()
            self.assertEqual(visible(model.memory), visible(wanted))
            self.assertEqual((model.calls, model.r[2]), (calls, answer))
            visits.update(model.visits)
            cases += 1
        # The duplicate load at +0x90 is skipped by both branch-likely paths.
        self.assertEqual(
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits,
            {match.ENTRY + 0x90})
        self.assertEqual(cases, 6146)

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
            "wrong-align": body.replace("(length + 3) & ~3", "length & ~3"),
            "allow-equality": body.replace(">= queue->unk8", "> queue->unk8"),
            "no-capacity": body.replace(" - queue->unk4", ""),
            "wrong-payload": body.replace("length -= 4;", "length -= 0;"),
            "wrong-source": body.replace("input, length);", "(u8 *)&length, length);"),
            "no-publication": body.replace("queue->unkC = cursor;", "queue->unkC = queue->unkC;"),
            "wrong-full-result": body.replace("return 1;", "return 0;"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)

    def test_04_retail_caller_and_live_installed_state(self):
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        opcode = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        found = [offset for offset in range(0, len(rom) - 3, 4)
                 if struct.unpack_from(">I", rom, offset)[0] == opcode]
        self.assertEqual(found, [0x12570])
        predecessor, qualified, installed = match.source_states(
            (self.root / match.SOURCE).read_text())
        old_header, new_header, header_installed = match.header_states(
            (self.root / match.HEADER).read_text())
        self.assertEqual((installed, header_installed),
                         (self.report["installed"], self.report["installed"]))
        expected_owner = self.qualified_owner if installed else self.predecessor_owner
        expected_elf = self.qualified_elf if installed else self.predecessor_elf
        self.assertEqual((self.root / match.OBJECT).read_bytes(),
                         expected_owner.read_bytes())
        self.assertEqual((self.root / match.ELF).read_bytes(),
                         expected_elf.read_bytes())
        self.assertNotEqual(predecessor, qualified)
        self.assertNotEqual(old_header, new_header)
        wrapper = (self.root / "conker/src/init_12560.c").read_text()
        self.assertIn("func_15043BB8(&D_800427A0, arg1, arg2);", wrapper)
        wrapper_words = list(struct.unpack_from(">10I", rom, 0x12560))
        connected = {match.ENTRY + index * 4: word
                     for index, word in enumerate(self.words)}
        fixed_queue = 0x800427A0
        for read_cursor, write_cursor, length, phase in (
                (15, 0, 1, 0), (4, 3, 9, 8), (0, 0, 0, 0)):
            initial = fixture(16, read_cursor, write_cursor, length, phase,
                              queue=fixed_queue)
            wanted, helper_calls, answer = reference(
                initial, 16, read_cursor, write_cursor, length, phase,
                queue=fixed_queue)
            model = WriterOracle(
                wrapper_words, initial, length, phase, entry=0x10012560,
                queue=0xDEADBEEF, connected=connected).run()
            self.assertEqual(visible(model.memory), visible(wanted))
            if helper_calls:
                target, arguments = helper_calls[0]
                helper_calls[0] = (target, (*arguments[:3], arguments[3] - 24,
                                             arguments[4]))
            self.assertEqual(model.calls, [
                (match.ENTRY, (fixed_queue, INPUT, length)), *helper_calls])
            self.assertEqual(model.r[2], answer)


if __name__ == "__main__":
    unittest.main()
