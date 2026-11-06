"""Direct two-bank quad record constructor and a literal whole-image gate."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_asset_block_walker_candidates as candidate
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
SIZE,BUILD=280,candidate.BUILD
OBJECT='conker/build/src/game/generated_42DC0.c.o'
ASM='conker/asm/42DC0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
REGISTRY='conker/src/game/entrypoint.c'
BASELINE_SHA='3ec248e2a5e65ba6ce6cf3a0d05946eb7e7f18fcc83fcfa4bfb6bf08afbb4cd9'
GUARD_SHA='b53721d727660eca66ed2771ba8fd8597642b08a123168033628a26ff92fd46b'
BINDINGS={60: [('R_MIPS_26', 'func_10003C6C')], 68: [('R_MIPS_HI16', 'D_80082F80')], 72: [('R_MIPS_LO16', 'D_80082F80')], 104: [('R_MIPS_26', 'func_10004514')], 156: [('R_MIPS_26', 'func_15015A38')], 240: [('R_MIPS_26', 'func_10004074')]}
RAW_SHA='657555146e18a6926a4d009e89fcefbbcfcb0b8cccd72cb76c7f8767333eba3e'
NORM_SHA='389c197b436eab16c3f4b71c68a9bed91a99394258aa9f77201c364274a8f645'
sha=lambda b:hashlib.sha256(b).hexdigest()

def proposed_guards(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Asset walker predecessor guards changed')
    nl=b'\r\n' if b'\r\n' in before else b'\n'
    row=b'generated_42DC0,func_15015920,0xC0,0x01D07821,0x020E7821,-,-,Preserve unsigned address-add operand order,,,false'
    if not before.endswith(b'\n'):raise ValueError('Asset walker guard predecessor has no final newline')
    return before+row+nl
def symbols():
    return dict(D_80082F80=0x80082F80,func_10003C6C=0x10003C6C,func_10004514=0x10004514,func_15015A38=0x15015A38,func_10004074=0x10004074)


def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze asset-walker predecessor first')
        screen=json.loads((out/'screen-inputs.json').read_text(encoding='utf-8'))
        for n,h in screen.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Asset walker screen input changed: '+n)
        names=sorted(set(screen)|{candidate.CALLER_OBJECT})
        values={}
        for n in sorted(set(names)):
            data=(root/n).read_bytes();q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);values[n]=sha(data)
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,GUARDS,candidate.CALLER_SOURCE,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen asset-walker input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected asset-walker input changed: '+n)
    old=(dest/GUARDS).read_bytes();new=proposed_guards(old)
    if(root/GUARDS).read_bytes() not in(old,new):raise ValueError('Asset walker guard history changed')
    return len(values)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def checked(raw,bindings,truth,normalized=False):
    expected=NORM_SHA if normalized else RAW_SHA
    if len(raw)!=SIZE or sha(raw)!=expected or bindings!=BINDINGS:raise ValueError('Asset walker complete body/bindings changed')
    literal=bytearray(raw)
    if not normalized:
        before=struct.unpack_from('>I',raw,0xC0)[0];after=0x020E7821
        if before!=0x01D07821 or before&0xFC00FFFF!=after&0xFC00FFFF or before>>21&31!=after>>16&31 or before>>16&31!=after>>21&31 or before&63!=33:raise ValueError('Asset walker guard is not a pure unsigned-add operand exchange')
        struct.pack_into('>I',literal,0xC0,after)
    if bound_blob(literal,bindings,symbols())!=list(struct.unpack('>70I',truth)):raise ValueError('Asset walker complete literal body differs')
    return raw,bindings


def compact_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after);ar,br=a.pop('.reginfo'),b.pop('.reginfo')
    old=bytes.fromhex('800000060000000000000000000000000000000000007ff0')
    new=bytes.fromhex('a31ffff60000000000000000000000000000000000007ff0')
    if ar[:4]!=br[:4]or ar[5:]!=br[5:]or ar[4]!=old or br[4]!=new:raise ValueError('Asset walker compact register metadata changed')
    raw,_=function_blob(after);mask=0
    for w in struct.unpack('>70I',raw):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0:regs=(rs,)if fn==8 else(rt,rd)if fn in(0,2,3)else(rs,rt,rd)
        elif op==3:regs=(31,)
        elif op==15:regs=(rt,)
        elif op in(9,10,12,13,33,35,36,40,41,43,4,5,20,21):regs=(rs,rt)
        else:raise ValueError('Unclassified keyed register word %08X'%w)
        for r in regs:
            if r:mask|=1<<r
    if int.from_bytes(old[:4],'big')|mask!=int.from_bytes(new[:4],'big'):raise ValueError('Asset walker aggregate register mask is not derived from its complete body')
    if a!=b:raise ValueError('Asset walker compact data pools changed')

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_42DC0.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

# Closed GNU hash-chain permutations caused by the new external references.
# Pin every definition, complete string block and byte position; exclude none.
METADATA_GROUPS=()

def reorder_metadata(before,result):
    rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
    for first,names,order in METADATA_GROUPS:
        group=[rows[first+16*i]for i in range(len(names))]
        if tuple(n for n,_,_ in group)!=names:raise ValueError('Asset walker named metadata group changed')
        strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
        if before[start:start+len(strings)]!=strings:raise ValueError('Asset walker symbol-name block changed')
        offset=0;name_offset=group[0][1][0]
        for slot,index in enumerate(order):
            name,fields,_=group[index];encoded=name.encode()+b'\0'
            struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:])
            result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
        if offset!=len(strings):raise ValueError('Asset walker metadata length changed')

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Asset walker literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Asset walker predecessor symbol asset-walker changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Asset walker literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    want=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if want!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Asset walker named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
    r=dict(calls=[4*i for i,w in enumerate(ws)if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],tails=[4*i for i,w in enumerate(ws)if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],pointers=[4*i for i,w in enumerate(ws)if w==ENTRY])
    if r!=dict(calls=[0x34DA0],tails=[],pointers=[]):raise ValueError('Asset walker caller census changed')
    if struct.unpack_from('>4I',rom,0x34DA0)!=(0x0D405648,0x00002025,0x0D402298,0):raise ValueError('Asset walker startup window changed')
    return r

def qualify_caller(root,out):
    from tools import pad_c_object
    before,after,_=candidate.caller_states((root/candidate.CALLER_SOURCE).read_text(encoding='utf-8'))
    frozen=(out/'match-frozen'/candidate.CALLER_SOURCE).read_text(encoding='utf-8')
    if before!=frozen:raise ValueError('Asset walker caller source predecessor changed')
    old,od=candidate.compile_owner(root,out,before,'match-caller-before');new,nd=candidate.compile_owner(root,out,after,'match-caller-narrow')
    if od or nd or same_functions(old,new)!=1 or alloc_pools(old)!=alloc_pools(new):raise ValueError('Asset walker caller ABI changes emitted data/code')
    hashes=[]
    for label,obj in (('before',old),('narrow',new)):
        p=out/('caller-padded-'+label);s=p.with_suffix('.s');o=p.with_suffix('.o')
        s.write_text(pad_c_object.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt','entrypoint',rodata_symbol='jtbl_80095A30_game',word_patches_path=root/GUARDS),encoding='utf-8')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
        hashes.append(sha(o.read_bytes()))
    if hashes[0]!=hashes[1] or hashes[0]!=sha((root/candidate.CALLER_OBJECT).read_bytes()):raise ValueError('Asset walker caller padded owner changed')
    return dict(raw_functions=1,pools_and_register_metadata_unchanged=True,padded_owner_sha256=hashes[0],prototype='void(s16)')


def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    caller=qualify_caller(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if candidate.diagnostics(od)!=candidate.diagnostics(nd):raise ValueError('Asset walker owner diagnostics changed: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked(*function_blob(new),truth)
    rn=same_functions(old,new,(FUNCTION,))
    compact_pools(old,new)
    before_csv=out/'match-frozen'/GUARDS;after_csv=out/'proposed-guards.csv';after_csv.write_bytes(proposed_guards(before_csv.read_bytes()))
    oo=assemble_owner(root,out,old,'match-predecessor-owner',before_csv);no=assemble_owner(root,out,new,'match-qualified-owner',after_csv)
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Asset walker live owner differs')
    checked(*function_blob(no),truth,normalized=True);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Asset walker padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'asset-walker-predecessor-image');ne=harness.link_image(root,out,no,'asset-walker-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Asset walker live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>70I',truth)):raise ValueError('Asset walker body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Asset walker protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=70,raw_words=70,raw_word_differences=1,frame=56,guards=1,bindings=6,raw_neighbors=rn,neighbors=pn,all_data_pools_unchanged=True,compact_pools_and_metadata_unchanged=False,compact_GPR_mask_before='80000006',compact_GPR_mask_after='A31FFFF6',compact_GPR_mask_body_derived=True,diagnostics=candidate.diagnostics(nd),qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(after_csv.read_bytes()),guard_predecessor_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=len(METADATA_GROUPS),all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root),caller_ABI=caller)
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
