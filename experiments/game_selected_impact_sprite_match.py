"""Complete impact callback, closed unused frame tail, and literal full-image audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments import game_selected_impact_sprite_candidates as candidate
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
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BASELINE_SHA='eb7bf8d4743637447c3828453d66ce32a6302c1278cb9da46b582686e481cfcc'
GUARD_SHA='7279941acba7f0702468e833e5918a31209722e4ce3479f3a0e8b964b1a5c725'

def function_blob(obj,index):
    t,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def derive(raw,bindings,index):
    t=candidate.TARGETS[index]
    if len(raw)!=4*t['words'] or sha(raw)!=t['raw_sha256'] or bindings!=t['bindings']:raise ValueError('Sprite body/bindings changed')
    result=bytearray(raw)
    for at,(old,new)in t['patches'].items():
        if struct.unpack_from('>I',result,at)[0]!=old or at in bindings:raise ValueError('Sprite schedule guard changed')
        struct.pack_into('>I',result,at,new)
    audit_schedule(raw,bytes(result),index)
    return bytes(result),dict(bindings)

def audit_schedule(raw,updated,index):
    if index!=0:raise ValueError('Foreign impact sprite target')
    a,b=(struct.unpack('>109I',v)for v in(raw,updated))
    for i in(20,30,73,80):
        x,y=a[i],b[i]
        if x&0xFC00FFFF!=y&0xFC00FFFF or x&63!=0x21 or(x>>21&31,x>>16&31)!=(y>>16&31,y>>21&31):raise ValueError('Foreign impact ADDU guard')
    if Counter(a[47:54])!=Counter(b[47:54])or Counter(a[67:70])!=Counter(b[67:70]):raise ValueError('Impact stores/index schedule not closed')
    # Both reorderings preserve public store/read order. Only the independent
    # stride constant moves before the mark and live index read.
    if(a[67],a[68],a[69],b[67],b[68],b[69])!=(0xA1590020,0x820B002D,0x24040014,0x24040014,0xA1590020,0x820B002D):raise ValueError('Foreign impact public memory order')
    frame_words={0:(0x27BDFF00,0x27BDFF08),4:(0xAFA50104,0xAFA500FC),5:(0xAFA60108,0xAFA60100),6:(0xAFA7010C,0xAFA70104),10:(0xC7A80110,0xC7A80108),70:(0xC7A60110,0xC7A60108),99:(0x8FA70114,0x8FA7010C),106:(0x27BD0100,0x27BD00F8)}
    for i,pair in frame_words.items():
        if(a[i],b[i])!=pair:raise ValueError('Impact frame/home transformation changed')
    incoming={4,5,6,10,70,99};addresses=[];memory=[]
    for i,w in enumerate(a):
        op,rs,rt,off=w>>26,w>>21&31,w>>16&31,w&65535
        if rs!=29:continue
        if op==9:
            if rt==29:
                if i not in(0,106):raise ValueError('Unexpected impact stack adjustment')
            else:
                if off not in(0x38,0x50):raise ValueError('Unexpected impact local address escape')
                addresses.append(off)
        elif op in(0x23,0x2B,0x31,0x39,0x29,0x28,0x24,0x21,0x25):
            size=1 if op in(0x28,0x24)else 2 if op in(0x29,0x21,0x25)else 4
            if i in incoming:
                if off<256 or(b[i]&65535)!=off-8:raise ValueError('Impact incoming absolute home changed')
            elif off+size>248:raise ValueError('Impact frame tail is live')
            memory.append((i,off,size))
        else:raise ValueError('Unexpected impact use of SP')
    if addresses!=[0x50,0x50,0x38]or 0x50+168!=248 or 0x38+12>248:raise ValueError('Impact descriptor/vector extent changed')
    return dict(raw_frame=256,retail_frame=248,unused_tail_bytes=8,private_accesses=len(memory)-len(incoming),incoming_homes=len(incoming),address_escapes=addresses)

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Sprite guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode())))
    if any(r['function']in [t['function']for t in candidate.TARGETS]for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Sprite guards already present')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    for t in candidate.TARGETS:
        for at,(old,new)in sorted(t['patches'].items()):writer.writerow(dict(filename=t['owner'],function=t['function'],offset='0x%X'%at,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',note='Normalize proved unused impact frame tail, argument homes and closed schedules',omit='false'))
    return before+stream.getvalue().encode()

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Sprite discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/undefined_syms_auto.txt','conker/conker.us.yaml','conker/retail_layout.us.txt'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Sprite protected input changed: '+n)
    hp=out/'match-include-sha256.json'
    if not hp.exists():
        headers={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in headers:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        hp.write_text(json.dumps(headers,indent=2)+'\n',encoding='utf-8')
    headers=json.loads(hp.read_text(encoding='utf-8'))
    for n,h in headers.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Sprite include changed: '+n)
    return len(values)+len(headers)

def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    emit=pad_generated_object.emit_padded_assembly if index==0 else pad_c_object.emit_padded_assembly
    s.write_text(emit(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded and a!=b:
        x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if struct.unpack_from('>I',x[4],8)[0]!=0xD0DD0 or struct.unpack_from('>I',raw,8)[0]!=0xF0DF1:raise ValueError('Foreign sprite FPR mask change')
        struct.pack_into('>I',raw,8,0xD0DD0);b['.reginfo']=(*y[:4],bytes(raw),*y[5:])
    if a!=b:raise ValueError('Sprite allocatable pools changed: '+repr([(n,a.get(n),b.get(n))for n in a.keys()|b.keys()if a.get(n)!=b.get(n)])[:1400])
    x,y=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if x is not None or y is not None:
        if x is None or y is None or x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]:raise ValueError('Sprite options shape changed')
        raw=bytearray(y[1])
        if x[1]!=y[1] and not padded:
            if struct.unpack_from('>I',x[1],16)[0]!=0xD0DD0 or struct.unpack_from('>I',raw,16)[0]!=0xF0DF1:raise ValueError('Sprite options FPR mask changed')
            struct.pack_into('>I',raw,16,0xD0DD0)
        if x[1]!=bytes(raw):raise ValueError('Sprite options changed beyond FPR mask')

def link_image(root,out,owners,label):
    linker=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,o in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=o.relative_to(root/'conker').as_posix()
        if linker.count(old)!=1:raise ValueError('Sprite link owner reference changed')
        linker=linker.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);script=d/'conker.ld';script.write_text(linker,encoding='utf-8');elf=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True);return elf

def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Sprite predecessor image changed')
    expected=bytearray(before);sizes={t['function']:t['words']*4 for t in candidate.TARGETS}
    for t in candidate.TARGETS:
        size=4*t['words'];at=elf_slot_offset(before,t['entry'],size);expected[at:at+size]=rom[t['rom']:t['rom']+size]
        rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
        if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Sprite predecessor symbol changed')
        struct.pack_into('>I',expected,rows[0][0]+8,size)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Sprite literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    if Counter((n,f[1],sizes.get(n,f[2]),*f[3:])for p,n,f,s in symbol_rows(before))!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Sprite symbol definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);rom=(root/ROM_IMAGE).read_bytes();owners=[[],[]];compacts=[];reports=[];phases=[]
    beforeguards=(out/'match-frozen'/GUARDS).read_bytes();afterguards=guard_manifest(beforeguards);gp=[out/'predecessor-guards.csv',out/'proposed-guards.csv'];gp[0].write_bytes(beforeguards);gp[1].write_bytes(afterguards)
    for i,t in enumerate(candidate.TARGETS):
        before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'),i);phases.append(installed)
        if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Sprite reconstructed predecessor changed')
        old,od=candidate.compile_owner(root,out,before,'match-predecessor-%d'%i);new,nd=candidate.compile_owner(root,out,after,'match-qualified-%d'%i);diagnostics=paired_diagnostics(od,nd,t['owner']);raw_neighbors=same_functions(old,new,(t['function'],));pools(old,new)
        raw,b=function_blob(new,i);normalized,nb=derive(raw,b,i);symbols={n:int(n.split('_')[1],16)for rr in b.values()for _,n in rr}
        if bound_blob(normalized,nb,symbols)!=list(struct.unpack_from('>%dI'%t['words'],rom,t['rom'])):raise ValueError('Sprite derived complete body differs')
        oo=assemble_owner(root,out,old,i,'match-predecessor-owner-%d'%i,gp[0]);no=assemble_owner(root,out,new,i,'match-qualified-owner-%d'%i,gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
        if function_blob(no,i)!=(normalized,nb):raise ValueError('Sprite padder differs')
        if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live sprite owner differs')
        owners[0].append(oo);owners[1].append(no);compacts.append(new);(out/('proposed-%d.c'%i)).write_text(after,encoding='utf-8');reports.append(dict(function=t['function'],words=t['words'],frame=t['frame'],guards=len(t['patches']),bindings=len(b),raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes())))
    if len(set(phases))!=1:raise ValueError('Sprite two source phases differ')
    installed=phases[0]
    if(root/GUARDS).read_bytes()!=(afterguards if installed else beforeguards):raise ValueError('Sprite guard phase differs')
    oe=link_image(root,out,owners[0],'sprite-predecessor-image');ne=link_image(root,out,owners[1],'sprite-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live sprite ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or set(changed)!={t['function']for t in candidate.TARGETS}:raise ValueError('Sprite complete function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sprite protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=reports,qualified_elf_sha256=sha(updated),guard_sha256=sha(afterguards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return dict(report=report,predecessor_owners=owners[0],qualified_owners=owners[1],qualified_compacts=compacts,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
