"""Direct constructor with three-owner C ABI audit and literal whole image."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_owner_vector_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_path_heading_turn_match import padded_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=284,candidate.BUILD
OBJECT='conker/build/src/game_18D770.c.o'
ASM='conker/asm/nonmatchings/game_18D770/func_15160A58.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
LAYOUT='conker/retail_layout.us.txt'
BASELINE_SHA='8804d7955b17011daf0710dfef42c9270d60845540ffac14d8db3012753fb018'
GUARD_SHA='ad8c4e24d535e3ccc7aa3d4c3ae7db4972c569bbf690238f68c65757438993c6'
BINDINGS={224:[('R_MIPS_26','func_151602C0')],252:[('R_MIPS_26','memcpy')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        values=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Owner-vector discovery changed: '+n)
        names=set(values)|{LAYOUT,'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={*candidate.SOURCES,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen owner-vector input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected owner-vector input changed: '+n)
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Constructor guards changed')
    return len(values)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def checked(raw,bindings,truth):
    if len(raw)!=SIZE or len(truth)!=SIZE or bindings!=BINDINGS:raise ValueError('Constructor extent/bindings changed')
    expected=bytearray(truth)
    for at in BINDINGS:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFC000000)
    if raw!=bytes(expected):raise ValueError('Constructor complete body changed')
    return raw,bindings

def diagnostic_rows(text):
    import re
    rows=re.findall(r'cfe: Warning (\d+): [^\n]*, line \d+: ([^\n]+)\n([^\n]*)\n([^\n]*)\n',text)
    if len(rows)!=text.count('Warning '):raise ValueError('Constructor unparsed diagnostic')
    return Counter(tuple(v.strip()for v in row)for row in rows)

def paired_diagnostics(before,after,owner):
    a,b=diagnostic_rows(before),diagnostic_rows(after);removed=a-b;added=b-a
    if added:raise ValueError('New constructor-owner diagnostics: '+repr(added))
    if owner==FILENAME:
        if (sum(a.values()),sum(b.values()),sum(removed.values()))!=(44,42,2) or any(row[0]!='712' or 'temp_v0 = func_15160A58('not in row[2]for row in removed):raise ValueError('Constructor warning delta changed')
    elif removed:raise ValueError('Caller warning set unexpectedly changed')
    return dict(before=sum(a.values()),after=sum(b.values()),removed=[dict(kind=row[0],message=row[1],code=row[2],caret=row[3],count=n)for row,n in removed.items()],new=[])

def assemble_owner(root,out,obj,label,owner):
    from tools import pad_c_object
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(owner+'.c.o')
    if owner.startswith('generated_'):
        asm=emit_padded_assembly(obj,root/'conker/asm'/(owner.removeprefix('generated_')+'.s'),filename=owner,word_patches_path=root/GUARDS)
    else:asm=pad_c_object.emit_padded_assembly(obj,root/LAYOUT,owner,word_patches_path=root/GUARDS)
    s.write_text(asm,encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Owner-vector literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,28):raise ValueError('Owner-vector predecessor symbol extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Owner-vector literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    want=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if want!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Owner-vector named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom)
    got=dict(calls=[4*i for i,w in enumerate(words)if w==(0x0C000000|((ENTRY>>2)&0x3FFFFFF))],tails=[4*i for i,w in enumerate(words)if w==(0x08000000|((ENTRY>>2)&0x3FFFFFF))],pointers=[4*i for i,w in enumerate(words)if w==ENTRY])
    expected=json.loads((root/BUILD/'caller-static.json').read_text(encoding='utf-8'))
    if any(got[k]!=expected[k]for k in got)or(len(got['calls']),len(got['tails']),len(got['pointers']))!=(12,0,0):raise ValueError('Constructor caller census changed')
    return got

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out);owners={};installed_values=[]
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    for index,path in enumerate(candidate.SOURCES):
        owner=Path(path).stem;before,after,installed=candidate.source_states((root/path).read_text(encoding='utf-8'),path);installed_values.append(installed)
        old,od=candidate.compile_owner(root,out,before,'match-predecessor-'+owner);new,nd=candidate.compile_owner(root,out,after,'match-qualified-'+owner)
        diagnostics=paired_diagnostics(od,nd,owner);raw_neighbors=same_functions(old,new,(FUNCTION,)if path==SOURCE else())
        if alloc_pools(old)!=alloc_pools(new):raise ValueError('Constructor raw pools changed: '+owner)
        if path==SOURCE:checked(*function_blob(new),truth)
        oo=assemble_owner(root,out,old,'match-predecessor-'+owner+'-owner',owner);no=assemble_owner(root,out,new,'match-qualified-'+owner+'-owner',owner)
        object_path='conker/build/'+str(Path(path).relative_to('conker').with_suffix('.c.o'))
        if (no if installed else oo).read_bytes()!=(root/object_path).read_bytes():raise ValueError('Constructor live object differs: '+owner)
        padded_neighbors=same_functions(oo,no,(FUNCTION,)if path==SOURCE else())
        if padded_pools(oo)!=padded_pools(no):raise ValueError('Constructor padded pools changed: '+owner)
        if path!=SOURCE and oo.read_bytes()!=no.read_bytes():raise ValueError('Constructor caller object is not completely invariant: '+owner)
        if path==SOURCE:checked(*function_blob(no),truth)
        q=out/'proposed'/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(after,encoding='utf-8')
        owners[owner]=dict(source=path,object=object_path,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_pools_fixed=True,padded_pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),object_completely_fixed=(path!=SOURCE))
        if path==SOURCE:old_owner,new_owner,raw_owner=oo,no,new
    if len(set(installed_values))!=1:raise ValueError('Constructor source installation is partial')
    installed=installed_values[0]
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'vector-predecessor-image');ne=harness.link_image(root,out,new_owner,'vector-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if (after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Constructor live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Constructor whole body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Constructor protected data differs')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=71,slot_words=71,alignment_words=0,frame=104,guards=0,bindings=2,raw_word_differences=0,owners=owners,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text((out/'proposed'/SOURCE).read_text(encoding='utf-8'),encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=raw_owner,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
