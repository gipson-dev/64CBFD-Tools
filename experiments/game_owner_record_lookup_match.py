"""Complete owner-record search, retail switch pool and literal full-image audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_owner_record_lookup_candidates as candidate
from tools.experiments import game_actor_height_effect_match as metadata
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
MAKE='conker/Makefile'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BASELINE_SHA='179206d917663ba74e403486ca6fa037b6f195ddcd6e10329b56b965178083f3'
GUARD_SHA='a1d33e60900a06e6821361960dc1e6f3bfec2d850c8a916e7ad511103c0ec45f'
METADATA_GROUPS=((('D_800A7434','D_8008F750','D_8009E714'),(1,2,0)),(('jtbl_800A7410','D_800CBD78'),(1,0)))

def function_blob(obj,index):
    t,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def derive(raw,bindings,index):
    t=candidate.TARGETS[index]
    if index!=0 or len(raw)!=356 or sha(raw)!=t['raw_sha256']or bindings!=t['bindings']:raise ValueError('Owner-record body/bindings changed')
    words=list(struct.unpack('>89I',raw))
    if words[11:13]!=[0x24420000,0x24840000]or bindings[44]!=[('R_MIPS_LO16','D_800DCE50')]or bindings[48]!=[('R_MIPS_LO16','D_800DD190')]:raise ValueError('Owner-record address schedule changed')
    # Two independent ADDIU address completions; their LO16 bindings move
    # together. There are no intervening memory accesses or possible traps.
    words[11],words[12]=words[12],words[11];moved=dict(bindings);moved[44],moved[48]=moved[48],moved[44]
    for at in(144,152):moved[at]=[(k,candidate.RODATA_SYMBOL)for k,n in moved[at]]
    return struct.pack('>89I',*words),moved

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Owner-record guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode())))
    if any(r['function']==candidate.TARGETS[0]['function']for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Owner-record guards already present')
    raw=candidate.TARGETS[0];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    for at,other in((44,48),(48,44)):
        old,new=raw['patches'][at];expected=raw['bindings'][at][0];replacement=raw['bindings'][other][0]
        writer.writerow(dict(filename=raw['owner'],function=raw['function'],offset='0x%X'%at,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations=expected[0]+':'+expected[1],replacement_relocations=replacement[0]+':'+replacement[1],note='Exchange independent row/end ADDIU completions and their LO16 bindings',omit='false'))
    return before+stream.getvalue().encode()


def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Owner-record discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/undefined_syms_auto.txt','conker/conker.us.yaml','conker/retail_layout.us.txt'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Owner-record protected input changed: '+n)
    hp=out/'match-include-sha256.json'
    if not hp.exists():
        headers={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in headers:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        hp.write_text(json.dumps(headers,indent=2)+'\n',encoding='utf-8')
    headers=json.loads(hp.read_text(encoding='utf-8'))
    for n,h in headers.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Owner-record include changed: '+n)
    return len(values)+len(headers)

def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    emit=pad_generated_object.emit_padded_assembly if index==0 else pad_c_object.emit_padded_assembly
    s.write_text(emit(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards,rodata_symbol=candidate.RODATA_SYMBOL),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded:
        expected=(1,2,0,16,bytes(48),tuple((4*i,2,('text','func_1518BA90',off))for i,off in enumerate((164,256,256,256,256,256,312,312,172))))
        if '.rodata'in a or b.get('.rodata')!=expected:raise ValueError('Owner-record complete switch pool changed: '+repr(b.get('.rodata')))
        b=dict(b);b.pop('.rodata')
    if a!=b:raise ValueError('Owner-record other allocatable pools changed')
    x,y=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if x is not None or y is not None:
        if x is None or y is None or x[0][1:4]+x[0][5:]!=y[0][1:4]+y[0][5:]or x[1]!=y[1]:raise ValueError('Owner-record options changed')
        if x[0][0]!=y[0][0]and(padded or(x[0][0],y[0][0])!=(33,41)):raise ValueError('Owner-record options name offset changed beyond the added .rodata name')


def link_image(root,out,owners,label):
    linker=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,o in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=o.relative_to(root/'conker').as_posix()
        if linker.count(old)!=1:raise ValueError('Owner-record link owner reference changed')
        linker=linker.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);script=d/'conker.ld';script.write_text(linker,encoding='utf-8');elf=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True);return elf

def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Owner-record predecessor image changed')
    expected=bytearray(before);sizes={t['function']:t['words']*4 for t in candidate.TARGETS}
    for t in candidate.TARGETS:
        size=4*t['words'];at=elf_slot_offset(before,t['entry'],size);expected[at:at+size]=rom[t['rom']:t['rom']+size]
        rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
        if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Owner-record predecessor symbol changed')
        struct.pack_into('>I',expected,rows[0][0]+8,size)
    named={n:p for p,n,f,s in symbol_rows(before)}
    groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Owner-record literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    if Counter((n,f[1],sizes.get(n,f[2]),*f[3:])for p,n,f,s in symbol_rows(before))!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Owner-record symbol definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);mb,ma,mi=candidate.make_states((root/MAKE).read_text(encoding='utf-8'));assert mb==(out/'match-frozen'/MAKE).read_text(encoding='utf-8');(out/'proposed-Makefile').write_text(ma,encoding='utf-8');rom=(root/ROM_IMAGE).read_bytes();owners=[[],[]];compacts=[];reports=[];phases=[]
    beforeguards=(out/'match-frozen'/GUARDS).read_bytes();afterguards=guard_manifest(beforeguards);gp=[out/'predecessor-guards.csv',out/'proposed-guards.csv'];gp[0].write_bytes(beforeguards);gp[1].write_bytes(afterguards)
    for i,t in enumerate(candidate.TARGETS):
        before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'),i);phases.append(installed)
        if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Owner-record reconstructed predecessor changed')
        old,od=candidate.compile_owner(root,out,before,'match-predecessor-%d'%i);new,nd=candidate.compile_owner(root,out,after,'match-qualified-%d'%i);diagnostics=paired_diagnostics(od,nd,t['owner']);raw_neighbors=same_functions(old,new,(t['function'],));pools(old,new)
        raw,b=function_blob(new,i);normalized,nb=derive(raw,b,i);symbols={n:int(n.split('_')[1],16)for rr in nb.values()for _,n in rr}
        if bound_blob(normalized,nb,symbols)!=list(struct.unpack_from('>%dI'%t['words'],rom,t['rom'])):raise ValueError('Owner-record derived complete body differs')
        oo=assemble_owner(root,out,old,i,'match-predecessor-owner-%d'%i,gp[0]);no=assemble_owner(root,out,new,i,'match-qualified-owner-%d'%i,gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
        if function_blob(no,i)!=(normalized,nb):raise ValueError('Owner-record padder differs')
        if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live lookup owner differs')
        owners[0].append(oo);owners[1].append(no);compacts.append(new);(out/('proposed-%d.c'%i)).write_text(after,encoding='utf-8');reports.append(dict(function=t['function'],words=t['words'],frame=t['frame'],guards=len(t['patches']),bindings=len(b),raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes())))
    if len(set(phases))!=1:raise ValueError('Owner-record source phases differ')
    installed=phases[0]
    if mi!=installed:raise ValueError('Owner-record source/Make phases differ')
    if(root/GUARDS).read_bytes()!=(afterguards if installed else beforeguards):raise ValueError('Owner-record guard phase differs')
    oe=link_image(root,out,owners[0],'lookup-predecessor-image');ne=link_image(root,out,owners[1],'lookup-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live lookup ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or set(changed)!={t['function']for t in candidate.TARGETS}:raise ValueError('Owner-record complete function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner-record protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=reports,qualified_elf_sha256=sha(updated),guard_sha256=sha(afterguards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return dict(report=report,predecessor_owners=owners[0],qualified_owners=owners[1],qualified_compacts=compacts,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
