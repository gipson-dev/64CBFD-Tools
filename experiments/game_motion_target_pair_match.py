"""Qualify the split motion callback and ten-target initializer as exact C."""

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess

from tools import progress as progress_tool
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_four_head_lookup_match import diagnostics
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import (
    ELF_HEADER,
    SECTION_HEADER,
    emit_padded_assembly,
    parse_object,
    read_c_string,
)
from tools.tests.game_owner_pool import normalized_pools


OWNER = "generated_F5800"
WRAPPER = "func_150C84F4"
INITIALIZER = "func_150C851C"
FUNCTIONS = (WRAPPER, INITIALIZER)
SOURCE = "conker/src/game/generated_F5800.c"
OBJECT = "conker/build/src/game/generated_F5800.c.o"
ASM = "conker/asm/F5800.s"
LAYOUT = "conker/retail_layout.us.txt"
SYMBOLS = "conker/symbol_addrs.us.txt"
UNDEFINED = "conker/undefined_funcs_auto.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-motion-target-pair-150C84F4-match"

WRAPPER_ENTRY = 0x150C84F4
INITIALIZER_ENTRY = 0x150C851C
WRAPPER_ROM = 0xF59A4
INITIALIZER_ROM = 0xF59CC
WRAPPER_SIZE = 40
INITIALIZER_SIZE = 228
PAIR_SIZE = WRAPPER_SIZE + INITIALIZER_SIZE

RAW_SHA256 = {
    WRAPPER: "fbd4957fdbbfd0aa1d1151d80ac4c9b855e9a50512e43a44e2dba6fed332829c",
    INITIALIZER: "ae64e70d706ac3da5e326de8f9805f0f09c51ff4a2972f9a48d6a889985a6e72",
}
RETAIL_SHA256 = {
    WRAPPER: "dfc02278a0a839890e3995367c6854a32a7b781e046ff29e70eff0d6e8f8661b",
    INITIALIZER: "a7824c362f513604e2da19bc96450f4981454abdf28af3debf90e5971f2d8e7d",
}
BINDINGS = {
    WRAPPER: {
        0x010: [("R_MIPS_26", "func_150C8350")],
    },
    INITIALIZER: {
        0x008: [("R_MIPS_HI16", "D_800BE4E0")],
        0x014: [("R_MIPS_LO16", "D_800BE4E0")],
        0x038: [("R_MIPS_26", "func_150CDB6C")],
        0x088: [("R_MIPS_26", "func_150ADA20")],
    },
}

DECLARATIONS = """extern s32 D_800BE4E0;
s32 func_150ADA20(void);
void func_150CDB6C(s32 value);
"""

WRAPPER_SELECTED = """/* Advance the motion table once for the primary frame layer. */
void func_150C84F4(s32 view) {
    if (view == 0) {
        func_150C8350();
    }
}"""

INITIALIZER_SELECTED = """/* Randomize ten motion targets from the selected intensity. */
void func_150C851C(s32 intensity) {
    s32 offset;
    s32 base;
    u32 span;
    s32 target;

    if (D_800BE4E0 != 0) {
        func_150CDB6C(intensity);
        base = (intensity * 300) >> 8;
        span = ((intensity * 50) >> 8) + 50;
        for (offset = 0; offset != 100; offset += 10) {
            target = base;
            target += (u32)func_150ADA20() % span;
            *(s16 *)(D_800BE4E0 + offset + 8) = target;
        }
    }
}"""

PATCH_ROWS = (
    dict(offset="0x070", expected="0x0013C203", replacement="0x00137A03",
         note="Normalize the independent span fixed-point shift register"),
    dict(offset="0x074", expected="0x00127A03", replacement="0x0012C203",
         note="Normalize the independent base fixed-point shift register"),
    dict(offset="0x078", expected="0x01E09025", replacement="0x03009025",
         note="Carry the base through retail's t8 fixed-point lifetime"),
    dict(offset="0x07C", expected="0x27130032", replacement="0x25F30032",
         note="Carry the span through retail's t7 fixed-point lifetime"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return {
        "filename": OWNER,
        "function": INITIALIZER,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    placeholder = lambda name: "s32 %s() {\n    return 0;\n}" % name
    installed = all(body in live for body in (WRAPPER_SELECTED, INITIALIZER_SELECTED))
    predecessor = live
    if installed:
        if live.count(DECLARATIONS) != 1:
            raise ValueError("Installed motion-target declarations changed")
        predecessor = predecessor.replace(DECLARATIONS, "", 1)
        for name, body in ((WRAPPER, WRAPPER_SELECTED),
                           (INITIALIZER, INITIALIZER_SELECTED)):
            if predecessor.count(body) != 1:
                raise ValueError("Installed motion-target body changed: " + name)
            predecessor = predecessor.replace(body, placeholder(name), 1)
        return predecessor, live, True

    if any(body in live for body in (WRAPPER_SELECTED, INITIALIZER_SELECTED)):
        raise ValueError("Partially installed motion-target source")
    qualified = live
    anchor = "extern f32 D_800BE9A4;\n"
    if qualified.count(anchor) != 1 or DECLARATIONS in qualified:
        raise ValueError("Motion-target declaration predecessor changed")
    qualified = qualified.replace(anchor, anchor + DECLARATIONS, 1)
    for name, body in ((WRAPPER, WRAPPER_SELECTED),
                       (INITIALIZER, INITIALIZER_SELECTED)):
        lo, hi = function_span(qualified, name)
        if qualified[lo:hi] != placeholder(name):
            raise ValueError("Motion-target placeholder changed: " + name)
        qualified = qualified[:lo] + body + qualified[hi:]
    return live, qualified, False


def recovered_layout(before):
    old = b"game,generated_F5800,func_150C84F4,0x150C84F4,0x150C8600"
    if before.count(old) != 1:
        raise ValueError("Motion-target merged layout row changed")
    newline = b"\r\n" if old + b"\r\n" in before else b"\n"
    new = (
        b"game,generated_F5800,func_150C84F4,0x150C84F4,0x150C851C" +
        newline +
        b"game,generated_F5800,func_150C851C,0x150C851C,0x150C8600"
    )
    return before.replace(old, new, 1)


def predecessor_layout(after):
    new = b"game,generated_F5800,func_150C84F4,0x150C84F4,0x150C851C"
    newline = b"\r\n" if new + b"\r\n" in after else b"\n"
    block = new + newline + b"game,generated_F5800,func_150C851C,0x150C851C,0x150C8600"
    if after.count(block) != 1:
        raise ValueError("Installed motion-target layout rows changed")
    return after.replace(
        block,
        b"game,generated_F5800,func_150C84F4,0x150C84F4,0x150C8600",
        1,
    )


SYMBOL_ROW = b"func_150C851C = 0x150C851C; // type:func defined:true"
UNDEFINED_ROW = b"func_150C851C = 0x150C851C;"


def recovered_symbols(before):
    if b"func_150C851C" in before:
        raise ValueError("Motion-target symbol annotation already exists")
    newline = b"\r\n" if before.endswith(b"\r\n") else b"\n"
    if not before.endswith(newline):
        raise ValueError("Motion-target symbol manifest termination changed")
    return before + SYMBOL_ROW + newline


def predecessor_symbols(after):
    newline = b"\r\n" if SYMBOL_ROW + b"\r\n" in after else b"\n"
    row = SYMBOL_ROW + newline
    if after.count(row) != 1:
        raise ValueError("Installed motion-target symbol annotation changed")
    return after.replace(row, b"", 1)


def recovered_undefined(before):
    newline = b"\r\n" if UNDEFINED_ROW + b"\r\n" in before else b"\n"
    row = UNDEFINED_ROW + newline
    if before.count(row) != 1:
        raise ValueError("Motion-target generated fallback changed")
    return before.replace(row, b"", 1)


def predecessor_undefined(after):
    if UNDEFINED_ROW in after:
        raise ValueError("Motion-target generated fallback still present")
    newline = b"\r\n" if after.endswith(b"\r\n") else b"\n"
    lines = after.splitlines(keepends=True)
    address = INITIALIZER_ENTRY
    index = next((i for i, line in enumerate(lines)
                  if re.search(rb"0x([0-9A-Fa-f]+)", line) and
                  int(re.search(rb"0x([0-9A-Fa-f]+)", line).group(1), 16) > address),
                 len(lines))
    lines.insert(index, UNDEFINED_ROW + newline)
    return b"".join(lines)


def inventory_states(root, installed):
    live_layout = (root / LAYOUT).read_bytes()
    live_symbols = (root / SYMBOLS).read_bytes()
    live_undefined = (root / UNDEFINED).read_bytes()
    if installed:
        predecessor = {
            LAYOUT: predecessor_layout(live_layout),
            SYMBOLS: predecessor_symbols(live_symbols),
            UNDEFINED: predecessor_undefined(live_undefined),
        }
        qualified = {
            LAYOUT: live_layout,
            SYMBOLS: live_symbols,
            UNDEFINED: live_undefined,
        }
    else:
        predecessor = {LAYOUT: live_layout, SYMBOLS: live_symbols,
                       UNDEFINED: live_undefined}
        qualified = {
            LAYOUT: recovered_layout(live_layout),
            SYMBOLS: recovered_symbols(live_symbols),
            UNDEFINED: recovered_undefined(live_undefined),
        }
    return predecessor, qualified


def write_patches(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def retail_bytes(root, name):
    rom, size = ((WRAPPER_ROM, WRAPPER_SIZE) if name == WRAPPER else
                 (INITIALIZER_ROM, INITIALIZER_SIZE))
    data = (root / ROM_IMAGE).read_bytes()[rom:rom + size]
    if len(data) != size or digest(data) != RETAIL_SHA256[name]:
        raise ValueError("Motion-target retail bytes changed: " + name)
    return data


def retail_object_bytes(root, name):
    result = bytearray(retail_bytes(root, name))
    for offset, rows in BINDINGS[name].items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", result, offset,
                         struct.unpack_from(">I", result, offset)[0] & mask)
    return bytes(result)


def checked_candidate(root, obj, name):
    raw, bindings = function_blob(obj, name)
    if digest(raw) != RAW_SHA256[name] or bindings != BINDINGS[name]:
        raise ValueError("Motion-target natural candidate changed: " + name)
    expected = retail_object_bytes(root, name)
    differences = [offset for offset in range(0, len(raw), 4)
                   if raw[offset:offset + 4] != expected[offset:offset + 4]]
    wanted = [] if name == WRAPPER else [int(row["offset"], 0)
                                         for row in PATCH_ROWS]
    if len(raw) != len(expected) or differences != wanted:
        raise ValueError("Motion-target difference set changed: " + name)
    return raw, bindings


def assemble_original(root, output):
    source = (root / ASM).read_text()
    objects = {}
    for name in FUNCTIONS:
        start = "glabel " + name + "\n"
        end = "endlabel " + name
        if source.count(start) != 1 or source.count(end) != 1:
            raise ValueError("Unknown original motion-target boundary: " + name)
        block = start + source.split(start, 1)[1].split(end, 1)[0] + end + "\n"
        assembly = output / ("original-" + name + ".s")
        assembly.write_text(
            '.include "' + str(root / "conker/include/asm_processor_prelude.inc") +
            '"\n' + block + "\n.type " + name + ", @function\n.size " +
            name + ", .-" + name + "\n")
        obj = assembly.with_suffix(".o")
        subprocess.run([
            "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
            "-mabi=32", "-o", str(obj), str(assembly),
        ], check=True, capture_output=True)
        objects[name] = obj
    return objects


def assemble_owner(root, output, compact, rows, fields, label,
                   function_objects=None):
    directory = output / label
    directory.mkdir(parents=True, exist_ok=True)
    patches = directory / "retail-word-patches.csv"
    write_patches(patches, fields, rows)
    assembly = directory / (OWNER + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact,
        root / ASM,
        function_objects=function_objects,
        word_patches_path=patches,
        filename=OWNER,
    ))
    obj = directory / (OWNER + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly),
    ], check=True, capture_output=True)
    return obj


def link_image(root, output, owner, label, undefined_bytes):
    old = OBJECT.removeprefix("conker/")
    new = owner.relative_to(root / "conker").as_posix()
    linker = (root / LINKER).read_text()
    if linker.count(old) != 1:
        raise ValueError("Motion-target linker owner reference changed")
    directory = output / label
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "conker.ld"
    script.write_text(linker.replace(old, new, 1))
    undefined = directory / "undefined_funcs_auto.txt"
    undefined.write_bytes(undefined_bytes)
    elf = directory / "conker.us.elf"
    mapfile = directory / "conker.us.map"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", script.relative_to(root / "conker").as_posix(),
        "-Map", mapfile.relative_to(root / "conker").as_posix(),
        "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
        "-T", "undefined_syms_auto.txt", "-T",
        undefined.relative_to(root / "conker").as_posix(),
        "--no-check-sections", "--no-warn-mismatch", "-o",
        elf.relative_to(root / "conker").as_posix(),
    ], cwd=root / "conker", check=True, capture_output=True)
    return elf, mapfile


def alloc_sections(path):
    data = Path(path).read_bytes()
    header = ELF_HEADER.unpack_from(data)
    sections = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11])
                for i in range(header[12])]
    names_header = sections[header[13]]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    result = {}
    for row in sections:
        name = read_c_string(names, row[0])
        if row[2] & 2:
            payload = b"" if row[1] == 8 else data[row[4]:row[4] + row[5]]
            result[name] = (row[1], row[3], row[5], payload)
    return result


def caller_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    def sites(entry, opcode):
        word = opcode | ((entry >> 2) & 0x03FFFFFF)
        return [index * 4 for index, value in enumerate(words) if value == word]
    wrapper_calls = sites(WRAPPER_ENTRY, 0x0C000000)
    wrapper_jumps = sites(WRAPPER_ENTRY, 0x08000000)
    wrapper_pointers = [index * 4 for index, value in enumerate(words)
                        if value == WRAPPER_ENTRY]
    initializer_calls = sites(INITIALIZER_ENTRY, 0x0C000000)
    initializer_jumps = sites(INITIALIZER_ENTRY, 0x08000000)
    initializer_pointers = [index * 4 for index, value in enumerate(words)
                            if value == INITIALIZER_ENTRY]
    if (wrapper_calls or wrapper_jumps or wrapper_pointers != [0x2317E8] or
            initializer_calls != [0xBC98, 0x3D3B8, 0x53094] or
            initializer_jumps or initializer_pointers):
        raise ValueError("Motion-target caller/registration evidence changed")
    return {
        WRAPPER: {
            "direct_jal_calls": [], "direct_jumps": [],
            "aligned_pointer_literals": ["0x2317e8"],
            "registration": "D_8008CD04[9]",
            "abi": "void callback with one signed 32-bit frame-layer index",
        },
        INITIALIZER: {
            "direct_jal_calls": [hex(value) for value in initializer_calls],
            "direct_jumps": [], "aligned_pointer_literals": [],
            "callers": ["func_1000BC28", "func_1500FE30",
                        "script command 0x55 handler"],
            "abi": "void function with one signed 32-bit intensity",
        },
    }


def project_progress(root, output, mapfile, owner, symbols):
    text = mapfile.read_text()
    shadow = owner.relative_to(root / "conker").as_posix()
    production = OBJECT.removeprefix("conker/")
    if text.count(shadow) < 1:
        raise ValueError("Motion-target qualified map owner path missing")
    text = text.replace(shadow, production)
    combined = []
    rows = []
    for section in ("init", "game", "debugger"):
        files, functions = progress_tool.parse_map(io.StringIO(text), "." + section)
        for filename, names in files.items():
            for name in progress_tool.parse_file(str(root / "conker"), filename,
                                                 names):
                functions[name]["language"] = "c"
        section_text = progress_tool.generate_csv(files, functions, "us", section)
        combined.append(section_text + "\n")
        rows.extend(csv.DictReader(io.StringIO(section_text)))
    progress = output / "projected-progress.csv"
    progress.write_text("".join(combined))
    symbol_path = output / "qualified-symbols.us.txt"
    symbol_path.write_bytes(symbols)
    pair = {row["function"]: row for row in rows
            if row["function"] in FUNCTIONS}
    converted = sum(row["language"] == "c" for row in rows)
    if (len(rows), converted) != (6046, 5512):
        raise ValueError("Motion-target projected inventory totals changed")
    if [(pair[name]["filename"], pair[name]["length"], pair[name]["language"])
            for name in FUNCTIONS] != [
                (OWNER, "40", "c"), (OWNER, "228", "c")]:
        raise ValueError("Motion-target projected split rows changed")
    result = subprocess.run([
        "python3", "tools/match_progress.py", str(progress.relative_to(root)),
        str((output / "qualified-image/conker.us.elf").relative_to(root)),
        ROM_IMAGE, "--version", "us", "--objdump", "mips-linux-gnu-objdump",
        "--symbol-addrs", str(symbol_path.relative_to(root)),
    ], cwd=root, check=True, capture_output=True, text=True)
    (output / "projected-match-progress.txt").write_text(result.stdout)
    expected = {
        "total": (4136, 5512, 0, 1376),
        "init": (492, 492, 0, 0),
        "game": (3463, 4839, 0, 1376),
        "debugger": (181, 181, 0, 0),
    }
    measured = {}
    for label, exact, total, percent, blocked, different in re.findall(
            r"\| (total|init|game|debugger) \| (\d+) / (\d+) \(([0-9.]+)%\) "
            r"\| (\d+) \| (\d+) \|", result.stdout):
        measured[label] = (int(exact), int(total), int(blocked), int(different),
                           percent)
    if {key: value[:4] for key, value in measured.items()} != expected:
        raise ValueError("Motion-target projected exact counts changed: " +
                         repr(measured))
    return {"functions": len(rows), "converted": converted,
            "pair": pair, "match_progress": measured}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_inventory, qualified_inventory = inventory_states(root, installed)

    with (root / GUARDS).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        live_rows = list(reader)
    expected_rows = [complete_row(row) for row in PATCH_ROWS]
    target_rows = [row for row in live_rows
                   if row["filename"] == OWNER and
                   row["function"] == INITIALIZER]
    if installed:
        if target_rows != expected_rows:
            raise ValueError("Installed motion-target guards changed")
        predecessor_rows = [row for row in live_rows if row not in target_rows]
        qualified_rows = live_rows
    else:
        if target_rows:
            raise ValueError("Unexpected predecessor motion-target guards")
        predecessor_rows = live_rows
        qualified_rows = live_rows + expected_rows

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before_diagnostics) != diagnostics(after_diagnostics):
        raise ValueError("Motion-target owner diagnostics changed")
    for name in FUNCTIONS:
        checked_candidate(root, qualified_compact, name)

    original = assemble_original(root, output)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_rows, fields,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_rows, fields,
        "qualified-owner")
    truth_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_rows, fields,
        "truth-owner", original)
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Motion-target selected owner differs from production")
    for name in FUNCTIONS:
        expected = (retail_object_bytes(root, name), BINDINGS[name])
        if function_blob(qualified_owner, name) != expected:
            raise ValueError("Qualified motion-target owner differs: " + name)
        if function_blob(original[name], name) != expected:
            raise ValueError("Original motion-target owner differs: " + name)
    if qualified_owner.read_bytes() != truth_owner.read_bytes():
        raise ValueError("Qualified motion-target owner differs from assembly truth")
    neighbors = same_functions(predecessor_owner, qualified_owner, FUNCTIONS)
    if neighbors != 17 or normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Motion-target owner neighbors or pools changed")

    baseline_elf, _ = link_image(
        root, output, predecessor_owner, "baseline-image",
        predecessor_inventory[UNDEFINED])
    boundary_elf, _ = link_image(
        root, output, predecessor_owner, "boundary-image",
        qualified_inventory[UNDEFINED])
    qualified_elf, qualified_map = link_image(
        root, output, qualified_owner, "qualified-image",
        qualified_inventory[UNDEFINED])
    truth_elf, _ = link_image(
        root, output, truth_owner, "truth-image",
        qualified_inventory[UNDEFINED])
    selected_elf = qualified_elf if installed else baseline_elf
    if selected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Motion-target selected full image differs from production")
    if alloc_sections(baseline_elf) != alloc_sections(boundary_elf):
        raise ValueError("Motion-target inventory-only link changed loaded sections")
    if qualified_elf.read_bytes() != truth_elf.read_bytes():
        raise ValueError("Motion-target qualified full image differs from assembly truth")

    baseline_functions, _, baseline_addresses = load_elf_functions(
        str(baseline_elf), "mips-linux-gnu-objdump")
    boundary_functions, _, boundary_addresses = load_elf_functions(
        str(boundary_elf), "mips-linux-gnu-objdump")
    qualified_functions, _, qualified_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    if set(boundary_functions) - set(baseline_functions) != {INITIALIZER}:
        raise ValueError("Motion-target boundary added unexpected functions")
    if set(baseline_functions) - set(boundary_functions):
        raise ValueError("Motion-target boundary removed functions")
    if any(boundary_addresses[name] != address
           for name, address in baseline_addresses.items()):
        raise ValueError("Motion-target boundary shifted an address")
    if (set(boundary_functions) != set(qualified_functions) or
            boundary_addresses != qualified_addresses):
        raise ValueError("Motion-target qualified inventory changed")
    changed = sorted(name for name in qualified_functions
                     if boundary_functions[name] != qualified_functions[name])
    if changed != sorted(FUNCTIONS):
        raise ValueError("Motion-target full-image closure changed: " + repr(changed))
    for name, words in ((WRAPPER, 10), (INITIALIZER, 57)):
        if qualified_functions[name] != list(struct.unpack(">%dI" % words,
                                                            retail_bytes(root, name))):
            raise ValueError("Linked motion-target payload differs: " + name)

    protected = audit_layout(qualified_elf, root / "conker")
    if (protected["exact"], protected["bytes"], protected["owner_count"],
            protected["different_bytes"]) != (True, 189088, 720, 0):
        raise ValueError("Motion-target protected data changed")
    inventory = project_progress(root, output, qualified_map, qualified_owner,
                                 qualified_inventory[SYMBOLS])

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "qualified-layout.us.txt").write_bytes(qualified_inventory[LAYOUT])
    (output / "qualified-symbols.us.txt").write_bytes(qualified_inventory[SYMBOLS])
    (output / "qualified-undefined-functions.txt").write_bytes(
        qualified_inventory[UNDEFINED])
    patches = output / "qualified-patches.csv"
    write_patches(patches, fields, qualified_rows)

    report = {
        "functions": list(FUNCTIONS),
        "source_installed": installed,
        "words": {WRAPPER: 10, INITIALIZER: 57},
        "frames": {WRAPPER: 24, INITIALIZER: 48},
        "natural_positional_differences": {WRAPPER: 0, INITIALIZER: 4},
        "guards": 4,
        "relocations": {name: len(BINDINGS[name]) for name in FUNCTIONS},
        "neighbors": neighbors,
        "raw_sha256": RAW_SHA256,
        "retail_sha256": RETAIL_SHA256,
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "assembly_truth_owner_sha256": digest(truth_owner.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "assembly_truth_elf_sha256": digest(truth_elf.read_bytes()),
        "disassembly_functions_before": len(baseline_functions),
        "disassembly_functions_after": len(qualified_functions),
        "inventory_added_only": INITIALIZER,
        "changed_bodies": changed,
        "all_addresses_fixed": True,
        "inventory_only_loaded_sections_equal": True,
        "strict_exclusions": 0,
        "callers": caller_evidence(root),
        "game_data": protected,
        "inventory": inventory,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return {
        "report": report,
        "fields": fields,
        "predecessor_rows": predecessor_rows,
        "qualified_rows": qualified_rows,
        "predecessor_compact": predecessor_compact,
        "qualified_compact": qualified_compact,
        "predecessor_owner": predecessor_owner,
        "qualified_owner": qualified_owner,
        "truth_owner": truth_owner,
        "baseline_elf": baseline_elf,
        "boundary_elf": boundary_elf,
        "qualified_elf": qualified_elf,
        "truth_elf": truth_elf,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
