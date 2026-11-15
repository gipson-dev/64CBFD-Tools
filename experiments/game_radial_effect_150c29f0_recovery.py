"""Recover the complete radial effect packet and timer update without installing."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-radial-effect-150c29f0-private';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C29F0'
ENTRY,ROM,SIZE=0x150c29f0,0xefea0,528
PREAMBLE='''typedef struct {
    f32 x, y, z;
    f32 size0, delta0, size1, delta1, delta2;
    s16 code0, code1, duration;
    u8 firstColor[3], alpha;
    u16 flags2A;
    u8 secondColor[3], enabled;
    s32 zero30;
    u8 kind34;
    u8 reserved35[3];
    f32 zero38, value3C, value40, value44;
} RadialEffectPacket150C29F0;

extern f32 D_800A02A0, D_800A02A4, D_800A02A8, D_800A02AC;
extern f32 D_800A02B0, D_800A02B4, D_800A02B8, D_800A02BC;
void *func_15149550(RadialEffectPacket150C29F0 *, u8, u8, s32, u8, s32);
'''
BODY='''/* Submit a randomized radial effect and refresh the owner's timer. */
void func_150C29F0(u8 *owner) {
    RadialEffectPacket150C29F0 packet;
    f32 firstScale, secondScale;
    u8 angle;
    f32 directionX, directionZ, radius;
    u8 *position;

    angle = func_150ADA20();
    directionX = func_151423D8((u8)(angle - 64));
    directionZ = func_151423D8(angle);
    radius = func_150ADA68() * *(f32 *)(owner + 0x30);
    packet.code0 = 0x6231;
    packet.code1 = 0x1A4D;
    packet.firstColor[0] = 0;
    packet.firstColor[1] = 0;
    packet.firstColor[2] = 0;
    packet.alpha = 255;
    packet.secondColor[0] = 255;
    packet.secondColor[1] = 255;
    packet.zero30 = 0;
    packet.flags2A = 1;
    packet.secondColor[2] = 0;
    packet.enabled = 1;
    position = owner + 0x28;
    packet.duration = (u32)func_150ADA20() % 201U + 100;
    packet.kind34 = 15;
    packet.value40 = D_800A02A0;
    packet.zero38 = 0.0f;
    packet.value44 = D_800A02A4;
    packet.x = *(f32 *)position + radius * directionX;
    packet.y = *(f32 *)(position + 12);
    packet.value3C = D_800A02A8;
    packet.z = *(f32 *)(position + 4) + radius * directionZ;
    firstScale = func_150ADA68() * 0.5f + 1.0f;
    secondScale = func_150ADA68() * 0.5f + 1.0f;
    packet.size0 = D_800A02AC * firstScale;
    packet.size1 = D_800A02B0 * firstScale;
    packet.delta0 = D_800A02B4 * secondScale;
    packet.delta1 = D_800A02B8 * secondScale;
    packet.delta2 = D_800A02BC * secondScale;
    func_15149550(&packet, 10, 1, 0, owner[0xC], owner[1]);
    *(s16 *)(owner + 0xE) = (u32)func_150ADA20() % 51U + 25;
}'''

def proposed(source):
 stub=body(source,NAME);assert stub=='s32 func_150C29F0() {\n    return 0;\n}'
 result=source.replace(stub,BODY).replace('s32 func_150C29F0();\n','')
 result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C29F0.s. */\n','')
 return result.rstrip()+'\n'

def symbols():
 result={('D_%08X'%v):v for v in range(0x800a02a0,0x800a02c0,4)}
 return dict(result,func_150ADA20=0x150ada20,func_150ADA68=0x150ada68,func_151423D8=0x151423d8,func_15149550=0x15149550)

def programs():
 truth=list(struct.unpack_from('>132I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));raw,refs=payload(OUT/'recovered.o',NAME)
 return truth,bound_blob(raw,refs,symbols())

def main():
 frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 before=(frozen/SOURCE).read_text();candidate=proposed(before);installed=(ROOT/SOURCE).read_text()==candidate
 plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'recovered');assert d1==d2,(d1,d2)
 neighbors=same_functions(base,obj,(NAME,));assert normalized_pools(base)==normalized_pools(obj)
 truth,raw=programs();blob,refs=payload(obj,NAME)
 report=dict(body_words=len(raw),retail_words=132,frame=(-raw[0])&65535,neighbors=neighbors,real_word_differences=sum(a!=b for a,b in zip(truth,raw))+abs(len(truth)-len(raw)),raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),installed=installed,c_match_credit=0)
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
