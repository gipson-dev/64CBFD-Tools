"""Private text-buffer fade recovery; explicitly no byte-match or installation credit."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150D01A0','generated_FC5F0'
SOURCE='conker/src/game/generated_FC5F0.c'
BUILD='conker/build/game-text-buffer-fade-150D01A0-match'
ENTRY,ROM,WORDS=0x150D01A0,0xFD650,69
OLD='s32 func_150D01A0() {\n    return 0;\n}'
SELECTED="""/* Blend the two text buffers while the signed byte countdown decays. */
s32 func_150D01A0(u8 *owner) {
    s8 *count;
    u8 opacity = 0;
    u8 inverse = 255;
    TextDescriptorFC5F0 *text;

    count = (s8 *)((TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28))->payload;
    if (((((u8 **)&owner)[0])[0x30] & 1) != 0) {
        *count = 8;
    }
    if (*count > 0) {
        opacity = *count * 31;
        inverse = 255 - opacity;
        *count = (u8)((u32)*count - (u32)D_800BE9E4);
    }
    if (inverse != 0) {
        func_1504332C(206, 196, 97, inverse);
        text = (TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28);
        func_15042D94(146, 190, 129, (s32)text->buffers[text->index]);
    }
    if (opacity != 0) {
        text = (TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28);
        func_1504332C(206, 196, 97, opacity);
        func_15042D94(146, 190, 129, (s32)text->buffers[text->index ^ 1]);
    }
    return 1;
}"""
