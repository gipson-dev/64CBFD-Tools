"""Recover the signed-threshold callback with two ordered unsigned RNG draws."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1516A538','generated_197120'
SOURCE='conker/src/game/generated_197120.c'
ENTRY,ROM,WORDS=0x1516A538,0x1979E8,68
BUILD='conker/build/game-threshold-random-effect-1516A538-match'
PLACEHOLDER='s32 func_1516A538() {\n    return 0;\n}'
DECLARATIONS='''s32 func_150ADA20(void);
void func_15171D4C(f32, f32, f32, s16, u16, u8, f32, s32, s32, s32, s32, s32, u8, s32);

'''
SELECTED='''/* Submit the randomized effect once the signed record value reaches 0x300. */
void func_1516A538(u8 *record) {
    u32 variant;
    s32 scale;
    u32 angle;

    if (*(s16 *)(record + 0x14) >= 0x300) {
        variant = (u32)func_150ADA20() % 3u;
        scale = record[0x25];
        angle = (u32)func_150ADA20() % 360u;
        func_15171D4C((f32)*(s16 *)(record + 0x18),
                     (f32)(*(s16 *)(record + 0x1A) - 10),
                     (f32)*(s16 *)(record + 0x1C),
                     100, 0, variant + 32,
                     (f32)angle,
                     0, scale * 25 / 255 + 25, 0, 256, 0,
                     record[0x0C], record[1]);
    }
}'''
def source_states(live):
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live:return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live:return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Threshold random effect source state changed')
def compare(body=SELECTED,label='selected',declarations=DECLARATIONS):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    text=source_states((ROOT/SOURCE).read_text())[1].replace(DECLARATIONS+SELECTED,declarations+body,1)
    obj,diag=compile_owner(ROOT,out,text,label);raw,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];body_bytes=raw[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+272]
    r=dict(words=size//4,raw_sha256=hashlib.sha256(body_bytes).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
      differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>68I',truth)))if a!=b],
      bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':print(json.dumps(compare(),indent=2))
