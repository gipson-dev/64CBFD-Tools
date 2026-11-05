"""Screen the effect lifetime ramps, live size growth and one-shot value switch."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_151A25E0", "generated_1CC440"
SOURCE = "conker/src/game/generated_1CC440.c"
BUILD = "conker/build/game-effect-lifetime-growth-candidates"
ENTRY, ROM, WORDS = 0x151A25E0, 0x1CFA90, 67
PLACEHOLDER = "s32 func_151A25E0() {\n    return 0;\n}"
DECLARATIONS = "extern s32 D_800BE9E4;\n\n"
SELECTED = """/* Apply lifetime ramps in order, with live size growth and a one-shot switch. */
void func_151A25E0(u8 *effect) {
    s16 *parameters = (s16 *)(effect + 0x50);
    s32 time = *(s16 *)(effect + 0x38);

    if (parameters[2] < time) {
        effect[0x3F] = parameters[0] * (parameters[1] - time);
    }
    if (parameters[5] < time) {
        *(s16 *)(effect + 0x34) = *(s16 *)(effect + 0x36) = parameters[3] * (parameters[4] - time);
    }
    if (time < parameters[8]) {
        effect[0x3F] = parameters[9] * time;
    }
    if (time < parameters[10]) {
        u32 increment = parameters[11] * (u32)D_800BE9E4;

        *(s16 *)(effect + 0x34) += increment;
        *(s16 *)(effect + 0x36) += increment;
        time = *(s16 *)(effect + 0x38);
    }
    if (time < parameters[12]) {
        *(s16 *)(effect + 0x32) = parameters[13];
        parameters[12] = -9999;
        time = *(s16 *)(effect + 0x38);
    }
    effect[0x40] = effect[0x41] = effect[0x42] = parameters[7] * time;
}"""


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(PLACEHOLDER) == 1 and SELECTED not in live and DECLARATIONS not in live:
        return live, live.replace(marker, marker + "\n" + DECLARATIONS, 1).replace(PLACEHOLDER, SELECTED, 1), False
    if live.count(SELECTED) == 1 and PLACEHOLDER not in live and live.count(DECLARATIONS) == 1:
        return live.replace("\n" + DECLARATIONS, "", 1).replace(SELECTED, PLACEHOLDER, 1), live, True
    raise ValueError("Effect lifetime growth source changed")


def source_with(body=SELECTED):
    return source_states((ROOT / SOURCE).read_text())[1].replace(SELECTED, body, 1)


def compare(label="selected", body=SELECTED):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), label)
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    raw = text[start:start + size]
    linked, _ = link_owner(ROOT, output, obj, OWNER)
    ours = linked[start:start + size]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    differences = [{"offset": i * 4, "ours": a, "retail": b}
                   for i, (a, b) in enumerate(itertools.zip_longest(
                       struct.unpack(">%dI" % (size // 4), ours),
                       struct.unpack(">%dI" % WORDS, retail), fillvalue=0)) if a != b]
    return {"label": label, "words": size // 4, "differences": differences,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(), "diagnostics": diagnostics,
            "bindings": {at - start: rows for at, rows in relocations.items() if start <= at < start + size}}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
