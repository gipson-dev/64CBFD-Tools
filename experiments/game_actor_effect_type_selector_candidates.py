"""Screen the actor effect-type selector against its two fixed retail tables."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x15134070, 0x161520, 63
FUNCTION = "func_15134070"
TABLE = 0x800A4350
ANCHOR = "jtbl_800A4350_game"
SOURCE = "conker/src/game_161520.c"
OBJECT = "conker/build/src/game_161520.c.o"
BUILD = "conker/build/game-actor-effect-type-selector"
PROTOTYPE = "s32 func_15134070(u8 *actor);"
PROFILES = {
    "o2g3": ("-O2", "-g3"),
    "o2": ("-O2",),
    "o1g3": ("-O1", "-g3"),
    "o1": ("-O1",),
}
GROUPS = {
    14: (0x87, 0xB0),
    15: (0xB1,),
    16: (0xB4,),
    17: (0x70, 0xB2),
    18: (0xAB,),
    13: (0x10, 0x38, 0x91),
    12: (0x98,),
    11: (0x34,),
    10: (0x47,),
    1: (0x11, 0x14, 0x3B),
    2: (0x5A, 0x5F, 0x74, 0x75, 0x7A),
    3: (0x58, 0x5B, 0x80),
    4: (0x16, 0x88, 0x90),
    5: (0x9C,),
    6: (0x9D,),
    7: (0x96,),
    8: (0xA0,),
    9: (0x9F,),
    19: (0x9A,),
    0: (0, 1, 2, 3, 4),
}
SELECTED = """/* Map an actor identity to its point/effect descriptor type. */
s32 func_15134070(u8 *actor) {
    s32 identity = actor[4];

    switch (identity) {
        case 0x87:
        case 0xB0:
            return 14;
        case 0xB1:
            return 15;
        case 0xB4:
            return 16;
        case 0x70:
        case 0xB2:
            return 17;
        case 0xAB:
            return 18;
        case 0x10:
        case 0x38:
        case 0x91:
            return 13;
        case 0x98:
            return 12;
        case 0x34:
            return 11;
        case 0x47:
            return 10;
        case 0x11:
        case 0x14:
        case 0x3B:
            return 1;
        case 0x5A:
        case 0x5F:
        case 0x74:
        case 0x75:
        case 0x7A:
            return 2;
        case 0x58:
        case 0x5B:
        case 0x80:
            return 3;
        case 0x16:
        case 0x88:
        case 0x90:
            return 4;
        case 0x9C:
            return 5;
        case 0x9D:
            return 6;
        case 0x96:
            return 7;
        case 0xA0:
            return 8;
        case 0x9F:
            return 9;
        case 0x9A:
            return 19;
        case 0:
        case 1:
        case 2:
        case 3:
        case 4:
            return 0;
    }
    return 99;
}"""


def candidate_owner(root):
    before = (root / SOURCE).read_text()
    placeholder = (
        "/* Non-matching C placeholders for "
        "asm/nonmatchings/game_161520/func_15134070.s. */\n"
        "s32 func_15134070() {\n"
        "    return 0;\n"
        "}")
    if SELECTED not in before:
        if before.count(placeholder) != 1:
            raise ValueError("Actor effect-type selector definition changed")
        before = before.replace(placeholder, SELECTED)
    declaration = "s32 func_15134070();"
    if PROTOTYPE not in before:
        if before.count(declaration) != 1:
            raise ValueError("Actor effect-type selector declaration changed")
        before = before.replace(declaration, PROTOTYPE)
    return before


def compile_candidate_owner(root, output):
    return compile_owner(
        root, output, candidate_owner(root), "actor-effect-selector-owner")


def candidates():
    for kind, default in itertools.product(("inline", "s32", "u32", "u8"),
                                           (False, True)):
        body = SELECTED
        if kind == "inline":
            body = body.replace("    s32 identity = actor[4];\n\n", "")
            body = body.replace("switch (identity)", "switch (actor[4])")
        else:
            body = body.replace("s32 identity =", kind + " identity =")
        if default:
            body = body.replace(
                "    }\n    return 99;",
                "        default:\n            return 99;\n    }")
        yield "%s-%d" % (kind, default), body


def compile_candidate(root, output, name, body=SELECTED, profile="o2g3"):
    source, obj, elf = (output / (name + suffix)
                        for suffix in (".c", ".o", ".elf"))
    source.write_text(
        '#include <ultra64.h>\n#include "functions.h"\n'
        '#include "variables.h"\n' + body + "\n")
    result = subprocess.run([
        "ido/ido5.3_recomp/cc", "-c", "-32", "-G", "0", "-Xfullwarn",
        "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
        "-Wab,-r4300_mul", "-mips2", "-o32", "-I", "conker/include", "-I",
        "conker/include/2.0L", "-I", "conker/include/2.0L/PR",
        "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
        "-D_MIPS_SZLONG=32", *PROFILES[profile], "-o",
        str(obj.relative_to(root)), str(source.relative_to(root)),
    ], cwd=root, capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    if result.returncode or diagnostics:
        raise ValueError(diagnostics)
    script = output / (name + ".ld")
    script.write_text(
        "SECTIONS { .text 0x15134070 : SUBALIGN(4) { *(.text) } "
        ".rodata 0x800A4350 : SUBALIGN(4) { *(.rodata) } }\n")
    subprocess.run([
        "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script),
        "-e", FUNCTION, "-o", str(elf), str(obj),
    ], check=True, capture_output=True)
    _, symbols, relocations = parse_object(obj)
    pools = sections(elf)
    text = pools[".text"][1]
    start, size = symbols[FUNCTION]["value"], symbols[FUNCTION]["size"]
    words = list(struct.unpack_from(">%dI" % (size // 4), text, start))
    end = max(index for index, word in enumerate(words)
              if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError("Nonzero selector tail")
    words = words[:end]
    table_bytes = pools.get(".rodata", (TABLE, b""))[1]
    retail = list(struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM))
    game_address, game_data = sections(
        root / "conker/build/conker.us.elf")[".game_data"]
    retail_tables = game_data[TABLE - game_address:TABLE - game_address + 0x260]
    record = {
        "name": name,
        "profile": profile,
        "body_words": end,
        "object_words": size // 4,
        "differences": sum(
            left != right for left, right in itertools.zip_longest(
                words, retail, fillvalue=0)),
        "diagnostics": diagnostics,
        "rodata_bytes": len(table_bytes),
        "table_differences": sum(
            left != right for left, right in itertools.zip_longest(
                table_bytes[:0x260], retail_tables, fillvalue=0)),
        "relocations": relocations,
    }
    return record, words, table_bytes


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(exist_ok=True)
    records = []
    for name, body in candidates():
        for profile in PROFILES:
            record, _, _ = compile_candidate(
                root, output, name + "-" + profile, body, profile)
            records.append(record)
            print(record["name"], record["body_words"],
                  record["differences"], record["rodata_bytes"],
                  record["table_differences"], flush=True)
    (output / "measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
