"""Height/effect/sound callback ABI and IEEE-single behavioral oracle."""

from dataclasses import dataclass
from pathlib import Path
import struct
import subprocess

from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path.cwd()
OUTPUT = ROOT / "conker/build/game-height-sound-probe-151A9BA0-match"
FUNCTION = "func_151A9BA0"
ENTRY = 0x151A9BA0
OWNER, ACTOR, OTHER = 0x30000, 0x70000, 0x90000
QUERY, EFFECT, SOUND = 0x15045800, 0x151ABE40, 0x10010FFC
SYMBOLS = {
    "D_800A8F7C": 0x800A8F7C,
    "func_15045800": QUERY,
    "func_151ABE40": EFFECT,
    "func_10010FFC": SOUND,
}


def bits(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


def floating(word):
    return struct.unpack(">f", struct.pack(">I", word))[0]


ROM = (ROOT / "conker/conker.us.bin").read_bytes()
THRESHOLD = struct.unpack_from(
    ">I", ROM, 0x2275E0 + SYMBOLS["D_800A8F7C"] - 0x80082B20)[0]


@dataclass(frozen=True)
class Case:
    top: int = bits(1000.0)
    y: int = bits(200.0)
    x: int = bits(125.25)
    z: int = bits(-75.5)
    outcome: int = 1
    mode: int = 0
    identity: int = 255
    category: int = 128
    height: int = bits(17.5)
    phase: int = 0

    @property
    def position(self):
        return STACK + self.phase - 16


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-1024, 1024)}
    for pointer, size in ((OWNER - 32, 256), (ACTOR - 32, 384),
                          (OTHER - 32, 384)):
        assert not (pointer < STACK + 1024 and pointer + size > STACK - 1024)
        memory.update({pointer + index: (index * 13 + 0x59) & 0xFF
                       for index in range(size)})
    put(memory, OWNER + 24, ACTOR)
    put(memory, ACTOR + 20, case.x)
    put(memory, ACTOR + 24, case.y)
    put(memory, ACTOR + 28, case.z)
    put(memory, ACTOR + 280, case.top)
    put(memory, SYMBOLS["D_800A8F7C"], THRESHOLD)
    memory[OWNER + 1] = case.identity
    memory[OWNER + 12] = case.category
    return memory


def effect(memory, case, target):
    if target == QUERY:
        put(memory, OWNER + 52, case.height)
        memory[OWNER + 80] ^= 0x40
        if case.mode & 1:
            memory[OWNER + 1] ^= 0xFF
            memory[OWNER + 12] ^= 0x55
        if case.mode & 2:
            put(memory, case.position, bits(-77.25))
            put(memory, case.position + 4, bits(-999.0))
            put(memory, case.position + 8, bits(99.5))
        if case.mode & 4:
            put(memory, OWNER + 24, OTHER)
    elif target == EFFECT:
        memory[OWNER + 53] ^= 0xAA
        memory[OWNER + 81] ^= 0x20
        if case.mode & 8:
            put(memory, OWNER + 24, OTHER)
    elif target == SOUND:
        memory[OWNER + 82] ^= 0x10


def reference(initial, case):
    memory = dict(initial)
    position = case.position
    top = floating(read(memory, ACTOR + 280))
    if floating(THRESHOLD) < top:
        y = bits(top + 100.0)
    else:
        y = bits(floating(read(memory, ACTOR + 24)) + 150.0)
    for index, value in enumerate((read(memory, ACTOR + 20), y,
                                   read(memory, ACTOR + 28))):
        put(memory, position + 4 * index, value)
    calls = [(QUERY, (position, 0, bits(floating(y) - 300.0), OWNER + 52),
              tuple(read(memory, position + 4 * index) for index in range(3)))]
    effect(memory, case, QUERY)
    if case.outcome:
        put(memory, position + 4, read(memory, OWNER + 52))
        calls.append((EFFECT,
                      (position, OWNER + 52, 1, memory[OWNER + 12],
                       memory[OWNER + 1]),
                      tuple(read(memory, position + 4 * index)
                            for index in range(3))))
        effect(memory, case, EFFECT)
        calls.append((SOUND, (0, 0x11, 0x5208, 0, 0, ACTOR), None))
        effect(memory, case, SOUND)
    return memory, calls


class Oracle(FactoryOracle):
    def __init__(self, words, memory, case, entry=ENTRY, connected=None):
        super().__init__(words, memory, case, entry=entry, s=SYMBOLS,
                         connected=connected, arguments=(OWNER,))

    def record_call(self, target):
        if target == QUERY:
            args = tuple(self.arguments(4))
            position = tuple(read(self.memory, args[0] + 4 * index)
                             for index in range(3))
        elif target == EFFECT:
            args = tuple(self.arguments(5))
            position = tuple(read(self.memory, args[0] + 4 * index)
                             for index in range(3))
        elif target == SOUND:
            args = tuple(self.arguments(6))
            position = None
        else:
            raise AssertionError("Unexpected height/sound target %08X" % target)
        self.calls.append((target, args, position))
        self.events.append(("CALL", target, args, position))

    def hook(self, target):
        effect(self.memory, self.case, target)
        for index in range(4):
            self.put(self.r[29] + 4 * index, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.condition = True
        self.r[2] = (self.case.outcome & 0xFFFFFFFF) if target == QUERY else 0


def linked(obj, label, entry=ENTRY, symbols=None):
    symbols = SYMBOLS if symbols is None else symbols
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    assembly, unknown = emit_function(
        text, function, relocations, FUNCTION, symbols)
    assert not unknown
    path = OUTPUT / label
    path.with_suffix(".s").write_text(assembly)
    path.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry +
        "\n".join("%s = 0x%X;" % item for item in symbols.items()))
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-march=vr4300", "-o",
        str(path.with_suffix(".o")), str(path.with_suffix(".s"))],
        capture_output=True, check=True)
    subprocess.run([
        "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T",
        str(path.with_suffix(".ld")), "-e", FUNCTION, "-o",
        str(path.with_suffix(".elf")), str(path.with_suffix(".o"))],
        capture_output=True, check=True)
    payload = sections(path.with_suffix(".elf"))[".text"][1][:function["size"]]
    return list(struct.unpack(">%dI" % (function["size"] // 4), payload))


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 1024 <= address < STACK + 1024}
