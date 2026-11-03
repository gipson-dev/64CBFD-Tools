"""Screen complete semantic source shapes for ``func_1504A620``."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.match_progress import load_elf_functions


ENTRY = 0x1504A620
ROM = 0x77AD0
WORDS = 68
FUNCTION = "func_1504A620"
SOURCE = "conker/src/game_77AD0.c"
OWNER = "game_77AD0"
PROFILES = {
    "o2g3": ("-O2", "-g3"),
    "o2": ("-O2",),
    "o1g3": ("-O1", "-g3"),
    "o1": ("-O1",),
}
SYMBOLS = {"D_800990B0": 0x800990B0, "D_800990B4": 0x800990B4}


def body(declaration_order, *, square_local, assignment, multiply_assignment, ln2_local):
    declarations = {
        "ratio": "    f32 ratio;",
        "previous": "    f32 previous;",
        "accumulator": "    f32 accumulator;",
        "term": "    f32 term;",
        "divisor": "    s32 divisor;",
        "ln2": "    f32 ln2;",
        "square": "    f32 ratioSquared;",
    }
    keys = list(declaration_order)
    if ln2_local:
        keys.append("ln2")
    if square_local:
        keys.append("square")
    lines = ["f32 func_1504A620(f32 arg0) {"] + [declarations[key] for key in keys]
    lines += [
        "",
        "    if (arg0 < 0.0f) {",
        "        return 0.0f;",
        "    }",
        "    if (arg0 == 0.0f) {",
        "        return 0.0f;",
        "    }",
        "",
        "    accumulator = 0.0f;",
        "    while (arg0 >= 2.0f) {",
        "        arg0 *= 0.5f;",
        "        accumulator += D_800990B0;",
        "    }",
        "",
    ]
    if ln2_local:
        lines.append("    ln2 = D_800990B4;")
    lines += [
        "    while (arg0 < 1.0f) {",
        "        arg0 *= 2.0f;",
        "        accumulator -= %s;" % ("ln2" if ln2_local else "D_800990B4"),
        "    }",
        "",
        "    ratio = (arg0 - 1.0f) / (arg0 + 1.0f);",
    ]
    if square_local:
        lines.append("    ratioSquared = ratio * ratio;")
    lines += [
        "    term = 2.0f * ratio;",
        "    divisor = 1;",
        "",
        "    do {",
        "        previous = accumulator;",
        "        accumulator %s term / (f32) divisor;" % ("+=" if assignment else "= accumulator +"),
        "        term %s %s;" % ("*=" if multiply_assignment else "= term *", "ratioSquared" if square_local else "ratio * ratio"),
        "        divisor += 2;",
        "    } while (accumulator != previous);",
        "",
        "    return accumulator;",
        "}",
    ]
    return "\n".join(lines)


ORDERS = {
    "draft": ("ratio", "previous", "accumulator", "term", "divisor"),
    "acc-first": ("accumulator", "ratio", "term", "previous", "divisor"),
    "term-first": ("term", "ratio", "accumulator", "previous", "divisor"),
    "previous-first": ("previous", "accumulator", "ratio", "term", "divisor"),
}


def candidates():
    for order_name, order in ORDERS.items():
        for square_local, assignment, multiply_assignment, ln2_local in itertools.product((False, True), repeat=4):
            name = "%s-sq%d-add%d-mul%d-ln%d" % (
                order_name, square_local, assignment, multiply_assignment, ln2_local
            )
            yield name, body(order, square_local=square_local, assignment=assignment,
                             multiply_assignment=multiply_assignment, ln2_local=ln2_local)


SELECTED = body(ORDERS["draft"], square_local=False, assignment=True,
                multiply_assignment=False, ln2_local=True)


def compile_candidate(root, output, name, selected=SELECTED, profile="o2g3"):
    source, obj, elf = (output / (name + suffix) for suffix in (".c", ".o", ".elf"))
    source.write_text(
        "#include <ultra64.h>\nextern f32 D_800990B0;\nextern f32 D_800990B4;\n" + selected + "\n"
    )
    result = subprocess.run([
        "ido/ido5.3_recomp/cc", "-c", "-32", "-G", "0", "-Xfullwarn", "-Xcpluscomm",
        "-signed", "-nostdinc", "-non_shared", "-Wab,-r4300_mul", "-mips2", "-o32",
        "-I", "conker/include", "-I", "conker/include/2.0L", "-I", "conker/include/2.0L/PR",
        "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2", "-D_MIPS_SZLONG=32",
        *PROFILES[profile], "-o", str(obj.relative_to(root)), str(source.relative_to(root)),
    ], cwd=root, capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    if result.returncode:
        raise ValueError(diagnostics)
    script = output / "logarithm.ld"
    script.write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % ENTRY)
    subprocess.run([
        "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script), "-e", FUNCTION,
        *["--defsym=%s=0x%X" % item for item in SYMBOLS.items()],
        "-o", str(elf), str(obj),
    ], check=True, capture_output=True)
    words = load_elf_functions(str(elf), "mips-linux-gnu-objdump")[0][FUNCTION]
    end = max(index for index, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise AssertionError("nonzero words follow the final return")
    words = words[:end]
    retail = list(struct.unpack_from(">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM))
    slot = words + [0] * max(0, WORDS - end)
    differences = [(index * 4, "0x%08X" % actual, "0x%08X" % expected)
                   for index, (actual, expected) in enumerate(zip(slot, retail)) if actual != expected]
    frames = [(-word) & 0xFFFF for word in words
              if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000]
    return {
        "name": name,
        "profile": profile,
        "body_words": end,
        "frame": frames[0] if frames else 0,
        "differences": len(differences) + max(0, end - WORDS),
        "different_words": differences,
        "exact": slot == retail,
        "diagnostics": diagnostics,
    }, words


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-logarithm-approximation"
    output.mkdir(exist_ok=True)
    records = []
    for name, candidate in candidates():
        for profile in PROFILES:
            record, _ = compile_candidate(root, output, name + "-" + profile, candidate, profile)
            records.append(record)
            print(record["name"], record["body_words"], record["frame"], record["differences"], flush=True)
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
