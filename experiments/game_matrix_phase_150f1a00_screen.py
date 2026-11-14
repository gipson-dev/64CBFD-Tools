"""Reproduce an uncredited C screen for the actor matrix phase update."""
import hashlib,os,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-matrix-phase-150f1a00-durable'
INPUTS={
 'conker/src/game/generated_11C2B0.c':'37f3f4a73144495de6a277b93bf8a148b70d9a2603b0d6a3c7f18598ff378b05',
 'conker/asm/11C2B0.s':'064851c4bd1d09f2eec8dc0b3bbfa579b8e028d24e94c8ce4468d5a1732403db',
 'conker/asm/61490.s':'cef63d34c187a6a3058da2f4253076b7b0c48625e03195c2fee4801dd32e9f53',
 'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
 'conker/include/structs.h':'0103b809787d88d65a2262cf619aaf537bb85cea25bd2aca5c312f2db28eafde',
 'conker/include/variables.h':'3cd24cd9fea98901536137649368536fbbd56018cac571b6476701802c1bc00c',
 'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
}
OLD='s32 func_150F1A00() {\n    return 0;\n}'
NEW='''typedef struct { u16 values[3]; } PhaseRates;
extern PhaseRates D_80088B00;
extern s16 D_800CC298[];
extern s32 D_800BE9E4;
extern f32 D_800A18E8, D_800A18EC, D_800A18F0;
f32 cosf(f32);
void func_150F1A00(u8 *actor) {
    PhaseRates rates = D_80088B00;
    s32 kind = 0;
    u32 flags = *(u32 *)(actor + 0x2e4);
    f32 *matrix;
    f32 scale;
    int row, col;
    if ((flags & 3) == 3) kind = 1;
    if ((flags & 12) == 12) kind = 2;
    D_800CC298[10] = (s16)((u32)(s32)D_800CC298[10] + (u32)rates.values[kind] * (u32)D_800BE9E4);
    scale = ((cosf((f32)D_800CC298[10] * D_800A18E8) + 1.0f) * 0.5f * D_800A18EC) + D_800A18F0;
    matrix = (f32 *)(*(u32 *)(actor + 0x1d4) + 0xf80);
    for (row = 0; row < 3; row++) { for (col = 0; col < 3; col++) matrix[row * 4 + col] *= scale; }
}'''

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,digest in INPUTS.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Screen input changed: '+name)
    source=(ROOT/'conker/src/game/generated_11C2B0.c').read_text()
    assert source.count(OLD)==1
    before,bd=compile_owner(ROOT,OUT,source,'before')
    after,ad=compile_owner(ROOT,OUT,source.replace(OLD,NEW),'candidate')
    if bd or ad or same_functions(before,after,('func_150F1A00',))!=43 or normalized_pools(before)!=normalized_pools(after):
        raise ValueError('Candidate changed neighbor, pool or diagnostic')
    symbols={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
    assert symbols['cosf']==0x15047c00
    code=bound_blob(*payload(after,'func_150F1A00'),symbols)
    rom=struct.unpack_from('>82I',(ROOT/'conker/conker.us.bin').read_bytes(),0x11eeb0)
    assert len(code)==82 and sum(a==b for a,b in zip(code,rom))==18
    return source,after

def compile_control(source,name,old,new):
    assert NEW.count(old)==1
    modified=NEW.replace(old,new);assert modified!=NEW
    obj,diagnostics=compile_owner(ROOT,OUT,source.replace(OLD,modified),'control-'+name)
    if diagnostics:raise ValueError(diagnostics)
    return obj
