"""Guest execution oracle for the byte-exact effect-actor update callback."""
from pathlib import Path
import json
import struct
import subprocess

from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


STATE = 0x30000


def symbols(layout):
    return {
        "sinf": (0x15047D60, 0x17148000, 0x17248000)[layout],
        "D_800BE9A4": (0x800BE9A4, 0x03437FFC, 0x02448000)[layout],
    }


def link(obj, output, source, layout):
    syms = symbols(layout)
    entry = (source.ENTRY, 0x17038000, 0x1F00FFFC)[layout]
    text, functions, relocations = parse_object(obj)
    assembly, unknown = emit_function(text, functions[source.FUNCTION], relocations,
                                      source.FUNCTION, syms)
    assert not unknown
    path = output / ("guest-layout-%d" % layout)
    path.with_suffix(".s").write_text(assembly)
    path.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry
        + "\n".join("%s = 0x%X;" % item for item in syms.items()))
    subprocess.run(["mips-linux-gnu-as", "-EB", "-march=vr4300", "-o",
                    str(path.with_suffix(".o")), str(path.with_suffix(".s"))], check=True)
    subprocess.run(["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T",
                    str(path.with_suffix(".ld")), "-e", source.FUNCTION, "-o",
                    str(path.with_suffix(".elf")), str(path.with_suffix(".o"))], check=True)
    raw = sections(path.with_suffix(".elf"))[".text"][1][:source.SIZE]
    return entry, syms, list(struct.unpack(">%dI" % source.WORDS, raw))


def fixture(index, syms):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF for i in range(-256, 256)}
    memory.update({STATE + i: (i * 13 + index * 7) & 0xFF for i in range(512)})
    lifetime = (0.0, -0.5, 0.25, 1.0, 3.0, 9.0)[index % 6]
    values = {0x170: lifetime, 0x174: (index % 11 - 5) * 0.5,
              0x178: float(index & 255), 0x17C: (index % 17 - 8) * 0.25,
              0x180: (index % 13 - 6) * 0.125,
              0x20: float(index), 0x24: float(index) * 0.5, 0x28: -float(index),
              0x50: 0.5, 0x54: -0.25, 0x58: 1.25}
    for offset, value in values.items():
        put(memory, STATE + offset, bits(value))
    put(memory, syms["D_800BE9A4"], bits(0.5 if index & 2 else 1.0))
    return memory


def wave(index):
    return (0.0, 0.25, 0.5, 0.75, 1.0)[index % 5]


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 256 <= address < STACK + 256}


def reference(initial, index, syms):
    memory = dict(initial)
    phase = read(memory, STATE + 0x17C)
    if index & 1:
        put(memory, syms["D_800BE9A4"], bits(0.25))
        put(memory, STATE + 0x174, bits(3.0))
    answer = bits(wave(index))
    scale = fp(read(memory, STATE + 0x174), answer, "mul")
    put(memory, STATE + 0x1C, scale); put(memory, STATE + 0x18, scale)
    opacity = int(floating(read(memory, STATE + 0x178))) & 0xFF
    memory[STATE + 0x70] = int(opacity * wave(index)) & 0xFF
    dt = read(memory, syms["D_800BE9A4"])
    lifetime = fp(read(memory, STATE + 0x170), dt, "sub")
    put(memory, STATE + 0x170, lifetime)
    result = 0
    if floating(lifetime) > 0.0:
        put(memory, STATE + 0x17C, fp(read(memory, STATE + 0x17C),
            fp(read(memory, STATE + 0x180), dt, "mul"), "add"))
        for position, velocity in ((0x20, 0x50), (0x24, 0x54), (0x28, 0x58)):
            put(memory, STATE + position, fp(read(memory, STATE + position),
                fp(read(memory, STATE + velocity), dt, "mul"), "add"))
        result = 1
    return memory, result, phase


class Oracle(AreaOracle):
    def __init__(self, words, memory, index, entry, syms):
        self.index = index
        super().__init__(words, memory, (STATE,), entry=entry)
        self.syms = syms
    def record_call(self, target):
        assert target == self.syms["sinf"]
        self.calls.append((target, (self.f[12],)))
    def hook(self, target):
        assert target == self.syms["sinf"]
        if self.index & 1:
            put(self.memory, self.syms["D_800BE9A4"], bits(0.25))
            put(self.memory, STATE + 0x174, bits(3.0))
        self.f[0] = bits(wave(self.index))


def qualify(root, output, source):
    programs = []
    for layout in range(3):
        entry, syms, original = link(root / source.OBJECT, output, source, layout)
        _, _, candidate = link(output / "selected-final.o", output, source, layout)
        assert original == candidate
        programs.append((entry, syms, original))
    covered = set(); executions = 0
    for entry, syms, words in programs:
        for index in range(256):
            initial = fixture(index, syms)
            expected, result, phase = reference(initial, index, syms)
            machine = Oracle(words, initial, index, entry, syms).run()
            assert (public(machine.memory), machine.r[2]) == (public(expected), result)
            assert machine.calls == [(syms["sinf"], (phase,))]
            covered.update(pc - entry for pc in machine.visits
                           if entry <= pc < entry + source.SIZE); executions += 1
    report = {"success": True, "private_only": True, "matching_credit": 0,
              "cases_per_layout": 256, "independent_links": 3,
              "executions": executions, "words": source.WORDS,
              "covered_words": len(covered), "positive_zero_negative_lifetime": True,
              "all256_opacity_inputs": True, "live_sine_mutations": True,
              "original_and_raw_C_words_equal": True}
    (output / "private-guest-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
