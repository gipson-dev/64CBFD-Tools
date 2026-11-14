"""Private compiler screen for an actor motion/crossing callback."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-crossing-150e6230-durable';out.mkdir(parents=True,exist_ok=True)
expected={'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
 'conker/build/conker.us.elf':'058f88114ae93f5fa9a271c240f4c0be1afcf68769fd51e3cb646c977cbde195',
 'conker/src/game/generated_113480.c':'38f102940a9460082650870ffa9efc5a754c26e390e562a67555dfd8dd02311e',
 'conker/build/src/game/generated_113480.c.o':'6d4daef0bee91dcf093a42fc0746ef3afb82aef023a8458225429fc678079432',
 'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a'}
for name,digest in expected.items():
 data=(root/name).read_bytes()
 if name.endswith('.c'):data=data.replace(b'\r\n',b'\n')
 if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('screen input changed: '+name)
path=root/'conker/src/game/generated_113480.c';owner=path.read_text();old='s32 func_150E6230() {\n    return 0;\n}';assert owner.count(old)==1
decl='''extern f32 D_800BE9A4;
extern s32 (*D_80088A10[])(u8 *);
f32 func_15144A74(f32 *, f32 *);
'''
body='''s32 func_150E6230(u8 *actor) {
    u8 *state = actor + 0x110;
    f32 delta[3];
    f32 speed, vx, vy, vz, sign;
    s8 result = 1;
    if (state[0] & 1) {
        delta[0] = *(f32 *)(state + 4) - *(f32 *)(actor + 0x34);
        delta[1] = *(f32 *)(state + 8) - *(f32 *)(actor + 0x38);
        delta[2] = *(f32 *)(state + 12) - *(f32 *)(actor + 0x3C);
        sign = func_15144A74(delta, (f32 *)(state + 4)) < 0.0f ? -1.0f : 1.0f;
        if (sign != *(f32 *)(state + 0x28)) {
            s8 selector = *(s8 *)(state + 0x2C);
            result = 0;
            if (selector != -1) result = (s8)D_80088A10[selector](actor);
        }
    }
    speed = *(f32 *)(actor + 0x50);
    vx = *(f32 *)(actor + 0x40) * speed;
    vy = *(f32 *)(actor + 0x44) * speed;
    vz = *(f32 *)(actor + 0x48) * speed;
    *(f32 *)(actor + 0x34) += vx * D_800BE9A4;
    *(f32 *)(actor + 0x38) += vy * D_800BE9A4;
    *(f32 *)(actor + 0x3C) += vz * D_800BE9A4;
    return result;
}'''
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
truth=struct.unpack_from('>92I',(root/'conker/conker.us.bin').read_bytes(),0x1136e0)
base,bd=compile_owner(root,out,owner,'baseline')
formatted=body.replace('s32 func_150E6230(u8 *actor) {','/* Advance motion and dispatch the configured crossing effect when its sign changes. */\ns32 func_150E6230(u8 *actor) {')
formatted=formatted.replace('            if (selector != -1) result = (s8)D_80088A10[selector](actor);','            if (selector != -1) {\n                result = (s8)D_80088A10[selector](actor);\n            }')
obj,diag=compile_owner(root,out,owner.replace(old,decl+formatted),'formatted')
ws=bound_blob(*payload(obj,'func_150E6230'),symbols)
assert len(ws)==90 and sum(a==b for a,b in zip(ws,truth))==50 and same_functions(base,obj,('func_150E6230',))==4 and normalized_pools(base)==normalized_pools(obj) and diag==bd==''
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('guard','guest','connected','caller','native','padder','fault','overlap','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_motion_crossing_150e6230_'+name],cwd=root,env=env,check=True)
print('motion crossing: 90 compiler words, 50 retail positions; complete private checks passed',flush=True)
