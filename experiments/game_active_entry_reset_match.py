"""Whole-owner and literal linked-image gates for the direct reset loop."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_active_entry_reset_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
BUILD=candidate.BUILD
ELF,GUARDS,MAKE='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile'
ROM_IMAGE,LINKER='conker/conker.us.bin','conker/build/conker.ld'
BASELINE_SHA='c1252d3127415b7cf315d97adee1d1a3a03255f07d9b40417755c8132e3015ad'
GUARD_SHA='66ad0ff1fb837b102250469a08f2fa8f7e862bde40868b3b8f0357346ca8571b'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,refs,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=288 or sha(raw)!=t['raw_sha256']or refs!=t['bindings']:raise ValueError('Direct reset body/bindings changed')
    return raw,refs
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Reset guard baseline changed')
    return before
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze reset predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object']}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected reset input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded:
        b=dict(b);x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if(struct.unpack_from('>I',x[4])[0],struct.unpack_from('>I',raw)[0],struct.unpack_from('>I',x[4],8)[0],struct.unpack_from('>I',raw,8)[0])!=(0xA31FFFFE,0xA33FFFFE,0xFFFF5,0x3FFFF5):raise ValueError('Reset usage masks changed')
        raw[:4]=x[4][:4];raw[8:12]=x[4][8:12];b['.reginfo']=(*y[:4],bytes(raw),*y[5:])
    if a!=b:raise ValueError('Reset allocatable pools changed')
    aa,bb=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if aa is None and bb is None:return
    if aa is None or bb is None or aa[0][:4]+aa[0][5:]!=bb[0][:4]+bb[0][5:]:raise ValueError('Reset options shape changed')
    raw=bytearray(bb[1])
    if not padded:
        if(struct.unpack_from('>I',aa[1],8)[0],struct.unpack_from('>I',raw,8)[0],struct.unpack_from('>I',aa[1],16)[0],struct.unpack_from('>I',raw,16)[0])!=(0xA31FFFFE,0xA33FFFFE,0xFFFF5,0x3FFFF5):raise ValueError('Reset options masks changed')
        raw[8:12]=aa[1][8:12];raw[16:20]=aa[1][16:20]
    if aa[1]!=bytes(raw):raise ValueError('Reset options payload changed')
def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];d=out/label;d.mkdir(parents=True,exist_ok=True);src=d/'owner.s';dest=d/(t['owner']+'.c.o')
    src.write_text(pad_generated_object.emit_padded_assembly(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(dest),str(src)],cwd=root/'conker',capture_output=True,check=True)
    return dest
def link_image(root,out,owners,label):
    script=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,obj in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=obj.relative_to(root/'conker').as_posix()
        if script.count(old)!=1:raise ValueError('Reset linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Reset predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],288);expected[at:at+288]=rom[t['rom']:t['rom']+288]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Reset predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,288)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',((0x2DE86C,('D_800A9D40','D_800A6CB8'),(1,0)),)):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:raise ValueError('Literal reset full image differs')
    wanted=Counter((n,f[1],288 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Reset named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Reset predecessor source changed')
    guards=out/'unchanged-guards.csv';guards.write_bytes(guard_manifest((out/'match-frozen'/GUARDS).read_bytes()))
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(D_800A9D40=0x800A9D40,func_1513F680=0x1513F680,func_150ADA20=0x150ADA20,bzero=0x100226F0)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>72I',rom,t['rom'])):raise ValueError('Direct reset words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',guards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('Reset padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Reset live owner differs')
    oe=link_image(root,out,[oo],'reset-predecessor-image');ne=link_image(root,out,[no],'reset-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('Reset live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('Reset body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('Reset protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=72,frame=64,guards=0,bindings=5,raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
