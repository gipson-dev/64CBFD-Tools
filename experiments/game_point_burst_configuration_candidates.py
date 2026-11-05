"""Screen the copied-position burst descriptor and eight-argument submission."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_effect_configuration_packet_candidates import PACKET as SHAPE
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151DCDE0','generated_20A290'
SOURCE='conker/src/game/generated_20A290.c'
BUILD='conker/build/game-point-burst-configuration-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x151DCDE0,0x20A290,66,68
PLACEHOLDER='s32 func_151DCDE0() {\n    return 0;\n}'
PACKET=SHAPE.replace('1CBE20','20A290')
DECLARATIONS=PACKET+'''
extern f32 D_800AB558, D_800AB55C, D_800AB560, D_800AB564;
extern s32 D_800AB550;
extern f32 D_800AB554;
void func_15152190(Configuration20A290 *, s32 *, f32 *, s32, f32, u8, u8, s32);

'''
SELECTED='''/* Submit the copied position with this burst's fixed configuration and channel. */
void func_151DCDE0(Position20A290 *position, u8 channel, s32 context) {
    Configuration20A290 packet;
    f32 scale = D_800AB558;

    packet.count = 12;
    packet.countRange = 5;
    packet.position = *position;
    packet.angle = 0;
    packet.angleRange = 255;
    packet.pitch = -64;
    packet.pitchRange = 49;
    packet.speed = 3.0f;
    packet.speedRange = 9.0f;
    packet.vertical = D_800AB55C;
    packet.verticalRange = D_800AB560;
    packet.lifetime = 25;
    packet.lifetimeRange = 20;
    packet.scale = scale;
    packet.scaleRange = scale;
    packet.spread = D_800AB564;
    func_15152190(&packet, &D_800AB550, &D_800AB554, 1, 26.0f, 0, channel, context);
}'''
def source_states(live):
    marker='/* Non-matching placeholders for the text-only asm slice asm/20A290.s. */'
    recovered='/* Copied-position burst configuration from asm/20A290.s. */'
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(marker,DECLARATIONS+recovered,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(recovered,marker,1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Point burst configuration source state changed')
def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    diffs=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=diffs,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
