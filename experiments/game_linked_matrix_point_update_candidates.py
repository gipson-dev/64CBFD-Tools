"""Screen complete semantic C for the matrix-backed linked actor point callback."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_15107E48", "generated_133190"
SOURCE = "conker/src/game/generated_133190.c"
BUILD = "conker/build/game-linked-matrix-point-update-candidates"
ENTRY, ROM, WORDS = 0x15107E48, 0x1352F8, 67
PLACEHOLDER = "s32 func_15107E48() {\n    return 0;\n}"
DECLARATIONS = "void func_15107F54(u8 *, u8, u8 *, u8 *);\n\n"
SELECTED = """/* Transform a valid linked actor point and refresh its fractional points if moved. */
s32 func_15107E48(u8 *owner, u8 *changed) {
    u8 *link = *(u8 **)(owner + 0x60);
    u8 *actor = *(u8 **)link;
    struct17 original;
    f32 *savedPoint;
    f32 *point;

    if (*(s32 *)actor == 0 || link[4] != actor[0x3B]) {
        return 0;
    }
    if ((point = (f32 *)(owner + 0x14), *(s32 *)(actor + 0x1D4) == 0)) {
        return 0;
    }
    *changed = 0;
    original = *(struct17 *)point;
    savedPoint = point;
    func_15107F54(actor, link[0x14], link + 8, (u8 *)point);
    if (original.unk0 != *(f32 *)(owner + 0x14) ||
            original.unk4 != *(f32 *)(owner + 0x18) ||
            original.unk8 != *(f32 *)(owner + 0x1C)) {
        *changed = 1;
        func_15107AE0(savedPoint, (f32 *)(owner + 0x38),
                      (f32 *)(owner + 0x20), (f32 *)(owner + 0x2C));
    }
    return 1;
}"""


def source_states(live):
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live or DECLARATIONS in live:
            raise ValueError("Linked matrix point predecessor changed")
        return live, live.replace(PLACEHOLDER, DECLARATIONS + SELECTED, 1), False
    if live.count(DECLARATIONS + SELECTED) == 1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS + SELECTED, PLACEHOLDER, 1), live, True
    raise ValueError("Linked matrix point source state changed")


def source_with(body):
    _, qualified, _ = source_states((ROOT / SOURCE).read_text())
    return qualified.replace(SELECTED, body, 1)


def compare(label="selected", body=SELECTED):
    out = ROOT / BUILD
    out.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, out, source_with(body), label)
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    raw = text[start:start + size]
    linked, _ = link_owner(ROOT, out, obj, OWNER)
    ours = linked[start:start + size]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    words = struct.unpack(">%dI" % (size // 4), ours)
    truth = struct.unpack(">%dI" % WORDS, retail)
    differences = [{"offset": i * 4, "ours": a, "retail": b}
                   for i, (a, b) in enumerate(itertools.zip_longest(words, truth, fillvalue=0)) if a != b]
    return {"label":label,"words":len(words),"frame":(-words[0]) & 0xFFFF,
            "raw_sha256":hashlib.sha256(raw).hexdigest(),
            "linked_sha256":hashlib.sha256(ours).hexdigest(),
            "retail_sha256":hashlib.sha256(retail).hexdigest(),
            "differences":differences,"diagnostics":diagnostics,
            "bindings":{at-start:rows for at,rows in relocations.items() if start<=at<start+size}}


if __name__ == "__main__":
    variants = {
        "selected": SELECTED,
        "point-after-gate": SELECTED.replace(
            "if ((point = (f32 *)(owner + 0x14), *(s32 *)(actor + 0x1D4) == 0))",
            "if (*(s32 *)(actor + 0x1D4) == 0)").replace(
                "    *changed = 0;", "    point = (f32 *)(owner + 0x14);\n    *changed = 0;", 1),
        "no-saved-alias": SELECTED.replace("    f32 *savedPoint;\n", "").replace(
            "    savedPoint = point;\n", "").replace("func_15107AE0(savedPoint,", "func_15107AE0(point,"),
    }
    for label, body in variants.items():
        print(json.dumps(compare(label, body), indent=2), flush=True)
