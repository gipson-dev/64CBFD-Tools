"""Reproduce an uncredited C screen for the actor matrix phase update."""
import csv,hashlib,io,json,os,re,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-matrix-phase-150f1a00-durable'
INPUTS={
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
/* Advance the shared phase and scale the actor's three matrix axes. */
void func_150F1A00(u8 *actor) {
    PhaseRates rates = D_80088B00;
    s32 kind = 0;
    u32 flags = *(u32 *)(actor + 0x2e4);
    f32 *matrix;
    f32 scale;
    u32 row, col;
    if ((flags & 3) == 3) kind = 1;
    if ((flags & 12) == 12) kind = 2;
    D_800CC298[10] = (s16)((u32)(s32)D_800CC298[10] + (u32)rates.values[kind] * (u32)D_800BE9E4);
    scale = ((cosf((f32)D_800CC298[10] * D_800A18E8) + 1.0f) * 0.5f * D_800A18EC) + D_800A18F0;
    matrix = (f32 *)(*(u32 *)(actor + 0x1d4) + 0xf80);
    for (row = 0; row < 3; row++) { for (col = 0; col < 3; col++) matrix[col] *= scale; matrix += 4; }
}'''
MANIFEST=json.loads(Path(__file__).with_name('game_matrix_phase_150f1a00_manifest.json').read_text())
sha=lambda text:hashlib.sha256(text.encode()).hexdigest()

def versions():
    result={};states=[]
    assert MANIFEST['source']['old']==OLD and MANIFEST['source']['new']==NEW
    for name in ('source','caller'):
        item=MANIFEST[name];text=(ROOT/item['path']).read_text()
        if sha(text)==item['before_sha256']:before=text;installed=False
        elif sha(text)==item['after_sha256']:
            assert text.count(item['new'])==1
            before=text.replace(item['new'],item['old']);installed=True
        else:raise ValueError('Unknown '+name+' state')
        assert sha(before)==item['before_sha256'] and before.count(item['old'])==1
        after=before.replace(item['old'],item['new']);assert sha(after)==item['after_sha256']
        result[name]=(before,after);states.append(installed)
    assert len(set(states))==1
    installed=states[0];item=MANIFEST['guards'];text=(ROOT/item['path']).read_text()
    if installed:
        assert text.endswith(item['append']);before=text[:-len(item['append'])];after=text
    else:before=text;after=text+item['append']
    assert sha(before)==item['before_sha256'] and sha(after)==item['after_sha256']
    result['guards']=(before,after)
    return result,installed

def assemble(text,label):
    asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
    args=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
    result=subprocess.run(args,cwd=ROOT/'conker',capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr)
    return obj

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,digest in INPUTS.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Screen input changed: '+name)
    texts,installed=versions();source=texts['source'][0]
    for path,digest in MANIFEST['baseline'].items():
        dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            if installed or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Pre-install baseline missing: '+path)
            shutil.copyfile(ROOT/path,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:raise ValueError('Frozen baseline changed: '+path)
    before,bd=compile_owner(ROOT,OUT,source,'before')
    after,ad=compile_owner(ROOT,OUT,texts['source'][1],'candidate')
    if bd or ad or same_functions(before,after,('func_150F1A00',))!=43 or normalized_pools(before)!=normalized_pools(after):
        raise ValueError('Candidate changed neighbor, pool or diagnostic')
    symbols={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
    assert symbols['cosf']==0x15047c00
    code=bound_blob(*payload(after,'func_150F1A00'),symbols)
    rom=struct.unpack_from('>82I',(ROOT/'conker/conker.us.bin').read_bytes(),0x11eeb0)
    assert len(code)==82 and sum(a==b for a,b in zip(code,rom))==58
    ca,cd=compile_owner(ROOT,OUT,texts['caller'][0],'caller-before');cb,ce=compile_owner(ROOT,OUT,texts['caller'][1],'caller-after')
    assert not cd and not ce and same_functions(ca,cb)==10 and normalized_pools(ca)==normalized_pools(cb)
    (OUT/'caller-after.c').write_text(texts['caller'][1]);(OUT/'private-guards.csv').write_text(texts['guards'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
    (OUT/'guard-rows.json').write_text(json.dumps(MANIFEST['guard_rows'],indent=2)+'\n')
    old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
    assert new[:len(old)]==old and new[len(old):]==MANIFEST['guard_rows'] and len(new)-len(old)==24
    asm=(ROOT/'conker/asm/11C2B0.s').read_text();match=re.search(r'^glabel func_150F1A00\n.*?^endlabel func_150F1A00\s*$',asm,re.M|re.S);assert match
    assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size func_150F1A00,.-func_150F1A00\n','retail')
    for kind in ('generated','c'):
        if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/11C2B0.s',filename='generated_11C2B0',word_patches_path=OUT/'proposed-guards.csv')
        else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt','generated_11C2B0',word_patches_path=OUT/'proposed-guards.csv')
        padded=assemble(text,kind+'-guarded')
        assert bound_blob(*payload(padded,'func_150F1A00'),symbols)==list(rom)
        assert same_functions(ROOT/'conker/build/src/game/generated_11C2B0.c.o',padded,('func_150F1A00',))==43
    return source,after

def compile_control(source,name,old,new):
    assert NEW.count(old)==1
    modified=NEW.replace(old,new);assert modified!=NEW
    obj,diagnostics=compile_owner(ROOT,OUT,source.replace(OLD,modified),'control-'+name)
    if diagnostics:raise ValueError(diagnostics)
    return obj
