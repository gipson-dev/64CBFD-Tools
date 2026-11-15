"""Recover the complete state-19/20 callback without production installation."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-impact-phase-150c3994-match';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C3994'
ENTRY,ROM,SIZE=0x150C3994,0xF0E44,948
PREAMBLE='''extern f32 D_800A0334;
void func_151B9BF0(s32, s32, s16, s16, s16, s16, s16, s16,
                   s16, s16, s16, s16, s16, u32, u8, s32);
void func_15188810(u8 *, s32, s32);
void func_150C1660(f32, f32, f32, u8);
void func_1506AC8C(void *, s32, s32);
'''
BODY='''/* Advance the state-19/20 effect phase, motion and exit transition. */
void func_150C3994(u8 *actor) {
    if (*(s32 *)actor == 20) {
        if (*(s32 *)(actor + 0x2E4) == 0) {
            func_151B9BF0(47, 1,
                (s16)(s32)*(f32 *)(actor + 0x14),
                (s16)(s32)(*(f32 *)(actor + 0x18) + 30.0f),
                (s16)(s32)*(f32 *)(actor + 0x1C),
                2000, 1000, 400, 200, 3072, 3072, 1, 1, 0, 255, 0);
        } else {
            func_15188810(actor, 100, 0);
        }
    }
    if (*(f32 *)(actor + 0x20) < 0.0f &&
        20.0f < *(f32 *)(actor + 0x28) && actor[0x136] == 0 &&
        *(f32 *)(actor + 0x28) < -20.0f * *(f32 *)(actor + 0x20)) {
        func_10010630(0x92, (struct127 *)actor, 32000, 200, 2500);
        actor[0x136] = 1;
    }
    if (actor[0x83] == 0) {
        *(f32 *)(actor + 0x148) = 70.0f;
        if (*(s32 *)(actor + 0x2E4) == 0) {
            func_151B9BF0(47, 1,
                (s16)(s32)*(f32 *)(actor + 0x14),
                (s16)(s32)(*(f32 *)(actor + 0x18) + 30.0f),
                (s16)(s32)*(f32 *)(actor + 0x1C),
                2200, 1280, 800, 700, 3072, 3072, 20, 1, 0, 255, 0);
            func_150C1660(*(f32 *)(actor + 0x14),
                          *(f32 *)(actor + 0x18) + 30.0f,
                          *(f32 *)(actor + 0x1C), 255);
            func_1506AC8C(actor, 6, 0);
        } else {
            func_15188810(actor, 100, 0);
        }
        func_10010344(0x1A9, actor, 32767, 1000, 2000);
        actor[0xD0] = 1;
        *(u32 *)(actor + 0xF8) |= 0x01008000;
        *(f32 *)(actor + 0x114) = 500.0f;
    }
    actor[0x125] = 255;
    actor[0x83]++;
    if (actor[0x83] >= 11) {
        *(u32 *)(actor + 0xF8) &= 0xFFFF7FFF;
    }
    *(f32 *)(actor + 0x40) =
        (*(u16 *)(actor + 0x7A) + 16384) * 0.0054931640625f;
    func_15059140((struct127 *)actor);
    *(f32 *)(actor + 0xB8) += *(f32 *)(actor + 0x148);
    *(f32 *)(actor + 0x148) *= D_800A0334;
    if ((*(f32 *)(actor + 0x28) == 0.0f && actor[0x83] >= 21 &&
         *(s16 *)(actor + 0xCC) == 0) || actor[0x107] != 0 || actor[0x1CA] == 0) {
        func_150C3D5C(actor);
        func_10010630(0x93, (struct127 *)actor, 32000, 200, 2500);
        func_15060F28((struct127 *)actor, 1);
    }
}'''

def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C3994() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C3994();\n','')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C3994.s. */\n','')
    return result.rstrip()+'\n'

def symbols():
    return {n:int(n.split('_')[1],16) for n in ('D_800A0334','func_151B9BF0','func_15188810','func_10010630','func_150C1660','func_1506AC8C','func_10010344','func_15059140','func_150C3D5C','func_15060F28')}

def programs():
    truth=list(struct.unpack_from('>237I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME)
    return truth,bound_blob(raw,refs,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    before=(frozen/SOURCE).read_text();source=proposed(before)
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17 and normalized_pools(base)==normalized_pools(obj)
    subprocess.run([sys.executable,str(ROOT/'tools/check_motion_effect_150c2c00_pool.py'),str(obj)],cwd=ROOT,check=True)
    truth,raw=programs();blob,refs=payload(obj,NAME)
    report=dict(body_words=len(raw),retail_words=237,frame=(-raw[0])&65535,retail_frame=80,neighbors=17,
        raw_word_differences=sum(a!=b for a,b in zip(truth,raw))+abs(len(truth)-len(raw)),raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),installed=False,c_match_credit=0)
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
