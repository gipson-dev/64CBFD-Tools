"""Complete private exit-effect recovery, including the retained cartridge check."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-exit-150c3d5c-private';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C3D5C'
ENTRY,ROM,SIZE=0x150C3D5C,0xF120C,960
PREAMBLE='''extern f32 D_800A0338;
s32 func_151EF040(s32, s32);
void func_15171200(s32, s32, f32, f32, f32, f32, f32, f32,
                   f32, s32, s32, f32, u8, s32);
/* The current spray implementation accepts full-width coordinate words. */
void func_151709B4(s32, s32, s32, s32, f32, u8, s32);
void func_1516D99C(
    s16, s16, s16, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8,
    u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8,
    s16, s16, s16, s16, u16, u8, u8, u8, u8, s16, u16, u16,
    u8, u8, u8, u8, u8, s32, u8, u8, s32, s32);
struct225 *func_151602C0(Header *, Header2 *, s32, s32, s32, s32,
                         u8, u8, s32, u8, s32);
'''
BODY='''/* Submit the actor's exit effects and preserve the retail cartridge check. */
void func_150C3D5C(u8 *actor) {
    s32 cartridgeWord;
    Header descriptor;
    Header2 position;
    s32 (*readWord)(s32, s32) = func_151EF040;

    func_151B9BF0(47, 1,
        (s16)(s32)*(f32 *)(actor + 0x14),
        (s16)(s32)*(f32 *)(actor + 0x18),
        (s16)(s32)*(f32 *)(actor + 0x1C),
        1400, 1280, 800, 1200, 512, 512, 30, 1, 0, 255, 0);

    cartridgeWord = 0xC23459B8;
    readWord(func_150C3D48(cartridgeWord), (s32)&cartridgeWord);
    if (cartridgeWord != 0x0330C820) {
        /* Retail disables this entrypoint when the cartridge word differs. */
        ((u32 *)&func_10004074)[0] = 0x03E00008;
        ((u32 *)&func_10004074)[1] = 0;
    }
    func_15171200(3, 203, *(f32 *)(actor + 0x14),
        *(f32 *)(actor + 0x18), *(f32 *)(actor + 0x1C),
        10.0f, 1.0f, 2.0f, 60.0f, 3, 60, D_800A0338, 255, 0);
    func_151709B4((s32)*(f32 *)(actor + 0x14),
        (s32)(*(f32 *)(actor + 0x18) + 20.0f),
        (s32)*(f32 *)(actor + 0x1C), 10, 2000.0f, 255, 0);
    func_1516D99C(
        (s16)(s32)*(f32 *)(actor + 0x14),
        (s16)(s32)*(f32 *)(actor + 0x18),
        (s16)(s32)*(f32 *)(actor + 0x1C),
        13, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 255, 0, 0, 0,
        20, 20, 2, 0, 0, 0, 0, 81, 81, 81, 81, 10, 1, 0, 255,
        10, 1400, 400, 1, 1, 0, 1, 0, 0, 0, 0, 0, 255, 0);
    descriptor.unk0 = 3;
    descriptor.unk1 = -1;
    descriptor.unk2 = (u32)func_150ADA20() % 11U + 10;
    descriptor.unk4 = 0;
    position.unk0 = (s32)*(f32 *)(actor + 0x14);
    position.unk4 = (s32)*(f32 *)(actor + 0x18);
    position.unk8 = (s32)*(f32 *)(actor + 0x1C);
    func_151602C0(&descriptor, &position, (u32)func_150ADA20() % 52U + 40,
                  255, 255, 90, 255, 0, 0, 255, 1);
}'''

def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C3D5C() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C3D5C();','void func_150C3D5C(u8 *);')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C3D5C.s. */\n','')
    return result.rstrip()+'\n'

def symbols():
    return {n:int(n.split('_')[1],16) for n in ('D_800A0338','func_151B9BF0','func_150C3D48','func_151EF040','func_10004074','func_15171200','func_151709B4','func_1516D99C','func_150ADA20','func_151602C0')}

def programs():
    truth=list(struct.unpack_from('>240I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME)
    return truth,bound_blob(raw,refs,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for n,h in record['inputs'].items():assert sha(ROOT/n)==h,n
    before=(frozen/SOURCE).read_text();source=proposed(before)
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17 and normalized_pools(base)==normalized_pools(obj)
    subprocess.run([sys.executable,str(ROOT/'tools/check_motion_effect_150c2c00_pool.py'),str(obj)],cwd=ROOT,check=True)
    truth,raw=programs();blob,refs=payload(obj,NAME)
    report=dict(body_words=len(raw),retail_body_words=240,retail_slot_words=241,frame=(-raw[0])&65535,retail_frame=256,neighbors=17,
        raw_word_differences=sum(a!=b for a,b in zip(truth,raw))+abs(len(truth)-len(raw)),raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),installed=False,c_match_credit=0)
    for n,h in record['inputs'].items():assert sha(ROOT/n)==h,n
    (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
