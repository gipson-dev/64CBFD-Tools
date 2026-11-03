"""Screen semantic C forms for func_15123070's camera heading normalizer."""

import argparse
import hashlib
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x15123070
ROM = 0x150520
WORDS = 67
FUNCTION = "func_15123070"
SOURCE = "conker/src/game_14FF90.c"
OWNER = "game_14FF90"
BUILD = "conker/build/game-camera-heading-normalizer-candidates"
DECLARATION = "s32 func_15123070(s32 arg0);"
TYPED_DECLARATION = "void func_15123070(struct108 *camera);"
FUNCTIONS_INCLUDE = '#include "functions.h"'
LOOSE_VECTOR_INCLUDE = """/* Retail keeps the camera in the vector helper's unused fourth argument. */
#define func_15048F90 func_15048F90_legacy_three_argument_signature
#include "functions.h"
#undef func_15048F90
extern void func_15048F90();"""
PLACEHOLDER = """/* Non-matching C placeholders for asm/nonmatchings/game_14FF90/func_15123070.s. */
s32 func_15123070(s32 arg0) {
    return 0;
}"""
LEGACY_DRAFT = """// NON-MATCHING: 1 missing lui
// void func_15123070(struct108 *arg0) {
//     f32 temp_f0;
//     struct17 tmp;
//
//     if ((arg0->unk6C8 != 0) && ((arg0->unk6FC == 10) || (arg0->unk6FC == 14))) {
//         func_15048F90(&arg0->unk618, &arg0->unk2A4, &tmp, arg0);
//         arg0->unk390 = arg0->unk37C - func_15048FC8(&tmp);
//     } else {
//         temp_f0 = arg0->unk3D0->unk40 - arg0->unk37C - 180.0f;
//
//         while (temp_f0 < 0.0f) {
//             temp_f0 += 360.0f;
//         }
//
//         arg0->unk390 = temp_f0;
//     }
//
//     while (arg0->unk390 < -360.0f) {
//         arg0->unk390 += 360.0f;
//     }
// }"""
PREDECESSOR_BLOCK = PLACEHOLDER + "\n" + LEGACY_DRAFT

BODY_TEMPLATE = """/* Update and normalize the camera heading relative to its tracked actor. */
void func_15123070(struct108 *camera) {
    f32 heading;
    struct17 direction;

    if ((camera->unk6C8 != 0) &&
            ((camera->unk6FC == 10) || (camera->unk6FC == 14))) {
        CALL_FORM
        camera->unk390 = camera->unk37C - func_15048FC8(&direction);
    } else {
        heading = camera->unk3D0->unk40 - camera->unk37C - 180.0f;
        while (heading < 0.0f) {
            heading += 360.0f;
        }
        camera->unk390 = heading;
    }
    while (camera->unk390 < -360.0f) {
        camera->unk390 += 360.0f;
    }
}"""
SELECTED = BODY_TEMPLATE.replace(
    "CALL_FORM",
    "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);").replace(
    "    struct17 direction;", "    struct17 direction;\n    f32 special_heading;").replace(
    "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
    "        special_heading = camera->unk37C - func_15048FC8(&direction);\n        camera->unk390 = special_heading;")


ROOT = Path(__file__).resolve().parents[2]


def source_with(body, loose_vector=False):
    source = (ROOT / SOURCE).read_text()
    if source.count(DECLARATION) != 1 or source.count(PLACEHOLDER) != 1:
        raise ValueError("Camera heading normalizer predecessor source changed")
    source = source.replace(DECLARATION, TYPED_DECLARATION, 1).replace(
        PLACEHOLDER, body, 1)
    if loose_vector:
        if source.count(FUNCTIONS_INCLUDE) != 1:
            raise ValueError("Camera owner functions include changed")
        source = source.replace(FUNCTIONS_INCLUDE, LOOSE_VECTOR_INCLUDE, 1)
    return source


def variants():
    yield "selected", SELECTED
    yield "direct-fourth-argument", BODY_TEMPLATE.replace(
        "CALL_FORM", "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")
    yield "three-argument", BODY_TEMPLATE.replace(
        "CALL_FORM", "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction);")
    yield "cast-oldstyle-fourth", BODY_TEMPLATE.replace(
        "CALL_FORM", "((void (*)())func_15048F90)((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")
    yield "cast-typed-fourth", BODY_TEMPLATE.replace(
        "CALL_FORM", "((void (*)(struct17 *, struct17 *, struct17 *, struct108 *))func_15048F90)((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")
    yield "loose-direct-fourth", BODY_TEMPLATE.replace(
        "CALL_FORM", "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")


def shape_variants():
    base = BODY_TEMPLATE.replace(
        "CALL_FORM", "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")
    yield "shape-baseline", base
    yield "shape-branch-minimum", base.replace(
        "    f32 heading;", "    f32 heading;\n    f32 minimum;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);\n        minimum = -360.0f;").replace(
        "        camera->unk390 = heading;", "        camera->unk390 = heading;\n        minimum = -360.0f;").replace(
        "camera->unk390 < -360.0f", "camera->unk390 < minimum")
    yield "shape-common-minimum", base.replace(
        "    f32 heading;", "    f32 heading;\n    f32 minimum;").replace(
        "    while (camera->unk390 < -360.0f)",
        "    minimum = -360.0f;\n    while (camera->unk390 < minimum)")
    yield "shape-output-pointer", base.replace(
        "camera->unk390", "*output").replace(
        "    struct17 direction;", "    struct17 direction;\n    f32 *output = &camera->unk390;")
    yield "shape-helper-result-local", base.replace(
        "    f32 heading;", "    f32 heading;\n    f32 direction_heading;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        direction_heading = func_15048FC8(&direction);\n        camera->unk390 = camera->unk37C - direction_heading;")
    yield "shape-reversed-final-test", base.replace(
        "camera->unk390 < -360.0f", "-360.0f > camera->unk390")
    yield "shape-final-for", base.replace(
        "    while (camera->unk390 < -360.0f) {\n        camera->unk390 += 360.0f;\n    }",
        "    for (; camera->unk390 < -360.0f; camera->unk390 += 360.0f) {\n    }")
    yield "shape-final-guarded-do", base.replace(
        "    while (camera->unk390 < -360.0f) {\n        camera->unk390 += 360.0f;\n    }",
        "    if (camera->unk390 < -360.0f) {\n        do {\n            camera->unk390 += 360.0f;\n        } while (camera->unk390 < -360.0f);\n    }")
    yield "shape-first-guarded-do", base.replace(
        "        while (heading < 0.0f) {\n            heading += 360.0f;\n        }",
        "        if (heading < 0.0f) {\n            do {\n                heading += 360.0f;\n            } while (heading < 0.0f);\n        }")
    yield "shape-special-value-local", base.replace(
        "    f32 heading;", "    f32 heading;\n    f32 special_heading;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        special_heading = camera->unk37C - func_15048FC8(&direction);\n        camera->unk390 = special_heading;")
    yield "shape-special-value-after-struct", base.replace(
        "    struct17 direction;", "    struct17 direction;\n    f32 special_heading;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        special_heading = camera->unk37C - func_15048FC8(&direction);\n        camera->unk390 = special_heading;")
    yield "shape-special-value-existing-heading", base.replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        heading = camera->unk37C - func_15048FC8(&direction);\n        camera->unk390 = heading;")
    yield "shape-duplicated-normalize", """/* Update and normalize the camera heading relative to its tracked actor. */
void func_15123070(struct108 *camera) {
    f32 heading;
    struct17 direction;

    if ((camera->unk6C8 != 0) &&
            ((camera->unk6FC == 10) || (camera->unk6FC == 14))) {
        func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);
        camera->unk390 = camera->unk37C - func_15048FC8(&direction);
        while (camera->unk390 < -360.0f) {
            camera->unk390 += 360.0f;
        }
    } else {
        heading = camera->unk3D0->unk40 - camera->unk37C - 180.0f;
        while (heading < 0.0f) {
            heading += 360.0f;
        }
        camera->unk390 = heading;
        while (camera->unk390 < -360.0f) {
            camera->unk390 += 360.0f;
        }
    }
}"""
    yield "shape-union-minimum-bits", base.replace(
        "    struct17 direction;",
        "    struct17 direction;\n    union { u32 bits; f32 value; } minimum;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);\n        minimum.bits = 0xC3B40000;").replace(
        "        camera->unk390 = heading;",
        "        camera->unk390 = heading;\n        minimum.bits = 0xC3B40000;").replace(
        "camera->unk390 < -360.0f", "camera->unk390 < minimum.value")
    yield "shape-union-minimum-float", base.replace(
        "    struct17 direction;",
        "    struct17 direction;\n    union { u32 bits; f32 value; } minimum;").replace(
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);",
        "        camera->unk390 = camera->unk37C - func_15048FC8(&direction);\n        minimum.value = -360.0f;").replace(
        "        camera->unk390 = heading;",
        "        camera->unk390 = heading;\n        minimum.value = -360.0f;").replace(
        "camera->unk390 < -360.0f", "camera->unk390 < minimum.value")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    try:
        obj, diagnostics = compile_owner(ROOT, output, source_with(
            body, loose_vector=(name.startswith("loose-") or name == "selected")), name,
                                         flags=flags)
    except ValueError as error:
        return {"name": name, "compile_error": str(error)}
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
        "linked_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


def compare_minimal(name, body, flags=("-O2", "-g3")):
    """Compile only this function so unsupported owner profiles can be screened."""
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    source = output / (name + "-minimal.c")
    obj = output / (name + "-minimal.o")
    source.write_text(
        '#include <ultra64.h>\n#include "structs.h"\n'
        'void func_15048F90();\nf32 func_15048FC8(struct17 *);\n\n' +
        body + "\n")
    includes = [".", "include", "include/2.0L", "include/2.0L/PR",
                "include/libc", "src/libultra/os", "src/libultra/audio",
                "src/libultra/io"]
    command = [str(ROOT / "ido/ido5.3_recomp/cc"), "-c", "-32", "-G", "0",
        "-Xfullwarn", "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
        "-Wab,-r4300_mul", "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
        "-D_MIPS_SZLONG=32", "-woff", "649,838",
        *[flag for path in includes for flag in ("-I", path)], *flags,
        "-mips2", "-o32", "-o", str(obj.relative_to(ROOT / "conker")),
        str(source.relative_to(ROOT / "conker"))]
    result = subprocess.run(command, cwd=ROOT / "conker", capture_output=True,
                            text=True)
    if result.returncode:
        return {"name": name, "compile_error": result.stdout + result.stderr}
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
        if left != right]
    return {"name": name, "flags": flags, "words": len(our_words),
            "differences": len(differences), "difference_rows": differences,
            "diagnostics": result.stdout + result.stderr,
            "linked_sha256": hashlib.sha256(ours).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-only", action="store_true")
    parser.add_argument("--shapes", action="store_true")
    parser.add_argument("--filter", default="")
    args = parser.parse_args()
    records = []
    for name, body in (() if args.minimal_only else (
            pair for pair in variants()
            if not args.filter or args.filter in pair[0])):
        record = compare(name, body)
        records.append(record)
        if "compile_error" in record:
            print(name, "compile error", flush=True)
        else:
            print(name, record["words"], record["differences"], flush=True)
    body = BODY_TEMPLATE.replace(
        "CALL_FORM", "func_15048F90((struct17 *)&camera->unk618, &camera->unk2A4, &direction, camera);")
    profiles = (("minimal-O2g3", ("-O2", "-g3")),
                           ("minimal-O2", ("-O2",)),
                           ("minimal-O2g3-nounroll", ("-O2", "-g3", "-Wo,-loopunroll,0")),
                           ("minimal-O1g3", ("-O1", "-g3")),
                           ("minimal-O1", ("-O1",)),
                           ("minimal-g", ("-g",)),
                           ("minimal-O0", ("-O0",)),
                           ("minimal-O3", ("-O3",)))
    jobs = (((name, candidate_body, ("-O2", "-g3"))
             for name, candidate_body in shape_variants()
             if not args.filter or args.filter in name) if args.shapes else (
                (profile, body, flags) for profile, flags in profiles)) \
        if args.minimal_only else ()
    for profile, candidate_body, flags in jobs:
        record = compare_minimal(profile, candidate_body, flags=flags)
        records.append(record)
        if "compile_error" in record:
            print(record["name"], "compile error", flush=True)
        else:
            print(record["name"], record["words"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
