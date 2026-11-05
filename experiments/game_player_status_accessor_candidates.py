"""Screen the seven-field player status accessor and halfword argument homes."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150859AC','generated_B21B0'
SOURCE='conker/src/game/generated_B21B0.c'
BUILD='conker/build/game-player-status-accessor-candidates'
ENTRY,ROM,WORDS=0x150859AC,0xB2E5C,68
PLACEHOLDER='s32 func_150859AC() {\n    return 0;\n}'
MAKE_RULE='$(BUILD_DIR)/$(SRC_DIR)/game/generated_B21B0.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009D9A0\n'
MAKE_ANCHOR='$(BUILD_DIR)/$(SRC_DIR)/game/generated_E4070.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009FD00_game\n'
REPAIRS={
    'conker/Makefile':((MAKE_ANCHOR,MAKE_ANCHOR+MAKE_RULE,1),),
    'conker/include/functions.h':(('s32  func_150859AC(s16 arg0, s32 arg1); // a guess','s32 func_150859AC(s16 slot, s16 field); /* Seven player-status fields. */',1),),
    'conker/src/game/generated_5D2C0.c':(('s32 func_150859AC(s32, s32);','s32 func_150859AC(s16, s16);',1),),
    'conker/src/game/generated_B3020.c':(('s32 func_150859AC(s16 slot, s32 field);','s32 func_150859AC(s16 slot, s16 field);',1),('s32 func_150859AC(s16, s32);','s32 func_150859AC(s16, s16);',2)),
    'conker/src/game/generated_215960.c':(('#include "variables.h"\n','#include "variables.h"\ns32 func_150859AC(s16 slot, s16 field);\n',1),),
}
DECLARATIONS='''/* The six field labels are offset views of 0x1C-byte status records. */
typedef struct { s32 value; u8 padding[24]; } StatusWordB21B0;
typedef struct { s8 value; u8 padding[27]; } StatusSignedByteB21B0;
typedef struct { u8 value; u8 padding[27]; } StatusUnsignedByteB21B0;
extern s16 D_800D2340;
extern StatusWordB21B0 D_800D213C[], D_800D2140[], D_800D2148[];
extern StatusSignedByteB21B0 D_800D2144[], D_800D2145[];
extern StatusUnsignedByteB21B0 D_800D2146[];

'''
SELECTED='''/* Read one of the seven status fields; slots at least 255 return zero. */
s32 func_150859AC(s16 slot, s16 field) {
    if (slot >= 255) return 0;
    switch (field) {
        case 0: return (u16)D_800D2340 & (1u << slot);
        case 1: return D_800D213C[slot].value;
        case 2: return D_800D2140[slot].value;
        case 3: return D_800D2144[slot].value;
        case 4: return D_800D2145[slot].value;
        case 5: return D_800D2146[slot].value;
        case 6: return D_800D2148[slot].value;
    }
    /* Other selectors have the retail routine's unspecified result. */
}'''

def source_states(live):
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Player status accessor source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def repair_states(path,live):
    before=after=live;flags=[]
    for old,new,count in REPAIRS[path]:
        if live.count(new)==count:
            before=before.replace(new,old);flags.append(True)
        elif live.count(old)==count and new not in live:
            after=after.replace(old,new);flags.append(False)
        else:raise ValueError('Player status interface repair changed: '+path)
    if len(set(flags))!=1:raise ValueError('Partial player status interface repair: '+path)
    return before,after,flags[0]

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    diffs=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=diffs,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
