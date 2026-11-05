"""Qualify the 60-byte point burst packet and its two closed scheduling cycles."""
import csv,hashlib,json,struct,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_point_burst_configuration_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_20A290.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/20A290.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BUILD='conker/build/game-point-burst-configuration-151DCDE0-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE,NATURAL_FRAME,RETAIL_FRAME=264,272,104,104
RAW_SHA256='48e55cb6768699ad4e8c69efe30b48cd464407db817dab8f7029b9a08fd18a33'
RETAIL_SHA256='c48ab78e23b381916876ed7555086bfa6271e675a796b3197d8c311aa5c3a8d6'
BASELINE_ELF_SHA256='2b159614d3d148da67218b70c03f8caa8e463dc23b675257e2c84325bdd5e5f9'
BINDINGS={0x18:[('R_MIPS_HI16','D_800AB558')],0x24:[('R_MIPS_LO16','D_800AB558')],
0x70:[('R_MIPS_HI16','D_800AB55C')],0x74:[('R_MIPS_LO16','D_800AB55C')],
0x78:[('R_MIPS_HI16','D_800AB560')],0x7C:[('R_MIPS_LO16','D_800AB560')],
0x80:[('R_MIPS_HI16','D_800AB564')],0x84:[('R_MIPS_LO16','D_800AB564')],
0x98:[('R_MIPS_HI16','D_800AB550')],0xBC:[('R_MIPS_LO16','D_800AB550')],
0x9C:[('R_MIPS_HI16','D_800AB554')],0xB8:[('R_MIPS_LO16','D_800AB554')],0xF0:[('R_MIPS_26','func_15152190')]}
PERMUTATION={**dict(zip(range(1,10),(6,9,1,2,3,4,5,7,8))),**dict(zip(range(46,53),(51,52,46,47,48,49,50)))}
RETAIL_BINDINGS={next((dst*4 for dst,src in PERMUTATION.items()if src*4==at),at):rows for at,rows in BINDINGS.items()}
PREIMAGES={1:0xAFBF0024,2:0xAFA40068,3:0xAFA5006C,4:0xAFA60070,5:0x8FB90068,6:0x3C010000,7:0x240E000C,8:0x240F0005,9:0xC4200000,
46:0x24C60000,47:0x24A50000,48:0xAFA00014,49:0x27A4002C,50:0x24070001,51:0xE7A0005C,52:0xE7A00060}
GUARD_WORDS=tuple((dst*4,PREIMAGES[dst],PREIMAGES[src])for dst,src in PERMUTATION.items())
PATCH_ROWS=tuple(dict(offset='0x%03X'%at,expected='0x%08X'%a,replacement='0x%08X'%b)for at,a,b in GUARD_WORDS)
SYMBOL_GROUPS=(
    (0x2A73BC,('D_800AB550','func_1500E70C','D_800AB940'),(1,2,0)),
    (0x2AADAC,('D_800A3304','D_80099004','D_8009E534'),(2,0,1)),
    (0x2AB1AC,('D_80099000','D_8009E530','D_8009E960'),(1,2,0)),
    (0x2B8E2C,('D_80099014','D_8009E974'),(1,0)),
    (0x2D609C,('D_800AB560','.L15034114_game_data','D_8009D300'),(1,2,0)))
source_states=candidate.source_states
def complete_row(row):
    at=int(row['offset'],0);binding=lambda rows:'|'.join(k+':'+s for k,s in rows)or'-'
    return dict(filename=FILENAME,function=FUNCTION,**row,expected_relocations=binding(BINDINGS.get(at,[])),replacement_relocations=binding(RETAIL_BINDINGS.get(at,[])),
        note='Derive initial scale snapshot and independent burst packet store schedules',insert_after='',insert_after_relocations='',omit='false')
def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Burst configuration raw body or bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Burst configuration retail body changed')
    words=struct.unpack('>66I',raw)
    if any(words[i]!=w for i,w in PREIMAGES.items()):raise ValueError('Burst configuration scheduling preimage changed')
    result=struct.pack('>66I',*(words[PERMUTATION.get(i,i)]for i in range(66)));expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26' else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if result!=bytes(expected):raise ValueError('Burst configuration fitted body differs')
    return result
def census(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)];pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0x82D2C]or pointers:raise ValueError('Burst configuration caller census changed')
    return dict(direct_calls=['0x82D2C'],pointers=[],caller='func_1505528C',abi='void(Position20A290 *, u8 channel, s32 context)',callee='func_15152190')
def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Burst configuration strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT_SIZE)
    if before[at+SIZE:at+SLOT_SIZE]!=bytes(8):raise ValueError('Burst configuration alignment changed')
    expected[at:at+SIZE]=truth;rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Burst configuration predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={name:(off,fields,string)for off,name,fields,string in symbol_rows(before)}
    for start,names,order in SYMBOL_GROUPS:
        group=[symbols[name]for name in names];strings=b''.join((name+'\0').encode()for name in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Burst configuration predecessor symbol group changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Burst configuration predecessor strings changed')
        if sorted(order)!=list(range(len(names))):raise ValueError('Burst configuration symbol group is not closed')
        text=b''
        for i,j in enumerate(order):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=147:raise ValueError('Burst configuration symbol serialization extent changed')
    if bytes(expected)!=after:
        offsets=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Burst configuration literal image differs: '+repr((len(offsets),list(map(hex,offsets[:40])))))
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=source_states((root/SOURCE).read_text())
    with(root/GUARDS).open(newline='')as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;live=list(reader)
    expected=[complete_row(r)for r in PATCH_ROWS];target=[r for r in live if r['filename']==FILENAME and r['function']==FUNCTION]
    if target!=(expected if installed else[]):raise ValueError('Burst configuration installed guards changed')
    old_rows=[r for r in live if not(r['filename']==FILENAME and r['function']==FUNCTION)];new_rows=old_rows+expected
    old_obj,old_diag=candidate.compile_owner(root,out,before_source,'predecessor-compact');new_obj,new_diag=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(old_diag)!=harness.diagnostics(new_diag):raise ValueError('Burst configuration owner diagnostics changed')
    fitted=normalized(*function_blob(new_obj),original_bytes(root))
    with patch.multiple(harness,FILENAME=FILENAME,ASM=ASM,OBJECT=OBJECT,LINKER=LINKER):
        old_owner=harness.assemble_owner(root,out,old_obj,old_rows,fields,'predecessor-owner');new_owner=harness.assemble_owner(root,out,new_obj,new_rows,fields,'qualified-owner')
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    if(new_owner if installed else old_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Burst configuration live owner differs')
    if function_blob(new_owner)!=(fitted,RETAIL_BINDINGS):raise ValueError('Burst configuration padded body differs')
    raw_neighbors=same_functions(old_obj,new_obj,(FUNCTION,));neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    for a,b in((old_obj,new_obj),(old_owner,new_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Burst configuration owner pools changed')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Burst configuration live image differs')
    delta=strict_image(before,after,original_bytes(root))
    old,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');new,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump');changed=[n for n in new if old[n]!=new[n]]
    slot=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SLOT_SIZE]
    if set(old)!=set(new)or aa!=bb or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>68I',slot)):raise ValueError('Burst configuration complete slot/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Burst configuration protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=66,slot_words=68,alignment_words=2,frame=104,guards=16,relocations=13,
        raw_neighbors=raw_neighbors,neighbors=neighbors,raw_sha256=RAW_SHA256,retail_sha256=RETAIL_SHA256,
        qualified_owner_sha256=hashlib.sha256(new_owner.read_bytes()).hexdigest(),predecessor_elf_sha256=BASELINE_ELF_SHA256,
        qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),changed_bodies=changed,all_addresses_fixed=True,
        strict_exclusions=0,strict_changed_bytes=delta,named_symbol_serialization_bytes=147,literal_full_image_prediction=True,registry=census(root),game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,predecessor_elf=old_elf,qualified_elf=new_elf,
        fields=fields,predecessor_rows=old_rows,qualified_rows=new_rows,qualified_compact=new_obj)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
