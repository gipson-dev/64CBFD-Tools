"""Direct body/binding, complete owner and literal zero-exclusion image gates."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_owner_position_request_candidates as candidate
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
OBJECT='conker/build/src/game/generated_1D0840.c.o'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='d05bc50428188e52c31da38789d7fb077727db3df75df1af9bfb3cfff352cbcd'
GUARD_SHA='7d469fee131d8adbc169fda991046c614fea90f2704bfcd612c41371e6efa1f0'
RAW_SHA='5504d4600cc27018d690639b32679b784de69382fec3aff6b100682add82413e'
BINDINGS={44:[('R_MIPS_26','memcpy')],108:[('R_MIPS_26','func_151A4E34')],220:[('R_MIPS_26','func_15147A80')],248:[('R_MIPS_26','memcpy')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
def symbols():return dict(memcpy=0x10022EC0,func_151A4E34=0x151A4E34,func_15147A80=0x15147A80)
def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def checked(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner-position complete body/bindings changed')
    if bound_blob(raw,bindings,symbols())!=list(struct.unpack('>70I',truth)):raise ValueError('Owner-position direct literal body differs')
    return raw,bindings
def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze owner-position predecessor first')
        values=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Owner-position discovery input changed: '+n)
        names=set(values)|{'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        names.update({'conker/asm/nonmatchings/generated_1D0840/func_151A5170.s','conker/include/macro.inc','conker/include/asm_processor_prelude.inc','conker/build/src/game/generated_174BF0.c.o'})
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:
            q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen owner-position input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected owner-position input changed: '+n)
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Unchanged owner-position guards differ')
    return len(values)
def compact_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after);ar,br=a.pop('.reginfo'),b.pop('.reginfo')
    if ar[:4]!=br[:4]or ar[5:]!=br[5:]or len(ar[4])!=24:raise ValueError('Owner-request compact metadata shape changed')
    raw,_=function_blob(after);gpr=fpr=0
    for w in struct.unpack('>70I',raw):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0:regs=(rs,)if fn==8 else(rs,rt,rd)
        elif op==3:regs=(31,)
        elif op in(4,5,9,13,33,35,36,37,40,41,43):regs=(rs,rt)
        elif op==17 and rs==4:regs=(rt,);fpr|=1<<rd
        elif op==57:regs=(rs,);fpr|=1<<rt
        else:raise ValueError('Unclassified owner-request register instruction')
        for r in regs:
            if r:gpr|=1<<r
    expected=bytearray(ar[4]);oldg=int.from_bytes(expected[:4],'big');oldf=int.from_bytes(expected[8:12],'big')
    expected[:4]=(oldg|gpr).to_bytes(4,'big');expected[8:12]=(oldf|fpr).to_bytes(4,'big')
    if bytes(expected)!=br[4]or a!=b:raise ValueError('Owner-request compact pools or derived register metadata differ')
    return dict(GPR_before='%08X'%oldg,GPR_after='%08X'%(oldg|gpr),FPR_before='%08X'%oldf,FPR_after='%08X'%(oldf|fpr),body_derived=True)
def assemble_owner(root,out,obj,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_1D0840.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=root/GUARDS),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Owner-position image predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Owner-position predecessor symbol differs')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[hex(i)for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Owner-position literal whole image differs: '+repr((len(before),len(after),len(diff),diff[:30])))
    return sum(a!=b for a,b in zip(before,after))
def census(root):
    image=(root/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image)
    v=dict(calls=[4*i for i,w in enumerate(words)if w==(0x0c000000|((ENTRY>>2)&0x3ffffff))],tails=[4*i for i,w in enumerate(words)if w==(0x08000000|((ENTRY>>2)&0x3ffffff))],pointers=[4*i for i,w in enumerate(words)if w==ENTRY])
    if v!=dict(calls=[0x1D08F0,0x1D23F0],tails=[],pointers=[]):raise ValueError('Owner-position caller census differs')
    return v
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    if bs!=(out/'match-frozen'/SOURCE).read_text(encoding='utf-8'):raise ValueError('Owner-position source predecessor differs')
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if od or nd:raise ValueError('Owner-position compiler diagnostics: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];checked(*function_blob(new),truth);rn=same_functions(old,new,(FUNCTION,));pools=compact_pools(old,new)
    oo=assemble_owner(root,out,old,'match-predecessor-owner');no=assemble_owner(root,out,new,'match-qualified-owner')
    if(no if installed else oo).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Owner-position live padded owner differs')
    checked(*function_blob(no),truth);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Owner-position padded pools differ')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'owner-request-predecessor-image');ne=harness.link_image(root,out,no,'owner-request-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Owner-position live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>70I',truth)):raise ValueError('Owner-position address/body closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner-position protected data differs')
    v=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=70,raw_word_differences=0,frame=168,guards=0,bindings=4,raw_neighbors=rn,neighbors=pn,compact_GPR_mask=pools,padded_pools_unchanged=True,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    return dict(report=v,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
