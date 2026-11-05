"""Direct random/color descriptor: whole owner, registration and complete image."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_random_colored_effect_descriptor_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=268,candidate.BUILD
OBJECT='conker/build/src/game/generated_176A00.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/176A00.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
RAW_SHA='f2969440d7eafdb519d6529b4c42ff67ed291d73f771dc91bcfd28ae193adfd0'
TRUTH_SHA='16caf9b2249e3385078f6daa7f74f48c10495f1e233bc89590fecd57c79e7355'
BASELINE_SHA='15b6a6f00f9db774fb5998dcc036398c8f2237bc2a2090a0db6031045a7ba592'
GUARD_SHA='892dcc21c80c8cc41c6970ed89c7f218e072b5a5487946d406a0d133e7f6d6d6'
BINDINGS={at:[('R_MIPS_26',name)]for at,name in((40,'func_150ADA20'),(76,'func_150ADA20'),(100,'func_150ADA20'),
 (148,'func_151429E0'),(168,'func_151429E0'),(180,'func_150ADA20'),(204,'func_150ADA20'),(240,'func_1518CA80'))}
sha=lambda b:hashlib.sha256(b).hexdigest()

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random/color descriptor raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Random/color descriptor original changed')
    expected=bytearray(truth)
    for at in bindings:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFC000000)
    if raw!=expected:raise ValueError('Random/color descriptor direct words differ')
    return raw

def assemble_owner(root,out,obj,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Random/color descriptor strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Random/color descriptor predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Random/color descriptor literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:40])))))
    wanted=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if wanted!=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(after)):raise ValueError('Random/color descriptor named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    data=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(data)-3,4):
        word=struct.unpack_from('>I',data,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:calls.append(at)
    if calls or pointers!=[0x22E8D4]:raise ValueError('Random/color descriptor registry changed')
    return dict(direct_calls=0,pointer_rom=0x22E8D4,table=0x80089E10,index=1,caller='func_1513CFE4',window=0x1513D290,indirect_call=0x1513D2B8,end=0x1513D2D0)

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Random/color descriptor guard manifest changed')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    diagnostics=harness.diagnostics(od)
    if diagnostics!=harness.diagnostics(nd)or diagnostics.count('Warning 712:')!=1 or 'func_1514BF50(arg0);'not in diagnostics:raise ValueError('Random/color descriptor owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized(*function_blob(new),truth)
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    a_pools,b_pools=alloc_pools(old),alloc_pools(new)
    a_info=bytes.fromhex('e3fffefe00000000ffff5ff7000000000000000000007ff0')
    b_info=bytes.fromhex('e3fffffe00000000ffff5ff7000000000000000000007ff0')
    if a_pools.get('.reginfo')!=(1879048198,2,0,4,a_info,())or b_pools.get('.reginfo')!=(1879048198,2,0,4,b_info,()):raise ValueError('Random/color descriptor compact T0 register mask changed')
    if {k:v for k,v in a_pools.items()if k!='.reginfo'}!={k:v for k,v in b_pools.items()if k!='.reginfo'}:raise ValueError('Random/color descriptor compact allocatable sections changed')
    old_owner=assemble_owner(root,out,old,'predecessor-owner');new_owner=assemble_owner(root,out,new,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Random/color descriptor live owner differs')
    if function_blob(new_owner)!=(function_blob(new)[0],BINDINGS):raise ValueError('Random/color descriptor padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Random/color descriptor padded allocatable sections changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Random/color descriptor live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>67I',truth)):raise ValueError('Random/color descriptor body/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Random/color descriptor protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=67,frame=80,guards=0,bindings=8,raw_neighbors=raw_neighbors,neighbors=neighbors,
        qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,
        all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,registration=census(root),unchanged_owner_warning=diagnostics)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
