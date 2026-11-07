"""Direct damped-record update and complete owner/image audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_damped_record_lifetime_candidates as candidate
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
OBJECT='conker/build/src/game/generated_1B1600.c.o'
ASM='conker/asm/1B1600.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='de1aad0c43aae018edc66254bc066e44e2b8bd9b7bf5eb2c72167e3076714bb4'
GUARD_SHA='72ad5715645cd16dfcfedaba1dd530570e9a3eaa07c8746f81ce20a2d908ef7d'
RAW_SHA='22253030de69d1b45b55c059d9a9fecf96bd75df83399579b651986a619deb94'
METADATA_GROUPS=()
BINDINGS={16:[('R_MIPS_HI16','D_800BE9E4')],20:[('R_MIPS_LO16','D_800BE9E4')],36:[('R_MIPS_26','func_10004074')],44:[('R_MIPS_26','func_1516972C')]}

def derive(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Complete damped record body/bindings changed')
    return raw,dict(bindings)

def guard_manifest(before,raw,bindings):
    derive(raw,bindings)
    if sha(before)!=GUARD_SHA:raise ValueError('Damped record guards changed')
    if any(r['function']==FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Direct damped record acquired guards')
    return before


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def audit_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after);changed=[]
    if a!=b:
        x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if struct.unpack_from('>I',x[4],0)[0]!=0xA37FFBFE or struct.unpack_from('>I',raw,0)[0]!=0xA37FFFFE:raise ValueError('Foreign damped GPR mask change')
        struct.pack_into('>I',raw,0,0xA37FFBFE);b['.reginfo']=(*y[:4],bytes(raw),*y[5:]);changed.append('T2 mask 0xA37FFBFE to 0xA37FFFFE')
        if a!=b:raise ValueError('Damped allocatable pools changed beyond the T2 mask')
    x,y=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if x is not None or y is not None:
        if x is None or y is None or x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]:raise ValueError('Damped options section shape changed')
        raw=bytearray(y[1])
        if x[1]!=y[1]:
            if struct.unpack_from('>I',x[1],8)[0]!=0xA37FFBFE or struct.unpack_from('>I',raw,8)[0]!=0xA37FFFFE:raise ValueError('Damped options GPR mask changed')
            struct.pack_into('>I',raw,8,0xA37FFBFE)
        if x[1]!=bytes(raw):raise ValueError('Damped options changed beyond T2')
    return changed


def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Damped record discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Damped record protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Damped record include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Damped record predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Damped record predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # This recovery changes no symbol/string ordering. Keep the serializer's
    # empty-cycle check and compare the complete image without exclusions.
    named={n:p for p,n,f,loc in symbol_rows(before)}
    groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:raise ValueError('Damped record literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Damped record definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'));mb,ma,mi=candidate.make_states((root/MAKE).read_text(encoding='utf-8'))
    if mi!=installed or mb!=(out/'match-frozen'/MAKE).read_text(encoding='utf-8'):raise ValueError('Damped source/profile phases differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor',flags=('-O2','-g3'));new,nd=candidate.compile_owner(root,out,after,'match-qualified',flags=candidate.FLAGS)
    profile_old,pd=candidate.compile_owner(root,out,before,'match-profile-predecessor',flags=candidate.FLAGS)
    if pd or same_functions(old,profile_old,())!=32:raise ValueError('Damped predecessor profile affected another body')
    default_new,dd=candidate.compile_owner(root,out,after,'match-unrolled-control',flags=('-O2','-g3'))
    if dd or len(function_blob(default_new)[0])!=440 or same_functions(old,default_new,(FUNCTION,))!=31:raise ValueError('Damped unroll control changed')
    diagnostics=paired_diagnostics(od,nd,FILENAME)
    if(diagnostics['before'],diagnostics['after'])!=(0,0):raise ValueError('Damped record diagnostic baseline changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,));raw_metadata=audit_pools(old,new)
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized,moved=derive(raw,bindings)
    symbols={n:int(n.split('_')[1],16)for values in bindings.values()for _,n in values}
    if bound_blob(normalized,moved,symbols)!=list(struct.unpack('>72I',truth)):raise ValueError('Damped record normalized body differs')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Damped record source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live damped record owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    padded_metadata=audit_pools(oo,no)
    if function_blob(no)!=(normalized,moved):raise ValueError('Damped record actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'damping-predecessor-image');ne=harness.link_image(root,out,no,'damping-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Damped record live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Damped record complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Damped record protected data differs')
    (out/'proposed-owner.c').write_text(after,encoding='utf-8');(out/'proposed-Makefile').write_text(ma,encoding='utf-8')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,raw_words=72,words=72,frame=24,slot_words=72,alignment_words=0,guards=0,inserted_words=0,bindings=4,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_metadata_changes=raw_metadata,padded_metadata_changes=padded_metadata,other_pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,profile_predecessor_functions_fixed=32,default_profile_unrolled_words=110,compiler_profile=list(candidate.FLAGS),protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
