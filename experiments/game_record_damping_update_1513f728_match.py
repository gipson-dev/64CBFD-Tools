"""Proved loop-exit scheduling, explicit binding moves and strict full-image gates."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_damping_update_1513f728_candidates as candidate
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
BASELINE_SHA='dcbf32c646a456f9018e2f426b44409d324ff50182ef2c3f0ea89a425aaf3876'
METADATA_GROUPS=()
GUARD_SHA='89060a24e81fd2df17749fc4379c55c983002fd7b4485ec97da47cd5a5ed5e47'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
# Closed source-index permutation of post-loop instructions. This moves no
# memory access across a store. Float operation grouping and operand roles stay
# fixed. The only duplicated instruction is an integer constant definition.
POST_LOOP_ORDER=(125,120,128,121,123,122,124,129,126,127,*range(131,173),174,173,175,130)

def derive(raw,refs,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=772 or sha(raw)!=t['raw_sha256']or refs!=t['bindings']:raise ValueError('Damping words/bindings changed')
    w=list(struct.unpack('>193I',raw));original=w[:]
    if (w[11],w[40],w[41],w[125],w[128],w[130])!=(0x1040006C,0x1040004F,0,0x3C013F00,0x44819000,0x24020001):raise ValueError('Damping exit/constant/return shape changed')
    if sorted(POST_LOOP_ORDER)!=list(range(120,176)):raise ValueError('Damping permutation not closed')
    for word in w[42:120]:
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        if op not in(0,4,5,9,17,49,57)or rs==1 or(op==0 and word!=0)or(op in(4,5,9)and rt==1):raise ValueError('AT is live on the loop fallthrough')
    # Initial zero and the main loop fall through 120. Exhausted remainder
    # takes BEQL to121 after its LUI delay slot; the nonzero edge annuls it.
    # Neither fallthrough loop reads AT before the idempotent LUI at120.
    # Each exit defines AT before MTC1; F18's old damping value is then dead.
    # Moving return1 to175 crosses no V0 use after the count has reached zero.
    w[40]=0x50400050;w[41]=original[125]
    w[120:176]=[original[i]for i in POST_LOOP_ORDER]
    nr={p:list(r)for p,r in refs.items()if not 480<=p<704}
    for dst,src in enumerate(POST_LOOP_ORDER,120):
        if src*4 in refs:nr[dst*4]=list(refs[src*4])
    if len(nr)!=len(refs):raise ValueError('Damping binding census changed')
    return struct.pack('>193I',*w),nr

def guard_rows():
    refs=candidate.TARGETS[0]['bindings'];raw=candidate.RAW;normal,nr=derive(raw,refs);rows=[]
    spec=lambda r:';'.join(k+':'+n for k,n in r)or'-'
    for i,(a,b)in enumerate(zip(struct.unpack('>193I',raw),struct.unpack('>193I',normal))):
        er,new=refs.get(i*4,[]),nr.get(i*4,[])
        if a!=b or er!=new:rows.append(['game_169510','func_1513F728','0x%03X'%(i*4),'0x%08X'%a,'0x%08X'%b,spec(er),spec(new),'Normalize proved damping loop-exit constant and independent post-loop schedule','','','false'])
    if len(rows)!=57:raise ValueError('Damping guard count changed')
    return rows

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Damping guard history changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows());return before+stream.getvalue().encode()

def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after)
    if a!=b:raise ValueError('Record damping inherited diagnostics changed')
    return dict(before=sum(a.values()),after=sum(b.values()),new=[])
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze record-damping predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object'],GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected record-damping input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if a!=b:raise ValueError('Record damping allocatable pools or register metadata changed')
    aa=dependent_sections(before.read_bytes());bb=dependent_sections(after.read_bytes())
    x,y=aa.get('.options'),bb.get('.options')
    if (x is None)!=(y is None)or(x is not None and(x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]or x[1]!=y[1])):raise ValueError('Record damping options metadata changed')
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
        if script.count(old)!=1:raise ValueError('Record damping linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Record damping predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],772);expected[at:at+772]=rom[t['rom']:t['rom']+772]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Record damping predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,772)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',METADATA_GROUPS):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        remaining=[i for i,(x,y)in enumerate(zip(expected,after))if x!=y]
        raise ValueError('Literal record-damping full image differs: '+repr((len(remaining),remaining[:48])))
    wanted=Counter((n,f[1],772 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Record damping named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Record damping predecessor source changed')
    oldguards=out/'predecessor-guards.csv';oldguards.write_bytes((out/'match-frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(oldguards.read_bytes()))
    if(root/GUARDS).read_bytes()!=(guards if installed else oldguards).read_bytes():raise ValueError('Live record-damping guards differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(D_800BE9E4=0x800BE9E4,D_800BE9A4=0x800BE9A4,D_800BE9A8=0x800BE9A8)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>193I',rom,t['rom'])):raise ValueError('Direct record-damping words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',oldguards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('Record damping padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Record damping live owner differs')
    oe=link_image(root,out,[oo],'record-damping-predecessor-image');ne=link_image(root,out,[no],'record-damping-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('Record damping live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('Record damping body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('Record damping protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=193,frame=48,guards=len(guard_rows()),bindings=len(t['bindings']),raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
