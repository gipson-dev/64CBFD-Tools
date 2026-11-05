"""Qualify a nine-word closed register allocation and the complete linked image."""
import csv,hashlib,io,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_material_tile_animation_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=284,candidate.BUILD
OBJECT='conker/build/src/game/generated_105760.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/105760.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
RAW_SHA='cd537882e4bdcc4f58af8c59bb00d49e486d0a22dbde9cc57277d9806f038012'
TRUTH_SHA='e9065d4c611170e40c9548a5efd4a6a6c7165c835187114e63b937b11ac95d73'
BASELINE_SHA='b64005a3ff94807627d9ab64a9793ab03814e9105d27b102120db133eb334895'
GUARD_SHA='98c78a54647943d6bad989031ecb0256e24cf2247923f8fd992118dc7ba00810'
BINDINGS={4:[('R_MIPS_HI16','D_80090298')],8:[('R_MIPS_LO16','D_80090298')],112:[('R_MIPS_HI16','D_800A0B10')],128:[('R_MIPS_LO16','D_800A0B10')]}
PATCHES=((204,0x006C1821,0x006C2021),(208,0x8C620000,0x8C820000),(216,0x00026B03,0x00027303),
 (224,0x31AE0FFF,0x31CF0FFF),(232,0x44043000,0x44073000),(240,0x04810002,0x04E10002),
 (244,0x00803025,0x00E03025),(248,0x008E3021,0x00EF3021),(268,0xAC690000,0xAC890000))
SYMBOL_GROUPS=((0x29F1DC,('D_800A0B10','D_800A02E0','D_8009FEE0','D_800A0F60'),(1,2,3,0)),
               (0x2BE30C,('D_80090298','D_800A6F98'),(1,0)))
sha=lambda b:hashlib.sha256(b).hexdigest()

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Material callback raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Material callback original changed')
    result=bytearray(raw)
    for at,old,new in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=old:raise ValueError('Material callback register guard changed')
        struct.pack_into('>I',result,at,new)
    expected=bytearray(truth)
    for at in bindings:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if result!=expected:raise ValueError('Material callback normalized body differs')
    return bytes(result)

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Material callback inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Material callback predecessor already guarded')
    rows=[dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations='-',replacement_relocations='-',
        note='Normalize closed material tile callback register allocation',insert_after='',insert_after_relocations='',omit='false')for at,old,new in PATCHES]
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator='\r\n');writer.writerows(rows)
    return before+out.getvalue().encode()

def assemble_owner(root,out,obj,manifest,label):
    path=out/label;path.mkdir(parents=True,exist_ok=True);guards=path/'patches.csv';guards.write_bytes(manifest)
    asm=path/(FILENAME+'.c.s');result=path/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=guards,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Material callback strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Material callback original extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={name:(off,fields,string)for off,name,fields,string in symbol_rows(before)}
    for start,names,order in SYMBOL_GROUPS:
        group=[symbols[name]for name in names];strings=b''.join((name+'\0').encode()for name in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Material callback symbol serialization baseline changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Material callback original string block changed')
        text=b''
        for i,j in enumerate(order):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=30:raise ValueError('Material callback named serialization extent changed')
    if bytes(expected)!=after:
        differences=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Material callback literal image differs: '+repr((len(before),len(after),len(differences),list(map(hex,differences[:40])))))
    definitions=lambda data:Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(data))
    changed=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if changed!=definitions(after):raise ValueError('Material callback named symbols changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    data=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(data)-3,4):
        word=struct.unpack_from('>I',data,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:calls.append(at)
    if calls or pointers!=[0x228C84]:raise ValueError('Material callback registration census changed')
    if struct.unpack_from('>I',data,0x5DA48)[0]!=0x0320F809:raise ValueError('Material callback indirect dispatcher changed')
    return dict(direct_calls=0,registered_pointer_rom=pointers[0],table=0x800841C0,index=1,dispatcher=0x15030578,indirect_call=0x15030598,continuation=0x150305A4)

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    frozen=out/'frozen';old_guards=(frozen/GUARDS).read_bytes();new_guards=guard_manifest(old_guards)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial material callback installation')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if od or nd:raise ValueError('Unexpected material callback diagnostics')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized(*function_blob(new),truth)
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    old_pools,new_pools=alloc_pools(old),alloc_pools(new)
    before_info=bytes.fromhex('a300f9f60000000000055df0000000000000000000007ff0')
    after_info=bytes.fromhex('a300fffe0000000000075df7000000000000000000007ff0')
    if old_pools.get('.reginfo')!=(1879048198,2,0,4,before_info,()) or new_pools.get('.reginfo')!=(1879048198,2,0,4,after_info,()):raise ValueError('Material callback compact register masks changed')
    if {k:v for k,v in old_pools.items()if k!='.reginfo'}!={k:v for k,v in new_pools.items()if k!='.reginfo'}:raise ValueError('Material callback compact pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Material callback live owner differs')
    if function_blob(new_owner)!=(normalized(*function_blob(new),truth),BINDINGS):raise ValueError('Material callback padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Material callback padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Material callback live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Material callback body/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=71,frame=0,guards=9,bindings=4,raw_neighbors=raw_neighbors,neighbors=neighbors,
        qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,
        all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,registration=census(root))
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
