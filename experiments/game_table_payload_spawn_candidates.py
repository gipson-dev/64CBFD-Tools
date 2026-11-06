"""Original table request and split payload copy; reproducible owner states."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1515A974','generated_185560'
SOURCE,ASM='conker/src/game/generated_185560.c','conker/asm/185560.s'
BUILD='conker/build/game-table-payload-spawn-1515A974-match'
ENTRY,ROM,WORDS=0x1515A974,0x187E24,68
OLD='s32 func_1515A974() {\n    return 0;\n}'
HEADERS='typedef struct {u8 bytes[4];} TableSpawnHeader1515A974;\ntypedef struct {f32 values[10];} TableSpawnValues1515A974;\ntypedef struct {\n    TableSpawnHeader1515A974 header;\n    TableSpawnValues1515A974 values;\n} TableSpawnPayload1515A974;\ntypedef struct {\n    f32 primary, secondary;\n    TableSpawnPayload1515A974 payload;\n} TableSpawnEntry1515A974;\ntypedef struct {\n    u8 kind;\n    u8 reserved01[3];\n    u8 *owner;\n    f32 primary, secondary;\n    f32 zero[5];\n    u8 enabled;\n    s8 mode;\n    u8 flags;\n} TableSpawnRequest1515A974;\nextern TableSpawnEntry1515A974 D_800A636C[];\nu8 *func_151A8B20(TableSpawnRequest1515A974 *, s16, s32, u8, s32);\n'
SELECTED='/* Create the selected table effect and attach its retained payload. */\nvoid func_1515A974(u8 * volatile owner, s32 unused) {\n    TableSpawnRequest1515A974 request;\n    u8 *created;\n    TableSpawnEntry1515A974 *entry;\n    TableSpawnPayload1515A974 payload;\n    u8 index = owner[0x1F];\n\n    if ((s32)index <= 0) {\n        request.kind = 0x0F;\n        request.owner = owner;\n        entry = &D_800A636C[index];\n        request.primary = entry->primary;\n        request.secondary = entry->secondary;\n        request.enabled = 0;\n        request.mode = -1;\n        request.flags = 2;\n        request.zero[0] = 0.0f;\n        request.zero[1] = 0.0f;\n        request.zero[2] = 0.0f;\n        request.zero[3] = 0.0f;\n        request.zero[4] = 0.0f;\n        payload.header = entry->payload.header;\n        payload.values = entry->payload.values;\n        created = func_151A8B20(&request, -1, 0x2C, 0xFF, 0);\n        if (created != NULL) {\n            memcpy(created + 0x80, &payload, sizeof(payload));\n        }\n    }\n}'
NEW=HEADERS+SELECTED

def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Table payload constructor source state changed')
