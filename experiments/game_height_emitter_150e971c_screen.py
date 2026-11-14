"""Reproduce the uncredited height-emitter compiler and descriptor screen."""
from pathlib import Path
import hashlib, json, os, struct, subprocess, sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-height-emitter-150e971c-durable'
out.mkdir(parents=True,exist_ok=True)
expected={
 'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
 'conker/build/conker.us.elf':'2efc0f036d1106ada19a8fc43da944c462029547123c1b249976dfa79cc02e33',
 'conker/src/game/generated_113D60.c':'24deeca424e3f22a18257161663db090a6d4ad2efac0631f333d0e23dd229cef',
 'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
}
for name,digest in expected.items():
 data=(root/name).read_bytes()
 if name.endswith('.c'):data=data.replace(b'\r\n',b'\n')
 if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('screen input changed: '+name)
path=root/'conker/src/game/generated_113D60.c'
owner=path.read_text()
old='s32 func_150E971C() {\n    return 0;\n}'
assert owner.count(old)==1
decl='''typedef struct HeightEmissionDescriptor113D60 {
    u32 flags; s16 lifetime; u8 kind, field07;
    u32 field08, field0c; u8 field10, field11, field12, field13, field14, field15;
    u8 field16, field17; u32 resource; u8 untouched1c[6];
    s16 field22, field24; u8 untouched26[2];
} HeightEmissionDescriptor113D60;
s32 func_151337C0(u8 *);
struct210 *func_1513C73C(s32, u8, u8, s32, f32, f32, f32, f32, f32,
                         u8, u8, s32, u8, s32);
'''
body='''s32 func_150E971C(u8 *actor) {
    HeightEmissionDescriptor113D60 descriptor;
    f32 range;
    u8 *state;
    s32 random;
    func_151337C0(actor);
    state = actor + 0x170;
    if (*(f32 *)(actor + 0x3C) < *(f32 *)state) {
        if ((*(u32 *)(state + 4) & 31) == 10) {
            range = func_150ADA68() * 20.0f + 20.0f;
            descriptor.kind = 11; descriptor.flags = 0x9701; descriptor.lifetime = 100;
            descriptor.field07 = 0; descriptor.field08 = 0; descriptor.field0c = 0;
            descriptor.field10 = 255; descriptor.field11 = 255; descriptor.field12 = 255;
            descriptor.field13 = 255; descriptor.field14 = 255; descriptor.field15 = 255;
            descriptor.resource = 0x3B0003; descriptor.field16 = 0; descriptor.field17 = 7;
            descriptor.field22 = 20; descriptor.field24 = 12;
            random = func_150ADA20();
            func_1513C73C((s32)&descriptor, 0, 0, (s32)(state + 8),
                *(f32 *)(actor + 0x38), *(f32 *)state + 5.0f,
                *(f32 *)(actor + 0x40), range, range, (u8)random, 0, 0,
                actor[0x0c], actor[1]);
        }
        return 0;
    }
    return 1;
}'''
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
truth=struct.unpack_from('>91I',(root/'conker/conker.us.bin').read_bytes(),0x116bcc)
base,bd=compile_owner(root,out,owner,'baseline')
candidate=body.replace('    s32 random;\n','').replace('            random = func_150ADA20();\n','').replace('(u8)random', '(func_150ADA20() & 255)')
rows={}
padded_decl=decl.replace('u8 untouched26[2];', 'u8 untouched26[2]; u8 scratch28[4];')
snapshot=body.replace('(u8)random', '(random & 255)')
for name,declaration,implementation in (('plain',decl,candidate),('padded',padded_decl,candidate),('snapshot',padded_decl,snapshot)):
    obj,diag=compile_owner(root,out,owner.replace(old,declaration+implementation),name)
    ws=bound_blob(*payload(obj,'func_150E971C'),symbols)
    row={'words':len(ws),'same_positions':sum(a==b for a,b in zip(ws,truth)),
         'neighbors':same_functions(base,obj,('func_150E971C',)),
         'pools_equal':normalized_pools(base)==normalized_pools(obj),'diagnostics':diag}
    if row!={'words':91,'same_positions':71 if name=='plain' else 67,'neighbors':28,'pools_equal':True,'diagnostics':bd}:
        raise ValueError((name,row))
    rows[name]=row
(out/'screen.json').write_text(json.dumps(rows,indent=2)+'\n')
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_guard_screen'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_connected_screen'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_model_screen'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_caller_screen'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_native_screen'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_image_screen'],cwd=root,env=env,check=True)
print(json.dumps(rows),flush=True)
