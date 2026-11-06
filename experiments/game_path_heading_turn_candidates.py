"""Live actor path heading and byte-threshold turning callback."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15077F64','game_A28B0'
SOURCE='conker/src/game_A28B0.c'
BUILD='conker/build/game-path-heading-turn-15077F64-match'
ENTRY,ROM,WORDS=0x15077F64,0xA5414,68
PROTOTYPE_BEFORE='s32 func_15077F64();'
PROTOTYPE_AFTER='void func_15077F64(void);'
OLD_BLOCK='/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_15077F64.s. */\ns32 func_15077F64() {\n    return 0;\n}\n// NON-MATCHING: what is D_800D2104 ???\n// void func_15056A00(s32, s32, u8);\n// void func_15077F64(void) {\n//     u8 temp_t6;\n//     struct169 *temp_v0;\n//     s32 phi_a0;\n//     s32 phi_a1;\n//\n//     temp_t6 = D_800D1890 - 1;\n//     temp_v0 = D_800D2104[D_800D154C->unk13F] + (D_800D154C->unk21E);\n//     D_800D154C->unk78 = func_1505A630(temp_v0->unk8 - D_800D154C->x_position, D_800D154C->z_position - temp_v0->unkC, 0);\n//     phi_a0 = phi_a1 = ((s32) (D_800D154C->unk78 - D_800D154C->unk76) >> 8) & 0xff;\n//     if ((phi_a0 & 0x80) != 0) {\n//         phi_a1 = phi_a0 = -phi_a0 & 0xFF;\n//     }\n//     if ((u8)D_80099A3C[temp_t6 * 0xA] < phi_a0) {\n//         D_800D154C->unk250 = (u8) D_800D1891;\n//         func_15056A00(D_800D154C, phi_a1, temp_t6);\n//     }\n// }\n\n'
SELECTED = '''/* Face the next path record, then submit turning state past its byte threshold. */
void func_15077F64(void) {
    extern void func_15056A00(void *, u8, u8);
    f32 x;
    f32 z;
    u8 threshold;
    u8 row;
    PathNode8 *node;
    s32 distance;
    s32 magnitude;
    u16 heading;

    node = &((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D154C->unk21E];
    x = node[1].x - D_800D154C->x_position;
    z = D_800D154C->z_position - node[1].z;
    row = D_800D1890 - 1;
    heading = func_1505A630(x, z, 0);
    D_800D154C->unk78 = heading;
    distance = magnitude = ((s32)(D_800D154C->unk78 - D_800D154C->unk76) >> 8) & 0xFF;
    if ((distance & 0x80) != 0) {
        magnitude = distance = -distance & 0xFF;
    }
    threshold = ((u8 *)D_80099A3C)[row * 10];
    if (threshold < distance) {
        D_800D154C->unk250 = D_800D1891;
        func_15056A00(D_800D154C, magnitude, row);
    }
}'''
NEW_BLOCK=SELECTED+"\n\n"

def source_states(live):
    if live.count(OLD_BLOCK)==1 and live.count(PROTOTYPE_BEFORE)==1 and SELECTED not in live:
        return live,live.replace(OLD_BLOCK,NEW_BLOCK,1).replace(PROTOTYPE_BEFORE,PROTOTYPE_AFTER,1),False
    if live.count(NEW_BLOCK)==1 and live.count(PROTOTYPE_AFTER)==1 and OLD_BLOCK not in live:
        return live.replace(NEW_BLOCK,OLD_BLOCK,1).replace(PROTOTYPE_AFTER,PROTOTYPE_BEFORE,1),live,True
    raise ValueError('Path heading-turn source/interface state changed')
