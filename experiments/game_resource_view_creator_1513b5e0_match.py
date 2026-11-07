"""Closed lifetime/schedule guards, complete owner and literal linked-image gates."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_resource_view_creator_1513b5e0_candidates as candidate
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
BASELINE_SHA='ee48bfffbe008eacf28903e17c86bd7ce0c3a0db40db31fbcfe40fe24cf45fdd'
METADATA_GROUPS=()
GUARD_SHA='b6b276d1ee5e6e69bcbd1cc995318ea562379c6716817fabfc1d1b4d3becf3f4'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def rename(word,mapping):
    op=word>>26
    if op==0:fields=(21,16,11)
    elif op in(2,3):fields=()
    elif op==15:fields=(16,)
    else:fields=(21,16)
    for shift in fields:
        reg=(word>>shift)&31
        word=(word&~(31<<shift))|(mapping.get(reg,reg)<<shift)
    return word

def normalization(raw,refs):
    if len(raw)!=420 or sha(raw)!='d4ea35b6be8c0053516ecb9efaa5a5a235c65a9292d37dffab195a7df259a985':raise ValueError('Resource creator raw body changed')
    if refs!=candidate.TARGETS[0]['bindings']:raise ValueError('Resource creator bindings changed')
    original=list(struct.unpack('>105I',raw));words=original[:]
    # Disjoint live ranges: the early expression's complete closed GPR cycle,
    # and the loop's row/cursor plus caller-clobbered temporary cycles.
    early={21:3,3:8,8:9,9:10,10:21}
    late={16:17,17:16,3:8,8:3,10:11,11:12,12:13,13:14,14:24,24:10}
    if set(early)!=set(early.values())or set(late)!=set(late.values()):raise ValueError('Register cycles are not closed')
    for i in range(32,49):words[i]=rename(words[i],early)
    for i in range(57,94):words[i]=rename(words[i],late)
    # Operation identities, with four real SP+50 transfers and a late saved-role
    # handoff. Every original instruction appears exactly once.
    order=list(range(25))+[27,28,25,26,29,38,30,31,32,33,34,35,36,37,39,40,41,42,43,44,45,46,
      'save-step-alloc',47,48,'reload-step-alloc',49,50,51,52,53,54,56,55,'save-step-copy',57,
      'reload-step-copy',58,60,61,62,59,64,65,63,'handoff-step',66]+list(range(67,105))
    if len(order)!=110 or sorted(i for i in order if isinstance(i,int))!=list(range(105)):raise ValueError('Instruction identities are not a permutation')
    positions={i:k for k,i in enumerate(order)if isinstance(i,int)}
    inserts={'save-step-alloc':0xAFA30050,'reload-step-alloc':0x8FA30050,
             'save-step-copy':0xAFA30050,'reload-step-copy':0x8FA30050,'handoff-step':0x0060A825}
    result=[];newrefs={};branches=[]
    for pos,i in enumerate(order):
        if isinstance(i,str):result.append(inserts[i]);continue
        w=words[i];op=w>>26
        if op in(1,4,5,6,7):
            imm=original[i]&65535;imm=imm-65536 if imm&32768 else imm
            dest=i+1+imm;replacement=positions[dest]-pos-1
            if not -32768<=replacement<32768:raise ValueError('Rebased branch overflows')
            w=(w&0xFFFF0000)|(replacement&65535);branches.append([i,dest,pos,positions[dest]])
        result.append(w)
        if i*4 in refs:newrefs[pos*4]=refs[i*4]
    effect=lambda w:w>>26 in(3,32,33,35,36,37,40,41,43)
    if [i for i in order if isinstance(i,int)and effect(original[i])]!=[i for i,w in enumerate(original)if effect(w)]:raise ValueError('Original memory/service order changed')
    return struct.pack('>110I',*result),newrefs,dict(order=order,branches=branches,early_cycle=early,late_cycles=late)

def derive(raw,refs,index=0):
    normal,bindings,proof=normalization(raw,refs)
    return normal,bindings

def guard_rows():
    raw=candidate.RAW;refs=candidate.TARGETS[0]['bindings'];normal,newrefs,proof=normalization(raw,refs)
    original=list(struct.unpack('>105I',raw));words=list(struct.unpack('>110I',normal));rows=[];pos=0
    for i in range(105):
        expected,replacement=original[i],words[pos];er,nr=refs.get(i*4,[]),newrefs.get(pos*4,[])
        insert=None
        if pos+1<len(proof['order'])and isinstance(proof['order'][pos+1],str):insert=words[pos+1]
        if expected!=replacement or er!=nr or insert is not None:
            reloc=lambda v:';'.join(t+':'+n for t,n in v)or'-'
            rows.append(['game_168A90','func_1513B5E0','0x%03X'%(i*4),'0x%08X'%expected,'0x%08X'%replacement,reloc(er),reloc(nr),'Normalize resource-view creator closed register lifetimes and independent schedule',''if insert is None else'0x%08X'%insert,''if insert is None else'-','false'])
        pos+=1+(insert is not None)
    if pos!=110 or sum(bool(r[8])for r in rows)!=5:raise ValueError('Resource creator spill accounting changed')
    return rows

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Resource creator guard predecessor changed')
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerows(guard_rows())
    return before+stream.getvalue().encode()

def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after)
    if a!=b or sum(a.values())!=4:raise ValueError('Fixed effect inherited diagnostics changed')
    return dict(before=4,after=4,new=[])
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze payload predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object'],GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected payload input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    old,new=a.pop('.reginfo',None),b.pop('.reginfo',None)
    if old is None or new is None or old[:4]!=new[:4]or old[5:]!=new[5:]:raise ValueError('Fixed effect register metadata geometry differs')
    x,y=(list(struct.unpack('>6I',v[4]))for v in(old,new));gpr=fpr=0
    raw,refs=function_blob(after)
    for word, in struct.iter_unpack('>I',raw):
        op=word>>26;rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
        if not word:continue
        if op==3:regs=(31,)
        elif op==17:
            if rs!=4:raise ValueError('Unqualified COP1 mask instruction')
            regs=(rt,);fpr|=1<<rd
        elif op==57:regs=(rs,);fpr|=1<<rt
        elif op==0:regs=(rs,rt,rd)
        else:regs=(rs,rt)
        for reg in regs:
            if reg:gpr|=1<<reg
    wanted=x[:]
    if padded:
        if old[4]!=bytes(24)or new[4]!=bytes(24):raise ValueError('Word-emitted owner register masks changed')
    else:wanted[0]|=gpr;wanted[2]|=fpr
    if y!=wanted or fpr!=0:raise ValueError('Fixed effect register metadata is not the observed target union')
    if a!=b:raise ValueError('Fixed effect pools changed: '+repr({n:(repr(a.get(n)),repr(b.get(n)))for n in set(a)|set(b)if a.get(n)!=b.get(n)}))
    aa,bb=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if aa is None and bb is None:return
    if aa is None or bb is None or aa[0][:4]+aa[0][5:]!=bb[0][:4]+bb[0][5:]or aa[1][:8]!=bb[1][:8]or aa[1][8:]!=old[4]or bb[1][8:]!=new[4]:raise ValueError('Fixed effect options differ beyond the same target register union')
def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];d=out/label;d.mkdir(parents=True,exist_ok=True);src=d/'owner.s';dest=d/(t['owner']+'.c.o')
    import sys
    sys.modules.setdefault('pad_generated_object',pad_generated_object)
    from tools import pad_c_object
    src.write_text(pad_c_object.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',t['owner'],word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(dest),str(src)],cwd=root/'conker',capture_output=True,check=True)
    return dest
def link_image(root,out,owners,label):
    script=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,obj in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=obj.relative_to(root/'conker').as_posix()
        if script.count(old)!=1:raise ValueError('Fixed effect linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Fixed effect predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],440);expected[at:at+440]=rom[t['rom']:t['rom']+440]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Fixed effect predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,440)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',METADATA_GROUPS):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        remaining=[i for i,(x,y)in enumerate(zip(expected,after))if x!=y]
        raise ValueError('Literal payload full image differs: '+repr((len(remaining),remaining[:48])))
    wanted=Counter((n,f[1],440 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Fixed effect named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Fixed effect predecessor source changed')
    oldguards=out/'predecessor-guards.csv';oldguards.write_bytes((out/'match-frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(oldguards.read_bytes()))
    if(root/GUARDS).read_bytes()!=(guards if installed else oldguards).read_bytes():raise ValueError('Live fixed-effect guards differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(func_1502B6BC=0x1502B6BC,D_80082FA0=0x80082FA0,func_15167A68=0x15167A68,memcpy=0x10022EC0,func_1510CE60=0x1510CE60)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>110I',rom,t['rom'])):raise ValueError('Direct payload words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',oldguards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('Fixed effect padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Fixed effect live owner differs')
    oe=link_image(root,out,[oo],'payload-predecessor-image');ne=link_image(root,out,[no],'payload-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('Fixed effect live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('Fixed effect body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('Fixed effect protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=110,frame=120,guards=len(guard_rows()),bindings=8,raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
