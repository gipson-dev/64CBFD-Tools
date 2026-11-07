"""Direct SDK body, unchanged guard history and zero-exclusion full image."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_combiner_state_1513f4e4_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
BUILD=candidate.BUILD
ELF,GUARDS,MAKE='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile'
ROM_IMAGE,LINKER='conker/conker.us.bin','conker/build/conker.ld'
BASELINE_SHA='aa952c7bda6ac273beebf2bc9deda8231bbd13e7964e5fa7f77752d98293f88f'
# New uses change GNU's encounter order for these two adjacent name pairs.
# Predict both complete symbol entries and their contiguous name strings;
# no byte range is excluded and each named definition must stay identical.
METADATA_GROUPS=((2790108,('D_800DD1BE','D_800AB1CC'),(1,0)),
                 (2853436,('D_800A4BA8','D_8009BBC0'),(1,0)))
GUARD_SHA='7d1ab46c6a902544af9086d2e3a0b1cabe5e0e467ba1c3f06be39b6f50d4fb9a'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,refs,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=412 or sha(raw)!=t['raw_sha256']or refs!=t['bindings']:raise ValueError('Direct combiner words/bindings changed')
    return raw,dict(refs)

def guard_rows():return []

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Combiner guard history changed')
    return before

def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after)
    if a!=b:raise ValueError('Combiner state inherited diagnostics changed')
    return dict(before=sum(a.values()),after=sum(b.values()),new=[])
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze combiner-state predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object'],GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected combiner-state input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if a!=b:raise ValueError('Combiner state allocatable pools or register metadata changed')
    aa=dependent_sections(before.read_bytes());bb=dependent_sections(after.read_bytes())
    x,y=aa.get('.options'),bb.get('.options')
    if (x is None)!=(y is None)or(x is not None and(x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]or x[1]!=y[1])):raise ValueError('Combiner state options metadata changed')
    if padded and a.get('.reginfo',[None]*5)[4]!=bytes(24):raise ValueError('Padded register masks changed')

def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];d=out/label;d.mkdir(parents=True,exist_ok=True);src=d/'owner.s';dest=d/(t['owner']+'.c.o')
    import sys
    sys.modules.setdefault('pad_generated_object',pad_generated_object)
    from tools import pad_c_object
    src.write_text(pad_c_object.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',t['owner'],rodata_symbol='jtbl_800A5188_game',word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(dest),str(src)],cwd=root/'conker',capture_output=True,check=True)
    return dest
def link_image(root,out,owners,label):
    script=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,obj in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=obj.relative_to(root/'conker').as_posix()
        if script.count(old)!=1:raise ValueError('Combiner state linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Combiner state predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],412);expected[at:at+412]=rom[t['rom']:t['rom']+412]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Combiner state predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,412)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',METADATA_GROUPS):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        remaining=[i for i,(x,y)in enumerate(zip(expected,after))if x!=y]
        raise ValueError('Literal combiner-state full image differs: '+repr((len(remaining),remaining[:48])))
    wanted=Counter((n,f[1],412 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Combiner state named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Combiner state predecessor source changed')
    oldguards=out/'predecessor-guards.csv';oldguards.write_bytes((out/'match-frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(oldguards.read_bytes()))
    if(root/GUARDS).read_bytes()!=(guards if installed else oldguards).read_bytes():raise ValueError('Live combiner-state guards differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(func_15143044=0x15143044,D_800DD1BE=0x800DD1BE,D_800A4BA8=0x800A4BA8)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>103I',rom,t['rom'])):raise ValueError('Direct combiner-state words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',oldguards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('Combiner state padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Combiner state live owner differs')
    oe=link_image(root,out,[oo],'combiner-state-predecessor-image');ne=link_image(root,out,[no],'combiner-state-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('Combiner state live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('Combiner state body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('Combiner state protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=103,frame=24,guards=len(guard_rows()),bindings=len(t['bindings']),raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
