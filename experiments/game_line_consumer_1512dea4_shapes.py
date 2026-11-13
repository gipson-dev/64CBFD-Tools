"""Compile private candidate shapes without replacing the production placeholder.

The candidate is intentionally not installable: the retail default kind reads
two incoming stack words, while these C locals are uninitialized in that case.
"""
from pathlib import Path
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

root=Path.cwd();out=root/'conker/build/game-line-consumer-1512dea4-screen';out.mkdir(parents=True,exist_ok=True)
source=(root/'conker/src/game_15B200.c').read_text();sha=lambda b:hashlib.sha256(b).hexdigest()
name='func_1512DEA4';target=list(struct.unpack_from('>166I',(root/'conker/conker.us.bin').read_bytes(),0x15b354))
declarations='''
typedef struct LINE_RECORD_ALIAS {
    u8 kind; u8 pad01[15]; f32 x,y,z,inverse,first,second,rate,damping;
    f32 rateVelocity,dampingVelocity,targetX,targetY,targetZ;
} LineMotion1512DEA4;
typedef struct LINE_RECORD_ALIAS { f32 x,y,z; } LineVelocity1512DEA4;
extern f32 D_800A3710, D_800A3714;
f32 sqrtf(f32);
void func_150495B0(f32 *, f32, f32 *, f32, f32, f32);
'''
function='''
/* Private experiment: the default case has unresolved incoming stack values. */
void func_1512DEA4(struct108 *camera) {
    f32 dx,dy,dz,distance;
    f32 offsetX,offsetZ,offsetY;
    LineMotion1512DEA4 *line;
    LineVelocity1512DEA4 *velocity;
    dx=camera->unk874-camera->unk2BC;
    dy=camera->unk878-camera->unk2C0;
    dz=camera->unk87C-camera->unk2C4;
    line=(LineMotion1512DEA4 *)&camera->unk870;
    distance=sqrtf(dx*dx+dy*dy+dz*dz);
    line->targetX=camera->unk874+line->x*distance;
    line->targetY=camera->unk878+line->y*distance;
    line->targetZ=camera->unk87C+line->z*distance;
    offsetY=line->second;
    switch (line->kind) {
    case 0: offsetX=line->first*line->z; offsetZ=line->first*-line->x; break;
    case 1: offsetX=line->first*-line->z; offsetZ=line->first*line->x; break;
    case 2: offsetX=line->first*line->x; offsetZ=line->first*line->z; break;
    case 3: offsetX=line->first*-line->x; offsetZ=line->first*-line->z; break;
    }
    line->targetX+=offsetX;line->targetY+=offsetY;line->targetZ+=offsetZ;
    if (camera->unk23C) {
        camera->unk2F8=line->targetX;camera->unk2FC=line->targetY;camera->unk300=line->targetZ;
        line->rate=40.0f;line->damping=40.0f;
    } else {
        velocity=(LineVelocity1512DEA4 *)((u8 *)camera+0x3c0);
        func_150495B0(&line->rate,10.0f,&line->rateVelocity,.6f,D_800A3710,camera->unk7B4);
        func_150495B0(&line->damping,10.0f,&line->dampingVelocity,.6f,D_800A3714,camera->unk7B4);
        func_150495B0(&camera->unk2F8,line->targetX,&velocity->x,line->rate,line->damping,camera->unk7B4);
        func_150495B0(&camera->unk2FC,line->targetY,&velocity->y,line->rate,line->damping,camera->unk7B4);
        func_150495B0(&camera->unk300,line->targetZ,&velocity->z,line->rate,line->damping,camera->unk7B4);
    }
}
'''
old=body(source,name);assert source.count(old)==1
prefix=source.replace('s32 func_1512DEA4();','void func_1512DEA4(struct108 *);')
prefix=prefix.replace('/* Non-matching C placeholders for asm/nonmatchings/game_15B200/func_1512DEA4.s. */','')
prefix=prefix.replace(old,declarations+'\n'+function)
baseline,bd=compile_owner(root,out,source,'before');results=[]
for variant in range(6):
    proposal=prefix
    if variant&1:proposal=proposal.replace('f32 offsetX,offsetZ,offsetY;','volatile f32 offsetX,offsetZ; f32 offsetY;')
    if variant&2:proposal=proposal.replace('dx=camera->unk874-camera->unk2BC;','line=(LineMotion1512DEA4 *)&camera->unk870;\n    dx=camera->unk874-camera->unk2BC;').replace('    line=(LineMotion1512DEA4 *)&camera->unk870;\n    distance=', '    distance=')
    if variant&4:proposal=proposal.replace('distance=sqrtf(dx*dx+dy*dy+dz*dz);','distance=sqrtf((dx*dx+dy*dy)+(dz*dz));')
    obj,diagnostics=compile_owner(root,out,proposal,f'shape-{variant:02d}')
    assert same_functions(baseline,obj,(name,))==1 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,name);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    symbols={'func_150495B0':0x150495b0,'D_800A3710':0x800a3710,'D_800A3714':0x800a3714}
    bound=bound_blob(raw,refs,symbols)
    result={'variant':variant,'words':len(words),'retail_words':len(target),'positional_differences':sum(a!=b for a,b in zip(bound,target))+abs(len(bound)-len(target)),
            'first_word':'0x%08X'%words[0],'relocations':sum(map(len,refs.values())),
            'diagnostics':diagnostics,'source_sha256':sha(proposal.encode()),'uninitialized_default_unqualified':True}
    results.append(result);print(result,flush=True)
assert (root/'conker/src/game_15B200.c').read_text()==source
(out/'shape-screen.json').write_text(json.dumps(results,indent=2)+'\n')
