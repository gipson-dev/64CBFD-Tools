"""Screen the position/byte/context configuration packet against its retail slot."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_effect_configuration_packet_candidates import PACKET as SHAPE
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1513A48C','game_161520'
SOURCE='conker/src/game_161520.c'
BUILD='conker/build/game-point-configuration-candidates'
ENTRY,ROM,WORDS=0x1513A48C,0x16793C,66
PLACEHOLDER='s32 func_1513A48C() {\n    return 0;\n}'
LEGACY_COMMENT='/* Non-matching C placeholders for asm/nonmatchings/game_161520/func_1513A48C.s. */'
PACKET=SHAPE.replace('1CBE20','161520')
DECLARATIONS=PACKET+'''
extern f32 D_800A4950, D_800A4954, D_800A4958, D_800A495C;
extern s32 D_800A4260;
extern f32 D_800A4264;
void func_15152190(Configuration161520 *, s32 *, f32 *, s32, f32, u8, u8, s32);

'''
SELECTED='''/* Submit a copied position and fixed effect parameters for this channel. */
void func_1513A48C(Position161520 *position, u8 channel, s32 context) {
    Configuration161520 packet;
    f32 scale = D_800A4950;

    packet.count = 8;
    packet.countRange = 4;
    packet.position = *position;
    packet.angle = 0;
    packet.angleRange = 255;
    packet.pitch = -55;
    packet.pitchRange = 32;
    packet.speed = 10.0f;
    packet.speedRange = 9.0f;
    packet.vertical = D_800A4954;
    packet.verticalRange = D_800A4958;
    packet.lifetime = 40;
    packet.lifetimeRange = 20;
    packet.scale = scale;
    packet.scaleRange = scale;
    packet.spread = D_800A495C;
    func_15152190(&packet, &D_800A4260, &D_800A4264, 1, 0.0f, 1, channel, context);
}'''

def source_states(live):
    declaration='s32 func_1513A48C();'
    marker='/* Generated placeholder declarations. */'
    if live.count(PLACEHOLDER)==1 and live.count(declaration)==1 and DECLARATIONS not in live:
        proposed=live.replace(marker,DECLARATIONS+marker,1).replace(declaration,
            'void func_1513A48C(Position161520 *position, u8 channel, s32 context);',1).replace(PLACEHOLDER,SELECTED,1)
        if proposed.count(LEGACY_COMMENT)!=1:raise ValueError('Point configuration placeholder comment changed')
        proposed=proposed.replace(LEGACY_COMMENT,'',1)
        return live,proposed,False
    typed='void func_1513A48C(Position161520 *position, u8 channel, s32 context);'
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and live.count(typed)==1:
        before=live.replace(DECLARATIONS,'',1).replace(typed,declaration,1).replace(SELECTED,PLACEHOLDER,1)
        if LEGACY_COMMENT in live:raise ValueError('Point configuration obsolete comment remains')
        before=before.replace('\n'+PLACEHOLDER,LEGACY_COMMENT+'\n'+PLACEHOLDER,1)
        return before,live,True
    raise ValueError('Point configuration source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED,flags=('-O2','-g3')):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diag=compile_owner(ROOT,out,source_with(body),label,flags)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    diffs=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=diffs,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})

if __name__=='__main__':print(json.dumps(compare(),indent=2))
