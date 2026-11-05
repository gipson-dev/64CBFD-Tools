"""Screen the material callback's animation-gated tile-size update."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150D82BC','generated_105760'
SOURCE='conker/src/game/generated_105760.c'
ENTRY,ROM,WORDS=0x150D82BC,0x10576C,71
BUILD='conker/build/game-material-tile-animation-150D82BC-match'
PLACEHOLDER='s32 func_150D82BC() {\n    return 0;\n}'
DECLARATIONS='''extern s32 D_80090298[];
extern f32 D_800A0B10;

'''
SELECTED='''/* Select the animation material and move its first tile-size command. */
s32 func_150D82BC(u8 *material, u8 *actor) {
    u8 *animation;
    Gfx *commands;
    s32 index;
    f32 fraction;
    s32 offset;
    s32 coordinate;
    s32 previous;

    animation = *(u8 **)(actor + 0x2D0);
    if (animation == NULL) return 0;
    *(s16 *)(material + 0x18) = D_80090298[6];
    if (*(u16 *)(actor + 0x84) == 13) {
        if (*(f32 *)(animation + 8) >= 23.0f &&
            *(f32 *)(animation + 8) <= 40.0f) {
            *(s16 *)(material + 0x18) = D_80090298[7];
            fraction = *(f32 *)(animation + 8) - 23.0f;
            fraction *= D_800A0B10;
            commands = **(Gfx ***)(material + 0x24);
            for (index = 0; *(s8 *)&commands[index] != -14; index++) {}
            commands += index;
            previous = (*(s32 *)commands >> 12) & 0xFFF;
            offset = 70.0f * fraction + 2.0f;
            coordinate = offset;
            if (offset < 0) coordinate = offset + previous;
            commands->words.w0 = ((coordinate & 0xFFF) << 12) | 0xF2000000 | 2;
        }
    }
    return 0;
}'''

def source_states(live):
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live:
        return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Material tile callback source state changed')

def compare(body=SELECTED,label='selected',flags=('-O2','-g3')):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    source=source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
    obj,diagnostics=compile_owner(ROOT,out,source,label,flags)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size]
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>71I',truth)))if a!=b]
    result=dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size},diagnostics=diagnostics)
    (out/(label+'-screen.json')).write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':print(json.dumps(compare(),indent=2))
