"""Recover the 104-byte clear and ten live-pointer save-record defaults."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15007168','game_33990'
SOURCE='conker/src/game_33990.c'
ENTRY,ROM,WORDS=0x15007168,0x34618,69
BUILD='conker/build/game-save-defaults-15007168-match'
PLACEHOLDER='// requires jump table\n/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_15007168.s. */\ns32 func_15007168() {\n    return 0;\n}'
DECLARATIONS='''typedef struct {
    u8 retained0, value1, value2, value3, value4;
    s8 value5;
    u8 retained6[3], value9;
} SaveDefaultRecord33990;
extern s8 *D_80082BBC;

'''
SELECTED='''/* Clear the save prefix and initialize ten records through the live pointer. */
void func_15007168(void) {
    u8 *end = D_800BE358;
    u8 *cursor = D_800BE2F0.bytes;
    u32 index;

    do {
        *cursor++ = 0;
    } while ((u32)cursor < (u32)end);

    for (index = 0; index < 10; index++) {
        ((SaveDefaultRecord33990 *)D_80082BBC)[index].value1 = 3;
        ((SaveDefaultRecord33990 *)D_80082BBC)[index].value3 = 2;
        ((SaveDefaultRecord33990 *)D_80082BBC)[index].value4 = 1;
        ((SaveDefaultRecord33990 *)D_80082BBC)[index].value2 = 10;
        switch (index) {
        case 0:
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 3;
            break;
        case 1:
        case 2:
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 5;
            break;
        case 7:
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 20;
            break;
        case 5:
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 20;
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value2 = 0;
            break;
        case 8:
        case 9:
            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 3;
            break;
        }
        ((SaveDefaultRecord33990 *)D_80082BBC)[index].value9 = 0;
    }
}'''
def source_states(live):
    old='s32 func_15007168();';new='void func_15007168(void);'
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live and live.count(old)==1:
        return live,live.replace(old,new,1).replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live and live.count(new)==1:
        return live.replace(new,old,1).replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Save defaults source state changed')
def compare(body=SELECTED,label='selected'):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);text=source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
    obj,diag=compile_owner(ROOT,out,text,label);raw,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];body_bytes=raw[start:start+size]
    r=dict(words=size//4,raw_sha256=hashlib.sha256(body_bytes).hexdigest(),diagnostics=diag,
      raw=[hex(w)for w in struct.unpack('>%dI'%(size//4),body_bytes)],bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':print(json.dumps(compare(),indent=2))
