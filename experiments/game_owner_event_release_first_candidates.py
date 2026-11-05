"""Screen the owner-event callback whose release arms precede timer updates."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_15191A84", "generated_1BA1D0"
SOURCE = "conker/src/game/generated_1BA1D0.c"
BUILD = "conker/build/game-owner-event-release-first-candidates"
ENTRY, ROM, WORDS = 0x15191A84, 0x1BEF34, 66
PLACEHOLDER = "s32 func_15191A84() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    u8 retained00[0x0D];
    u8 flags;
    s16 timer;
    u8 retained10[0x18];
    u8 *owner;
    u8 ownerId;
} OwnerEventRecord15191A84;

"""
SELECTED = """/* Release matching owner events before applying timer or forwarding commands.
 * Keep the event pointer and command byte in their retail argument homes. */
void func_15191A84(OwnerEventRecord15191A84 *record,
                   OwnerEvent15191980 *volatile event, s32 rawCommand) {
    if (((u8 *)&rawCommand)[3] == 0x0C ||
        ((u8 *)&rawCommand)[3] == 0x0E ||
        ((u8 *)&rawCommand)[3] == 0x50) {
        if (record->owner != event->owner && record->ownerId != event->ownerId) {
            return;
        }
        func_1516972C(record);
        return;
    }
    if (((u8 *)&rawCommand)[3] == 0x4E) {
        func_1516972C(record);
        return;
    }
    if (((u8 *)&rawCommand)[3] == 0x0D) {
        if (record->owner != event->owner && record->ownerId != event->ownerId) {
            return;
        }
        {
            u8 flags = record->flags;

            record->timer = 100;
            record->flags = flags | 1;
        }
        return;
    }
    func_15169850((s32)event, ((volatile u8 *)&rawCommand)[3],
                  (s32)&record->owner, (s32)&record->ownerId, (s32)record);
}"""


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(PLACEHOLDER) == 1 and SELECTED not in live and DECLARATIONS not in live:
        return live, live.replace(marker, marker + "\n" + DECLARATIONS, 1).replace(PLACEHOLDER, SELECTED, 1), False
    if live.count(SELECTED) == 1 and live.count(DECLARATIONS) == 1 and PLACEHOLDER not in live:
        return live.replace("\n" + DECLARATIONS, "", 1).replace(SELECTED, PLACEHOLDER, 1), live, True
    raise ValueError("Release-first owner event source changed")


def source_with(body=SELECTED, declarations=DECLARATIONS):
    return source_states((ROOT / SOURCE).read_text())[1].replace(SELECTED, body, 1).replace(DECLARATIONS, declarations, 1)


def compare(label="selected", body=SELECTED, declarations=DECLARATIONS):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body, declarations), label)
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
