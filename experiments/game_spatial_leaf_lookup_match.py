"""Direct spatial leaf lookup, pointer ABI, complete owners and literal ELF gate."""
import csv,hashlib,json,re,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_spatial_leaf_lookup_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game/generated_13BB20.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/13BB20.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
RAW_SHA='29ef167bd2d2248907a4a488573cf2c06997ff8a6d93bfad8d402eaeff93b329'
TRUTH_SHA='eaf82f4e2f801cf8feab9483cea652733efba6bb1fb347aeb4e8beb8792e209e'
BASELINE_SHA='94f8cc66a05885e429df07ebdf25554d0143f3d4fd7803c5fbf62890aa9b6fdc'
GUARD_SHA='892dcc21c80c8cc41c6970ed89c7f218e072b5a5487946d406a0d133e7f6d6d6'
BINDINGS={4:[('R_MIPS_HI16','D_800DBE48')],8:[('R_MIPS_LO16','D_800DBE48')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Spatial lookup raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Spatial lookup original changed')
    expected=bytearray(truth)
    for at in bindings:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if raw!=expected:raise ValueError('Spatial lookup direct words differ')
    return raw

def assemble_owner(root,out,obj,label):
    path=out/label;path.mkdir(parents=True,exist_ok=True);asm=path/(FILENAME+'.c.s');result=path/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Spatial lookup strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Spatial lookup predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Spatial lookup literal image differs: '+repr((len(before),len(after),len(differences),list(map(hex,differences[:40])))))
    expected_symbols=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if expected_symbols!=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(after)):raise ValueError('Spatial lookup named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    data=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(data)-3,4):
        word=struct.unpack_from('>I',data,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if word>>26!=3:raise ValueError('Unexpected spatial lookup tail call')
            calls.append(at)
    if pointers or len(calls)!=26:raise ValueError('Spatial lookup census changed')
    return calls

def qualify_callers(root,out,installed):
    rows=json.loads((out/'call-census.json').read_text());owners={r['owner']:r for r in rows}
    if len(owners)!=14 or census(root)!=[r['rom']for r in rows]:raise ValueError('Spatial lookup caller inventory changed')
    before_header,after_header,current=candidate.repair_states('conker/include/functions.h',(root/'conker/include/functions.h').read_text())
    if current!=installed:raise ValueError('Spatial lookup header installation changed')
    overlays={}
    for label,text in(('before',before_header),('after',after_header)):
        path=out/('header-'+label)/'functions.h';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);overlays[label]=path.relative_to(root/'conker').as_posix()
    report=[]
    for owner,row in sorted(owners.items()):
        if owner==FILENAME:continue
        path=row['source'];before=after=live=(root/path).read_text()
        if path in candidate.REPAIRS:
            before,after,current=candidate.repair_states(path,live)
            if current!=installed:raise ValueError('Spatial lookup caller installation changed: '+path)
        objects=[];diagnostics=[]
        for label,text in(('before',before),('after',after)):
            text=re.sub(r'(?m)^#\s*include\s*["<]functions\.h[">]',lambda _:'#include "'+overlays[label]+'"',text)
            obj,diag=candidate.compile_owner(root,out,text,'caller-'+owner+'-'+label);objects.append(obj);diagnostics.append(harness.diagnostics(diag))
        if diagnostics[0]!=diagnostics[1]:raise ValueError('Spatial lookup caller diagnostics changed: '+owner)
        count=same_functions(*objects)
        if alloc_pools(objects[0])!=alloc_pools(objects[1]):raise ValueError('Spatial lookup caller allocatable sections changed: '+owner)
        report.append(dict(owner=owner,unchanged_functions=count,allocatable_pools_unchanged=True))
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    for path in candidate.REPAIRS:
        if candidate.repair_states(path,(root/path).read_text())[2]!=installed:raise ValueError('Partial spatial lookup installation: '+path)
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Spatial lookup guards changed')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if od or nd:raise ValueError('Spatial lookup owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized(*function_blob(new),truth)
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Spatial lookup compact allocatable sections changed')
    old_owner=assemble_owner(root,out,old,'predecessor-owner');new_owner=assemble_owner(root,out,new,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Spatial lookup live owner differs')
    if function_blob(new_owner)!=(function_blob(new)[0],BINDINGS):raise ValueError('Spatial lookup padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Spatial lookup padded allocatable sections changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Spatial lookup live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Spatial lookup body/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Spatial lookup protected data changed')
    callers=qualify_callers(root,out,installed)
    report=dict(function=FUNCTION,source_installed=installed,words=68,frame=0,guards=0,bindings=2,raw_neighbors=raw_neighbors,neighbors=neighbors,
        qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,
        all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=26,caller_owners=14,caller_profiles=callers)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
