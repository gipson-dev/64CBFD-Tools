"""Screen the fractional phase accumulator and live randomized effect packet."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151A0AF8','generated_1CC440'
SOURCE='conker/src/game/generated_1CC440.c'
BUILD='conker/build/game-fractional-burst-emitter-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x151A0AF8,0x1CDFA8,69,69
PLACEHOLDER='s32 func_151A0AF8() {\n    return 0;\n}'
DECLARATIONS='''typedef struct {
    f32 x, y, z;
    u8 tag;
    u8 retained0D[3];
    f32 phase;
} FractionalBurstPayload151A0AF8;
typedef struct {
    u8 retained00[0x0C];
    u8 context;
    u8 retained0D[0x1B];
    FractionalBurstPayload151A0AF8 payload;
} FractionalBurstEmitter151A0AF8;
extern f32 D_800A8D10, D_800BE9A4;
f32 func_150ADA68(void);
void func_1514C678(f32, f32, f32, f32, s16, s16, s16, u8, s32, f32, void *, u8);

'''
SELECTED='''/* Accumulate fractional emissions and submit each burst using live payload fields. */
void func_151A0AF8(FractionalBurstEmitter151A0AF8 *record) {
    record->payload.phase += D_800A8D10 * D_800BE9A4;
    if (record->payload.phase > 1.0f) {
        FractionalBurstPayload151A0AF8 *payload = &record->payload;

        do {
            f32 magnitude = func_150ADA68() * 25.0f + 15.0f;

            func_1514C678(payload->x, payload->y, payload->z,
                magnitude,
                0, 255, 5, 4, payload->tag, 0.0f, NULL, record->context);
            payload->phase -= 1.0f;
        } while (payload->phase > 1.0f);
    }
}'''
def source_states(live):
    marker='/* Non-matching placeholders for the text-only asm slice asm/1CC440.s. */'
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(marker,DECLARATIONS+marker,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Fractional burst emitter source state changed')
def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
