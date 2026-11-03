"""Screen semantic C forms for func_151B9214's timed oscillation transition."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151B9214
ROM = 0x1E66C4
WORDS = 63
FUNCTION = "func_151B9214"
SOURCE = "conker/src/game/generated_1E6260.c"
OWNER = "generated_1E6260"
BUILD = "conker/build/game-timed-oscillation-transition-candidates"
DECLARATIONS = """extern f32 D_800BE9A4;
extern f32 D_800AA564;
f32 func_15144B68(f32);
f32 sinf(f32);
"""
TYPES = """typedef struct {
    f32 oscillation;
    f32 amplitude;
    f32 phase;
    f32 phaseRate;
    f32 targetAmplitude;
    f32 targetPhaseRate;
    f32 transitionTime;
    f32 amplitudeVelocity;
    f32 phaseRateVelocity;
} TimedOscillationTransition151B9214;
"""
PLACEHOLDER = """s32 func_151B9214() {
    return 0;
}"""
SELECTED = """/* Advance the oscillation and transition its amplitude and phase rate. */
s32 func_151B9214(u8 *owner) {
    TimedOscillationTransition151B9214 *state =
        (TimedOscillationTransition151B9214 *)(owner + 0x170);

    state->phase += state->phaseRate * D_800BE9A4;
    state->phase = func_15144B68(state->phase);
    state->oscillation = sinf(state->phase) * state->amplitude;
    if (0.0f < state->transitionTime) {
        state->transitionTime -= D_800BE9A4;
        state->phaseRate += state->phaseRateVelocity * D_800BE9A4;
        state->amplitude += state->amplitudeVelocity * D_800BE9A4;
    } else {
        state->phaseRate +=
            (state->targetPhaseRate - state->phaseRate) * D_800AA564;
        state->amplitude +=
            (state->targetAmplitude - state->amplitude) * D_800AA564;
    }
    return 1;
}"""
SELECTED_GUARDED = SELECTED.replace(
    "        (TimedOscillationTransition151B9214 *)(owner + 0x170);\n\n"
    "    state->phase",
    "        (TimedOscillationTransition151B9214 *)(owner + 0x170);\n"
    "    f32 transitionScale;\n\n"
    "    state->phase").replace(
    "    } else {\n"
    "        state->phaseRate +=\n"
    "            (state->targetPhaseRate - state->phaseRate) * D_800AA564;\n"
    "        state->amplitude +=\n"
    "            (state->targetAmplitude - state->amplitude) * D_800AA564;",
    "    } else {\n"
    "        transitionScale = D_800AA564;\n"
    "        state->phaseRate +=\n"
    "            (state->targetPhaseRate - state->phaseRate) * transitionScale;\n"
    "        state->amplitude +=\n"
    "            (state->targetAmplitude - state->amplitude) * transitionScale;")
RAW = """/* Advance the oscillation and transition its amplitude and phase rate. */
s32 func_151B9214(u8 *owner) {
    f32 *state = (f32 *)(owner + 0x170);

    state[2] += state[3] * D_800BE9A4;
    state[2] = func_15144B68(state[2]);
    state[0] = sinf(state[2]) * state[1];
    if (0.0f < state[6]) {
        state[6] -= D_800BE9A4;
        state[3] += state[8] * D_800BE9A4;
        state[1] += state[7] * D_800BE9A4;
    } else {
        state[3] += (state[5] - state[3]) * D_800AA564;
        state[1] += (state[4] - state[1]) * D_800AA564;
    }
    return 1;
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if source.count(PLACEHOLDER) != 1:
        raise ValueError("Timed oscillation transition placeholder changed")
    source = source.replace(PLACEHOLDER, body)
    anchor = "#include <ultra64.h>\n"
    if source.count(anchor) != 1:
        raise ValueError("Timed oscillation transition include anchor changed")
    return source.replace(anchor, anchor + TYPES + DECLARATIONS + "\n", 1)


def variants():
    yield "typed", SELECTED
    yield "typed-local-scale", SELECTED_GUARDED
    yield "typed-register-scale", SELECTED_GUARDED.replace(
        "    f32 transitionScale;", "    register f32 transitionScale;")
    yield "raw", RAW
    yield "typed-direct-target", SELECTED.replace(
        "        state->phaseRate +=\n"
        "            (state->targetPhaseRate - state->phaseRate) * D_800AA564;\n"
        "        state->amplitude +=\n"
        "            (state->targetAmplitude - state->amplitude) * D_800AA564;",
        "        state->phaseRate = state->phaseRate +\n"
        "            (state->targetPhaseRate - state->phaseRate) * D_800AA564;\n"
        "        state->amplitude = state->amplitude +\n"
        "            (state->targetAmplitude - state->amplitude) * D_800AA564;")
    yield "typed-reverse-positive", SELECTED.replace(
        "        state->phaseRate += state->phaseRateVelocity * D_800BE9A4;\n"
        "        state->amplitude += state->amplitudeVelocity * D_800BE9A4;",
        "        state->amplitude += state->amplitudeVelocity * D_800BE9A4;\n"
        "        state->phaseRate += state->phaseRateVelocity * D_800BE9A4;")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name, flags=flags)
    linked, functions = link_owner(ROOT, output, obj, OWNER)
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
