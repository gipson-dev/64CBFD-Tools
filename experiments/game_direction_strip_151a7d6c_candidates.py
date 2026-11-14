"""Private semantic screen for the polyline strip renderer; never installs code.

Matching remains incomplete. Equal body length/frame and bounded model cases
are evidence for this candidate, not production exact-match credit.
"""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
FUNCTION='func_151A7D6C'
ENTRY,ROM,WORDS,FRAME=0x151A7D6C,0x1D521C,373,0xC8
BUILD='conker/build/game-direction-strip-151a7d6c-screen'
SOURCE='conker/src/game/generated_1D4E00.c'
DECLARATIONS = """typedef struct {
    u8 pad00[18];
    s16 count;
    u8 pad14[8];
    u8 flags, pad1D[7];
    u8 color[4];
    f32 width;
    u8 pad2C[56];
    DirectionVertex151A7A90 *vertices;
    f32 timer;
    u8 cache[16];
    s32 bytes;
} DirectionStripState151A7D6C;
extern u8 D_80090D70[];
extern u32 D_800D2C9C, D_800A4AC8[];
void func_151D5D60(void *, s16, s32, Vtx **, u8 *);
struct17 *func_15144B34(s32);
Gfx *func_15142E24(Gfx *, void *, s32, s32, s32, s32, s32, u8, u8 *, u8 *, s32);
Gfx *func_15142B7C(Gfx *, u32, u32);
Gfx *func_15142C10(Gfx *, s32, s32, s32, s32, u8 *);
Gfx *func_1513F4E4(Gfx *, u8, u8 *);
Gfx *func_15142FBC(Gfx *, u32, u32, u8 *);
void func_15145548(struct17 *, struct17 *, struct17 *, struct17 *, f32 *);
f32 sqrtf(f32);
"""
SELECTED = """/* Render the active polyline as camera-facing textured quads. */
Gfx *func_151A7D6C(Gfx *output, DirectionStripState151A7D6C *state, s16 view) {
    Vtx *cursor;
    struct17 delta, closest, ray;

    struct17 *camera;
    f32 magnitude;
    u8 sync;
    s16 last;
    f32 parameter;
    f32 offsetX, offsetY, offsetZ, scale;
    s16 first, next;
    DirectionStripState151A7D6C *loopOwner;
    struct17 *left, *right;
    loopOwner = state;
    if (state->flags & 2) {
        func_151D5D60(state->cache, view, state->bytes, &cursor, NULL);
        if (cursor != NULL) {
            camera = func_15144B34(view);
            sync = 1;
            last = state->count - 1;
            first = 0;
            next = 1;
            output = func_15142E24(output, D_80090D70, 0, 0, 0, 0, 0x2C, 0, NULL, &sync, 3);
            output = func_15142B7C(output, 0x200005, 0x1F0600);
            output = func_15142C10(output, state->color[0], state->color[1], state->color[2], state->color[3], &sync);
            output = func_1513F4E4(output, 0x19, &sync);
            output = func_15142FBC(output, D_800D2C9C | 0x80000 | 0x2CA0, D_800A4AC8[7] | D_800A4AC8[6], &sync);
            delta.unk0 = state->vertices[0].outX - state->vertices[last].outX;
            delta.unk4 = state->vertices[0].outY - state->vertices[last].outY;
            delta.unk8 = state->vertices[0].outZ - state->vertices[last].outZ;
            func_15145548((struct17 *)&state->vertices[last].outX, &delta, camera, &closest, &parameter);
            ray.unk0 = camera->unk0 - closest.unk0;
            ray.unk4 = camera->unk4 - closest.unk4;
            ray.unk8 = camera->unk8 - closest.unk8;
            offsetX = delta.unk4 * ray.unk8 - ray.unk4 * delta.unk8;
            offsetY = delta.unk8 * ray.unk0 - ray.unk8 * delta.unk0;
            offsetZ = delta.unk0 * ray.unk4 - ray.unk0 * delta.unk4;
            magnitude = offsetX * offsetX + offsetY * offsetY + offsetZ * offsetZ;
            if (magnitude == 0.0f) {
                offsetX = 0.0f; offsetY = 0.0f; offsetZ = 0.0f;
            } else {
                scale = state->width / sqrtf(magnitude);
                offsetX = offsetX * scale;
                offsetY = offsetY * scale;
                offsetZ = offsetZ * scale;
            }
            if (state->count >= 2) {
                do {
                    right = (struct17 *)&state->vertices[next].outX;
                    left = (struct17 *)&state->vertices[first].outX;
                    cursor->v.ob[0] = (s32)(left->unk0 + offsetX);
                    cursor->v.ob[1] = (s32)(left->unk4 + offsetY);
                    cursor->v.ob[2] = (s32)(left->unk8 + offsetZ);
                    cursor->v.tc[0] = 0;
                    cursor->v.tc[1] = 0;
                    cursor->v.cn[0] = 255;
                    cursor->v.cn[1] = 255;
                    cursor->v.cn[2] = 255;
                    cursor->v.cn[3] = 255;
                    cursor->v.flag = 0;
                    cursor++;
                    cursor->v.ob[0] = (s32)(left->unk0 - offsetX);
                    cursor->v.ob[1] = (s32)(left->unk4 - offsetY);
                    cursor->v.ob[2] = (s32)(left->unk8 - offsetZ);
                    cursor->v.tc[0] = 960;
                    cursor->v.tc[1] = 0;
                    cursor->v.cn[0] = 255;
                    cursor->v.cn[1] = 255;
                    cursor->v.cn[2] = 255;
                    cursor->v.cn[3] = 255;
                    cursor->v.flag = 0;
                    cursor++;
                    cursor->v.ob[0] = (s32)(right->unk0 - offsetX);
                    cursor->v.ob[1] = (s32)(right->unk4 - offsetY);
                    cursor->v.ob[2] = (s32)(right->unk8 - offsetZ);
                    cursor->v.tc[0] = 960;
                    cursor->v.tc[1] = 960;
                    cursor->v.cn[0] = 255;
                    cursor->v.cn[1] = 255;
                    cursor->v.cn[2] = 255;
                    cursor->v.cn[3] = 255;
                    cursor->v.flag = 0;
                    cursor++;
                    cursor->v.ob[0] = (s32)(right->unk0 + offsetX);
                    cursor->v.ob[1] = (s32)(right->unk4 + offsetY);
                    cursor->v.ob[2] = (s32)(right->unk8 + offsetZ);
                    cursor->v.tc[0] = 0;
                    cursor->v.tc[1] = 960;
                    cursor->v.cn[0] = 255;
                    cursor->v.cn[1] = 255;
                    cursor->v.cn[2] = 255;
                    cursor->v.cn[3] = 255;
                    cursor->v.flag = 0;
                    cursor++;
                    next++;
                    gSPVertex(output++, cursor - 4, 4, 0);
                    { Gfx *command = output++; gSP1Triangle(command, 0, 1, 2, 0); }
                    gSP1Triangle(output++, 0, 2, 3, 0);
                    first++;
                } while (next < loopOwner->count);
            }
        }
    }
    return output;
}
"""
PLACEHOLDER='s32 func_151A7D6C() {\n    return 0;\n}'
def proposed(source):
    if source.count(PLACEHOLDER)!=1:raise ValueError('Unrecognized strip-renderer source state')
    return source.replace(PLACEHOLDER,DECLARATIONS+SELECTED.rstrip())
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    source=(root/SOURCE).read_text();before,_=compile_owner(root,out,source,'baseline');after,diagnostics=compile_owner(root,out,proposed(source),'selected')
    assert not diagnostics
    symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
    raw,refs=payload(after,FUNCTION);words=bound_blob(raw,refs,symbols);truth=struct.unpack_from('>373I',(root/'conker/conker.us.bin').read_bytes(),ROM)
    assert len(words)==WORDS and (-words[0])&65535==FRAME
    neighbors=same_functions(before,after,(FUNCTION,));assert neighbors==22 and normalized_pools(before)==normalized_pools(after)
    report=dict(function=FUNCTION,words=len(words),frame=FRAME,exact_words=sum(a==b for a,b in zip(words,truth)),different_words=sum(a!=b for a,b in zip(words,truth)),neighbors=neighbors,pools_unchanged=True,raw_sha256=hashlib.sha256(raw).hexdigest(),bindings={str(k):v for k,v in refs.items()},source_sha256=hashlib.sha256((out/'selected.c').read_bytes()).hexdigest(),installed=False,credited=False)
    (out/'selected-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
