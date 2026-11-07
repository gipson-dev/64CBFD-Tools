"""Qualify the sentinel diamond, ABI home and complete linked sprite owner."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments import game_seeded_sprite_candidates as candidate
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
BASELINE_SHA='652799e33cba0e843ac58ec6e3a2c6f81a3cd3383cca403a6c067af74e1dc165'
GUARD_SHA='4792e2d49631c53f8b7da7276d04153ea8133f2dc48ed5c8fdcbd63ee9b059cf'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,bindings,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=292 or sha(raw)!=t['raw_sha256']or bindings!=t['bindings']:raise ValueError('Sprite body/bindings changed')
    a=list(struct.unpack('>73I',raw));b=list(a)
    if(a[21],a[22],a[23],a[34],a[35],a[36])!=(0x4502000F,0xA7A300BE,0x844E0002,0x10000002,0xA0400008,0xA7A300BE):raise ValueError('Sprite sentinel diamond changed')
    # Rotate the same two paths. False stores the unadjusted height; true
    # reads Y, computes/stores the adjusted height, then clears the variant.
    b[21:37]=[0x45030004,a[23],0x1000000D,a[22],a[23],*a[24:34],a[35]]
    for i,old,new in((0,0x27BDFF30,0x27BDFF28),(2,0xAFA400D0,0xAFA400D8),(6,0x8FA200D0,0x8FA200D8),(58,0x8FA200D0,0x8FA200D8),(65,0x8FA900D0,0x8FA900D8),(70,0x27BD00D0,0x27BD00D8)):
        if a[i]!=old:raise ValueError('Sprite expected frame/home changed')
        b[i]=new
    if {i*4:(x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y}!=t['patches']:raise ValueError('Sprite derived guard set changed')
    updated=struct.pack('>73I',*b);audit_frame_and_paths(raw,updated)
    return updated,dict(bindings)
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Sprite guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode('utf-8'))))
    if any(r['function']=='func_15193390'for r in csv.DictReader(io.StringIO(before.decode('utf-8')))):raise ValueError('Sprite guards already present')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    for p,(old,new)in sorted(candidate.TARGETS[0]['patches'].items()):writer.writerow(dict(filename='generated_1C0840',function='func_15193390',offset='0x%X'%p,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',note='Normalize proved sprite sentinel diamond and unused frame tail with physical O32 home retained',omit='false'))
    return before+stream.getvalue().encode('utf-8')
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial={}
        for n in('discovery-input-sha256.json','supplemental-input-sha256.json'):initial.update(json.loads((out/n).read_text(encoding='utf-8')))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Sprite discovery changed: '+n)
        names=set(initial)|{'ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1')};names.update(p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:
            p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    extra=out/'match-helper-source-sha256.json'
    if not extra.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze copy source before installation')
        name='conker/asm/libultra/libc/bcopy.s';p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes());extra.write_text(json.dumps({name:sha(p.read_bytes())},indent=2)+'\n',encoding='utf-8')
    values.update(json.loads(extra.read_text(encoding='utf-8')))
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected sprite input changed: '+n)
    return len(values)
def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    s.write_text(pad_generated_object.emit_padded_assembly(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards),encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o
def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded:
        b=dict(b);x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if(struct.unpack_from('>I',x[4])[0],struct.unpack_from('>I',raw)[0],struct.unpack_from('>I',x[4],8)[0],struct.unpack_from('>I',raw,8)[0])!=(0x80000004,0xA300FFFE,0,0x707F0):raise ValueError('Sprite raw register masks changed')
        raw[:4]=x[4][:4];raw[8:12]=x[4][8:12];b['.reginfo']=(*y[:4],bytes(raw),*y[5:])
    if a!=b:raise ValueError('Sprite whole allocatable pools changed')
    aa,bb=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if aa is None and bb is None:return
    if aa is None or bb is None or aa[0][:4]+aa[0][5:]!=bb[0][:4]+bb[0][5:]:raise ValueError('Sprite options header changed')
    raw=bytearray(bb[1])
    if not padded:
        if(struct.unpack_from('>I',aa[1],8)[0],struct.unpack_from('>I',raw,8)[0],struct.unpack_from('>I',aa[1],16)[0],struct.unpack_from('>I',raw,16)[0])!=(0x80000004,0xA300FFFE,0,0x707F0):raise ValueError('Sprite options masks changed')
        raw[8:12]=aa[1][8:12];raw[16:20]=aa[1][16:20]
    if aa[1]!=bytes(raw):raise ValueError('Sprite options payload changed')
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
    expected=bytearray(before);t=candidate.TARGETS[0];at=elf_slot_offset(before,t['entry'],292);expected[at:at+292]=rom[t['rom']:t['rom']+292]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,292)
    from unittest.mock import patch
    from tools.experiments import game_actor_height_effect_match as metadata
    # Explicit closed GNU-ld bucket permutations, including the unequal
    # string lengths in the second group. Both entire tables stay checked.
    groups=((0x2B7B6C,('D_800A81B0','D_8009F640','D_80096240'),(1,2,0)),
            (0x2C58AC,('func_150F34A0','D_8009E480'),(1,0)))
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    wanted=Counter((n,f[1],292 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
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
    if bound_blob(normalized,nrefs,{n:(0x100226F0 if n=='bzero'else int(n.split('_')[1],16))for rows in nrefs.values()for _,n in rows})!=list(struct.unpack_from('>73I',rom,t['rom'])):raise ValueError('Normalized body differs')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',gp[0]);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(normalized,nrefs):raise ValueError('Padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live owner differs')
    if(root/GUARDS).read_bytes()!=(ag if installed else bg):raise ValueError('Guard phase differs')
    oe=link_image(root,out,[oo],'sprite-predecessor-image');ne=link_image(root,out,[no],'sprite-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[t['function']]:raise ValueError('Function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Protected data differs')
    (out/'proposed-0.c').write_text(after,encoding='utf-8')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=73,frame=216,guards=22,bindings=6,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(updated),guard_sha256=sha(ag),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
def audit_frame_and_paths(raw,updated):
    a,b=(struct.unpack('>73I',v)for v in(raw,updated))
    if(a[21],b[21],a[34],b[23])!=(0x4502000F,0x45030004,0x10000002,0x1000000D):raise ValueError('Sprite branch edges changed')
    if a[22]!=b[24]or a[23]!=b[22]or a[23]!=b[25]or tuple(a[24:34])!=tuple(b[26:36])or a[35]!=b[36]:raise ValueError('Sprite path operations changed')
    home=(2,6,58,65);escapes=[];private=[]
    for i,w in enumerate(a):
        op,rs,rt,offset=w>>26,w>>21&31,w>>16&31,w&65535
        if rs!=29:
            if op==0 and(rt==29 or(w>>11&31)==29):raise ValueError('Foreign sprite SP use')
            continue
        if op==9:
            if rt==29:
                if(i,w,b[i])not in((0,0x27BDFF30,0x27BDFF28),(70,0x27BD00D0,0x27BD00D8)):raise ValueError('Sprite frame imbalance')
            else:
                if offset!=0x28 or rt!=4:raise ValueError('Unexpected sprite address escape')
                escapes.append(offset)
        elif op in(0x23,0x2B,0x21,0x25,0x24,0x28,0x29,0x31,0x39):
            size=1 if op in(0x24,0x28)else 2 if op in(0x21,0x25,0x29)else 4
            if i in home:
                if offset!=208 or b[i]&65535!=216:raise ValueError('Sprite incoming physical home changed')
            elif offset+size>208:raise ValueError('Sprite raw private frame escape')
            private.append((i,offset,size))
        else:raise ValueError('Unknown sprite SP operation')
    if escapes!=[0x28,0x28,0x28]or len(private)!=21:raise ValueError('Sprite stack closure changed')
    return dict(raw_frame=208,retail_frame=216,unused_tail=8,home_accesses=4,descriptor=[40,208],address_escapes=3,raw_private_memory_instructions=17,branch_words=16,common_join=37,raw_unreachable=36,retail_unreachable=25)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
