"""Owner/tag cache lookup, typed request packet and the original switch table."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-owner-record-lookup-1518BA90-match'
RODATA_SYMBOL='jtbl_800A7410'
TARGETS=[{'function': 'func_1518BA90', 'source': 'conker/src/game/generated_1B8F40.c', 'owner': 'generated_1B8F40', 'object': 'conker/build/src/game/generated_1B8F40.c.o', 'assembly': 'conker/asm/1B8F40.s', 'entry': 353942160, 'rom': 1806144, 'words': 89, 'frame': 72, 'raw_sha256': '59218dcf32dda512f800f5483b846af19de70f58fc1b495b65df32767ae991b7', 'bindings': {28: [('R_MIPS_HI16', 'D_800DCE50')], 44: [('R_MIPS_LO16', 'D_800DCE50')], 40: [('R_MIPS_HI16', 'D_800DD190')], 48: [('R_MIPS_LO16', 'D_800DD190')], 144: [('R_MIPS_HI16', '.rodata')], 152: [('R_MIPS_LO16', '.rodata')], 172: [('R_MIPS_HI16', 'D_800A7434')], 176: [('R_MIPS_LO16', 'D_800A7434')], 180: [('R_MIPS_HI16', 'D_800A7438')], 184: [('R_MIPS_LO16', 'D_800A7438')], 188: [('R_MIPS_HI16', 'D_800A743C')], 192: [('R_MIPS_LO16', 'D_800A743C')], 332: [('R_MIPS_26', 'func_1518BCD0')]}, 'patches': {44: (608305152, 612630528), 48: (612630528, 608305152)}}]
SUPPORT='/* The update routine samples base + random * range and indices 0..limit. */\ntypedef struct {\n    f32 firstBase, firstRange, secondBase, secondRange;\n    s16 firstChoiceLimit, secondChoiceLimit;\n    u8 *owner;\n    u8 tag, mode, subtype, retained;\n} OwnerRecordRequest;\nextern f32 D_800A7434, D_800A7438, D_800A743C;\nvoid *func_1518BCD0(void *, u8, s32);\n'
SELECTED="/* Reuse the first owner/tag record, or construct the owner's default effect. */\nvoid *func_1518BA90(u8 *owner, u8 priority, s32 context) {\n    void *result;\n    OwnerRecordRequest request;\n    u8 *row;\n    u8 *end;\n    u8 *record;\n    if (owner == NULL) {\n        return NULL;\n    }\n    row = D_800DCE50;\n    end = (u8 *)&D_800DD190;\n    do {\n        record = *(u8 **)(row + 0x7C);\n        while (record != NULL) {\n            if (*(u8 **)(record + 0x24) == owner || owner[0x3B] == record[0x28]) {\n                return record;\n            }\n            record = *(u8 **)(record + 8);\n        }\n        row += 0x1A0;\n    } while (row != end);\n    switch (owner[4]) {\n        /* Unreachable for u8; preserves the original nine-entry table. */\n        case -1:\n            return NULL;\n        case 7:\n            request.firstBase = D_800A7434;\n            request.firstRange = D_800A7438;\n            request.secondBase = D_800A743C;\n            request.secondRange = 5.0f;\n            request.secondChoiceLimit = 55;\n            request.firstChoiceLimit = 4;\n            request.mode = 5;\n            request.subtype = 19;\n            break;\n        case 0:\n        case 1:\n        case 2:\n        case 3:\n        case 4:\n            request.secondChoiceLimit = 0;\n            request.firstChoiceLimit = 5;\n            request.mode = 5;\n            request.subtype = 19;\n            request.firstBase = 10.0f;\n            request.firstRange = 10.0f;\n            request.secondBase = 10.0f;\n            request.secondRange = 10.0f;\n            break;\n        default:\n            return NULL;\n    }\n    request.owner = owner;\n    request.tag = owner[0x3B];\n    result = func_1518BCD0(&request, priority, context);\n    return result;\n}"
MAKE_ANCHOR='$(BUILD_DIR)/$(SRC_DIR)/game/generated_1B1600.c.o: OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0\n'
MAKE_ADDITION='# Owner-record dispatch uses its preserved nine-entry retail switch table.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_1B8F40.c.o: RETAIL_RODATA_SYMBOL := jtbl_800A7410\n'

def source_states(live,index=0):
    if index!=0:raise ValueError('Only one owner-record source')
    stub='s32 func_1518BA90() {\n    return 0;\n}'
    selected=SUPPORT+'\n'+SELECTED
    if live.count(stub)==1:
        if selected in live or SUPPORT in live:raise ValueError('Owner-record predecessor changed')
        return live,live.replace(stub,selected,1),False
    if live.count(selected)!=1:raise ValueError('Owner-record source changed')
    return live.replace(selected,stub,1),live,True
def make_states(live):
    if live.count(MAKE_ANCHOR)!=1:raise ValueError('Owner-record Make anchor changed')
    if MAKE_ADDITION in live:
        if live.count(MAKE_ADDITION)!=1:raise ValueError('Duplicated owner-record table binding')
        return live.replace(MAKE_ADDITION,'',1),live,True
    if 'generated_1B8F40.c.o: RETAIL_RODATA_SYMBOL' in live:raise ValueError('Foreign owner-record table binding')
    return live,live.replace(MAKE_ANCHOR,MAKE_ANCHOR+MAKE_ADDITION,1),False
