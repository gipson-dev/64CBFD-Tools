"""Owner-link snapshot, optional queried position and returned payload record."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151A3504','generated_1D0840'
SOURCE,ASM='conker/src/game/generated_1D0840.c','conker/asm/1D0840.s'
BUILD='conker/build/game-owner-position-request-151A3504-match'
ENTRY,ROM,WORDS=0x151A3504,0x1D09B4,70
OLD='s32 func_151A3504() {\n    return 0;\n}'
HEADERS='typedef struct OwnerPosition151A3504 { f32 x, y, z; } OwnerPosition151A3504;\ntypedef struct OwnerSnapshot151A3504 {\n    u8 *owner;\n    u8 identity, slot, reserved06[2], remainder08[0x28];\n} OwnerSnapshot151A3504;\ntypedef struct OwnerPayload151A3504 {\n    OwnerSnapshot151A3504 snapshot;\n    u8 kind, reserved31[3];\n    OwnerPosition151A3504 position;\n    f32 value40;\n    u8 flag44, reserved45[3];\n    f32 value48;\n    u8 flag4C, reserved4D[3];\n} OwnerPayload151A3504;\ntypedef struct OwnerRequest151A3504 {\n    OwnerPosition151A3504 position;\n    s16 lifetime;\n    u16 flags;\n    s32 step;\n    u8 reserved14, count, reserved16[6];\n} OwnerRequest151A3504;\nvoid *memcpy(void *, const void *, u32);\ns32 func_151A4E34(u8 *, void *);\nu8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, void *, u8, s32);\n'
SELECTED='/* Snapshot an owner link, query its position, and attach the payload to a new record. */\nu8 *func_151A3504(void *input, u8 channel) {\n    OwnerRequest151A3504 request;\n    OwnerPayload151A3504 payload;\n    u8 *created;\n\n    if (*(u8 **)input == NULL) {\n        return NULL;\n    }\n    /* The query and factory consume partial records; leave reserved bytes alone. */\n    memcpy(&payload, input, 0x30);\n    payload.flag44 = 0;\n    request.count = 50;\n    request.flags = 2;\n    request.lifetime = 1000;\n    payload.kind = 6;\n    payload.flag4C = 0;\n    payload.value40 = 0.0f;\n    payload.value48 = 0.0f;\n    if (func_151A4E34((u8 *)&payload, &request.position)) {\n        payload.position = request.position;\n        request.flags |= 4;\n    }\n    request.step = 8;\n    created = func_15147A80(&request, 0x50, 0x18, 6, 6, 6, 0, 0, NULL, channel, 0);\n    if (created != NULL) {\n        memcpy(*(void **)(created + 0x98), &payload, 0x50);\n    }\n    return created;\n}'
NEW=HEADERS+SELECTED
def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Owner-position request source state changed')
