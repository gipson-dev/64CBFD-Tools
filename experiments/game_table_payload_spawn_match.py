"""Direct table payload constructor and a literal whole-image gate."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_table_payload_spawn_candidates as candidate
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
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game/generated_185560.c.o'
ASM='conker/asm/185560.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
REGISTRY='conker/asm/data/234400.rodata.s'
BASELINE_SHA='3d69279f0ee7f0d34f39a9a60f5d0a3aa5070fcf05f9be994af27770ec5e7134'
GUARD_SHA='b53721d727660eca66ed2771ba8fd8597642b08a123168033628a26ff92fd46b'
BINDINGS={20: [('R_MIPS_HI16', 'D_800A636C')], 32: [('R_MIPS_LO16', 'D_800A636C')], 228: [('R_MIPS_26', 'func_151A8B20')], 248: [('R_MIPS_26', 'memcpy')]}
RAW_SHA='6a4984688feea6f2a36c95cf929b25854c2eae1fd4a4ae5c4221e93be5889e27'
sha=lambda b:hashlib.sha256(b).hexdigest()

def proposed_guards(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Table payload guards changed')
    return before

def symbols():
    return dict(D_800A636C=0x800A636C,func_151A8B20=0x151A8B20,memcpy=0x10022EC0)

def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze table-payload motion predecessor first')
        screen=json.loads((out/'screen-inputs.json').read_text(encoding='utf-8'))
        for n,h in screen.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Table payload approach screen input changed: '+n)
        names=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,REGISTRY,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game/generated_1D4E00.c','conker/asm/1D4E00.s','conker/build/src/game/generated_1D4E00.c.o','conker/asm/data/24AB40.rodata.s']
        names += [q.relative_to(root).as_posix() for q in(root/'conker/include').rglob('*.h')]
        values={}
        for n in sorted(set(names)):
            data=(root/n).read_bytes();q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);values[n]=sha(data)
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen table-payload motion input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected table-payload motion input changed: '+n)
    old=(dest/GUARDS).read_bytes();new=proposed_guards(old)
    if(root/GUARDS).read_bytes() not in(old,new):raise ValueError('Table payload approach guard history changed')
    return len(values)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def checked(raw,bindings,truth,normalized=False):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Table payload complete raw body/bindings changed')
    if bound_blob(raw,bindings,symbols())!=list(struct.unpack('>68I',truth)):raise ValueError('Table payload original complete words changed')
    return raw,bindings

def compact_pools(before,after):
    if alloc_pools(before)!=alloc_pools(after):raise ValueError('Table payload compact pools/metadata changed')

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_185560.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

# Closed GNU hash-chain permutations caused by the new external references.
# Pin every definition, complete string block and byte position; exclude none.
METADATA_GROUPS=((0x2BA6DC,('func_15075BB8','D_8009E4D4'),(1,0)),)

def reorder_metadata(before,result):
    rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
    for first,names,order in METADATA_GROUPS:
        group=[rows[first+16*i]for i in range(len(names))]
        if tuple(n for n,_,_ in group)!=names:raise ValueError('Table payload named metadata group changed')
        strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
        if before[start:start+len(strings)]!=strings:raise ValueError('Table payload symbol-name block changed')
        offset=0;name_offset=group[0][1][0]
        for slot,index in enumerate(order):
            name,fields,_=group[index];encoded=name.encode()+b'\0'
            struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:])
            result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
        if offset!=len(strings):raise ValueError('Table payload metadata length changed')

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Table payload approach literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Table payload approach predecessor symbol table-payload changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Table payload approach literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    want=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if want!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Table payload approach named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
    r=dict(calls=[4*i for i,w in enumerate(ws)if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],tails=[4*i for i,w in enumerate(ws)if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],pointers=[4*i for i,w in enumerate(ws)if w==ENTRY])
    if r!=dict(calls=[],tails=[],pointers=[0x23445C]):raise ValueError('Table payload approach registration census changed')
    if '/* 23445C 8008F99C 1515A974 */ .word func_1515A974'not in(root/REGISTRY).read_text(encoding='utf-8'):raise ValueError('Table payload approach registration changed')
    return r

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if candidate.diagnostics(od)!=candidate.diagnostics(nd):raise ValueError('Table payload owner diagnostics changed: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked(*function_blob(new),truth)
    rn=same_functions(old,new,(FUNCTION,))
    compact_pools(old,new)
    before_csv=out/'match-frozen'/GUARDS;after_csv=out/'proposed-guards.csv';after_csv.write_bytes(proposed_guards(before_csv.read_bytes()))
    oo=assemble_owner(root,out,old,'match-predecessor-owner',before_csv);no=assemble_owner(root,out,new,'match-qualified-owner',after_csv)
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Table payload approach live owner differs')
    checked(*function_blob(no),truth,normalized=True);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Table payload approach padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'table-payload-predecessor-image');ne=harness.link_image(root,out,no,'table-payload-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Table payload approach live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Table payload approach body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Table payload approach protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=68,raw_words=68,raw_word_differences=0,frame=136,guards=0,bindings=4,raw_neighbors=rn,neighbors=pn,all_data_pools_unchanged=True,compact_pools_and_metadata_unchanged=True,diagnostics=candidate.diagnostics(nd),qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(after_csv.read_bytes()),guard_predecessor_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=len(METADATA_GROUPS),all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
