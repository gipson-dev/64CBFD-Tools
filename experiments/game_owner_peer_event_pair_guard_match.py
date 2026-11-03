"""Recover the paired class-53 owner identity event callbacks."""

import csv
from collections import Counter
import io
from pathlib import Path
import re
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.experiments.game_four_head_lookup_match import payload


FILENAME = "game_18D770"
SOURCE = "conker/src/game_18D770.c"
OBJECT = "conker/build/src/game_18D770.c.o"
BUILD = "conker/build/game-owner-peer-event-pair-guard-match"
WORDS = 53
RAW_WORDS = 52
FRAME = 0x18
DECLARATIONS = """typedef struct {
    u32 key;
    u8 tag;
} OwnerIdentityState;

typedef struct {
    u32 first;
    u32 second;
    u8 firstTag;
    u8 secondTag;
} OwnerIdentityEvent;

typedef void (*OwnerIdentityCallback)(void *, void *, u8);

"""
TARGETS = {
    "func_15163FEC": dict(entry=0x15163FEC, rom=0x19149C,
                           selector=0x2D, table="D_8008B374",
                           registry_index=16),
    "func_15164134": dict(entry=0x15164134, rom=0x1915E4,
                           selector=0x3D, table="D_8008B37C",
                           registry_index=17),
}
SYMBOLS = {
    "func_1516972C": 0x1516972C,
    "D_8008B374": 0x8008B374,
    "D_8008B37C": 0x8008B37C,
}


def selected_body(name):
    spec = TARGETS[name]
    return """/* Apply an identity event, or delegate it through the owner's subtype table. */
void NAME(void *owner, void *event, u8 kind) {
    OwnerIdentityState *current;
    OwnerIdentityState *identity;
    OwnerIdentityEvent *replacement;
    OwnerIdentityCallback callback;
    u32 key;
    u32 oldKey;

    current = (OwnerIdentityState *)((u8 *)owner + 0x18);
    if (kind == 0) {
        identity = event;
        key = identity->key;
        if ((key == current->key) || (identity->tag == current->tag)) {
            func_1516972C((struct102 *)owner);
        }
    } else if (kind == 0x2D) {
        replacement = event;
        oldKey = current->key;
        key = replacement->first;
        if (key == oldKey) {
            current->key = replacement->second;
            current->tag = replacement->secondTag;
        } else if (oldKey == replacement->second) {
            current->key = key;
            current->tag = replacement->firstTag;
        }
    } else {
        callback = ((OwnerIdentityCallback *)TABLE)[*((u8 *)owner + SELECTOR)];
        if (callback != NULL) {
            callback(owner, event, kind);
        }
    }
}
""".replace("NAME", name).replace("TABLE", spec["table"]) \
        .replace("SELECTOR", hex(spec["selector"]))


def recovered_owner(before):
    result = before
    if DECLARATIONS not in result:
        marker = '#include "variables.h"\n'
        if result.count(marker) != 1:
            raise ValueError("Owner identity include marker changed")
        result = result.replace(marker, marker + "\n" + DECLARATIONS, 1)
    for name in TARGETS:
        old_decl = "s32 %s();" % name
        new_decl = "void %s(void *, void *, u8);" % name
        if old_decl in result:
            result = result.replace(old_decl, new_decl, 1)
        elif new_decl not in result:
            raise ValueError("Owner identity declaration changed: " + name)
        start, end = function_span(result, name)
        existing = result[start:end]
        body = selected_body(name).rstrip()
        installed = body.split("\n", 1)[1]
        if existing != installed:
            if existing != "s32 %s() {\n    return 0;\n}" % name:
                raise ValueError("Owner identity definition changed: " + name)
            result = result[:start] + body + result[end:]
            result = result.replace(
                "// ???\n/* Non-matching C placeholders for "
                "asm/nonmatchings/game_18D770/%s.s. */\n" % name, "", 1)
            result = result.replace(
                "/* Non-matching C placeholders for "
                "asm/nonmatchings/game_18D770/%s.s. */\n" % name, "", 1)
    return result


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    _, baseline = compile_owner(
        root, output, (root / SOURCE).read_text(),
        "owner-peer-event-pair-baseline")
    obj, diagnostics = compile_owner(
        root, output, recovered_owner((root / SOURCE).read_text()),
        "owner-peer-event-pair-compact")
    def rows(text):
        lines = text.splitlines()
        result = []
        for index, line in enumerate(lines):
            match = re.match(r"cfe: Warning (\d+): .*?, line \d+: (.*)", line)
            if match:
                source = lines[index + 1].strip() if index + 1 < len(lines) else ""
                result.append((match.group(1), match.group(2), source))
            elif line.startswith("cfe:") and "Warning" not in line:
                raise ValueError("Unexpected owner identity diagnostic: " + line)
        return Counter(result)
    if rows(diagnostics) != rows(baseline):
        raise ValueError("Owner identity diagnostics changed: " + diagnostics)
    return obj


def relocation_text(relocations):
    return "-" if not relocations else ";".join(
        kind + ":" + symbol for kind, symbol in relocations)


def unrelocated(word, relocations):
    for kind, _ in relocations:
        if kind in ("R_MIPS_HI16", "R_MIPS_LO16"):
            word &= 0xFFFF0000
        elif kind == "R_MIPS_26":
            word &= 0xFC000000
        else:
            raise ValueError("Unsupported owner identity relocation: " + kind)
    return word


def guard_rows(root, obj, name):
    spec = TARGETS[name]
    raw, relocations = payload(obj, name)
    if len(raw) != RAW_WORDS * 4:
        raise ValueError("Owner identity raw extent changed: " + name)
    raw_words = struct.unpack(">%dI" % RAW_WORDS, raw)
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(),
                                spec["rom"])
    rows = []
    for index in range(RAW_WORDS):
        retail_index = index if index <= 37 else index + 1
        bindings = tuple(relocations.get(index * 4, ()))
        expected = raw_words[index]
        replacement = unrelocated(retail[retail_index], bindings)
        insertion = retail[38] if index == 37 else None
        if expected == replacement and insertion is None:
            continue
        rows.append({
            "filename": FILENAME,
            "function": name,
            "offset": "0x%03X" % (index * 4),
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": relocation_text(bindings),
            "replacement_relocations": relocation_text(bindings),
            "note": "Normalize closed owner identity event compiler schedule",
            "insert_after": "0x%08X" % insertion if insertion is not None else "",
            "insert_after_relocations": "-" if insertion is not None else "",
            "omit": "false",
        })
    if len(rows) != 7 or sum(bool(row["insert_after"]) for row in rows) != 1:
        raise ValueError("Owner identity guard closure changed: " + name)
    return rows


def all_rows(root, obj):
    return [row for name in TARGETS for row in guard_rows(root, obj, name)]


def write_rows(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]),
                            lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")
