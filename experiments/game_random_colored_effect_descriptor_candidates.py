"""Recover the callback's 0x32-byte position/random/color descriptor."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15149EC4','generated_176A00'
SOURCE='conker/src/game/generated_176A00.c'
ENTRY,ROM,WORDS=0x15149EC4,0x177374,67
BUILD='conker/build/game-random-colored-effect-descriptor-15149EC4-match'
PLACEHOLDER='s32 func_15149EC4() {\n    return 0;\n}'
DECLARATIONS='''typedef struct { f32 x, y, z; } EffectPosition176A00;
typedef struct {
    EffectPosition176A00 position;
    u8 retained0C[10];
    s16 value16, value18, value1A, value1C, value1E, value20;
    s16 value22, value24, value26;
    u8 firstRGB[3], secondRGB[3], alpha, value2F;
    s8 value30;
    u8 flags;
} EffectDescriptor176A00;
s32 func_150ADA20(void);
void func_151429E0(u8, u8 *, u8 *, u8 *);
void func_1518CA80(EffectDescriptor176A00 *, u8);

'''
SELECTED='''/* Submit a position snapshot with ordered random fields and two color rows. */
s32 func_15149EC4(u8 *actor) {
    EffectDescriptor176A00 descriptor;

    descriptor.position = *(EffectPosition176A00 *)(actor + 0x34);
    descriptor.value16 = 0;
    descriptor.value18 = 0;
    descriptor.value1A = descriptor.value1C = (u32)func_150ADA20() % 6u + 8;
    descriptor.value1E = 0;
    descriptor.value20 = 0;
    descriptor.value22 = (u32)func_150ADA20() % 201u + 100;
    descriptor.value24 = (u32)func_150ADA20() % 5u + 3;
    descriptor.value26 = 600;
    func_151429E0(3, &descriptor.firstRGB[0], &descriptor.firstRGB[1], &descriptor.firstRGB[2]);
    func_151429E0(4, &descriptor.secondRGB[0], &descriptor.secondRGB[1], &descriptor.secondRGB[2]);
    descriptor.alpha = 255;
    descriptor.value2F = (u32)func_150ADA20() % 65u + 92;
    descriptor.value30 = (u32)func_150ADA20() % 3u + 1;
    descriptor.flags = 0;
    func_1518CA80(&descriptor, 1);
    return 0;
}'''

def source_states(live):
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live:return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live:return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Random/color descriptor source state changed')

def compare(body=SELECTED,label='selected',declarations=DECLARATIONS):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    source=source_states((ROOT/SOURCE).read_text())[1].replace(DECLARATIONS+SELECTED,declarations+body,1)
    obj,diag=compile_owner(ROOT,out,source,label);text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+268]
    result=dict(words=size//4,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>67I',truth)))if a!=b],
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(compare(),indent=2))
