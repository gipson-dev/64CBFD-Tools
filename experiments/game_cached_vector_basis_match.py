"""Direct cached vector preparation and complete owner/image audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_cached_vector_basis_candidates as candidate
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
OBJECT='conker/build/src/game/generated_17CAF0.c.o'
ASM='conker/asm/17CAF0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='37445089783b40e86d03888ca71642b0ff1e9ddc8499c57119049e707f6ebc27'
GUARD_SHA='9892912f5423eb5e518da147fb0bf7e358de56260cb3d59e6b2e6d1bcff0c4ab'
RAW_SHA='679b33b7cc68b7ce017a43195dd39d33fcb7532d6b3bb3832f4dbccbf068f221'
METADATA_GROUPS=()
BINDINGS={40: [('R_MIPS_26', 'func_15145128')], 136: [('R_MIPS_26', 'func_15146078')], 196: [('R_MIPS_26', 'func_15145128')], 228: [('R_MIPS_26', 'func_15145128')]}

def derive(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Complete cached basis body/bindings changed')
    return raw,dict(bindings)

def guard_manifest(before,raw,bindings):
    derive(raw,bindings)
    if sha(before)!=GUARD_SHA:raise ValueError('Cached basis guards changed')
    if any(r['function']==FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Direct cached basis acquired guards')
    return before


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Cached basis discovery changed: '+n)
        names=set(initial)|{'conker/asm/nonmatchings/game_16EE20/func_15145128.s','conker/asm/nonmatchings/game_16EE20/func_15146078.s','conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Cached basis protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Cached basis include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Cached basis predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Cached basis predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # This recovery changes no symbol/string ordering. Keep the serializer's
    # empty-cycle check and compare the complete image without exclusions.
    named={n:p for p,n,f,loc in symbol_rows(before)}
    groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:raise ValueError('Cached basis literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Cached basis definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    diagnostics=paired_diagnostics(od,nd,FILENAME)
    if(diagnostics['before'],diagnostics['after'])!=(0,0):raise ValueError('Cached basis diagnostic baseline changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,));a,b=alloc_pools(old),alloc_pools(new)
    if a!=b:raise ValueError('Basis raw allocatable pools/register metadata changed')
    x,y=(dependent_sections(p.read_bytes())['.options']for p in(old,new))
    if x[1]!=y[1]or x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]:raise ValueError('Basis raw options payload or section shape changed')
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized,moved=derive(raw,bindings)
    symbols={n:int(n.split('_')[1],16)for values in bindings.values()for _,n in values}
    if bound_blob(normalized,moved,symbols)!=list(struct.unpack('>72I',truth)):raise ValueError('Cached basis normalized body differs')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Cached basis source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live cached basis owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Padded cached basis pools/register metadata changed')
    if function_blob(no)!=(normalized,moved):raise ValueError('Cached basis actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'basis-predecessor-image');ne=harness.link_image(root,out,no,'basis-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Cached basis live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Cached basis complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Cached basis protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,raw_words=72,words=72,frame=32,slot_words=72,alignment_words=0,guards=0,inserted_words=0,bindings=4,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_and_padded_pools_register_metadata_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
