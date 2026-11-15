"""Private shared particle-update recovery; no installation or match credit."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
NAME='func_15175958';ENTRY=0x15175958;ROM=0x1A2E08;SIZE=3844
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-particle-common-15175958-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
RAW_SHA256='3e8deef5b52b493afa4cbb2afb794341f4aae6cfa701184aea8df8a32bf78c54'
PRIMARY={'conker/asm/1A20A0.s': '82c15ef3cf40f643b350bfb70c2f8527cf870015b5db7325ab9f6508a0be1b92', 'conker/asm/data/24BC30.rodata.s': '7c48a3be051724c8c04dde83f9f3c541fe12ae0230a8d58d5945681347794273', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382'}
EXTRA='''typedef VertexWave1517725C ParticleConfig15175958;
extern f32 D_800A717C, D_800A7180, D_800A7184, D_800A7188, D_800A718C;
extern f32 D_800A7190, D_800A7194, D_800A7198, D_800A719C, D_800A71A0, D_800A71A4, D_800A71A8;
extern s32 D_800BE9F0, D_800C35B0, D_800D2138;
extern u8 D_800C35EA, D_800C35E8, D_800DDF60[];
extern f32 D_800D9B1C;
f32 func_150484A0(f32, f32);
f32 sqrtf(f32);
f32 fabsf(f32);
#pragma intrinsic (fabsf)
extern u8 D_800D9C50[];
s32 func_150490A8(struct17 *);
s32 func_1000F3D0(s32);
void func_1000F91C(s32, s32, s32, s32, s32, s32, s32, s32, s32, s32);
void func_10010F88(s32, s32, s16, s32, s32, s32, s32, s32, s32, s32);
'''
SELECTED='''/* Update a particle's fade, steering, motion, sound and visibility lifetime. */
void func_15175958(Particle15175390 *record) {
    f32 direction[3];
    f32 angles[3];
    f32 sineTilt, sineHeading, cosineTilt;
    f32 turnStep, difference, limit, value, rate, cosineHeading;
    u32 remainder;
    struct17 relative;
    u8 *surface;
    ParticleConfig15175958 *config;
    ModelRow15176B84 *models;
    s32 alpha;
    s32 soundRandom;
    f32 offsetZ, offsetX;
    s32 distance;
    s32 reverse;
    s32 angle;
    u32 surfaceFlags;
    s32 state;
    s32 variant;

    variant = record->variant;
    if (((ModelRow15176B84 *)D_800DDE80)[variant][0] == 0 ||
        D_800DDF78[variant] == 0) {
        func_1516972C(record);
        return;
    }
    alpha = record->stateF0;
    if ((variant == 8 || variant == 9) &&
        D_800BE9F0 == 6 && D_800C35EA != 0 && D_800C35E8 == 15) {
        record->flags &= 0xFFF7;
        if (D_800C35EA == 0 || D_800C35E8 != 15) {
            func_1516972C(record);
            return;
        }
        if (D_800C35B0 >= 60) {
            if (!(record->flags & 0x200)) {
                record->flags = (record->flags & 0xFFB3) | 0x200;
                offsetX = record->position[0] - D_800A717C;
                offsetZ = record->position[2] - D_800A7180;
                record->fieldB4 = D_800A7184 - func_150484A0(offsetX, offsetZ);
                record->angularRate = D_800A7188;
                record->fieldBC = sqrtf(offsetX * offsetX + offsetZ * offsetZ);
            }
        }
    }
    if (record->stateF1 == 0) {
        if ((record->flags & 8) && D_800DDF5C[record->slot] == 0) {
            record->stateF1 = 1;
        } else if (alpha != 255) {
            alpha = (s32)((u32)alpha + ((u32)D_800BE9E4 << 2));
            if (alpha >= 256) { alpha = 255; }
            record->stateF0 = alpha;
        }
        models = &((ModelRow15176B84 *)D_800DDE80)[record->variant];
    } else {
        if (alpha == 0) {
            func_1516972C(record);
            return;
        }
        alpha = (s32)((u32)alpha - ((u32)D_800BE9E4 << 2));
        if (alpha < 0) { alpha = 0; }
        record->stateF0 = alpha;
        models = &((ModelRow15176B84 *)D_800DDE80)[record->variant];
    }
    D_800DDF68[record->variant] = 1;
    config = &((ParticleConfig15175958 *)D_8008D0B0)[record->variant];
    if (record->sound != 0) {
        if (func_1000F3D0(record->sound) != 0) {
            func_1000F91C(record->sound, 0x7D00, 0, 0, 0,
                         (s32)record->position[0], (s32)record->position[1],
                         (s32)record->position[2], 1000, 4000);
        } else {
            record->sound = 0;
        }
    }
    if (record->flags & 4) {
        distance = func_150AD960((s32)record->position[0], (s32)record->position[2],
                                record->sourceX, record->sourceZ);
        reverse = 0;
        if ((record->flags & 0x10) && distance < record->innerRadius) {
            reverse = 1;
        }
        if (record->outerRadius < distance || reverse != 0) {
            relative.unk0 = record->sourceX - record->position[0];
            relative.unk8 = record->position[2] - record->sourceZ;
            angle = func_150490A8(&relative);
            if (reverse != 0) { angle = (s32)((u32)angle + 128U); }
            if (angle >= 256) { angle = (s32)((u32)angle - 256U); }
            record->fieldE0 = angle * 1.40625f;
            record->state91 = 3;
            record->fieldDC = config->turnTicks;
        }
        state = record->state91;
        if (state == 3) {
            turnStep = (f32)D_800BE9E4 * 0.5f;
            if (record->fieldE0 < record->heading) { turnStep = -turnStep; }
            difference = record->fieldE0 - record->heading;
            if (fabsf(difference) >= 180.0f) { turnStep = -turnStep; }
            if ((turnStep > 0.0f && record->angularRate < 0.0f) ||
                (turnStep < 0.0f && record->angularRate > 0.0f)) {
                record->state91 = 2;
                state = 2;
            } else {
                state = record->state91;
                record->angularRate += turnStep;
            }
        }
        if (state == 2) {
            if (record->angularRate != 0.0f) {
                if (record->angularRate > 0.0f) {
                    record->angularRate -= (f32)D_800BE9E4 * 0.5f;
                    if (record->angularRate < 0.0f) { record->angularRate = 0.0f; }
                } else {
                    record->angularRate += (f32)D_800BE9E4 * 0.5f;
                    if (record->angularRate > 0.0f) { record->angularRate = 0.0f; }
                }
            }
            record->fieldDC = (s32)((u32)(s32)record->fieldDC - (u32)D_800BE9E4);
            if (record->fieldDC <= 0) {
                record->fieldE0 = (u32)func_150ADA20() % 360U;
                record->state91 = 3;
                record->fieldDC = config->idleTicks;
            }
        }
        limit = config->turnLimit;
        if (limit < fabsf(record->angularRate)) {
            if (record->angularRate > 0.0f) { record->angularRate = limit; }
            else { record->angularRate = -limit; }
        }
    }
    if (record->flags & 0x80) {
        record->groundHeight = func_1510F8D8((s32)record->position[0],
            (s32)record->position[1], (s32)record->position[2], &surface);
        surfaceFlags = 0;
        if (surface != 0) {
            surfaceFlags = D_800DBE5C[(s32)((u32)surface - (u32)D_800DBE3C) / 12];
        }
        record->surfaceFlags = surfaceFlags;
    }
    if (record->flags & 0x40) {
        if (record->fieldDE >= 0) {
            record->fieldDE = (s32)((u32)(s32)record->fieldDE - (u32)D_800BE9E4);
            if (record->fieldDE <= 0) {
                record->fieldDE = -1;
                remainder = (u32)func_150ADA20();
                remainder %= (u32)record->verticalRange;
                value = (f32)(s32)remainder;
                if ((s32)remainder < 0) { value += 4294967296.0f; }
                value += record->sourceY;
                record->targetHeight = value;
                if (record->position[1] < value) { record->fieldB4 = -1.0f; }
                else { record->fieldB4 = 1.0f; }
            } else {
                if (record->tilt > 0.0f) { record->fieldB4 = -1.0f; }
                else if (record->tilt < 0.0f) { record->fieldB4 = 1.0f; }
            }
        } else {
            value = record->fieldB4;
            if ((value > 0.0f && record->position[1] < record->targetHeight) ||
                (value < 0.0f && record->targetHeight < record->position[1])) {
                record->fieldDE = 120;
                record->fieldB4 = -value;
            }
        }
    }
    if (!(record->flags & 0x200)) {
        record->tilt += record->fieldB4;
        limit = config->tiltLimit;
        value = record->tilt;
        if (value < -limit) { record->tilt = -limit; }
        else if (limit < value) { record->tilt = limit; }
        else { record->tilt = value; }
        rate = record->angularRate;
        if (D_800A718C < fabsf(rate)) {
            record->heading += rate;
            value = record->heading;
            if (value < 0.0f) { record->heading = value + 360.0f; }
            else if (value >= 360.0f) { record->heading = value - 360.0f; }
            if (!(record->flags & 0x20)) {
                value = -record->angularRate;
                record->fieldBC = value;
                record->fieldB0 += value;
                limit = config->bankLimit;
                value = record->fieldB0;
                if (value < -limit) { record->fieldB0 = -limit; }
                else if (limit < value) { record->fieldB0 = limit; }
                else { record->fieldB0 = value; }
            }
        } else {
            if (record->fieldB0 > 0.0f) { record->fieldBC = -1.0f; }
            else if (record->fieldB0 < 0.0f) { record->fieldBC = 1.0f; }
            record->fieldB0 += record->fieldBC;
            if (fabsf(record->fieldB0) < D_800A718C) { record->fieldB0 = 0.0f; }
        }
        record->lifetime += record->mode;
        if (record->lifetime < config->minimumSpeed) { record->lifetime = config->minimumSpeed; }
        else {
            record->lifetime = record->lifetime > config->maximumSpeed ? config->maximumSpeed : record->lifetime;
        }
    }
    if (!(record->flags & 1)) {
        if (record->tilt >= 0.0f) {
            if ((*models)[1] == record->model && config->wave < config->switchLimit &&
                -config->switchLimit < config->wave) { record->model = (*models)[2]; }
        } else {
            if ((*models)[2] == record->model && config->wave < config->switchLimit &&
                -config->switchLimit < config->wave) { record->model = (*models)[1]; }
        }
    }
    if (record->flags & 0x200) {
        limit = D_800A7190;
        rate = record->angularRate;
        value = (f32)D_800BE9E4;
        record->fieldB4 += rate * value;
        record->angularRate = rate + D_800A7194;
        if (limit < record->angularRate) { record->angularRate = limit; }
        record->fieldBC -= D_800A7198 * value;
        if (record->fieldBC < 60.0f) { record->fieldBC = 60.0f; }
        sineTilt = func_150AD78C(record->fieldB4);
        value = func_150AD780(record->fieldB4);
        record->position[0] = record->fieldBC * value + D_800A719C;
        record->position[2] = record->fieldBC * sineTilt + D_800A71A0;
        record->position[1] -= 100.0f / ((record->fieldBC - 60.0f) + 4.0f);
        if (record->position[1] < D_800A71A4 || D_800C35EA == 0 || D_800C35E8 != 15) {
            func_1516972C(record);
            return;
        }
    } else {
        value = D_800A71A8;
        angles[0] = record->tilt * value;
        angles[1] = record->heading * value;
        angles[2] = record->fieldB0 * value;
        sineTilt = func_150AD78C(angles[0]);
        sineHeading = func_150AD78C(angles[1]);
        cosineTilt = func_150AD780(angles[0]);
        cosineHeading = func_150AD780(angles[1]);
        direction[0] = cosineTilt * sineHeading;
        direction[1] = -sineTilt;
        direction[2] = cosineTilt * cosineHeading;
        rate = (f32)(s32)((u32)(s32)record->lifetime * (u32)D_800BE9E4);
        record->position[0] += direction[0] * rate;
        record->position[1] += direction[1] * rate;
        record->position[2] += direction[2] * rate;
    }
    if (((u8 *)record)[0] == 19 && D_800DDF60[record->slot] == 0) {
        soundRandom = func_150ADA20() & 127;
        func_10010F88(16, 0x7FFF, (s16)soundRandom, 0, 0,
                     (s32)record->position[0], (s32)record->position[1],
                     (s32)record->position[2], 500, 4000);
        soundRandom = func_150ADA20() & 63;
        D_800DDF60[record->slot] = soundRandom + 30;
    }
    if ((record->flags & 2) &&
        func_1510AEE0(D_800D9C10, record->position[0], record->position[1], record->position[2],
                     D_800D9B20, D_800D9B1C, D_800D35E0, D_800D35E4, 0, 0) &&
        (D_800D2138 != 1 ||
         func_1510AEE0(D_800D9C50, record->position[0], record->position[1], record->position[2],
                      D_800D9B20, D_800D9B1C, D_800D35E0, D_800D35E4, 0, 0))) {
        func_1516972C(record);
    }
}'''

def proposed(before):
    assert body(before,NAME)=='s32 func_15175958() {\n    return 0;\n}'
    old='    u8 retained00[0x18];\n    f32 wave, speed, retained20, phase, amplitude, retained2C, outerRadius, innerRadius;'
    new='    u8 maximumSpeed, minimumSpeed, idleTicks, turnTicks;\n    f32 bankLimit, tiltLimit, retained0C, turnLimit, retained14;\n    f32 wave, speed, switchLimit, phase, amplitude, retained2C, outerRadius, innerRadius;'
    assert before.count(old)==1
    result=before.replace(old,new).replace(body(before,NAME),SELECTED);pos=result.index('/* Recovered routine')
    return result[:pos]+EXTRA+'\n'+result[pos:]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for p,expected in PRIMARY.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,p
    before=(ROOT/SOURCE).read_text();old,d=compile_owner(ROOT,OUT,before,'baseline');assert d==''
    obj,d=compile_owner(ROOT,OUT,proposed(before),'selected');assert d==''
    raw,refs=payload(obj,NAME);w=bound(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>961I',rom,ROM))
    assert len(w)==956 and (-w[0]&65535)==0xC8 and hashlib.sha256(raw).hexdigest()==RAW_SHA256
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((ENTRY>>2)&0x3ffffff)
    callers=[i*4 for i,x in enumerate(allwords)if x==jal];pointers=[i*4 for i,x in enumerate(allwords)if x==ENTRY]
    assert callers==[0x1A3FA8,0x1A4008,0x1A4284] and pointers==[0x230170,0x230378,0x230D38,0x230D6C]
    report=dict(words=956,retail_words=961,differences=sum(a!=b for a,b in zip(w,truth))+abs(len(w)-961),frame=200,retail_frame=200,raw_sha256=RAW_SHA256,binding_sites=len(refs),neighbors=8,direct_callers=callers,registry_pointers=pointers,private=True,exact_credit=0)
    (OUT/'screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
