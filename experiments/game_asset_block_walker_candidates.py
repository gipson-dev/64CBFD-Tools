"""Asset blocks: narrow selector ABI, live bounds and unsigned byte-size decoding."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15015920','generated_42DC0'
SOURCE,ASM='conker/src/game/generated_42DC0.c','conker/asm/42DC0.s'
CALLER_SOURCE='conker/src/game/entrypoint.c'
CALLER_OBJECT='conker/build/src/game/entrypoint.c.o'
BUILD='conker/build/game-asset-block-walker-15015920-match'
ENTRY,ROM,WORDS=0x15015920,0x42DD0,70
OLD='s32 func_15015920() {\n    return 0;\n}'
HEADERS="typedef struct AssetRange15015920 { s32 start, end; } AssetRange15015920;\nextern AssetRange15015920 D_80082F80[];\ns32 func_10003C6C(s32, s32, s32, s32, s32);\ns32 func_10004514(s32, void *, u32, s32);\nvoid func_10004074(void *);\n/* Retail consumes (u8 *, s32, s32); keep the unfinished consumer's existing declaration. */\ns32 func_15015A38();\n"
SELECTED='/* Load the selected asset range, consume its blocks, and free the temporary copy. */\nvoid func_15015920(s16 selector) {\n    u8 *base;\n    u8 *cursor;\n    s32 index;\n\n    base = (u8 *)func_10003C6C(0x2800, 1, 2, 1, 0);\n    func_10004514(D_80082F80[selector].start, base,\n                 (u32)D_80082F80[selector].end - (u32)D_80082F80[selector].start, 1);\n    cursor = base;\n    index = 0;\n    if ((u32)cursor + 15 < (u32)base + D_80082F80[selector].end - D_80082F80[selector].start) {\n        do {\n            func_15015A38(cursor, index, selector);\n            /* Read the live big-endian size after the consumer; unsigned sums wrap. */\n            cursor = (u8 *)((u32)cursor + ((u32)cursor[5] << 16) +\n                           ((u32)cursor[6] << 8) + (u32)cursor[7] + ((u32)cursor[4] << 24));\n            index++;\n        } while ((u32)cursor + 15 < (u32)base + D_80082F80[selector].end - D_80082F80[selector].start);\n    }\n    func_10004074(base);\n}'
NEW=HEADERS+SELECTED

def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Asset walker source state changed')
def caller_states(live):
    a,b='void func_15015920(s32);','void func_15015920(s16);'
    if live.count(a)==1 and b not in live:return live,live.replace(a,b,1),False
    if live.count(b)==1 and a not in live:return live.replace(b,a,1),live,True
    raise ValueError('Asset walker caller declaration changed')
