"""Screen semantic C forms for func_15190F9C's dual-phase position update."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x15190F9C
ROM = 0x1BE44C
WORDS = 60
FUNCTION = "func_15190F9C"
SOURCE = "conker/src/game/generated_1BA1D0.c"
BUILD = "conker/build/game-dual-phase-position-update-candidates"
DECLARATIONS = "extern s32 D_800BE9E4;\nf32 func_151423D8(u8);\n"
PLACEHOLDER = """s32 func_15190F9C() {
    return 0;
}"""
SELECTED = """/* Advance two phase bytes and ease the planar position toward their sampled offsets. */
s32 func_15190F9C(u8 *state) {
    u8 *parameters = state;
    f32 firstSample;
    f32 secondSample;
    f32 firstCurrent;
    f32 secondCurrent;

    state[0x131] += (s32)*(s8 *)(state + 0x133) * (u32)D_800BE9E4;
    state[0x132] += (s32)*(s8 *)(state + 0x134) * (u32)D_800BE9E4;
    firstSample = func_151423D8((u8)(state[0x131] - 0x40));
    parameters += 0x110;
    secondSample = func_151423D8((u8)(parameters[0x22] - 0x40));

    firstCurrent = *(f32 *)(state + 0x2C);
    secondCurrent = *(f32 *)(state + 0x30);
    *(f32 *)(state + 0x2C) =
        ((*(f32 *)(parameters + 0x30) * firstSample +
          *(f32 *)(parameters + 0x28)) - firstCurrent) * 0.5f + firstCurrent;
    *(f32 *)(state + 0x30) =
        ((*(f32 *)(parameters + 0x34) * secondSample +
          *(f32 *)(parameters + 0x2C)) - secondCurrent) * 0.5f + secondCurrent;
    return 1;
}"""
POINTER = """/* Advance two phase bytes and ease the planar position toward their sampled offsets. */
s32 func_15190F9C(u8 *state) {
    u8 *parameters;
    f32 firstSample;
    f32 secondSample;
    f32 current;

    state[0x131] += (s32)*(s8 *)(state + 0x133) * (u32)D_800BE9E4;
    state[0x132] += (s32)*(s8 *)(state + 0x134) * (u32)D_800BE9E4;
    firstSample = func_151423D8((u8)(state[0x131] - 0x40));
    parameters = state + 0x110;
    secondSample = func_151423D8((u8)(parameters[0x22] - 0x40));

    current = *(f32 *)(state + 0x2C);
    *(f32 *)(state + 0x2C) = current +
        ((*(f32 *)(parameters + 0x28) + *(f32 *)(parameters + 0x30) * firstSample) - current) * 0.5f;
    current = *(f32 *)(state + 0x30);
    *(f32 *)(state + 0x30) = current +
        ((*(f32 *)(parameters + 0x2C) + *(f32 *)(parameters + 0x34) * secondSample) - current) * 0.5f;
    return 1;
}"""
TYPED = """typedef struct {
    u8 pad0[0x21];
    u8 firstPhase;
    u8 secondPhase;
    s8 firstRate;
    s8 secondRate;
    u8 pad25[3];
    f32 firstBase;
    f32 secondBase;
    f32 firstScale;
    f32 secondScale;
} DualPhaseParameters15190F9C;

typedef struct {
    u8 pad0[0x2C];
    f32 firstPosition;
    f32 secondPosition;
    u8 pad34[0xDC];
    DualPhaseParameters15190F9C parameters;
} DualPhaseState15190F9C;

/* Advance two phase bytes and ease the planar position toward their sampled offsets. */
s32 func_15190F9C(DualPhaseState15190F9C *state) {
    DualPhaseParameters15190F9C *parameters;
    f32 firstSample;
    f32 secondSample;

    state->parameters.firstPhase +=
        (s32)state->parameters.firstRate * (u32)D_800BE9E4;
    state->parameters.secondPhase +=
        (s32)state->parameters.secondRate * (u32)D_800BE9E4;
    firstSample = func_151423D8((u8)(state->parameters.firstPhase - 0x40));
    parameters = &state->parameters;
    secondSample = func_151423D8((u8)(parameters->secondPhase - 0x40));

    state->firstPosition +=
        ((parameters->firstBase + parameters->firstScale * firstSample) -
         state->firstPosition) * 0.5f;
    state->secondPosition +=
        ((parameters->secondBase + parameters->secondScale * secondSample) -
         state->secondPosition) * 0.5f;
    return 1;
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if body not in source:
        if source.count(PLACEHOLDER) != 1:
            raise ValueError("Dual-phase position source state changed")
        source = source.replace(PLACEHOLDER, body)
    if DECLARATIONS not in source:
        marker = '#include "structs.h"\n'
        if source.count(marker) != 1:
            raise ValueError("Owner include marker changed")
        source = source.replace(marker, marker + DECLARATIONS, 1)
    return source


def variants():
    yield "selected", SELECTED
    yield "pointer", POINTER
    yield "typed", TYPED
    yield "pointer-direct-current", POINTER.replace(
        "    f32 current;\n", "").replace(
        "    current = *(f32 *)(state + 0x2C);\n"
        "    *(f32 *)(state + 0x2C) = current +\n"
        "        ((*(f32 *)(parameters + 0x28) + *(f32 *)(parameters + 0x30) * firstSample) - current) * 0.5f;",
        "    *(f32 *)(state + 0x2C) +=\n"
        "        ((*(f32 *)(parameters + 0x28) + *(f32 *)(parameters + 0x30) * firstSample) -\n"
        "         *(f32 *)(state + 0x2C)) * 0.5f;").replace(
        "    current = *(f32 *)(state + 0x30);\n"
        "    *(f32 *)(state + 0x30) = current +\n"
        "        ((*(f32 *)(parameters + 0x2C) + *(f32 *)(parameters + 0x34) * secondSample) - current) * 0.5f;",
        "    *(f32 *)(state + 0x30) +=\n"
        "        ((*(f32 *)(parameters + 0x2C) + *(f32 *)(parameters + 0x34) * secondSample) -\n"
        "         *(f32 *)(state + 0x30)) * 0.5f;")
    yield "unsigned-rate", SELECTED.replace(
        "(s32)*(s8 *)(state + 0x133)", "*(s8 *)(state + 0x133)").replace(
        "(s32)*(s8 *)(state + 0x134)", "*(s8 *)(state + 0x134)")
    yield "direct-current", SELECTED.replace(
        "    f32 current;\n", "").replace(
        "    current = *(f32 *)(state + 0x2C);\n"
        "    *(f32 *)(state + 0x2C) = current +\n"
        "        ((*(f32 *)(state + 0x138) + *(f32 *)(state + 0x140) * firstSample) - current) * 0.5f;",
        "    *(f32 *)(state + 0x2C) +=\n"
        "        ((*(f32 *)(state + 0x138) + *(f32 *)(state + 0x140) * firstSample) -\n"
        "         *(f32 *)(state + 0x2C)) * 0.5f;").replace(
        "    current = *(f32 *)(state + 0x30);\n"
        "    *(f32 *)(state + 0x30) = current +\n"
        "        ((*(f32 *)(state + 0x13C) + *(f32 *)(state + 0x144) * secondSample) - current) * 0.5f;",
        "    *(f32 *)(state + 0x30) +=\n"
        "        ((*(f32 *)(state + 0x13C) + *(f32 *)(state + 0x144) * secondSample) -\n"
        "         *(f32 *)(state + 0x30)) * 0.5f;")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name, flags=flags)
    linked, functions = link_owner(ROOT, output, obj, "generated_1BA1D0")
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0))
        if left != right
    ]
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    records = []
    for name, body in variants():
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
