"""Direct 68-byte point-effect descriptor, original frame and strict ELF audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_selected_point_effect_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_actor_height_effect_match as metadata
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
SIZE=288
OBJECT='conker/build/src/game/generated_173D40.c.o'
ASM='conker/asm/173D40.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='9dca25bb40d84489fcddaf9a2c74f425b835610143b3059fd1d23526eb85b8b2'
GUARD_SHA='9892912f5423eb5e518da147fb0bf7e358de56260cb3d59e6b2e6d1bcff0c4ab'
RAW_SHA='d9589bfe950bb4bf969c41060fe2f79c72c657e15b3090f412eb53e72167a547'
METADATA_GROUPS=(
    (('D_800A571C','D_80097E7C'),(1,0)),
    (('D_800A5708','D_800A1408'),(1,0)),
    (('D_800A5714','.L15025120_game_data'),(1,0)),
    (('func_10001000','D_8009E4A8'),(1,0)),
    (('D_800A5710','func_15017930','D_8009CF10'),(1,2,0)),
    (('D_800A570C','D_800A140C'),(1,0)),
)
BINDINGS={48: [('R_MIPS_26', 'func_15146890')], 124: [('R_MIPS_HI16', 'D_800A5708')], 128: [('R_MIPS_LO16', 'D_800A5708')], 132: [('R_MIPS_HI16', 'D_800A570C')], 136: [('R_MIPS_LO16', 'D_800A570C')], 156: [('R_MIPS_HI16', 'D_800A5710')], 160: [('R_MIPS_LO16', 'D_800A5710')], 164: [('R_MIPS_HI16', 'D_800A5714')], 168: [('R_MIPS_LO16', 'D_800A5714')], 172: [('R_MIPS_HI16', 'D_800A5718')], 180: [('R_MIPS_LO16', 'D_800A5718')], 184: [('R_MIPS_HI16', 'D_800A571C')], 192: [('R_MIPS_LO16', 'D_800A571C')], 264: [('R_MIPS_26', 'func_15150F90')]}

def derive(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Complete point descriptor body/bindings changed')
    return raw,dict(bindings)

def guard_manifest(before,raw,bindings):
    derive(raw,bindings)
    if sha(before)!=GUARD_SHA:raise ValueError('Point descriptor guards changed')
    if any(r['function']==FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Direct point descriptor acquired guards')
    return before


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Point descriptor discovery changed: '+n)
        names=set(initial)|{'conker/asm/data/24A190.rodata.s','conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Point descriptor protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Point descriptor include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Point descriptor predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Point descriptor predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # New constant references reorder six bounded GNU symbol/string buckets.
    # Serialize only frozen BEFORE definitions in the measured closed cycles;
    # retain the complete image and all named definitions without exclusions.
    named={n:p for p,n,f,loc in symbol_rows(before)}
    groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:raise ValueError('Point descriptor literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Point descriptor definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    diagnostics=paired_diagnostics(od,nd,FILENAME)
    if(diagnostics['before'],diagnostics['after'])!=(0,0):raise ValueError('Point descriptor diagnostic baseline changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,));a,b=alloc_pools(old),alloc_pools(new)
    if set(a)!=set(b)or[n for n in a if a[n]!=b[n]]!=['.reginfo']:raise ValueError('Point descriptor raw loaded pool delta is not closed')
    x,y=a['.reginfo'],b['.reginfo']
    if x[:4]!=y[:4]or x[5:]!=y[5:]:raise ValueError('Point descriptor raw register section shape changed')
    x,y=(struct.unpack('>6I',v[4])for v in(x,y))
    if x[1:]!=y[1:]or(x[0],y[0])!=(0xA301CFFE,0xA301FFFE):raise ValueError('Only recovered T4/T5 use may enter the raw mask')
    x,y=(dependent_sections(p.read_bytes())['.options'][1]for p in(old,new))
    if x[:8]!=y[:8]or x[12:]!=y[12:]or(x[8:12].hex(),y[8:12].hex())!=('a301cffe','a301fffe'):raise ValueError('Point descriptor raw options differ beyond T4/T5')
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized,moved=derive(raw,bindings)
    symbols={n:int(n.split('_')[1],16)for values in bindings.values()for _,n in values}
    if bound_blob(normalized,moved,symbols)!=list(struct.unpack('>72I',truth)):raise ValueError('Point descriptor normalized body differs')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Point descriptor source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live point descriptor owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Padded point descriptor pools/register metadata changed')
    if function_blob(no)!=(normalized,moved):raise ValueError('Point descriptor actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'descriptor-predecessor-image');ne=harness.link_image(root,out,no,'descriptor-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Point descriptor live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Point descriptor complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Point descriptor protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,raw_words=72,words=72,frame=104,slot_words=72,alignment_words=0,guards=0,inserted_words=0,bindings=14,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_GPR_before='0xa301cffe',raw_GPR_after='0xa301fffe',only_raw_T4_T5_mask_added=True,other_raw_and_all_padded_pools_register_metadata_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
