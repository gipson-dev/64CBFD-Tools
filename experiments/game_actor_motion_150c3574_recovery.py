"""Private semantic recovery of the state-24 actor movement/sound callback.

No production source, guard, or conversion credit is changed by this screen.
"""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-motion-150c3574-private';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C3574'
ENTRY,ROM,SIZE=0x150C3574,0xF0A24,1056
PREAMBLE='''extern f32 D_800A0320, D_800A0324, D_800A0328;
extern f32 D_800A032C, D_800A0330;
void func_1505A250(f32, f32, f32, f32 *, f32 *);
void func_1505A3A8(f32, void *, f32, f32, u8);
void func_15056B08(void *);
void func_150562FC(void *);
void func_150599C8(void *, s32, u16);
void func_1001091C(struct127 *, s32);
f32 sqrtf(f32);
'''
BODY='''/* Update the state-24 actor's movement, facing, animation and loop sound. */
void func_150C3574(u8 *actor) {
    f32 deceleration = 0.25f;
    f32 animationScale = 0.5f;
    f32 speed;
    u16 heading;
    s32 currentHeading;
    s32 volume;

    actor[0x80] = 10;
    if (actor[4] == 0x25) {
        func_1505A250(0.0f, 0.0f, 0.15f,
                     (f32 *)(actor + 0x164), (f32 *)(actor + 0x168));
        deceleration = D_800A0320;
        if (actor[0x87] & 1) {
            *(s16 *)(actor + 0x224) = (s32)*(f32 *)(actor + 0x18);
        }
        *(s16 *)(actor + 0x160) = 0;
    }
    func_1505A3A8(0.0f, actor, 2.0f, deceleration, 0);
    *(f32 *)(actor + 0x24) = 3.0f;
    if (actor[4] == 0x10) {
        animationScale = 0.375f;
    }
    if (actor[4] == 0xAC) {
        animationScale = 1.5f;
    }
    animationScale *= 0.75f;
    func_15056B08(actor);
    if (actor[0x13D] != 0) {
        func_150562FC(actor);
    }
    func_15059140((struct127 *)actor);
    *(f32 *)(actor + 0xBC) =
        (*(f32 *)(actor + 0x14) - *(f32 *)(actor + 0x2C)) * D_800BE9A8;
    *(f32 *)(actor + 0x148) =
        (*(f32 *)(actor + 0x1C) - *(f32 *)(actor + 0x34)) * D_800BE9A8;
    speed = sqrtf(*(f32 *)(actor + 0xBC) * *(f32 *)(actor + 0xBC) +
                  *(f32 *)(actor + 0x148) * *(f32 *)(actor + 0x148));
    if ((speed + 4.0f) + (speed + 4.0f) < *(f32 *)(actor + 0x3C)) {
        *(f32 *)(actor + 0x3C) = speed + speed;
    }
    if (actor[0x87] == 4) {
        D_800D1580 = 0xFF020133;
        D_800D154C = D_800CC2D0;
        func_1506E8D8();
        D_800D154C = (struct127 *)actor;
        *(f32 *)(actor + 0x164) = *(f32 *)(actor + 0xBC);
        *(f32 *)(actor + 0x168) = *(f32 *)(actor + 0x148);
        *(f32 *)(actor + 0x3C) = 0.0f;
    }
    actor[0x87] <<= 1;
    if (0.5f < speed && actor[0x13D] == 0) {
        *(u16 *)(actor + 0x78) = func_1505A630(
            *(f32 *)(actor + 0x14) - *(f32 *)(actor + 0x2C),
            *(f32 *)(actor + 0x34) - *(f32 *)(actor + 0x1C), 0);
    }
    currentHeading = *(u16 *)(actor + 0x78);
    if ((*(u16 *)(actor + 0x7A) - currentHeading - 0x4000) & 0x8000) {
        heading = currentHeading;
    } else {
        heading = currentHeading ^ 0x8000;
    }
    func_150599C8(actor, 2, heading);
    if (30.0f < *(f32 *)(actor + 0x28)) {
        *(f32 *)(actor + 0x44) *= D_800A0324;
    } else {
        *(f32 *)(actor + 0x44) = speed + speed;
    }
    if (actor[0x13D] != 0) {
        *(f32 *)(actor + 0x44) = 0.0f;
    }
    func_15052490((struct127 *)actor, *(u16 *)(actor + 0x78),
                  *(f32 *)(actor + 0x44),
                  (2.0f - *(f32 *)(actor + 0x14C)) * animationScale);
    if (*(f32 *)(actor + 0x44) < D_800A0328) {
        func_100109D0((struct127 *)actor);
    } else if (func_100107F8((struct127 *)actor) == 0) {
        if (actor[4] == 0xAC) {
            D_800D1580 = 0x630;
        } else if (actor[4] == 0x25) {
            D_800D1580 = 0x67A;
        } else {
            D_800D1580 = 0x62A;
        }
        func_1506E5FC();
    } else {
        volume = (s32)(*(f32 *)(actor + 0x44) * D_800A032C);
        if (volume > 28000) {
            volume = 28000;
        }
        if (actor[4] == 0x25) {
            volume >>= 1;
        }
        func_1001091C((struct127 *)actor, volume);
    }
    if (*(f32 *)(actor + 0x44) < D_800A0330) {
        func_100109D0((struct127 *)actor);
    }
}'''

def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C3574() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C3574();\n','')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C3574.s. */\n','')
    return result.rstrip()+'\n'

def symbols():
    return {name:int(name.split('_')[1],16) for name in
        ('D_800A0320','D_800A0324','D_800A0328','D_800A032C','D_800A0330',
         'D_800BE9A8','D_800D1580','D_800D154C','D_800CC2D0',
         'func_1505A250','func_1505A3A8','func_15056B08','func_150562FC',
         'func_15059140','func_1506E8D8','func_1505A630','func_150599C8',
         'func_15052490','func_100109D0','func_100107F8','func_1506E5FC','func_1001091C')}

def programs():
    truth=list(struct.unpack_from('>264I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME)
    return truth,bound_blob(raw,refs,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    before=(frozen/SOURCE).read_text();source=proposed(before)
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered')
    assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17
    assert normalized_pools(base)==normalized_pools(obj)
    subprocess.run(['python3','tools/check_motion_effect_150c2c00_pool.py',str(obj)],cwd=ROOT,check=True)
    truth,raw=programs();blob,refs=payload(obj,NAME)
    report=dict(body_words=len(raw),retail_words=264,frame=(-raw[0])&65535,retail_frame=56,
        neighbors=17,real_word_differences=sum(a!=b for a,b in zip(truth,raw))+abs(len(truth)-len(raw)),
        raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),
        prior_pool_guard=True,installed=False,c_match_credit=0)
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
