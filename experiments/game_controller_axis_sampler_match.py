"""Complete controller sampler, closed register recipe and literal whole-image gate."""
import csv,hashlib,io,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_controller_axis_sampler_candidates as candidate
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
FUNCTION,FILENAME,SOURCE,ASM=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE,candidate.ASM
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
SIZE=280
OBJECT='conker/build/src/game/generated_6CEA0.c.o'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='89e741ec7be49a4f13b1cc59e0d4bf204bb3dc74c7c85c27f272cbf3c62a2b2b'
GUARD_SHA='3faf86a68cc26b5a29f6e96d1aaf8aa1c905686fa74a5992b868a70ef3bcdfd6'
RAW_SHA='d530e6fa7895be182fc599d2ce867d85f1c692e9694148b08d5fb3149f82f7fc'
BINDINGS={20: [('R_MIPS_HI16', 'D_800BE728')], 24: [('R_MIPS_LO16', 'D_800BE728')], 12: [('R_MIPS_HI16', 'D_80084484')], 16: [('R_MIPS_LO16', 'D_80084484')], 56: [('R_MIPS_HI16', 'D_80084484')], 60: [('R_MIPS_LO16', 'D_80084484')], 84: [('R_MIPS_HI16', 'D_80084484')], 88: [('R_MIPS_LO16', 'D_80084484')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
def symbols():return dict(D_80084484=0x80084484,D_800BE728=0x800BE728)
def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def recipe(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Controller sampler complete raw body/bindings changed')
    words=list(struct.unpack('>70I',raw));new=list(words)
    # Rotate only the independent argument sign extension past the LUI/LH pair.
    new[2:5]=[words[3],words[4],words[2]]
    rel={p:list(v)for p,v in bindings.items()if p not in(12,16)};rel[8]=bindings[12];rel[12]=bindings[16]
    # Closed lifetimes: five becomes V1, and the two -1 constants shift one temp.
    for index,old,reg in ((20,11,3),(22,11,3),(25,12,11),(49,12,11),(44,13,12),(61,13,12)):
        if new[index]>>16&31!=old:raise ValueError('Controller sampler role boundary changed')
        new[index]=(new[index]&~(31<<16))|(reg<<16)
    return struct.pack('>70I',*new),rel
def guard_rows(raw,bindings):
    new,rel=recipe(raw,bindings);rows=[]
    for i,(a,b)in enumerate(zip(struct.unpack('>70I',raw),struct.unpack('>70I',new))):
        at=i*4
        if a==b and bindings.get(at,[])==rel.get(at,[]):continue
        uses=lambda values:';'.join(k+':'+s for k,s in values)or'-'
        rows.append(dict(filename=FILENAME,function=FUNCTION,offset='0x%X'%at,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=uses(bindings.get(at,[])),replacement_relocations=uses(rel.get(at,[])),note='Normalize controller sampler independent opening schedule and closed constant register roles',insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=9:raise ValueError('Controller sampler guard count changed')
    return rows
def proposed_guards(before,raw,bindings):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Controller sampler guard predecessor changed')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(r['function']==FUNCTION for r in reader):raise ValueError('Controller sampler guards already published')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(raw,bindings))
    return before+stream.getvalue().encode('ascii')
def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze sampler predecessor first')
        values=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Sampler discovery input changed: '+n)
        names=set(values)|{'conker/symbol_addrs.us.txt','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:
            q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen sampler input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected sampler input changed: '+n)
    return len(values)
def compact_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after);ar,br=a.pop('.reginfo'),b.pop('.reginfo')
    if ar[:4]!=br[:4]or ar[5:]!=br[5:]or ar[4][4:]!=br[4][4:]:raise ValueError('Sampler compact register metadata changed outside GPR mask')
    raw,_=function_blob(after);mask=0
    for w in struct.unpack('>70I',raw):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0:regs=(rs,)if fn==8 else(rt,rd)if fn in(0,2,3)else(rs,rt,rd)
        elif op==15:regs=(rt,)
        elif op in(9,10,32,33,35,40,41,43,4,5,20,21):regs=(rs,rt)
        else:raise ValueError('Unclassified sampler register instruction')
        for r in regs:
            if r:mask|=1<<r
    old=int.from_bytes(ar[4][:4],'big');new=int.from_bytes(br[4][:4],'big')
    if old|mask!=new or a!=b:raise ValueError('Sampler compact pools or derived GPR mask changed')
    return dict(before='%08X'%old,after='%08X'%new,body_derived=True)
def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_6CEA0.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Sampler image predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Sampler predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[hex(i)for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Sampler literal whole image differs: '+repr((len(before),len(after),len(diff),diff[:35])))
    return sum(a!=b for a,b in zip(before,after))
def census(root):
    image=(root/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image)
    v=dict(calls=[4*i for i,w in enumerate(words)if w==(0x0C000000|((ENTRY>>2)&0x3ffffff))],tails=[4*i for i,w in enumerate(words)if w==(0x08000000|((ENTRY>>2)&0x3ffffff))],pointers=[4*i for i,w in enumerate(words)if w==ENTRY])
    if v!=dict(calls=[0x6D198],tails=[],pointers=[]):raise ValueError('Sampler caller census changed')
    return v
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'));bm,nm,profile=candidate.make_states((root/MAKE).read_text(encoding='utf-8'))
    if installed!=profile:raise ValueError('Sampler source/profile adoption states differ')
    if bs!=(out/'match-frozen'/SOURCE).read_text(encoding='utf-8')or bm!=(out/'match-frozen'/MAKE).read_text(encoding='utf-8'):raise ValueError('Sampler source/Make predecessor changed')
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact',flags=('-O2','-g3'));new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if od or nd:raise ValueError('Sampler compiler diagnostics: '+od+nd)
    raw,bindings=function_blob(new);literal,newrel=recipe(raw,bindings);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    if bound_blob(literal,newrel,symbols())!=list(struct.unpack('>70I',truth)):raise ValueError('Sampler recipe literal mismatch')
    rn=same_functions(old,new,(FUNCTION,));pools=compact_pools(old,new)
    before_csv=out/'match-frozen'/GUARDS;after_csv=out/'proposed-guards.csv';after_csv.write_bytes(proposed_guards(before_csv.read_bytes(),raw,bindings))
    oo=assemble_owner(root,out,old,'match-predecessor-owner',before_csv);no=assemble_owner(root,out,new,'match-qualified-owner',after_csv)
    if (no if installed else oo).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Sampler live padded owner differs')
    if function_blob(no)!=(literal,newrel):raise ValueError('Sampler padded body/bindings differ')
    pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Sampler padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'sampler-predecessor-image');ne=harness.link_image(root,out,no,'sampler-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if (after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Sampler live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>70I',truth)):raise ValueError('Sampler address/body closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sampler protected data changed')
    v=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=70,raw_word_differences=9,frame=0,guards=9,bindings=8,raw_neighbors=rn,neighbors=pn,compact_GPR_mask=pools,padded_pools_unchanged=True,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(after_csv.read_bytes()),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'proposed-Makefile').write_text(nm,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    return dict(report=v,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
