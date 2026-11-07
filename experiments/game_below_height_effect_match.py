"""Qualify a closed frame/spill transformation and the literal full image."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments import game_below_height_effect_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
BUILD=candidate.BUILD
ELF,GUARDS,MAKE='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile'
ROM_IMAGE,LINKER='conker/conker.us.bin','conker/build/conker.ld'
BASELINE_SHA='bf6774ce158a355996b9f3fd20bf5f3968e37f1e6af1732b0b363884c405718f'
GUARD_SHA='41c72a77ad2e2f185a04e0d6a7fddb3272e915175be8f4ebbf7756a90436ffc6'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,bindings,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=276 or sha(raw)!=t['raw_sha256']or bindings!=t['bindings']:raise ValueError('Height body/bindings changed')
    result=bytearray(raw)
    for p,(old,new)in t['patches'].items():
        if struct.unpack_from('>I',raw,p)[0]!=old or p in bindings:raise ValueError('Height expected guard changed')
        struct.pack_into('>I',result,p,new)
    audit_frame(raw,bytes(result))
    return bytes(result),dict(bindings)
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Height guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode('utf-8'))))
    if any(r['function']=='func_15189EBC'for r in csv.DictReader(io.StringIO(before.decode('utf-8')))):raise ValueError('Height guards already present')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    for p,(old,new)in sorted(candidate.TARGETS[0]['patches'].items()):writer.writerow(dict(filename='generated_1B6DB0',function='func_15189EBC',offset='0x%X'%p,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',note='Normalize proved below-height private frame and closed position-pointer spill',omit='false'))
    return before+stream.getvalue().encode('utf-8')
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial={}
        for name in('discovery-input-sha256.json','supplemental-input-sha256.json'):initial.update(json.loads((out/name).read_text(encoding='utf-8')))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Height discovery changed: '+n)
        names=set(initial)|{'ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1')}
        names.update(p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:
            p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Height protected input changed: '+n)
    return len(values)
def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    s.write_text(pad_generated_object.emit_padded_assembly(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded:
        b=dict(b);x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if (struct.unpack_from('>I',x[4])[0],struct.unpack_from('>I',raw)[0])!=(0xA001C1F6,0xA303FFFE):raise ValueError('Height raw GPR masks changed')
        raw[:4]=x[4][:4];b['.reginfo']=(*y[:4],bytes(raw),*y[5:])
    if a!=b:raise ValueError('Height whole allocatable pools changed')
    aa,bb=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if aa is None and bb is None:return
    if aa is None or bb is None or aa[0][:4]+aa[0][5:]!=bb[0][:4]+bb[0][5:]:raise ValueError('Height options header changed')
    raw=bytearray(bb[1])
    if not padded:
        if(struct.unpack_from('>I',aa[1],8)[0],struct.unpack_from('>I',raw,8)[0])!=(0xA001C1F6,0xA303FFFE):raise ValueError('Height options mask changed')
        raw[8:12]=aa[1][8:12]
    if aa[1]!=bytes(raw):raise ValueError('Height options payload changed')
def link_image(root,out,owners,label):
    linker=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,obj in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=obj.relative_to(root/'conker').as_posix()
        if linker.count(old)!=1:raise ValueError('Link owner reference changed')
        linker=linker.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);script=d/'conker.ld';script.write_text(linker,encoding='utf-8');elf=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return elf
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Predecessor image changed')
    expected=bytearray(before);t=candidate.TARGETS[0];at=elf_slot_offset(before,t['entry'],276);expected[at:at+276]=rom[t['rom']:t['rom']+276]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,276)
    # The two newly referenced constants exchange positions with existing
    # names in their GNU-ld buckets. Predict the complete closed symbol and
    # string permutations; do not exclude either metadata section.
    from unittest.mock import patch
    from tools.experiments import game_actor_height_effect_match as metadata
    groups=((0x2B8ABC,('D_800A73B0','D_8009E640'),(1,0)),
            (0x2C791C,('D_800A73A8','D_8009E638'),(1,0)))
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    wanted=Counter((n,f[1],276 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Symbol definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);rom=(root/ROM_IMAGE).read_bytes();t=candidate.TARGETS[0]
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Reconstructed predecessor changed')
    bg=(out/'match-frozen'/GUARDS).read_bytes();ag=guard_manifest(bg);gp=[out/'predecessor-guards.csv',out/'proposed-guards.csv'];gp[0].write_bytes(bg);gp[1].write_bytes(ag)
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);raw_neighbors=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=function_blob(new);normalized,nrefs=derive(raw,refs)
    if bound_blob(normalized,nrefs,{n:int(n.split('_')[1],16)for rows in nrefs.values()for _,n in rows})!=list(struct.unpack_from('>69I',rom,t['rom'])):raise ValueError('Normalized body differs')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',gp[0]);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(normalized,nrefs):raise ValueError('Padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live owner differs')
    if(root/GUARDS).read_bytes()!=(ag if installed else bg):raise ValueError('Guard phase differs')
    oe=link_image(root,out,[oo],'height-predecessor-image');ne=link_image(root,out,[no],'height-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[t['function']]:raise ValueError('Function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Protected data differs')
    (out/'proposed-0.c').write_text(after,encoding='utf-8')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=69,frame=80,guards=4,bindings=7,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(updated),guard_sha256=sha(ag),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
def audit_frame(raw,updated):
    a,b=(struct.unpack('>69I',v)for v in(raw,updated));patches=candidate.TARGETS[0]['patches']
    if {i*4:(x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y}!=patches:raise ValueError('Foreign height transformation')
    accesses=[];escapes=[];spill=[]
    for i,w in enumerate(a):
        op,rs,rt,offset=w>>26,w>>21&31,w>>16&31,w&65535
        if rs!=29:
            if op==0 and(rt==29 or(w>>11&31)==29):raise ValueError('Unproved height SP use')
            continue
        if op==9:
            if rt==29:
                if(i,w,b[i])not in((0,0x27BDFFB8,0x27BDFFB0),(68,0x27BD0048,0x27BD0050)):raise ValueError('Unbalanced height frames')
            else:
                if (i*4,rt,offset)!=(0xBC,13,0x34):raise ValueError('Unexpected height local address escape')
                escapes.append(offset)
        elif op in(0x23,0x2B,0x39):
            if offset+4>72:raise ValueError('Height raw frame escape')
            if i*4 in(0x4C,0x5C):
                if (op,rt,offset,b[i]&65535)not in((0x2B,2,0x44,0x40),(0x23,2,0x44,0x40)):raise ValueError('Foreign height pointer spill')
                spill.append((op,rt))
            elif b[i]!=w or offset not in(0x10,0x14,0x18,0x24,0x28,0x2C,0x34,0x38,0x3C):raise ValueError('Unexpected height private access')
            accesses.append((i*4,offset))
        else:raise ValueError('Unknown height SP instruction')
    if len(accesses)!=14 or escapes!=[0x34]or spill!=[(0x2B,2),(0x23,2)]:raise ValueError('Height frame closure changed')
    # The sole escaping object is the 12-byte vector [0x34,0x40). Both pointer
    # spill slots lie outside it and the outgoing arguments/saved registers.
    # The guarded frame ends at0x50, with its last live byte at0x43.
    return dict(raw_frame=72,retail_frame=80,private_accesses=14,incoming_homes=0,vector=[0x34,0x40],old_spill=[0x44,0x48],new_spill=[0x40,0x44],retail_unused_tail=12,address_escapes=1)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
