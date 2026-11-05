"""Direct list dispatcher, signed root/word arguments, callers and whole image."""
import hashlib,json,re,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_node_payload_dispatch_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments import game_recursive_node_search as recursive
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=264,candidate.BUILD
OBJECT='conker/build/src/game/generated_179F30.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/179F30.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
RAW_SHA='0d963230f51acf20fce38e6ca82b66cb9afdbca9dfaaddc8e234d229477556b3'
TRUTH_SHA='1b4ee138e6a3ebc678e083572c38d424243fdc1066ea0f4b764e76a1e9555cfe'
BASELINE_SHA='c896ff6aec86e3f2311c1b13f8a999dbbb9b175dece56efc0b2bc208f86d8200'
GUARD_SHA='892dcc21c80c8cc41c6970ed89c7f218e072b5a5487946d406a0d133e7f6d6d6'
BINDINGS={68:[('R_MIPS_HI16','D_8008AB64')],80:[('R_MIPS_LO16','D_8008AB64')],84:[('R_MIPS_HI16','D_8008ABE8')],88:[('R_MIPS_LO16','D_8008ABE8')],120:[('R_MIPS_26','func_1514D4B8')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Node dispatcher raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Node dispatcher original changed')
    expected=bytearray(truth)
    for at,rows in bindings.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=expected:raise ValueError('Node dispatcher direct words differ')
    return raw

def assemble_owner(root,out,obj,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Node dispatcher strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Node dispatcher predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Node dispatcher literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:40])))))
    wanted=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if wanted!=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(after)):raise ValueError('Node dispatcher named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    data=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(data)-3,4):
        word=struct.unpack_from('>I',data,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if word>>26!=3:raise ValueError('Unexpected node dispatcher tail call')
            calls.append(at)
    if pointers or len(calls)!=6:raise ValueError('Node dispatcher call inventory changed')
    return calls

def frozen_inputs(root,out):
    manifest=json.loads((out/'input-sha256.json').read_text())
    if len(manifest)!=145:raise ValueError('Node dispatcher frozen inventory changed')
    changed={SOURCE,*candidate.REPAIRS,ELF,OBJECT,'conker/build/conker.us.bin','conker/progress.csv','graphify-out/graph.json'}
    for name,wanted in manifest.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Node dispatcher frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Node dispatcher protected input changed: '+name)
    return len(manifest)

def qualify_callers(root,out,installed):
    rows=json.loads((out/'call-census.json').read_text());owners={r['owner']:r for r in rows}
    if len(owners)!=4 or census(root)!=[r['rom']for r in rows]:raise ValueError('Node dispatcher caller census changed')
    before_header,after_header,current=candidate.repair_states('conker/include/functions.h',(root/'conker/include/functions.h').read_text())
    if current!=installed:raise ValueError('Node dispatcher header installation changed')
    overlays={}
    for label,text in(('before',before_header),('after',after_header)):
        path=out/('header-'+label)/'functions.h';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);overlays[label]=path.relative_to(root/'conker').as_posix()
    report=[]
    for owner,row in sorted(owners.items()):
        path=row['source'];before=after=live=(root/path).read_text()
        if path in candidate.REPAIRS:
            before,after,current=candidate.repair_states(path,live)
            if current!=installed:raise ValueError('Node dispatcher caller installation changed: '+path)
        objects=[];diagnostics=[]
        for label,text in(('before',before),('after',after)):
            text=re.sub(r'(?m)^#\s*include\s*["<]functions\.h[">]',lambda _:'#include "'+overlays[label]+'"',text)
            obj,diag=candidate.compile_owner(root,out,text,'caller-'+owner+'-'+label);objects.append(obj);diagnostics.append(harness.diagnostics(diag))
        removed=0
        if diagnostics[0]!=diagnostics[1]and owner=='game_A28B0':
            pattern=r'cfe: Warning 712: <unit>, line #: illegal combination of pointer and integer\n     func_1514D3B0\(D_800D154C, tmp0, tmp1, tmp2\);\n[- ]+\^\n'
            stripped,removed=re.subn(pattern,'',diagnostics[0])
            if removed!=1 or stripped!=diagnostics[1]:raise ValueError('Unexpected node dispatcher caller warning change')
        elif diagnostics[0]!=diagnostics[1]:raise ValueError('Node dispatcher caller diagnostics changed: '+owner)
        count=same_functions(*objects)
        if alloc_pools(objects[0])!=alloc_pools(objects[1]):raise ValueError('Node dispatcher caller allocatable sections changed: '+owner)
        report.append(dict(owner=owner,unchanged_functions=count,allocatable_pools_unchanged=True,removed_owner_pointer_warning=removed))
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    frozen_count=frozen_inputs(root,out)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    for path in candidate.REPAIRS:
        if candidate.repair_states(path,(root/path).read_text())[2]!=installed:raise ValueError('Partial node dispatcher installation: '+path)
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Node dispatcher guard manifest changed')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    diagnostics=harness.diagnostics(od)
    if diagnostics!=harness.diagnostics(nd)or diagnostics.count('Warning 712:')!=4:raise ValueError('Node dispatcher owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized(*function_blob(new),truth)
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    ap,bp=alloc_pools(old),alloc_pools(new)
    ai=bytes.fromhex('a31ffffe0000000000050550000000000000000000007ff0')
    bi=bytes.fromhex('a3fffffe0000000000050550000000000000000000007ff0')
    if ap.get('.reginfo')!=(1879048198,2,0,4,ai,())or bp.get('.reginfo')!=(1879048198,2,0,4,bi,()):raise ValueError('Node dispatcher S5/S6/S7 register mask changed')
    if {k:v for k,v in ap.items()if k!='.reginfo'}!={k:v for k,v in bp.items()if k!='.reginfo'}:raise ValueError('Node dispatcher compact allocatable sections changed')
    old_owner=assemble_owner(root,out,old,'predecessor-owner');new_owner=assemble_owner(root,out,new,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Node dispatcher live owner differs')
    if function_blob(new_owner)!=(function_blob(new)[0],BINDINGS):raise ValueError('Node dispatcher padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Node dispatcher padded allocatable sections changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Node dispatcher live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>66I',truth)):raise ValueError('Node dispatcher body/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Node dispatcher protected data changed')
    context=recursive.retail_context({'conker/conker.us.bin':(root/ROM_IMAGE).read_bytes(),'conker/build/conker.us.elf':after})
    (out/'retail-node-context.json').write_text(json.dumps(context,indent=2)+'\n')
    callers=qualify_callers(root,out,installed)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen_count,words=66,frame=56,guards=0,bindings=5,raw_neighbors=raw_neighbors,neighbors=neighbors,
        qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,
        all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=6,caller_owners=4,caller_profiles=callers,unchanged_owner_warning_count=4)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
