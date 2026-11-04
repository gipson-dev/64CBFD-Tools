"""Qualify func_151218C4's actor/view reset as guarded semantic C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_state_reset_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


BASE_FUNCTION_BLOB = harness.function_blob


FUNCTION = candidate.FUNCTION
FILENAME = "generated_14D110"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_14D110.c.o"
ASM = "conker/asm/14D110.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-actor-state-reset-151218C4-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_SIZE = 66 * 4
NATURAL_FRAME = RETAIL_FRAME = 0x28
# Compact relocatable object bytes; the candidate screen's linked-body digest is
# recorded separately by its report after resolving both JAL relocations.
RAW_SHA256 = "cf1916459a330b68a9248e0cc24787548e7e7a20018b4857f4dd0813f6522764"
RETAIL_SHA256 = "6c1dc094e0c5a9c5dfaf0492a38a25029b2a430a7f9e9f0e18774fc134577bc2"
BINDINGS = {
    0x0D4: [("R_MIPS_26", "func_1506160C")],
    0x0E8: [("R_MIPS_26", "func_151C9ED4")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = (
    dict(offset="0x074", expected="0xA60B084A", replacement="0x44800000",
         note="Schedule the shared floating-zero load before the fallback timer store"),
    dict(offset="0x078", expected="0x44800000", replacement="0xA60B084A",
         note="Schedule the fallback timer store after the shared floating-zero load"),
    dict(offset="0x090", expected="0xE6040374", replacement="0x26020740",
         note="Form the shared view-state base before publishing the reset distance"),
    dict(offset="0x094", expected="0x26020740", replacement="0xE6040374",
         note="Publish the reset distance after forming the shared view-state base"),
)
COMMENT_BEFORE = "/* Non-matching placeholders for the text-only asm slice asm/14D110.s. */"
COMMENT_AFTER = "/* Restored functions and remaining placeholders for asm/14D110.s. */"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.SELECTED in live or
                candidate.SELECTED_DECLARATIONS in live or
                live.count(COMMENT_BEFORE) != 1 or COMMENT_AFTER in live):
            raise ValueError("Actor-state reset predecessor source changed")
        qualified = live.replace(
            marker, marker + candidate.SELECTED_DECLARATIONS, 1
        ).replace(COMMENT_BEFORE, COMMENT_AFTER, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1
        )
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.SELECTED_DECLARATIONS) != 1 or
                live.count(COMMENT_AFTER) != 1 or
                candidate.PLACEHOLDER in live or COMMENT_BEFORE in live):
            raise ValueError("Installed actor-state reset source changed")
        predecessor = live.replace(
            candidate.SELECTED_DECLARATIONS, "", 1
        ).replace(COMMENT_AFTER, COMMENT_BEFORE, 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1
        )
        return predecessor, live, True
    raise ValueError("Actor-state reset source state changed")


def checked_candidate(root, obj):
    raw, bindings = BASE_FUNCTION_BLOB(obj)
    if len(raw) != NATURAL_SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Actor-state reset natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Actor-state reset natural frame changed")
    if bindings != BINDINGS:
        raise ValueError("Actor-state reset bindings changed")
    padded = raw + b"\0\0\0\0"
    expected = harness.retail_object_bytes(root)
    differences = [
        offset for offset in range(0, SIZE, 4)
        if padded[offset:offset + 4] != expected[offset:offset + 4]
    ]
    wanted = [int(row["offset"], 0) for row in PATCH_ROWS]
    if differences != wanted:
        raise ValueError("Actor-state reset natural difference set changed")
    return raw, bindings


def slot_function_blob(obj):
    """Include the generated-slice alignment word in assembled owner slots."""
    raw, bindings = BASE_FUNCTION_BLOB(obj)
    path = Path(obj)
    if path.parent.name.endswith("-owner") and len(raw) == NATURAL_SIZE:
        text, functions, _ = harness.parse_object(path)
        end = functions[FUNCTION]["value"] + NATURAL_SIZE
        if text[end:end + 4] != b"\0\0\0\0":
            raise ValueError("Actor-state reset trailing alignment word changed")
        raw += b"\0\0\0\0"
    return raw, bindings


def caller_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(
        ">%dI" % (len(image) // 4), image[:len(image) & ~3]
    )
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls != [0x14E548] or pointers:
        raise ValueError("Actor-state reset caller evidence changed")

    assembly = (root / ASM).read_text()
    caller = assembly.split("glabel func_15120158\n", 1)[1].split(
        "endlabel func_15120158", 1
    )[0]
    required = (
        "14E524 15121074 02002025 */  or         $a0, $s0, $zero",
        "14E548 15121098 0D448631 */  jal        func_151218C4",
        "14E54C 1512109C AFA80054 */   sw        $t0, 0x54($sp)",
        "14E550 151210A0 8FA80054 */  lw         $t0, 0x54($sp)",
    )
    if any(caller.count(text) != 1 for text in required):
        raise ValueError("Actor-state reset caller ABI changed")
    return {
        "direct_jal_calls": ["0x14e548"],
        "aligned_pointer_literals": [],
        "caller": "func_15120158 at 0x15121098",
        "abi": "one struct108-compatible actor pointer; no return value consumed",
    }


def prepare(root, output=None):
    replacements = {
        "FUNCTION": FUNCTION,
        "FILENAME": FILENAME,
        "SOURCE": SOURCE,
        "OBJECT": OBJECT,
        "ASM": ASM,
        "GUARDS": GUARDS,
        "ELF": ELF,
        "LINKER": LINKER,
        "ROM_IMAGE": ROM_IMAGE,
        "REGISTRY": REGISTRY,
        "BUILD": BUILD,
        "ENTRY": ENTRY,
        "ROM": ROM,
        "WORDS": WORDS,
        "SIZE": SIZE,
        "NATURAL_FRAME": NATURAL_FRAME,
        "RETAIL_FRAME": RETAIL_FRAME,
        "RAW_SHA256": RAW_SHA256,
        "RETAIL_SHA256": RETAIL_SHA256,
        "BINDINGS": BINDINGS,
        "RETAIL_BINDINGS": RETAIL_BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "source_states": source_states,
        "checked_candidate": checked_candidate,
        "function_blob": slot_function_blob,
        "registry_evidence": caller_evidence,
    }
    saved = {name: getattr(harness, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(harness, name, value)
        result = harness.prepare(root, output or Path(root) / BUILD)
    finally:
        for name, value in saved.items():
            setattr(harness, name, value)
    report = result["report"]
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != 4 or
            report["natural_positional_differences"] != 4 or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("Actor-state reset qualification report changed")
    report["natural_body_words"] = NATURAL_SIZE // 4
    report["retail_slot_words"] = WORDS
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
