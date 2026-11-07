"""Closed matrix/points lifetimes and a strict complete-image gate."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_vertex_callback_1513e83c_candidates as candidate
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
BASELINE_SHA='635e1081b99cac777e9be8fd50f4ceede6f224d3c2de0d3a8b0cf24ddb9912fc'
METADATA_GROUPS=()
GUARD_SHA='3cac0eb5aeb58c3d77c9a52374a6707ff9bc3c8d426b8f1f1e135ead4847f776'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,refs,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=668 or sha(raw)!=t['raw_sha256']or refs!=t['bindings']:raise ValueError('Vertex words/bindings changed')
    w=list(struct.unpack('>167I',raw))
    expected={40:0xC624002C,43:0xC624002C,44:0x27B30098,45:0x02602025,78:0x27B2005C,79:0x2414000C,117:0x02602025,119:0x02498821}
    for i,v in expected.items():
        if w[i]!=v or i*4 in refs:raise ValueError('Closed vertex lifetime changed')
    # On either successful edge, compute the matrix address before the sole
    # common width read. No call/store intervenes. Rename matrix S3->S2 and
    # points S2->S3 after the last view/copy use, before both are restored.
    # The point-base and stride definitions commute before MULTU consumes them.
    for i,v in {40:0x27B20098,43:0x27B20098,44:0xC624002C,45:0x02402025,78:0x2414000C,79:0x27B3005C,117:0x02402025,119:0x02698821}.items():w[i]=v
    return struct.pack('>167I',*w),dict(refs)

def guard_rows():
    raw=candidate.RAW;normal,refs=derive(raw,candidate.TARGETS[0]['bindings']);rows=[]
    for i,(a,b)in enumerate(zip(struct.unpack('>167I',raw),struct.unpack('>167I',normal))):
        if a!=b:rows.append(['game_169510','func_1513E83C','0x%03X'%(i*4),'0x%08X'%a,'0x%08X'%b,'-','-','Normalize closed matrix/points roles and independent address schedule','','','false'])
    if len(rows)!=8:raise ValueError('Vertex guard count changed')
    return rows

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Vertex guard history changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows());return before+stream.getvalue().encode()

def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after)
    if a!=b:raise ValueError('Record vertex inherited diagnostics changed')
    return dict(before=sum(a.values()),after=sum(b.values()),new=[])
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze record-vertex predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object'],GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected record-vertex input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if a!=b:raise ValueError('Record vertex allocatable pools or register metadata changed')
    aa=dependent_sections(before.read_bytes());bb=dependent_sections(after.read_bytes())
    x,y=aa.get('.options'),bb.get('.options')
    if (x is None)!=(y is None)or(x is not None and(x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]or x[1]!=y[1])):raise ValueError('Record vertex options metadata changed')
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
        if script.count(old)!=1:raise ValueError('Record vertex linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Record vertex predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],668);expected[at:at+668]=rom[t['rom']:t['rom']+668]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Record vertex predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,668)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',METADATA_GROUPS):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        remaining=[i for i,(x,y)in enumerate(zip(expected,after))if x!=y]
        raise ValueError('Literal record-vertex full image differs: '+repr((len(remaining),remaining[:48])))
    wanted=Counter((n,f[1],668 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Record vertex named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Record vertex predecessor source changed')
    oldguards=out/'predecessor-guards.csv';oldguards.write_bytes((out/'match-frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(oldguards.read_bytes()))
    if(root/GUARDS).read_bytes()!=(guards if installed else oldguards).read_bytes():raise ValueError('Live record-vertex guards differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(func_151D5D60=0x151D5D60,memcpy=0x10022EC0,func_150A8050=0x150A8050,func_150A7960=0x150A7960)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>167I',rom,t['rom'])):raise ValueError('Direct record-vertex words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',oldguards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('Record vertex padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Record vertex live owner differs')
    oe=link_image(root,out,[oo],'record-vertex-predecessor-image');ne=link_image(root,out,[no],'record-vertex-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('Record vertex live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('Record vertex body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('Record vertex protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=167,frame=216,guards=len(guard_rows()),bindings=len(t['bindings']),raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
