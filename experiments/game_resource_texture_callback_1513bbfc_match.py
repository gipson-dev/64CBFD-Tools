"""Direct SDK draw, complete owner and literal linked-image gates."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_resource_texture_callback_1513bbfc_candidates as candidate
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
BASELINE_SHA='d6b18982fb0d18255216f90349ef497fc8c257e0ddc6e3e6b2dc4f9c6b613e1c'
METADATA_GROUPS=((2752124,('func_15128774','D_80087434'),(1,0)),(2818140,('D_800A4A2C','D_800A7668'),(1,0)))
GUARD_SHA='5f6f9d9b935ceac0f3819711842f4d278bbaa5911c32214771aade923d984f87'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def normalization(raw,refs):
    if len(raw)!=688 or sha(raw)!=candidate.TARGETS[0]['raw_sha256']or refs!=candidate.TARGETS[0]['bindings']:raise ValueError('Texture callback raw body/bindings changed')
    original=list(struct.unpack('>172I',raw));words=original[:]
    assert words[26]==0x3C090000 and words[27]==0x25290000 and words[28]==0xC5240000
    assert refs[26*4]==[('R_MIPS_HI16','D_800A4A74')] and refs[27*4]==[('R_MIPS_LO16','D_800A4A74')] and 28*4 not in refs
    # Fuse the dead caller-clobbered address temporary into the LWC1 address.
    words[26]=(words[26]&~(31<<16))|(1<<16)
    words[28]=(words[28]&~(31<<21))|(1<<21);refs={p:r for p,r in refs.items()if p!=27*4};refs[28*4]=[('R_MIPS_LO16','D_800A4A74')]
    word=words[22];assert word==0x03108821
    words[22]=(word&~((31<<21)|(31<<16)))|((word>>21&31)<<16)|((word>>16&31)<<21)
    word=words[109];assert word==0x008D7021
    words[109]=(word&~((31<<21)|(31<<16)))|((word>>21&31)<<16)|((word>>16&31)<<21)
    # The final two range temporaries form a closed T4/T5 swap. Their sole
    # joint consumer is a commutative ADDU, whose operand swap leaves its bits.
    assert words[150]==0x8CCD0004 and words[151]==0x8CCC0000 and words[152]==0x018D7021
    words[150]=(words[150]&~(31<<16))|(12<<16)
    words[151]=(words[151]&~(31<<16))|(13<<16)
    order=list(range(27))+list(range(28,50))+[51,52,50,53,58,55,54,57,56]+list(range(59,76))+[78,82,76,77,79,81,80,84,83,103]+list(range(85,102))+[155,102,'index-copy']+list(range(104,120))+list(range(121,152))+[120]+list(range(152,155))+['page-copy']+list(range(156,172))
    assert len(order)==173 and sorted(i for i in order if isinstance(i,int))==[i for i in range(172)if i!=27]
    assert words[103]==words[155]==0 and words[107]==0x8CC40000 and words[113]==0x910F0000
    positions={i:k for k,i in enumerate(order)if isinstance(i,int)};result=[];newrefs={};branches=[]
    for pos,i in enumerate(order):
        if isinstance(i,str):result.append(words[107 if i=='index-copy'else 113]);continue
        w=words[i];op=w>>26
        if op in(1,4,5,6,7,20,21,22,23)or(op==17 and w>>21&31==8):
            dest=i+1+((w&65535)^32768)-32768
            if i==102:assert dest==107;dest=108
            if i==154:
                assert dest==113 and op==5;dest=114;w=(w&0x03FFFFFF)|(21<<26)
            if i==157:assert dest==76;dest=78
            offset=positions[dest]-pos-1;assert -32768<=offset<32768
            w=(w&0xFFFF0000)|(offset&65535);branches.append([i,dest,pos,positions[dest]])
        result.append(w)
        if i*4 in refs:newrefs[pos*4]=refs[i*4]
    return struct.pack('>173I',*result),newrefs,dict(order=order,branches=branches,folded_address_word=27,reused_NOP_words=[103,155],path_duplicated_loads=[107,113])

def derive(raw,refs,index=0):
    result,bindings,proof=normalization(raw,refs)
    return result,bindings

def guard_rows():
    raw=candidate.RAW;refs=candidate.TARGETS[0]['bindings'];normal,nr,proof=normalization(raw,refs)
    old=list(struct.unpack('>172I',raw));new=list(struct.unpack('>173I',normal));rows=[];pos=0
    reloc=lambda value:';'.join(t+':'+n for t,n in value)or'-'
    for i in range(172):
        er=refs.get(i*4,[])
        if i==27:
            rows.append(['game_168A90','func_1513BBFC','0x%03X'%(i*4),'0x%08X'%old[i],'0x%08X'%old[i],reloc(er),'-','Fold texture scalar address into its relocated LWC1','','','true']);continue
        replacement=new[pos];rr=nr.get(pos*4,[]);insert=None
        if pos+1<len(proof['order'])and isinstance(proof['order'][pos+1],str):insert=new[pos+1]
        if old[i]!=replacement or er!=rr or insert is not None:
            rows.append(['game_168A90','func_1513BBFC','0x%03X'%(i*4),'0x%08X'%old[i],'0x%08X'%replacement,reloc(er),reloc(rr),'Normalize resource texture callback independent schedule and closed branch paths',''if insert is None else'0x%08X'%insert,''if insert is None else'-','false'])
        pos+=1+(insert is not None)
    if pos!=173 or sum(bool(r[8])for r in rows)!=2 or sum(r[10]=='true'for r in rows)!=1:raise ValueError('Texture callback guard accounting changed')
    return rows

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Texture callback guard predecessor changed')
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerows(guard_rows())
    return before+stream.getvalue().encode()



def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after)
    if a!=b or sum(a.values())!=4:raise ValueError('View resource draw inherited diagnostics changed')
    return dict(before=4,after=4,new=[])
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen';t=candidate.TARGETS[0]
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze view-draw predecessor before installation')
        names=json.loads((out/'input-names.json').read_text(encoding='utf-8'))
        values={n:sha((root/n).read_bytes())for n in names}
        for n in names:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,'conker/build/conker.us.bin','graphify-out/graph.json',t['source'],t['object'],GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected view-draw input changed: '+n)
    return len(values)
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    old,new=a.pop('.reginfo',None),b.pop('.reginfo',None)
    if old is None or new is None or old[:4]!=new[:4]or old[5:]!=new[5:]:raise ValueError('View resource draw register metadata geometry differs')
    x,y=(list(struct.unpack('>6I',v[4]))for v in(old,new));gpr=fpr=0
    raw,refs=function_blob(after)
    for word, in struct.iter_unpack('>I',raw):
        op=word>>26;rs,rt,rd,fd=word>>21&31,word>>16&31,word>>11&31,word>>6&31;fn=word&63;fp=[]
        if not word:continue
        if op==3:regs=(31,)
        elif op==17:
            if rs in(0,4):regs=(rt,);fp=[rd]
            elif rs==8:regs=()
            elif rs in(16,20):
                regs=();fp=[rd]if fn in(4,6,7,13,32)else[rd,rt]
                if fn!=50:fp.append(fd)
                # IDO reserves the even/odd O32 allocation pair for every
                # arithmetic/conversion value, unlike a bare MTC1 store.
                fp=[v for reg in fp for v in(reg,reg^1)]
            else:raise ValueError('Foreign texture COP1 operation')
        elif op in(49,53,57,61):regs=(rs,);fp=[rt]if op in(49,57)else[rt,rt+1]
        elif op==15:regs=(rt,)
        elif op==0:
            regs=(rs,)if fn==8 else(rs,rd)if fn==9 else(rt,rd)if fn in(0,2,3)else(rs,rt,rd)
        else:regs=(rs,rt)
        for reg in regs:
            if reg:gpr|=1<<reg
        for reg in fp:fpr|=1<<reg
    wanted=x[:]
    if padded:
        if old[4]!=bytes(24)or new[4]!=bytes(24):raise ValueError('Word-emitted owner register masks changed')
    else:wanted[0]|=gpr;wanted[2]|=fpr
    if y!=wanted or fpr!=0xFFFFFFFF:raise ValueError('View resource draw register metadata is not the observed target union')
    if a!=b:raise ValueError('View resource draw pools changed: '+repr({n:(repr(a.get(n)),repr(b.get(n)))for n in set(a)|set(b)if a.get(n)!=b.get(n)}))
    aa,bb=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if aa is None and bb is None:return
    if aa is None or bb is None or aa[0][:4]+aa[0][5:]!=bb[0][:4]+bb[0][5:]or aa[1][:8]!=bb[1][:8]or aa[1][8:]!=old[4]or bb[1][8:]!=new[4]:raise ValueError('View resource draw options differ beyond the same target register union')
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
        if script.count(old)!=1:raise ValueError('View resource draw linker owner changed')
        script=script.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);ld=d/'conker.ld';ld.write_text(script,encoding='utf-8');dest=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(dest.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return dest
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('View resource draw predecessor image changed')
    t=candidate.TARGETS[0];expected=bytearray(before);at=elf_slot_offset(before,t['entry'],692);expected[at:at+692]=rom[t['rom']:t['rom']+692]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('View resource draw predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,692)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata,'METADATA_GROUPS',METADATA_GROUPS):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        remaining=[i for i,(x,y)in enumerate(zip(expected,after))if x!=y]
        raise ValueError('Literal view-draw full image differs: '+repr((len(remaining),remaining[:48])))
    wanted=Counter((n,f[1],692 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('View resource draw named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD);out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);t=candidate.TARGETS[0];rom=(root/ROM_IMAGE).read_bytes()
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('View resource draw predecessor source changed')
    oldguards=out/'predecessor-guards.csv';oldguards.write_bytes((out/'match-frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(oldguards.read_bytes()))
    if(root/GUARDS).read_bytes()!=(guards if installed else oldguards).read_bytes():raise ValueError('Live view-draw guards differ')
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);rn=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=derive(*function_blob(new));symbols=dict(func_1513B968=0x1513B968,sinf=0x15047D60,func_15144B34=0x15144B34,D_800A49C0=0x800A49C0,D_800A4A2C=0x800A4A2C,D_800A4A74=0x800A4A74,D_800A4A78=0x800A4A78,D_800A4A7C=0x800A4A7C,D_800A4A80=0x800A4A80,D_800BE9C0=0x800BE9C0)
    if bound_blob(raw,refs,symbols)!=list(struct.unpack_from('>173I',rom,t['rom'])):raise ValueError('Direct view-draw words differ')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',oldguards);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',guards);pn=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(raw,refs):raise ValueError('View resource draw padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('View resource draw live owner differs')
    oe=link_image(root,out,[oo],'view-draw-predecessor-image');ne=link_image(root,out,[no],'view-draw-qualified-image')
    if(root/ELF).read_bytes()!=(ne if installed else oe).read_bytes():raise ValueError('View resource draw live image differs')
    delta=strict_image(oe.read_bytes(),ne.read_bytes(),rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[t['function']]:raise ValueError('View resource draw body/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'])!=(True,189088,720):raise ValueError('View resource draw protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=173,frame=88,guards=len(guard_rows()),bindings=len(t['bindings']),raw_neighbors=rn,padded_neighbors=pn,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(ne.read_bytes()),guard_sha256=sha(guards.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[t['function']],protected_data=data)
    (out/'proposed-0.c').write_text(after,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
