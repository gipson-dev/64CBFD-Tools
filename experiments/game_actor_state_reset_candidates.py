"""Screen semantic C forms for the actor-state reset at func_151218C4."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    link_owner,
)


FUNCTION = "func_151218C4"
OWNER = "generated_14D110"
SOURCE = "conker/src/game/generated_14D110.c"
BUILD = "conker/build/game-actor-state-reset-151218C4-candidates"
ENTRY = 0x151218C4
ROM = 0x14ED74
WORDS = 67

TYPED_DECLARATIONS = """#include "structs.h"
void func_1506160C(struct127 *, s32, u8, u8, s32);
void func_151C9ED4(void *);
"""

OLD_STYLE_DECLARATIONS = """#include "structs.h"
void func_1506160C();
void func_151C9ED4();
"""

PLACEHOLDER = """s32 func_151218C4() {
    return 0;
}"""

BYTE_BODY = """/* Reset the actor's view state unless its resource blocks the reset. */
void func_151218C4(u8 *actor) {
    u8 *view;

    if ((*(u16 *)*(u8 **)(actor + 0x36C) & 0x10) == 0) {
        if (*(s32 *)(actor + 0x34) == 0x40) {
            if (*(s32 *)(actor + 0x6FC) == 0xF) {
                *(f32 *)(actor + 0x898) = 0.0f;
                *(f32 *)(actor + 0x89C) = 0.0f;
            }
            *(*(u8 **)(actor + 0x3D4) + 0x198) = 0;
            *(s16 *)(actor + 0x73C) = 0;
            *(s16 *)(actor + 0x84A) = 0x3C;
        } else {
            *(s16 *)(actor + 0x84A) = 0x3C;
            *(s16 *)(actor + 0x73C) = 3;
        }
        view = actor + 0x740;
        *(f32 *)(actor + 0x374) = 200.0f;
        *(f32 *)(actor + 0x348) = 100.0f;
        *(s32 *)(actor + 0x134) = (s32)*(f32 *)(view + 0x2C);
        view[0x4C] = 0;
        *(f32 *)(actor + 0x190) = 0.0f;
        *(f32 *)(actor + 0x99C) = 0.0f;
        *(f32 *)(actor + 0x198) = 0.0f;
        func_1506160C(*(void **)(actor + 0x3D0), 2, 0xFF, 0x20,
                      actor[0x23D]);
        if (actor[0x84C] != 0) {
            func_151C9ED4(actor);
            actor[0x84C] = 0;
        }
    }
}"""

VOID_VIEW_BODY = BYTE_BODY.replace(
    "    u8 *view;", "    void *view;"
).replace(
    "        view = actor + 0x740;", "        view = (void *)(actor + 0x740);"
).replace(
    "*(f32 *)(view + 0x2C)", "*(f32 *)((u8 *)view + 0x2C)"
).replace(
    "        view[0x4C] = 0;", "        *((u8 *)view + 0x4C) = 0;"
)

STRUCT_VIEW_BODY = BYTE_BODY.replace(
    "/* Reset the actor's view state unless its resource blocks the reset. */",
    """typedef struct {
    u8 pad0[0x2C];
    f32 angle;
    u8 pad30[0x1C];
    u8 active;
} ResetView151218C4;

/* Reset the actor's view state unless its resource blocks the reset. */""",
).replace(
    "    u8 *view;", "    ResetView151218C4 *view;"
).replace(
    "        view = actor + 0x740;",
    "        view = (ResetView151218C4 *)(actor + 0x740);",
).replace(
    "*(f32 *)(view + 0x2C)", "view->angle"
).replace(
    "        view[0x4C] = 0;", "        view->active = 0;"
)

TYPED_ACTOR_BODY = """typedef struct {
    u8 pad0[0x2C];
    f32 angle;
    u8 pad30[0x1C];
    u8 active;
} ResetView151218C4;

typedef struct {
    u8 pad0[0x34];
    s32 kind;
    u8 pad38[0xFC];
    s32 angleInteger;
    u8 pad138[0x58];
    f32 reset190;
    u8 pad194[0x4];
    f32 reset198;
    u8 pad19C[0xA1];
    u8 commandByte;
    u8 pad23E[0x10A];
    f32 distance348;
    u8 pad34C[0x20];
    u16 *resourceFlags;
    u8 pad370[0x4];
    f32 distance374;
    u8 pad378[0x58];
    struct127 *commandTarget;
    struct127 *target;
    u8 pad3D8[0x324];
    s32 mode;
    u8 pad700[0x3C];
    s16 state;
    u8 pad73E[0x2];
    ResetView151218C4 view;
    u8 pad790[0xBA];
    s16 timer;
    u8 cleanupPending;
    u8 pad84D[0x4B];
    f32 reset898;
    f32 reset89C;
    u8 pad8A0[0xFC];
    f32 reset99C;
} ResetActor151218C4;

/* Reset the actor's view state unless its resource blocks the reset. */
void func_151218C4(ResetActor151218C4 *actor) {
    ResetView151218C4 *view;

    if ((*actor->resourceFlags & 0x10) == 0) {
        if (actor->kind == 0x40) {
            if (actor->mode == 0xF) {
                actor->reset898 = 0.0f;
                actor->reset89C = 0.0f;
            }
            actor->target->unk198 = 0;
            actor->state = 0;
            actor->timer = 0x3C;
        } else {
            actor->timer = 0x3C;
            actor->state = 3;
        }
        view = &actor->view;
        actor->distance374 = 200.0f;
        actor->distance348 = 100.0f;
        actor->angleInteger = (s32)view->angle;
        view->active = 0;
        actor->reset190 = 0.0f;
        actor->reset99C = 0.0f;
        actor->reset198 = 0.0f;
        func_1506160C(actor->commandTarget, 2, 0xFF, 0x20,
                      actor->commandByte);
        if (actor->cleanupPending != 0) {
            func_151C9ED4(actor);
            actor->cleanupPending = 0;
        }
    }
}"""

VOLATILE_ACTOR_BODY = TYPED_ACTOR_BODY.replace(
    "void func_151218C4(ResetActor151218C4 *actor) {\n"
    "    ResetView151218C4 *view;",
    "void func_151218C4(volatile ResetActor151218C4 *actor) {\n"
    "    volatile ResetView151218C4 *view;",
).replace(
    "            func_151C9ED4(actor);", "            func_151C9ED4((void *)actor);"
)

REGISTER_VIEW_BODY = VOLATILE_ACTOR_BODY.replace(
    "    volatile ResetView151218C4 *view;",
    "    register volatile ResetView151218C4 *view;",
)

BRANCH_VIEW_BODY = VOLATILE_ACTOR_BODY.replace(
    "        view = &actor->view;\n", ""
).replace(
    "            actor->timer = 0x3C;\n        } else {",
    "            actor->timer = 0x3C;\n"
    "            view = &actor->view;\n"
    "        } else {",
).replace(
    "            actor->state = 3;\n        }",
    "            actor->state = 3;\n"
    "            view = &actor->view;\n"
    "        }",
)

COMMAND_TEMP_BODY = BRANCH_VIEW_BODY.replace(
    "    volatile ResetView151218C4 *view;",
    "    volatile ResetView151218C4 *view;\n    u8 commandByte;",
).replace(
    "        view->active = 0;\n        actor->reset190 = 0.0f;",
    "        view->active = 0;\n"
    "        commandByte = actor->commandByte;\n"
    "        actor->reset190 = 0.0f;",
).replace(
    "                      actor->commandByte);",
    "                      commandByte);",
)

NONVOLATILE_COMMAND_BODY = BRANCH_VIEW_BODY.replace(
    "                      actor->commandByte);",
    "                      ((ResetActor151218C4 *)actor)->commandByte);",
)

NONVOLATILE_FIRST_RESET_BODY = NONVOLATILE_COMMAND_BODY.replace(
    "        actor->reset190 = 0.0f;",
    "        ((ResetActor151218C4 *)actor)->reset190 = 0.0f;",
)
NONVOLATILE_TWO_RESETS_BODY = NONVOLATILE_FIRST_RESET_BODY.replace(
    "        actor->reset99C = 0.0f;",
    "        ((ResetActor151218C4 *)actor)->reset99C = 0.0f;",
)
NONVOLATILE_THREE_RESETS_BODY = NONVOLATILE_TWO_RESETS_BODY.replace(
    "        actor->reset198 = 0.0f;",
    "        ((ResetActor151218C4 *)actor)->reset198 = 0.0f;",
)

COMMAND_S32_BODY = COMMAND_TEMP_BODY.replace(
    "    u8 commandByte;", "    s32 commandByte;"
)
COMMAND_U32_BODY = COMMAND_TEMP_BODY.replace(
    "    u8 commandByte;", "    u32 commandByte;"
)
COMMAND_FIRST_BODY = COMMAND_TEMP_BODY.replace(
    "    volatile ResetView151218C4 *view;\n    u8 commandByte;",
    "    u8 commandByte;\n    volatile ResetView151218C4 *view;",
)

SELECTED = NONVOLATILE_THREE_RESETS_BODY
SELECTED_DECLARATIONS = TYPED_DECLARATIONS


def variants():
    yield "byte-u8-nested-typed", BYTE_BODY, TYPED_DECLARATIONS
    yield "byte-u8-nested-old-style", BYTE_BODY, OLD_STYLE_DECLARATIONS
    yield "void-view-u8-nested-typed", VOID_VIEW_BODY, TYPED_DECLARATIONS
    yield "void-view-u8-nested-old-style", VOID_VIEW_BODY, OLD_STYLE_DECLARATIONS
    yield "struct-view-u8-nested-typed", STRUCT_VIEW_BODY, TYPED_DECLARATIONS
    yield "struct-view-u8-nested-old-style", STRUCT_VIEW_BODY, OLD_STYLE_DECLARATIONS
    yield "typed-actor-typed-helpers", TYPED_ACTOR_BODY, TYPED_DECLARATIONS
    yield "typed-actor-old-style-helpers", TYPED_ACTOR_BODY, OLD_STYLE_DECLARATIONS
    yield "volatile-actor-typed-helpers", VOLATILE_ACTOR_BODY, TYPED_DECLARATIONS
    yield "volatile-actor-old-style-helpers", VOLATILE_ACTOR_BODY, OLD_STYLE_DECLARATIONS
    yield "register-view-typed-helpers", REGISTER_VIEW_BODY, TYPED_DECLARATIONS
    yield "register-view-old-style-helpers", REGISTER_VIEW_BODY, OLD_STYLE_DECLARATIONS
    yield "branch-view-typed-helpers", BRANCH_VIEW_BODY, TYPED_DECLARATIONS
    yield "branch-view-old-style-helpers", BRANCH_VIEW_BODY, OLD_STYLE_DECLARATIONS
    yield "command-temp-typed-helpers", COMMAND_TEMP_BODY, TYPED_DECLARATIONS
    yield "command-temp-old-style-helpers", COMMAND_TEMP_BODY, OLD_STYLE_DECLARATIONS
    yield "nonvolatile-command-typed-helpers", NONVOLATILE_COMMAND_BODY, TYPED_DECLARATIONS
    yield "nonvolatile-command-old-style-helpers", NONVOLATILE_COMMAND_BODY, OLD_STYLE_DECLARATIONS
    yield "nonvolatile-command-reset1", NONVOLATILE_FIRST_RESET_BODY, TYPED_DECLARATIONS
    yield "nonvolatile-command-reset2", NONVOLATILE_TWO_RESETS_BODY, TYPED_DECLARATIONS
    yield "nonvolatile-command-reset3", NONVOLATILE_THREE_RESETS_BODY, TYPED_DECLARATIONS
    yield "command-s32-typed-helpers", COMMAND_S32_BODY, TYPED_DECLARATIONS
    yield "command-u32-typed-helpers", COMMAND_U32_BODY, TYPED_DECLARATIONS
    yield "command-first-typed-helpers", COMMAND_FIRST_BODY, TYPED_DECLARATIONS
    yield "void-view-void-nested-old-style", VOID_VIEW_BODY.replace(
        "void func_151218C4(u8 *actor)", "void func_151218C4(void *arg0)"
    ).replace(
        "    void *view;\n", "    u8 *actor = (u8 *)arg0;\n    void *view;\n"
    ), OLD_STYLE_DECLARATIONS
    yield "byte-u8-early-return-old-style", BYTE_BODY.replace(
        "    if ((*(u16 *)*(u8 **)(actor + 0x36C) & 0x10) == 0) {\n",
        "    if (*(u16 *)*(u8 **)(actor + 0x36C) & 0x10) {\n"
        "        return;\n"
        "    }\n"
        "    {\n",
    ), OLD_STYLE_DECLARATIONS
    yield "byte-void-nested-old-style", BYTE_BODY.replace(
        "void func_151218C4(u8 *actor)", "void func_151218C4(void *arg0)"
    ).replace(
        "    u8 *view;\n", "    u8 *actor = (u8 *)arg0;\n    u8 *view;\n"
    ), OLD_STYLE_DECLARATIONS
    yield "byte-no-view-temp-old-style", BYTE_BODY.replace(
        "    u8 *view;\n\n", ""
    ).replace(
        "        view = actor + 0x740;\n", ""
    ).replace(
        "*(f32 *)(view + 0x2C)", "*(f32 *)(actor + 0x76C)"
    ).replace(
        "        view[0x4C] = 0;", "        actor[0x78C] = 0;"
    ), OLD_STYLE_DECLARATIONS
    yield "byte-s32-return-old-style", BYTE_BODY.replace(
        "void func_151218C4(u8 *actor)", "s32 func_151218C4(u8 *actor)"
    ).replace(
        "    }\n}", "    }\n    return 0;\n}", 1
    ), OLD_STYLE_DECLARATIONS


def candidate_source(before, body, declarations):
    if before.count(PLACEHOLDER) != 1:
        raise ValueError("Actor-state reset placeholder anchor changed")
    include_anchor = "#include <ultra64.h>\n"
    if before.count(include_anchor) != 1:
        raise ValueError("Actor-state reset include anchor changed")
    return before.replace(
        include_anchor, include_anchor + declarations, 1
    ).replace(PLACEHOLDER, body, 1)


def retail_bytes(root):
    image = (root / "conker/conker.us.bin").read_bytes()
    return image[ROM:ROM + WORDS * 4]


def compare(actual, retail):
    actual_words = list(struct.iter_unpack(">I", actual))
    retail_words = list(struct.iter_unpack(">I", retail))
    limit = max(len(actual_words), len(retail_words))
    return [
        index for index in range(limit)
        if (actual_words[index] if index < len(actual_words) else None) !=
           (retail_words[index] if index < len(retail_words) else None)
    ]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = retail_bytes(root)
    records = []
    for entry in variants():
        label, body, declarations = entry[:3]
        flags = entry[3] if len(entry) == 4 else ("-O2", "-g3")
        source = candidate_source(before, body, declarations)
        obj, diagnostics = compile_owner(
            root, output, source, label + "-" + OWNER, flags=flags
        )
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        while len(actual) > len(retail) and actual[-4:] == b"\0\0\0\0":
            actual = actual[:-4]
        differences = compare(actual, retail)
        record = {
            "variant": label,
            "words": len(actual) // 4,
            "retail_words": WORDS,
            "flags": list(flags),
            "differences": len(differences),
            "difference_indices": differences,
            "body_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(json.dumps({
            key: value for key, value in record.items()
            if key != "diagnostics"
        }))
    (output / "candidates.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
