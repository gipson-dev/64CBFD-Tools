"""Direct oriented-effect constructor: complete owners and literal whole-image proof."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_oriented_effect_parameters_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_path_heading_turn_match import padded_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game/generated_108E90.c.o'
ASM='conker/asm/108E90.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
REGISTRY='conker/asm/data/22EF80.rodata.s'
BASELINE_SHA='16169692060a8ca375662bc2f555d3b6352d28fbb6514714aae7102e5ba32c03'
GUARD_SHA='31a596ab2aed75f8e41e1119155b7381d597b7ae51ceda71eaa56b9c78854cd8'
RAW_SHA='fe8d411d307647c7241053ab0ae591782fd791f1f750f77161db466ba17706b6'
BINDINGS={20:[('R_MIPS_HI16','D_800A0C24')],24:[('R_MIPS_LO16','D_800A0C24')],28:[('R_MIPS_HI16','D_800A0C28')],32:[('R_MIPS_LO16','D_800A0C28')],36:[('R_MIPS_HI16','D_800A0C2C')],40:[('R_MIPS_LO16','D_800A0C2C')],60:[('R_MIPS_HI16','D_800A0C30')],68:[('R_MIPS_LO16','D_800A0C30')],248:[('R_MIPS_26','func_15152F70')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def freeze(root,out):
    path=out/'input-sha256.json'
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze constructor predecessor first')
        initial=json.loads((out/'screen-inputs.json').read_text(encoding='utf-8'))
        for name,wanted in initial.items():
            if sha((root/name).read_bytes())!=wanted:raise ValueError('Screen input changed: '+name)
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,REGISTRY,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game/done/game_1765E0.c','conker/src/game/generated_17CAF0.c','conker/build/src/game/generated_17CAF0.c.o','conker/asm/17CAF0.s']
        paths += [p.relative_to(root).as_posix() for p in(root/'conker/include').rglob('*.h')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));changed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Constructor frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Constructor protected input changed: '+name)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items() if start<=at<start+size}

def checked(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Constructor raw body/bindings changed')
    if bound_blob(raw,bindings)!=list(struct.unpack('>68I',truth)):raise ValueError('Constructor original bytes changed')
    return raw,bindings

def compact_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after)
    # IDO's register-use metadata grows with the real float constructor.
    # Pin every byte of this sole expected metadata change, then all pools.
    ar,br=a.pop('.reginfo'),b.pop('.reginfo')
    if ar[:4]!=br[:4] or ar[5:]!=br[5:] or ar[4].hex()!='a300c7fe0000000000000000000000000000000000007ff0' or br[4].hex()!='a300fffe0000000000050551000000000000000000007ff0':raise ValueError('Constructor IDO register masks changed')
    if a!=b:raise ValueError('Constructor compact pools changed')

def assemble_owner(root,out,obj,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);asm=p/'owner.s';result=p/'generated_108E90.c.o'
    asm.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=root/GUARDS),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack_from('>%dI'%(len(rom)//4),rom)
    q=dict(calls=[i*4 for i,w in enumerate(ws) if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],tails=[i*4 for i,w in enumerate(ws) if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],pointers=[i*4 for i,w in enumerate(ws) if w==ENTRY])
    if q!=dict(calls=[],tails=[],pointers=[0x22EFA8]):raise ValueError('Constructor caller census changed')
    registry=(root/REGISTRY).read_text(encoding='utf-8')
    if '/* 22EFA8 8008A4E8 150DBC60 */ .word func_150DBC60' not in registry:raise ValueError('Constructor callback registration changed')
    return q

# Closed GNU hash-chain permutations caused by the new external references.
# Complete names, definitions, string blocks and resulting byte positions are
# predicted; no symbol table or string table bytes are excluded.
METADATA_GROUPS=(
    (0x2A068C,('D_8009A9F8','D_8009E4F8'),(1,0)),
    (0x2B093C,('func_1506FD30','D_800A6754','D_8009E4FC'),(2,0,1)),
    (0x2B23CC,('D_800A0C2C','D_80096BFC','D_800A77A8','D_8009E668','D_800A48FC'),(1,2,3,4,0)),
    (0x2B5A2C,('D_800A0C24','D_800A03F4','D_800A48F4'),(1,2,0)),
    (0x2B9A2C,('D_800A0C28','D_800A03F8','D_80096BF8','D_800A48F8'),(1,2,3,0)),
    (0x2C1FBC,('D_800A0C30','D_800A07B0'),(1,0)),
)

def reorder_metadata(before,result):
    rows={p:(n,f,s) for p,n,f,s in symbol_rows(before)}
    for first,names,order in METADATA_GROUPS:
        group=[rows[first+16*i] for i in range(len(names))]
        if tuple(n for n,_,_ in group)!=names:raise ValueError('Constructor named metadata group changed')
        strings=b''.join(n.encode()+b'\0' for n in names);start=group[0][2]
        if before[start:start+len(strings)]!=strings:raise ValueError('Constructor symbol-name block changed')
        offset=0;name_offset=group[0][1][0]
        for slot,index in enumerate(order):
            name,fields,_=group[index];encoded=name.encode()+b'\0'
            struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
        if offset!=len(strings):raise ValueError('Constructor metadata length changed')

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Constructor literal inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f) for p,n,f,s in symbol_rows(before) if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Constructor predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError('Constructor literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:]) for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:]) for p,n,f,s in symbol_rows(after)):raise ValueError('Constructor named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    if od or nd:raise ValueError('Constructor owner diagnostics changed: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked(*function_blob(new),truth)
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Constructor guards changed')
    rn=same_functions(old,new,(FUNCTION,))
    compact_pools(old,new)
    oo=assemble_owner(root,out,old,'predecessor-owner');no=assemble_owner(root,out,new,'qualified-owner')
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Constructor live owner differs')
    checked(*function_blob(no),truth);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Constructor padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'predecessor-image');ne=harness.link_image(root,out,no,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Constructor live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b) or aa!=bb or changed!=[FUNCTION] or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Constructor body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Constructor protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=68,raw_words=68,frame=112,input_bytes=88,input_SP_offset=24,guards=0,bindings=9,raw_neighbors=rn,neighbors=pn,all_pools_unchanged=True,diagnostics='',qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
