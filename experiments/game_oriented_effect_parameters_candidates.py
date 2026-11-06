"""Original oriented-effect constructor and reproducible complete-owner source states."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150DBC60','generated_108E90'
SOURCE='conker/src/game/generated_108E90.c'
BUILD='conker/build/game-oriented-effect-parameters-150DBC60-match'
ENTRY,ROM,WORDS=0x150DBC60,0x109110,68
OLD='s32 func_150DBC60() {\n    return 0;\n}'
HEADERS = """typedef struct { f32 x, y, z; } OrientedEffectPosition;
typedef struct {
    OrientedEffectPosition position;
    f32 fieldCBase, field10Range, field14Base, field18Range, speedBase, speedRange;
    s16 countBase, countRange, firstAngleBase, firstAngleRange;
    s16 secondAngleBase, secondAngleRange, byteBase, byteRange, shortBase, shortRange;
    u8 fixed38, fixed39, private3A[2];
    s32 argument3C, argument40, argument44, argument48, argument4C, argument50;
    u8 fixed54, fixed55, privateTail56[2];
} OrientedEffectInput;
extern f32 D_800A0C24, D_800A0C28, D_800A0C2C, D_800A0C30;
void func_15152F70(OrientedEffectInput *, u8);
"""
SELECTED = """/* Submit the original oriented-effect descriptor with the owner's byte mode. */
void func_150DBC60(struct260 *owner) {
    OrientedEffectInput input;
    input.position.x = D_800A0C24;
    input.position.y = D_800A0C28;
    input.position.z = D_800A0C2C;
    input.speedBase = 7.0f;
    input.speedRange = 5.0f;
    input.field14Base = D_800A0C30;
    input.field18Range = 0.0f;
    input.countBase = 1;
    input.countRange = 2;
    input.firstAngleBase = -75;
    input.secondAngleBase = -38;
    input.firstAngleRange = 22;
    input.secondAngleRange = 35;
    input.byteBase = 3;
    input.byteRange = 2;
    input.shortBase = 41;
    input.shortRange = 0;
    input.fieldCBase = 2.0f;
    input.field10Range = 2.0f;
    input.fixed38 = 10;
    input.fixed39 = 40;
    input.argument3C = 1;
    input.argument40 = 0;
    input.argument44 = 0;
    input.argument48 = 0;
    input.argument4C = 0;
    input.argument50 = 0;
    input.fixed54 = 255;
    input.fixed55 = 255;
    func_15152F70(&input, ((u8 *)owner)[0x0C]);
}"""
NEW=HEADERS+SELECTED

def source_states(live):
    old_include='#include <ultra64.h>\n'
    new_include=old_include+'#include "structs.h"\n'
    if live.count(OLD)==1 and NEW not in live and new_include not in live:
        return live,live.replace(OLD,NEW,1).replace(old_include,new_include,1),False
    if live.count(NEW)==1 and OLD not in live and live.count(new_include)==1:
        return live.replace(NEW,OLD,1).replace(new_include,old_include,1),live,True
    raise ValueError('Oriented-effect constructor source state changed')
