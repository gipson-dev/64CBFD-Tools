"""Recover the complete motion-gated effect accumulator without installation."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-motion-effect-150c2c00-private';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C2C00'
ENTRY,ROM,SIZE=0x150c2c00,0xf00b0,972
PREAMBLE='''extern f32 D_800A02C0, D_800A02C4, D_800A02C8, D_800A02CC;
extern f32 D_800A02D0, D_800A02D4, D_800A02D8, D_800A02DC;
extern f32 D_800A02E0, D_800A02E4, D_800A02E8, D_800A02EC;
extern f32 D_800A02F0, D_800A02F4, D_800A02F8, D_800A02FC;
extern f32 D_800A0300, D_800A0304, D_800A0308, D_800A030C;
void func_1514373C(f32, f32, f32 *, f32 *);
'''
BODY='''/* Consume accumulated emission attempts, gated by motion and heading. */
void func_150C2C00(u8 *owner) {
    RadialEffectPacket150C29F0 packet;
    f32 heading;
    f32 firstScale, secondScale;
    f32 *accumulator;
    f32 *motion;
    f32 x, z, speedSquared;
    f32 angleLimit, headingBase, headingScale, effectScale;
    void *created;

    *(f32 *)(owner + 0x28) +=
        (((func_150ADA68() * 20.0f) * D_800A02C0) * D_800BE9A4) * D_800A02C4;
    accumulator = (f32 *)(owner + 0x28);
    if (1.0f < *accumulator) {
        motion = func_15144B34(D_80082FA4);
        x = motion[0];
        z = motion[2];
        speedSquared = x * x + z * z;
        if (D_800A02C8 < speedSquared) {
            packet.y = -390.0f;
            packet.value40 = D_800A02CC;
            packet.value44 = D_800A02D0;
            angleLimit = D_800A02D4;
            headingBase = D_800A02D8;
            headingScale = D_800A02DC;
            packet.value3C = 0.0f;
            packet.code0 = 0x6231;
            packet.code1 = 0x1A4D;
            packet.firstColor[0] = 0;
            packet.firstColor[1] = 0;
            packet.firstColor[2] = 0;
            packet.alpha = 255;
            packet.secondColor[1] = 255;
            packet.secondColor[2] = 20;
            packet.enabled = 1;
            /* This packet variant uses word 0x30 as mode four. */
            packet.zero30 = 4;
            packet.flags2A = 1;
            packet.kind34 = 25;
            effectScale = D_800A02E0;
            do {
                heading = func_150ADA68() * headingScale + headingBase;
                if (func_15144C8C(func_150484A0(motion[0], motion[2]), heading) < angleLimit) {
                    func_1514373C(heading,
                        func_150ADA68() * D_800A02E4 + D_800A02E8,
                        &packet.x, &packet.z);
                    firstScale = (func_150ADA68() * D_800A02EC + D_800A02F0) * effectScale;
                    secondScale = func_150ADA68();
                    packet.size0 = D_800A02F4 * firstScale;
                    packet.size1 = D_800A02F8 * firstScale;
                    secondScale = (secondScale * D_800A02FC + D_800A0300) * effectScale;
                    packet.delta0 = D_800A0304 * secondScale;
                    packet.delta1 = D_800A0308 * secondScale;
                    packet.delta2 = D_800A030C * secondScale;
                    packet.duration = (u32)func_150ADA20() % 151U + 50;
                    packet.zero38 = (func_150ADA68() * 500.0f) * effectScale;
                    packet.secondColor[0] = (u32)func_150ADA20() % 156U + 100;
                    created = func_15149550(&packet, 10, 1, 0, owner[0xC], owner[1]);
                    if (created != 0) {
                        memcpy((u8 *)created + 0x160, &heading, sizeof(heading));
                    }
                }
                *accumulator -= 1.0f;
            } while (1.0f < *accumulator);
        } else {
            do {
                *accumulator -= 1.0f;
            } while (1.0f < *accumulator);
        }
    }
}'''

def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C2C00() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C2C00();\n','')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('#include <ultra64.h>','#include <ultra64.h>\n#include <string.h>',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C2C00.s. */\n','')
    return result.rstrip()+'\n'

def symbols():
    result={('D_%08X'%v):v for v in range(0x800a02c0,0x800a0310,4)}
    return dict(result,D_800BE9A4=0x800be9a4,D_80082FA4=0x80082fa4,
        func_150ADA20=0x150ada20,func_150ADA68=0x150ada68,
        func_15144B34=0x15144b34,func_150484A0=0x150484a0,
        func_15144C8C=0x15144c8c,func_1514373C=0x1514373c,
        func_15149550=0x15149550,memcpy=0x10022ec0)

def programs():
    truth=list(struct.unpack_from('>243I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME)
    return truth,bound_blob(raw,refs,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    before=(frozen/SOURCE).read_text();source=proposed(before)
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17
    assert normalized_pools(base)==normalized_pools(obj)
    truth,raw=programs();blob,refs=payload(obj,NAME)
    report=dict(body_words=len(raw),retail_words=243,frame=(-raw[0])&65535,retail_frame=232,neighbors=17,real_word_differences=sum(a!=b for a,b in zip(truth,raw))+abs(len(truth)-len(raw)),raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),installed=False,c_match_credit=0)
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
