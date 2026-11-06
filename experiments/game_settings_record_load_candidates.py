"""Load a weighted-checksum settings packet while preserving its live byte 16."""
from pathlib import Path
from unittest.mock import patch
import subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner as compile_default
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15007440','game_33990'
SOURCE='conker/src/game_33990.c'
ENTRY,ROM,WORDS=0x15007440,0x348F0,70
BUILD='conker/build/game-settings-record-load-15007440-match'
PLACEHOLDER='/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_15007440.s. */\ns32 func_15007440() {\n    return 0;\n}'
DECLARATIONS='extern u8 D_8008FE30;\ns32 func_151DD9E4();\nvoid func_151E7EF8(void);\n'
SELECTED='''/* Load the settings payload, retaining its live signed byte at offset 16. */
void func_15007440(void) {
    u16 checksum;
    s32 index;
    s8 saved;
    s8 *settings;
    s8 *cursor;
    u8 *record;

    func_151DD3A0(&D_800BE900, 0, D_800BE358, 32);
    checksum = 0xCC;
    record = D_800BE35A;
    index = 2;
    do {
        checksum += *record++ << (index++ & 3);
    } while (index < 30);
    settings = D_800E0BE0;
    saved = settings[16];
    if (checksum != *(u16 *)D_800BE358) {
        cursor = D_800E0BE0;
        do {
            cursor += 4;
            cursor[-4] = -1;
            cursor[-3] = -1;
            cursor[-2] = -1;
            cursor[-1] = -1;
        } while ((u32)cursor != (u32)D_800E0BFC);
    } else {
        cursor = D_800E0BE0;
        record = D_800BE358;
        do {
            u8 first = record[2];
            u8 second = record[3];
            u8 third = record[4];
            u8 fourth = record[5];
            cursor += 4;
            record += 4;
            cursor[-4] = first;
            cursor[-3] = second;
            cursor[-2] = third;
            cursor[-1] = fourth;
        } while ((u32)cursor != (u32)D_800E0BFC);
    }
    settings[16] = saved;
    func_151DD9E4();
    func_151E7EF8();
    D_8008FE30 = 1;
}'''

def source_states(live):
    old='s32 func_15007440();';new='void func_15007440(void);';anchor='s32 func_151DD4E0(OSMesgQueue *, u8, u8 *);\n'
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live and live.count(old)==1 and live.count(anchor)==1:
        return live,live.replace(anchor,anchor+DECLARATIONS,1).replace(old,new,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and live.count(new)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(new,old,1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Settings loader source state changed')

def compile_owner(root,out,text,label,nounroll=False):
    # This root owner is entirely C. Keep the asm processor's supported O2/g3
    # mode; the no-unroll switch belongs exclusively to the actual IDO driver.
    if 'GLOBAL_ASM'in text:raise ValueError('Settings loader owner gained assembly processing')
    run=subprocess.run
    def invoke(cmd,*a,**kw):
        if any(str(v).endswith('asm_processor.py')for v in cmd):cmd=[v for v in cmd if v!='-Wo,-loopunroll,0']
        return run(cmd,*a,**kw)
    flags=('-O2','-g3','-Wo,-loopunroll,0')if nounroll else('-O2','-g3')
    with patch('subprocess.run',side_effect=invoke):return compile_default(root,out,text,label,flags)
